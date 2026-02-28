"""
L3.4 — State Recovery Unit Tests

Validates: page reload at each of 7 states restores correct workflow state.
Spec: docs/best_practices/yaml/application_state_spec.yaml
Payload: docs/refactor/payloads/beta_l3_application_state_test.json#L3_4_state_recovery
Invariant: I6
Results: docs/beta/execution_results/L3_4_results.md
"""

from __future__ import annotations

import json
import os
from unittest.mock import MagicMock, patch

import pytest

os.environ.setdefault('AWS_ACCESS_KEY_ID', 'testing')
os.environ.setdefault('AWS_SECRET_ACCESS_KEY', 'testing')
os.environ.setdefault('AWS_DEFAULT_REGION', 'us-east-1')
os.environ.setdefault('DYNAMODB_TABLE_NAME', 'careervp-users-table-test')
os.environ.setdefault('ENVIRONMENT', 'test')

USER_ID = 'user-test-123'
APPLICATION_ID = 'app-test-001'
JOB_ID = 'job-xyz789'
CV_ID = 'cv-abc456'


def _event() -> dict[str, object]:
    return {
        'httpMethod': 'GET',
        'path': f'/applications/{APPLICATION_ID}',
        'pathParameters': {'application_id': APPLICATION_ID},
        'requestContext': {'authorizer': {'claims': {'sub': USER_ID}}},
        'headers': {'Content-Type': 'application/json'},
        'body': None,
    }


def _app(state: str, **overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        'application_id': APPLICATION_ID,
        'user_id': USER_ID,
        'state': state,
        'job_id': JOB_ID,
        'cv_id': None,
        'created_at': '2026-02-26T00:00:00+00:00',
        'updated_at': '2026-02-26T00:00:00+00:00',
        'trial_credit_consumed': state != 'created',
        'artifact_statuses': {},
        'gap_questions': [],
        'gap_responses': [],
    }
    base.update(overrides)
    return base


@pytest.mark.unit
class TestCreatedStateRecovery:
    def test_created_state_recovery(self) -> None:
        from careervp.handlers.application_handler import lambda_handler

        with patch('careervp.handlers.application_handler._get_application_repository') as mock_repo_factory:
            mock_repo = MagicMock()
            mock_repo.get.return_value = _app('created')
            mock_repo_factory.return_value = mock_repo
            response = lambda_handler(_event(), MagicMock())

        payload = json.loads(response['body'])
        assert response['statusCode'] == 200
        assert payload['cv'] is None
        assert payload['gap_analysis']['questions'] == []
        assert payload['reload_route'].startswith('/applications')


@pytest.mark.unit
class TestGapQuestionsReadyRecovery:
    def test_gap_questions_ready_recovery(self) -> None:
        from careervp.handlers.application_handler import lambda_handler

        with patch('careervp.handlers.application_handler._get_application_repository') as mock_repo_factory:
            mock_repo = MagicMock()
            mock_repo.get.return_value = _app(
                'gap_questions_ready',
                cv_id=CV_ID,
                gap_questions=[{'question_id': 'q-1', 'question': 'Describe impact'}],
            )
            mock_repo_factory.return_value = mock_repo
            response = lambda_handler(_event(), MagicMock())

        payload = json.loads(response['body'])
        assert response['statusCode'] == 200
        assert payload['cv'] == {'cv_id': CV_ID}
        assert payload['gap_analysis']['questions']
        assert payload['reload_route'].startswith('/gap-questions')


@pytest.mark.unit
class TestArtifactsGeneratingRecovery:
    def test_artifacts_generating_recovery(self) -> None:
        from careervp.handlers.application_handler import lambda_handler

        with patch('careervp.handlers.application_handler._get_application_repository') as mock_repo_factory:
            mock_repo = MagicMock()
            mock_repo.get.return_value = _app(
                'artifacts_generating',
                cv_id=CV_ID,
                gap_responses=[{'question_id': 'q-1', 'response': 'Impact detail'}],
                artifact_statuses={
                    'vpr': 'completed',
                    'cover_letter': 'generating',
                    'cv_tailored': 'pending',
                    'interview_prep': 'pending',
                    'gap_analysis': 'completed',
                },
            )
            mock_repo_factory.return_value = mock_repo
            response = lambda_handler(_event(), MagicMock())

        payload = json.loads(response['body'])
        assert response['statusCode'] == 200
        assert payload['artifacts']['cover_letter']['status'] == 'generating'
        assert payload['gap_analysis']['responses']
        assert payload['reload_route'].startswith('/artifacts')


@pytest.mark.unit
class TestArtifactsCompletedRecovery:
    def test_artifacts_completed_recovery(self) -> None:
        from careervp.handlers.application_handler import lambda_handler

        with patch('careervp.handlers.application_handler._get_application_repository') as mock_repo_factory:
            mock_repo = MagicMock()
            mock_repo.get.return_value = _app(
                'artifacts_completed',
                cv_id=CV_ID,
                artifact_statuses={
                    'vpr': 'completed',
                    'cover_letter': 'completed',
                    'cv_tailored': 'completed',
                    'interview_prep': 'completed',
                    'gap_analysis': 'completed',
                },
            )
            mock_repo_factory.return_value = mock_repo
            response = lambda_handler(_event(), MagicMock())

        payload = json.loads(response['body'])
        assert response['statusCode'] == 200
        assert all(artifact['status'] == 'completed' for artifact in payload['artifacts'].values())


@pytest.mark.unit
class TestTrialCreditNotDoubleCharged:
    def test_trial_credit_consumed_flag_preserved_on_reload(self) -> None:
        from careervp.handlers.application_handler import lambda_handler

        with patch('careervp.handlers.application_handler._get_application_repository') as mock_repo_factory:
            mock_repo = MagicMock()
            mock_repo.get.return_value = _app('gap_questions_pending', trial_credit_consumed=True)
            mock_repo_factory.return_value = mock_repo
            response = lambda_handler(_event(), MagicMock())

        payload = json.loads(response['body'])
        assert response['statusCode'] == 200
        assert payload['application']['trial_credit_consumed'] is True


@pytest.mark.unit
class TestReloadRouteResolution:
    @pytest.mark.parametrize(
        'state,expected_route_fragment',
        [
            ('created', 'applications'),
            ('cv_selected', 'applications'),
            ('gap_questions_pending', 'gap-questions'),
            ('gap_questions_ready', 'gap-questions'),
            ('gap_responses_submitted', 'gap-questions'),
            ('artifacts_generating', 'artifacts'),
            ('artifacts_completed', 'artifacts'),
        ],
    )
    def test_reload_route_for_state(self, state: str, expected_route_fragment: str) -> None:
        from careervp.handlers.application_handler import lambda_handler

        with patch('careervp.handlers.application_handler._get_application_repository') as mock_repo_factory:
            mock_repo = MagicMock()
            mock_repo.get.return_value = _app(state)
            mock_repo_factory.return_value = mock_repo
            response = lambda_handler(_event(), MagicMock())

        payload = json.loads(response['body'])
        assert response['statusCode'] == 200
        assert expected_route_fragment in payload['reload_route']
