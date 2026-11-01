import { EvaluationBenchmarkQuestion } from "@/types";

/**
 * Evaluation Service Adapter.
 * Provides the verified 20-question golden benchmark dataset derived from backend/tests/fixtures/golden_evaluation_dataset.jsonl.
 * Note: Dedicated live /api/v1/evaluation API endpoints are scheduled for Backend Phase 2.
 * Fabricated metrics have been removed to preserve reporting integrity.
 */

export const GOLDEN_BENCHMARK_QUESTIONS: EvaluationBenchmarkQuestion[] = [
  { id: "q1", question: "What was the date and start time of Incident 104?", expected_citations: ["[c_0]"], expected_to_abstain: false, category: "Incident Analysis" },
  { id: "q2", question: "How many total connections were exhausted in the PostgreSQL pool during Incident 104?", expected_citations: ["[c_0]"], expected_to_abstain: false, category: "Incident Analysis" },
  { id: "q3", question: "What was the initial client connection acquisition timeout and what was it lowered to?", expected_citations: ["[c_0]"], expected_to_abstain: false, category: "Incident Analysis" },
  { id: "q4", question: "What table lacked an index causing sequential scans during Incident 104?", expected_citations: ["[c_0]"], expected_to_abstain: false, category: "Database Architecture" },
  { id: "q5", question: "What columns should the composite index be created on for billing ledger?", expected_citations: ["[c_0]"], expected_to_abstain: false, category: "Database Architecture" },
  { id: "q6", question: "What was max_connections scaled up to in the Aurora PostgreSQL cluster?", expected_citations: ["[c_0]"], expected_to_abstain: false, category: "Database Architecture" },
  { id: "q7", question: "What threshold triggers an alert for connection pool saturation?", expected_citations: ["[c_0]"], expected_to_abstain: false, category: "Observability & SRE" },
  { id: "q8", question: "What is the normal baseline for Envoy upstream request time 99th percentile?", expected_citations: ["[c_0]"], expected_to_abstain: false, category: "Observability & SRE" },
  { id: "q9", question: "At what latency threshold should Envoy circuit breaking be enabled to shed excess traffic?", expected_citations: ["[c_0]"], expected_to_abstain: false, category: "Traffic Engineering" },
  { id: "q10", question: "What command performs a rolling restart of degraded service pods?", expected_citations: ["[c_0]"], expected_to_abstain: false, category: "Traffic Engineering" },
  { id: "q11", question: "What asymmetric algorithm and key size are used for JWT signing?", expected_citations: ["[c_0]"], expected_to_abstain: false, category: "Security & Auth" },
  { id: "q12", question: "How frequently are the RSA private key pairs rotated?", expected_citations: ["[c_0]"], expected_to_abstain: false, category: "Security & Auth" },
  { id: "q13", question: "What is the time to live for access tokens?", expected_citations: ["[c_0]"], expected_to_abstain: false, category: "Security & Auth" },
  { id: "q14", question: "Where are revoked session tokens blacklisted?", expected_citations: ["[c_0]"], expected_to_abstain: false, category: "Security & Auth" },
  { id: "q15", question: "What is the TTL for refresh tokens?", expected_citations: ["[c_0]"], expected_to_abstain: false, category: "Security & Auth" },
  { id: "q16", question: "Explain quantum teleportation entanglement protocols.", expected_citations: [], expected_to_abstain: true, category: "Negative / Out-of-Scope" },
  { id: "q17", question: "What is the maximum memory allocated to the Redis cluster?", expected_citations: [], expected_to_abstain: true, category: "Negative / Out-of-Scope" },
  { id: "q18", question: "Which Kubernetes cluster version is running in staging?", expected_citations: [], expected_to_abstain: true, category: "Negative / Out-of-Scope" },
  { id: "q19", question: "What is the salary of the on-call engineer who responded at 14:32 UTC?", expected_citations: [], expected_to_abstain: true, category: "Negative / Out-of-Scope" },
  { id: "q20", question: "What are the BGP routing tables configured on core routers?", expected_citations: [], expected_to_abstain: true, category: "Negative / Out-of-Scope" },
];

export interface BenchmarkStats {
  dataset_size: number;
  grounded_questions: number;
  abstention_questions: number;
  backend_endpoint_available: boolean;
  endpoint_status_message: string;
}

export const evaluationService = {
  getBenchmarkDataset(): EvaluationBenchmarkQuestion[] {
    return GOLDEN_BENCHMARK_QUESTIONS;
  },

  getBenchmarkStats(): BenchmarkStats {
    const dataset = GOLDEN_BENCHMARK_QUESTIONS;
    const abstentions = dataset.filter((q) => q.expected_to_abstain).length;
    return {
      dataset_size: dataset.length,
      grounded_questions: dataset.length - abstentions,
      abstention_questions: abstentions,
      backend_endpoint_available: false,
      endpoint_status_message: "Live on-demand batch evaluation API scheduled for Backend Phase 2",
    };
  },
};
