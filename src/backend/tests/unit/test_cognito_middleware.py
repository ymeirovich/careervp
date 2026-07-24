"""L2.3 unit tests for Cognito-only identity extraction and static policy checks."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from careervp.handlers.auth_utils import extract_user_id

REPO_ROOT = Path(__file__).resolve().parents[3]
HANDLERS_DIR = REPO_ROOT / 'careervp' / 'handlers'


def _event_with_claims(user_id: str = 'user-123') -> dict:
    return {
        'requestContext': {
            'authorizer': {
                'jwt': {'claims': {'sub': user_id}},
            }
        }
    }


def _event_with_rest_claims(user_id: str = 'user-123') -> dict:
    return {
        'requestContext': {
            'authorizer': {
                'claims': {'sub': user_id},
            }
        }
    }


def _event_without_authorizer() -> dict:
    return {
        'requestContext': {},
        'headers': {'X-User-Id': 'spoofed-user'},
        'body': json.dumps({'user_id': 'spoofed-user'}),
        'queryStringParameters': {'user_id': 'spoofed-user'},
    }


@pytest.mark.unit
class TestExtractUserId:
    def test_extracts_sub_from_cognito_claims(self) -> None:
        assert extract_user_id(_event_with_claims('user-abc')) == 'user-abc'

    def test_extracts_sub_from_rest_claims_shape(self) -> None:
        assert extract_user_id(_event_with_rest_claims('user-rest')) == 'user-rest'

    def test_returns_none_when_no_authorizer(self) -> None:
        assert extract_user_id({'requestContext': {}}) is None

    def test_returns_none_when_no_sub(self) -> None:
        event = {'requestContext': {'authorizer': {'jwt': {'claims': {}}}}}
        assert extract_user_id(event) is None

    def test_spoofed_x_user_id_header_is_not_honored(self) -> None:
        # P-04: the `x-user-id` / `X-User-Id` header fallback was a client-supplied identity
        # bypass and has been removed. A request with no Cognito authorizer but a spoofed header
        # must fail closed (return None -> handlers 401), never resolve the spoofed identity.
        assert extract_user_id(_event_without_authorizer()) is None

    def test_spoofed_body_user_id_is_not_honored(self) -> None:
        # P-04: body `user_id` is never trusted; identity comes only from validated claims.
        assert extract_user_id(_event_without_authorizer()) is None

    def test_spoofed_query_param_user_id_is_not_honored(self) -> None:
        # P-04: query-string `user_id` is never trusted; identity comes only from validated claims.
        assert extract_user_id(_event_without_authorizer()) is None


def _grep_files(pattern: str) -> list[str]:
    hits: list[str] = []
    for path in HANDLERS_DIR.rglob('*.py'):
        text = path.read_text(encoding='utf-8')
        for lineno, line in enumerate(text.splitlines(), start=1):
            if pattern in line:
                hits.append(f'{path.relative_to(REPO_ROOT)}:{lineno}:{line.strip()}')
    return hits


@pytest.mark.unit
class TestIdentityStaticAnalysis:
    def test_no_x_user_id_header_in_handlers(self) -> None:
        hits = _grep_files('x-user-id') + _grep_files('X-User-Id')
        assert hits == [], 'Unexpected X-User-Id usage:\n' + '\n'.join(hits)

    def test_no_payload_or_body_user_id_extraction_in_handlers(self) -> None:
        hits: list[str] = []
        for path in HANDLERS_DIR.rglob('*.py'):
            text = path.read_text(encoding='utf-8')
            for lineno, line in enumerate(text.splitlines(), start=1):
                normalized = line.replace('"', "'")
                if "payload.get('user_id')" in normalized or "body.get('user_id')" in normalized:
                    hits.append(f'{path.relative_to(REPO_ROOT)}:{lineno}:{line.strip()}')
        assert hits == [], 'Unexpected payload/body user_id extraction:\n' + '\n'.join(hits)
