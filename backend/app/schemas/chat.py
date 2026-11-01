"""Chat, Search, and Citation schemas."""
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, ConfigDict


class CitationResponse(BaseModel):
    marker: str  # e.g., [c_0], [c_1]
    document_id: str
    document_title: str
    chunk_id: str
    snippet: str
    score: float


class SearchResultItem(BaseModel):
    chunk_id: str
    document_id: str
    document_title: str
    content: str
    score: float
    chunk_index: int
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SearchRequest(BaseModel):
    query: str = Field(min_length=1)
    workspace_id: str
    top_k: int = Field(default=5, ge=1, le=50)
    mode: str = Field(default="hybrid", pattern="^(hybrid|dense|sparse)$")


class SearchResponse(BaseModel):
    query: str
    mode: str
    results: List[SearchResultItem]
    total_results: int


class ChatRequest(BaseModel):
    query: str = Field(min_length=1)
    workspace_id: str
    conversation_id: Optional[str] = None
    top_k: int = Field(default=5, ge=1, le=20)


class ChatResponse(BaseModel):
    answer: str
    conversation_id: str
    message_id: str
    citations: List[CitationResponse] = Field(default_factory=list)
    is_abstention: bool = False
    ungrounded_claims: List[str] = Field(default_factory=list)
    model_used: str
    provider_used: str
    latency_ms: int


class MessageResponse(BaseModel):
    id: str
    role: str
    content: str
    citations: List[CitationResponse] = Field(default_factory=list)
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ConversationResponse(BaseModel):
    id: str
    workspace_id: str
    title: str
    summary: Optional[str] = None
    messages: List[MessageResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
