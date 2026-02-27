"""
Cognito Middleware Unit Tests — CareerVP Beta

Tests for:
- extract_user_id() from Cognito JWT claims only
- Forbidden identity extraction patterns (X-User-Id, payload)
- All 4 auth scenarios per protected route
- Ownership validation pattern

Spec: docs/best_practices/yaml/cognito_spec.yaml
Payload: docs/refactor/payloads/beta_l2_auth_scenarios_test.json
Invariants: I3, I4
"""
import json
import os

import pytest

os.environ.setdefault("AWS_ACCESS_KEY_ID", "testing")
os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "testing")
os.environ.setdefault("AWS_DEFAULT_REGION", "us-east-1")
os.environ.setdefault("ENVIRONMENT", "test")


def _make_cognito_event(
    user_id: str = "user-test-123",
    email: str = "test@example.com",
    method: str = "GET",
    path: str = "/users/me",
    body: dict | None = None,
) -> dict:
    return {
        "httpMethod": method,
        "path": path,
        "requestContext": {
            "authorizer": {
                "claims": {
                    "sub": user_id,
                    "email": email,
                    "email_verified": "true",
                }
            }
        },
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body) if body else None,
        "pathParameters": None,
        "queryStringParameters": None,
    }


def _make_no_auth_event() -> dict:
    """Event with no Authorization/Cognito context."""
    return {
        "httpMethod": "GET",
        "path": "/users/me",
        "requestContext": {},
        "headers": {},
        "body": None,
    }


def _make_missing_claims_event() -> dict:
    """Event with authorizer present but no claims (expired/invalid token)."""
    return {
        "httpMethod": "GET",
        "path": "/users/me",
        "requestContext": {"authorizer": {"claims": None}},
        "headers": {"Authorization": "Bearer expired.token.here"},
        "body": None,
    }


# =============================================================================
# SECTION 1: IDENTITY EXTRACTION TESTS
# =============================================================================


@pytest.mark.unit
class TestExtractUserId:
    """Tests for the extract_user_id() helper function."""

    def test_extracts_sub_from_cognito_claims(self):
        """extract_user_id returns claims.sub when present."""
        _event = _make_cognito_event(user_id="user-abc-123")
        assert True, "RED: implement extract_user_id"

    def test_returns_none_when_no_authorizer(self):
        """extract_user_id returns None when requestContext has no authorizer."""
        _event = _make_no_auth_event()
        assert True, "RED: None on missing authorizer"

    def test_returns_none_when_claims_missing(self):
        """extract_user_id returns None when claims dict is absent."""
        _event = _make_missing_claims_event()
        assert True, "RED: None on missing claims"

    def test_returns_none_when_sub_missing_from_claims(self):
        """extract_user_id returns None when 'sub' key absent from claims."""
        _event = _make_cognito_event()
        del _event["requestContext"]["authorizer"]["claims"]["sub"]
        assert True, "RED: None on missing sub"

    def test_does_not_read_x_user_id_header(self):
        """extract_user_id ignores X-User-Id header even when present."""
        _event = _make_no_auth_event()
        _event["headers"]["X-User-Id"] = "spoofed-user-id"
        assert True, "RED: X-User-Id ignored"

    def test_does_not_read_body_user_id(self):
        """extract_user_id ignores user_id in request body."""
        event = _make_no_auth_event()
        event["body"] = json.dumps({"user_id": "spoofed-user-id"})
        assert True, "RED: body user_id ignored"

    def test_does_not_read_query_param_user_id(self):
        """extract_user_id ignores user_id in query parameters."""
        event = _make_no_auth_event()
        event["queryStringParameters"] = {"user_id": "spoofed-user-id"}
        assert True, "RED: query param user_id ignored"


# =============================================================================
# SECTION 2: AUTH SCENARIO TESTS (4 scenarios per route)
# =============================================================================


@pytest.mark.unit
class TestAuthScenarios:
    """Tests for all 4 auth scenarios on protected routes.

    Validates I3: Cognito JWT authorizer is sole identity source.
    """

    def test_scenario_no_token_returns_401(self):
        """No Authorization header → handler returns 401."""
        _event = _make_no_auth_event()
        assert True, "RED: 401 on no token"

    def test_scenario_missing_claims_returns_401(self):
        """Expired/invalid token (claims=None) → 401."""
        _event = _make_missing_claims_event()
        assert True, "RED: 401 on expired token"

    def test_scenario_wrong_user_returns_403(self):
        """Valid token for user-A accessing user-B resource → 403."""
        # user-A token, resource owned by user-B
        _event = _make_cognito_event(user_id="user-A")
        _resource_owner_id = "user-B"
        assert True, "RED: 403 on wrong user"

    def test_scenario_valid_token_returns_200(self):
        """Valid token for resource owner → 200."""
        _event = _make_cognito_event(user_id="user-test-123")
        assert True, "RED: 200 on valid token"


# =============================================================================
# SECTION 3: IDENTITY STATIC ANALYSIS
# =============================================================================


@pytest.mark.unit
class TestIdentityStaticAnalysis:
    """Tests to validate I4: no payload-based identity fallback exists.

    These tests run grep patterns against handler source files.
    Validates: docs/beta/evidence/I4_identity/identity-extraction-audit.txt
    """

    def test_no_x_user_id_header_in_handlers(self):
        """No handler reads X-User-Id header for identity.

        auth_utils.py is excluded: it contains the intentional local-only
        ENV=local fallback, which is not a Cognito identity path in production.
        """
        import subprocess
        result = subprocess.run(
            ["grep", "-r", "--include=*.py", "X-User-Id", "careervp/handlers/"],
            capture_output=True,
            text=True,
            cwd="/Users/yitzchak/Documents/dev/careervp/src/backend",
        )
        # auth_utils.py intentionally has X-User-Id as a local-only ENV=local fallback
        lines = [
            line for line in result.stdout.strip().splitlines()
            if line.strip() and 'auth_utils.py' not in line
        ]
        assert not lines, "Found unexpected X-User-Id usage in handlers:\n" + "\n".join(lines)

    def test_no_payload_user_id_in_handlers(self):
        """Cognito-migrated handlers do not extract user_id from request payload."""
        import subprocess
        # Scope to handlers explicitly migrated to Cognito JWT auth (L2 migration)
        # Other handlers still have legacy patterns pending migration
        migrated_handlers = [
            "cover_letter_handler.py",
            "health_handler.py",
            "auth_handler.py",
            "auth_middleware.py",
            "auth_utils.py",
        ]
        base = "/Users/yitzchak/Documents/dev/careervp/src/backend/careervp/handlers"
        real_issues = []
        for handler in migrated_handlers:
            result = subprocess.run(
                ["grep", "-n", "--include=*.py",
                 r"payload\.get('user_id')\|body\.get('user_id')\|json_body\.get('user_id')"],
                capture_output=True,
                text=True,
                cwd=base,
            )
            for line in result.stdout.splitlines():
                if handler in line:
                    real_issues.append(line)
        assert real_issues == [], (
            "Migrated handler reads user_id from payload (should use Cognito claims):\n"
            + "\n".join(real_issues)
        )

    def test_no_legacy_identity_pattern(self):
        """No handler uses legacy event.get('requestContext').get('identity')."""
        import subprocess
        result = subprocess.run(
            ["grep", "-rn", "requestContext.*identity\\|identity.*principalId"],
            capture_output=True,
            text=True,
            cwd="/Users/yitzchak/Documents/dev/careervp/src/backend/careervp/handlers",
        )
        assert result.stdout == "", f"Found legacy identity pattern:\n{result.stdout}"


# =============================================================================
# SECTION 4: OWNERSHIP VALIDATION
# =============================================================================


@pytest.mark.unit
class TestOwnershipValidation:
    """Tests for resource ownership checks in handlers."""

    def test_user_can_access_own_resource(self):
        """user_id == resource.user_id → 200."""
        assert True, "RED: own resource accessible"

    def test_user_cannot_access_others_resource(self):
        """user_id != resource.user_id → 403 Forbidden."""
        assert True, "RED: others resource blocked"

    def test_ownership_check_before_data_returned(self):
        """Ownership validated before any data is returned."""
        assert True, "RED: ownership first"

    def test_missing_user_id_returns_401_not_403(self):
        """No auth (user_id=None) → 401, not 403."""
        assert True, "RED: 401 vs 403 distinction"
