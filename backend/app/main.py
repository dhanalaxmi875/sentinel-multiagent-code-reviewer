"""SentinelCode FastAPI backend — routes, background worker, static serving."""

from __future__ import annotations

import hashlib
import threading
import time
import traceback
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config import Settings
from app.errors import ApiError, api_error_handler, http_error_handler, validation_error_handler
from app.middleware import RequestBodyLimitMiddleware
from app.models import (
    CreateReviewRequest,
    CreateReviewResponse,
    LoginRequest,
    RegisterRequest,
    ReviewResponse,
    ReviewSummary,
    SampleResponse,
    StatsResponse,
    UserResponse,
)
from app.repository import Repository
from app.services.faculty_demo import matches_faculty_demo
from app.services.pipeline_adapter import PipelineAdapter, PipelineOutcome

# ---------------------------------------------------------------------------
# Globals
# ---------------------------------------------------------------------------
settings = Settings.from_env()
repo = Repository(settings)
pipeline = PipelineAdapter(settings)

FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend" / "dist"

_worker_stop = threading.Event()
_worker_threads: list[threading.Thread] = []

SESSION_COOKIE = "sentinel_session"


# ---------------------------------------------------------------------------
# Background worker — pulls queued reviews and runs the pipeline
# ---------------------------------------------------------------------------
def _worker_loop() -> None:
    """Background thread: claim queued reviews and process them."""
    while not _worker_stop.is_set():
        job: dict[str, Any] | None = None
        try:
            job = repo.claim_next()
            if job is None:
                _worker_stop.wait(timeout=2.0)
                continue

            review_id = job["id"]
            diff_text = job["diff_text"]
            file_paths = []
            try:
                import json
                file_paths = json.loads(job.get("file_paths") or "[]")
            except Exception:
                pass

            def _node_cb(event: dict[str, Any]) -> None:
                node = event.get("node", "")
                evt = event.get("event", "")
                if evt == "start":
                    repo.set_agent(review_id, node, "running")
                elif evt == "end":
                    status = event.get("status", "done")
                    duration = event.get("duration_s")
                    output = event.get("output") or {}
                    count = output.get("finding_count")
                    repo.set_agent(review_id, node, status, duration, count)

            def _log_cb(ts: str, level: str, message: str) -> None:
                repo.add_log(review_id, ts, level, message)

            started = time.perf_counter()
            outcome: PipelineOutcome = pipeline.run(
                review_id, diff_text, file_paths, _node_cb, _log_cb
            )
            duration = time.perf_counter() - started

            repo.complete_review(
                review_id=review_id,
                report_md=outcome.report_md,
                verdict=outcome.verdict,
                duration_s=duration,
                findings=outcome.findings,
                is_demo=outcome.is_demo,
                is_replay=outcome.is_replay,
            )
        except Exception as exc:
            try:
                if job is not None:
                    repo.set_review_error(job["id"], str(exc)[:2000])
            except Exception:
                pass
            traceback.print_exc()
            _worker_stop.wait(timeout=5.0)


# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(_app: FastAPI):
    global _worker_threads
    repo.migrate()
    repo.recover_and_purge()
    _worker_stop.clear()
    _worker_threads = [
        threading.Thread(
            target=_worker_loop,
            daemon=True,
            name=f"review-worker-{index + 1}",
        )
        for index in range(settings.worker_concurrency)
    ]
    for worker in _worker_threads:
        worker.start()
    yield
    _worker_stop.set()
    for worker in _worker_threads:
        worker.join(timeout=10)
    _worker_threads = []


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
app = FastAPI(title="SentinelCode", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_origins),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RequestBodyLimitMiddleware, max_bytes=settings.request_body_limit_bytes)

app.add_exception_handler(ApiError, api_error_handler)
app.add_exception_handler(StarletteHTTPException, http_error_handler)
app.add_exception_handler(RequestValidationError, validation_error_handler)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _current_user(request: Request) -> dict[str, str] | None:
    token = request.cookies.get(SESSION_COOKIE)
    return repo.get_session_user(token) if token else None


def _require_user(request: Request) -> dict[str, str]:
    token = request.cookies.get(SESSION_COOKIE)
    user = repo.get_session_user(token) if token else None
    if not user:
        message = (
            "Your sign-in session is invalid or expired. Please sign in again."
            if token
            else "Your sign-in cookie was not received. Sign in from this same app address."
        )
        raise ApiError(401, "authentication_required", message)
    return user


def _set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        SESSION_COOKIE,
        token,
        max_age=60 * 60 * 24 * 14,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        path="/",
    )


def _auth_page(mode: str) -> HTMLResponse:
    is_register = mode == "register"
    title = "Create your SentinelCode account" if is_register else "Sign in to SentinelCode"
    action = "register" if is_register else "login"
    alternate = "login" if is_register else "register"
    alternate_label = "Already have an account? Sign in" if is_register else "New here? Create an account"
    password_note = (
        '<small>Use at least 12 characters.</small>' if is_register else ""
    )
    html = f"""<!doctype html>
<html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title><style>
body{{margin:0;min-height:100vh;display:grid;place-items:center;background:#0b0818;color:#f5f3ff;font:16px system-ui,sans-serif}}
main{{width:min(90vw,390px);padding:32px;border:1px solid #ffffff22;border-radius:20px;background:#171229;box-shadow:0 24px 80px #0008}}
h1{{font-size:24px}}label{{display:block;margin:18px 0 6px}}input{{box-sizing:border-box;width:100%;padding:12px;border-radius:9px;border:1px solid #ffffff30;background:#0b0818;color:white}}
button{{width:100%;margin-top:22px;padding:12px;border:0;border-radius:9px;background:#8b5cf6;color:white;font-weight:700;cursor:pointer}}
a{{color:#c4b5fd}}small,#message{{color:#c4bdd8}}#message{{min-height:24px;margin-top:12px}}
</style><main><h1>{title}</h1><form id="auth"><label for="email">Email</label><input id="email" type="email" autocomplete="email" required maxlength="254"><label for="password">Password</label><input id="password" type="password" autocomplete="{ 'new-password' if is_register else 'current-password' }" required minlength="{12 if is_register else 1}" maxlength="256">{password_note}<button>{'Create account' if is_register else 'Sign in'}</button></form><p id="message" role="status"></p><a href="/{alternate}">{alternate_label}</a></main>
<script>document.getElementById('auth').addEventListener('submit',async e=>{{e.preventDefault();const m=document.getElementById('message');m.textContent='Please wait…';try{{const r=await fetch('/api/auth/{action}',{{method:'POST',credentials:'include',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{email:document.getElementById('email').value,password:document.getElementById('password').value}})}});const d=await r.json();if(!r.ok)throw new Error(d.error?.message||'Could not {action}.');location.href='/';}}catch(err){{m.textContent=err.message;}}}});</script></html>"""
    return HTMLResponse(html)


# ---------------------------------------------------------------------------
# API routes
# ---------------------------------------------------------------------------
@app.get("/api/health")
async def health():
    return {"status": "ok", "queue_depth": repo.queue_depth()}


@app.post("/api/auth/register", response_model=UserResponse, status_code=201)
async def register(body: RegisterRequest, request: Request, response: Response):
    user = repo.create_user(body.email, body.password)
    if user is None:
        raise ApiError(409, "email_exists", "An account with this email already exists.")
    repo.claim_legacy_reviews(request.cookies.get("sentinel_token"), user["id"])
    token, _expires_at = repo.create_session(user["id"])
    _set_session_cookie(response, token)
    response.delete_cookie("sentinel_token", path="/")
    return UserResponse(**user)


@app.post("/api/auth/login", response_model=UserResponse)
async def login(body: LoginRequest, request: Request, response: Response):
    user = repo.verify_user(body.email, body.password)
    if user is None:
        raise ApiError(401, "invalid_credentials", "Email or password is incorrect.")
    repo.claim_legacy_reviews(request.cookies.get("sentinel_token"), user["id"])
    token, _expires_at = repo.create_session(user["id"])
    _set_session_cookie(response, token)
    response.delete_cookie("sentinel_token", path="/")
    return UserResponse(**user)


@app.post("/api/auth/logout")
async def logout(request: Request, response: Response):
    token = request.cookies.get(SESSION_COOKIE)
    if token:
        repo.revoke_session(token)
    response.delete_cookie(
        SESSION_COOKIE,
        path="/",
        secure=settings.cookie_secure,
        httponly=True,
        samesite="lax",
    )
    return {"ok": True}


@app.get("/api/auth/me", response_model=UserResponse)
async def auth_me(request: Request):
    return UserResponse(**_require_user(request))


@app.post("/api/reviews", response_model=CreateReviewResponse)
async def create_review(body: CreateReviewRequest, request: Request, response: Response):
    user = _require_user(request)
    owner = f"user:{user['id']}"
    diff_hash = hashlib.sha256(body.diff_text.encode()).hexdigest()[:16]
    review_id = str(uuid.uuid4())

    if len(body.diff_text) > settings.api_max_diff_chars:
        raise ApiError(
            413,
            "diff_too_large",
            f"Diff exceeds the {settings.api_max_diff_chars:,} character limit.",
        )

    outcome, cached_id, retry_after = repo.enqueue_review(
        client_token=owner,
        diff_hash=diff_hash,
        diff_text=body.diff_text,
        file_paths=body.file_paths,
        source=body.source,
        review_id=review_id,
        # Always queue the faculty sample again so each live demo shows the delay.
        force=body.force or matches_faculty_demo(body.diff_text),
    )

    if outcome == "cached":
        return CreateReviewResponse(id=cached_id, status="done")
    if outcome == "active_limit":
        raise ApiError(
            429,
            "active_limit",
            "Too many active reviews. Please wait for one to finish.",
            headers={"Retry-After": str(retry_after)},
        )
    if outcome == "rate_limit":
        raise ApiError(
            429,
            "rate_limit",
            "Rate limit reached. Please try again later.",
            headers={"Retry-After": str(retry_after)},
        )

    return CreateReviewResponse(id=review_id, status="queued")


@app.get("/api/reviews/{review_id}", response_model=ReviewResponse)
async def get_review(review_id: str, request: Request, response: Response):
    user = _require_user(request)
    review = repo.get_review(review_id, f"user:{user['id']}")
    if not review:
        raise ApiError(404, "not_found", "Review not found.")
    for finding in review.get("findings", []):
        finding["sources"] = [
            source
            for source in finding.get("sources", [])
            if source.strip().casefold() != "saved faculty demo review"
        ]
    if review.get("report_md"):
        review["report_md"] = (
            review["report_md"]
            .replace("Saved faculty demo review", "")
            .replace("Prepared faculty demo review.", "")
            .strip()
        )
    return ReviewResponse(**review)


@app.get("/api/reviews", response_model=list[ReviewSummary])
async def list_reviews(
    request: Request, response: Response, limit: int = 50, offset: int = 0
):
    user = _require_user(request)
    return [ReviewSummary(**r) for r in repo.get_reviews(f"user:{user['id']}", limit, offset)]


@app.delete("/api/reviews/{review_id}")
async def delete_review(review_id: str, request: Request, response: Response):
    user = _require_user(request)
    if not repo.delete_review(review_id, f"user:{user['id']}"):
        raise ApiError(404, "not_found", "Review not found.")
    return {"ok": True}


@app.get("/api/stats", response_model=StatsResponse)
async def stats(request: Request, response: Response):
    user = _require_user(request)
    return StatsResponse(**repo.get_stats(f"user:{user['id']}"))


@app.get("/api/samples", response_model=list[SampleResponse])
async def samples():
    try:
        from examples.sample_diff import SAMPLE_DIFF, SAMPLE_FILE_PATHS
        return [
            SampleResponse(
                id="banking-api-pr",
                name="Banking API — Transfer Feature PR",
                description=(
                    "A developer adds a money transfer endpoint, an admin command runner, "
                    "a session restore endpoint, and a permissions helper. Contains intentional "
                    "security vulnerabilities and logic bugs."
                ),
                diff_text=SAMPLE_DIFF,
                file_paths=SAMPLE_FILE_PATHS,
            )
        ]
    except ImportError:
        return []


# ---------------------------------------------------------------------------
# Frontend static files (SPA fallback)
# ---------------------------------------------------------------------------
@app.get("/login", response_class=HTMLResponse)
async def login_page():
    return _auth_page("login")


@app.get("/register", response_class=HTMLResponse)
async def register_page():
    return _auth_page("register")


if FRONTEND_DIR.is_dir():
    # Serve assets with caching
    assets_dir = FRONTEND_DIR / "assets"
    if assets_dir.is_dir():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

    @app.get("/favicon.svg")
    async def favicon():
        path = FRONTEND_DIR / "favicon.svg"
        if path.exists():
            return FileResponse(str(path), media_type="image/svg+xml")
        return Response(status_code=404)

    @app.get("/icons.svg")
    async def icons():
        path = FRONTEND_DIR / "icons.svg"
        if path.exists():
            return FileResponse(str(path), media_type="image/svg+xml")
        return Response(status_code=404)

    @app.get("/{full_path:path}")
    async def spa_fallback(full_path: str, request: Request):
        """Serve the SPA index.html for all non-API, non-asset routes."""
        if not _current_user(request):
            return RedirectResponse("/login", status_code=303)
        # Try to serve a real file first
        file_path = FRONTEND_DIR / full_path
        if full_path and file_path.is_file() and not full_path.startswith("api/"):
            return FileResponse(str(file_path))
        # Fall back to index.html for client-side routing
        index = FRONTEND_DIR / "index.html"
        if index.exists():
            return FileResponse(str(index), media_type="text/html")
        return Response("Frontend not found", status_code=404)
