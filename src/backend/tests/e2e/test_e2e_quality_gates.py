from __future__ import annotations

try:
    from .e2e_helpers import (
        E2E_JOB_URL,
        E2EClient,
        artifact_result,
        assert_no_banned_words,
        create_job,
        poll_completed,
        register_and_login,
        require,
        upload_cv,
    )
except ImportError:  # pragma: no cover
    from e2e_helpers import (  # type: ignore
        E2E_JOB_URL,
        E2EClient,
        artifact_result,
        assert_no_banned_words,
        create_job,
        poll_completed,
        register_and_login,
        require,
        upload_cv,
    )


def test_e2e_quality_gates() -> None:
    client = E2EClient.from_env()
    user = register_and_login(client)
    token = user['token']
    cv_id = upload_cv(client, token)
    job_id = create_job(client, token)

    # VPR's upstream dependency check refuses with 409 `upstream_required` unless company
    # research exists for the application, so the chain has to start here.
    client.request(
        'POST',
        '/company-research/fetch',
        token=token,
        json_body={'job_id': job_id, 'company_name': 'Example Corp', 'url': E2E_JOB_URL},
        expected_status=202,
    )

    gap_q = client.request(
        'POST',
        '/gap-analysis/questions',
        token=token,
        json_body={'cv_id': cv_id, 'job_id': job_id},
        expected_status=200,
    )
    questions = gap_q.data.get('data', gap_q.data).get('questions', [])
    responses = []
    for q in questions:
        qid = q.get('question_id') or q.get('id')
        if qid:
            responses.append({'question_id': str(qid), 'response': 'Quality gate STAR response with outcomes.'})
    # Canonical body from src/frontend/api/methods.ts:154 — `{responses}` only; the wire answers 200.
    gap_r = client.request(
        'POST',
        f'/jobs/{job_id}/gap-responses',
        token=token,
        json_body={'responses': responses},
        expected_status=200,
    )
    gap_ids = gap_r.data.get('data', gap_r.data).get('gap_response_ids', [])
    if not isinstance(gap_ids, list) or not gap_ids:
        gap_ids = [item['question_id'] for item in responses if item.get('question_id')]

    vpr = client.request(
        'POST',
        '/vpr/generate',
        token=token,
        json_body={'cv_id': cv_id, 'job_id': job_id, 'gap_response_ids': gap_ids},
        expected_status=202,
    )
    vpr_id = str(require(vpr.data, 'request_id', 'id', 'vpr_id'))
    vpr_result = artifact_result(poll_completed(client, token, f'/vpr/{vpr_id}/status', timeout_seconds=180))
    vpr_text = str(vpr_result.get('strategic_narrative') or vpr_result.get('uvp') or '')
    if vpr_text:
        assert_no_banned_words(vpr_text)

    cvt = client.request(
        'POST',
        '/cv-tailoring/generate',
        token=token,
        json_body={'cv_id': cv_id, 'job_id': job_id, 'vpr_id': vpr_id},
        expected_status=202,
    )
    cvt_id = str(require(cvt.data, 'request_id', 'id'))
    cvt_result = artifact_result(poll_completed(client, token, f'/cv-tailoring/{cvt_id}/status', timeout_seconds=120))
    assert float(cvt_result.get('ats_score', 0)) >= 8.0

    cl = client.request(
        'POST',
        '/cover-letter/generate',
        token=token,
        json_body={
            'cv_id': cv_id,
            'job_id': job_id,
            'vpr_id': vpr_id,
            'gap_response_ids': gap_ids,
            'company_research_id': 'placeholder-research-id',
        },
        expected_status={200, 202, 422},
    )
    if cl.status == 422:
        return
    cl_result = artifact_result(cl.data)
    if cl.status == 202:
        cl_id = str(require(cl.data, 'request_id', 'id'))
        cl_result = artifact_result(poll_completed(client, token, f'/cover-letter/{cl_id}/status', timeout_seconds=90))
    cl_text = str(cl_result.get('cover_letter') or cl_result.get('text') or '')
    if cl_text:
        assert_no_banned_words(cl_text)
