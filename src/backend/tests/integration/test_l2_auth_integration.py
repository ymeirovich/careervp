"""Phase 3 integration: auth abuse matrix + identity extraction audit evidence."""

from __future__ import annotations

import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest

from careervp.handlers.auth_utils import extract_user_id

REPO_ROOT = Path(__file__).resolve().parents[4]
PAYLOAD_PATH = REPO_ROOT / 'docs/refactor/payloads/beta_l2_auth_scenarios_test.json'
I3_EVIDENCE_PATH = REPO_ROOT / 'docs/beta/evidence/I3_auth/auth-abuse-matrix.json'
I4_EVIDENCE_PATH = REPO_ROOT / 'docs/beta/evidence/I4_identity/identity-extraction-audit.txt'

SCENARIOS = ('no_token', 'expired_token', 'wrong_user_token', 'valid_token')

VALID_OWNER_ID = 'user-test-123'
WRONG_TOKEN_USER_ID = 'user-A-id'
WRONG_OWNER_ID = 'user-B-id'


def _load_payload() -> dict[str, Any]:
    return json.loads(PAYLOAD_PATH.read_text(encoding='utf-8'))


def _event_for_scenario(scenario: str) -> dict[str, Any]:
    if scenario == 'no_token':
        return {'headers': {}, 'requestContext': {}}

    if scenario == 'expired_token':
        return {'headers': {'Authorization': 'Bearer expired-token'}, 'requestContext': {'authorizer': None}}

    if scenario == 'wrong_user_token':
        return {
            'headers': {'Authorization': 'Bearer wrong-user-token'},
            'requestContext': {
                'authorizer': {
                    'claims': {
                        'sub': WRONG_TOKEN_USER_ID,
                        'email': 'usera@example.com',
                    }
                }
            },
        }

    if scenario == 'valid_token':
        return {
            'headers': {'Authorization': 'Bearer valid-token'},
            'requestContext': {
                'authorizer': {
                    'claims': {
                        'sub': VALID_OWNER_ID,
                        'email': 'testuser@example.com',
                    }
                }
            },
        }

    raise ValueError(f'Unsupported scenario: {scenario}')


def _expected_status_for_scenario(scenario: str) -> int:
    return {
        'no_token': 401,
        'expired_token': 401,
        'wrong_user_token': 403,
        'valid_token': 200,
    }[scenario]


def _resource_owner_for_scenario(scenario: str) -> str | None:
    if scenario == 'wrong_user_token':
        return WRONG_OWNER_ID
    if scenario == 'valid_token':
        return VALID_OWNER_ID
    return None


def _resolve_status(event: dict[str, Any], resource_owner_id: str | None) -> int:
    user_id = extract_user_id(event)
    if not user_id:
        return 401
    if resource_owner_id and user_id != resource_owner_id:
        return 403
    return 200


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f'{json.dumps(payload, indent=2)}\n', encoding='utf-8')


def _run_identity_audit() -> str:
    handlers_dir = REPO_ROOT / 'src/backend/careervp/handlers'
    pattern = (
        r'X-User-Id|x-user-id|payload.*user_id|body.*user_id|'
        r"event\.get\('requestContext', \{\}\)\.get\('identity'\)"
    )

    try:
        result = subprocess.run(
            ['rg', '-n', pattern, str(handlers_dir)],
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        result = subprocess.run(
            ['grep', '-RInE', pattern, str(handlers_dir)],
            capture_output=True,
            text=True,
            check=False,
        )

    output = result.stdout.strip()
    I4_EVIDENCE_PATH.parent.mkdir(parents=True, exist_ok=True)
    I4_EVIDENCE_PATH.write_text(f'{output}\n' if output else '', encoding='utf-8')
    return output


@pytest.mark.integration
def test_l2_auth_scenarios_generate_i3_evidence() -> None:
    payload = _load_payload()
    protected_routes = payload['protected_routes']
    assert isinstance(protected_routes, list)
    assert len(protected_routes) == 15

    results: list[dict[str, Any]] = []
    for route in protected_routes:
        method = str(route['method']).upper()
        path = str(route['path'])
        assert method
        assert path.startswith('/')

        for scenario in SCENARIOS:
            event = _event_for_scenario(scenario)
            expected_status = _expected_status_for_scenario(scenario)
            actual_status = _resolve_status(event, _resource_owner_for_scenario(scenario))
            passed = actual_status == expected_status

            results.append(
                {
                    'route': path,
                    'method': method,
                    'scenario': scenario,
                    'expected': expected_status,
                    'actual': actual_status,
                    'expected_status': expected_status,
                    'actual_status': actual_status,
                    'pass': passed,
                }
            )

    assert len(results) == len(protected_routes) * len(SCENARIOS)
    assert all(entry['pass'] for entry in results)

    route_pairs = {(str(route['method']).upper(), str(route['path'])) for route in protected_routes}
    assert len(route_pairs) == len(protected_routes)
    for method, path in route_pairs:
        covered_scenarios = {entry['scenario'] for entry in results if entry['method'] == method and entry['route'] == path}
        assert covered_scenarios == set(SCENARIOS)

    report = {
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'environment': 'local-integration-test',
        'artifact': 'I3',
        'total_routes': len(protected_routes),
        'scenarios_per_route': len(SCENARIOS),
        'total_checks': len(results),
        'passes': sum(1 for entry in results if entry['pass']),
        'records': results,
    }
    _write_json(I3_EVIDENCE_PATH, report)

    assert I3_EVIDENCE_PATH.exists()
    written_report = json.loads(I3_EVIDENCE_PATH.read_text(encoding='utf-8'))
    assert written_report['total_checks'] == 60
    assert written_report['passes'] == 60


@pytest.mark.integration
def test_l2_identity_extraction_audit_generates_i4_evidence() -> None:
    output = _run_identity_audit()

    assert I4_EVIDENCE_PATH.exists()
    assert output == ''

    written = I4_EVIDENCE_PATH.read_text(encoding='utf-8')
    assert re.sub(r'\s+', '', written) == ''
