"""Document management and upload endpoints."""
import os
from typing import List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from backend.app.db.session import get_db
from backend.app.models.user import User
from backend.app.api.dependencies import get_current_user, verify_workspace_access
from backend.app.services.document_service import document_service
from backend.app.schemas.document import DocumentResponse, DocumentUploadResponse, ChunkResponse
from backend.app.core.config import settings

router = APIRouter(prefix="/workspaces/{workspace_id}/documents", tags=["Documents"])


@router.post("/upload", response_model=DocumentUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    workspace_id: str,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Upload and ingest a technical document (PDF, Markdown, TXT, CSV, JSON)."""
    verify_workspace_access(workspace_id, current_user, db)
    
    # Additional content-type validation
    allowed_types = {
        "application/pdf",
        "text/plain",
        "text/markdown",
        "text/csv",
        "application/json",
    }
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported content type: {file.content_type}. Allowed: {', '.join(allowed_types)}"
        )
    
    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file is empty")

    # Double-check file size (FastAPI may not catch all cases)
    if len(file_bytes) > settings.MAX_UPLOAD_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File size exceeds maximum allowed limit of {settings.MAX_UPLOAD_SIZE_BYTES // (1024 * 1024)} MB"
        )

    doc = document_service.upload_and_process(
        workspace_id=workspace_id,
        user_id=current_user.id,
        filename=file.filename or "uploaded_document",
        content=file_bytes,
        db=db,
    )
    return DocumentUploadResponse(
        message="Document uploaded and indexed successfully",
        document=doc,
    )


@router.get("", response_model=List[DocumentResponse])
def list_documents(
    workspace_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all documents indexed in the given workspace."""
    verify_workspace_access(workspace_id, current_user, db)
    return document_service.list_workspace_documents(workspace_id, db)


@router.get("/{document_id}", response_model=DocumentResponse)
def get_document(
    workspace_id: str,
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve document details and status by ID."""
    verify_workspace_access(workspace_id, current_user, db)
    return document_service.get_document(document_id, db)


@router.get("/{document_id}/chunks", response_model=List[ChunkResponse])
def get_document_chunks(
    workspace_id: str,
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve all chunks and structural metadata generated for a document."""
    verify_workspace_access(workspace_id, current_user, db)
    # Ensure document belongs to workspace
    doc = document_service.get_document(document_id, db)
    if doc.workspace_id != workspace_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found in workspace")
    return document_service.get_document_chunks(document_id, db)


@router.get("/{document_id}/download")
def download_document(
    workspace_id: str,
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Download the original uploaded document file."""
    verify_workspace_access(workspace_id, current_user, db)
    doc = document_service.get_document(document_id, db)
    if doc.workspace_id != workspace_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found in workspace")

    file_path = doc.file_path
    if not file_path or not os.path.exists(file_path):
        # Fallback check relative to settings.STORAGE_DIR
        candidate = os.path.join(settings.STORAGE_DIR, workspace_id, os.path.basename(file_path or doc.filename))
        if os.path.exists(candidate):
            file_path = candidate
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Original document file not found on disk at {doc.file_path}"
            )

    ext = os.path.splitext(doc.filename)[1].lower()
    media_types = {
        ".pdf": "application/pdf",
        ".md": "text/markdown",
        ".txt": "text/plain",
        ".csv": "text/csv",
        ".json": "application/json",
    }
    media_type = media_types.get(ext, "application/octet-stream")

    return FileResponse(
        path=file_path,
        filename=doc.filename,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{doc.filename}"'},
    )


@router.post("/{document_id}/reindex", response_model=DocumentResponse)
def reindex_document(
    workspace_id: str,
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Re-parse, re-chunk, and re-embed an existing document using the configured embedding provider."""
    verify_workspace_access(workspace_id, current_user, db)
    doc = document_service.get_document(document_id, db)
    if doc.workspace_id != workspace_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found in workspace")
    return document_service.reindex_document(document_id, db)


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(
    workspace_id: str,
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a document and all associated chunks."""
    verify_workspace_access(workspace_id, current_user, db)
    doc = document_service.get_document(document_id, db)
    if doc.workspace_id != workspace_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found in workspace")
    document_service.delete_document(document_id, db)
    return None

