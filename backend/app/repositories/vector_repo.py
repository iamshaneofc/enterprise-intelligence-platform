"""Vector and Hybrid Search Repository with dual PostgreSQL pgvector and SQLite support."""
import math
import re
import numpy as np
from typing import List, Tuple, Optional, Set
from sqlalchemy.orm import Session
from sqlalchemy import text

from backend.app.models.chunk import Chunk
from backend.app.models.document import Document
from backend.app.core.logging import logger
from backend.app.core.config import settings

_LEXICAL_STOPWORDS: Set[str] = {
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and",
    "any", "are", "aren't", "as", "at", "be", "because", "been", "before", "being",
    "below", "between", "both", "but", "by", "can", "can't", "cannot", "could",
    "couldn't", "did", "didn't", "do", "does", "doesn't", "doing", "don't", "down",
    "during", "each", "few", "for", "from", "further", "had", "hadn't", "has",
    "hasn't", "have", "haven't", "having", "he", "her", "here", "hers", "him",
    "his", "how", "i", "if", "in", "into", "is", "isn't", "it", "its", "just",
    "me", "more", "most", "my", "myself", "no", "nor", "not", "of", "off", "on",
    "once", "only", "or", "other", "our", "ours", "out", "over", "own", "same",
    "should", "so", "some", "such", "than", "that", "the", "their", "theirs", "them",
    "then", "there", "these", "they", "this", "those", "through", "to", "too",
    "under", "until", "up", "very", "was", "wasn't", "we", "were", "what", "when",
    "where", "which", "while", "who", "whom", "why", "will", "with", "would",
    "you", "your", "yours", "tell", "give", "please", "know", "show", "find"
}


def _tokenize_text(text: str) -> List[str]:
    """Extract alphanumeric, underscore, and hyphen tokens normalized to lower case."""
    if not text:
        return []
    return re.findall(r"\b[a-zA-Z0-9_\-]{2,}\b", text.lower())



class VectorRepository:
    """Repository handling dense vector similarity and sparse lexical search over document chunks."""

    @staticmethod
    def cosine_similarity(vec_a: List[float], vec_b: List[float]) -> float:
        """Compute cosine similarity between two float vectors."""
        if not vec_a or not vec_b or len(vec_a) != len(vec_b):
            return 0.0
        a = np.array(vec_a, dtype=np.float32)
        b = np.array(vec_b, dtype=np.float32)
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        if norm_a == 0.0 or norm_b == 0.0:
            return 0.0
        return float(np.dot(a, b) / (norm_a * norm_b))

    def similarity_search(
        self,
        query_vector: List[float],
        workspace_id: str,
        top_k: int,
        db: Session,
        document_id: Optional[str] = None,
    ) -> List[Tuple[Chunk, float]]:
        """
        Execute dense vector similarity search scoped to workspace.
        Uses native pgvector if on PostgreSQL, or vectorized NumPy fallback on SQLite.
        Returns list of (Chunk, similarity_score) sorted descending by score.
        """
        dialect_name = db.bind.dialect.name if db.bind else ""
        
        if dialect_name == "postgresql":
            try:
                # Native PostgreSQL pgvector cosine distance: 1 - (embedding <=> query)
                # Select all chunk fields to avoid N+1 queries
                # Cast the query vector to vector type for pgvector
                query_str = """
                    SELECT c.id, c.document_id, c.workspace_id, c.chunk_index, 
                           c.content, c.chunk_metadata, c.embedding, c.created_at,
                           1 - (c.embedding <=> CAST(:query_vec AS vector)) AS score
                    FROM chunks c
                    WHERE c.workspace_id = :workspace_id
                """
                params = {"query_vec": query_vector, "workspace_id": workspace_id, "top_k": top_k}
                if document_id:
                    query_str += " AND c.document_id = :document_id"
                    params["document_id"] = document_id
                query_str += " ORDER BY c.embedding <=> CAST(:query_vec AS vector) ASC LIMIT :top_k"
                
                rows = db.execute(text(query_str), params).fetchall()
                results = []
                for row in rows:
                    # Construct Chunk object from row data (avoid N+1 query)
                    chunk = Chunk(
                        id=row[0],
                        document_id=row[1],
                        workspace_id=row[2],
                        chunk_index=row[3],
                        content=row[4],
                        chunk_metadata=row[5] or {},
                        embedding=row[6],
                        created_at=row[7],
                    )
                    results.append((chunk, float(row[8])))
                return results
            except Exception as e:
                logger.warning(f"Native pgvector search failed ({e}), falling back to in-memory similarity")

        # Fallback for SQLite or local testing
        query = db.query(Chunk).filter(Chunk.workspace_id == workspace_id)
        if document_id:
            query = query.filter(Chunk.document_id == document_id)
        chunks = query.all()

        scored_chunks: List[Tuple[Chunk, float]] = []
        for ch in chunks:
            if ch.embedding:
                score = self.cosine_similarity(query_vector, ch.embedding)
                scored_chunks.append((ch, score))

        scored_chunks.sort(key=lambda x: x[1], reverse=True)
        return scored_chunks[:top_k]

    def sparse_search(
        self,
        query: str,
        workspace_id: str,
        top_k: int,
        db: Session,
        document_id: Optional[str] = None,
    ) -> List[Tuple[Chunk, float]]:
        """
        Execute sparse lexical BM25-style keyword search over chunk contents.
        Returns list of (Chunk, bm25_score) sorted descending.
        """
        raw_tokens = _tokenize_text(query)
        filtered_terms = [t for t in raw_tokens if t not in _LEXICAL_STOPWORDS and len(t) > 2]
        terms = filtered_terms if filtered_terms else raw_tokens
        if not terms:
            terms = [query.lower().strip()]

        base_query = db.query(Chunk).filter(Chunk.workspace_id == workspace_id)
        if document_id:
            base_query = base_query.filter(Chunk.document_id == document_id)
        chunks = base_query.all()

        if not chunks:
            return []

        # Simple BM25 scoring implementation
        # N = total chunks
        N = len(chunks)
        # Calculate document frequency (DF) for each query term
        df = {t: 0 for t in terms}
        chunk_words_list = []
        avg_doc_len = 0.0

        for ch in chunks:
            words = _tokenize_text(ch.content)
            chunk_words_list.append(words)
            avg_doc_len += len(words)
            word_set = set(words)
            for t in terms:
                if t in word_set:
                    df[t] += 1

        avg_doc_len = avg_doc_len / max(1, N)
        k1 = 1.5
        b = 0.75

        scored_chunks: List[Tuple[Chunk, float]] = []
        for ch, words in zip(chunks, chunk_words_list):
            doc_len = len(words)
            score = 0.0
            word_counts = {}
            for w in words:
                word_counts[w] = word_counts.get(w, 0) + 1

            for t in terms:
                n_t = df[t]
                if n_t == 0:
                    continue
                # IDF
                idf = math.log((N - n_t + 0.5) / (n_t + 0.5) + 1.0)
                # Term Frequency in this doc
                tf = word_counts.get(t, 0)
                # BM25 weight
                num = tf * (k1 + 1.0)
                denom = tf + k1 * (1.0 - b + b * (doc_len / avg_doc_len))
                score += idf * (num / max(0.001, denom))

            if score > 0:
                scored_chunks.append((ch, score))

        scored_chunks.sort(key=lambda x: x[1], reverse=True)
        return scored_chunks[:top_k]


vector_repo = VectorRepository()

