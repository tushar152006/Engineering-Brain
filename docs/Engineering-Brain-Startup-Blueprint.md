# Engineering Brain Startup Blueprint

Version: 1.0  
Date: 2026-05-30  
Audience: student founding team, technical mentors, early users, incubators, and investors

## Executive Summary

Engineering Brain is an AI engineering intelligence platform that understands a company's repositories, pull requests, commit history, documentation, and architecture, then answers engineering questions like a senior engineer who has read the whole codebase.

The best MVP is intentionally narrow: GitHub plus documentation only. Do not start with Slack, Jira, email, Confluence, Linear, Notion, incident tools, or deployment logs. Those integrations can come later. The first product should deeply understand repositories, architecture, PRs, and docs, because this is where engineering teams feel the most pain and where a student team can build a credible demo in 3 to 4 months.

The wedge feature should be an AI PR Review Agent that comments on GitHub pull requests and cites codebase context, documentation, and past architectural decisions. This creates an immediate demo moment: "The system remembers why we built the architecture this way and catches violations before a senior engineer has to."

This blueprint assumes a near-zero budget and uses open-source software, free tiers, and self-hosted components wherever possible.

## Sources and Market Notes

Market and free-tier assumptions should be rechecked before fundraising or production launch because cloud pricing changes frequently.

- Grand View Research estimated the AI code assistants market at USD 8.5B in 2025 with a forecast of USD 42.9B by 2033.
- Market.us estimated the AI code assistant market at USD 5.5B in 2024 and USD 47.3B by 2034.
- GitHub Copilot reportedly crossed 20M all-time users in 2025.
- Render's free documentation states that free web services and datastores are for previews, hobby projects, and testing, not production.
- Neo4j lists AuraDB Free at USD 0 with no credit card required.
- Cloudflare R2's official pricing lists a free tier of 10 GB-month storage, 1M Class A operations, 10M Class B operations, and free egress for standard storage.
- Upstash's official pricing lists a free Redis tier with 256 MB data and 500K monthly commands.

Useful links:

- https://www.grandviewresearch.com/industry-analysis/ai-code-assistants-market-report
- https://market.us/report/ai-code-assistant-market/
- https://techcrunch.com/2025/07/30/github-copilot-crosses-20-million-all-time-users/
- https://render.com/free
- https://neo4j.com/pricing/
- https://developers.cloudflare.com/r2/pricing/
- https://upstash.com/pricing
- https://sourcegraph.com/docs/cody
- https://www.glean.com/product/ai-search

---

# Section 1: Market Analysis

## Problem Statement

Engineering knowledge is fragmented across code, pull requests, commit messages, docs, diagrams, issues, tribal memory, and senior engineers' heads. New engineers waste weeks trying to understand architecture. Senior engineers are interrupted repeatedly for context. AI coding tools can write snippets, but they often lack durable organizational memory and cannot explain why a codebase evolved the way it did.

The core pain:

- Onboarding takes too long.
- Code search is keyword-based and misses intent.
- Documentation becomes stale.
- Architecture decisions are buried in old PRs and comments.
- Pull request reviews depend heavily on a small number of senior engineers.
- AI coding tools hallucinate when they do not understand the actual repository.
- Teams cannot easily ask, "What breaks if we change this?"

## Target Users

Primary users:

- Engineering teams with 5 to 100 developers.
- Startups with fast-changing codebases.
- Open-source maintainers.
- Student engineering teams and hackathon teams.
- Agencies maintaining multiple client repositories.

Buyer personas:

- CTO or technical founder who wants faster onboarding and better review quality.
- Engineering manager who wants less senior-engineer interruption.
- Staff engineer who wants architectural consistency.
- Developer productivity lead who wants AI tooling with codebase context.

Early adopter profile:

- Uses GitHub.
- Has at least 3 repositories or one medium-size monorepo.
- Has docs in Markdown, README files, ADRs, or docs folders.
- Reviews pull requests regularly.
- Already uses ChatGPT, Claude, Cursor, Copilot, or Sourcegraph but still struggles with organization-specific context.

## Competitor Analysis

### GitHub Copilot

Strengths:

- Deep GitHub and IDE distribution.
- Strong code completion and chat.
- Increasingly agentic.
- Trusted by many enterprise teams.

Weaknesses:

- Often optimized for individual coding flow more than organizational memory.
- Context can be shallow or session-based.
- Explaining architecture across repos is still inconsistent.
- PR review may not be deeply grounded in team-specific historical decisions.

### Sourcegraph Cody and Sourcegraph Code Search

Strengths:

- Excellent code search heritage.
- Strong repository indexing.
- Enterprise code intelligence positioning.
- Multi-repository context.

Weaknesses:

- Enterprise-oriented and potentially heavy for small teams.
- Less accessible to a student-built, open-source, free-first audience.
- Complex setup for small teams that only need GitHub plus docs intelligence.

### Glean

Strengths:

- Strong enterprise knowledge search.
- Connectors across many workplace systems.
- Knowledge graph positioning.

Weaknesses:

- Broad enterprise search, not engineering-first.
- May be expensive or too broad for startups.
- Less focused on PR review, code graph reasoning, and code architecture.

### Cursor, Windsurf, Claude Code, OpenAI Codex-style coding agents

Strengths:

- Strong coding velocity.
- Excellent developer experience.
- Agentic editing and task execution.

Weaknesses:

- Typically oriented around the current workspace or task.
- Less likely to maintain a durable company-wide engineering memory.
- May not build a persistent graph of architecture, PRs, decisions, and ownership.

### Swimm, Mintlify, ReadMe, documentation assistants

Strengths:

- Good documentation workflows.
- Help keep docs closer to code.

Weaknesses:

- Not a full engineering brain.
- Usually do not combine repository graph, PR history, architecture reasoning, and review automation.

## Why Current Solutions Fail

Current solutions often fail because they are either:

- Too local: They understand the open editor, not the organization.
- Too generic: They answer with plausible AI text but lack grounded code context.
- Too expensive: Enterprise search and AI tools are unaffordable for students and small startups.
- Too broad: They integrate every SaaS tool before deeply solving code intelligence.
- Too passive: They wait for questions instead of appearing in PRs at the moment of engineering decision.
- Too temporary: They do not maintain a persistent, queryable memory that improves over time.

## Unique Value Proposition

Engineering Brain is the open, free-first AI memory layer for engineering teams.

Positioning:

"Connect GitHub and docs. Get a senior-engineer-level assistant that answers architecture questions, explains code relationships, and reviews pull requests using your team's actual engineering history."

Core differentiators:

- GitHub-native from day one.
- Documentation-aware and architecture-aware.
- Knowledge graph plus RAG, not only vector search.
- PR comments cite files, docs, commits, and past decisions.
- Free or near-zero-cost deployment for small teams.
- Open-source-first community strategy.
- Designed for students and startups before enterprise.

## Market Size Estimation

Top-down:

- The AI code assistant market is already measured in multiple billions of dollars and is forecast to grow rapidly through the 2030s.
- Developer tools is a large existing software category, and AI is creating a new layer around code search, review, documentation, and autonomous engineering.

Bottom-up:

- GitHub has well over 100M developers globally.
- If only 1 percent of active professional GitHub teams pay USD 20 to USD 100 per developer per month for engineering intelligence, the opportunity is large.
- A narrow beachhead of startups with 5 to 50 engineers is enough for a meaningful seed-stage business.

Practical student-team goal:

- First 10 users: open-source maintainers, student teams, local startups.
- First 100 users: GitHub public repo analyzer plus PR agent waitlist.
- First 10 paying teams: small startups that want PR review and onboarding acceleration.

---

# Section 2: Product Requirements

## Core MVP Features

The MVP should include:

1. GitHub repository connection.
2. Repository ingestion for code, README files, Markdown docs, package files, config files, and architecture docs.
3. Incremental updates through GitHub webhooks.
4. Code-aware chunking and embedding.
5. Hybrid search: keyword plus vector plus graph.
6. Chat interface for engineering questions.
7. Architecture summary generation.
8. File, function, class, and dependency relationship mapping.
9. PR Review Agent that comments on GitHub pull requests.
10. Source citations for every important answer.
11. Admin dashboard for indexing status.
12. Public repo analyzer with no signup for growth.

## Advanced Features

Add after the MVP is validated:

- ADR extraction from PRs and docs.
- Ownership inference by commit history.
- "What breaks if..." impact analysis.
- Bug investigation workflows.
- Test recommendation agent.
- Release risk summaries.
- Monorepo service map.
- API contract map.
- IDE extension.
- Slack or Discord bot.
- Jira, Linear, Notion, Confluence integrations.
- Self-hosted enterprise deployment.
- Fine-tuned reranker for code and docs.
- Autonomous issue-to-PR agent.

## Future Vision

Long-term, Engineering Brain becomes:

- The memory layer for engineering organizations.
- A codebase-native AI architect.
- A PR reviewer with institutional context.
- An onboarding companion for every new engineer.
- A platform for autonomous AI engineers that can safely modify code because they understand the system.

## User Stories

As a new engineer:

- I want to ask what a service does so that I can onboard faster.
- I want to understand why a pattern exists so that I do not rewrite old mistakes.
- I want file and function citations so that I can verify the answer.

As a senior engineer:

- I want the assistant to answer repetitive architecture questions.
- I want PR comments when a change violates existing architecture.
- I want architecture summaries generated from the current repo state.

As an engineering manager:

- I want to reduce onboarding time.
- I want visibility into documentation gaps.
- I want safer PR review without adding more process.

As an open-source maintainer:

- I want contributors to understand the codebase before opening PRs.
- I want automated guidance for PRs that touch risky areas.

## User Flows

### Flow 1: Connect a Repository

1. User signs in with GitHub.
2. User installs GitHub App on selected repositories.
3. Backend receives installation event.
4. Ingestion worker clones or fetches repository contents.
5. Parser extracts files, symbols, dependencies, docs, and metadata.
6. Embedding worker creates chunks and embeddings.
7. Graph worker creates file, symbol, dependency, and PR relationships.
8. Dashboard shows "Index ready."

### Flow 2: Ask an Engineering Question

1. User asks: "How does authentication work?"
2. Query planner classifies the question as architecture plus code explanation.
3. Retrieval fetches docs, files, symbols, and graph neighbors.
4. Reranker orders evidence.
5. LLM generates answer with citations.
6. UI shows answer, relevant files, and confidence notes.

### Flow 3: PR Review Agent

1. Developer opens a PR.
2. GitHub webhook triggers PR ingestion.
3. Diff analyzer identifies changed files and functions.
4. Agent retrieves related architecture docs, historical PRs, owners, and similar changes.
5. Agent checks for risks, missing tests, inconsistent patterns, and undocumented architecture changes.
6. Agent posts a GitHub review comment with citations.
7. User can mark feedback useful or false positive.

### Flow 4: Public Repo Analyzer

1. Visitor enters a public GitHub repo URL.
2. System performs a limited, rate-controlled ingest.
3. Visitor gets architecture map, top modules, setup summary, and suggested first issues.
4. Visitor can share the report.
5. Report page links to the full product waitlist.

---

# Section 3: System Architecture

## High-Level Architecture

```text
                              +----------------------+
                              |      GitHub App       |
                              | OAuth + Webhooks + PR |
                              +----------+-----------+
                                         |
                                         v
+------------------+        +-----------------------+        +--------------------+
|   Web Frontend   | <----> |      API Backend      | <----> |  Auth + Tenancy    |
| Next.js/React    |        | FastAPI or NestJS     |        | Supabase/GitHub    |
+--------+---------+        +-----------+-----------+        +--------------------+
         |                              |
         |                              v
         |                    +---------------------+
         |                    |     Job Queue       |
         |                    | Redis / Upstash     |
         |                    +----------+----------+
         |                               |
         v                               v
+------------------+        +-----------------------+        +--------------------+
| Chat + Dashboard |        | Ingestion Workers     | -----> | Object Storage     |
| Search + Reports |        | Repo/PR/Docs parsing  |        | Cloudflare R2      |
+------------------+        +-----------+-----------+        +--------------------+
                                         |
               +-------------------------+--------------------------+
               |                         |                          |
               v                         v                          v
      +----------------+        +----------------+          +----------------+
      | PostgreSQL     |        | Vector Store   |          | Knowledge Graph|
      | Supabase/Neon  |        | pgvector/Qdrant|          | Neo4j/Memgraph |
      +----------------+        +----------------+          +----------------+
               |                         |                          |
               +-------------------------+--------------------------+
                                         |
                                         v
                              +----------------------+
                              | Retrieval + Agents   |
                              | RAG + tools + memory |
                              +----------+-----------+
                                         |
                                         v
                              +----------------------+
                              | LLM Layer            |
                              | Ollama/Groq/Local    |
                              +----------------------+
```

## Frontend

Recommended: Next.js with TypeScript and Tailwind CSS.

Screens:

- Landing page with public repo analyzer.
- Login page.
- Repo connection page.
- Indexing dashboard.
- Chat with citations.
- Architecture map view.
- PR review configuration.
- Admin page for usage and logs.

## Backend

Recommended: FastAPI with Python.

Why:

- Python is ideal for parsing, ML, embeddings, LangGraph, LlamaIndex, and GitHub automation.
- FastAPI is fast enough and easy for students.
- OpenAPI docs come free.

Core modules:

- Auth and organization tenancy.
- GitHub App webhook handler.
- Repository ingestion API.
- Search API.
- Chat API.
- Agent orchestration API.
- PR review API.
- Admin API.

## Authentication

MVP:

- GitHub OAuth for user login.
- GitHub App installation for repository access.
- Supabase Auth can handle user sessions if the team wants speed.

Authorization model:

- User belongs to organization.
- Organization has GitHub installations.
- Installation grants repository access.
- Repository belongs to organization.
- User permissions are synced from GitHub where possible.

## Database

Use PostgreSQL as the source of truth for:

- Users.
- Organizations.
- Repositories.
- Ingestion jobs.
- Files and metadata.
- Chunks.
- PRs.
- Agent runs.
- Feedback.
- Billing later.

Free options:

- Supabase Free.
- Neon Free.
- Local Docker Postgres for development.

## Vector Database

Best MVP choice: pgvector inside PostgreSQL.

Reason:

- Fewer moving pieces.
- Easy to query chunks and metadata together.
- Free with Supabase, Neon, or local Postgres.

Upgrade path:

- Qdrant for larger-scale vector search.
- Weaviate or Milvus for enterprise scale.
- Managed vector DB only after revenue.

## Knowledge Graph

MVP options:

1. Start with Postgres adjacency tables if Neo4j free limits are painful.
2. Use Neo4j AuraDB Free for graph demos and Cypher queries.
3. Use Memgraph locally if self-hosting.

Graph is used for:

- File imports.
- Function calls.
- Class inheritance.
- PR touches file.
- Engineer owns file.
- Service exposes API.
- Doc describes module.

## Agent Framework

Recommended:

- LangGraph for structured agent workflows.
- Plain Python functions for tools.
- Avoid overly complex multi-agent autonomy in the MVP.

Key principle:

- Agents should be deterministic pipelines with LLM steps, not magical loops.

## LLM Layer

Free-first stack:

- Local Ollama for development and demos.
- Qwen2.5-Coder, DeepSeek-Coder, CodeLlama, or StarCoder2 depending on hardware.
- Groq free developer API for hosted fast inference when available.
- Hugging Face free inference for experiments, with strict rate-limit expectations.

Production principle:

- Build an LLM adapter so you can swap providers.
- Store prompts and model settings by task.
- Use smaller models for classification and bigger models for final synthesis.

## Retrieval System

Use hybrid retrieval:

```text
User question
    |
    v
Query planner
    |
    +--> Keyword search: exact symbols, filenames, error messages
    +--> Vector search: conceptual docs and code chunks
    +--> Graph traversal: dependencies, owners, neighboring functions
    |
    v
Merge candidates
    |
    v
Rerank
    |
    v
Build compact context pack
    |
    v
LLM answer with citations
```

## Tool Calling System

Tools should be typed, permissioned, and logged.

MVP tools:

- search_code(query, repo_id)
- search_docs(query, repo_id)
- get_file(path, repo_id)
- get_symbol(symbol_id)
- get_graph_neighbors(entity_id)
- get_pr_diff(pr_id)
- get_related_prs(file_path)
- post_pr_comment(pr_id, body)
- create_architecture_summary(repo_id)

## Deployment Architecture

Near-zero-cost deployment:

```text
Cloudflare Pages
    Frontend

Render Free or Railway Trial
    API service

Render Free Worker or local scheduled worker
    Ingestion and embedding jobs

Supabase or Neon
    Postgres + pgvector + auth

Upstash Redis Free
    Queue, rate limits, cache

Neo4j AuraDB Free
    Knowledge graph prototype

Cloudflare R2 Free
    Raw repo snapshots, generated reports, artifacts

GitHub App
    OAuth, webhooks, PR comments
```

Production upgrade:

- Move API and workers to Fly.io, Railway paid, Render paid, Kubernetes, or ECS.
- Move graph to paid Neo4j or self-hosted Memgraph.
- Move vector to Qdrant cluster.
- Add Sentry, OpenTelemetry, Grafana, and Prometheus.

---

# Section 4: Free Tech Stack Only

## Frontend

Chosen: Next.js, React, TypeScript, Tailwind CSS, shadcn/ui.

Why:

- Fast development.
- Great ecosystem.
- Easy deployment to Cloudflare Pages, Vercel, Netlify, or Render.
- Strong developer familiarity.

Pros:

- Modern UI quickly.
- Good routing and API integration.
- Large open-source ecosystem.

Cons:

- Can become complex if overused.
- Server components can confuse beginners.

Alternatives:

- Vite + React for simpler frontend.
- SvelteKit for speed and smaller code.
- Remix for full-stack routing.

Recommendation:

- Use Vite + React if the team is newer.
- Use Next.js if the team already knows it.

## Backend

Chosen: FastAPI.

Why:

- Python ecosystem is ideal for AI.
- Easy docs.
- Good async support.

Pros:

- Fast to build.
- Works well with Pydantic.
- Easy background task integrations.

Cons:

- Requires discipline for larger codebases.
- Async database patterns can confuse beginners.

Alternatives:

- NestJS if the team prefers TypeScript.
- Django if the team wants batteries included.
- Go if the team wants performance and simplicity later.

## Database

Chosen: PostgreSQL with Supabase Free or Neon Free.

Why:

- Relational data is core to the product.
- Postgres can also host pgvector.
- SQL is reliable and familiar.

Pros:

- Durable source of truth.
- Good indexing.
- Good ecosystem.

Cons:

- Free-tier storage is limited.
- Large codebases require careful pruning.

Alternatives:

- Local Postgres on a free VM.
- SQLite for local-only prototype.

## Vector DB

Chosen: pgvector first.

Why:

- Reduces infrastructure complexity.
- Good enough for MVP scale.

Pros:

- Metadata joins are simple.
- Easy migrations.
- Free if Postgres is already free.

Cons:

- Not as optimized as dedicated vector DBs.
- Scaling beyond millions of chunks requires work.

Alternatives:

- Qdrant, best open-source upgrade.
- Weaviate for graph-like metadata.
- Milvus for larger infrastructure teams.

## Knowledge Graph

Chosen: Neo4j AuraDB Free for hosted graph; Postgres graph tables as fallback.

Why:

- Neo4j is easy to demo.
- Cypher is expressive.
- Graph visualization is valuable for architecture demos.

Pros:

- Strong graph query language.
- Great for architecture relationships.
- Good visualization story.

Cons:

- Free-tier capacity limits.
- Another database to maintain.

Alternatives:

- Memgraph self-hosted.
- ArangoDB.
- Postgres recursive CTEs.

## LLM

Chosen:

- Local Ollama for development.
- Groq free API for hosted demos when available.
- Provider adapter abstraction from day one.

Pros:

- No required paid API.
- Keeps architecture future-proof.
- Local models improve privacy story.

Cons:

- Local models need hardware.
- Free hosted APIs have rate limits and can change.
- Smaller models may be weaker at complex reasoning.

Alternatives:

- Hugging Face inference.
- Together.ai free credits if available.
- OpenRouter free models if available.
- Paid OpenAI, Anthropic, or Gemini later.

## Embedding Model

Chosen: BAAI/bge-small-en-v1.5 or nomic-embed-text.

Why:

- Good open-source embeddings.
- Runs locally.
- Works for docs and code reasonably well.

Pros:

- Free.
- Easy with sentence-transformers or Ollama.
- Lightweight.

Cons:

- Code-specific retrieval may need better models.
- Cross-language retrieval may be weaker.

Alternatives:

- jina-embeddings-v2-base-code.
- bge-base-en.
- e5-small-v2.
- Voyage/OpenAI paid later.

## RAG Framework

Chosen: LlamaIndex or custom RAG pipeline.

Recommendation:

- Start custom for ingestion, chunking, retrieval, and citations.
- Use LlamaIndex only for utilities if it speeds development.

Pros:

- Custom pipeline teaches the team and avoids framework lock-in.
- LlamaIndex has useful readers and abstractions.

Cons:

- Custom RAG needs careful testing.
- Framework abstractions can hide important details.

## Agent Framework

Chosen: LangGraph.

Why:

- Good for deterministic multi-step workflows.
- Supports state machines.
- Better than unbounded agent loops.

Pros:

- Clear control flow.
- Testable nodes.
- Good fit for PR review pipelines.

Cons:

- Learning curve.
- Can be overkill for simple chat.

Alternative:

- Plain Python orchestration until Month 2.

## DevOps

Chosen:

- Docker Compose for local development.
- GitHub Actions for CI.
- Cloudflare Pages for frontend.
- Render Free or Railway Trial for API.
- Supabase/Neon for Postgres.

Pros:

- Free or almost free.
- Familiar to students.
- Easy demo deployment.

Cons:

- Free services sleep.
- Cold starts can hurt demos.
- Limits can break during traffic spikes.

## Monitoring

Chosen:

- OpenTelemetry instrumentation.
- Grafana Cloud Free if available.
- Sentry Free for frontend/backend errors.
- Structured logs in Postgres for agent runs.

Pros:

- Enough for MVP.
- Helps debug agent quality.

Cons:

- Free quotas.
- Requires discipline to add useful metadata.

---

# Section 5: AI Architecture

## Shared Agent Principles

All agents should:

- Use retrieved evidence before answering.
- Cite files, docs, PRs, or commits.
- Separate facts from inferences.
- Refuse to make unsupported claims.
- Log inputs, retrieval results, prompts, outputs, and user feedback.
- Run with scoped repository permissions.

## Repository Understanding Agent

Responsibilities:

- Ingest repositories.
- Detect languages, frameworks, services, and package managers.
- Parse files into code chunks and symbol records.
- Extract imports, exports, function definitions, class definitions, and routes.
- Summarize modules.

Inputs:

- Repository URL or GitHub installation.
- Branch name.
- File tree.
- Commit metadata.

Outputs:

- Repository summary.
- File summaries.
- Symbol index.
- Dependency edges.
- Framework detection report.
- Indexing status.

Tools:

- tree-sitter parsers.
- ripgrep.
- language-specific static analyzers.
- package file parsers.
- embedding service.
- graph writer.

Prompt skeleton:

```text
You are analyzing a software repository.
Given file paths, code snippets, docs, dependency files, and detected framework metadata,
produce a concise engineering summary.
Do not invent services or dependencies.
Return:
1. Primary purpose
2. Main modules
3. External dependencies
4. Entry points
5. Important risks or unknowns
6. Files that support each claim
```

Memory:

- Persistent file summaries.
- Repository-level summary.
- Language and framework metadata.
- Previous ingestion snapshots.

## Architecture Agent

Responsibilities:

- Generate architecture summaries.
- Build service maps.
- Explain module boundaries.
- Identify data flow and API flow.
- Compare implementation against docs.

Inputs:

- Repository graph.
- Documentation chunks.
- Package manifests.
- API route files.
- Docker Compose, Kubernetes, Terraform, or deployment configs.

Outputs:

- Architecture overview.
- Service dependency map.
- API map.
- Data flow summary.
- Architecture risks.

Tools:

- graph traversal.
- code search.
- doc search.
- file fetch.
- diagram generator.

Prompt skeleton:

```text
You are a staff software architect.
Use only the supplied evidence to explain the architecture.
For every major claim, cite a file, doc, or graph relationship.
If the evidence is incomplete, say what is missing.
Return:
1. System overview
2. Main components
3. Request/data flow
4. Important dependencies
5. Architecture decisions inferred from code
6. Risks and documentation gaps
```

Memory:

- Architecture summaries by version.
- ADRs.
- Service ownership.
- Known architecture constraints.

## Code Review Agent

Responsibilities:

- Review PR diffs.
- Detect architecture violations.
- Detect risky changes.
- Suggest missing tests.
- Cite historical decisions.
- Post comments to GitHub.

Inputs:

- PR diff.
- Changed files.
- Related docs.
- Related PRs.
- Ownership metadata.
- Test files.

Outputs:

- GitHub review comments.
- Risk score.
- Suggested test areas.
- Summary for maintainers.

Tools:

- get_pr_diff.
- search_related_code.
- search_related_docs.
- get_past_prs_touching_files.
- get_file_owners.
- post_pr_comment.

Prompt skeleton:

```text
You are a senior engineer reviewing a pull request.
Focus on correctness, architecture consistency, missing tests, security, and maintainability.
Use the supplied repository context and PR diff.
Only leave comments that are actionable and grounded in evidence.
Avoid style nitpicks.
Each comment must include:
- Risk
- Evidence
- Suggested fix
- Citation to code/docs/history
```

Memory:

- Past review comments.
- User feedback on comment quality.
- False positive records.
- Repository review rules.

## Documentation Agent

Responsibilities:

- Summarize documentation.
- Detect stale docs.
- Generate README or architecture docs.
- Suggest ADRs from PRs.

Inputs:

- Markdown docs.
- README files.
- Code summaries.
- Architecture graph.
- Recent PRs.

Outputs:

- Doc summaries.
- Missing docs report.
- Draft docs.
- Staleness warnings.

Tools:

- doc search.
- code search.
- graph traversal.
- markdown writer.

Prompt skeleton:

```text
You are a technical documentation engineer.
Use code and docs evidence to identify documentation gaps.
Do not rewrite docs unless asked.
Return:
1. Existing documentation summary
2. Missing documentation
3. Potentially stale documentation
4. Suggested new doc pages
5. Evidence for each finding
```

Memory:

- Doc versions.
- Generated summaries.
- Known stale docs.

## Bug Investigation Agent

Responsibilities:

- Help investigate bugs.
- Find likely files and functions.
- Trace related code paths.
- Suggest reproduction steps.
- Suggest tests to add.

Inputs:

- Bug report.
- Error message.
- Stack trace.
- Logs if provided later.
- Repository graph.
- Related issues and PRs.

Outputs:

- Ranked suspected causes.
- Relevant files.
- Debugging plan.
- Test recommendations.

Tools:

- exact search.
- symbol search.
- graph traversal.
- similar issue search.
- file fetch.

Prompt skeleton:

```text
You are debugging a production issue.
Given the bug report, stack trace, and retrieved code context,
rank possible causes.
For each cause, include:
- Why it is plausible
- Evidence
- What to inspect next
- A minimal test or reproduction idea
Do not claim certainty unless evidence is direct.
```

Memory:

- Past bugs.
- Fix PRs.
- Error message embeddings.
- Known flaky areas.

---

# Section 6: Knowledge Graph Design

## Entity Schema

Core entities:

- Organization
- User
- Engineer
- Repository
- Branch
- Commit
- PullRequest
- Issue
- File
- Directory
- Symbol
- Class
- Function
- Method
- Interface
- Module
- Package
- Service
- APIEndpoint
- DatabaseTable
- Config
- DocumentationPage
- ArchitectureDecision
- Chunk
- Test

## Relationship Schema

Important relationships:

- Organization OWNS Repository
- User MEMBER_OF Organization
- Engineer AUTHORED Commit
- Engineer OPENED PullRequest
- PullRequest TOUCHES File
- PullRequest INTRODUCES Symbol
- PullRequest REFERENCES Issue
- Commit MODIFIES File
- File DEFINES Symbol
- File IMPORTS File
- Function CALLS Function
- Class EXTENDS Class
- Method BELONGS_TO Class
- Service EXPOSES APIEndpoint
- APIEndpoint HANDLED_BY Function
- DocumentationPage DESCRIBES Service
- DocumentationPage REFERENCES File
- ArchitectureDecision CONSTRAINS Service
- Test COVERS Function
- File HAS_CHUNK Chunk
- Chunk MENTIONS Symbol

## Storage Strategy

MVP:

- Store graph relationships in Postgres tables first.
- Mirror important relationships into Neo4j for graph queries and visualization.
- Keep Postgres as the source of truth.

Reason:

- Postgres is easier to back up and migrate.
- Neo4j free tier may be limited.
- Graph can be rebuilt from Postgres if needed.

Graph rebuild flow:

```text
Postgres source tables
    |
    v
Graph projection job
    |
    v
Neo4j nodes and edges
    |
    v
Architecture queries and visualization
```

---

# Section 7: RAG System

## Chunking Strategy

Use different chunking for docs and code.

Documentation chunks:

- Split by Markdown headings.
- Target 300 to 800 tokens.
- Preserve heading path.
- Store neighboring section links.
- Keep source URL, file path, and line range.

Code chunks:

- Prefer AST-aware chunks using tree-sitter.
- Chunk by function, class, method, route handler, config block, or test case.
- For large functions, split into logical blocks.
- Always include file path, symbol name, language, imports, and parent class/module.

PR chunks:

- Chunk PR description.
- Chunk diff hunks.
- Store changed files.
- Store review comments and decision comments if accessible.

## Embedding Strategy

Use at least two embedding namespaces:

- docs: natural language docs, READMEs, ADRs.
- code: code chunks, symbols, API routes.

Recommended model:

- bge-small-en-v1.5 for first MVP.
- nomic-embed-text if using Ollama.
- Upgrade to a code-aware embedding model later.

Embedding metadata:

- org_id
- repo_id
- branch
- file_path
- language
- chunk_type
- symbol_id
- commit_sha
- updated_at
- visibility

## Indexing Strategy

Initial indexing:

1. Clone repository shallowly.
2. Respect ignore rules.
3. Skip binaries, lockfiles unless needed, generated files, build artifacts, and large files.
4. Parse file tree.
5. Detect frameworks.
6. Extract symbols and dependencies.
7. Generate summaries.
8. Embed chunks.
9. Write graph edges.

Incremental indexing:

1. GitHub webhook receives push or PR event.
2. Fetch changed files.
3. Delete stale chunks for changed files.
4. Re-parse only changed files.
5. Update changed graph edges.
6. Recompute affected summaries.
7. Store new commit snapshot.

## Hybrid Retrieval

Search stack:

- Exact keyword search for symbols, filenames, API paths, errors.
- Vector search for conceptual questions.
- Graph expansion for related functions, imports, tests, owners, and docs.
- Recency boost for recently changed files.
- Authority boost for README, docs, ADRs, and high-centrality files.

Example:

```text
Question: "Where is payment authorization enforced?"

Keyword candidates:
    authorize, payment, permission, route names

Vector candidates:
    docs about payment flow

Graph candidates:
    route handler -> service -> auth middleware -> tests

Final context:
    payment route, auth middleware, payment service, ADR, tests
```

## Re-ranking

MVP:

- Score candidates using weighted heuristic:
  - exact match score
  - vector similarity
  - graph distance
  - file authority
  - recency
  - chunk type

Upgrade:

- Use open-source cross-encoder reranker such as bge-reranker-base.

## Context Management

Context pack format:

- User question.
- Interpreted intent.
- Top evidence items.
- Graph relationships.
- Relevant snippets.
- Known constraints.
- Explicit unknowns.

Rules:

- Keep final context under model limit.
- Prefer fewer, stronger citations.
- Include line ranges where possible.
- Do not include unrelated chunks just because they are semantically similar.
- Summarize long files before sending to LLM.

---

# Section 8: Database Schema

## PostgreSQL Schema

```sql
create table organizations (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  slug text unique not null,
  created_at timestamptz default now()
);

create table users (
  id uuid primary key default gen_random_uuid(),
  github_user_id bigint unique,
  email text,
  name text,
  avatar_url text,
  created_at timestamptz default now()
);

create table organization_members (
  organization_id uuid references organizations(id) on delete cascade,
  user_id uuid references users(id) on delete cascade,
  role text not null check (role in ('owner','admin','member','viewer')),
  created_at timestamptz default now(),
  primary key (organization_id, user_id)
);

create table github_installations (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid references organizations(id) on delete cascade,
  installation_id bigint unique not null,
  account_login text not null,
  created_at timestamptz default now()
);

create table repositories (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid references organizations(id) on delete cascade,
  github_repo_id bigint unique,
  full_name text not null,
  default_branch text not null default 'main',
  visibility text not null,
  last_indexed_commit text,
  indexing_status text not null default 'pending',
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

create table files (
  id uuid primary key default gen_random_uuid(),
  repository_id uuid references repositories(id) on delete cascade,
  path text not null,
  language text,
  size_bytes integer,
  sha text,
  is_generated boolean default false,
  summary text,
  updated_at timestamptz default now(),
  unique (repository_id, path)
);

create table symbols (
  id uuid primary key default gen_random_uuid(),
  repository_id uuid references repositories(id) on delete cascade,
  file_id uuid references files(id) on delete cascade,
  name text not null,
  qualified_name text,
  kind text not null,
  start_line integer,
  end_line integer,
  signature text,
  summary text,
  created_at timestamptz default now()
);

create table chunks (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid references organizations(id) on delete cascade,
  repository_id uuid references repositories(id) on delete cascade,
  file_id uuid references files(id) on delete cascade,
  symbol_id uuid references symbols(id) on delete set null,
  chunk_type text not null,
  content text not null,
  content_hash text not null,
  start_line integer,
  end_line integer,
  metadata jsonb not null default '{}',
  created_at timestamptz default now()
);

create extension if not exists vector;

create table chunk_embeddings (
  chunk_id uuid primary key references chunks(id) on delete cascade,
  embedding vector(384),
  model text not null,
  created_at timestamptz default now()
);

create table pull_requests (
  id uuid primary key default gen_random_uuid(),
  repository_id uuid references repositories(id) on delete cascade,
  github_pr_number integer not null,
  title text,
  body text,
  author_login text,
  base_branch text,
  head_branch text,
  state text,
  merged boolean default false,
  created_at timestamptz,
  updated_at timestamptz,
  unique (repository_id, github_pr_number)
);

create table commits (
  id uuid primary key default gen_random_uuid(),
  repository_id uuid references repositories(id) on delete cascade,
  sha text not null,
  author_login text,
  message text,
  committed_at timestamptz,
  unique (repository_id, sha)
);

create table graph_edges (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid references organizations(id) on delete cascade,
  repository_id uuid references repositories(id) on delete cascade,
  source_type text not null,
  source_id uuid not null,
  relationship text not null,
  target_type text not null,
  target_id uuid not null,
  weight numeric default 1,
  metadata jsonb not null default '{}',
  created_at timestamptz default now()
);

create table agent_runs (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid references organizations(id) on delete cascade,
  repository_id uuid references repositories(id) on delete cascade,
  agent_type text not null,
  input jsonb not null,
  output jsonb,
  status text not null default 'running',
  model text,
  started_at timestamptz default now(),
  completed_at timestamptz
);

create table feedback (
  id uuid primary key default gen_random_uuid(),
  agent_run_id uuid references agent_runs(id) on delete cascade,
  user_id uuid references users(id) on delete set null,
  rating integer check (rating between 1 and 5),
  label text,
  comment text,
  created_at timestamptz default now()
);
```

## Neo4j Schema

Node labels:

```cypher
(:Organization {id, name, slug})
(:Repository {id, full_name, default_branch})
(:File {id, path, language})
(:Directory {path})
(:Symbol {id, name, qualified_name, kind})
(:Function {id, name, qualified_name})
(:Class {id, name, qualified_name})
(:PullRequest {id, number, title, state})
(:Commit {sha, message})
(:Engineer {login, name})
(:Issue {id, number, title})
(:Service {id, name})
(:APIEndpoint {method, path})
(:DocumentationPage {id, path, title})
(:ArchitectureDecision {id, title, status})
```

Relationships:

```cypher
(:Organization)-[:OWNS]->(:Repository)
(:Repository)-[:CONTAINS]->(:File)
(:File)-[:DEFINES]->(:Symbol)
(:File)-[:IMPORTS]->(:File)
(:Function)-[:CALLS]->(:Function)
(:Class)-[:EXTENDS]->(:Class)
(:PullRequest)-[:TOUCHES]->(:File)
(:PullRequest)-[:AUTHORED_BY]->(:Engineer)
(:Commit)-[:MODIFIES]->(:File)
(:DocumentationPage)-[:DESCRIBES]->(:Service)
(:DocumentationPage)-[:REFERENCES]->(:File)
(:ArchitectureDecision)-[:CONSTRAINS]->(:Service)
(:Service)-[:EXPOSES]->(:APIEndpoint)
(:APIEndpoint)-[:HANDLED_BY]->(:Function)
```

Indexes:

```cypher
create constraint repository_id if not exists for (r:Repository) require r.id is unique;
create constraint file_id if not exists for (f:File) require f.id is unique;
create constraint symbol_id if not exists for (s:Symbol) require s.id is unique;
create index file_path if not exists for (f:File) on (f.path);
create index symbol_name if not exists for (s:Symbol) on (s.name);
```

## Vector Storage Schema

Core fields:

- chunk_id
- embedding
- model
- repository_id
- file_id
- chunk_type
- language
- symbol_kind
- path
- line range
- commit sha

Recommended pgvector index:

```sql
create index chunk_embeddings_hnsw_idx
on chunk_embeddings
using hnsw (embedding vector_cosine_ops);

create index chunks_repo_type_idx
on chunks(repository_id, chunk_type);
```

---

# Section 9: Development Roadmap

## Month 1: Foundation and Repository Indexing

Goal: Ingest GitHub repositories and answer basic grounded questions.

Week 1:

- Finalize product scope.
- Create GitHub organization and public landing repo.
- Build design mockups.
- Set up monorepo, CI, Docker Compose.
- Create FastAPI backend and React frontend.
- Create Postgres schema.

Deliverables:

- Running local app.
- Auth mock.
- Basic dashboard.
- Database migrations.

Week 2:

- Build GitHub OAuth and GitHub App installation.
- Store installations and repositories.
- Build repository fetcher.
- Implement file filtering.
- Store file tree and raw metadata.

Deliverables:

- Connect GitHub repo.
- List repositories.
- Start ingestion job.

Week 3:

- Add parser pipeline.
- Extract README/docs.
- Add tree-sitter for one or two languages only.
- Create chunks.
- Generate embeddings locally.
- Store chunks and embeddings in pgvector.

Deliverables:

- Searchable code/docs chunks.
- Basic semantic search endpoint.

Week 4:

- Build chat endpoint with citations.
- Implement hybrid retrieval v1.
- Build indexing status UI.
- Add architecture summary v1.
- Test with 5 public repos.

Deliverables:

- Ask questions about a repo.
- Answers cite files.
- Demo-ready repo summary.

Expected outcome:

- A user can connect a GitHub repo and ask basic architecture/code questions.

## Month 2: Knowledge Graph and Architecture Intelligence

Goal: Explain code relationships and generate useful architecture summaries.

Week 5:

- Add symbol extraction for JavaScript/TypeScript and Python.
- Store functions, classes, imports.
- Create graph_edges table.
- Build graph queries for file neighbors.

Deliverables:

- File relationship map.
- Symbol search.

Week 6:

- Add Neo4j projection.
- Build architecture graph view.
- Add module/service detection heuristics.
- Add package and route parsing.

Deliverables:

- Visual service/module map.
- Cypher-based graph queries.

Week 7:

- Build Architecture Agent.
- Generate architecture summaries by repo.
- Detect entry points, APIs, data stores, external services.
- Add docs-vs-code gap report.

Deliverables:

- Architecture report page.
- Downloadable markdown report.

Week 8:

- Improve retrieval quality.
- Add reranking heuristic.
- Add feedback buttons.
- Add answer confidence and unknowns.
- Run usability tests with 5 to 10 developers.

Deliverables:

- Better chat accuracy.
- Feedback logging.
- Architecture demo script.

Expected outcome:

- The product feels like it understands a repository, not just files.

## Month 3: PR Review Agent and Growth Loop

Goal: Create the "wow" feature and public acquisition loop.

Week 9:

- Implement GitHub PR webhooks.
- Fetch PR diff.
- Map changed hunks to files and symbols.
- Retrieve related code, docs, and PR history.

Deliverables:

- PR ingestion pipeline.
- PR context pack.

Week 10:

- Build Code Review Agent.
- Generate private review summary first.
- Add risk scoring.
- Add missing test detection.
- Add repository-specific review rules.

Deliverables:

- Review dashboard.
- Agent output without posting comments yet.

Week 11:

- Enable GitHub PR comments.
- Add safe mode: only comment when confidence is high.
- Add comment deduplication.
- Add feedback labels: useful, wrong, too noisy.

Deliverables:

- GitHub PR Review Agent.
- Demo on sample PRs.

Week 12:

- Build public repo analyzer.
- Generate shareable public architecture reports.
- Add waitlist capture.
- Publish open-source core.
- Launch to student communities and open-source maintainers.

Deliverables:

- Public growth page.
- Shareable reports.
- First 50 waitlist users.

Expected outcome:

- Users can see immediate value in PRs.

## Month 4: Validation, Reliability, and Fundraising Readiness

Goal: Turn demo into pilot-ready product.

Week 13:

- Improve indexing reliability.
- Add webhook incremental updates.
- Add job retries and failure visibility.
- Add usage limits.

Deliverables:

- Stable indexing pipeline.
- Admin debugging tools.

Week 14:

- Add multi-repo organization support.
- Improve permission checks.
- Add basic team roles.
- Add data deletion flow.

Deliverables:

- Safer team usage.
- Basic compliance story.

Week 15:

- Run pilots with 3 to 5 teams.
- Measure onboarding use cases and PR comment quality.
- Improve prompts and retrieval based on feedback.
- Create case studies.

Deliverables:

- Pilot feedback.
- Product metrics.
- Demo quotes.

Week 16:

- Prepare YC/investor materials.
- Record demo video.
- Create landing page.
- Create pricing page.
- Decide open-source roadmap.

Deliverables:

- Investor deck.
- YC application draft.
- Public GitHub repo.
- Launch checklist.

Expected outcome:

- A credible MVP with users, feedback, and a focused wedge.

---

# Section 10: Team Structure

Assume 8 students.

## Student 1: Technical Lead / AI Architect

Responsibilities:

- Own overall architecture.
- Design RAG and agent workflows.
- Review backend and AI code.
- Decide model/provider strategy.
- Maintain technical roadmap.

## Student 2: AI Engineer - Retrieval

Responsibilities:

- Chunking and embeddings.
- Hybrid retrieval.
- Reranking.
- Evaluation datasets.
- Answer citation quality.

## Student 3: AI Engineer - Agents

Responsibilities:

- Repository Understanding Agent.
- Architecture Agent.
- Code Review Agent.
- Prompt engineering.
- Agent run logging and feedback loops.

## Student 4: Backend Engineer

Responsibilities:

- FastAPI services.
- Database schema.
- GitHub OAuth and GitHub App.
- API endpoints.
- Job orchestration.

## Student 5: Backend/Platform Engineer

Responsibilities:

- Ingestion workers.
- Tree-sitter parsing.
- GitHub webhook processing.
- Queue and retry system.
- Object storage.

## Student 6: Frontend Engineer

Responsibilities:

- React/Next.js app.
- Dashboard.
- Chat UI.
- Architecture report UI.
- PR review settings UI.

## Student 7: DevOps/Security Engineer

Responsibilities:

- Docker Compose.
- CI/CD.
- Deployment.
- Secrets management.
- Observability.
- Access control.

## Student 8: Product/Growth Engineer

Responsibilities:

- User interviews.
- Landing page.
- Public repo analyzer.
- Demo scripts.
- Analytics.
- Community launch.
- Documentation.

Operating rhythm:

- Weekly sprint planning.
- 2 demos per month.
- Every feature must have an owner.
- Every agent must have an eval set.
- Every user interview should produce a product decision.

---

# Section 11: MVP Plan

## Minimum Features

Build only:

- GitHub App connection.
- Repo and docs ingestion.
- Code/docs semantic search.
- Architecture summary.
- Chat with citations.
- PR Review Agent.
- Public repo analyzer.
- Basic dashboard.

## What Not To Build

Do not build in the MVP:

- Slack integration.
- Jira integration.
- Email ingestion.
- Enterprise SSO.
- Full autonomous code editing.
- IDE extension.
- Custom model training.
- Multi-cloud deployment.
- Kubernetes.
- Complex billing system.
- Perfect graph visualization.
- Support for every programming language.

## Fastest Route To Validation

1. Pick TypeScript and Python repositories first.
2. Build a public repo analyzer.
3. Analyze popular open-source repos and share reports.
4. Let users ask 5 free questions about a repo.
5. Ask for email to enable PR Review Agent.
6. Run PR reviews on 3 pilot teams.
7. Measure how many comments are useful.

Validation metrics:

- 30 percent of public analyzer users ask a follow-up question.
- 10 percent join waitlist.
- 5 pilot teams install GitHub App.
- PR Review Agent produces at least 1 useful comment per 3 PRs.
- Less than 20 percent of comments are marked noisy or wrong.
- At least 3 teams say they would pay.

---

# Section 12: Monetization

## Free Tier

Price: USD 0/month.

Limits:

- Public repositories only, or 1 private repo.
- 1 seat.
- 100 questions/month.
- 10 PR reviews/month.
- Limited indexing frequency.
- Community support.

Purpose:

- Growth.
- Open-source adoption.
- Student and indie developer usage.

## Startup Tier

Price: USD 19 to USD 29 per developer/month, or USD 99/month flat for up to 5 developers.

Includes:

- Private repositories.
- 5 to 10 seats.
- 1 organization.
- 10 repositories.
- 1,000 questions/month.
- 200 PR reviews/month.
- Weekly architecture reports.

Target:

- Early-stage startups.
- Agencies.
- Small teams.

## Team Tier

Price: USD 49 per developer/month or USD 499/month for up to 20 developers.

Includes:

- Multi-repo support.
- Higher PR review limits.
- Ownership inference.
- Team roles.
- Better audit logs.
- Priority support.
- Custom review rules.

Target:

- Growing engineering teams.

## Enterprise Tier

Price: USD 20K to USD 100K/year depending on size.

Includes:

- Self-hosted or VPC deployment.
- SSO/SAML.
- Advanced permission sync.
- Audit logs.
- Dedicated support.
- Custom model routing.
- Compliance features.
- Private graph and vector infrastructure.

Target:

- Regulated companies.
- Large engineering organizations.

## Pricing Philosophy

Charge for:

- Private code understanding.
- PR review automation.
- Team collaboration.
- Security and compliance.
- Higher usage.

Do not charge early for:

- Public repo analyzer.
- Open-source projects.
- Student experimentation.

---

# Section 13: Security

## Data Isolation

Rules:

- Every table includes organization_id where relevant.
- All queries are scoped by organization and repository.
- Background jobs carry organization context.
- Vector and graph queries must filter by organization/repository.
- Never mix context across organizations.

## Access Control

MVP:

- GitHub OAuth.
- GitHub App installation permissions.
- Organization roles: owner, admin, member, viewer.
- Repository access synced from GitHub where feasible.

Later:

- SSO/SAML.
- SCIM.
- Fine-grained RBAC.
- Policy engine such as OpenFGA or Casbin.

## Secrets Management

Local:

- .env files excluded from Git.
- Example env file committed.

Hosted:

- Use platform secret managers.
- Rotate GitHub App private keys when needed.
- Encrypt stored tokens.
- Store only needed permissions.

Rules:

- Never log tokens.
- Never send secrets to LLMs.
- Redact secrets during ingestion.
- Run secret scanning before indexing chunks.

## Permission Systems

GitHub App permissions:

- Repository contents: read.
- Pull requests: read/write only for PR comments.
- Metadata: read.
- Issues: optional later.
- Checks: optional later.

Principle of least privilege:

- Start with read-only and request write access only when PR Review Agent is enabled.
- Let admins disable PR comments.
- Add dry-run review mode.

## Security Risks and Mitigations

Risk: Private code leakage to external LLMs.

Mitigation:

- Default to local models for private repos.
- Make provider routing explicit.
- Add "no external LLM" mode.

Risk: Prompt injection from repository docs.

Mitigation:

- Treat retrieved content as untrusted data.
- System prompt states that repo content cannot override policies.
- Strip suspicious instructions from docs before final context.

Risk: Over-permissioned GitHub App.

Mitigation:

- Minimal permissions.
- Separate read-only mode and PR-comment mode.

Risk: Cross-tenant retrieval leakage.

Mitigation:

- Mandatory organization filters.
- Integration tests for tenancy.
- Row-level security if using Supabase.

---

# Section 14: Investor Pitch

## One-Line Pitch

Engineering Brain is the AI memory layer that understands your GitHub repositories, docs, architecture, and PR history like a senior engineer.

## Elevator Pitch

Engineering teams waste enormous time rediscovering how their own systems work. Current AI coding tools are powerful, but they often lack durable company-specific engineering memory. Engineering Brain connects to GitHub and documentation, builds a code-aware knowledge graph, and answers architecture questions with citations. Its wedge is an AI PR Review Agent that comments on pull requests using past architectural decisions and repository context. We start free and open-source for small teams, then monetize private repositories, team features, and enterprise deployment.

## YC Application Summary

We are building Engineering Brain, an AI engineering intelligence platform for software teams. It connects to GitHub and docs, indexes code, PRs, commits, and architecture relationships, then acts like a senior engineer that can answer questions and review pull requests with citations. The initial wedge is a GitHub PR Review Agent that flags risky changes and cites relevant code, docs, and historical decisions. Teams already use AI coding tools, but those tools do not maintain durable organizational engineering memory. We are starting with students, open-source maintainers, and startups using a free-first product and public repo analyzer for distribution.

## Demo Script

Demo setup:

- Use a real public repo.
- Show GitHub App connection.
- Show indexing status.
- Show architecture summary.
- Ask an engineering question.
- Open a sample PR.
- Show the PR Review Agent comment with citations.

Script:

1. "This is Engineering Brain. It connects to GitHub and reads the repo, docs, PRs, and architecture relationships."
2. "Here is a freshly indexed repository. The system has detected the main modules, entry points, API routes, and dependency graph."
3. "I can ask, 'How does authentication work?' The answer cites the auth middleware, route handlers, and docs."
4. "Now here is the real wedge: a pull request changed an auth-sensitive route."
5. "Engineering Brain reviewed the PR and found that the change bypasses a pattern used elsewhere. It cites the related file and historical decision."
6. "This saves senior engineers from repeating context and helps new engineers avoid architecture mistakes."

---

# Section 15: Implementation Details

## Folder Structure

```text
engineering-brain/
  apps/
    web/
      src/
        app/
        components/
        lib/
        styles/
      package.json
    api/
      app/
        main.py
        api/
          routes_auth.py
          routes_github.py
          routes_repos.py
          routes_search.py
          routes_chat.py
          routes_agents.py
        core/
          config.py
          security.py
          logging.py
        db/
          models.py
          migrations/
        services/
          github_service.py
          repo_service.py
          search_service.py
          chat_service.py
        agents/
          repository_agent.py
          architecture_agent.py
          code_review_agent.py
          documentation_agent.py
          bug_agent.py
        retrieval/
          chunking.py
          embeddings.py
          hybrid_search.py
          rerank.py
          context_pack.py
        graph/
          writer.py
          queries.py
          neo4j_projection.py
        workers/
          ingest_repo.py
          index_file.py
          review_pr.py
          summarize_architecture.py
      pyproject.toml
  packages/
    shared-types/
    prompts/
    evals/
  infra/
    docker-compose.yml
    render.yaml
    cloudflare-pages.md
  docs/
    architecture.md
    security.md
    api.md
    roadmap.md
  scripts/
    seed_demo_repo.py
    run_evals.py
```

## API Design

Authentication:

```text
GET  /auth/github/login
GET  /auth/github/callback
POST /auth/logout
GET  /me
```

GitHub:

```text
POST /github/webhooks
GET  /github/installations
GET  /github/repositories
POST /github/repositories/{repo_id}/sync
```

Repositories:

```text
GET  /repos
GET  /repos/{repo_id}
GET  /repos/{repo_id}/index-status
GET  /repos/{repo_id}/files
GET  /repos/{repo_id}/files/{file_id}
GET  /repos/{repo_id}/symbols
```

Search:

```text
POST /search
POST /search/code
POST /search/docs
POST /search/hybrid
```

Chat:

```text
POST /chat
GET  /chat/sessions
GET  /chat/sessions/{session_id}
```

Agents:

```text
POST /agents/repository-summary
POST /agents/architecture-summary
POST /agents/pr-review
POST /agents/documentation-audit
POST /agents/bug-investigation
GET  /agents/runs/{run_id}
```

Public analyzer:

```text
POST /public/analyze
GET  /public/reports/{report_id}
```

## Microservice Architecture

MVP should be a modular monolith plus workers.

```text
api service:
  auth
  GitHub webhooks
  search
  chat
  agent orchestration

worker service:
  repo ingestion
  embeddings
  graph projection
  PR review
  report generation

frontend service:
  dashboard
  chat
  reports
  settings
```

Why not microservices immediately:

- Student team velocity matters more than distributed system purity.
- Debugging is easier.
- Deployment is cheaper.

Split later when:

- Ingestion jobs block API performance.
- PR review needs independent scaling.
- Enterprise customers require isolated workers.

## Deployment Instructions

Local:

```bash
git clone https://github.com/your-org/engineering-brain
cd engineering-brain
cp .env.example .env
docker compose up -d postgres redis neo4j
cd apps/api
uv sync
uv run fastapi dev app/main.py
cd ../web
npm install
npm run dev
```

Hosted MVP:

1. Create Supabase project.
2. Enable pgvector.
3. Apply database migrations.
4. Create GitHub App.
5. Add GitHub App credentials to backend secrets.
6. Deploy API to Render or Railway.
7. Deploy worker to Render worker or scheduled job.
8. Deploy frontend to Cloudflare Pages.
9. Create Upstash Redis database.
10. Create Cloudflare R2 bucket.
11. Create Neo4j AuraDB Free database.
12. Add webhook URL to GitHub App.
13. Run demo repo ingestion.

Environment variables:

```text
DATABASE_URL=
REDIS_URL=
GITHUB_APP_ID=
GITHUB_APP_PRIVATE_KEY=
GITHUB_CLIENT_ID=
GITHUB_CLIENT_SECRET=
GITHUB_WEBHOOK_SECRET=
LLM_PROVIDER=
GROQ_API_KEY=
OLLAMA_BASE_URL=
R2_ACCESS_KEY_ID=
R2_SECRET_ACCESS_KEY=
R2_BUCKET=
NEO4J_URI=
NEO4J_USERNAME=
NEO4J_PASSWORD=
```

---

# Section 16: Open-Source Strategy

## What To Open Source

Open-source:

- Repo analyzer core.
- Chunking pipeline.
- Code graph extractor.
- Prompt templates.
- Local-only version.
- Public architecture report generator.
- Evaluation datasets for open-source repos.

Keep proprietary initially:

- Hosted multi-tenant platform.
- PR Review Agent quality tuning.
- Enterprise permission sync.
- Usage analytics.
- Billing.
- Managed deployment tooling.

## How To Attract GitHub Stars

Build public artifacts developers want:

- "Paste any GitHub repo, get an architecture report."
- Badges: "Architecture understood by Engineering Brain."
- Weekly teardown posts of popular open-source repos.
- Before/after PR review demos.
- Free local CLI.
- "Ask your repo" demo with no signup.

Launch channels:

- GitHub.
- Hacker News.
- Reddit programming communities.
- Product Hunt.
- LinkedIn developer posts.
- University startup communities.
- Open-source maintainer outreach.

Star-worthy README:

- GIF demo at the top.
- One-command local setup.
- Clear architecture diagram.
- Example output from a famous repo.
- Roadmap.
- Good first issues.
- Contributor guide.

## Community Strategy

Community loops:

- Public Discord.
- Weekly build logs.
- Open issues for language parser support.
- Invite maintainers to submit repo reports.
- Student ambassador program.
- Monthly "AI codebase understanding benchmark."

Contributor paths:

- Add language parser.
- Add framework detector.
- Improve prompts.
- Add eval cases.
- Add UI improvements.
- Write docs.

---

# Section 17: Risks

## Technical Risks

Risk: Retrieval quality is poor.

Mitigation:

- Build eval set early.
- Use exact search plus vector search.
- Require citations.
- Log failed questions.

Risk: PR comments are noisy.

Mitigation:

- Start with dry-run mode.
- Comment only on high-confidence issues.
- Prefer fewer, deeper comments.
- Add feedback buttons.

Risk: Free-tier limits break demos.

Mitigation:

- Keep local demo path with Docker Compose.
- Cache public reports.
- Use rate limits.
- Keep fallback services.

Risk: Large repositories are hard to index.

Mitigation:

- File filters.
- Incremental indexing.
- Index only default branch first.
- Prioritize docs, source files, and config.

Risk: Local models are not strong enough.

Mitigation:

- Use local models for retrieval and summaries.
- Use free hosted LLMs for final answer where allowed.
- Keep provider adapter ready for paid models later.

## Product Risks

Risk: Users already have Copilot/Cursor and do not see need.

Mitigation:

- Focus on organization memory and PR review, not autocomplete.

Risk: Users do not trust AI review comments.

Mitigation:

- Cite evidence.
- Let teams configure strictness.
- Show dry-run summaries first.

Risk: Setup friction is too high.

Mitigation:

- Public repo analyzer first.
- GitHub App install flow.
- Sample repos.

## Competition Risks

Risk: GitHub or Cursor ships similar features.

Mitigation:

- Move faster in open-source and small-team segment.
- Build graph + documentation + PR-history specialization.
- Create community and self-hosted option.

Risk: Enterprise search tools expand into code intelligence.

Mitigation:

- Stay engineering-native.
- Win PR workflow.
- Offer low-cost self-hosted path.

## Scaling Risks

Risk: Indexing costs grow with repository size.

Mitigation:

- Incremental indexing.
- Queue-based processing.
- Usage quotas.
- Paid plans for private large repos.

Risk: Multi-tenant security becomes complex.

Mitigation:

- Build tenancy into schema from day one.
- Add tests for data isolation.
- Offer self-hosting for sensitive customers.

---

# Section 18: Final Recommendation

## Is This Worth Building?

Yes. This is worth building if the team stays focused on GitHub plus documentation and avoids becoming a generic workplace AI search tool. The idea is strong because engineering teams already feel the pain, AI coding adoption is growing quickly, and most tools still struggle with durable organization-specific engineering context.

## Probability Of Getting First Users

Estimated probability: high, around 70 percent if the team ships a public repo analyzer and personally recruits users.

Reasons:

- Students can access other students, open-source maintainers, and startups.
- Public GitHub repo analysis is low-friction.
- Developers are curious about AI tools.

## Probability Of Raising Funding

Estimated probability: moderate, around 20 to 35 percent after a working MVP and early pilots.

Funding probability improves if:

- PR Review Agent produces consistently useful comments.
- At least 5 real teams install the GitHub App.
- Users report reduced onboarding or review time.
- The demo clearly shows architecture memory.

Funding probability is weak if:

- The product is only another chat-with-repo clone.
- There are no users.
- Answers lack citations.
- The PR agent is noisy.

## Most Important Feature To Focus On First

The most important feature is the PR Review Agent that comments on GitHub pull requests using codebase context, documentation, and past architecture decisions.

Why:

- It appears in an existing workflow.
- It gives immediate value.
- It creates a memorable demo.
- It differentiates from generic repo chat.
- It can become the wedge into paid teams.

## Final Build Order

1. GitHub repo ingestion.
2. Code and docs search with citations.
3. Architecture summary.
4. Incremental webhook updates.
5. PR Review Agent dry-run.
6. GitHub PR comments.
7. Public repo analyzer.
8. Pilot teams.

## Final CTO Advice

Do not build "autonomous AI engineer" first. Build trust first. Trust comes from grounded answers, citations, and useful PR comments. If the product becomes the tool that knows why the codebase works the way it does, autonomy becomes a natural next step.

