"""Deterministic safety rules for SentinelCode final review output."""

import re


BLOCKING_RATIONALE = (
    "Critical or high-severity findings are present in the submitted code and "
    "must be fixed before merge."
)


def has_blocking_finding(review: str) -> bool:
    """
    Return True when a CRITICAL or HIGH finding is listed in the final review.
    """
    return bool(
        re.search(
            r"^\s*-\s*\*{0,2}(CRITICAL|HIGH)\b",
            review,
            flags=re.IGNORECASE | re.MULTILINE,
        )
    )


def enforce_verdict(review: str) -> str:
    """
    Force REQUEST CHANGES whenever the review contains CRITICAL or HIGH issues.
    Replace the full verdict section to prevent contradictory LLM rationale.
    """
    if not has_blocking_finding(review):
        return review

    verdict_section = (
        "### Verdict\n"
        "**REQUEST CHANGES**\n\n"
        f"{BLOCKING_RATIONALE}"
    )

    if re.search(r"### Verdict[\s\S]*$", review, flags=re.IGNORECASE):
        return re.sub(
            r"### Verdict[\s\S]*$",
            verdict_section,
            review,
            flags=re.IGNORECASE,
        )

    return f"{review.rstrip()}\n\n{verdict_section}\n"