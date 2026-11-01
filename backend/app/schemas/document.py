"""Document schemas."""
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, ConfigDict


class DocumentResponse(BaseModel):
    id: str
    workspace_id: str
    title: str
    filename: str
    file_size_bytes: int
    file_type: str
    file_hash: str
    status: str
    chunk_count: int
    error_message: Optional[str] = None
    doc_metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DocumentUploadResponse(BaseModel):
    message: str
    document: DocumentResponse


class ChunkResponse(BaseModel):
    id: str
    document_id: str
    chunk_index: int
    content: str
    chunk_metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
