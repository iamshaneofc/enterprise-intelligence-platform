"""Autonomous Agent endpoints."""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.db.session import get_db
from backend.app.models.user import User
from backend.app.models.agent import AgentRun, AgentToolExecution
from backend.app.api.dependencies import get_current_user, verify_workspace_access
from backend.app.agents.orchestrator import agent_orchestrator
from backend.app.schemas.agent import (
    AgentInvestigateRequest,
    AgentRunResponse,
    ToolExecutionResponse,
)

router = APIRouter(prefix="/workspaces/{workspace_id}/agent", tags=["Autonomous Agents"])


@router.post("/investigate", response_model=AgentRunResponse, status_code=status.HTTP_201_CREATED)
def trigger_agent_investigation(
    workspace_id: str,
    req: AgentInvestigateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Launch autonomous multi-step technical investigation with search, analysis, and report generation."""
    verify_workspace_access(workspace_id, current_user, db)
    run = agent_orchestrator.run_investigation(
        task=req.task,
        workspace_id=workspace_id,
        user_id=current_user.id,
        conversation_id=req.conversation_id,
        max_steps=req.max_steps,
        db=db,
    )
    return run


@router.get("/runs", response_model=List[AgentRunResponse])
def list_agent_runs(
    workspace_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all autonomous agent runs for workspace owned by current user."""
    verify_workspace_access(workspace_id, current_user, db)
    return db.query(AgentRun).filter(
        AgentRun.workspace_id == workspace_id,
        AgentRun.user_id == current_user.id,
    ).order_by(AgentRun.created_at.desc()).all()


@router.get("/runs/{run_id}", response_model=AgentRunResponse)
def get_agent_run(
    workspace_id: str,
    run_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve details, execution traces, and report of an agent investigation."""
    verify_workspace_access(workspace_id, current_user, db)
    run = db.query(AgentRun).filter(
        AgentRun.id == run_id,
        AgentRun.workspace_id == workspace_id,
        AgentRun.user_id == current_user.id,
    ).first()
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent run not found")
    return run

