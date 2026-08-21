"""Thin OpenAI-compatible chat client used to ground matching and cover-letter generation."""

from __future__ import annotations

import json

from openai import OpenAI

from job_agent.config import get_settings
from job_agent.models import CandidateProfile, Job, MatchResult


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
        response = self._client.chat.completions.create(
            model=self._model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Rewrite the body of the given LaTeX cover letter to target the "
                        "supplied job and candidate background. Preserve the LaTeX "
                        "structure and return only the full LaTeX document, no commentary."
                        "Try to change the text as little as possible while still tailoring "
                        "it to the job and candidate."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
        )
        return response.choices[0].message.content or base_letter

    def _chat_json(self, system: str, user: str) -> dict:
        """Call the chat endpoint and parse a single JSON object response."""
        response = self._client.chat.completions.create(
            model=self._model,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        content = response.choices[0].message.content or "{}"
        return json.loads(content)
