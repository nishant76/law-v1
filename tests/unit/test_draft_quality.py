"""
Unit tests for draft quality scoring
"""
import pytest
from backend.services.draft_quality_service import DraftQualityService


class TestDraftQuality:
    """Test draft quality scoring functionality"""

    @pytest.fixture
    def quality_service(self):
        """Draft quality service instance"""
        return DraftQualityService()

    def test_calculate_draft_quality_score_perfect_draft(self, quality_service):
        """Test scoring for a perfect draft"""
        draft = {
            "draft_sections": {
                "court_heading": "IN THE COURT OF LEARNED CIVIL JUDGE, CHANDIGARH",
                "parties_section": "Petitioner: John Doe vs Respondent: Jane Smith",
                "facts_section": "The petitioner filed a suit under Section 138 NI Act for dishonour of cheque amounting to ₹1,00,000",
                "grounds_section": "The petitioner respectfully submits that the respondent issued a cheque which was dishonoured",
                "prayer_section": "It is respectfully prayed that the court may be pleased to grant relief",
                "verification": "Verified on oath at Chandigarh",
            },
            "citations_used": ["2023 SCC 123", "2022 P&H HC 456"],
            "strategy_notes": "Strategic delay approach implemented",
            "completeness_score": 95,
        }

        citations_verified = [
            {"raw_text": "2023 SCC 123", "status": "verified"},
            {"raw_text": "2022 P&H HC 456", "status": "verified"},
        ]

        brief = {
            "facts": "Cheque dishonour case under Section 138 NI Act",
            "relief": "Compensation and interest",
        }

        result = quality_service.calculate_draft_quality_score(draft, citations_verified, brief)

        assert result["overall_score"] >= 80.0
        assert result["threshold_passed"] is True
        assert result["dimensions"]["citation_safety"]["score"] == 100.0
        assert len(result["blocking_issues"]) == 0

    def test_calculate_draft_quality_score_fabricated_citations_blocked(self, quality_service):
        """Test that drafts with fabricated citations are blocked"""
        draft = {
            "draft_sections": {
                "court_heading": "IN THE COURT OF LEARNED CIVIL JUDGE, CHANDIGARH",
                "parties_section": "Petitioner: John Doe vs Respondent: Jane Smith",
                "facts_section": "The petitioner filed a suit",
                "grounds_section": "The petitioner submits",
                "prayer_section": "It is prayed that relief be granted",
                "verification": "Verified",
            },
            "citations_used": ["2023 SCC 999"],  # Fabricated citation
        }

        citations_verified = [
            {"raw_text": "2023 SCC 999", "status": "fabricated"},
        ]

        brief = {"facts": "Test facts", "relief": "Test relief"}

        result = quality_service.calculate_draft_quality_score(draft, citations_verified, brief)

        assert result["dimensions"]["citation_safety"]["score"] == 0.0
        assert result["threshold_passed"] is False
        assert "Citation safety below 50%" in result["blocking_issues"]

    def test_calculate_draft_quality_score_missing_sections(self, quality_service):
        """Test scoring when required sections are missing"""
        draft = {
            "draft_sections": {
                "court_heading": "IN THE COURT OF LEARNED CIVIL JUDGE, CHANDIGARH",
                # Missing parties_section, facts_section, grounds_section, prayer_section, verification
            },
        }

        citations_verified = []
        brief = {"facts": "Test facts", "relief": "Test relief"}

        result = quality_service.calculate_draft_quality_score(draft, citations_verified, brief)

        assert result["dimensions"]["completeness"]["score"] < 30.0  # Only 1/6 sections present
        assert result["overall_score"] > 50.0  # But overall score can be >50 due to other factors
        assert result["threshold_passed"] is True  # Citation safety is 100%, overall >50%

    def test_calculate_draft_quality_score_unverified_citations_partial_score(self, quality_service):
        """Test scoring with unverified citations (amber warning)"""
        draft = {
            "draft_sections": {
                "court_heading": "IN THE COURT OF LEARNED CIVIL JUDGE, CHANDIGARH",
                "parties_section": "Petitioner: John Doe vs Respondent: Jane Smith",
                "facts_section": "The petitioner filed a suit",
                "grounds_section": "The petitioner submits",
                "prayer_section": "It is prayed that relief be granted",
                "verification": "Verified",
            },
            "citations_used": ["2023 SCC 123"],
        }

        citations_verified = [
            {"raw_text": "2023 SCC 123", "status": "unverified"},
        ]

        brief = {"facts": "Test facts", "relief": "Test relief"}

        result = quality_service.calculate_draft_quality_score(draft, citations_verified, brief)

        assert result["dimensions"]["citation_safety"]["score"] == 50.0  # Half points for unverified
        assert result["threshold_passed"] is True  # Citation safety = 50%, overall should be >50%

    def test_calculate_draft_quality_score_mixed_citations(self, quality_service):
        """Test scoring with mix of verified and unverified citations"""
        draft = {
            "draft_sections": {
                "court_heading": "IN THE COURT OF LEARNED CIVIL JUDGE, CHANDIGARH",
                "parties_section": "Petitioner: John Doe vs Respondent: Jane Smith",
                "facts_section": "The petitioner filed a suit",
                "grounds_section": "The petitioner submits",
                "prayer_section": "It is prayed that relief be granted",
                "verification": "Verified",
            },
            "citations_used": ["2023 SCC 123", "2022 P&H HC 456"],
        }

        citations_verified = [
            {"raw_text": "2023 SCC 123", "status": "verified"},
            {"raw_text": "2022 P&H HC 456", "status": "unverified"},
        ]

        brief = {"facts": "Test facts", "relief": "Test relief"}

        result = quality_service.calculate_draft_quality_score(draft, citations_verified, brief)

        # (1.0 + 0.5) / 2 * 100 = 75.0
        assert result["dimensions"]["citation_safety"]["score"] == 75.0

    def test_calculate_draft_quality_score_brief_coverage(self, quality_service):
        """Test brief coverage scoring"""
        draft = {
            "draft_sections": {
                "court_heading": "IN THE COURT OF LEARNED CIVIL JUDGE, CHANDIGARH",
                "parties_section": "Petitioner: John Doe vs Respondent: Jane Smith",
                "facts_section": "The petitioner filed a suit under Section 138 NI Act for dishonour of cheque amounting to ₹1,00,000",
                "grounds_section": "The petitioner submits",
                "prayer_section": "It is prayed that the court may grant compensation and interest",
                "verification": "Verified",
            },
        }

        citations_verified = []
        brief = {
            "facts": "The petitioner filed a suit under Section 138 NI Act for dishonour of cheque amounting to ₹1,00,000",
            "relief": "Compensation and interest",
        }

        result = quality_service.calculate_draft_quality_score(draft, citations_verified, brief)

        # Should get high brief coverage score
        assert result["dimensions"]["brief_coverage"]["score"] > 70.0

    def test_calculate_draft_quality_score_language_formality(self, quality_service):
        """Test language formality scoring"""
        # Formal legal language
        formal_draft = {
            "draft_sections": {
                "court_heading": "IN THE COURT OF LEARNED CIVIL JUDGE, CHANDIGARH",
                "parties_section": "Petitioner: John Doe vs Respondent: Jane Smith",
                "facts_section": "The petitioner respectfully submits",
                "grounds_section": "The petitioner invokes Section 138 of the Negotiable Instruments Act",
                "prayer_section": "It is respectfully prayed",
                "verification": "Verified on oath",
            },
        }

        citations_verified = []
        brief = {"facts": "Test facts", "relief": "Test relief"}

        formal_result = quality_service.calculate_draft_quality_score(formal_draft, citations_verified, brief)

        # Informal language
        informal_draft = {
            "draft_sections": {
                "court_heading": "IN THE COURT OF LEARNED CIVIL JUDGE, CHANDIGARH",
                "parties_section": "Petitioner: John Doe vs Respondent: Jane Smith",
                "facts_section": "I filed a suit because you didn't pay me",
                "grounds_section": "You owe me money okay?",
                "prayer_section": "Give me my money please",
                "verification": "Verified",
            },
        }

        informal_result = quality_service.calculate_draft_quality_score(informal_draft, citations_verified, brief)

        # Formal should score higher than informal
        assert formal_result["dimensions"]["language"]["score"] > informal_result["dimensions"]["language"]["score"]

    def test_calculate_draft_quality_score_empty_draft(self, quality_service):
        """Test scoring for empty/incomplete draft"""
        draft = {"draft_sections": {}}
        citations_verified = []
        brief = {"facts": "Test facts", "relief": "Test relief"}

        result = quality_service.calculate_draft_quality_score(draft, citations_verified, brief)

        assert result["overall_score"] < 50.0  # Empty draft should score low
        assert result["threshold_passed"] is False
        assert len(result["blocking_issues"]) >= 1

    def test_calculate_draft_quality_score_weights_applied_correctly(self, quality_service):
        """Test that dimension weights are applied correctly"""
        draft = {
            "draft_sections": {
                "court_heading": "IN THE COURT OF LEARNED CIVIL JUDGE, CHANDIGARH",
                "parties_section": "Petitioner: John Doe vs Respondent: Jane Smith",
                "facts_section": "The petitioner filed a suit",
                "grounds_section": "The petitioner submits",
                "prayer_section": "It is prayed that relief be granted",
                "verification": "Verified",
            },
        }

        citations_verified = [{"raw_text": "2023 SCC 123", "status": "verified"}]
        brief = {"facts": "Test facts", "relief": "Test relief"}

        result = quality_service.calculate_draft_quality_score(draft, citations_verified, brief)

        # Verify weights are applied (35% citation, 25% completeness, etc.)
        expected_overall = (
            result["dimensions"]["citation_safety"]["score"] * 0.35 +
            result["dimensions"]["completeness"]["score"] * 0.25 +
            result["dimensions"]["legal_accuracy"]["score"] * 0.20 +
            result["dimensions"]["brief_coverage"]["score"] * 0.15 +
            result["dimensions"]["language"]["score"] * 0.05
        )

        assert abs(result["overall_score"] - expected_overall) < 0.1