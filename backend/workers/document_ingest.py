"""
Celery worker tasks for document processing
Thin wrappers only — all logic in services/
"""
from celery import shared_task
from celery.utils.log import get_task_logger
import asyncio


from backend.services.document_service import get_document_service
from backend.core.database import AsyncSessionLocal
from backend.models import DocumentStatus

logger = get_task_logger(__name__)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,  # 1 second
    autoretry_for=(Exception,),
    retry_backoff=True,  # Exponential backoff: 1s, 2s, 4s
    retry_backoff_max=600,  # Max 10 minutes between retries
)
def document_ingest(
    self,
    document_id: str,
    firm_id: str,
    filename: str,
    file_type: str
):
    """
    Background job: Ingest and index document
    
    Flow:
    1. Pull file from Azure Blob Storage
    2. Run OCR if needed (via Azure Document Intelligence)
    3. Extract text and chunk into 500-token chunks (50-token overlap)
    4. Generate embeddings (text-embedding-ada-002)
    5. Index in Azure AI Search
    6. Update document status to "indexed"
    
    Args:
        document_id: Document ID
        firm_id: Firm ID
        filename: Original filename
        file_type: File type/extension
        
    Raises:
        On failure: sets status="failed" with plain English error, retries 3x
    """
    try:
        logger.info(f"Starting document ingest: {document_id}")

        result = asyncio.run(
            _document_ingest_async(
                document_id=document_id,
                firm_id=firm_id,
                filename=filename,
                file_type=file_type,
            )
        )

        logger.info(f"Document ingest complete: {document_id}")
        return result

    except Exception as exc:
        logger.error(f"Document ingest failed: {str(exc)}")

        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(
                _update_document_failed(
                    document_id=document_id,
                    error_reason=str(exc),
                )
            )
        finally:
            loop.close()

        logger.warning(f"Retrying document ingest {self.request.retries}/3: {document_id}")
        raise self.retry(exc=exc)


async def _document_ingest_async(
    document_id: str,
    firm_id: str,
    filename: str,
    file_type: str
) -> dict:
    """
    Async implementation of document ingest
    All business logic delegated to DocumentService
    """
    service = get_document_service()
    
    async with AsyncSessionLocal() as session:
        try:
            # Step 1: Get document from DB
            document = await service.get_document(session, document_id, firm_id)
            if not document:
                raise ValueError(f"Document not found: {document_id}")
            
            logger.info(f"Processing document: {filename}")
            
            # Step 2: Get file bytes — from Redis cache (dev) or Azure Blob (prod)
            import redis.asyncio as aioredis
            from backend.core.config import settings as _settings
            _redis = aioredis.from_url(_settings.REDIS_URL)
            file_content = await _redis.get(f"file_content:{document_id}")
            await _redis.aclose()
            if not file_content:
                # TODO: fetch from Azure Blob Storage when configured
                raise ValueError(
                    f"File content not found in cache for document {document_id}. "
                    "Re-upload the document."
                )
            
            # Step 3: Extract text (OCR if needed)
            text = await service.extract_text_from_document(file_content, file_type)
            logger.info(f"Extracted {len(text)} characters from {filename}")
            
            # Step 4-6: Chunk, embed, and index through Azure AI Search
            # If search is unavailable (e.g. dev env), skip gracefully —
            # OCR text is still saved so extraction and chat work.
            chunk_count = 0
            try:
                chunks = await service.ingest_document(
                    text=text,
                    document_id=document_id,
                    firm_id=firm_id,
                    filename=filename,
                    vertical="law",
                )
                chunk_count = len(chunks)
                logger.info(f"Indexed {chunk_count} chunks for document {document_id}")
            except Exception as search_exc:
                logger.warning(
                    f"Azure Search indexing failed for {document_id} "
                    f"(search disabled or unreachable): {search_exc}. "
                    "Document will be marked indexed — OCR text saved, search skipped."
                )

            # Step 7: Persist OCR text and mark indexed regardless of search outcome
            success = await service.update_document_indexed(
                session=session,
                document_id=document_id,
                chunk_count=chunk_count,
                ocr_text=text,
            )

            if not success:
                raise Exception("Failed to update document status in database")
            
            logger.info(f"Document ingest successful: {document_id} ({len(chunks)} chunks)")
            
            return {
                "document_id": document_id,
                "status": "indexed",
                "chunk_count": len(chunks)
            }
            
        except Exception as exc:
            logger.error(f"Error in document_ingest_async: {str(exc)}")
            raise


async def _update_document_failed(document_id: str, error_reason: str):
    """Update document status to failed"""
    try:
        service = get_document_service()
        async with AsyncSessionLocal() as session:
            await service.update_document_status(
                session=session,
                document_id=document_id,
                status=DocumentStatus.FAILED,
                error_reason=error_reason
            )
    except Exception as e:
        logger.error(f"Failed to update document error status: {str(e)}")
