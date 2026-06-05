import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import make_asgi_app

from app.api.routes import router
from app.api.routes_github import router as github_router
from app.api.routes_public import router as public_router
from app.core.config import settings
from app.core.observability import init_sentry, MetricsMiddleware
from app.db.persistent_store import get_persistent_store

logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    app = FastAPI(
        title="Engineering Brain API",
        version="1.0.0",
        description="Repository intelligence API",
    )

    # Initialize Sentry
    init_sentry()

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Add metrics middleware
    app.add_middleware(MetricsMiddleware)

    # Include routers
    app.include_router(router)
    app.include_router(github_router)
    app.include_router(public_router)

    # Mount Prometheus metrics
    metrics_app = make_asgi_app()
    app.mount("/metrics", metrics_app)

    # Startup/shutdown events
    @app.on_event("startup")
    async def startup_event():
        # Initialize database
        if settings.use_persistent_store and settings.database_url:
            try:
                store = get_persistent_store()
                await store.initialize()
                logger.info("Persistent store database initialized successfully")
            except Exception as e:
                logger.exception("Failed to initialize database: %s", e)

        # Initialize Redis queue
        try:
            from app.services.job_queue import get_job_queue
            await get_job_queue()
            logger.info("Redis job queue initialized successfully")
        except Exception as e:
            logger.warning("Redis queue connection failed: %s", e)

    @app.on_event("shutdown")
    async def shutdown_event():
        # Close database
        if settings.use_persistent_store and settings.database_url:
            try:
                store = get_persistent_store()
                await store.shutdown()
                logger.info("Persistent store database shut down successfully")
            except Exception as e:
                logger.exception("Failed to shutdown database: %s", e)

        # Disconnect Redis queue
        try:
            from app.services.job_queue import get_job_queue
            jq = await get_job_queue()
            await jq.disconnect()
            logger.info("Redis job queue disconnected successfully")
        except Exception as e:
            logger.warning("Failed to disconnect Redis queue: %s", e)

    return app


app = create_app()
