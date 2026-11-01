# ADR-004: Custom Tool-Calling Agent Architecture

## Status
ACCEPTED

## Context
Module D (AI Agents) mandates building an autonomous agent with at least three functional tools:
1. `Knowledge Base Search`: Semantically searches internal technical documents and returns passages with source metadata.
2. `Document Analysis`: Performs deep structural analysis on a specific document, identifying events, reported causes, symptoms, and mitigations.
3. `Structured Report Generation`: Compiles findings into an executive markdown/JSON report.

The agent must select tools dynamically based on user intent, validate parameters, execute multi-step plans (e.g., search output fed into document analysis, which feeds into report generation), enforce execution limits, and handle failures gracefully.

We must evaluate whether to use a high-level agent framework (LangChain / LangGraph, CrewAI, AutoGen) or build a custom tool-calling engine in pure Python.

## Decision
We select a **Custom Tool-Calling Agent Architecture** utilizing standard LLM function/tool-calling protocols (OpenAI Tool Calling / Anthropic Tool Use) and **Pydantic v2** for runtime argument validation.

The agent runtime consists of:
- `BaseTool` abstract interface defining tool name, description, Pydantic argument schema, and `execute()` method.
- `ToolRegistry` managing registered tools and auto-generating provider-specific tool schemas.
- `AgentOrchestrator` managing the multi-turn reasoning loop:
  1. Inspect user prompt and conversation state.
  2. Prompt the LLM with registered tool schemas.
  3. Parse model tool call directives with strict Pydantic validation.
  4. Dispatch and execute the selected tool with a 30-second timeout.
  5. Feed the tool output (or error message) back to the LLM context.
  6. Repeat until the LLM emits a final response or hits the maximum step limit (max 5 loops).
- `ExecutionAuditLogger` persisting each step, input, output, duration, and status to the `agent_tool_calls` table.

## Alternatives Considered
- **LangChain / LangGraph:**
  - *Pros:* Out-of-the-box prebuilt agent abstractions.
  - *Cons:* Heavy dependency footprint, frequent breaking changes across minor versions, opaque internal state machines that obscure execution logs, and excessive layers of abstraction that complicate live debugging during the 60-minute technical evaluation.
- **CrewAI / AutoGen:**
  - *Pros:* Multi-agent conversational abstractions.
  - *Cons:* Designed for complex multi-persona simulations; introduces unnecessary conversational overhead and unpredictable token burn for a structured technical investigation task.

## Rationale
1. **Compliance with Strict Assessment Instructions:** Rule 1 (Independent Engineering Decisions) and Rule 5 (Code Ownership) require that the candidate fully understand and defend every major component. A custom engine ensures complete transparency and code ownership.
2. **Deterministic Live Technical Verification:** During the supervised live evaluation, reviewers may ask to "Implement a new tool in the existing agent architecture" (Live Verification Scenario 3). In our custom architecture, adding a new tool requires merely writing a single subclass of `BaseTool` and registering it in one line.
3. **Safety & Zero-Trust Sandboxing:** A custom engine ensures the agent cannot execute arbitrary shell commands, raw SQL, or dangerous system calls. All tools are sandboxed, typed, and read-only.

## Consequences
- **Positive:**
  - Zero external framework churn or mysterious abstractions.
  - Clear, inspectable, and streamable execution states for the frontend UI.
  - Complete control over step limits, timeout controls, and error recovery loops.
- **Negative:**
  - Requires writing the loop orchestrator and schema mapper (~150-200 lines of clean Python code).

