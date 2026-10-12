import operator
from typing import Annotated, TypedDict


class ReviewState(TypedDict):
    # Input
    code_diff: str
    file_paths: list[str]

    # Orchestrator routing decisions
    active_agents: list[str]

    # Specialist outputs
    bug_report: Annotated[list[str], operator.add]
    security_report: Annotated[list[str], operator.add]
    quality_report: Annotated[list[str], operator.add]
    test_report: Annotated[list[str], operator.add]

    # Verification Agent output
    verified_report: str

    # Final output
    final_review: str