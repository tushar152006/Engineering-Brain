from functools import cached_property

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # App configuration
    app_env: str = Field(default="development", alias="APP_ENV")
    app_version: str = Field(default="1.0.0", alias="APP_VERSION")
    api_cors_origins: str = Field(
        default="http://127.0.0.1:5173,http://localhost:5173",
        alias="API_CORS_ORIGINS",
    )

    # Storage (Phase 1)
    enable_local_repo_import: bool = Field(default=True, alias="ENABLE_LOCAL_REPO_IMPORT")
    max_index_file_bytes: int = Field(default=250_000, alias="MAX_INDEX_FILE_BYTES")
    index_store_path: str = Field(
        default=".engineering-brain/index-store.json",
        alias="INDEX_STORE_PATH",
    )

    # Database (Phase 4)
    database_url: str | None = Field(default=None, alias="DATABASE_URL")
    use_persistent_store: bool = Field(default=True, alias="USE_PERSISTENT_STORE")

    # Redis (Phase 4)
    redis_url: str = Field(default="redis://localhost:6379", alias="REDIS_URL")

    # Ollama integration
    ollama_base_url: str = Field(default="http://127.0.0.1:11434", alias="OLLAMA_BASE_URL")
    ollama_chat_model: str = Field(default="llama3.1:8b", alias="OLLAMA_CHAT_MODEL")
    ollama_embed_model: str = Field(default="nomic-embed-text", alias="OLLAMA_EMBED_MODEL")
    enable_llm: bool = Field(default=True, alias="ENABLE_LLM")
    enable_embeddings: bool = Field(default=True, alias="ENABLE_EMBEDDINGS")
    embed_batch_size: int = Field(default=8, alias="EMBED_BATCH_SIZE")

    # GitHub OAuth (Phase 4)
    github_client_id: str | None = Field(default=None, alias="GITHUB_CLIENT_ID")
    github_client_secret: str | None = Field(default=None, alias="GITHUB_CLIENT_SECRET")
    github_oauth_redirect_uri: str = Field(
        default="http://localhost:8000/auth/github/callback",
        alias="GITHUB_OAUTH_REDIRECT_URI",
    )

    # GitHub App (Phase 4)
    github_app_id: str | None = Field(default=None, alias="GITHUB_APP_ID")
    github_app_private_key: str | None = Field(default=None, alias="GITHUB_APP_PRIVATE_KEY")
    github_webhook_secret: str | None = Field(default=None, alias="GITHUB_WEBHOOK_SECRET")

    # Legacy GitHub Token (Phase 1)
    github_token: str | None = Field(default=None, alias="GITHUB_TOKEN")

    # PR Review settings
    pr_review_dry_run: bool = Field(default=True, alias="PR_REVIEW_DRY_RUN")
    pr_review_min_confidence: str = Field(default="medium", alias="PR_REVIEW_MIN_CONFIDENCE")

    # Monitoring (Phase 4)
    sentry_dsn: str | None = Field(default=None, alias="SENTRY_DSN")

    @cached_property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.api_cors_origins.split(",") if origin.strip()]


settings = Settings()
