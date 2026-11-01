"""RAG orchestration service coordinating retrieval, LLM synthesis, grounding, and citations."""
import uuid
from typing import Optional
from sqlalchemy.orm import Session

from backend.app.core.logging import logger
from backend.app.core.exceptions import EntityNotFoundError
from backend.app.retrieval.hybrid import hybrid_retriever
from backend.app.rag.prompt_templates import RAG_SYSTEM_PROMPT, build_rag_user_prompt
from backend.app.rag.citations import CitationMap
from backend.app.rag.grounding import is_model_abstention, find_ungrounded_claims
from backend.app.llm.base import LLMMessage
from backend.app.llm.router import llm_router
from backend.app.models.conversation import Conversation, Message, Citation
from backend.app.schemas.chat import (
    SearchResponse,
    SearchResultItem,
    ChatResponse,
    CitationResponse,
)


class RAGService:
    """End-to-end RAG orchestrator with short-citation mapping and anti-hallucination checks."""

    def search(
        self,
        query: str,
        workspace_id: str,
        top_k: int = 5,
        mode: str = "hybrid",
        db: Session = None,
    ) -> SearchResponse:
        """Search documents across workspace using dense, sparse, or hybrid retrieval."""
        results = hybrid_retriever.retrieve(
            query=query,
            workspace_id=workspace_id,
            top_k=top_k,
            mode=mode,
            db=db,
        )

        items = [
            SearchResultItem(
                chunk_id=r.chunk.id,
                document_id=r.chunk.document_id,
                document_title=r.document_title,
                content=r.chunk.content,
                score=r.score,
                chunk_index=r.chunk.chunk_index,
                metadata=r.chunk.chunk_metadata or {},
            )
            for r in results
        ]

        return SearchResponse(
            query=query,
            mode=mode,
            results=items,
            total_results=len(items),
        )

    def generate_rag_response(
        self,
        query: str,
        workspace_id: str,
        user_id: str,
        conversation_id: Optional[str] = None,
        top_k: int = 5,
        db: Session = None,
    ) -> ChatResponse:
        """Execute full grounded RAG pipeline with short citation resolution and validation."""
        # 1. Manage Conversation Session
        if conversation_id:
            conv = db.query(Conversation).filter(
                Conversation.id == conversation_id,
                Conversation.workspace_id == workspace_id,
                Conversation.user_id == user_id,
            ).first()
            if not conv:
                raise EntityNotFoundError(f"Conversation {conversation_id} not found")
        else:
            conv = Conversation(
                workspace_id=workspace_id,
                user_id=user_id,
                title=query[:60].strip(),
            )
            db.add(conv)
            db.flush()
            conversation_id = conv.id

        # 2. Retrieve evidence chunks
        retrieved_chunks = hybrid_retriever.retrieve(
            query=query,
            workspace_id=workspace_id,
            top_k=top_k,
            mode="hybrid",
            db=db,
        )

        citation_map = CitationMap(retrieved_chunks)

        # 3. Build prompt
        user_prompt = build_rag_user_prompt(query, retrieved_chunks)
        messages = [
            LLMMessage(role="system", content=RAG_SYSTEM_PROMPT),
            LLMMessage(role="user", content=user_prompt),
        ]

        # 4. Invoke LLM via router
        llm_resp = llm_router.generate(
            messages=messages,
            workspace_id=workspace_id,
            user_id=user_id,
            db=db,
        )

        # 5. Verify Grounding and Citations
        is_abstain = is_model_abstention(llm_resp.content)
        citations = citation_map.resolve(llm_resp.content) if not is_abstain else []
        
        context_texts = [r.chunk.content for r in retrieved_chunks]
        ungrounded = find_ungrounded_claims(llm_resp.content, context_texts) if not is_abstain else []

        # 6. Save Messages and Citations in DB
        user_msg = Message(
            conversation_id=conversation_id,
            role="user",
            content=query,
            token_count=len(query) // 4,
        )
        db.add(user_msg)

        assistant_msg = Message(
            conversation_id=conversation_id,
            role="assistant",
            content=llm_resp.content,
            token_count=llm_resp.completion_tokens,
            msg_metadata={
                "model": llm_resp.model,
                "provider": llm_resp.provider,
                "is_fallback": llm_resp.is_fallback,
                "is_abstention": is_abstain,
                "ungrounded_claims_count": len(ungrounded),
            },
        )
        db.add(assistant_msg)
        db.flush()

        # Persist citations
        for cit in citations:
            db_cit = Citation(
                message_id=assistant_msg.id,
                chunk_id=cit.chunk_id,
                document_id=cit.document_id,
                citation_marker=cit.marker,
                score=cit.score,
                snippet=cit.snippet,
            )
            db.add(db_cit)

        db.commit()

        return ChatResponse(
            answer=llm_resp.content,
            conversation_id=conversation_id,
            message_id=assistant_msg.id,
            citations=citations,
            is_abstention=is_abstain,
            ungrounded_claims=ungrounded,
            model_used=llm_resp.model,
            provider_used=llm_resp.provider,
            latency_ms=llm_resp.latency_ms,
        )


rag_service = RAGService()

