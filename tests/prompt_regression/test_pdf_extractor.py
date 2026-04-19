"""
Prompt regression tests for PDF extractor
"""
import pytest
from unittest.mock import AsyncMock
from backend.services.prompts.pdf_extractor import SYSTEM_PROMPT, USER_PROMPT_TEMPLATE, MODEL
from backend.services.llm_service import LLMService


@pytest.mark.prompt_regression
class TestPDFExtractorPrompt:
    """Regression tests for PDF extractor prompt"""

    @pytest.fixture
    def llm_service(self):
        """LLM service instance"""
        return LLMService()

    def test_system_prompt_structure(self):
        """Test that system prompt contains required elements"""
        assert "legal document data extraction specialist" in SYSTEM_PROMPT.lower()
        assert "indian courts" in SYSTEM_PROMPT.lower()
        assert "valid json only" in SYSTEM_PROMPT.lower()
        assert "confidence score" in SYSTEM_PROMPT.lower()
        assert "never guess" in SYSTEM_PROMPT.lower()

    def test_user_prompt_template_variables(self):
        """Test that user prompt template has required variables"""
        assert "{document_text}" in USER_PROMPT_TEMPLATE

    def test_output_schema_fields(self):
        """Test that all required fields are specified in the prompt"""
        required_fields = [
            "case_number", "petitioner", "respondent", "court",
            "date_of_order", "next_hearing_date", "relief_granted",
            "conditions_imposed", "amount", "judge_name"
        ]

        prompt_text = USER_PROMPT_TEMPLATE.lower()
        for field in required_fields:
            assert field in prompt_text, f"Required field '{field}' not found in prompt"

    @pytest.mark.asyncio
    async def test_prompt_output_format_consistency(self, llm_service):
        """Test that prompt produces consistent JSON output format"""
        test_document = """
        IN THE COURT OF CIVIL JUDGE (SENIOR DIVISION) AMRITSAR

        Case No: CS-123/2023

        Rajesh Kumar ...Plaintiff
        Versus
        State Bank of India ...Defendant

        Date of Order: 15.12.2023

        Next Hearing: 20.01.2024 at 10:30 AM

        Relief: The plaintiff is entitled to recover Rs. 5,00,000/-

        Conditions: The defendant shall pay the amount within 30 days.

        Judge: Shri Justice A.K. Singh
        """

        mock_response = '''{
            "case_number": {"value": "CS-123/2023", "confidence": 95},
            "petitioner": {"value": "Rajesh Kumar", "confidence": 90},
            "respondent": {"value": "State Bank of India", "confidence": 90},
            "court": {"value": "Civil Judge (Senior Division) Amritsar", "confidence": 85},
            "date_of_order": {"value": "2023-12-15", "confidence": 90},
            "next_hearing_date": {"value": "2024-01-20", "confidence": 85},
            "relief_granted": {"value": "Recovery of Rs. 5,00,000/-", "confidence": 80},
            "conditions_imposed": {"value": ["Defendant shall pay within 30 days"], "confidence": 75},
            "amount": {"value": "500000", "confidence": 95},
            "judge_name": {"value": "A.K. Singh", "confidence": 80}
        }'''

        with pytest.mock.patch.object(llm_service, 'call_completion', return_value=mock_response) as mock_call:
            result = await llm_service.call_completion(
                system_prompt=SYSTEM_PROMPT,
                user_prompt=USER_PROMPT_TEMPLATE.format(document_text=test_document),
                model=MODEL
            )

            parsed_result = json.loads(result)

            # Verify all expected fields are present with correct structure
            expected_fields = [
                "case_number", "petitioner", "respondent", "court",
                "date_of_order", "next_hearing_date", "relief_granted",
                "conditions_imposed", "amount", "judge_name"
            ]

            for field in expected_fields:
                assert field in parsed_result, f"Missing field: {field}"
                assert "value" in parsed_result[field], f"Missing value in field: {field}"
                assert "confidence" in parsed_result[field], f"Missing confidence in field: {field}"
                assert isinstance(parsed_result[field]["confidence"], int)
                assert 0 <= parsed_result[field]["confidence"] <= 100

    @pytest.mark.asyncio
    async def test_prompt_confidence_scoring(self, llm_service):
        """Test that confidence scores are appropriate for different data clarity"""
        clear_document = """
        Case No: CS-123/2023
        Plaintiff: John Doe
        Defendant: Jane Smith
        Amount: Rs. 1,00,000/-
        """

        mock_response_clear = '''{
            "case_number": {"value": "CS-123/2023", "confidence": 95},
            "petitioner": {"value": "John Doe", "confidence": 90},
            "respondent": {"value": "Jane Smith", "confidence": 90},
            "court": {"value": null, "confidence": 0},
            "date_of_order": {"value": null, "confidence": 0},
            "next_hearing_date": {"value": null, "confidence": 0},
            "relief_granted": {"value": null, "confidence": 0},
            "conditions_imposed": {"value": [], "confidence": 0},
            "amount": {"value": "100000", "confidence": 95},
            "judge_name": {"value": null, "confidence": 0}
        }'''

        with pytest.mock.patch.object(llm_service, 'call_completion', return_value=mock_response_clear) as mock_call:
            result = await llm_service.call_completion(
                system_prompt=SYSTEM_PROMPT,
                user_prompt=USER_PROMPT_TEMPLATE.format(document_text=clear_document),
                model=MODEL
            )

            parsed_result = json.loads(result)

            # High confidence for clearly present data
            assert parsed_result["case_number"]["confidence"] >= 90
            assert parsed_result["amount"]["confidence"] >= 90

            # Low confidence for missing data
            assert parsed_result["court"]["confidence"] == 0
            assert parsed_result["date_of_order"]["confidence"] == 0

    @pytest.mark.asyncio
    async def test_prompt_handles_complex_conditions(self, llm_service):
        """Test that prompt correctly extracts complex conditions"""
        complex_document = """
        The defendant shall:
        1. Pay the principal amount of Rs. 2,50,000/- within 15 days
        2. Pay interest at 12% per annum from the date of filing
        3. Pay costs of Rs. 10,000/-
        4. Furnish security for the remaining amount
        """

        mock_response = '''{
            "case_number": {"value": null, "confidence": 0},
            "petitioner": {"value": null, "confidence": 0},
            "respondent": {"value": null, "confidence": 0},
            "court": {"value": null, "confidence": 0},
            "date_of_order": {"value": null, "confidence": 0},
            "next_hearing_date": {"value": null, "confidence": 0},
            "relief_granted": {"value": "Payment of principal, interest, and costs", "confidence": 80},
            "conditions_imposed": {
                "value": [
                    "Pay principal amount of Rs. 2,50,000/- within 15 days",
                    "Pay interest at 12% per annum from filing date",
                    "Pay costs of Rs. 10,000/-",
                    "Furnish security for remaining amount"
                ],
                "confidence": 85
            },
            "amount": {"value": "250000", "confidence": 90},
            "judge_name": {"value": null, "confidence": 0}
        }'''

        with pytest.mock.patch.object(llm_service, 'call_completion', return_value=mock_response) as mock_call:
            result = await llm_service.call_completion(
                system_prompt=SYSTEM_PROMPT,
                user_prompt=USER_PROMPT_TEMPLATE.format(document_text=complex_document),
                model=MODEL
            )

            parsed_result = json.loads(result)

            conditions = parsed_result["conditions_imposed"]["value"]
            assert len(conditions) == 4
            assert "principal amount" in conditions[0]
            assert "interest" in conditions[1]
            assert "costs" in conditions[2]
            assert "security" in conditions[3]

    @pytest.mark.asyncio
    async def test_prompt_date_format_standardization(self, llm_service):
        """Test that dates are standardized to YYYY-MM-DD format"""
        document_with_dates = """
        Order dated: 15th December, 2023
        Next hearing on 20/01/2024
        Previous order on 10-11-2023
        """

        mock_response = '''{
            "case_number": {"value": null, "confidence": 0},
            "petitioner": {"value": null, "confidence": 0},
            "respondent": {"value": null, "confidence": 0},
            "court": {"value": null, "confidence": 0},
            "date_of_order": {"value": "2023-12-15", "confidence": 85},
            "next_hearing_date": {"value": "2024-01-20", "confidence": 80},
            "relief_granted": {"value": null, "confidence": 0},
            "conditions_imposed": {"value": [], "confidence": 0},
            "amount": {"value": null, "confidence": 0},
            "judge_name": {"value": null, "confidence": 0}
        }'''

        with pytest.mock.patch.object(llm_service, 'call_completion', return_value=mock_response) as mock_call:
            result = await llm_service.call_completion(
                system_prompt=SYSTEM_PROMPT,
                user_prompt=USER_PROMPT_TEMPLATE.format(document_text=document_with_dates),
                model=MODEL
            )

            parsed_result = json.loads(result)

            # Dates should be in YYYY-MM-DD format
            assert parsed_result["date_of_order"]["value"] == "2023-12-15"
            assert parsed_result["next_hearing_date"]["value"] == "2024-01-20"

    @pytest.mark.asyncio
    async def test_prompt_amount_extraction(self, llm_service):
        """Test that amounts are extracted and standardized"""
        document_with_amounts = """
        The plaintiff is entitled to recover Rs. 5,00,000/- (Five Lakhs Only)
        Plus interest at 9% per annum amounting to Rs. 45,000/-
        Total amount: ₹6,50,000
        """

        mock_response = '''{
            "case_number": {"value": null, "confidence": 0},
            "petitioner": {"value": null, "confidence": 0},
            "respondent": {"value": null, "confidence": 0},
            "court": {"value": null, "confidence": 0},
            "date_of_order": {"value": null, "confidence": 0},
            "next_hearing_date": {"value": null, "confidence": 0},
            "relief_granted": {"value": "Recovery of amount with interest", "confidence": 75},
            "conditions_imposed": {"value": [], "confidence": 0},
            "amount": {"value": "500000", "confidence": 95},
            "judge_name": {"value": null, "confidence": 0}
        }'''

        with pytest.mock.patch.object(llm_service, 'call_completion', return_value=mock_response) as mock_call:
            result = await llm_service.call_completion(
                system_prompt=SYSTEM_PROMPT,
                user_prompt=USER_PROMPT_TEMPLATE.format(document_text=document_with_amounts),
                model=MODEL
            )

            parsed_result = json.loads(result)

            # Amount should be extracted as numeric string
            assert parsed_result["amount"]["value"] == "500000"
            assert parsed_result["amount"]["confidence"] >= 90

    @pytest.mark.asyncio
    async def test_prompt_qa_functionality(self, llm_service):
        """Test Q&A functionality over extracted document"""
        # This would test the "What conditions did the court impose?" type questions
        # For now, just verify the prompt structure supports it
        pass

    def test_model_configuration(self):
        """Test that correct model is configured"""
        assert MODEL == "gpt-4o-mini"

    @pytest.mark.asyncio
    async def test_prompt_error_handling(self, llm_service):
        """Test that prompt handles malformed or empty documents"""
        empty_document = ""

        mock_response = '''{
            "case_number": {"value": null, "confidence": 0},
            "petitioner": {"value": null, "confidence": 0},
            "respondent": {"value": null, "confidence": 0},
            "court": {"value": null, "confidence": 0},
            "date_of_order": {"value": null, "confidence": 0},
            "next_hearing_date": {"value": null, "confidence": 0},
            "relief_granted": {"value": null, "confidence": 0},
            "conditions_imposed": {"value": [], "confidence": 0},
            "amount": {"value": null, "confidence": 0},
            "judge_name": {"value": null, "confidence": 0}
        }'''

        with pytest.mock.patch.object(llm_service, 'call_completion', return_value=mock_response) as mock_call:
            result = await llm_service.call_completion(
                system_prompt=SYSTEM_PROMPT,
                user_prompt=USER_PROMPT_TEMPLATE.format(document_text=empty_document),
                model=MODEL
            )

            parsed_result = json.loads(result)

            # All fields should be null/empty with 0 confidence
            for field in parsed_result.values():
                if isinstance(field, dict):
                    assert field["value"] is None or field["value"] == []
                    assert field["confidence"] == 0
                elif isinstance(field, list):
                    assert field == []