"""Conversational session management endpoints."""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from backend.app.db.session import get_db
from backend.app.models.user import User
from backend.app.models.conversation import Conversation, Message, Citation
from backend.app.api.dependencies import get_current_user, verify_workspace_access
from backend.app.schemas.chat import ConversationResponse, MessageResponse, CitationResponse

router = APIRouter(prefix="/workspaces/{workspace_id}/conversations", tags=["Conversations"])


def _build_conversation_response(conv: Conversation) -> ConversationResponse:
    """Build a ConversationResponse from a Conversation ORM object with messages and citations."""
    messages_out = []
    for msg in conv.messages:
        cits = [
            CitationResponse(
                marker=c.citation_marker,
                document_id=c.document_id,
                document_title="Indexed Source",
                chunk_id=c.chunk_id,
                snippet=c.snippet,
                score=c.score,
            )
            for c in msg.citations
        ]
        messages_out.append(
            MessageResponse(
                id=msg.id,
                role=msg.role,
                content=msg.content,
                citations=cits,
                created_at=msg.created_at,
            )
        )

    return ConversationResponse(
        id=conv.id,
        workspace_id=conv.workspace_id,
        title=conv.title,
        summary=conv.summary,
        messages=messages_out,
        created_at=conv.created_at,
        updated_at=conv.updated_at,
    )


@router.get("", response_model=List[ConversationResponse])
def list_conversations(
    workspace_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all active conversations in workspace."""
    verify_workspace_access(workspace_id, current_user, db)
    conversations = db.query(Conversation).options(
        joinedload(Conversation.messages).joinedload(Message.citations)
    ).filter(
        Conversation.workspace_id == workspace_id,
        Conversation.user_id == current_user.id,
    ).order_by(Conversation.updated_at.desc()).all()
    
    return [_build_conversation_response(conv) for conv in conversations]


@router.get("/{conversation_id}", response_model=ConversationResponse)
def get_conversation(
    workspace_id: str,
    conversation_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve full conversation details with message history and citations."""
    verify_workspace_access(workspace_id, current_user, db)
    conv = db.query(Conversation).options(
        joinedload(Conversation.messages).joinedload(Message.citations)
    ).filter(
        Conversation.id == conversation_id,
        Conversation.workspace_id == workspace_id,
        Conversation.user_id == current_user.id,
    ).first()
    if not conv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")

    return _build_conversation_response(conv)


@router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_conversation(
    workspace_id: str,
    conversation_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a conversation and its messages."""
    verify_workspace_access(workspace_id, current_user, db)
    conv = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.workspace_id == workspace_id,
        Conversation.user_id == current_user.id,
    ).first()
    if not conv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    
    db.delete(conv)
    db.commit()
    return None

