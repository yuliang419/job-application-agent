"""Shared contract for job-board adapters."""

from abc import ABC, abstractmethod
from typing import Iterable

from job_agent.http import JobBoardAccessError, fetch
from job_agent.models import Job

__all__ = ["JobBoardAccessError", "JobBoardScraper"]


class JobBoardScraper(ABC):
    """Find jobs from one board and return application job records."""

    @abstractmethod
    def search(self, query: str, location: str) -> list[Job]:
        """Return jobs matching one query and location."""

    @staticmethod
    def _fetch(url: str, timeout: float) -> str:
        """Fetch one public board page as UTF-8 text."""
        return fetch(url, timeout)

    @staticmethod
    def _deduplicate(jobs: Iterable[Job]) -> list[Job]:
        """Return jobs with one record per canonical job URL."""
        unique_jobs: list[Job] = []
        seen_urls: set[str] = set()
        for job in jobs:
            url = str(job.url)
            if url not in seen_urls:
                seen_urls.add(url)
                unique_jobs.append(job)
        return unique_jobs
