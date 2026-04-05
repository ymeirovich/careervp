"""
Unit tests for vpr_worker_handler._extract_job_id_from_record.

Regression guard for the DynamoDB Stream KeyError bug: before the fix the handler
did record['body'] unconditionally, which crashed on DynamoDB Stream events because
those records have no 'body' key.  These tests must pass for all three trigger
shapes the worker can receive.
"""

from __future__ import annotations

from careervp.handlers.vpr_worker_handler import _extract_job_id_from_record

JOB_ID = 'abc12345-0000-0000-0000-000000000001'


# ── SQS records ───────────────────────────────────────────────────────────────


def test_sqs_record_returns_job_id() -> None:
    import json

    record = {
        'eventSource': 'aws:sqs',
        'body': json.dumps({'job_id': JOB_ID, 'user_id': 'u1'}),
    }
    assert _extract_job_id_from_record(record) == JOB_ID


def test_sqs_record_missing_body_returns_none() -> None:
    """KeyError guard: records without 'body' must return None, not raise."""
    record = {'eventSource': 'aws:sqs', 'messageId': 'm1'}
    assert _extract_job_id_from_record(record) is None


def test_sqs_record_body_missing_job_id_returns_none() -> None:
    import json

    record = {'eventSource': 'aws:sqs', 'body': json.dumps({'user_id': 'u1'})}
    assert _extract_job_id_from_record(record) is None


# ── DynamoDB Stream records ───────────────────────────────────────────────────


def _dynamo_insert_record(job_id: str, status: str = 'PENDING') -> dict:
    return {
        'eventSource': 'aws:dynamodb',
        'eventName': 'INSERT',
        'dynamodb': {
            'Keys': {'job_id': {'S': job_id}},
            'NewImage': {
                'job_id': {'S': job_id},
                'status': {'S': status},
                'user_id': {'S': 'user-1'},
            },
            'StreamViewType': 'NEW_AND_OLD_IMAGES',
        },
    }


def test_dynamo_insert_returns_job_id() -> None:
    record = _dynamo_insert_record(JOB_ID)
    assert _extract_job_id_from_record(record) == JOB_ID


def test_dynamo_modify_returns_none() -> None:
    """MODIFY events must be ignored to prevent infinite loops on status updates."""
    record = _dynamo_insert_record(JOB_ID)
    record['eventName'] = 'MODIFY'
    assert _extract_job_id_from_record(record) is None


def test_dynamo_remove_returns_none() -> None:
    record = _dynamo_insert_record(JOB_ID)
    record['eventName'] = 'REMOVE'
    assert _extract_job_id_from_record(record) is None


def test_dynamo_record_without_event_source_key_still_parsed() -> None:
    """Records may arrive without 'eventSource' but with 'dynamodb' — still parse."""
    record = {
        'eventName': 'INSERT',
        'dynamodb': {
            'Keys': {'job_id': {'S': JOB_ID}},
            'NewImage': {'job_id': {'S': JOB_ID}, 'status': {'S': 'PENDING'}},
        },
    }
    assert _extract_job_id_from_record(record) == JOB_ID


def test_dynamo_insert_empty_new_image_returns_none() -> None:
    record = {
        'eventSource': 'aws:dynamodb',
        'eventName': 'INSERT',
        'dynamodb': {'NewImage': {}},
    }
    assert _extract_job_id_from_record(record) is None
