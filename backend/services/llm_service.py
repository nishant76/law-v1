"""
LLM Service — all AI/LLM calls go through this class
Handles both Azure OpenAI and direct OpenAI API with automatic provider selection.
Support for embeddings, completions with retry logic and safety checks.
Never instantiate OpenAI client outside this service.
"""

import asyncio
import logging
from typing import Optional, List, Dict, Any, Union
from datetime import datetime, timedelta
from enum import Enum

from openai import AsyncAzureOpenAI, AsyncOpenAI, RateLimitError, InternalServerError, APIError

from backend.core.config import settings
from backend.core.logger import get_logger

logger = get_logger(__name__)


class ModelType(str, Enum):
    """Available models"""
    GPT4O = "gpt-4o"
    GPT4O_MINI = "gpt-4o-mini"
    GPT52 = "gpt-5.2"
    EMBEDDING = "text-embedding-ada-002"


class LLMError(Exception):
    """Base LLM error"""
    pass


class LLMRateLimitError(LLMError):
    """Rate limit exceeded"""
    pass


class LLMContentFilterError(LLMError):
    """Content filter triggered"""
    pass


class LLMTokenLimitError(LLMError):
    """Token limit exceeded"""
    pass


class LLMService:
    """
    OpenAI service wrapper supporting both Azure OpenAI and direct OpenAI API.
    Provider selection is automatic based on USE_AZURE_OPENAI config flag.
    
    Rules:
    - Retry on RateLimitError: 3x with backoff (1s, 2s, 4s)
    - Retry on InternalServerError: 3x then graceful message
    - No retry on ContentFilterError
    - No retry on TokenLimitError
    - Alert on single request > 10,000 tokens
    - Hard token limit per firm per day (GAP-003)
    """
    
    def __init__(self):
        """Initialize OpenAI client (Azure or direct based on config)"""
        self.use_azure = settings.USE_AZURE_OPENAI
        
        if self.use_azure:
            # Initialize Azure OpenAI
            logger.info("Initializing Azure OpenAI client")
            self.client: Union[AsyncAzureOpenAI, AsyncOpenAI] = AsyncAzureOpenAI(
                api_key=settings.AZURE_OPENAI_API_KEY or "",
                api_version=settings.AZURE_OPENAI_API_VERSION,
                azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
            )
        else:
            # Initialize direct OpenAI API
            logger.info("Initializing direct OpenAI API client")
            self.client: Union[AsyncAzureOpenAI, AsyncOpenAI] = AsyncOpenAI(
                api_key=settings.OPENAI_API_KEY,
                organization=settings.OPENAI_ORG_ID,
            )
        
        # Token tracking per firm per day
        self.firm_daily_tokens: Dict[str, Dict[str, Any]] = {}
        self.FIRM_DAILY_TOKEN_LIMIT = 1_000_000  # 1M tokens/day per firm
    
    async def embed_query(self, query: str) -> List[float]:
        """
        Convert query string to vector using text-embedding model.
        Uses Azure embedding deployment or direct OpenAI API based on config.
        
        Args:
            query: Search query text
            
        Returns:
            Vector embedding (1536 dimensions)
            
        Raises:
            LLMError: If embedding fails
        """
        try:
            logger.debug(f"Embedding query: {query[:100]}...")
            
            # Get embedding model name
            if self.use_azure:
                embedding_model = settings.EMBEDDING_DEPLOYMENT
            else:
                embedding_model = "text-embedding-3-large"  # Direct OpenAI uses text-embedding-3-large
            
            response = await self.client.embeddings.create(
                input=query,
                model=embedding_model,
                encoding_format="float",
            )
            
            # Extract embedding vector
            embedding = response.data[0].embedding
            logger.debug(f"Embedding generated: {len(embedding)} dimensions")
            
            return embedding
            
        except RateLimitError as e:
            logger.error(f"Rate limit on embeddings: {e}")
            raise LLMRateLimitError(str(e))
            logger.error(f"Service unavailable on embeddings: {e}")
            raise LLMError(f"Embedding service temporarily unavailable: {str(e)}")
        except Exception as e:
            logger.error(f"Error embedding query: {e}")
            raise LLMError(f"Failed to embed query: {str(e)}")

    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Embed a batch of texts using embedding model (Azure or OpenAI)."""
        try:
            # Get embedding model name
            if self.use_azure:
                embedding_model = settings.EMBEDDING_DEPLOYMENT
            else:
                embedding_model = "text-embedding-3-large"  # Direct OpenAI uses text-embedding-3-large
            
            response = await self.client.embeddings.create(
                input=texts,
                model=embedding_model,
                encoding_format="float",
            )
            embeddings = [item.embedding for item in response.data]
            logger.debug(f"Embedded {len(embeddings)} texts")
            return embeddings
        except RateLimitError as e:
            logger.error(f"Rate limit on embeddings: {e}")
            raise LLMRateLimitError(str(e))
        except InternalServerError as e:
            logger.error(f"Service unavailable on embeddings: {e}")
            raise LLMError(f"Embedding service temporarily unavailable: {str(e)}")
        except Exception as e:
            logger.error(f"Error embedding texts: {e}")
            raise LLMError(f"Failed to embed texts: {str(e)}")
    
    async def call_completion(
        self,
        system_prompt: str,
        user_prompt: str,
        model: ModelType = ModelType.GPT4O_MINI,
        temperature: float = 0.0,
        max_tokens: Optional[int] = None,
        firm_id: Optional[str] = None,
        timeout: int = 30,
    ) -> str:
        """
        Call Azure OpenAI chat completion with retry logic
        
        Args:
            system_prompt: System instructions
            user_prompt: User message
            model: Model to use (GPT4O or GPT4O_MINI)
            temperature: Randomness (0.0=deterministic)
            max_tokens: Max response tokens
            firm_id: Firm ID for token tracking
            timeout: Request timeout in seconds
            
        Returns:
            Response text
            
        Raises:
            LLMError: If completion fails
        """
        
        # Estimate tokens in request
        estimated_tokens = self._estimate_tokens(system_prompt + user_prompt)
        
        # Alert if exceeds 10,000 tokens
        if estimated_tokens > 10_000:
            logger.warning(
                f"Large request ({estimated_tokens} tokens) from firm {firm_id}: "
                f"{user_prompt[:100]}..."
            )
        
        # Check firm daily limit
        if firm_id:
            await self._check_firm_token_limit(firm_id, estimated_tokens)
        
        # Get model name / deployment name based on provider
        if self.use_azure:
            # Azure OpenAI uses deployment names
            if model == ModelType.GPT4O:
                model_name = settings.GPT4O_DEPLOYMENT
            elif model == ModelType.GPT52:
                model_name = settings.GPT52_DEPLOYMENT
            else:
                model_name = settings.GPT4O_MINI_DEPLOYMENT
        else:
            # Direct OpenAI uses model names
            if model == ModelType.GPT4O:
                model_name = "gpt-4o"
            elif model == ModelType.GPT52:
                model_name = "gpt-5.2"
            else:
                model_name = "gpt-4o-mini"
        
        # Retry logic: RateLimitError (3x), InternalServerError (3x)
        max_retries = 3
        backoff_seconds = [1, 2, 4]
        
        for attempt in range(max_retries + 1):
            try:
                # gpt-5.2 uses max_completion_tokens (via extra_body to support
                # older SDK versions); all other models use max_tokens directly.
                if model == ModelType.GPT52:
                    create_kwargs = dict(
                        model=model_name,
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt},
                        ],
                        temperature=temperature,
                        top_p=1.0,
                        extra_body={"max_completion_tokens": max_tokens} if max_tokens else {},
                    )
                else:
                    create_kwargs = dict(
                        model=model_name,
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt},
                        ],
                        temperature=temperature,
                        max_tokens=max_tokens,
                        top_p=1.0,
                    )
                response = await asyncio.wait_for(
                    self.client.chat.completions.create(**create_kwargs),
                    timeout=timeout
                )
                
                # Track tokens
                if firm_id:
                    actual_tokens = response.usage.total_tokens
                    await self._track_firm_tokens(firm_id, actual_tokens)
                
                return response.choices[0].message.content
                
            except RateLimitError as e:
                if attempt < max_retries:
                    wait_time = backoff_seconds[attempt]
                    logger.warning(
                        f"Rate limit (attempt {attempt + 1}/{max_retries + 1}), "
                        f"retrying in {wait_time}s: {e}"
                    )
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"Rate limit exceeded after {max_retries} retries")
                    raise LLMRateLimitError(f"Rate limit exceeded: {str(e)}")
            
            except InternalServerError as e:
                if attempt < max_retries:
                    wait_time = backoff_seconds[attempt]
                    logger.warning(
                        f"Service unavailable (attempt {attempt + 1}/{max_retries + 1}), "
                        f"retrying in {wait_time}s: {e}"
                    )
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"Service unavailable after {max_retries} retries")
                    raise LLMError(
                        "OpenAI service is temporarily unavailable. Please try again in a few minutes."
                    )
            
            except APIError as e:
                error_str = str(e).lower()
                
                # Content filter triggered — no retry
                if "content_filter" in error_str or "content blocked" in error_str:
                    logger.error(f"Content filter triggered: {e}")
                    raise LLMContentFilterError(
                        "Content filter triggered. Please rephrase your request."
                    )
                
                # Token limit — no retry
                if "token" in error_str and "exceed" in error_str:
                    logger.error(f"Token limit exceeded: {e}")
                    raise LLMTokenLimitError(
                        "Request is too large. Please split into smaller parts."
                    )
                
                # Other API errors — retry
                if attempt < max_retries:
                    wait_time = backoff_seconds[attempt]
                    logger.warning(
                        f"API error (attempt {attempt + 1}/{max_retries + 1}), "
                        f"retrying in {wait_time}s: {e}"
                    )
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"API error after {max_retries} retries: {e}")
                    raise LLMError(f"OpenAI API error: {str(e)}")
            
            except asyncio.TimeoutError:
                if attempt < max_retries:
                    wait_time = backoff_seconds[attempt]
                    logger.warning(
                        f"Timeout (attempt {attempt + 1}/{max_retries + 1}), "
                        f"retrying in {wait_time}s"
                    )
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"Timeout after {max_retries} retries")
                    raise LLMError("Request timeout. Please try again.")
            
            except Exception as e:
                logger.error(f"Unexpected error in completion: {e}", exc_info=True)
                raise LLMError(f"Failed to generate response: {str(e)}")
        
        raise LLMError("Unknown error in completion call")
    
    async def call_chat_completion(
        self,
        system_prompt: str,
        messages: List[Dict[str, str]],
        model: ModelType = ModelType.GPT52,
        temperature: float = 0.0,
        max_tokens: Optional[int] = None,
        firm_id: Optional[str] = None,
        timeout: int = 60,
    ) -> str:
        """
        Multi-turn chat completion. Accepts full conversation history.
        messages: list of {"role": "user"|"assistant", "content": "..."}
        """
        combined_text = system_prompt + " ".join(m.get("content", "") for m in messages)
        estimated_tokens = self._estimate_tokens(combined_text)

        if estimated_tokens > 10_000:
            logger.warning(f"Large chat request ({estimated_tokens} tokens) from firm {firm_id}")

        if firm_id:
            await self._check_firm_token_limit(firm_id, estimated_tokens)

        if self.use_azure:
            if model == ModelType.GPT4O:
                model_name = settings.GPT4O_DEPLOYMENT
            elif model == ModelType.GPT52:
                model_name = settings.GPT52_DEPLOYMENT
            else:
                model_name = settings.GPT4O_MINI_DEPLOYMENT
        else:
            if model == ModelType.GPT4O:
                model_name = "gpt-4o"
            elif model == ModelType.GPT52:
                model_name = "gpt-5.2"
            else:
                model_name = "gpt-4o-mini"

        full_messages = [{"role": "system", "content": system_prompt}] + messages

        max_retries = 3
        backoff_seconds = [1, 2, 4]

        for attempt in range(max_retries + 1):
            try:
                if model == ModelType.GPT52:
                    create_kwargs = dict(
                        model=model_name,
                        messages=full_messages,
                        temperature=temperature,
                        top_p=1.0,
                        extra_body={"max_completion_tokens": max_tokens} if max_tokens else {},
                    )
                else:
                    create_kwargs = dict(
                        model=model_name,
                        messages=full_messages,
                        temperature=temperature,
                        max_tokens=max_tokens,
                        top_p=1.0,
                    )

                response = await asyncio.wait_for(
                    self.client.chat.completions.create(**create_kwargs),
                    timeout=timeout,
                )

                if firm_id:
                    await self._track_firm_tokens(firm_id, response.usage.total_tokens)

                return response.choices[0].message.content

            except RateLimitError as e:
                if attempt < max_retries:
                    await asyncio.sleep(backoff_seconds[attempt])
                else:
                    raise LLMRateLimitError(f"Rate limit exceeded: {e}")
            except InternalServerError as e:
                if attempt < max_retries:
                    await asyncio.sleep(backoff_seconds[attempt])
                else:
                    raise LLMError("Service temporarily unavailable.")
            except APIError as e:
                error_str = str(e).lower()
                if "content_filter" in error_str or "content blocked" in error_str:
                    raise LLMContentFilterError("Content filter triggered.")
                if "token" in error_str and "exceed" in error_str:
                    raise LLMTokenLimitError("Request too large.")
                if attempt < max_retries:
                    await asyncio.sleep(backoff_seconds[attempt])
                else:
                    raise LLMError(f"API error: {e}")
            except asyncio.TimeoutError:
                if attempt < max_retries:
                    await asyncio.sleep(backoff_seconds[attempt])
                else:
                    raise LLMError("Request timed out.")
            except Exception as e:
                raise LLMError(f"Failed to generate response: {e}")

        raise LLMError("Unknown error in chat completion")

    def _estimate_tokens(self, text: str) -> int:
        """
        Rough estimation of token count
        Approximation: ~4 characters = 1 token
        """
        return len(text) // 4
    
    async def _check_firm_token_limit(self, firm_id: str, requested_tokens: int):
        """Check if firm is within daily token limit"""
        today = datetime.utcnow().date().isoformat()
        key = f"{firm_id}:{today}"
        
        if key not in self.firm_daily_tokens:
            self.firm_daily_tokens[key] = {
                "used": 0,
                "date": today,
            }
        
        used = self.firm_daily_tokens[key]["used"]
        total_would_be = used + requested_tokens
        
        if total_would_be > self.FIRM_DAILY_TOKEN_LIMIT:
            remaining = self.FIRM_DAILY_TOKEN_LIMIT - used
            logger.warning(
                f"Firm {firm_id} would exceed daily token limit: "
                f"{total_would_be:,} tokens (limit: {self.FIRM_DAILY_TOKEN_LIMIT:,}). "
                f"Remaining today: {remaining:,}"
            )
            # For Phase 1, log and warn but allow (GAP-003 to implement hard limit later)
    
    async def _track_firm_tokens(self, firm_id: str, tokens: int):
        """Track actual tokens used by firm"""
        today = datetime.utcnow().date().isoformat()
        key = f"{firm_id}:{today}"
        
        if key not in self.firm_daily_tokens:
            self.firm_daily_tokens[key] = {
                "used": 0,
                "date": today,
            }
        
        self.firm_daily_tokens[key]["used"] += tokens
        used = self.firm_daily_tokens[key]["used"]
        
        if used % 50_000 == 0:  # Log every 50K tokens
            logger.info(f"Firm {firm_id} has used {used:,} tokens today")


# Singleton instance
_llm_service: Optional[LLMService] = None


def get_llm_service() -> LLMService:
    """Get or create LLM service singleton"""
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService()
    return _llm_service
