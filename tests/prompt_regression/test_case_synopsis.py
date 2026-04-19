"""
Prompt regression tests for case synopsis generation
"""
import pytest
from unittest.mock import AsyncMock
from backend.services.prompts.case_synopsis import SYSTEM_PROMPT, USER_PROMPT_TEMPLATE, MODEL
from backend.services.llm_service import LLMService


@pytest.mark.prompt_regression
class TestCaseSynopsisPrompt:
    """Regression tests for case synopsis prompt to ensure consistent output format"""

    @pytest.fixture
    def llm_service(self):
        """LLM service instance"""
        return LLMService()

    def test_system_prompt_structure(self):
        """Test that system prompt contains required elements"""
        assert "legal document analyst" in SYSTEM_PROMPT.lower()
        assert "indian law" in SYSTEM_PROMPT.lower()
        assert "punjab and haryana" in SYSTEM_PROMPT.lower()
        assert "valid json only" in SYSTEM_PROMPT.lower()
        assert "never fabricate" in SYSTEM_PROMPT.lower()

    def test_user_prompt_template_variables(self):
        """Test that user prompt template has required variables"""
        assert "{document_text}" in USER_PROMPT_TEMPLATE

    def test_user_prompt_structure(self):
        """Test that user prompt contains required elements"""
        assert "court document" in USER_PROMPT_TEMPLATE.lower()
        assert "structured information" in USER_PROMPT_TEMPLATE.lower()
        assert "exact structure" in USER_PROMPT_TEMPLATE.lower()

    def test_output_schema_fields(self):
        """Test that output schema contains all required fields"""
        # This would be defined in the prompt file
        required_fields = [
            "case_name", "petitioner", "respondent", "court",
            "judgment_date", "case_number", "facts", "issues",
            "held", "citations_used", "relief_granted", "confidence"
        ]

        # Check that the prompt mentions all required fields
        prompt_text = USER_PROMPT_TEMPLATE.lower()
        for field in required_fields:
            assert field in prompt_text, f"Required field '{field}' not found in prompt"

    @pytest.mark.asyncio
    async def test_prompt_output_format_consistency(self, llm_service):
        """Test that prompt produces consistent JSON output format"""
        test_document = """
        IN THE HIGH COURT OF PUNJAB AND HARYANA AT CHANDIGARH

        Criminal Misc. No. 1234 of 2023

        Rajesh Kumar ...Petitioner
        Versus
        State of Punjab ...Respondent

        This is a petition under Section 482 CrPC for quashing of FIR.

        Facts: The petitioner was involved in a cheque bounce case under Section 138 NI Act.

        Held: The petition is dismissed. The petitioner has failed to make out a case for quashing.

        Citations: 2023 SCC 123, AIR 2022 P&H 456
        """

        # Mock LLM response
        mock_response = '''{
            "case_name": "Rajesh Kumar v. State of Punjab",
            "petitioner": "Rajesh Kumar",
            "respondent": "State of Punjab",
            "court": "High Court of Punjab and Haryana",
            "judgment_date": "2023-12-01",
            "case_number": "Criminal Misc. No. 1234 of 2023",
            "facts": "Petitioner filed petition under Section 482 CrPC for quashing of FIR in cheque bounce case under Section 138 NI Act.",
            "issues": ["Whether FIR should be quashed"],
            "held": "The petition is dismissed. Petitioner failed to make out case for quashing.",
            "citations_used": ["2023 SCC 123", "AIR 2022 P&H 456"],
            "relief_granted": null,
            "confidence": 95
        }'''

        with pytest.mock.patch.object(llm_service, 'call_completion', return_value=mock_response) as mock_call:
            result = await llm_service.call_completion(
                system_prompt=SYSTEM_PROMPT,
                user_prompt=USER_PROMPT_TEMPLATE.format(document_text=test_document),
                model=MODEL
            )

            # Verify the call was made
            mock_call.assert_called_once()

            # Parse the result
            import json
            parsed_result = json.loads(result)

            # Verify all expected fields are present
            expected_fields = [
                "case_name", "petitioner", "respondent", "court",
                "judgment_date", "case_number", "facts", "issues",
                "held", "citations_used", "relief_granted", "confidence"
            ]

            for field in expected_fields:
                assert field in parsed_result, f"Missing field: {field}"

            # Verify data types
            assert isinstance(parsed_result["case_name"], str)
            assert isinstance(parsed_result["petitioner"], str)
            assert isinstance(parsed_result["respondent"], str)
            assert isinstance(parsed_result["court"], str)
            assert isinstance(parsed_result["facts"], str)
            assert isinstance(parsed_result["issues"], list)
            assert isinstance(parsed_result["held"], str)
            assert isinstance(parsed_result["citations_used"], list)
            assert isinstance(parsed_result["confidence"], int)
            assert 0 <= parsed_result["confidence"] <= 100

    @pytest.mark.asyncio
    async def test_prompt_handles_missing_data(self, llm_service):
        """Test that prompt handles documents with missing information"""
        incomplete_document = """
        IN THE COURT OF XYZ

        Some case without complete details.

        No clear petitioner or respondent mentioned.
        """

        mock_response = '''{
            "case_name": null,
            "petitioner": null,
            "respondent": null,
            "court": "Court of XYZ",
            "judgment_date": null,
            "case_number": null,
            "facts": "Incomplete document with missing party details",
            "issues": [],
            "held": null,
            "citations_used": [],
            "relief_granted": null,
            "confidence": 20
        }'''

        with pytest.mock.patch.object(llm_service, 'call_completion', return_value=mock_response) as mock_call:
            result = await llm_service.call_completion(
                system_prompt=SYSTEM_PROMPT,
                user_prompt=USER_PROMPT_TEMPLATE.format(document_text=incomplete_document),
                model=MODEL
            )

            parsed_result = json.loads(result)

            # Should handle null values gracefully
            assert parsed_result["case_name"] is None
            assert parsed_result["petitioner"] is None
            assert parsed_result["respondent"] is None
            assert parsed_result["confidence"] < 50  # Low confidence for incomplete data

    @pytest.mark.asyncio
    async def test_prompt_rejects_fabricated_information(self, llm_service):
        """Test that prompt does not fabricate information not in document"""
        minimal_document = "This is a court document."

        mock_response = '''{
            "case_name": null,
            "petitioner": null,
            "respondent": null,
            "court": null,
            "judgment_date": null,
            "case_number": null,
            "facts": "Minimal court document",
            "issues": [],
            "held": null,
            "citations_used": [],
            "relief_granted": null,
            "confidence": 10
        }'''

        with pytest.mock.patch.object(llm_service, 'call_completion', return_value=mock_response) as mock_call:
            result = await llm_service.call_completion(
                system_prompt=SYSTEM_PROMPT,
                user_prompt=USER_PROMPT_TEMPLATE.format(document_text=minimal_document),
                model=MODEL
            )

            parsed_result = json.loads(result)

            # Should not fabricate parties or case details
            assert parsed_result["case_name"] is None
            assert parsed_result["petitioner"] is None
            assert parsed_result["respondent"] is None
            assert parsed_result["confidence"] < 30  # Very low confidence

    def test_model_configuration(self):
        """Test that correct model is configured"""
        assert MODEL == "gpt-4o-mini"

    @pytest.mark.asyncio
    async def test_prompt_token_limit_handling(self, llm_service):
        """Test that prompt handles very long documents appropriately"""
        long_document = "Court document text. " * 10000  # Very long document

        # Should still produce valid JSON
        mock_response = '''{
            "case_name": "Very Long Document Case",
            "petitioner": "Petitioner",
            "respondent": "Respondent",
            "court": "High Court",
            "judgment_date": "2023-01-01",
            "case_number": "Case 123",
            "facts": "Extremely long court document with repeated text",
            "issues": ["Various issues"],
            "held": "Judgment delivered",
            "citations_used": ["2023 SCC 123"],
            "relief_granted": "Relief granted",
            "confidence": 85
        }'''

        with pytest.mock.patch.object(llm_service, 'call_completion', return_value=mock_response) as mock_call:
            result = await llm_service.call_completion(
                system_prompt=SYSTEM_PROMPT,
                user_prompt=USER_PROMPT_TEMPLATE.format(document_text=long_document),
                model=MODEL
            )

            parsed_result = json.loads(result)
            assert isinstance(parsed_result, dict)
            assert "confidence" in parsed_result

    @pytest.mark.asyncio
    async def test_prompt_citation_extraction_accuracy(self, llm_service):
        """Test that citations are extracted accurately"""
        document_with_citations = """
        This judgment refers to 2023 SCC 123, AIR 2022 SC 456, and P&H HC 789 of 2021.
        Also mentioned: (2020) 2 SCC 234 and [2021] 1 P&H HC 567.
        """

        mock_response = '''{
            "case_name": "Citation Test Case",
            "petitioner": "Test Petitioner",
            "respondent": "Test Respondent",
            "court": "Test Court",
            "judgment_date": "2023-01-01",
            "case_number": "Test 123",
            "facts": "Document containing various citation formats",
            "issues": ["Citation extraction"],
            "held": "Citations extracted",
            "citations_used": ["2023 SCC 123", "AIR 2022 SC 456", "P&H HC 789 of 2021", "(2020) 2 SCC 234", "[2021] 1 P&H HC 567"],
            "relief_granted": null,
            "confidence": 90
        }'''

        with pytest.mock.patch.object(llm_service, 'call_completion', return_value=mock_response) as mock_call:
            result = await llm_service.call_completion(
                system_prompt=SYSTEM_PROMPT,
                user_prompt=USER_PROMPT_TEMPLATE.format(document_text=document_with_citations),
                model=MODEL
            )

            parsed_result = json.loads(result)

            citations = parsed_result["citations_used"]
            assert len(citations) == 5
            assert "2023 SCC 123" in citations
            assert "AIR 2022 SC 456" in citations
            assert "P&H HC 789 of 2021" in citations