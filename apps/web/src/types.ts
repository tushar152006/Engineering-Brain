export type RepositorySource = "github" | "local";

export type IndexingStatus = "pending" | "indexing" | "embedding" | "ready" | "failed";

export interface RepositoryRecord {
  id: string;
  name: string;
  source: RepositorySource;
  source_url?: string | null;
  file_count: number;
  chunk_count: number;
  embedded_chunk_count: number;
  symbol_count: number;
  edge_count: number;
  languages: string[];
  indexed_at: string;
  status: IndexingStatus;
  error?: string | null;
}

export interface RepositoryIndexResponse {
  repository: RepositoryRecord;
  indexed_files: number;
  indexed_chunks: number;
  skipped_files: number;
}

export interface IndexJobStatus {
  repo_id: string;
  status: IndexingStatus;
  file_count: number;
  chunk_count: number;
  embedded_chunk_count: number;
  symbol_count: number;
  error?: string | null;
}

export interface Citation {
  chunk_id: string;
  file_path: string;
  start_line: number;
  end_line: number;
  title: string;
  excerpt: string;
  score: number;
}

export interface SearchResponse {
  query: string;
  results: Citation[];
}

export interface ChatResponse {
  answer: string;
  citations: Citation[];
  confidence: string;
  unknowns?: string[];
  model_used?: string | null;
}

// ── Phase 2 types ─────────────────────────────────────────────────────────────

export interface Symbol {
  id: string;
  repo_id: string;
  file_path: string;
  name: string;
  qualified_name: string;
  kind: string;  // "function" | "class" | "method" | "async_function"
  start_line: number;
  end_line: number;
  signature?: string | null;
  language: string;
}

export interface SymbolListResponse {
  repo_id: string;
  symbols: Symbol[];
  total: number;
}

export interface GraphNode {
  id: string;
  label: string;
  language: string;
  chunk_count: number;
  degree: number;
}

export interface GraphEdge {
  source: string;
  target: string;
  relationship: string;
}

export interface GraphResponse {
  repo_id: string;
  nodes: GraphNode[];
  edges: GraphEdge[];
  total_nodes: number;
  total_edges: number;
}

export interface ArchitectureSummary {
  repository: RepositoryRecord;
  summary: string;
  top_directories: Array<{ name: string; chunk_count: number }>;
  important_files: string[];
  entrypoints: string[];
  frameworks: Array<{ name: string; evidence_files: string[] }>;
  next_steps: string[];
  // Phase 2
  llm_narrative?: string | null;
  docs_gap_report?: string | null;
  symbol_count: number;
  top_symbols: Array<{
    name: string;
    kind: string;
    file: string;
    line: number;
    signature?: string | null;
  }>;
  dependency_summary: {
    total_edges?: number;
    most_imported?: Array<[string, number]>;
    most_importing?: Array<[string, number]>;
  };
}

// ── Phase 3 types ─────────────────────────────────────────────────────────────

export interface ReviewComment {
  file_path: string;
  line?: number | null;
  risk: "high" | "medium" | "low";
  category: string;
  message: string;
  suggestion?: string | null;
  evidence: string[];
  confidence: "high" | "medium" | "low";
}

export interface PRReviewResponse {
  run_id: string;
  repo_id: string;
  pr_number?: number | null;
  comments: ReviewComment[];
  risk_summary: "high" | "medium" | "low" | "clean";
  summary: string;
  missing_tests: string[];
  changed_files: string[];
  model_used?: string | null;
  posted_to_github: boolean;
  dry_run: boolean;
}

export type PublicReportStatus = "pending" | "analyzing" | "ready" | "failed";

export interface PublicReportResponse {
  report_id: string;
  github_url: string;
  status: PublicReportStatus;
  repo_name?: string | null;
  summary?: string | null;
  languages: string[];
  frameworks: any[];
  top_directories: any[];
  entrypoints: string[];
  important_files: string[];
  symbol_count: number;
  file_count: number;
  next_steps: string[];
  error?: string | null;
  created_at: string;
  share_url?: string | null;
}

export interface LLMStatus {
  ollama_available: boolean;
  chat_model: string;
  embed_model: string;
  llm_enabled: boolean;
  embeddings_enabled: boolean;
}

export interface AgentRun {
  id: string;
  repo_id: string;
  agent_type: "pr_review" | "architecture" | "public_analyze";
  status: "running" | "done" | "failed";
  input: any;
  output?: PRReviewResponse | any | null;
  model?: string | null;
  error?: string | null;
  started_at: string;
  completed_at?: string | null;
}
