"""Semgrep integration for deterministic static security analysis."""

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def _get_semgrep_executable() -> str:
    """Find the semgrep executable across PATH and local virtual environment."""
    exe = shutil.which("semgrep")
    if exe:
        return exe

    env_dir = Path(sys.executable).parent
    for name in ("semgrep.exe", "semgrep", "semgrep.cmd"):
        candidate = env_dir / name
        if candidate.is_file():
            return str(candidate)

    return "semgrep"


def scan_python_code(code: str) -> list[dict]:
    """
    Scan Python source code using Semgrep's community Python rules.

    Returns a normalized list of findings. If Semgrep is unavailable or fails,
    returns an empty list rather than stopping the complete AI review pipeline.
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        source_file = Path(temp_dir) / "review_target.py"
        output_file = Path(temp_dir) / "semgrep_results.json"

        source_file.write_text(code, encoding="utf-8")

        custom_rules = Path("semgrep_rules").resolve()
        if not custom_rules.exists():
            custom_rules = Path(__file__).resolve().parent.parent / "semgrep_rules"
        rules_arg = str(custom_rules) if custom_rules.exists() else "semgrep_rules"

        command = [
            _get_semgrep_executable(),
            "--config",
            "p/python",
            "--config",
            "p/owasp-top-ten",
            "--config",
            rules_arg,
            "--disable-version-check",
            "--metrics=off",
            "--no-git-ignore",
            "--json",
            "--output",
            str(output_file),
            source_file.name,
        ]

        try:
            subprocess.run(
                command,
                cwd=temp_dir,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=90,
                check=False,
            )

            if not output_file.exists():
                return []

            data = json.loads(output_file.read_text(encoding="utf-8"))

        except (subprocess.SubprocessError, OSError, json.JSONDecodeError):
            return []

    findings = []

    for result in data.get("results", []):
        extra = result.get("extra", {})
        metadata = extra.get("metadata", {})

        findings.append(
            {
                "rule_id": result.get("check_id", "unknown-rule"),
                "message": extra.get("message", "Semgrep finding"),
                "severity": extra.get("severity", "WARNING"),
                "line": result.get("start", {}).get("line"),
                "code": extra.get("lines", "").strip(),
                "cwe": metadata.get("cwe", []),
            }
        )

    return findings


def format_semgrep_report(findings: list[dict]) -> str:
    """Format Semgrep findings so they can be read by the Verification Agent."""
    if not findings:
        return "No Semgrep findings were generated."

    lines = ["## Semgrep Static Analysis Report"]

    for finding in findings[:10]:
        cwe = ", ".join(finding["cwe"]) if finding["cwe"] else "Not specified"

        lines.extend(
            [
                f"- Rule: {finding['rule_id']}",
                f"  - Severity: {finding['severity']}",
                f"  - CWE: {cwe}",
                f"  - Line: {finding['line']}",
                f"  - Evidence: {finding['code']}",
                f"  - Message: {finding['message']}",
            ]
        )

    return "\n".join(lines)