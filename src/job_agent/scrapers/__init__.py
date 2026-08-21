"""Job-board adapters."""

from .base import JobBoardAccessError, JobBoardScraper
from .linkedin_scraper import LinkedInScraper

__all__ = [
	"JobBoardAccessError",
	"JobBoardScraper",
	"LinkedInScraper",
]