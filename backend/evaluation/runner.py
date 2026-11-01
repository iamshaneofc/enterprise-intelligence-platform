"""Evaluation runner for Enterprise Intelligence Platform.

Runs the golden evaluation dataset through the RAG pipeline and computes metrics.
Supports both offline (fake providers) and online (real providers) evaluation modes.
"""
import json
import time
import os
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
from pathlib import Path

from sqlalchemy.orm import Session

from backend.app.db.session import SessionLocal
from backend.app.models.user import User
from backend.app.models.workspace import Workspace
from backend.app.services.rag_service import rag_service
from backend.app.embeddings.provider import FakeEmbeddingProvider, get_embedding_provider
from backend.app.llm.router import llm_router
from backend.app.llm.fake_client import FakeLLMClient
from backend.evaluation.metrics import (
    evaluate_retrieval_precision,
    evaluate_citation_accuracy,
    evaluate_abstention_accuracy,
    evaluate_answer_correctness,
    compute_aggregate_metrics,
)


@dataclass
class EvaluationConfig:
    """Configuration for evaluation run."""
    dataset_path: str = "backend/tests/fixtures/golden_evaluation_dataset.jsonl"
    use_fake_llm: bool = True
    use_fake_embeddings: bool = True
    top_k: int = 5
    output_path: Optional[str] = None


@dataclass
class QuestionResult:
    """Result for a single evaluation question."""
    question_id: str
    question: str
    answer: str
    is_abstention: bool
    citations: List[Dict[str, Any]]
    ungrounded_claims: List[str]
    retrieval_results: List[Dict[str, Any]]
    latency_ms: int
    prompt_tokens: int
    completion_tokens: int
    expected_to_abstain: bool
    expected_citations: List[str]
    
    # Computed metrics
    retrieval: Dict[str, float]
    citation: Dict[str, float]
    abstention: Dict[str, float]
    answer_correctness: Dict[str, float]


class EvaluationRunner:
    """Runs evaluation on the golden dataset."""
    
    def __init__(self, config: EvaluationConfig = None):
        self.config = config or EvaluationConfig()
        self.results: List[QuestionResult] = []
    
    def setup_test_data(self, db: Session) -> tuple[User, Workspace]:
        """Create test user, workspace, and ingest test documents."""
        # Create user
        user = User(
            email="eval@enterprise.io",
            hashed_password="eval_hash",
            full_name="Evaluation User",
            role="engineer",
            is_active=True,
        )
        db.add(user)
        db.flush()
        
        # Create workspace
        workspace = Workspace(
            name="Evaluation Workspace",
            slug=f"eval-ws-{user.id[:8]}",
            description="Workspace for evaluation runs",
            owner_id=user.id,
        )
        db.add(workspace)
        db.flush()
        
        # Add workspace member
        from backend.app.models.workspace import WorkspaceMember
        member = WorkspaceMember(workspace_id=workspace.id, user_id=user.id, role="admin")
        db.add(member)
        db.commit()
        db.refresh(user)
        db.refresh(workspace)
        
        # Ingest test documents from fixtures
        fixtures_dir = Path(__file__).parent.parent / "tests" / "fixtures" / "synthetic_docs"
        doc_files = [
            "incident_104_db_pool_outage.md",
            "api_gateway_latency_runbook.md",
            "auth_jwt_service_spec.md",
        ]
        
        for doc_file in doc_files:
            file_path = fixtures_dir / doc_file
            if file_path.exists():
                with open(file_path, "rb") as f:
                    content = f.read()
                
                rag_service.search  # Ensure service is imported
                doc = rag_service.search  # Access to trigger service init
                
                from backend.app.services.document_service import document_service
                document_service.upload_and_process(
                    workspace_id=workspace.id,
                    user_id=user.id,
                    filename=doc_file,
                    content=content,
                    db=db,
                )
        
        return user, workspace
    
    def load_dataset(self) -> List[Dict[str, Any]]:
        """Load the golden evaluation dataset."""
        dataset_path = Path(self.config.dataset_path)
        if not dataset_path.exists():
            raise FileNotFoundError(f"Dataset not found: {dataset_path}")
        
        questions = []
        with open(dataset_path, "r") as f:
            for line in f:
                line = line.strip()
                if line:
                    questions.append(json.loads(line))
        return questions
    
    def run_evaluation(self) -> Dict[str, Any]:
        """Run the complete evaluation."""
        print(f"Starting evaluation with config: {self.config}")
        
        # Setup database and test data
        db = SessionLocal()
        try:
            user, workspace = self.setup_test_data(db)
            print(f"Created test user {user.id} and workspace {workspace.id}")
            
            # Load dataset
            questions = self.load_dataset()
            print(f"Loaded {len(questions)} questions from dataset")
            
            # Run each question
            for q in questions:
                print(f"  Evaluating {q['id']}: {q['question'][:60]}...")
                result = self.run_question(q, workspace.id, user.id, db)
                self.results.append(result)
            
            # Compute aggregate metrics
            aggregate = compute_aggregate_metrics([
                {
                    "retrieval": r.retrieval,
                    "citation": r.citation,
                    "abstention": r.abstention,
                    "latency_ms": r.latency_ms,
                    "prompt_tokens": r.prompt_tokens,
                    "completion_tokens": r.completion_tokens,
                }
                for r in self.results
            ])
            
            # Prepare output
            output = {
                "config": asdict(self.config),
                "aggregate_metrics": aggregate,
                "per_question_results": [asdict(r) for r in self.results],
            }
            
            if self.config.output_path:
                with open(self.config.output_path, "w") as f:
                    json.dump(output, f, indent=2, default=str)
                print(f"Results saved to {self.config.output_path}")
            
            return output
            
        finally:
            db.close()
    
    def run_question(
        self,
        question: Dict[str, Any],
        workspace_id: str,
        user_id: str,
        db: Session,
    ) -> QuestionResult:
        """Run a single evaluation question."""
        start_time = time.time()
        
        # Run RAG pipeline
        rag_result = rag_service.generate_rag_response(
            query=question["question"],
            workspace_id=workspace_id,
            user_id=user_id,
            top_k=self.config.top_k,
            db=db,
        )
        
        latency_ms = int((time.time() - start_time) * 1000)
        
        # Also run retrieval separately for metrics
        search_result = rag_service.search(
            query=question["question"],
            workspace_id=workspace_id,
            top_k=self.config.top_k,
            mode="hybrid",
            db=db,
        )
        
        # Compute metrics
        retrieval_metrics = evaluate_retrieval_precision(
            retrieved_chunks=[
                {
                    "chunk_id": r.chunk_id,
                    "content": r.content,
                    "score": r.score,
                }
                for r in search_result.results
            ],
            expected_citations=question.get("expected_citations", []),
            top_k=self.config.top_k,
        )
        
        citation_metrics = evaluate_citation_accuracy(
            answer=rag_result.answer,
            citations=[asdict(c) for c in rag_result.citations],
            ungrounded_claims=rag_result.ungrounded_claims,
        )
        
        abstention_metrics = evaluate_abstention_accuracy(
            is_abstention=rag_result.is_abstention,
            expected_to_abstain=question.get("expected_to_abstain", False),
        )
        
        # For answer correctness, we'd need expected keywords per question
        # This is a placeholder - in practice you'd have ground truth answers
        answer_correctness = evaluate_answer_correctness(
            answer=rag_result.answer,
            expected_keywords=None,
        )
        
        return QuestionResult(
            question_id=question["id"],
            question=question["question"],
            answer=rag_result.answer,
            is_abstention=rag_result.is_abstention,
            citations=[asdict(c) for c in rag_result.citations],
            ungrounded_claims=rag_result.ungrounded_claims,
            retrieval_results=[
                {
                    "chunk_id": r.chunk_id,
                    "document_id": r.document_id,
                    "document_title": r.document_title,
                    "content": r.content,
                    "score": r.score,
                    "chunk_index": r.chunk_index,
                    "metadata": r.metadata,
                }
                for r in search_result.results
            ],
            latency_ms=latency_ms,
            prompt_tokens=rag_result.citations[0].__dict__.get("prompt_tokens", 0) if rag_result.citations else 0,
            completion_tokens=0,  # Not directly available from ChatResponse
            expected_to_abstain=question.get("expected_to_abstain", False),
            expected_citations=question.get("expected_citations", []),
            retrieval=retrieval_metrics,
            citation=citation_metrics,
            abstention=abstention_metrics,
            answer_correctness=answer_correctness,
        )


def run_evaluation(
    dataset_path: str = None,
    use_fake_llm: bool = True,
    use_fake_embeddings: bool = True,
    top_k: int = 5,
    output_path: str = None,
) -> Dict[str, Any]:
    """
    Convenience function to run evaluation.
    
    Args:
        dataset_path: Path to golden dataset JSONL
        use_fake_llm: Use fake LLM provider (for CI/offline)
        use_fake_embeddings: Use fake embedding provider
        top_k: Number of retrieval results
        output_path: Optional path to save results JSON
        
    Returns:
        Dict with aggregate and per-question results
    """
    config = EvaluationConfig(
        dataset_path=dataset_path or "backend/tests/fixtures/golden_evaluation_dataset.jsonl",
        use_fake_llm=use_fake_llm,
        use_fake_embeddings=use_fake_embeddings,
        top_k=top_k,
        output_path=output_path,
    )
    
    # Override providers for fake mode
    if use_fake_llm:
        os.environ["USE_FAKE_LLM"] = "true"
    if use_fake_embeddings:
        os.environ["USE_FAKE_EMBEDDINGS"] = "true"
    
    runner = EvaluationRunner(config)
    return runner.run_evaluation()


if __name__ == "__main__":
    # Allow running as script
    import argparse
    parser = argparse.ArgumentParser(description="Run RAG evaluation")
    parser.add_argument("--dataset", default="backend/tests/fixtures/golden_evaluation_dataset.jsonl")
    parser.add_argument("--fake-llm", action="store_true", default=True)
    parser.add_argument("--fake-embeddings", action="store_true", default=True)
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--output", default=None)
    args = parser.parse_args()
    
    result = run_evaluation(
        dataset_path=args.dataset,
        use_fake_llm=args.fake_llm,
        use_fake_embeddings=args.fake_embeddings,
        top_k=args.top_k,
        output_path=args.output,
    )
    
    print("\n=== AGGREGATE METRICS ===")
    for category, metrics in result["aggregate_metrics"].items():
        print(f"\n{category.upper()}:")
        for k, v in metrics.items():
            print(f"  {k}: {v:.4f}" if isinstance(v, float) else f"  {k}: {v}")