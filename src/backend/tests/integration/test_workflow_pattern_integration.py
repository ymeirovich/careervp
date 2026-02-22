from __future__ import annotations

try:
    from .integration_helpers import (
        IntegrationApiClient,
        create_authenticated_user,
        create_job_and_get_id,
        generate_gap_questions,
        poll_until_terminal,
        require_field,
        submit_cv_tailoring_generate,
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
        poll_until_terminal,
        require_field,
        submit_cv_tailoring_generate,
        submit_gap_responses,
        submit_vpr_generate,
        unwrap_payload,
        upload_cv_and_get_id,
    )


def test_workflow_pattern_integration() -> None:
    client = IntegrationApiClient.from_env()
    user = create_authenticated_user(client)
    token = user['login_token']

    cv_id = upload_cv_and_get_id(client, token)
    job_id = create_job_and_get_id(client, token)

    gap_questions_response, questions = generate_gap_questions(client, token, cv_id, job_id)
    assert gap_questions_response.status == 200
    assert len(questions) == 10

    gap_responses_response, gap_response_ids = submit_gap_responses(client, token, cv_id, job_id, questions)
    assert gap_responses_response.status == 200
    assert len(gap_response_ids) > 0

    vpr_submit_response, vpr_request_id = submit_vpr_generate(
        client,
        token,
        cv_id,
        job_id,
        gap_response_ids,
    )
    assert vpr_submit_response.status == 202
    assert vpr_request_id

    vpr_terminal_response = poll_until_terminal(
        client,
        f'/vpr/{vpr_request_id}',
        token=token,
        timeout_seconds=120,
        poll_interval_seconds=5,
    )
    vpr_payload = unwrap_payload(vpr_terminal_response.data)
    assert str(vpr_payload.get('status', '')).lower() == 'completed'
    assert require_field(vpr_payload, 'uvp')
    differentiators = vpr_payload.get('differentiators')
    assert isinstance(differentiators, list) and len(differentiators) > 0

    tailoring_submit_response, tailoring_request_id = submit_cv_tailoring_generate(
        client,
        token,
        cv_id,
        job_id,
        vpr_request_id,
    )
    assert tailoring_submit_response.status == 202
    assert tailoring_request_id

    tailoring_terminal_response = poll_until_terminal(
        client,
        f'/cv-tailoring/{tailoring_request_id}',
        token=token,
        timeout_seconds=120,
        poll_interval_seconds=5,
    )
    tailoring_payload = unwrap_payload(tailoring_terminal_response.data)
    assert str(tailoring_payload.get('status', '')).lower() == 'completed'
    assert float(tailoring_payload.get('ats_score', 0)) >= 8.0
