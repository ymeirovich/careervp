from __future__ import annotations

try:
    from .e2e_helpers import E2EClient, create_job, register_and_login, upload_cv
except ImportError:  # pragma: no cover
    from e2e_helpers import E2EClient, create_job, register_and_login, upload_cv  # type: ignore


def test_e2e_unauthorized_access_returns_401() -> None:
    client = E2EClient.from_env()
    protected = [
        ('GET', '/users/me', None),
        ('POST', '/vpr/generate', {'cv_id': 'x', 'job_id': 'y', 'gap_response_ids': ['z']}),
        ('GET', '/vpr/nonexistent-id', None),
        ('POST', '/cv-tailoring/generate', {'cv_id': 'x'}),
        ('POST', '/cover-letter/generate', {'cv_id': 'x'}),
        ('POST', '/interview-prep/generate', {'vpr_id': 'x'}),
        ('GET', '/company-research/nonexistent-id', None),
        ('GET', '/jobs/nonexistent-id', None),
    ]
    for method, path, body in protected:
        client.request(method, path, json_body=body, expected_status=401)

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
        assert 'error' in res.data


def test_e2e_not_found_returns_404() -> None:
    client = E2EClient.from_env()
    user = register_and_login(client)
    token = user['token']
    for path in [
        '/vpr/nonexistent-id',
        '/cv-tailoring/nonexistent-id',
        '/cover-letter/nonexistent-id',
        '/interview-prep/nonexistent-id',
        '/jobs/nonexistent-id',
        '/company-research/nonexistent-id',
    ]:
        client.request('GET', path, token=token, expected_status=404)


def test_e2e_prerequisites_not_met_returns_422() -> None:
    client = E2EClient.from_env()
    user = register_and_login(client)
    token = user['token']
    cv_id = upload_cv(client, token)
    job_id = create_job(client, token)

    client.request(
        'POST',
        '/vpr/generate',
        token=token,
        json_body={'cv_id': cv_id, 'job_id': job_id, 'gap_response_ids': ['non-existent']},
        expected_status=422,
    )

    cl_payload = {
        'cv_id': cv_id,
        'job_id': job_id,
        'vpr_id': 'non-existent-vpr',
        'gap_response_ids': ['non-existent-gap'],
        'company_research_id': 'non-existent-research',
    }
    client.request('POST', '/cover-letter/generate', token=token, json_body=cl_payload, expected_status=422)
