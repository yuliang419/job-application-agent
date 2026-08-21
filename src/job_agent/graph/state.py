"""Shared state threaded through the job-application LangGraph workflow."""

from __future__ import annotations

from typing import TypedDict

from job_agent.models import Application, CandidateProfile, Job, MatchReport, MatchReview


class AgentState(TypedDict, total=False):
    """Fields accumulated across the scrape -> match -> review -> cover-letter stages."""

    query: str
    location: str
    cv_path: str
    candidate: CandidateProfile
    jobs: list[Job]
    report: MatchReport
    review: MatchReview
    applications: list[Application]
