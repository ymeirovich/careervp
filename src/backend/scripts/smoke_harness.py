#!/usr/bin/env python3
"""P-30: 4-wire deploy smoke harness.

Runs the same four live proofs before and after any risky deploy:

1. ``health``            - ``GET /health`` returns 200.
2. ``cors_exact_origin`` - OPTIONS+GET on a protected route echo the *exact*
   frontend origin (a wildcard ``*`` success response fails the leg).
3. ``authed_read``       - an authenticated read returns 200 *and* the same
   read without a token is rejected (an unauthenticated 200 fails the leg).
4. ``presigned_upload``  - a presigned upload URL is issued and accepted.

The harness is transport-injectable so its logic is unit-testable offline; the
CLI entry point uses ``requests`` against a live ``API_BASE``. It emits
machine-readable JSON evidence (request ids, status codes, headers, assertion
results) suitable for the P-29 evidence pack.

No secrets are read from committed files: the Cognito test token and the
frontend origin come from the environment.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Mapping, Protocol

# The exact set of wires every smoke run must exercise. Order is stable so the
# evidence file and the CLI summary are deterministic.
REQUIRED_WIRES: tuple[str, ...] = (
    'health',
    'cors_exact_origin',
    'authed_read',
    'presigned_upload',
)

WILDCARD_ORIGIN = '*'


@dataclass(frozen=True)
class HttpResponse:
    """A minimal, transport-agnostic HTTP response."""

    status: int
    headers: Mapping[str, str] = field(default_factory=dict)
    body: object = None
    request_id: str | None = None

    def header(self, name: str) -> str | None:
        """Case-insensitive header lookup."""
        lowered = name.lower()
        for key, value in self.headers.items():
            if key.lower() == lowered:
                return value
        return None


class Transport(Protocol):
    """Something that can perform an HTTP request and return an HttpResponse."""

    def request(
        self,
        method: str,
        url: str,
        *,
        headers: Mapping[str, str] | None = None,
        json_body: object | None = None,
    ) -> HttpResponse: ...


@dataclass(frozen=True)
class SmokeConfig:
    """Inputs for a smoke run.

    All secret-bearing or environment-specific values come from the caller /
    environment; nothing is hard-coded or read from a committed file.
    """

    api_base: str
    origin: str
    token: str | None = None
    health_path: str = '/health'
    protected_path: str = '/users/me'
    authed_read_path: str = '/users/me'
    presigned_path: str = '/users/me/cv/presigned-upload'
    timeout_seconds: int = 30

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> 'SmokeConfig':
        source = os.environ if env is None else env
        api_base = source.get('API_BASE', '').strip().rstrip('/')
        if not api_base:
            raise ValueError('API_BASE is required for the smoke harness')
        return cls(
            api_base=api_base,
            origin=source.get('SMOKE_ORIGIN', '').strip(),
            token=(source.get('SMOKE_TOKEN', '').strip() or None),
            health_path=source.get('SMOKE_HEALTH_PATH', '/health'),
            protected_path=source.get('SMOKE_PROTECTED_PATH', '/users/me'),
            authed_read_path=source.get('SMOKE_AUTHED_PATH', '/users/me'),
            presigned_path=source.get('SMOKE_PRESIGNED_PATH', '/users/me/cv/presigned-upload'),
            timeout_seconds=int(source.get('SMOKE_TIMEOUT_SECONDS', '30')),
        )

    def url(self, path: str) -> str:
        return f'{self.api_base}{path}'


@dataclass(frozen=True)
class CheckResult:
    """The outcome of one wire."""

    name: str
    passed: bool
    detail: str
    status: int | None = None
    request_id: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            'name': self.name,
            'passed': self.passed,
            'status': self.status,
            'request_id': self.request_id,
            'detail': self.detail,
        }


@dataclass(frozen=True)
class SmokeReport:
    """Aggregate result of a smoke run."""

    api_base: str
    origin: str
    checks: list[CheckResult]
    timestamp: str

    @property
    def passed(self) -> bool:
        wires_seen = {check.name for check in self.checks}
        if wires_seen != set(REQUIRED_WIRES):
            return False
        return all(check.passed for check in self.checks)

    def to_evidence(self) -> dict[str, object]:
        return {
            'api_base': self.api_base,
            'origin': self.origin,
            'timestamp': self.timestamp,
            'passed': self.passed,
            'checks': [check.to_dict() for check in self.checks],
        }


def evaluate_cors(allow_origin: str | None, expected_origin: str) -> tuple[bool, str]:
    """Return (passed, detail) for a CORS success response.

    A missing header, a wildcard, or a mismatched origin all fail: a successful
    CORS response must echo the *exact* requesting origin.
    """
    if allow_origin is None:
        return False, 'no Access-Control-Allow-Origin header on success response'
    if allow_origin == WILDCARD_ORIGIN:
        return False, 'wildcard Access-Control-Allow-Origin is not allowed on success'
    if allow_origin != expected_origin:
        return False, f'origin mismatch: got {allow_origin!r}, expected {expected_origin!r}'
    return True, f'exact origin echoed: {allow_origin!r}'


def check_health(config: SmokeConfig, transport: Transport) -> CheckResult:
    resp = transport.request('GET', config.url(config.health_path))
    passed = resp.status == 200
    detail = 'health returned 200' if passed else f'health returned {resp.status}'
    return CheckResult('health', passed, detail, resp.status, resp.request_id)


def check_cors_exact_origin(config: SmokeConfig, transport: Transport) -> CheckResult:
    origin_headers = {'Origin': config.origin}
    preflight = transport.request(
        'OPTIONS',
        config.url(config.protected_path),
        headers={**origin_headers, 'Access-Control-Request-Method': 'GET'},
    )
    if preflight.status not in (200, 204):
        return CheckResult(
            'cors_exact_origin',
            False,
            f'preflight OPTIONS returned {preflight.status}',
            preflight.status,
            preflight.request_id,
        )
    get_resp = transport.request(
        'GET',
        config.url(config.protected_path),
        headers={**origin_headers, 'Authorization': _bearer(config.token)},
    )
    passed, detail = evaluate_cors(get_resp.header('Access-Control-Allow-Origin'), config.origin)
    return CheckResult('cors_exact_origin', passed, detail, get_resp.status, get_resp.request_id)


def check_authed_read(config: SmokeConfig, transport: Transport) -> CheckResult:
    authed = transport.request(
        'GET',
        config.url(config.authed_read_path),
        headers={'Authorization': _bearer(config.token)},
    )
    if authed.status != 200:
        return CheckResult(
            'authed_read',
            False,
            f'authenticated read returned {authed.status}, expected 200',
            authed.status,
            authed.request_id,
        )
    unauth = transport.request('GET', config.url(config.authed_read_path))
    if unauth.status not in (401, 403):
        return CheckResult(
            'authed_read',
            False,
            f'unauthenticated read returned {unauth.status}; a protected route must reject with 401/403',
            unauth.status,
            unauth.request_id,
        )
    return CheckResult(
        'authed_read',
        True,
        f'authed 200 and unauth rejected with {unauth.status}',
        authed.status,
        authed.request_id,
    )


def check_presigned_upload(config: SmokeConfig, transport: Transport) -> CheckResult:
    issued = transport.request(
        'POST',
        config.url(config.presigned_path),
        headers={'Authorization': _bearer(config.token)},
        json_body={'file_type': 'txt'},
    )
    if issued.status not in (200, 201):
        return CheckResult(
            'presigned_upload',
            False,
            f'presigned request returned {issued.status}',
            issued.status,
            issued.request_id,
        )
    upload_url = _extract_upload_url(issued.body)
    if not upload_url:
        return CheckResult(
            'presigned_upload',
            False,
            'presigned response contained no upload URL',
            issued.status,
            issued.request_id,
        )
    put = transport.request('PUT', upload_url, json_body={'smoke': True})
    passed = put.status in (200, 204)
    detail = 'presigned URL issued and upload accepted' if passed else f'presigned upload PUT returned {put.status}'
    return CheckResult('presigned_upload', passed, detail, put.status, put.request_id)


def run_smoke(config: SmokeConfig, transport: Transport) -> SmokeReport:
    checks = [
        check_health(config, transport),
        check_cors_exact_origin(config, transport),
        check_authed_read(config, transport),
        check_presigned_upload(config, transport),
    ]
    return SmokeReport(
        api_base=config.api_base,
        origin=config.origin,
        checks=checks,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


def _bearer(token: str | None) -> str:
    return f'Bearer {token}' if token else ''


def _extract_upload_url(body: object) -> str | None:
    if not isinstance(body, Mapping):
        return None
    for key in ('upload_url', 'url', 'presigned_url'):
        value = body.get(key)
        if isinstance(value, str) and value:
            return value
    data = body.get('data')
    if isinstance(data, Mapping):
        return _extract_upload_url(data)
    return None


class RequestsTransport:
    """Live transport backed by the ``requests`` library."""

    def __init__(self, timeout_seconds: int) -> None:
        import requests  # imported lazily so offline tests need no dependency

        self._requests = requests
        self._timeout = timeout_seconds

    def request(
        self,
        method: str,
        url: str,
        *,
        headers: Mapping[str, str] | None = None,
        json_body: object | None = None,
    ) -> HttpResponse:
        clean_headers = {k: v for k, v in (headers or {}).items() if v}
        response = self._requests.request(
            method.upper(),
            url,
            headers=clean_headers,
            json=json_body,
            timeout=self._timeout,
        )
        try:
            body: object = response.json()
        except ValueError:
            body = None
        return HttpResponse(
            status=response.status_code,
            headers=dict(response.headers),
            body=body,
            request_id=response.headers.get('x-amzn-RequestId') or response.headers.get('x-amz-request-id'),
        )


def write_evidence(report: SmokeReport, out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    path = out_dir / f'smoke-{stamp}-{uuid.uuid4().hex[:6]}.json'
    path.write_text(json.dumps(report.to_evidence(), indent=2, sort_keys=True), encoding='utf-8')
    return path


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description='P-30 4-wire deploy smoke harness')
    parser.add_argument(
        '--evidence-dir',
        type=Path,
        default=Path('docs/evidence'),
        help='directory to write JSON evidence into',
    )
    parser.add_argument(
        '--print-only',
        action='store_true',
        help='print evidence to stdout instead of writing a file',
    )
    args = parser.parse_args(list(argv) if argv is not None else None)

    config = SmokeConfig.from_env()
    transport = RequestsTransport(config.timeout_seconds)
    report = run_smoke(config, transport)
    evidence = report.to_evidence()

    if args.print_only:
        print(json.dumps(evidence, indent=2, sort_keys=True))
    else:
        path = write_evidence(report, args.evidence_dir)
        print(f'evidence written to {path}')

    for check in report.checks:
        marker = 'PASS' if check.passed else 'FAIL'
        print(f'  [{marker}] {check.name}: {check.detail}', file=sys.stderr)

    return 0 if report.passed else 1


if __name__ == '__main__':
    sys.exit(main())
