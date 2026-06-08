"""
L3.1 — Application Schema Unit Tests

Validates: ApplicationRepository CRUD, 7-state lifecycle, and conditional state writes.
Spec: docs/best_practices/yaml/application_state_spec.yaml
Payload: docs/refactor/payloads/beta_l3_application_state_test.json#L3_1_schema
Invariant: I6
Results: docs/beta/execution_results/L3_1_results.md
"""

from __future__ import annotations

import os
from datetime import datetime
from unittest.mock import MagicMock
from uuid import UUID

import pytest

from careervp.dal.application_repository import APPLICATION_STATES, VALID_TRANSITIONS, ApplicationRepository

os.environ.setdefault('AWS_ACCESS_KEY_ID', 'testing')
os.environ.setdefault('AWS_SECRET_ACCESS_KEY', 'testing')
os.environ.setdefault('AWS_DEFAULT_REGION', 'us-east-1')
os.environ.setdefault('DYNAMODB_TABLE_NAME', 'careervp-users-table-test')
os.environ.setdefault('ENVIRONMENT', 'test')

VALID_STATES = [
    'created',
    'cv_selected',
    'gap_questions_pending',
    'gap_questions_ready',
    'gap_responses_submitted',
    'artifacts_generating',
    'artifacts_completed',
]


@pytest.fixture
def mock_table() -> MagicMock:
    table = MagicMock()
    table.put_item.return_value = {}
    table.update_item.return_value = {}
    table.get_item.return_value = {}
    return table


@pytest.fixture
def repository(mock_table: MagicMock) -> ApplicationRepository:
    dal = MagicMock()
    dal.table_name = 'careervp-users-table-test'
    dal._get_db_handler.return_value = mock_table
    return ApplicationRepository(dal=dal)


@pytest.mark.unit
class TestApplicationCreation:
    def test_application_created_with_correct_schema(self, repository: ApplicationRepository, mock_table: MagicMock) -> None:
        application_id = repository.create(user_id='user-123', job_id='job-456')

        assert application_id
        UUID(application_id)
        mock_table.put_item.assert_called_once()
        item = mock_table.put_item.call_args.kwargs['Item']
        assert item['userId'] == 'user-123'
        assert item['applicationId'] == application_id

    def test_application_initial_state_is_created(self, repository: ApplicationRepository, mock_table: MagicMock) -> None:
        repository.create(user_id='user-123', job_id='job-456')
        item = mock_table.put_item.call_args.kwargs['Item']
        assert item['state'] == 'created'

    def test_application_create_sets_created_at(self, repository: ApplicationRepository, mock_table: MagicMock) -> None:
        repository.create(user_id='user-123', job_id='job-456')
        item = mock_table.put_item.call_args.kwargs['Item']
        assert isinstance(item['created_at'], str)
        datetime.fromisoformat(item['created_at'])

    def test_application_create_sets_user_id(self, repository: ApplicationRepository, mock_table: MagicMock) -> None:
        repository.create(user_id='user-123', job_id='job-456')
        item = mock_table.put_item.call_args.kwargs['Item']
        assert item['user_id'] == 'user-123'

    def test_application_create_sets_job_id(self, repository: ApplicationRepository, mock_table: MagicMock) -> None:
        repository.create(user_id='user-123', job_id='job-456')
        item = mock_table.put_item.call_args.kwargs['Item']
        assert item['job_id'] == 'job-456'

    def test_artifact_statuses_initialized_empty(self, repository: ApplicationRepository, mock_table: MagicMock) -> None:
        repository.create(user_id='user-123', job_id='job-456')
        item = mock_table.put_item.call_args.kwargs['Item']
        assert item['artifact_statuses'] == {}


@pytest.mark.unit
class TestApplicationStateTransitions:
    def test_state_transition_uses_condition_expression(self, repository: ApplicationRepository, mock_table: MagicMock) -> None:
        repository.update_state(
            application_id='app-123',
            user_id='user-123',
            expected_state='created',
            new_state='cv_selected',
        )
        mock_table.update_item.assert_called_once()
        kwargs = mock_table.update_item.call_args.kwargs
        assert '#state = :expected_state' in kwargs['ConditionExpression']
        assert kwargs['ExpressionAttributeValues'][':expected_state'] == 'created'
        assert kwargs['ExpressionAttributeValues'][':new_state'] == 'cv_selected'

    def test_invalid_transition_raises_error(self, repository: ApplicationRepository) -> None:
        with pytest.raises(ValueError, match='Invalid state transition'):
            repository.update_state(
                application_id='app-123',
                user_id='user-123',
                expected_state='cv_selected',
                new_state='artifacts_completed',
            )

    def test_backward_transition_blocked(self, repository: ApplicationRepository) -> None:
        with pytest.raises(ValueError, match='Invalid state transition'):
            repository.update_state(
                application_id='app-123',
                user_id='user-123',
                expected_state='gap_questions_ready',
                new_state='created',
            )

    def test_terminal_state_transition_blocked(self, repository: ApplicationRepository) -> None:
        with pytest.raises(ValueError, match='Invalid state transition'):
            repository.update_state(
                application_id='app-123',
                user_id='user-123',
                expected_state='artifacts_completed',
                new_state='created',
            )

    @pytest.mark.parametrize(
        'from_state,to_state',
        [(from_state, to_state) for from_state, to_states in VALID_TRANSITIONS.items() for to_state in to_states],
    )
    def test_valid_transition_succeeds(
        self,
        from_state: str,
        to_state: str,
        repository: ApplicationRepository,
        mock_table: MagicMock,
    ) -> None:
        mock_table.update_item.reset_mock()
        repository.update_state(
            application_id='app-123',
            user_id='user-123',
            expected_state=from_state,
            new_state=to_state,
        )
        mock_table.update_item.assert_called_once()


@pytest.mark.unit
class TestApplicationStateModel:
    @pytest.mark.parametrize('state', VALID_STATES)
    def test_state_enum_contains_state(self, state: str) -> None:
        assert state in APPLICATION_STATES

    def test_state_enum_has_expected_states(self) -> None:
        # Core 7 states + FE-UI-029 additive Company Research gate states
        # (cr_pending, cr_failed) and artifacts_failed.
        assert len(APPLICATION_STATES) == 10


@pytest.mark.unit
class TestApplicationArtifactStatus:
    def test_update_artifact_status_stores_status(self, repository: ApplicationRepository, mock_table: MagicMock) -> None:
        repository.update_artifact_status(
            application_id='app-123',
            user_id='user-123',
            artifact_type='vpr',
            status='completed',
        )
        kwargs = mock_table.update_item.call_args.kwargs
        assert 'artifact_statuses.#artifact_type = :status' in kwargs['UpdateExpression']
        assert kwargs['ExpressionAttributeNames']['#artifact_type'] == 'vpr'
        assert kwargs['ExpressionAttributeValues'][':status'] == 'completed'

    def test_update_artifact_status_does_not_affect_other_types(self, repository: ApplicationRepository, mock_table: MagicMock) -> None:
        repository.update_artifact_status(
            application_id='app-123',
            user_id='user-123',
            artifact_type='cover_letter',
            status='failed',
        )
        kwargs = mock_table.update_item.call_args.kwargs
        assert kwargs['ExpressionAttributeNames']['#artifact_type'] == 'cover_letter'
        assert kwargs['ExpressionAttributeValues'][':status'] == 'failed'


@pytest.mark.unit
class TestApplicationRepository:
    def test_get_returns_none_for_missing_application(self, repository: ApplicationRepository, mock_table: MagicMock) -> None:
        mock_table.get_item.return_value = {}
        assert repository.get(application_id='app-123', user_id='user-123') is None

    def test_get_returns_application_for_existing(self, repository: ApplicationRepository, mock_table: MagicMock) -> None:
        mock_table.get_item.return_value = {'Item': {'application_id': 'app-123', 'state': 'created'}}
        result = repository.get(application_id='app-123', user_id='user-123')
        assert result is not None
        assert result['application_id'] == 'app-123'

    def test_update_cv_stores_cv_id(self, repository: ApplicationRepository, mock_table: MagicMock) -> None:
        repository.update_cv(application_id='app-123', user_id='user-123', cv_id='cv-321')
        kwargs = mock_table.update_item.call_args.kwargs
        assert 'cv_id = :cv_id' in kwargs['UpdateExpression']
        assert kwargs['ExpressionAttributeValues'][':cv_id'] == 'cv-321'

    def test_no_scan_used_in_any_operation(self, repository: ApplicationRepository, mock_table: MagicMock) -> None:
        repository.create(user_id='user-123', job_id='job-456')
        repository.get(application_id='app-123', user_id='user-123')
        repository.update_cv(application_id='app-123', user_id='user-123', cv_id='cv-321')
        repository.update_artifact_status(
            application_id='app-123',
            user_id='user-123',
            artifact_type='vpr',
            status='completed',
        )
        assert not mock_table.scan.called
