"""RAG orchestration service coordinating retrieval, LLM synthesis, grounding, and citations."""
import uuid
from typing import Optional
from sqlalchemy.orm import Session

from backend.app.core.logging import logger
from backend.app.core.exceptions import EntityNotFoundError
from backend.app.retrieval.hybrid import hybrid_retriever
from backend.app.rag.prompt_templates import RAG_SYSTEM_PROMPT, build_rag_user_prompt
from backend.app.rag.citations import CitationMap
from backend.app.rag.grounding import (
    is_model_abstention,
    find_ungrounded_claims,
    verify_claim_grounding,
    strip_evidence_echo,
)
from backend.app.rag.evidence_gate import evidence_sufficiency_gate, EvidenceDecision
from backend.app.observability.langfuse_tracer import observe
from backend.app.llm.base import LLMMessage
from backend.app.llm.router import llm_router
from backend.app.models.conversation import Conversation, Message, Citation
from backend.app.schemas.chat import (
    SearchResponse,
    SearchResultItem,
    ChatResponse,
    CitationResponse,
)
from backend.app.services.intent_classifier import intent_classifier, IntentType
from backend.app.services.conversational_service import get_conversational_response, get_llm_conversational_response


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

    @observe(name="rag_response_generation")
    def generate_rag_response(
        self,
        query: str,
        workspace_id: str,
        user_id: str,
        conversation_id: Optional[str] = None,
        top_k: int = 5,
        db: Session = None,
    ) -> ChatResponse:
        """Execute full grounded RAG pipeline with short citation resolution and validation.
        
        Now includes intent classification to route conversational queries
        to a conversational response path, bypassing the evidence gate.
        """
        # 0. Classify intent to route conversational vs document queries
        intent = intent_classifier.classify(query)
        
        # Handle conversational queries with a conversational response
        if intent.is_conversational and not intent.should_use_rag:
            return self._generate_conversational_response(
                query=query,
                workspace_id=workspace_id,
                user_id=user_id,
                conversation_id=conversation_id,
                intent=intent,
                db=db,
            )

        # For document questions and mixed queries, proceed with full RAG pipeline
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

        # 3. Assess Evidence Sufficiency & Conflict Detection Gate
        assessment = evidence_sufficiency_gate.assess_evidence(query, retrieved_chunks)

        if assessment.decision == EvidenceDecision.INSUFFICIENT:
            # Deterministic Pre-Generation Abstention: short-circuit without calling LLM
            abstain_content = f"ABSTAIN: insufficient_evidence. {assessment.rationale}"
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
                content=abstain_content,
                token_count=len(abstain_content) // 4,
                msg_metadata={
                    "is_abstention": True,
                    "evidence_decision": assessment.decision.value,
                    "confidence_score": assessment.confidence_score,
                    "pre_generation_gate": True,
                },
            )
            db.add(assistant_msg)
            db.commit()

            return ChatResponse(
                answer=abstain_content,
                conversation_id=conversation_id,
                message_id=assistant_msg.id,
                citations=[],
                is_abstention=True,
                ungrounded_claims=[],
                model_used="evidence_sufficiency_gate",
                provider_used="system",
                latency_ms=1,
            )

        if assessment.decision == EvidenceDecision.CONFLICTING and assessment.conflict:
            # Detectable factual contradiction between documents
            conflict_content = (
                f"ABSTAIN: conflicting_evidence. {assessment.conflict.description}"
            )
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
                content=conflict_content,
                token_count=len(conflict_content) // 4,
                msg_metadata={
                    "is_abstention": True,
                    "evidence_decision": assessment.decision.value,
                    "conflict_details": assessment.conflict.description,
                    "confidence_score": assessment.confidence_score,
                },
            )
            db.add(assistant_msg)
            db.commit()

            return ChatResponse(
                answer=conflict_content,
                conversation_id=conversation_id,
                message_id=assistant_msg.id,
                citations=[],
                is_abstention=True,
                ungrounded_claims=[],
                model_used="evidence_sufficiency_gate",
                provider_used="system",
                latency_ms=1,
            )

        # 4. Filter Context Chunks: only inject PRIMARY and SUPPLEMENTARY chunks
        context_chunks = assessment.chunks_for_context if assessment.chunks_for_context else retrieved_chunks
        citation_map = CitationMap(context_chunks)

        # 5. Build prompt
        user_prompt = build_rag_user_prompt(query, context_chunks)
        messages = [
            LLMMessage(role="system", content=RAG_SYSTEM_PROMPT),
            LLMMessage(role="user", content=user_prompt),
        ]

        # 6. Invoke LLM via router
        llm_resp = llm_router.generate(
            messages=messages,
            workspace_id=workspace_id,
            user_id=user_id,
            db=db,
        )

        # 7. Active Post-Generation Claim Verification & Grounding
        context_texts = [r.chunk.content for r in context_chunks]
        chunk_marker_map = {f"[c_{i}]": r.chunk.content for i, r in enumerate(context_chunks)}
        verification = verify_claim_grounding(llm_resp.content, context_texts, chunk_marker_map)

        final_content = verification.verified_answer
        is_abstain = is_model_abstention(final_content) or verification.should_abstain
        citations = citation_map.resolve(final_content) if not is_abstain else []
        ungrounded = verification.ungrounded_claims if not is_abstain else []

        # 8. Save Messages and Citations in DB
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
            content=final_content,
            token_count=llm_resp.completion_tokens,
            msg_metadata={
                "model": llm_resp.model,
                "provider": llm_resp.provider,
                "is_fallback": llm_resp.is_fallback,
                "is_abstention": is_abstain,
                "ungrounded_claims_count": len(ungrounded),
                "grounding_score": verification.grounding_score,
                "hallucination_rate": verification.hallucination_rate,
                "evidence_decision": assessment.decision.value,
                "confidence_score": assessment.confidence_score,
            },
        )
        db.add(assistant_msg)
        db.commit()

        return ChatResponse(
            answer=final_content,
            conversation_id=conversation_id,
            message_id=assistant_msg.id,
            citations=citations,
            is_abstention=is_abstain,
            ungrounded_claims=ungrounded,
            model_used=llm_resp.model,
            provider_used=llm_resp.provider,
            latency_ms=llm_resp.latency_ms,
        )

    def _generate_conversational_response(
        self,
        query: str,
        workspace_id: str,
        user_id: str,
        conversation_id: Optional[str] = None,
        intent: IntentType = None,
        db: Session = None,
    ) -> ChatResponse:
        """Generate a conversational response without document retrieval.
        
        Handles greetings, capability questions, clarifications, social chat,
        and other conversational interactions without document retrieval.
        """
        # Manage Conversation Session
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

        # Get conversational response using the conversational service
        try:
            # Use the intent_type from the intent classification
            intent_type_str = intent.intent_type.value if intent else "conversational"
            response_content = get_conversational_response(query, workspace_id, intent_type=intent.intent_type if intent else None)
            
            # If no quick pattern matches, fall back to LLM-based conversational response
            if response_content is None:
                try:
                    response_content = get_llm_conversational_response(query, [])
                except Exception as e:
                    logger.warning(f"LLM conversational response generation failed: {e}")
                    response_content = "I'm here to help! I can search your documents, investigate incidents, analyze technical issues, or answer questions about your documentation. How can I help you today?"
            elif response_content is None:
                response_content = "I'm here to help! I can search your documents, investigate incidents, analyze technical issues, or answer questions about your documentation. How can I help you today?"
        except Exception as e:
            logger.warning(f"Conversational response generation failed: {e}")
            response_content = "I'm here to help! I can search your documents, investigate incidents, analyze technical issues, or answer questions about your documentation. How can I help you today?"
        
        # Save messages
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
            content=response_content,
            token_count=len(response_content) // 4,
            msg_metadata={
                "intent_type": intent.intent_type.value if intent else "conversational",
                "is_conversational": True,
                "is_abstention": False,
            },
        )
        db.add(assistant_msg)
        db.commit()

        return ChatResponse(
            answer=response_content,
            conversation_id=conversation_id,
            message_id=assistant_msg.id,
            citations=[],
            is_abstention=False,
            ungrounded_claims=[],
            model_used="conversational",
            provider_used="conversational",
            latency_ms=1,
        )


rag_service = RAGService()

