"""LLM client using Anthropic API directly (not Bedrock)."""

from __future__ import annotations

import json
import math
import os
import re
from typing import Any, cast

import boto3
from anthropic import Anthropic

from careervp.logic.cv_summarizer import CVSummarizer
from careervp.logic.llm_cache import LLMResponseCache
from careervp.models.cv import UserCV

# Default model: Haiku for cost efficiency (per CLAUDE.md Decision 1.2)
DEFAULT_MODEL = 'claude-haiku-4-5-20251001'
DEFAULT_TEMPERATURE = 0.3


def _get_anthropic_client() -> Anthropic:
    """Get Anthropic client with API key from env or SSM."""
    api_key = os.environ.get('ANTHROPIC_API_KEY')

    if not api_key:
        ssm_param = os.environ.get('ANTHROPIC_API_KEY_SSM_PARAM')
        if ssm_param:
            ssm_client = boto3.client('ssm')
            response = ssm_client.get_parameter(Name=ssm_param, WithDecryption=True)
            api_key = response['Parameter']['Value']

    if not api_key:
        raise ValueError('ANTHROPIC_API_KEY not found in environment or SSM')

    return Anthropic(api_key=api_key)


class LLMClient:
    """LLM client using Anthropic API directly."""

    _CV_SUMMARY_TRIGGER_TOKENS = 5000
    _CV_SECTION_PATTERN = re.compile(r'(?s)(# CV\s*\n)(.*?)(\n\n# |\Z)')

    def __init__(self, client: Anthropic | None = None, cache: LLMResponseCache | None = None) -> None:
        self._client = client or _get_anthropic_client()
        self._cv_summarizer = CVSummarizer()
        self._cache = cache or LLMResponseCache()

    def generate(
        self,
        prompt: str,
        timeout: int = 300,
        cv: UserCV | None = None,
        model_name: str = DEFAULT_MODEL,
        temperature: float = DEFAULT_TEMPERATURE,
    ) -> dict[str, Any]:
        """Invoke Anthropic API and return parsed JSON payload."""
        _ = timeout
        optimized_prompt = self._build_optimized_prompt(prompt, cv) if cv else prompt

        cache_key = self._get_cache_key(optimized_prompt, cv, model_name, temperature)
        cached = self._check_cache(cache_key)
        if cached is not None:
            return cached

        response = self._call_anthropic(optimized_prompt, model_name, temperature)
        return self._handle_response(response, cache_key)

    def _get_cache_key(
        self,
        prompt: str,
        cv: UserCV | None,
        model_name: str,
        temperature: float,
    ) -> str | None:
        """Generate cache key if prompt is cacheable."""
        if not self._cache.is_cacheable(prompt):
            return None
        return self._cache.generate_cache_key(
            prompt=prompt,
            cv_id=cv.cv_id if cv else None,
            model_name=model_name,
            temperature=temperature,
        )

    def _check_cache(self, cache_key: str | None) -> dict[str, Any] | None:
        """Check cache and return cached value if found."""
        if cache_key is None:
            return None
        cached_value = self._cache.get(cache_key)
        if cached_value is not None:
            try:
                return cast(dict[str, Any], json.loads(cached_value))
            except json.JSONDecodeError:
                self._cache.delete(cache_key)
        return None

    def _call_anthropic(self, prompt: str, model_name: str, temperature: float) -> str:
        """Call Anthropic API and return text content."""
        response = self._client.messages.create(
            model=model_name,
            max_tokens=4096,
            temperature=temperature,
            messages=[{'role': 'user', 'content': prompt}],
        )
        for block in response.content:
            if block.type == 'text':
                return block.text
        return ''

    def _handle_response(self, text_content: str, cache_key: str | None) -> dict[str, Any]:
        """Parse response and handle caching."""
        parsed_response = self._try_parse_json(text_content)

        if cache_key is not None:
            if self._is_error_response(parsed_response):
                self._cache.delete(cache_key)
            else:
                self._cache.set(cache_key, json.dumps(parsed_response, ensure_ascii=False))
        return parsed_response

    def _try_parse_json(self, text: str) -> dict[str, Any]:
        """Try to parse response as JSON, fallback to text wrapper."""
        try:
            return cast(dict[str, Any], json.loads(text))
        except json.JSONDecodeError:
            # Return as JSON with text field
            return {'text': text}

    @staticmethod
    def _is_error_response(payload: dict[str, Any]) -> bool:
        error_fields = ('error', 'errors', 'exception')
        if any(payload.get(field) for field in error_fields):
            return True

        status_code = payload.get('status_code') or payload.get('statusCode')
        return isinstance(status_code, int) and status_code >= 400

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
