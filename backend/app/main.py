from __future__ import annotations

import asyncio
import hashlib
import logging
import shutil
import sys
from contextlib import asynccontextmanager, closing
from pathlib import Path
from typing import Annotated
from uuid import UUID, uuid4

import httpx
from fastapi import Depends, FastAPI, Header, Query, Response
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

from .config import Settings
from .errors import (
    ApiError,
    api_error_handler,
    http_error_handler,
    validation_error_handler,
)
from .middleware import RequestBodyLimitMiddleware
from .models import (
    CreateReviewRequest,
    CreateReviewResponse,
    ReviewResponse,
    ReviewSummary,
    SampleResponse,
    StatsResponse,
)
from .repository import Repository
from .services.pipeline_adapter import PipelineAdapter
from .worker import WorkerManager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("sentinel.backend")


def _client_token(
    value: Annotated[str | None, Header(alias="X-Client-Token")] = None,
) -> str:
    if not value:
        raise ApiError(401, "client_token_required", "X-Client-Token header is required.")
    try:
        return str(UUID(value))
    except (ValueError, AttributeError):
        raise ApiError(401, "invalid_client_token", "X-Client-Token must be a UUID.") from None


ClientToken = Annotated[str, Depends(_client_token)]


def _validate_diff(diff_text: str, max_chars: int) -> None:
    if not diff_text.strip():
        raise ApiError(422, "empty_diff", "diff_text must not be empty.")
    if "\x00" in diff_text:
        raise ApiError(422, "nul_byte", "diff_text must not contain NUL bytes.")
    if len(diff_text) > max_chars:
        raise ApiError(
            422,
            "diff_too_large",
            f"diff_text exceeds the configured maximum of {max_chars} characters.",
        )
    has_headers = "--- " in diff_text and "+++ " in diff_text
    has_hunk = "@@" in diff_text
    if not (has_headers and has_hunk):
        raise ApiError(
            422,
            "invalid_unified_diff",
            "diff_text must be a unified diff with file headers and at least one hunk.",
        )


def _check_ollama(settings: Settings) -> tuple[bool, bool]:
    try:
        response = httpx.get(f"{settings.ollama_base_url.rstrip('/')}/api/tags", timeout=2.0)
        response.raise_for_status()
        names = {
            str(item.get("name", ""))
            for item in response.json().get("models", [])
            if isinstance(item, dict)
        }
        model_available = settings.model in names or any(
            name.split(":", 1)[0] == settings.model.split(":", 1)[0] for name in names
        )
        return True, model_available
    except (httpx.HTTPError, ValueError, AttributeError):
        return False, False


def _semgrep_available() -> bool:
    if shutil.which("semgrep"):
        return True
    executable_dir = Path(sys.executable).parent
    return any(
        (executable_dir / name).is_file() for name in ("semgrep", "semgrep.exe", "semgrep.cmd")
    )


def create_app(
    settings: Settings | None = None,
    pipeline_adapter: PipelineAdapter | None = None,
) -> FastAPI:
    resolved_settings = settings or Settings.from_env()
    repository = Repository(resolved_settings)
    adapter = pipeline_adapter or PipelineAdapter(resolved_settings)

    @asynccontextmanager
    async def lifespan(application: FastAPI):
        repository.migrate()
        repository.recover_and_purge()
        manager = WorkerManager(repository, adapter, resolved_settings)
        application.state.repository = repository
        application.state.worker_manager = manager
        await manager.start()
        try:
            yield
        finally:
            await manager.stop()

    app = FastAPI(title="SentinelCode API", version="1.0.0", lifespan=lifespan)
    app.state.settings = resolved_settings
    app.state.repository = repository
    app.state.worker_manager = None
    app.add_middleware(
        RequestBodyLimitMiddleware,
        max_bytes=resolved_settings.request_body_limit_bytes,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(resolved_settings.cors_origins),
        allow_credentials=False,
        allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "X-Client-Token"],
    )
    app.add_exception_handler(ApiError, api_error_handler)
    app.add_exception_handler(StarletteHTTPException, http_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)

    @app.get("/api/health")
    async def health() -> dict[str, object]:
        try:
            with closing(repository.connect()) as connection, connection:
                connection.execute("SELECT 1").fetchone()
            db_ok = True
        except Exception:
            db_ok = False
            logger.exception("Health check could not read SQLite")
        ollama_reachable, model_available = await asyncio.to_thread(
            _check_ollama, resolved_settings
        )
        manager: WorkerManager | None = app.state.worker_manager
        return {
            "ok": db_ok,
            "db": db_ok,
            "ollama_reachable": ollama_reachable,
            "model_available": model_available,
            "semgrep_available": _semgrep_available(),
            "worker_alive": bool(manager and manager.alive),
            "queue_depth": repository.queue_depth() if db_ok else 0,
        }

    @app.get("/api/samples", response_model=list[SampleResponse])
    def samples() -> list[dict[str, object]]:
        from examples.sample_diff import SAMPLE_DIFF, SAMPLE_FILE_PATHS

        return [
            {
                "id": "banking-api",
                "name": "Banking API Demo",
                "description": "Built-in sample diff from examples/sample_diff.py.",
                "diff_text": SAMPLE_DIFF,
                "file_paths": SAMPLE_FILE_PATHS,
            }
        ]

    @app.post(
        "/api/reviews",
        response_model=CreateReviewResponse,
        status_code=202,
    )
    def create_review(
        body: CreateReviewRequest,
        response: Response,
        token: ClientToken,
    ) -> CreateReviewResponse:
        _validate_diff(body.diff_text, resolved_settings.api_max_diff_chars)
        diff_hash = hashlib.sha256(body.diff_text.encode("utf-8")).hexdigest()
        new_id = str(uuid4())
        result, review_id, retry_after = repository.enqueue_review(
            client_token=token,
            diff_hash=diff_hash,
            diff_text=body.diff_text,
            file_paths=body.file_paths,
            source=body.source,
            review_id=new_id,
            force=body.force,
            is_demo=resolved_settings.fake_pipeline,
        )
        if result == "active_limit":
            raise ApiError(
                429,
                "active_review_limit",
                "At most "
                f"{resolved_settings.max_active_reviews_per_token} reviews may be queued "
                "or running for this token.",
                {"Retry-After": str(retry_after)},
            )
        if result == "rate_limit":
            raise ApiError(
                429,
                "review_rate_limit",
                f"Review rate limit reached ({resolved_settings.reviews_per_hour} per hour).",
                {"Retry-After": str(retry_after)},
            )
        status = "done" if result == "cached" else "queued"
        if result == "cached":
            response.status_code = 200
        return CreateReviewResponse(id=review_id or new_id, status=status)

    @app.get("/api/reviews", response_model=list[ReviewSummary])
    def list_reviews(
        token: ClientToken,
        limit: int = Query(default=50, ge=1, le=100),
        offset: int = Query(default=0, ge=0),
    ) -> list[dict[str, object]]:
        return repository.get_reviews(token, limit, offset)

    @app.get("/api/reviews/{review_id}", response_model=ReviewResponse)
    def get_review(review_id: str, token: ClientToken) -> dict[str, object]:
        review = repository.get_review(review_id, token)
        if review is None:
            raise ApiError(404, "review_not_found", "Review not found.")
        return review

    @app.delete("/api/reviews/{review_id}", status_code=204)
    def delete_review(review_id: str, token: ClientToken) -> Response:
        if not repository.delete_review(review_id, token):
            raise ApiError(404, "review_not_found", "Review not found.")
        return Response(status_code=204)

    @app.get("/api/stats", response_model=StatsResponse)
    def stats(token: ClientToken) -> dict[str, object]:
        return repository.get_stats(token)

    return app


app = create_app()
