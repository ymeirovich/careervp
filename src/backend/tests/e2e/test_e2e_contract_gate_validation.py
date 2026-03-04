from __future__ import annotations

try:
    from .e2e_helpers import E2EClient, register_and_login
except ImportError:  # pragma: no cover
    from e2e_helpers import E2EClient, register_and_login  # type: ignore


def test_e2e_contract_gate_validation() -> None:
    client = E2EClient.from_env()
    user = register_and_login(client)
    token = user['token']

    checks = [
        ('POST', '/auth/register', None, {'email': 'x', 'password': 'y', 'name': 'z'}, {201, 400, 409}),
        ('POST', '/auth/login', None, {'email': 'x', 'password': 'y'}, {200, 401, 400}),
        ('POST', '/auth/refresh', token, None, {200, 401}),
        ('GET', '/users/me', token, None, {200, 401}),
        ('PUT', '/users/me', token, {'name': 'Gate User'}, {200, 400, 401}),
        ('POST', '/users/me/cv', token, {'text_content': 'Contract gate CV text content'}, {201, 400, 401}),
        ('GET', '/users/me/cvs', token, None, {200, 401}),
        ('POST', '/jobs', token, {'title': 't', 'company': 'c', 'description': 'd'}, {201, 400, 401}),
        ('GET', '/jobs', token, None, {200, 401}),
        ('GET', '/jobs/nonexistent-id', token, None, {200, 401, 404}),
        ('POST', '/vpr/generate', token, {'cv_id': 'x', 'job_id': 'y', 'gap_response_ids': ['z']}, {202, 400, 401, 422}),
        ('GET', '/vpr/nonexistent-id', token, None, {200, 401, 404}),
        ('GET', '/users/me/vprs', token, None, {200, 401}),
        ('POST', '/gap-analysis/questions', token, {'cv_id': 'x', 'job_id': 'y'}, {200, 400, 401}),
        ('POST', '/jobs/nonexistent-id/gap-responses', token, {'cv_id': 'x', 'job_id': 'y', 'responses': []}, {200, 201, 400, 401, 404}),
        ('GET', '/gap-analysis/nonexistent-id/questions', token, None, {200, 401, 404}),
        ('POST', '/cv-tailoring/generate', token, {'cv_id': 'x'}, {202, 400, 401, 422}),
        ('GET', '/cv-tailoring/nonexistent-id', token, None, {200, 401, 404}),
        ('GET', '/users/me/tailored-cvs', token, None, {200, 401}),
        ('POST', '/cover-letter/generate', token, {'cv_id': 'x'}, {202, 400, 401, 422}),
        ('GET', '/cover-letter/nonexistent-id', token, None, {200, 401, 404}),
        ('GET', '/users/me/cover-letters', token, None, {200, 401}),
        ('POST', '/interview-prep/generate', token, {'vpr_id': 'x'}, {202, 400, 401, 422}),
        ('GET', '/interview-prep/nonexistent-id', token, None, {200, 401, 404}),
        ('POST', '/company-research/fetch', token, {'domain': 'example.com'}, {200, 202, 400, 401}),
        ('GET', '/company-research/nonexistent-id', token, None, {200, 401, 404}),
        ('GET', '/health', None, None, {200}),
    ]

    for method, path, auth, payload, expected in checks:
        res = client.request(method, path, token=auth, json_body=payload, expected_status=expected)
        assert res.status != 500, f'{method} {path} returned 500'
        assert 'Missing Authentication Token' not in res.text, f'{method} {path} route is missing'
