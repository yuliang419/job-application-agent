"""Command-line entry point for the job-application agent workflow."""

from __future__ import annotations

from pathlib import Path

import typer
from langchain_core.runnables import RunnableConfig
from langgraph.types import Command
from rich.console import Console
from rich.progress import Progress, TaskID
from rich.table import Table

from job_agent.graph import build_graph
from job_agent.models import Application, MatchReport, MatchReview

app = typer.Typer(help="Scan job boards, score matches, and draft cover letters for approved jobs.")
console = Console()


@app.command()
def scan(
    query: str,
    location: str,
    thread_id: str = typer.Option(..., help="Unique id used to resume this run via 'review'."),
    cv: Path = typer.Option(..., exists=True, help="Path to the candidate's CV PDF."),
) -> None:
    """Scrape jobs, score them against the CV, and print the top-10 match report."""
    with build_graph() as graph:
        config: RunnableConfig = {"configurable": {"thread_id": thread_id}}
        inputs = {"query": query, "location": location, "cv_path": str(cv)}

        with Progress(console=console) as progress:
            tasks: dict[str, TaskID] = {}
            for chunk in graph.stream(inputs, config=config, stream_mode="custom"):
                stage, done, total = chunk["stage"], chunk["done"], chunk["total"]
                if stage not in tasks:
                    tasks[stage] = progress.add_task(stage, total=total)
                progress.update(tasks[stage], completed=done)

        report = MatchReport.model_validate(graph.get_state(config).values["report"])
        _print_report(report)
        console.print(f"\nRun `job-agent review {thread_id} --approve <url>` to continue.")



@app.command()
def review(
    thread_id: str,
    reviewer: str = typer.Option(..., help="Name recorded on the review decision."),
    approve: list[str] = typer.Option([], help="Job URL(s) to approve for a cover letter."),
) -> None:
    """Resume a scan with the human's approved job URLs and generate cover letters."""
    with build_graph() as graph:
        config: RunnableConfig = {"configurable": {"thread_id": thread_id}}
        match_review = MatchReview(reviewer=reviewer, selected_job_urls=approve)
        result = graph.invoke(Command(resume=match_review.model_dump(mode="json")), config=config)

        applications = [Application.model_validate(item) for item in result["applications"]]
        if not applications:
            console.print("No jobs were approved; no cover letters generated.")
            return
        for application in applications:
            console.print(
                f"Saved cover letter for {application.job.company} - {application.job.title}"
            )


def _print_report(report: MatchReport) -> None:
    """Render a ranked match report as a table."""
    table = Table(title="Top job matches")
    table.add_column("Rank")
    table.add_column("Score")
    table.add_column("Title")
    table.add_column("Company")
    table.add_column("URL")
    for ranked in report.jobs:
        table.add_row(
            str(ranked.rank),
            str(ranked.match.score),
            ranked.job.title,
            ranked.job.company,
            str(ranked.job.url),
        )
    console.print(table)


if __name__ == "__main__":
    app()
