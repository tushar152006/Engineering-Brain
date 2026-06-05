"""Observability and monitoring setup for production."""

from __future__ import annotations

import logging
import time
from typing import Callable

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from prometheus_client import Counter, Histogram, Gauge

from app.core.config import settings

logger = logging.getLogger(__name__)

# ─── Prometheus Metrics ───────────────────────────────────────────────────────

# Request metrics
REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"],
)

REQUEST_DURATION = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration",
    ["method", "endpoint"],
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
)

# Search metrics
SEARCH_COUNT = Counter(
    "search_requests_total",
    "Total search requests",
    ["repo_id", "search_type"],
)

SEARCH_DURATION = Histogram(
    "search_duration_seconds",
    "Search latency",
    ["search_type"],
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0),
)

SEARCH_RESULTS = Gauge(
    "search_result_count",
    "Number of search results returned",
)

# Indexing metrics
INDEX_COUNT = Counter(
    "indexing_operations_total",
    "Total indexing operations",
    ["repo_id", "status"],
)

INDEX_DURATION = Histogram(
    "indexing_duration_seconds",
    "Indexing latency",
    buckets=(1.0, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0),
)

CHUNKS_INDEXED = Gauge(
    "chunks_indexed_total",
    "Total chunks indexed",
)

# Database metrics
DB_QUERY_COUNT = Counter(
    "db_queries_total",
    "Total database queries",
    ["operation", "table"],
)

DB_QUERY_DURATION = Histogram(
    "db_query_duration_seconds",
    "Database query latency",
    ["operation"],
    buckets=(0.001, 0.01, 0.05, 0.1, 0.25, 0.5, 1.0),
)

# Agent metrics
AGENT_RUNS = Counter(
    "agent_runs_total",
    "Total agent runs",
    ["agent_type", "status"],
)

AGENT_DURATION = Histogram(
    "agent_duration_seconds",
    "Agent execution time",
    ["agent_type"],
    buckets=(1.0, 5.0, 10.0, 30.0, 60.0),
)

# Cache metrics
CACHE_HITS = Counter(
    "cache_hits_total",
    "Cache hits",
    ["cache_type"],
)

CACHE_MISSES = Counter(
    "cache_misses_total",
    "Cache misses",
    ["cache_type"],
)

# System metrics
ACTIVE_REQUESTS = Gauge(
    "active_requests",
    "Active HTTP requests",
)

QUEUE_LENGTH = Gauge(
    "queue_length",
    "Job queue length",
    ["queue_name"],
)


def init_sentry() -> None:
    """Initialize Sentry error tracking."""
    if not settings.sentry_dsn:
        logger.info("Sentry not configured")
        return

    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        integrations=[
            FastApiIntegration(),
        ],
        traces_sample_rate=0.1,
        environment=settings.app_env,
        release=settings.app_version,
    )
    logger.info("Sentry initialized")


class MetricsMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware for Prometheus metrics."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Track request metrics."""
        ACTIVE_REQUESTS.inc()
        start_time = time.time()

        try:
            response = await call_next(request)
        except Exception as exc:
            REQUEST_COUNT.labels(
                method=request.method,
                endpoint=request.url.path,
                status="error",
            ).inc()
            ACTIVE_REQUESTS.dec()
            raise

        duration = time.time() - start_time

        REQUEST_COUNT.labels(
            method=request.method,
            endpoint=request.url.path,
            status=response.status_code,
        ).inc()

        REQUEST_DURATION.labels(
            method=request.method,
            endpoint=request.url.path,
        ).observe(duration)

        ACTIVE_REQUESTS.dec()

        return response


def record_search(
    repo_id: str,
    search_type: str,
    duration: float,
    result_count: int,
) -> None:
    """Record search metrics."""
    SEARCH_COUNT.labels(repo_id=repo_id, search_type=search_type).inc()
    SEARCH_DURATION.labels(search_type=search_type).observe(duration)
    SEARCH_RESULTS.set(result_count)


def record_indexing(
    repo_id: str,
    status: str,
    duration: float,
    chunk_count: int,
) -> None:
    """Record indexing metrics."""
    INDEX_COUNT.labels(repo_id=repo_id, status=status).inc()
    INDEX_DURATION.observe(duration)
    CHUNKS_INDEXED.set(chunk_count)


def record_db_query(
    operation: str,
    table: str,
    duration: float,
) -> None:
    """Record database query metrics."""
    DB_QUERY_COUNT.labels(operation=operation, table=table).inc()
    DB_QUERY_DURATION.labels(operation=operation).observe(duration)


def record_agent_run(
    agent_type: str,
    status: str,
    duration: float,
) -> None:
    """Record agent run metrics."""
    AGENT_RUNS.labels(agent_type=agent_type, status=status).inc()
    AGENT_DURATION.labels(agent_type=agent_type).observe(duration)


def record_cache_hit(cache_type: str) -> None:
    """Record cache hit."""
    CACHE_HITS.labels(cache_type=cache_type).inc()


def record_cache_miss(cache_type: str) -> None:
    """Record cache miss."""
    CACHE_MISSES.labels(cache_type=cache_type).inc()


def set_queue_length(queue_name: str, length: int) -> None:
    """Set queue length metric."""
    QUEUE_LENGTH.labels(queue_name=queue_name).set(length)
