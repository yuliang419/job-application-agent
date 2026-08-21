"""Application configuration loaded from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


def _as_bool(value: str) -> bool:
	return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
	"""Runtime settings for the job application agent."""

	llm_api_key: str | None
	llm_model: str
	llm_base_url: str | None
	headless_browser: bool
	data_dir: Path


@lru_cache(maxsize=1)
def get_settings() -> Settings:
	"""Return settings using environment variables with safe local defaults."""
	return Settings(
		llm_api_key=os.getenv("LLM_API_KEY"),
		llm_model=os.getenv("LLM_MODEL", "gpt-4o-mini"),
		llm_base_url=os.getenv("LLM_BASE_URL"),
		headless_browser=_as_bool(os.getenv("HEADLESS_BROWSER", "true")),
		data_dir=Path(os.getenv("JOB_AGENT_DATA_DIR", "data")),
	)
