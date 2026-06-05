-- Engineering Brain Database Initialization
-- This script runs automatically when PostgreSQL container starts

-- Create pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Organizations
CREATE TABLE IF NOT EXISTS organizations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL UNIQUE,
    slug TEXT UNIQUE NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Users
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    github_user_id BIGINT UNIQUE,
    email TEXT UNIQUE,
    name TEXT,
    avatar_url TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Organization members
CREATE TABLE IF NOT EXISTS organization_members (
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN ('owner', 'admin', 'member', 'viewer')),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (organization_id, user_id)
);

-- Repositories
CREATE TABLE IF NOT EXISTS repositories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    github_repo_id BIGINT UNIQUE,
    full_name TEXT NOT NULL,
    default_branch TEXT NOT NULL DEFAULT 'main',
    visibility TEXT NOT NULL DEFAULT 'public',
    last_indexed_commit TEXT,
    indexing_status TEXT NOT NULL DEFAULT 'pending',
    file_count INT DEFAULT 0,
    chunk_count INT DEFAULT 0,
    embedded_chunk_count INT DEFAULT 0,
    symbol_count INT DEFAULT 0,
    edge_count INT DEFAULT 0,
    languages TEXT[] DEFAULT '{}',
    indexed_at TIMESTAMPTZ,
    error TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(organization_id, github_repo_id)
);

CREATE INDEX IF NOT EXISTS idx_repositories_org ON repositories(organization_id);
CREATE INDEX IF NOT EXISTS idx_repositories_status ON repositories(indexing_status);
CREATE INDEX IF NOT EXISTS idx_repositories_updated ON repositories(updated_at DESC);

-- Files
CREATE TABLE IF NOT EXISTS files (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    repository_id UUID NOT NULL REFERENCES repositories(id) ON DELETE CASCADE,
    path TEXT NOT NULL,
    language TEXT,
    size_bytes INT,
    sha TEXT,
    is_generated BOOLEAN DEFAULT FALSE,
    summary TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(repository_id, path)
);

CREATE INDEX IF NOT EXISTS idx_files_repo ON files(repository_id);
CREATE INDEX IF NOT EXISTS idx_files_language ON files(language);

-- Chunks (indexed content)
CREATE TABLE IF NOT EXISTS chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    repository_id UUID NOT NULL REFERENCES repositories(id) ON DELETE CASCADE,
    file_id UUID REFERENCES files(id) ON DELETE CASCADE,
    chunk_type TEXT NOT NULL,
    content TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    start_line INT,
    end_line INT,
    title TEXT,
    token_estimate INT,
    symbol_name TEXT,
    symbol_kind TEXT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(repository_id, content_hash)
);

CREATE INDEX IF NOT EXISTS idx_chunks_repo ON chunks(repository_id);
CREATE INDEX IF NOT EXISTS idx_chunks_file ON chunks(file_id);
CREATE INDEX IF NOT EXISTS idx_chunks_type ON chunks(chunk_type);

-- Chunk embeddings
CREATE TABLE IF NOT EXISTS chunk_embeddings (
    chunk_id UUID PRIMARY KEY REFERENCES chunks(id) ON DELETE CASCADE,
    embedding vector(384),
    model TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_embeddings_hnsw ON chunk_embeddings
    USING hnsw (embedding vector_cosine_ops);

-- Symbols (functions, classes, etc.)
CREATE TABLE IF NOT EXISTS symbols (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    repository_id UUID NOT NULL REFERENCES repositories(id) ON DELETE CASCADE,
    file_id UUID REFERENCES files(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    qualified_name TEXT,
    kind TEXT NOT NULL,
    start_line INT,
    end_line INT,
    signature TEXT,
    language TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_symbols_repo ON symbols(repository_id);
CREATE INDEX IF NOT EXISTS idx_symbols_file ON symbols(file_id);
CREATE INDEX IF NOT EXISTS idx_symbols_name ON symbols(name);
CREATE INDEX IF NOT EXISTS idx_symbols_kind ON symbols(kind);

-- Graph edges (dependencies)
CREATE TABLE IF NOT EXISTS graph_edges (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    repository_id UUID NOT NULL REFERENCES repositories(id) ON DELETE CASCADE,
    source_type TEXT NOT NULL,
    source_id UUID NOT NULL,
    relationship TEXT NOT NULL,
    target_type TEXT NOT NULL,
    target_id UUID NOT NULL,
    weight NUMERIC DEFAULT 1,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_edges_repo ON graph_edges(repository_id);
CREATE INDEX IF NOT EXISTS idx_edges_source ON graph_edges(source_id);
CREATE INDEX IF NOT EXISTS idx_edges_target ON graph_edges(target_id);

-- Pull requests
CREATE TABLE IF NOT EXISTS pull_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    repository_id UUID NOT NULL REFERENCES repositories(id) ON DELETE CASCADE,
    github_pr_number INT NOT NULL,
    title TEXT,
    body TEXT,
    author_login TEXT,
    base_branch TEXT,
    head_branch TEXT,
    state TEXT,
    merged BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ,
    UNIQUE(repository_id, github_pr_number)
);

CREATE INDEX IF NOT EXISTS idx_prs_repo ON pull_requests(repository_id);
CREATE INDEX IF NOT EXISTS idx_prs_state ON pull_requests(state);

-- Agent runs
CREATE TABLE IF NOT EXISTS agent_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    repository_id UUID NOT NULL REFERENCES repositories(id) ON DELETE CASCADE,
    agent_type TEXT NOT NULL,
    input JSONB NOT NULL,
    output JSONB,
    status TEXT NOT NULL DEFAULT 'running',
    model TEXT,
    error TEXT,
    started_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_runs_repo ON agent_runs(repository_id);
CREATE INDEX IF NOT EXISTS idx_runs_status ON agent_runs(status);
CREATE INDEX IF NOT EXISTS idx_runs_type ON agent_runs(agent_type);

-- Feedback
CREATE TABLE IF NOT EXISTS feedback (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_run_id UUID REFERENCES agent_runs(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    rating INT CHECK (rating BETWEEN 1 AND 5),
    label TEXT,
    comment TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_feedback_run ON feedback(agent_run_id);
CREATE INDEX IF NOT EXISTS idx_feedback_user ON feedback(user_id);

-- Create default organization
INSERT INTO organizations (name, slug)
VALUES ('Default', 'default')
ON CONFLICT (slug) DO NOTHING;

-- Materialized views for analytics
CREATE MATERIALIZED VIEW IF NOT EXISTS repository_stats AS
SELECT
    r.id,
    r.full_name,
    r.indexing_status,
    r.file_count,
    r.chunk_count,
    r.embedded_chunk_count,
    r.symbol_count,
    r.edge_count,
    r.languages,
    r.indexed_at,
    COUNT(DISTINCT ch.id) as actual_chunk_count,
    COUNT(DISTINCT ce.chunk_id) as actual_embedded_count
FROM repositories r
LEFT JOIN chunks ch ON r.id = ch.repository_id
LEFT JOIN chunk_embeddings ce ON ch.id = ce.chunk_id
GROUP BY r.id, r.full_name, r.indexing_status, r.file_count,
         r.chunk_count, r.embedded_chunk_count, r.symbol_count,
         r.edge_count, r.languages, r.indexed_at;

CREATE UNIQUE INDEX IF NOT EXISTS idx_repo_stats_id ON repository_stats(id);

-- Function to update repository updated_at timestamp
CREATE OR REPLACE FUNCTION update_repository_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_repository_updated_at
BEFORE UPDATE ON repositories
FOR EACH ROW
EXECUTE FUNCTION update_repository_updated_at();

-- Log initialization
SELECT NOW(), 'Engineering Brain database initialized successfully' as message;
