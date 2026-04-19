"""
Unit tests for citation verification
"""
import json
import pytest
from unittest.mock import AsyncMock, MagicMock
from backend.services.citation_verifier_service import CitationVerifierService


class TestCitationVerifier:
    """Test citation extraction and verification functionality"""

    @pytest.fixture
    def verifier_service(self):
        """Citation verifier service instance with mocked LLM service"""
        service = CitationVerifierService()
        service.llm_service = AsyncMock()
        return service

    @pytest.mark.asyncio
    async def test_extract_citations_from_text_known_formats(self, verifier_service):
        """Test extraction of citations in known Indian legal formats"""
        draft_text = """
        The petitioner relies on the judgment in State of Punjab v. Baldev Singh (2023 SCC 123)
        where the Supreme Court held that Section 138 proceedings are quasi-criminal.

        Further reference is made to Punjab & Haryana High Court decision in
        Rajesh Kumar v. State of Haryana (2022 P&H HC 456) which discusses territorial jurisdiction.

        The matter is also covered by the ruling in AIR 2021 SC 789.
        """

        # Mock LLM response
        mock_response = {
            "citations": [
                {
                    "raw_text": "2023 SCC 123",
                    "case_name": "State of Punjab v. Baldev Singh",
                    "year": 2023,
                    "reporter": "SCC",
                    "volume": None,
                    "page": "123",
                    "court": "Supreme Court"
                },
                {
                    "raw_text": "2022 P&H HC 456",
                    "case_name": "Rajesh Kumar v. State of Haryana",
                    "year": 2022,
                    "reporter": "P&H HC",
                    "volume": None,
                    "page": "456",
                    "court": "Punjab & Haryana High Court"
                },
                {
                    "raw_text": "AIR 2021 SC 789",
                    "case_name": None,
                    "year": 2021,
                    "reporter": "AIR",
                    "volume": None,
                    "page": "789",
                    "court": "Supreme Court"
                }
            ]
        }

        verifier_service.llm_service.call_completion = AsyncMock(return_value=json.dumps(mock_response))

        citations = await verifier_service.extract_citations_from_text(draft_text)

        assert len(citations) == 3
        assert citations[0]["raw_text"] == "2023 SCC 123"
        assert citations[0]["case_name"] == "State of Punjab v. Baldev Singh"
        assert citations[0]["year"] == 2023
        assert citations[0]["reporter"] == "SCC"

    def test_extract_citations_from_text_no_citations(self, verifier_service):
        """Test extraction when no citations are present"""
        draft_text = """
        The petitioner respectfully submits that the cheque was dishonoured.
        The respondent failed to make payment despite notice.
        It is prayed that appropriate relief be granted.
        """

        mock_response = {"citations": []}
        verifier_service.llm_service.call_completion = AsyncMock(return_value=str(mock_response).replace("'", '"'))

        import asyncio
        citations = asyncio.run(verifier_service.extract_citations_from_text(draft_text))

        assert len(citations) == 0

    def test_extract_citations_from_text_malformed_response(self, verifier_service):
        """Test handling of malformed LLM responses"""
        draft_text = "Some draft text with citations"

        # Malformed JSON response
        verifier_service.llm_service.call_completion = AsyncMock(return_value="invalid json")

        import asyncio
        with pytest.raises(Exception):  # Should raise JSON parsing error
            asyncio.run(verifier_service.extract_citations_from_text(draft_text))

    @pytest.mark.asyncio
    async def test_verify_citation_exact_match(self, verifier_service):
        """Test verification of citation with exact database match"""
        citation = {
            "raw_text": "2023 SCC 123",
            "case_name": "State of Punjab v. Baldev Singh",
            "year": 2023,
            "court": "Supreme Court"
        }

        # Mock database citation
        mock_db_citation = MagicMock()
        mock_db_citation.id = "uuid-123"
        mock_db_citation.case_name = "State of Punjab v. Baldev Singh"
        mock_db_citation.year = 2023
        mock_db_citation.court = "Supreme Court of India"
        mock_db_citation.citation_key = "2023 SCC 123"

        # Mock session
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_db_citation]
        mock_session.execute.return_value = mock_result

        result = await verifier_service.verify_citation(citation, "firm-123", mock_session)

        assert result["status"] == "verified"
        assert result["match_score"] >= 0.8
        assert result["matched_citation_id"] == "uuid-123"

    @pytest.mark.asyncio
    async def test_verify_citation_partial_match(self, verifier_service):
        """Test verification with partial match (unverified status)"""
        citation = {
            "raw_text": "2023 SCC 999",
            "case_name": "Some Case Name",
            "year": 2023,
            "court": "High Court"
        }

        # Mock database citation with partial match
        mock_db_citation = MagicMock()
        mock_db_citation.id = "uuid-456"
        mock_db_citation.case_name = "Different Case Name"
        mock_db_citation.year = 2023
        mock_db_citation.court = "Punjab & Haryana High Court"
        mock_db_citation.citation_key = "2023 P&H HC 999"

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_db_citation]
        mock_session.execute.return_value = mock_result

        result = await verifier_service.verify_citation(citation, "firm-123", mock_session)

        assert result["status"] == "unverified"  # Partial match
        assert result["match_score"] < 0.8

    @pytest.mark.asyncio
    async def test_verify_citation_no_match(self, verifier_service):
        """Test verification when no matching citation exists"""
        citation = {
            "raw_text": "2023 SCC 999",
            "case_name": "Non-existent Case",
            "year": 2023
        }

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []  # No matches
        mock_session.execute.return_value = mock_result

        result = await verifier_service.verify_citation(citation, "firm-123", mock_session)

        assert result["status"] == "unverified"
        assert result["match_score"] == 0.0
        assert "No matching citation found" in result["reason"]

    @pytest.mark.asyncio
    async def test_verify_citation_fabricated_missing_data(self, verifier_service):
        """Test verification of fabricated citation with missing required data"""
        citation = {
            "raw_text": "Invalid Citation",
            # Missing case_name and year
        }

        mock_session = AsyncMock()

        result = await verifier_service.verify_citation(citation, "firm-123", mock_session)

        assert result["status"] == "fabricated"
        assert result["match_score"] == 0.0
        assert "Missing case name or year" in result["reason"]

    @pytest.mark.asyncio
    async def test_verify_all_citations_mixed_results(self, verifier_service):
        """Test verification of multiple citations with mixed results"""
        draft_text = "Draft with multiple citations"

        # Mock extraction
        verifier_service.extract_citations_from_text = AsyncMock(return_value=[
            {"raw_text": "2023 SCC 123", "case_name": "Verified Case", "year": 2023},
            {"raw_text": "2023 SCC 456", "case_name": "Unverified Case", "year": 2023},
            {"raw_text": "2023 SCC 789", "case_name": "Fabricated Case", "year": 2023},
        ])

        # Mock verification results
        verifier_service.verify_citation = AsyncMock(side_effect=[
            {"status": "verified", "match_score": 0.9},
            {"status": "unverified", "match_score": 0.6},
            {"status": "fabricated", "match_score": 0.2},
        ])

        mock_session = AsyncMock()

        result = await verifier_service.verify_all_citations(draft_text, "firm-123", mock_session)

        assert len(result["citations"]) == 3
        assert result["verified_count"] == 1
        assert result["unverified_count"] == 1
        assert result["fabricated_count"] == 1
        assert result["citation_safety_score"] == pytest.approx(33.33, abs=0.01)  # 1/3 * 100

    @pytest.mark.asyncio
    async def test_verify_all_citations_no_citations(self, verifier_service):
        """Test verification when no citations are found"""
        draft_text = "Draft without any citations"

        verifier_service.extract_citations_from_text = AsyncMock(return_value=[])

        mock_session = AsyncMock()

        result = await verifier_service.verify_all_citations(draft_text, "firm-123", mock_session)

        assert len(result["citations"]) == 0
        assert result["citation_safety_score"] == 100.0  # No citations = safe
        assert result["verified_count"] == 0
        assert result["unverified_count"] == 0
        assert result["fabricated_count"] == 0

    def test_calculate_match_score_perfect_match(self, verifier_service):
        """Test match score calculation for perfect match"""
        extracted = {
            "case_name": "State of Punjab v. Baldev Singh",
            "year": 2023,
            "court": "Supreme Court",
            "reporter": "SCC"
        }

        db_citation = MagicMock()
        db_citation.case_name = "State of Punjab v. Baldev Singh"
        db_citation.year = 2023
        db_citation.court = "Supreme Court of India"
        db_citation.citation_key = "2023 SCC 123"

        score = verifier_service._calculate_match_score(extracted, db_citation)

        assert score == 1.0  # Perfect match

    def test_calculate_match_score_partial_match(self, verifier_service):
        """Test match score calculation for partial match"""
        extracted = {
            "case_name": "State of Punjab v. Baldev Singh",  # Exact name match
            "year": 2023,
            "court": "High Court",  # Different court
        }

        db_citation = MagicMock()
        db_citation.case_name = "State of Punjab v. Baldev Singh"
        db_citation.year = 2023
        db_citation.court = "Punjab & Haryana High Court"
        db_citation.citation_key = "2023 P&H HC 456"

        score = verifier_service._calculate_match_score(extracted, db_citation)

        # Should get high score: name match (0.4) + year match (0.3) + court match (0.2) = 0.9
        assert abs(score - 0.9) < 0.1

    def test_calculate_match_score_no_match(self, verifier_service):
        """Test match score calculation for no match"""
        extracted = {
            "case_name": "Completely Different Case",
            "year": 2020,  # Wrong year
            "court": "District Court",
        }

        db_citation = MagicMock()
        db_citation.case_name = "State of Punjab v. Baldev Singh"
        db_citation.year = 2023
        db_citation.court = "Supreme Court of India"
        db_citation.citation_key = "2023 SCC 123"

        score = verifier_service._calculate_match_score(extracted, db_citation)

        assert score < 0.5  # Low match score