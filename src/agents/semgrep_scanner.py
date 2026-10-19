"""Semgrep Scanner Agent: deterministic static security analysis."""

from src.logger import get_logger
from src.state import ReviewState
from src.tools_semgrep import format_semgrep_report, scan_python_code

_log = get_logger("semgrep_scanner")


def _extract_added_python_lines(diff: str) -> str:
    """
    Extract added Python lines from a unified Git diff.

    Removes diff metadata such as +++, @@, and file markers.
    """
    lines = []

    for line in diff.splitlines():
        if line.startswith("+++") or line.startswith("diff ") or line.startswith("@@"):
            continue

        if line.startswith("+"):
            lines.append(line[1:])

    return "\n".join(lines)


def semgrep_scanner_node(state: ReviewState) -> dict:
    """Run Semgrep against code added in the submitted Git diff."""
    _log.info("Running Semgrep static analysis...")

    source_code = _extract_added_python_lines(state["code_diff"])

    if not source_code.strip():
        return {"semgrep_report": "No added source code available for Semgrep scan."}

    findings = scan_python_code(source_code)
    report = format_semgrep_report(findings)

    return {"semgrep_report": report}