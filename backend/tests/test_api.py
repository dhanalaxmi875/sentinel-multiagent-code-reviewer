from __future__ import annotations

import sqlite3
import threading
import uuid
from dataclasses import replace
from typing import Any

import pytest
from backend.app.config import Settings
from backend.app.main import create_app
from backend.app.repository import Repository
from backend.app.services.pipeline_adapter import PipelineAdapter
from conftest import (
    FINDINGS,
    REPORT,
    VALID_DIFF,
    StubAdapter,
    SyncASGIClient,
    auth,
    wait_for_status,
)


def create(client: SyncASGIClient, token: str, diff: str = VALID_DIFF, **extra: Any):
    return client.post(
        "/api/reviews",
        headers=auth(token),
        json={"diff_text": diff, "file_paths": ["sample.py"], "source": "web", **extra},
    )


def test_client_token_required_and_validated(client_factory):
    with client_factory(StubAdapter()) as client:
        missing = client.get("/api/reviews")
        invalid = client.get("/api/stats", headers=auth("not-a-uuid"))
    assert missing.status_code == 401
    assert missing.json()["error"]["code"] == "client_token_required"
    assert invalid.status_code == 401
    assert invalid.json()["error"]["code"] == "invalid_client_token"


@pytest.mark.parametrize(
    ("diff", "message"),
    [
        ("", "must not be empty"),
        ("plain code", "unified diff"),
        (VALID_DIFF + "\x00", "NUL bytes"),
        (VALID_DIFF + "+" + "x" * 100, "maximum of 100"),
    ],
)
def test_diff_validation_errors(client_factory, diff: str, message: str):
    with client_factory(StubAdapter()) as client:
        response = create(client, str(uuid.uuid4()), diff)
    assert response.status_code == 422
    assert message in response.json()["error"]["message"]


def test_lifecycle_response_shape_and_agent_timings(client_factory):
    token = str(uuid.uuid4())
    started = threading.Event()
    release = threading.Event()
    adapter = StubAdapter(started=started, release=release)
    with client_factory(adapter) as client:
        queued = create(client, token)
        assert queued.status_code == 202
        assert queued.json()["status"] == "queued"
        assert started.wait(timeout=1)
        running = client.get(f"/api/reviews/{queued.json()['id']}", headers=auth(token)).json()
        assert running["status"] == "running"
        release.set()
        done = wait_for_status(client, queued.json()["id"], token, "done")

    assert done["verdict"] == "REQUEST_CHANGES"
    assert done["report_md"] == REPORT
    assert done["diff_text"] == VALID_DIFF
    assert done["agents"]
    assert all("duration_s" in agent and "finding_count" in agent for agent in done["agents"])
    assert done["findings"][0]["sources"] == ["Security Agent", "Semgrep"]
    assert any(log["message"] == "stub pipeline complete" for log in done["logs"])


def test_failure_does_not_kill_worker(client_factory):
    token = str(uuid.uuid4())
    adapter = StubAdapter(fail_first=True)
    with client_factory(adapter) as client:
        first = create(client, token)
        second = create(client, token, VALID_DIFF.replace("+new", "+other"))
        failed = wait_for_status(client, first.json()["id"], token, "failed")
        done = wait_for_status(client, second.json()["id"], token, "done")
    assert "intentional pipeline exception" in failed["error"]
    assert done["verdict"] == "REQUEST_CHANGES"
    assert adapter.calls == 2


def test_timeout_marks_review_failed(client_factory):
    token = str(uuid.uuid4())
    with client_factory(StubAdapter(delay_s=0.12), review_timeout_s=0.03) as client:
        response = create(client, token)
        failed = wait_for_status(client, response.json()["id"], token, "failed")
    assert "timed out after 0.03 seconds" in failed["error"]


def test_restart_recovery_marks_running_review_failed(settings: Settings):
    repository = Repository(settings)
    repository.migrate()
    token = str(uuid.uuid4())
    review_id = str(uuid.uuid4())
    repository.enqueue_review(
        client_token=token,
        diff_hash="abc",
        diff_text=VALID_DIFF,
        file_paths=[],
        source="web",
        review_id=review_id,
        force=False,
    )
    assert repository.claim_next() is not None
    with SyncASGIClient(create_app(settings, StubAdapter())) as client:
        response = client.get(f"/api/reviews/{review_id}", headers=auth(token))
    assert response.status_code == 200
    assert response.json()["status"] == "failed"
    assert response.json()["error"] == "interrupted by server restart"


def test_rate_limit_returns_retry_after(client_factory):
    token = str(uuid.uuid4())
    with client_factory(StubAdapter(), reviews_per_hour=1) as client:
        first = create(client, token)
        wait_for_status(client, first.json()["id"], token, "done")
        second = create(client, token, VALID_DIFF.replace("+new", "+different"))
    assert second.status_code == 429
    assert int(second.headers["Retry-After"]) > 0
    assert second.json()["error"]["code"] == "review_rate_limit"


def test_active_review_limit(client_factory):
    token = str(uuid.uuid4())
    started = threading.Event()
    release = threading.Event()
    with client_factory(
        StubAdapter(started=started, release=release), max_active_reviews_per_token=1
    ) as client:
        create(client, token)
        assert started.wait(timeout=1)
        second = create(client, token, VALID_DIFF.replace("+new", "+different"))
        release.set()
    assert second.status_code == 429
    assert second.json()["error"]["code"] == "active_review_limit"


def test_hash_cache_and_force(client_factory):
    token = str(uuid.uuid4())
    adapter = StubAdapter()
    with client_factory(adapter) as client:
        first = create(client, token)
        wait_for_status(client, first.json()["id"], token, "done")
        cached = create(client, token)
        forced = create(client, token, force=True)
        if forced.status_code == 202:
            wait_for_status(client, forced.json()["id"], token, "done")
    assert cached.status_code == 200
    assert cached.json() == {"id": first.json()["id"], "status": "done"}
    assert forced.status_code == 202
    assert forced.json()["id"] != first.json()["id"]
    assert adapter.calls == 2


def test_token_scoping_and_delete_cascade(client_factory, settings: Settings):
    token_a, token_b = str(uuid.uuid4()), str(uuid.uuid4())
    with client_factory(StubAdapter()) as client:
        created = create(client, token_a)
        review_id = created.json()["id"]
        wait_for_status(client, review_id, token_a, "done")
        foreign_read = client.get(f"/api/reviews/{review_id}", headers=auth(token_b))
        foreign_delete = client.delete(f"/api/reviews/{review_id}", headers=auth(token_b))
        deleted = client.delete(f"/api/reviews/{review_id}", headers=auth(token_a))

    assert foreign_read.status_code == 404
    assert foreign_delete.status_code == 404
    assert deleted.status_code == 204
    with sqlite3.connect(settings.database_path) as connection:
        for table in ("reviews", "findings", "agent_runs", "review_logs"):
            assert connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] == 0


def test_stats_are_scoped_and_count_only_kept_findings(client_factory):
    token = str(uuid.uuid4())
    findings = FINDINGS + [
        {
            **FINDINGS[0],
            "id": "f-rejected",
            "severity": "HIGH",
            "status": "rejected",
            "rejection_reason": "removed by verifier",
        }
    ]
    with client_factory(StubAdapter(findings=findings)) as client:
        first = create(client, token)
        wait_for_status(client, first.json()["id"], token, "done")
        stats = client.get("/api/stats", headers=auth(token)).json()
        other = client.get("/api/stats", headers=auth(str(uuid.uuid4()))).json()
    assert stats["total_reviews"] == 1
    assert stats["finding_counts"] == {"critical": 1, "high": 0, "medium": 0, "low": 0}
    assert stats["verdict_split"] == {"approve": 0, "request_changes": 1}
    assert stats["avg_review_time_s"] >= 0
    assert other["total_reviews"] == 0


def test_samples_endpoint_returns_real_built_in_diff(client_factory):
    with client_factory(StubAdapter()) as client:
        response = client.get("/api/samples")
    assert response.status_code == 200
    sample = response.json()[0]
    from examples.sample_diff import SAMPLE_DIFF

    assert sample["id"] == "banking-api"
    assert sample["diff_text"] == SAMPLE_DIFF


def test_health_endpoint(client_factory, monkeypatch):
    from backend.app import main

    monkeypatch.setattr(main, "_check_ollama", lambda _: (True, True))
    monkeypatch.setattr(main, "_semgrep_available", lambda: True)
    with client_factory(StubAdapter()) as client:
        response = client.get("/api/health")
    body = response.json()
    assert body == {
        "ok": True,
        "db": True,
        "ollama_reachable": True,
        "model_available": True,
        "semgrep_available": True,
        "worker_alive": True,
        "queue_depth": 0,
    }


def test_fake_pipeline_marks_results_as_demo(client_factory, settings: Settings):
    fake_settings = replace(settings, fake_pipeline=True, api_max_diff_chars=300)
    fake = PipelineAdapter(fake_settings)
    token = str(uuid.uuid4())
    diff = VALID_DIFF.replace(
        "+new", '+cursor.execute("SELECT * FROM users WHERE id = " + user_id)'
    )
    with SyncASGIClient(create_app(fake_settings, fake)) as client:
        response = create(client, token, diff)
        review = wait_for_status(client, response.json()["id"], token, "done")
    assert review["is_demo"] is True
    assert any(finding["status"] == "rejected" for finding in review["findings"])


@pytest.mark.slow
def test_real_pipeline_when_ollama_is_available(settings: Settings):
    from backend.app.main import _check_ollama, create_app

    settings = replace(settings, review_timeout_s=1200)
    reachable, model_available = _check_ollama(settings)
    if not (reachable and model_available):
        pytest.skip("Ollama is unavailable or configured model is not installed")
    token = str(uuid.uuid4())
    with SyncASGIClient(create_app(settings, PipelineAdapter(settings))) as client:
        created = create(client, token)
        assert created.status_code == 202
        completed = wait_for_status(client, created.json()["id"], token, "done")
    assert completed["report_md"]
