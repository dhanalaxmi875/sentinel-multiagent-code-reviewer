# SentinelCode API backend

FastAPI service for the existing SentinelCode review UI. The backend imports the pipeline from the repository's `src/` package directly; it does not copy the pipeline or start a subprocess. Submitted diffs are kept as text and passed to the review pipeline. They are never imported, evaluated, or executed by the API.

## Requirements and setup

- Python 3.11 or newer
- Ollama with the configured model for real reviews
- Semgrep on `PATH` for Semgrep results (the pipeline continues if it is unavailable)

From the repository root:

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
python -m pip install -r backend/requirements.txt
cp backend/.env.example backend/.env
cd backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

On Windows PowerShell, copy the example with `Copy-Item .env.example .env`. The service loads `.env` through the existing project dotenv setup. The default database is `backend/data/reviews.sqlite3`; the directory and versioned schema are created at startup. SQLite runs in WAL mode with foreign keys and a busy timeout. Startup marks interrupted `running` jobs failed and resumes persisted `queued` jobs.

## Environment

| Variable | Default | Purpose |
| --- | --- | --- |
| `DATABASE_URL` | `sqlite:///./data/reviews.sqlite3` | SQLite file URL or path; relative paths resolve from `backend/`. |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama server URL used by the existing pipeline. |
| `MODEL` | `qwen2.5-coder:14b` | Model used by the existing pipeline; `OLLAMA_MODEL` remains supported and takes precedence for compatibility. |
| `CORS_ORIGINS` | `http://localhost:5173,http://127.0.0.1:5173` | Comma-separated browser origins. |
| `API_MAX_DIFF_CHARS` | `40000` | HTTP submission limit. Separate from the pre-existing `MAX_DIFF_CHARS` chunker setting. |
| `MAX_DIFF_CHARS` | `12000` | Existing pipeline chunker limit; unchanged by this backend. |
| `REVIEWS_PER_HOUR` | `10` | Maximum created reviews per client token per rolling hour. |
| `MAX_ACTIVE_REVIEWS_PER_TOKEN` | `3` | Maximum queued or running jobs per token. |
| `WORKER_CONCURRENCY` | `1` | Number of FIFO queue workers. Ollama is normally served sequentially. |
| `REVIEW_TIMEOUT_S` | `1200` | Per-review timeout. A running Python thread cannot be safely killed, so the review is marked failed at the deadline and that worker slot stays occupied until the pipeline call exits. |
| `RETENTION_DAYS` | `30` | Delete reviews and related records after this many days. Set to `0` to disable purge. |
| `SENTINEL_FAKE_PIPELINE` | `false` | Use deterministic UI/test data without calling Ollama. All such reviews are stored and returned with `is_demo=true`. |
| `LOG_MAX_RECORDS` | `500` | Maximum captured pipeline log records per review; character capture is also capped and truncation is reported explicitly. |
| `REQUEST_BODY_LIMIT_BYTES` | `1000000` | Maximum raw HTTP request body size. |

Example fake-mode run:

```bash
SENTINEL_FAKE_PIPELINE=true python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

## API

Every request except `GET /api/health` and `GET /api/samples` requires `X-Client-Token` containing a UUID. Reviews, stats, limits, and deduplication are scoped to that token. A foreign review ID returns 404.

| Method | Endpoint | Success response | Notes |
| --- | --- | --- | --- |
| `GET` | `/api/health` | `{ok, db, ollama_reachable, model_available, semgrep_available, worker_alive, queue_depth}` | Dependency and queue health; no client token. |
| `GET` | `/api/samples` | `[{id,name,description,diff_text,file_paths}]` | The banking API sample is the actual diff from `examples/sample_diff.py`. No sample findings/results are fabricated. |
| `POST` | `/api/reviews` | `202 {id,status:"queued"}` | Body: `{diff_text,file_paths?,source?,force?}`. Validation failures are 422. A finished same-token SHA-256 duplicate returns the existing `{id,status:"done"}` with 200; `force:true` bypasses the cache. Rate limits return 429 and `Retry-After`. |
| `GET` | `/api/reviews` | `[{id,status,verdict,finding_counts,created_at,duration_s}]` | Newest first; accepts `limit` (1–100) and `offset`. Counts include kept findings only. |
| `GET` | `/api/reviews/{id}` | Review detail | Includes pipeline status/timing, findings, report, diff, logs, and additive `is_demo` / `is_replay` flags. |
| `DELETE` | `/api/reviews/{id}` | `204 No Content` | Cascades to findings, agent runs, and review logs. |
| `GET` | `/api/stats` | `{total_reviews,finding_counts,verdict_split,avg_review_time_s}` | Per-token user-facing counts only. No evaluation or benchmark metrics. |

Errors use `{ "error": { "code": "...", "message": "..." } }`. Submitted diffs must be non-empty unified diffs with file headers and a hunk, contain no NUL byte, and fit the configured character limit. The single background worker claims persisted jobs FIFO, writes measured graph-node wall times and review-scoped pipeline logs, and continues after a job fails. An opt-in graph callback records the Orchestrator's selected agents and marks unselected agents skipped; it is disabled for the normal CLI path.

## Database schema and migrations

`app/migrations/001_initial.sql` is migration version 1. `schema_migrations` records applied versions. The schema contains:

- `reviews`: UUID, owner token, SHA-256 hash, diff text, file paths, source, status/verdict/report/error, demo/replay flags, timestamps, and duration.
- `findings`: structured kept/rejected findings, with `source` from `src/structured_findings.py` mapped to API `sources`.
- `agent_runs`: agent state, measured duration, and finding count.
- `review_logs`: timestamped level/message records, captured for the active review context and deleted with that review.

Indexes cover `(client_token, created_at)`, `(client_token, diff_hash)`, queue status, and review child lookups. SQLite foreign keys are enabled per connection.

## Development and tests

From `backend/`:

```bash
python -m pytest
ruff check app tests
mypy app
```

The default pytest config excludes the real-model `slow` test. Run that check explicitly with `python -m pytest -m slow`; it skips if the configured Ollama model is unavailable. Unit/API tests use a mocked pipeline or the explicit fake adapter and a temporary SQLite file.

## Troubleshooting

- **Ollama unreachable:** start Ollama and confirm `OLLAMA_BASE_URL`. `/api/health` reports reachability; failed review details explain connection failures.
- **Model unavailable:** pull the model named by `MODEL` (or `OLLAMA_MODEL`) and check `/api/health`'s `model_available` field.
- **Semgrep unavailable:** install Semgrep and put it on `PATH`. Health reports it as unavailable, and the review log records that scanning continued without results.
- **CORS error in Vite:** add the exact frontend origin to `CORS_ORIGINS`, then restart the backend.
- **429 response:** honor `Retry-After`; active-review limits and rolling hourly limits are independent and scoped to the client UUID.
- **Review says it was interrupted:** the previous server stopped while the job was running. Queued jobs resume automatically; in-progress local model calls cannot be resumed safely.
- **Slow or timed out review:** local model inference can take minutes. Increase `REVIEW_TIMEOUT_S` if appropriate and check Ollama health. A timed-out thread is allowed to exit before its worker starts another pipeline call.
- **SQLite lock:** use a local writable disk and keep `DATABASE_URL` pointing to one SQLite file. WAL and a 10-second busy timeout are enabled.

## Scope and verification notes

The backend's real Ollama, GPU timing, and installed Semgrep behavior depend on the host environment. The fake adapter exists for UI/test development only and its records carry `is_demo=true`. No recorded-result replay is shipped.

