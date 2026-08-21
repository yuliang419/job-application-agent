"""Job-board adapters."""

from __future__ import annotations

from .base import JobBoardAccessError, JobBoardScraper
from .linkedin_scraper import LinkedInScraper

SCRAPER_REGISTRY: dict[str, type[JobBoardScraper]] = {
	"linkedin": LinkedInScraper,
}


def get_scrapers(names: list[str] | None = None) -> list[JobBoardScraper]:
	"""Instantiate the requested scrapers, defaulting to every registered board."""
	selected = names or list(SCRAPER_REGISTRY)
	return [SCRAPER_REGISTRY[name]() for name in selected]


__all__ = [
	"JobBoardAccessError",
	"JobBoardScraper",
	"LinkedInScraper",
	"SCRAPER_REGISTRY",
	"get_scrapers",
]