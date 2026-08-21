"""Job-board adapters."""

from __future__ import annotations

import inspect

from .base import JobBoardAccessError, JobBoardScraper
from .linkedin_scraper import LinkedInScraper

SCRAPER_REGISTRY: dict[str, type[JobBoardScraper]] = {
	"linkedin": LinkedInScraper,
}


def get_scrapers(names: list[str] | None = None, **kwargs: object) -> list[JobBoardScraper]:
	"""Instantiate the requested scrapers, defaulting to every registered board.

	Extra ``kwargs`` (e.g. ``experience_levels``, ``pages_per_location``) are passed
	to each scraper's constructor only if it accepts them, since boards differ in
	which options they support.
	"""
	selected = names or list(SCRAPER_REGISTRY)
	scrapers = []
	for name in selected:
		cls = SCRAPER_REGISTRY[name]
		accepted = inspect.signature(cls.__init__).parameters
		supported_kwargs = {
			key: value for key, value in kwargs.items() if key in accepted and value is not None
		}
		scrapers.append(cls(**supported_kwargs))
	return scrapers


__all__ = [
	"JobBoardAccessError",
	"JobBoardScraper",
	"LinkedInScraper",
	"SCRAPER_REGISTRY",
	"get_scrapers",
]