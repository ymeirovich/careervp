from __future__ import annotations

try:
    from .integration_helpers import (
        IntegrationApiClient,
        create_authenticated_user,
        create_job_and_get_id,
        fetch_json_from_url,
        generate_gap_questions,
        maybe_assert_queue_has_messages,
        poll_until_terminal,
        require_field,
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
        fetch_json_from_url,
        generate_gap_questions,
        maybe_assert_queue_has_messages,
        poll_until_terminal,
        require_field,
        submit_gap_responses,
        submit_vpr_generate,
        unwrap_payload,
        upload_cv_and_get_id,
    )


def test_vpr_async_flow_integration() -> None:
    client = IntegrationApiClient.from_env()
    user = create_authenticated_user(client)
    token = user['login_token']

    cv_id = upload_cv_and_get_id(client, token)
    job_id = create_job_and_get_id(client, token)
    _, questions = generate_gap_questions(client, token, cv_id, job_id)
    _, gap_response_ids = submit_gap_responses(client, token, cv_id, job_id, questions)

    submit_response, request_id = submit_vpr_generate(client, token, cv_id, job_id, gap_response_ids)
    submit_payload = unwrap_payload(submit_response.data)
    assert submit_response.status == 202
    assert str(submit_payload.get('status', '')).lower() == 'processing'

    immediate_status = client.request('GET', f'/vpr/{request_id}', token=token, expected_status=200)
    immediate_payload = unwrap_payload(immediate_status.data)
    assert str(immediate_payload.get('status', '')).lower() in {'pending', 'processing'}

    maybe_assert_queue_has_messages('INTEGRATION_VPR_QUEUE_URL', timeout_seconds=10)

    terminal_response = poll_until_terminal(
        client,
        f'/vpr/{request_id}',
        token=token,
        timeout_seconds=180,
        poll_interval_seconds=5,
    )
    terminal_payload = unwrap_payload(terminal_response.data)
    assert str(terminal_payload.get('status', '')).lower() == 'completed'

    result_url = str(require_field(terminal_payload, 'result_url'))
    assert result_url.startswith('http')
    result_payload = fetch_json_from_url(result_url)
    assert 'uvp' in result_payload
    assert 'differentiators' in result_payload

    token_usage = terminal_payload.get('token_usage')
    assert isinstance(token_usage, dict)
    assert int(token_usage.get('input_tokens', 0)) > 0
    assert int(token_usage.get('output_tokens', 0)) > 0
