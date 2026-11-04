"""Evaluation API endpoints."""
import os
from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.app.core.config import settings
from backend.app.db.session import get_db
from backend.app.models.user import User
from backend.app.api.dependencies import get_current_user, verify_workspace_access
from backend.evaluation.runner import run_evaluation, EvaluationConfig

router = APIRouter(prefix="/workspaces/{workspace_id}/evaluation", tags=["Evaluation"])


class EvaluationRequest(BaseModel):
    """Request to trigger an evaluation run."""
    dataset_path: Optional[str] = Field(default=None, description="Path to evaluation dataset (defaults to golden dataset)")
    top_k: int = Field(default=5, ge=1, le=20, description="Number of retrieval results per question")
    use_fake_llm: bool = Field(default=False, description="Use fake LLM provider for deterministic results (disabled in production)")
    use_fake_embeddings: bool = Field(default=False, description="Use fake embedding provider for deterministic results (disabled in production)")
    output_path: Optional[str] = Field(default=None, description="Optional path to save results")


class EvaluationStatusResponse(BaseModel):
    """Status of an evaluation run."""
    status: str
    message: Optional[str] = None
    results: Optional[dict] = None


@router.post("/run", response_model=EvaluationStatusResponse, status_code=status.HTTP_202_ACCEPTED)
async def run_evaluation_endpoint(
    workspace_id: str,
    request: EvaluationRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Trigger an evaluation run.
    
    This endpoint starts the evaluation in the background and returns immediately.
    The evaluation results will be available via the status endpoint.
    """
    verify_workspace_access(workspace_id, current_user, db)
    
    # For now, run synchronously since background tasks with DB sessions are tricky
    # In production, this would use a proper task queue
    config = EvaluationConfig(
        dataset_path=request.dataset_path or "backend/tests/fixtures/golden_evaluation_dataset.jsonl",
        use_fake_llm=request.use_fake_llm,
        use_fake_embeddings=request.use_fake_embeddings,
        top_k=request.top_k,
        output_path=request.output_path,
    )
    
    try:
        result = run_evaluation(
            dataset_path=config.dataset_path,
            use_fake_llm=config.use_fake_llm,
            use_fake_embeddings=config.use_fake_embeddings,
            top_k=config.top_k,
            output_path=config.output_path,
        )
        
        # Extract key metrics for response
        aggregate = result.get("aggregate_metrics", {})
        
        return EvaluationStatusResponse(
            status="completed",
            message="Evaluation completed successfully",
            results=result
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Evaluation failed: {str(e)}"
        )


@router.get("/provider-status")
async def get_provider_status(
    workspace_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Inspect the current runtime LLM and Embedding provider state."""
    verify_workspace_access(workspace_id, current_user, db)
    return {
        "use_fake_llm": settings.USE_FAKE_LLM,
        "use_fake_embeddings": settings.USE_FAKE_EMBEDDINGS,
        "env_use_fake_llm": os.environ.get("USE_FAKE_LLM"),
        "env_use_fake_embeddings": os.environ.get("USE_FAKE_EMBEDDINGS"),
        "primary_llm_provider": settings.PRIMARY_LLM_PROVIDER,
        "primary_llm_model": settings.PRIMARY_LLM_MODEL,
        "environment": settings.ENVIRONMENT,
    }


@router.post("/reset-providers")
async def reset_providers(
    workspace_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Administrative reset: restore real LLM and Embedding providers in process memory."""
    verify_workspace_access(workspace_id, current_user, db)
    settings.USE_FAKE_LLM = False
    settings.USE_FAKE_EMBEDDINGS = False
    os.environ["USE_FAKE_LLM"] = "false"
    os.environ["USE_FAKE_EMBEDDINGS"] = "false"
    return {
        "status": "success",
        "message": "Runtime providers successfully restored to production mode (real LLM and embeddings).",
        "use_fake_llm": settings.USE_FAKE_LLM,
        "use_fake_embeddings": settings.USE_FAKE_EMBEDDINGS,
    }


@router.get("/results", response_model=EvaluationStatusResponse)
async def get_latest_evaluation_results(
    workspace_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get the latest evaluation results for this workspace.
    
    This is a placeholder - in production, evaluation results would be stored
    and retrieved from a database.
    """
    verify_workspace_access(workspace_id, current_user, db)
    
    return EvaluationStatusResponse(
        status="not_available",
        message="Evaluation results storage not yet implemented. Use POST /run to execute a new evaluation.",
        results=None
    )