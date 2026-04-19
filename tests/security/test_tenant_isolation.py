"""
Security tests for tenant isolation and access control
"""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.law_firm import Firm
from backend.models.law_user import User, UserRole
from backend.models.law_document import Document
from backend.models.law_citation import Citation
from backend.models.law_matter import Matter
from backend.core.security import create_access_token


@pytest.mark.security
class TestTenantIsolation:
    """Security tests ensuring proper tenant isolation"""

    @pytest.mark.asyncio
    async def test_firm_data_isolation_documents(self, test_client: AsyncClient, test_db: AsyncSession):
        """Test that firms cannot access each other's documents"""
        # Create two firms
        firm_a = Firm(
            name="Firm A",
            email="firm_a@test.com",
            city="Amritsar",
            state="Punjab",
            plan="solo"
        )
        firm_b = Firm(
            name="Firm B",
            email="firm_b@test.com",
            city="Ludhiana",
            state="Punjab",
            plan="solo"
        )
        test_db.add(firm_a)
        test_db.add(firm_b)
        await test_db.commit()

        # Create users for each firm
        user_a = User(
            firm_id=firm_a.id,
            name="User A",
            email="user_a@test.com",
            hashed_password="hashed",
            role=UserRole.LAWYER
        )
        user_b = User(
            firm_id=firm_b.id,
            name="User B",
            email="user_b@test.com",
            hashed_password="hashed",
            role=UserRole.LAWYER
        )
        test_db.add(user_a)
        test_db.add(user_b)
        await test_db.commit()

        # Create documents for each firm
        doc_a = Document(
            firm_id=firm_a.id,
            file_name="firm_a_doc.pdf",
            file_type="pdf",
            file_size_bytes=1024000,
            blob_path="firm_a/doc.pdf",
            status="indexed"
        )
        doc_b = Document(
            firm_id=firm_b.id,
            file_name="firm_b_doc.pdf",
            file_type="pdf",
            file_size_bytes=1024000,
            blob_path="firm_b/doc.pdf",
            status="indexed"
        )
        test_db.add(doc_a)
        test_db.add(doc_b)
        await test_db.commit()

        # Create tokens for each user
        token_a = create_access_token({"sub": str(user_a.id), "firm_id": str(firm_a.id), "vertical": "law"})
        token_b = create_access_token({"sub": str(user_b.id), "firm_id": str(firm_b.id), "vertical": "law"})

        # Firm A user tries to access their document
        headers_a = {"Authorization": f"Bearer {token_a}"}
        response_a = await test_client.get(f"/api/v1/documents/{doc_a.id}", headers=headers_a)
        assert response_a.status_code == 200

        # Firm A user tries to access Firm B's document
        response_a_cross = await test_client.get(f"/api/v1/documents/{doc_b.id}", headers=headers_a)
        assert response_a_cross.status_code == 404  # Should not find

        # Firm B user tries to access their document
        headers_b = {"Authorization": f"Bearer {token_b}"}
        response_b = await test_client.get(f"/api/v1/documents/{doc_b.id}", headers=headers_b)
        assert response_b.status_code == 200

        # Firm B user tries to access Firm A's document
        response_b_cross = await test_client.get(f"/api/v1/documents/{doc_a.id}", headers=headers_b)
        assert response_b_cross.status_code == 404  # Should not find

    @pytest.mark.asyncio
    async def test_firm_data_isolation_matters(self, test_client: AsyncClient, test_db: AsyncSession):
        """Test that firms cannot access each other's matters"""
        # Create two firms
        firm_a = Firm(name="Firm A", email="firm_a@test.com", city="Amritsar", state="Punjab", plan="solo")
        firm_b = Firm(name="Firm B", email="firm_b@test.com", city="Ludhiana", state="Punjab", plan="solo")
        test_db.add(firm_a)
        test_db.add(firm_b)
        await test_db.commit()

        # Create users
        user_a = User(firm_id=firm_a.id, name="User A", email="user_a@test.com", hashed_password="hashed", role=UserRole.LAWYER)
        user_b = User(firm_id=firm_b.id, name="User B", email="user_b@test.com", hashed_password="hashed", role=UserRole.LAWYER)
        test_db.add(user_a)
        test_db.add(user_b)
        await test_db.commit()

        # Create matters for each firm
        matter_a = Matter(
            firm_id=firm_a.id,
            case_number="CR-123/2023",
            case_name="State v. Accused A",
            court="District Court Amritsar",
            matter_type="criminal"
        )
        matter_b = Matter(
            firm_id=firm_b.id,
            case_number="CR-456/2023",
            case_name="State v. Accused B",
            court="District Court Ludhiana",
            matter_type="criminal"
        )
        test_db.add(matter_a)
        test_db.add(matter_b)
        await test_db.commit()

        # Create tokens
        token_a = create_access_token({"sub": str(user_a.id), "firm_id": str(firm_a.id), "vertical": "law"})
        token_b = create_access_token({"sub": str(user_b.id), "firm_id": str(firm_b.id), "vertical": "law"})

        # Test matter access isolation
        headers_a = {"Authorization": f"Bearer {token_a}"}
        headers_b = {"Authorization": f"Bearer {token_b}"}

        # Firm A can access their matter
        response_a = await test_client.get(f"/api/v1/matters/{matter_a.id}", headers=headers_a)
        assert response_a.status_code == 200

        # Firm A cannot access Firm B's matter
        response_a_cross = await test_client.get(f"/api/v1/matters/{matter_b.id}", headers=headers_a)
        assert response_a_cross.status_code == 404

        # Firm B can access their matter
        response_b = await test_client.get(f"/api/v1/matters/{matter_b.id}", headers=headers_b)
        assert response_b.status_code == 200

        # Firm B cannot access Firm A's matter
        response_b_cross = await test_client.get(f"/api/v1/matters/{matter_a.id}", headers=headers_b)
        assert response_b_cross.status_code == 404

    @pytest.mark.asyncio
    async def test_public_citations_accessible_to_all_firms(self, test_client: AsyncClient, test_db: AsyncSession):
        """Test that public citations are accessible to all firms"""
        # Create a public citation
        citation = Citation(
            citation_key="2023 SCC 123",
            case_name="State of Punjab v. Baldev Singh",
            court="Supreme Court of India",
            year=2023,
            official_source="eSCR",
            source_url="https://sci.gov.in",
            judgment_text="Test judgment text"
        )
        test_db.add(citation)
        await test_db.commit()

        # Create two firms and users
        firm_a = Firm(name="Firm A", email="firm_a@test.com", city="Amritsar", state="Punjab", plan="solo")
        firm_b = Firm(name="Firm B", email="firm_b@test.com", city="Ludhiana", state="Punjab", plan="solo")
        test_db.add(firm_a)
        test_db.add(firm_b)
        await test_db.commit()

        user_a = User(firm_id=firm_a.id, name="User A", email="user_a@test.com", hashed_password="hashed", role=UserRole.LAWYER)
        user_b = User(firm_id=firm_b.id, name="User B", email="user_b@test.com", hashed_password="hashed", role=UserRole.LAWYER)
        test_db.add(user_a)
        test_db.add(user_b)
        await test_db.commit()

        token_a = create_access_token({"sub": str(user_a.id), "firm_id": str(firm_a.id), "vertical": "law"})
        token_b = create_access_token({"sub": str(user_b.id), "firm_id": str(firm_b.id), "vertical": "law"})

        # Both firms should be able to search public citations
        headers_a = {"Authorization": f"Bearer {token_a}"}
        headers_b = {"Authorization": f"Bearer {token_b}"}

        search_data = {"query": "State of Punjab", "scope": "public_judgments"}

        response_a = await test_client.post("/api/v1/search", json=search_data, headers=headers_a)
        response_b = await test_client.post("/api/v1/search", json=search_data, headers=headers_b)

        assert response_a.status_code == 200
        assert response_b.status_code == 200

        data_a = response_a.json()
        data_b = response_b.json()

        # Both should find the same public citation
        results_a = data_a["data"]["public_judgments"]
        results_b = data_b["data"]["public_judgments"]

        assert len(results_a) >= 1
        assert len(results_b) >= 1
        assert results_a[0]["citation_key"] == results_b[0]["citation_key"]

    @pytest.mark.asyncio
    async def test_role_based_access_control(self, test_client: AsyncClient, test_db: AsyncSession):
        """Test that different roles have appropriate access levels"""
        # Create a firm
        firm = Firm(name="Test Firm", email="test@test.com", city="Amritsar", state="Punjab", plan="small")
        test_db.add(firm)
        await test_db.commit()

        # Create users with different roles
        lawyer = User(firm_id=firm.id, name="Lawyer", email="lawyer@test.com", hashed_password="hashed", role=UserRole.LAWYER)
        staff = User(firm_id=firm.id, name="Staff", email="staff@test.com", hashed_password="hashed", role=UserRole.STAFF)
        admin = User(firm_id=firm.id, name="Admin", email="admin@test.com", hashed_password="hashed", role=UserRole.FIRM_ADMIN)
        test_db.add(lawyer)
        test_db.add(staff)
        test_db.add(admin)
        await test_db.commit()

        # Create tokens
        token_lawyer = create_access_token({"sub": str(lawyer.id), "firm_id": str(firm.id), "vertical": "law"})
        token_staff = create_access_token({"sub": str(staff.id), "firm_id": str(firm.id), "vertical": "law"})
        token_admin = create_access_token({"sub": str(admin.id), "firm_id": str(firm.id), "vertical": "law"})

        headers_lawyer = {"Authorization": f"Bearer {token_lawyer}"}
        headers_staff = {"Authorization": f"Bearer {token_staff}"}
        headers_admin = {"Authorization": f"Bearer {token_admin}"}

        # Test document access (all roles should have access)
        response_lawyer = await test_client.get("/api/v1/documents", headers=headers_lawyer)
        response_staff = await test_client.get("/api/v1/documents", headers=headers_staff)
        response_admin = await test_client.get("/api/v1/documents", headers=headers_admin)

        assert response_lawyer.status_code in [200, 404]  # 404 if no documents
        assert response_staff.status_code in [200, 404]
        assert response_admin.status_code in [200, 404]

        # Test user management (only admin should have access)
        response_lawyer_users = await test_client.get("/api/v1/firms/users", headers=headers_lawyer)
        response_staff_users = await test_client.get("/api/v1/firms/users", headers=headers_staff)
        response_admin_users = await test_client.get("/api/v1/firms/users", headers=headers_admin)

        assert response_lawyer_users.status_code == 403  # Forbidden
        assert response_staff_users.status_code == 403
        assert response_admin_users.status_code == 200

    @pytest.mark.asyncio
    async def test_jwt_token_firm_id_validation(self, test_client: AsyncClient, test_db: AsyncSession):
        """Test that JWT tokens are properly validated for firm_id"""
        # Create a firm and user
        firm = Firm(name="Test Firm", email="test@test.com", city="Amritsar", state="Punjab", plan="solo")
        test_db.add(firm)
        await test_db.commit()

        user = User(firm_id=firm.id, name="Test User", email="user@test.com", hashed_password="hashed", role=UserRole.LAWYER)
        test_db.add(user)
        await test_db.commit()

        # Create a valid token
        valid_token = create_access_token({"sub": str(user.id), "firm_id": str(firm.id), "vertical": "law"})

        # Create a token with wrong firm_id
        wrong_firm_token = create_access_token({"sub": str(user.id), "firm_id": "wrong-firm-id", "vertical": "law"})

        # Create a token missing firm_id
        no_firm_token = create_access_token({"sub": str(user.id), "vertical": "law"})

        # Test with valid token
        headers_valid = {"Authorization": f"Bearer {valid_token}"}
        response_valid = await test_client.get("/api/v1/documents", headers=headers_valid)
        assert response_valid.status_code in [200, 404]

        # Test with wrong firm token
        headers_wrong = {"Authorization": f"Bearer {wrong_firm_token}"}
        response_wrong = await test_client.get("/api/v1/documents", headers=headers_wrong)
        assert response_wrong.status_code == 404  # Should not find any data

        # Test with no firm token
        headers_no_firm = {"Authorization": f"Bearer {no_firm_token}"}
        response_no_firm = await test_client.get("/api/v1/documents", headers=headers_no_firm)
        assert response_no_firm.status_code == 401  # Should be unauthorized

    @pytest.mark.asyncio
    async def test_sql_injection_prevention(self, test_client: AsyncClient, firm_a_token: str):
        """Test that SQL injection attempts are prevented"""
        headers = {"Authorization": f"Bearer {firm_a_token}"}

        # Try SQL injection in search query
        malicious_queries = [
            "'; DROP TABLE documents; --",
            "' OR '1'='1",
            "'; SELECT * FROM users; --",
            "test'; UPDATE documents SET status='failed'; --"
        ]

        for query in malicious_queries:
            search_data = {"query": query, "scope": "own_documents"}
            response = await test_client.post("/api/v1/search", json=search_data, headers=headers)

            # Should not crash or return sensitive data
            assert response.status_code in [200, 422]  # Either success or validation error

            if response.status_code == 200:
                data = response.json()
                # Should not contain unexpected results
                assert "documents" in data["data"] or "own_documents" in data["data"]

    @pytest.mark.asyncio
    async def test_rate_limiting_enforcement(self, test_client: AsyncClient, firm_a_token: str):
        """Test that rate limiting is properly enforced"""
        headers = {"Authorization": f"Bearer {firm_a_token}"}

        # Make many rapid requests
        responses = []
        for i in range(70):  # Exceed the 60 requests/minute limit
            response = await test_client.get("/api/v1/documents", headers=headers)
            responses.append(response.status_code)

        # Should see some rate limiting (429) responses
        rate_limited_responses = [r for r in responses if r == 429]
        assert len(rate_limited_responses) > 0, "Rate limiting should be enforced"

    @pytest.mark.asyncio
    async def test_request_id_tracking(self, test_client: AsyncClient, firm_a_token: str):
        """Test that request IDs are properly tracked"""
        headers = {"Authorization": f"Bearer {firm_a_token}"}

        response = await test_client.get("/api/v1/documents", headers=headers)

        # Should have request_id in response headers
        assert "x-request-id" in response.headers or "request_id" in response.headers

    @pytest.mark.asyncio
    async def test_audit_log_isolation(self, test_client: AsyncClient, test_db: AsyncSession):
        """Test that audit logs are properly isolated by firm"""
        from backend.models.shared_audit_log import AuditLog

        # Create two firms
        firm_a = Firm(name="Firm A", email="firm_a@test.com", city="Amritsar", state="Punjab", plan="solo")
        firm_b = Firm(name="Firm B", email="firm_b@test.com", city="Ludhiana", state="Punjab", plan="solo")
        test_db.add(firm_a)
        test_db.add(firm_b)
        await test_db.commit()

        # Create audit logs for each firm
        log_a = AuditLog(
            firm_id=firm_a.id,
            user_id="user-a-id",
            action="document_upload",
            resource_type="document",
            resource_id="doc-a-id",
            details={"file_name": "test_a.pdf"}
        )
        log_b = AuditLog(
            firm_id=firm_b.id,
            user_id="user-b-id",
            action="document_upload",
            resource_type="document",
            resource_id="doc-b-id",
            details={"file_name": "test_b.pdf"}
        )
        test_db.add(log_a)
        test_db.add(log_b)
        await test_db.commit()

        # Create users and tokens
        user_a = User(firm_id=firm_a.id, name="User A", email="user_a@test.com", hashed_password="hashed", role=UserRole.FIRM_ADMIN)
        user_b = User(firm_id=firm_b.id, name="User B", email="user_b@test.com", hashed_password="hashed", role=UserRole.FIRM_ADMIN)
        test_db.add(user_a)
        test_db.add(user_b)
        await test_db.commit()

        token_a = create_access_token({"sub": str(user_a.id), "firm_id": str(firm_a.id), "vertical": "law"})
        token_b = create_access_token({"sub": str(user_b.id), "firm_id": str(firm_b.id), "vertical": "law"})

        # Each firm should only see their own audit logs
        headers_a = {"Authorization": f"Bearer {token_a}"}
        headers_b = {"Authorization": f"Bearer {token_b}"}

        response_a = await test_client.get("/api/v1/audit/logs", headers=headers_a)
        response_b = await test_client.get("/api/v1/audit/logs", headers=headers_b)

        if response_a.status_code == 200:
            data_a = response_a.json()
            logs_a = data_a["data"]
            # Should only contain Firm A's logs
            for log in logs_a:
                assert log["firm_id"] == str(firm_a.id)

        if response_b.status_code == 200:
            data_b = response_b.json()
            logs_b = data_b["data"]
            # Should only contain Firm B's logs
            for log in logs_b:
                assert log["firm_id"] == str(firm_b.id)