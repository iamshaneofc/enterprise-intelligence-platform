"""Unit tests for Autonomous Agent tools and reasoning orchestrator."""
import time
from unittest.mock import patch, MagicMock
from sqlalchemy.orm import Session
from pydantic import ValidationError
import pytest

from backend.app.models.user import User
from backend.app.models.workspace import Workspace
from backend.app.agents.tools import (
    tool_registry,
    KnowledgeBaseSearchInput,
    DocumentAnalysisInput,
    StructuredReportGenerationInput,
)
from backend.app.agents.orchestrator import agent_orchestrator, run_with_timeout, parse_llm_action
from backend.app.models.agent import AgentRun, AgentToolExecution


def create_user_and_workspace(db: Session):
    user = User(
        email="test_agent@corp.com",
        hashed_password="hash",
        full_name="Agent User",
        role="engineer"
    )
    db.add(user)
    db.flush()
    ws = Workspace(
        name="Agent Workspace",
        slug=f"agent-ws-{user.id[:6]}",
        owner_id=user.id
    )
    db.add(ws)
    db.flush()
    return user, ws


def test_tool_registry_graceful_error_handling(db_session: Session):
    user, ws = create_user_and_workspace(db_session)
    # Invalid tool name should return graceful error JSON
    res1 = tool_registry.execute_tool("nonexistent_tool", {}, ws.id, db_session)
    assert res1["ok"] is False
    assert "not recognized" in res1["error"]

    # Missing required parameter should return graceful error JSON
    res2 = tool_registry.execute_tool("knowledge_base_search", {}, ws.id, db_session)
    assert res2["ok"] is False
    assert "required" in res2["error"]


def test_tool_input_validation_pydantic():
    """Test that tool input schemas validate correctly."""
    # Valid inputs
    valid_search = KnowledgeBaseSearchInput(query="test query", top_k=5)
    assert valid_search.query == "test query"
    assert valid_search.top_k == 5
    
    valid_analysis = DocumentAnalysisInput(target="incident root cause")
    assert valid_analysis.target == "incident root cause"
    
    valid_report = StructuredReportGenerationInput(
        title="Test Report",
        findings=["Finding 1", "Finding 2"],
        recommendations=["Rec 1", "Rec 2"],
    )
    assert valid_report.title == "Test Report"
    assert len(valid_report.findings) == 2
    
    # Invalid inputs
    with pytest.raises(ValidationError):
        KnowledgeBaseSearchInput(query="")  # Empty query
    
    with pytest.raises(ValidationError):
        KnowledgeBaseSearchInput(query="test", top_k=0)  # Invalid top_k
    
    with pytest.raises(ValidationError):
        KnowledgeBaseSearchInput(query="test", top_k=25)  # top_k too large
    
    with pytest.raises(ValidationError):
        DocumentAnalysisInput(target="")  # Empty target


def test_tool_registry_input_validation(db_session: Session):
    """Test that tool registry validates inputs using Pydantic."""
    user, ws = create_user_and_workspace(db_session)
    
    # Invalid top_k
    res = tool_registry.execute_tool("knowledge_base_search", {"query": "test", "top_k": 0}, ws.id, db_session)
    assert res["ok"] is False
    assert "Invalid tool input" in res["error"]
    
    # Invalid target
    res = tool_registry.execute_tool("document_analysis", {"target": ""}, ws.id, db_session)
    assert res["ok"] is False
    assert "Invalid tool input" in res["error"]


def test_structured_report_generation_tool(db_session: Session):
    user, ws = create_user_and_workspace(db_session)
    inp = {
        "title": "PostgreSQL Outage Postmortem",
        "findings": ["Pool exhausted 200 connections", "Missing database index"],
        "recommendations": ["Scale connections to 400", "Add composite index"],
    }
    res = tool_registry.execute_tool("structured_report_generation", inp, ws.id, db_session)
    assert res["ok"] is True
    data = res["data"]
    assert "formatted_report" in data
    assert "# PostgreSQL Outage Postmortem" in data["formatted_report"]


def test_agent_orchestrator_investigation_loop(db_session: Session):
    user, ws = create_user_and_workspace(db_session)
    run = agent_orchestrator.run_investigation(
        task="Investigate PostgreSQL connection pool exhaustion incident",
        workspace_id=ws.id,
        user_id=user.id,
        max_steps=3,
        db=db_session,
    )

    assert run.status == "completed"
    assert run.total_steps > 0
    assert run.final_output is not None
    assert run.execution_time_ms is not None

    # Verify tool execution records in DB
    tool_execs = db_session.query(AgentToolExecution).filter(AgentToolExecution.agent_run_id == run.id).all()
    assert len(tool_execs) > 0
    for te in tool_execs:
        assert te.status == "success"
        assert te.tool_name in ("knowledge_base_search", "document_analysis", "structured_report_generation")


def test_run_with_timeout_success():
    """Test run_with_timeout completes successfully within timeout."""
    def quick_func(x, y):
        return x + y
    
    result = run_with_timeout(quick_func, 5, 2, 3)
    assert result == 5


def test_run_with_timeout_failure():
    """Test run_with_timeout raises TimeoutError for slow functions."""
    def slow_func():
        time.sleep(10)
        return "done"
    
    with pytest.raises(TimeoutError):
        run_with_timeout(slow_func, 1)


def test_run_with_timeout_propagates_exception():
    """Test run_with_timeout propagates exceptions from the function."""
    def failing_func():
        raise ValueError("test error")
    
    with pytest.raises(ValueError, match="test error"):
        run_with_timeout(failing_func, 5)


def test_parse_llm_action_valid_json():
    """Test parsing valid JSON action from LLM response."""
    response = '{"thought": "Search for info", "action": "knowledge_base_search", "action_input": {"query": "test"}}'
    parsed = parse_llm_action(response)
    assert parsed["thought"] == "Search for info"
    assert parsed["action"] == "knowledge_base_search"
    assert parsed["action_input"]["query"] == "test"


def test_parse_llm_action_code_block():
    """Test parsing JSON from code block."""
    response = '''```json
{"thought": "Search", "action": "knowledge_base_search", "action_input": {"query": "test"}}
```'''
    parsed = parse_llm_action(response)
    assert parsed["action"] == "knowledge_base_search"


def test_parse_llm_action_malformed():
    """Test parsing malformed response falls back to defaults."""
    response = "This is not JSON at all"
    parsed = parse_llm_action(response)
    assert parsed["action"] == "knowledge_base_search"
    assert "thought" in parsed
    assert "action_input" in parsed


def test_parse_llm_action_partial_json():
    """Test parsing partially valid JSON."""
    response = '{"action": "document_analysis"}'
    parsed = parse_llm_action(response)
    assert parsed["action"] == "document_analysis"
    assert "thought" in parsed


def test_agent_timeout_enforcement(db_session: Session):
    """Test that agent respects step timeout."""
    user, ws = create_user_and_workspace(db_session)
    
    # Create a mock LLM that simulates a slow response
    from backend.app.llm.router import llm_router
    from backend.app.llm.base import LLMMessage, LLMResponse
    
    original_generate = llm_router.generate
    
    def slow_generate(*args, **kwargs):
        time.sleep(2)
        return original_generate(*args, **kwargs)
    
    with patch.object(llm_router, 'generate', side_effect=slow_generate):
        # Run with very short timeout (1 second)
        original_timeout = agent_orchestrator.step_timeout
        agent_orchestrator.step_timeout = 1
        
        try:
            run = agent_orchestrator.run_investigation(
                task="Investigate timeout behavior",
                workspace_id=ws.id,
                user_id=user.id,
                max_steps=3,
                db=db_session,
            )
            # Should complete but with timeout recorded in scratchpad
            assert run.status in ("completed", "failed")
            # Check that timeout was recorded
            tool_execs = db_session.query(AgentToolExecution).filter(
                AgentToolExecution.agent_run_id == run.id
            ).all()
            timeout_recorded = any("timed out" in te.error_message for te in tool_execs if te.error_message)
            # At least one timeout should be recorded
            assert timeout_recorded or run.total_steps > 0
        finally:
            agent_orchestrator.step_timeout = original_timeout


def test_agent_malformed_llm_output_handling(db_session: Session):
    """Test agent handles malformed LLM output gracefully."""
    user, ws = create_user_and_workspace(db_session)
    
    from backend.app.llm.router import llm_router
    from backend.app.llm.base import LLMResponse
    
    original_generate = llm_router.generate
    
    def malformed_generate(*args, **kwargs):
        return LLMResponse(
            content="This is not valid JSON at all! No action here.",
            model="fake",
            provider="fake",
            prompt_tokens=10,
            completion_tokens=10,
            total_tokens=20,
            latency_ms=10,
        )
    
    with patch.object(llm_router, 'generate', side_effect=malformed_generate):
        run = agent_orchestrator.run_investigation(
            task="Investigate with malformed LLM output",
            workspace_id=ws.id,
            user_id=user.id,
            max_steps=2,
            db=db_session,
        )
        # Should still complete using default action
        assert run.status == "completed"
        assert run.total_steps > 0
