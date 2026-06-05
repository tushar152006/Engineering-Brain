"""PostgreSQL schema and migration guide for Engineering Brain.

This schema implements the production database layer using PostgreSQL + pgvector.
Run these migrations to upgrade from the in-memory store to a persistent database.
"""

# Migration 001: Create base tables
CREATE_BASE_TABLES = """
-- Organizations and users
CREATE TABLE IF NOT EXISTS organizations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    slug TEXT UNIQUE NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    github_user_id BIGINT UNIQUE,
    email TEXT,
    name TEXT,
    avatar_url TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS organization_members (
    organization_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN ('owner', 'admin', 'member', 'viewer')),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (organization_id, user_id)
);

-- Repositories
CREATE TABLE IF NOT EXISTS repositories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
    github_repo_id BIGINT UNIQUE,
    full_name TEXT NOT NULL,
    default_branch TEXT NOT NULL DEFAULT 'main',
    visibility TEXT NOT NULL,
    last_indexed_commit TEXT,
    indexing_status TEXT NOT NULL DEFAULT 'pending',
    file_count INT DEFAULT 0,
    chunk_count INT DEFAULT 0,
    embedded_chunk_count INT DEFAULT 0,
    symbol_count INT DEFAULT 0,
    edge_count INT DEFAULT 0,
    languages TEXT[] DEFAULT '{}',
    indexed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(organization_id, github_repo_id)
);

CREATE INDEX IF NOT EXISTS idx_repositories_org ON repositories(organization_id);
CREATE INDEX IF NOT EXISTS idx_repositories_status ON repositories(indexing_status);
"""

# Migration 002: Create content tables
CREATE_CONTENT_TABLES = """
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
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(repository_id, content_hash)
);

CREATE INDEX IF NOT EXISTS idx_chunks_repo ON chunks(repository_id);
CREATE INDEX IF NOT EXISTS idx_chunks_file ON chunks(file_id);

-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS chunk_embeddings (
    chunk_id UUID PRIMARY KEY REFERENCES chunks(id) ON DELETE CASCADE,
    embedding vector(384),
    model TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_embeddings_hnsw ON chunk_embeddings
    USING hnsw (embedding vector_cosine_ops);
"""

# Migration 003: Create symbol and graph tables
CREATE_SYMBOL_TABLES = """
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
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(repository_id, source_type, source_id, relationship, target_id)
);

CREATE INDEX IF NOT EXISTS idx_edges_repo ON graph_edges(repository_id);
CREATE INDEX IF NOT EXISTS idx_edges_source ON graph_edges(source_id);
CREATE INDEX IF NOT EXISTS idx_edges_target ON graph_edges(target_id);
"""

# Migration 004: Create PR and agent tables
CREATE_PR_AGENT_TABLES = """
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
"""

# Migration 005: Create materialized views for analytics
CREATE_ANALYTICS_VIEWS = """
CREATE MATERIALIZED VIEW IF NOT EXISTS repository_stats AS
SELECT
    r.id,
    r.full_name,
    r.indexing_status,
    COUNT(DISTINCT f.id) as file_count,
    COUNT(DISTINCT ch.id) as chunk_count,
    COUNT(DISTINCT ce.chunk_id) as embedded_count,
    COUNT(DISTINCT s.id) as symbol_count,
    COUNT(DISTINCT ge.id) as edge_count,
    ARRAY_AGG(DISTINCT f.language) as languages
FROM repositories r
LEFT JOIN files f ON r.id = f.repository_id
LEFT JOIN chunks ch ON r.id = ch.repository_id
LEFT JOIN chunk_embeddings ce ON ch.id = ce.chunk_id
LEFT JOIN symbols s ON r.id = s.repository_id
LEFT JOIN graph_edges ge ON r.id = ge.repository_id
GROUP BY r.id, r.full_name, r.indexing_status;

CREATE MATERIALIZED VIEW IF NOT EXISTS symbol_connections AS
SELECT
    s1.id as source_symbol_id,
    s1.name as source_name,
    s2.id as target_symbol_id,
    s2.name as target_name,
    COUNT(*) as connection_count
FROM symbols s1
JOIN files f1 ON s1.file_id = f1.id
JOIN graph_edges ge ON f1.id::TEXT = ge.source_id::TEXT
JOIN files f2 ON f2.repository_id = s1.repository_id
JOIN symbols s2 ON s2.file_id = f2.id
WHERE ge.relationship = 'imports'
GROUP BY s1.id, s1.name, s2.id, s2.name;
"""

# Migration rollback SQL
DROP_ANALYTICS_VIEWS = """
DROP MATERIALIZED VIEW IF EXISTS symbol_connections CASCADE;
DROP MATERIALIZED VIEW IF EXISTS repository_stats CASCADE;
"""

DROP_TABLES = """
DROP TABLE IF EXISTS feedback CASCADE;
DROP TABLE IF EXISTS agent_runs CASCADE;
DROP TABLE IF EXISTS pull_requests CASCADE;
DROP TABLE IF EXISTS graph_edges CASCADE;
DROP TABLE IF EXISTS symbols CASCADE;
DROP TABLE IF EXISTS chunk_embeddings CASCADE;
DROP TABLE IF EXISTS chunks CASCADE;
DROP TABLE IF EXISTS files CASCADE;
DROP TABLE IF EXISTS organization_members CASCADE;
DROP TABLE IF EXISTS users CASCADE;
DROP TABLE IF EXISTS repositories CASCADE;
DROP TABLE IF EXISTS organizations CASCADE;
"""

# Migration application functions
def create_all_tables(connection) -> None:
    """Create all tables and indexes."""
    migrations = [
        ("Base tables", CREATE_BASE_TABLES),
        ("Content tables", CREATE_CONTENT_TABLES),
        ("Symbol tables", CREATE_SYMBOL_TABLES),
        ("PR/Agent tables", CREATE_PR_AGENT_TABLES),
        ("Analytics views", CREATE_ANALYTICS_VIEWS),
    ]

    for name, sql in migrations:
        print(f"Creating {name}...")
        connection.execute(sql)
        connection.commit()
        print(f"✓ {name} created")


def drop_all_tables(connection) -> None:
    """Drop all tables and clean up."""
    print("Dropping analytics views...")
    connection.execute(DROP_ANALYTICS_VIEWS)
    connection.commit()

    print("Dropping all tables...")
    connection.execute(DROP_TABLES)
    connection.commit()

    print("✓ All tables dropped")
