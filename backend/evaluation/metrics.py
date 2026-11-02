"""Evaluation metrics for RAG system quality assessment."""
from typing import List, Dict, Any, Optional, Set
from dataclasses import dataclass
from collections import Counter
import json
import re
import math


@dataclass
class RetrievalMetrics:
    """Metrics for retrieval quality."""
    precision_at_k: float
    recall_at_k: float
    mrr: float  # Mean Reciprocal Rank
    ndcg_at_k: float


@dataclass
class CitationMetrics:
    """Metrics for citation quality."""
    resolution_rate: float  # Fraction of citations that resolve to valid chunks
    grounding_rate: float   # Fraction of claims with valid citations
    hallucination_rate: float  # Fraction of ungrounded claims


@dataclass
class AbstentionMetrics:
    """Metrics for abstention behavior."""
    accuracy: float
    false_abstention_rate: float  # Abstained when should have answered
    false_answer_rate: float      # Answered when should have abstained


@dataclass
class LatencyMetrics:
    """Latency and token usage metrics."""
    avg_latency_ms: float
    avg_prompt_tokens: float
    avg_completion_tokens: float
    avg_total_tokens: float


@dataclass
class EvaluationResult:
    """Complete evaluation results."""
    retrieval: RetrievalMetrics
    citation: CitationMetrics
    abstention: AbstentionMetrics
    latency: LatencyMetrics
    per_question: List[Dict[str, Any]]


_STOP_WORDS = {
    "a", "an", "the", "in", "on", "at", "to", "for", "with", "by", "of", "from",
    "and", "or", "is", "are", "was", "were", "be", "been", "being", "have", "has",
    "had", "do", "does", "did", "this", "that", "these", "those", "it", "its",
    "as", "if", "each", "all", "which", "what", "where", "when", "how", "who"
}


def _tokenize(text: str) -> List[str]:
    """Tokenize string into lowercase alphanumeric words."""
    if not text:
        return []
    return [w.lower() for w in re.findall(r'\b\w+\b', text) if w.strip()]


def _extract_content_tokens(text: str) -> set[str]:
    """Extract informative non-stopword tokens."""
    tokens = _tokenize(text)
    return {t for t in tokens if t not in _STOP_WORDS and len(t) >= 2}


def compute_context_precision(
    retrieved_contexts: List[str],
    ground_truth_context: str,
    relevance_threshold: float = 0.20,
) -> float:
    """
    Compute deterministic heuristic Context Precision@K.
    
    NOTE: This is a pure-function, deterministic lexical and entity matching metric,
    NOT an official RAGAS LLM-judge metric. It measures whether ground-truth relevant chunks
    are ranked higher in the retrieved context list without invoking external LLMs:
    Context Precision@K = sum(Precision@k * v_k) / sum(v_k)
    where v_k is binary relevance of chunk at rank k.
    
    If ground_truth_context is empty (e.g. out-of-domain / unanswerable),
    returns 1.0 (model should abstain and no context was expected).
    """
    if not ground_truth_context or not ground_truth_context.strip():
        return 1.0
    if not retrieved_contexts:
        return 0.0

    gt_tokens = _extract_content_tokens(ground_truth_context)
    if not gt_tokens:
        return 1.0

    relevant_flags = []
    for ctx in retrieved_contexts:
        ctx_tokens = _extract_content_tokens(ctx)
        if not ctx_tokens:
            relevant_flags.append(0)
            continue
        overlap = len(gt_tokens & ctx_tokens) / max(1, len(gt_tokens))
        # Check if numbers or dates in ground_truth match chunk
        gt_numbers = set(re.findall(r'\b\d+(?:[\.:-]\d+)*\b', ground_truth_context))
        ctx_numbers = set(re.findall(r'\b\d+(?:[\.:-]\d+)*\b', ctx))
        has_num_overlap = bool(gt_numbers and (gt_numbers & ctx_numbers))

        is_relevant = 1 if (overlap >= relevance_threshold or has_num_overlap) else 0
        relevant_flags.append(is_relevant)

    total_relevant = sum(relevant_flags)
    if total_relevant == 0:
        return 0.0

    precision_sum = 0.0
    running_relevant = 0
    for rank, is_rel in enumerate(relevant_flags, start=1):
        if is_rel:
            running_relevant += 1
            precision_at_k = running_relevant / rank
            precision_sum += precision_at_k

    return precision_sum / total_relevant


def compute_context_recall(
    retrieved_contexts: List[str],
    ground_truth_context: str,
    overlap_threshold: float = 0.40,
) -> float:
    """
    Compute deterministic heuristic Context Recall.
    
    NOTE: This is a pure-function, deterministic lexical overlap metric,
    NOT an official RAGAS LLM-judge metric. It measures the fraction of ground truth
    statements or sentences attributable to retrieved contexts without invoking an external LLM:
    Context Recall = (attributable GT sentences) / (total GT sentences)
    
    If ground_truth_context is empty, returns 1.0.
    """
    if not ground_truth_context or not ground_truth_context.strip():
        return 1.0
    if not retrieved_contexts:
        return 0.0

    combined_context = " ".join(retrieved_contexts).lower()
    all_ctx_tokens = set(_tokenize(combined_context))

    # Split ground truth context into sentence units
    raw_sentences = [s.strip() for s in re.split(r'[.!?;\n]+', ground_truth_context) if s.strip()]
    if not raw_sentences:
        return 1.0

    attributable = 0
    for sentence in raw_sentences:
        sent_tokens = _extract_content_tokens(sentence)
        if not sent_tokens:
            attributable += 1
            continue
        matched_tokens = sent_tokens & all_ctx_tokens
        coverage = len(matched_tokens) / len(sent_tokens)
        
        # Check numbers
        sent_numbers = set(re.findall(r'\b\d+(?:[\.:-]\d+)*\b', sentence))
        num_matched = True
        if sent_numbers:
            ctx_numbers = set(re.findall(r'\b\d+(?:[\.:-]\d+)*\b', combined_context))
            num_matched = bool(sent_numbers & ctx_numbers)

        if coverage >= overlap_threshold and num_matched:
            attributable += 1

    return attributable / len(raw_sentences)


def compute_f1_token_overlap(
    prediction: str,
    ground_truth: str,
    is_abstention: bool = False,
    expected_to_abstain: bool = False,
) -> float:
    """
    Compute token-level F1 score between prediction and ground truth.
    
    Properly accounts for abstention:
    - If expected to abstain and prediction abstained: F1 = 1.0
    - If expected to abstain and prediction did not abstain: F1 = 0.0
    - If not expected to abstain and prediction abstained: F1 = 0.0
    - Otherwise: standard harmonic mean of token precision and recall.
    """
    if expected_to_abstain:
        return 1.0 if is_abstention else 0.0
    if is_abstention and not expected_to_abstain:
        return 0.0
    if not ground_truth or not ground_truth.strip():
        return 1.0 if is_abstention else 0.0

    pred_tokens = _tokenize(prediction)
    gt_tokens = _tokenize(ground_truth)

    if not pred_tokens and not gt_tokens:
        return 1.0
    if not pred_tokens or not gt_tokens:
        return 0.0

    pred_counter = Counter(pred_tokens)
    gt_counter = Counter(gt_tokens)

    common_count = sum((pred_counter & gt_counter).values())
    if common_count == 0:
        return 0.0

    precision = common_count / len(pred_tokens)
    recall = common_count / len(gt_tokens)
    return 2.0 * (precision * recall) / (precision + recall)


def compute_ir_metrics(
    relevance_vector: List[int],
    k: int = 5,
    total_relevant: Optional[int] = None,
) -> Dict[str, float]:
    """
    Pure mathematical Information Retrieval evaluation.
    
    Formulations:
    - Precision@K = (Relevant Retrieved Items in Top K) / K
      Denominator is fixed cutoff K. If fewer than K items are retrieved,
      the unretrieved slots are treated as non-relevant.
    - Recall@K = (Relevant Retrieved Items in Top K) / Total Relevant Items
      Denominator is total_relevant in the corpus. If total_relevant == 0 (e.g. unanswerable),
      returns 0.0.
    - MRR (Mean Reciprocal Rank) = 1 / rank of the first relevant retrieved item in Top K,
      or 0.0 if no relevant items retrieved in Top K.
    - NDCG@K = DCG@K / IDCG@K
      DCG@K = sum((2^rel - 1) / log2(rank + 1))
      IDCG@K = sum(1.0 / log2(rank + 1)) for rank in 1..min(K, total_relevant).
      If IDCG@K == 0, returns 0.0.
    """
    if k <= 0 or not relevance_vector:
        return {
            "precision_at_k": 0.0,
            "recall_at_k": 0.0,
            "mrr": 0.0,
            "ndcg_at_k": 0.0,
        }

    top_k_rel = relevance_vector[:k]
    relevant_retrieved = sum(1 for r in top_k_rel if r > 0)

    # 1. Precision@K
    precision_at_k = relevant_retrieved / k

    # 2. Recall@K
    if total_relevant is None:
        total_relevant = max(1, sum(1 for r in relevance_vector if r > 0))

    if total_relevant <= 0:
        recall_at_k = 0.0
    else:
        recall_at_k = min(1.0, relevant_retrieved / total_relevant)

    # 3. MRR (Reciprocal Rank)
    mrr = 0.0
    for rank, r in enumerate(top_k_rel, start=1):
        if r > 0:
            mrr = 1.0 / rank
            break

    # 4. NDCG@K
    dcg = sum((math.pow(2, r) - 1.0) / math.log2(rank + 1) for rank, r in enumerate(top_k_rel, start=1))
    ideal_num = min(k, total_relevant) if total_relevant > 0 else 0
    idcg = sum(1.0 / math.log2(rank + 1) for rank in range(1, ideal_num + 1))
    ndcg_at_k = (dcg / idcg) if idcg > 0.0 else 0.0

    return {
        "precision_at_k": round(precision_at_k, 6),
        "recall_at_k": round(recall_at_k, 6),
        "mrr": round(mrr, 6),
        "ndcg_at_k": round(ndcg_at_k, 6),
    }


def evaluate_retrieval_precision(
    retrieved_chunks: List[Dict[str, Any]],
    expected_citations: Optional[List[str]] = None,
    top_k: int = 5,
    ground_truth_context: Optional[str] = None,
    relevant_chunk_ids: Optional[Set[str]] = None,
    relevance_scores: Optional[List[float]] = None,
    total_relevant: Optional[int] = None,
    relevance_threshold: float = 0.20,
) -> Dict[str, float]:
    """
    Evaluate retrieval precision, recall, MRR, and NDCG using exact Information Retrieval mathematics.
    
    Relevance Determination:
    1. If `relevance_scores` is given: items with score >= relevance_threshold are marked relevant (1).
    2. If `relevant_chunk_ids` is given: chunks whose chunk_id is in the set are relevant (1).
    3. If `ground_truth_context` is given: content token overlap >= relevance_threshold or shared numbers/dates.
    4. If only `expected_citations` is given: markers like '[c_0]' map to rank indices, or match chunk_id.
    
    Returns:
        Dict with precision_at_k, recall_at_k, mrr, ndcg_at_k, and diagnostic breakdown.
    """
    if not retrieved_chunks or top_k <= 0:
        return {
            "precision_at_k": 0.0,
            "recall_at_k": 0.0,
            "mrr": 0.0,
            "ndcg_at_k": 0.0,
        }

    top_chunks = retrieved_chunks[:top_k]
    rel_vector: List[int] = []

    # Strategy 1: Explicit relevance scores provided
    if relevance_scores is not None:
        rel_vector = [1 if (s >= relevance_threshold or s >= 1.0) else 0 for s in relevance_scores[:top_k]]
        if total_relevant is None:
            total_relevant = max(1, sum(1 for s in relevance_scores if (s >= relevance_threshold or s >= 1.0)))

    # Strategy 2: Explicit set of relevant chunk IDs provided
    elif relevant_chunk_ids is not None:
        for ch in top_chunks:
            cid = ch.get("chunk_id", "")
            rel_vector.append(1 if cid in relevant_chunk_ids else 0)
        if total_relevant is None:
            total_relevant = len(relevant_chunk_ids)

    # Strategy 3: Ground-truth reference context provided
    elif ground_truth_context and ground_truth_context.strip():
        gt_tokens = _extract_content_tokens(ground_truth_context)
        gt_numbers = set(re.findall(r'\b\d+(?:[\.:-]\d+)*\b', ground_truth_context))

        for ch in top_chunks:
            content = ch.get("content", "")
            ctx_tokens = _extract_content_tokens(content)
            overlap = len(gt_tokens & ctx_tokens) / max(1, len(gt_tokens)) if gt_tokens else 0.0
            ctx_numbers = set(re.findall(r'\b\d+(?:[\.:-]\d+)*\b', content))
            has_num_overlap = bool(gt_numbers and (gt_numbers & ctx_numbers))
            is_rel = 1 if (overlap >= relevance_threshold or has_num_overlap) else 0
            rel_vector.append(is_rel)

        if total_relevant is None:
            total_relevant = max(1, sum(rel_vector))

    # Strategy 4: Citation markers / expected citations fallback
    elif expected_citations:
        expected_set = set(expected_citations)
        for idx, ch in enumerate(top_chunks):
            cid = ch.get("chunk_id", "")
            marker = f"[c_{idx}]"
            is_rel = 1 if (marker in expected_set or cid in expected_set) else 0
            rel_vector.append(is_rel)
        if total_relevant is None:
            total_relevant = len(expected_citations)

    # Strategy 5: No ground truth context or citations provided (unanswerable / empty)
    else:
        rel_vector = [0] * len(top_chunks)
        if total_relevant is None:
            total_relevant = 0

    return compute_ir_metrics(rel_vector, k=top_k, total_relevant=total_relevant)


def evaluate_citation_accuracy(
    answer: str,
    citations: List[Dict[str, Any]],
    ungrounded_claims: List[str],
    is_abstention: bool = False,
) -> Dict[str, float]:
    """
    Evaluate citation quality.
    
    Args:
        answer: Generated answer text
        citations: List of citation dicts with marker, chunk_id, score, snippet
        ungrounded_claims: List of ungrounded claims detected
        is_abstention: Whether the answer represents an intentional abstention
        
    Returns:
        Dict with resolution_rate, grounding_rate, hallucination_rate
    """
    if is_abstention:
        return {
            "resolution_rate": 1.0,
            "grounding_rate": 1.0,
            "hallucination_rate": 0.0,
        }

    # Resolution rate: citations that have valid chunk_ids
    if citations:
        valid_citations = sum(1 for c in citations if c.get("chunk_id"))
        resolution_rate = valid_citations / len(citations)
    else:
        resolution_rate = 1.0  # No citations to resolve
    
    # Grounding rate: fraction of factual claims with citations
    sentences = re.split(r'[.!?]+', answer)
    factual_sentences = [s for s in sentences if len(s.strip()) > 20]
    if factual_sentences:
        cited_sentences = sum(1 for s in factual_sentences if re.search(r'\[c_\d+\]', s))
        grounding_rate = cited_sentences / len(factual_sentences)
    else:
        grounding_rate = 1.0
    
    # Hallucination rate: ungrounded claims
    hallucination_rate = len(ungrounded_claims) / max(1, len(factual_sentences))
    
    return {
        "resolution_rate": resolution_rate,
        "grounding_rate": grounding_rate,
        "hallucination_rate": min(hallucination_rate, 1.0),
    }


def evaluate_abstention_accuracy(
    is_abstention: bool,
    expected_to_abstain: bool,
) -> Dict[str, float]:
    """
    Evaluate abstention behavior.
    
    Args:
        is_abstention: Whether the model abstained
        expected_to_abstain: Whether the question should trigger abstention
        
    Returns:
        Dict with accuracy, false_abstention_rate, false_answer_rate
    """
    if is_abstention == expected_to_abstain:
        accuracy = 1.0
    else:
        accuracy = 0.0
    
    false_abstention = 1.0 if (is_abstention and not expected_to_abstain) else 0.0
    false_answer = 1.0 if (not is_abstention and expected_to_abstain) else 0.0
    
    return {
        "accuracy": accuracy,
        "false_abstention_rate": false_abstention,
        "false_answer_rate": false_answer,
    }


def evaluate_answer_correctness(
    answer: str,
    expected_keywords: List[str] = None,
) -> Dict[str, float]:
    """
    Evaluate answer correctness using keyword matching.
    
    Args:
        answer: Generated answer
        expected_keywords: List of keywords that should appear in correct answer
        
    Returns:
        Dict with keyword_coverage score
    """
    if not expected_keywords:
        return {"keyword_coverage": 1.0, "note": "No expected keywords provided"}
    
    answer_lower = answer.lower()
    matched = sum(1 for kw in expected_keywords if kw.lower() in answer_lower)
    coverage = matched / len(expected_keywords)
    
    return {
        "keyword_coverage": coverage,
        "matched_keywords": matched,
        "total_keywords": len(expected_keywords),
    }


def compute_aggregate_metrics(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Compute aggregate metrics across all questions, including category breakdowns."""
    if not results:
        return {}
    
    # Retrieval metrics
    precisions = [r.get("retrieval", {}).get("precision_at_k", 0) for r in results]
    recalls = [r.get("retrieval", {}).get("recall_at_k", 0) for r in results]
    mrrs = [r.get("retrieval", {}).get("mrr", 0) for r in results]
    ndcgs = [r.get("retrieval", {}).get("ndcg_at_k", 0) for r in results if "ndcg_at_k" in r.get("retrieval", {})]
    
    # Citation metrics
    resolution_rates = [r.get("citation", {}).get("resolution_rate", 1) for r in results]
    grounding_rates = [r.get("citation", {}).get("grounding_rate", 1) for r in results]
    hallucination_rates = [r.get("citation", {}).get("hallucination_rate", 0) for r in results]
    
    # Abstention metrics
    abstention_accuracies = [r.get("abstention", {}).get("accuracy", 1) for r in results]
    false_abstentions = [r.get("abstention", {}).get("false_abstention_rate", 0) for r in results]
    false_answers = [r.get("abstention", {}).get("false_answer_rate", 0) for r in results]
    
    # Latency metrics
    latencies = [r.get("latency_ms", 0) for r in results]
    prompt_tokens = [r.get("prompt_tokens", 0) for r in results]
    completion_tokens = [r.get("completion_tokens", 0) for r in results]

    # RAGAS / Advanced metrics
    ctx_precisions = [r.get("context_precision", 0.0) for r in results if "context_precision" in r]
    ctx_recalls = [r.get("context_recall", 0.0) for r in results if "context_recall" in r]
    f1_scores = [r.get("f1_score", 0.0) for r in results if "f1_score" in r]

    # Category breakdown
    categories: Dict[str, List[Dict[str, Any]]] = {}
    for r in results:
        cat = r.get("category", "unspecified")
        categories.setdefault(cat, []).append(r)

    by_category: Dict[str, Dict[str, float]] = {}
    for cat, cat_results in categories.items():
        cat_g = [cr.get("citation", {}).get("grounding_rate", 1) for cr in cat_results]
        cat_h = [cr.get("citation", {}).get("hallucination_rate", 0) for cr in cat_results]
        cat_a = [cr.get("abstention", {}).get("accuracy", 1) for cr in cat_results]
        cat_f1 = [cr.get("f1_score", 0.0) for cr in cat_results if "f1_score" in cr]
        cat_cp = [cr.get("context_precision", 0.0) for cr in cat_results if "context_precision" in cr]
        cat_cr = [cr.get("context_recall", 0.0) for cr in cat_results if "context_recall" in cr]

        by_category[cat] = {
            "count": len(cat_results),
            "grounding_rate": sum(cat_g) / len(cat_g),
            "hallucination_rate": sum(cat_h) / len(cat_h),
            "abstention_accuracy": sum(cat_a) / len(cat_a),
            "avg_f1_score": (sum(cat_f1) / len(cat_f1)) if cat_f1 else 0.0,
            "avg_context_precision": (sum(cat_cp) / len(cat_cp)) if cat_cp else 0.0,
            "avg_context_recall": (sum(cat_cr) / len(cat_cr)) if cat_cr else 0.0,
        }
    
    metrics: Dict[str, Any] = {
        "retrieval": {
            "avg_precision_at_k": (sum(precisions) / len(precisions)) if precisions else 0.0,
            "avg_recall_at_k": (sum(recalls) / len(recalls)) if recalls else 0.0,
            "avg_mrr": (sum(mrrs) / len(mrrs)) if mrrs else 0.0,
            "avg_ndcg_at_k": (sum(ndcgs) / len(ndcgs)) if ndcgs else 0.0,
        },
        "citation": {
            "avg_resolution_rate": sum(resolution_rates) / len(resolution_rates),
            "avg_grounding_rate": sum(grounding_rates) / len(grounding_rates),
            "avg_hallucination_rate": sum(hallucination_rates) / len(hallucination_rates),
        },
        "abstention": {
            "accuracy": sum(abstention_accuracies) / len(abstention_accuracies),
            "false_abstention_rate": sum(false_abstentions) / len(false_abstentions),
            "false_answer_rate": sum(false_answers) / len(false_answers),
        },
        "latency": {
            "avg_latency_ms": sum(latencies) / len(latencies),
            "avg_prompt_tokens": sum(prompt_tokens) / len(prompt_tokens),
            "avg_completion_tokens": sum(completion_tokens) / len(completion_tokens),
            "avg_total_tokens": sum(p + c for p, c in zip(prompt_tokens, completion_tokens)) / len(prompt_tokens),
        },
    }

    if ctx_precisions:
        deterministic_metrics = {
            "avg_context_precision": sum(ctx_precisions) / len(ctx_precisions),
            "avg_context_recall": sum(ctx_recalls) / len(ctx_recalls) if ctx_recalls else 0.0,
            "avg_f1_token_overlap": sum(f1_scores) / len(f1_scores) if f1_scores else 0.0,
            "evaluation_type": "deterministic_heuristic_pure_function",
        }
        metrics["deterministic_context"] = deterministic_metrics
        # Retain ragas alias for backwards compatibility
        metrics["ragas"] = deterministic_metrics

    if by_category:
        metrics["by_category"] = by_category

    return metrics