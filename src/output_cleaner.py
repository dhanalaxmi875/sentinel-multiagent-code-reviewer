"""Deterministic cleanup rules for SentinelCode verification output."""

import re


def limit_rejected_findings(report: str, max_items: int = 3) -> str:
    """
    Keep at most `max_items` bullets in the Rejected Findings section.

    This prevents local LLMs from producing long, repetitive rejection lists.
    """
    pattern = (
        r"(### Rejected Findings\s*\n)"
        r"(.*?)(?=\n### |\Z)"
    )

    match = re.search(pattern, report, flags=re.DOTALL | re.IGNORECASE)
    if not match:
        return report

    header = match.group(1)
    section_content = match.group(2).strip()

    if section_content.lower() == "none.":
        return report

    items = re.split(r"(?=^- )", section_content, flags=re.MULTILINE)
    items = [item.strip() for item in items if item.strip()]

    limited_items = items[:max_items]

    cleaned_section = header + "\n".join(limited_items) + "\n"

    return report[:match.start()] + cleaned_section + report[match.end():]


def remove_duplicate_rejected_findings(report: str) -> str:
    """
    Remove rejected items that duplicate an accepted or suggested issue.

    Specifically removes rejected SQL-input validation/sanitization items if
    SQL Injection is already accepted in the report.
    """
    has_sql_injection = bool(
        re.search(r"SQL\s*Injection", report, flags=re.IGNORECASE)
    )

    if not has_sql_injection:
        return report

    duplicate_patterns = [
        r"- Improper Input Validation or Missing Sanitization.*?(?=\n- |\n### |\Z)",
        r"- Missing Sanitization.*?(?=\n- |\n### |\Z)",
    ]

    for pattern in duplicate_patterns:
        report = re.sub(
            pattern,
            "",
            report,
            flags=re.IGNORECASE | re.DOTALL,
        )

    return report


def clean_confidence_placeholders(report: str) -> str:
    """Replace literal CONFIDENCE placeholder text with MEDIUM or HIGH."""
    # Replace literal CONFIDENCE placeholder
    report = re.sub(r"\|\s*CONFIDENCE\b", "| MEDIUM", report, flags=re.IGNORECASE)
    report = re.sub(r"\bCONFIDENCE\b", "MEDIUM", report)
    return report


def clean_verified_report(report: str) -> str:
    """Apply all deterministic cleanup rules to verifier output."""
    report = clean_confidence_placeholders(report)
    report = remove_duplicate_rejected_findings(report)
    report = remove_unsupported_suggestions(report)
    report = limit_rejected_findings(report, max_items=3)

    report = re.sub(r"\n{3,}", "\n\n", report).strip()
    return report

def remove_unsupported_suggestions(report: str) -> str:
    """
    Remove suggestions that explicitly admit they lack evidence or specificity.
    """
    pattern = (
        r"- \*\*(?:LOW|MEDIUM) \| (?:LOW|MEDIUM)\*\*.*?"
        r"(?=^- \*\*|\n### |\Z)"
    )

    matches = re.findall(pattern, report, flags=re.IGNORECASE | re.DOTALL | re.MULTILINE)

    for item in matches:
        weak_reason = (
            "not specific enough" in item.lower()
            or "lack concrete evidence" in item.lower()
            or "evidence is incomplete" in item.lower()
        )
        if weak_reason:
            report = report.replace(item, "")

    return report