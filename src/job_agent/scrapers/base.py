"""Shared contract for job-board adapters."""

from abc import ABC, abstractmethod
from typing import Iterable
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from job_agent.models import Job


class JobBoardAccessError(RuntimeError):
    """A board denied access to an automated public-page request."""


class JobBoardScraper(ABC):
    """Find jobs from one board and return application job records."""

    @abstractmethod
    def search(self, query: str, location: str) -> list[Job]:
        """Return jobs matching one query and location."""

    @staticmethod
    def _fetch(url: str, timeout: float) -> str:
        """Fetch one public board page as UTF-8 text."""
        request = Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (compatible; JobSearchClient/1.0)"
            },
        )
        try:
            with urlopen(request, timeout=timeout) as response:
                return response.read().decode("utf-8", errors="replace")
        except HTTPError as error:
            if error.code == 403:
                raise JobBoardAccessError(
                    "Board denied this automated request (HTTP 403). Use a "
                    "board-approved API, export, or manually supplied job "
                    "URLs instead of retrying."
                ) from error
            raise

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