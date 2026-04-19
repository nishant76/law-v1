"""
Integration tests for document management
"""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from unittest.mock import patch, AsyncMock

from backend.models.law_document import Document, DocumentStatus


@pytest.mark.integration
class TestDocumentsIntegration:
    """Integration tests for document upload, processing, and management"""

    @pytest.mark.asyncio
    async def test_document_upload_flow(self, test_client: AsyncClient, firm_a_token: str, test_db: AsyncSession):
        """Test complete document upload and processing flow"""
        headers = {"Authorization": f"Bearer {firm_a_token}"}

        # Mock file upload
        files = {
            "file": ("test_judgment.pdf", b"fake pdf content", "application/pdf")
        }
        data = {
            "file_name": "test_judgment.pdf",
            "file_type": "pdf"
        }

        with patch("backend.services.document_service.DocumentService.upload_document") as mock_upload:
            mock_upload.return_value = {
                "document_id": "test-doc-id",
                "status": "pending",
                "message": "Document uploaded successfully"
            }

            response = await test_client.post("/api/v1/documents/upload", files=files, data=data, headers=headers)

            assert response.status_code == 201
            data = response.json()
            assert data["success"] is True
            assert data["data"]["status"] == "pending"

    @pytest.mark.asyncio
    async def test_document_processing_background_job(self, test_client: AsyncClient, firm_a_token: str, test_db: AsyncSession):
        """Test that document processing happens asynchronously"""
        headers = {"Authorization": f"Bearer {firm_a_token}"}

        # Create a document in pending state
        document = Document(
            firm_id="firm-a-id",  # Would need actual UUID
            file_name="test.pdf",
            file_type="pdf",
            file_size_bytes=1024000,
            blob_path="test/path.pdf",
            status=DocumentStatus.PENDING
        )
        test_db.add(document)
        await test_db.commit()

        # Mock the background processing
        with patch("backend.workers.document_worker.process_document.delay") as mock_delay:
            mock_delay.return_value = AsyncMock()

            # Trigger processing (this would be done by a background job in real scenario)
            from backend.services.document_service import DocumentService
            service = DocumentService()
            await service.process_document(document.id)

            # Verify background job was queued
            mock_delay.assert_called_once_with(document.id)

    @pytest.mark.asyncio
    async def test_document_status_tracking(self, test_client: AsyncClient, firm_a_token: str, test_db: AsyncSession):
        """Test document status updates throughout processing"""
        headers = {"Authorization": f"Bearer {firm_a_token}"}

        # Create document
        document = Document(
            firm_id="firm-a-id",
            file_name="test.pdf",
            file_type="pdf",
            file_size_bytes=1024000,
            blob_path="test/path.pdf",
            status=DocumentStatus.PENDING
        )
        test_db.add(document)
        await test_db.commit()

        doc_id = document.id

        # Check initial status
        response = await test_client.get(f"/api/v1/documents/{doc_id}", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["status"] == "pending"

        # Update to processing
        document.status = DocumentStatus.PROCESSING
        await test_db.commit()

        response = await test_client.get(f"/api/v1/documents/{doc_id}", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["status"] == "processing"

        # Update to indexed
        document.status = DocumentStatus.INDEXED
        document.ocr_text = "Extracted text content"
        await test_db.commit()

        response = await test_client.get(f"/api/v1/documents/{doc_id}", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["status"] == "indexed"
        assert data["data"]["ocr_text"] == "Extracted text content"

    @pytest.mark.asyncio
    async def test_document_firm_isolation(self, test_client: AsyncClient, firm_a_token: str, firm_b_token: str, test_db: AsyncSession):
        """Test that firms cannot access each other's documents"""
        # Create document for Firm A
        doc_a = Document(
            firm_id="firm-a-id",
            file_name="firm_a_doc.pdf",
            file_type="pdf",
            file_size_bytes=1024000,
            blob_path="firm_a/doc.pdf",
            status=DocumentStatus.INDEXED
        )
        test_db.add(doc_a)

        # Create document for Firm B
        doc_b = Document(
            firm_id="firm-b-id",
            file_name="firm_b_doc.pdf",
            file_type="pdf",
            file_size_bytes=1024000,
            blob_path="firm_b/doc.pdf",
            status=DocumentStatus.INDEXED
        )
        test_db.add(doc_b)

        await test_db.commit()

        # Firm A tries to access their document
        headers_a = {"Authorization": f"Bearer {firm_a_token}"}
        response_a = await test_client.get(f"/api/v1/documents/{doc_a.id}", headers=headers_a)

        assert response_a.status_code == 200
        data_a = response_a.json()
        assert data_a["data"]["file_name"] == "firm_a_doc.pdf"

        # Firm A tries to access Firm B's document
        response_a_wrong = await test_client.get(f"/api/v1/documents/{doc_b.id}", headers=headers_a)

        assert response_a_wrong.status_code == 404  # Should not find

        # Firm B tries to access their document
        headers_b = {"Authorization": f"Bearer {firm_b_token}"}
        response_b = await test_client.get(f"/api/v1/documents/{doc_b.id}", headers=headers_b)

        assert response_b.status_code == 200
        data_b = response_b.json()
        assert data_b["data"]["file_name"] == "firm_b_doc.pdf"

    @pytest.mark.asyncio
    async def test_document_list_pagination(self, test_client: AsyncClient, firm_a_token: str, test_db: AsyncSession):
        """Test document listing with pagination"""
        headers = {"Authorization": f"Bearer {firm_a_token}"}

        # Create multiple documents
        for i in range(10):
            doc = Document(
                firm_id="firm-a-id",
                file_name=f"doc_{i}.pdf",
                file_type="pdf",
                file_size_bytes=1024000,
                blob_path=f"path/doc_{i}.pdf",
                status=DocumentStatus.INDEXED
            )
            test_db.add(doc)

        await test_db.commit()

        # Test pagination
        response = await test_client.get("/api/v1/documents?page=1&per_page=5", headers=headers)

        assert response.status_code == 200
        data = response.json()
        documents = data["data"]["documents"]

        assert len(documents) == 5
        assert data["data"]["total"] >= 10
        assert data["data"]["page"] == 1
        assert data["data"]["per_page"] == 5

    @pytest.mark.asyncio
    async def test_document_search_filtering(self, test_client: AsyncClient, firm_a_token: str, test_db: AsyncSession):
        """Test document search and filtering"""
        headers = {"Authorization": f"Bearer {firm_a_token}"}

        # Create documents with different statuses
        docs = [
            Document(
                firm_id="firm-a-id",
                file_name="indexed_doc.pdf",
                file_type="pdf",
                file_size_bytes=1024000,
                blob_path="path/indexed.pdf",
                status=DocumentStatus.INDEXED,
                ocr_text="This is indexed content"
            ),
            Document(
                firm_id="firm-a-id",
                file_name="pending_doc.pdf",
                file_type="pdf",
                file_size_bytes=1024000,
                blob_path="path/pending.pdf",
                status=DocumentStatus.PENDING
            ),
            Document(
                firm_id="firm-a-id",
                file_name="failed_doc.pdf",
                file_type="pdf",
                file_size_bytes=1024000,
                blob_path="path/failed.pdf",
                status=DocumentStatus.FAILED,
                error_message="OCR failed"
            )
        ]

        for doc in docs:
            test_db.add(doc)

        await test_db.commit()

        # Filter by status
        response = await test_client.get("/api/v1/documents?status=indexed", headers=headers)

        assert response.status_code == 200
        data = response.json()
        documents = data["data"]["documents"]

        assert len(documents) == 1
        assert documents[0]["status"] == "indexed"

        # Search by content
        response = await test_client.get("/api/v1/documents?search=indexed%20content", headers=headers)

        assert response.status_code == 200
        data = response.json()
        documents = data["data"]["documents"]

        # Should find the indexed document
        assert len(documents) >= 1
        found_indexed = any(doc["file_name"] == "indexed_doc.pdf" for doc in documents)
        assert found_indexed

    @pytest.mark.asyncio
    async def test_document_retry_failed_processing(self, test_client: AsyncClient, firm_a_token: str, test_db: AsyncSession):
        """Test retry functionality for failed document processing"""
        headers = {"Authorization": f"Bearer {firm_a_token}"}

        # Create failed document
        document = Document(
            firm_id="firm-a-id",
            file_name="failed.pdf",
            file_type="pdf",
            file_size_bytes=1024000,
            blob_path="path/failed.pdf",
            status=DocumentStatus.FAILED,
            error_message="OCR processing failed"
        )
        test_db.add(document)
        await test_db.commit()

        doc_id = document.id

        # Retry processing
        with patch("backend.workers.document_worker.process_document.delay") as mock_delay:
            mock_delay.return_value = AsyncMock()

            response = await test_client.post(f"/api/v1/documents/{doc_id}/retry", headers=headers)

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True

            # Verify background job was queued
            mock_delay.assert_called_once_with(doc_id)

    @pytest.mark.asyncio
    async def test_document_soft_delete(self, test_client: AsyncClient, firm_a_token: str, test_db: AsyncSession):
        """Test soft delete functionality"""
        headers = {"Authorization": f"Bearer {firm_a_token}"}

        # Create document
        document = Document(
            firm_id="firm-a-id",
            file_name="test.pdf",
            file_type="pdf",
            file_size_bytes=1024000,
            blob_path="path/test.pdf",
            status=DocumentStatus.INDEXED
        )
        test_db.add(document)
        await test_db.commit()

        doc_id = document.id

        # Soft delete
        response = await test_client.delete(f"/api/v1/documents/{doc_id}", headers=headers)

        assert response.status_code == 204

        # Verify document is marked as deleted
        result = await test_db.execute(
            Document.__table__.select().where(Document.id == doc_id)
        )
        deleted_doc = result.scalar_one()
        assert deleted_doc.deleted_at is not None

        # Verify it's not returned in normal queries
        response = await test_client.get(f"/api/v1/documents/{doc_id}", headers=headers)
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_document_file_size_limits(self, test_client: AsyncClient, firm_a_token: str):
        """Test file size limit enforcement"""
        headers = {"Authorization": f"Bearer {firm_a_token}"}

        # Try to upload file that's too large
        large_content = b"x" * (51 * 1024 * 1024)  # 51MB
        files = {
            "file": ("large_file.pdf", large_content, "application/pdf")
        }
        data = {
            "file_name": "large_file.pdf",
            "file_type": "pdf"
        }

        response = await test_client.post("/api/v1/documents/upload", files=files, data=data, headers=headers)

        assert response.status_code == 413  # Payload too large

    @pytest.mark.asyncio
    async def test_document_type_validation(self, test_client: AsyncClient, firm_a_token: str):
        """Test file type validation"""
        headers = {"Authorization": f"Bearer {firm_a_token}"}

        # Try to upload unsupported file type
        files = {
            "file": ("script.exe", b"fake exe content", "application/x-msdownload")
        }
        data = {
            "file_name": "script.exe",
            "file_type": "exe"
        }

        response = await test_client.post("/api/v1/documents/upload", files=files, data=data, headers=headers)

        assert response.status_code == 400  # Bad request
        data = response.json()
        assert "not supported" in data["error"]["message"].lower()

    @pytest.mark.asyncio
    async def test_concurrent_document_uploads(self, test_client: AsyncClient, firm_a_token: str):
        """Test handling of concurrent document uploads"""
        import asyncio
        headers = {"Authorization": f"Bearer {firm_a_token}"}

        async def upload_document(i):
            files = {
                "file": (f"test_{i}.pdf", b"fake pdf content", "application/pdf")
            }
            data = {
                "file_name": f"test_{i}.pdf",
                "file_type": "pdf"
            }

            with patch("backend.services.document_service.DocumentService.upload_document") as mock_upload:
                mock_upload.return_value = {
                    "document_id": f"doc-{i}",
                    "status": "pending",
                    "message": "Document uploaded successfully"
                }

                response = await test_client.post("/api/v1/documents/upload", files=files, data=data, headers=headers)
                return response.status_code

        # Upload 5 documents concurrently
        tasks = [upload_document(i) for i in range(5)]
        results = await asyncio.gather(*tasks)

        # All should succeed
        for status_code in results:
            assert status_code == 201