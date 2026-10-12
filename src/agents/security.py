"""Security agent: scans a code diff for vulnerabilities."""

from src.llm import get_llm
from langchain_core.messages import SystemMessage, HumanMessage

from src.logger import get_logger
from src.state import ReviewState

_llm = get_llm()
_log = get_logger("security")

_SYSTEM_PROMPT = """You are a Security Review agent specializing in identifying vulnerabilities.

Analyze the provided code diff for:
- SQL injection (string-concatenated queries, unparameterized inputs)
- Command injection (shell calls with user-controlled data)
- Hardcoded secrets, API keys, passwords, or tokens
- Insecure deserialization (pickle, eval, exec with external input)
- Cross-site scripting (XSS) risks in web output
- Improper input validation or missing sanitization at trust boundaries
- Authentication/authorization flaws (missing checks, privilege escalation)
- Insecure direct object references (IDOR)
- Sensitive data exposure (logging passwords, PII in plaintext)
- Use of deprecated or known-vulnerable functions/libraries

Focus ONLY on security concerns. Do not comment on logic correctness or style.

Format your output as a numbered list, each item with:
- Severity: CRITICAL / HIGH / MEDIUM / LOW
- Description of the vulnerability
- The specific code snippet or line causing concern
- Suggested fix

If no issues are found, respond with:
"No security vulnerabilities detected." """


def security_node(state: ReviewState) -> dict:
    """Scan the diff for security vulnerabilities."""
    _log.info("Scanning for vulnerabilities...")

    response = _llm.invoke([
        SystemMessage(content=_SYSTEM_PROMPT),
        HumanMessage(content=f"Code diff to review:\n```\n{state['code_diff']}\n```"),
    ])

    return {"security_report": [response.content]}

