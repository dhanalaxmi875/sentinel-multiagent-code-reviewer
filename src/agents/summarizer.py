"""Summarizer Agent: produces a concise final review from verified findings."""

from langchain_core.messages import HumanMessage, SystemMessage

from src.llm import get_llm
from src.logger import get_logger
from src.state import ReviewState
from src.verification_rules import apply_verification_rules, enforce_verdict

_llm = get_llm()
_log = get_logger("summarizer")

_SYSTEM_PROMPT = """You are SentinelCode's Final Review Summarizer.

Create a concise, developer-friendly pull-request review using only the
Verification Agent report provided. Do not introduce new findings.

You MUST preserve full Markdown formatting (headings, bullet points, bold labels).

Use exactly this structure:

## Code Review Summary

### Critical Issues (must fix before merge)
- **CRITICAL | HIGH** Finding title
  - Evidence: exact code pattern from the diff
  - Fix: concise valid remediation
  - Source: SentinelCode
(If there are no critical/high issues, write: None)

### Suggestions (should fix, improves quality)
- **MEDIUM | HIGH** Finding title
  - Evidence or Reason: explanation
  - Fix: suggested fix
  - Source: SentinelCode
(If there are no suggestions, write: None)

### Rejected Findings
- Finding title
  - Reason: why it was rejected
(If there are no rejected findings, write: None)

### Verdict
**REQUEST CHANGES** (if any Critical/High issues exist) or **APPROVE** (if no Critical/High issues exist)

One concise sentence explaining the decision.

Rules:
- Never introduce a finding that is not present in the Verification Agent report.
- If a section has no findings in the Verification Agent report, you MUST output None for that section.
- Never output literal placeholder text like "CONFIDENCE" or "SEVERITY". Use actual values: CRITICAL, HIGH, MEDIUM, LOW.
- If confidence cannot be determined, use MEDIUM.
- When Critical Issues contain findings, Verdict MUST be **REQUEST CHANGES**.
- When Critical Issues is None, Verdict MUST be **APPROVE**.
- Keep each item concise: issue, evidence, fix, and source.
- Do not repeat duplicate findings.
"""


def summarizer_node(state: ReviewState) -> dict:
    """Create the final review using verified findings only."""
    _log.info("Compiling final review from verified findings...")

    verified_report = state.get(
        "verified_report",
        "No verification report was generated."
    )
    code_diff = state.get("code_diff", "")
    verified_report = apply_verification_rules(verified_report, context=code_diff)

    response = _llm.invoke([
        SystemMessage(content=_SYSTEM_PROMPT),
        HumanMessage(content=(
            f"Verification Agent report:\n\n{verified_report}\n\n"
            "Generate the final code review."
        )),
    ])

    final_review = apply_verification_rules(response.content, context=code_diff)

    from src.structured_findings import parse_accepted_findings
    structured_findings = parse_accepted_findings(final_review, code_diff)

    return {
        "final_review": final_review,
        "structured_findings": structured_findings,
    }