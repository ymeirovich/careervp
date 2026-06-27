"""Unit tests for job URL domain validation."""

from __future__ import annotations

from dataclasses import dataclass
from unittest.mock import patch

import httpx

from careervp.logic.utils.domain_validator import validate_job_url


@dataclass
class _FakeResponse:
    status_code: int
    url: str
    text: str = ''


def test_validate_job_url_rejects_invalid_format() -> None:
    result = validate_job_url('example.com/jobs/1')

    assert result.success is True
    assert result.data is not None
    assert result.data.classification == 'invalid_format'


def test_validate_job_url_returns_unreachable_when_dns_fails() -> None:
    with patch('careervp.logic.utils.domain_validator._hostname_resolves', return_value=False):
        result = validate_job_url('https://www.example.com/jobs/1')

    assert result.success is True
    assert result.data is not None
    assert result.data.classification == 'unreachable'
    assert result.data.domain == 'example.com'


def test_validate_job_url_falls_back_to_get_when_head_is_unsupported() -> None:
    calls: list[str] = []

    def _send_request(method: str, url: str) -> _FakeResponse:
        calls.append(method)
        if method == 'HEAD':
            return _FakeResponse(status_code=405, url=url)
        return _FakeResponse(status_code=200, url=url, text='<html><body>Engineering role</body></html>')

    with (
        patch('careervp.logic.utils.domain_validator._hostname_resolves', return_value=True),
        patch('careervp.logic.utils.domain_validator._send_request', side_effect=_send_request),
    ):
        result = validate_job_url('https://www.example.com/jobs/1')

    assert result.success is True
    assert result.data is not None
    assert result.data.classification == 'valid'
    assert result.data.domain == 'example.com'
    assert calls == ['HEAD', 'GET']


def test_validate_job_url_retries_once_after_timeout() -> None:
    attempts = 0

    def _send_request(method: str, url: str) -> _FakeResponse:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise httpx.TimeoutException('timeout')
        return _FakeResponse(status_code=200, url=url)

    with (
        patch('careervp.logic.utils.domain_validator._hostname_resolves', return_value=True),
        patch('careervp.logic.utils.domain_validator._send_request', side_effect=_send_request),
    ):
        result = validate_job_url('https://example.com/jobs/1')

    assert result.success is True
    assert result.data is not None
    assert result.data.classification == 'valid'
    assert attempts == 2


def test_validate_job_url_marks_parked_domains() -> None:
    def _send_request(method: str, url: str) -> _FakeResponse:
        if method == 'HEAD':
            return _FakeResponse(status_code=405, url=url)
        return _FakeResponse(status_code=200, url=url, text='<html><body>This domain is for sale.</body></html>')

    with (
        patch('careervp.logic.utils.domain_validator._hostname_resolves', return_value=True),
        patch('careervp.logic.utils.domain_validator._send_request', side_effect=_send_request),
    ):
        result = validate_job_url('https://example.com/jobs/1')

    assert result.success is True
    assert result.data is not None
    assert result.data.classification == 'parked'
