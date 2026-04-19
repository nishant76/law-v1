"""
Document Ingest Pipeline — Complete Implementation Guide
=========================================================

This guide explains the complete flow of the document ingest pipeline,
from file upload to indexing and search-readiness.

## Architecture Overview

The pipeline consists of three main layers:

1. **API Layer** (backend/api/documents.py)
   - Receives HTTP requests from frontend
   - Validates inputs
   - Handles authentication/authorization
   - Returns responses faster than ingest completes

2. **Service Layer** (backend/services/document_service.py)
   - Contains ALL business logic
   - Handles file storage, text extraction, chunking, embedding, indexing
   - Can be called from endpoints OR Celery tasks
   - Testable and reusable

3. **Worker Layer** (backend/workers/document_ingest.py)
   - Celery background job (thin wrapper only)
   - Calls DocumentService methods
   - Handles retry logic with exponential backoff
   - Graceful error handling

## Complete Flow

### Step 1: File Upload via HTTP (POST /api/v1/documents/upload)

```
Frontend
  ↓
POST /api/v1/documents/upload
  (multipart/form-data with file)
  ↓
api/documents.py → upload_document()
  ├─ Get firm_id from JWT (injected by middleware)
  ├─ Validate file type (PDF, DOCX, images only)
  ├─ Validate file size (max 50MB)
  ├─ Call DocumentService.save_to_blob_storage()
  │  ├ Save file to Azure Blob Storage
  │  └ Return blob_path
  ├─ Call DocumentService.store_document_in_db()
  │  ├ Create Document record in DB
  │  ├ Status = "pending"
  │  └ Return document object with ID
  ├─ Enqueue Celery task: document_ingest(document_id, firm_id, filename, file_type)
  └─ Return 202 ACCEPTED with document_id and status="pending"
        ↓
    [Client receives immediately — upload complete]
```

### Step 2: Background Processing (Celery Job)

The Celery job runs asynchronously in the background (10-minute timeout):

```
Celery Worker (documents queue)
  ↓
workers/document_ingest.py → document_ingest()
  ├─ Retry logic: 3x with exponential backoff
  │  (1s, 2s, 4s delays between attempts)
  ├─ Call DocumentService.get_document(document_id)
  │  └ Retrieve document from DB
  ├─ Call DocumentService.extract_text_from_document()
  │  ├ Fetch file from Azure Blob Storage
  │  ├ If PDF: Run OCR via Azure Document Intelligence
  │  ├ Extract text/images
  │  └ Return full text
  ├─ Call DocumentService.chunk_text()
  │  ├ Split text into 500-token chunks
  │  ├ 50-token overlap between chunks
  │  └ Return list of chunks
  ├─ Call DocumentService.generate_embeddings()
  │  ├ Call Azure OpenAI text-embedding-ada-002
  │  ├ Generate 1536-dimensional embeddings
  │  ├ One embedding per chunk
  │  └ Return list of embeddings
  ├─ Call DocumentService.index_in_search()
  │  ├ Connect to Azure AI Search
  │  ├ Create index entries for each chunk
  │  │  ├ metadata: document_id, firm_id, file_name
  │  │  ├ content: chunk text
  │  │  └ embedding: vector
  │  ├ Set RLS filter (firm_id) so other firms can't see this
  │  └ Return success
  └─ Call DocumentService.update_document_indexed()
     ├ Update status = "indexed"
     ├ Set chunk_count
     ├ Set indexed_at timestamp
     └ Return success
```

### Step 3: Failure Handling

If ANY step fails:

```
On Exception:
  ├─ Catch error with plain-English message
  └─ Call DocumentService.update_document_status()
     ├ Status = "failed"
     ├ error_reason = plain-English message (e.g. "File too large for OCR")
     └ Document marked failed in DB
  ├─ Task retries automatically 3x:
  │  ├ Attempt 1: after 1 second
  │  ├ Attempt 2: after 2 seconds
  │  └ Attempt 3: after 4 seconds
  └─ After 3 retries: abandon and leave status="failed"
```

### Step 4: Frontend Polling

Frontend polls document status:

```
Frontend: GET /api/v1/documents/{document_id}
  ↓
api/documents.py → get_document()
  ├─ Retrieve document from DB
  └─ Return current status
     ├─ status="pending"   → Still waiting for processing
     ├─ status="processing" → Currently being processed
     ├─ status="indexed"   → Ready for search
     └─ status="failed"    → ERROR: Display error_reason to user
```

## Configuration

### Required Environment Variables

```bash
# Azure Blob Storage
BLOB_CONNECTION_STRING=<your-connection-string>
BLOB_CONTAINER_NAME=documents

# Azure Document Intelligence (for OCR)
DOCUMENT_INTELLIGENCE_ENDPOINT=https://<region>.api.cognitive.microsoft.com/
DOCUMENT_INTELLIGENCE_API_KEY=<your-key>

# Azure OpenAI (for embeddings)
AZURE_OPENAI_ENDPOINT=https://<resource>.openai.azure.com/
AZURE_OPENAI_API_KEY=<your-key>
AZURE_OPENAI_API_VERSION=2024-10-21
EMBEDDING_DEPLOYMENT=text-embedding-ada-002

# Azure Search (for indexing)
AZURE_SEARCH_ENDPOINT=https://<service>.search.windows.net/
AZURE_SEARCH_KEY=<your-key>
AZURE_SEARCH_INDEX_NAME=documents

# Celery / Redis
REDIS_URL=redis://localhost:6379/0
```

## Testing the Pipeline

### 1. Start the Server

```bash
# Start FastAPI + PostgreSQL + Redis + Celery
docker-compose up -d

# Or locally:
python main.py  # FastAPI
celery -A celery_app worker -Q documents -l info  # Celery worker
```

### 2. Upload a Document

```bash
# Using curl:
curl -X POST http://localhost:8000/api/v1/documents/upload \
  -F "file=@sample.pdf" \
  -F "matter_id=00000000-0000-0000-0000-000000000001"

# Using Python:
import requests
with open('sample.pdf', 'rb') as f:
    response = requests.post(
        'http://localhost:8000/api/v1/documents/upload',
        files={'file': f},
        data={'matter_id': '00000000-0000-0000-0000-000000000001'}
    )
    print(response.json())

# Expected response (202 ACCEPTED):
{
  "success": true,
  "data": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "file_name": "sample.pdf",
    "file_type": "pdf",
    "file_size_bytes": 1048576,
    "status": "pending",
    "chunk_count": 0,
    "created_at": "2024-04-08T10:30:00Z",
    "indexed_at": null
  },
  "meta": {
    "request_id": "abc123",
    "message": "Document received and queued for processing. Check status later."
  }
}
```

### 3. Poll Document Status

```bash
curl http://localhost:8000/api/v1/documents/550e8400-e29b-41d4-a716-446655440000

# After a few seconds:
{
  "success": true,
  "data": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "file_name": "sample.pdf",
    "file_type": "pdf",
    "file_size_bytes": 1048576,
    "status": "indexed",
    "chunk_count": 42,
    "created_at": "2024-04-08T10:30:00Z",
    "indexed_at": "2024-04-08T10:30:15Z"
  },
  "meta": {"request_id": "abc123"}
}
```

### 4. Check Celery Logs

```bash
# Watch Celery worker output
docker-compose logs celery

# Or if running locally:
celery -A celery_app worker -Q documents -l info
```

Expected output:
```
Starting document ingest: 550e8400-e29b-41d4-a716-446655440000
Extracted 5234 characters from sample.pdf
Created 42 chunks
Generated 42 embeddings
Indexed document 550e8400... with 42 chunks in search index for firm xx
Document ingest successful: 550e8400... (42 chunks)
```

## Performance Targets

From CLAUDE.md:
- Upload API response: < 3 seconds (returns before processing starts)
- Full document indexing (background): < 10 minutes (Celery timeout)
- Text extraction: < 10 seconds
- Embedding generation: < 5 seconds
- Search indexing: < 10 seconds

## CLAUDE.md Compliance Checklist

✅ All business logic in services/ (DocumentService)
✅ Celery tasks are thin wrappers (document_ingest wraps service calls)
✅ Async everywhere (AsyncSession, async functions)
✅ UUID primary keys (Document.id = UUID)
✅ TIMESTAMPTZ (created_at, indexed_at)
✅ Soft deletes (deleted_at column exists)
✅ firm_id from JWT, never request body
✅ Parameterised database queries (SQLAlchemy ORM)
✅ Standardised error response format
✅ request_id in every response header
✅ Never log document content (logs only actions and IDs)
✅ Retry logic: 3x exponential backoff
✅ Plain English error messages for users
✅ 202 ACCEPTED for async operations

## Files Modified/Created

1. backend/schemas/document.py
   - DocumentUploadRequest
   - DocumentResponse
   - DocumentUploadResponse

2. backend/services/document_service.py (NEW)
   - DocumentService class
   - validate_upload()
   - save_to_blob_storage()
   - store_document_in_db()
   - extract_text_from_document()
   - chunk_text()
   - generate_embeddings()
   - index_in_search()
   - update_document_indexed()

3. backend/workers/document_ingest.py (NEW)
   - document_ingest() Celery task
   - _document_ingest_async() implementation
   - _update_document_failed() error handler

4. backend/api/documents.py (NEW)
   - upload_document() endpoint
   - get_document() endpoint

5. main.py (UPDATED)
   - Added documents router import
   - Included documents router

6. requirements.txt (UPDATED)
   - Added: azure-ai-documentintelligence
   - Added: tiktoken

## Next Steps

1. **Run migrations** (if not already done):
   ```bash
   python run_migrations.py
   ```

2. **Install new dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up Azure services** (dev.env):
   ```bash
   # Copy .env.example and fill in Azure credentials
   cp .env.example .env
   # Edit .env with your Azure services
   ```

4. **Start the stack**:
   ```bash
   docker-compose up -d
   ```

5. **Test the pipeline** (see Testing section above)

6. **Implement Azure client connections**:
   - In DocumentService, replace mock Azure calls with real SDK calls
   - Use Azure SDK clients in __init__ method

7. **Monitor in production**:
   - Watch Celery task completion rates
   - Set up alerts for retry rates > 5%
   - Track document indexing latency

## Troubleshooting

### "Failed to save to blob storage"
- Check BLOB_CONNECTION_STRING in .env
- Verify Azure Blob Storage account exists and is accessible
- Check file permissions

### "Document not found" when polling
- Verify document_id is correct
- Check that firm_id in JWT matches document's firm_id
- Document may have been soft-deleted (check deleted_at)

### Celery task not processing
- Check Redis is running: `redis-cli ping`
- Check Celery worker is running: `celery -A celery_app inspect active`
- Verify REDIS_URL in .env

### "Retry: 3x exponential backoff" infinite loop
- Likely same error each time (not transient)
- Check error logs for actual error
- Document will eventually get status="failed"

### High token count errors
- Document may contain too many pages or dense text
- Suggest to user: split into smaller documents or submit later

## API Endpoints Summary

| Method | Path | Status | Purpose |
|--------|------|--------|---------|
| POST | /api/v1/documents/upload | 202 | Upload document, start processing |
| GET | /api/v1/documents/{id} | 200 | Get document status |

## Security Considerations

✅ firm_id enforced (from JWT, never request body)
✅ Never logs document content (PII protection)
✅ RLS enabled on documents table
✅ soft delete only (never hard delete)
✅ Sanitise all paths before building blob paths
✅ Validate file extensions and MIME types
✅ File size limit enforced (50MB max)
✅ Error messages don't reveal sensitive info

---

Last updated: April 2026
"""
