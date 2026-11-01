"""Tests for evaluation framework."""
import pytest
import json
import tempfile
import os
from pathlib import Path

from backend.evaluation.metrics import (
    compute_ir_metrics,
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
    """Test retrieval precision evaluation with true IR mathematics."""
    retrieved = [
        {"chunk_id": "c1", "content": "PostgreSQL connection pool exhausted", "score": 0.9},
        {"chunk_id": "c2", "content": "API gateway timeout", "score": 0.7},
    ]
    expected = ["[c_0]"]
    
    # 1 of 2 retrieved items is relevant; with K=5, precision@5 is 1/5 = 0.2
    metrics = evaluate_retrieval_precision(retrieved, expected, top_k=5)
    assert "precision_at_k" in metrics
    assert "recall_at_k" in metrics
    assert "mrr" in metrics
    assert "ndcg_at_k" in metrics
    assert metrics["precision_at_k"] == 0.2
    assert metrics["recall_at_k"] == 1.0
    assert metrics["mrr"] == 1.0
    assert metrics["ndcg_at_k"] == 1.0
    
    # When top_k=1, precision@1 is 1/1 = 1.0
    metrics_top1 = evaluate_retrieval_precision(retrieved, expected, top_k=1)
    assert metrics_top1["precision_at_k"] == 1.0
    
    # Empty retrieval
    metrics_empty = evaluate_retrieval_precision([], expected, top_k=5)
    assert metrics_empty["precision_at_k"] == 0.0
    assert metrics_empty["recall_at_k"] == 0.0
    assert metrics_empty["mrr"] == 0.0
    assert metrics_empty["ndcg_at_k"] == 0.0


# ---------------------------------------------------------------------------
# Comprehensive Information Retrieval Mathematics Unit Tests
# ---------------------------------------------------------------------------

def test_ir_perfect_retrieval():
    """Fixture A: All 3 relevant documents retrieved at the top (ranks 1, 2, 3) out of 5."""
    rel_vector = [1, 1, 1, 0, 0]
    metrics = compute_ir_metrics(rel_vector, k=5, total_relevant=3)
    assert metrics["precision_at_k"] == 0.6  # 3 / 5
    assert metrics["recall_at_k"] == 1.0     # 3 / 3
    assert metrics["mrr"] == 1.0             # 1 / 1
    assert metrics["ndcg_at_k"] == 1.0       # DCG == IDCG


def test_ir_completely_irrelevant_retrieval():
    """Fixture B: Zero relevant documents in top 5 when 2 exist in corpus."""
    rel_vector = [0, 0, 0, 0, 0]
    metrics = compute_ir_metrics(rel_vector, k=5, total_relevant=2)
    assert metrics["precision_at_k"] == 0.0
    assert metrics["recall_at_k"] == 0.0
    assert metrics["mrr"] == 0.0
    assert metrics["ndcg_at_k"] == 0.0


def test_ir_partially_relevant_retrieval():
    """Fixture C: 2 relevant documents retrieved at ranks 2 and 4 out of 5."""
    rel_vector = [0, 1, 0, 1, 0]
    metrics = compute_ir_metrics(rel_vector, k=5, total_relevant=2)
    assert metrics["precision_at_k"] == 0.4  # 2 / 5
    assert metrics["recall_at_k"] == 1.0     # 2 / 2
    assert metrics["mrr"] == 0.5             # 1 / 2
    # Hand calculation: DCG = 1/log2(3) + 1/log2(5) = 1.0616063
    # IDCG = 1/log2(2) + 1/log2(3) = 1.6309298
    # NDCG = 1.0616063 / 1.6309298 = 0.650921
    assert pytest.approx(metrics["ndcg_at_k"], 1e-5) == 0.650921


def test_ir_relevant_documents_at_different_ranks():
    """Fixture D: Verify MRR = 1/rank across ranks 1 to 5."""
    for rank in range(1, 6):
        vector = [0] * 5
        vector[rank - 1] = 1
        m = compute_ir_metrics(vector, k=5, total_relevant=1)
        expected_mrr = round(1.0 / rank, 6)
        assert pytest.approx(m["mrr"], 1e-5) == expected_mrr


def test_ir_empty_retrieval():
    """Fixture E: Empty candidate list produces zero for all IR metrics without division by zero."""
    metrics = compute_ir_metrics([], k=5, total_relevant=3)
    assert metrics["precision_at_k"] == 0.0
    assert metrics["recall_at_k"] == 0.0
    assert metrics["mrr"] == 0.0
    assert metrics["ndcg_at_k"] == 0.0


def test_ir_no_relevant_ground_truth_documents():
    """Fixture F: Unanswerable query with 0 relevant documents in corpus."""
    rel_vector = [0, 0, 0, 0, 0]
    metrics = compute_ir_metrics(rel_vector, k=5, total_relevant=0)
    assert metrics["precision_at_k"] == 0.0
    assert metrics["recall_at_k"] == 0.0
    assert metrics["mrr"] == 0.0
    assert metrics["ndcg_at_k"] == 0.0


def test_ir_fewer_than_k_retrieved_chunks():
    """Fixture G: Only 2 items retrieved when K=5; 1 is relevant."""
    rel_vector = [1, 0]
    metrics = compute_ir_metrics(rel_vector, k=5, total_relevant=2)
    # Precision@5 uses denominator K=5 -> 1/5 = 0.20
    assert metrics["precision_at_k"] == 0.2
    # Recall@5 uses total_relevant=2 -> 1/2 = 0.50
    assert metrics["recall_at_k"] == 0.5
    assert metrics["mrr"] == 1.0
    # IDCG@5 for 2 items = 1.0 + 1/log2(3) = 1.6309298
    # DCG = 1.0 / log2(2) = 1.0
    # NDCG = 1.0 / 1.6309298 = 0.613147
    assert pytest.approx(metrics["ndcg_at_k"], 1e-5) == 0.613147


def test_ir_multiple_queries_aggregate_averages():
    """Fixture H: Macro-averages across heterogeneous queries match hand-calculated values."""
    q1 = {"retrieval": compute_ir_metrics([1, 1, 1, 0, 0], k=5, total_relevant=3)}  # P=0.6, R=1.0, MRR=1.0
    q2 = {"retrieval": compute_ir_metrics([1, 0, 0, 0, 0], k=5, total_relevant=2)}  # P=0.2, R=0.5, MRR=1.0
    q3 = {"retrieval": compute_ir_metrics([0, 0, 0, 0, 0], k=5, total_relevant=1)}  # P=0.0, R=0.0, MRR=0.0
    
    agg = compute_aggregate_metrics([q1, q2, q3])
    expected_avg_p = (0.6 + 0.2 + 0.0) / 3   # 0.266667
    expected_avg_r = (1.0 + 0.5 + 0.0) / 3   # 0.500000
    expected_avg_mrr = (1.0 + 1.0 + 0.0) / 3 # 0.666667
    
    assert pytest.approx(agg["retrieval"]["avg_precision_at_k"], 1e-5) == expected_avg_p
    assert pytest.approx(agg["retrieval"]["avg_recall_at_k"], 1e-5) == expected_avg_r
    assert pytest.approx(agg["retrieval"]["avg_mrr"], 1e-5) == expected_avg_mrr
    assert "avg_ndcg_at_k" in agg["retrieval"]


def test_ir_ndcg_ranking_sensitivity():
    """Fixture I: Placing relevant items higher in rank strictly increases NDCG."""
    run_a = compute_ir_metrics([1, 0], k=2, total_relevant=1)  # Relevant at rank 1: NDCG = 1.0
    run_b = compute_ir_metrics([0, 1], k=2, total_relevant=1)  # Relevant at rank 2: NDCG = 0.63093
    assert run_a["ndcg_at_k"] == 1.0
    assert pytest.approx(run_b["ndcg_at_k"], 1e-5) == 0.63093
    assert run_a["ndcg_at_k"] > run_b["ndcg_at_k"]


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