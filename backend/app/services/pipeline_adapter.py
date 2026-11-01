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

from ..config import Settings

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
    def __init__(self, review_id: str, sink: LogCallback, max_records: int):
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
        if self.record_count >= self.max_records:
            if not self.truncated:
                self.truncated = True
                self.sink(
                    datetime.now(UTC).isoformat(),
                    "WARNING",
                    f"Review log capture reached {self.max_records} records; "
                    "later records were not stored.",
                )
            return
        self.record_count += 1
        message = record.getMessage()
        remaining = self.max_chars - self.char_count
        if remaining <= 0:
            if not self.truncated:
                self.truncated = True
                self.sink(
                    datetime.now(UTC).isoformat(),
                    "WARNING",
                    f"Review log capture reached {self.max_chars} characters; "
                    "later records were not stored.",
                )
            return
        if len(message) > remaining:
            message = message[:remaining] + " [message truncated by log capture limit]"
            self.truncated = True
        self.char_count += len(message)
        self.sink(
            datetime.fromtimestamp(record.created, UTC).isoformat(),
            record.levelname,
            message,
        )


def _count_agent_findings(node: str, output: dict[str, Any]) -> int:
    if node == "summarizer":
        return len(output.get("structured_findings", []))
    if node == "semgrep_scanner":
        return len(re.findall(r"(?m)^- Rule:", output.get("semgrep_report", "")))
    if node == "verifier":
        accepted = _extract_section(
            output.get("verified_report", ""),
            ("### Accepted", "### Critical Issues", "### Suggestions"),
        )
        return len(
            re.findall(r"(?m)^\s*-\s*(?:\[|\*\*)?(?:CRITICAL|HIGH|MEDIUM|LOW)\b", accepted, re.I)
        )
    if node in {"bug_detector", "security", "code_quality", "test_coverage"}:
        key = {
            "bug_detector": "bug_report",
            "security": "security_report",
            "code_quality": "quality_report",
            "test_coverage": "test_report",
        }[node]
        text = "\n".join(output.get(key, []))
        if re.search(r"(?i)^\s*(?:no\s|test coverage appears sufficient)", text.strip()):
            return 0
        return len(re.findall(r"(?m)^\s*\d+[.)]\s+", text))
    return 0


def _extract_section(report: str, headings: tuple[str, ...]) -> str:
    lines = report.splitlines()
    start = next(
        (
            i
            for i, line in enumerate(lines)
            if line.strip().lower() in {h.lower() for h in headings}
        ),
        None,
    )
    if start is None:
        return ""
    end = next(
        (i for i in range(start + 1, len(lines)) if re.match(r"^#{2,3}\s", lines[i])),
        len(lines),
    )
    return "\n".join(lines[start + 1 : end]).strip()


def _split_finding_blocks(section: str) -> list[str]:
    if not section or re.fullmatch(r"(?is)\s*-?\s*none\.?\s*", section):
        return []
    blocks = re.split(r"(?m)(?=^\s*-\s+)", section)
    return [block.strip() for block in blocks if block.strip()]


def _title_from_block(block: str) -> str:
    first = next((line.strip() for line in block.splitlines() if line.strip()), "")
    first = re.sub(r"^[-*]\s+", "", first)
    first = re.sub(
        r"^(?:\*\*)?(?:\[)?(?:CRITICAL|HIGH|MEDIUM|LOW)\s*\|\s*(?:HIGH|MEDIUM|LOW)(?:\])?(?:\*\*)?\s*",
        "",
        first,
        flags=re.I,
    )
    return first.strip(" *-\t")


def _field(block: str, names: str) -> str:
    match = re.search(
        rf"(?ims)^\s*(?:-\s*)?(?:{names})\s*:\s*(.*?)(?=^\s*(?:-\s*)?(?:Evidence|Fix|Source|Reason|CWE|Severity|Confidence)\s*:|\Z)",
        block,
        re.I,
    )
    return match.group(1).strip() if match else ""


def _normalize(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def _similarity(left: str, right: str) -> float:
    a = _normalize(left)
    b = _normalize(right)
    if not a or not b:
        return 0.0
    if a in b or b in a:
        return 0.9
    ratio = SequenceMatcher(None, a, b).ratio()
    words_a, words_b = set(a.split()), set(b.split())
    overlap = len(words_a & words_b) / max(1, len(words_a | words_b))
    return max(ratio, overlap)


def _normalize_severity(text: str, default: str = "LOW") -> str:
    match = re.search(r"\b(CRITICAL|HIGH|MEDIUM|LOW)\b", text, re.I)
    return match.group(1).upper() if match else default


def _normalize_confidence(text: str, default: str = "LOW") -> str:
    match = re.search(r"\b(HIGH|MEDIUM|LOW)\b", text, re.I)
    return match.group(1).upper() if match else default


def _candidate_findings(state: dict[str, Any], diff_text: str) -> list[dict[str, Any]]:
    from src.structured_findings import extract_file_and_line_from_diff, parse_diff_hunks

    diff_map = parse_diff_hunks(diff_text)
    reports = (
        ("bug_report", "Bug & Logic Detector"),
        ("security_report", "Security Agent"),
        ("quality_report", "Code Quality Agent"),
        ("test_report", "Test Coverage Agent"),
    )
    candidates: list[dict[str, Any]] = []
    for key, source in reports:
        content = "\n".join(state.get(key, []))
        if not content or re.search(
            r"(?i)no (?:logic|security|code quality) "
            r"(?:or |vulnerabilities|issues|correctness issues)",
            content,
        ):
            continue
        blocks = re.split(r"(?m)(?=^\s*\d+[.)]\s+)", content)
        blocks = [block.strip() for block in blocks if re.match(r"(?s)^\s*\d+[.)]\s+", block)]
        if not blocks and content.strip():
            first = content.strip()
            if not re.search(r"(?i)(?:no issues|no vulnerabilities|appears sufficient)", first):
                blocks = [first]
        for block in blocks:
            block = re.sub(r"^\s*\d+[.)]\s+", "", block)
            title = _title_from_block(block)
            if not title or len(title) > 500:
                continue
            severity = _normalize_severity(block)
            confidence = _normalize_confidence(block)
            evidence = _field(block, r"Evidence|Code(?: snippet)?|Snippet|Line")
            fix = _field(block, r"Fix|Suggested fix|Recommendation")
            file_path, line_number = extract_file_and_line_from_diff(evidence, title, diff_map)
            candidates.append(
                {
                    "title": title,
                    "severity": severity,
                    "confidence": confidence,
                    "cwe": "",
                    "file": file_path or "",
                    "line": line_number or 0,
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
            if not title or _normalize(title) == "none":
                continue
            candidate = max(
                candidates, key=lambda item: _similarity(title, item["title"]), default=None
            )
            if candidate is not None and _similarity(title, candidate["title"]) < 0.34:
                candidate = None
            reason = _field(block, "Reason")
            item = dict(candidate or {})
            item.update(
                {
                    "id": str(uuid.uuid4()),
                    "title": title,
                    "severity": _normalize_severity(block, item.get("severity", "LOW")),
                    "confidence": _normalize_confidence(block, item.get("confidence", "LOW")),
                    "evidence": item.get("evidence", ""),
                    "fix": item.get("fix", ""),
                    "sources": item.get("sources", []),
                    "status": "rejected",
                    "rejection_reason": reason or "removed by verifier",
                }
            )
            if not any(_similarity(item["title"], current["title"]) > 0.75 for current in rejected):
                rejected.append(item)

    for candidate in candidates:
        title = candidate["title"]
        if any(_similarity(title, item["title"]) > 0.7 for item in kept + rejected):
            continue
        rejected.append(
            {
                **candidate,
                "id": str(uuid.uuid4()),
                "rejection_reason": "removed by verifier",
            }
        )

    return rejected


def _normalize_findings(
    structured: list[dict[str, Any]],
    report: str,
    verifier_report: str,
    verifier_input: dict[str, Any],
    diff_text: str,
) -> list[dict[str, Any]]:
    from src.structured_findings import _infer_cwe_from_finding

    kept: list[dict[str, Any]] = []
    for raw in structured:
        title = str(raw.get("title", "")).strip()
        if not title:
            continue
        source_value = raw.get("source", raw.get("sources", []))
        sources = source_value if isinstance(source_value, list) else [str(source_value)]
        severity = _normalize_severity(str(raw.get("severity", "LOW")))
        confidence = _normalize_confidence(str(raw.get("confidence", "LOW")))
        kept.append(
            {
                "id": str(uuid.uuid4()),
                "title": title,
                "severity": severity,
                "confidence": confidence,
                "cwe": str(
                    raw.get("cwe") or _infer_cwe_from_finding(title, str(raw.get("evidence", "")))
                ),
                "file": str(raw.get("file") or ""),
                "line": int(raw.get("line") or 0),
                "evidence": str(raw.get("evidence") or ""),
                "fix": str(raw.get("fix") or ""),
                "sources": [str(source) for source in sources if source],
                "status": "kept",
                "rejection_reason": None,
            }
        )
    candidates = _candidate_findings(verifier_input, diff_text)
    rejected = _rejected_findings(verifier_report or report, candidates, kept)
    # Include final-report rejections if the verifier's trace did not contain them.
    final_rejected = _rejected_findings(report, candidates, kept + rejected)
    for item in final_rejected:
        if not any(_similarity(item["title"], existing["title"]) > 0.75 for existing in rejected):
            rejected.append(item)
    return kept + rejected


def _parse_verdict(report: str) -> str | None:
    match = re.search(r"\b(REQUEST\s+CHANGES|APPROVE)\b", report, re.I)
    if not match:
        return None
    return "REQUEST_CHANGES" if match.group(1).upper().startswith("REQUEST") else "APPROVE"


class PipelineAdapter:
    def __init__(self, settings: Settings):
        self.settings = settings

    def run(
        self,
        *,
        review_id: str,
        diff_text: str,
        file_paths: list[str],
        node_callback: NodeCallback,
        log_callback: LogCallback,
    ) -> PipelineOutcome:
        if self.settings.fake_pipeline:
            return self._run_fake(review_id, diff_text, file_paths, node_callback, log_callback)
        return self._run_real(review_id, diff_text, file_paths, node_callback, log_callback)

    def _run_real(
        self,
        review_id: str,
        diff_text: str,
        file_paths: list[str],
        node_callback: NodeCallback,
        log_callback: LogCallback,
    ) -> PipelineOutcome:
        from src.main import run_review

        trace: dict[str, Any] = {}

        def callback(event: dict[str, Any]) -> None:
            node_callback(event)
            if event.get("event") == "start" and event.get("node") == "verifier":
                trace["input"] = dict(event.get("state", {}))
            if event.get("event") == "end" and event.get("node") == "verifier":
                output = event.get("output", {})
                trace["verifier_report"] = output.get("verified_report", "")
                trace["verifier_report_before_rules"] = output.get(
                    "verifier_report_before_rules", ""
                )
            if event.get("event") == "end" and event.get("node") == "summarizer":
                trace["structured_findings"] = event.get("output", {}).get(
                    "structured_findings", []
                )

        root_logger = logging.getLogger("review")
        handler = _ReviewLogHandler(review_id, log_callback, self.settings.log_max_records)
        context_token = _review_context.set(review_id)
        root_logger.addHandler(handler)
        try:
            from src.tools_semgrep import _get_semgrep_executable

            semgrep_executable = _get_semgrep_executable()
            if semgrep_executable == "semgrep" and shutil.which("semgrep") is None:
                log_callback(
                    datetime.now(UTC).isoformat(),
                    "WARNING",
                    "Semgrep executable is unavailable; the pipeline scanner will "
                    "continue without Semgrep results.",
                )
            report = run_review(
                diff_text,
                file_paths,
                node_callback=callback,
                capture_verifier_trace=True,
            )
        finally:
            root_logger.removeHandler(handler)
            handler.close()
            _review_context.reset(context_token)

        findings = _normalize_findings(
            trace.get("structured_findings", []),
            report,
            trace.get("verifier_report", ""),
            trace.get("input", {}),
            diff_text,
        )
        return PipelineOutcome(report, _parse_verdict(report), findings)

    def _run_fake(
        self,
        review_id: str,
        diff_text: str,
        file_paths: list[str],
        node_callback: NodeCallback,
        log_callback: LogCallback,
    ) -> PipelineOutcome:
        del file_paths
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
        synthetic = bool(re.search(r"execute\s*\(\s*['\"]SELECT", diff_text, re.I))
        findings: list[dict[str, Any]] = []
        if synthetic:
            findings.append(
                {
                    "id": str(uuid.uuid4()),
                    "title": "Demo simulation: query text is concatenated",
                    "severity": "CRITICAL",
                    "confidence": "HIGH",
                    "cwe": "CWE-89",
                    "file": "",
                    "line": 0,
                    "evidence": "",
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
                    "cwe": "",
                    "file": "",
                    "line": 0,
                    "evidence": "",
                    "fix": "",
                    "sources": ["Demo adapter"],
                    "status": "rejected",
                    "rejection_reason": "Illustrative fake-adapter output.",
                }
            )
        report = (
            "## Code Review Summary\n\n"
            "### Critical Issues (must fix before merge)\n"
            + (
                "- **CRITICAL | HIGH** Demo simulation: query text is concatenated\n"
                if synthetic
                else "None\n"
            )
            + "\n### Suggestions (should fix, improves quality)\nNone\n\n"
            "### Rejected Findings\n"
            + (
                "- Demo-only simulated finding rejection\n"
                "  - Reason: Illustrative fake-adapter output.\n\n"
                if synthetic
                else "None\n\n"
            )
            + "### Verdict\n**"
            + ("REQUEST CHANGES" if synthetic else "APPROVE")
            + "**\n\nThis is a deterministic fake-pipeline demo response."
        )
        for agent in agents:
            started = time.perf_counter()
            node_callback({"event": "start", "node": agent})
            time.sleep(0.08)
            count = int(agent == "summarizer") * len([f for f in findings if f["status"] == "kept"])
            node_callback(
                {
                    "event": "end",
                    "node": agent,
                    "status": "done",
                    "duration_s": time.perf_counter() - started,
                    "output": {},
                    "finding_count": count,
                }
            )
            log_callback(
                datetime.now(UTC).isoformat(),
                "INFO",
                f"Demo adapter completed {agent} for review {review_id}.",
            )
        return PipelineOutcome(
            report,
            "REQUEST_CHANGES" if synthetic else "APPROVE",
            findings,
            is_demo=True,
        )
