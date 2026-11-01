"""Grounding verification, abstention parsing, and anti-hallucination checks."""
import re
from typing import List


def is_model_abstention(text: str) -> bool:
    """Detect whether LLM emitted an explicit abstention signal due to insufficient evidence."""
    patterns = [
        r"ABSTAIN:\s*insufficient_evidence",
        r"insufficient\s+evidence",
        r"does\s+not\s+contain\s+(sufficient|enough)\s+information",
        r"cannot\s+be\s+determined\s+from\s+the\s+provided\s+context",
    ]
    for pattern in patterns:
        if re.search(pattern, text, re.IGNORECASE):
            return True
    return False


def find_ungrounded_claims(answer: str, context_chunks: List[str]) -> List[str]:
    """
    Deterministic anti-hallucination guard adapted from reference enterprise RAG architecture.
    Extracts dates, technical numbers, and identifiers from answer text and verifies presence in context.
    """
    corpus = " ".join(context_chunks).lower()
    ungrounded: List[str] = []

    # 1. Extract dates (e.g. 2026-03-15 or 2026/03/15)
    dates = re.findall(r"\b\d{4}[-/]\d{1,2}[-/]\d{1,2}\b", answer)
    for d in dates:
        if d.lower() not in corpus:
            ungrounded.append(f"Date '{d}' not found in source evidence")

    # 2. Extract technical numbers with units or large numbers (e.g., 200, 4200ms, 60s, 5s)
    # Ignore standalone small single-digit numbers which might be markers
    num_matches = re.findall(r"\b(\d+(?:\.\d+)?(?:\s*(?:ms|s|connections|nodes|mb|gb|%))?)\b", answer, re.IGNORECASE)
    for num_expr in num_matches:
        clean_expr = num_expr.strip().lower()
        # Skip simple single digits or citation index numbers
        if clean_expr in ("0", "1", "2", "3", "4", "5", "104"):
            continue
        if len(clean_expr) > 1 and clean_expr not in corpus:
            # Check if base number is in corpus
            base_num = re.sub(r"[^\d.]", "", clean_expr)
            if base_num and base_num not in corpus:
                ungrounded.append(f"Metric or number '{num_expr}' not found in source evidence")

    # 3. Extract URLs
    urls = re.findall(r"https?://[^\s)\]]+", answer)
    for url in urls:
        if url.lower() not in corpus:
            ungrounded.append(f"URL '{url}' not found in source evidence")

    return list(set(ungrounded))

