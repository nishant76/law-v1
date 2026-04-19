"""
Document model — uploaded case files for RAG
"""
import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import String, UUID, ForeignKey, DateTime, Text, Integer, Boolean, Enum, Index
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
import enum
from .base import BaseModel


class DocumentStatus(str, enum.Enum):
    """Document processing status"""
    PENDING = "pending"
    PROCESSING = "processing"
    INDEXED = "indexed"
    FAILED = "failed"


class Document(BaseModel):
    """Uploaded document for indexing and RAG"""
    __tablename__ = "documents"
    __table_args__ = (
        Index("ix_documents_deleted_at", "deleted_at"),
        Index("ix_documents_firm_id", "firm_id"),
        Index("ix_documents_matter_id", "matter_id"),
        Index("ix_documents_status", "status"),
        {"schema": "law"},
    )

    firm_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("law.firms.id"), nullable=False)
    matter_id: Mapped[Optional[UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("law.matters.id"), nullable=True)

    # File information
    file_name: Mapped[str] = mapped_column(String(500), nullable=False)
    file_type: Mapped[str] = mapped_column(String(50), nullable=False)  # pdf, docx, image, etc.
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)

    # Azure Blob Storage
    blob_path: Mapped[str] = mapped_column(String(500), nullable=False)  # path in azure blob storage
    blob_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)  # signed URL for retrieval

    # Processing
    status: Mapped[DocumentStatus] = mapped_column(Enum(DocumentStatus, values_callable=lambda x: [e.value for e in x]), default=DocumentStatus.PENDING, nullable=False, index=True)
    error_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # Plain English error message

    # OCR and indexing
    ocr_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # Full extracted text from OCR
    chunk_count: Mapped[int] = mapped_column(Integer, default=0)  # Number of chunks in Azure AI Search

    # Azure AI Search
    search_index_name: Mapped[str] = mapped_column(String(100), default="law-documents")

    # Metadata
    uploaded_by_user_id: Mapped[Optional[UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("law.users.id"), nullable=True)
    upload_source: Mapped[str] = mapped_column(String(50), default="web")  # web, google_drive, etc.

    # Timestamps
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    indexed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    def __repr__(self) -> str:
        return f"<Document(id={self.id}, file_name={self.file_name}, status={self.status})>"
