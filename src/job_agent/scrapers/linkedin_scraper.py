"""Utilities for collecting publicly visible LinkedIn job search listings.

These helpers only request LinkedIn's public guest job-search pages.  Callers
are responsible for complying with LinkedIn's terms, robots directives, and
applicable rate limits.
"""

from __future__ import annotations

import re
import time
from html import unescape
from typing import Iterable, Iterator, Sequence
from urllib.parse import urlencode

from job_agent.models import Job

from .base import JobBoardScraper


LINKEDIN_GUEST_JOBS_URL = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"

# LinkedIn's public job-search experience filter values.
EXPERIENCE_LEVELS: dict[str, str] = {
    "internship": "1",
    "entry": "2",
    "associate": "3",
    "mid-senior": "4",
    "director": "5",
    "executive": "6",
}

class LinkedInScraper(JobBoardScraper):
    """Collect public LinkedIn guest-search jobs."""

    def __init__(
        self,
        experience_levels: Sequence[str] | None = None,
        *,
        pages_per_location: int = 1,
        page_size: int = 25,
        delay_seconds: float = 1.0,
        timeout: float = 15.0,
    ) -> None:
        self.experience_levels = experience_levels
        self.pages_per_location = pages_per_location
        self.page_size = page_size
        self.delay_seconds = delay_seconds
        self.timeout = timeout

    def search(self, query: str, location: str) -> list[Job]:
        """Return shared job records for query and location."""
        return scrape_jobs(
            keywords=query,
            locations=[location],
            experience_levels=self.experience_levels,
            pages_per_location=self.pages_per_location,
            page_size=self.page_size,
            delay_seconds=self.delay_seconds,
            timeout=self.timeout,
        )


def build_search_url(
    keywords: str,
    location: str,
    experience_levels: Sequence[str] | None = None,
    *,
    start: int = 0,
) -> str:
    """Build a public LinkedIn guest-search URL for the supplied criteria.

    ``experience_levels`` accepts: internship, entry, associate, mid-senior,
    director, and executive. Multiple values are sent as an OR filter.
    """
    if not keywords.strip():
        raise ValueError("keywords must not be empty")
    if not location.strip():
        raise ValueError("location must not be empty")
    if start < 0:
        raise ValueError("start must be zero or greater")

    params: dict[str, str | int] = {
        "keywords": keywords.strip(),
        "location": location.strip(),
        "start": start,
    }
    if experience_levels:
        normalized = [level.lower().strip() for level in experience_levels]
        invalid = sorted(set(normalized).difference(EXPERIENCE_LEVELS))
        if invalid:
            raise ValueError(f"unsupported experience level(s): {', '.join(invalid)}")
        params["f_E"] = ",".join(EXPERIENCE_LEVELS[level] for level in normalized)

    return f"{LINKEDIN_GUEST_JOBS_URL}?{urlencode(params)}"


def scrape_jobs(
    keywords: str,
    locations: Iterable[str],
    experience_levels: Sequence[str] | None = None,
    *,
    pages_per_location: int = 1,
    page_size: int = 25,
    delay_seconds: float = 1.0,
    timeout: float = 15.0,
) -> list[Job]:
    """Fetch and return de-duplicated shared job records."""
    if pages_per_location < 1:
        raise ValueError("pages_per_location must be at least 1")
    if page_size < 1:
        raise ValueError("page_size must be at least 1")

    jobs: list[Job] = []
    for location in locations:
        for page in range(pages_per_location):
            url = build_search_url(keywords, location, experience_levels, start=page * page_size)
            jobs.extend(_parse_job_cards(JobBoardScraper._fetch(url, timeout)))
            if delay_seconds > 0 and page < pages_per_location - 1:
                time.sleep(delay_seconds)
    return JobBoardScraper._deduplicate(jobs)


def _parse_job_cards(html: str) -> Iterator[Job]:
    """Extract shared job fields present in guest-search result cards."""
    for card in re.findall(r'<li\b[\s\S]*?</li>', html):
        link_match = re.search(r'<a[^>]+href="([^\"]+)"', card)
        title_match = re.search(r'<h3[^>]*>([\s\S]*?)</h3>', card)
        company_match = re.search(r'<h4[^>]*>([\s\S]*?)</h4>', card)
        location_match = re.search(r'class="[^\"]*job-search-card__location[^\"]*"[^>]*>([\s\S]*?)</', card)
        if not (link_match and title_match and company_match and location_match):
            continue
        yield Job(
            title=_clean(title_match.group(1)),
            company=_clean(company_match.group(1)),
            location=_clean(location_match.group(1)),
            description="Description unavailable from LinkedIn search result.",
            url=unescape(link_match.group(1)).split("?")[0],
            source="LinkedIn",
        )


def _clean(value: str) -> str:
    return re.sub(r"\s+", " ", unescape(re.sub(r"<[^>]+>", "", value))).strip()