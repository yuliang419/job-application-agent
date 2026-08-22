"""Shared state threaded through the job-application LangGraph workflow."""

from __future__ import annotations

from typing_extensions import NotRequired, TypedDict

from job_agent.models import Application, CandidateProfile, Job, MatchReport, MatchReview


class AgentState(TypedDict):
    """Fields accumulated across the scrape -> match -> review -> cover-letter stages.

    The scan/location/CV fields are supplied at graph invocation and always present.
    The rest are only populated once their producing node has run, hence NotRequired.
    """

    query: str
    location: str
    cv_path: str
    job_board: str
    experience_levels: list[str]
    date_posted: str
    pages_per_location: int
    candidate: NotRequired[CandidateProfile]
    jobs: NotRequired[list[Job]]
    report: NotRequired[MatchReport]
    review: NotRequired[MatchReview]
    applications: NotRequired[list[Application]]
