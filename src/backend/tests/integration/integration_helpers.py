from __future__ import annotations

import base64
import json
import os
import time
import uuid
from dataclasses import dataclass
from typing import Any, Iterable, Sequence

import pytest

requests = pytest.importorskip('requests')


TERMINAL_STATUSES = {'completed', 'failed'}
IN_FLIGHT_STATUSES = {'pending', 'processing', 'queued', 'in_progress', 'running'}


@dataclass
class HTTPResponse:
    status: int
    data: dict[str, Any]
    text: str
    headers: dict[str, str]


def unwrap_payload(payload: dict[str, Any]) -> dict[str, Any]:
    maybe_data = payload.get('data')
    if isinstance(maybe_data, dict):
        return maybe_data
    return payload


def require_field(payload: dict[str, Any], *keys: str) -> Any:
    normalized = unwrap_payload(payload)
    for key in keys:
        if key in normalized and normalized[key] not in (None, ''):
            return normalized[key]
    raise AssertionError(f'Expected one of keys {keys} in payload. payload={json.dumps(payload, default=str)}')


def optional_field(payload: dict[str, Any], *keys: str) -> Any | None:
    normalized = unwrap_payload(payload)
    for key in keys:
        value = normalized.get(key)
        if value is not None:
            return value
    return None


def unique_email(prefix: str = 'int-test') -> str:
    return f'{prefix}-{uuid.uuid4().hex[:12]}@careervp.com'


class IntegrationApiClient:
    def __init__(self, base_url: str, timeout_seconds: int = 30) -> None:
        self.base_url = base_url.rstrip('/')
        self.timeout_seconds = timeout_seconds

    @classmethod
    def from_env(cls) -> 'IntegrationApiClient':
        base_url = os.getenv('API_BASE', '').strip().rstrip('/')
        if not base_url:
            pytest.skip('API_BASE is not set. Skipping integration tests.')
        timeout_seconds = int(os.getenv('INTEGRATION_HTTP_TIMEOUT_SECONDS', '30'))
        return cls(base_url=base_url, timeout_seconds=timeout_seconds)

    def request(
        self,
        method: str,
        path: str,
        *,
        token: str | None = None,
        json_body: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        expected_status: int | Iterable[int] | None = None,
    ) -> HTTPResponse:
        request_headers = {'Content-Type': 'application/json'}
        if headers:
            request_headers.update(headers)
        if token:
            request_headers['Authorization'] = f'Bearer {token}'

        response = requests.request(
            method=method.upper(),
            url=f'{self.base_url}{path}',
            json=json_body,
            params=params,
            headers=request_headers,
            timeout=self.timeout_seconds,
        )

        try:
            data = response.json()
            if not isinstance(data, dict):
                data = {'result': data}
        except ValueError:
            data = {}

        if expected_status is not None:
            if isinstance(expected_status, int):
                expected = {expected_status}
            else:
                expected = set(expected_status)
            if response.status_code not in expected:
                raise AssertionError(f'{method.upper()} {path} returned {response.status_code}, expected {sorted(expected)}. body={response.text}')

        return HTTPResponse(
            status=response.status_code,
            data=data,
            text=response.text,
            headers=dict(response.headers),
        )


def post_with_payload_fallback(
    client: IntegrationApiClient,
    path: str,
    payloads: Sequence[dict[str, Any]],
    *,
    token: str | None = None,
    expected_status: int,
) -> HTTPResponse:
    attempts: list[str] = []
    for payload in payloads:
        response = client.request('POST', path, token=token, json_body=payload, expected_status=None)
        attempts.append(f'payload={payload} -> status={response.status}')
        if response.status == expected_status:
            return response
    raise AssertionError(f'All payload attempts failed for POST {path}; expected status {expected_status}. Attempts: {"; ".join(attempts)}')


def create_authenticated_user(client: IntegrationApiClient) -> dict[str, str]:
    email = unique_email()
    password = 'SecureP@ss123!'
    name = 'Integration Test'

    register_response = client.request(
        'POST',
        '/auth/register',
        json_body={'email': email, 'password': password, 'name': name},
        expected_status=201,
    )
    register_token = require_field(register_response.data, 'access_token')

    login_response = client.request(
        'POST',
        '/auth/login',
        json_body={'email': email, 'password': password},
        expected_status=200,
    )
    login_token = require_field(login_response.data, 'access_token')

    return {
        'email': email,
        'password': password,
        'name': name,
        'register_token': register_token,
        'login_token': login_token,
    }


def upload_cv_and_get_id(client: IntegrationApiClient, token: str) -> str:
    cv_text = 'Jane Doe\nSenior Backend Engineer\nBuilt Python APIs, AWS Lambda workloads, DynamoDB data models, and CI pipelines.'
    cv_file_content = base64.b64encode(cv_text.encode('utf-8')).decode('utf-8')
    payloads = [
        {'text_content': cv_text},
        {'file_content': cv_file_content, 'file_type': 'txt'},
    ]
    response = post_with_payload_fallback(
        client,
        '/users/me/cv',
        payloads,
        token=token,
        expected_status=201,
    )
    return str(require_field(response.data, 'cv_id', 'id'))


def create_job_and_get_id(client: IntegrationApiClient, token: str) -> str:
    payloads = [
        {
            'title': 'Senior Backend Engineer',
            'company': 'Integration Labs',
            'job_description': 'Build secure backend APIs, queues, and CI guardrails.',
            'url': 'https://example.com/jobs/backend-1',
        },
        {
            'position': 'Senior Backend Engineer',
            'company': 'Integration Labs',
            'description': 'Build secure backend APIs, queues, and CI guardrails.',
            'url': 'https://example.com/jobs/backend-1',
        },
    ]
    response = post_with_payload_fallback(
        client,
        '/jobs',
        payloads,
        token=token,
        expected_status=201,
    )
    return str(require_field(response.data, 'job_id', 'id'))


def generate_gap_questions(
    client: IntegrationApiClient,
    token: str,
    cv_id: str,
    job_id: str,
) -> tuple[HTTPResponse, list[dict[str, Any]]]:
    response = client.request(
        'POST',
        '/gap-analysis/questions',
        token=token,
        json_body={'cv_id': cv_id, 'job_id': job_id},
        expected_status=200,
    )
    questions = optional_field(response.data, 'questions')
    if not isinstance(questions, list):
        raise AssertionError(f'Expected list[questions]. payload={response.data}')
    return response, [q for q in questions if isinstance(q, dict)]


def submit_gap_responses(
    client: IntegrationApiClient,
    token: str,
    cv_id: str,
    job_id: str,
    questions: Sequence[dict[str, Any]],
) -> tuple[HTTPResponse, list[str]]:
    response_items: list[dict[str, str]] = []
    for question in questions[:10]:
        question_id = question.get('question_id') or question.get('id')
        if question_id:
            response_items.append(
                {
                    'question_id': str(question_id),
                    'response': 'Integration response describing measurable impact and STAR evidence.',
                }
            )

    if not response_items:
        raise AssertionError('No question ids were returned for gap response submission.')

    payloads = [
        {'cv_id': cv_id, 'job_id': job_id, 'responses': response_items},
        {'cv_id': cv_id, 'job_id': job_id, 'answers': response_items},
    ]
    response = post_with_payload_fallback(
        client,
        f'/jobs/{job_id}/gap-responses',
        payloads,
        token=token,
        expected_status=201,
    )

    ids_value = optional_field(response.data, 'gap_response_ids', 'response_ids', 'ids')
    ids: list[str] = []
    if isinstance(ids_value, list):
        ids = [str(v) for v in ids_value if v]
    if not ids:
        # The current gap-responses contract returns aggregate save status without ids.
        # Reuse submitted question ids as downstream dependency handles.
        ids = [item['question_id'] for item in response_items if item.get('question_id')]
    if not ids:
        raise AssertionError(f'Expected non-empty gap response ids. payload={response.data}')
    return response, ids


def submit_vpr_generate(
    client: IntegrationApiClient,
    token: str,
    cv_id: str,
    job_id: str,
    gap_response_ids: Sequence[str],
    *,
    overrides: dict[str, Any] | None = None,
) -> tuple[HTTPResponse, str]:
    payload: dict[str, Any] = {
        'cv_id': cv_id,
        'job_id': job_id,
        'gap_response_ids': list(gap_response_ids),
    }
    if overrides:
        payload.update(overrides)

    response = client.request(
        'POST',
        '/vpr/generate',
        token=token,
        json_body=payload,
        expected_status=202,
    )
    request_id = str(require_field(response.data, 'request_id', 'vpr_id', 'id', 'job_id'))
    return response, request_id


def submit_cv_tailoring_generate(
    client: IntegrationApiClient,
    token: str,
    cv_id: str,
    job_id: str,
    vpr_id: str,
) -> tuple[HTTPResponse, str]:
    response = client.request(
        'POST',
        '/cv-tailoring/generate',
        token=token,
        json_body={'cv_id': cv_id, 'job_id': job_id, 'vpr_id': vpr_id},
        expected_status=202,
    )
    request_id = str(require_field(response.data, 'request_id', 'id', 'tailoring_id'))
    return response, request_id


def poll_until_terminal(
    client: IntegrationApiClient,
    path: str,
    *,
    token: str,
    timeout_seconds: int,
    poll_interval_seconds: int = 5,
) -> HTTPResponse:
    deadline = time.time() + timeout_seconds
    last_payload: dict[str, Any] = {}
    while time.time() < deadline:
        response = client.request('GET', path, token=token, expected_status=200)
        payload = unwrap_payload(response.data)
        last_payload = payload
        status = str(payload.get('status', '')).lower()
        if status in TERMINAL_STATUSES:
            return response
        if status in IN_FLIGHT_STATUSES or not status:
            time.sleep(poll_interval_seconds)
            continue
        time.sleep(poll_interval_seconds)
    raise AssertionError(f'Timed out waiting for terminal status on {path}. last_payload={last_payload}')


def fetch_json_from_url(url: str) -> dict[str, Any]:
    response = requests.get(url, timeout=30)
    if response.status_code != 200:
        raise AssertionError(f'Expected 200 for result url fetch. got={response.status_code} body={response.text}')
    try:
        data = response.json()
    except ValueError as exc:
        raise AssertionError(f'Result URL did not return JSON. body={response.text}') from exc
    if not isinstance(data, dict):
        raise AssertionError('Expected JSON object from result URL.')
    return data


def maybe_assert_queue_has_messages(queue_url_env_var: str, *, timeout_seconds: int) -> None:
    queue_url = os.getenv(queue_url_env_var, '').strip()
    if not queue_url:
        return

    boto3 = pytest.importorskip('boto3')
    sqs = boto3.client('sqs')
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        attrs = sqs.get_queue_attributes(
            QueueUrl=queue_url,
            AttributeNames=['ApproximateNumberOfMessages', 'ApproximateNumberOfMessagesNotVisible'],
        )['Attributes']
        visible = int(attrs.get('ApproximateNumberOfMessages', '0'))
        invisible = int(attrs.get('ApproximateNumberOfMessagesNotVisible', '0'))
        if visible + invisible > 0:
            return
        time.sleep(2)
    raise AssertionError(f'Expected queue {queue_url_env_var} to receive messages within {timeout_seconds}s.')
