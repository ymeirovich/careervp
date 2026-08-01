from __future__ import annotations

try:
    from .e2e_helpers import E2EClient, create_job, register_and_login, unwrap, upload_cv
except ImportError:  # pragma: no cover
    from e2e_helpers import E2EClient, create_job, register_and_login, unwrap, upload_cv  # type: ignore


def test_e2e_unauthorized_access_returns_401() -> None:
    client = E2EClient.from_env()
    protected = [
        ('GET', '/users/me', None),
        ('POST', '/vpr/generate', {'cv_id': 'x', 'job_id': 'y', 'gap_response_ids': ['z']}),
        ('GET', '/vpr/nonexistent-id/status', None),
        ('POST', '/cv-tailoring/generate', {'cv_id': 'x'}),
        ('POST', '/cover-letter/generate', {'cv_id': 'x'}),
        ('POST', '/interview-prep/generate', {'vpr_id': 'x'}),
        ('GET', '/company-research/nonexistent-id', None),
        ('GET', '/jobs/nonexistent-id', None),
    ]
    for method, path, body in protected:
        res = client.request(method, path, json_body=body, expected_status=401)
        # A 403 DEFAULT_4XX would also be a non-2xx, but it means the method is unrouted,
        # not that the authorizer rejected the caller. Pin the authorizer's own envelope.
        assert unwrap(res.data).get('code') == 'UNAUTHORIZED', f'{method} {path} did not return the authorizer 401 envelope: {res.text}'

    client.request('GET', '/health', expected_status=200)


def test_e2e_invalid_input_returns_400() -> None:
    client = E2EClient.from_env()
    user = register_and_login(client)
    token = user['token']

    cases = [
        ('POST', '/auth/register', {'email': 'invalid'}, None),
        ('POST', '/auth/register', {'email': 'a@b.com'}, None),
        ('POST', '/jobs', {}, token),
        ('POST', '/vpr/generate', {'cv_id': 'x'}, token),
        ('POST', '/cv-tailoring/generate', {'cv_id': 'x'}, token),
        ('POST', '/gap-analysis/questions', {}, token),
    ]
    for method, path, body, auth_token in cases:
        res = client.request(method, path, token=auth_token, json_body=body, expected_status=400)
        # Two validation envelopes are published across handlers: `{error, ...}` (auth,
        # jobs, gap analysis, VPR, cover letter, interview prep) and
        # `{success: false, code, message, errors[]}` (CV tailoring). Both are explicit
        # machine-readable refusals; a 400 carrying neither fails this test.
        payload = res.data
        assert payload.get('error') or (payload.get('code') and payload.get('message')), (
            f'{method} {path} returned 400 with no machine-readable error identity: {res.text}'
        )


def test_e2e_not_found_returns_404() -> None:
    client = E2EClient.from_env()
    user = register_and_login(client)
    token = user['token']
    # Artifact reads live on `/{id}/status`; the bare `/{id}` has no GET method and would
    # answer 403 DEFAULT_4XX, which is an unrouted response, not a not-found response.
    for path in [
        '/vpr/nonexistent-id/status',
        '/cv-tailoring/nonexistent-id/status',
        '/cover-letter/nonexistent-id/status',
        '/interview-prep/nonexistent-id/status',
        '/jobs/nonexistent-id',
    ]:
        res = client.request('GET', path, token=token, expected_status=404)
        # Same two published envelopes as the 400 cases: `{error, ...}` and
        # `{success: false, code, message}` (CV tailoring). A 404 carrying neither fails.
        payload = unwrap(res.data)
        assert payload.get('error') or (payload.get('code') and payload.get('message')), (
            f'GET {path} returned 404 with no machine-readable error identity: {res.text}'
        )

    # Company research does not 404 for an absent record: its published contract is a 200
    # carrying the explicit absent envelope, which is what the frontend consumes
    # (src/frontend/api/methods.ts:105-110 treats anything but `completed` as null).
    absent = client.request('GET', '/company-research/nonexistent-id', token=token, expected_status=200)
    absent_payload = unwrap(absent.data)
    assert absent_payload.get('status') == 'not_generated'
    assert absent_payload.get('company_research') is None


def test_e2e_prerequisites_not_met_returns_409_upstream_required() -> None:
    client = E2EClient.from_env()
    user = register_and_login(client)
    token = user['token']
    cv_id = upload_cv(client, token)
    job_id = create_job(client, token)

    # No company research has been requested for this application, so the VPR dependency
    # gate refuses. The deployed contract for an unmet prerequisite is 409
    # `upstream_required` with the unmet artifacts named — not a bare 422.
    vpr = client.request(
        'POST',
        '/vpr/generate',
        token=token,
        json_body={'cv_id': cv_id, 'job_id': job_id, 'gap_response_ids': ['non-existent']},
        expected_status=409,
    )
    vpr_payload = unwrap(vpr.data)
    assert vpr_payload.get('status') == 'upstream_required'
    assert vpr_payload.get('missing') == ['company_research']

    cl_payload = {
        'cv_id': cv_id,
        'job_id': job_id,
        'vpr_id': 'non-existent-vpr',
        'gap_response_ids': ['non-existent-gap'],
        'company_research_id': 'non-existent-research',
    }
    cover_letter = client.request('POST', '/cover-letter/generate', token=token, json_body=cl_payload, expected_status=409)
    cl_body = unwrap(cover_letter.data)
    assert cl_body.get('status') == 'upstream_required'
    missing = cl_body.get('missing')
    assert isinstance(missing, list) and missing, f'409 carried no unmet-artifact list: {cover_letter.text}'
