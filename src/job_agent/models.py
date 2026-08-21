"""Validated data contracts for job-application workflow."""

from datetime import datetime
from enum import Enum
from typing import Annotated, Optional

from pydantic import AfterValidator, BaseModel, Field, HttpUrl, TypeAdapter

_http_url_adapter = TypeAdapter(HttpUrl)


def _validate_http_url(value: str) -> str:
    """Confirm one URL is well-formed http(s), keeping the field a plain str.

    A plain str (rather than pydantic.HttpUrl) is required because LangGraph's
    msgpack checkpoint serializer cannot serialize pydantic's Url wrapper type.
    """
    _http_url_adapter.validate_python(value)
    return value


HttpUrlStr = Annotated[str, AfterValidator(_validate_http_url)]


class ApplicationStatus(str, Enum):
    """Stages of an application. Submission requires human approval."""

    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    SUBMITTED = "submitted"


class Job(BaseModel):
    """Role discovered from a job board."""

    title: str = Field(min_length=1)
    company: str = Field(min_length=1)
    location: str = Field(min_length=1)
    description: str = Field(min_length=1)
    url: HttpUrlStr
    source: str = Field(min_length=1)
    discovered_at: datetime = Field(default_factory=datetime.utcnow)


class CandidateProfile(BaseModel):
    """Structured candidate information extracted from a CV."""

    full_name: str = Field(min_length=1)
    summary: str = Field(min_length=1)
    skills: list[str] = Field(default_factory=list)
    experience: list[str] = Field(default_factory=list)


class MatchResult(BaseModel):
    """CV-to-job matching outcome."""

    score: int = Field(ge=0, le=100)
    matching_skills: list[str] = Field(default_factory=list)
    missing_skills: list[str] = Field(default_factory=list)
    explanation: str = Field(min_length=1)


class RankedJob(BaseModel):
    """One job and its CV match result in a generated report."""

    job: Job
    match: MatchResult
    rank: int = Field(ge=1)


class MatchReport(BaseModel):
    """Highest-scoring jobs presented for human selection."""

    candidate: CandidateProfile
    jobs: list[RankedJob] = Field(min_length=1, max_length=10)
    generated_at: datetime = Field(default_factory=datetime.utcnow)


class MatchReview(BaseModel):
    """Human selection of report jobs eligible for letter generation."""

    reviewer: str = Field(min_length=1)
    selected_job_urls: list[HttpUrlStr] = Field(default_factory=list)
    comments: str = ""
    decided_at: datetime = Field(default_factory=datetime.utcnow)


class ReviewDecision(BaseModel):
    """Human decision recorded after cover-letter generation."""

    reviewer: str = Field(min_length=1)
    approved: bool
    comments: str = ""
    decided_at: datetime = Field(default_factory=datetime.utcnow)


class Application(BaseModel):
    """Application package held for human review before submission."""

    job: Job
    candidate: CandidateProfile
    match: MatchResult
    cover_letter: str = Field(min_length=1)
    status: ApplicationStatus = ApplicationStatus.PENDING_REVIEW
    review: Optional[ReviewDecision] = None
    submitted_at: Optional[datetime] = None