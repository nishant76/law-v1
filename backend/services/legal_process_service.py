"""
Legal Process Guide Service — provides procedural guidance for Punjab/Haryana courts
AI reads from curated knowledge base JSON files — never generates from memory
"""
import json
import os
import asyncio
from typing import Dict, Any, List, Optional
from pathlib import Path

from backend.services.llm_service import get_llm_service, ModelType
from backend.services.prompts.legal_process_guide import legal_process_guide_prompt
from backend.core.logger import get_logger
from backend.core.sanitiser import sanitise_document_text

logger = get_logger(__name__)


class LegalProcessService:
    """Legal process guidance service"""

    def __init__(self):
        self.llm_service = get_llm_service()
        self.knowledge_base_path = Path(__file__).parent.parent / "data" / "legal_process"
        self._knowledge_base = None

    async def get_procedure(
        self,
        matter_type: str,
        court: str,
        facts: str,
    ) -> Dict[str, Any]:
        """
        Get procedural guidance for a matter type

        Args:
            matter_type: Type of legal matter
            court: Court name
            facts: Brief facts of the case

        Returns:
            Structured procedural guidance or error message
        """
        try:
            # Load knowledge base if not already loaded
            if self._knowledge_base is None:
                self._knowledge_base = self._load_knowledge_base()

            # Find relevant knowledge base data
            kb_data = self._find_relevant_kb_data(matter_type, court)

            if not kb_data:
                return {
                    "success": False,
                    "error": f"Procedure not available for matter type '{matter_type}'",
                    "message": "This matter type is not in our curated knowledge base. Please verify the procedure directly at the court registry.",
                    "verify_at_registry": True,
                }

            # Call AI with knowledge base data
            guidance = await self._generate_guidance_with_ai(
                matter_type=matter_type,
                court=court,
                facts=facts,
                knowledge_base_data=kb_data,
            )

            return {
                "success": True,
                "matter_type": matter_type,
                "court": court,
                "guidance": guidance,
            }

        except Exception as e:
            logger.error(f"Failed to get procedure for {matter_type}: {str(e)}")
            raise

    def list_matter_types(self) -> List[str]:
        """
        List all supported matter types from knowledge base

        Returns:
            List of supported matter types
        """
        try:
            if self._knowledge_base is None:
                self._knowledge_base = self._load_knowledge_base()

            matter_types = []
            for category_data in self._knowledge_base.values():
                if isinstance(category_data, dict):
                    for matter_key in category_data.keys():
                        if matter_key != "_disclaimer":
                            matter_types.append(matter_key.replace("_", " ").title())

            return sorted(matter_types)

        except Exception as e:
            logger.error(f"Failed to list matter types: {str(e)}")
            return []

    def _load_knowledge_base(self) -> Dict[str, Any]:
        """Load all knowledge base JSON files"""
        kb = {}

        json_files = [
            "civil_suits.json",
            "criminal_matters.json",
            "property_disputes.json",
            "consumer_cases.json",
            "matrimonial.json",
        ]

        for json_file in json_files:
            file_path = self.knowledge_base_path / json_file
            if file_path.exists():
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        # Merge all categories into one dict
                        for category, matters in data.items():
                            if category != "_disclaimer":
                                kb[category] = matters
                    logger.info(f"Loaded knowledge base from {json_file}")
                except Exception as e:
                    logger.error(f"Failed to load {json_file}: {str(e)}")
            else:
                logger.warning(f"Knowledge base file not found: {file_path}")

        return kb

    def _find_relevant_kb_data(self, matter_type: str, court: str) -> Optional[Dict[str, Any]]:
        """
        Find relevant knowledge base data for matter type

        Args:
            matter_type: Matter type to search for
            court: Court (for future filtering)

        Returns:
            Knowledge base data or None
        """
        if not self._knowledge_base:
            return None

        # Normalize matter type for searching
        search_key = matter_type.lower().replace(" ", "_")

        # Search through all categories
        for category, matters in self._knowledge_base.items():
            if isinstance(matters, dict):
                for matter_key, matter_data in matters.items():
                    if matter_key == search_key:
                        return matter_data

                    # Also check matter_type field
                    if isinstance(matter_data, dict) and matter_data.get("matter_type", "").lower().replace(" ", "_") == search_key:
                        return matter_data

        return None

    async def _generate_guidance_with_ai(
        self,
        matter_type: str,
        court: str,
        facts: str,
        knowledge_base_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Generate guidance using AI with knowledge base data

        Args:
            matter_type: Matter type
            court: Court
            facts: Brief facts
            knowledge_base_data: Curated knowledge base data

        Returns:
            Structured guidance
        """
        try:
            # Format knowledge base data as JSON string
            kb_json = json.dumps(knowledge_base_data, indent=2, ensure_ascii=False)

            # Sanitise facts before prompt injection (GAP-001)
            safe_facts = sanitise_document_text(facts)

            # Call LLM with legal process guide prompt
            user_prompt = legal_process_guide_prompt.user_prompt_template.format(
                matter_type=matter_type,
                court=court,
                facts=safe_facts,
                knowledge_base_data=kb_json,
            )

            response_text = await asyncio.wait_for(
                self.llm_service.call_completion(
                    system_prompt=legal_process_guide_prompt.system_prompt,
                    user_prompt=user_prompt,
                    model=legal_process_guide_prompt.model,
                    temperature=legal_process_guide_prompt.temperature,
                    max_tokens=legal_process_guide_prompt.max_tokens,
                ),
                timeout=90.0
            )

            # Parse JSON response
            guidance = json.loads(response_text)

            logger.info(f"Generated procedural guidance for {matter_type}")
            return guidance

        except asyncio.TimeoutError:
            logger.error(f"AI request timed out after 90s for legal process guidance matter_type={matter_type}")
            raise ValueError("AI request timed out — please try again")
        except Exception as e:
            logger.error(f"Failed to generate guidance with AI: {str(e)}")
            raise


# Singleton instance
_legal_process_service: Optional[LegalProcessService] = None


def get_legal_process_service() -> LegalProcessService:
    """Get or create legal process service instance"""
    global _legal_process_service
    if _legal_process_service is None:
        _legal_process_service = LegalProcessService()
    return _legal_process_service