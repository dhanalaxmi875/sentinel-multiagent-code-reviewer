"""Test Coverage agent: identifies untested logic paths and missing edge cases."""

from src.llm import get_llm
from langchain_core.messages import SystemMessage, HumanMessage

from src.logger import get_logger
from src.state import ReviewState

_llm = get_llm()
_log = get_logger("test_coverage")

_SYSTEM_PROMPT = """You are a Test Coverage agent specializing in identifying testing gaps.

Analyze the provided code diff for:
- New logic paths that have no corresponding test
- Missing edge case tests (empty input, zero, None, boundary values, max values)
- Error/exception paths that are not tested
- Branches (if/else, switch) that are only partially covered
- Functions that are complex enough to warrant but lack unit tests
- Existing tests that might break due to the new changes (regression risk)
- Opportunities to add property-based or parameterized tests

Focus ONLY on test coverage and testing strategy. Do not comment on bugs or style.

Format your output as a numbered list, each item with:
- What is untested or at risk
- Suggested test case(s) to add (with brief pseudo-code or description)

If coverage appears adequate, respond with:
"Test coverage appears sufficient for the changes made." """


def test_coverage_node(state: ReviewState) -> dict:
    """Identify gaps in test coverage introduced by the diff."""
    _log.info("Evaluating test coverage gaps...")

    response = _llm.invoke([
        SystemMessage(content=_SYSTEM_PROMPT),
        HumanMessage(content=f"Code diff to review:\n```\n{state['code_diff']}\n```"),
    ])

    return {"test_report": [response.content]}

