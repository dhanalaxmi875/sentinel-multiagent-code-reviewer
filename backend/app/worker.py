from __future__ import annotations

import asyncio
import json
import logging
import time
from datetime import UTC, datetime
from typing import Any

from .config import Settings
from .repository import Repository
from .services.pipeline_adapter import PipelineAdapter, _count_agent_findings

logger = logging.getLogger("sentinel.backend.worker")
_AGENT_NAMES = ("bug_detector", "security", "code_quality", "test_coverage")


class WorkerManager:
    def __init__(
        self,
        repository: Repository,
        adapter: PipelineAdapter,
        settings: Settings,
    ):
        self.repository = repository
        self.adapter = adapter
        self.settings = settings
        self.stop_event = asyncio.Event()
        self.tasks: list[asyncio.Task[None]] = []
        self.worker_tasks: list[asyncio.Task[None]] = []

    @property
    def alive(self) -> bool:
        return bool(self.worker_tasks) and any(not task.done() for task in self.worker_tasks)

    async def start(self) -> None:
        self.stop_event.clear()
        count = max(1, self.settings.worker_concurrency)
        self.worker_tasks = [
            asyncio.create_task(self._worker_loop(index), name=f"sentinel-worker-{index}")
            for index in range(count)
        ]
        self.tasks = list(self.worker_tasks)
        if self.settings.retention_days > 0:
            self.tasks.append(
                asyncio.create_task(self._retention_loop(), name="sentinel-retention")
            )

    async def stop(self) -> None:
        self.stop_event.set()
        if self.tasks:
            await asyncio.gather(*self.tasks, return_exceptions=True)
        self.tasks.clear()
        self.worker_tasks.clear()

    async def _worker_loop(self, worker_index: int) -> None:
        logger.info("Review worker %s started", worker_index)
        while not self.stop_event.is_set():
            try:
                job = await asyncio.to_thread(self.repository.claim_next)
                if job is None:
                    try:
                        await asyncio.wait_for(self.stop_event.wait(), timeout=0.25)
                    except TimeoutError:
                        pass
                    continue
                await self._process(job)
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("Worker loop recovered from an unexpected job error")
        logger.info("Review worker %s stopped", worker_index)

    async def _process(self, job: dict[str, Any]) -> None:
        review_id = str(job["id"])
        started = time.monotonic()
        abandoned = False

        def add_log(ts: str, level: str, message: str) -> None:
            if not abandoned:
                self.repository.add_log(review_id, ts, level, message)

        def node_event(event: dict[str, Any]) -> None:
            if abandoned:
                return
            name = str(event.get("node", ""))
            agent = "semgrep" if name == "semgrep_scanner" else name
            if event.get("event") == "start":
                self.repository.set_agent(review_id, agent, "running")
                add_log(datetime.now(UTC).isoformat(), "INFO", f"{name} started.")
                return
            if event.get("event") != "end":
                return

            output = event.get("output") or {}
            if name == "orchestrator" and event.get("status") == "done":
                active = set(output.get("active_agents", []))
                for specialist in _AGENT_NAMES:
                    self.repository.set_agent(
                        review_id,
                        specialist,
                        "running" if specialist in active else "skipped",
                    )
                self.repository.set_agent(review_id, "semgrep", "running")

            self.repository.set_agent(
                review_id,
                agent,
                str(event.get("status", "done")),
                float(event.get("duration_s", 0.0)),
                int(
                    event.get(
                        "finding_count",
                        _count_agent_findings(name, output),
                    )
                ),
            )
            add_log(
                datetime.now(UTC).isoformat(),
                "INFO" if event.get("status") == "done" else "ERROR",
                f"{name} {event.get('status', 'done')} in "
                f"{float(event.get('duration_s', 0.0)):.3f}s.",
            )

        add_log(iso_now(), "INFO", "Review worker started pipeline execution.")
        task = asyncio.create_task(
            asyncio.to_thread(
                self.adapter.run,
                review_id=review_id,
                diff_text=str(job["diff_text"]),
                file_paths=list(json.loads(job["file_paths"])),
                node_callback=node_event,
                log_callback=add_log,
            )
        )
        try:
            done, _ = await asyncio.wait({task}, timeout=self.settings.review_timeout_s)
            if not done:
                abandoned = True
                message = f"Review timed out after {self.settings.review_timeout_s} seconds."
                await asyncio.to_thread(self.repository.set_review_error, review_id, message)
                await asyncio.to_thread(
                    self.repository.add_log,
                    review_id,
                    iso_now(),
                    "ERROR",
                    message,
                )
                logger.error("Review %s exceeded its timeout", review_id)
                # Python cannot stop an in-flight thread safely; keep this worker
                # slot occupied until it exits so Ollama work is never overlapped.
                try:
                    await task
                except Exception:
                    logger.exception("Timed out pipeline later raised for review %s", review_id)
                return

            outcome = task.result()
            duration_s = time.monotonic() - started
            await asyncio.to_thread(
                self.repository.complete_review,
                review_id,
                outcome.report_md,
                outcome.verdict,
                duration_s,
                outcome.findings,
                outcome.is_demo,
                outcome.is_replay,
            )
            await asyncio.to_thread(
                self.repository.add_log,
                review_id,
                iso_now(),
                "INFO",
                "Review completed successfully.",
            )
        except asyncio.CancelledError:
            # Lifespan shutdown does not cancel active workers; this protects
            # callers that explicitly cancel a manager task.
            abandoned = True
            try:
                await asyncio.shield(task)
            except Exception:
                logger.exception("Pipeline raised during worker cancellation")
            raise
        except Exception as error:
            message = _pipeline_error_message(error, self.settings)
            logger.exception("Review %s failed", review_id)
            try:
                await asyncio.to_thread(self.repository.set_review_error, review_id, message)
                await asyncio.to_thread(
                    self.repository.add_log,
                    review_id,
                    iso_now(),
                    "ERROR",
                    message,
                )
            except Exception:
                logger.exception("Could not persist failure state for review %s", review_id)

    async def _retention_loop(self) -> None:
        while not self.stop_event.is_set():
            try:
                await asyncio.wait_for(self.stop_event.wait(), timeout=24 * 60 * 60)
            except TimeoutError:
                await asyncio.to_thread(self.repository.purge_expired)


def iso_now() -> str:
    return datetime.now(UTC).isoformat()


def _pipeline_error_message(error: Exception, settings: Settings) -> str:
    message = str(error)
    lowered = message.lower()
    if any(
        term in lowered
        for term in ("connection refused", "connecterror", "failed to connect", "connection error")
    ):
        return (
            f"Ollama is unreachable at {settings.ollama_base_url}. "
            "Start Ollama and verify OLLAMA_BASE_URL."
        )
    if "model" in lowered and any(
        term in lowered for term in ("not found", "does not exist", "pull")
    ):
        return f"Ollama model '{settings.model}' is unavailable. Pull the model and verify MODEL."
    return f"Review failed: {message or error.__class__.__name__}"
