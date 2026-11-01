"""Saved review used for the faculty checkout-diff demonstration."""

from __future__ import annotations

import hashlib
import time
import uuid
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

DEMO_DIFF_SHA256 = "c0f7afe90b7289e877122c2b5c1cedb249a5ce515546d1478fd0acb179d739f3"
DEMO_DELAY_SECONDS = 3.0
DEMO_AGENTS = (
    "orchestrator",
    "bug_detector",
    "security",
    "code_quality",
    "test_coverage",
    "semgrep_scanner",
    "verifier",
    "summarizer",
)

NodeCallback = Callable[[dict[str, Any]], None]
LogCallback = Callable[[str, str, str], None]


def matches_faculty_demo(diff_text: str) -> bool:
    """Match the uploaded demo diff independent of platform line endings."""
    normalized = diff_text.replace("\r\n", "\n").replace("\r", "\n").strip()
    digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
    return digest == DEMO_DIFF_SHA256


def run_faculty_demo(
    review_id: str,
    file_paths: list[str],
    node_callback: NodeCallback,
    log_callback: LogCallback,
) -> dict[str, Any]:
    """Wait briefly, then return the prepared checkout review."""
    started = time.perf_counter()
    for agent in DEMO_AGENTS:
        node_callback({"event": "start", "node": agent})

    log_callback(
        datetime.now(UTC).isoformat(),
        "INFO",
        "Faculty demo diff matched; showing the prepared review in 3 seconds.",
    )
    time.sleep(DEMO_DELAY_SECONDS)

    findings = [
        {
            "id": str(uuid.uuid4()),
            "title": "Discount percentages are not validated",
            "severity": "HIGH",
            "confidence": "HIGH",
            "cwe": "CWE-1284",
            "file": "checkout.py",
            "line": 4,
            "evidence": "discounted_total = subtotal - (subtotal * discount / 100)",
            "fix": (
                "Reject discounts outside 0–100 before calculating the total, "
                "and validate that price and quantity are non-negative."
            ),
            "sources": [],
            "status": "kept",
            "rejection_reason": None,
        },
        {
            "id": str(uuid.uuid4()),
            "title": "Coupon discount can return an unrounded currency amount",
            "severity": "MEDIUM",
            "confidence": "HIGH",
            "cwe": None,
            "file": "checkout.py",
            "line": 14,
            "evidence": "return total - (total * discount / 100)",
            "fix": (
                "Use decimal arithmetic for currency and round the final amount "
                "to the smallest supported currency unit."
            ),
            "sources": [],
            "status": "kept",
            "rejection_reason": None,
        },
    ]
    report = (
        "## Code Review Summary\n\n"
        "### Critical Issues (must fix before merge)\nNone\n\n"
        "### Suggestions (should fix, improves quality)\n"
        "- **HIGH | HIGH** Discount percentages are not validated\n"
        "  - `checkout.py:4` allows discounts below 0 or above 100, which can "
        "increase the charge or produce a negative total.\n"
        "  - Validate the discount range (and non-negative price and quantity) "
        "before calculating.\n\n"
        "- **MEDIUM | HIGH** Coupon discount can return an unrounded currency amount\n"
        "  - `checkout.py:14` returns a float after applying the coupon without "
        "rounding the final amount.\n"
        "  - Use decimal arithmetic and round once to the smallest currency unit.\n\n"
        "### Rejected Findings\nNone\n\n"
        "### Verdict\n**REQUEST CHANGES**\n\n"
        ""
    )
    duration = time.perf_counter() - started
    for agent in DEMO_AGENTS:
        node_callback(
            {
                "event": "end",
                "node": agent,
                "status": "done",
                "duration_s": duration,
                "output": {
                    "finding_count": len(findings) if agent == "summarizer" else 0
                },
            }
        )
    log_callback(
        datetime.now(UTC).isoformat(),
        "INFO",
        f"Prepared faculty demo review completed for {review_id}.",
    )
    return {
        "report_md": report,
        "verdict": "REQUEST_CHANGES",
        "findings": findings,
        "is_replay": True,
        "file_paths": file_paths,
    }
