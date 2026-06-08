"""
Search Service — unified semantic search over public judgments and own files
Handles hybrid search (vector + keyword) using Azure AI Search
Returns results clearly labeled by source type
"""

import asyncio
import json
import re
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
from urllib.parse import quote

from sqlalchemy import select, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession
import httpx

from backend.models.law_citation import Citation
from backend.services.llm_service import get_llm_service, ModelType
from backend.services.rag_service import get_rag_service
from backend.services.query_expander import expand_query, build_expanded_query_string
from backend.services.prompts.rag_synthesis import rag_synthesis_prompt
from backend.services.prompts.search_enrichment import search_analysis_prompt
from backend.core.config import settings
from backend.core.logger import get_logger

logger = get_logger(__name__)


class SearchResultType(str, Enum):
    """Source of search result"""
    PUBLIC_JUDGMENT = "public_judgment"
    OWN_FILE = "own_file"


class PublicJudgmentResult(Dict[str, Any]):
    """Result from public judgment search"""
    pass


class OwnFileResult(Dict[str, Any]):
    """Result from own files search"""
    pass


class SearchService:
    """
    Unified semantic search service
    
    Searches:
    1. Public judgments in law.citations (hybrid: vector + keyword)
    2. Own files in law.documents (hybrid: vector + keyword)
    
    Both via Azure AI Search
    """
    
    # Azure AI Search indexes
    PUBLIC_JUDGMENTS_INDEX = "public-judgments"
    OWN_FILES_INDEX = "own-documents"
    
    def __init__(self, session: AsyncSession):
        """
        Initialize search service
        
        Args:
            session: Database session for local queries
        """
        self.session = session
        self.llm_service = get_llm_service()
        self.rag_service = get_rag_service()
    
    async def embed_query(self, query: str) -> List[float]:
        """
        Convert search query to vector embedding
        
        Args:
            query: Search query text
            
        Returns:
            Vector embedding (1536 dimensions)
        """
        return await self.llm_service.embed_query(query)
    
    async def search_public_judgments(
        self,
        query: str,
        _query_vector: List[float],
        filters: Optional[Dict[str, Any]] = None,
        firm_id: Optional[str] = None,
        top: int = 10,
    ) -> List[PublicJudgmentResult]:
        """
        Search public judgments (law.citations) using PostgreSQL full-text search.
        Falls back to per-word ILIKE when FTS returns zero results.
        Public judgments are NOT filtered by firm_id — they belong to everyone.

        Args:
            query: Search query text
            _query_vector: Embedded query vector (unused until Azure AI Search is wired)
            filters: Optional filters (outcome, court, year_from, year_to, matter_type)
            firm_id: Used for logging only — never for filtering
            top: Max results to return
        """
        try:
            search_filters = self._build_search_filters(filters)

            # Debug: log total rows available before filtering
            count_result = await self.session.execute(
                select(func.count()).select_from(Citation).where(Citation.deleted_at.is_(None))
            )
            total = count_result.scalar_one()
            logger.info(
                f"search_public_judgments: query='{query[:80]}' "
                f"total_citations_in_db={total} firm={firm_id}"
            )

            results = await self._search_local_citations(
                query=query,
                filters=search_filters,
                top=top,
            )


            logger.info(f"search_public_judgments: returning {len(results)} results")
            return results

        except Exception as e:
            logger.error(f"Error searching public judgments: {e}", exc_info=True)
            return []
    
    async def search_own_files(
        self,
        query: str,
        query_vector: List[float],
        firm_id: str,
        top: int = 15,
        expanded_queries: Optional[List[str]] = None,
    ) -> List[OwnFileResult]:
        """
        Hybrid search over firm's indexed documents.
        Uses query expansion to catch vocabulary mismatches.

        Args:
            query: Search query text
            query_vector: Embedded query vector
            firm_id: Firm ID (required - searches only own firm's documents)
            top: Number of results to return (default 15)
            expanded_queries: Related terms from query_expander (optional)

        Returns:
            List of results with document_name, page, excerpt, score, confidence
        """
        try:
            logger.info(f"Searching own files: {query[:100]}... (firm: {firm_id})")

            chunks = await self.rag_service.retrieve_chunks(
                query=query,
                firm_id=firm_id,
                top_k=top,
                query_vector=query_vector,
                expanded_queries=expanded_queries,
            )

            results = [
                {
                    "document_name": chunk.get("document_name"),
                    "page": chunk.get("page_number", 0),
                    "excerpt": chunk.get("text", "")[:250],
                    "score": chunk.get("score", 0.0),
                    "document_id": chunk.get("document_id"),
                    "chunk_index": chunk.get("chunk_index"),
                    "result_type": SearchResultType.OWN_FILE,
                }
                for chunk in chunks
            ]

            logger.info(f"Found {len(results)} own file results")
            return results

        except Exception as e:
            logger.error(f"Error searching own files: {e}", exc_info=True)
            return []
    
    async def unified_search(
        self,
        query: str,
        filters: Optional[Dict[str, Any]] = None,
        firm_id: Optional[str] = None,
        top_per_source: int = 10,
    ) -> Dict[str, Any]:
        """
        Unified search over both sources simultaneously
        Uses asyncio.gather to run both searches in parallel
        
        Args:
            query: Search query text
            filters: Filters for public judgments
            firm_id: Firm ID
            top_per_source: Results per source (default 10)
            
        Returns:
            {
                "success": bool,
                "query": str,
                "from_your_files": [List of OwnFileResult],
                "from_public_judgments": [List of PublicJudgmentResult],
                "total_results": int,
                "duration_ms": float
            }
        """
        start_time = datetime.utcnow()

        try:
            logger.info(f"Unified search: {query[:100]}... (firm: {firm_id})")

            # Step 1: Embed query + expand to related legal terms (parallel).
            # Both are best-effort — if Azure OpenAI is unavailable we fall back:
            #   embed_query  → empty vector  (public judgment FTS still works via ILIKE)
            #   expand_query → [query] only  (static synonyms still fire inside expand_query)
            embed_result, expand_result = await asyncio.gather(
                asyncio.wait_for(self.embed_query(query), timeout=8.0),
                expand_query(query, use_llm=True),
                return_exceptions=True,
            )

            if isinstance(embed_result, list):
                query_vector = embed_result
            else:
                logger.warning(
                    f"unified_search: embed_query failed ({embed_result!r}) — "
                    "falling back to keyword-only search"
                )
                query_vector = []

            expanded_queries: List[str] = (
                expand_result if isinstance(expand_result, list) else [query]
            )

            # Use expanded query string for FTS/ILIKE (public judgments)
            expanded_query_str = build_expanded_query_string(expanded_queries)
            logger.info(
                f"unified_search: original='{query[:50]}', "
                f"vector={'yes' if query_vector else 'no (fallback)'}, "
                f"expanded={len(expanded_queries)} terms"
            )

            # Step 2: Run both searches in parallel
            own_files_task = self.search_own_files(
                query=query,
                query_vector=query_vector,
                firm_id=firm_id or "",
                top=top_per_source,
                expanded_queries=expanded_queries,
            ) if firm_id else asyncio.sleep(0)

            public_judgments_task = self.search_public_judgments(
                query=expanded_query_str or query,
                _query_vector=query_vector,
                filters=filters,
                firm_id=firm_id,
                top=top_per_source,
            )
            
            # Gather results
            results = await asyncio.gather(
                own_files_task,
                public_judgments_task,
                return_exceptions=True
            )
            
            own_file_results = results[0] if isinstance(results[0], list) else []
            public_judgment_results = results[1] if isinstance(results[1], list) else []

            # Step 3: For each public judgment, return cached enrichment or schedule background task
            for result in public_judgment_results:
                result["enrichment"] = self.enrich_search_result(result, query)

            # Step 4: Generate overall analysis when >= 3 public results (fresh per search)
            overall_analysis = await self.synthesise_search_analysis(
                query=query,
                results=public_judgment_results,
                firm_id=firm_id,
            )

            duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000

            response = {
                "success": True,
                "query": query,
                "from_your_files": own_file_results,
                "from_public_judgments": public_judgment_results,
                "overall_analysis": overall_analysis,
                "total_results": len(own_file_results) + len(public_judgment_results),
                "duration_ms": duration_ms,
            }

            logger.info(
                f"Unified search completed: {len(own_file_results)} own files, "
                f"{len(public_judgment_results)} public judgments, "
                f"analysis={'yes' if overall_analysis else 'no (<3 results)'} "
                f"in {duration_ms:.0f}ms"
            )

            return response
            
        except Exception as e:
            logger.error(f"Error in unified search: {e}", exc_info=True)
            return {
                "success": False,
                "query": query,
                "error": str(e),
                "from_your_files": [],
                "from_public_judgments": [],
            }
    
    async def synthesise_answer(
        self,
        query: str,
        chunks: List[Dict[str, Any]],
        firm_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Generate a synthesized answer from retrieved chunks using RAG.

        Fixed in v2:
          • Properly parses the structured JSON response from GPT-4o-mini
            (v1 was doing response_text[:300] and never parsing JSON — confidence
            was always 5 regardless of what the LLM returned)
          • Uses document_name key (not 'source' which never existed in chunks)
          • Uses top 10 chunks instead of 5 for better coverage
          • Includes page_number in source attribution
          • Surfaces concept_found_as and what_is_present from the new prompt
          • Adds low-confidence warning with actionable guidance

        Args:
            query:   Original search query
            chunks:  Retrieved chunks from RAG index (sorted by score desc)
            firm_id: Firm ID for token tracking

        Returns:
            {
                "answer": str,
                "answer_found": bool,
                "concept_found_as": str | None,
                "confidence": int (0-10),
                "sources": [{"document_name", "page", "excerpt"}],
                "what_is_present": str,
                "missing_information": str | None,
                "warning": str | None,
            }
        """
        try:
            logger.info(
                f"synthesise_answer: {len(chunks)} chunks, query='{query[:60]}', firm={firm_id}"
            )

            if not chunks:
                return {
                    "answer": (
                        "No relevant information found in your uploaded documents. "
                        "Try uploading the specific judgment or document you are looking for."
                    ),
                    "answer_found": False,
                    "concept_found_as": None,
                    "confidence": 0,
                    "sources": [],
                    "what_is_present": "No documents indexed yet.",
                    "missing_information": "Upload the relevant document and try again.",
                    "warning": "Upload more relevant documents to improve search quality.",
                }

            # Format chunks — use document_name (correct key), include page number
            context_lines = []
            for i, chunk in enumerate(chunks[:10], 1):   # use top 10, not 5
                doc = chunk.get("document_name") or "Unknown document"
                page = chunk.get("page_number", 0)
                text = chunk.get("text", "").strip()
                score = chunk.get("score", 0.0)
                context_lines.append(
                    f"[Excerpt {i} | {doc} | Page {page} | Score {score:.2f}]\n{text}"
                )
            context_text = "\n\n---\n\n".join(context_lines)

            user_prompt = rag_synthesis_prompt.format_user_prompt(
                query=query,
                context_chunks=context_text,
            )

            response_text = await self.llm_service.call_completion(
                system_prompt=rag_synthesis_prompt.system_prompt,
                user_prompt=user_prompt,
                model=ModelType(rag_synthesis_prompt.model.value),
                temperature=0.0,
                max_tokens=rag_synthesis_prompt.max_tokens,
                firm_id=firm_id,
            )

            # ── Parse JSON response (v1 never did this — it was broken) ────────
            parsed = self._parse_json_response(response_text)
            if not parsed:
                # LLM returned non-JSON — return the raw text as a fallback answer
                logger.warning("synthesise_answer: LLM returned non-JSON, using raw text")
                return {
                    "answer": response_text[:600].strip(),
                    "answer_found": True,
                    "concept_found_as": None,
                    "confidence": 4,
                    "sources": [],
                    "what_is_present": "See answer above.",
                    "missing_information": None,
                }

            # ── Normalise and clamp values ──────────────────────────────────────
            confidence = int(parsed.get("confidence", 5))
            confidence = max(0, min(10, confidence))

            result: Dict[str, Any] = {
                "answer": parsed.get("answer", ""),
                "answer_found": bool(parsed.get("answer_found", confidence >= 4)),
                "concept_found_as": parsed.get("concept_found_as"),
                "confidence": confidence,
                "sources": parsed.get("sources", []),
                "what_is_present": parsed.get("what_is_present", ""),
                "missing_information": parsed.get("missing_information"),
            }

            if confidence < 4:
                result["warning"] = (
                    "Low confidence — the document may not directly address this question. "
                    "Upload more relevant documents to improve results."
                )

            logger.info(
                f"synthesise_answer: confidence={confidence}, "
                f"answer_found={result['answer_found']}, "
                f"concept_found_as={result['concept_found_as']}"
            )
            return result

        except Exception as e:
            logger.error(f"synthesise_answer: error: {e}", exc_info=True)
            return {
                "answer": "Failed to generate answer. Please try again.",
                "answer_found": False,
                "concept_found_as": None,
                "confidence": 0,
                "sources": [],
                "what_is_present": "",
                "missing_information": None,
                "error": str(e),
            }
    
    # ===================
    # Private helper methods
    # ===================
    
    def _build_search_filters(self, filters: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Build filter dictionary for search"""
        if not filters:
            return {}
        
        search_filter = {}
        
        # Map outcome filter values
        if "outcome" in filters:
            outcome_map = {
                "favour_petitioner": ["allowed", "granted", "accepted"],
                "favour_respondent": ["dismissed", "rejected"],
                "bail_granted": ["bail_granted"],
                "bail_refused": ["bail_refused"],
            }
            mapped = outcome_map.get(filters["outcome"], [])
            if mapped:
                search_filter["outcome"] = mapped
        
        # Add other filters
        if "court" in filters:
            search_filter["court"] = filters["court"]
        
        if "matter_type" in filters:
            search_filter["matter_type"] = filters["matter_type"]
        
        if "year_from" in filters:
            search_filter["year_from"] = filters["year_from"]
        
        if "year_to" in filters:
            search_filter["year_to"] = filters["year_to"]
        
        return search_filter
    
    async def _search_local_citations(
        self,
        query: str,
        filters: Dict[str, Any],
        top: int = 10,
    ) -> List[PublicJudgmentResult]:
        """
        PostgreSQL full-text search over law.citations.
        Public judgments are shared across all firms — no firm_id filter applied.

        Strategy:
          1. FTS via to_tsvector / plainto_tsquery across case_name, primary_citation,
             matter_type, subject_tags, and court.
          2. If FTS returns zero rows, fall back to per-word ILIKE across the same columns
             so partial / non-English terms still match.
        """
        try:
            # Base condition — never show soft-deleted rows
            base = [Citation.deleted_at.is_(None)]

            # Optional structured filters
            if filters.get("outcome"):
                base.append(Citation.outcome.in_(filters["outcome"]))
            if filters.get("court"):
                base.append(Citation.court == filters["court"])
            if filters.get("matter_type"):
                base.append(Citation.matter_type == filters["matter_type"])
            if filters.get("year_from"):
                base.append(Citation.year >= filters["year_from"])
            if filters.get("year_to"):
                base.append(Citation.year <= filters["year_to"])

            citations: List[Citation] = []

            if query:
                # --- Pass 1: PostgreSQL full-text search ---
                search_doc = func.to_tsvector(
                    "english",
                    Citation.case_name
                    + " "
                    + func.coalesce(Citation.primary_citation, "")
                    + " "
                    + func.coalesce(Citation.matter_type, "")
                    + " "
                    + func.coalesce(Citation.subject_tags, "")
                    + " "
                    + func.coalesce(Citation.court, ""),
                )
                fts_stmt = (
                    select(Citation)
                    .where(and_(*base, search_doc.op("@@")(func.plainto_tsquery("english", query))))
                    .limit(top)
                )
                fts_rows = await self.session.execute(fts_stmt)
                citations = list(fts_rows.scalars().all())
                logger.info(f"_search_local_citations: FTS returned {len(citations)} rows for '{query[:60]}'")

                # --- Pass 2: per-word ILIKE fallback (includes expanded query terms) ---
                if not citations:
                    # Split ALL words from both original and expanded query string
                    words = list({
                        w for w in query.split() + (query.split())
                        if len(w) > 2
                    })
                    word_clauses = [
                        or_(
                            Citation.case_name.ilike(f"%{w}%"),
                            Citation.matter_type.ilike(f"%{w}%"),
                            Citation.primary_citation.ilike(f"%{w}%"),
                            Citation.subject_tags.ilike(f"%{w}%"),
                            Citation.court.ilike(f"%{w}%"),
                            Citation.judgment_text.ilike(f"%{w}%"),
                        )
                        for w in words
                    ]
                    if word_clauses:
                        like_stmt = (
                            select(Citation)
                            .where(and_(*base, or_(*word_clauses)))
                            .limit(top)
                        )
                        like_rows = await self.session.execute(like_stmt)
                        citations = list(like_rows.scalars().all())
                        logger.info(
                            f"_search_local_citations: ILIKE fallback returned {len(citations)} rows"
                        )
            else:
                # No query text — return most recent citations
                stmt = (
                    select(Citation)
                    .where(and_(*base))
                    .order_by(Citation.year.desc())
                    .limit(top)
                )
                rows = await self.session.execute(stmt)
                citations = list(rows.scalars().all())

            return [self._format_citation_result(c) for c in citations]

        except Exception as e:
            logger.error(f"Error in _search_local_citations: {e}", exc_info=True)
            return []

    def _format_citation_result(self, c: Citation) -> PublicJudgmentResult:
        return {
            "id": str(c.id),
            "case_name": c.case_name,
            "petitioner": c.petitioner,
            "respondent": c.respondent,
            "court": c.court,
            "year": c.year,
            "judgment_date": c.judgment_date.isoformat() if c.judgment_date else None,
            "citation_key": c.citation_key,
            "primary_citation": c.primary_citation,
            "summary": c.summary,
            "source_url": c.source_url,
            "official_source": c.official_source,
            "matter_type": c.matter_type,
            "outcome": c.outcome,
            "subject_tags": c.subject_tags,
            "relevance_score": 0.95,
            "result_type": SearchResultType.PUBLIC_JUDGMENT,
            "enrichment": c.enrichment,  # None if not yet enriched — Celery will fill it
        }

    def enrich_search_result(
        self,
        result: Dict[str, Any],
        query: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Return cached enrichment for a result, or schedule background enrichment.

        If enrichment is already present in the formatted result (loaded from DB),
        return it immediately. Otherwise dispatch a Celery task so the next search
        for this citation will hit the cache.

        Args:
            result: Formatted citation dict (from _format_citation_result)
            query:  The original search query (used by worker to set relevance)

        Returns:
            Enrichment dict if cached, None if background task was scheduled.
        """
        if result.get("enrichment"):
            return result["enrichment"]

        citation_id = result.get("id")
        if citation_id:
            # DEMO MODE: .delay() requires Redis — skip enrichment if Celery unavailable.
            # TODO: restore .delay() before production deployment (Redis required).
            try:
                from backend.workers.citations import enrich_citation_task
                enrich_citation_task.delay(citation_id, query)
                logger.debug(f"Scheduled background enrichment for citation {citation_id}")
            except Exception as e:
                logger.debug(f"Celery unavailable — citation enrichment skipped: {e}")

        return None

    async def synthesise_search_analysis(
        self,
        query: str,
        results: List[PublicJudgmentResult],
        firm_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Generate an overall AI analysis across all public judgment results.
        Fresh per search — never cached (it is query-specific).
        Only called when >= 3 public judgment results are returned.

        Args:
            query:   The original search query
            results: Public judgment result dicts (must have case_name + enrichment)
            firm_id: Firm ID for token tracking

        Returns:
            SearchAnalysis dict or None if fewer than 3 results.
        """
        if len(results) < 3:
            return None

        # Build the case summary fed to the prompt.
        # Each line is prefixed with [id:<uuid>] so the LLM can key relevance_per_case by ID.
        case_lines = []
        for r in results:
            enrichment = r.get("enrichment") or {}
            ratio = enrichment.get("ratio") or "ratio not yet available"
            case_id = r.get("id", "")
            case_lines.append(
                f"[id:{case_id}] {r['case_name']} ({r.get('year', '?')}): {ratio}"
            )
        cases_summary = "\n".join(case_lines)

        user_prompt = search_analysis_prompt.format_user_prompt(
            query=query,
            cases_summary=cases_summary,
        )

        try:
            response_text = await self.llm_service.call_completion(
                system_prompt=search_analysis_prompt.system_prompt,
                user_prompt=user_prompt,
                model=ModelType(search_analysis_prompt.model.value),
                temperature=0.0,
                max_tokens=search_analysis_prompt.max_tokens,
                firm_id=firm_id,
            )
            return self._parse_json_response(response_text)
        except Exception as e:
            logger.error(f"synthesise_search_analysis failed: {e}", exc_info=True)
            return None

    def _parse_json_response(self, text: str) -> Optional[Dict[str, Any]]:
        """Strip optional markdown fences then parse JSON."""
        cleaned = text.strip()
        if cleaned.startswith("```"):
            parts = cleaned.split("```")
            cleaned = parts[1].lstrip("json").strip() if len(parts) > 1 else cleaned
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as e:
            logger.error(f"_parse_json_response: JSON parse error: {e} — raw: {text[:200]}")
            return None
    
    async def _search_azure_ai_search(
        self,
        index_name: str,
        query: str,
        query_vector: List[float],
        filters: Dict[str, Any],
        top: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Search via Azure AI Search HTTP API
        In MVP, returns empty (placeholder for full implementation)
        """
        try:
            logger.debug(f"Searching Azure AI Search index: {index_name}")
            
            # TODO: Implement actual Azure AI Search HTTP call
            # POST to AZURE_SEARCH_ENDPOINT/indexes/{index_name}/docs/search?api-version=2021-04-30-Preview
            # With hybrid search: vector_search + text search
            
            # For MVP, return empty list
            return []
            
        except Exception as e:
            logger.error(f"Error searching Azure AI Search: {e}", exc_info=True)
            return []


def get_search_service(session: AsyncSession) -> SearchService:
    """Factory function to get search service instance"""
    return SearchService(session)
