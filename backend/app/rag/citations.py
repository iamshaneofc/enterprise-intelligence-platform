"""Short citation aliasing and resolution map."""
import re
from typing import List, Dict
from backend.app.retrieval.hybrid import RetrievedChunk
from backend.app.schemas.chat import CitationResponse


class CitationMap:
    """Maintains mapping from short LLM prompt aliases ([c_0], [c_1]) to database entities."""

    def __init__(self, retrieved_chunks: List[RetrievedChunk]):
        self._map: Dict[str, CitationResponse] = {}
        for idx, r in enumerate(retrieved_chunks):
            marker = f"[c_{idx}]"
            snippet = r.chunk.content.strip().replace("\n", " ")[:200]
            self._map[marker] = CitationResponse(
                marker=marker,
                document_id=r.chunk.document_id,
                document_title=r.document_title,
                chunk_id=r.chunk.id,
                snippet=snippet,
                score=r.score,
            )

    def resolve(self, answer_text: str) -> List[CitationResponse]:
        """Extract cited markers from answer and return matching structured citations."""
        found_markers = re.findall(r"\[c_\d+\]", answer_text)
        resolved: List[CitationResponse] = []
        seen = set()

        for marker in found_markers:
            if marker in self._map and marker not in seen:
                resolved.append(self._map[marker])
                seen.add(marker)

        return resolved

