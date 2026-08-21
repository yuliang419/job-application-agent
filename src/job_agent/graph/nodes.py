"""Node functions for the scan -> match -> human review -> cover-letter graph."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from langgraph.config import get_stream_writer
from langgraph.types import interrupt

from job_agent.cover_letter_editor import generate_cover_letter, save_cover_letter
from job_agent.document_parser import PdfDocumentParser
from job_agent.graph.state import AgentState
from job_agent.llm import LLMClient
from job_agent.matcher import build_match_report
from job_agent.models import Application, MatchReport, MatchReview
from job_agent.scrapers import get_scrapers


@lru_cache(maxsize=1)
def _get_llm() -> LLMClient:
    """Build the LLM client on first use so importing this module needs no credentials."""
    return LLMClient()


def parse_cv(state: AgentState) -> dict:
    """Extract a structured candidate profile from the configured CV file."""
    cv_text = PdfDocumentParser(Path(state["cv_path"])).parse()
    return {"candidate": _get_llm().extract_candidate_profile(cv_text)}


def scrape_jobs(state: AgentState) -> dict:
    """Collect jobs for the requested query and location from every registered board."""
    writer = get_stream_writer()
    scrapers = get_scrapers()
    jobs = []
    for done, scraper in enumerate(scrapers, start=1):
        jobs.extend(scraper.search(state["query"], state["location"]))
        writer({"stage": "scrape_jobs", "done": done, "total": len(scrapers)})
    return {"jobs": jobs}


def score_jobs(state: AgentState) -> dict:
    """Rank scraped jobs against the candidate profile, keeping the top 10."""
    writer = get_stream_writer()

    def on_scored(done: int, total: int) -> None:
        writer({"stage": "score_jobs", "done": done, "total": total})

    report = build_match_report(state["candidate"], state["jobs"], _get_llm(), on_scored)
    return {"report": report}


def human_review(state: AgentState) -> dict:
    """Pause the graph and wait for a human decision on which jobs to pursue."""
    report = MatchReport.model_validate(state["report"])
    resume_value = interrupt({"report": report.model_dump(mode="json")})
    return {"review": MatchReview.model_validate(resume_value)}


def generate_letters(state: AgentState) -> dict:
    """Tailor and save a cover letter for every job the human approved."""
    review = MatchReview.model_validate(state["review"])
    report = MatchReport.model_validate(state["report"])
    approved_urls = {str(url) for url in review.selected_job_urls}

    applications = []
    for ranked in report.jobs:
        if str(ranked.job.url) not in approved_urls:
            continue
        letter = generate_cover_letter(ranked.job, report.candidate, _get_llm())
        save_cover_letter(ranked.job, letter)
        applications.append(
            Application(
                job=ranked.job,
                candidate=report.candidate,
                match=ranked.match,
                cover_letter=letter,
            )
        )
    return {"applications": applications}
