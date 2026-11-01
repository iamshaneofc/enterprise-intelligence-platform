"""Chat and Search endpoints for knowledge retrieval and RAG."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.db.session import get_db
from backend.app.models.user import User
from backend.app.api.dependencies import get_current_user, verify_workspace_access
from backend.app.services.rag_service import rag_service
from backend.app.schemas.chat import (
    SearchRequest,
    SearchResponse,
    ChatRequest,
    ChatResponse,
)

router = APIRouter(prefix="/workspaces/{workspace_id}", tags=["Retrieval & Chat"])


@router.post("/search", response_model=SearchResponse)
def search_documents(
    workspace_id: str,
    req: SearchRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Execute hybrid, dense, or sparse search across technical documents in the workspace."""
    verify_workspace_access(workspace_id, current_user, db)
    return rag_service.search(
        query=req.query,
        workspace_id=workspace_id,
        top_k=req.top_k,
        mode=req.mode,
        db=db,
    )


@router.post("/chat", response_model=ChatResponse)
def chat_with_documents(
    workspace_id: str,
    req: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Generate source-grounded answers with citations, abstention detection, and anti-hallucination guard."""
    verify_workspace_access(workspace_id, current_user, db)
    return rag_service.generate_rag_response(
        query=req.query,
        workspace_id=workspace_id,
        user_id=current_user.id,
        conversation_id=req.conversation_id,
        top_k=req.top_k,
        db=db,
    )

