"""
Document request/response schemas (Pydantic v2)
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from enum import Enum


class DocumentStatusEnum(str, Enum):
    """Document processing status"""
    PENDING = "pending"
    PROCESSING = "processing"
    INDEXED = "indexed"
    FAILED = "failed"


class DocumentUploadRequest(BaseModel):
    """Document upload request"""
    matter_id: Optional[str] = Field(None, description="Optional matter ID to associate document")


class DocumentResponse(BaseModel):
    """Document response"""
    id: str
    file_name: str
    file_type: str
    file_size_bytes: int
    status: DocumentStatusEnum
    error_reason: Optional[str] = None
    chunk_count: int = 0
    created_at: datetime
    indexed_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class DocumentUploadResponse(BaseModel):
    """Immediate response after upload (before indexing)"""
    success: bool
    data: DocumentResponse
    meta: dict = Field(default_factory=dict)
    
    class Config:
        from_attributes = True


class DocumentListResponse(BaseModel):
    """List of documents"""
    success: bool
    data: list[DocumentResponse]
    meta: dict = Field(default_factory=dict)


class DocumentErrorResponse(BaseModel):
    """Error response"""
    success: bool = False
    error: dict
    meta: dict = Field(default_factory=dict)
