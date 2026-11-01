"""Deterministic Fake LLM client for offline execution and automated testing."""
import json
import re
import time
from typing import List, Optional
from backend.app.llm.base import BaseLLMClient, LLMMessage, LLMResponse


class FakeLLMClient(BaseLLMClient):
    """
    Deterministic simulated LLM client.
    Accurately emulates realistic RAG responses with citations [c_0], [c_1],
    abstention triggers, and structured output formatting.
    """
    def __init__(self, model: str = "fake-claude-3-5-sonnet", provider: str = "fake"):
        self.model = model
        self.provider = provider
        self.force_fail = False  # Can be set to True to test failover routing

    def generate(
        self,
        messages: List[LLMMessage],
        temperature: float = 0.0,
        max_tokens: int = 2048,
    ) -> LLMResponse:
        from backend.app.core.exceptions import LLMQuotaExceededError
        if self.force_fail:
            raise LLMQuotaExceededError("Simulated primary provider rate limit (429)")

        start_time = time.time()
        combined_text = "\n".join(m.content for m in messages)
        prompt_tokens = len(combined_text) // 4

        # Check for agent prompt requesting tool action
        if "Available Tools:" in combined_text or "Choose the next action" in combined_text:
            content = self._generate_agent_response(combined_text)
        elif "Answer the engineering question strictly using the provided context" in combined_text or "<untrusted_document_context>" in combined_text:
            content = self._generate_rag_response(combined_text)
        else:
            content = f"Simulated response to: {messages[-1].content[:100]}"

        completion_tokens = len(content) // 4
        latency_ms = int((time.time() - start_time) * 1000)

        return LLMResponse(
            content=content,
            model=self.model,
            provider=self.provider,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
            latency_ms=latency_ms,
            is_fallback=False,
        )

    def _generate_rag_response(self, text: str) -> str:
        """Synthesize source-grounded response citing available citations."""
        # Find citation markers in context
        c_markers = re.findall(r"\[(c_\d+)\]", text)
        unique_markers = sorted(list(set(c_markers)))

        # Abstention check: if no context or explicitly unanswerable
        lower = text.lower()
        if not unique_markers or "unrelated topic" in lower or "quantum teleportation" in lower:
            return "ABSTAIN: insufficient_evidence. The provided document context does not contain sufficient verified facts to answer this inquiry."

        citations_str = " ".join(f"[{m}]" for m in unique_markers[:2])
        
        # Grounded answer synthesis referencing technical context
        if "incident" in lower or "pool" in lower or "postgres" in lower:
            return (
                f"Based on the engineering postmortem {citations_str}, on 2026-03-15 at 14:22 UTC, the PostgreSQL "
                f"connection pool exhausted all 200 connections due to a missing index and transaction leak. "
                f"The resolution involved adjusting max_connections to 400 and reducing the connection timeout to 5s."
            )
        elif "gateway" in lower or "504" in lower or "timeout" in lower:
            return (
                f"According to the operational logs {citations_str}, the API gateway experienced elevated 504 timeouts "
                f"with p99 latency reaching 4200ms due to upstream worker thread starvation."
            )
        else:
            return (
                f"According to verified documentation {citations_str}, the system configuration details have been confirmed "
                f"and validated across all active nodes."
            )

    def _generate_agent_response(self, text: str) -> str:
        """Generate structured agent reasoning and tool invocation JSON."""
        # Check current step
        step_match = re.search(r"Step (\d+)", text)
        step = int(step_match.group(1)) if step_match else 1

        if step == 1:
            return json.dumps({
                "thought": "I need to search the knowledge base for technical documentation regarding the reported issue.",
                "action": "knowledge_base_search",
                "action_input": {"query": "PostgreSQL connection pool outage incident"}
            })
        elif step == 2:
            return json.dumps({
                "thought": "Now I should deeply analyze the retrieved document chunks for root causes and timestamps.",
                "action": "document_analysis",
                "action_input": {"target": "incident root cause and timeline"}
            })
        else:
            return json.dumps({
                "thought": "I have gathered sufficient factual evidence across the documents to produce a structured incident report.",
                "action": "structured_report_generation",
                "action_input": {
                    "title": "Incident 104 Root Cause Analysis",
                    "findings": [
                        "Exhaustion of 200 connections at 14:22 UTC on 2026-03-15",
                        "Transaction leak identified in accounts service",
                        "Remediation: max_connections increased to 400, timeout set to 5s"
                    ],
                    "recommendations": ["Add missing database index", "Deploy connection pool circuit breaker"]
                }
            })

