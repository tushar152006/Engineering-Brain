import {
  Brain,
  CheckCircle,
  ChevronDown,
  ChevronUp,
  ClipboardCopy,
  Code2,
  GitBranch,
  Layers,
  Loader2,
  MessageSquareText,
  Network,
  RotateCcw,
  Search,
  ServerCog,
  Sparkles,
  ThumbsUp,
  ThumbsDown,
  Trash2,
  Zap,
  GitPullRequest,
  ExternalLink,
  Globe,
  AlertCircle,
  Check,
} from "lucide-react";
import {
  FormEvent,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import ReactMarkdown from "react-markdown";
import rehypeHighlight from "rehype-highlight";
import {
  architectureSummary,
  architectureSummaryDeep,
  chatStream,
  deleteRepository,
  getGraph,
  getLLMStatus,
  getRepositoryStatus,
  getSymbols,
  indexRepository,
  listRepositories,
  searchRepository,
  submitFeedback,
  triggerPRReview,
  listPRReviews,
  getPRReview,
  analyzePublicRepo,
  getPublicReport,
} from "./api";
import type {
  ArchitectureSummary,
  Citation,
  GraphResponse,
  IndexingStatus,
  LLMStatus,
  RepositoryRecord,
  SearchResponse,
  Symbol,
  AgentRun,
} from "./types";

// ── Types ─────────────────────────────────────────────────────────────────────
interface ChatTurn {
  id: string;
  question: string;
  answer: string;
  citations: Citation[];
  confidence: string;
  unknowns?: string[];
  modelUsed?: string | null;
  streaming?: boolean;
}

type MainTab = "chat" | "search" | "symbols" | "graph" | "architecture" | "pr_reviews";

// ── Polling interval ──────────────────────────────────────────────────────────
const POLL_INTERVAL_MS = 2500;

// ── Helpers ───────────────────────────────────────────────────────────────────
function isActive(status: IndexingStatus) {
  return status === "indexing" || status === "embedding";
}

function statusLabel(status: IndexingStatus): string {
  switch (status) {
    case "indexing":  return "Indexing…";
    case "embedding": return "Embedding…";
    case "ready":     return "Ready";
    case "failed":    return "Failed";
    default:          return "Pending";
  }
}

function copyToClipboard(text: string) {
  navigator.clipboard.writeText(text).catch(() => {});
}

function uid() {
  return Math.random().toString(36).slice(2, 10);
}

function kindColor(kind: string): string {
  const map: Record<string, string> = {
    class: "#7C3AED",
    function: "#0EA5E9",
    async_function: "#06B6D4",
    method: "#8B5CF6",
    interface: "#10B981",
    variable: "#F59E0B",
  };
  return map[kind] || "#6B7280";
}

// ── Sub-components ────────────────────────────────────────────────────────────
function CitationCard({ citation }: { citation: Citation }) {
  const [expanded, setExpanded] = useState(false);
  return (
    <article
      className={`citation${expanded ? " expanded" : ""}`}
      onClick={() => setExpanded((e) => !e)}
    >
      <div className="citation-header">
        <span className="citation-path">{citation.file_path}</span>
        <div style={{ display: "flex", alignItems: "center", gap: 6, flexShrink: 0 }}>
          <span className="citation-lines">:{citation.start_line}–{citation.end_line}</span>
          <span className="citation-score">{citation.score.toFixed(3)}</span>
          {expanded ? <ChevronUp size={12} color="var(--text-muted)" /> : <ChevronDown size={12} color="var(--text-muted)" />}
        </div>
      </div>
      <pre className="citation-excerpt">{citation.excerpt}</pre>
    </article>
  );
}

function CitationList({ result }: { result: SearchResponse | null }) {
  if (!result) return null;
  if (result.results.length === 0)
    return <p className="muted">No matching citations found.</p>;
  return (
    <div className="results">
      {result.results.map((c) => (
        <CitationCard key={c.chunk_id} citation={c} />
      ))}
    </div>
  );
}

function IndexingProgress({
  status,
  chunkCount,
  embeddedCount,
}: {
  status: IndexingStatus;
  chunkCount: number;
  embeddedCount: number;
}) {
  const pct =
    status === "embedding" && chunkCount > 0
      ? Math.round((embeddedCount / chunkCount) * 100)
      : null;

  return (
    <div className="progress-wrap">
      <div className="progress-label">
        <span>{statusLabel(status)}</span>
        {pct !== null && <span>{pct}%</span>}
        {status === "indexing" && <span>Extracting symbols + building graph…</span>}
      </div>
      <div className="progress-track">
        {pct !== null ? (
          <div className="progress-fill" style={{ width: `${pct}%` }} />
        ) : (
          <div className="progress-fill indeterminate" />
        )}
      </div>
    </div>
  );
}

function ChatTurnBlock({ turn }: { turn: ChatTurn }) {
  const [copied, setCopied] = useState(false);
  const [citationsOpen, setCitationsOpen] = useState(false);
  const [feedbackGiven, setFeedbackGiven] = useState<number | null>(null);

  function handleCopy() {
    copyToClipboard(turn.answer);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  function handleFeedback(rating: number) {
    if (feedbackGiven !== null) return;
    setFeedbackGiven(rating);
    submitFeedback({
      run_id: turn.id,
      rating,
    }).catch(() => {
      setFeedbackGiven(null); // Revert on fail
    });
  }

  return (
    <div className="chat-turn">
      <div className="chat-question">
        <span className="chat-role-label">You</span>
        <p>{turn.question}</p>
      </div>

      <div className="chat-answer">
        <span className="chat-role-label assistant">brain</span>
        {turn.streaming && !turn.answer ? (
          <div className="streaming-placeholder">
            <span className="blink-cursor" />
          </div>
        ) : (
          <div className="answer-text">
            <ReactMarkdown rehypePlugins={[rehypeHighlight]}>
              {turn.answer}
            </ReactMarkdown>
            {turn.unknowns && turn.unknowns.length > 0 && (
              <div className="unknowns-block" style={{ marginTop: 12, padding: "8px 12px", background: "var(--surface-2)", borderRadius: 6 }}>
                <strong style={{ fontSize: 12, color: "var(--text-muted)" }}>Unknowns:</strong>
                <ul style={{ fontSize: 13, margin: "4px 0 0 0", paddingLeft: 20 }}>
                  {turn.unknowns.map((u, i) => <li key={i}>{u}</li>)}
                </ul>
              </div>
            )}
            {turn.streaming && <span className="blink-cursor inline" />}
          </div>
        )}

        {!turn.streaming && turn.answer && (
          <div className="answer-meta">
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <span className={`confidence-badge ${turn.confidence}`}>
                {turn.confidence} confidence
              </span>
              {turn.modelUsed && (
                <div className="llm-badge">
                  <Sparkles size={10} />
                  {turn.modelUsed}
                </div>
              )}
            </div>
            <div style={{ display: "flex", gap: 6 }}>
              {turn.citations.length > 0 && (
                <button
                  type="button"
                  className="icon-btn"
                  onClick={() => setCitationsOpen((o) => !o)}
                >
                  {citationsOpen ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
                  {turn.citations.length} citations
                </button>
              )}
              <button type="button" className="icon-btn" onClick={() => handleFeedback(5)} title="Helpful" disabled={feedbackGiven !== null}>
                <ThumbsUp size={12} color={feedbackGiven === 5 ? "var(--primary)" : undefined} />
              </button>
              <button type="button" className="icon-btn" onClick={() => handleFeedback(1)} title="Not helpful" disabled={feedbackGiven !== null}>
                <ThumbsDown size={12} color={feedbackGiven === 1 ? "var(--error)" : undefined} />
              </button>
              <button type="button" className="icon-btn" onClick={handleCopy} title="Copy answer">
                {copied ? <CheckCircle size={12} /> : <ClipboardCopy size={12} />}
                {copied ? " Copied" : " Copy"}
              </button>
            </div>
          </div>
        )}

        {citationsOpen && turn.citations.length > 0 && (
          <div className="results" style={{ marginTop: 10 }}>
            {turn.citations.map((c) => (
              <CitationCard key={c.chunk_id} citation={c} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

// ── Symbol Explorer Panel ─────────────────────────────────────────────────────
function SymbolPanel({ repoId, symbolCount }: { repoId: string; symbolCount: number }) {
  const [symbols, setSymbols] = useState<Symbol[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [q, setQ] = useState("");
  const [kindFilter, setKindFilter] = useState("");
  const [langFilter, setLangFilter] = useState("");
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const fetchSymbols = useCallback(async (query: string, kind: string, lang: string) => {
    setLoading(true);
    try {
      const res = await getSymbols(repoId, {
        q: query || undefined,
        kind: kind || undefined,
        language: lang || undefined,
        limit: 200,
      });
      setSymbols(res.symbols);
      setTotal(res.total);
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  }, [repoId]);

  useEffect(() => {
    fetchSymbols("", "", "");
  }, [fetchSymbols]);

  function handleQChange(val: string) {
    setQ(val);
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => fetchSymbols(val, kindFilter, langFilter), 300);
  }

  function handleKindChange(val: string) {
    setKindFilter(val);
    fetchSymbols(q, val, langFilter);
  }

  function handleLangChange(val: string) {
    setLangFilter(val);
    fetchSymbols(q, kindFilter, val);
  }

  return (
    <div className="panel symbol-panel">
      <div className="panel-title">
        <Code2 size={15} />
        <span>Symbol Explorer</span>
        <span className="muted" style={{ marginLeft: "auto", fontSize: "11px" }}>
          {total} symbols total
        </span>
      </div>

      {symbolCount === 0 ? (
        <p className="muted">No symbols extracted. Re-index this repository to extract symbols.</p>
      ) : (
        <>
          <div className="symbol-filters">
            <input
              className="symbol-search"
              placeholder="Search symbols…"
              value={q}
              onChange={(e) => handleQChange(e.target.value)}
            />
            <select value={kindFilter} onChange={(e) => handleKindChange(e.target.value)}>
              <option value="">All kinds</option>
              <option value="class">Class</option>
              <option value="function">Function</option>
              <option value="async_function">Async Function</option>
              <option value="method">Method</option>
              <option value="interface">Interface</option>
            </select>
            <select value={langFilter} onChange={(e) => handleLangChange(e.target.value)}>
              <option value="">All languages</option>
              <option value="python">Python</option>
              <option value="typescript">TypeScript</option>
              <option value="javascript">JavaScript</option>
            </select>
          </div>

          {loading ? (
            <div className="loader-row"><Loader2 size={16} className="spin-icon" /> Loading…</div>
          ) : symbols.length === 0 ? (
            <p className="muted">No symbols match your filter.</p>
          ) : (
            <div className="symbol-list">
              {symbols.map((sym) => (
                <div key={sym.id} className="symbol-row">
                  <span
                    className="symbol-kind-badge"
                    style={{ background: kindColor(sym.kind) + "22", color: kindColor(sym.kind) }}
                  >
                    {sym.kind.replace("_", " ")}
                  </span>
                  <div className="symbol-info">
                    <span className="symbol-name">{sym.name}</span>
                    {sym.signature && (
                      <code className="symbol-sig">{sym.signature}</code>
                    )}
                    <span className="symbol-file">{sym.file_path}:{sym.start_line}</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
}

// ── Dependency Graph Panel ────────────────────────────────────────────────────
function GraphPanel({ repoId, edgeCount }: { repoId: string; edgeCount: number }) {
  const [graph, setGraph] = useState<GraphResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [selected, setSelected] = useState<string | null>(null);

  async function loadGraph() {
    setLoading(true);
    try {
      const res = await getGraph(repoId, 60);
      setGraph(res);
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (edgeCount > 0) loadGraph();
  }, [repoId, edgeCount]);

  if (edgeCount === 0) {
    return (
      <div className="panel">
        <div className="panel-title"><Network size={15} /><span>Dependency Graph</span></div>
        <p className="muted">No import edges extracted. Re-index this repository to build the dependency graph.</p>
      </div>
    );
  }

  const selectedEdges = selected
    ? graph?.edges.filter((e) => e.source === selected || e.target === selected) ?? []
    : [];

  const langColors: Record<string, string> = {
    python: "#3B82F6",
    typescript: "#0EA5E9",
    javascript: "#F59E0B",
    unknown: "#6B7280",
  };

  return (
    <div className="panel graph-panel">
      <div className="panel-title">
        <Network size={15} />
        <span>Dependency Graph</span>
        <span className="muted" style={{ marginLeft: "auto", fontSize: "11px" }}>
          {graph ? `${graph.total_nodes} files · ${graph.total_edges} edges` : ""}
        </span>
      </div>

      {loading ? (
        <div className="loader-row"><Loader2 size={16} className="spin-icon" /> Loading graph…</div>
      ) : graph ? (
        <div className="graph-container">
          <div className="graph-legend">
            {Object.entries(langColors).map(([lang, color]) => (
              <span key={lang} className="legend-item">
                <span className="legend-dot" style={{ background: color }} />
                {lang}
              </span>
            ))}
          </div>

          <div className="graph-node-grid">
            {graph.nodes.map((node) => {
              const isSelected = selected === node.id;
              const isNeighbor = selectedEdges.some((e) => e.source === node.id || e.target === node.id);
              return (
                <div
                  key={node.id}
                  className={`graph-node${isSelected ? " selected" : isNeighbor ? " neighbor" : ""}`}
                  onClick={() => setSelected(isSelected ? null : node.id)}
                  title={node.id}
                  style={{
                    borderLeftColor: langColors[node.language] || langColors.unknown,
                    opacity: selected && !isSelected && !isNeighbor ? 0.35 : 1,
                  }}
                >
                  <span className="graph-node-label">{node.label}</span>
                  <span className="graph-node-meta">{node.degree} edges · {node.chunk_count} chunks</span>
                </div>
              );
            })}
          </div>

          {selected && selectedEdges.length > 0 && (
            <div className="graph-detail">
              <div className="graph-detail-title">
                Connections for <strong>{selected.split("/").pop()}</strong>
              </div>
              {selectedEdges.map((e, i) => (
                <div key={i} className="graph-edge-row">
                  <span className="graph-edge-source">{e.source.split("/").pop()}</span>
                  <span className="graph-edge-rel">→</span>
                  <span className="graph-edge-target">{e.target.split("/").pop()}</span>
                </div>
              ))}
            </div>
          )}

          {graph.total_nodes > graph.nodes.length && (
            <p className="muted" style={{ marginTop: 12, fontSize: 11 }}>
              Showing {graph.nodes.length} of {graph.total_nodes} files. Most connected files are shown first.
            </p>
          )}
        </div>
      ) : null}
    </div>
  );
}

// ── Architecture Panel ────────────────────────────────────────────────────────
function ArchitecturePanel({
  repoId,
  busy,
  repoIsIndexing,
}: {
  repoId: string;
  busy: boolean;
  repoIsIndexing: boolean;
}) {
  const [summary, setSummary] = useState<ArchitectureSummary | null>(null);
  const [isBusy, setIsBusy] = useState(false);
  const [mode, setMode] = useState<"static" | "deep">("static");

  async function handleSummary() {
    setIsBusy(true);
    setSummary(null);
    try {
      const result =
        mode === "deep"
          ? await architectureSummaryDeep(repoId)
          : await architectureSummary(repoId);
      setSummary(result);
    } catch {
      // ignore
    } finally {
      setIsBusy(false);
    }
  }

  return (
    <div className="panel">
      <div className="panel-title">
        <Brain size={15} />
        <span>Architecture Summary</span>
      </div>

      <div className="arch-controls">
        <div className="mode-toggle">
          <button
            type="button"
            className={mode === "static" ? "mode-btn active" : "mode-btn"}
            onClick={() => setMode("static")}
          >
            <Layers size={12} /> Static
          </button>
          <button
            type="button"
            className={mode === "deep" ? "mode-btn active" : "mode-btn"}
            onClick={() => setMode("deep")}
          >
            <Sparkles size={12} /> AI Narrative
          </button>
        </div>
        <button
          type="button"
          className="button-primary"
          disabled={!repoId || busy || isBusy || repoIsIndexing}
          onClick={handleSummary}
        >
          {isBusy ? <><Loader2 size={13} className="spin-icon" /> Analysing…</> : "Generate"}
        </button>
      </div>

      {summary && (
        <div className="arch-content">
          {/* Summary */}
          <p className="summary-text">{summary.summary}</p>

          {/* LLM Narrative */}
          {summary.llm_narrative && (
            <div className="llm-narrative">
              <div className="llm-narrative-title">
                <Sparkles size={12} /> AI Architecture Narrative
              </div>
              <ReactMarkdown>{summary.llm_narrative}</ReactMarkdown>
            </div>
          )}

          {/* Stats row */}
          <div className="arch-stats-row">
            <div className="arch-stat">
              <span className="arch-stat-value">{summary.symbol_count}</span>
              <span className="arch-stat-label">Symbols</span>
            </div>
            <div className="arch-stat">
              <span className="arch-stat-value">{summary.dependency_summary.total_edges ?? 0}</span>
              <span className="arch-stat-label">Import edges</span>
            </div>
            <div className="arch-stat">
              <span className="arch-stat-value">{summary.entrypoints.length}</span>
              <span className="arch-stat-label">Entrypoints</span>
            </div>
            <div className="arch-stat">
              <span className="arch-stat-value">{summary.frameworks.length}</span>
              <span className="arch-stat-label">Frameworks</span>
            </div>
          </div>

          {/* Top Directories */}
          {summary.top_directories.length > 0 && (
            <>
              <h3 style={{ marginTop: 20 }}>Top Directories</h3>
              <div className="tag-row">
                {summary.top_directories.map((d) => (
                  <span className="tag" key={d.name}>
                    {d.name} · {d.chunk_count}
                  </span>
                ))}
              </div>
            </>
          )}

          {/* Frameworks */}
          {summary.frameworks.length > 0 && (
            <>
              <h3 style={{ marginTop: 16 }}>Framework Signals</h3>
              <div className="signal-list">
                {summary.frameworks.map((fw) => (
                  <div className="signal" key={fw.name}>
                    <span className="signal-name">{fw.name}</span>
                    <span className="signal-files">{fw.evidence_files.join(", ")}</span>
                  </div>
                ))}
              </div>
            </>
          )}

          {/* Top Symbols */}
          {summary.top_symbols.length > 0 && (
            <>
              <h3 style={{ marginTop: 16 }}>Key Symbols</h3>
              <div className="symbol-list compact">
                {summary.top_symbols.slice(0, 12).map((s, i) => (
                  <div key={i} className="symbol-row">
                    <span
                      className="symbol-kind-badge"
                      style={{ background: kindColor(s.kind) + "22", color: kindColor(s.kind) }}
                    >
                      {s.kind.replace("_", " ")}
                    </span>
                    <div className="symbol-info">
                      <span className="symbol-name">{s.name}</span>
                      <span className="symbol-file">{s.file}:{s.line}</span>
                    </div>
                  </div>
                ))}
              </div>
            </>
          )}

          {/* Most Imported files */}
          {(summary.dependency_summary.most_imported?.length ?? 0) > 0 && (
            <>
              <h3 style={{ marginTop: 16 }}>Most Imported Files</h3>
              <ul className="file-list">
                {summary.dependency_summary.most_imported!.map(([file, count]) => (
                  <li key={file}>{file} <span className="muted">({count} imports)</span></li>
                ))}
              </ul>
            </>
          )}

          {/* Entrypoints */}
          {summary.entrypoints.length > 0 && (
            <>
              <h3 style={{ marginTop: 16 }}>Entrypoints</h3>
              <ul className="file-list">
                {summary.entrypoints.map((f) => <li key={f}>{f}</li>)}
              </ul>
            </>
          )}

          {/* Next steps */}
          {summary.next_steps.length > 0 && (
            <div className="next-steps">
              <div className="next-steps-title">Suggested next steps</div>
              {summary.next_steps.map((s, i) => (
                <div key={i} className="next-step-item">→ {s}</div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ── Main app ──────────────────────────────────────────────────────────────────
export function App() {
  const [repositories, setRepositories] = useState<RepositoryRecord[]>([]);
  const [selectedRepoId, setSelectedRepoId] = useState("");
  const [source, setSource] = useState<"github" | "local">("github");
  const [repoInput, setRepoInput] = useState("https://github.com/fastapi/fastapi");
  const [query, setQuery] = useState("");
  const [question, setQuestion] = useState("");
  const [searchResult, setSearchResult] = useState<SearchResponse | null>(null);
  const [chatHistory, setChatHistory] = useState<ChatTurn[]>([]);
  const [activeTab, setActiveTab] = useState<MainTab>("chat");
  const [statusMsg, setStatusMsg] = useState("Ready");
  const [isBusy, setIsBusy] = useState(false);
  const [isStreaming, setIsStreaming] = useState(false);
  const [llmStatus, setLLMStatus] = useState<LLMStatus | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const chatBottomRef = useRef<HTMLDivElement>(null);
  const streamAbortRef = useRef<AbortController | null>(null);

  // Phase 3 States
  const [viewMode, setViewMode] = useState<"workspace" | "public_analyzer">("workspace");
  const [prReviews, setPrReviews] = useState<AgentRun[]>([]);
  const [selectedPRReview, setSelectedPRReview] = useState<AgentRun | null>(null);
  const [prNumberInput, setPrNumberInput] = useState("");
  const [prReviewDryRun, setPrReviewDryRun] = useState(true);
  const [prReviewPostToGithub, setPrReviewPostToGithub] = useState(false);
  const [prReviewBusy, setPrReviewBusy] = useState(false);

  const [publicUrlInput, setPublicUrlInput] = useState("https://github.com/pallets/flask");
  const [publicReport, setPublicReport] = useState<any | null>(null);
  const [publicReportLoading, setPublicReportLoading] = useState(false);
  const [publicReportStatusMsg, setPublicReportStatusMsg] = useState("");
  const [waitlistEmail, setWaitlistEmail] = useState("");
  const [waitlistSuccess, setWaitlistSuccess] = useState(false);
  const [copiedShareLink, setCopiedShareLink] = useState(false);

  const selectedRepo = useMemo(
    () => repositories.find((r) => r.id === selectedRepoId) ?? repositories[0],
    [repositories, selectedRepoId]
  );

  // Scroll to bottom of chat thread when history grows
  useEffect(() => {
    chatBottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [chatHistory]);

  // Fetch LLM availability once on mount
  useEffect(() => {
    getLLMStatus().then(setLLMStatus).catch(() => {});
  }, []);

  // Parse shareable public reports from URL parameter
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const reportId = params.get("report");
    if (reportId) {
      setViewMode("public_analyzer");
      setPublicReportLoading(true);
      getPublicReport(reportId)
        .then((report) => {
          setPublicReport(report);
          setPublicUrlInput(report.github_url);
        })
        .catch(() => {
          setPublicReportStatusMsg("Failed to load the shared report.");
        })
        .finally(() => {
          setPublicReportLoading(false);
        });
    }
  }, []);

  // Initial repo list
  useEffect(() => {
    listRepositories()
      .then((items) => {
        setRepositories(items);
        if (items[0]) setSelectedRepoId(items[0].id);
      })
      .catch(() => setStatusMsg("API not connected — is the backend running?"));
  }, []);

  // Poll active PR reviews in background
  useEffect(() => {
    const runningReviews = prReviews.filter((r) => r.status === "running");
    if (runningReviews.length === 0) return;

    const interval = setInterval(async () => {
      await Promise.allSettled(
        runningReviews.map(async (run) => {
          try {
            const updated = await getPRReview(selectedRepoId, run.id);
            if (updated.status !== "running") {
              setPrReviews((current) =>
                current.map((r) => (r.id === run.id ? updated : r))
              );
              if (selectedPRReview?.id === run.id) {
                setSelectedPRReview(updated);
              }
            }
          } catch {
            // ignore
          }
        })
      );
    }, 3000);

    return () => clearInterval(interval);
  }, [prReviews, selectedRepoId, selectedPRReview]);

  // Fetch PR reviews when selected repository changes or when reviews tab becomes active
  const fetchPRReviews = useCallback(async () => {
    if (!selectedRepoId) return;
    try {
      const runs = await listPRReviews(selectedRepoId);
      setPrReviews(runs);
    } catch {
      // ignore
    }
  }, [selectedRepoId]);

  useEffect(() => {
    if (activeTab === "pr_reviews" && selectedRepoId) {
      fetchPRReviews();
    }
  }, [activeTab, selectedRepoId, fetchPRReviews]);

  // ── Handlers ──────────────────────────────────────────────────────────────

  async function handleIndex(event: FormEvent) {
    event.preventDefault();
    setIsBusy(true);
    setStatusMsg("Starting indexing job…");
    try {
      const response = await indexRepository(
        source === "github" ? { source, url: repoInput } : { source, local_path: repoInput }
      );
      const items = await listRepositories();
      setRepositories(items);
      setSelectedRepoId(response.repository.id);
      setStatusMsg(`Indexing started for "${response.repository.name}"`);
    } catch (error) {
      setStatusMsg(error instanceof Error ? error.message : "Indexing failed");
    } finally {
      setIsBusy(false);
    }
  }

  async function handleReindex() {
    if (!selectedRepo) return;
    setIsBusy(true);
    setStatusMsg("Re-indexing repository…");
    try {
      await indexRepository(
        selectedRepo.source === "github"
          ? { source: "github", url: selectedRepo.source_url ?? "" }
          : { source: "local", local_path: selectedRepo.source_url ?? "" }
      );
      const items = await listRepositories();
      setRepositories(items);
      setStatusMsg(`Re-index started for "${selectedRepo.name}"`);
    } catch (error) {
      setStatusMsg(error instanceof Error ? error.message : "Re-index failed");
    } finally {
      setIsBusy(false);
    }
  }

  async function handleDelete(repoId: string) {
    if (!window.confirm("Delete this repository and all its indexed data?")) return;
    setDeletingId(repoId);
    try {
      await deleteRepository(repoId);
      const items = await listRepositories();
      setRepositories(items);
      if (selectedRepoId === repoId) {
        setSelectedRepoId(items[0]?.id ?? "");
        setSearchResult(null);
        setChatHistory([]);
      }
      setStatusMsg("Repository deleted");
    } catch (error) {
      setStatusMsg(error instanceof Error ? error.message : "Delete failed");
    } finally {
      setDeletingId(null);
    }
  }

  async function handleTriggerPRReview(event: FormEvent) {
    event.preventDefault();
    if (!selectedRepoId || prReviewBusy) return;
    const prNum = parseInt(prNumberInput.trim());
    if (isNaN(prNum)) {
      alert("Please enter a valid PR number.");
      return;
    }

    setPrReviewBusy(true);
    setStatusMsg(`Triggering review for PR #${prNum}…`);
    try {
      const newRun = await triggerPRReview(selectedRepoId, {
        pr_number: prNum,
        post_to_github: prReviewPostToGithub,
        dry_run: prReviewDryRun,
      });
      setPrReviews((current) => [newRun, ...current]);
      setSelectedPRReview(newRun);
      setPrNumberInput("");
      setStatusMsg(`PR Review Agent running for PR #${prNum}`);
    } catch (error) {
      alert(error instanceof Error ? error.message : "Failed to trigger PR review");
      setStatusMsg("PR Review trigger failed");
    } finally {
      setPrReviewBusy(false);
    }
  }

  async function handlePublicAnalyze(event: FormEvent) {
    event.preventDefault();
    if (publicReportLoading || !publicUrlInput.trim()) return;

    setPublicReport(null);
    setPublicReportLoading(true);
    setWaitlistSuccess(false);
    setCopiedShareLink(false);
    setPublicReportStatusMsg("Cloning and parsing public repository…");

    try {
      const initReport = await analyzePublicRepo(publicUrlInput.trim());
      let reportId = initReport.report_id;
      
      // Poll report status
      const pollInterval = setInterval(async () => {
        try {
          const report = await getPublicReport(reportId);
          if (report.status === "ready") {
            clearInterval(pollInterval);
            setPublicReport(report);
            setPublicReportLoading(false);
            setPublicReportStatusMsg("");
          } else if (report.status === "failed") {
            clearInterval(pollInterval);
            setPublicReportStatusMsg(`Analysis failed: ${report.error || "Unknown error"}`);
            setPublicReportLoading(false);
          } else {
            setPublicReportStatusMsg(`Repository Status: ${report.status} (this can take up to a minute)`);
          }
        } catch {
          clearInterval(pollInterval);
          setPublicReportStatusMsg("Network error checking analysis status.");
          setPublicReportLoading(false);
        }
      }, 3000);

    } catch (error) {
      setPublicReportStatusMsg(error instanceof Error ? error.message : "Trigger failed");
      setPublicReportLoading(false);
    }
  }

  function handleShareReport() {
    if (!publicReport) return;
    const shareUrl = `${window.location.origin}${window.location.pathname}?report=${publicReport.report_id}`;
    copyToClipboard(shareUrl);
    setCopiedShareLink(true);
    setTimeout(() => setCopiedShareLink(false), 2500);
  }

  function handleJoinWaitlist(e: FormEvent) {
    e.preventDefault();
    if (!waitlistEmail.trim()) return;
    // Simulate successful waitlist join
    setWaitlistSuccess(true);
    setWaitlistEmail("");
  }

  async function handleSearch(event: FormEvent) {
    event.preventDefault();
    if (!selectedRepo || isActive(selectedRepo.status) || !query.trim()) return;
    setIsBusy(true);
    setStatusMsg("Searching with hybrid retrieval + graph expansion…");
    try {
      setSearchResult(await searchRepository(selectedRepo.id, query));
      setStatusMsg(
        selectedRepo.embedded_chunk_count > 0
          ? "Semantic + keyword + graph search complete"
          : "Keyword search complete (no embeddings yet)"
      );
    } catch (error) {
      setStatusMsg(error instanceof Error ? error.message : "Search failed");
    } finally {
      setIsBusy(false);
    }
  }

  async function handleChat(event: FormEvent) {
    event.preventDefault();
    if (!selectedRepo || isActive(selectedRepo.status) || isStreaming) return;

    const q = question.trim();
    if (!q) return;

    streamAbortRef.current?.abort();
    const abort = new AbortController();
    streamAbortRef.current = abort;

    const turnId = uid();
    const newTurn: ChatTurn = {
      id: turnId,
      question: q,
      answer: "",
      citations: [],
      confidence: "low",
      modelUsed: null,
      streaming: true,
    };
    setChatHistory((h) => [...h, newTurn]);
    setIsStreaming(true);
    setStatusMsg("Streaming answer with graph-expanded context…");

    try {
      await chatStream(
        selectedRepo.id,
        q,
        (token) => {
          setChatHistory((h) =>
            h.map((t) => (t.id === turnId ? { ...t, answer: t.answer + token } : t))
          );
        },
        (meta) => {
          setChatHistory((h) =>
            h.map((t) =>
              t.id === turnId
                ? {
                    ...t,
                    citations: meta.citations,
                    confidence: meta.confidence,
                    unknowns: (meta as any).unknowns,
                    modelUsed: meta.model_used ?? null,
                    streaming: false,
                  }
                : t
            )
          );
          setStatusMsg(meta.model_used ? `Answer from ${meta.model_used}` : "Citation-only answer (Ollama offline)");
        },
        abort.signal
      );
    } catch (err) {
      if ((err as Error).name !== "AbortError") {
        setChatHistory((h) =>
          h.map((t) =>
            t.id === turnId
              ? { ...t, answer: t.answer || "⚠️ Stream error — check that the backend is running.", streaming: false }
              : t
          )
        );
        setStatusMsg("Chat stream failed");
      }
    } finally {
      setIsStreaming(false);
    }
  }

  const busy = isBusy || isStreaming;
  const repoIsIndexing = !!(selectedRepo && isActive(selectedRepo.status));

  // ── Tab content ───────────────────────────────────────────────────────────
  function renderTab() {
    if (!selectedRepo) return null;

    switch (activeTab) {
      case "chat":
        return (
          <div className="panel chat-panel">
            <div className="panel-title">
              <MessageSquareText size={15} />
              <span>AI Q&amp;A</span>
              {chatHistory.length > 0 && (
                <button
                  type="button"
                  className="button-text-link"
                  style={{ marginLeft: "auto" }}
                  onClick={() => { setChatHistory([]); streamAbortRef.current?.abort(); }}
                >
                  Clear
                </button>
              )}
            </div>

            {chatHistory.length > 0 && (
              <div className="chat-thread">
                {chatHistory.map((turn) => (
                  <ChatTurnBlock key={turn.id} turn={turn} />
                ))}
                <div ref={chatBottomRef} />
              </div>
            )}

            {chatHistory.length === 0 && (
              <div className="chat-empty">
                <Brain size={28} color="var(--text-muted)" />
                <p className="muted">Ask anything about this codebase. Answers are grounded in code citations.</p>
                {selectedRepo.symbol_count > 0 && (
                  <p className="muted" style={{ fontSize: 11 }}>
                    {selectedRepo.symbol_count} symbols · {selectedRepo.edge_count} graph edges · graph-expanded retrieval active
                  </p>
                )}
              </div>
            )}

            <form onSubmit={handleChat} style={{ display: "grid", gap: 8 }}>
              <textarea
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                placeholder="How does authentication work in this project?"
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    handleChat(e as unknown as FormEvent);
                  }
                }}
              />
              <button
                type="submit"
                className="button-primary"
                disabled={!selectedRepo || isBusy || repoIsIndexing || isStreaming}
              >
                {isStreaming ? <><Loader2 size={13} className="spin-icon" /> Streaming…</> : "Ask"}
              </button>
            </form>
          </div>
        );

      case "search":
        return (
          <form className="panel" onSubmit={handleSearch}>
            <div className="panel-title">
              <Search size={15} />
              <span>Hybrid Search</span>
              <span className="muted" style={{ marginLeft: "auto", fontSize: 11 }}>
                keyword + semantic + graph
              </span>
            </div>
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="How does routing work?"
              onKeyDown={(e) =>
                e.key === "Enter" && !e.shiftKey && handleSearch(e as unknown as FormEvent)
              }
            />
            <button
              type="submit"
              className="button-primary"
              disabled={!selectedRepo || busy || repoIsIndexing}
            >
              Search
            </button>
            <CitationList result={searchResult} />
          </form>
        );

      case "symbols":
        return (
          <SymbolPanel
            repoId={selectedRepo.id}
            symbolCount={selectedRepo.symbol_count ?? 0}
          />
        );

      case "graph":
        return (
          <GraphPanel
            repoId={selectedRepo.id}
            edgeCount={selectedRepo.edge_count ?? 0}
          />
        );

      case "architecture":
        return (
          <ArchitecturePanel
            repoId={selectedRepo.id}
            busy={busy}
            repoIsIndexing={repoIsIndexing}
          />
        );

      case "pr_reviews":
        return (
          <div className="pr-reviews-tab-layout">
            <div className="pr-review-left-panel">
              {/* Trigger Agent Card */}
              <form className="panel" onSubmit={handleTriggerPRReview}>
                <div className="panel-title">
                  <GitPullRequest size={15} />
                  <span>Review Codebase PR</span>
                </div>
                <label>
                  Pull Request Number
                  <input
                    type="text"
                    value={prNumberInput}
                    onChange={(e) => setPrNumberInput(e.target.value)}
                    placeholder="Enter PR Number (e.g. 42)"
                  />
                </label>
                
                <div className="pr-checkbox-group">
                  <label className="checkbox-label">
                    <input
                      type="checkbox"
                      checked={prReviewDryRun}
                      onChange={(e) => setPrReviewDryRun(e.target.checked)}
                    />
                    <span>Dry run (No GitHub comment)</span>
                  </label>
                  
                  <label className="checkbox-label">
                    <input
                      type="checkbox"
                      checked={prReviewPostToGithub}
                      onChange={(e) => setPrReviewPostToGithub(e.target.checked)}
                    />
                    <span>Post comment to GitHub</span>
                  </label>
                </div>

                <button
                  type="submit"
                  className="button-primary"
                  disabled={prReviewBusy || repoIsIndexing}
                >
                  {prReviewBusy ? (
                    <><Loader2 size={13} className="spin-icon" /> Triggering Review…</>
                  ) : (
                    "Trigger PR Review"
                  )}
                </button>
              </form>

              {/* Review History Card */}
              <div className="panel">
                <div className="panel-title">
                  <span>PR Review History</span>
                </div>
                <div className="pr-run-list">
                  {prReviews.length === 0 ? (
                    <p className="muted">No code reviews triggered yet.</p>
                  ) : (
                    prReviews.map((run) => {
                      const isSelected = selectedPRReview?.id === run.id;
                      return (
                        <button
                          key={run.id}
                          type="button"
                          className={`pr-run-row${isSelected ? " active" : ""}`}
                          onClick={() => setSelectedPRReview(run)}
                        >
                          <div className="pr-run-header">
                            <strong>PR #{run.input?.pr_number ?? "?"}</strong>
                            <span className={`pr-status-badge ${run.status}`}>
                              {run.status === "running" && (
                                <Loader2 size={10} className="spin-icon" />
                              )}
                              {run.status}
                            </span>
                          </div>
                          <div className="pr-run-meta">
                            <span>{new Date(run.started_at).toLocaleTimeString()}</span>
                            {run.status === "done" && (
                              <span className={`risk-badge-text ${run.output?.risk_summary}`}>
                                {run.output?.risk_summary} risk
                              </span>
                            )}
                          </div>
                        </button>
                      );
                    })
                  )}
                </div>
              </div>
            </div>

            {/* Inspector Panel */}
            <div className="pr-review-inspector">
              {selectedPRReview ? (
                <div className="panel select-pr-panel">
                  <div className="panel-title" style={{ borderBottom: "1px solid var(--hairline-soft)", paddingBottom: "12px" }}>
                    <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
                      <h2>PR #{selectedPRReview.input?.pr_number ?? "?"} Review Details</h2>
                      <span className="meta">Run ID: {selectedPRReview.id}</span>
                    </div>
                    {selectedPRReview.status === "done" && (
                      <span className={`confidence-badge ${selectedPRReview.output?.risk_summary}`}>
                        {selectedPRReview.output?.risk_summary} risk
                      </span>
                    )}
                  </div>

                  {selectedPRReview.status === "running" && (
                    <div className="inspect-state">
                      <Loader2 size={24} className="spin-icon" color="var(--primary)" />
                      <p>PR Review Agent is analyzing the diff and codebase hierarchy…</p>
                      <p className="muted" style={{ fontSize: 12 }}>This might take 10-25 seconds depending on local LLM speed.</p>
                    </div>
                  )}

                  {selectedPRReview.status === "failed" && (
                    <div className="inspect-state">
                      <AlertCircle size={24} color="var(--error)" />
                      <p style={{ color: "var(--error)" }}>PR Review Agent failed</p>
                      <pre className="error-box">{selectedPRReview.error || "Unknown error occurred during review execution."}</pre>
                    </div>
                  )}

                  {selectedPRReview.status === "done" && selectedPRReview.output && (
                    <div className="pr-report-content">
                      <div className="pr-summary-card">
                        <h3>Overall Summary</h3>
                        <p>{selectedPRReview.output.summary}</p>
                      </div>

                      {/* Review Comments */}
                      <h3>Comments ({selectedPRReview.output.comments.length})</h3>
                      {selectedPRReview.output.comments.length === 0 ? (
                        <div className="pr-clean-state">
                          <Check size={16} color="var(--success)" />
                          <span>Code Review Agent found no architectural or logic violations. Clean code!</span>
                        </div>
                      ) : (
                        <div className="pr-comment-list">
                          {selectedPRReview.output.comments.map((comment: any, idx: number) => (
                            <div key={idx} className="pr-comment-card">
                              <div className="pr-comment-header">
                                <span className="pr-comment-file">{comment.file_path} {comment.line && `:L${comment.line}`}</span>
                                <div style={{ display: "flex", gap: 6 }}>
                                  <span className="pr-comment-category">{comment.category}</span>
                                  <span className={`pr-comment-risk-pill ${comment.risk}`}>{comment.risk}</span>
                                </div>
                              </div>
                              <p className="pr-comment-msg">{comment.message}</p>
                              {comment.suggestion && (
                                <div className="pr-comment-suggestion">
                                  <strong style={{ fontSize: 12, color: "var(--graphite)" }}>Suggestion:</strong>
                                  <pre><code>{comment.suggestion}</code></pre>
                                </div>
                              )}
                              {comment.evidence && comment.evidence.length > 0 && (
                                <div className="pr-comment-evidence">
                                  <strong style={{ fontSize: 11, color: "var(--slate)" }}>Evidence Citations:</strong>
                                  <div className="tag-row" style={{ marginTop: 4 }}>
                                    {comment.evidence.map((ev: string, evIdx: number) => (
                                      <span key={evIdx} className="tag" style={{ fontSize: 10 }}>{ev}</span>
                                    ))}
                                  </div>
                                </div>
                              )}
                            </div>
                          ))}
                        </div>
                      )}

                      {/* Missing Tests */}
                      {selectedPRReview.output.missing_tests && selectedPRReview.output.missing_tests.length > 0 && (
                        <div className="pr-missing-tests-card">
                          <h3>Suggested Missing Tests</h3>
                          <ul className="file-list">
                            {selectedPRReview.output.missing_tests.map((test: string, idx: number) => (
                              <li key={idx}>{test}</li>
                            ))}
                          </ul>
                        </div>
                      )}

                      {/* Run Info */}
                      <div className="pr-run-footer" style={{ borderTop: "1px solid var(--hairline-soft)", paddingTop: "12px", display: "flex", justifyContent: "space-between", fontSize: 12 }}>
                        <span className="muted">Model: {selectedPRReview.model || "Local Code Review Agent"}</span>
                        {selectedPRReview.output.posted_to_github && (
                          <span style={{ color: "var(--success)", fontWeight: 600 }}>✓ Posted review to GitHub</span>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              ) : (
                <div className="panel empty-state">
                  <GitPullRequest size={32} color="var(--text-muted)" />
                  <p>Select a PR Review run from the logs, or trigger a new one to view automated review details.</p>
                </div>
              )}
            </div>
          </div>
        );

      default:
        return null;
    }
  }

  // ── Render view mode ──────────────────────────────────────────────────────
  if (viewMode === "public_analyzer") {
    return (
      <div className="app-shell">
        <header className="topbar">
          <div className="topbar-brand">
            <div className="topbar-logo">
              <Brain size={18} />
            </div>
            <div>
              <div className="brand-name">engineering brain</div>
              <div className="brand-phase">Phase 3 · PR Review &amp; Public Growth Loop</div>
            </div>
          </div>
          <div className="topbar-right">
            <button
              type="button"
              className="button-ghost"
              onClick={() => {
                setViewMode("workspace");
                setPublicReport(null);
                setPublicReportStatusMsg("");
                window.history.replaceState({}, "", window.location.pathname);
              }}
            >
              Back to Dashboard
            </button>
          </div>
        </header>

        <main className="content public-analyzer-page">
          {/* Landing / Search Panel */}
          {!publicReport && !publicReportLoading && (
            <div className="public-landing-hero">
              <div className="hero-dark-overlay">
                <span className="eyebrow" style={{ color: "var(--stone)" }}>PUBLIC REPOSITORY ANALYZER</span>
                <h1>runwai code intelligence</h1>
                <p className="subtitle" style={{ color: "var(--ash)", maxWidth: 650, margin: "var(--spacing-md) 0 var(--spacing-xl) 0" }}>
                  Ingest any public GitHub repository to map its module hierarchy, detect entrypoints, extract key symbols, and synthesize an architectural report in seconds.
                </p>
                
                <form onSubmit={handlePublicAnalyze} className="public-url-form">
                  <input
                    type="text"
                    value={publicUrlInput}
                    onChange={(e) => setPublicUrlInput(e.target.value)}
                    placeholder="https://github.com/owner/repository"
                    required
                  />
                  <button type="submit" className="button-primary" style={{ background: "var(--on-primary)", color: "var(--primary)", border: "none" }}>
                    Analyze Repository
                  </button>
                </form>

                {publicReportStatusMsg && (
                  <p className="muted" style={{ marginTop: 12, color: "var(--stone)" }}>{publicReportStatusMsg}</p>
                )}
              </div>
            </div>
          )}

          {/* Loading state */}
          {publicReportLoading && (
            <div className="panel public-analyzer-loader">
              <div className="progress-wrap" style={{ maxWidth: 500, width: "100%", margin: "0 auto", padding: "48px 0", display: "grid", gap: 16, textAlign: "center" }}>
                <Loader2 size={32} className="spin-icon" style={{ margin: "0 auto" }} />
                <h3>{publicReportStatusMsg || "Indexing repository files…"}</h3>
                <div className="progress-track">
                  <div className="progress-fill indeterminate" />
                </div>
              </div>
            </div>
          )}

          {/* Ready Report Display */}
          {publicReport && (
            <div className="public-report-display">
              <div className="report-header-section">
                <div>
                  <span className="eyebrow">Architecture Report</span>
                  <h2>{publicReport.repo_name}</h2>
                  <a href={publicReport.github_url} target="_blank" rel="noreferrer" className="button-text-link" style={{ fontSize: 13, display: "inline-flex", alignItems: "center", gap: 4, marginTop: 4 }}>
                    <Globe size={11} /> View on GitHub <ExternalLink size={10} />
                  </a>
                </div>
                <div className="report-actions">
                  <button type="button" className="button-primary" onClick={handleShareReport}>
                    {copiedShareLink ? "Link Copied ✓" : "Share Report"}
                  </button>
                  <button
                    type="button"
                    className="button-ghost"
                    onClick={() => {
                      setPublicReport(null);
                      window.history.replaceState({}, "", window.location.pathname);
                    }}
                  >
                    Clear Analysis
                  </button>
                </div>
              </div>

              {/* Narrative Summary */}
              <div className="panel pr-summary-card">
                <h3>Executive Architecture Narrative</h3>
                <div className="answer-text">
                  <ReactMarkdown>{publicReport.summary}</ReactMarkdown>
                </div>
              </div>

              {/* Editorial Grid (2 columns) */}
              <div className="editorial-report-grid">
                <div className="editorial-column">
                  {/* Metadata */}
                  <div className="panel">
                    <div className="panel-title">Repository Metrics</div>
                    <div className="arch-stats-row" style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
                      <div className="arch-stat">
                        <span className="arch-stat-value">{publicReport.file_count}</span>
                        <span className="arch-stat-label">Total Files</span>
                      </div>
                      <div className="arch-stat">
                        <span className="arch-stat-value">{publicReport.symbol_count}</span>
                        <span className="arch-stat-label">Symbols</span>
                      </div>
                    </div>

                    <h3 style={{ marginTop: 12 }}>Languages</h3>
                    <div className="tag-row">
                      {publicReport.languages.map((lang: string) => (
                        <span key={lang} className="tag">{lang}</span>
                      ))}
                    </div>

                    {publicReport.top_directories && publicReport.top_directories.length > 0 && (
                      <>
                        <h3 style={{ marginTop: 16 }}>Directory Structure</h3>
                        <div className="tag-row">
                          {publicReport.top_directories.map((dir: any) => (
                            <span key={dir.name} className="tag">
                              {dir.name} · {dir.chunk_count}
                            </span>
                          ))}
                        </div>
                      </>
                    )}
                  </div>

                  {/* Frameworks */}
                  {publicReport.frameworks && publicReport.frameworks.length > 0 && (
                    <div className="panel">
                      <div className="panel-title">Detected Frameworks</div>
                      <div className="signal-list">
                        {publicReport.frameworks.map((fw: any) => (
                          <div className="signal" key={fw.name}>
                            <span className="signal-name">{fw.name}</span>
                            <span className="signal-files" style={{ fontSize: 11 }}>{fw.evidence_files.join(", ")}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>

                <div className="editorial-column">
                  {/* Entrypoints */}
                  {publicReport.entrypoints && publicReport.entrypoints.length > 0 && (
                    <div className="panel">
                      <div className="panel-title">Entrypoints</div>
                      <ul className="file-list">
                        {publicReport.entrypoints.map((file: string) => (
                          <li key={file} style={{ fontFamily: "ui-monospace, SFMono-Regular, monospace", fontSize: 13 }}>{file}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {/* Important Files */}
                  {publicReport.important_files && publicReport.important_files.length > 0 && (
                    <div className="panel">
                      <div className="panel-title">Important Files</div>
                      <ul className="file-list">
                        {publicReport.important_files.map((file: string) => (
                          <li key={file} style={{ fontFamily: "ui-monospace, SFMono-Regular, monospace", fontSize: 13 }}>{file}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              </div>

              {/* Next Steps */}
              {publicReport.next_steps && publicReport.next_steps.length > 0 && (
                <div className="panel next-steps-full">
                  <h3>Recommended Next Steps</h3>
                  <div className="next-steps">
                    {publicReport.next_steps.map((step: string, idx: number) => (
                      <div key={idx} className="next-step-item">→ {step}</div>
                    ))}
                  </div>
                </div>
              )}

              {/* Lead Capture Waitlist */}
              <div className="panel public-waitlist-box">
                <div className="waitlist-header">
                  <Brain size={24} />
                  <h3>Get automated PR reviews with full context</h3>
                  <p className="muted" style={{ maxWidth: 500 }}>
                    Enable our PR Review Agent to automatically review diffs, enforce architectural constraints, and alert your team on violations directly on GitHub.
                  </p>
                </div>
                
                {waitlistSuccess ? (
                  <div className="waitlist-success-banner">
                    <CheckCircle size={18} color="var(--success)" />
                    <strong>Thank you! You've successfully joined the Engineering Brain waitlist.</strong>
                  </div>
                ) : (
                  <form onSubmit={handleJoinWaitlist} className="waitlist-form">
                    <input
                      type="email"
                      value={waitlistEmail}
                      onChange={(e) => setWaitlistEmail(e.target.value)}
                      placeholder="Type your engineering email"
                      required
                    />
                    <button type="submit" className="button-primary">
                      Join waitlist
                    </button>
                  </form>
                )}
              </div>
            </div>
          )}
        </main>
      </div>
    );
  }

  return (
    <div className="app-shell">
      {/* ── Top bar ──────────────────────────────────────────────────────── */}
      <header className="topbar">
        <div className="topbar-brand">
          <div className="topbar-logo">
            <Brain size={18} />
          </div>
          <div>
            <div className="brand-name">engineering brain</div>
            <div className="brand-phase">Phase 3 · PR Review &amp; Public Growth Loop</div>
          </div>
        </div>

        <div className="topbar-right">
          <button
            type="button"
            className="button-ghost"
            style={{ height: 32, padding: "0 12px", fontSize: 12 }}
            onClick={() => setViewMode("public_analyzer")}
          >
            Public Analyzer
          </button>
          
          {llmStatus !== null && (
            <div className={`llm-badge${llmStatus.ollama_available ? "" : " offline"}`}>
              <Sparkles size={11} />
              {llmStatus.ollama_available
                ? llmStatus.chat_model
                : "Ollama offline · keyword mode"}
            </div>
          )}
          <div className={`status-pill${busy ? " busy" : ""}`}>
            {busy ? <div className="spinner" /> : <div className="status-dot" />}
            {busy ? "Working…" : statusMsg}
          </div>
        </div>
      </header>

      {/* ── Workspace ────────────────────────────────────────────────────── */}
      <div className="workspace">
        {/* ── Sidebar ──────────────────────────────────────────────────── */}
        <aside className="sidebar">
          {/* Index form */}
          <form className="panel" onSubmit={handleIndex}>
            <div className="panel-title">
              <GitBranch size={15} />
              <span>Index Repository</span>
            </div>
            <label>
              Source
              <select
                value={source}
                onChange={(e) => setSource(e.target.value as "github" | "local")}
              >
                <option value="github">Public GitHub URL</option>
                <option value="local">Local path</option>
              </select>
            </label>
            <label>
              {source === "github" ? "GitHub URL" : "Local path"}
              <input
                value={repoInput}
                onChange={(e) => setRepoInput(e.target.value)}
                placeholder={
                  source === "github"
                    ? "https://github.com/owner/repo"
                    : "/path/to/repo"
                }
              />
            </label>
            <button type="submit" className="button-primary" disabled={busy}>
              {isBusy ? <><Loader2 size={13} className="spin-icon" /> Indexing…</> : "Index"}
            </button>
          </form>

          {/* Repo list */}
          <div className="panel">
            <div className="panel-title">
              <ServerCog size={15} />
              <span>Repositories</span>
            </div>
            <div className="repo-list">
              {repositories.length === 0 ? (
                <p className="muted">No repositories indexed yet.</p>
              ) : (
                repositories.map((repo) => (
                  <div key={repo.id} className={`repo-row${repo.id === selectedRepo?.id ? " active" : ""}`}>
                    <button
                      className="repo"
                      onClick={() => setSelectedRepoId(repo.id)}
                    >
                      <strong>{repo.name}</strong>
                      <span className="repo-meta">
                        {repo.file_count} files · {repo.chunk_count} chunks
                        {repo.symbol_count > 0 && ` · ${repo.symbol_count} symbols`}
                      </span>
                      <span className={`repo-status-badge ${repo.status}`}>
                        {isActive(repo.status) && (
                          <div className="spinner" style={{ width: 8, height: 8, borderWidth: 1.5 }} />
                        )}
                        {statusLabel(repo.status)}
                      </span>
                    </button>
                    <button
                      className="icon-btn repo-delete-btn"
                      title="Delete repository"
                      disabled={deletingId === repo.id || isActive(repo.status)}
                      onClick={(e) => { e.stopPropagation(); handleDelete(repo.id); }}
                    >
                      {deletingId === repo.id
                        ? <div className="spinner" style={{ width: 11, height: 11, borderWidth: 1.5 }} />
                        : <Trash2 size={12} />
                      }
                    </button>
                  </div>
                ))
              )}
            </div>
          </div>
        </aside>

        {/* ── Content ──────────────────────────────────────────────────── */}
        <section className="content">
          {/* Repo header */}
          {selectedRepo ? (
            <div className="repo-header">
              <div>
                <p className="eyebrow">Active Repository</p>
                <h2>{selectedRepo.name}</h2>
              </div>
              <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-end", gap: 8 }}>
                <div className="tag-row">
                  {selectedRepo.languages.slice(0, 8).map((lang) => (
                    <span className="tag" key={lang}>{lang}</span>
                  ))}
                </div>
                <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
                  {selectedRepo.embedded_chunk_count > 0 && (
                    <div className="llm-badge">
                      <Zap size={10} />
                      {selectedRepo.embedded_chunk_count} vectors
                    </div>
                  )}
                  {selectedRepo.symbol_count > 0 && (
                    <div className="llm-badge" style={{ background: "var(--surface-2)" }}>
                      <Code2 size={10} />
                      {selectedRepo.symbol_count} symbols
                    </div>
                  )}
                  {selectedRepo.edge_count > 0 && (
                    <div className="llm-badge" style={{ background: "var(--surface-2)" }}>
                      <Network size={10} />
                      {selectedRepo.edge_count} edges
                    </div>
                  )}
                  {(selectedRepo.status === "ready" || selectedRepo.status === "failed") && (
                    <button
                      type="button"
                      className="button-ghost"
                      title="Re-index this repository"
                      disabled={busy}
                      onClick={handleReindex}
                    >
                      <RotateCcw size={12} />
                      <span>Re-index</span>
                    </button>
                  )}
                </div>
              </div>
            </div>
          ) : (
            <div className="empty-state">
              <Brain size={32} color="var(--text-muted)" />
              <p>Index a repository to start asking engineering questions with cited, graph-expanded answers.</p>
            </div>
          )}

          {/* Indexing progress */}
          {selectedRepo && isActive(selectedRepo.status) && (
            <div className="panel">
              <IndexingProgress
                status={selectedRepo.status}
                chunkCount={selectedRepo.chunk_count}
                embeddedCount={selectedRepo.embedded_chunk_count}
              />
            </div>
          )}

          {/* Tab bar */}
          {selectedRepo && (
            <div className="tab-bar">
              <button
                id="tab-chat"
                className={`tab-btn${activeTab === "chat" ? " active" : ""}`}
                onClick={() => setActiveTab("chat")}
              >
                <MessageSquareText size={13} /> Chat
              </button>
              <button
                id="tab-search"
                className={`tab-btn${activeTab === "search" ? " active" : ""}`}
                onClick={() => setActiveTab("search")}
              >
                <Search size={13} /> Search
              </button>
              <button
                id="tab-symbols"
                className={`tab-btn${activeTab === "symbols" ? " active" : ""}`}
                onClick={() => setActiveTab("symbols")}
              >
                <Code2 size={13} /> Symbols
                {(selectedRepo.symbol_count ?? 0) > 0 && (
                  <span className="tab-count">{selectedRepo.symbol_count}</span>
                )}
              </button>
              <button
                id="tab-graph"
                className={`tab-btn${activeTab === "graph" ? " active" : ""}`}
                onClick={() => setActiveTab("graph")}
              >
                <Network size={13} /> Graph
                {(selectedRepo.edge_count ?? 0) > 0 && (
                  <span className="tab-count">{selectedRepo.edge_count}</span>
                )}
              </button>
              <button
                id="tab-architecture"
                className={`tab-btn${activeTab === "architecture" ? " active" : ""}`}
                onClick={() => setActiveTab("architecture")}
              >
                <Brain size={13} /> Architecture
              </button>
              <button
                id="tab-pr-reviews"
                className={`tab-btn${activeTab === "pr_reviews" ? " active" : ""}`}
                onClick={() => setActiveTab("pr_reviews")}
              >
                <GitPullRequest size={13} /> PR Reviews
                {prReviews.length > 0 && (
                  <span className="tab-count">{prReviews.length}</span>
                )}
              </button>
            </div>
          )}

          {/* Tab content */}
          {selectedRepo && renderTab()}
        </section>
      </div>
    </div>
  );
}
