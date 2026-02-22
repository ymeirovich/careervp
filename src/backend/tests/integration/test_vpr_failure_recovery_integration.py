from __future__ import annotations

import json
import os

import pytest

try:
    from .integration_helpers import (
        IntegrationApiClient,
        create_authenticated_user,
        create_job_and_get_id,
        generate_gap_questions,
        maybe_assert_queue_has_messages,
        poll_until_terminal,
        submit_gap_responses,
        submit_vpr_generate,
        unwrap_payload,
        upload_cv_and_get_id,
    )
except ImportError:  # pragma: no cover
    from integration_helpers import (
        IntegrationApiClient,
        create_authenticated_user,
        create_job_and_get_id,
        generate_gap_questions,
        maybe_assert_queue_has_messages,
        poll_until_terminal,
        submit_gap_responses,
        submit_vpr_generate,
        unwrap_payload,
        upload_cv_and_get_id,
    )


def test_vpr_failure_recovery_integration() -> None:
    failure_payload_raw = os.getenv('INTEGRATION_VPR_FAILURE_PAYLOAD', '').strip()
    if not failure_payload_raw:
        pytest.skip('Set INTEGRATION_VPR_FAILURE_PAYLOAD JSON to force a deterministic worker failure scenario.')

    try:
        failure_overrides = json.loads(failure_payload_raw)
    except json.JSONDecodeError as exc:
        raise AssertionError('INTEGRATION_VPR_FAILURE_PAYLOAD must be valid JSON.') from exc
    if not isinstance(failure_overrides, dict):
        raise AssertionError('INTEGRATION_VPR_FAILURE_PAYLOAD must decode to a JSON object.')

    client = IntegrationApiClient.from_env()
    user = create_authenticated_user(client)
    token = user['login_token']

    cv_id = upload_cv_and_get_id(client, token)
    job_id = create_job_and_get_id(client, token)
    _, questions = generate_gap_questions(client, token, cv_id, job_id)
    _, gap_response_ids = submit_gap_responses(client, token, cv_id, job_id, questions)

    submit_response, request_id = submit_vpr_generate(
        client,
        token,
        cv_id,
        job_id,
        gap_response_ids,
        overrides=failure_overrides,
    )
    assert submit_response.status == 202

    terminal_response = poll_until_terminal(
        client,
        f'/vpr/{request_id}',
        token=token,
        timeout_seconds=300,
        poll_interval_seconds=5,
    )
    terminal_payload = unwrap_payload(terminal_response.data)
    assert str(terminal_payload.get('status', '')).lower() == 'failed'
    assert terminal_payload.get('error') or terminal_payload.get('error_message')

    maybe_assert_queue_has_messages('INTEGRATION_VPR_DLQ_URL', timeout_seconds=30)
