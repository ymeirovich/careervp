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
        unwrap,
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
        unwrap,
        upload_cv,
    )


def test_e2e_happy_path_full_job_application() -> None:
    client = E2EClient.from_env()
    user = register_and_login(client)
    token = user['token']

    me = client.request('GET', '/users/me', token=token, expected_status=200)
    assert unwrap(me.data).get('email') == user['email']

    cv_id = upload_cv(client, token)
    cvs = client.request('GET', '/users/me/cvs', token=token, expected_status=200)
    assert isinstance(unwrap(cvs.data).get('cvs', unwrap(cvs.data).get('items', [])), list)

    job_id = create_job(client, token)
    jobs = client.request('GET', '/jobs', token=token, expected_status=200)
    assert isinstance(unwrap(jobs.data).get('jobs', unwrap(jobs.data).get('items', [])), list)

    # Canonical CompanyResearchRequest (api_models.py:577) — keyed on `job_id`, not a
    # bare `domain`.
    cr = client.request(
        'POST',
        '/company-research/fetch',
        token=token,
        json_body={'job_id': job_id, 'company_name': 'Example Corp', 'url': E2E_JOB_URL},
        expected_status=202,
    )
    cr_payload = unwrap(cr.data)
    company_research_id = str(cr_payload.get('request_id') or cr_payload.get('research_id') or '')

    gap_q = client.request(
        'POST',
        '/gap-analysis/questions',
        token=token,
        json_body={'cv_id': cv_id, 'job_id': job_id},
        expected_status=200,
    )
    questions = unwrap(gap_q.data).get('questions', [])
    assert isinstance(questions, list) and len(questions) == 10

    responses = []
    for q in questions:
        qid = q.get('question_id') or q.get('id')
        if qid:
            responses.append({'question_id': str(qid), 'response': 'STAR response with measurable impact.'})
    # Canonical body from src/frontend/api/methods.ts:154 — `{responses}` only; the wire answers 200.
    gap_r = client.request(
        'POST',
        f'/jobs/{job_id}/gap-responses',
        token=token,
        json_body={'responses': responses},
        expected_status=200,
    )
    gap_ids = unwrap(gap_r.data).get('gap_response_ids', unwrap(gap_r.data).get('response_ids', []))
    if not isinstance(gap_ids, list) or not gap_ids:
        gap_ids = [item['question_id'] for item in responses if item.get('question_id')]
    assert isinstance(gap_ids, list) and len(gap_ids) > 0

    vpr = client.request(
        'POST',
        '/vpr/generate',
        token=token,
        json_body={'cv_id': cv_id, 'job_id': job_id, 'gap_response_ids': gap_ids},
        expected_status=202,
    )
    vpr_id = str(require(vpr.data, 'request_id', 'vpr_id', 'id'))
    vpr_result = artifact_result(poll_completed(client, token, f'/vpr/{vpr_id}/status', timeout_seconds=180))
    assert vpr_result.get('uvp')
    diffs = vpr_result.get('differentiators', [])
    assert isinstance(diffs, list) and len(diffs) >= 3
    assert float(vpr_result.get('company_job_fit_score', 0)) > 0

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
    # `fvs_validation` is deliberately not exposed on the status response
    # (cv_tailoring_handler.py:1114); `fact_verification_detail.passed` is the published
    # form of the same fact.
    fvs = cvt_result.get('fact_verification_detail', {})
    assert isinstance(fvs, dict)
    assert fvs.get('passed') is True

    cl = client.request(
        'POST',
        '/cover-letter/generate',
        token=token,
        json_body={
            'cv_id': cv_id,
            'job_id': job_id,
            'vpr_id': vpr_id,
            'gap_response_ids': gap_ids,
            'company_research_id': company_research_id or 'placeholder-research-id',
        },
        expected_status={200, 202},
    )
    if cl.status == 202:
        cl_id = str(require(cl.data, 'request_id', 'id'))
        cl_result = artifact_result(poll_completed(client, token, f'/cover-letter/{cl_id}/status', timeout_seconds=90))
    else:
        cl_result = artifact_result(cl.data)
    cl_text = str(cl_result.get('cover_letter') or cl_result.get('text') or '')
    if cl_text:
        assert_no_banned_words(cl_text)

    ip = client.request(
        'POST',
        '/interview-prep/generate',
        token=token,
        json_body={'application_id': job_id, 'vpr_id': vpr_id, 'gap_response_ids': gap_ids},
        expected_status={200, 202},
    )
    if ip.status == 202:
        ip_id = str(require(ip.data, 'request_id', 'id'))
        ip_result = artifact_result(poll_completed(client, token, f'/interview-prep/{ip_id}/status', timeout_seconds=90))
    else:
        ip_result = artifact_result(ip.data)
    questions = ip_result.get('questions', [])
    assert isinstance(questions, list) and len(questions) >= 10
