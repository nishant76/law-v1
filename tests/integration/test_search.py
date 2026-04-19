"""
Integration tests for search functionality
"""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.law_citation import Citation
from backend.models.law_document import Document


@pytest.mark.integration
class TestSearchIntegration:
    """Integration tests for unified search functionality"""

    @pytest.mark.asyncio
    async def test_unified_search_both_sources(self, test_client: AsyncClient, firm_a_token: str, test_db: AsyncSession):
        """Test unified search querying both public judgments and own documents"""
        headers = {"Authorization": f"Bearer {firm_a_token}"}

        # Create test citation
        citation = Citation(
            citation_key="2023 SCC 123",
            case_name="State of Punjab v. Baldev Singh",
            court="Supreme Court of India",
            year=2023,
            matter_type="criminal",
            outcome="granted",
            official_source="eSCR",
            source_url="https://sci.gov.in",
            judgment_text="Test judgment text about Section 138 NI Act"
        )
        test_db.add(citation)

        # Create test document
        document = Document(
            firm_id="firm-a-id",  # Would need actual firm ID
            file_name="test_judgment.pdf",
            file_type="pdf",
            file_size_bytes=1024000,
            blob_path="test/path.pdf",
            status="indexed",
            ocr_text="Test document text about Section 138 proceedings"
        )
        test_db.add(document)

        await test_db.commit()

        search_data = {
            "query": "Section 138 NI Act",
            "scope": "both",
            "filters": {
                "outcome": "granted",
                "court": "Supreme Court"
            }
        }

        response = await test_client.post("/api/v1/search", json=search_data, headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

        results = data["data"]
        assert "public_judgments" in results
        assert "own_documents" in results

        # Should find the citation
        public_results = results["public_judgments"]
        assert len(public_results) >= 1

        # Check result structure
        result = public_results[0]
        assert "case_name" in result
        assert "court" in result
        assert "year" in result
        assert "citation" in result
        assert "source_url" in result

    @pytest.mark.asyncio
    async def test_search_filters_applied_correctly(self, test_client: AsyncClient, firm_a_token: str, test_db: AsyncSession):
        """Test that search filters are applied correctly"""
        headers = {"Authorization": f"Bearer {firm_a_token}"}

        # Create test citations with different outcomes
        citations = [
            Citation(
                citation_key="2023 SCC 123",
                case_name="Case A",
                court="Supreme Court of India",
                year=2023,
                outcome="granted",
                official_source="eSCR"
            ),
            Citation(
                citation_key="2023 SCC 456",
                case_name="Case B",
                court="Supreme Court of India",
                year=2023,
                outcome="refused",
                official_source="eSCR"
            ),
            Citation(
                citation_key="2022 P&H HC 789",
                case_name="Case C",
                court="Punjab & Haryana High Court",
                year=2022,
                outcome="granted",
                official_source="P&H HC"
            )
        ]

        for citation in citations:
            test_db.add(citation)

        await test_db.commit()

        # Search with outcome filter
        search_data = {
            "query": "case",
            "scope": "public_judgments",
            "filters": {
                "outcome": "granted"
            }
        }

        response = await test_client.post("/api/v1/search", json=search_data, headers=headers)

        assert response.status_code == 200
        data = response.json()
        results = data["data"]["public_judgments"]

        # Should only return granted cases
        for result in results:
            assert result["outcome"] == "granted"

    @pytest.mark.asyncio
    async def test_firm_isolation_search_results(self, test_client: AsyncClient, firm_a_token: str, firm_b_token: str, test_db: AsyncSession):
        """Test that firms cannot see each other's search results"""
        # Create document for Firm A
        doc_a = Document(
            firm_id="firm-a-id",  # Would need actual UUID
            file_name="firm_a_doc.pdf",
            file_type="pdf",
            file_size_bytes=1024000,
            blob_path="firm_a/doc.pdf",
            status="indexed",
            ocr_text="Confidential Firm A case information"
        )
        test_db.add(doc_a)

        # Create document for Firm B
        doc_b = Document(
            firm_id="firm-b-id",  # Would need actual UUID
            file_name="firm_b_doc.pdf",
            file_type="pdf",
            file_size_bytes=1024000,
            blob_path="firm_b/doc.pdf",
            status="indexed",
            ocr_text="Confidential Firm B case information"
        )
        test_db.add(doc_b)

        await test_db.commit()

        # Search with Firm A token
        headers_a = {"Authorization": f"Bearer {firm_a_token}"}
        search_data = {"query": "confidential", "scope": "own_documents"}

        response_a = await test_client.post("/api/v1/search", json=search_data, headers=headers_a)

        assert response_a.status_code == 200
        data_a = response_a.json()
        own_docs_a = data_a["data"]["own_documents"]

        # Should only see Firm A's documents
        for doc in own_docs_a:
            assert "Firm A" in doc.get("content", "")

        # Search with Firm B token
        headers_b = {"Authorization": f"Bearer {firm_b_token}"}
        response_b = await test_client.post("/api/v1/search", json=search_data, headers=headers_b)

        assert response_b.status_code == 200
        data_b = response_b.json()
        own_docs_b = data_b["data"]["own_documents"]

        # Should only see Firm B's documents
        for doc in own_docs_b:
            assert "Firm B" in doc.get("content", "")

        # Firm A should not see Firm B's results and vice versa
        assert len(own_docs_a) != len(own_docs_b) or own_docs_a != own_docs_b

    @pytest.mark.asyncio
    async def test_search_scope_filtering(self, test_client: AsyncClient, firm_a_token: str):
        """Test that search scope filters work correctly"""
        headers = {"Authorization": f"Bearer {firm_a_token}"}

        # Test public judgments only
        search_data = {
            "query": "Section 138",
            "scope": "public_judgments"
        }

        response = await test_client.post("/api/v1/search", json=search_data, headers=headers)

        assert response.status_code == 200
        data = response.json()
        results = data["data"]

        assert "public_judgments" in results
        assert "own_documents" not in results or len(results["own_documents"]) == 0

        # Test own documents only
        search_data["scope"] = "own_documents"

        response = await test_client.post("/api/v1/search", json=search_data, headers=headers)

        assert response.status_code == 200
        data = response.json()
        results = data["data"]

        assert "own_documents" in results
        assert "public_judgments" not in results or len(results["public_judgments"]) == 0

    @pytest.mark.asyncio
    async def test_search_pagination(self, test_client: AsyncClient, firm_a_token: str, test_db: AsyncSession):
        """Test search result pagination"""
        headers = {"Authorization": f"Bearer {firm_a_token}"}

        # Create multiple test citations
        for i in range(10):
            citation = Citation(
                citation_key=f"2023 SCC {100+i}",
                case_name=f"Test Case {i}",
                court="Supreme Court of India",
                year=2023,
                official_source="eSCR"
            )
            test_db.add(citation)

        await test_db.commit()

        search_data = {
            "query": "test",
            "scope": "public_judgments",
            "pagination": {
                "page": 1,
                "per_page": 5
            }
        }

        response = await test_client.post("/api/v1/search", json=search_data, headers=headers)

        assert response.status_code == 200
        data = response.json()
        results = data["data"]["public_judgments"]

        assert len(results) <= 5  # Should respect pagination

    @pytest.mark.asyncio
    async def test_search_query_validation(self, test_client: AsyncClient, firm_a_token: str):
        """Test search query validation"""
        headers = {"Authorization": f"Bearer {firm_a_token}"}

        # Test empty query
        search_data = {"query": "", "scope": "both"}

        response = await test_client.post("/api/v1/search", json=search_data, headers=headers)

        assert response.status_code == 422  # Validation error

        # Test query too long
        long_query = "a" * 1000
        search_data = {"query": long_query, "scope": "both"}

        response = await test_client.post("/api/v1/search", json=search_data, headers=headers)

        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_search_performance_under_load(self, test_client: AsyncClient, firm_a_token: str):
        """Test search performance under concurrent load"""
        import asyncio
        headers = {"Authorization": f"Bearer {firm_a_token}"}

        search_data = {"query": "test", "scope": "both"}

        # Make multiple concurrent search requests
        async def single_search():
            response = await test_client.post("/api/v1/search", json=search_data, headers=headers)
            return response.status_code, response.json()

        tasks = [single_search() for _ in range(10)]
        results = await asyncio.gather(*tasks)

        # All should succeed
        for status_code, data in results:
            assert status_code == 200
            assert data["success"] is True

    @pytest.mark.asyncio
    async def test_search_history_tracking(self, test_client: AsyncClient, firm_a_token: str, test_db: AsyncSession):
        """Test that searches are properly tracked in history"""
        headers = {"Authorization": f"Bearer {firm_a_token}"}

        search_data = {
            "query": "unique search term",
            "scope": "public_judgments"
        }

        response = await test_client.post("/api/v1/search", json=search_data, headers=headers)

        assert response.status_code == 200

        # Check that search was recorded
        from backend.models.law_search_history import SearchHistory

        result = await test_db.execute(
            SearchHistory.__table__.select().where(
                SearchHistory.query.contains("unique search term")
            )
        )
        search_record = result.scalar_one_or_none()

        assert search_record is not None
        assert search_record.scope == "public_judgments"