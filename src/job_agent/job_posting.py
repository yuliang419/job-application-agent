"""Fetch a job-posting page and clean it into plain text for LLM extraction."""

from __future__ import annotations

import re
from html import unescape

from job_agent.http import fetch

_TAG_BLOCK = re.compile(r"<(script|style)[^>]*>.*?</\1>", re.IGNORECASE | re.DOTALL)
_TAG = re.compile(r"<[^>]+>")
_WHITESPACE = re.compile(r"\s+")
_MAX_CHARS = 12000


def fetch_job_posting_text(url: str, timeout: float = 15.0) -> str:
    """Download one job-posting page and return cleaned, truncated plain text."""
    html = fetch(url, timeout)
    text = _TAG_BLOCK.sub(" ", html)
    text = _TAG.sub(" ", text)
    text = unescape(text)
    text = _WHITESPACE.sub(" ", text).strip()
    return text[:_MAX_CHARS]
