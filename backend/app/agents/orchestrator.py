"""Autonomous AI Agent Orchestrator with constrained tool-use and execution tracing."""
import json
import re
import time
import threading
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List, Callable, TypeVar
from sqlalchemy.orm import Session

from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.core.exceptions import AgentExecutionError
from backend.app.models.agent import AgentRun, AgentToolExecution
from backend.app.agents.tools import tool_registry
from backend.app.llm.base import LLMMessage
from backend.app.llm.router import llm_router


T = TypeVar('T')


def run_with_timeout(func: Callable[..., T], timeout_seconds: int, *args, **kwargs) -> T:
    """
    Execute a function with a timeout.
    
    Args:
        func: Function to execute
        timeout_seconds: Maximum time to wait
        *args, **kwargs: Arguments to pass to function
        
    Returns:
        Function result
        
    Raises:
        TimeoutError: If function doesn't complete within timeout
        Exception: Any exception raised by the function
    """
    result = [None]
    exception = [None]
    
    def target():
        try:
            result[0] = func(*args, **kwargs)
        except Exception as e:
            exception[0] = e
    
    thread = threading.Thread(target=target)
    thread.daemon = True
    thread.start()
    thread.join(timeout=timeout_seconds)
    
    if thread.is_alive():
        raise TimeoutError(f"Operation timed out after {timeout_seconds} seconds")
    
    if exception[0]:
        raise exception[0]
    
    return result[0]


def parse_llm_action(response_content: str) -> Dict[str, Any]:
    """
    Parse LLM response to extract action JSON.
    More robust than simple regex - handles common formatting issues.
    
    Args:
        response_content: Raw LLM response text
        
    Returns:
        Parsed action dict with thought, action, action_input
    """
    default = {
        "thought": "Analyzing next step",
        "action": "knowledge_base_search",
        "action_input": {"query": ""},
    }
    
    # Try to find JSON in code blocks first
    code_block_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", response_content, re.DOTALL)
    if code_block_match:
        try:
            return json.loads(code_block_match.group(1))
        except json.JSONDecodeError:
            pass
    
    # Try to find JSON object (most common case)
    json_match = re.search(r"\{.*\}", response_content, re.DOTALL)
    if json_match:
        try:
            parsed = json.loads(json_match.group(0))
            # Validate required fields
            if "action" in parsed:
                return {
                    "thought": parsed.get("thought", default["thought"]),
                    "action": parsed.get("action", default["action"]),
                    "action_input": parsed.get("action_input", default["action_input"]),
                }
        except json.JSONDecodeError:
            pass
    
    # Fallback: try to extract from key-value patterns
    thought_match = re.search(r'"thought"\s*:\s*"([^"]*)"', response_content)
    action_match = re.search(r'"action"\s*:\s*"([^"]*)"', response_content)
    input_match = re.search(r'"action_input"\s*:\s*(\{.*?\})', response_content, re.DOTALL)
    
    if action_match:
        result = {"action": action_match.group(1)}
        if thought_match:
            result["thought"] = thought_match.group(1)
        if input_match:
            try:
                result["action_input"] = json.loads(input_match.group(1))
            except json.JSONDecodeError:
                result["action_input"] = default["action_input"]
        else:
            result["action_input"] = default["action_input"]
        return result
    
    logger.warning(f"Could not parse LLM action from response, using defaults: {response_content[:200]}")
    return default


AGENT_SYSTEM_PROMPT = """You are an autonomous Senior Engineering Incident Investigation Agent.
Your goal is to investigate complex technical problems by querying knowledge bases, analyzing document evidence, and compiling structured reports.

You have access to the following tools:
{tool_definitions}

Instructions:
1. Always output your decision in strict JSON format:
{{
  "thought": "Your internal engineering rationale for this step",
  "action": "tool_name",
  "action_input": {{"param": "value"}}
}}
2. Take one action at a time.
3. When you have gathered sufficient evidence to conclude the investigation, call 'structured_report_generation' to produce the final report.
"""


class AgentOrchestrator:
    """Manages autonomous multi-step reasoning, tool dispatch, error feedback, and execution traces."""

    def __init__(self, max_steps: int = settings.AGENT_MAX_STEPS):
        self.max_steps = max_steps
        self.step_timeout = settings.AGENT_TIMEOUT_SECONDS

    def run_investigation(
        self,
        task: str,
        workspace_id: str,
        user_id: str,
        conversation_id: Optional[str] = None,
        max_steps: Optional[int] = None,
        db: Session = None,
    ) -> AgentRun:
        """Execute autonomous investigation loop with timeout enforcement."""
        steps_limit = max_steps or self.max_steps
        start_time = time.time()

        # Initialize AgentRun record
        agent_run = AgentRun(
            workspace_id=workspace_id,
            user_id=user_id,
            conversation_id=conversation_id,
            task=task,
            status="running",
            plan=[],
            total_steps=0,
        )
        db.add(agent_run)
        db.commit()
        db.refresh(agent_run)

        scratchpad: List[Dict[str, Any]] = []
        final_report: Optional[str] = None

        system_prompt = AGENT_SYSTEM_PROMPT.format(
            tool_definitions=tool_registry.get_tool_definitions()
        )

        try:
            for step in range(1, steps_limit + 1):
                # Check overall timeout
                elapsed = time.time() - start_time
                if elapsed >= self.step_timeout * steps_limit:
                    logger.warning(f"AgentRun {agent_run.id}: Overall timeout reached, stopping")
                    break
                
                logger.info(f"AgentRun {agent_run.id}: Starting Step {step}/{steps_limit}")

                # Format prompt with accumulated scratchpad history
                history_text = "\n".join(
                    f"Step {s['step']}:\nThought: {s['thought']}\nAction: {s['action']}({json.dumps(s['input'])})\nObservation: {json.dumps(s['output'])}\n"
                    for s in scratchpad
                )

                step_prompt = f"""Task: {task}
Current Step: Step {step} of {steps_limit}

Previous Steps:
{history_text or 'No steps taken yet.'}

Choose the next action in strict JSON format:"""

                messages = [
                    LLMMessage(role="system", content=system_prompt),
                    LLMMessage(role="user", content=step_prompt),
                ]

                # Generate next step from LLM with timeout
                try:
                    llm_resp = run_with_timeout(
                        llm_router.generate,
                        self.step_timeout,
                        messages=messages,
                        workspace_id=workspace_id,
                        user_id=user_id,
                        db=db,
                    )
                except TimeoutError:
                    logger.error(f"AgentRun {agent_run.id}: LLM generation timed out at step {step}")
                    # Record timeout in scratchpad
                    tool_output = {"ok": False, "error": f"LLM generation timed out after {self.step_timeout}s"}
                    tool_exec = AgentToolExecution(
                        agent_run_id=agent_run.id,
                        step_number=step,
                        tool_name="llm_generation",
                        tool_input={"messages": [m.content for m in messages]},
                        tool_output=tool_output,
                        status="error",
                        execution_time_ms=self.step_timeout * 1000,
                        error_message="LLM generation timeout",
                    )
                    db.add(tool_exec)
                    db.flush()
                    scratchpad.append({
                        "step": step,
                        "thought": "LLM generation timed out",
                        "action": "llm_generation",
                        "input": {"messages": [m.content for m in messages]},
                        "output": tool_output,
                    })
                    break
                except Exception as llm_err:
                    logger.error(f"AgentRun {agent_run.id}: LLM generation failed: {llm_err}")
                    tool_output = {"ok": False, "error": f"LLM generation failed: {str(llm_err)}"}
                    tool_exec = AgentToolExecution(
                        agent_run_id=agent_run.id,
                        step_number=step,
                        tool_name="llm_generation",
                        tool_input={"messages": [m.content for m in messages]},
                        tool_output=tool_output,
                        status="error",
                        execution_time_ms=0,
                        error_message=str(llm_err),
                    )
                    db.add(tool_exec)
                    db.flush()
                    scratchpad.append({
                        "step": step,
                        "thought": "LLM generation failed",
                        "action": "llm_generation",
                        "input": {"messages": [m.content for m in messages]},
                        "output": tool_output,
                    })
                    break

                # Parse JSON action using improved parser
                parsed_action = parse_llm_action(llm_resp.content)
                thought = parsed_action["thought"]
                action_name = parsed_action["action"]
                action_input = parsed_action["action_input"]

                # Execute Tool with timeout
                tool_start = time.time()
                try:
                    tool_output = run_with_timeout(
                        tool_registry.execute_tool,
                        self.step_timeout,
                        tool_name=action_name,
                        tool_input=action_input,
                        workspace_id=workspace_id,
                        db=db,
                    )
                except TimeoutError:
                    logger.error(f"AgentRun {agent_run.id}: Tool '{action_name}' timed out")
                    tool_output = {"ok": False, "error": f"Tool '{action_name}' timed out after {self.step_timeout}s"}
                    tool_duration_ms = self.step_timeout * 1000
                except Exception as tool_err:
                    logger.error(f"AgentRun {agent_run.id}: Tool '{action_name}' failed: {tool_err}")
                    tool_output = {"ok": False, "error": f"Tool '{action_name}' failed: {str(tool_err)}"}
                    tool_duration_ms = int((time.time() - tool_start) * 1000)
                else:
                    tool_duration_ms = int((time.time() - tool_start) * 1000)

                # Record Tool Execution in DB
                tool_exec = AgentToolExecution(
                    agent_run_id=agent_run.id,
                    step_number=step,
                    tool_name=action_name,
                    tool_input=action_input,
                    tool_output=tool_output,
                    status="success" if tool_output.get("ok") else "error",
                    execution_time_ms=tool_duration_ms,
                    error_message=tool_output.get("error"),
                )
                db.add(tool_exec)
                db.flush()

                scratchpad.append({
                    "step": step,
                    "thought": thought,
                    "action": action_name,
                    "input": action_input,
                    "output": tool_output,
                })

                # Check if report generated
                if action_name == "structured_report_generation" and tool_output.get("ok"):
                    data = tool_output.get("data", {})
                    final_report = data.get("formatted_report")
                    break

            # If loop finished without structured report tool, generate summary
            if not final_report:
                final_report = (
                    f"# Investigation Summary for: {task}\n\n"
                    f"Completed {len(scratchpad)} investigation steps across indexed documentation. "
                    f"Evidence gathered from knowledge base search and document analysis."
                )

            total_latency_ms = int((time.time() - start_time) * 1000)
            agent_run.status = "completed"
            agent_run.plan = scratchpad
            agent_run.final_output = final_report
            agent_run.total_steps = len(scratchpad)
            agent_run.execution_time_ms = total_latency_ms
            agent_run.completed_at = datetime.now(timezone.utc)
            db.commit()
            db.refresh(agent_run)

            return agent_run

        except Exception as e:
            logger.error(f"AgentRun {agent_run.id} failed: {str(e)}", exc_info=True)
            agent_run.status = "failed"
            agent_run.final_output = f"Agent failed: {str(e)}"
            agent_run.completed_at = datetime.now(timezone.utc)
            db.commit()
            raise AgentExecutionError(f"Autonomous investigation failed: {str(e)}")


agent_orchestrator = AgentOrchestrator()

