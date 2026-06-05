import type {
  ArchitectureSummary,
  ChatResponse,
  GraphResponse,
  IndexJobStatus,
  LLMStatus,
  RepositoryIndexResponse,
  RepositoryRecord,
  RepositorySource,
  SearchResponse,
  SymbolListResponse,
  AgentRun,
} from "./types";


const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(options?.headers ?? {})
    }
  });

  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || `Request failed with status ${response.status}`);
  }

  // 204 No Content — return undefined
  if (response.status === 204) return undefined as T;

  return response.json() as Promise<T>;
}

// ── Repository management ─────────────────────────────────────────────────────

export function indexRepository(payload: {
  source: RepositorySource;
  url?: string;
  local_path?: string;
  name?: string;
}) {
  return request<RepositoryIndexResponse>("/api/repositories/index", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export function listRepositories() {
  return request<RepositoryRecord[]>("/api/repositories");
}

export function getRepository(repoId: string) {
  return request<RepositoryRecord>(`/api/repositories/${repoId}`);
}

export function getRepositoryStatus(repoId: string) {
  return request<IndexJobStatus>(`/api/repositories/${repoId}/status`);
}

export function deleteRepository(repoId: string) {
  return request<void>(`/api/repositories/${repoId}`, { method: "DELETE" });
}

// ── Search & Chat ─────────────────────────────────────────────────────────────

export function searchRepository(repoId: string, query: string) {
  return request<SearchResponse>("/api/search", {
    method: "POST",
    body: JSON.stringify({ repo_id: repoId, query })
  });
}

export function chat(repoId: string, question: string) {
  return request<ChatResponse>("/api/chat", {
    method: "POST",
    body: JSON.stringify({ repo_id: repoId, question })
  });
}

/**
 * Streaming chat via SSE.
 * Calls onToken for each text chunk, then onDone with final metadata.
 */
export async function chatStream(
  repoId: string,
  question: string,
  onToken: (token: string) => void,
  onDone: (meta: Pick<ChatResponse, "citations" | "confidence" | "model_used" | "unknowns">) => void,
  signal?: AbortSignal
): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/api/chat/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ repo_id: repoId, question }),
    signal,
  });

  if (!response.ok) {
    const msg = await response.text();
    throw new Error(msg || `Stream request failed: ${response.status}`);
  }

  const reader = response.body!.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() ?? "";
    for (const line of lines) {
      if (!line.startsWith("data: ")) continue;
      const payload = line.slice(6).trim();
      if (payload === "[DONE]") continue;
      try {
        const evt = JSON.parse(payload) as {
          type: string;
          token?: string;
          citations?: ChatResponse["citations"];
          confidence?: string;
          model_used?: string | null;
        };
        if (evt.type === "token" && evt.token) {
          onToken(evt.token);
        } else if (evt.type === "done") {
          onDone({
            citations: evt.citations ?? [],
            confidence: evt.confidence ?? "low",
            unknowns: (evt as any).unknowns,
            model_used: evt.model_used ?? null,
          });
        }
      } catch {
        // ignore malformed lines
      }
    }
  }
}

// ── Architecture Summary ──────────────────────────────────────────────────────

export function architectureSummary(repoId: string) {
  return request<ArchitectureSummary>("/api/architecture-summary", {
    method: "POST",
    body: JSON.stringify({ repo_id: repoId })
  });
}

export function architectureSummaryDeep(repoId: string) {
  return request<ArchitectureSummary>("/api/architecture-summary/deep", {
    method: "POST",
    body: JSON.stringify({ repo_id: repoId })
  });
}

// ── Phase 2: Symbols & Graph ──────────────────────────────────────────────────

export function getSymbols(repoId: string, params?: {
  kind?: string;
  language?: string;
  q?: string;
  limit?: number;
}) {
  const qs = new URLSearchParams();
  if (params?.kind) qs.set("kind", params.kind);
  if (params?.language) qs.set("language", params.language);
  if (params?.q) qs.set("q", params.q);
  if (params?.limit) qs.set("limit", String(params.limit));
  const query = qs.toString();
  return request<SymbolListResponse>(`/api/repositories/${repoId}/symbols${query ? `?${query}` : ""}`);
}

export function getGraph(repoId: string, maxNodes?: number) {
  const qs = maxNodes ? `?max_nodes=${maxNodes}` : "";
  return request<GraphResponse>(`/api/repositories/${repoId}/graph${qs}`);
}

// ── LLM Status ───────────────────────────────────────────────────────────────

export function getLLMStatus() {
  return request<LLMStatus>("/api/llm/status");
}

// ── Phase 3: Feedback & PR Review ─────────────────────────────────────────────

export function submitFeedback(payload: { run_id: string; rating: number; label?: string; comment?: string }) {
  return request<any>("/api/chat/feedback", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export function analyzePublicRepo(github_url: string) {
  return request<any>("/api/public/analyze", {
    method: "POST",
    body: JSON.stringify({ github_url })
  });
}

export function getPublicReport(report_id: string) {
  return request<any>(`/api/public/reports/${report_id}`);
}

export function triggerPRReview(repoId: string, payload: { pr_number: number; post_to_github: boolean; dry_run: boolean }) {
  return request<AgentRun>(`/api/repositories/${repoId}/pr-reviews`, {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export function listPRReviews(repoId: string) {
  return request<AgentRun[]>(`/api/repositories/${repoId}/pr-reviews`);
}

export function getPRReview(repoId: string, runId: string) {
  return request<AgentRun>(`/api/repositories/${repoId}/pr-reviews/${runId}`);
}
