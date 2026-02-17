"""Compatibility LLM client for CV tailoring tests."""

from __future__ import annotations

import json
import math
import re
from typing import Any, cast

import boto3

from careervp.logic.cv_summarizer import CVSummarizer
from careervp.models.cv import UserCV

bedrock_client = boto3.client('bedrock-runtime')


class LLMClient:
    """Simple LLM client wrapper used by CV tailoring handler."""

    _CV_SUMMARY_TRIGGER_TOKENS = 5000
    _CV_SECTION_PATTERN = re.compile(r'(?s)(# CV\s*\n)(.*?)(\n\n# |\Z)')

    def __init__(self, client: Any | None = None) -> None:
        self._client = client or bedrock_client
        self._cv_summarizer = CVSummarizer()

    def generate(self, prompt: str, timeout: int = 300, cv: UserCV | None = None) -> dict[str, Any]:
        """Invoke Bedrock model and return parsed JSON payload."""
        _ = timeout
        optimized_prompt = prompt
        if cv is not None:
            optimized_prompt = self._build_optimized_prompt(prompt=prompt, cv=cv)

        response = self._client.invoke_model(
            body=json.dumps({'prompt': optimized_prompt}),
            modelId='claude-haiku-4-5-20251001',
        )
        body = response.get('body')
        if hasattr(body, 'read'):
            payload = body.read()
        else:
            payload = body
        if isinstance(payload, bytes):
            payload = payload.decode('utf-8')
        if isinstance(payload, str):
            return cast(dict[str, Any], json.loads(payload))
        return cast(dict[str, Any], payload)

    def _build_optimized_prompt(self, prompt: str, cv: UserCV) -> str:
        cv_payload = self._maybe_summarize_cv(cv)
        if not isinstance(cv_payload, dict):
            return prompt

        summarized_cv = self._format_summarized_cv(cv, cv_payload)
        return self._replace_cv_section(prompt, summarized_cv)

    def _maybe_summarize_cv(self, cv: UserCV) -> UserCV | dict[str, Any]:
        """Summarize only when raw CV context is large enough to impact costs."""
        cv_json = json.dumps(cv.model_dump(mode='json'), ensure_ascii=False)
        cv_token_count = self._estimate_tokens(cv_json)
        if cv_token_count <= self._CV_SUMMARY_TRIGGER_TOKENS:
            return cv
        return self._cv_summarizer.summarize(cv)

    def _format_summarized_cv(self, cv: UserCV, summarized_cv: dict[str, Any]) -> str:
        lines = [f'Name: {cv.full_name}']

        summary = str(summarized_cv.get('summary', '')).strip()
        if summary:
            lines.append(f'Summary: {summary}')

        experience_entries = summarized_cv.get('experience', [])
        if isinstance(experience_entries, list) and experience_entries:
            lines.append('Experience:')
            for entry in experience_entries:
                lines.append(f'- {entry}')

        extracted_skills = summarized_cv.get('skills_extracted', [])
        if isinstance(extracted_skills, list) and extracted_skills:
            skill_values = [str(skill) for skill in extracted_skills]
            lines.append('Skills: ' + ', '.join(skill_values))

        education = str(summarized_cv.get('education', '')).strip()
        if education:
            lines.append(f'Education: {education}')

        token_count = summarized_cv.get('token_count', 0)
        was_truncated = summarized_cv.get('was_truncated', False)
        lines.append(f'Compression Metadata: token_count={token_count}, was_truncated={was_truncated}')

        return '\n'.join(lines)

    def _replace_cv_section(self, prompt: str, summarized_cv_text: str) -> str:
        match = self._CV_SECTION_PATTERN.search(prompt)
        if match is None:
            return f'{prompt}\n\n# CV\n{summarized_cv_text}'

        prefix = prompt[: match.start(2)]
        suffix = prompt[match.end(2) :]
        return f'{prefix}{summarized_cv_text}{suffix}'

    @staticmethod
    def _estimate_tokens(text: str) -> int:
        if not text:
            return 0
        return max(1, math.ceil(len(text) / 4))
