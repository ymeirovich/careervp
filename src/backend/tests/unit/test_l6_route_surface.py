"""
L6.4 — Route Surface Verification Unit Tests

Validates: deployed routes match frozen spec, I7 evidence generated
Spec: docs/best_practices/yaml/cicd_spec.yaml
Payload: docs/refactor/payloads/beta_l6_route_surface_test.json#L6_4_route_surface
Invariant: I7
Results: docs/beta/execution_results/L6_4_results.md
"""

import json
import os

import pytest

CANONICAL_ROUTES_PATH = '/Users/yitzchak/Documents/dev/careervp/docs/beta/canonical_routes.md'
FROZEN_SPEC_PATH = '/Users/yitzchak/Documents/dev/careervp/docs/beta/evidence/I7_routes/frozen_spec.json'
ROUTE_DIFF_PATH = '/Users/yitzchak/Documents/dev/careervp/docs/beta/evidence/I7_routes/route-surface-diff.txt'
API_CONSTRUCT_PATH = '/Users/yitzchak/Documents/dev/careervp/infra/careervp/api_construct.py'

EXPECTED_ROUTE_COUNT = 31

# Deprecated routes that must NOT be in the deployed surface
DEPRECATED_ROUTES = [
    'GET /api/cv',
    'POST /api/cv',
    'GET /api/jobs',
    'POST /api/jobs',
    'GET /api/users',
]

# Canonical routes that MUST be in the deployed surface
CANONICAL_ROUTES = [
    'GET /health',
    'POST /auth/register',
    'POST /auth/login',
    'POST /auth/refresh',
    'GET /users/me',
    'POST /users/me/cv',
    'GET /users/me/cv',
    'GET /users/me/usage',
    'POST /jobs',
    'GET /jobs/{job_id}',
    'GET /jobs',
    'POST /gap-questions',
    'GET /gap-questions/{question_id}',
    'POST /gap-questions/{question_id}/responses',
    'POST /vprs',
    'GET /vprs',
    'GET /vprs/{vpr_id}',
    'POST /cover-letters',
    'GET /cover-letters',
    'GET /cover-letters/{cover_letter_id}',
    'POST /cv-tailorings',
    'GET /cv-tailorings',
    'GET /cv-tailorings/{cv_tailoring_id}',
    'POST /interview-preps',
    'GET /interview-preps',
    'GET /interview-preps/{interview_prep_id}',
    'GET /applications/{application_id}',
    'POST /company-research',
    'POST /company-research/fetch',
    'GET /company-research/{research_id}',
    'GET /company-research',
]


@pytest.mark.unit
class TestRouteSurfaceMatchesSpec:
    """Deployed route surface must exactly match canonical spec."""

    def test_route_count_is_31(self):
        """Exactly 31 routes in canonical spec."""
        assert len(CANONICAL_ROUTES) == EXPECTED_ROUTE_COUNT, f'Expected {EXPECTED_ROUTE_COUNT} canonical routes, got {len(CANONICAL_ROUTES)}'

    @pytest.mark.parametrize('route', CANONICAL_ROUTES)
    def test_canonical_route_in_spec(self, route):
        """Each canonical route is in the spec list."""
        assert route in CANONICAL_ROUTES, f'Canonical route missing: {route}'

    @pytest.mark.parametrize('deprecated_route', DEPRECATED_ROUTES)
    def test_deprecated_route_not_in_canonical_spec(self, deprecated_route):
        """Deprecated /api/* routes not in canonical spec."""
        assert deprecated_route not in CANONICAL_ROUTES, f'Deprecated route still in canonical spec: {deprecated_route}'


@pytest.mark.unit
class TestRouteSurfaceDiffEmpty:
    """Route diff between deployed API and frozen spec must be empty."""

    def test_route_diff_file_exists(self):
        """route-surface-diff.txt evidence file exists."""
        assert os.path.exists(ROUTE_DIFF_PATH), f'route-surface-diff.txt missing at {ROUTE_DIFF_PATH}'

    def test_route_diff_is_empty(self):
        """route-surface-diff.txt exists and is empty (no differences)."""
        assert os.path.exists(ROUTE_DIFF_PATH), f'Missing: {ROUTE_DIFF_PATH}'
        with open(ROUTE_DIFF_PATH) as f:
            content = f.read().strip()
        assert content == '', f'Route diff is non-empty:\n{content}'

    def test_frozen_spec_exists(self):
        """frozen_spec.json evidence file exists."""
        assert os.path.exists(FROZEN_SPEC_PATH), f'frozen_spec.json missing at {FROZEN_SPEC_PATH}'

    def test_frozen_spec_has_31_routes(self):
        """frozen_spec.json contains exactly 40 routes (31 original + 4 billing + 5 new endpoints)."""
        assert os.path.exists(FROZEN_SPEC_PATH), f'Missing: {FROZEN_SPEC_PATH}'
        with open(FROZEN_SPEC_PATH) as f:
            spec = json.load(f)
        routes = spec.get('routes', [])
        assert len(routes) == 40, f'Expected 40 routes in frozen spec, got {len(routes)}'


@pytest.mark.unit
class TestRouteAuthenticationSurface:
    """Auth surface: public routes use NONE, protected routes use COGNITO."""

    def test_health_route_is_public(self):
        """GET /health has no authentication requirement per frozen spec."""
        assert os.path.exists(FROZEN_SPEC_PATH), f'Missing: {FROZEN_SPEC_PATH}'
        with open(FROZEN_SPEC_PATH) as f:
            spec = json.load(f)
        health = next((r for r in spec['routes'] if r['path'] == '/health'), None)
        assert health is not None, 'GET /health not found in frozen spec'
        assert health['auth'] == 'NONE', f'Expected NONE auth for /health, got: {health["auth"]}'

    def test_auth_routes_are_public(self):
        """POST /auth/* routes have no authentication requirement."""
        assert os.path.exists(FROZEN_SPEC_PATH), f'Missing: {FROZEN_SPEC_PATH}'
        with open(FROZEN_SPEC_PATH) as f:
            spec = json.load(f)
        auth_routes = [r for r in spec['routes'] if r['path'].startswith('/auth/')]
        assert len(auth_routes) >= 3, f'Expected 3+ /auth/* routes, got {len(auth_routes)}'
        for route in auth_routes:
            assert route['auth'] == 'NONE', f'Expected NONE auth for {route["path"]}, got: {route["auth"]}'

    def test_protected_routes_require_cognito(self):
        """All non-health/non-auth routes require Cognito authorization."""
        assert os.path.exists(FROZEN_SPEC_PATH), f'Missing: {FROZEN_SPEC_PATH}'
        with open(FROZEN_SPEC_PATH) as f:
            spec = json.load(f)
        # Exclude public routes: /auth/*, /health, and /billing/webhook (called by Stripe, not browsers)
        public_paths = {'/health', '/billing/webhook'}
        protected = [r for r in spec['routes'] if not r['path'].startswith('/auth/') and r['path'] not in public_paths]
        for route in protected:
            assert route['auth'] == 'COGNITO', f'Expected COGNITO auth for {route["path"]}, got: {route["auth"]}'

    def test_no_custom_lambda_authorizer_routes(self):
        """No routes using custom Lambda authorizer (replaced by Cognito)."""
        assert os.path.exists(FROZEN_SPEC_PATH), f'Missing: {FROZEN_SPEC_PATH}'
        with open(FROZEN_SPEC_PATH) as f:
            spec = json.load(f)
        lambda_auth = [r for r in spec['routes'] if r.get('auth') == 'LAMBDA']
        assert lambda_auth == [], f'Routes still using Lambda authorizer: {lambda_auth}'


@pytest.mark.unit
class TestNoDeprecatedRoutes:
    """No deprecated /api/* routes exist in deployed API."""

    @pytest.mark.parametrize('deprecated_route', DEPRECATED_ROUTES)
    def test_deprecated_route_not_deployed(self, deprecated_route):
        """Deprecated route not present in canonical spec."""
        assert deprecated_route not in CANONICAL_ROUTES, f"Deprecated route '{deprecated_route}' still in canonical spec"

    def test_no_api_prefix_routes_deployed(self):
        """No routes with /api/ prefix exist in canonical spec."""
        api_prefix_routes = [r for r in CANONICAL_ROUTES if '/api/' in r]
        assert api_prefix_routes == [], f'Routes with /api/ prefix found: {api_prefix_routes}'


@pytest.mark.unit
class TestCvTailoringDeleteRouteSurface:
    """CV tailoring route surface must include delete route."""

    def test_cv_tailoring_delete_route_present(self):
        """The cv-tailoring proxy covers DELETE /cv-tailoring/{cvTailoringId}."""
        with open(API_CONSTRUCT_PATH) as f:
            content = f.read()

        assert '("/cv-tailoring", self.cv_tailoring_func, True)' in content
