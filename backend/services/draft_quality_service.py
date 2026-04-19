"""
Draft Quality Service — calculates quality scores for generated drafts
Scores across 5 dimensions: citation safety, completeness, legal accuracy, brief coverage, language
"""
import re
from typing import Dict, Any, List, Optional
from backend.core.logger import get_logger

logger = get_logger(__name__)


class DraftQualityService:
    """Draft quality assessment service"""

    def calculate_draft_quality_score(
        self,
        draft: Dict[str, Any],
        citations_verified: List[Dict[str, Any]],
        brief: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Calculate overall draft quality score across 5 dimensions

        Args:
            draft: Draft dict from filing service
            citations_verified: Citation verification results
            brief: Original brief data

        Returns:
            Quality scores per dimension and overall
        """
        try:
            # Calculate citation safety score (35% weight)
            citation_safety_score = self._calculate_citation_safety_score(citations_verified)

            # Calculate completeness score (25% weight)
            completeness_score = self._calculate_completeness_score(draft)

            # Calculate legal accuracy score (20% weight)
            legal_accuracy_score = self._calculate_legal_accuracy_score(draft, citations_verified)

            # Calculate brief coverage score (15% weight)
            brief_coverage_score = self._calculate_brief_coverage_score(draft, brief)

            # Calculate language score (5% weight)
            language_score = self._calculate_language_score(draft)

            # Calculate overall score
            overall_score = (
                citation_safety_score * 0.35 +
                completeness_score * 0.25 +
                legal_accuracy_score * 0.20 +
                brief_coverage_score * 0.15 +
                language_score * 0.05
            )

            result = {
                "overall_score": round(overall_score, 1),
                "dimensions": {
                    "citation_safety": {
                        "score": round(citation_safety_score, 1),
                        "weight": 35,
                        "description": "Citation verification and safety",
                    },
                    "completeness": {
                        "score": round(completeness_score, 1),
                        "weight": 25,
                        "description": "All required sections present",
                    },
                    "legal_accuracy": {
                        "score": round(legal_accuracy_score, 1),
                        "weight": 20,
                        "description": "Legal reasoning and citations",
                    },
                    "brief_coverage": {
                        "score": round(brief_coverage_score, 1),
                        "weight": 15,
                        "description": "Coverage of provided facts",
                    },
                    "language": {
                        "score": round(language_score, 1),
                        "weight": 5,
                        "description": "Formal legal language",
                    },
                },
                "threshold_passed": overall_score >= 50.0 and citation_safety_score >= 50.0,
                "blocking_issues": [],
            }

            # Add blocking issues
            if citation_safety_score < 50.0:
                result["blocking_issues"].append("Citation safety below 50%")

            if overall_score < 50.0:
                result["blocking_issues"].append("Overall quality below 50%")

            logger.info(f"Draft quality score: {overall_score:.1f}% (threshold: {'PASS' if result['threshold_passed'] else 'FAIL'})")

            return result

        except Exception as e:
            logger.error(f"Failed to calculate draft quality: {str(e)}")
            raise

    def _calculate_citation_safety_score(self, citations_verified: List[Dict[str, Any]]) -> float:
        """Calculate citation safety score (0-100)"""
        if not citations_verified:
            return 100.0  # No citations = safe

        verified_count = sum(1 for c in citations_verified if c.get("status") == "verified")
        unverified_count = sum(1 for c in citations_verified if c.get("status") == "unverified")
        fabricated_count = sum(1 for c in citations_verified if c.get("status") == "fabricated")

        total = len(citations_verified)

        # Verified citations get full points
        # Unverified get half points (amber warning)
        # Fabricated get zero points (red error)
        score = ((verified_count * 1.0) + (unverified_count * 0.5) + (fabricated_count * 0.0)) / total * 100

        return min(100.0, max(0.0, score))

    def _calculate_completeness_score(self, draft: Dict[str, Any]) -> float:
        """Calculate completeness score based on required sections"""
        draft_sections = draft.get("draft_sections", {})

        required_sections = [
            "court_heading",
            "parties_section",
            "facts_section",
            "grounds_section",
            "prayer_section",
            "verification",
        ]

        present_sections = 0
        for section in required_sections:
            if section in draft_sections and draft_sections[section].strip():
                present_sections += 1

        completeness = (present_sections / len(required_sections)) * 100

        # Bonus for strategy notes and completeness score
        if draft.get("strategy_notes"):
            completeness += 5
        if draft.get("completeness_score"):
            completeness += 5

        return min(100.0, completeness)

    def _calculate_legal_accuracy_score(self, draft: Dict[str, Any], citations_verified: List[Dict[str, Any]]) -> float:
        """Calculate legal accuracy score"""
        score = 50.0  # Base score

        # Citations used should match verified citations
        citations_used = draft.get("citations_used", [])
        verified_citations = [c for c in citations_verified if c.get("status") == "verified"]

        if citations_used and verified_citations:
            # Check if citations used are actually verified
            verified_raw_texts = {c.get("raw_text", "") for c in verified_citations}
            used_verified = sum(1 for citation in citations_used if citation in verified_raw_texts)

            if len(citations_used) > 0:
                citation_accuracy = (used_verified / len(citations_used)) * 100
                score += (citation_accuracy - 50) * 0.5  # Adjust towards citation accuracy

        # Check for legal terminology
        grounds_section = draft.get("draft_sections", {}).get("grounds_section", "")
        if re.search(r'\b(section|article|order|rule|act)\b', grounds_section, re.IGNORECASE):
            score += 10

        # Check for proper legal structure
        if "grounds" in grounds_section.lower() and "prayer" in draft.get("draft_sections", {}).get("prayer_section", "").lower():
            score += 10

        return min(100.0, max(0.0, score))

    def _calculate_brief_coverage_score(self, draft: Dict[str, Any], brief: Dict[str, Any]) -> float:
        """Calculate how well the draft covers the provided brief"""
        score = 50.0  # Base score

        facts_section = draft.get("draft_sections", {}).get("facts_section", "").lower()
        brief_facts = brief.get("facts", "").lower()
        brief_relief = brief.get("relief", "").lower()

        # Check if key facts from brief are mentioned
        brief_words = set(re.findall(r'\b\w+\b', brief_facts))
        facts_words = set(re.findall(r'\b\w+\b', facts_section))

        if brief_words:
            coverage = len(brief_words.intersection(facts_words)) / len(brief_words) * 100
            score += (coverage - 50) * 0.8  # Adjust towards coverage

        # Check if relief is mentioned in prayer section
        prayer_section = draft.get("draft_sections", {}).get("prayer_section", "").lower()
        relief_words = set(re.findall(r'\b\w+\b', brief_relief))
        prayer_words = set(re.findall(r'\b\w+\b', prayer_section))

        if relief_words:
            relief_coverage = len(relief_words.intersection(prayer_words)) / len(relief_words) * 100
            score += (relief_coverage - 50) * 0.2  # Smaller weight for relief

        return min(100.0, max(0.0, score))

    def _calculate_language_score(self, draft: Dict[str, Any]) -> float:
        """Calculate language quality score"""
        score = 50.0  # Base score

        # Combine all sections
        all_text = ""
        for section in draft.get("draft_sections", {}).values():
            if isinstance(section, str):
                all_text += section + " "

        if not all_text.strip():
            return 0.0

        # Check for formal legal language patterns
        formal_indicators = [
            r'\b(respectfully|prayer|grounds|facts|verification)\b',
            r'\b(honourable|court|petitioner|respondent)\b',
            r'\b(section|article|act|rule)\b',
        ]

        formal_score = 0
        for pattern in formal_indicators:
            if re.search(pattern, all_text, re.IGNORECASE):
                formal_score += 10

        score += formal_score

        # Penalize for informal language
        informal_indicators = [
            r'\b(i|me|my|you|your)\b',  # First/second person
            r'\b(okay|ok|yeah|nah)\b',  # Slang
        ]

        for pattern in informal_indicators:
            if re.search(pattern, all_text, re.IGNORECASE):
                score -= 15

        return min(100.0, max(0.0, score))


# Singleton instance
_draft_quality_service: Optional[DraftQualityService] = None


def get_draft_quality_service() -> DraftQualityService:
    """Get or create draft quality service instance"""
    global _draft_quality_service
    if _draft_quality_service is None:
        _draft_quality_service = DraftQualityService()
    return _draft_quality_service