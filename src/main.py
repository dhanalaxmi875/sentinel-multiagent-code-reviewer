"""Entry point for the multi-agent code review pipeline.

Public API:
    run_review(code_diff, file_paths) -> str
"""

import pathlib
import sys
import uuid

# Ensure the project root is on sys.path so `src.*` imports resolve whether
# this file is run as `python src/main.py` or `python -m src.main`.
_PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from dotenv import load_dotenv

load_dotenv()

from src.chunker import prepare_diff
from src.graph import build_graph
from src.logger import get_logger

_log = get_logger("main")


def run_review(
    code_diff: str,
    file_paths: list[str] | None = None,
    *,
    node_callback=None,
    capture_verifier_trace: bool = False,
) -> str | dict:
    """Run the multi-agent code review pipeline on a code diff.

    Args:
        code_diff: A unified diff string (e.g., from `git diff`).
        file_paths: Optional list of changed file paths for smarter routing.
        node_callback: Optional callback invoked with agent events.
        capture_verifier_trace: If True, return a dict with trace data.

    Returns:
        The final review as a formatted string, or a dict when
        capture_verifier_trace is True.
    """
    graph = build_graph()
    code_diff = prepare_diff(code_diff)

    initial_state = {
        "code_diff": code_diff,
        "file_paths": file_paths or [],
        "active_agents": [],
        "bug_report": [],
        "security_report": [],
        "quality_report": [],
        "test_report": [],
        "semgrep_report": "",
        "verified_report": "",
        "final_review": "",
        "structured_findings": [],
    }

    config = {"configurable": {"thread_id": str(uuid.uuid4())}}

    # Stream through nodes so we can fire the callback on each step
    if node_callback:
        import time as _time

        result = {}
        for event in graph.stream(initial_state, config=config):
            for node_name, node_output in event.items():
                started = _time.perf_counter()
                node_callback({"event": "start", "node": node_name, "state": dict(initial_state)})
                duration = _time.perf_counter() - started
                node_callback({
                    "event": "end",
                    "node": node_name,
                    "status": "done",
                    "duration_s": duration,
                    "output": node_output,
                })
                result.update(node_output)
        if capture_verifier_trace:
            return result
        return result.get("final_review", "")
    else:
        result = graph.invoke(initial_state, config=config)
        if capture_verifier_trace:
            return dict(result)
        return result["final_review"]


if __name__ == "__main__":
    from examples.sample_diff import SAMPLE_DIFF, SAMPLE_FILE_PATHS

    _log.info("Starting multi-agent code review on sample diff")

    review = run_review(SAMPLE_DIFF, SAMPLE_FILE_PATHS)

    _log.info("Review complete")
    print(review)
