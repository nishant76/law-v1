# SuperAdvocate — AI-Powered Legal Workspace
## Phase 1: Solo Lawyers in Punjab/Haryana

SuperAdvocate is an AI-powered legal workspace for solo lawyers and small firms in Punjab, Haryana, and Chandigarh. Phase 1 provides semantic search over public Indian judgments and lawyers' own case files, unified in a single interface.

### Quick Start

#### 1. Local Setup with Docker

**Prerequisites:**
- Docker and Docker Compose installed
- Python 3.11+ (optional, for direct development)

**Start all services:**
```bash
cp .env.example .env
docker-compose up
```

This starts:
- FastAPI backend (http://localhost:8000)
- PostgreSQL database
- Redis cache
- Celery worker for background jobs

**Health check:**
```bash
curl http://localhost:8000/api/v1/health
```

#### 2. Project Structure

```
superadvocate/
├── backend/
│   ├── api/              # FastAPI routers
│   ├── services/         # Business logic only
│   ├── models/           # SQLAlchemy ORM
│   ├── schemas/          # Pydantic schemas
│   ├── core/             # config.py, logger.py
│   ├── middleware/       # JWT, logging, rate limiting
│   ├── workers/          # Celery tasks
│   └── migrations/       # Alembic migrations
├── main.py               # FastAPI entry point
├── celery_app.py         # Celery configuration
└── requirements.txt
```

#### 3. Environment Variables

Copy `.env.example` to `.env` and fill in Azure credentials:

```bash
cp .env.example .env
```

For **local development**, dummy values work for non-Azure services.

#### 4. API Convention

All responses follow this shape:
```json
{
  "success": true,
  "data": {},
  "error": null,
  "meta": {
    "request_id": "uuid",
    "version": "v1"
  }
}
```

#### 5. Key Endpoints (Phase 1)

- `GET /api/v1/health` — Application health check
- `POST /api/v1/documents/upload` — Upload PDF/DOCX (Phase 1)
- `GET /api/v1/search` — Unified search (Phase 1)

---

### Development Workflow

**Edit code** → Docker auto-reloads FastAPI (volume-mounted)

**Run migrations:**
```bash
docker-compose exec backend alembic upgrade head
```

**View logs:**
```bash
docker-compose logs -f backend
docker-compose logs -f celery
```

**Stop services:**
```bash
docker-compose down
```

---

### Testing

#### Test Structure

```
tests/
├── conftest.py                    # Shared test fixtures
├── pytest.ini                     # Test configuration
├── unit/                          # Unit tests
│   ├── test_sanitiser.py         # Document sanitisation
│   ├── test_draft_quality.py     # Draft quality scoring
│   └── test_citation_verifier.py # Citation verification
├── integration/                   # Integration tests
│   ├── test_auth.py              # Authentication flow
│   ├── test_search.py            # Search functionality
│   └── test_documents.py         # Document management
├── security/                      # Security tests
│   └── test_tenant_isolation.py  # Multi-tenant isolation
└── prompt_regression/            # Prompt regression tests
    ├── test_case_synopsis.py     # Case synopsis prompts
    └── test_pdf_extractor.py     # PDF extractor prompts
```

#### Running Tests

**Run all tests:**
```bash
# With Docker (recommended)
docker-compose exec backend pytest

# Or directly (if running without Docker)
pytest
```

**Run specific test categories:**
```bash
# Unit tests only
pytest -m unit

# Integration tests only
pytest -m integration

# Security tests only
pytest -m security

# Prompt regression tests only
pytest -m prompt_regression
```

**Run specific test files:**
```bash
# Single test file
pytest tests/unit/test_sanitiser.py

# Multiple files
pytest tests/unit/test_sanitiser.py tests/unit/test_draft_quality.py
```

**Run with coverage:**
```bash
pytest --cov=backend --cov-report=html
```

**Run tests in verbose mode:**
```bash
pytest -v
```

#### Test Configuration

- **Database:** SQLite in-memory for fast testing
- **Azure Services:** All mocked to avoid real API calls
- **Multi-tenant:** Two test firms (firm-a, firm-b) for isolation testing
- **Async:** All tests support async/await patterns

#### Writing New Tests

**Unit Test Example:**
```python
import pytest
from backend.services.sanitiser_service import SanitiserService

def test_sanitise_control_characters():
    service = SanitiserService()
    text = "Hello\x00World\x01Test"
    result = service.sanitise(text)
    assert "\x00" not in result
    assert "\x01" not in result
    assert "HelloWorldTest" == result
```

**Integration Test Example:**
```python
@pytest.mark.integration
async def test_document_upload_flow(test_client: AsyncClient, firm_a_token: str):
    headers = {"Authorization": f"Bearer {firm_a_token}"}
    files = {"file": ("test.pdf", b"content", "application/pdf")}
    data = {"file_name": "test.pdf"}

    response = await test_client.post("/api/v1/documents/upload", files=files, data=data, headers=headers)
    assert response.status_code == 201
```

**Security Test Example:**
```python
@pytest.mark.security
async def test_firm_isolation_documents(test_client: AsyncClient, firm_a_token: str, firm_b_token: str):
    # Test that firms cannot access each other's documents
    headers_a = {"Authorization": f"Bearer {firm_a_token}"}
    headers_b = {"Authorization": f"Bearer {firm_b_token}"}

    # Create document for firm A, try to access from firm B
    # Should return 404, not 403
```

#### Test Fixtures

Available in `tests/conftest.py`:
- `test_db`: Async SQLAlchemy session
- `test_client`: FastAPI test client
- `firm_a_token`, `firm_b_token`: JWT tokens for test firms
- Azure service mocks (OpenAI, Search, Blob Storage)

#### CI/CD Integration

Tests run automatically on:
- Pull requests
- Main branch pushes
- Manual trigger

**Local pre-commit:**
```bash
pytest --tb=short
```

---

### Security

- ✓ GZipMiddleware enabled (compress responses > 1KB)
- ✓ Request logging with request_id tracking
- ✓ CORS configured (development: * → production: law.superadvocate.ai only)
- ✓ JWT validation ready (Phase 1 middleware stub)
- ✓ Soft deletes on all tables
- ✓ PostgreSQL Row Level Security (RLS) ready

---

### Coding Rules

- **Async everywhere** — never sync database calls
- **Business logic in services/** — never in api/ routers
- **Celery tasks are thin wrappers** — call services/ only
- **Parameterised queries only** — never f-strings in SQL
- **UUID primary keys** — never integers
- **Never hard delete** — use soft deletes (deleted_at column)
- **Secrets in .env** — never commit to git

---

### Phase 1 Features (Build Only These)

1. Document Library — upload + index
2. Public Judgment Search — 10,000+ judgments
3. Own Files Search (RAG)
4. Unified Search Interface
5. PDF Extractor
6. Case Synopsis Generator
7. Smart Reply Generator
8. Strategic Filing Drafter
9. Deadline Tracker (with WhatsApp reminders)
10. Legal Process Guide

See CLAUDE.md for complete feature specs and rules.

---

### Next Steps

- [ ] Run `docker-compose up` to verify all services start
- [ ] Test `/api/v1/health` endpoint
- [ ] Create PostgreSQL schema for law vertical
- [ ] Build document ingest pipeline (Celery)
- [ ] Implement search service (Azure AI Search)
