"""TEST-CANCEL-001 § worker-skip-cancelled: an already-CANCELLED artifact must
not be resurrected by a late/redelivered SQS message.

The realistic vector: a user clicks Generate then Cancel within seconds; the SQS
message is still in flight; when the worker dequeues it the artifact is already
CANCELLED. The worker must skip (or have its claim rejected) and never flip the
artifact back to PROCESSING/COMPLETED (FE-UI-043).

Coverage by worker:
  - VPR / CR        : precheck skips a CANCELLED job/artifact before any work.
  - Cover letter / IP: conditional PROCESSING claim is rejected (CCF) and surfaced
                       as CancelledBeforePersist; the SQS loop skips cleanly
                       (no task_success, no DLQ).
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest
from botocore.exceptions import ClientError

from careervp.logic.cancellation import CancelledBeforePersist

_CCF = ClientError(
    {'Error': {'Code': 'ConditionalCheckFailedException', 'Message': 'Condition failed'}},
    'UpdateItem',
)


# ---------------------------------------------------------------------------
# VPR worker — precheck skip
# ---------------------------------------------------------------------------


def test_vpr_worker_skips_cancelled_job(monkeypatch: pytest.MonkeyPatch) -> None:
    from careervp.handlers import vpr_worker_handler

    repo = MagicMock()
    repo.get_job.return_value = {'job_id': 'job-1', 'user_id': 'u1', 'status': 'CANCELLED'}
    execute = MagicMock()
    monkeypatch.setattr(vpr_worker_handler, '_execute_job', execute)

    record = {'body': json.dumps({'job_id': 'job-1', 'user_id': 'u1'})}
    vpr_worker_handler._process_job_record(repo, record, 'bucket-1')

    # No claim write and no generation: the cancelled job is left untouched.
    execute.assert_not_called()
    repo.update_job_status.assert_not_called()


# ---------------------------------------------------------------------------
# Company Research worker — precheck skip
# ---------------------------------------------------------------------------


def test_cr_worker_skips_cancelled_artifact(monkeypatch: pytest.MonkeyPatch) -> None:
    from careervp.handlers import company_research_worker_handler as cr

    app_repo = MagicMock()
    app_repo.get.return_value = {'artifact_statuses': {'company_research': 'cancelled'}}
    monkeypatch.setattr(cr, '_get_app_repo', lambda: app_repo)

    async_proc = MagicMock()
    monkeypatch.setattr(cr, '_async_process_record', async_proc)

    record = {'body': json.dumps({'user_id': 'u1', 'job_id': 'job-1', 'company_name': 'Acme'})}
    cr._process_record(record)

    # Research is never (re)run for a cancelled artifact.
    async_proc.assert_not_called()


# ---------------------------------------------------------------------------
# Cover letter — conditional claim + clean SQS skip
# ---------------------------------------------------------------------------


def test_cover_letter_processing_claim_rejected_when_cancelled(monkeypatch: pytest.MonkeyPatch) -> None:
    from careervp.handlers import cover_letter_handler as cl

    table = MagicMock()
    table.update_item.side_effect = _CCF
    monkeypatch.setattr('boto3.resource', lambda *a, **k: MagicMock(Table=lambda _n: table))

    with pytest.raises(CancelledBeforePersist):
        cl._update_artifact_status(user_id='u1', job_id='job-1', status='PROCESSING', fail_if_cancelled=True)

    # The write must have been conditional (otherwise the guard is dead code).
    assert 'ConditionExpression' in table.update_item.call_args.kwargs


def test_cover_letter_sqs_skips_on_cancel(monkeypatch: pytest.MonkeyPatch) -> None:
    from careervp.handlers import cover_letter_handler as cl

    monkeypatch.setattr(cl, '_generate_and_persist_from_sqs', MagicMock(side_effect=CancelledBeforePersist('job-1')))
    success = MagicMock()
    failure = MagicMock()
    monkeypatch.setattr(cl, '_send_task_success', success)
    monkeypatch.setattr(cl, '_send_task_failure', failure)

    event = {'Records': [{'body': json.dumps({'job_id': 'job-1', 'user_id': 'u1', 'task_token': 'tok'})}]}
    result = cl._process_sqs_event(event)

    success.assert_not_called()  # cancelled job must NOT report success
    failure.assert_called_once()  # but must signal the chain branch
    assert result['statusCode'] == 200  # no DLQ / no re-raise


# ---------------------------------------------------------------------------
# Interview prep — conditional claim + clean SQS skip
# ---------------------------------------------------------------------------


def test_interview_prep_processing_claim_rejected_when_cancelled(monkeypatch: pytest.MonkeyPatch) -> None:
    from careervp.handlers import interview_prep_handler as ip

    table = MagicMock()
    table.update_item.side_effect = _CCF
    monkeypatch.setattr('boto3.resource', lambda *a, **k: MagicMock(Table=lambda _n: table))

    with pytest.raises(CancelledBeforePersist):
        ip._update_artifact_status(user_id='u1', job_id='job-1', status='PROCESSING', fail_if_cancelled=True)

    assert 'ConditionExpression' in table.update_item.call_args.kwargs


def test_interview_prep_sqs_skips_on_cancel(monkeypatch: pytest.MonkeyPatch) -> None:
    from careervp.handlers import interview_prep_handler as ip

    monkeypatch.setattr(ip, '_generate_and_persist_from_sqs', MagicMock(side_effect=CancelledBeforePersist('job-1')))
    success = MagicMock()
    failure = MagicMock()
    monkeypatch.setattr(ip, '_send_task_success', success)
    monkeypatch.setattr(ip, '_send_task_failure', failure)

    event = {'Records': [{'body': json.dumps({'job_id': 'job-1', 'user_id': 'u1', 'task_token': 'tok'})}]}
    result = ip._process_sqs_event(event)

    success.assert_not_called()
    failure.assert_called_once()
    assert result['statusCode'] == 200


# ---------------------------------------------------------------------------
# Negative control: a non-cancelled claim must NOT raise / must NOT be conditional-rejected
# ---------------------------------------------------------------------------


def test_cover_letter_claim_succeeds_when_not_cancelled(monkeypatch: pytest.MonkeyPatch) -> None:
    from careervp.handlers import cover_letter_handler as cl

    table = MagicMock()
    table.update_item.return_value = {}
    monkeypatch.setattr('boto3.resource', lambda *a, **k: MagicMock(Table=lambda _n: table))

    # Should not raise on the happy path.
    cl._update_artifact_status(user_id='u1', job_id='job-1', status='PROCESSING', fail_if_cancelled=True)
    assert table.update_item.called
