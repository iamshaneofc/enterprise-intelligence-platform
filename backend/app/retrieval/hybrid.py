"""Hybrid Search Retriever combining dense vector search and sparse BM25 with Reciprocal Rank Fusion (RRF)."""
from dataclasses import dataclass
from typing import List, Dict, Optional, Any
from sqlalchemy.orm import Session

from backend.app.core.config import settings
from backend.app.models.chunk import Chunk
from backend.app.models.document import Document
from backend.app.repositories.vector_repo import vector_repo
from backend.app.embeddings.provider import get_embedding_provider
from backend.app.observability.langfuse_tracer import observe


@dataclass
class RetrievedChunk:
    """Standardized retrieval result with score, chunk object, and document title."""
    chunk: Chunk
    score: float
    document_title: str


class HybridRetriever:
    """Executes dense vector search, sparse keyword search, or hybrid RRF fusion."""

    def __init__(self, rrf_k: int = settings.RRF_K):
        self.rrf_k = rrf_k

    @observe(name="hybrid_retrieval")
    def retrieve(
        self,
        query: str,
        workspace_id: str,
        top_k: int = settings.TOP_K_RETRIEVAL,
        mode: str = "hybrid",
        db: Session = None,
        document_id: Optional[str] = None,
    ) -> List[RetrievedChunk]:
        """Retrieve top relevant chunks matching query within workspace."""
        if not db:
            raise ValueError("Database session is required for retrieval")

        # Preload document titles map for efficiency
        doc_titles: Dict[str, str] = {
            doc.id: doc.title
            for doc in db.query(Document.id, Document.title).filter(Document.workspace_id == workspace_id).all()
        }

        if mode == "sparse":
            sparse_hits = vector_repo.sparse_search(query, workspace_id, top_k, db, document_id)
            return [
                RetrievedChunk(
                    chunk=ch,
                    score=round(score, 4),
                    document_title=doc_titles.get(ch.document_id, "Unknown Document"),
                )
                for ch, score in sparse_hits
            ]

        # Generate query embedding for dense/hybrid
        embedder = get_embedding_provider()
        query_vector = embedder.embed_text(query)

        if mode == "dense":
            dense_hits = vector_repo.similarity_search(query_vector, workspace_id, top_k, db, document_id)
            return [
                RetrievedChunk(
                    chunk=ch,
                    score=round(score, 4),
                    document_title=doc_titles.get(ch.document_id, "Unknown Document"),
                )
                for ch, score in dense_hits
            ]

        # Mode == "hybrid": Reciprocal Rank Fusion
        candidate_k = max(top_k * 2, 10)
        dense_hits = vector_repo.similarity_search(query_vector, workspace_id, candidate_k, db, document_id)
        sparse_hits = vector_repo.sparse_search(query, workspace_id, candidate_k, db, document_id)

        rrf_scores: Dict[str, float] = {}
        chunk_map: Dict[str, Chunk] = {}

        # Dense rank contributions
        for rank, (ch, _) in enumerate(dense_hits, start=1):
            rrf_scores[ch.id] = rrf_scores.get(ch.id, 0.0) + (1.0 / (self.rrf_k + rank))
            chunk_map[ch.id] = ch

        # Sparse rank contributions
        for rank, (ch, _) in enumerate(sparse_hits, start=1):
            rrf_scores[ch.id] = rrf_scores.get(ch.id, 0.0) + (1.0 / (self.rrf_k + rank))
            chunk_map[ch.id] = ch

        # Sort combined results by RRF score descending
        sorted_ids = sorted(rrf_scores.keys(), key=lambda cid: rrf_scores[cid], reverse=True)

        results: List[RetrievedChunk] = []
        for cid in sorted_ids[:top_k]:
            chunk = chunk_map[cid]
            results.append(
                RetrievedChunk(
                    chunk=chunk,
                    score=round(rrf_scores[cid], 5),
                    document_title=doc_titles.get(chunk.document_id, "Unknown Document"),
                )
            )

        return results


hybrid_retriever = HybridRetriever()

