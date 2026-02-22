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


def register_and_login(client: E2EClient) -> dict[str, str]:
    email = os.getenv('TEST_USER_EMAIL', f'e2e-{uuid.uuid4().hex[:10]}@careervp.com')
    password = os.getenv('TEST_USER_PASSWORD', 'SecureP@ss123!')
    name = 'E2E Test User'

    reg = client.request(
        'POST',
        '/auth/register',
        json_body={'email': email, 'password': password, 'name': name},
        expected_status={200, 201, 409},
    )
    reg_token = unwrap(reg.data).get('access_token')

    login = client.request(
        'POST',
        '/auth/login',
        json_body={'email': email, 'password': password},
        expected_status=200,
    )
    login_token = require(login.data, 'access_token')
    return {'email': email, 'password': password, 'token': str(login_token), 'register_token': str(reg_token or '')}


def upload_cv(client: E2EClient, token: str) -> str:
    cv_text = 'Senior backend engineer with Python, AWS Lambda, and DynamoDB experience.'
    cv_b64 = base64.b64encode(cv_text.encode('utf-8')).decode('utf-8')
    variants = [
        {'text_content': cv_text},
        {'file_content': cv_b64, 'file_type': 'txt'},
    ]
    for payload in variants:
        res = client.request('POST', '/users/me/cv', token=token, json_body=payload)
        if res.status == 201:
            return str(require(res.data, 'cv_id', 'id'))
    raise AssertionError('Could not upload CV with supported payload variants.')


def create_job(client: E2EClient, token: str) -> str:
    variants = [
        {
            'title': 'Senior Backend Engineer',
            'company': 'Example Corp',
            'description': 'Build secure APIs and async services.',
        },
        {
            'title': 'Senior Backend Engineer',
            'company_name': 'Example Corp',
            'job_description': 'Build secure APIs and async services.',
        },
    ]
    for payload in variants:
        res = client.request('POST', '/jobs', token=token, json_body=payload)
        if res.status == 201:
            return str(require(res.data, 'job_id', 'id'))
    raise AssertionError('Could not create job with supported payload variants.')


def poll_completed(client: E2EClient, token: str, path: str, timeout_seconds: int) -> dict[str, Any]:
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
