from __future__ import annotations

import json
from typing import Any
from unittest.mock import MagicMock

from botocore.exceptions import ClientError

from careervp.handlers import vpr_worker_handler
from careervp.models.result import Result, ResultCode


def _repo(*, processing_success: bool = True) -> MagicMock:
    repo = MagicMock()
    repo.update_job_status.return_value = Result(
        success=processing_success,
        data={},
        code=ResultCode.SUCCESS if processing_success else ResultCode.DYNAMODB_CONDITION_CHECK_FAILED,
    )
    repo.update_job.return_value = Result(success=True, data={}, code=ResultCode.SUCCESS)
    return repo


def _job() -> dict[str, Any]:
    return {
        'user_id': 'user-1',
        'application_id': 'app-1',
        'input_data': {
            'job_posting': {
                'company_name': 'Acme',
                'role_title': 'Engineer',
                'description': 'Build systems',
                'requirements': ['Python'],
            },
            'gap_responses': [],
        },
    }


def test_success_path_sends_task_success(monkeypatch: Any) -> None:
    repo = _repo()
    cv_dal = MagicMock()
    cv_dal.get_cv.return_value = {'parsed': 'cv'}
    cv_dal.get_next_vpr_version.return_value = 1
    monkeypatch.setattr(vpr_worker_handler, 'DynamoDalHandler', MagicMock(return_value=cv_dal))
    vpr = MagicMock(version=1, word_count=100)
    vpr.model_dump_json.return_value = '{"ok": true}'
    response = MagicMock(vpr=vpr, token_usage=None)
    monkeypatch.setattr(vpr_worker_handler, 'generate_vpr', MagicMock(return_value=Result(success=True, data=response, code=ResultCode.SUCCESS)))
    monkeypatch.setattr(vpr_worker_handler, '_generate_presigned_url', MagicMock(return_value='https://example.test/result'))
    monkeypatch.setattr(vpr_worker_handler.s3, 'put_object', MagicMock())
    monkeypatch.setattr(vpr_worker_handler.sfn, 'send_task_success', MagicMock())
    monkeypatch.setattr(vpr_worker_handler.sfn, 'send_task_failure', MagicMock())

    vpr_worker_handler._execute_job(repo, _job(), 'job-1', 'bucket-1', 'token-1')

    vpr_worker_handler.sfn.send_task_success.assert_called_once_with(
        taskToken='token-1',
        output=json.dumps({'job_id': 'job-1', 'vpr_id': 'job-1'}),
    )
    vpr_worker_handler.sfn.send_task_failure.assert_not_called()


def test_failure_path_sends_task_failure(monkeypatch: Any) -> None:
    repo = _repo()
    cv_dal = MagicMock()
    cv_dal.get_cv.return_value = None
    monkeypatch.setattr(vpr_worker_handler, 'DynamoDalHandler', MagicMock(return_value=cv_dal))
    monkeypatch.setattr(vpr_worker_handler.sfn, 'send_task_failure', MagicMock())

    vpr_worker_handler._execute_job(repo, _job(), 'job-1', 'bucket-1', 'token-1')

    vpr_worker_handler.sfn.send_task_failure.assert_called_once_with(
        taskToken='token-1',
        error='VPRFailed',
        cause='User CV not found',
    )


def test_no_token_is_backward_compatible(monkeypatch: Any) -> None:
    repo = _repo()
    cv_dal = MagicMock()
    cv_dal.get_cv.return_value = None
    monkeypatch.setattr(vpr_worker_handler, 'DynamoDalHandler', MagicMock(return_value=cv_dal))
    monkeypatch.setattr(vpr_worker_handler.sfn, 'send_task_success', MagicMock())
    monkeypatch.setattr(vpr_worker_handler.sfn, 'send_task_failure', MagicMock())

    vpr_worker_handler._execute_job(repo, _job(), 'job-1', 'bucket-1', None)

    vpr_worker_handler.sfn.send_task_success.assert_not_called()
    vpr_worker_handler.sfn.send_task_failure.assert_not_called()


def test_lost_processing_race_does_not_double_signal(monkeypatch: Any) -> None:
    repo = _repo(processing_success=False)
    monkeypatch.setattr(vpr_worker_handler.sfn, 'send_task_success', MagicMock())
    monkeypatch.setattr(vpr_worker_handler.sfn, 'send_task_failure', MagicMock())

    vpr_worker_handler._execute_job(repo, _job(), 'job-1', 'bucket-1', 'token-1')

    vpr_worker_handler.sfn.send_task_success.assert_not_called()
    vpr_worker_handler.sfn.send_task_failure.assert_not_called()


def test_existing_job_posting_status_can_be_claimed(monkeypatch: Any) -> None:
    repo = _repo(processing_success=False)
    monkeypatch.setattr(vpr_worker_handler.sfn, 'send_task_success', MagicMock())
    monkeypatch.setattr(vpr_worker_handler.sfn, 'send_task_failure', MagicMock())
    job = _job()
    job['status'] = 'active'

    vpr_worker_handler._execute_job(repo, job, 'job-1', 'bucket-1', 'token-1')

    repo.update_job_status.assert_called_once()
    assert repo.update_job_status.call_args.kwargs['expected_current_status'] == 'active'
    vpr_worker_handler.sfn.send_task_success.assert_not_called()
    vpr_worker_handler.sfn.send_task_failure.assert_not_called()


def test_s3_failure_sends_task_failure(monkeypatch: Any) -> None:
    repo = _repo()
    cv_dal = MagicMock()
    cv_dal.get_cv.return_value = {'parsed': 'cv'}
    cv_dal.get_next_vpr_version.return_value = 1
    monkeypatch.setattr(vpr_worker_handler, 'DynamoDalHandler', MagicMock(return_value=cv_dal))
    vpr = MagicMock(version=1, word_count=100)
    vpr.model_dump_json.return_value = '{"ok": true}'
    response = MagicMock(vpr=vpr, token_usage=None)
    monkeypatch.setattr(vpr_worker_handler, 'generate_vpr', MagicMock(return_value=Result(success=True, data=response, code=ResultCode.SUCCESS)))
    monkeypatch.setattr(
        vpr_worker_handler.s3,
        'put_object',
        MagicMock(side_effect=ClientError({'Error': {'Code': 'AccessDenied', 'Message': 'denied'}}, 'PutObject')),
    )
    monkeypatch.setattr(vpr_worker_handler.sfn, 'send_task_failure', MagicMock())

    vpr_worker_handler._execute_job(repo, _job(), 'job-1', 'bucket-1', 'token-1')

    vpr_worker_handler.sfn.send_task_failure.assert_called_once()
    assert vpr_worker_handler.sfn.send_task_failure.call_args.kwargs['error'] == 'VPRFailed'
