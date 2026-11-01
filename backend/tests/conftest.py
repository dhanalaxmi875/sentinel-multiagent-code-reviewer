from __future__ import annotations

import asyncio
import threading
import time
import uuid
from collections.abc import Callable
from pathlib import Path
from typing import Any

import httpx
import pytest
from backend.app.config import Settings
from backend.app.main import create_app
from backend.app.services.pipeline_adapter import PipelineOutcome
from fastapi import FastAPI


class SyncASGIClient:
    """Synchronous facade over httpx's async ASGI test transport."""

    def __init__(self, app: FastAPI):
        self.app = app
        self.loop = asyncio.new_event_loop()
        self.ready = threading.Event()
        self.lifespan = app.router.lifespan_context(app)
        self.async_client: httpx.AsyncClient | None = None

        def run_loop() -> None:
            asyncio.set_event_loop(self.loop)
            self.ready.set()
            self.loop.run_forever()
            self.loop.run_until_complete(self.loop.shutdown_asyncgens())

        self.thread = threading.Thread(target=run_loop, daemon=True)
        self.thread.start()
        self.ready.wait(timeout=2)
        self._run(self._start())

    async def _start(self) -> None:
        await self.lifespan.__aenter__()
        self.async_client = httpx.AsyncClient(
            transport=httpx.ASGITransport(app=self.app),
            base_url="http://testserver",
        )

    async def _close(self) -> None:
        if self.async_client is not None:
            await self.async_client.aclose()
        await self.lifespan.__aexit__(None, None, None)

    def _run(self, coroutine: Any) -> Any:
        future = asyncio.run_coroutine_threadsafe(coroutine, self.loop)
        return future.result(timeout=30)

    def get(self, url: str, **kwargs: Any) -> httpx.Response:
        assert self.async_client is not None
        return self._run(self.async_client.get(url, **kwargs))

    def post(self, url: str, **kwargs: Any) -> httpx.Response:
        assert self.async_client is not None
        return self._run(self.async_client.post(url, **kwargs))

    def delete(self, url: str, **kwargs: Any) -> httpx.Response:
        assert self.async_client is not None
        return self._run(self.async_client.delete(url, **kwargs))

    def __enter__(self) -> SyncASGIClient:
        return self

    def __exit__(self, exc_type: Any, exc: Any, traceback: Any) -> None:
        try:
            self._run(self._close())
        finally:
            self.loop.call_soon_threadsafe(self.loop.stop)
            self.thread.join(timeout=5)


VALID_DIFF = "--- a/sample.py\n+++ b/sample.py\n@@ -1 +1 @@\n-old\n+new\n"
REPORT = """## Code Review Summary

### Critical Issues (must fix before merge)
- **CRITICAL | HIGH** SQL injection in query
  - Evidence: cursor.execute(query + user_id)
  - Fix: Use query parameters.
  - Source: Security Agent

### Suggestions (should fix, improves quality)
None

### Rejected Findings
- Unsupported claim
  - Reason: No supporting code evidence.

### Verdict
**REQUEST CHANGES**"""
FINDINGS = [
    {
        "id": "f-1",
        "title": "SQL injection in query",
        "severity": "CRITICAL",
        "confidence": "HIGH",
        "cwe": "CWE-89",
        "file": "sample.py",
        "line": 1,
        "evidence": "cursor.execute(query + user_id)",
        "fix": "Use query parameters.",
        "sources": ["Security Agent", "Semgrep"],
        "status": "kept",
        "rejection_reason": None,
    }
]


class StubAdapter:
    def __init__(
        self,
        *,
        fail_first: bool = False,
        started: Any = None,
        release: Any = None,
        delay_s: float = 0,
        verdict: str = "REQUEST_CHANGES",
        findings: list[dict[str, Any]] | None = None,
    ):
        self.calls = 0
        self.fail_first = fail_first
        self.started = started
        self.release = release
        self.delay_s = delay_s
        self.verdict = verdict
        self.findings = findings if findings is not None else FINDINGS

    def run(
        self,
        *,
        review_id: str,
        diff_text: str,
        file_paths: list[str],
        node_callback: Callable[[dict[str, Any]], None],
        log_callback: Callable[[str, str, str], None],
    ) -> PipelineOutcome:
        del review_id, diff_text, file_paths
        self.calls += 1
        if self.fail_first and self.calls == 1:
            raise RuntimeError("intentional pipeline exception")
        if self.started is not None:
            self.started.set()
        if self.release is not None:
            self.release.wait(timeout=2)
        if self.delay_s:
            time.sleep(self.delay_s)
        nodes = (
            ("orchestrator", {"active_agents": ["security"]}, 0),
            ("security", {}, 1),
            ("semgrep_scanner", {}, 0),
            ("verifier", {}, 1),
            ("summarizer", {}, len(self.findings)),
        )
        for name, output, count in nodes:
            node_callback({"event": "start", "node": name})
            node_callback(
                {
                    "event": "end",
                    "node": name,
                    "status": "done",
                    "duration_s": 0.001,
                    "finding_count": count,
                    "output": output,
                }
            )
        log_callback("2026-01-01T00:00:00+00:00", "INFO", "stub pipeline complete")
        return PipelineOutcome(REPORT, self.verdict, self.findings)


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    database = tmp_path / "sentinel.sqlite3"
    return Settings(
        database_url=f"sqlite:///{database.as_posix()}",
        database_path=database,
        api_max_diff_chars=100,
        reviews_per_hour=10,
        max_active_reviews_per_token=3,
        worker_concurrency=1,
        review_timeout_s=2,
        retention_days=0,
        fake_pipeline=False,
        request_body_limit_bytes=1_000_000,
    )


@pytest.fixture
def client_factory(settings: Settings):
    def make(adapter: Any | None = None, **setting_changes: Any) -> SyncASGIClient:
        current = settings
        for name, value in setting_changes.items():
            object.__setattr__(current, name, value)
        app = create_app(current, adapter)
        return SyncASGIClient(app)

    return make


def auth(token: str | None = None) -> dict[str, str]:
    return {"X-Client-Token": token or str(uuid.uuid4())}


def wait_for_status(
    client: SyncASGIClient, review_id: str, token: str, target: str
) -> dict[str, Any]:
    deadline = time.monotonic() + 4
    last: dict[str, Any] = {}
    while time.monotonic() < deadline:
        response = client.get(f"/api/reviews/{review_id}", headers=auth(token))
        if response.status_code == 200:
            last = response.json()
            if last["status"] == target:
                return last
        time.sleep(0.02)
    raise AssertionError(f"review did not reach {target}: {last}")
