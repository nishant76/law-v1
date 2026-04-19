"""
Reply Service — business logic for Smart Reply Generator
Handles allegation extraction, legal grounds suggestion, and reply generation
"""
import uuid
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models import Document, Draft, DraftType, DraftStatus
from backend.services.llm_service import get_llm_service, ModelType
from backend.services.prompts.reply_generator import allegation_extraction_prompt, legal_grounds_prompt
from backend.core.logger import get_logger
from backend.core.sanitiser import sanitise_document_text

logger = get_logger(__name__)


class ReplyService:
    """Smart Reply Generator service"""

    def __init__(self):
        self.llm_service = get_llm_service()

    async def extract_allegations(
        self,
        document_id: str,
        firm_id: str,
        session: AsyncSession,
    ) -> Dict[str, Any]:
        """
        Extract allegations from legal notice document

        Args:
            document_id: Document ID of the legal notice
            firm_id: Firm ID
            session: Database session

        Returns:
            Extracted allegations with metadata
        """
        try:
            # Get document
            stmt = select(Document).where(
                Document.id == uuid.UUID(document_id),
                Document.firm_id == uuid.UUID(firm_id),
                Document.deleted_at.is_(None),
            )
            result = await session.execute(stmt)
            document = result.scalar_one_or_none()

            if not document:
                raise ValueError(f"Document not found: {document_id}")

            # For MVP, assume document text is available
            # In production, would load from blob storage and OCR if needed
            notice_text = "Mock legal notice text. This would contain the actual notice content extracted from the uploaded document."

            # Sanitize text
            sanitized_text = sanitise_document_text(notice_text)

            # Call LLM for allegation extraction
            system_prompt = allegation_extraction_prompt.system_prompt
            user_prompt = allegation_extraction_prompt.format_user_prompt(
                notice_text=sanitized_text
            )

            response_text = await asyncio.wait_for(
                self.llm_service.call_completion(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    model=ModelType(allegation_extraction_prompt.model.value),
                    temperature=0.0,
                    max_tokens=1000,
                    firm_id=firm_id,
                ),
                timeout=90.0
            )

            # Parse JSON response
            import json
            allegations_data = json.loads(response_text)

            logger.info(
                f"Extracted {len(allegations_data.get('allegations', []))} allegations "
                f"from document {document_id}"
            )

            return allegations_data

        except asyncio.TimeoutError:
            logger.error(f"AI request timed out after 90s for allegation extraction document={document_id}")
            raise ValueError("AI request timed out — please try again")
        except Exception as e:
            logger.error(f"Failed to extract allegations: {str(e)}")
            raise

    async def get_legal_grounds(
        self,
        allegation: str,
        matter_type: str,
        firm_id: str,
        session: AsyncSession,
    ) -> Dict[str, Any]:
        """
        Get legal grounds for denying an allegation

        Args:
            allegation: The allegation text
            matter_type: Type of matter (property, cheque, employment, etc.)
            firm_id: Firm ID
            session: Database session

        Returns:
            Suggested legal grounds with citations
        """
        try:
            # Search for verified citations (placeholder - would search law.citations)
            verified_citations = "Mock verified citations from database search"

            # Call LLM for legal grounds
            system_prompt = legal_grounds_prompt.system_prompt
            user_prompt = legal_grounds_prompt.format_user_prompt(
                allegation=allegation,
                matter_type=matter_type,
                verified_citations=verified_citations,
            )

            response_text = await asyncio.wait_for(
                self.llm_service.call_completion(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    model=ModelType(legal_grounds_prompt.model.value),
                    temperature=0.0,
                    max_tokens=800,
                    firm_id=firm_id,
                ),
                timeout=90.0
            )

            # Parse JSON response
            import json
            grounds_data = json.loads(response_text)

            logger.info(f"Generated legal grounds for allegation: {allegation[:50]}...")

            return grounds_data

        except asyncio.TimeoutError:
            logger.error("AI request timed out after 90s for legal grounds generation")
            raise ValueError("AI request timed out — please try again")
        except Exception as e:
            logger.error(f"Failed to get legal grounds: {str(e)}")
            raise

    async def generate_reply(
        self,
        document_id: str,
        firm_id: str,
        allegation_responses: List[Dict[str, Any]],
        session: AsyncSession,
    ) -> Draft:
        """
        Generate complete reply incorporating lawyer's decisions

        Args:
            document_id: Original notice document ID
            firm_id: Firm ID
            allegation_responses: List of {"point_number": int, "stance": "admit/deny/partial", "grounds": str}
            session: Database session

        Returns:
            Created Draft object
        """
        try:
            # Get document for context
            stmt = select(Document).where(
                Document.id == uuid.UUID(document_id),
                Document.firm_id == uuid.UUID(firm_id),
                Document.deleted_at.is_(None),
            )
            result = await session.execute(stmt)
            document = result.scalar_one_or_none()

            if not document:
                raise ValueError(f"Document not found: {document_id}")

            # Format allegation responses for prompt
            responses_text = "\n".join([
                f"Point {resp['point_number']}: {resp['stance']} - {resp.get('grounds', '')}"
                for resp in allegation_responses
            ])

            # Generate reply using LLM (placeholder prompt)
            system_prompt = """You are an expert Indian lawyer drafting replies to legal notices.
Generate a complete, professional reply incorporating the lawyer's decisions on each allegation.
Use formal legal language appropriate for Punjab/Haryana courts.
Include only verified citations."""

            user_prompt = f"""Generate a complete reply to this legal notice.

Original notice document: {document.file_name}
Lawyer's decisions on allegations:
{responses_text}

Generate the full reply document with proper formatting."""

            response_text = await asyncio.wait_for(
                self.llm_service.call_completion(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    model=ModelType.GPT4O_MINI,
                    temperature=0.0,
                    max_tokens=2000,
                    firm_id=firm_id,
                ),
                timeout=90.0
            )

            # Create draft record
            draft = Draft(
                firm_id=uuid.UUID(firm_id),
                matter_id=document.matter_id,
                draft_type=DraftType.REPLY,
                title=f"Reply to Legal Notice - {document.file_name}",
                content=response_text,
                status=DraftStatus.GENERATED,
                confidence_score=85,  # Placeholder
            )

            session.add(draft)
            await session.flush()
            await session.commit()

            logger.info(f"Generated reply draft: {draft.id}")
            return draft

        except asyncio.TimeoutError:
            await session.rollback()
            logger.error(f"AI request timed out after 90s for reply generation document={document_id}")
            raise ValueError("AI request timed out — please try again")
        except Exception as e:
            await session.rollback()
            logger.error(f"Failed to generate reply: {str(e)}")
            raise

    async def export_reply_docx(
        self,
        draft_id: str,
        firm_id: str,
        session: AsyncSession,
    ) -> bytes:
        """
        Export reply draft as formatted .docx

        Args:
            draft_id: Draft ID
            firm_id: Firm ID
            session: Database session

        Returns:
            DOCX file content as bytes
        """
        try:
            # Get draft
            stmt = select(Draft).where(
                Draft.id == uuid.UUID(draft_id),
                Draft.firm_id == uuid.UUID(firm_id),
                Draft.deleted_at.is_(None),
            )
            result = await session.execute(stmt)
            draft = result.scalar_one_or_none()

            if not draft:
                raise ValueError(f"Draft not found: {draft_id}")

            # Generate DOCX (placeholder - would use python-docx or similar)
            # For now, return mock DOCX content
            docx_content = b"Mock DOCX content for reply draft"

            logger.info(f"Exported DOCX for draft {draft_id}")
            return docx_content

        except Exception as e:
            logger.error(f"Failed to export DOCX: {str(e)}")
            raise


# Singleton instance
_reply_service: Optional[ReplyService] = None


def get_reply_service() -> ReplyService:
    """Get or create reply service instance"""
    global _reply_service
    if _reply_service is None:
        _reply_service = ReplyService()
    return _reply_service