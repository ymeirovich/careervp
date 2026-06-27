"""Job URL validation utilities for application creation."""

from __future__ import annotations

import socket
from dataclasses import dataclass
from typing import Final, Literal
from urllib.parse import SplitResult, urlsplit, urlunsplit

import httpx
from pydantic import BaseModel, Field

from careervp.models.result import Result, ResultCode

DomainValidationClassification = Literal['valid', 'unreachable', 'parked', 'invalid_format']

REQUEST_TIMEOUT_SECONDS: Final[float] = 2.0
REQUEST_RETRY_ATTEMPTS: Final[int] = 2
HEAD_UNSUPPORTED_STATUSES: Final[set[int]] = {405, 501}
USER_AGENT: Final[str] = 'CareerVP/1.0 (+https://careervp.ai)'
PARKING_HOST_MARKERS: Final[tuple[str, ...]] = (
    'afternic',
    'bodis',
    'dan.com',
    'domainmarket',
    'hugedomains',
    'parkingcrew',
    'parklogic',
    'sedoparking',
)
PARKED_PAGE_MARKERS: Final[tuple[str, ...]] = (
    'buy this domain',
    'domain for sale',
    'is for sale',
    'parked free',
    'this domain may be for sale',
)


class DomainValidation(BaseModel):
    """Normalized job URL validation result."""

    classification: DomainValidationClassification
    domain: str | None = Field(default=None)
    normalized_url: str | None = Field(default=None)
    http_status: int | None = Field(default=None)
    final_url: str | None = Field(default=None)


@dataclass(slots=True)
class _ProbeOutcome:
    status_code: int | None = None
    final_url: str | None = None
    body: str | None = None
    timed_out: bool = False


def validate_job_url(url: str) -> Result[DomainValidation]:
    """Validate job URL format, DNS reachability, and parked-domain heuristics."""
    parsed = _parse_job_url(url)
    if parsed is None or parsed.hostname is None:
        return Result(
            success=True,
            data=DomainValidation(classification='invalid_format'),
            code=ResultCode.VALIDATION_SUCCESS,
        )

    normalized_url = _build_normalized_url(parsed)
    domain = _normalize_domain(parsed.hostname)

    if not _hostname_resolves(parsed.hostname):
        return Result(
            success=True,
            data=DomainValidation(
                classification='unreachable',
                domain=domain,
                normalized_url=normalized_url,
            ),
            code=ResultCode.VALIDATION_SUCCESS,
        )

    probe = _probe_url(normalized_url)
    if probe.status_code is None:
        return Result(
            success=True,
            data=DomainValidation(
                classification='unreachable',
                domain=domain,
                normalized_url=normalized_url,
            ),
            code=ResultCode.VALIDATION_SUCCESS,
        )

    classification: DomainValidationClassification = 'parked' if _looks_parked(probe.final_url or normalized_url, probe.body) else 'valid'
    return Result(
        success=True,
        data=DomainValidation(
            classification=classification,
            domain=domain,
            normalized_url=normalized_url,
            http_status=probe.status_code,
            final_url=probe.final_url,
        ),
        code=ResultCode.VALIDATION_SUCCESS,
    )


def _parse_job_url(url: str) -> SplitResult | None:
    trimmed = url.strip()
    if not trimmed:
        return None
    parsed = urlsplit(trimmed)
    if parsed.scheme not in {'http', 'https'}:
        return None
    if not parsed.netloc or not parsed.hostname:
        return None
    return parsed


def _build_normalized_url(parsed: SplitResult) -> str:
    hostname = parsed.hostname.lower() if parsed.hostname else ''
    netloc = hostname
    if parsed.port is not None:
        netloc = f'{netloc}:{parsed.port}'
    path = parsed.path or '/'
    return urlunsplit((parsed.scheme.lower(), netloc, path, parsed.query, ''))


def _normalize_domain(hostname: str) -> str:
    return hostname.lower().removeprefix('www.')


def _hostname_resolves(hostname: str) -> bool:
    try:
        socket.getaddrinfo(hostname, None)
    except socket.gaierror:
        return False
    return True


def _probe_url(url: str) -> _ProbeOutcome:
    head_result = _request_with_retry('HEAD', url)
    if head_result.status_code in HEAD_UNSUPPORTED_STATUSES:
        get_result = _request_with_retry('GET', url)
        return get_result if get_result.status_code is not None else head_result

    if head_result.status_code is not None:
        return head_result

    if head_result.timed_out:
        get_result = _request_with_retry('GET', url)
        if get_result.status_code is not None:
            return get_result

    return head_result


def _request_with_retry(method: Literal['HEAD', 'GET'], url: str) -> _ProbeOutcome:
    for attempt in range(REQUEST_RETRY_ATTEMPTS):
        try:
            response = _send_request(method, url)
            body = response.text if method == 'GET' else None
            return _ProbeOutcome(
                status_code=response.status_code,
                final_url=str(response.url),
                body=body,
            )
        except httpx.TimeoutException:
            if attempt == REQUEST_RETRY_ATTEMPTS - 1:
                return _ProbeOutcome(timed_out=True)
        except httpx.RequestError:
            return _ProbeOutcome()
    return _ProbeOutcome()


def _send_request(method: Literal['HEAD', 'GET'], url: str) -> httpx.Response:
    with httpx.Client(
        follow_redirects=True,
        timeout=REQUEST_TIMEOUT_SECONDS,
        headers={'User-Agent': USER_AGENT},
    ) as client:
        return client.request(method, url)


def _looks_parked(final_url: str, body: str | None) -> bool:
    lowered_url = final_url.lower()
    if any(marker in lowered_url for marker in PARKING_HOST_MARKERS):
        return True
    if not body:
        return False
    lowered_body = body.lower()
    return any(marker in lowered_body for marker in PARKED_PAGE_MARKERS)


__all__ = ['DomainValidation', 'DomainValidationClassification', 'validate_job_url']
