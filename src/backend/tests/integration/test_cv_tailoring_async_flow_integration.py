from __future__ import annotations

try:
    from .integration_helpers import (
        IntegrationApiClient,
        create_authenticated_user,
        create_job_and_get_id,
        generate_gap_questions,
        poll_until_terminal,
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
        submit_cv_tailoring_generate,
        submit_gap_responses,
        submit_vpr_generate,
        unwrap_payload,
        upload_cv_and_get_id,
    )


def test_cv_tailoring_async_flow_integration() -> None:
    client = IntegrationApiClient.from_env()
    user = create_authenticated_user(client)
    token = user['login_token']

    cv_id = upload_cv_and_get_id(client, token)
    job_id = create_job_and_get_id(client, token)
    _, questions = generate_gap_questions(client, token, cv_id, job_id)
    _, gap_response_ids = submit_gap_responses(client, token, cv_id, job_id, questions)

    _, vpr_request_id = submit_vpr_generate(client, token, cv_id, job_id, gap_response_ids)
    vpr_terminal_response = poll_until_terminal(
        client,
        f'/vpr/{vpr_request_id}',
        token=token,
        timeout_seconds=180,
        poll_interval_seconds=5,
    )
    vpr_payload = unwrap_payload(vpr_terminal_response.data)
    assert str(vpr_payload.get('status', '')).lower() == 'completed'

    submit_response, tailoring_request_id = submit_cv_tailoring_generate(
        client,
        token,
        cv_id,
        job_id,
        vpr_request_id,
    )
    assert submit_response.status == 202

    terminal_response = poll_until_terminal(
        client,
        f'/cv-tailoring/{tailoring_request_id}',
        token=token,
        timeout_seconds=120,
        poll_interval_seconds=5,
    )
    payload = unwrap_payload(terminal_response.data)
    assert str(payload.get('status', '')).lower() == 'completed'
    assert float(payload.get('ats_score', 0)) >= 8.0

    keyword_matches = payload.get('keyword_matches')
    assert keyword_matches is not None

    fvs_validation = payload.get('fvs_validation')
    assert isinstance(fvs_validation, dict)
    assert fvs_validation.get('is_valid') is True
