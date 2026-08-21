"""Shared HTTP fetch helper for scraping public job pages."""

from __future__ import annotations

from urllib.error import HTTPError
from urllib.request import Request, urlopen


class JobBoardAccessError(RuntimeError):
    """A board denied access to an automated public-page request."""


def fetch(url: str, timeout: float = 15.0) -> str:
    """Fetch one public page as UTF-8 text."""
    request = Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (compatible; JobSearchClient/1.0)"},
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            return response.read().decode("utf-8", errors="replace")
    except HTTPError as error:
        if error.code == 403:
            raise JobBoardAccessError(
                "Page denied this automated request (HTTP 403). Use a "
                "board-approved API, export, or a manually supplied job "
                "description instead of retrying."
            ) from error
        raise
