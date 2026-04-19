"""
Document Service Implementation — Azure Integration Guide
==========================================================

This file explains how to implement the actual Azure SDK calls in
DocumentService to replace the mock implementations.

Each section shows:
1. Current mock implementation (placeholder)
2. Real implementation (with Azure SDK)
3. Environment variables needed
4. Error handling patterns

## 1. Azure Blob Storage Setup

### Environment Variables

Add to .env:
```
BLOB_CONNECTION_STRING=DefaultEndpointsProtocol=https;AccountName=...;AccountKey=...
BLOB_CONTAINER_NAME=documents
```

### Mock Implementation (Current in document_service.py)

```python
async def save_to_blob_storage(self, file_content, filename, firm_id, file_type):
    blob_path = f"documents/{firm_id}/{uuid.uuid4()}/{filename}"
    return blob_path
```

### Real Implementation

```python
from azure.storage.blob import BlobClient, generate_blob_sas, BlobSasPermissions
from azure.core.exceptions import AzureError

async def save_to_blob_storage(self, file_content, filename, firm_id, file_type):
    try:
        # Parse connection string (done once in __init__, stored in self)
        if not self._blob_client:
            self._blob_client = BlobClient.from_connection_string(
                settings.BLOB_CONNECTION_STRING,
                container_name=settings.BLOB_CONTAINER_NAME,
                blob_name="temp"  # Will override per upload
            )
        
        # Generate blob name
        blob_name = f"documents/{firm_id}/{uuid.uuid4()}/{filename}"
        
        # Create blob client for this specific blob
        blob_client = BlobClient.from_connection_string(
            settings.BLOB_CONNECTION_STRING,
            container_name=settings.BLOB_CONTAINER_NAME,
            blob_name=blob_name
        )
        
        # Upload file
        blob_client.upload_blob(file_content, overwrite=True)
        
        logger.info(f"Uploaded to blob: {blob_name}")
        return blob_name
        
    except AzureError as e:
        logger.error(f"Azure Storage error: {str(e)}")
        raise Exception(f"Failed to upload file: {str(e)}")
```

### Configuration in config.py

Add to Settings class:
```python
BLOB_CONNECTION_STRING: str = Field(default="", env="BLOB_CONNECTION_STRING")
BLOB_CONTAINER_NAME: str = Field(default="documents", env="BLOB_CONTAINER_NAME")
```

---

## 2. Azure Document Intelligence - OCR

### Environment Variables

Add to .env:
```
DOCUMENT_INTELLIGENCE_ENDPOINT=https://YOUR_REGION.api.cognitive.microsoft.com/
DOCUMENT_INTELLIGENCE_API_KEY=YOUR_API_KEY
```

### Mock Implementation (Current)

```python
async def extract_text_from_document(self, file_content, file_type):
    return "Mock extracted text from document..."
```

### Real Implementation

```python
from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.core.credentials import AzureKeyCredential
from azure.core.exceptions import AzureError
import asyncio

async def extract_text_from_document(self, file_content, file_type):
    try:
        # Initialize client (done once in __init__)
        if not self._doc_intelligence_client:
            self._doc_intelligence_client = DocumentIntelligenceClient(
                endpoint=settings.DOCUMENT_INTELLIGENCE_ENDPOINT,
                credential=AzureKeyCredential(settings.DOCUMENT_INTELLIGENCE_API_KEY)
            )
        
        # Run OCR
        # For PDFs and images, send the file to Azure Document Intelligence
        from io import BytesIO
        
        poller = self._doc_intelligence_client.begin_analyze_document(
            "prebuilt-document",
            document=BytesIO(file_content),
            content_type=self._get_content_type(file_type)
        )
        
        # Wait for completion (with timeout)
        result = await asyncio.to_thread(
            lambda: poller.result()
        )
        
        # Extract text from result
        extracted_text = ""
        if result.paragraphs:
            extracted_text = "\n".join([p.content for p in result.paragraphs])
        
        logger.info(f"Extracted {len(extracted_text)} chars from {file_type}")
        return extracted_text
        
    except AzureError as e:
        logger.error(f"Document Intelligence error: {str(e)}")
        raise Exception(f"Failed to extract text from document: {str(e)}")

def _get_content_type(self, file_type: str) -> str:
    """Map file extension to MIME type for Document Intelligence"""
    mime_types = {
        'pdf': 'application/pdf',
        'jpg': 'image/jpeg',
        'jpeg': 'image/jpeg',
        'png': 'image/png',
        'tiff': 'image/tiff',
        'tif': 'image/tiff',
        'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'doc': 'application/msword',
    }
    return mime_types.get(file_type.lower(), 'application/pdf')
```

### Configuration in config.py

Add to Settings class:
```python
DOCUMENT_INTELLIGENCE_ENDPOINT: str = Field(default="", env="DOCUMENT_INTELLIGENCE_ENDPOINT")
DOCUMENT_INTELLIGENCE_API_KEY: str = Field(default="", env="DOCUMENT_INTELLIGENCE_API_KEY")
```

---

## 3. Azure OpenAI - Embeddings

### Environment Variables (Already in .env)

```
AZURE_OPENAI_ENDPOINT=https://YOUR_RESOURCE.openai.azure.com/
AZURE_OPENAI_API_KEY=YOUR_API_KEY
AZURE_OPENAI_API_VERSION=2024-10-21
EMBEDDING_DEPLOYMENT=text-embedding-ada-002
```

### Mock Implementation (Current)

```python
async def generate_embeddings(self, texts):
    embeddings = []
    for text in texts:
        embedding = [0.1 * (i % 10) for i in range(1536)]
        embeddings.append(embedding)
    return embeddings
```

### Real Implementation

```python
from openai import AsyncAzureOpenAI
from azure.core.exceptions import AzureError

async def generate_embeddings(self, texts):
    try:
        # Initialize client (done once in __init__)
        if not self._embeddings_client:
            self._embeddings_client = AsyncAzureOpenAI(
                api_key=settings.AZURE_OPENAI_API_KEY,
                api_version=settings.AZURE_OPENAI_API_VERSION,
                azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
            )
        
        # Generate embeddings
        response = await self._embeddings_client.embeddings.create(
            input=texts,
            model=settings.EMBEDDING_DEPLOYMENT,
        )
        
        # Extract embedding vectors
        embeddings = [item.embedding for item in response.data]
        
        logger.info(f"Generated {len(embeddings)} embeddings")
        return embeddings
        
    except AzureError as e:
        logger.error(f"Azure OpenAI error: {str(e)}")
        raise Exception(f"Failed to generate embeddings: {str(e)}")
```

### Configuration in config.py

These are already present, see existing config.py

---

## 4. Azure AI Search - Indexing

### Environment Variables

Add to .env:
```
AZURE_SEARCH_ENDPOINT=https://YOUR_SERVICE.search.windows.net/
AZURE_SEARCH_KEY=YOUR_API_KEY
AZURE_SEARCH_INDEX_NAME=documents
```

### Mock Implementation (Current)

```python
async def index_in_search(self, document_id, chunks, embeddings, firm_id, filename):
    logger.info(f"Indexed document {document_id} with {len(chunks)} chunks...")
    return True
```

### Real Implementation

```python
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    SearchIndex, SearchField, SearchFieldDataType, SimpleField,
    SearchableField, VectorSearch, HnswAlgorithmConfiguration, VectorSearchProfile
)
from azure.core.credentials import AzureKeyCredential
from azure.core.exceptions import AzureError

async def index_in_search(self, document_id, chunks, embeddings, firm_id, filename):
    try:
        # Initialize clients (done once in __init__)
        if not self._search_client:
            self._search_client = SearchClient(
                endpoint=settings.AZURE_SEARCH_ENDPOINT,
                index_name=settings.AZURE_SEARCH_INDEX_NAME,
                credential=AzureKeyCredential(settings.AZURE_SEARCH_KEY)
            )
        
        # Prepare documents for indexing
        documents = []
        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            doc = {
                "id": f"{document_id}_{i}",  # Unique ID per chunk
                "document_id": document_id,
                "firm_id": firm_id,
                "file_name": filename,
                "chunk_number": i,
                "chunk_text": chunk,
                "embedding_vector": embedding,
                "chunk_created_at": datetime.utcnow().isoformat(),
            }
            documents.append(doc)
        
        # Index documents (to Azure AI Search)
        result = await asyncio.to_thread(
            lambda: self._search_client.upload_documents(documents)
        )
        
        logger.info(f"Indexed {len(documents)} chunks for document {document_id}")
        return True
        
    except AzureError as e:
        logger.error(f"Azure Search error: {str(e)}")
        raise Exception(f"Failed to index in search: {str(e)}")
    except Exception as e:
        logger.error(f"Indexing error: {str(e)}")
        raise
```

### Create Index (One-time Setup)

Run this once to create the search index:

```python
from azure.search.documents.indexes.models import (
    SearchIndex, SearchField, SearchFieldDataType,
    VectorSearch, HnswAlgorithmConfiguration, VectorSearchProfile
)

# Call this in a one-time setup script or management endpoint
async def create_search_index(self):
    """Create search index with vector search support"""
    try:
        index_client = SearchIndexClient(
            endpoint=settings.AZURE_SEARCH_ENDPOINT,
            credential=AzureKeyCredential(settings.AZURE_SEARCH_KEY)
        )
        
        fields = [
            SimpleField(name="id", type=SearchFieldDataType.String, key=True),
            SearchableField(name="chunk_text", type=SearchFieldDataType.String),
            SimpleField(name="document_id", type=SearchFieldDataType.String),
            SimpleField(name="firm_id", type=SearchFieldDataType.String, filterable=True),
            SimpleField(name="file_name", type=SearchFieldDataType.String),
            SimpleField(name="chunk_number", type=SearchFieldDataType.Int32),
            SimpleField(name="embedding_vector", type=SearchFieldDataType.Collection(SearchFieldDataType.Single), 
                       searchable=True, vector_search_dimensions=1536),
            SimpleField(name="chunk_created_at", type=SearchFieldDataType.DateTimeOffset),
        ]
        
        vector_search = VectorSearch(
            algorithms=[HnswAlgorithmConfiguration(name="hnsw")],
            profiles=[VectorSearchProfile(name="myHnswProfile", algorithm_configuration_name="hnsw")]
        )
        
        index = SearchIndex(
            name=settings.AZURE_SEARCH_INDEX_NAME,
            fields=fields,
            vector_search=vector_search
        )
        
        result = index_client.create_or_update_index(index)
        logger.info(f"Created/Updated search index: {result.name}")
        return True
        
    except AzureError as e:
        logger.error(f"Failed to create index: {str(e)}")
        raise
```

### Configuration in config.py

Add to Settings class:
```python
AZURE_SEARCH_ENDPOINT: str = Field(default="", env="AZURE_SEARCH_ENDPOINT")
AZURE_SEARCH_KEY: str = Field(default="", env="AZURE_SEARCH_KEY")
AZURE_SEARCH_INDEX_NAME: str = Field(default="documents", env="AZURE_SEARCH_INDEX_NAME")
```

---

## Integration Steps

1. **Update requirements.txt** if needed (already done):
   - azure-ai-documentintelligence
   - All others already present

2. **Update config.py** with new settings:
   ```python
   # Add to backend/core/config.py Settings class
   BLOB_CONNECTION_STRING: str
   BLOB_CONTAINER_NAME: str
   DOCUMENT_INTELLIGENCE_ENDPOINT: str
   DOCUMENT_INTELLIGENCE_API_KEY: str
   AZURE_SEARCH_ENDPOINT: str
   AZURE_SEARCH_KEY: str
   AZURE_SEARCH_INDEX_NAME: str
   ```

3. **Update .env** with Azure credentials:
   ```bash
   cp .env.example .env
   # Edit .env with your credentials
   ```

4. **Update DocumentService** in backend/services/document_service.py:
   - Replace mock implementations with real Azure SDK calls
   - Update __init__ to initialize clients
   - Add error handling as shown above

5. **Create Search Index** (one-time):
   ```python
   # Run setup script to create index
   python -c "from backend.services.document_service import DocumentService; import asyncio; asyncio.run(DocumentService().create_search_index())"
   ```

6. **Test the pipeline**:
   ```bash
   # Upload a document
   curl -X POST http://localhost:8000/api/v1/documents/upload -F "file=@sample.pdf"
   
   # Monitor Celery worker
   celery -A celery_app worker -Q documents -l info
   ```

---

## Error Handling Patterns

### AzureError Handling

```python
from azure.core.exceptions import AzureError, ResourceNotFoundError, ResourceExistsError

try:
    # Azure operation
except ResourceNotFoundError:
    # Resource doesn't exist — might be transient, retry
    raise Exception("Resource temporarily unavailable")
except ResourceExistsError:
    # Resource already exists — probably OK, continue
    pass
except AzureError as e:
    # Generic Azure error — transient, will retry
    raise Exception(f"Azure service error: {str(e)}")
```

### Rate Limiting

From CLAUDE.md:
- Retry on RateLimitError: 3x with backoff (1s, 2s, 4s)
- Already configured in Celery task with autoretry_for

### Token Limits

```python
# Check if text is too large before embedding
max_tokens_per_chunk = 8000
if len(text) > max_tokens_per_chunk * TOKEN_ESTIMATE_RATIO:
    raise Exception("Document too large for processing. Please split into smaller files.")
```

---

## Deployment Checklist

- [ ] All Azure services created and accessible
- [ ] All credentials in .env (never commit to git)
- [ ] requirements.txt updated
- [ ] config.py updated with new Settings
- [ ] Search index created
- [ ] Real Azure SDK implementations added to DocumentService
- [ ] Celery worker running with documents queue
- [ ] FastAPI server running
- [ ] Test upload and monitoring working
- [ ] Error handling tested (delete blob, disable service, etc.)
- [ ] Performance benchmarked (chunk creation, embedding, indexing)

---

Last updated: April 2026
"""
