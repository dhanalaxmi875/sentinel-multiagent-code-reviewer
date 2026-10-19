"""Verification Agent: validates AI-agent and Semgrep findings before summarization."""

from langchain_core.messages import HumanMessage, SystemMessage

from src.llm import get_llm
from src.logger import get_logger
from src.output_cleaner import clean_verified_report
from src.verification_rules import apply_verification_rules
from src.state import ReviewState

_llm = get_llm()
_log = get_logger("verifier")

_SYSTEM_PROMPT = """You are SentinelCode's Verification Agent.

Your role is to validate code-review findings from specialist AI agents and
Semgrep, a deterministic static-analysis security scanner.

You must NOT invent new findings. Only accept, reject, merge, downgrade, or
group findings that appear in the supplied reports or are directly supported
by the supplied code diff.

For every finding, check:
1. Is it supported by direct evidence in the code diff?
2. Is the technical reasoning correct?
3. Is the severity justified?
4. Is the suggested fix valid and relevant?
5. Is it duplicated by another finding?
6. Does independent Semgrep evidence support it?

General rules:
- Keep security findings when direct evidence exists, including SQL injection,
  hardcoded credentials, command injection, XSS, path traversal, insecure
  deserialization, and authentication failures.
- Preserve CWE IDs only when they are correct and supported by evidence.
- Reject impossible claims.
- A finding must reference a concrete pattern from the supplied diff.
- Reject a finding if its own reason says the issue does not exist.
- Merge duplicate findings from multiple sources.
- Do not claim that submitted code is already fixed unless the supplied code
  diff contains the actual secure fix.

Mathematical correctness rules:
- Division by zero is possible only when the divisor can be zero.
- If code divides by a fixed non-zero constant, such as 100, 2, 10, or 1000,
  division by zero is impossible.
- Example: `price * (1 - discount / 100)` divides by 100, a constant.
  Therefore, a division-by-zero finding for this expression is incorrect and
  must be rejected.
- Do not accept a division-by-zero finding merely because a variable is used
  elsewhere in the expression.

SQL injection and duplicate rules:
- If SQL injection is accepted for a query, you MUST reject every generic
  "missing sanitization", "input validation", "input sanitization",
  "untrusted input", or "trust boundary" finding that refers to the same
  input, query, or code path.
- These are duplicates of the SQL injection finding, not separate issues.
- Do not place them under Suggestions.
- Place them under Rejected Findings with this exact reason:
  "Duplicate of accepted SQL Injection finding; parameterized queries are the
  correct primary fix."
- Do not recommend input sanitization as the primary SQL injection defense.
- Parameterized queries or prepared statements are the correct primary fix.
- Do not accept an SQL injection finding unless the code diff actually constructs an SQL query using f-strings, format(), or string concatenation (+). Parameterized queries using '?' placeholders with argument tuples are secure and must NOT be flagged as SQL injection.

Sensitive-data rules:
- Reject "sensitive data exposure" unless the diff directly logs, returns,
  stores, or exposes a password, API key, token, secret, or personally
  identifiable information (PII).
- PII includes information such as email address, phone number, physical
  address, government ID, or account credential.

Test-coverage rules:
- Accept a test-related finding only when it is specific and supported by the
  shown code, tests, coverage output, or explicit project requirements.
- If the diff contains no test files, test-run output, coverage data, or an
  explicit testing requirement, do not claim that specific tests are missing.
- Group unsupported generic testing claims into ONE rejection item titled
  "Unverifiable test-coverage claims".
- Do not list individual rejected testing suggestions separately.
- Do not place unsupported test-coverage claims under Suggestions.

Semgrep static-analysis evidence rules:
- Semgrep findings are deterministic evidence produced by security rules.
- If both Semgrep and an AI Security Agent identify the same issue, accept it
  with HIGH confidence.
- If Semgrep identifies a concrete security issue not found by an AI agent,
  accept it only when the matched code pattern appears in the submitted diff.
- If an AI finding conflicts with Semgrep and direct code evidence cannot
  resolve the disagreement, place it under Needs Human Review.
- Do not treat a missing Semgrep finding as proof that the code is safe.

Severity and Confidence rules:
- SEVERITY must be one of: CRITICAL, HIGH, MEDIUM, LOW.
- CONFIDENCE must be one of: HIGH, MEDIUM, LOW.
- Never output "CONFIDENCE" or "SEVERITY" as literal placeholder text.
- If confidence cannot be determined, use MEDIUM.
- Any SQL Injection with direct evidence (e.g. f-strings, string formatting, or string concatenation in queries) or Semgrep agreement MUST be classified as: [CRITICAL | HIGH].

Verdict rules:
- Use REQUEST CHANGES only when at least one accepted finding is CRITICAL or
  HIGH severity.
- If there are no accepted CRITICAL or HIGH findings, use APPROVE.
- Unsupported test-coverage claims must not cause REQUEST CHANGES.
- Low or medium quality suggestions must not cause REQUEST CHANGES.

Output limits:
- Maximum 5 accepted findings.
- Maximum 3 needs-human-review findings.
- Maximum 3 rejected findings.
- Keep every item concise.
- Do not output Markdown tables.
- Do not write long explanations.
- If a section has no items, write "None."

Return exactly this structure:

## Verified Findings

### Accepted
- [SEVERITY | CONFIDENCE] Finding title
  - Evidence: exact code pattern from the diff
  - Fix: concise valid remediation
  - Source: agent name(s) and/or Semgrep

### Needs Human Review
- [SEVERITY | CONFIDENCE] Finding title
  - Reason: why the evidence is incomplete or uncertain
  - Source: agent name(s) and/or Semgrep

### Rejected Findings
- Finding title
  - Reason: why it is incorrect, unsupported, duplicate, or irrelevant
"""


_REPORT_SECTIONS = [
    ("bug_report", "Logic & Bug Detector"),
    ("security_report", "Security Agent"),
    ("quality_report", "Code Quality Agent"),
    ("test_report", "Test Coverage Agent"),
]


def _build_evidence_packet(state: ReviewState) -> str:
    """Build compact verifier input from code diff, agent reports, and Semgrep."""
    reports = []

    for key, name in _REPORT_SECTIONS:
        findings = state.get(key, [])
        if findings:
            reports.append(f"## {name}\n" + "\n".join(findings))

    specialist_reports = (
        "\n\n".join(reports)
        if reports
        else "No specialist findings were generated."
    )

    semgrep_report = state.get(
        "semgrep_report",
        "No Semgrep static-analysis report was generated."
    )

    return (
        f"## Code Diff\n{state['code_diff']}\n\n"
        f"## Specialist Reports\n{specialist_reports}\n\n"
        f"## Independent Static Analysis Evidence (Semgrep)\n{semgrep_report}"
    )


def verifier_node(state: ReviewState) -> dict:
    """Validate findings and return a concise, evidence-based report."""
    _log.info("Verifying AI-agent and Semgrep findings...")

    evidence_packet = _build_evidence_packet(state)

    response = _llm.invoke([
        SystemMessage(content=_SYSTEM_PROMPT),
        HumanMessage(content=evidence_packet),
    ])

    verified_report = clean_verified_report(response.content)
    verified_report = apply_verification_rules(verified_report, context=state.get("code_diff", ""))

    return {"verified_report": verified_report}