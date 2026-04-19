"""
Document API endpoints
"""
import uuid
from typing import Optional

from fastapi import APIRouter, UploadFile, File, Depends, Form, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.config import settings
from backend.core.database import get_session
from backend.core.logger import get_logger
from backend.core.dependencies import CurrentUser, get_current_user
from backend.core.rbac import require_permission
from backend.schemas.document import (
    DocumentUploadResponse,
    DocumentResponse,
    DocumentListResponse,
    DocumentErrorResponse,
)
from backend.services.document_service import get_document_service
from backend.workers.document_ingest import document_ingest as document_ingest_task

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/documents", tags=["documents"])


@router.post("/upload", response_model=DocumentUploadResponse, status_code=status.HTTP_202_ACCEPTED)
async def upload_document(
    file: UploadFile = File(...),
    matter_id: Optional[str] = Form(None),
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Upload a document for processing

    Flow:
    1. Validate file type and size
    2. Save to Azure Blob Storage
    3. Create document record with status="pending"
    4. Enqueue background job
    5. Return immediately with document_id

    Args:
        file: File to upload (PDF, DOCX, images)
        matter_id: Optional matter ID to associate document
        current_user: Authenticated user (injected from JWT)
        session: Database session (injected)

    Returns:
        DocumentUploadResponse with document info and status="pending"

    Note:
        Returns 202 ACCEPTED because processing is asynchronous
        Check document status later to see if indexing completed
    """
    try:
        firm_id = current_user.firm_id
        user_id = current_user.user_id

        logger.info(f"Document upload started: {file.filename}")

        service = get_document_service()

        # Step 1: Validate upload
        is_valid, error_msg = await service.validate_upload(
            filename=file.filename,
            file_size=file.size if file.size else 0
        )

        if not is_valid:
            logger.warning(f"Upload validation failed: {error_msg}")
            return DocumentUploadResponse(
                success=False,
                data=None,
                error={"code": "validation_failed", "message": error_msg, "action": "retry"},
                meta={"request_id": str(uuid.uuid4())}
            )
        
        # Read file content
        file_content = await file.read()

        # Step 2: Save to Azure Blob Storage
        try:
            blob_path = await service.save_to_blob_storage(
                file_content=file_content,
                filename=file.filename,
                firm_id=firm_id,
                file_type=file.filename.rsplit('.', 1)[-1] if '.' in file.filename else ''
            )
        except Exception as e:
            error_msg = f"Failed to save to storage: {str(e)}"
            logger.error(error_msg)
            return DocumentUploadResponse(
                success=False,
                data=None,
                error={"code": "storage_error", "message": error_msg, "action": "retry"},
                meta={"request_id": str(uuid.uuid4())}
            )
        
        # Step 3: Create document record in DB
        try:
            document = await service.store_document_in_db(
                session=session,
                firm_id=firm_id,
                matter_id=matter_id,
                filename=file.filename,
                file_type=file.filename.rsplit('.', 1)[-1] if '.' in file.filename else '',
                file_size_bytes=len(file_content),
                blob_path=blob_path,
                user_id=user_id
            )
        except Exception as e:
            error_msg = f"Failed to store document: {str(e)}"
            logger.error(error_msg)
            return DocumentUploadResponse(
                success=False,
                data=None,
                error={"code": "database_error", "message": error_msg, "action": "contact_support"},
                meta={"request_id": str(uuid.uuid4())}
            )
        
        # Cache raw file bytes in Redis so the Celery worker can retrieve them
        # before Azure Blob Storage is configured. Keyed by document ID. TTL: 1 hour.
        try:
            import redis.asyncio as aioredis
            _redis = aioredis.from_url(settings.REDIS_URL)
            await _redis.setex(f"file_content:{document.id}", 3600, file_content)
            await _redis.aclose()
        except Exception as e:
            logger.warning(f"Failed to cache file in Redis: {e}")

        # Step 4: Enqueue background job
        try:
            task = document_ingest_task.delay(
                document_id=str(document.id),
                firm_id=firm_id,
                filename=file.filename,
                file_type=file.filename.rsplit('.', 1)[-1] if '.' in file.filename else ''
            )
            logger.info(f"Enqueued document_ingest task: {task.id} for document {document.id}")
        except Exception as e:
            error_msg = f"Failed to enqueue processing: {str(e)}"
            logger.error(error_msg)
            # Don't fail the upload, just log the error
            # User can retry processing later
        
        # Step 5: Return immediately
        document_response = DocumentResponse(
            id=str(document.id),
            file_name=document.file_name,
            file_type=document.file_type,
            file_size_bytes=document.file_size_bytes,
            status=document.status.value,
            error_reason=document.error_reason,
            chunk_count=document.chunk_count,
            created_at=document.created_at,
            indexed_at=document.indexed_at
        )
        
        logger.info(f"Document upload successful: {document.id} (status=pending, processing in background)")
        
        return DocumentUploadResponse(
            success=True,
            data=document_response,
            meta={
                "request_id": str(uuid.uuid4()),
                "message": "Document received and queued for processing. Check status later."
            }
        )
        
    except Exception as e:
        error_msg = f"Unexpected error during upload: {str(e)}"
        logger.error(error_msg)
        return DocumentUploadResponse(
            success=False,
            data=None,
            error={"code": "server_error", "message": error_msg, "action": "contact_support"},
            meta={" ": str(uuid.uuid4())}
        )


@router.get("/{document_id}", response_model=DocumentUploadResponse)
async def get_document(
    document_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Get document status and details

    Args:
        document_id: Document ID
        current_user: Authenticated user (injected from JWT)
        session: Database session (injected)

    Returns:
        DocumentUploadResponse with current document info
    """
    try:
        service = get_document_service()
        document = await service.get_document(session, document_id, current_user.firm_id)
        
        if not document:
            return DocumentUploadResponse(
                success=False,
                data=None,
                error={"code": "not_found", "message": "Document not found", "action": "check_id"},
                meta={"request_id": str(uuid.uuid4())}
            )
        
        document_response = DocumentResponse(
            id=str(document.id),
            file_name=document.file_name,
            file_type=document.file_type,
            file_size_bytes=document.file_size_bytes,
            status=document.status.value,
            error_reason=document.error_reason,
            chunk_count=document.chunk_count,
            created_at=document.created_at,
            indexed_at=document.indexed_at
        )
        
        return DocumentUploadResponse(
            success=True,
            data=document_response,
            meta={"request_id": str(uuid.uuid4())}
        )
        
    except Exception as e:
        logger.error(f"Error getting document: {str(e)}")
        return DocumentUploadResponse(
            success=False,
            data=None,
            error={"code": "server_error", "message": str(e), "action": "retry"},
            meta={"request_id": str(uuid.uuid4())}
        )


@router.delete("/{document_id}")
@require_permission("delete_documents")
async def delete_document(
    document_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Soft delete a document and remove from search index

    Args:
        document_id: Document ID to delete
        current_user: Authenticated user (must be firm_admin or lawyer)
        session: Database session

    Returns:
        Success response or error

    Permissions:
        - firm_admin: Can delete any document in their firm
        - lawyer: Can delete any document in their firm
        - staff: Cannot delete documents
    """
    try:
        service = get_document_service()
        success = await service.delete_document(session, document_id, current_user.firm_id)

        if not success:
            return DocumentUploadResponse(
                success=False,
                data=None,
                error={"code": "delete_failed", "message": "Failed to delete document", "action": "retry"},
                meta={"request_id": str(uuid.uuid4())}
            )

        return DocumentUploadResponse(
            success=True,
            data={"document_id": document_id, "deleted": True},
            meta={"request_id": str(uuid.uuid4()), "message": "Document deleted successfully"}
        )

    except ValueError as e:
        # Document not found or doesn't belong to firm
        return DocumentUploadResponse(
            success=False,
            data=None,
            error={"code": "not_found", "message": str(e), "action": "check_id"},
            meta={"request_id": str(uuid.uuid4())}
        )
    except Exception as e:
        logger.error(f"Error deleting document: {str(e)}")
        return DocumentUploadResponse(
            success=False,
            data=None,
            error={"code": "server_error", "message": str(e), "action": "contact_support"},
            meta={"request_id": str(uuid.uuid4())}
        )
