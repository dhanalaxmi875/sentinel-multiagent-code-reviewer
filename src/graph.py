"""LangGraph pipeline for SentinelCode multi-agent code review."""

from langgraph.graph import END, START, StateGraph
from langgraph.checkpoint.memory import MemorySaver

from src.state import ReviewState
from src.agents.orchestrator import orchestrator_node
from src.agents.bug_detector import bug_detector_node
from src.agents.security import security_node
from src.agents.code_quality import code_quality_node
from src.agents.test_coverage import test_coverage_node
from src.agents.verifier import verifier_node
from src.agents.summarizer import summarizer_node
from src.agents.semgrep_scanner import semgrep_scanner_node

_SPECIALIST_AGENTS = {
    "bug_detector",
    "security",
    "code_quality",
    "test_coverage",
}


def _route_to_specialists(state: ReviewState) -> list[str]:
    """Return agents selected by the orchestrator."""
    return [agent for agent in state["active_agents"] if agent in _SPECIALIST_AGENTS]


def build_graph():
    """Build SentinelCode's multi-agent review workflow.

    Topology:
        orchestrator
            ↓
        specialist agents + semgrep_scanner (parallel)
            ↓
        verifier
            ↓
        summarizer
            ↓
        END
    """
    graph = StateGraph(ReviewState)

    graph.add_node("orchestrator", orchestrator_node)
    graph.add_node("bug_detector", bug_detector_node)
    graph.add_node("security", security_node)
    graph.add_node("code_quality", code_quality_node)
    graph.add_node("test_coverage", test_coverage_node)
    graph.add_node("verifier", verifier_node)
    graph.add_node("summarizer", summarizer_node)
    graph.add_node("semgrep_scanner", semgrep_scanner_node)

    graph.add_edge(START, "orchestrator")
    graph.add_edge("orchestrator", "semgrep_scanner")

    graph.add_conditional_edges(
        "orchestrator",
        _route_to_specialists,
        {agent: agent for agent in _SPECIALIST_AGENTS},
    )

    # All specialist reviews and Semgrep scan must complete before verification.
    for agent in _SPECIALIST_AGENTS:
        graph.add_edge(agent, "verifier")
    graph.add_edge("semgrep_scanner", "verifier")

    graph.add_edge("verifier", "summarizer")
    graph.add_edge("summarizer", END)

    return graph.compile(checkpointer=MemorySaver())