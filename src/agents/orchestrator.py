"""Orchestrator agent: routes the diff to the appropriate specialist agents."""

import json
import re

from src.llm import get_llm
from langchain_core.messages import SystemMessage, HumanMessage

from src.logger import get_logger
from src.state import ReviewState

_llm = get_llm()
_log = get_logger("orchestrator")

_SYSTEM_PROMPT = """You are an orchestrator for a multi-agent code review system.

Given a code diff and the list of changed file paths, decide which specialist review agents to activate.

Available agents:
- bug_detector   : logic errors, off-by-one, null dereferences, infinite loops, wrong conditionals
- security       : SQL injection, hardcoded secrets, insecure input handling, vulnerable patterns
- code_quality   : readability, naming, function length, duplication, style adherence
- test_coverage  : missing tests, untested edge cases, logic with no corresponding test

Rules:
- Always activate bug_detector and code_quality for any non-trivial code change.
- Activate security for backend code, API endpoints, auth, database queries, config files.
- Skip security for pure CSS/HTML/style-only changes unless they contain inline scripts.
- Activate test_coverage when test files are present OR when new logic is added without tests.
- You may activate all four agents when in doubt.

Respond ONLY with a JSON object in this exact format:
{
  "active_agents": ["bug_detector", "security", "code_quality", "test_coverage"],
  "reasoning": "brief explanation of routing decisions"
}"""


def orchestrator_node(state: ReviewState) -> dict:
    """Decide which specialist agents to activate for this diff."""
    file_list = "\n".join(state["file_paths"]) if state["file_paths"] else "unknown"

    response = _llm.invoke([
        SystemMessage(content=_SYSTEM_PROMPT),
        HumanMessage(content=(
            f"File paths changed:\n{file_list}\n\n"
            f"Code diff:\n```\n{state['code_diff']}\n```"
        )),
    ])

    text = response.content
    # Extract JSON from the response
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        data = json.loads(match.group())
    else:
        # Fallback: activate all agents
        data = {"active_agents": ["bug_detector", "security", "code_quality", "test_coverage"]}

    active = [a for a in data.get("active_agents", []) if a in {
        "bug_detector", "security", "code_quality", "test_coverage"
    }]

    _log.info("Routing to agents: %s", active)
    if "reasoning" in data:
        _log.info("Routing reason: %s", data["reasoning"])

    return {"active_agents": active}

