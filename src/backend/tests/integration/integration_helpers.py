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


def artifact_result(payload: dict[str, Any]) -> dict[str, Any]:
    """Return the generated-content body of an artifact status response.

    The deployed `/{id}/status` contract nests the artifact under `result` and keeps
    only lifecycle fields (`status`, `id`, timestamps) at the top level.
    """
    normalized = unwrap_payload(payload)
    result = normalized.get('result')
    return result if isinstance(result, dict) else normalized


def cv_record(payload: dict[str, Any]) -> dict[str, Any]:
    """Return the parsed-CV body of a `POST /users/me/cv` response (nested under `user_cv`)."""
    normalized = unwrap_payload(payload)
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


def create_authenticated_user(client: IntegrationApiClient, *, require_fresh_registration: bool = False) -> dict[str, str]:
    # Cognito's built-in email sender caps the SignUp verification mail at 50/day for the
    # whole user pool. A suite that registers a fresh user per test exhausts that quota and
    # every later register — including re-registering an existing address — answers 500.
    # Supplying TEST_USER_EMAIL and TEST_USER_PASSWORD reuses an existing account and skips
    # /auth/register entirely. Tests that are about registration itself pass
    # require_fresh_registration=True and always take the register path.
    reuse_email = os.getenv('TEST_USER_EMAIL', '').strip()
    reuse_password = os.getenv('TEST_USER_PASSWORD', '').strip()
    if reuse_email and reuse_password and not require_fresh_registration:
        login = client.request(
            'POST',
            '/auth/login',
            json_body={'email': reuse_email, 'password': reuse_password},
            expected_status=200,
        )
        reused_token = str(require_field(login.data, 'id_token'))
        # A reused account carries the trial counters of every previous run, and the
        # 3-application trial is smaller than one pass of this suite; without this the
        # account 403s `trial_exhausted` on the second run. A freshly registered user needs
        # no reset, so this is confined to the reuse path.
        client.request('POST', '/users/me/trial/reset', token=reused_token, json_body={}, expected_status=200)
        return {
            'email': reuse_email,
            'password': reuse_password,
            'name': 'Integration Test',
            'register_token': '',
            'login_token': reused_token,
            'refresh_token': str(require_field(login.data, 'refresh_token')),
            'cognito_access_token': str(require_field(login.data, 'access_token')),
        }

    email = unique_email()
    password = 'SecureP@ss123!'
    name = 'Integration Test'

    register_response = client.request(
        'POST',
        '/auth/register',
        json_body={'email': email, 'password': password, 'name': name},
        expected_status=201,
    )
    register_token = require_field(register_response.data, 'id_token')

    login_response = client.request(
        'POST',
        '/auth/login',
        json_body={'email': email, 'password': password},
        expected_status=200,
    )
    # The deployed API Gateway authorizer is a COGNITO_USER_POOLS authorizer, which
    # accepts the ID token only; the access token is rejected with 401 on every
    # authenticated route. The frontend does the same (src/frontend/lib/auth.ts
    # getCurrentToken -> session.getIdToken()).
    login_token = require_field(login_response.data, 'id_token')
    # Retained for the two Cognito/OAuth wires that do NOT go through the product
    # authorizer: POST /auth/refresh consumes the refresh token, and POST /auth/logout
    # decodes whichever Cognito token it is given. Never send these to a product route.
    refresh_token = require_field(login_response.data, 'refresh_token')
    cognito_access_token = require_field(login_response.data, 'access_token')

    return {
        'email': email,
        'password': password,
        'name': name,
        'register_token': register_token,
        'login_token': login_token,
        'refresh_token': refresh_token,
        'cognito_access_token': cognito_access_token,
    }


# Named employers and dated roles are required: the parser rejects a work entry whose
# company is absent (`WorkExperience.company` is a required str), which 500s the upload.
INTEGRATION_CV_TEXT = (
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
INTEGRATION_JOB_URL = 'https://example.com/'


def upload_cv_and_get_id(client: IntegrationApiClient, token: str) -> str:
    # Canonical shape, identical to what src/frontend/app/cv-center/page.tsx posts:
    # base64 file content under `cv_content`, plus `file_name` and `file_type`.
    payload = {
        'cv_content': base64.b64encode(INTEGRATION_CV_TEXT.encode('utf-8')).decode('utf-8'),
        'file_name': 'integration-jane-doe-cv.txt',
        'file_type': 'txt',
    }
    response = client.request('POST', '/users/me/cv', token=token, json_body=payload, expected_status=201)
    return str(require_field(cv_record(response.data), 'cv_id', 'id'))


def create_job_and_get_id(client: IntegrationApiClient, token: str) -> str:
    # Canonical CreateJobInput from src/frontend/lib/types.ts:53 — `company_name` and
    # `description`, not the `company`/`job_description` aliases job_handler still maps.
    payload = {
        'title': 'Senior Backend Engineer',
        'company_name': 'Integration Labs',
        'description': 'Build secure backend APIs, queues, and CI guardrails.',
        'url': INTEGRATION_JOB_URL,
    }
    response = client.request('POST', '/jobs', token=token, json_body=payload, expected_status=201)
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

    # Canonical body from src/frontend/api/methods.ts:154 — `{responses}` only; the
    # deployed GapResponseRequest carries no cv_id/job_id fields, and the wire answers 200.
    response = client.request(
        'POST',
        f'/jobs/{job_id}/gap-responses',
        token=token,
        json_body={'responses': response_items},
        expected_status=200,
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
    # Bare `GET /{artifact}/{id}` is not a routed method on the deployed API; it returns
    # the API Gateway DEFAULT_4XX response (403), which reads like an auth failure. The
    # only artifact read route is `/{id}/status`, so refuse to poll anything else.
    if not path.endswith('/status'):
        raise AssertionError(f'Artifact polling must target /{{id}}/status; got {path}')
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
