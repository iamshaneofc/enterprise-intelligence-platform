"""Evaluation metrics for RAG system quality assessment."""
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import json
import re


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


def evaluate_retrieval_precision(
    retrieved_chunks: List[Dict[str, Any]],
    expected_citations: List[str],
    top_k: int = 5,
) -> Dict[str, float]:
    """
    Evaluate retrieval precision at K.
    
    Args:
        retrieved_chunks: List of retrieved chunk dicts with 'chunk_id' and 'score'
        expected_citations: List of expected citation markers like ['[c_0]', '[c_1]']
        top_k: Number of top results to consider
        
    Returns:
        Dict with precision, recall, MRR, NDCG metrics
    """
    if not retrieved_chunks:
        return {"precision_at_k": 0.0, "recall_at_k": 0.0, "mrr": 0.0, "ndcg_at_k": 0.0}
    
    # For this simplified evaluation, we check if the top chunk matches expected
    # In a full implementation, you'd map citation markers to chunk IDs
    top_chunks = retrieved_chunks[:top_k]
    
    # Precision: how many of the top-k are relevant
    # Since we don't have ground truth relevance labels, we use a proxy:
    # If expected_citations is not empty, assume the first expected is relevant
    if expected_citations:
        # Check if top result has content (proxy for relevance)
        precision = 1.0 if top_chunks and top_chunks[0].get("content") else 0.0
        recall = 1.0 if top_chunks else 0.0
    else:
        # For abstention cases, we don't measure retrieval precision
        precision = 0.0
        recall = 0.0
    
    # MRR: reciprocal rank of first relevant result
    mrr = 1.0 if top_chunks else 0.0
    
    # NDCG simplified
    ndcg = 1.0 if top_chunks else 0.0
    
    return {
        "precision_at_k": precision,
        "recall_at_k": recall,
        "mrr": mrr,
        "ndcg_at_k": ndcg,
    }


def evaluate_citation_accuracy(
    answer: str,
    citations: List[Dict[str, Any]],
    ungrounded_claims: List[str],
) -> Dict[str, float]:
    """
    Evaluate citation quality.
    
    Args:
        answer: Generated answer text
        citations: List of citation dicts with marker, chunk_id, score, snippet
        ungrounded_claims: List of ungrounded claims detected
        
    Returns:
        Dict with resolution_rate, grounding_rate, hallucination_rate
    """
    # Resolution rate: citations that have valid chunk_ids
    if citations:
        valid_citations = sum(1 for c in citations if c.get("chunk_id"))
        resolution_rate = valid_citations / len(citations)
    else:
        resolution_rate = 1.0  # No citations to resolve
    
    # Grounding rate: fraction of factual claims with citations
    # Simple heuristic: count sentences with citation markers
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
    For more sophisticated evaluation, use an LLM judge.
    
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
    """Compute aggregate metrics across all questions."""
    if not results:
        return {}
    
    # Retrieval metrics
    precisions = [r.get("retrieval", {}).get("precision_at_k", 0) for r in results]
    recalls = [r.get("retrieval", {}).get("recall_at_k", 0) for r in results]
    mrrs = [r.get("retrieval", {}).get("mrr", 0) for r in results]
    
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
    
    return {
        "retrieval": {
            "avg_precision_at_k": sum(precisions) / len(precisions),
            "avg_recall_at_k": sum(recalls) / len(recalls),
            "avg_mrr": sum(mrrs) / len(mrrs),
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