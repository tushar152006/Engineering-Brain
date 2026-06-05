"""Pydantic schemas for Engineering Brain API.

All public API request/response models live here.
Internal-only types (e.g. SourceFile) also live here for convenience.
"""

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, HttpUrl


class RepositorySource(StrEnum):
    github = "github"
    local = "local"


class IndexingStatus(StrEnum):
    pending = "pending"
    indexing = "indexing"
    embedding = "embedding"
    ready = "ready"
    failed = "failed"


class IndexRepositoryRequest(BaseModel):
    source: RepositorySource
    url: HttpUrl | None = None
    local_path: str | None = None
    name: str | None = None


class SourceFile(BaseModel):
    path: str
    language: str
    content: str
    size_bytes: int


# ---------------------------------------------------------------------------
# Chunk — core unit of indexed content
# ---------------------------------------------------------------------------

class Chunk(BaseModel):
    id: str
    repo_id: str
    file_path: str
    language: str
    chunk_type: str          # "code" | "docs"
    title: str
    content: str
    start_line: int
    end_line: int
    token_estimate: int
    embedding: list[float] | None = None
    # Phase 2: extracted symbol metadata
    symbol_name: str | None = None
    symbol_kind: str | None = None  # "function" | "class" | "method" | "variable"
    imports: list[str] = Field(default_factory=list)  # files this chunk imports


# ---------------------------------------------------------------------------
# Symbol — extracted code symbol (function, class, etc.)
# ---------------------------------------------------------------------------

class Symbol(BaseModel):
    id: str
    repo_id: str
    file_path: str
    name: str
    qualified_name: str
    kind: str               # "function" | "class" | "method" | "variable" | "interface"
    start_line: int
    end_line: int
    signature: str | None = None
    language: str


# ---------------------------------------------------------------------------
# Graph edge — file/symbol dependency relationship
# ---------------------------------------------------------------------------

class GraphEdge(BaseModel):
    source_path: str        # importing file
    target_path: str        # imported file / module
    relationship: str       # "imports" | "calls" | "extends"
    line: int | None = None


# ---------------------------------------------------------------------------
# Repository
# ---------------------------------------------------------------------------

class RepositoryRecord(BaseModel):
    id: str
    name: str
    source: RepositorySource
    source_url: str | None = None
    file_count: int = 0
    chunk_count: int = 0
    embedded_chunk_count: int = 0
    symbol_count: int = 0
    edge_count: int = 0
    languages: list[str] = Field(default_factory=list)
    indexed_at: str
    status: IndexingStatus = IndexingStatus.ready
    error: str | None = None


class RepositoryIndexResponse(BaseModel):
    repository: RepositoryRecord
    indexed_files: int
    indexed_chunks: int
    skipped_files: int


class IndexJobStatusResponse(BaseModel):
    repo_id: str
    status: IndexingStatus
    file_count: int
    chunk_count: int
    embedded_chunk_count: int
    symbol_count: int = 0
    error: str | None = None


# ---------------------------------------------------------------------------
# Search & Chat
# ---------------------------------------------------------------------------

class SearchRequest(BaseModel):
    repo_id: str
    query: str = Field(min_length=2)
    limit: int = Field(default=8, ge=1, le=20)


class Citation(BaseModel):
    chunk_id: str
    file_path: str
    start_line: int
    end_line: int
    title: str
    excerpt: str
    score: float


class SearchResponse(BaseModel):
    query: str
    results: list[Citation]


class ChatRequest(BaseModel):
    repo_id: str
    question: str = Field(min_length=3)
    limit: int = Field(default=8, ge=1, le=12)


class ChatResponse(BaseModel):
    answer: str
    citations: list[Citation]
    confidence: str
    unknowns: list[str] = Field(default_factory=list)
    model_used: str | None = None


# ---------------------------------------------------------------------------
# Architecture Summary
# ---------------------------------------------------------------------------

class ArchitectureSummaryRequest(BaseModel):
    repo_id: str


class DirectorySummary(BaseModel):
    name: str
    chunk_count: int


class FrameworkSignal(BaseModel):
    name: str
    evidence_files: list[str]


class ArchitectureSummaryResponse(BaseModel):
    repository: RepositoryRecord
    summary: str
    top_directories: list[DirectorySummary]
    important_files: list[str]
    entrypoints: list[str]
    frameworks: list[FrameworkSignal]
    next_steps: list[str]
    # Phase 2 additions
    llm_narrative: str | None = None      # LLM-generated architecture narrative
    docs_gap_report: str | None = None    # Docs-vs-code gap report
    symbol_count: int = 0
    top_symbols: list[dict[str, Any]] = Field(default_factory=list)
    dependency_summary: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Symbol & Graph endpoints (Phase 2)
# ---------------------------------------------------------------------------

class SymbolListResponse(BaseModel):
    repo_id: str
    symbols: list[Symbol]
    total: int


class GraphResponse(BaseModel):
    repo_id: str
    nodes: list[dict[str, Any]]   # {id, label, language, chunk_count}
    edges: list[dict[str, Any]]   # {source, target, relationship}
    total_nodes: int
    total_edges: int


# ---------------------------------------------------------------------------
# Phase 3: PR Review Agent
# ---------------------------------------------------------------------------

class DiffHunk(BaseModel):
    """Single hunk of a unified diff."""
    file_path: str
    old_start: int
    new_start: int
    added_lines: list[str]
    removed_lines: list[str]
    context_lines: list[str]
    raw: str


class PRInfo(BaseModel):
    """Metadata about a pull request."""
    repo_id: str
    pr_number: int | None = None
    title: str = ""
    body: str = ""
    author_login: str = ""
    base_branch: str = "main"
    head_branch: str = ""
    changed_files: list[str] = Field(default_factory=list)
    diff: str = ""                       # raw unified diff text
    github_repo: str | None = None       # owner/repo for GitHub API


class ReviewComment(BaseModel):
    """Single review comment from the Code Review Agent."""
    file_path: str
    line: int | None = None
    risk: str                            # "high" | "medium" | "low"
    category: str                        # "architecture" | "security" | "test" | "style" | "logic"
    message: str
    suggestion: str | None = None
    evidence: list[str] = Field(default_factory=list)  # cited file paths / docs
    confidence: str = "medium"           # "high" | "medium" | "low"


class PRReviewRequest(BaseModel):
    """Request to run PR review agent."""
    repo_id: str
    pr_number: int | None = None
    diff: str | None = None              # raw diff text (if not fetching from GitHub)
    title: str = ""
    body: str = ""
    author_login: str = ""
    github_repo: str | None = None       # owner/repo if posting comments
    post_to_github: bool = False         # set True to post comments via GitHub API
    dry_run: bool = True


class PRReviewResponse(BaseModel):
    """Response from the Code Review Agent."""
    run_id: str
    repo_id: str
    pr_number: int | None = None
    comments: list[ReviewComment]
    risk_summary: str                    # "high" | "medium" | "low" | "clean"
    summary: str                         # 1–2 sentence narrative
    missing_tests: list[str] = Field(default_factory=list)
    changed_files: list[str] = Field(default_factory=list)
    model_used: str | None = None
    posted_to_github: bool = False
    dry_run: bool = True


# ---------------------------------------------------------------------------
# Phase 3: Agent Run Logging
# ---------------------------------------------------------------------------

class AgentRunStatus(StrEnum):
    running = "running"
    done = "done"
    failed = "failed"


class AgentRun(BaseModel):
    """Persisted record of a single agent invocation."""
    id: str
    repo_id: str
    agent_type: str                      # "pr_review" | "architecture" | "public_analyze"
    status: AgentRunStatus = AgentRunStatus.done
    input: dict[str, Any] = Field(default_factory=dict)
    output: dict[str, Any] | None = None
    model: str | None = None
    error: str | None = None
    started_at: str
    completed_at: str | None = None


class AgentRunListResponse(BaseModel):
    runs: list[AgentRun]
    total: int


# ---------------------------------------------------------------------------
# Phase 3: Feedback
# ---------------------------------------------------------------------------

class FeedbackLabel(StrEnum):
    useful = "useful"
    wrong = "wrong"
    noisy = "noisy"
    incomplete = "incomplete"


class FeedbackRequest(BaseModel):
    run_id: str
    rating: int = Field(ge=1, le=5)     # 1–5 stars
    label: FeedbackLabel | None = None
    comment: str | None = None


class FeedbackRecord(BaseModel):
    id: str
    run_id: str
    rating: int
    label: FeedbackLabel | None = None
    comment: str | None = None
    created_at: str


class FeedbackResponse(BaseModel):
    feedback: FeedbackRecord


# ---------------------------------------------------------------------------
# Phase 3: Public Repo Analyzer
# ---------------------------------------------------------------------------

class PublicAnalyzeRequest(BaseModel):
    """Kick off a no-signup analysis of a public GitHub repo."""
    github_url: str                      # e.g. https://github.com/owner/repo
    requester_ip: str | None = None      # populated by the route handler


class PublicReportStatus(StrEnum):
    pending = "pending"
    analyzing = "analyzing"
    ready = "ready"
    failed = "failed"


class PublicReportResponse(BaseModel):
    """Status + content of a public repo analysis report."""
    report_id: str
    github_url: str
    status: PublicReportStatus
    # populated when status == ready
    repo_name: str | None = None
    summary: str | None = None
    languages: list[str] = Field(default_factory=list)
    frameworks: list[dict[str, Any]] = Field(default_factory=list)
    top_directories: list[dict[str, Any]] = Field(default_factory=list)
    entrypoints: list[str] = Field(default_factory=list)
    important_files: list[str] = Field(default_factory=list)
    symbol_count: int = 0
    file_count: int = 0
    next_steps: list[str] = Field(default_factory=list)
    error: str | None = None
    created_at: str
    share_url: str | None = None


# ---------------------------------------------------------------------------
# Phase 3: GitHub Webhook
# ---------------------------------------------------------------------------

class GitHubWebhookPRPayload(BaseModel):
    """Minimal subset of GitHub pull_request webhook payload."""
    action: str                          # "opened" | "synchronize" | "reopened" | "closed"
    number: int
    pull_request: dict[str, Any]
    repository: dict[str, Any]

