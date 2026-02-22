from __future__ import annotations

from typing import Any

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


def _extract_text(payload: dict[str, Any], *keys: str) -> str:
    normalized = unwrap_payload(payload)
    for key in keys:
        value = normalized.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return ''


def _post_generate_and_resolve(
    client: IntegrationApiClient,
    token: str,
    path: str,
    status_path_prefix: str,
    body: dict[str, Any],
) -> dict[str, Any]:
    response = client.request('POST', path, token=token, json_body=body, expected_status={200, 201, 202})
    payload = unwrap_payload(response.data)
    if response.status in {200, 201}:
        return payload

    request_id = str(require_field(payload, 'request_id', 'id'))
    terminal = poll_until_terminal(
        client,
        f'{status_path_prefix}/{request_id}',
        token=token,
        timeout_seconds=180,
        poll_interval_seconds=5,
    )
    terminal_payload = unwrap_payload(terminal.data)
    assert str(terminal_payload.get('status', '')).lower() == 'completed'
    return terminal_payload


def test_full_pipeline_integration() -> None:
    client = IntegrationApiClient.from_env()
    user = create_authenticated_user(client)
    token = user['login_token']

    cv_id = upload_cv_and_get_id(client, token)
    job_id = create_job_and_get_id(client, token)

    company_research_response = client.request(
        'POST',
        '/company-research/fetch',
        token=token,
        json_body={'domain': 'example.com'},
        expected_status=200,
    )
    company_research_payload = unwrap_payload(company_research_response.data)
    assert company_research_payload

    _, questions = generate_gap_questions(client, token, cv_id, job_id)
    assert len(questions) == 10

    gap_response_submit, gap_response_ids = submit_gap_responses(client, token, cv_id, job_id, questions)
    assert gap_response_submit.status == 200
    assert len(gap_response_ids) > 0

    _, vpr_request_id = submit_vpr_generate(client, token, cv_id, job_id, gap_response_ids)
    vpr_terminal = poll_until_terminal(
        client,
        f'/vpr/{vpr_request_id}',
        token=token,
        timeout_seconds=180,
        poll_interval_seconds=5,
    )
    vpr_payload = unwrap_payload(vpr_terminal.data)
    assert str(vpr_payload.get('status', '')).lower() == 'completed'
    assert vpr_payload.get('uvp')

    _, tailoring_request_id = submit_cv_tailoring_generate(client, token, cv_id, job_id, vpr_request_id)
    tailoring_terminal = poll_until_terminal(
        client,
        f'/cv-tailoring/{tailoring_request_id}',
        token=token,
        timeout_seconds=180,
        poll_interval_seconds=5,
    )
    tailoring_payload = unwrap_payload(tailoring_terminal.data)
    assert str(tailoring_payload.get('status', '')).lower() == 'completed'
    assert float(tailoring_payload.get('ats_score', 0)) >= 8.0

    cover_letter_payload = _post_generate_and_resolve(
        client,
        token,
        '/cover-letter/generate',
        '/cover-letter',
        {
            'cv_id': cv_id,
            'job_id': job_id,
            'vpr_id': vpr_request_id,
            'gap_response_ids': gap_response_ids,
            'company_research_id': company_research_payload.get('research_id'),
        },
    )
    cover_letter_text = _extract_text(cover_letter_payload, 'cover_letter', 'content', 'text')
    assert len([p for p in cover_letter_text.split('\n\n') if p.strip()]) >= 3

    interview_payload = _post_generate_and_resolve(
        client,
        token,
        '/interview-prep/generate',
        '/interview-prep',
        {'vpr_id': vpr_request_id, 'gap_response_ids': gap_response_ids},
    )
    interview_questions = interview_payload.get('questions')
    assert isinstance(interview_questions, list)
    assert len(interview_questions) >= 10

    if cover_letter_text and vpr_payload.get('uvp'):
        assert str(vpr_payload.get('uvp'))[:20] in cover_letter_text
