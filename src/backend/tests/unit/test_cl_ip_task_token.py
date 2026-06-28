from __future__ import annotations

import json
from typing import Any
from unittest.mock import MagicMock

import pytest

from careervp.handlers import cover_letter_handler, interview_prep_handler


def _sqs_event(body: dict[str, Any]) -> dict[str, Any]:
    return {
        'Records': [
            {
                'eventSource': 'aws:sqs',
                'body': json.dumps(body),
            }
        ]
    }


def _patch_sfn(monkeypatch: pytest.MonkeyPatch, module: Any) -> MagicMock:
    client = MagicMock()
    monkeypatch.setattr(module, 'sfn', client, raising=False)
    return client


def test_cover_letter_worker_sends_task_success_with_chain_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    sfn = _patch_sfn(monkeypatch, cover_letter_handler)
    worker = MagicMock()
    monkeypatch.setattr(cover_letter_handler, '_generate_and_persist_from_sqs', worker)

    cover_letter_handler._process_sqs_event(
        _sqs_event(
            {
                'job_id': 'app-1',
                'user_id': 'user-1',
                'vpr_id': 'vpr-1',
                'company_context': {'company_name': 'Acme'},
                'task_token': 'token-cl',
            }
        )
    )

    worker.assert_called_once()
    request_data = worker.call_args.kwargs['request_data']
    assert request_data['vpr_id'] == 'vpr-1'
    assert request_data['application_id'] == 'app-1'
    sfn.send_task_success.assert_called_once_with(
        taskToken='token-cl',
        output=json.dumps({'job_id': 'app-1', 'cover_letter_id': 'app-1'}),
    )
    sfn.send_task_failure.assert_not_called()


def test_interview_prep_worker_sends_task_success_with_chain_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    sfn = _patch_sfn(monkeypatch, interview_prep_handler)
    worker = MagicMock()
    monkeypatch.setattr(interview_prep_handler, '_generate_and_persist_from_sqs', worker)

    interview_prep_handler._process_sqs_event(
        _sqs_event(
            {
                'job_id': 'app-1',
                'user_id': 'user-1',
                'vpr_id': 'vpr-1',
                'task_token': 'token-ip',
            }
        )
    )

    worker.assert_called_once()
    request_data = worker.call_args.kwargs['request_data']
    assert request_data['vpr_id'] == 'vpr-1'
    assert request_data['application_id'] == 'app-1'
    sfn.send_task_success.assert_called_once_with(
        taskToken='token-ip',
        output=json.dumps({'job_id': 'app-1', 'interview_prep_id': 'app-1'}),
    )
    sfn.send_task_failure.assert_not_called()


def test_cover_letter_and_interview_prep_failures_send_task_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    for module, token, error_name in (
        (cover_letter_handler, 'token-cl', 'CoverLetterFailed'),
        (interview_prep_handler, 'token-ip', 'InterviewPrepFailed'),
    ):
        sfn = _patch_sfn(monkeypatch, module)
        monkeypatch.setattr(module, '_generate_and_persist_from_sqs', MagicMock(side_effect=RuntimeError('boom')))

        module._process_sqs_event(_sqs_event({'job_id': 'app-1', 'user_id': 'user-1', 'vpr_id': 'vpr-1', 'task_token': token}))

        sfn.send_task_failure.assert_called_once_with(
            taskToken=token,
            error=error_name,
            cause='boom',
        )
        sfn.send_task_success.assert_not_called()


def test_manual_worker_path_without_task_token_does_not_signal_and_still_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    for module in (cover_letter_handler, interview_prep_handler):
        sfn = _patch_sfn(monkeypatch, module)
        monkeypatch.setattr(module, '_generate_and_persist_from_sqs', MagicMock(side_effect=RuntimeError('boom')))

        with pytest.raises(RuntimeError, match='boom'):
            module._process_sqs_event(_sqs_event({'job_id': 'manual-1', 'user_id': 'user-1', 'request_data': {'vpr_id': 'vpr-1'}}))

        sfn.send_task_success.assert_not_called()
        sfn.send_task_failure.assert_not_called()
