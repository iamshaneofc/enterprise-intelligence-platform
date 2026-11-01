/**
 * TypeScript Data Models mirroring backend schemas and frontend domain state.
 */

export type UserRole = "admin" | "engineer" | "viewer";

export interface User {
  id: string;
  email: string;
  full_name: string;
  role: UserRole;
  is_active: boolean;
  created_at: string;
}

export interface AuthToken {
  access_token: string;
  token_type: string;
  expires_in: number;
}

export interface Workspace {
  id: string;
  name: string;
  slug: string;
  description?: string | null;
  owner_id: string;
  created_at: string;
  updated_at: string;
}

export type DocumentStatus = "pending" | "processing" | "completed" | "failed";

export interface DocumentItem {
  id: string;
  workspace_id: string;
  title: string;
  filename: string;
  file_size_bytes: number;
  file_type: string;
  file_hash: string;
  status: DocumentStatus;
  chunk_count: number;
  error_message?: string | null;
  doc_metadata: Record<string, any>;
  created_at: string;
  updated_at: string;
}

export interface ChunkItem {
  id: string;
  document_id: string;
  chunk_index: number;
  content: string;
  chunk_metadata: {
    page_number?: number;
    section_header?: string;
    token_count?: number;
    [key: string]: any;
  };
  created_at: string;
}

export interface Citation {
  marker: string; // e.g. "[c_0]", "[c_1]"
  document_id: string;
  document_title: string;
  chunk_id: string;
  snippet: string;
  score: number;
}

export interface SearchResultItem {
  chunk_id: string;
  document_id: string;
  document_title: string;
  content: string;
  score: number;
  chunk_index: number;
  metadata: Record<string, any>;
}

export interface SearchResponse {
  query: string;
  mode: "hybrid" | "dense" | "sparse";
  results: SearchResultItem[];
  total_results: number;
}

export interface ChatResponse {
  answer: string;
  conversation_id: string;
  message_id: string;
  citations: Citation[];
  is_abstention: boolean;
  ungrounded_claims: string[];
  model_used: string;
  provider_used: string;
  latency_ms: number;
}

export interface MessageItem {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  citations?: Citation[];
  created_at: string;
}

export interface ConversationItem {
  id: string;
  workspace_id: string;
  title: string;
  summary?: string | null;
  messages: MessageItem[];
  created_at: string;
  updated_at: string;
}

export type AgentRunStatus = "queued" | "running" | "completed" | "failed";

export interface ToolExecution {
  id: string;
  step_number: number;
  tool_name: string;
  tool_input: Record<string, any>;
  tool_output: Record<string, any>;
  status: "success" | "error";
  execution_time_ms: number;
  error_message?: string | null;
  created_at: string;
}

export interface AgentRun {
  id: string;
  workspace_id: string;
  task: string;
  status: AgentRunStatus;
  plan: any[];
  final_output?: string | null;
  tool_executions: ToolExecution[];
  total_steps: number;
  execution_time_ms?: number | null;
  created_at: string;
  completed_at?: string | null;
}

export interface SystemHealth {
  status: string;
  service: string;
  version: string;
  environment: string;
  timestamp: string;
  database?: string;
}

export interface EvaluationBenchmarkQuestion {
  id: string;
  question: string;
  expected_citations: string[];
  expected_to_abstain: boolean;
  category?: string;
}

export interface EvaluationMetricSummary {
  dataset_size: number;
  total_evaluated: number;
  passed: number;
  failed: number;
  abstention_questions: number;
  precision_at_k: number;
  retrieval_relevance: number;
  citation_accuracy: number;
  grounding_score: number;
  answer_correctness: number;
  abstention_accuracy: number;
  avg_latency_ms: number;
  total_tokens: number;
  estimated_cost_usd: number;
  primary_model: string;
}

export interface AggregateMetrics {
  retrieval: {
    avg_precision_at_k: number;
    avg_recall_at_k: number;
    avg_mrr: number;
  };
  citation: {
    avg_resolution_rate: number;
    avg_grounding_rate: number;
    avg_hallucination_rate: number;
  };
  abstention: {
    accuracy: number;
    false_abstention_rate: number;
    false_answer_rate: number;
  };
  latency: {
    avg_latency_ms: number;
    avg_prompt_tokens: number;
    avg_completion_tokens: number;
    avg_total_tokens: number;
  };
}

export interface QuestionEvaluationResult {
  question_id: string;
  question: string;
  answer: string;
  is_abstention: boolean;
  citations: any[];
  ungrounded_claims: string[];
  latency_ms: number;
  retrieval: {
    precision_at_k: number;
    recall_at_k: number;
    reciprocal_rank: number;
  };
  citation: {
    resolution_rate: number;
    grounding_rate: number;
    hallucination_rate: number;
  };
  abstention: {
    is_correct: number;
    false_abstention: number;
    false_answer: number;
  };
}

export interface LiveEvaluationResponse {
  status: string;
  message?: string;
  results?: {
    config: {
      dataset_path: string;
      use_fake_llm: boolean;
      use_fake_embeddings: boolean;
      top_k: number;
      output_path?: string | null;
    };
    aggregate_metrics: AggregateMetrics;
    per_question_results: QuestionEvaluationResult[];
  };
}

