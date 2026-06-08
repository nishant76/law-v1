"""
Filing Service — generates strategic court filings with citation verification and quality scoring
"""
import uuid
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime
from sqlalchemy import select, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models import Draft, DraftType, DraftStatus, Citation
from backend.services.llm_service import get_llm_service, ModelType
from backend.services.citation_verifier_service import get_citation_verifier_service
from backend.services.draft_quality_service import get_draft_quality_service
from backend.services.prompts.filing_drafter import filing_drafter_prompt
from backend.core.logger import get_logger
from backend.core.sanitiser import sanitise_document_text

logger = get_logger(__name__)


class FilingService:
    """Strategic filing generation service"""

    def __init__(self):
        self.llm_service = get_llm_service()
        self.citation_verifier = get_citation_verifier_service()
        self.quality_service = get_draft_quality_service()

    async def generate_filing(
        self,
        firm_id: str,
        filing_type: str,
        objective: str,
        court: str,
        client_name: str,
        facts: str,
        relief: str,
        session: AsyncSession,
        user_selected_citations: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Generate a strategic filing with citation verification and quality scoring

        Args:
            firm_id: Firm ID from JWT
            filing_type: Type of filing (suit, petition, etc.)
            objective: Filing objective (Win/Delay/Challenge/Settle/Preserve)
            court: Court name
            client_name: Client name
            facts: Case facts
            relief: Relief sought
            session: Database session

        Returns:
            Draft data with quality scores and verification status
        """
        try:
            logger.info(f"Generating {filing_type} filing for {client_name} with objective: {objective}")

            # Fetch relevant verified citations from DB
            db_citations = await self._fetch_relevant_citations(
                filing_type, objective, court, facts, session
            )

            # Merge user-selected citations (priority) with DB-fetched ones
            if user_selected_citations:
                # User-selected go first so the LLM knows to prioritise them
                verified_citations = user_selected_citations + [
                    c for c in db_citations if c not in user_selected_citations
                ]
                logger.info(
                    f"Using {len(user_selected_citations)} user-selected + "
                    f"{len(db_citations)} DB citations for {filing_type}"
                )
            else:
                verified_citations = db_citations

            # Generate draft using GPT-4o
            draft_data = await self._generate_draft_with_ai(
                filing_type=filing_type,
                objective=objective,
                court=court,
                client_name=client_name,
                facts=facts,
                relief=relief,
                verified_citations=verified_citations,
            )

            # Extract and verify citations from generated draft
            draft_text = self._combine_draft_sections(draft_data.get("draft_sections", {}))
            citation_verification = await self.citation_verifier.verify_all_citations(
                draft_text, firm_id, session
            )

            # Calculate quality score
            brief_data = {
                "facts": facts,
                "relief": relief,
                "filing_type": filing_type,
                "objective": objective,
            }

            quality_scores = self.quality_service.calculate_draft_quality_score(
                draft_data, citation_verification["citations"], brief_data
            )

            # Check if draft passes quality threshold
            if not quality_scores["threshold_passed"]:
                logger.warning(f"Draft failed quality threshold: {quality_scores['blocking_issues']}")
                return {
                    "success": False,
                    "draft": draft_data,
                    "quality_scores": quality_scores,
                    "citation_verification": citation_verification,
                    "error": "Draft failed quality threshold",
                    "blocking_issues": quality_scores["blocking_issues"],
                }

            # Store draft in database
            draft_id = await self._store_draft(
                firm_id=firm_id,
                filing_type=filing_type,
                objective=objective,
                court=court,
                client_name=client_name,
                facts=facts,
                relief=relief,
                draft_data=draft_data,
                quality_scores=quality_scores,
                citation_verification=citation_verification,
                session=session,
            )

            logger.info(f"Successfully generated filing draft {draft_id}")

            return {
                "success": True,
                "draft_id": draft_id,
                "draft": draft_data,
                "quality_scores": quality_scores,
                "citation_verification": citation_verification,
            }

        except Exception as e:
            logger.error(f"Failed to generate filing: {str(e)}")
            raise

    async def _fetch_relevant_citations(
        self,
        filing_type: str,
        objective: str,
        court: str,
        facts: str,
        session: AsyncSession,
    ) -> List[str]:
        """
        Fetch relevant verified citations for the filing

        Args:
            filing_type: Type of filing
            objective: Filing objective
            court: Court name
            facts: Case facts
            session: Database session

        Returns:
            List of citation strings
        """
        try:
            # Build search query based on filing type and objective
            search_terms = []

            # Add filing type keywords
            filing_keywords = {
                "civil suit": ["civil", "suit", "plaint"],
                "petition": ["petition", "writ"],
                "appeal": ["appeal", "revision"],
                "application": ["application", "motion"],
            }

            if filing_type.lower() in filing_keywords:
                search_terms.extend(filing_keywords[filing_type.lower()])

            # Add objective keywords
            objective_keywords = {
                "win on merits": ["merits", "substantive"],
                "delay proceedings": ["delay", "adjourn", "postpone", "cpc"],
                "challenge jurisdiction": ["jurisdiction", "competent"],
                "seek settlement": ["settlement", "compromise"],
                "preserve appeal rights": ["appeal", "limitation"],
            }

            if objective.lower() in objective_keywords:
                search_terms.extend(objective_keywords[objective.lower()])

            # Search citations database
            stmt = select(Citation).where(
                and_(
                    Citation.deleted_at.is_(None),
                    or_(
                        *[Citation.case_name.ilike(f"%{term}%") for term in search_terms],
                        *[Citation.judgment_text.ilike(f"%{term}%") for term in search_terms],
                    )
                )
            ).limit(10)  # Limit to top 10 relevant citations

            result = await session.execute(stmt)
            citations = result.scalars().all()

            # Format citations for prompt
            formatted_citations = []
            for citation in citations:
                citation_str = f"{citation.case_name} ({citation.year})"
                if citation.citation_key:
                    citation_str += f" {citation.citation_key}"
                if citation.court:
                    citation_str += f" - {citation.court}"
                formatted_citations.append(citation_str)

            logger.info(f"Fetched {len(formatted_citations)} relevant citations")
            return formatted_citations

        except Exception as e:
            logger.error(f"Failed to fetch relevant citations: {str(e)}")
            return []

    async def _generate_draft_with_ai(
        self,
        filing_type: str,
        objective: str,
        court: str,
        client_name: str,
        facts: str,
        relief: str,
        verified_citations: List[str],
    ) -> Dict[str, Any]:
        """
        Generate draft using GPT-4o with filing drafter prompt

        Args:
            filing_type: Type of filing
            objective: Filing objective
            court: Court name
            client_name: Client name
            facts: Case facts
            relief: Relief sought
            verified_citations: List of verified citations

        Returns:
            Draft data from AI
        """
        try:
            # Format citations for prompt
            citations_text = "\n".join(f"- {citation}" for citation in verified_citations)
            if not citations_text:
                citations_text = "No verified citations available"

            # Sanitise facts and relief before prompt injection (GAP-001)
            safe_facts = sanitise_document_text(facts)
            safe_relief = sanitise_document_text(relief)

            # Call LLM with filing drafter prompt
            user_prompt = filing_drafter_prompt.user_prompt_template.format(
                filing_type=filing_type,
                objective=objective,
                court=court,
                client_name=client_name,
                facts=safe_facts,
                relief=safe_relief,
                verified_citations=citations_text,
            )

            response_text = await asyncio.wait_for(
                self.llm_service.call_completion(
                    system_prompt=filing_drafter_prompt.system_prompt,
                    user_prompt=user_prompt,
                    model=filing_drafter_prompt.model,
                    temperature=filing_drafter_prompt.temperature,
                    max_tokens=filing_drafter_prompt.max_tokens,
                ),
                timeout=90.0
            )

            # Parse JSON response
            import json, re
            if not response_text or not response_text.strip():
                raise ValueError("LLM returned an empty response — check API key quota or model availability")

            # Strip markdown fences if present
            cleaned = response_text.strip()
            if cleaned.startswith("```"):
                cleaned = re.sub(r"^```[a-z]*\n?", "", cleaned)
                cleaned = re.sub(r"\n?```$", "", cleaned.strip()).strip()

            draft_data = json.loads(cleaned)
            logger.info(f"Generated draft with {len(draft_data.get('citations_used', []))} citations used")
            return draft_data

        except asyncio.TimeoutError:
            logger.error("AI request timed out after 90s for filing generation")
            raise ValueError("AI request timed out — please try again")
        except Exception as e:
            logger.error(f"Failed to generate draft with AI: {str(e)}")
            raise

    def _combine_draft_sections(self, draft_sections: Dict[str, str]) -> str:
        """Combine all draft sections into single text for citation verification"""
        sections = [
            "court_heading",
            "parties_section",
            "facts_section",
            "grounds_section",
            "prayer_section",
            "verification",
        ]

        combined = ""
        for section in sections:
            if section in draft_sections and draft_sections[section]:
                combined += draft_sections[section] + "\n\n"

        return combined.strip()

    async def _store_draft(
        self,
        firm_id: str,
        filing_type: str,
        objective: str,
        court: str,
        client_name: str,
        facts: str,
        relief: str,
        draft_data: Dict[str, Any],
        quality_scores: Dict[str, Any],
        citation_verification: Dict[str, Any],
        session: AsyncSession,
    ) -> str:
        """
        Store draft in database

        Args:
            firm_id: Firm ID
            filing_type: Type of filing
            objective: Filing objective
            court: Court name
            client_name: Client name
            facts: Case facts
            relief: Relief sought
            draft_data: AI-generated draft data
            quality_scores: Quality assessment results
            citation_verification: Citation verification results
            session: Database session

        Returns:
            Draft ID
        """
        try:
            draft_id = str(uuid.uuid4())

            # Combine draft sections into content
            content = self._combine_draft_sections(draft_data.get("draft_sections", {}))

            # Store metadata as JSON in content or separate fields
            import json
            metadata = {
                "draft_sections": draft_data.get("draft_sections", {}),
                "citations_used": draft_data.get("citations_used", []),
                "strategy_notes": draft_data.get("strategy_notes", ""),
                "completeness_score": draft_data.get("completeness_score", 0),
                "missing_facts": draft_data.get("missing_facts", []),
                "quality_scores": quality_scores,
                "citation_verification": citation_verification,
                "filing_type": filing_type,
                "objective": objective,
                "court": court,
                "client_name": client_name,
                "facts": facts,
                "relief": relief,
            }

            # Create draft record
            draft = Draft(
                id=draft_id,
                firm_id=uuid.UUID(firm_id),
                draft_type=DraftType.FILING_DRAFT,
                title=f"{filing_type} - {client_name}",
                content=content,
                status=DraftStatus.GENERATED,
                quality_score=int(quality_scores.get("overall_score", 0)),
                citation_safety_score=int(quality_scores.get("dimensions", {}).get("citation_safety", {}).get("score", 0)),
                completeness_score=draft_data.get("completeness_score", 0),
                legal_accuracy_score=int(quality_scores.get("dimensions", {}).get("legal_accuracy", {}).get("score", 0)),
                language_score=int(quality_scores.get("dimensions", {}).get("language", {}).get("score", 0)),
                filing_objective=objective.lower().replace(" ", "_"),
            )

            session.add(draft)
            await session.commit()

            logger.info(f"Stored draft {draft_id} in database")
            return draft_id

        except Exception as e:
            await session.rollback()
            logger.error(f"Failed to store draft: {str(e)}")
            raise

    async def get_draft(self, draft_id: str, firm_id: str, session: AsyncSession) -> Optional[Dict[str, Any]]:
        """
        Get draft by ID with firm ownership check

        Args:
            draft_id: Draft ID
            firm_id: Firm ID for ownership check
            session: Database session

        Returns:
            Draft data or None
        """
        try:
            stmt = select(Draft).where(
                and_(
                    Draft.id == draft_id,
                    Draft.firm_id == uuid.UUID(firm_id),
                    Draft.deleted_at.is_(None),
                )
            )

            result = await session.execute(stmt)
            draft = result.scalar_one_or_none()

            if not draft:
                return None

            # For filing drafts, we need to reconstruct the structured data
            # This is a simplified version - in production, you'd store metadata separately
            return {
                "id": str(draft.id),
                "filing_type": draft.title.split(" - ")[0] if " - " in draft.title else "Unknown",
                "objective": draft.filing_objective.replace("_", " ").title() if draft.filing_objective else "Unknown",
                "court": "Unknown",  # Would need to store in metadata
                "client_name": draft.title.split(" - ")[1] if " - " in draft.title else "Unknown",
                "facts": "Unknown",  # Would need to store in metadata
                "relief": "Unknown",  # Would need to store in metadata
                "content": draft.content,
                "quality_score": draft.quality_score,
                "citation_safety_score": draft.citation_safety_score,
                "completeness_score": draft.completeness_score,
                "legal_accuracy_score": draft.legal_accuracy_score,
                "language_score": draft.language_score,
                "status": draft.status.value,
                "created_at": draft.created_at.isoformat() if draft.created_at else None,
            }

        except Exception as e:
            logger.error(f"Failed to get draft {draft_id}: {str(e)}")
            raise

    async def regenerate_draft(
        self,
        draft_id: str,
        firm_id: str,
        session: AsyncSession,
    ) -> Dict[str, Any]:
        """
        Regenerate a draft with same inputs

        Args:
            draft_id: Existing draft ID
            firm_id: Firm ID
            session: Database session

        Returns:
            New draft data
        """
        try:
            # Get existing draft
            existing_draft = await self.get_draft(draft_id, firm_id, session)
            if not existing_draft:
                raise ValueError("Draft not found")

            # Regenerate with same inputs
            return await self.generate_filing(
                firm_id=firm_id,
                filing_type=existing_draft["filing_type"],
                objective=existing_draft["objective"],
                court=existing_draft["court"],
                client_name=existing_draft["client_name"],
                facts=existing_draft["facts"],
                relief=existing_draft["relief"],
                session=session,
            )

        except Exception as e:
            logger.error(f"Failed to regenerate draft {draft_id}: {str(e)}")
            raise


# Singleton instance
_filing_service: Optional[FilingService] = None


def get_filing_service() -> FilingService:
    """Get or create filing service instance"""
    global _filing_service
    if _filing_service is None:
        _filing_service = FilingService()
    return _filing_service