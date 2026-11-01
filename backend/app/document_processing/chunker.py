"""Recursive Character and Semantic Document Chunker."""
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from backend.app.core.config import settings
from backend.app.document_processing.parsers import ParsedBlock


@dataclass
class ProcessedChunk:
    """Standardized document chunk ready for embedding and indexing."""
    chunk_index: int
    content: str
    metadata: Dict[str, Any]


class DocumentChunker:
    """Splits structured parsed document blocks into semantically coherent overlapping chunks."""

    def __init__(
        self,
        chunk_size: int = settings.CHUNK_SIZE,
        chunk_overlap: int = settings.CHUNK_OVERLAP,
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.separators = ["\n\n", "\n", ". ", "? ", "! ", "; ", " ", ""]

    @staticmethod
    def estimate_tokens(text: str) -> int:
        """Estimate token count with fallback heuristic."""
        try:
            import tiktoken
            enc = tiktoken.get_encoding("cl100k_base")
            return len(enc.encode(text))
        except Exception:
            return max(1, len(text) // 4)

    def _split_text_recursive(self, text: str, separators: List[str]) -> List[str]:
        """Recursively divide text using priority separator hierarchy."""
        final_chunks: List[str] = []
        separator = separators[-1]
        new_separators = []

        for i, sep in enumerate(separators):
            if sep == "":
                separator = ""
                break
            if sep in text:
                separator = sep
                new_separators = separators[i + 1:]
                break

        splits = text.split(separator) if separator else list(text)
        good_splits: List[str] = []

        for s in splits:
            if not s.strip():
                continue
            if len(s) < self.chunk_size:
                good_splits.append(s)
            else:
                if new_separators:
                    sub_splits = self._split_text_recursive(s, new_separators)
                    good_splits.extend(sub_splits)
                else:
                    # Character slice fallback
                    for idx in range(0, len(s), self.chunk_size - self.chunk_overlap):
                        good_splits.append(s[idx:idx + self.chunk_size])

        # Merge adjacent small splits up to chunk_size with overlap
        current_chunk: List[str] = []
        current_len = 0

        for s in good_splits:
            add_len = len(s) + (len(separator) if current_chunk else 0)
            if current_len + add_len > self.chunk_size:
                if current_chunk:
                    merged = separator.join(current_chunk).strip()
                    if merged:
                        final_chunks.append(merged)
                    
                    # Overlap handling: keep end splits that fit overlap budget
                    overlap_splits = []
                    overlap_len = 0
                    for prev in reversed(current_chunk):
                        if overlap_len + len(prev) <= self.chunk_overlap:
                            overlap_splits.insert(0, prev)
                            overlap_len += len(prev)
                        else:
                            break
                    current_chunk = overlap_splits
                    current_len = sum(len(x) for x in current_chunk)

            current_chunk.append(s)
            current_len += len(s)

        if current_chunk:
            merged = separator.join(current_chunk).strip()
            if merged:
                final_chunks.append(merged)

        return final_chunks

    def chunk_blocks(self, blocks: List[ParsedBlock]) -> List[ProcessedChunk]:
        """Chunk a list of parsed document blocks preserving page & section metadata."""
        all_chunks: List[ProcessedChunk] = []
        chunk_counter = 0

        for block in blocks:
            raw_text = block.text.strip()
            if not raw_text:
                continue

            # If small enough, keep as single chunk
            if len(raw_text) <= self.chunk_size:
                chunks_text = [raw_text]
            else:
                chunks_text = self._split_text_recursive(raw_text, self.separators)

            for text_piece in chunks_text:
                if not text_piece.strip():
                    continue

                chunk_meta = {
                    "page_number": block.page_number,
                    "section_header": block.section_header,
                    "heading": block.section_header,
                    "token_count": self.estimate_tokens(text_piece),
                    **block.metadata,
                }

                all_chunks.append(
                    ProcessedChunk(
                        chunk_index=chunk_counter,
                        content=text_piece,
                        metadata=chunk_meta,
                    )
                )
                chunk_counter += 1

        return all_chunks


document_chunker = DocumentChunker()

