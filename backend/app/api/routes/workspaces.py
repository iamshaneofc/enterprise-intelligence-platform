"""Workspace management endpoints."""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import re

from backend.app.db.session import get_db
from backend.app.models.user import User
from backend.app.models.workspace import Workspace, WorkspaceMember
from backend.app.schemas.workspace import WorkspaceCreateRequest, WorkspaceResponse
from backend.app.api.dependencies import get_current_user

router = APIRouter(prefix="/workspaces", tags=["Workspaces"])


@router.post("", response_model=WorkspaceResponse, status_code=status.HTTP_201_CREATED)
def create_workspace(
    req: WorkspaceCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new workspace."""
    slug = req.slug
    if not slug:
        base = re.sub(r"[^a-zA-Z0-9]+", "-", req.name.lower()).strip("-")
        slug = f"{base}-{current_user.id[:6]}"
        
    existing = db.query(Workspace).filter(Workspace.slug == slug).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Workspace with slug '{slug}' already exists",
        )

    workspace = Workspace(
        name=req.name,
        slug=slug,
        description=req.description,
        owner_id=current_user.id,
    )
    db.add(workspace)
    db.flush()

    member = WorkspaceMember(
        workspace_id=workspace.id,
        user_id=current_user.id,
        role="admin",
    )
    db.add(member)
    db.commit()
    db.refresh(workspace)
    return workspace


@router.get("", response_model=List[WorkspaceResponse])
def list_workspaces(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all workspaces owned by or shared with current user."""
    # Find all workspace IDs where user is member or owner
    member_ws_ids = [m.workspace_id for m in db.query(WorkspaceMember).filter(WorkspaceMember.user_id == current_user.id).all()]
    workspaces = db.query(Workspace).filter(
        (Workspace.owner_id == current_user.id) | (Workspace.id.in_(member_ws_ids))
    ).all()
    return workspaces


@router.get("/{workspace_id}", response_model=WorkspaceResponse)
def get_workspace(
    workspace_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get single workspace by ID."""
    workspace = db.query(Workspace).filter(Workspace.id == workspace_id).first()
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found",
        )
    return workspace

