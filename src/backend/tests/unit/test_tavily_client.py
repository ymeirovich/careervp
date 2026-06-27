"""Unit tests for careervp.logic.utils.tavily_client."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from careervp.logic.utils.tavily_client import TAVILY_SEARCH_URL, TavilyClient
from careervp.models.result import ResultCode


@pytest.fixture(autouse=True)
def _clear_tavily_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv('TAVILY_API_KEY', raising=False)
    monkeypatch.delenv('TAVILY_API_KEY_SSM_PARAM', raising=False)


def _http_client_with_json(payload: dict[str, object]) -> AsyncMock:
    response = MagicMock()
    response.raise_for_status = MagicMock()
    response.json.return_value = payload

    http_client = AsyncMock()
    http_client.post.return_value = response
    http_client.__aenter__.return_value = http_client
    http_client.__aexit__.return_value = None
    return http_client


def test_key_from_explicit_arg_takes_priority(monkeypatch: pytest.MonkeyPatch) -> None:
    """Explicit api_key should win over env and skip SSM."""

    async def run() -> None:
        monkeypatch.setenv('TAVILY_API_KEY', 'env-key')
        monkeypatch.setenv('TAVILY_API_KEY_SSM_PARAM', '/careervp/dev/tavily-api-key')
        http_client = _http_client_with_json(
            {
                'results': [
                    {
                        'title': 'Acme About',
                        'url': 'https://acme.com/about',
                        'raw_content': 'Acme Corp builds workflow products.',
                    }
                ]
            }
        )

        with (
            patch.object(TavilyClient, '_fetch_from_ssm', return_value='ssm-key') as mock_fetch_ssm,
            patch('careervp.logic.utils.tavily_client.httpx.AsyncClient', return_value=http_client),
        ):
            result = await TavilyClient(api_key='explicit-key').search('Acme Corp mission products business model')

        assert result.success is True
        assert http_client.post.await_args.args == (TAVILY_SEARCH_URL,)
        assert http_client.post.await_args.kwargs['json']['api_key'] == 'explicit-key'
        mock_fetch_ssm.assert_not_called()

    asyncio.run(run())


def test_key_from_env_when_no_arg(monkeypatch: pytest.MonkeyPatch) -> None:
    """Env key should be used when no explicit api_key is provided."""

    async def run() -> None:
        monkeypatch.setenv('TAVILY_API_KEY', 'env-key')
        monkeypatch.setenv('TAVILY_API_KEY_SSM_PARAM', '/careervp/dev/tavily-api-key')
        http_client = _http_client_with_json(
            {
                'results': [
                    {
                        'title': 'Acme Overview',
                        'url': 'https://acme.com',
                        'content': 'Acme Corp overview content.',
                    }
                ]
            }
        )

        with (
            patch.object(TavilyClient, '_fetch_from_ssm', return_value='ssm-key') as mock_fetch_ssm,
            patch('careervp.logic.utils.tavily_client.httpx.AsyncClient', return_value=http_client),
        ):
            result = await TavilyClient().search('Acme Corp')

        assert result.success is True
        assert http_client.post.await_args.kwargs['json']['api_key'] == 'env-key'
        mock_fetch_ssm.assert_not_called()

    asyncio.run(run())


def test_key_from_ssm_when_no_arg_or_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """SSM should be used when neither explicit arg nor env key is present."""

    async def run() -> None:
        monkeypatch.setenv('TAVILY_API_KEY_SSM_PARAM', '/careervp/dev/tavily-api-key')
        ssm_client = MagicMock()
        ssm_client.get_parameter.return_value = {'Parameter': {'Value': 'ssm-key'}}
        http_client = _http_client_with_json(
            {
                'results': [
                    {
                        'title': 'Acme Overview',
                        'url': 'https://acme.com',
                        'content': 'Acme Corp overview content.',
                    }
                ]
            }
        )

        with (
            patch('careervp.logic.utils.tavily_client.boto3.client', return_value=ssm_client),
            patch('careervp.logic.utils.tavily_client.httpx.AsyncClient', return_value=http_client),
        ):
            result = await TavilyClient().search('Acme Corp')

        assert result.success is True
        assert http_client.post.await_args.kwargs['json']['api_key'] == 'ssm-key'
        ssm_client.get_parameter.assert_called_once_with(Name='/careervp/dev/tavily-api-key', WithDecryption=True)

    asyncio.run(run())


def test_missing_key_returns_clean_result_failure() -> None:
    """Missing key should return Result failure without opening an HTTP client."""

    async def run() -> None:
        with patch('careervp.logic.utils.tavily_client.httpx.AsyncClient') as client_cls:
            result = await TavilyClient().search('Acme Corp')

        assert result.success is False
        assert result.code == ResultCode.MISSING_ENV
        assert result.error is not None
        client_cls.assert_not_called()

    asyncio.run(run())


def test_search_success_normalizes_to_searchresult(monkeypatch: pytest.MonkeyPatch) -> None:
    """TavilyClient.search should normalize payload items into SearchResult."""

    async def run() -> None:
        monkeypatch.setenv('TAVILY_API_KEY', 'env-key')
        http_client = _http_client_with_json(
            {
                'results': [
                    {
                        'title': 'Acme About',
                        'url': 'https://acme.com/about',
                        'raw_content': 'Acme Corp builds workflow products for enterprise teams.',
                    },
                    {
                        'title': 'Missing url',
                        'raw_content': 'should be ignored',
                    },
                ]
            }
        )

        with patch('careervp.logic.utils.tavily_client.httpx.AsyncClient', return_value=http_client):
            result = await TavilyClient().search('Acme Corp mission products business model', include_domains=['acme.com'], max_results=3)

        assert result.success is True
        assert result.data is not None
        assert len(result.data) == 1
        assert result.data[0].title == 'Acme About'
        assert str(result.data[0].url) == 'https://acme.com/about'
        assert result.data[0].snippet == 'Acme Corp builds workflow products for enterprise teams.'
        request_payload = http_client.post.await_args.kwargs['json']
        assert request_payload['include_domains'] == ['acme.com']
        assert request_payload['max_results'] == 3

    asyncio.run(run())


def test_search_provider_error_wrapped_in_result(monkeypatch: pytest.MonkeyPatch) -> None:
    """Provider timeouts or request errors should be wrapped in Result."""

    async def run() -> None:
        monkeypatch.setenv('TAVILY_API_KEY', 'env-key')
        http_client = AsyncMock()
        http_client.post.side_effect = httpx.TimeoutException('timeout')
        http_client.__aenter__.return_value = http_client
        http_client.__aexit__.return_value = None

        with patch('careervp.logic.utils.tavily_client.httpx.AsyncClient', return_value=http_client):
            result = await TavilyClient().search('Acme Corp')

        assert result.success is False
        assert result.code == ResultCode.TIMEOUT

    asyncio.run(run())
