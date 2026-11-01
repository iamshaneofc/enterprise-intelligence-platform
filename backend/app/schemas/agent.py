"""Autonomous Agent schemas."""
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, ConfigDict


class AgentInvestigateRequest(BaseModel):
    task: str = Field(min_length=3)
    workspace_id: str
    conversation_id: Optional[str] = None
    max_steps: Optional[int] = Field(default=5, ge=1, le=10)


class ToolExecutionResponse(BaseModel):
    id: str
    step_number: int
    tool_name: str
    tool_input: Dict[str, Any]
    tool_output: Dict[str, Any]
    status: str
    execution_time_ms: int
    error_message: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AgentRunResponse(BaseModel):
    id: str
    workspace_id: str
    task: str
    status: str
    plan: List[Any] = Field(default_factory=list)
    final_output: Optional[str] = None
    tool_executions: List[ToolExecutionResponse] = Field(default_factory=list)
    total_steps: int
    execution_time_ms: Optional[int] = None
    created_at: datetime
    completed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
