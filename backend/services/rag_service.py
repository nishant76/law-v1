import asyncio
import re
from typing import Any, Dict, List, Optional

import httpx

from backend.services.llm_service import get_llm_service
from backend.core.config import settings
from backend.core.logger import get_logger

try:
    import tiktoken
except ImportError:  # pragma: no cover
    tiktoken = None

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Paragraph splitting helpers
# ---------------------------------------------------------------------------
# Patterns that signal paragraph / section breaks in Indian court documents
_PARA_BREAK = re.compile(r"\n{2,}")
_SECTION_NUM = re.compile(r"^\s*(\d+\.|para\s*\d+|[IVXLC]+\.)\s+", re.IGNORECASE)
_PAGE_MARKER = re.compile(r"--- ?[Pp]age (\d+) ?---")


class RAGService:
    """RAG pipeline: chunking, embedding, indexing, retrieval."""

    CHUNK_SIZE_TOKENS = 500
    OVERLAP_TOKENS = 50
    EMBED_BATCH_SIZE = 100
    SEARCH_API_VERSION = "2021-04-30-Preview"
    VECTOR_FIELD_NAME = "embedding"
    SEARCH_TIMEOUT = 30
    MAX_DELETE_BATCH = 1000

    def __init__(self):
        self.llm_service = get_llm_service()
        self.search_endpoint = settings.AZURE_SEARCH_ENDPOINT.rstrip("/")
        self.search_key = settings.AZURE_SEARCH_KEY

    def _ensure_configured(self):
        if not self.search_endpoint or not self.search_key:
            raise RuntimeError(
                "Azure Search is not configured. Set AZURE_SEARCH_ENDPOINT and AZURE_SEARCH_KEY."
            )

    def _validate_firm_id(self, firm_id: str) -> str:
        if not re.fullmatch(r"[0-9a-fA-F\-]+", firm_id):
            raise ValueError("Invalid firm_id format")
        return firm_id

    def _get_index_name(self, firm_id: str) -> str:
        firm_id = self._validate_firm_id(firm_id)
        return f"superadvocate-law-{firm_id}"

    def _get_headers(self) -> Dict[str, str]:
        return {
            "api-key": self.search_key,
            "Content-Type": "application/json",
        }

    async def _http_client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(timeout=self.SEARCH_TIMEOUT)

    def _get_tokenizer(self):
        if tiktoken is None:
            raise ImportError(
                "tiktoken is required for chunking. Install tiktoken in the Python environment."
            )

        return tiktoken.encoding_for_model("text-embedding-ada-002")

    def chunk_document(self, text: str, document_id: str, firm_id: str) -> List[Dict[str, Any]]:
        """
        Split document text into chunks using paragraph-aware strategy.

        Strategy (in priority order):
          1. Split on paragraph boundaries (double newlines, section headers).
             This keeps legal arguments and reasoning together.
          2. If a paragraph exceeds CHUNK_SIZE_TOKENS, fall back to token-window
             splitting with OVERLAP_TOKENS overlap — same as the old algorithm.
          3. Accumulate short paragraphs into a single chunk until the token
             budget is full, then start a new chunk.  Consecutive small paragraphs
             that together belong to the same argument stay together.
          4. Track page numbers from ``--- Page N ---`` markers inserted by the
             OCR worker (document_service.py).  If no markers exist, page stays 0.

        This produces chunks that are semantically coherent for Indian court
        documents — each numbered paragraph / ground stays whole rather than
        being cut mid-sentence.
        """
        tokenizer = self._get_tokenizer()

        if not text or not text.strip():
            return []

        # ── Step 1: Extract page markers and split into paragraphs ────────────
        paragraphs: List[Dict[str, Any]] = []   # {text, page}
        current_page = 1

        raw_paragraphs = _PARA_BREAK.split(text)
        for para in raw_paragraphs:
            # Check for page marker lines
            for line in para.splitlines():
                m = _PAGE_MARKER.match(line.strip())
                if m:
                    current_page = int(m.group(1))

            clean_para = para.strip()
            if not clean_para:
                continue

            # Strip the page-marker lines from the paragraph text itself
            clean_lines = [
                ln for ln in clean_para.splitlines()
                if not _PAGE_MARKER.match(ln.strip())
            ]
            clean_para = "\n".join(clean_lines).strip()
            if clean_para:
                paragraphs.append({"text": clean_para, "page": current_page})

        if not paragraphs:
            return []

        # ── Step 2: Accumulate paragraphs into chunks ─────────────────────────
        chunks: List[Dict[str, Any]] = []
        chunk_index = 0

        current_texts: List[str] = []
        current_tokens: int = 0
        current_page_num: int = paragraphs[0]["page"]
        # Keep a small trailing buffer for overlap
        overlap_buffer: str = ""

        def _flush(texts: List[str], page: int, idx: int) -> int:
            """Emit one chunk and return incremented index."""
            combined = "\n\n".join(texts).strip()
            if not combined:
                return idx
            tok_count = len(tokenizer.encode(combined))
            chunks.append({
                "chunk_index": idx,
                "text": combined,
                "token_count": tok_count,
                "page_number": page,
            })
            return idx + 1

        for para_dict in paragraphs:
            para_text = para_dict["text"]
            para_page = para_dict["page"]
            para_tokens = len(tokenizer.encode(para_text))

            if para_tokens > self.CHUNK_SIZE_TOKENS:
                # ── Paragraph too long: flush current buffer, then token-split ──
                if current_texts:
                    chunk_index = _flush(current_texts, current_page_num, chunk_index)
                    overlap_buffer = current_texts[-1] if current_texts else ""
                    current_texts = []
                    current_tokens = 0

                # Token-window split for this oversized paragraph
                token_ids = tokenizer.encode(
                    (overlap_buffer + "\n\n" + para_text).strip()
                    if overlap_buffer else para_text
                )
                start = 0
                while start < len(token_ids):
                    end = min(start + self.CHUNK_SIZE_TOKENS, len(token_ids))
                    chunk_tokens = token_ids[start:end]
                    chunk_text = tokenizer.decode(chunk_tokens).strip()
                    if chunk_text:
                        chunks.append({
                            "chunk_index": chunk_index,
                            "text": chunk_text,
                            "token_count": len(chunk_tokens),
                            "page_number": para_page,
                        })
                        chunk_index += 1
                    if end == len(token_ids):
                        break
                    start = end - self.OVERLAP_TOKENS
                    if start < 0:
                        start = 0

                # Carry the last window as overlap into the next paragraph
                if chunks:
                    last_text = chunks[-1]["text"]
                    last_ids = tokenizer.encode(last_text)
                    overlap_buffer = tokenizer.decode(
                        last_ids[-self.OVERLAP_TOKENS:]
                    )
                current_page_num = para_page
                continue

            # ── Normal paragraph: accumulate until budget full ────────────────
            if current_tokens + para_tokens > self.CHUNK_SIZE_TOKENS and current_texts:
                chunk_index = _flush(current_texts, current_page_num, chunk_index)
                # Carry last paragraph as overlap
                overlap_buffer = current_texts[-1] if current_texts else ""
                current_texts = [overlap_buffer] if overlap_buffer else []
                current_tokens = len(tokenizer.encode(overlap_buffer)) if overlap_buffer else 0

            current_texts.append(para_text)
            current_tokens += para_tokens
            current_page_num = para_page

        # Flush remainder
        if current_texts:
            _flush(current_texts, current_page_num, chunk_index)

        logger.info(
            f"chunk_document: document_id={document_id}, firm_id={firm_id}, "
            f"paragraphs={len(paragraphs)}, chunks={len(chunks)}"
        )
        return chunks

    async def embed_chunks(self, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Embed chunks in batches using text-embedding-ada-002."""
        if not chunks:
            return []

        all_embeddings: List[List[float]] = []
        for start in range(0, len(chunks), self.EMBED_BATCH_SIZE):
            batch = chunks[start : start + self.EMBED_BATCH_SIZE]
            texts = [chunk["text"] for chunk in batch]
            embeddings = await self.llm_service.embed_texts(texts)
            all_embeddings.extend(embeddings)

        if len(all_embeddings) != len(chunks):
            raise ValueError("Embedding service returned an unexpected number of vectors")

        for chunk, embedding in zip(chunks, all_embeddings):
            chunk["embedding"] = embedding

        logger.info(f"embed_chunks: embedded {len(chunks)} chunks")
        return chunks

    async def _ensure_search_index(self, index_name: str) -> None:
        """Ensure Azure AI Search index exists for the firm."""
        self._ensure_configured()
        index_url = f"{self.search_endpoint}/indexes/{index_name}?api-version={self.SEARCH_API_VERSION}"
        headers = self._get_headers()

        async with await self._http_client() as client:
            response = await client.get(index_url, headers=headers)
            if response.status_code == 200:
                return
            if response.status_code != 404:
                response.raise_for_status()

            create_url = index_url
            body = {
                "name": index_name,
                "fields": [
                    {"name": "id", "type": "Edm.String", "key": True, "filterable": False},
                    {"name": "document_id", "type": "Edm.String", "filterable": True, "searchable": False},
                    {"name": "firm_id", "type": "Edm.String", "filterable": True, "searchable": False},
                    {"name": "vertical", "type": "Edm.String", "filterable": True, "searchable": False},
                    {"name": "chunk_index", "type": "Edm.Int32", "filterable": True, "sortable": True},
                    {"name": "text", "type": "Edm.String", "searchable": True, "analyzerName": "en.microsoft"},
                    {
                        "name": self.VECTOR_FIELD_NAME,
                        "type": "Collection(Edm.Single)",
                        "searchable": False,
                        "vectorSearchDimensions": 1536,
                    },
                    {"name": "document_name", "type": "Edm.String", "filterable": True, "searchable": True},
                    {"name": "page_number", "type": "Edm.Int32", "filterable": True},
                ],
                "vectorSearch": {
                    "algorithmConfigurations": [
                        {
                            "@odata.type": "#Microsoft.Azure.Search.HnswVectorSearchAlgorithmConfiguration",
                            "name": "default",
                        }
                    ]
                },
            }

            response = await client.put(create_url, json=body, headers=headers)
            response.raise_for_status()
            logger.info(f"Created Azure Search index: {index_name}")

    async def _upload_documents(self, index_name: str, documents: List[Dict[str, Any]]) -> bool:
        self._ensure_configured()
        payload = {
            "value": [
                {"@search.action": "upload", **document} for document in documents
            ]
        }
        url = f"{self.search_endpoint}/indexes/{index_name}/docs/index?api-version={self.SEARCH_API_VERSION}"
        headers = self._get_headers()

        async with await self._http_client() as client:
            response = await client.post(url, json=payload, headers=headers)
            if response.status_code not in (200, 201):
                logger.error(
                    f"Azure Search upload failed ({response.status_code}): {response.text}"
                )
                return False

            logger.info(
                f"Uploaded {len(documents)} chunks to Azure Search index {index_name}"
            )
            return True

    async def index_chunks(
        self,
        chunks: List[Dict[str, Any]],
        document_id: str,
        firm_id: str,
        vertical: str,
        document_name: str,
    ) -> bool:
        """Index embedded chunks into Azure AI Search."""
        if not chunks:
            logger.warning("index_chunks: no chunks to index")
            return True

        if not self.search_endpoint or not self.search_key:
            logger.warning(
                "index_chunks: Azure Search not configured — skipping indexing. "
                "Set AZURE_SEARCH_ENDPOINT and AZURE_SEARCH_KEY to enable."
            )
            return True

        index_name = self._get_index_name(firm_id)
        await self._ensure_search_index(index_name)

        documents = []
        for chunk in chunks:
            documents.append(
                {
                    "id": f"{document_id}-{chunk['chunk_index']}",
                    "document_id": document_id,
                    "firm_id": firm_id,
                    "vertical": vertical,
                    "chunk_index": chunk["chunk_index"],
                    "text": chunk["text"],
                    self.VECTOR_FIELD_NAME: chunk["embedding"],
                    "document_name": document_name,
                    "page_number": chunk.get("page_number", 0),
                }
            )

        return await self._upload_documents(index_name, documents)

    async def delete_document_chunks(self, document_id: str, firm_id: str) -> bool:
        """Remove all chunks for a document from Azure AI Search."""
        index_name = self._get_index_name(firm_id)
        ids = await self._find_chunk_ids(document_id, index_name)
        if not ids:
            logger.info(
                f"delete_document_chunks: no chunks found for document {document_id}"
            )
            return True

        actions = [{"@search.action": "delete", "id": doc_id} for doc_id in ids]
        payload = {"value": actions}
        url = f"{self.search_endpoint}/indexes/{index_name}/docs/index?api-version={self.SEARCH_API_VERSION}"

        async with await self._http_client() as client:
            response = await client.post(url, json=payload, headers=self._get_headers())
            if response.status_code not in (200, 201):
                logger.error(
                    f"Azure Search delete failed ({response.status_code}): {response.text}"
                )
                return False

            logger.info(
                f"Deleted {len(ids)} chunks for document {document_id} from index {index_name}"
            )
            return True

    async def _find_chunk_ids(self, document_id: str, index_name: str) -> List[str]:
        self._ensure_configured()
        search_url = (
            f"{self.search_endpoint}/indexes/{index_name}/docs/search?api-version={self.SEARCH_API_VERSION}"
        )
        payload = {
            "search": "*",
            "filter": f"document_id eq '{document_id}'",
            "select": ["id"],
            "top": self.MAX_DELETE_BATCH,
        }

        async with await self._http_client() as client:
            response = await client.post(search_url, json=payload, headers=self._get_headers())
            response.raise_for_status()
            body = response.json()

        return [hit.get("id") for hit in body.get("value", []) if hit.get("id")]

    # Minimum cosine score to include a chunk in context.
    # Below this threshold the chunk is noise — not worth feeding to the LLM.
    MIN_SCORE_THRESHOLD = 0.25

    async def retrieve_chunks(
        self,
        query: str,
        firm_id: str,
        top_k: int = 15,
        query_vector: Optional[List[float]] = None,
        expanded_queries: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search firm's RAG index and return the top relevant chunks.

        Improvements over v1:
          • top_k default raised from 10 → 15 (more recall)
          • score filtering: drops chunks below MIN_SCORE_THRESHOLD
          • expanded_queries: runs additional searches for related terms,
            merges and deduplicates by chunk id before returning
          • Sorts final list by score descending
        """
        if not firm_id:
            return []

        if not self.search_endpoint or "<" in self.search_endpoint:
            logger.warning("Azure Search not configured — skipping own-files search")
            return []

        index_name = self._get_index_name(firm_id)
        if query_vector is None:
            query_vector = await self.llm_service.embed_query(query)

        # ── Run searches for original query + expanded terms ──────────────────
        queries_to_run: List[tuple[str, List[float]]] = [(query, query_vector)]

        if expanded_queries:
            # Embed the first 2 expansion terms (cap to stay within latency budget)
            expansion_tasks = [
                self.llm_service.embed_query(t)
                for t in expanded_queries[1:3]   # skip index 0 = original query
            ]
            try:
                extra_vectors = await asyncio.gather(*expansion_tasks, return_exceptions=True)
                for term, vec in zip(expanded_queries[1:3], extra_vectors):
                    if isinstance(vec, list):
                        queries_to_run.append((term, vec))
            except Exception as e:
                logger.warning(f"retrieve_chunks: expansion embedding failed: {e}")

        all_hits: Dict[str, Dict[str, Any]] = {}   # keyed by chunk id to dedup

        for q_text, q_vec in queries_to_run:
            search_url = (
                f"{self.search_endpoint}/indexes/{index_name}/docs/search"
                f"?api-version={self.SEARCH_API_VERSION}"
            )
            payload: Dict[str, Any] = {
                "search": q_text or "*",
                "vector": {
                    "value": q_vec,
                    "fields": self.VECTOR_FIELD_NAME,
                    "k": top_k,
                    "similarityAlgorithm": "cosine",
                },
                "filter": f"firm_id eq '{firm_id}'",
                "select": [
                    "document_id",
                    "chunk_index",
                    "text",
                    "document_name",
                    "page_number",
                ],
                "top": top_k,
            }

            try:
                async with await self._http_client() as client:
                    response = await client.post(
                        search_url, json=payload, headers=self._get_headers()
                    )
                    response.raise_for_status()
                    body = response.json()

                for hit in body.get("value", []):
                    score = hit.get("@search.score", 0.0)
                    if score < self.MIN_SCORE_THRESHOLD:
                        continue
                    chunk_id = f"{hit.get('document_id')}-{hit.get('chunk_index')}"
                    if chunk_id not in all_hits or score > all_hits[chunk_id]["score"]:
                        all_hits[chunk_id] = {
                            "document_id": hit.get("document_id"),
                            "chunk_index": hit.get("chunk_index"),
                            "text": hit.get("text", ""),
                            "document_name": hit.get("document_name"),
                            "page_number": hit.get("page_number", 0),
                            "score": score,
                        }
            except Exception as e:
                logger.warning(f"retrieve_chunks: search failed for query '{q_text[:40]}': {e}")

        # Sort by score descending, return top_k
        hits = sorted(all_hits.values(), key=lambda h: h["score"], reverse=True)[:top_k]

        logger.info(
            f"retrieve_chunks: original='{query[:50]}', expansions={len(queries_to_run)-1}, "
            f"firm_id={firm_id}, returned={len(hits)} (filtered by score≥{self.MIN_SCORE_THRESHOLD})"
        )
        return hits


_rag_service: Optional[RAGService] = None


def get_rag_service() -> RAGService:
    global _rag_service
    if _rag_service is None:
        _rag_service = RAGService()
    return _rag_service
