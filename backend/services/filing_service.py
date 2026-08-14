"""
Filing Service — generates strategic court filings with citation verification and quality scoring
"""
import io
import re
import json
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
from backend.services.prompts.filing_drafter import filing_drafter_prompt, filing_template_prompt
from backend.services.prompts.brief_analyzer import brief_analyzer_prompt, DIMENSIONS
from backend.services.filing_examples import get_format_example
from backend.services import jurisdiction_service, special_acts_service
from backend.core.logger import get_logger
from backend.core.sanitiser import sanitise_document_text

logger = get_logger(__name__)

_TOKEN_RE = re.compile(r"\{\{(\w+)\}\}")


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

    # ------------------------------------------------------------------
    # Fill-in-the-blanks TEMPLATE generation (new Draft-a-Filing flow)
    # ------------------------------------------------------------------

    @staticmethod
    async def extract_text(file_bytes: bytes, ext: str) -> str:
        """Extract text from an uploaded PDF/DOCX draft."""
        ft = ext.lower().lstrip(".")
        if ft == "pdf":
            from pypdf import PdfReader
            reader = PdfReader(io.BytesIO(file_bytes))
            return "\n".join((p.extract_text() or "") for p in reader.pages).strip()
        if ft == "docx":
            from docx import Document as DocxDocument
            doc = DocxDocument(io.BytesIO(file_bytes))
            return "\n".join(p.text for p in doc.paragraphs).strip()
        raise ValueError("Only PDF and DOCX files are supported.")

    @staticmethod
    def _parse_json(raw: str) -> Dict[str, Any]:
        cleaned = (raw or "").strip()
        if not cleaned:
            raise ValueError("LLM returned an empty response — check API key quota.")
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```[a-z]*\n?", "", cleaned)
            cleaned = re.sub(r"\n?```$", "", cleaned.strip()).strip()
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            m = re.search(r"\{[\s\S]*\}", cleaned)
            if m:
                return json.loads(m.group())
            raise ValueError("Could not parse the AI response as JSON.")

    @staticmethod
    def _reconcile_fields(template: str, fields: List[Dict[str, Any]]) -> List[Dict[str, str]]:
        """Ensure every {{token}} in the template has exactly one key_field, in
        order of first appearance — add missing ones, drop unused ones."""
        used = list(dict.fromkeys(_TOKEN_RE.findall(template)))  # ordered, unique
        by_key = {f.get("key"): f for f in (fields or []) if f.get("key")}
        out: List[Dict[str, str]] = []
        for key in used:
            f = by_key.get(key) or {}
            out.append({
                "key": key,
                "label": f.get("label") or key.replace("_", " ").title(),
                "example": f.get("example") or "",
                # Pre-filled value extracted from the lawyer's input (empty if not stated).
                "value": str(f.get("value") or "").strip(),
            })
        return out

    async def generate_template(
        self,
        firm_id: str,
        court: str,
        input_text: str,
        selected_citations: Optional[List[Dict[str, Any]]],
        is_existing_draft: bool = False,
    ) -> Dict[str, Any]:
        """Generate a fill-in-the-blanks template from a rough description or an
        uploaded draft. Returns title, template_markdown ({{tokens}}), key_fields."""
        safe_input = sanitise_document_text(input_text or "").strip()
        if not safe_input:
            raise ValueError("Please describe the draft or upload a document.")

        cit_lines: List[str] = []
        for c in (selected_citations or []):
            name = (c.get("case_name") or "").strip()
            cit = c.get("citation")
            if not name:
                continue
            cit_lines.append(f"{name} — {cit}" if cit else name)
        citations_text = "\n".join(f"- {c}" for c in cit_lines) if cit_lines else "No citations provided."

        source_note = (
            "The input below is an EXISTING draft. Preserve its intent and substance, but fully "
            "rewrite it into proper, well-formatted legal language and convert every case-specific "
            "detail into a placeholder token."
            if is_existing_draft else
            "Draft a new filing from the lawyer's description below."
        )

        user_prompt = filing_template_prompt.user_prompt_template.format(
            source_note=source_note,
            court=court or "NOT SPECIFIED — infer from matter",
            user_input=safe_input[:12000],
            verified_citations=citations_text,
        )

        # Append a real P&H HC format example so the LLM matches the correct structure
        format_example = get_format_example(safe_input)
        if format_example:
            user_prompt = user_prompt.rstrip() + "\n\n" + format_example
            logger.debug(f"Injected format example ({len(format_example)} chars) into filing prompt")

        # Ground the drafter on VERIFIED offence→court data (BNSS First Schedule) so
        # it never emits a section number/forum from memory. Degrade gracefully:
        # if the data file is missing the drafter still runs on the prompt's general
        # rule (never block a draft over the grounding step).
        try:
            grounding = jurisdiction_service.grounding_block(safe_input)
            if grounding:
                user_prompt = user_prompt.rstrip() + "\n\n" + grounding
                logger.debug(f"Injected jurisdiction grounding ({len(grounding)} chars)")
        except jurisdiction_service.JurisdictionDataError as exc:
            logger.warning(f"Jurisdiction grounding unavailable: {exc}")

        # Ground the drafter on VERIFIED special-act bars (NDPS s.37, PMLA s.45,
        # UAPA s.43D(5), NI s.138/142, s.12A CCA, s.80 CPC, s.69 Partnership,
        # s.14 HMA) — the landmine table in docs/drafting_correctness_audit.md.
        # jurisdiction_service covers the BNS First Schedule only; these are the
        # bars that make a filing NOT MAINTAINABLE if missed (an NDPS bail draft
        # was caught omitting s.37, the quantity, and the Special Court).
        # Same degrade-gracefully rule: never block a draft over grounding.
        try:
            bars = special_acts_service.grounding_block(safe_input)
            if bars:
                user_prompt = user_prompt.rstrip() + "\n\n" + bars
                logger.debug(
                    "Injected special-act bar grounding (%d chars, triggers=%s)",
                    len(bars), special_acts_service.detect_triggers(safe_input),
                )
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"Special-act grounding unavailable: {exc}")

        try:
            response_text = await asyncio.wait_for(
                self.llm_service.call_completion(
                    system_prompt=filing_template_prompt.system_prompt,
                    user_prompt=user_prompt,
                    model=filing_template_prompt.model,
                    temperature=filing_template_prompt.temperature,
                    max_tokens=filing_template_prompt.max_tokens,
                    firm_id=firm_id,
                    # GPT-5.2 generating up to max_tokens=6000 of structured legal text is
                    # slower than the 30s default (tuned for gpt-4o-mini) — matches the
                    # PDF Extractor's GPT-5.2 timeout pattern (pdf_extractor_service.py).
                    timeout=110,
                ),
                timeout=120.0,
            )
        except asyncio.TimeoutError:
            raise ValueError("AI request timed out — please try again")

        data = self._parse_json(response_text)
        template = (data.get("template_markdown") or "").strip()
        if not template:
            raise ValueError("Draft generation failed — no template returned.")

        key_fields = self._reconcile_fields(template, data.get("key_fields") or [])
        logger.info(f"Generated filing template firm={firm_id} fields={len(key_fields)}")
        return {
            "title": (data.get("title") or "Draft").strip(),
            "detected_document_type": (data.get("detected_document_type") or "").strip(),
            "template_markdown": template,
            "key_fields": key_fields,
            "citations_used": data.get("citations_used") or [],
            # Facts the draft needs but the brief did not supply. The statutory-bar
            # grounding routes unknowns here (e.g. seized quantity for the NDPS s.37
            # classification) rather than letting the model invent a figure, so the
            # UI must surface it — an unflagged gap is worse than a visible one.
            "missing_facts": [
                str(f) for f in (data.get("missing_facts") or []) if str(f).strip()
            ],
            "strategy_notes": data.get("strategy_notes") or "",
        }

    # ------------------------------------------------------------------
    # Pre-flight BRIEF completeness check (powers the live "Brief strength"
    # meter + clarifying questions in the drafting UI, BEFORE generation).
    # ------------------------------------------------------------------

    _DIMENSION_LABELS = dict(DIMENSIONS)

    @staticmethod
    def _score_band(score: int) -> str:
        """Human label for the completeness meter."""
        if score >= 75:
            return "Strong"
        if score >= 45:
            return "Workable"
        return "Thin"

    def _normalise_analysis(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Coerce the LLM analysis into a stable shape the frontend can render.
        Always returns all six dimensions in canonical order with a label, so a
        partial/garbled LLM response never breaks the meter."""
        try:
            score = int(round(float(data.get("completeness_score", 0))))
        except (TypeError, ValueError):
            score = 0
        score = max(0, min(100, score))

        by_key = {
            d.get("key"): d
            for d in (data.get("dimensions") or [])
            if isinstance(d, dict) and d.get("key")
        }
        dimensions: List[Dict[str, Any]] = []
        for key, label in DIMENSIONS:
            d = by_key.get(key) or {}
            dimensions.append({
                "key": key,
                "label": label,
                "present": bool(d.get("present", False)),
                "note": str(d.get("note") or "").strip(),
            })

        questions: List[Dict[str, str]] = []
        for i, q in enumerate(data.get("questions") or []):
            if not isinstance(q, dict):
                continue
            text = str(q.get("question") or "").strip()
            if not text:
                continue
            questions.append({
                "id": f"q{i + 1}",
                "question": text,
                "why": str(q.get("why") or "").strip(),
            })

        return {
            "detected_filing_type": str(data.get("detected_filing_type") or "").strip(),
            "completeness_score": score,
            "score_band": self._score_band(score),
            "dimensions": dimensions,
            "questions": questions[:4],
        }

    async def analyze_brief(
        self,
        firm_id: str,
        brief: str,
        court: str = "",
        type_hint: str = "",
    ) -> Dict[str, Any]:
        """Cheap pre-flight completeness check on the drafting brief.

        Returns the inferred filing type, a 0-100 completeness_score with band,
        the six-dimension checklist, and up to 4 clarifying questions. Called live
        (debounced) as the lawyer types — must stay fast and never raise for a
        short/empty brief (returns a neutral 'thin' shape instead)."""
        safe_brief = sanitise_document_text(brief or "").strip()
        # Too little to assess meaningfully — return an honest empty state, no LLM call.
        if len(safe_brief) < 25:
            return self._normalise_analysis({})

        user_prompt = brief_analyzer_prompt.user_prompt_template.format(
            type_hint=(type_hint or "").strip() or "(none)",
            court=(court or "").strip() or "(none)",
            brief=safe_brief[:6000],
        )

        try:
            response_text = await asyncio.wait_for(
                self.llm_service.call_completion(
                    system_prompt=brief_analyzer_prompt.system_prompt,
                    user_prompt=user_prompt,
                    model=brief_analyzer_prompt.model,
                    temperature=brief_analyzer_prompt.temperature,
                    max_tokens=brief_analyzer_prompt.max_tokens,
                    firm_id=firm_id,
                    timeout=20,
                ),
                timeout=25.0,
            )
        except asyncio.TimeoutError:
            raise ValueError("Brief check timed out — please try again")

        data = self._parse_json(response_text)
        result = self._normalise_analysis(data)
        # Never log brief content (PII / GAP-032) — counts only.
        logger.info(
            f"Analyzed brief firm={firm_id} score={result['completeness_score']} "
            f"questions={len(result['questions'])}"
        )
        return result

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
                    timeout=80,
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