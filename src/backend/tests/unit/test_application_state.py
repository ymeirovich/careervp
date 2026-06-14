"""
Application state model and recovery tests.

Spec: docs/best_practices/yaml/application_state_spec.yaml
Payload: docs/refactor/payloads/beta_l3_application_state_test.json
Invariant: I6
"""

from __future__ import annotations

import json
import os
from unittest.mock import MagicMock, patch

import pytest

from careervp.dal.application_repository import APPLICATION_STATES, VALID_TRANSITIONS, ApplicationRepository

os.environ.setdefault('AWS_ACCESS_KEY_ID', 'testing')
os.environ.setdefault('AWS_SECRET_ACCESS_KEY', 'testing')
os.environ.setdefault('AWS_DEFAULT_REGION', 'us-east-1')
os.environ.setdefault('DYNAMODB_TABLE_NAME', 'careervp-users-table-test')
os.environ.setdefault('ENVIRONMENT', 'test')


def _event(user_id: str | None, application_id: str = 'app-xyz789') -> dict[str, object]:
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


def _application_record(state: str = 'created', user_id: str = 'user-test-123') -> dict[str, object]:
    return {
        'pk': f'USER#{user_id}',
        'sk': 'APP#app-xyz789',
        'application_id': 'app-xyz789',
        'user_id': user_id,
        'job_id': 'job-abc456',
        'cv_id': 'cv-001' if state != 'created' else None,
        'state': state,
        'created_at': '2026-02-26T10:00:00+00:00',
        'updated_at': '2026-02-26T10:10:00+00:00',
        'trial_credit_consumed': state != 'created',
        'artifact_statuses': {
            'vpr': 'pending',
            'cv_tailored': 'pending',
            'cover_letter': 'pending',
            'interview_prep': 'pending',
            'gap_analysis': 'pending',
        },
    }


@pytest.fixture
def repository() -> ApplicationRepository:
    table = MagicMock()
    table.put_item.return_value = {}
    table.update_item.return_value = {}
    table.get_item.return_value = {}
    dal = MagicMock()
    dal.table_name = 'careervp-users-table-test'
    dal._get_db_handler.return_value = table
    repo = ApplicationRepository(dal=dal)
    repo._test_table = table  # type: ignore[attr-defined]
    return repo


@pytest.mark.unit
class TestApplicationStateModel:
    def test_all_states_are_canonical(self) -> None:
        # Core 7-state machine remains unchanged; FE-UI-029 adds the additive
        # Company Research gate states; FE-UI-039 adds artifacts_partial.
        expected = (
            'created',
            'cv_selected',
            'gap_questions_pending',
            'gap_questions_ready',
            'gap_responses_submitted',
            'cr_pending',
            'cr_failed',
            'artifacts_generating',
            'artifacts_partial',
            'artifacts_completed',
            'artifacts_failed',
        )
        assert APPLICATION_STATES == expected

    def test_valid_transitions_cover_all_states(self) -> None:
        assert set(VALID_TRANSITIONS.keys()) == set(APPLICATION_STATES)

    def test_invalid_transition_raises_error(self, repository: ApplicationRepository) -> None:
        with pytest.raises(ValueError, match='Invalid state transition'):
            repository.update_state(
                application_id='app-xyz789',
                user_id='user-test-123',
                expected_state='artifacts_completed',
                new_state='created',
            )

    def test_state_transition_uses_conditional_write(self, repository: ApplicationRepository) -> None:
        repository.update_state(
            application_id='app-xyz789',
            user_id='user-test-123',
            expected_state='created',
            new_state='cv_selected',
        )
        table = repository._test_table  # type: ignore[attr-defined]
        kwargs = table.update_item.call_args.kwargs
        assert '#state = :expected_state' in kwargs['ConditionExpression']


@pytest.mark.unit
class TestCompanyResearchGate:
    def test_cr_gate_transitions_are_valid(self) -> None:
        assert 'cr_pending' in VALID_TRANSITIONS['gap_responses_submitted']
        assert set(VALID_TRANSITIONS['cr_pending']) == {'artifacts_generating', 'cr_failed'}
        assert VALID_TRANSITIONS['cr_failed'] == ('cr_pending',)

    def test_legacy_direct_path_still_allowed(self) -> None:
        # Feature-flag OFF path: gap_responses_submitted → artifacts_generating directly.
        assert 'artifacts_generating' in VALID_TRANSITIONS['gap_responses_submitted']

    def test_invalid_transition_raises_typed_error(self, repository: ApplicationRepository) -> None:
        from careervp.models.exceptions import InvalidStateTransitionError

        with pytest.raises(InvalidStateTransitionError):
            repository.update_state(
                application_id='app-xyz789',
                user_id='user-test-123',
                expected_state='cr_failed',
                new_state='artifacts_completed',
            )

    def test_cr_transition_uses_conditional_write(self, repository: ApplicationRepository) -> None:
        repository.update_state(
            application_id='app-xyz789',
            user_id='user-test-123',
            expected_state='cr_pending',
            new_state='cr_failed',
        )
        kwargs = repository._test_table.update_item.call_args.kwargs  # type: ignore[attr-defined]
        assert '#state = :expected_state' in kwargs['ConditionExpression']

    def test_set_company_research_error_marks_artifact_failed(self, repository: ApplicationRepository) -> None:
        repository.set_company_research_error(
            application_id='app-xyz789',
            user_id='user-test-123',
            error=True,
        )
        table = repository._test_table  # type: ignore[attr-defined]
        first_call = table.update_item.call_args_list[0].kwargs
        second_call = table.update_item.call_args_list[1].kwargs
        assert first_call['ExpressionAttributeValues'][':error'] is True
        assert second_call['ExpressionAttributeNames']['#cr'] == 'company_research'
        assert second_call['ExpressionAttributeValues'][':cr_status'] == 'failed'

    def test_set_company_research_error_is_idempotent(self, repository: ApplicationRepository) -> None:
        repository.set_company_research_error('app-xyz789', 'user-test-123', True)
        repository.set_company_research_error('app-xyz789', 'user-test-123', True)
        # No conditional-state write: double-call writes the same flag without raising.
        for call in repository._test_table.update_item.call_args_list:  # type: ignore[attr-defined]
            assert ':expected_state' not in call.kwargs.get('ExpressionAttributeValues', {})

    def test_set_company_research_error_clears_to_pending(self, repository: ApplicationRepository) -> None:
        repository.set_company_research_error('app-xyz789', 'user-test-123', False)
        second_call = repository._test_table.update_item.call_args_list[1].kwargs  # type: ignore[attr-defined]
        assert second_call['ExpressionAttributeValues'][':cr_status'] == 'pending'


@pytest.mark.unit
class TestRecoveryCompanyResearch:
    def test_recovery_includes_company_research_artifact(self) -> None:
        from careervp.handlers.application_handler import lambda_handler

        record = _application_record(state='cr_pending', user_id='user-test-123')
        record['artifact_statuses']['company_research'] = 'processing'  # type: ignore[index]
        with (
            patch('careervp.handlers.application_handler._get_application_repository') as mock_repo_factory,
            patch('careervp.handlers.application_handler._get_jobs_repository') as mock_jobs_factory,
        ):
            mock_repo = MagicMock()
            mock_repo.get.return_value = record
            mock_repo_factory.return_value = mock_repo
            mock_jobs = MagicMock()
            mock_jobs.get_job.return_value = {'job_id': 'job-abc456'}
            mock_jobs_factory.return_value = mock_jobs
            response = lambda_handler(_event('user-test-123'), MagicMock())

        payload = json.loads(response['body'])
        assert payload['artifacts']['company_research']['status'] == 'processing'
        assert payload['reload_route'] == '/artifacts'

    def test_recovery_includes_company_research_error_flag(self) -> None:
        from careervp.handlers.application_handler import lambda_handler

        record = _application_record(state='cr_failed', user_id='user-test-123')
        record['company_research_error'] = True
        with patch('careervp.handlers.application_handler._get_application_repository') as mock_repo_factory:
            mock_repo = MagicMock()
            mock_repo.get.return_value = record
            mock_repo_factory.return_value = mock_repo
            response = lambda_handler(_event('user-test-123'), MagicMock())

        payload = json.loads(response['body'])
        assert payload['application']['company_research_error'] is True

    def test_recovery_defaults_company_research_error_false(self) -> None:
        from careervp.handlers.application_handler import lambda_handler

        with patch('careervp.handlers.application_handler._get_application_repository') as mock_repo_factory:
            mock_repo = MagicMock()
            mock_repo.get.return_value = _application_record(state='created')
            mock_repo_factory.return_value = mock_repo
            response = lambda_handler(_event('user-test-123'), MagicMock())

        payload = json.loads(response['body'])
        assert payload['application']['company_research_error'] is False
        assert payload['artifacts']['company_research']['status'] == 'pending'


@pytest.mark.unit
class TestApplicationRecovery:
    def test_recovery_returns_200_for_owner(self) -> None:
        from careervp.handlers.application_handler import lambda_handler

        with (
            patch('careervp.handlers.application_handler._get_application_repository') as mock_repo_factory,
            patch('careervp.handlers.application_handler._get_jobs_repository') as mock_jobs_factory,
        ):
            mock_repo = MagicMock()
            mock_repo.get.return_value = _application_record(user_id='user-test-123')
            mock_repo_factory.return_value = mock_repo
            mock_jobs = MagicMock()
            mock_jobs.get_job.return_value = {'job_id': 'job-abc456', 'title': 'Engineer'}
            mock_jobs_factory.return_value = mock_jobs
            response = lambda_handler(_event('user-test-123'), MagicMock())

        assert response['statusCode'] == 200
        payload = json.loads(response['body'])
        assert payload['application']['application_id'] == 'app-xyz789'

    def test_recovery_returns_403_for_wrong_user(self) -> None:
        from careervp.handlers.application_handler import lambda_handler

        with patch('careervp.handlers.application_handler._get_application_repository') as mock_repo_factory:
            mock_repo = MagicMock()
            mock_repo.get.return_value = _application_record(user_id='owner-user')
            mock_repo_factory.return_value = mock_repo
            response = lambda_handler(_event('other-user'), MagicMock())
        assert response['statusCode'] == 403

    def test_recovery_returns_404_for_missing_application(self) -> None:
        from careervp.handlers.application_handler import lambda_handler

        with (
            patch('careervp.handlers.application_handler._get_application_repository') as mock_repo_factory,
            patch('careervp.handlers.application_handler._get_jobs_repository') as mock_jobs_factory,
        ):
            mock_repo = MagicMock()
            mock_repo.get.return_value = None
            mock_repo_factory.return_value = mock_repo
            mock_jobs = MagicMock()
            mock_jobs.get_job.return_value = None
            mock_jobs_factory.return_value = mock_jobs
            response = lambda_handler(_event('user-test-123'), MagicMock())
        assert response['statusCode'] == 404


@pytest.mark.unit
class TestArtifactStatusTracking:
    def test_artifact_status_updates_on_worker_complete(self, repository: ApplicationRepository) -> None:
        repository.update_artifact_status(
            application_id='app-xyz789',
            user_id='user-test-123',
            artifact_type='vpr',
            status='completed',
        )
        table = repository._test_table  # type: ignore[attr-defined]
        kwargs = table.update_item.call_args.kwargs
        assert kwargs['ExpressionAttributeNames']['#artifact_type'] == 'vpr'
        assert kwargs['ExpressionAttributeValues'][':status'] == 'completed'

    def test_artifact_status_updates_on_worker_fail(self, repository: ApplicationRepository) -> None:
        repository.update_artifact_status(
            application_id='app-xyz789',
            user_id='user-test-123',
            artifact_type='cover_letter',
            status='failed',
        )
        table = repository._test_table  # type: ignore[attr-defined]
        kwargs = table.update_item.call_args.kwargs
        assert kwargs['ExpressionAttributeNames']['#artifact_type'] == 'cover_letter'
        assert kwargs['ExpressionAttributeValues'][':status'] == 'failed'


@pytest.mark.unit
class TestReloadRecovery:
    @pytest.mark.parametrize(
        'state,expected_prefix',
        [
            ('created', '/applications'),
            ('cv_selected', '/applications'),
            ('gap_questions_ready', '/gap-questions'),
            ('gap_responses_submitted', '/gap-questions'),
            ('artifacts_generating', '/artifacts'),
            ('artifacts_partial', '/artifacts'),
            ('artifacts_completed', '/artifacts'),
        ],
    )
    def test_reload_returns_correct_state_field(self, state: str, expected_prefix: str) -> None:
        from careervp.handlers.application_handler import lambda_handler

        with patch('careervp.handlers.application_handler._get_application_repository') as mock_repo_factory:
            mock_repo = MagicMock()
            mock_repo.get.return_value = _application_record(state=state)
            mock_repo_factory.return_value = mock_repo
            response = lambda_handler(_event('user-test-123'), MagicMock())

        assert response['statusCode'] == 200
        payload = json.loads(response['body'])
        assert payload['reload_route'].startswith(expected_prefix)

    def test_trial_credit_not_double_charged_on_reload(self) -> None:
        from careervp.handlers.application_handler import lambda_handler

        with patch('careervp.handlers.application_handler._get_application_repository') as mock_repo_factory:
            mock_repo = MagicMock()
            mock_repo.get.return_value = _application_record(state='gap_questions_pending')
            mock_repo_factory.return_value = mock_repo
            response = lambda_handler(_event('user-test-123'), MagicMock())

        payload = json.loads(response['body'])
        assert payload['application']['trial_credit_consumed'] is True
