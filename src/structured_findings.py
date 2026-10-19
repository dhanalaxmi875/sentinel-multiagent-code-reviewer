"""Structured findings extractor and diff line mapper for SentinelCode."""

import json
from pathlib import Path
import re


def parse_diff_hunks(diff_text: str) -> dict[str, dict[int, str]]:
    """
    Parse a unified diff and return a mapping of target file paths to added/modified lines.

    Returns:
        dict[file_path, dict[line_number, line_content]]
    """
    files: dict[str, dict[int, str]] = {}
    current_file = None
    current_line = 0

    for raw_line in diff_text.splitlines():
        if raw_line.startswith("+++ b/"):
            current_file = raw_line[6:].strip()
            if current_file not in files:
                files[current_file] = {}
            continue
        elif raw_line.startswith("+++ "):
            # Some diffs don't use b/ prefix
            current_file = raw_line[4:].strip()
            if current_file.startswith("b/"):
                current_file = current_file[2:]
            if current_file not in files:
                files[current_file] = {}
            continue

        if raw_line.startswith("@@ "):
            # Parse hunk header: @@ -a,b +start,count @@ or @@ -a,b +start @@
            m = re.search(r"\+(\d+)(?:,(\d+))?", raw_line)
            if m:
                current_line = int(m.group(1))
            continue

        if current_file is None:
            continue

        if raw_line.startswith("+") and not raw_line.startswith("+++"):
            line_text = raw_line[1:]
            files[current_file][current_line] = line_text
            current_line += 1
        elif raw_line.startswith("-") and not raw_line.startswith("---"):
            # Deletion does not advance target line number
            pass
        elif raw_line.startswith(" ") or raw_line == "":
            current_line += 1

    return files


def extract_file_and_line_from_diff(
    evidence: str,
    title: str,
    diff_map: dict[str, dict[int, str]],
) -> tuple[str | None, int | None]:
    """
    Attempt to find the file and line number in the diff that corresponds to evidence and title.
    """
    if not diff_map:
        return None, None

    # Check if a file name is explicitly mentioned in title or evidence
    candidate_files = []
    combined_query = f"{title} {evidence}"
    for f in diff_map:
        base_name = Path(f).name
        if base_name in combined_query or f in combined_query:
            candidate_files.append(f)

    # If no candidate file found, search across all files in the diff
    search_files = candidate_files if candidate_files else list(diff_map.keys())

    # Clean evidence lines for searching
    clean_evidence_lines = []
    for line in evidence.splitlines():
        s = line.strip().strip("`").strip()
        if s and not s.startswith("```"):
            clean_evidence_lines.append(s)

    # 1. Search for an exact line match of evidence lines
    for clean_ev in clean_evidence_lines:
        for f in search_files:
            for line_no, content in diff_map[f].items():
                if clean_ev == content.strip():
                    return f, line_no

    # 2. Search for substring match of evidence lines (minimum 8 chars to avoid false hits)
    for clean_ev in clean_evidence_lines:
        if len(clean_ev) < 8:
            continue
        for f in search_files:
            for line_no, content in diff_map[f].items():
                if clean_ev in content or content.strip() in clean_ev:
                    return f, line_no

    # 3. If file candidate is known and has lines in diff, pick the first line if unique
    if len(candidate_files) == 1:
        f = candidate_files[0]
        if diff_map[f]:
            return f, min(diff_map[f].keys())

    return (search_files[0], min(diff_map[search_files[0]].keys())) if len(search_files) == 1 and diff_map[search_files[0]] else (None, None)


def parse_accepted_findings(report: str, diff_text: str | None = None) -> list[dict]:
    """
    Parse accepted findings (Critical Issues and Suggestions) from a SentinelCode Markdown report.
    Maps findings to files and lines using the diff if provided.
    """
    diff_map = parse_diff_hunks(diff_text) if diff_text else {}
    findings: list[dict] = []

    # Sections to inspect (only accepted findings, exclude Rejected Findings)
    section_patterns = [
        ("CRITICAL", r"(?ms)### Critical Issues(?:\s*\(must fix before merge\))?\s*(.*?)(?=### Suggestions|### Rejected|### Verdict|\Z)"),
        ("MEDIUM", r"(?ms)### Suggestions(?:\s*\(should fix, improves quality\))?\s*(.*?)(?=### Critical|### Rejected|### Verdict|\Z)"),
    ]

    for default_sev, pattern in section_patterns:
        match = re.search(pattern, report)
        if not match:
            continue

        body = match.group(1).strip()
        if not body or re.match(r"^-?\s*None\.?$", body, re.IGNORECASE):
            continue

        # Split into finding blocks
        blocks = re.split(r"(?m)(?=^- (?:\[|\*\*)?[A-Z]+)", body)
        for block in blocks:
            b_clean = block.strip()
            if not b_clean or re.match(r"^-?\s*None\.?$", b_clean, re.IGNORECASE):
                continue

            lines = b_clean.splitlines()
            header_line = lines[0].strip()
            if header_line.startswith("- "):
                header_line = header_line[2:].strip()

            # Parse severity, confidence, and title
            sev = default_sev
            conf = "HIGH" if default_sev == "CRITICAL" else "MEDIUM"
            title = header_line

            header_match = re.match(
                r"^(?:\[|\*\*)?([A-Za-z]+)\s*\|\s*([A-Za-z]+)(?:\*\]|\*\*|\])?\s*[-—:]?\s*(.*)",
                header_line,
                flags=re.IGNORECASE,
            )
            if header_match:
                sev = header_match.group(1).upper()
                conf = header_match.group(2).upper()
                title = header_match.group(3).strip()
            else:
                title = re.sub(r"^(?:\[|\*\*)?[A-Za-z]+\s*\|\s*[A-Za-z]+(?:\*\]|\*\*|\])?\s*", "", header_line).strip()

            # Normalize values
            if conf in ("CONFIDENCE", "UNKNOWN", ""):
                conf = "MEDIUM"
            if sev in ("SEVERITY", ""):
                sev = default_sev

            # Parse Evidence, Fix, Source
            evidence = ""
            fix = ""
            sources: list[str] = []
            cwe = ""

            ev_match = re.search(r"(?ms)(?:^|\n)\s*-\s*Evidence:\s*(.*?)(?=\n\s*-\s*(?:Fix|Source|Reason|CWE):|\Z)", b_clean)
            if ev_match:
                evidence = ev_match.group(1).strip()

            fix_match = re.search(r"(?ms)(?:^|\n)\s*-\s*Fix:\s*(.*?)(?=\n\s*-\s*(?:Evidence|Source|Reason|CWE):|\Z)", b_clean)
            if fix_match:
                fix = fix_match.group(1).strip()

            src_match = re.search(r"(?m)(?:^|\n)\s*-\s*Source:\s*(.*?)$", b_clean)
            if src_match:
                raw_src = src_match.group(1).strip()
                raw_src = re.sub(r"(?i)agent name\(s\):?\s*", "", raw_src)
                for part in re.split(r",| and | / ", raw_src):
                    p = part.strip()
                    if p and p not in sources:
                        sources.append(p)
            if not sources:
                sources = ["SentinelCode"]

            # Infer CWE if present
            if "sql injection" in title.lower() or "sql injection" in evidence.lower():
                cwe = "CWE-89"
            elif "command injection" in title.lower():
                cwe = "CWE-78"

            # Locate file and line number
            file_path, line_no = extract_file_and_line_from_diff(evidence, title, diff_map)

            findings.append({
                "title": title,
                "severity": sev,
                "confidence": conf,
                "file": file_path,
                "line": line_no,
                "evidence": evidence,
                "fix": fix,
                "source": sources,
                "cwe": cwe,
            })

    return findings


def save_structured_findings(findings: list[dict], output_file: str | Path) -> None:
    """Save structured findings list as a formatted JSON file."""
    path = Path(output_file)
    path.write_text(json.dumps(findings, indent=2), encoding="utf-8")
