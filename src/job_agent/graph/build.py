"""Compile the scan -> match -> human-review -> cover-letter LangGraph workflow."""

from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from job_agent.config import get_settings
from job_agent.graph.nodes import generate_letters, human_review, parse_cv, scrape_jobs, score_jobs
from job_agent.graph.state import AgentState


@contextmanager
def build_graph() -> Iterator[CompiledStateGraph]:
    """Yield a compiled graph backed by a sqlite checkpointer for cross-run persistence.

    A checkpointer is required because `human_review` interrupts the graph and the
    CLI resumes it in a later, separate process invocation.
    """
    settings = get_settings()
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    db_path = settings.data_dir / "checkpoints.sqlite"

    with SqliteSaver.from_conn_string(str(db_path)) as checkpointer:
        graph = StateGraph(AgentState)
        graph.add_node("parse_cv", parse_cv)
        graph.add_node("scrape_jobs", scrape_jobs)
        graph.add_node("score_jobs", score_jobs)
        graph.add_node("human_review", human_review)
        graph.add_node("generate_letters", generate_letters)

        graph.add_edge(START, "parse_cv")
        graph.add_edge("parse_cv", "scrape_jobs")
        graph.add_edge("scrape_jobs", "score_jobs")
        graph.add_edge("score_jobs", "human_review")
        graph.add_edge("human_review", "generate_letters")
        graph.add_edge("generate_letters", END)

        yield graph.compile(checkpointer=checkpointer)
