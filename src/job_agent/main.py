"""Command-line entry point for the job-application agent workflow."""

from __future__ import annotations

from pathlib import Path

import typer
from langchain_core.runnables import RunnableConfig
from langgraph.types import Command
from rich.console import Console
from rich.progress import Progress, TaskID
from rich.table import Table

from job_agent.config import get_settings
from job_agent.cover_letter_editor import generate_cover_letter, save_cover_letter
from job_agent.document_parser import PdfDocumentParser
from job_agent.graph import build_graph
from job_agent.job_posting import fetch_job_posting_text
from job_agent.llm import LLMClient
from job_agent.models import Application, MatchReport, MatchReview
from job_agent.scrapers import SCRAPER_REGISTRY

app = typer.Typer(help="Scan job boards, score matches, and draft cover letters for approved jobs.")
console = Console()


@app.command()
def scan(
    keywords: str,
    location: str,
    thread_id: str = typer.Option(..., help="Unique id used to resume this run via 'review'."),
    cv: Path = typer.Option(..., exists=True, help="Path to the candidate's CV PDF."),
    job_board: str = typer.Option(
        "linkedin", help=f"Job board to scrape. One of: {', '.join(SCRAPER_REGISTRY)}."
    ),
    experience_level: list[str] = typer.Option(
        [],
        help=(
            "Optional experience-level filter(s), repeatable (board-specific, e.g. "
            "internship, entry, associate, mid-senior, director, executive for LinkedIn)."
        ),
    ),
    date_posted: str = typer.Option(
        None,
        help="Optional posting-age filter (board-specific, e.g. day, week, month for LinkedIn).",
    ),
    pages_per_location: int = typer.Option(1, min=1, help="Result pages to fetch per location."),
) -> None:
    """Scrape jobs, score them against the CV, and print the top-10 match report."""
    if job_board not in SCRAPER_REGISTRY:
        raise typer.BadParameter(
            f"Unknown job board '{job_board}'. Choose one of: {', '.join(SCRAPER_REGISTRY)}."
        )

    with build_graph() as graph:
        config: RunnableConfig = {"configurable": {"thread_id": thread_id}}
        inputs = {
            "query": keywords,
            "location": location,
            "cv_path": str(cv),
            "job_board": job_board,
            "experience_levels": experience_level,
            "date_posted": date_posted,
            "pages_per_location": pages_per_location,
        }

        with Progress(console=console) as progress:
            tasks: dict[str, TaskID] = {}
            for chunk in graph.stream(inputs, config=config, stream_mode="custom"):
                stage, done, total = chunk["stage"], chunk["done"], chunk["total"]
                if stage not in tasks:
                    tasks[stage] = progress.add_task(stage, total=total)
                progress.update(tasks[stage], completed=done)

        report = MatchReport.model_validate(graph.get_state(config).values["report"])
        report_path = _save_report(report, thread_id)
        console.print(f"Saved match report to {report_path}")
        console.print(f"Run `job-agent review {thread_id} --approve <url>` to continue.")



@app.command()
def review(
    thread_id: str,
    reviewer: str = typer.Option(..., help="Name recorded on the review decision."),
    approve: list[str] = typer.Option([], help="Job URL(s) to approve for a cover letter."),
    template: Path = typer.Option("data/cover_letter.tex", exists=True, help="Path to cover letter template (.txt or .tex)."),
) -> None:
    """Resume a scan with the human's approved job URLs and generate cover letters."""
    with build_graph() as graph:
        config: RunnableConfig = {"configurable": {"thread_id": thread_id}}
        match_review = MatchReview(reviewer=reviewer, selected_job_urls=approve)
        result = graph.invoke(
            Command(resume=match_review.model_dump(mode="json"), template_path=str(template)),
            config=config,
        )

        applications = [Application.model_validate(item) for item in result["applications"]]
        if not applications:
            console.print("No jobs were approved; no cover letters generated.")
            return
        for application in applications:
            console.print(
                f"Saved cover letter for {application.job.company} - {application.job.title}"
            )


@app.command()
def letter(
    cv: Path = typer.Option(..., exists=True, help="Path to the candidate's CV PDF."),
    url: str = typer.Option(..., help="Job posting URL."),
    template: Path = typer.Option("data/cover_letter.tex", exists=True, help="Path to cover letter template (.txt or .tex)."),
) -> None:
    """Generate a tailored cover letter from just a CV and a job posting URL."""
    llm = LLMClient()
    job = llm.extract_job_posting(url, fetch_job_posting_text(url))

    cv_text = PdfDocumentParser(cv).parse()
    candidate = llm.extract_candidate_profile(cv_text)
    letter_content, letter_format = generate_cover_letter(job, candidate, llm, template)
    letter_path = save_cover_letter(job, letter_content, letter_format)
    console.print(f"Saved cover letter to {letter_path}")


def _save_report(report: MatchReport, thread_id: str) -> Path:
    """Render the ranked match report to a text file wide enough to keep full URLs."""
    table = Table(title="Top job matches")
    table.add_column("Rank")
    table.add_column("Score")
    table.add_column("Title")
    table.add_column("Company")
    table.add_column("URL", overflow="fold", no_wrap=True)
    for ranked in report.jobs:
        table.add_row(
            str(ranked.rank),
            str(ranked.match.score),
            ranked.job.title,
            ranked.job.company,
            str(ranked.job.url),
        )

    longest_url = max((len(str(ranked.job.url)) for ranked in report.jobs), default=0)
    width = 60 + longest_url

    reports_dir = get_settings().data_dir / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    report_path = reports_dir / f"{thread_id}.txt"

    file_console = Console(file=report_path.open("w"), width=width)
    file_console.print(table)
    return report_path


if __name__ == "__main__":
    app()
