"""Tavily search client for company research retrieval."""

from __future__ import annotations

import os
from typing import Any, Final, Literal, cast

import boto3
import httpx
from botocore.exceptions import BotoCoreError, ClientError
from pydantic import HttpUrl

from careervp.handlers.utils.observability import logger
from careervp.models.company import SearchResult
from careervp.models.result import Result, ResultCode

TAVILY_SEARCH_URL: Final[str] = 'https://api.tavily.com/search'
TAVILY_TIMEOUT: Final[float] = 20.0
SearchDepth = Literal['basic', 'advanced']


class TavilyClient:
    """Small Result-wrapped Tavily REST client.

    API key resolution mirrors the LLM client order:
    explicit argument > TAVILY_API_KEY environment variable > SSM parameter.
    """

    def __init__(self, api_key: str | None = None) -> None:
        self._api_key = api_key or os.environ.get('TAVILY_API_KEY')

        if not self._api_key:
            ssm_param_name = os.environ.get('TAVILY_API_KEY_SSM_PARAM')
            if ssm_param_name:
                logger.info('Fetching TAVILY_API_KEY from SSM Parameter Store', parameter=ssm_param_name)
                self._api_key = self._fetch_from_ssm(ssm_param_name)

    async def search(
        self,
        query: str,
        *,
        search_depth: SearchDepth = 'advanced',
        include_raw_content: bool = True,
        max_results: int = 5,
        include_domains: list[str] | None = None,
    ) -> Result[list[SearchResult]]:
        """Run a Tavily search and return normalized SearchResult objects."""
        if not self._api_key:
            return Result(success=False, error='TAVILY_API_KEY not found in environment variable or SSM Parameter Store', code=ResultCode.MISSING_ENV)

        payload: dict[str, Any] = {
            'api_key': self._api_key,
            'query': query,
            'search_depth': search_depth,
            'include_raw_content': include_raw_content,
            'max_results': max_results,
        }
        if include_domains:
            payload['include_domains'] = include_domains

        try:
            async with httpx.AsyncClient(timeout=TAVILY_TIMEOUT) as client:
                response = await client.post(TAVILY_SEARCH_URL, json=payload)
                response.raise_for_status()
        except httpx.TimeoutException:
            return Result(success=False, error='Tavily search timeout', code=ResultCode.TIMEOUT)
        except httpx.HTTPStatusError as exc:
            status_code = exc.response.status_code if exc.response else 'unknown'
            return Result(success=False, error=f'Tavily search HTTP {status_code}', code=ResultCode.SEARCH_FAILED)
        except httpx.RequestError as exc:
            return Result(success=False, error=f'Tavily search request error: {exc}', code=ResultCode.SEARCH_FAILED)
        except Exception as exc:  # noqa: BLE001
            return Result(success=False, error=f'Tavily search error: {exc}', code=ResultCode.SEARCH_FAILED)

        try:
            response_payload = response.json()
        except ValueError:
            return Result(success=False, error='Tavily search returned invalid JSON', code=ResultCode.SEARCH_FAILED)

        results = _parse_tavily_results(response_payload)
        if not results:
            return Result(success=False, error='No Tavily search results found', code=ResultCode.NO_RESULTS)
        return Result(success=True, data=results, code=ResultCode.SUCCESS)

    def _fetch_from_ssm(self, parameter_name: str) -> str | None:
        """Fetch the Tavily API key from SSM Parameter Store."""
        try:
            ssm_client = boto3.client('ssm')
            response = ssm_client.get_parameter(Name=parameter_name, WithDecryption=True)
            api_key: str = response['Parameter']['Value']
            logger.info('Successfully fetched TAVILY_API_KEY from SSM', parameter=parameter_name)
            return api_key
        except (ClientError, BotoCoreError) as exc:
            logger.error('Failed to fetch Tavily parameter from SSM', parameter=parameter_name, error=str(exc))
            return None
        except KeyError as exc:
            logger.error('Unexpected Tavily SSM response structure', parameter=parameter_name, error=str(exc))
            return None


def _parse_tavily_results(payload: Any) -> list[SearchResult]:
    """Normalize Tavily response JSON into SearchResult items."""
    if not isinstance(payload, dict):
        return []
    raw_results = payload.get('results')
    if not isinstance(raw_results, list):
        return []

    parsed: list[SearchResult] = []
    for item in raw_results:
        if not isinstance(item, dict):
            continue
        title = _coerce_text(item.get('title'))
        url = _coerce_text(item.get('url'))
        snippet = _coerce_text(item.get('raw_content')) or _coerce_text(item.get('content'))
        if not title or not url or not snippet:
            continue
        try:
            parsed.append(SearchResult(title=title, url=cast(HttpUrl, url), snippet=snippet))
        except ValueError:
            continue
    return parsed


def _coerce_text(value: Any) -> str:
    if isinstance(value, str):
        return value.strip()
    return ''


__all__ = ['TAVILY_SEARCH_URL', 'TAVILY_TIMEOUT', 'TavilyClient']
