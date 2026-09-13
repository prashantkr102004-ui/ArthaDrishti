from functools import lru_cache
from pathlib import Path

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url


class Settings(BaseSettings):
    app_name: str = Field(default="ArthaDrishti API", alias="APP_NAME")
    app_env: str = Field(default="development", alias="APP_ENV")
    debug: bool = Field(default=True, alias="DEBUG")
    api_v1_prefix: str = Field(default="/api/v1", alias="API_V1_PREFIX")
    database_url: str = Field(alias="DATABASE_URL")
    frontend_origin: str = Field(
        default="http://localhost:3000",
        alias="FRONTEND_ORIGIN",
    )
    jwt_secret_key: str = Field(alias="JWT_SECRET_KEY")
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    access_token_expire_minutes: int = Field(
        default=30,
        alias="ACCESS_TOKEN_EXPIRE_MINUTES",
    )
    document_storage_path: str = Field(
        default="storage/documents",
        alias="DOCUMENT_STORAGE_PATH",
    )
    max_upload_size_mb: int = Field(default=10, alias="MAX_UPLOAD_SIZE_MB")
    allowed_document_mime_types: str = Field(
        default="application/pdf",
        alias="ALLOWED_DOCUMENT_MIME_TYPES",
    )
    llm_provider: str = Field(default="mock", alias="LLM_PROVIDER")
    llm_api_key: str | None = Field(default=None, alias="LLM_API_KEY")
    llm_model: str = Field(default="mock-financial-tool-caller", alias="LLM_MODEL")
    assistant_max_question_chars: int = Field(
        default=500,
        alias="ASSISTANT_MAX_QUESTION_CHARS",
    )
    assistant_max_tool_rounds: int = Field(
        default=3,
        alias="ASSISTANT_MAX_TOOL_ROUNDS",
    )
    embedding_provider: str = Field(default="local", alias="EMBEDDING_PROVIDER")
    embedding_model: str = Field(
        default="arthadrishti-keyword-hashing-v1",
        alias="EMBEDDING_MODEL",
    )
    embedding_dimensions: int = Field(default=16, alias="EMBEDDING_DIMENSIONS")
    rag_chunk_size_chars: int = Field(default=1200, alias="RAG_CHUNK_SIZE_CHARS")
    rag_chunk_overlap_chars: int = Field(default=200, alias="RAG_CHUNK_OVERLAP_CHARS")
    rag_retrieval_min_score: float = Field(default=0.15, alias="RAG_RETRIEVAL_MIN_SCORE")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    @property
    def frontend_origins(self) -> list[str]:
        return [
            origin.strip()
            for origin in self.frontend_origin.split(",")
            if origin.strip()
        ]

    @model_validator(mode="after")
    def validate_production_settings(self) -> "Settings":
        if self.app_env.casefold() != "production":
            return self

        errors = []
        if self.debug:
            errors.append("DEBUG must be false in production")
        if len(self.jwt_secret_key) < 32 or self.jwt_secret_key == "replace-with-a-long-random-secret":
            errors.append("JWT_SECRET_KEY must be a strong production secret")
        if "*" in self.frontend_origins:
            errors.append("FRONTEND_ORIGIN must not use '*' in production")
        try:
            database_url = make_url(self.database_url)
            if not database_url.drivername.startswith("postgresql"):
                errors.append("DATABASE_URL must use PostgreSQL in production")
        except Exception:
            errors.append("DATABASE_URL must be a valid SQLAlchemy database URL")
        if errors:
            raise ValueError("; ".join(errors))
        return self

    @property
    def allowed_mime_types(self) -> set[str]:
        return {
            mime_type.strip()
            for mime_type in self.allowed_document_mime_types.split(",")
            if mime_type.strip()
        }

    @property
    def max_upload_size_bytes(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024

    @property
    def resolved_document_storage_path(self) -> Path:
        path = Path(self.document_storage_path)
        if path.is_absolute():
            return path.resolve()
        return (Path.cwd() / path).resolve()


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
