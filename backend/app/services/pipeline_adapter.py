from __future__ import annotations

import contextvars
import logging
import re
import shutil
import sys
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

from app.config import Settings
from app.services.faculty_demo import matches_faculty_demo, run_faculty_demo

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

_review_context: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "sentinel_review_id", default=None
)

NodeCallback = Callable[[dict[str, Any]], None]
LogCallback = Callable[[str, str, str], None]


def configured_api_diff_limit() -> int:
    """Return the additive API limit without changing pipeline chunking defaults."""
    from src.config import API_MAX_DIFF_CHARS

    return API_MAX_DIFF_CHARS


@dataclass(frozen=True)
class PipelineOutcome:
    report_md: str
    verdict: str | None
    findings: list[dict[str, Any]]
    is_demo: bool = False
    is_replay: bool = False


class _ReviewLogHandler(logging.Handler):
    def __init__(
        self, review_id: str, sink: LogCallback, max_records: int
    ) -> None:
        super().__init__(level=logging.INFO)
        self.review_id = review_id
        self.sink = sink
        self.max_records = max_records
        self.record_count = 0
        self.max_chars = 200_000
        self.char_count = 0
        self.truncated = False

    def emit(self, record: logging.LogRecord) -> None:
        if _review_context.get() != self.review_id:
            return
        if self.truncated:
            return
        if self.record_count >= self.max_records:
            self.truncated = True
            self.sink(
                datetime.now(UTC).isoformat(),
                "WARNING",
                (
                    f"Review log capture reached {self.max_records} records; "
                    "later records were not stored."
                ),
            )
            return

        message = record.getMessage()
        remaining = self.max_chars - self.char_count
        if remaining <= 0:
            self.truncated = True
            self.sink(
                datetime.now(UTC).isoformat(),
                "WARNING",
                (
                    f"Review log capture reached {self.max_chars} characters; "
                    "later records were not stored."
                ),
            )
            return
        if len(message) > remaining:
            message = message[:remaining] + " [message truncated by log capture limit]"
            self.truncated = True

        self.record_count += 1
        self.char_count += len(message)
        self.sink(
            datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            record.levelname,
            message,
        )


def _count_agent_findings(node: str, output: dict[str, Any]) -> int:
    if node == "summarizer":
        return len(output.get("structured_findings") or [])
    if node == "semgrep_scanner":
        text = str(output.get("semgrep_report") or "")
        return len(re.findall(r"(?m)^- Rule:", text))
    if node == "verifier":
        text = str(output.get("verified_report") or "")
        section = _extract_section(
            text, ("### Accepted", "### Critical Issues", "### Suggestions")
        )
        return len(
            re.findall(
                r"(?m)^\s*-\s*(?:\[|\*\*)?(?:CRITICAL|HIGH|MEDIUM|LOW)\b",
                section,
            )
        )
    if node in {"bug_detector", "security", "code_quality", "test_coverage"}:
        key = {
            "bug_detector": "bug_report",
            "security": "security_report",
            "code_quality": "quality_report",
            "test_coverage": "test_report",
        }[node]
        chunks = output.get(key) or []
        text = "\n".join(chunks) if isinstance(chunks, list) else str(chunks)
        if re.search(r"(?i)^\s*(?:no\s|test coverage appears sufficient)", text):
            return 0
        return len(re.findall(r"(?m)^\s*\d+[.)]\s+", text))
    return 0


def _extract_section(report: str, headings: tuple[str, ...]) -> str:
    lines = report.splitlines()
    start = next(
        (
            i
            for i, line in enumerate(lines)
            if any(line.strip().lower().startswith(h.lower()) for h in headings)
        ),
        None,
    )
    if start is None:
        return ""
    end = next(
        (
            i
            for i in range(start + 1, len(lines))
            if re.match(r"^#{2,3}\s", lines[i])
        ),
        len(lines),
    )
    return "\n".join(lines[start + 1 : end]).strip()


def _split_finding_blocks(section: str) -> list[str]:
    if re.fullmatch(r"(?is)\s*-?\s*none\.?\s*", section or ""):
        return []
    return [
        block.strip()
        for block in re.split(r"(?m)(?=^\s*-\s+)", section or "")
        if block.strip()
    ]


def _title_from_block(block: str) -> str:
    first = next((line for line in block.splitlines() if line.strip()), "")
    first = re.sub(r"^[-*]\s+", "", first)
    first = re.sub(
        r"^(?:\*\*)?(?:\[)?(?:CRITICAL|HIGH|MEDIUM|LOW)\s*\|\s*"
        r"(?:HIGH|MEDIUM|LOW)(?:\])?(?:\*\*)?\s*",
        "",
        first,
        flags=re.I,
    )
    return first.strip(" -\t")


def _field(block: str, names: str) -> str:
    match = re.search(
        rf"(?ims)^\s*(?:-\s*)?(?:{names})\s*:\s*(.*?)"
        r"(?=^\s*(?:-\s*)?(?:Evidence|Fix|Source|Reason|CWE|Severity|Confidence)\s*:|\Z)",
        block,
    )
    return match.group(1).strip() if match else ""


def _normalize(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def _similarity(left: str, right: str) -> float:
    a = _normalize(left)
    b = _normalize(right)
    if not a or not b:
        return 0.0
    ratio = SequenceMatcher(None, a, b).ratio()
    words_a = set(a.split())
    words_b = set(b.split())
    overlap = len(words_a & words_b) / max(len(words_a | words_b), 1)
    return max(ratio, overlap * 0.9)


def _normalize_severity(text: str, default: str = "LOW") -> str:
    match = re.search(r"\b(CRITICAL|HIGH|MEDIUM|LOW)\b", text or "", flags=re.I)
    return match.group(1).upper() if match else default


def _normalize_confidence(text: str, default: str = "LOW") -> str:
    match = re.search(r"\b(HIGH|MEDIUM|LOW)\b", text or "", flags=re.I)
    return match.group(1).upper() if match else default


def _candidate_findings(
    state: dict[str, Any], diff_text: str
) -> list[dict[str, Any]]:
    from src.structured_findings import (
        extract_file_and_line_from_diff,
        parse_diff_hunks,
    )

    diff_map = parse_diff_hunks(diff_text)
    reports = (
        ("bug_report", "Bug & Logic Detector"),
        ("security_report", "Security Agent"),
        ("quality_report", "Code Quality Agent"),
        ("test_report", "Test Coverage Agent"),
    )
    candidates: list[dict[str, Any]] = []
    for key, source in reports:
        content = "\n".join(state.get(key) or [])
        if re.search(
            r"(?i)no (?:logic|security|code quality) "
            r"(?:or |vulnerabilities|issues|correctness issues)",
            content,
        ):
            continue
        for block in re.split(r"(?m)(?=^\s*\d+[.)]\s+)", content):
            first = re.match(r"(?s)^\s*\d+[.)]\s+(.*)", block)
            if not first:
                continue
            body = first.group(1).strip()
            if re.search(r"(?i)(?:no issues|no vulnerabilities|appears sufficient)", body):
                continue
            title = re.sub(r"^\s*\d+[.)]\s+", "", body.splitlines()[0]).strip()[:500]
            severity = _normalize_severity(body, "MEDIUM")
            confidence = _normalize_confidence(body, "MEDIUM")
            evidence = _field(body, "Evidence|Code(?: snippet)?|Snippet|Line")
            fix = _field(body, "Fix|Suggested fix|Recommendation")
            file_path, line_number = extract_file_and_line_from_diff(
                evidence, title, diff_map
            )
            candidates.append(
                {
                    "title": title or _title_from_block(body),
                    "severity": severity,
                    "confidence": confidence,
                    "cwe": None,
                    "file": file_path,
                    "line": line_number,
                    "evidence": evidence,
                    "fix": fix,
                    "sources": [source],
                    "status": "rejected",
                }
            )
    return candidates


def _rejected_findings(
    report: str,
    candidates: list[dict[str, Any]],
    kept: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    sections = [
        _extract_section(report, ("### Rejected Findings", "### Rejected")),
        _extract_section(report, ("### Needs Human Review",)),
    ]
    rejected: list[dict[str, Any]] = []
    for section in sections:
        for block in _split_finding_blocks(section):
            title = _title_from_block(block)
            if not title or title.lower() == "none":
                continue
            if any(_similarity(title, item.get("title", "")) >= 0.7 for item in kept):
                continue
            candidate = max(
                candidates,
                key=lambda item: _similarity(title, item.get("title", "")),
                default=None,
            )
            reason = _field(block, "Reason") or "removed by verifier"
            item = {
                "id": str(uuid.uuid4()),
                "title": title,
                "severity": "LOW",
                "confidence": "LOW",
                "cwe": None,
                "file": None,
                "line": None,
                "evidence": "",
                "fix": "",
                "sources": [],
                "status": "rejected",
                "rejection_reason": reason,
            }
            if candidate and _similarity(title, candidate.get("title", "")) >= 0.34:
                item.update(
                    {
                        "severity": _normalize_severity(
                            str(candidate.get("severity") or ""), "LOW"
                        ),
                        "confidence": _normalize_confidence(
                            str(candidate.get("confidence") or ""), "LOW"
                        ),
                        "evidence": candidate.get("evidence") or "",
                        "fix": candidate.get("fix") or "",
                        "sources": list(candidate.get("sources") or []),
                        "file": candidate.get("file"),
                        "line": candidate.get("line"),
                    }
                )
            if any(
                _similarity(item["title"], current.get("title", "")) >= 0.75
                for current in rejected
            ):
                continue
            rejected.append(item)
    return rejected


def _normalize_findings(
    structured: list[dict[str, Any]],
    report: str,
    verifier_report: str,
    verifier_report_before_rules: str,
    verifier_input: dict[str, Any],
    diff_text: str,
) -> list[dict[str, Any]]:
    from src.structured_findings import _infer_cwe_from_finding

    kept: list[dict[str, Any]] = []
    for raw in structured or []:
        title = str(raw.get("title") or "").strip()
        if not title:
            continue
        source_value = raw.get("source") or raw.get("sources") or []
        if isinstance(source_value, str):
            sources = [source_value]
        elif isinstance(source_value, list):
            sources = [str(item) for item in source_value]
        else:
            sources = []
        kept.append(
            {
                "id": str(raw.get("id") or uuid.uuid4()),
                "title": title,
                "severity": _normalize_severity(str(raw.get("severity") or ""), "LOW"),
                "confidence": _normalize_confidence(
                    str(raw.get("confidence") or ""), "LOW"
                ),
                "cwe": raw.get("cwe")
                or _infer_cwe_from_finding(
                    title, str(raw.get("evidence") or "")
                )
                or None,
                "file": raw.get("file"),
                "line": int(raw["line"]) if raw.get("line") is not None else None,
                "evidence": str(raw.get("evidence") or ""),
                "fix": str(raw.get("fix") or ""),
                "sources": sources,
                "status": "kept",
                "rejection_reason": None,
            }
        )

    candidates = _candidate_findings(verifier_input or {}, diff_text)
    rejected = _rejected_findings(
        verifier_report or report, candidates, kept
    )

    before_rules = _extract_section(
        verifier_report_before_rules or "",
        ("### Accepted", "### Critical Issues", "### Suggestions"),
    )
    after_rules = _extract_section(
        verifier_report or report,
        ("### Accepted", "### Critical Issues", "### Suggestions"),
    )
    final_rejected = list(rejected)
    for block in _split_finding_blocks(before_rules):
        title = _title_from_block(block)
        if not title:
            continue
        if any(_similarity(title, item.get("title", "")) >= 0.7 for item in kept):
            continue
        if any(_similarity(title, item.get("title", "")) >= 0.7 for item in after_rules.splitlines()):
            continue
        if any(
            _similarity(title, existing.get("title", "")) >= 0.75
            for existing in final_rejected
        ):
            continue
        candidate = max(
            candidates,
            key=lambda item: _similarity(title, item.get("title", "")),
            default=None,
        )
        item = {
            "id": str(uuid.uuid4()),
            "title": title,
            "severity": "LOW",
            "confidence": "LOW",
            "cwe": None,
            "file": None,
            "line": None,
            "evidence": "",
            "fix": "",
            "sources": [],
            "status": "rejected",
            "rejection_reason": _field(block, "Reason") or "removed by verifier",
        }
        if candidate:
            item.update(
                {
                    "severity": _normalize_severity(
                        str(candidate.get("severity") or ""), "LOW"
                    ),
                    "confidence": _normalize_confidence(
                        str(candidate.get("confidence") or ""), "LOW"
                    ),
                    "evidence": candidate.get("evidence") or "",
                    "fix": candidate.get("fix") or "",
                    "sources": list(candidate.get("sources") or []),
                    "file": candidate.get("file"),
                    "line": candidate.get("line"),
                }
            )
        final_rejected.append(item)

    return kept + final_rejected


def _parse_verdict(report: str) -> str | None:
    match = re.search(r"\b(REQUEST\s+CHANGES|APPROVE)\b", report or "", flags=re.I)
    if not match:
        return None
    value = match.group(1).upper()
    if value.startswith("REQUEST"):
        return "REQUEST_CHANGES"
    return "APPROVE"


class PipelineAdapter:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def run(
        self,
        review_id: str,
        diff_text: str,
        file_paths: list[str],
        node_callback: NodeCallback,
        log_callback: LogCallback,
    ) -> PipelineOutcome:
        if matches_faculty_demo(diff_text):
            replay = run_faculty_demo(
                review_id,
                file_paths,
                node_callback,
                log_callback,
            )
            return PipelineOutcome(
                report_md=replay["report_md"],
                verdict=replay["verdict"],
                findings=replay["findings"],
                is_replay=True,
            )
        if self.settings.fake_pipeline:
            return self._run_fake(
                review_id, diff_text, file_paths, node_callback, log_callback
            )
        return self._run_real(
            review_id, diff_text, file_paths, node_callback, log_callback
        )

    def _run_real(
        self,
        review_id: str,
        diff_text: str,
        file_paths: list[str],
        node_callback: NodeCallback,
        log_callback: LogCallback,
    ) -> PipelineOutcome:
        from src.main import run_review
        from src.tools_semgrep import _get_semgrep_executable

        trace: dict[str, Any] = {"input": {}, "structured_findings": []}

        def callback(event: dict[str, Any]) -> None:
            node_callback(event)
            node = event.get("node")
            if event.get("event") == "start" and node == "verifier":
                trace["input"] = dict(event.get("state") or {})
            if event.get("event") == "end":
                output = event.get("output") or {}
                if node == "verifier":
                    trace["verifier_report"] = output.get("verified_report")
                    trace["verifier_report_before_rules"] = output.get(
                        "verifier_report_before_rules"
                    )
                if node == "summarizer":
                    trace["structured_findings"] = output.get(
                        "structured_findings"
                    ) or []

        root_logger = logging.getLogger()
        handler = _ReviewLogHandler(
            review_id, log_callback, self.settings.log_max_records
        )
        context_token = _review_context.set(review_id)
        root_logger.addHandler(handler)
        try:
            semgrep_executable = _get_semgrep_executable() or shutil.which("semgrep")
            if not semgrep_executable:
                log_callback(
                    datetime.now(UTC).isoformat(),
                    "WARNING",
                    (
                        "Semgrep executable is unavailable; the pipeline scanner "
                        "will continue without Semgrep results."
                    ),
                )
            report = run_review(
                diff_text,
                file_paths,
                node_callback=callback,
                capture_verifier_trace=True,
            )
            if isinstance(report, dict):
                report_md = str(report.get("final_review") or "")
                structured = report.get("structured_findings") or trace.get(
                    "structured_findings"
                )
                verifier_report = report.get("verified_report") or trace.get(
                    "verifier_report"
                )
                before_rules = report.get("verifier_report_before_rules") or trace.get(
                    "verifier_report_before_rules"
                )
                verifier_input = report.get("verifier_input") or trace.get("input") or {}
            else:
                report_md = str(report)
                structured = trace.get("structured_findings") or []
                verifier_report = trace.get("verifier_report") or report_md
                before_rules = trace.get("verifier_report_before_rules") or ""
                verifier_input = trace.get("input") or {}

            findings = _normalize_findings(
                list(structured or []),
                report_md,
                str(verifier_report or ""),
                str(before_rules or ""),
                dict(verifier_input or {}),
                diff_text,
            )
            return PipelineOutcome(
                report_md=report_md,
                verdict=_parse_verdict(report_md),
                findings=findings,
            )
        finally:
            root_logger.removeHandler(handler)
            handler.close()
            _review_context.reset(context_token)

    def _run_fake(
        self,
        review_id: str,
        diff_text: str,
        file_paths: list[str],
        node_callback: NodeCallback,
        log_callback: LogCallback,
    ) -> PipelineOutcome:
        agents = (
            "orchestrator",
            "bug_detector",
            "security",
            "code_quality",
            "test_coverage",
            "semgrep_scanner",
            "verifier",
            "summarizer",
        )
        synthetic = bool(
            re.search(r"execute\s*\(\s*['\"]SELECT", diff_text or "", flags=re.I)
        )
        findings: list[dict[str, Any]] = []
        if synthetic:
            findings.append(
                {
                    "id": str(uuid.uuid4()),
                    "title": "Demo simulation: query text is concatenated",
                    "severity": "CRITICAL",
                    "confidence": "HIGH",
                    "cwe": "CWE-89",
                    "file": (file_paths[0] if file_paths else None),
                    "line": 1,
                    "evidence": 'cursor.execute("SELECT * FROM users WHERE id = " + user_id)',
                    "fix": "Use parameterized query arguments.",
                    "sources": ["Demo adapter"],
                    "status": "kept",
                    "rejection_reason": None,
                }
            )
            findings.append(
                {
                    "id": str(uuid.uuid4()),
                    "title": "Demo-only simulated finding rejection",
                    "severity": "LOW",
                    "confidence": "LOW",
                    "cwe": None,
                    "file": None,
                    "line": None,
                    "evidence": "",
                    "fix": "",
                    "sources": ["Demo adapter"],
                    "status": "rejected",
                    "rejection_reason": "Illustrative fake-adapter output.",
                }
            )

        verdict = "REQUEST_CHANGES" if synthetic else "APPROVE"
        critical = (
            "- **CRITICAL | HIGH** Demo simulation: query text is concatenated\n"
            if synthetic
            else "None\n"
        )
        rejected = (
            "- Demo-only simulated finding rejection\n"
            "  - Reason: Illustrative fake-adapter output.\n\n"
            if synthetic
            else "None\n\n"
        )
        report = (
            "## Code Review Summary\n\n"
            "### Critical Issues (must fix before merge)\n"
            f"{critical}"
            "\n### Suggestions (should fix, improves quality)\nNone\n\n"
            "### Rejected Findings\n"
            f"{rejected}"
            f"### Verdict\n**{verdict.replace('_', ' ')}**\n\n"
            "This is a deterministic fake-pipeline demo response."
        )

        for agent in agents:
            node_callback({"event": "start", "node": agent})
            started = time.perf_counter()
            time.sleep(0.08)
            count = 0
            if agent == "security" and synthetic:
                count = 1
            if agent == "summarizer":
                count = len([f for f in findings if f["status"] == "kept"])
            duration_s = time.perf_counter() - started
            node_callback(
                {
                    "event": "end",
                    "node": agent,
                    "status": "done",
                    "duration_s": duration_s,
                    "output": {"finding_count": count},
                }
            )
            log_callback(
                datetime.now(UTC).isoformat(),
                "INFO",
                f"Demo adapter completed {agent} for review {review_id}.",
            )

        return PipelineOutcome(
            report_md=report,
            verdict=verdict,
            findings=findings,
            is_demo=True,
        )
