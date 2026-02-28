"""
L3.3 — Trial Credit Charging Unit Tests

Validates: credit charged BEFORE LLM call, state transitions wired, exhausted/expired trial blocks LLM.
Spec: docs/best_practices/yaml/trial_enforcement_spec.yaml
Payload: docs/refactor/payloads/beta_l3_application_state_test.json#L3_3_trial_credit_charging
Invariant: I5, I6
Results: docs/beta/execution_results/L3_3_results.md
"""

from __future__ import annotations

import json
import os
from unittest.mock import MagicMock, patch

import pytest

from careervp.logic.trial_service import TrialExhaustedException, TrialExpiredException, TrialService
from careervp.models.result import Result, ResultCode

os.environ.setdefault('AWS_ACCESS_KEY_ID', 'testing')
os.environ.setdefault('AWS_SECRET_ACCESS_KEY', 'testing')
os.environ.setdefault('AWS_DEFAULT_REGION', 'us-east-1')
os.environ.setdefault('DYNAMODB_TABLE_NAME', 'careervp-users-table-test')
os.environ.setdefault('ENVIRONMENT', 'test')


def _event(path: str = '/jobs/job-1/gap-questions') -> dict[str, object]:
    return {
        'httpMethod': 'POST',
        'path': path,
        'pathParameters': {'jobId': 'job-1'},
        'requestContext': {'authorizer': {'claims': {'sub': 'user-1'}}},
        'headers': {'Content-Type': 'application/json'},
        'body': json.dumps({'cv_id': 'cv-1', 'job_id': 'job-1', 'application_id': 'app-1'}),
    }


@pytest.mark.unit
class TestCreditChargedBeforeLLM:
    def test_credit_charged_before_llm_called(self) -> None:
        from careervp.handlers.gap_handler import lambda_handler

        call_order: list[str] = []
        trial_service = MagicMock()
        trial_service.check_trial_status.side_effect = lambda user_id: call_order.append('check_trial_status') or {
            'is_active': True
        }
        trial_service.consume_credit.side_effect = lambda user_id: call_order.append('consume_credit')

        app_repo = MagicMock()
        app_repo.update_state.side_effect = lambda **_: call_order.append('update_state')

        with (
            patch('careervp.handlers.gap_handler._get_trial_service', return_value=trial_service),
            patch('careervp.handlers.gap_handler._get_application_repository', return_value=app_repo),
            patch('careervp.handlers.gap_handler._get_table') as mock_table,
            patch('careervp.handlers.gap_handler.generate_gap_questions') as mock_generate,
        ):
            mock_table.return_value = MagicMock()
            mock_generate.side_effect = lambda **_: call_order.append('generate_gap_questions') or Result(
                success=True,
                data=[{'question_id': 'q-1', 'question': 'Describe impact', 'tags': ['[CV IMPACT]']}],
                code=ResultCode.GAP_QUESTIONS_GENERATED,
            )
            response = lambda_handler(_event(), MagicMock())

        assert response['statusCode'] == 201
        assert call_order.index('consume_credit') < call_order.index('generate_gap_questions')
        assert app_repo.update_state.call_count == 2
        assert app_repo.update_state.call_args_list[0].kwargs['new_state'] == 'gap_questions_pending'
        assert app_repo.update_state.call_args_list[1].kwargs['new_state'] == 'gap_questions_ready'

    def test_llm_not_called_when_trial_exhausted(self) -> None:
        from careervp.handlers.gap_handler import lambda_handler

        trial_service = MagicMock()
        trial_service.check_trial_status.return_value = {'is_active': True}
        trial_service.consume_credit.side_effect = TrialExhaustedException('user-1', 3)
        with (
            patch('careervp.handlers.gap_handler._get_trial_service', return_value=trial_service),
            patch('careervp.handlers.gap_handler.generate_gap_questions') as mock_generate,
        ):
            response = lambda_handler(_event(), MagicMock())

        assert response['statusCode'] == 403
        mock_generate.assert_not_called()

    def test_llm_not_called_when_trial_expired(self) -> None:
        from careervp.handlers.gap_handler import lambda_handler

        trial_service = MagicMock()
        trial_service.check_trial_status.side_effect = TrialExpiredException('user-1', 15)
        with (
            patch('careervp.handlers.gap_handler._get_trial_service', return_value=trial_service),
            patch('careervp.handlers.gap_handler.generate_gap_questions') as mock_generate,
        ):
            response = lambda_handler(_event(), MagicMock())

        assert response['statusCode'] == 403
        mock_generate.assert_not_called()

    def test_consume_credit_called_once_per_request(self) -> None:
        from careervp.handlers.gap_handler import lambda_handler

        trial_service = MagicMock()
        trial_service.check_trial_status.return_value = {'is_active': True}
        trial_service.consume_credit.return_value = None
        with (
            patch('careervp.handlers.gap_handler._get_trial_service', return_value=trial_service),
            patch('careervp.handlers.gap_handler._get_application_repository') as mock_repo_factory,
            patch('careervp.handlers.gap_handler._get_table') as mock_table,
            patch('careervp.handlers.gap_handler.generate_gap_questions') as mock_generate,
        ):
            mock_repo_factory.return_value = MagicMock()
            mock_table.return_value = MagicMock()
            mock_generate.return_value = Result(
                success=True,
                data=[{'question_id': 'q-1', 'question': 'Describe impact', 'tags': ['[CV IMPACT]']}],
                code=ResultCode.GAP_QUESTIONS_GENERATED,
            )
            response = lambda_handler(_event(), MagicMock())

        assert response['statusCode'] == 201
        trial_service.consume_credit.assert_called_once_with('user-1')


@pytest.mark.unit
class TestTrialServiceImplementation:
    def test_trial_service_uses_condition_expression(self) -> None:
        table = MagicMock()
        table.update_item.return_value = {}
        dal = MagicMock()
        dal.table_name = 'table'
        dal._get_db_handler.return_value = table
        service = TrialService(dal=dal)

        service.consume_credit('user-1')

        kwargs = table.update_item.call_args.kwargs
        assert 'application_count < :max' in kwargs['ConditionExpression']
        assert kwargs['ExpressionAttributeValues'][':max'] == 3

    def test_trial_service_check_expiry_by_date(self) -> None:
        table = MagicMock()
        table.get_item.return_value = {
            'Item': {
                'pk': 'USER#user-1',
                'sk': 'TRIAL',
                'created_at': '2020-01-01T00:00:00+00:00',
                'application_count': 0,
                'trial_active': True,
            }
        }
        dal = MagicMock()
        dal.table_name = 'table'
        dal._get_db_handler.return_value = table
        service = TrialService(dal=dal)

        with pytest.raises(TrialExpiredException):
            service.check_trial_status('user-1')

    def test_trial_service_check_app_count(self) -> None:
        table = MagicMock()
        table.get_item.return_value = {
            'Item': {
                'pk': 'USER#user-1',
                'sk': 'TRIAL',
                'created_at': '2026-02-20T00:00:00+00:00',
                'application_count': 3,
                'trial_active': True,
            }
        }
        dal = MagicMock()
        dal.table_name = 'table'
        dal._get_db_handler.return_value = table
        service = TrialService(dal=dal)

        with pytest.raises(TrialExhaustedException):
            service.check_trial_status('user-1')
