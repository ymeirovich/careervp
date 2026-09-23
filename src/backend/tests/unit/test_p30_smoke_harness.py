"""P-30 RED tests: the 4-wire deploy smoke harness.

These exercise the harness logic offline with a programmable fake transport so
no live API or Cognito token is needed. See ``scripts/smoke_harness.py``.
"""

from __future__ import annotations

import base64
import importlib.util
import json
import sys
from pathlib import Path
from typing import Mapping

import pytest

# The harness lives under scripts/ (not an importable package), so load it by path.
_HARNESS_PATH = Path(__file__).resolve().parents[2] / 'scripts' / 'smoke_harness.py'
_spec = importlib.util.spec_from_file_location('smoke_harness', _HARNESS_PATH)
assert _spec is not None and _spec.loader is not None
smoke_harness = importlib.util.module_from_spec(_spec)
# Register before exec so dataclasses can resolve string annotations (PEP 563).
sys.modules['smoke_harness'] = smoke_harness
_spec.loader.exec_module(smoke_harness)

HttpResponse = smoke_harness.HttpResponse
SmokeConfig = smoke_harness.SmokeConfig


class FakeTransport:
    """Return a programmed HttpResponse per (METHOD, path-or-url)."""

    def __init__(self, routes: Mapping[tuple[str, str], HttpResponse]) -> None:
        self._routes = dict(routes)
        self.calls: list[tuple[str, str]] = []

    def request(self, method, url, *, headers=None, json_body=None):  # type: ignore[no-untyped-def]
        self.calls.append((method.upper(), url))
        key = (method.upper(), url)
        if key in self._routes:
            return self._routes[key]
        # Match by path suffix so tests need not spell the full base URL.
        for (rmethod, rpath), resp in self._routes.items():
            if rmethod == method.upper() and url.endswith(rpath):
                return resp
        raise AssertionError(f'no fake route for {method} {url}')


BASE = 'https://api.example.test'
ORIGIN = 'https://app.example.test'


SMOKE_CV_ID = 'cv-abc-123'


def _happy_routes(*, allow_origin: str = ORIGIN, unauth_status: int = 401):
    return {
        ('GET', '/health'): HttpResponse(200),
        ('OPTIONS', '/users/me'): HttpResponse(204, {'Access-Control-Allow-Origin': allow_origin}),
        # GET /users/me is used by both the CORS leg (with Origin) and the
        # authed_read leg; the fake returns the same success either way, and a
        # separate unauth entry is matched first for the no-auth call.
        ('GET', '/users/me'): HttpResponse(200, {'Access-Control-Allow-Origin': allow_origin}, {'user_id': 'u1'}),
        # The real upload contract: base64 cv_content in, the CV row back out,
        # then the same path lists the CVs so the wire can read its write back.
        ('POST', '/users/me/cv'): HttpResponse(201, body={'success': True, 'user_cv': {'cv_id': SMOKE_CV_ID}}),
        ('GET', '/users/me/cv'): HttpResponse(200, body={'cvs': [{'cv_id': SMOKE_CV_ID}], 'cursor': None}),
    }


def _config() -> SmokeConfig:
    return SmokeConfig(api_base=BASE, origin=ORIGIN, token='fake-token')


def test_p30_harness_requires_four_wires():
    """The harness declares exactly the four required wires and runs them all."""
    assert set(smoke_harness.REQUIRED_WIRES) == {
        'health',
        'cors_exact_origin',
        'authed_read',
        'authed_upload',
    }
    # A run with an unauthenticated-rejection route present produces all four.
    routes = _happy_routes()
    transport = FakeTransport(routes)
    # Distinguish the unauth GET (no Authorization) from the authed one by
    # letting the authed path route return 200 and adding an unauth override.
    report = _run_with_unauth(transport)
    assert {c.name for c in report.checks} == set(smoke_harness.REQUIRED_WIRES)


def _run_with_unauth(transport):  # type: ignore[no-untyped-def]
    return smoke_harness.run_smoke(_config(), transport)


def test_p30_cors_asserts_exact_origin_not_wildcard():
    """A wildcard Access-Control-Allow-Origin fails the success CORS leg."""
    passed, detail = smoke_harness.evaluate_cors('*', ORIGIN)
    assert passed is False
    assert 'wildcard' in detail.lower()

    transport = FakeTransport(_happy_routes(allow_origin='*'))
    report = smoke_harness.run_smoke(_config(), transport)
    cors = next(c for c in report.checks if c.name == 'cors_exact_origin')
    assert cors.passed is False
    # exact-origin echo passes
    ok, _ = smoke_harness.evaluate_cors(ORIGIN, ORIGIN)
    assert ok is True


def test_p30_authed_read_rejects_unauthenticated_success():
    """If the unauthenticated read returns 200, the authed_read leg fails."""
    routes = _happy_routes()
    transport = _UnauthAwareTransport(routes, unauth_status=200)
    report = smoke_harness.run_smoke(_config(), transport)
    authed = next(c for c in report.checks if c.name == 'authed_read')
    assert authed.passed is False
    assert 'unauth' in authed.detail.lower()


def test_p30_upload_wire_posts_base64_cv_content_to_the_real_route():
    """The upload wire sends a typed base64 file to /users/me/cv.

    The API has no presigned-upload route; the handler owns the S3 put.
    """
    captured: dict[str, object] = {}

    class _CapturingTransport(_UnauthAwareTransport):
        def request(self, method, url, *, headers=None, json_body=None):  # type: ignore[no-untyped-def]
            if method.upper() == 'POST' and url.endswith('/users/me/cv'):
                captured['body'] = json_body
            return super().request(method, url, headers=headers, json_body=json_body)

    transport = _CapturingTransport(_happy_routes(), unauth_status=401)
    report = smoke_harness.run_smoke(_config(), transport)

    upload = next(c for c in report.checks if c.name == 'authed_upload')
    assert upload.passed is True

    body = captured['body']
    assert isinstance(body, dict)
    assert body['file_name'] == 'p30-smoke.txt'
    assert body['file_type'] == 'txt'
    decoded = base64.b64decode(body['cv_content']).decode('utf-8')
    assert decoded == smoke_harness.SMOKE_CV_FIXTURE


def test_p30_upload_wire_fails_when_upload_is_not_readable_back():
    """A write that does not appear in the read-back fails the wire (S3/DB write not durable)."""
    routes = dict(_happy_routes())
    routes[('GET', '/users/me/cv')] = HttpResponse(200, body={'cvs': [{'cv_id': 'some-other-cv'}]})
    transport = _UnauthAwareTransport(routes, unauth_status=401)

    report = smoke_harness.run_smoke(_config(), transport)
    upload = next(c for c in report.checks if c.name == 'authed_upload')
    assert upload.passed is False
    assert 'absent from the CV read-back' in upload.detail


def test_p30_upload_wire_fails_when_response_has_no_cv_id():
    """A 201 with no cv_id fails the wire -- the harness must not accept an empty success."""
    routes = dict(_happy_routes())
    routes[('POST', '/users/me/cv')] = HttpResponse(201, body={'success': True})
    transport = _UnauthAwareTransport(routes, unauth_status=401)

    report = smoke_harness.run_smoke(_config(), transport)
    upload = next(c for c in report.checks if c.name == 'authed_upload')
    assert upload.passed is False
    assert 'no cv_id' in upload.detail


def test_p30_outputs_machine_readable_evidence():
    """A dry run emits JSON with api_base, origin, checks[], passed, per-check status."""
    transport = _UnauthAwareTransport(_happy_routes(), unauth_status=401)
    report = smoke_harness.run_smoke(_config(), transport)
    evidence = report.to_evidence()
    serialized = json.loads(json.dumps(evidence))  # must be JSON-serializable

    assert serialized['api_base'] == BASE
    assert serialized['origin'] == ORIGIN
    assert isinstance(serialized['checks'], list) and len(serialized['checks']) == 4
    assert serialized['passed'] is True
    for check in serialized['checks']:
        assert set(check) >= {'name', 'passed', 'status', 'detail'}


def test_p30_custom_domain_smoke_uses_api_dev_domain():
    """O-9/P-26: the harness runs with API_BASE=https://api.dev.careervp.com."""
    config = SmokeConfig.from_env({'API_BASE': 'https://api.dev.careervp.com', 'SMOKE_ORIGIN': ORIGIN})
    assert config.api_base == 'https://api.dev.careervp.com'
    assert config.url('/health') == 'https://api.dev.careervp.com/health'


class _UnauthAwareTransport(FakeTransport):
    """Fake transport that returns a distinct status for the no-Authorization GET."""

    def __init__(self, routes, *, unauth_status: int) -> None:  # type: ignore[no-untyped-def]
        super().__init__(routes)
        self._unauth_status = unauth_status

    def request(self, method, url, *, headers=None, json_body=None):  # type: ignore[no-untyped-def]
        is_authed_read = method.upper() == 'GET' and url.endswith('/users/me')
        has_auth = bool((headers or {}).get('Authorization'))
        if is_authed_read and not has_auth:
            self.calls.append((method.upper(), url))
            return HttpResponse(self._unauth_status)
        return super().request(method, url, headers=headers, json_body=json_body)


def test_from_env_requires_api_base():
    with pytest.raises(ValueError):
        SmokeConfig.from_env({'SMOKE_ORIGIN': ORIGIN})
