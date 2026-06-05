"""Redis-based job queue for background tasks.

Handles async indexing, embedding, and PR reviews without blocking the API.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Callable, Optional
from datetime import datetime, UTC

import redis.asyncio as aioredis

from app.core.config import settings

logger = logging.getLogger(__name__)


class JobQueue:
    """Redis-backed job queue for background processing."""

    def __init__(self, redis_url: str | None = None):
        self._redis_url = redis_url or settings.redis_url
        self._redis: aioredis.Redis | None = None

    async def connect(self) -> None:
        """Connect to Redis."""
        self._redis = await aioredis.from_url(
            self._redis_url,
            encoding="utf8",
            decode_responses=True
        )
        logger.info("Connected to Redis queue")

    async def disconnect(self) -> None:
        """Disconnect from Redis."""
        if self._redis:
            await self._redis.close()
            logger.info("Disconnected from Redis")

    async def enqueue(
        self,
        queue_name: str,
        job_id: str,
        job_type: str,
        payload: dict[str, Any],
        priority: int = 0,
        ttl: int = 3600,
    ) -> None:
        """Enqueue a job."""
        if not self._redis:
            raise RuntimeError("Redis not connected")

        job = {
            "id": job_id,
            "type": job_type,
            "payload": json.dumps(payload),
            "status": "queued",
            "created_at": datetime.now(UTC).isoformat(),
            "priority": priority,
        }

        # Add to queue (sorted by priority, then FIFO)
        await self._redis.zadd(
            f"queue:{queue_name}",
            {json.dumps(job): -priority},  # Negative for max-heap behavior
        )

        # Set expiration
        await self._redis.expire(f"queue:{queue_name}", ttl)
        logger.info(f"Enqueued job {job_id} to {queue_name}")

    async def dequeue(self, queue_name: str) -> dict | None:
        """Dequeue a job."""
        if not self._redis:
            raise RuntimeError("Redis not connected")

        # Get job with highest priority (lowest negative score)
        results = await self._redis.zrange(
            f"queue:{queue_name}",
            0, 0,
            byscore=False
        )

        if not results:
            return None

        job_str = results[0]
        job = json.loads(job_str)

        # Remove from queue
        await self._redis.zrem(f"queue:{queue_name}", job_str)

        # Mark as processing
        job["status"] = "processing"
        await self._redis.set(
            f"job:{job['id']}",
            json.dumps(job),
            ex=3600
        )

        return job

    async def complete(self, job_id: str, result: dict) -> None:
        """Mark job as complete."""
        if not self._redis:
            raise RuntimeError("Redis not connected")

        await self._redis.set(
            f"job:{job_id}:result",
            json.dumps(result),
            ex=3600
        )
        await self._redis.delete(f"job:{job_id}")
        logger.info(f"Job {job_id} completed")

    async def fail(self, job_id: str, error: str) -> None:
        """Mark job as failed."""
        if not self._redis:
            raise RuntimeError("Redis not connected")

        await self._redis.set(
            f"job:{job_id}:error",
            error,
            ex=3600
        )
        await self._redis.delete(f"job:{job_id}")
        logger.error(f"Job {job_id} failed: {error}")

    async def get_job_status(self, job_id: str) -> str:
        """Get job status."""
        if not self._redis:
            raise RuntimeError("Redis not connected")

        # Check if processing
        job = await self._redis.get(f"job:{job_id}")
        if job:
            return "processing"

        # Check if completed
        result = await self._redis.get(f"job:{job_id}:result")
        if result:
            return "completed"

        # Check if failed
        error = await self._redis.get(f"job:{job_id}:error")
        if error:
            return "failed"

        return "unknown"

    async def queue_length(self, queue_name: str) -> int:
        """Get queue length."""
        if not self._redis:
            return 0
        return await self._redis.zcard(f"queue:{queue_name}")


class IndexQueue:
    """Specialized queue for repository indexing jobs."""

    def __init__(self, job_queue: JobQueue):
        self._queue = job_queue

    async def enqueue_index(
        self,
        job_id: str,
        repo_id: str,
        url: str,
        source: str,
    ) -> None:
        """Enqueue repository indexing job."""
        await self._queue.enqueue(
            queue_name="indexing",
            job_id=job_id,
            job_type="index_repository",
            payload={
                "repo_id": repo_id,
                "url": url,
                "source": source,
            },
            priority=0,
        )

    async def enqueue_pr_review(
        self,
        job_id: str,
        repo_id: str,
        pr_number: int,
        title: str,
        diff: str,
    ) -> None:
        """Enqueue PR review job."""
        await self._queue.enqueue(
            queue_name="pr_reviews",
            job_id=job_id,
            job_type="review_pr",
            payload={
                "repo_id": repo_id,
                "pr_number": pr_number,
                "title": title,
                "diff": diff,
            },
            priority=1,  # Higher priority than indexing
        )


# Global instances
job_queue: JobQueue | None = None
index_queue: IndexQueue | None = None


async def get_job_queue() -> JobQueue:
    """Get global job queue."""
    global job_queue
    if job_queue is None:
        job_queue = JobQueue()
        await job_queue.connect()
    return job_queue


async def get_index_queue() -> IndexQueue:
    """Get global index queue."""
    global index_queue
    if index_queue is None:
        jq = await get_job_queue()
        index_queue = IndexQueue(jq)
    return index_queue
