from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


def _api_diff_limit() -> int:
    explicit = os.getenv("API_MAX_DIFF_CHARS")
    if explicit is not None:
        return int(explicit)
    try:
        from .services.pipeline_adapter import configured_api_diff_limit

        return configured_api_diff_limit()
    except (ImportError, ModuleNotFoundError):
        return 40_000


def _sqlite_path(database_url: str) -> Path:
    if database_url.startswith("sqlite:///./"):
        return Path(database_url.removeprefix("sqlite:///./"))
    if database_url.startswith("sqlite:////"):
        return Path(database_url.removeprefix("sqlite:///"))
    if database_url.startswith("sqlite:///"):
        return Path(database_url.removeprefix("sqlite:///"))
    return Path(database_url)


@dataclass(frozen=True)
class Settings:
    database_url: str = "sqlite:///./data/reviews.sqlite3"
    database_path: Path = Path("data/reviews.sqlite3")
    cors_origins: tuple[str, ...] = (
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    )
    api_max_diff_chars: int = 40_000
    reviews_per_hour: int = 10
    max_active_reviews_per_token: int = 3
    worker_concurrency: int = 1
    review_timeout_s: int = 1200
    retention_days: int = 30
    ollama_base_url: str = "http://localhost:11434"
    model: str = "qwen2.5-coder:14b"
    fake_pipeline: bool = False
    log_max_records: int = 500
    request_body_limit_bytes: int = 1_000_000

    @classmethod
    def from_env(cls) -> Settings:
        database_url = os.getenv("DATABASE_URL", "sqlite:///./data/reviews.sqlite3")
        origins = tuple(
            origin.strip()
            for origin in os.getenv(
                "CORS_ORIGINS",
                "http://localhost:5173,http://127.0.0.1:5173",
            ).split(",")
            if origin.strip()
        )
        return cls(
            database_url=database_url,
            database_path=_sqlite_path(database_url),
            cors_origins=origins,
            api_max_diff_chars=_api_diff_limit(),
            reviews_per_hour=int(os.getenv("REVIEWS_PER_HOUR", "10")),
            max_active_reviews_per_token=int(os.getenv("MAX_ACTIVE_REVIEWS_PER_TOKEN", "3")),
            worker_concurrency=int(os.getenv("WORKER_CONCURRENCY", "1")),
            review_timeout_s=int(os.getenv("REVIEW_TIMEOUT_S", "1200")),
            retention_days=int(os.getenv("RETENTION_DAYS", "30")),
            ollama_base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
            model=os.getenv("OLLAMA_MODEL", os.getenv("MODEL", "qwen2.5-coder:14b")),
            fake_pipeline=os.getenv("SENTINEL_FAKE_PIPELINE", "false").lower()
            in {"1", "true", "yes", "on"},
            log_max_records=max(1, int(os.getenv("LOG_MAX_RECORDS", "500"))),
            request_body_limit_bytes=max(
                65_536,
                int(os.getenv("REQUEST_BODY_LIMIT_BYTES", "1000000")),
            ),
        )
