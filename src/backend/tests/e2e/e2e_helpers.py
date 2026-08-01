from __future__ import annotations

import base64
import json
import os
import time
import uuid
from dataclasses import dataclass
from typing import Any, Iterable

import pytest

requests = pytest.importorskip('requests')

BANNED_WORDS = [
    'leverage',
    'delve',
    'landscape',
    'robust',
    'streamline',
    'utilize',
    'facilitate',
    'cutting-edge',
    'harness',
    'spearhead',
    'synergy',
    'paradigm',
    'holistic',
    'ecosystem',
    'empower',
    'revolutionize',
]


@dataclass
class Resp:
    status: int
    data: dict[str, Any]
    text: str


def unwrap(payload: dict[str, Any]) -> dict[str, Any]:
    data = payload.get('data')
    return data if isinstance(data, dict) else payload


def require(payload: dict[str, Any], *keys: str) -> Any:
    normalized = unwrap(payload)
    for key in keys:
        value = normalized.get(key)
        if value not in (None, ''):
            return value
    raise AssertionError(f'Missing required keys {keys} in payload: {json.dumps(payload, default=str)}')


def artifact_result(payload: dict[str, Any]) -> dict[str, Any]:
    """Return the generated-content body of an artifact status response.

    The deployed `/{id}/status` contract nests the artifact under `result` and keeps
    only lifecycle fields (`status`, `id`, timestamps) at the top level.
    """
    normalized = unwrap(payload)
    result = normalized.get('result')
    return result if isinstance(result, dict) else normalized


def cv_record(payload: dict[str, Any]) -> dict[str, Any]:
    """Return the parsed-CV body of a `POST /users/me/cv` response (nested under `user_cv`)."""
    normalized = unwrap(payload)
    nested = normalized.get('user_cv')
    return nested if isinstance(nested, dict) else normalized


def decode_token_claims(token: str) -> dict[str, Any]:
    """Decode the claim set of a JWT WITHOUT verifying its signature.

    Only the decoded claims are returned. The raw token is never returned, logged,
    or embedded in an assertion message — callers must assert on claims alone.
    """
    segments = token.split('.')
    if len(segments) != 3:
        raise AssertionError('API credential is not a three-segment JWT.')
    payload_segment = segments[1]
    payload_segment += '=' * (-len(payload_segment) % 4)
    claims = json.loads(base64.urlsafe_b64decode(payload_segment.encode('ascii')).decode('utf-8'))
    if not isinstance(claims, dict):
        raise AssertionError('JWT claim set did not decode to a JSON object.')
    return claims


class E2EClient:
    def __init__(self, base_url: str, timeout_seconds: int = 30) -> None:
        self.base_url = base_url.rstrip('/')
        self.timeout_seconds = timeout_seconds

    @classmethod
    def from_env(cls) -> 'E2EClient':
        api_base = os.getenv('API_BASE', '').strip().rstrip('/')
        if not api_base:
            pytest.skip('API_BASE not set; skipping E2E tests.')
        return cls(api_base, int(os.getenv('E2E_HTTP_TIMEOUT_SECONDS', '30')))

    def request(
        self,
        method: str,
        path: str,
        *,
        token: str | None = None,
        json_body: dict[str, Any] | None = None,
        expected_status: int | Iterable[int] | None = None,
    ) -> Resp:
        headers = {'Content-Type': 'application/json'}
        if token:
            headers['Authorization'] = f'Bearer {token}'
        r = requests.request(
            method.upper(),
            f'{self.base_url}{path}',
            headers=headers,
            json=json_body,
            timeout=self.timeout_seconds,
        )
        try:
            data = r.json()
            if not isinstance(data, dict):
                data = {'result': data}
        except ValueError:
            data = {}
        if expected_status is not None:
            expected = {expected_status} if isinstance(expected_status, int) else set(expected_status)
            assert r.status_code in expected, f'{method} {path} returned {r.status_code}; expected {sorted(expected)}; body={r.text}'
        return Resp(r.status_code, data, r.text)


def _login_only(client: E2EClient, email: str, password: str) -> dict[str, str]:
    login = client.request(
        'POST',
        '/auth/login',
        json_body={'email': email, 'password': password},
        expected_status=200,
    )
    token = str(require(login.data, 'id_token'))
    # A reused account carries the trial counters of every previous run, and the 3-application
    # trial is smaller than one pass of this suite; without this the account 403s
    # `trial_exhausted` on the second run. A freshly registered user needs no reset, so this
    # is confined to the reuse path and never runs on the default path.
    client.request('POST', '/users/me/trial/reset', token=token, json_body={}, expected_status=200)
    return {
        'email': email,
        'password': password,
        'token': token,
        'register_token': '',
        'refresh_token': str(require(login.data, 'refresh_token')),
        'cognito_access_token': str(require(login.data, 'access_token')),
    }


def register_and_login(client: E2EClient) -> dict[str, str]:
    # Cognito's built-in email sender caps the SignUp verification mail at 50/day for the
    # whole user pool. A suite that registers a fresh user per test exhausts that quota and
    # every later register — including re-registering an existing address — answers 500.
    # Supplying TEST_USER_EMAIL and TEST_USER_PASSWORD reuses an existing account and skips
    # /auth/register entirely; registration coverage lives in test_auth_flow_integration.
    reuse_email = os.getenv('TEST_USER_EMAIL', '').strip()
    reuse_password = os.getenv('TEST_USER_PASSWORD', '').strip()
    if reuse_email and reuse_password:
        return _login_only(client, reuse_email, reuse_password)

    email = f'e2e-{uuid.uuid4().hex[:10]}@careervp.com'
    password = 'SecureP@ss123!'
    name = 'E2E Test User'

    reg = client.request(
        'POST',
        '/auth/register',
        json_body={'email': email, 'password': password, 'name': name},
        expected_status={200, 201, 409},
    )
    reg_token = unwrap(reg.data).get('id_token')

    login = client.request(
        'POST',
        '/auth/login',
        json_body={'email': email, 'password': password},
        expected_status=200,
    )
    # The deployed API Gateway authorizer is a COGNITO_USER_POOLS authorizer, which
    # accepts the ID token only; the access token is rejected with 401 on every
    # authenticated route. The frontend does the same (src/frontend/lib/auth.ts
    # getCurrentToken -> session.getIdToken()).
    login_token = require(login.data, 'id_token')
    # Retained for the two Cognito/OAuth wires that do NOT go through the product
    # authorizer: POST /auth/refresh consumes the refresh token, and POST /auth/logout
    # decodes whichever Cognito token it is given. Never send these to a product route.
    refresh = require(login.data, 'refresh_token')
    access = require(login.data, 'access_token')
    return {
        'email': email,
        'password': password,
        'token': str(login_token),
        'register_token': str(reg_token or ''),
        'refresh_token': str(refresh),
        'cognito_access_token': str(access),
    }


# Named employers and dated roles are required: the parser rejects a work entry whose
# company is absent (`WorkExperience.company` is a required str), which 500s the upload.
E2E_CV_TEXT = (
    'Jane Doe\n'
    'Senior Backend Engineer\n'
    'Email: jane.doe@example.com | Phone: +1-555-0100 | Tel Aviv, Israel\n\n'
    'PROFESSIONAL SUMMARY\n'
    'Backend engineer with eight years building Python services on AWS.\n\n'
    'WORK EXPERIENCE\n'
    'Senior Backend Engineer, Integration Labs Ltd, Tel Aviv, Israel (2021 - Present)\n'
    '- Built Python APIs on AWS Lambda serving 40M requests per month.\n'
    '- Designed DynamoDB single-table data models and cut read cost by 38 percent.\n\n'
    'Backend Engineer, Northwind Software Ltd, Haifa, Israel (2018 - 2021)\n'
    '- Delivered CI pipelines on GitHub Actions, cutting release time from 40 to 9 minutes.\n\n'
    'EDUCATION\n'
    'BSc Computer Science, Technion - Israel Institute of Technology, 2018\n\n'
    'SKILLS\n'
    'Python, AWS Lambda, DynamoDB, API Gateway, Terraform, pytest\n'
)

# `POST /jobs` requires `url` and live-fetches it for reachability, so the fixture URL
# has to resolve. A deep path under example.com does not.
E2E_JOB_URL = 'https://example.com/'


def upload_cv(client: E2EClient, token: str) -> str:
    # Canonical shape, identical to what src/frontend/app/cv-center/page.tsx posts:
    # base64 file content under `cv_content`, plus `file_name` and `file_type`.
    payload = {
        'cv_content': base64.b64encode(E2E_CV_TEXT.encode('utf-8')).decode('utf-8'),
        'file_name': 'e2e-jane-doe-cv.txt',
        'file_type': 'txt',
    }
    res = client.request('POST', '/users/me/cv', token=token, json_body=payload, expected_status=201)
    return str(require(cv_record(res.data), 'cv_id', 'id'))


def create_job(client: E2EClient, token: str) -> str:
    # Canonical CreateJobInput from src/frontend/lib/types.ts:53 — `company_name` and
    # `description`, not the `company`/`job_description` aliases job_handler still maps.
    payload = {
        'title': 'Senior Backend Engineer',
        'company_name': 'Example Corp',
        'description': 'Build secure APIs and async services.',
        'url': E2E_JOB_URL,
    }
    res = client.request('POST', '/jobs', token=token, json_body=payload, expected_status=201)
    return str(require(res.data, 'job_id', 'id'))


def poll_completed(client: E2EClient, token: str, path: str, timeout_seconds: int) -> dict[str, Any]:
    # Bare `GET /{artifact}/{id}` is not a routed method on the deployed API; it returns
    # the API Gateway DEFAULT_4XX response (403), which reads like an auth failure. The
    # only artifact read route is `/{id}/status`, so refuse to poll anything else.
    if not path.endswith('/status'):
        raise AssertionError(f'Artifact polling must target /{{id}}/status; got {path}')
    deadline = time.time() + timeout_seconds
    last: dict[str, Any] = {}
    while time.time() < deadline:
        res = client.request('GET', path, token=token, expected_status=200)
        payload = unwrap(res.data)
        last = payload
        status = str(payload.get('status', '')).lower()
        if status == 'completed':
            return payload
        if status == 'failed':
            raise AssertionError(f'{path} failed: {res.text}')
        time.sleep(5)
    raise AssertionError(f'Timed out waiting for completion on {path}; last={last}')


def assert_no_banned_words(text: str) -> None:
    lower = text.lower()
    bad = [word for word in BANNED_WORDS if word in lower]
    assert not bad, f'Anti-AI banned words found: {bad}'
