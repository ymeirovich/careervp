"""RED behavior contract for P-17 worker partial batch failure responses."""

from __future__ import annotations

import importlib
import json
import os
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

FAILED_MESSAGE_ID = 'msg-failed'
BACKEND_SRC = str(Path(__file__).resolve().parents[2])
EXPECTED_FAILURE_RESPONSE = {'batchItemFailures': [{'itemIdentifier': FAILED_MESSAGE_ID}]}
WORKERS = {
    'VprSqsWorkerLambda': ('careervp.handlers.vpr_worker_handler', 'lambda_handler'),
    'CoverLetterWorkerLambda': ('careervp.handlers.cover_letter_handler', 'lambda_handler'),
    'InterviewPrepWorkerLambda': ('careervp.handlers.interview_prep_handler', 'lambda_handler'),
    'CvTailorWorkerLambda': ('careervp.handlers.cv_tailoring_handler', 'handler'),
    'CompanyResearchWorkerLambda': ('careervp.handlers.company_research_worker_handler', 'lambda_handler'),
}


def _sqs_record(message_id: str, job_id: str) -> dict[str, Any]:
    return {
        'messageId': message_id,
        'eventSource': 'aws:sqs',
        'attributes': {'ApproximateReceiveCount': '1'},
        'body': json.dumps(
            {
                'job_id': job_id,
                'user_id': 'user-p17',
                'application_id': 'app-p17',
                'company_name': 'Acme',
                'task_token': 'token-p17',
                'request_data': {
                    'cv_id': 'cv-p17',
                    'job_id': job_id,
                    'application_id': 'app-p17',
                    'vpr_id': 'vpr-p17',
                    'gap_response_ids': ['gap-p17'],
                },
            }
        ),
    }


def _sqs_batch_with_one_failure() -> dict[str, list[dict[str, Any]]]:
    return {
        'Records': [
            _sqs_record('msg-good-1', 'job-good-1'),
            _sqs_record(FAILED_MESSAGE_ID, 'job-failed'),
            _sqs_record('msg-good-2', 'job-good-2'),
        ]
    }


def _import_worker(module_name: str) -> Any:
    sys.path = [path for path in sys.path if path != BACKEND_SRC]
    sys.path.insert(0, BACKEND_SRC)
    for loaded_name, module in list(sys.modules.items()):
        if loaded_name == 'careervp' or loaded_name.startswith('careervp.'):
            module_file = str(getattr(module, '__file__', '') or '')
            if not module_file.startswith(BACKEND_SRC):
                sys.modules.pop(loaded_name, None)
    try:
        return importlib.import_module(module_name)
    except Exception as exc:  # noqa: BLE001
        return {'import_error': f'{type(exc).__name__}: {exc}'}


def _side_effect_from_record(record: dict[str, Any]) -> None:
    if record.get('messageId') == FAILED_MESSAGE_ID:
        raise RuntimeError('p17 forced failed record')


def _side_effect_from_job_id(*_args: Any, **kwargs: Any) -> None:
    if kwargs.get('job_id') == 'job-failed':
        raise RuntimeError('p17 forced failed record')


def _call_worker(construct_id: str, module_name: str, handler_name: str, monkeypatch: pytest.MonkeyPatch) -> Any:
    os.environ.setdefault('AWS_DEFAULT_REGION', 'us-east-1')
    os.environ.setdefault('AWS_EC2_METADATA_DISABLED', 'true')
    module = _import_worker(module_name)
    if isinstance(module, dict):
        return module
    handler = getattr(module, handler_name, None)
    if not callable(handler):
        return {'missing_handler': f'{module_name}.{handler_name}'}

    if construct_id == 'VprSqsWorkerLambda':
        monkeypatch.setattr(module, '_process_job_record', lambda _jobs_repo, record, _bucket: _side_effect_from_record(record))
        monkeypatch.setattr(module, 'JobsRepository', MagicMock(return_value=MagicMock()))
        monkeypatch.setattr(module, '_get_results_bucket', lambda: 'test-bucket')
    elif construct_id in {'CoverLetterWorkerLambda', 'InterviewPrepWorkerLambda'}:
        monkeypatch.setattr(module, '_generate_and_persist_from_sqs', _side_effect_from_job_id)
        monkeypatch.setattr(module, '_send_task_success', MagicMock())
        monkeypatch.setattr(module, '_send_task_failure', MagicMock())
    elif construct_id == 'CompanyResearchWorkerLambda':
        monkeypatch.setattr(module, '_process_record', _side_effect_from_record)

    try:
        worker_handler: Callable[[dict[str, Any], Any], dict[str, Any]] = handler
        return worker_handler(_sqs_batch_with_one_failure(), MagicMock())
    except Exception as exc:  # noqa: BLE001
        return {'raised': f'{type(exc).__name__}: {exc}'}


@pytest.mark.parametrize(('construct_id', 'module_name', 'handler_name'), [(key, *value) for key, value in WORKERS.items()])
def test_p17_worker_handlers_return_batch_item_failures(
    construct_id: str,
    module_name: str,
    handler_name: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AC-P17-1 behavior half: worker handlers return only failed SQS message ids."""
    actual = _call_worker(construct_id, module_name, handler_name, monkeypatch)
    assert actual == EXPECTED_FAILURE_RESPONSE, (
        f'AC-P17-1 {construct_id} must return exactly {EXPECTED_FAILURE_RESPONSE!r} for one failed record; got {actual!r}'
    )
