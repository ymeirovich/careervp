"""Contract gate for the deployed API surface.

This file is a GATE, not a survey. Every check declares which of five outcomes the
deployed API is contractually required to produce, and the check fails if the API
produces any other one:

- ``AUTHENTICATED_OK``      a credentialled request that must succeed. 401 is a FAILURE
                            here; accepting it is what made the previous version of this
                            file unable to detect a broken credential.
- ``PUBLIC_OK``             an unauthenticated route that must succeed.
- ``VALIDATION_FAILURE``    a deliberately malformed body that must be refused with 400
                            and an error body.
- ``NOT_FOUND``             a well-formed request for an absent record, which must be
                            refused with 404 and an error body.
- ``UNAUTHORIZED_NEGATIVE`` a deliberately uncredentialled request that must be refused
                            with the authorizer's own 401 ``UNAUTHORIZED`` envelope.

Independently of the declared outcome, two responses fail the gate everywhere:
a 5xx, and an API Gateway default response (403 ``DEFAULT_4XX`` / "Missing Authentication
Token"), which means the method is not routed at all. An unrouted method is
indistinguishable from an auth failure by status code alone, so it is checked by body.
"""

from __future__ import annotations

import base64
from typing import Any

try:
    from .e2e_helpers import E2E_CV_TEXT, E2E_JOB_URL, E2EClient, Resp, create_job, register_and_login, unwrap
except ImportError:  # pragma: no cover
    from e2e_helpers import E2E_CV_TEXT, E2E_JOB_URL, E2EClient, Resp, create_job, register_and_login, unwrap  # type: ignore

AUTHENTICATED_OK = 'authenticated_ok'
PUBLIC_OK = 'public_ok'
VALIDATION_FAILURE = 'validation_failure'
NOT_FOUND = 'not_found'
UNAUTHORIZED_NEGATIVE = 'unauthorized_negative'


def _assert_routed(kind: str, method: str, path: str, res: Resp) -> None:
    """Fail the gate when API Gateway answered instead of the service."""
    assert res.status < 500, f'[{kind}] {method} {path} returned {res.status}: {res.text}'
    body = unwrap(res.data)
    unrouted = body.get('code') == 'DEFAULT_4XX' or body.get('error') == 'DEFAULT_4XX' or 'Missing Authentication Token' in res.text
    assert not unrouted, f'[{kind}] {method} {path} is not a routed method — API Gateway answered with its default response: {res.text}'


def _check(client: E2EClient, kind: str, method: str, path: str, token: str | None, body: dict[str, Any] | None, expected: set[int]) -> None:
    res = client.request(method, path, token=token, json_body=body, expected_status=None)
    _assert_routed(kind, method, path, res)

    assert res.status in expected, f'[{kind}] {method} {path} returned {res.status}; expected {sorted(expected)}; body={res.text}'

    payload = unwrap(res.data)
    if kind == UNAUTHORIZED_NEGATIVE:
        assert payload.get('code') == 'UNAUTHORIZED', f'[{kind}] {method} {path} did not carry the authorizer 401 envelope: {res.text}'
    elif kind in {VALIDATION_FAILURE, NOT_FOUND}:
        assert payload.get('error') or payload.get('message') or payload.get('code'), (
            f'[{kind}] {method} {path} returned {res.status} with no error body: {res.text}'
        )


def test_e2e_contract_gate_validation() -> None:
    client = E2EClient.from_env()
    user = register_and_login(client)
    token = user['token']
    refresh_token = user['refresh_token']
    job_id = create_job(client, token)

    canonical_cv = {
        'cv_content': base64.b64encode(E2E_CV_TEXT.encode('utf-8')).decode('utf-8'),
        'file_name': 'contract-gate-cv.txt',
        'file_type': 'txt',
    }
    canonical_job = {
        'title': 'Senior Backend Engineer',
        'company_name': 'Example Corp',
        'description': 'Build secure APIs and async services.',
        'url': E2E_JOB_URL,
    }

    checks: list[tuple[str, str, str, str | None, dict[str, Any] | None, set[int]]] = [
        # ── Authenticated happy path. A 401 here fails the gate. ──
        # /auth/refresh is not behind the product authorizer; it consumes the refresh token.
        (AUTHENTICATED_OK, 'POST', '/auth/refresh', refresh_token, None, {200}),
        (AUTHENTICATED_OK, 'GET', '/users/me', token, None, {200}),
        (AUTHENTICATED_OK, 'PUT', '/users/me', token, {'name': 'Gate User'}, {200}),
        (AUTHENTICATED_OK, 'POST', '/users/me/cv', token, canonical_cv, {201}),
        (AUTHENTICATED_OK, 'GET', '/users/me/cv', token, None, {200}),
        (AUTHENTICATED_OK, 'POST', '/jobs', token, canonical_job, {201}),
        (AUTHENTICATED_OK, 'GET', '/jobs', token, None, {200}),
        (AUTHENTICATED_OK, 'GET', f'/jobs/{job_id}', token, None, {200}),
        (AUTHENTICATED_OK, 'GET', f'/jobs/{job_id}/gap-questions', token, None, {200}),
        (AUTHENTICATED_OK, 'GET', '/vprs', token, None, {200}),
        (AUTHENTICATED_OK, 'GET', '/cv-tailorings', token, None, {200}),
        (AUTHENTICATED_OK, 'GET', '/cover-letters', token, None, {200}),
        (AUTHENTICATED_OK, 'GET', '/interview-preps', token, None, {200}),
        # An absent company-research record is a 200 carrying the explicit absent envelope.
        (AUTHENTICATED_OK, 'GET', '/company-research/nonexistent-id', token, None, {200}),
        # ── Public ──
        (PUBLIC_OK, 'GET', '/health', None, None, {200}),
        # ── Explicit validation failures ──
        (VALIDATION_FAILURE, 'POST', '/auth/register', None, {'email': 'x', 'password': 'y', 'name': 'z'}, {400}),
        (VALIDATION_FAILURE, 'POST', '/auth/login', None, {'email': 'x', 'password': 'y'}, {400}),
        # `url` is required and reachability-checked, so a job without one is refused.
        (VALIDATION_FAILURE, 'POST', '/jobs', token, {'title': 't', 'company_name': 'c', 'description': 'd'}, {400}),
        (VALIDATION_FAILURE, 'POST', '/vpr/generate', token, {'cv_id': 'x'}, {400}),
        (VALIDATION_FAILURE, 'POST', '/gap-analysis/questions', token, {}, {400}),
        (VALIDATION_FAILURE, 'POST', f'/jobs/{job_id}/gap-responses', token, {'responses': []}, {400}),
        (VALIDATION_FAILURE, 'POST', '/cv-tailoring/generate', token, {'cv_id': 'x'}, {400}),
        (VALIDATION_FAILURE, 'POST', '/cover-letter/generate', token, {'cv_id': 'x'}, {400}),
        (VALIDATION_FAILURE, 'POST', '/interview-prep/generate', token, {'vpr_id': 'x'}, {400}),
        # The stale `{domain}` shape must stay refused; the canonical body is keyed on job_id.
        (VALIDATION_FAILURE, 'POST', '/company-research/fetch', token, {'domain': 'example.com'}, {400}),
        # ── Explicit not-found ──
        (NOT_FOUND, 'GET', '/jobs/nonexistent-id', token, None, {404}),
        (NOT_FOUND, 'GET', '/vpr/nonexistent-id/status', token, None, {404}),
        (NOT_FOUND, 'GET', '/cv-tailoring/nonexistent-id/status', token, None, {404}),
        (NOT_FOUND, 'GET', '/cover-letter/nonexistent-id/status', token, None, {404}),
        (NOT_FOUND, 'GET', '/interview-prep/nonexistent-id/status', token, None, {404}),
        (NOT_FOUND, 'POST', '/gap-analysis/questions', token, {'cv_id': 'nonexistent-cv', 'job_id': job_id}, {404}),
        # ── Deliberate unauthorized negatives ──
        (UNAUTHORIZED_NEGATIVE, 'GET', '/users/me', None, None, {401}),
        (UNAUTHORIZED_NEGATIVE, 'GET', '/jobs', None, None, {401}),
        (UNAUTHORIZED_NEGATIVE, 'POST', '/vpr/generate', None, {'cv_id': 'x', 'job_id': 'y', 'gap_response_ids': ['z']}, {401}),
        (UNAUTHORIZED_NEGATIVE, 'GET', '/vpr/nonexistent-id/status', None, None, {401}),
        (UNAUTHORIZED_NEGATIVE, 'GET', '/company-research/nonexistent-id', None, None, {401}),
    ]

    for kind, method, path, auth, payload, expected in checks:
        _check(client, kind, method, path, auth, payload, expected)
