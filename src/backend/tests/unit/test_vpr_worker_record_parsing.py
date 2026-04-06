"""
Unit tests for vpr_worker_handler._extract_job_id_from_record.

The vpr-worker Lambda is triggered exclusively via SQS (vpr-sqs-worker is the
authoritative trigger; the DynamoDB Stream event source was removed to eliminate
a PENDING→PROCESSING race condition).

Regression guards:
- Records without 'body' must return None, not raise KeyError.
- Records with 'body' but no 'job_id' must return None, not raise.
"""

from __future__ import annotations

import json

from careervp.handlers.vpr_worker_handler import _extract_job_id_from_record

JOB_ID = 'abc12345-0000-0000-0000-000000000001'


def test_sqs_record_returns_job_id() -> None:
    record = {
        'eventSource': 'aws:sqs',
        'body': json.dumps({'job_id': JOB_ID, 'user_id': 'u1'}),
    }
    assert _extract_job_id_from_record(record) == JOB_ID


def test_sqs_record_missing_body_returns_none() -> None:
    """Original regression: record['body'] raised KeyError on non-SQS events.
    The function must return None gracefully instead of crashing the batch."""
    record = {'eventSource': 'aws:sqs', 'messageId': 'm1'}
    assert _extract_job_id_from_record(record) is None


def test_sqs_record_body_missing_job_id_returns_none() -> None:
    record = {'eventSource': 'aws:sqs', 'body': json.dumps({'user_id': 'u1'})}
    assert _extract_job_id_from_record(record) is None


def test_record_with_no_keys_returns_none() -> None:
    """Completely empty record must not raise."""
    assert _extract_job_id_from_record({}) is None
