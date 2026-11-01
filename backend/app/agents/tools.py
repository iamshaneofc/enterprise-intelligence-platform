"""Agent Tool Trio with graceful error recovery."""
import time
import json
from typing import Dict, Any, Callable, List
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field, ValidationError

from backend.app.retrieval.hybrid import hybrid_retriever
from backend.app.models.chunk import Chunk
from backend.app.core.config import settings
from backend.app.core.exceptions import AgentExecutionError


class ToolExecutionResult:
    """Standardized tool output wrapper."""
    def __init__(self, ok: bool, data: Any = None, error: str = None):
        self.ok = ok
        self.data = data or {}
        self.error = error

    def to_dict(self) -> Dict[str, Any]:
        res = {"ok": self.ok}
        if self.ok:
            res["data"] = self.data
        else:
            res["error"] = self.error
        return res


# Pydantic schemas for tool input validation
class KnowledgeBaseSearchInput(BaseModel):
    query: str = Field(..., min_length=1, description="Search query")
    top_k: int = Field(default=3, ge=1, le=20, description="Number of results to return")


class DocumentAnalysisInput(BaseModel):
    target: str = Field(..., min_length=1, description="Target concept to analyze")


class StructuredReportGenerationInput(BaseModel):
    title: str = Field(default="Engineering Investigation Report", description="Report title")
    findings: List[str] = Field(default_factory=list, description="Key findings")
    recommendations: List[str] = Field(default_factory=list, description="Actionable recommendations")


TOOL_SCHEMAS = {
    "knowledge_base_search": KnowledgeBaseSearchInput,
    "document_analysis": DocumentAnalysisInput,
    "structured_report_generation": StructuredReportGenerationInput,
}


class AgentToolRegistry:
    """Registry managing available agent tools and defensive execution."""

    def __init__(self):
        self.tools = {
            "knowledge_base_search": self.knowledge_base_search,
            "document_analysis": self.document_analysis,
            "structured_report_generation": self.structured_report_generation,
        }

    def get_tool_definitions(self) -> str:
        return """
1. knowledge_base_search(query: str, top_k: int = 3)
   - Searches indexed engineering documents and retrieves relevant text chunks.
2. document_analysis(target: str)
   - Analyzes technical evidence across retrieved document context for root cause and timeline.
3. structured_report_generation(title: str, findings: list[str], recommendations: list[str])
   - Synthesizes findings into a verified final incident or technical investigation report.
"""

    def execute_tool(
        self,
        tool_name: str,
        tool_input: Dict[str, Any],
        workspace_id: str,
        db: Session,
    ) -> Dict[str, Any]:
        """Execute tool safely with input validation, intercepting exceptions and returning graceful JSON errors."""
        tool_fn = self.tools.get(tool_name)
        if not tool_fn:
            return {"ok": False, "error": f"Tool '{tool_name}' is not recognized"}

        # Validate input against Pydantic schema
        schema = TOOL_SCHEMAS.get(tool_name)
        if schema:
            try:
                validated_input = schema(**tool_input)
                tool_input = validated_input.model_dump()
            except ValidationError as e:
                return {"ok": False, "error": f"Invalid tool input: {e.errors()}"}

        try:
            return tool_fn(tool_input, workspace_id, db)
        except Exception as e:
            return {"ok": False, "error": f"Tool execution failed: {str(e)}"}

    def knowledge_base_search(
        self,
        tool_input: Dict[str, Any],
        workspace_id: str,
        db: Session,
    ) -> Dict[str, Any]:
        """Tool 1: Knowledge Base Search."""
        query = tool_input.get("query", "")
        if not query:
            return {"ok": False, "error": "Query parameter is required"}
        top_k = tool_input.get("top_k", 3)

        retrieved = hybrid_retriever.retrieve(
            query=query,
            workspace_id=workspace_id,
            top_k=top_k,
            mode="hybrid",
            db=db,
        )

        results = [
            {
                "chunk_id": r.chunk.id,
                "document_title": r.document_title,
                "score": r.score,
                "snippet": r.chunk.content[:250],
            }
            for r in retrieved
        ]
        return {"ok": True, "data": {"results": results, "count": len(results)}}

    def document_analysis(
        self,
        tool_input: Dict[str, Any],
        workspace_id: str,
        db: Session,
    ) -> Dict[str, Any]:
        """Tool 2: Deep Document Analysis."""
        target = tool_input.get("target", "")
        if not target:
            return {"ok": False, "error": "Target concept is required"}

        # Fetch recent workspace chunks to analyze
        chunks = db.query(Chunk).filter(Chunk.workspace_id == workspace_id).limit(10).all()
        matched = []
        for ch in chunks:
            if any(term in ch.content.lower() for term in target.lower().split()):
                matched.append(ch.content[:300])

        return {
            "ok": True,
            "data": {
                "target": target,
                "evidence_snippets": matched or [c.content[:200] for c in chunks[:2]],
                "analysis_summary": f"Identified {len(matched)} evidence segments correlating with '{target}'",
            },
        }

    def structured_report_generation(
        self,
        tool_input: Dict[str, Any],
        workspace_id: str,
        db: Session,
    ) -> Dict[str, Any]:
        """Tool 3: Structured Report Generation."""
        title = tool_input.get("title", "Engineering Investigation Report")
        findings = tool_input.get("findings", [])
        recommendations = tool_input.get("recommendations", [])

        report_markdown = f"# {title}\n\n## Key Findings\n"
        for f in findings:
            report_markdown += f"- {f}\n"

        report_markdown += "\n## Actionable Recommendations\n"
        for r in recommendations:
            report_markdown += f"- {r}\n"

        return {
            "ok": True,
            "data": {
                "title": title,
                "findings": findings,
                "recommendations": recommendations,
                "formatted_report": report_markdown,
            },
        }


tool_registry = AgentToolRegistry()

