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


def _get_format_from_path(template_path: Path) -> str:
    """Determine format from template file extension."""
    suffix = template_path.suffix.lower()
    if suffix == ".txt":
        return "txt"
    elif suffix == ".tex":
        return "tex"
    else:
        raise ValueError(f"Unsupported template extension '{suffix}'. Must be .txt or .tex")


def generate_cover_letter(
    job: Job, candidate: CandidateProfile, llm: LLMClient, template_path: Path
) -> tuple[str, str]:
    """Tailor the cover letter template for one job and return (content, format).
    
    Args:
        job: The job for which the cover letter is being generated.
        candidate: The candidate profile.
        llm: The LLM client.
        template_path: Path to the cover letter template file (.txt or .tex).
    
    Returns:
        Tuple of (cover_letter_text, format) where format is 'tex' or 'txt'.
    """
    if not template_path.exists():
        raise FileNotFoundError(f"Template file not found: {template_path}")
    
    base_letter = template_path.read_text()
    letter_format = _get_format_from_path(template_path)
    tailored_letter = llm.tailor_cover_letter(base_letter, job, candidate)
    return tailored_letter, letter_format


def save_cover_letter(job: Job, letter_content: str, format: str) -> Path:
    """Write a tailored cover letter under data/applications/<job-slug>/ and return its path.
    
    Args:
        job: The job for which the cover letter was generated.
        letter_content: The cover letter text.
        format: The format ('tex' for LaTeX, 'txt' for plain text).
    
    Returns:
        Path to the saved cover letter file.
    """
    if format not in ("tex", "txt"):
        raise ValueError(f"Unsupported format '{format}'. Must be 'tex' or 'txt'.")
    
    settings = get_settings()
    out_dir = settings.data_dir / "applications" / _job_slug(job)
    out_dir.mkdir(parents=True, exist_ok=True)
    
    out_path = out_dir / f"cover_letter.{format}"
    out_path.write_text(letter_content)
    return out_path
