from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.api.routes_github import router as github_router
from app.api.routes_public import router as public_router
from app.core.config import settings


def create_app() -> FastAPI:
    app = FastAPI(
        title="Engineering Brain API",
        version="0.1.0",
        description="Repository intelligence API for Engineering Brain.",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(router)
    app.include_router(github_router)
    app.include_router(public_router)
    return app


app = create_app()

