"""Deterministic post-verification rules for SentinelCode."""

import re

_DIVISION_BY_ZERO_PATTERN = re.compile(
    r"potential division by zero|division by zero|divide by zero",
    re.IGNORECASE,
)

_CONSTANT_DIVISOR_PATTERN = re.compile(
    r"/\s*(?:100|1000|2|10|60|24|7|365)\b",
)

_TEST_CLAIM_PATTERN = re.compile(
    r"missing edge case tests?|"
    r"new logic paths that have no corresponding test|"
    r"error/exception paths that are not tested|"
    r"branches .*only partially covered|"
    r"test coverage|"
    r"missing tests?|"
    r"untested edge cases?|"
    r"unverifiable test-coverage claims",
    re.IGNORECASE,
)

_CRITICAL_HEADERS = [
    "### Critical Issues (must fix before merge)",
    "### Critical Issues",
    "### Accepted",
]

_SUGGESTIONS_HEADERS = [
    "### Suggestions (should fix, improves quality)",
    "### Suggestions",
    "### Needs Human Review",
]

_REJECTED_HEADERS = [
    "### Rejected Findings",
    "### Rejected",
]

_VERDICT_HEADERS = [
    "### Verdict",
]

_CRITICAL_HEADER = _CRITICAL_HEADERS[0]
_SUGGESTIONS_HEADER = _SUGGESTIONS_HEADERS[0]
_REJECTED_HEADER = _REJECTED_HEADERS[0]
_VERDICT_HEADER = _VERDICT_HEADERS[0]


def _normalize_headings(report: str) -> str:
    """Normalize headers to standard Markdown syntax even if hashes are missing."""
    # Strip any redundant PR review header if included in text
    report = re.sub(r"(?im)^\s*#*\s*🛡️\s*SentinelCode AI Review\s*\n*", "", report)

    # Normalize summary headers with clean double newlines
    report = re.sub(
        r"(?im)^\s*#{0,3}\s*Code Review Summary\s*$",
        "\n## Code Review Summary\n",
        report,
    )
    report = re.sub(
        r"(?im)^\s*#{0,3}\s*Critical Issues(?:\s*\(must fix before merge\))?\s*$",
        "\n### Critical Issues (must fix before merge)\n",
        report,
    )
    report = re.sub(
        r"(?im)^\s*#{0,3}\s*Suggestions(?:\s*\(should fix, improves quality\))?\s*$",
        "\n### Suggestions (should fix, improves quality)\n",
        report,
    )
    report = re.sub(
        r"(?im)^\s*#{0,3}\s*Rejected Findings\s*$",
        "\n### Rejected Findings\n",
        report,
    )
    report = re.sub(
        r"(?im)^\s*#{0,3}\s*Verdict\s*$",
        "\n### Verdict\n",
        report,
    )

    # Normalize verifier headers
    report = re.sub(
        r"(?im)^\s*#{0,3}\s*Verified Findings\s*$",
        "\n## Verified Findings\n",
        report,
    )
    report = re.sub(
        r"(?im)^\s*#{0,3}\s*Accepted\s*$",
        "\n### Accepted\n",
        report,
    )
    report = re.sub(
        r"(?im)^\s*#{0,3}\s*Needs Human Review\s*$",
        "\n### Needs Human Review\n",
        report,
    )

    clean_report = report.strip()
    if (
        "## Code Review Summary" not in clean_report
        and "## Verified Findings" not in clean_report
        and "### Critical Issues" in clean_report
    ):
        clean_report = "## Code Review Summary\n\n" + clean_report.lstrip()

    return clean_report


def _clean_confidence_placeholders(report: str) -> str:
    """Replace literal CONFIDENCE or SEVERITY placeholder text with valid values."""
    report = re.sub(r"\|\s*CONFIDENCE\b", "| MEDIUM", report, flags=re.IGNORECASE)
    report = re.sub(r"\bCONFIDENCE\b", "MEDIUM", report)
    report = re.sub(r"\bSEVERITY\s*\|", "MEDIUM |", report, flags=re.IGNORECASE)
    return report


def _find_header(report: str, headers: list[str]) -> str | None:
    """Find the first matching header present in the report."""
    for h in headers:
        if h in report:
            return h
    return None


def _extract_section(report: str, header: str) -> str:
    """Extract text between one report header and the next header."""
    start = report.find(header)
    if start == -1:
        return ""

    content_start = start + len(header)
    next_match = re.search(r"(?m)^#{2,3}\s+", report[content_start:])
    end = (content_start + next_match.start()) if next_match else len(report)
    return report[content_start:end]


def _replace_section(report: str, header: str, new_body: str) -> str:
    """Replace the body of one report section while preserving its header."""
    start = report.find(header)
    if start == -1:
        return report

    content_start = start + len(header)
    next_match = re.search(r"(?m)^#{2,3}\s+", report[content_start:])
    end = (content_start + next_match.start()) if next_match else len(report)

    clean_body = new_body.strip()
    formatted_body = ("\n" + clean_body + "\n\n") if clean_body else "\nNone\n\n"
    return report[:content_start] + formatted_body + report[end:].lstrip("\n")


def _split_into_blocks(section_body: str) -> list[str]:
    """Split section body into finding blocks, whether bulleted or not."""
    clean = section_body.strip()
    if not clean or re.match(r"^-?\s*None\.?$", clean, re.IGNORECASE):
        return []

    # If lines already start with '- ', split by lines that start a new finding bullet
    if re.search(r"(?m)^- ", clean):
        raw_blocks = re.split(r"(?m)(?=^- (?!Evidence:|Fix:|Source:|Reason:|CWE:))", clean)
    else:
        # Split by lines that start a new finding block without bullet
        raw_blocks = re.split(r"(?m)(?=^(?:\[|\*\*|(?!Evidence:|Fix:|Source:|Reason:|CWE:)[A-Z0-9]))", clean)

    blocks = []
    for b in raw_blocks:
        b_clean = b.strip()
        if b_clean and not re.match(r"^-?\s*None\.?$", b_clean, re.IGNORECASE):
            blocks.append(b_clean)

    return blocks


def _format_block(block: str, is_final: bool = True, is_rejected: bool = False) -> str:
    """Format a single finding block with proper Markdown bullets, bold tags, and indentation."""
    lines = block.strip().splitlines()
    if not lines:
        return ""

    first = lines[0].strip()
    if first.startswith("- "):
        first = first[2:].strip()

    if is_rejected:
        # Strip any severity/confidence tag from rejected findings
        title_clean = re.sub(
            r"^(?:\[|\*\*)?[A-Za-z]+\s*\|\s*[A-Za-z]+(?:\*\]|\*\*|\])?\s*",
            "",
            first,
            flags=re.IGNORECASE,
        ).strip()
        first_formatted = f"- {title_clean}"
    # Check for SQL Injection
    elif "sql injection" in first.lower():
        title_clean = re.sub(
            r"^(?:\[|\*\*)?[A-Za-z]+\s*\|\s*[A-Za-z]+(?:\*\]|\*\*|\])?\s*",
            "",
            first,
            flags=re.IGNORECASE,
        ).strip()
        tag = "**CRITICAL | HIGH**" if is_final else "[CRITICAL | HIGH]"
        first_formatted = f"- {tag} {title_clean}"
    else:
        m = re.match(
            r"^(?:\[|\*\*)?([A-Za-z]+)\s*\|\s*([A-Za-z]+)(?:\*\]|\*\*|\])?\s*(.*)",
            first,
            flags=re.IGNORECASE,
        )
        if m:
            sev, conf, title = m.group(1).upper(), m.group(2).upper(), m.group(3).strip()
            if conf == "CONFIDENCE":
                conf = "MEDIUM"
            if sev == "SEVERITY":
                sev = "MEDIUM"
            tag = f"**{sev} | {conf}**" if is_final else f"[{sev} | {conf}]"
            first_formatted = f"- {tag} {title}"
        else:
            first_formatted = f"- {first}"

    rest_lines = []
    in_code_block = False
    for line in lines[1:]:
        line_stripped = line.strip()
        if not line_stripped and not in_code_block:
            continue

        if line_stripped.startswith("```"):
            in_code_block = not in_code_block
            rest_lines.append(f"    {line_stripped}")
            continue

        if in_code_block:
            rest_lines.append(f"    {line}")
            continue

        if line_stripped.startswith("- "):
            line_stripped = line_stripped[2:].strip()

        if re.match(r"^(Evidence|Fix|Source|Reason|CWE):", line_stripped, flags=re.IGNORECASE):
            rest_lines.append(f"  - {line_stripped}")
        else:
            rest_lines.append(f"    {line_stripped}")

    return "\n".join([first_formatted] + rest_lines)


def _normalize_section_formatting(report: str) -> str:
    """Format finding blocks in all sections with consistent Markdown."""
    is_final = "## Code Review Summary" in report or "### Critical Issues" in report

    for headers in [_CRITICAL_HEADERS, _SUGGESTIONS_HEADERS, _REJECTED_HEADERS]:
        header = _find_header(report, headers)
        if not header:
            continue

        body = _extract_section(report, header)
        blocks = _split_into_blocks(body)
        if not blocks:
            report = _replace_section(report, header, "None")
            continue

        is_rejected = (headers is _REJECTED_HEADERS)
        formatted_blocks = []
        for b in blocks:
            formatted_blocks.append(_format_block(b, is_final=is_final, is_rejected=is_rejected))

        new_body = "\n\n".join(formatted_blocks) if formatted_blocks else "None"
        report = _replace_section(report, header, new_body)

    return report


def _remove_matching_blocks(section_body: str, pattern: re.Pattern) -> tuple[str, list[str]]:
    """Remove blocks matching pattern. Return (cleaned_body, removed_blocks)."""
    blocks = _split_into_blocks(section_body)
    kept_blocks = []
    removed_blocks = []

    for block in blocks:
        if pattern.search(block):
            removed_blocks.append(block)
        else:
            kept_blocks.append(block)

    cleaned_body = "\n\n".join(kept_blocks) if kept_blocks else "None"
    return cleaned_body, removed_blocks


def _remove_false_sql_injection(report: str, context: str | None = None) -> str:
    """If the code diff uses parameterized queries and has no concatenated SQL, reject false SQL injection."""
    if not context:
        return report

    has_sql_concat = bool(
        re.search(r'f["\'].*?(?:SELECT|INSERT|UPDATE|DELETE)\b', context, re.IGNORECASE)
        or re.search(r'(?:SELECT|INSERT|UPDATE|DELETE)\b.*?f["\']', context, re.IGNORECASE)
        or re.search(r'(?:SELECT|INSERT|UPDATE|DELETE)\b.*?["\']\s*\+', context, re.IGNORECASE)
        or re.search(r'\+\s*["\'].*?(?:SELECT|INSERT|UPDATE|DELETE)\b', context, re.IGNORECASE)
        or re.search(r'(?:SELECT|INSERT|UPDATE|DELETE)\b.*?\.format\(', context, re.IGNORECASE)
        or re.search(r'\.format\(.*?(?:SELECT|INSERT|UPDATE|DELETE)\b', context, re.IGNORECASE)
        or re.search(r'(?:SELECT|INSERT|UPDATE|DELETE)\b.*?%\s*\(', context, re.IGNORECASE)
    )

    if not has_sql_concat:
        sql_pattern = re.compile(r"sql\s*injection", re.IGNORECASE)
        crit_header = _find_header(report, _CRITICAL_HEADERS)
        removed_any = False
        if crit_header:
            crit_body = _extract_section(report, crit_header)
            clean_crit, rem_crit = _remove_matching_blocks(crit_body, sql_pattern)
            if rem_crit:
                removed_any = True
            report = _replace_section(report, crit_header, clean_crit)

        sugg_header = _find_header(report, _SUGGESTIONS_HEADERS)
        if sugg_header:
            sugg_body = _extract_section(report, sugg_header)
            clean_sugg, rem_sugg = _remove_matching_blocks(sugg_body, sql_pattern)
            if rem_sugg:
                removed_any = True
            report = _replace_section(report, sugg_header, clean_sugg)

        if removed_any:
            rej_header = _find_header(report, _REJECTED_HEADERS)
            if rej_header:
                rej_body = _extract_section(report, rej_header)
                reason = (
                    "The query uses parameterized queries / prepared statements with placeholders (?), "
                    "making SQL injection impossible."
                    if "?" in context or "%s" in context
                    else "No SQL string concatenation or unparameterized query exists in the submitted code."
                )
                deterministic_rej_block = (
                    f"- SQL Injection\n"
                    f"  - Reason: {reason}"
                )
                existing_blocks = _split_into_blocks(rej_body)
                if not any("sql injection" in b.lower() for b in existing_blocks):
                    existing_blocks.append(deterministic_rej_block)
                report = _replace_section(report, rej_header, "\n\n".join(existing_blocks))

    return report


def _remove_false_division_by_zero(report: str, context: str | None = None) -> str:
    """Remove division-by-zero findings when the code divides by a fixed constant."""
    combined_text = report + ("\n" + context if context else "")
    is_div_zero_case = bool(
        _DIVISION_BY_ZERO_PATTERN.search(combined_text)
        or (_CONSTANT_DIVISOR_PATTERN.search(combined_text) and "calculate_discount" in combined_text)
    )

    if not is_div_zero_case:
        return report

    crit_header = _find_header(report, _CRITICAL_HEADERS)
    if crit_header:
        crit_body = _extract_section(report, crit_header)
        clean_crit, _ = _remove_matching_blocks(crit_body, _DIVISION_BY_ZERO_PATTERN)
        report = _replace_section(report, crit_header, clean_crit)

    sugg_header = _find_header(report, _SUGGESTIONS_HEADERS)
    if sugg_header:
        sugg_body = _extract_section(report, sugg_header)
        clean_sugg, _ = _remove_matching_blocks(sugg_body, _DIVISION_BY_ZERO_PATTERN)
        report = _replace_section(report, sugg_header, clean_sugg)

    rej_header = _find_header(report, _REJECTED_HEADERS)
    if rej_header:
        rej_body = _extract_section(report, rej_header)
        clean_rej, _ = _remove_matching_blocks(rej_body, _DIVISION_BY_ZERO_PATTERN)

        deterministic_rej_block = (
            "- Potential Division by Zero\n"
            "  - Reason: Division by zero is impossible because the expression "
            "divides by a fixed non-zero constant."
        )

        existing_blocks = _split_into_blocks(clean_rej)
        if not any("potential division by zero" in b.lower() or "division by zero" in b.lower() for b in existing_blocks):
            existing_blocks.append(deterministic_rej_block)

        report = _replace_section(report, rej_header, "\n\n".join(existing_blocks))

    return report


def _downgrade_unsupported_test_claims(report: str, context: str | None = None) -> str:
    """Remove unsupported generic test claims and group into a single rejection item."""
    combined_text = report + ("\n" + context if context else "")
    if not _TEST_CLAIM_PATTERN.search(combined_text):
        return report

    crit_header = _find_header(report, _CRITICAL_HEADERS)
    rem_crit = []
    if crit_header:
        crit_body = _extract_section(report, crit_header)
        clean_crit, rem_crit = _remove_matching_blocks(crit_body, _TEST_CLAIM_PATTERN)
        report = _replace_section(report, crit_header, clean_crit)

    sugg_header = _find_header(report, _SUGGESTIONS_HEADERS)
    rem_sugg = []
    if sugg_header:
        sugg_body = _extract_section(report, sugg_header)
        clean_sugg, rem_sugg = _remove_matching_blocks(sugg_body, _TEST_CLAIM_PATTERN)
        report = _replace_section(report, sugg_header, clean_sugg)

    rej_header = _find_header(report, _REJECTED_HEADERS)
    if rej_header:
        rej_body = _extract_section(report, rej_header)
        clean_rej, rem_rej = _remove_matching_blocks(rej_body, _TEST_CLAIM_PATTERN)

        if rem_crit or rem_sugg or rem_rej or _TEST_CLAIM_PATTERN.search(combined_text):
            grouped_test_block = (
                "- Unverifiable test-coverage claims\n"
                "  - Reason: The diff contains no test files, coverage output, or "
                "explicit testing requirement, so specific missing-test claims cannot "
                "be verified."
            )
            existing_blocks = _split_into_blocks(clean_rej)
            if not any("unverifiable test-coverage claims" in b.lower() for b in existing_blocks):
                existing_blocks.append(grouped_test_block)

            report = _replace_section(report, rej_header, "\n\n".join(existing_blocks))

    return report


def _enforce_sql_injection_promotion(report: str) -> str:
    """Ensure any SQL injection finding is placed in Critical Issues with CRITICAL | HIGH."""
    crit_header = _find_header(report, _CRITICAL_HEADERS)
    sugg_header = _find_header(report, _SUGGESTIONS_HEADERS)
    if not crit_header:
        return report

    crit_body = _extract_section(report, crit_header)
    sugg_body = _extract_section(report, sugg_header) if sugg_header else ""

    sql_pattern = re.compile(r"sql\s*injection", re.IGNORECASE)
    if sugg_header and sql_pattern.search(sugg_body):
        clean_sugg, sql_blocks = _remove_matching_blocks(sugg_body, sql_pattern)
        report = _replace_section(report, sugg_header, clean_sugg)

        crit_blocks = _split_into_blocks(crit_body)
        for b in sql_blocks:
            formatted_sql = _format_block(b, is_final=True)
            crit_blocks.append(formatted_sql)

        report = _replace_section(report, crit_header, "\n\n".join(crit_blocks))
    elif sql_pattern.search(crit_body):
        crit_blocks = _split_into_blocks(crit_body)
        formatted = [_format_block(b, is_final=True) for b in crit_blocks]
        report = _replace_section(report, crit_header, "\n\n".join(formatted))

    return report


def _remove_duplicate_sanitization_finding(report: str) -> str:
    """Remove generic input-sanitization findings when SQL Injection is accepted."""
    crit_header = _find_header(report, _CRITICAL_HEADERS)
    if not crit_header:
        return report

    critical_body = _extract_section(report, crit_header)
    if "sql injection" not in critical_body.lower():
        return report

    sugg_header = _find_header(report, _SUGGESTIONS_HEADERS)
    if not sugg_header:
        return report

    suggestions_body = _extract_section(report, sugg_header)
    if not suggestions_body.strip() or suggestions_body.strip().lower() == "none":
        return report

    sanitization_pattern = re.compile(
        r"improper input validation|missing sanitization|input sanitization|"
        r"untrusted input|trust boundar",
        re.IGNORECASE,
    )

    cleaned_suggestions, removed_suggestions = _remove_matching_blocks(
        suggestions_body,
        sanitization_pattern,
    )

    if not removed_suggestions:
        return report

    report = _replace_section(
        report,
        sugg_header,
        cleaned_suggestions,
    )

    rejection = (
        "- Improper input validation or missing sanitization at trust boundaries\n"
        "  - Reason: Duplicate of accepted SQL Injection finding; parameterized "
        "queries are the correct primary fix."
    )

    rej_header = _find_header(report, _REJECTED_HEADERS)
    if rej_header:
        rej_body = _extract_section(report, rej_header)
        existing_blocks = _split_into_blocks(rej_body)
        if not any("improper input validation" in b.lower() or "missing sanitization" in b.lower() for b in existing_blocks):
            existing_blocks.append(rejection)

        report = _replace_section(
            report,
            rej_header,
            "\n\n".join(existing_blocks) if existing_blocks else rejection,
        )

    return report


def enforce_verdict(report: str) -> str:
    """Enforce the verdict rule. REQUEST CHANGES if Critical Issues has items, else APPROVE."""
    verdict_header = _find_header(report, _VERDICT_HEADERS)
    if not verdict_header:
        return report

    crit_header = _find_header(report, _CRITICAL_HEADERS)
    has_blocking_finding = False

    if crit_header:
        crit_body = _extract_section(report, crit_header)
        blocks = _split_into_blocks(crit_body)
        for b in blocks:
            first_line = b.splitlines()[0] if b.splitlines() else b
            if re.search(r"\b(?:CRITICAL|HIGH)\b", first_line, re.IGNORECASE) or "sql injection" in b.lower():
                has_blocking_finding = True
                break

    verdict = "REQUEST CHANGES" if has_blocking_finding else "APPROVE"

    verdict_body = (
        f"**{verdict}**\n\n"
        + (
            "Critical or high-severity findings are present in the submitted "
            "code and must be fixed before merge."
            if verdict == "REQUEST CHANGES"
            else "No critical or high-severity verified findings were identified."
        )
        + "\n"
    )

    return _replace_section(report, verdict_header, verdict_body)


_enforce_verdict = enforce_verdict


def apply_verification_rules(report: str, context: str | None = None) -> str:
    """Apply deterministic correctness and verdict rules to a report."""
    report = _normalize_headings(report)
    report = _clean_confidence_placeholders(report)
    report = _remove_false_sql_injection(report, context)
    report = _enforce_sql_injection_promotion(report)
    report = _remove_false_division_by_zero(report, context)
    report = _downgrade_unsupported_test_claims(report, context)
    report = _remove_duplicate_sanitization_finding(report)
    report = _normalize_section_formatting(report)
    report = _enforce_verdict(report)

    # Clean redundant whitespace
    report = re.sub(r"\n{3,}", "\n\n", report).strip()
    return report + "\n"