"""
Citation Verifier Service — verifies citations in drafts before delivery
Checks law.citations table for matching cases, returns verification status
"""
import uuid
from typing import List, Dict, Any, Optional
from sqlalchemy import select, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models import Citation
from backend.services.llm_service import get_llm_service, ModelType
from backend.core.logger import get_logger

logger = get_logger(__name__)


class CitationVerifierService:
    """Citation verification service"""

    def __init__(self):
        self.llm_service = get_llm_service()

    async def extract_citations_from_text(self, text: str) -> List[Dict[str, Any]]:
        """
        Extract all case citations from draft text using GPT-4o-mini

        Args:
            text: Draft text to analyze

        Returns:
            List of extracted citations with metadata
        """
        try:
            # Citation extraction prompt
            system_prompt = """You are a citation extraction specialist for Indian
legal documents. Extract all case citations from legal text precisely.
Return only what is explicitly present — never infer or complete
partial citations."""

            user_prompt = f"""Extract all case citations from this
Indian legal document text.

Text:
{text}

Return JSON:
{{
  "citations": [
    {{
      "raw_text": "exact citation as written in document",
      "case_name": "party names only",
      "year": 2024,
      "reporter": "SCC/AIR/SCR/etc or null",
      "volume": "volume number or null",
      "page": "page number or null",
      "court": "court name or null"
    }}
  ]
}}"""

            response_text = await self.llm_service.call_completion(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                model=ModelType.GPT4O_MINI,
                temperature=0.0,
                max_tokens=1000,
            )

            # Parse JSON response
            import json
            result = json.loads(response_text)
            citations = result.get("citations", [])

            logger.info(f"Extracted {len(citations)} citations from draft text")
            return citations

        except Exception as e:
            logger.error(f"Failed to extract citations: {str(e)}")
            raise

    async def verify_citation(
        self,
        citation: Dict[str, Any],
        firm_id: str,
        session: AsyncSession,
    ) -> Dict[str, Any]:
        """
        Verify a single citation against law.citations table

        Args:
            citation: Citation dict from extraction
            firm_id: Firm ID (for logging)
            session: Database session

        Returns:
            Citation with verification status and match score
        """
        try:
            case_name = citation.get("case_name", "").strip()
            year = citation.get("year")
            court = citation.get("court", "").strip()
            reporter = citation.get("reporter", "").strip() if citation.get("reporter") else None
            volume = citation.get("volume")
            page = citation.get("page")

            if not case_name or not year:
                return {
                    **citation,
                    "status": "fabricated",
                    "match_score": 0.0,
                    "reason": "Missing case name or year",
                }

            # Search for matching citations
            stmt = select(Citation).where(
                and_(
                    Citation.deleted_at.is_(None),
                    Citation.case_name.ilike(f"%{case_name}%"),
                    Citation.year == year,
                )
            )

            # Add court filter if available
            if court:
                stmt = stmt.where(Citation.court.ilike(f"%{court}%"))

            # Add reporter filter if available
            if reporter:
                stmt = stmt.where(Citation.citation_key.ilike(f"%{reporter}%"))

            result = await session.execute(stmt)
            matches = result.scalars().all()

            if not matches:
                return {
                    **citation,
                    "status": "unverified",
                    "match_score": 0.0,
                    "reason": "No matching citation found in database",
                }

            # Find best match
            best_match = None
            best_score = 0.0

            for match in matches:
                score = self._calculate_match_score(citation, match)
                if score > best_score:
                    best_score = score
                    best_match = match

            if best_score >= 0.8:  # High confidence match
                status = "verified"
            elif best_score >= 0.5:  # Medium confidence
                status = "unverified"
            else:
                status = "fabricated"

            return {
                **citation,
                "status": status,
                "match_score": best_score,
                "matched_citation_id": str(best_match.id) if best_match else None,
                "reason": f"Best match score: {best_score:.2f}",
            }

        except Exception as e:
            logger.error(f"Failed to verify citation: {str(e)}")
            return {
                **citation,
                "status": "error",
                "match_score": 0.0,
                "reason": f"Verification error: {str(e)}",
            }

    def _calculate_match_score(self, extracted: Dict[str, Any], db_citation: Citation) -> float:
        """Calculate similarity score between extracted and DB citation"""
        score = 0.0
        total_weight = 0.0

        # Case name similarity (weight: 0.4)
        extracted_name = extracted.get("case_name", "").lower()
        db_name = db_citation.case_name.lower()
        if extracted_name in db_name or db_name in extracted_name:
            score += 0.4
        total_weight += 0.4

        # Year match (weight: 0.3)
        if extracted.get("year") == db_citation.year:
            score += 0.3
        total_weight += 0.3

        # Court match (weight: 0.2)
        extracted_court = extracted.get("court", "").lower()
        db_court = db_citation.court.lower()
        if extracted_court and (extracted_court in db_court or db_court in extracted_court):
            score += 0.2
        total_weight += 0.2

        # Reporter match (weight: 0.1)
        extracted_reporter = extracted.get("reporter", "").lower()
        if extracted_reporter and extracted_reporter in db_citation.citation_key.lower():
            score += 0.1
        total_weight += 0.1

        return score / total_weight if total_weight > 0 else 0.0

    async def verify_all_citations(
        self,
        draft_text: str,
        firm_id: str,
        session: AsyncSession,
    ) -> Dict[str, Any]:
        """
        Extract and verify all citations in draft text

        Args:
            draft_text: Full draft text
            firm_id: Firm ID
            session: Database session

        Returns:
            Verification results with safety score
        """
        try:
            # Extract citations
            citations = await self.extract_citations_from_text(draft_text)

            if not citations:
                return {
                    "citations": [],
                    "citation_safety_score": 100.0,  # No citations = safe
                    "verified_count": 0,
                    "unverified_count": 0,
                    "fabricated_count": 0,
                }

            # Verify each citation
            verified_citations = []
            for citation in citations:
                verified = await self.verify_citation(citation, firm_id, session)
                verified_citations.append(verified)

            # Calculate safety score
            verified_count = sum(1 for c in verified_citations if c["status"] == "verified")
            unverified_count = sum(1 for c in verified_citations if c["status"] == "unverified")
            fabricated_count = sum(1 for c in verified_citations if c["status"] == "fabricated")

            total_citations = len(verified_citations)
            safety_score = (verified_count / total_citations) * 100 if total_citations > 0 else 100.0

            logger.info(
                f"Citation verification: {verified_count} verified, "
                f"{unverified_count} unverified, {fabricated_count} fabricated. "
                f"Safety score: {safety_score:.1f}%"
            )

            return {
                "citations": verified_citations,
                "citation_safety_score": safety_score,
                "verified_count": verified_count,
                "unverified_count": unverified_count,
                "fabricated_count": fabricated_count,
            }

        except Exception as e:
            logger.error(f"Failed to verify all citations: {str(e)}")
            raise


# Singleton instance
_citation_verifier_service: Optional[CitationVerifierService] = None


def get_citation_verifier_service() -> CitationVerifierService:
    """Get or create citation verifier service instance"""
    global _citation_verifier_service
    if _citation_verifier_service is None:
        _citation_verifier_service = CitationVerifierService()
    return _citation_verifier_service