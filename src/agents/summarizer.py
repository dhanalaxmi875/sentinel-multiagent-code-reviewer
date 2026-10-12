"""Summarizer Agent: produces a concise final review from verified findings."""

from langchain_core.messages import HumanMessage, SystemMessage

from src.llm import get_llm
from src.logger import get_logger
from src.state import ReviewState
from src.verification_rules import enforce_verdict
_llm = get_llm()
_log = get_logger("summarizer")

_SYSTEM_PROMPT = """You are SentinelCode's Final Review Summarizer.

Create a concise, developer-friendly pull-request review using only the
Verification Agent report provided. Do not introduce new findings.

Use exactly this structure:

## Code Review Summary

### Critical Issues (must fix before merge)
<List accepted CRITICAL or HIGH confidence findings only.>

### Suggestions (should fix, improves quality)
<List accepted MEDIUM or LOW severity findings and findings needing human review.>

### Rejected Findings
<List only meaningful rejected findings, if any. Otherwise write None.>

### Verdict
<One of: APPROVE | REQUEST CHANGES | NEEDS DISCUSSION>
<One concise sentence explaining the decision.>

Rules:
- Never promote a finding above the severity given by the Verification Agent.
- Preserve CWE IDs if available.
- Keep each item short: issue, evidence, and fix.
- Do not repeat duplicate findings.
- Do not mention raw specialist reports.
"""


def summarizer_node(state: ReviewState) -> dict:
    """Create the final review using verified findings only."""
    _log.info("Compiling final review from verified findings...")

    verified_report = state.get(
        "verified_report",
        "No verification report was generated."
    )

    response = _llm.invoke([
        SystemMessage(content=_SYSTEM_PROMPT),
        HumanMessage(content=(
            f"Verification Agent report:\n\n{verified_report}\n\n"
            "Generate the final code review."
        )),
    ])

final_review = enforce_verdict(response.content)

return {"final_review": final_review}