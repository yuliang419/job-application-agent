"""Rank scraped jobs against a candidate profile into a top-10 report."""

from __future__ import annotations

from typing import Callable, Optional

from job_agent.llm import LLMClient
from job_agent.models import CandidateProfile, Job, MatchReport, RankedJob


def build_match_report(
    candidate: CandidateProfile,
    jobs: list[Job],
    llm: LLMClient,
    on_scored: Optional[Callable[[int, int], None]] = None,
) -> MatchReport:
    """Score every job, then keep the top 10 by score as a ranked report."""
    total = len(jobs)
    scored = []
    for index, job in enumerate(jobs, start=1):
        scored.append((job, llm.score_job(candidate, job)))
        if on_scored:
            on_scored(index, total)
    scored.sort(key=lambda pair: pair[1].score, reverse=True)
    top = scored[:10]
    ranked_jobs = [
        RankedJob(job=job, match=match, rank=index + 1)
        for index, (job, match) in enumerate(top)
    ]
    return MatchReport(candidate=candidate, jobs=ranked_jobs)
