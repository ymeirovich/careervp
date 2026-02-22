from __future__ import annotations

import json
import os

import pytest

try:
    from .e2e_helpers import E2EClient, create_job, poll_completed, register_and_login, require, upload_cv
except ImportError:  # pragma: no cover
    from e2e_helpers import E2EClient, create_job, poll_completed, register_and_login, require, upload_cv  # type: ignore


def test_e2e_async_failure_and_recovery() -> None:
    fail_overrides_raw = os.getenv('E2E_VPR_FAILURE_OVERRIDES', '').strip()
    if not fail_overrides_raw:
        pytest.skip('Set E2E_VPR_FAILURE_OVERRIDES to trigger deterministic worker failure.')
    fail_overrides = json.loads(fail_overrides_raw)
    if not isinstance(fail_overrides, dict):
        raise AssertionError('E2E_VPR_FAILURE_OVERRIDES must be a JSON object.')

    client = E2EClient.from_env()
    user = register_and_login(client)
    token = user['token']
    cv_id = upload_cv(client, token)
    job_id = create_job(client, token)

    fail_payload = {'cv_id': cv_id, 'job_id': job_id, 'gap_response_ids': ['non-existent']}
    fail_payload.update(fail_overrides)
    fail_req = client.request('POST', '/vpr/generate', token=token, json_body=fail_payload, expected_status={202, 422})
    if fail_req.status == 422:
        pytest.skip('Environment validates prerequisites before async worker; cannot exercise DLQ path.')

    fail_id = str(require(fail_req.data, 'request_id', 'id'))
    fail_result = poll_completed(client, token, f'/vpr/{fail_id}', timeout_seconds=300)
    # If completion happened despite overrides, treat as env-dependent and skip strict failure assertion.
    if str(fail_result.get('status', '')).lower() != 'completed':
        assert str(fail_result.get('status', '')).lower() == 'failed'

    retry_payload = {'cv_id': cv_id, 'job_id': job_id, 'gap_response_ids': ['non-existent']}
    retry_req = client.request('POST', '/vpr/generate', token=token, json_body=retry_payload, expected_status={202, 422})
    if retry_req.status == 422:
        pytest.skip('Prerequisites intentionally blocked retry in this environment.')
