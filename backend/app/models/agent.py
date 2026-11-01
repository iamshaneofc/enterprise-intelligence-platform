"""Agent Run and Agent Tool Execution database models."""
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship

from backend.app.db.session import Base


class AgentRun(Base):
    __tablename__ = "agent_runs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    workspace_id = Column(String(36), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    conversation_id = Column(String(36), ForeignKey("conversations.id", ondelete="SET NULL"), nullable=True, index=True)
    task = Column(Text, nullable=False)
    status = Column(String(50), default="queued", nullable=False)  # queued, running, completed, failed
    plan = Column(JSON, default=list, nullable=False)
    final_output = Column(Text, nullable=True)
    total_steps = Column(Integer, default=0, nullable=False)
    execution_time_ms = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    completed_at = Column(DateTime, nullable=True)

    tool_executions = relationship("AgentToolExecution", back_populates="agent_run", cascade="all, delete-orphan", order_by="AgentToolExecution.step_number")


class AgentToolExecution(Base):
    __tablename__ = "agent_tool_executions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    agent_run_id = Column(String(36), ForeignKey("agent_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    step_number = Column(Integer, nullable=False)
    tool_name = Column(String(100), nullable=False)
    tool_input = Column(JSON, default=dict, nullable=False)
    tool_output = Column(JSON, default=dict, nullable=False)
    status = Column(String(50), default="success", nullable=False)  # success, error
    execution_time_ms = Column(Integer, default=0, nullable=False)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    agent_run = relationship("AgentRun", back_populates="tool_executions")

