"""Grounding verification, claim-level validation, abstention parsing, and anti-hallucination checks."""
import re
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Set, Tuple


_EVIDENCE_ECHO_PATTERNS = [
    re.compile(r"^\s*<untrusted_document_context>.*?</untrusted_document_context>\s*", re.DOTALL | re.IGNORECASE),
    re.compile(r"\[Document:[^\]]+\]\s*", re.IGNORECASE),
    re.compile(r"^\s*(?:chunk_id|document_id)\s*=\s*[a-f0-9\-]+.*$", re.MULTILINE | re.IGNORECASE),
]

_ABSTENTION_PATTERNS = [
    r"ABSTAIN:\s*insufficient_evidence",
    r"insufficient\s+evidence",
    r"does\s+not\s+contain\s+(sufficient|enough)\s+information",
    r"cannot\s+be\s+determined\s+from\s+the\s+provided\s+context",
    r"provided\s+document\s+context\s+does\s+not\s+contain",
    r"not\s+enough\s+information\s+in\s+the\s+indexed\s+documents",
]

_DATE_PATTERN = re.compile(r"\b\d{4}[-/]\d{1,2}[-/]\d{1,2}\b")
_NUMERIC_WITH_UNITS_PATTERN = re.compile(
    r"\b(\d+(?:\.\d+)?(?:\s*(?:ms|s|connections|nodes|mb|gb|tb|kb|pods|%|bit|key|rsa|sha))?)\b",
    re.IGNORECASE,
)
_URL_PATTERN = re.compile(r"https?://[^\s)\]]+", re.IGNORECASE)
_SENTENCE_SPLIT_PATTERN = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9])")


@dataclass
class GroundedClaim:
    """Individual atomic proposition evaluated against retrieved context."""
    claim_text: str
    is_grounded: bool
    cited_markers: List[str]
    supporting_chunks: List[str] = field(default_factory=list)
    unsupported_reasons: List[str] = field(default_factory=list)


@dataclass
class GroundingVerificationResult:
    """Complete evaluation of answer grounding against context."""
    is_grounded: bool
    verified_answer: str
    grounding_score: float
    hallucination_rate: float
    ungrounded_claims: List[str]
    claims: List[GroundedClaim]
    should_abstain: bool
    stripped_evidence_echo: bool = False


def is_model_abstention(text: str) -> bool:
    """Detect whether text represents an explicit abstention signal due to insufficient evidence."""
    for pattern in _ABSTENTION_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            return True
    return False


def strip_evidence_echo(text: str) -> str:
    """
    Remove prompt internals (e.g. leaked <untrusted_document_context> tags or raw chunk headers)
    that the LLM may accidentally echo into its reply.
    """
    cleaned = text
    for pat in _EVIDENCE_ECHO_PATTERNS:
        cleaned = pat.sub("", cleaned)
    return re.sub(r"\n{3,}", "\n\n", cleaned).strip()


def extract_claims(answer: str) -> List[str]:
    """Break answer text into distinct factual sentences/propositions."""
    clean_text = strip_evidence_echo(answer)
    # Remove markdown headers and list bullets from sentence boundary detection
    lines = clean_text.split("\n")
    sentences: List[str] = []
    for line in lines:
        line_clean = line.strip()
        if not line_clean or line_clean.startswith("#"):
            continue
        # Split on sentence terminals
        parts = _SENTENCE_SPLIT_PATTERN.split(line_clean)
        for part in parts:
            p_strip = part.strip()
            if len(p_strip) > 15:
                sentences.append(p_strip)
    return sentences if sentences else [clean_text] if clean_text else []


def find_ungrounded_claims(answer: str, context_chunks: List[str]) -> List[str]:
    """
    Deterministic anti-hallucination guard.
    Verifies that dates, specific numerical metrics, and URLs in the answer literally appear in context.
    """
    corpus = " ".join(context_chunks).lower()
    ungrounded: List[str] = []

    # 1. Extract dates (e.g. 2026-03-15)
    dates = _DATE_PATTERN.findall(answer)
    found_dates = set()
    for d in dates:
        found_dates.add(d)
        if d.lower() not in corpus:
            ungrounded.append(f"Date '{d}' not found in source evidence")

    # 2. Extract technical numbers with units or metrics
    num_matches = _NUMERIC_WITH_UNITS_PATTERN.findall(answer)
    for num_expr in num_matches:
        clean_expr = num_expr.strip().lower()
        # Skip markers, small ordinals, or sub-numbers that are part of an extracted date
        if clean_expr in ("0", "1", "2", "3", "4", "5", "10", "15", "104", "c_0", "c_1", "c_2", "c_3", "c_4"):
            continue
        # If the number is part of a verified date, skip
        if any(clean_expr in d for d in found_dates):
            continue
        if len(clean_expr) > 1 and clean_expr not in corpus:
            base_num = re.sub(r"[^\d.]", "", clean_expr)
            if base_num and base_num not in corpus:
                ungrounded.append(f"Metric or number '{num_expr}' not found in source evidence")

    # 3. Extract URLs
    urls = _URL_PATTERN.findall(answer)
    for url in urls:
        if url.lower() not in corpus:
            ungrounded.append(f"URL '{url}' not found in source evidence")

    return list(set(ungrounded))


def verify_claim_grounding(
    answer: str,
    context_chunks: List[str],
    chunk_marker_map: Optional[Dict[str, str]] = None,
) -> GroundingVerificationResult:
    """
    Comprehensive claim-level grounding verification.
    1. Extracts individual factual proposition sentences.
    2. Validates that citations [c_X] genuinely match content in chunk X.
    3. Runs entity/numeric verification.
    4. Applies controlled policy: preserves valid claims, purges ungrounded sentences,
       or triggers safe abstention if the core response is ungrounded.
    """
    if is_model_abstention(answer):
        return GroundingVerificationResult(
            is_grounded=True,
            verified_answer=answer,
            grounding_score=1.0,
            hallucination_rate=0.0,
            ungrounded_claims=[],
            claims=[],
            should_abstain=True,
            stripped_evidence_echo=False,
        )

    # 1. Strip prompt echo
    clean_answer = strip_evidence_echo(answer)
    echo_stripped = (clean_answer != answer)

    # 2. Extract deterministic ungrounded entities/numbers
    ungrounded_facts = find_ungrounded_claims(clean_answer, context_chunks)

    # 3. Break into sentences and verify claim attribution
    sentences = extract_claims(clean_answer)
    corpus = " ".join(context_chunks).lower()
    
    evaluated_claims: List[GroundedClaim] = []
    grounded_sentences: List[str] = []
    
    for sentence in sentences:
        markers = re.findall(r"\[(c_\d+)\]", sentence)
        claim_ungrounded_reasons: List[str] = []
        
        # Check if sentence has any of the ungrounded facts
        for u in ungrounded_facts:
            # Extract literal token (e.g. "Date '2026-03-15' not found..." -> "2026-03-15")
            token_match = re.search(r"'([^']+)'", u)
            if token_match and token_match.group(1).lower() in sentence.lower():
                claim_ungrounded_reasons.append(u)

        # Check citation alignment: if marker [c_X] is present, does chunk X support it?
        supporting_chunks = []
        if chunk_marker_map and markers:
            for m in markers:
                chunk_text = chunk_marker_map.get(f"[{m}]") or chunk_marker_map.get(m, "")
                if chunk_text:
                    # Check word overlap between sentence and cited chunk
                    sent_words = set(re.findall(r"\b[a-zA-Z0-9]{3,}\b", sentence.lower()))
                    chunk_words = set(re.findall(r"\b[a-zA-Z0-9]{3,}\b", chunk_text.lower()))
                    overlap = len(sent_words & chunk_words)
                    if overlap >= 2:
                        supporting_chunks.append(m)
                    else:
                        claim_ungrounded_reasons.append(f"Citation [{m}] lacks textual support for claim")

        is_claim_grounded = (len(claim_ungrounded_reasons) == 0)
        evaluated_claims.append(GroundedClaim(
            claim_text=sentence,
            is_grounded=is_claim_grounded,
            cited_markers=markers,
            supporting_chunks=supporting_chunks,
            unsupported_reasons=claim_ungrounded_reasons,
        ))

        if is_claim_grounded:
            grounded_sentences.append(sentence)

    total_claims = max(1, len(evaluated_claims))
    grounded_count = sum(1 for c in evaluated_claims if c.is_grounded)
    grounding_score = round(grounded_count / total_claims, 4)
    hallucination_rate = round(len(ungrounded_facts) / total_claims, 4)

    # Policy Enforcement:
    # If more than 50% of claims are ungrounded or severe numeric hallucinations exist:
    if grounding_score < 0.50 or len(ungrounded_facts) >= 2:
        should_abstain = True
        verified_answer = (
            "ABSTAIN: insufficient_evidence. The synthesized response contained unverified claims "
            "or metrics that could not be established from the indexed engineering documentation."
        )
    elif grounded_sentences and len(grounded_sentences) < len(sentences):
        # Preserve verified claims and strip ungrounded statements
        should_abstain = False
        verified_answer = " ".join(grounded_sentences)
    else:
        should_abstain = False
        verified_answer = clean_answer

    return GroundingVerificationResult(
        is_grounded=(grounding_score >= 0.80 and not should_abstain),
        verified_answer=verified_answer,
        grounding_score=grounding_score,
        hallucination_rate=min(1.0, hallucination_rate),
        ungrounded_claims=ungrounded_facts,
        claims=evaluated_claims,
        should_abstain=should_abstain,
        stripped_evidence_echo=echo_stripped,
    )
