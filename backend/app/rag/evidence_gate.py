"""Evidence Sufficiency Gate and Conflict Detection for Grounded Enterprise RAG."""
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Any, Optional, Set, Tuple

from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.retrieval.hybrid import RetrievedChunk


class EvidenceDecision(str, Enum):
    """Possible outcomes of pre-generation evidence assessment."""
    SUFFICIENT = "SUFFICIENT"
    INSUFFICIENT = "INSUFFICIENT"
    CONFLICTING = "CONFLICTING"
    NEEDS_CLARIFICATION = "NEEDS_CLARIFICATION"


class EvidenceRole(str, Enum):
    """Classification of chunk relevance to the query."""
    PRIMARY = "PRIMARY"
    SUPPLEMENTARY = "SUPPLEMENTARY"
    IRRELEVANT = "IRRELEVANT"


_STOPWORDS: Set[str] = {
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and",
    "any", "are", "aren't", "as", "at", "be", "because", "been", "before", "being",
    "below", "between", "both", "but", "by", "can", "can't", "cannot", "could",
    "couldn't", "did", "didn't", "do", "does", "doesn't", "doing", "don't", "down",
    "during", "each", "few", "for", "from", "further", "had", "hadn't", "has",
    "hasn't", "have", "haven't", "having", "he", "he'd", "he'll", "he's", "her",
    "here", "here's", "hers", "herself", "him", "himself", "his", "how", "how's",
    "i", "i'd", "i'll", "i'm", "i've", "if", "in", "into", "is", "isn't", "it",
    "it's", "its", "itself", "let's", "me", "more", "most", "mustn't", "my",
    "myself", "no", "nor", "not", "of", "off", "on", "once", "only", "or",
    "other", "ought", "our", "ours", "ourselves", "out", "over", "own", "same",
    "shan't", "she", "she'd", "she'll", "she's", "should", "shouldn't", "so",
    "some", "such", "than", "that", "that's", "the", "their", "theirs", "them",
    "themselves", "then", "there", "there's", "these", "they", "they'd", "they'll",
    "they're", "they've", "this", "those", "through", "to", "too", "under", "until",
    "up", "very", "was", "wasn't", "we", "we'd", "we'll", "we're", "we've", "were",
    "weren't", "what", "what's", "when", "when's", "where", "where's", "which",
    "while", "who", "who's", "whom", "why", "why's", "with", "won't", "would",
    "wouldn't", "you", "you'd", "you'll", "you're", "you've", "your", "yours",
    "yourself", "yourselves",
}

_NUMBER_PATTERN = re.compile(r"\b\d+(?:\.\d+)?(?:ms|s|m|h|%|mb|gb|tb|kb|connections|nodes|pods)?\b", re.IGNORECASE)
_DATE_PATTERN = re.compile(r"\b\d{4}[-/]\d{1,2}[-/]\d{1,2}\b")


@dataclass
class ScoredEvidenceChunk:
    """Retrieved chunk evaluated against query relevance signals."""
    chunk: RetrievedChunk
    role: EvidenceRole
    score: float
    query_coverage: float
    lexical_overlap: float
    matched_terms: List[str]
    has_heading_match: bool


@dataclass
class ConflictDetail:
    """Details of factual conflict detected between evidence sources."""
    has_conflict: bool = False
    conflict_type: str = ""
    description: str = ""
    competing_claims: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class EvidenceAssessment:
    """Complete pre-generation evaluation of retrieved evidence."""
    decision: EvidenceDecision
    confidence_score: float
    primary_chunks: List[RetrievedChunk]
    supplementary_chunks: List[RetrievedChunk]
    discarded_chunks: List[RetrievedChunk]
    scored_chunks: List[ScoredEvidenceChunk]
    conflict: Optional[ConflictDetail] = None
    rationale: str = ""

    @property
    def chunks_for_context(self) -> List[RetrievedChunk]:
        """Return non-irrelevant chunks ordered by relevance for context injection."""
        return self.primary_chunks + self.supplementary_chunks

    @property
    def is_sufficient(self) -> bool:
        return self.decision == EvidenceDecision.SUFFICIENT

    @property
    def is_conflicting(self) -> bool:
        return self.decision == EvidenceDecision.CONFLICTING

    @property
    def is_insufficient(self) -> bool:
        return self.decision == EvidenceDecision.INSUFFICIENT


class EvidenceSufficiencyGate:
    """
    Evaluates evidence sufficiency and detects conflicting information before LLM generation.
    Prevents generation when evidence is missing, distractor-only, or fundamentally contradictory.
    """

    def __init__(
        self,
        primary_threshold: Optional[float] = None,
        supplementary_threshold: Optional[float] = None,
        min_query_coverage: Optional[float] = None,
    ):
        self.primary_threshold = primary_threshold or getattr(settings, "EVIDENCE_PRIMARY_THRESHOLD", 0.35)
        self.supplementary_threshold = supplementary_threshold or getattr(settings, "EVIDENCE_SUPPLEMENTARY_THRESHOLD", 0.20)
        self.min_query_coverage = min_query_coverage or getattr(settings, "EVIDENCE_MIN_QUERY_COVERAGE", 0.25)

    def extract_query_terms(self, query: str) -> List[str]:
        """Extract meaningful semantic tokens from query, filtering out English stopwords."""
        tokens = re.findall(r"\b[a-zA-Z0-9_\-]{2,}\b", query.lower())
        meaningful = [t for t in tokens if t not in _STOPWORDS and len(t) > 2]
        return meaningful if meaningful else tokens

    def assess_evidence(
        self,
        query: str,
        retrieved_chunks: List[RetrievedChunk],
    ) -> EvidenceAssessment:
        """
        Evaluate retrieved evidence against query to determine if sufficient for grounded generation.
        """
        if not retrieved_chunks:
            return EvidenceAssessment(
                decision=EvidenceDecision.INSUFFICIENT,
                confidence_score=0.0,
                primary_chunks=[],
                supplementary_chunks=[],
                discarded_chunks=[],
                scored_chunks=[],
                rationale="Zero document chunks were retrieved for the inquiry.",
            )

        query_terms = self.extract_query_terms(query)
        if not query_terms:
            query_terms = [query.lower()]

        scored_chunks: List[ScoredEvidenceChunk] = []
        for r_chunk in retrieved_chunks:
            scored = self._score_chunk(query, query_terms, r_chunk)
            scored_chunks.append(scored)

        # Sort chunks descending by computed score
        scored_chunks.sort(key=lambda x: x.score, reverse=True)

        primary = [s.chunk for s in scored_chunks if s.role == EvidenceRole.PRIMARY]
        supplementary = [s.chunk for s in scored_chunks if s.role == EvidenceRole.SUPPLEMENTARY]
        discarded = [s.chunk for s in scored_chunks if s.role == EvidenceRole.IRRELEVANT]

        # Calculate overall query coverage across all candidate chunks
        all_matched_terms: Set[str] = set()
        for s in scored_chunks:
            if s.role != EvidenceRole.IRRELEVANT:
                all_matched_terms.update(s.matched_terms)
        total_query_coverage = len(all_matched_terms) / max(1, len(query_terms))

        # Check for factual conflicts in primary evidence
        conflict = self._detect_conflicts(query, primary)

        # Compute aggregate confidence score
        if primary:
            best_score = max(s.score for s in scored_chunks if s.role == EvidenceRole.PRIMARY)
            confidence = round(min(1.0, (best_score * 0.6) + (total_query_coverage * 0.4)), 4)
        else:
            confidence = round(total_query_coverage * 0.3, 4)

        # Determine decision
        if conflict.has_conflict:
            decision = EvidenceDecision.CONFLICTING
            rationale = f"Conflicting evidence detected across retrieved documents: {conflict.description}"
        elif len(primary) == 0 or total_query_coverage < self.min_query_coverage:
            decision = EvidenceDecision.INSUFFICIENT
            rationale = (
                f"Retrieved context does not contain sufficient verified facts for query. "
                f"Query term coverage: {total_query_coverage:.1%}, Primary chunks: {len(primary)}."
            )
        elif total_query_coverage < 0.40 and len(primary) == 1:
            decision = EvidenceDecision.NEEDS_CLARIFICATION
            rationale = "Retrieved evidence only partially covers the question requirements."
        else:
            decision = EvidenceDecision.SUFFICIENT
            rationale = f"Found {len(primary)} primary and {len(supplementary)} supplementary evidence chunks."

        return EvidenceAssessment(
            decision=decision,
            confidence_score=confidence,
            primary_chunks=primary,
            supplementary_chunks=supplementary,
            discarded_chunks=discarded,
            scored_chunks=scored_chunks,
            conflict=conflict if conflict.has_conflict else None,
            rationale=rationale,
        )

    def _score_chunk(
        self,
        query: str,
        query_terms: List[str],
        r_chunk: RetrievedChunk,
    ) -> ScoredEvidenceChunk:
        """Compute multi-signal evidence score for a single chunk."""
        content = r_chunk.chunk.content.lower()
        title = (r_chunk.document_title or "").lower()
        meta = r_chunk.chunk.chunk_metadata or {}
        heading = str(meta.get("heading", "")).lower()

        # Signal 1: Query Term Coverage
        matched_terms = [t for t in query_terms if t in content or t in title or t in heading]
        query_coverage = len(matched_terms) / max(1, len(query_terms))

        # Signal 2: Heading & Title Match
        has_heading_match = any(t in heading or t in title for t in query_terms)

        # Signal 3: Lexical density (frequency of query terms in content)
        content_words = content.split()
        total_term_freq = sum(content.count(t) for t in query_terms)
        lexical_overlap = min(1.0, total_term_freq / max(10, len(content_words)))

        # Signal 4: Retrieval normalized score
        raw_retrieval_score = float(r_chunk.score)
        # RRF scores are typically in [0.01, 0.04]; dense cosine scores are in [0.2, 0.9]
        if raw_retrieval_score < 0.10:
            norm_retrieval = min(1.0, raw_retrieval_score * 30.0)
        else:
            norm_retrieval = min(1.0, raw_retrieval_score)

        # Signal 5: Exact phrase match
        query_clean = re.sub(r"[^\w\s]", " ", query.lower()).strip()
        phrases_matched = 0
        words = query_clean.split()
        if len(words) >= 2:
            for i in range(len(words) - 1):
                bigram = f"{words[i]} {words[i+1]}"
                if bigram in content:
                    phrases_matched += 1
        phrase_boost = min(0.15, phrases_matched * 0.05)

        # Composite evidence score
        composite_score = (
            (query_coverage * 0.45)
            + (norm_retrieval * 0.30)
            + (lexical_overlap * 0.15)
            + (0.10 if has_heading_match else 0.0)
            + phrase_boost
        )

        # Classification into roles
        if composite_score >= self.primary_threshold and query_coverage >= self.min_query_coverage:
            role = EvidenceRole.PRIMARY
        elif composite_score >= self.supplementary_threshold and query_coverage >= (self.min_query_coverage * 0.5):
            role = EvidenceRole.SUPPLEMENTARY
        else:
            role = EvidenceRole.IRRELEVANT

        return ScoredEvidenceChunk(
            chunk=r_chunk,
            role=role,
            score=round(composite_score, 4),
            query_coverage=round(query_coverage, 4),
            lexical_overlap=round(lexical_overlap, 4),
            matched_terms=matched_terms,
            has_heading_match=has_heading_match,
        )

    def _detect_conflicts(
        self,
        query: str,
        primary_chunks: List[RetrievedChunk],
    ) -> ConflictDetail:
        """
        Detect factual contradictions across primary evidence (e.g. conflicting numerical metrics
        or dates between separate documents that lack progression language).
        """
        if len(primary_chunks) < 2:
            return ConflictDetail(has_conflict=False)

        # Group numbers and dates by document title
        doc_metrics: Dict[str, Set[str]] = {}
        for chunk in primary_chunks:
            title = chunk.document_title or "Doc"
            text = chunk.chunk.content
            numbers = set(_NUMBER_PATTERN.findall(text))
            dates = set(_DATE_PATTERN.findall(text))
            doc_metrics[title] = doc_metrics.get(title, set()).union(numbers).union(dates)

        # Check for numeric contradictions between distinct documents
        doc_names = list(doc_metrics.keys())
        if len(doc_names) >= 2:
            doc_a, doc_b = doc_names[0], doc_names[1]
            diff_a = doc_metrics[doc_a] - doc_metrics[doc_b]
            diff_b = doc_metrics[doc_b] - doc_metrics[doc_a]

            # If documents reference diametrically opposed numbers for key engineering parameters
            # and no transitional phrase like "upgraded to", "migrated to", "previously" is present
            progression_cues = ["scaled", "increased", "decreased", "lowered", "migrated", "updated to", "raised to"]
            all_text = " ".join(c.chunk.content.lower() for c in primary_chunks)
            has_progression = any(cue in all_text for cue in progression_cues)

            if not has_progression and diff_a and diff_b:
                # Check if query asks for a specific conflicting parameter
                query_lower = query.lower()
                conflicting_metrics = []
                for val in (diff_a | diff_b):
                    if any(term in query_lower for term in ["how many", "timeout", "latency", "size", "limit", "port"]):
                        conflicting_metrics.append(val)
                
                if len(conflicting_metrics) >= 2:
                    return ConflictDetail(
                        has_conflict=True,
                        conflict_type="numerical",
                        description=f"Documents '{doc_a}' and '{doc_b}' assert conflicting metrics without resolution metadata: {conflicting_metrics[:4]}",
                        competing_claims=[
                            {"document": doc_a, "values": list(diff_a)[:3]},
                            {"document": doc_b, "values": list(diff_b)[:3]},
                        ],
                    )

        return ConflictDetail(has_conflict=False)


evidence_sufficiency_gate = EvidenceSufficiencyGate()

