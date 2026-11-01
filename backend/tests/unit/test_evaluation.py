"""Tests for evaluation framework."""
import pytest
import json
import tempfile
import os
from pathlib import Path

from backend.evaluation.metrics import (
    evaluate_retrieval_precision,
    evaluate_citation_accuracy,
    evaluate_abstention_accuracy,
    evaluate_answer_correctness,
    compute_context_precision,
    compute_context_recall,
    compute_f1_token_overlap,
    compute_aggregate_metrics,
)
from backend.evaluation.runner import EvaluationConfig, QuestionResult, run_evaluation


def test_evaluate_retrieval_precision():
    """Test retrieval precision evaluation."""
    retrieved = [
        {"chunk_id": "c1", "content": "PostgreSQL connection pool exhausted", "score": 0.9},
        {"chunk_id": "c2", "content": "API gateway timeout", "score": 0.7},
    ]
    expected = ["[c_0]"]
    
    metrics = evaluate_retrieval_precision(retrieved, expected, top_k=5)
    assert "precision_at_k" in metrics
    assert "recall_at_k" in metrics
    assert "mrr" in metrics
    assert "ndcg_at_k" in metrics
    assert metrics["precision_at_k"] == 1.0
    
    # Empty retrieval
    metrics_empty = evaluate_retrieval_precision([], expected, top_k=5)
    assert metrics_empty["precision_at_k"] == 0.0


def test_evaluate_citation_accuracy():
    """Test citation accuracy evaluation."""
    answer = "The PostgreSQL pool exhausted 200 connections [c_0]. The timeout was 5s [c_1]."
    citations = [
        {"marker": "[c_0]", "chunk_id": "c1", "score": 0.9, "snippet": "PostgreSQL connection pool exhausted 200 connections"},
        {"marker": "[c_1]", "chunk_id": "c2", "score": 0.8, "snippet": "Timeout was lowered to 5s"},
    ]
    ungrounded = []
    
    metrics = evaluate_citation_accuracy(answer, citations, ungrounded)
    assert metrics["resolution_rate"] == 1.0
    assert metrics["grounding_rate"] > 0.5
    assert metrics["hallucination_rate"] == 0.0
    
    # Test with ungrounded claims
    ungrounded2 = ["Metric '9999' not found in source evidence"]
    metrics2 = evaluate_citation_accuracy(answer, citations, ungrounded2)
    assert metrics2["hallucination_rate"] > 0.0


def test_evaluate_abstention_accuracy():
    """Test abstention accuracy evaluation."""
    # Correct abstention
    metrics = evaluate_abstention_accuracy(True, True)
    assert metrics["accuracy"] == 1.0
    assert metrics["false_abstention_rate"] == 0.0
    assert metrics["false_answer_rate"] == 0.0
    
    # False abstention (should have answered)
    metrics = evaluate_abstention_accuracy(True, False)
    assert metrics["accuracy"] == 0.0
    assert metrics["false_abstention_rate"] == 1.0
    
    # False answer (should have abstained)
    metrics = evaluate_abstention_accuracy(False, True)
    assert metrics["accuracy"] == 0.0
    assert metrics["false_answer_rate"] == 1.0


def test_evaluate_answer_correctness():
    """Test answer correctness evaluation."""
    answer = "The PostgreSQL connection pool exhausted 200 connections on 2026-03-15."
    expected = ["PostgreSQL", "200", "2026-03-15"]
    
    metrics = evaluate_answer_correctness(answer, expected)
    assert metrics["keyword_coverage"] == 1.0
    assert metrics["matched_keywords"] == 3
    
    # Partial match
    metrics = evaluate_answer_correctness("PostgreSQL connection pool exhausted 200 connections on 2026-03-15", expected)
    assert metrics["keyword_coverage"] == 1.0
    
    # Only 2 out of 3 keywords
    metrics = evaluate_answer_correctness("PostgreSQL connection pool exhausted on 2026-03-15", expected)
    assert metrics["keyword_coverage"] == 2/3
    
    # No expected keywords
    metrics = evaluate_answer_correctness("Any answer", None)
    assert metrics["keyword_coverage"] == 1.0


def test_compute_context_precision():
    """Test context precision computation."""
    contexts = [
        "On 2026-03-15 at 14:22 UTC, the PostgreSQL connection pool exhausted all 200 available connections.",
        "Envoy gateway latency runbook and circuit breaking configuration.",
    ]
    gt_context = "On 2026-03-15 at 14:22 UTC, the PostgreSQL connection pool exhausted all 200 available connections."
    
    # Chunk 1 is relevant (rank 1), chunk 2 is not
    prec = compute_context_precision(contexts, gt_context)
    assert prec == 1.0

    # Empty GT context returns 1.0 (abstention scenario)
    assert compute_context_precision(contexts, "") == 1.0
    # Empty contexts return 0.0
    assert compute_context_precision([], gt_context) == 0.0


def test_compute_context_recall():
    """Test context recall computation."""
    contexts = [
        "On 2026-03-15 at 14:22 UTC, the PostgreSQL connection pool exhausted all 200 available connections.",
    ]
    gt_context = "On 2026-03-15 at 14:22 UTC, the PostgreSQL connection pool exhausted all 200 available connections."
    recall = compute_context_recall(contexts, gt_context)
    assert recall == 1.0

    # Irrelevant context
    recall_irrel = compute_context_recall(["Completely unrelated text about gardening."], gt_context)
    assert recall_irrel == 0.0


def test_compute_f1_token_overlap():
    """Test token F1 score computation."""
    pred = "The PostgreSQL connection pool exhausted 200 connections."
    gt = "The PostgreSQL connection pool exhausted 200 connections."
    assert compute_f1_token_overlap(pred, gt) == 1.0

    # Partial overlap
    pred_partial = "The PostgreSQL connection pool had issues."
    f1 = compute_f1_token_overlap(pred_partial, gt)
    assert 0.0 < f1 < 1.0

    # Abstention cases
    assert compute_f1_token_overlap("ABSTAIN: insufficient_evidence", "", is_abstention=True, expected_to_abstain=True) == 1.0
    assert compute_f1_token_overlap("Real answer", "", is_abstention=False, expected_to_abstain=True) == 0.0


def test_compute_aggregate_metrics():
    """Test aggregate metrics computation."""
    results = [
        {
            "retrieval": {"precision_at_k": 1.0, "recall_at_k": 1.0, "mrr": 1.0},
            "citation": {"resolution_rate": 1.0, "grounding_rate": 1.0, "hallucination_rate": 0.0},
            "abstention": {"accuracy": 1.0, "false_abstention_rate": 0.0, "false_answer_rate": 0.0},
            "latency_ms": 100,
            "prompt_tokens": 50,
            "completion_tokens": 50,
        },
        {
            "retrieval": {"precision_at_k": 0.5, "recall_at_k": 0.5, "mrr": 0.5},
            "citation": {"resolution_rate": 0.5, "grounding_rate": 0.5, "hallucination_rate": 0.5},
            "abstention": {"accuracy": 0.5, "false_abstention_rate": 0.5, "false_answer_rate": 0.5},
            "latency_ms": 200,
            "prompt_tokens": 100,
            "completion_tokens": 100,
        },
    ]
    
    agg = compute_aggregate_metrics(results)
    
    assert agg["retrieval"]["avg_precision_at_k"] == 0.75
    assert agg["retrieval"]["avg_recall_at_k"] == 0.75
    assert agg["citation"]["avg_resolution_rate"] == 0.75
    assert agg["abstention"]["accuracy"] == 0.75
    assert agg["latency"]["avg_latency_ms"] == 150


def test_evaluation_config():
    """Test evaluation configuration."""
    config = EvaluationConfig(
        dataset_path="test.jsonl",
        use_fake_llm=True,
        use_fake_embeddings=True,
        top_k=5,
    )
    assert config.dataset_path == "test.jsonl"
    assert config.use_fake_llm is True
    assert config.top_k == 5


# Integration test requires database - mark as integration
@pytest.mark.integration
def test_run_evaluation_offline():
    """Test running evaluation with fake providers (offline mode)."""
    # This test requires the full stack and database
    # Run with: pytest -m integration
    pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])