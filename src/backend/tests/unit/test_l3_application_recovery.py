"""
L3.2 — Application Recovery Endpoint Unit Tests

Validates: GET /applications/{id} returns full state for page-reload recovery.
Spec: docs/best_practices/yaml/application_state_spec.yaml
Payload: docs/refactor/payloads/beta_l3_application_state_test.json#L3_2_recovery_endpoint
Invariant: I6
Results: docs/beta/execution_results/L3_2_results.md
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

os.environ.setdefault('AWS_ACCESS_KEY_ID', 'testing')
os.environ.setdefault('AWS_SECRET_ACCESS_KEY', 'testing')
os.environ.setdefault('AWS_DEFAULT_REGION', 'us-east-1')
os.environ.setdefault('DYNAMODB_TABLE_NAME', 'careervp-users-table-test')
os.environ.setdefault('ENVIRONMENT', 'test')

OWNER_USER_ID = 'user-owner-123'
OTHER_USER_ID = 'user-other-456'
APPLICATION_ID = 'app-test-001'

REPO_ROOT = Path(__file__).resolve().parents[4]
CDK_PATH = REPO_ROOT / 'infra' / 'careervp' / 'api_construct.py'
JOB_HANDLER_PATH = REPO_ROOT / 'src' / 'backend' / 'careervp' / 'handlers' / 'job_handler.py'


def _make_event(user_id: str | None, application_id: str = APPLICATION_ID) -> dict:
    request_context: dict[str, object] = {}
    if user_id is not None:
        request_context = {'authorizer': {'claims': {'sub': user_id}}}
    return {
        'httpMethod': 'GET',
        'path': f'/applications/{application_id}',
        'pathParameters': {'application_id': application_id},
        'requestContext': request_context,
        'headers': {'Content-Type': 'application/json'},
        'body': None,
    }


def _make_application_record(state: str = 'created', user_id: str = OWNER_USER_ID) -> dict:
    return {
        'pk': f'USER#{user_id}',
        'sk': f'APP#{APPLICATION_ID}',
        'application_id': APPLICATION_ID,
        'user_id': user_id,
        'state': state,
        'job_id': 'job-xyz789',
        'cv_id': 'cv-abc123' if state != 'created' else None,
        'created_at': '2026-02-26T00:00:00+00:00',
        'updated_at': '2026-02-26T00:00:00+00:00',
        'trial_credit_consumed': state != 'created',
        'artifact_statuses': {
            'vpr': 'completed' if state == 'artifacts_completed' else 'pending',
            'cv_tailored': 'completed' if state == 'artifacts_completed' else 'pending',
            'cover_letter': 'completed' if state == 'artifacts_completed' else 'pending',
            'interview_prep': 'completed' if state == 'artifacts_completed' else 'pending',
            'gap_analysis': 'completed' if state == 'artifacts_completed' else 'pending',
        },
    }


def _make_job_record() -> dict:
    return {
        'job_id': 'job-xyz789',
        'user_id': OWNER_USER_ID,
        'title': 'Principal Engineer',
        'company_name': 'Acme',
        'description': 'Build resilient systems',
        'status': 'active',
    }


@pytest.mark.unit
class TestApplicationRecoveryHTTPStatus:
    def test_recovery_returns_200_for_own_application(self) -> None:
        from careervp.handlers.application_handler import lambda_handler

        event = _make_event(user_id=OWNER_USER_ID)
        with (
            patch('careervp.handlers.application_handler._get_application_repository') as mock_repo_factory,
            patch('careervp.handlers.application_handler._get_jobs_repository') as mock_jobs_factory,
        ):
            mock_repo = MagicMock()
            mock_repo.get.return_value = _make_application_record()
            mock_repo_factory.return_value = mock_repo
            mock_jobs = MagicMock()
            mock_jobs.get_job.return_value = _make_job_record()
            mock_jobs_factory.return_value = mock_jobs

            response = lambda_handler(event, MagicMock())

        assert response['statusCode'] == 200
        payload = json.loads(response['body'])
        assert payload['application']['application_id'] == APPLICATION_ID

    def test_recovery_returns_403_for_wrong_user(self) -> None:
        from careervp.handlers.application_handler import lambda_handler

        event = _make_event(user_id=OTHER_USER_ID)
        with patch('careervp.handlers.application_handler._get_application_repository') as mock_repo_factory:
            mock_repo = MagicMock()
            mock_repo.get.return_value = _make_application_record(user_id=OWNER_USER_ID)
            mock_repo_factory.return_value = mock_repo

            response = lambda_handler(event, MagicMock())

        assert response['statusCode'] == 403

    def test_recovery_returns_404_for_missing_application(self) -> None:
        from careervp.handlers.application_handler import lambda_handler

        event = _make_event(user_id=OWNER_USER_ID)
        with patch('careervp.handlers.application_handler._get_application_repository') as mock_repo_factory:
            mock_repo = MagicMock()
            mock_repo.get.return_value = None
            mock_repo_factory.return_value = mock_repo

            response = lambda_handler(event, MagicMock())

        assert response['statusCode'] == 404

    def test_recovery_returns_401_without_auth(self) -> None:
        from careervp.handlers.application_handler import lambda_handler

        response = lambda_handler(_make_event(user_id=None), MagicMock())
        assert response['statusCode'] == 401


@pytest.mark.unit
class TestApplicationRecoveryResponseFields:
    def test_recovery_response_contains_all_required_fields(self) -> None:
        from careervp.handlers.application_handler import lambda_handler

        event = _make_event(user_id=OWNER_USER_ID)
        with (
            patch('careervp.handlers.application_handler._get_application_repository') as mock_repo_factory,
            patch('careervp.handlers.application_handler._get_jobs_repository') as mock_jobs_factory,
        ):
            mock_repo = MagicMock()
            mock_repo.get.return_value = _make_application_record(state='gap_questions_ready')
            mock_repo_factory.return_value = mock_repo
            mock_jobs = MagicMock()
            mock_jobs.get_job.return_value = _make_job_record()
            mock_jobs_factory.return_value = mock_jobs

            response = lambda_handler(event, MagicMock())

        payload = json.loads(response['body'])
        assert response['statusCode'] == 200
        assert set(payload.keys()) >= {'application', 'job', 'cv', 'gap_analysis', 'artifacts', 'reload_route'}

    def test_recovery_null_gap_questions_when_in_created_state(self) -> None:
        from careervp.handlers.application_handler import lambda_handler

        event = _make_event(user_id=OWNER_USER_ID)
        with patch('careervp.handlers.application_handler._get_application_repository') as mock_repo_factory:
            mock_repo = MagicMock()
            mock_repo.get.return_value = _make_application_record(state='created')
            mock_repo_factory.return_value = mock_repo

            response = lambda_handler(event, MagicMock())

        payload = json.loads(response['body'])
        assert payload['gap_analysis']['questions'] == []
        assert payload['cv'] is None

    def test_recovery_populated_artifacts_when_completed(self) -> None:
        from careervp.handlers.application_handler import lambda_handler

        event = _make_event(user_id=OWNER_USER_ID)
        with patch('careervp.handlers.application_handler._get_application_repository') as mock_repo_factory:
            mock_repo = MagicMock()
            mock_repo.get.return_value = _make_application_record(state='artifacts_completed')
            mock_repo_factory.return_value = mock_repo

            response = lambda_handler(event, MagicMock())

        payload = json.loads(response['body'])
        assert all(item['status'] == 'completed' for item in payload['artifacts'].values())


@pytest.mark.unit
class TestApplicationRecoveryReloadRouting:
    @pytest.mark.parametrize(
        'state,expected_route_prefix',
        [
            ('created', '/applications'),
            ('cv_selected', '/applications'),
            ('gap_questions_pending', '/gap-questions'),
            ('gap_questions_ready', '/gap-questions'),
            ('gap_responses_submitted', '/gap-questions'),
            ('artifacts_generating', '/artifacts'),
            ('artifacts_completed', '/artifacts'),
        ],
    )
    def test_reload_route_matches_state(self, state: str, expected_route_prefix: str) -> None:
        from careervp.handlers.application_handler import lambda_handler

        event = _make_event(user_id=OWNER_USER_ID)
        with patch('careervp.handlers.application_handler._get_application_repository') as mock_repo_factory:
            mock_repo = MagicMock()
            mock_repo.get.return_value = _make_application_record(state=state)
            mock_repo_factory.return_value = mock_repo

            response = lambda_handler(event, MagicMock())

        payload = json.loads(response['body'])
        assert payload['reload_route'].startswith(expected_route_prefix)


@pytest.mark.unit
class TestApplicationRouteWiring:
    def test_route_uses_application_handler_lambda(self) -> None:
        source = CDK_PATH.read_text(encoding='utf-8')
        assert '("/applications/{application_id}", "GET", self.application_api_func)' in source

    def test_route_no_longer_uses_job_handler_lambda(self) -> None:
        source = CDK_PATH.read_text(encoding='utf-8')
        assert '("/applications/{application_id}", "GET", self.job_api_func)' not in source

    def test_job_handler_has_no_compatibility_alias(self) -> None:
        source = JOB_HANDLER_PATH.read_text(encoding='utf-8')
        assert "@app.get('/applications/<application_id>')" not in source
