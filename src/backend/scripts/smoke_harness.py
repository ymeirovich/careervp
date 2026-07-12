#!/usr/bin/env python3
"""P-30: 4-wire deploy smoke harness.

Runs the same four live proofs before and after any risky deploy:

1. ``health``            - ``GET /health`` returns 200.
2. ``cors_exact_origin`` - OPTIONS+GET on a protected route echo the *exact*
   frontend origin (a wildcard ``*`` success response fails the leg).
3. ``authed_read``       - an authenticated read returns 200 *and* the same
   read without a token is rejected (an unauthenticated 200 fails the leg).
4. ``authed_upload``     - an authenticated CV upload reaches S3 and reads back.

Wire 4 exercises ``POST /users/me/cv``, which is the only upload path this API
has: the file travels inline as base64 ``cv_content`` and the handler performs
the S3 put itself. There is no presigned-upload route (see ISSUES.md, I-01).

The harness is transport-injectable so its logic is unit-testable offline; the
CLI entry point uses ``requests`` against a live ``API_BASE``. It emits
machine-readable JSON evidence (request ids, status codes, headers, assertion
results) suitable for the P-29 evidence pack.

No secrets are read from committed files: the Cognito test token and the
frontend origin come from the environment.
"""

from __future__ import annotations

import argparse
import base64
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
    'authed_upload',
)

WILDCARD_ORIGIN = '*'

# Synthetic CV posted by the upload wire. Deliberately small and obviously fake:
# a real deploy runs this on every risky change, and the handler parses it with
# the AI parser and persists a CV row for the smoke user.
SMOKE_CV_FIXTURE = (
    'Jane Doe\n'
    'Software Engineer\n'
    'jane@example.com\n'
    '\n'
    'Experience\n'
    'Acme Corp, Backend Engineer, 2020-2024. Built Python APIs on AWS.\n'
    '\n'
    'Education\n'
    'BSc Computer Science, MIT, 2020.\n'
    '\n'
    'Skills\n'
    'Python, AWS, DynamoDB.\n'
)


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
    upload_path: str = '/users/me/cv'
    upload_file_name: str = 'p30-smoke.txt'
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
            upload_path=source.get('SMOKE_UPLOAD_PATH', '/users/me/cv'),
            upload_file_name=source.get('SMOKE_UPLOAD_FILE_NAME', 'p30-smoke.txt'),
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


def check_authed_upload(config: SmokeConfig, transport: Transport) -> CheckResult:
    """Wire 4: an authenticated upload lands in S3 and is readable back.

    ``POST /users/me/cv`` takes the file inline (base64 ``cv_content`` +
    ``file_name`` + ``file_type``) and the handler owns the S3 put, so posting
    and then reading the CV back is what proves the authenticated write path
    end to end.
    """
    payload = {
        'cv_content': base64.b64encode(SMOKE_CV_FIXTURE.encode('utf-8')).decode('ascii'),
        'file_name': config.upload_file_name,
        # Required to exercise the handler's file-content branch. Without this,
        # the OpenAPI adapter treats cv_content as plain text and skips S3.
        'file_type': 'txt',
    }
    issued = transport.request(
        'POST',
        config.url(config.upload_path),
        headers={'Authorization': _bearer(config.token)},
        json_body=payload,
    )
    if issued.status not in (200, 201):
        return CheckResult(
            'authed_upload',
            False,
            f'upload returned {issued.status}, expected 200/201',
            issued.status,
            issued.request_id,
        )
    cv_id = _extract_cv_id(issued.body)
    if not cv_id:
        return CheckResult(
            'authed_upload',
            False,
            'upload response contained no cv_id',
            issued.status,
            issued.request_id,
        )
    listed = transport.request(
        'GET',
        config.url(config.upload_path),
        headers={'Authorization': _bearer(config.token)},
    )
    if listed.status != 200:
        return CheckResult(
            'authed_upload',
            False,
            f'CV read-back returned {listed.status}, expected 200',
            listed.status,
            listed.request_id,
        )
    if not _cv_id_present(listed.body, cv_id):
        return CheckResult(
            'authed_upload',
            False,
            f'uploaded cv_id {cv_id} is absent from the CV read-back',
            listed.status,
            listed.request_id,
        )
    return CheckResult(
        'authed_upload',
        True,
        f'CV uploaded (cv_id={cv_id}) and read back',
        issued.status,
        issued.request_id,
    )


def run_smoke(config: SmokeConfig, transport: Transport) -> SmokeReport:
    checks = [
        check_health(config, transport),
        check_cors_exact_origin(config, transport),
        check_authed_read(config, transport),
        check_authed_upload(config, transport),
    ]
    return SmokeReport(
        api_base=config.api_base,
        origin=config.origin,
        checks=checks,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


def _bearer(token: str | None) -> str:
    return f'Bearer {token}' if token else ''


def _extract_cv_id(body: object) -> str | None:
    if not isinstance(body, Mapping):
        return None
    user_cv = body.get('user_cv')
    if isinstance(user_cv, Mapping):
        nested = user_cv.get('cv_id')
        if isinstance(nested, str) and nested:
            return nested
    top_level = body.get('cv_id')
    return top_level if isinstance(top_level, str) and top_level else None


def _cv_id_present(body: object, cv_id: str) -> bool:
    if not isinstance(body, Mapping):
        return False
    cvs = body.get('cvs')
    if not isinstance(cvs, list):
        return False
    return any(isinstance(cv, Mapping) and cv.get('cv_id') == cv_id for cv in cvs)


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
