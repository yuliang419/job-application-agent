"""Thin OpenAI-compatible chat client used to ground matching and cover-letter generation."""

from __future__ import annotations

import json
import re
from typing import Any

from openai import (
    APIConnectionError,
    AuthenticationError,
    OpenAI,
    RateLimitError,
)

from job_agent.config import get_settings
from job_agent.models import CandidateProfile, Job, MatchResult

_REASONING_BLOCK = re.compile(
    r"<(think|thinking|thought|reasoning)>.*?</\1>", re.IGNORECASE | re.DOTALL
)


class LLMRateLimitError(RuntimeError):
    """The configured LLM API key or endpoint is being rate limited."""


class LLMClient:
    """Wraps an OpenAI-compatible chat endpoint for structured, JSON-grounded responses."""

    def __init__(self) -> None:
        settings = get_settings()
        self._client = OpenAI(api_key=settings.llm_api_key, base_url=settings.llm_base_url)
        self._model = settings.llm_model

    def extract_candidate_profile(self, cv_text: str) -> CandidateProfile:
        """Turn raw CV text into a structured candidate profile."""
        payload = self._chat_json(
            system=(
                "Extract a candidate profile from a CV. Respond with a JSON object with "
                "keys: full_name (str), summary (str), skills (list of str), "
                "experience (list of str)."
            ),
            user=cv_text,
        )
        return CandidateProfile.model_validate(payload)

    def extract_job_posting(self, url: str, page_text: str) -> Job:
        """Extract structured job fields from a job-posting page's raw text."""
        payload = self._chat_json(
            system=(
                "Extract job posting details from the raw text of a job listing page. "
                "Respond with a JSON object with keys: title (str), company (str), "
                "location (str), description (str, the role responsibilities and "
                "requirements in plain text)."
            ),
            user=page_text,
        )
        payload["url"] = url
        payload["source"] = "manual"
        return Job.model_validate(payload)

    def score_job(self, candidate: CandidateProfile, job: Job) -> MatchResult:
        """Score one job against a candidate profile."""
        prompt = (
            f"Candidate profile:\n{candidate.model_dump_json()}\n\n"
            f"Job:\ntitle: {job.title}\ncompany: {job.company}\n"
            f"description: {job.description}\n"
        )
        payload = self._chat_json(
            system=(
                "Score how well the candidate matches the job on a 0-100 scale. Respond "
                "with a JSON object with keys: score (int 0-100), matching_skills "
                "(list of str), missing_skills (list of str), explanation (str)."
            ),
            user=prompt,
        )
        return MatchResult.model_validate(payload)

    def tailor_cover_letter(self, base_letter: str, job: Job, candidate: CandidateProfile) -> str:
        """Rewrite a base LaTeX cover letter to target one specific job."""
        prompt = (
            f"Base cover letter (LaTeX):\n{base_letter}\n\n"
            f"Candidate profile:\n{candidate.model_dump_json()}\n\n"
            f"Target job:\ntitle: {job.title}\ncompany: {job.company}\n"
            f"description: {job.description}\n"
        )
        response = self._create_chat_completion(
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Rewrite the body of the given LaTeX cover letter to target the "
                        "supplied job and candidate background. Preserve the LaTeX "
                        "structure and return only the full LaTeX document, no commentary."
                        "Try not to alter the experiences too much, but slightly adapt "
                        "them to highlight skills matching the job requirements."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
        )
        content = response.choices[0].message.content
        return _REASONING_BLOCK.sub("", content).strip() if content else base_letter

    def _chat_json(self, system: str, user: str) -> dict:
        """Call the chat endpoint and parse a single JSON object response."""
        response = self._create_chat_completion(
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        content = response.choices[0].message.content or "{}"
        return json.loads(_extract_json_object(content))

    def _create_chat_completion(self, **kwargs: Any):
        """Call the chat endpoint, translating provider errors into clear messages."""
        try:
            return self._client.chat.completions.create(model=self._model, **kwargs)
        except RateLimitError as error:
            raise LLMRateLimitError(
                f"LLM API key hit a rate limit or quota cap for model '{self._model}'. "
                "Wait and retry, use a different key, or reduce request volume "
                "(fewer --pages-per-location / scored jobs per scan)."
            ) from error
        except AuthenticationError as error:
            raise LLMRateLimitError(
                f"LLM API rejected credentials for model '{self._model}'. Check "
                "LLM_API_KEY in .env."
            ) from error
        except APIConnectionError as error:
            raise LLMRateLimitError(
                f"Could not reach the LLM API at {self._client.base_url}. Check "
                "LLM_BASE_URL and your network connection."
            ) from error


def _extract_json_object(content: str) -> str:
    """Isolate a JSON object, discarding any reasoning tags some models leak into content."""
    content = _REASONING_BLOCK.sub("", content).strip()
    start, end = content.find("{"), content.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise ValueError(f"No JSON object found in model response: {content!r}")
    return content[start : end + 1]
