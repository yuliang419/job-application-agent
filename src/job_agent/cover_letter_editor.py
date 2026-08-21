"""Generate and persist a tailored cover letter per approved job."""

from __future__ import annotations

import re
from pathlib import Path

from job_agent.config import get_settings
from job_agent.llm import LLMClient
from job_agent.models import CandidateProfile, Job


def _job_slug(job: Job) -> str:
    """Return a filesystem-safe folder name for one job."""
    raw = f"{job.company}-{job.title}"
    return re.sub(r"[^a-zA-Z0-9]+", "-", raw).strip("-").lower()


def generate_cover_letter(job: Job, candidate: CandidateProfile, llm: LLMClient) -> str:
    """Tailor the base LaTeX template for one job and return the LaTeX text."""
    settings = get_settings()
    base_letter = (settings.data_dir / "cover_letter.tex").read_text()
    return llm.tailor_cover_letter(base_letter, job, candidate)


def save_cover_letter(job: Job, letter_tex: str) -> Path:
    """Write a tailored cover letter under data/applications/<job-slug>/ and return its path."""
    settings = get_settings()
    out_dir = settings.data_dir / "applications" / _job_slug(job)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "cover_letter.tex"
    out_path.write_text(letter_tex)
    return out_path
