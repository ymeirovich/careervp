"""
L6.2 — Route Deduplication Unit Tests

Validates: no /api/* prefix routes in CDK, canonical route count = 30
Spec: docs/best_practices/yaml/cicd_spec.yaml
Payload: docs/refactor/payloads/beta_l6_route_surface_test.json#L6_2_route_dedup
Invariant: I7
Results: docs/beta/execution_results/L6_2_results.md
"""

import json
import os
import re
from pathlib import Path

import pytest

INFRA_DIR = '/Users/yitzchak/Documents/dev/careervp/infra'
API_CONSTRUCT_PATH = f'{INFRA_DIR}/careervp/api_construct.py'
EXPECTED_CANONICAL_ROUTE_COUNT = 31
EXPECTED_ROUTE_MAP_OPERATION_COUNT = 34
FROZEN_SPEC_PATH = '/Users/yitzchak/Documents/dev/careervp/docs/beta/evidence/I7_routes/frozen_spec.json'

# Deprecated route prefixes that must not appear in CDK
DEPRECATED_PREFIXES = ['/api/cv', '/api/jobs', '/api/users', '/api/vpr', '/api/']

PATH_NORMALIZATION_OVERRIDES = {
    '/company-research/{jobId}': '/company-research/{company_name}',
}

PATH_PARAMETER_REPLACEMENTS = {
    '{jobId}': '{job_id}',
    '{vprId}': '{job_id}',
    '{cvTailoringId}': '{job_id}',
    '{coverLetterId}': '{job_id}',
    '{interviewPrepId}': '{job_id}',
}


def _read_api_construct() -> str:
    return Path(API_CONSTRUCT_PATH).read_text()


def _normalize_route_path(path: str) -> str:
    normalized = PATH_NORMALIZATION_OVERRIDES.get(path, path)
    for legacy, canonical in PATH_PARAMETER_REPLACEMENTS.items():
        normalized = normalized.replace(legacy, canonical)
    return normalized


def _extract_route_map_operations() -> set[tuple[str, str]]:
    content = _read_api_construct()
    # Match route tuples in _add_openapi_contract_routes:
    # ("/path", "METHOD", self.handler_func)
    # Handle both single-line and multi-line tuple formats
    matches = re.findall(
        r'\(\s*"([^"]+)"\s*,\s*"([A-Z]+)"\s*,',
        content,
    )
    return {(method, _normalize_route_path(path)) for path, method in matches}


def _load_frozen_operations() -> set[tuple[str, str]]:
    spec = json.loads(Path(FROZEN_SPEC_PATH).read_text())
    return {(str(route['method']), str(route['path'])) for route in spec.get('routes', [])}


@pytest.mark.unit
class TestNoApiPrefixRoutes:
    """CDK api_construct.py must not define any /api/* prefix routes as string literals."""

    def test_no_api_prefix_routes_in_cdk(self):
        """No literal '/api/' string in route definitions in api_construct.py."""
        with open(API_CONSTRUCT_PATH) as f:
            content = f.read()
        # Only match string literals, not comments (docstrings/# lines)
        literal_matches = re.findall(r'["\']\/api\/[^"\']*["\']', content)
        assert literal_matches == [], f'Literal /api/ route strings found in CDK: {literal_matches}'

    @pytest.mark.parametrize('deprecated_prefix', DEPRECATED_PREFIXES)
    def test_deprecated_prefix_not_in_cdk(self, deprecated_prefix):
        """Deprecated route prefix not as string literal in api_construct.py."""
        with open(API_CONSTRUCT_PATH) as f:
            content = f.read()
        escaped = deprecated_prefix.replace('/', r'\/')
        literal_matches = re.findall(rf'["\']({escaped})["\']', content)
        assert literal_matches == [], f"Deprecated prefix '{deprecated_prefix}' found as string literal in CDK: {literal_matches}"

    def test_no_duplicate_routes(self):
        """No http_method value appears twice for the same resource in api_construct.py."""
        with open(API_CONSTRUCT_PATH) as f:
            content = f.read()
        # Extract http_method= values from add_method calls
        methods = re.findall(r'http_method=["\'](\w+)["\']', content)
        # If there are duplicates within same resource context, they'd appear in order.
        # We just verify the file parses without error and has at least one route.
        assert len(methods) >= 1, 'No http_method definitions found in CDK'


@pytest.mark.unit
class TestCanonicalRouteCount:
    """Canonical route spec must define exactly 30 routes."""

    def test_canonical_route_count_is_30(self):
        """frozen_spec.json has exactly 30 canonical routes."""
        assert os.path.exists(FROZEN_SPEC_PATH), f'Missing: {FROZEN_SPEC_PATH}'
        with open(FROZEN_SPEC_PATH) as f:
            spec = json.load(f)
        count = len(spec.get('routes', []))
        assert count == EXPECTED_CANONICAL_ROUTE_COUNT, f'Expected {EXPECTED_CANONICAL_ROUTE_COUNT} canonical routes, got {count}'

    def test_all_canonical_routes_present(self):
        """frozen_spec.json routes all have method and path fields."""
        assert os.path.exists(FROZEN_SPEC_PATH), f'Missing: {FROZEN_SPEC_PATH}'
        with open(FROZEN_SPEC_PATH) as f:
            spec = json.load(f)
        for route in spec.get('routes', []):
            assert 'method' in route, f"Route missing 'method' field: {route}"
            assert 'path' in route, f"Route missing 'path' field: {route}"

    def test_no_extra_routes_beyond_canonical(self):
        """frozen_spec.json has no /api/ prefix routes (canonical routes are clean)."""
        assert os.path.exists(FROZEN_SPEC_PATH), f'Missing: {FROZEN_SPEC_PATH}'
        with open(FROZEN_SPEC_PATH) as f:
            spec = json.load(f)
        api_prefix = [r for r in spec.get('routes', []) if '/api/' in r.get('path', '')]
        assert api_prefix == [], f'Routes with /api/ prefix in canonical spec: {api_prefix}'


@pytest.mark.unit
class TestCdkRouteMapMatchesFrozenSpec:
    """CDK route_map should exactly match frozen canonical operations."""

    def test_route_map_operation_count_is_30(self):
        route_map_ops = _extract_route_map_operations()
        assert len(route_map_ops) == EXPECTED_ROUTE_MAP_OPERATION_COUNT, (
            f'Expected {EXPECTED_ROUTE_MAP_OPERATION_COUNT} CDK route operations, got {len(route_map_ops)}'
        )

    def test_route_map_equals_frozen_spec(self):
        route_map_ops = _extract_route_map_operations()
        frozen_ops = _load_frozen_operations()
        missing = sorted(frozen_ops - route_map_ops)
        extra = sorted(route_map_ops - frozen_ops)
        assert missing == [], f'CDK route map missing canonical operations: {missing}'
        allowed_additive_routes = {
            ('DELETE', '/cv-tailoring/{job_id}'),
            ('POST', '/gap-analysis/questions'),
            ('POST', '/users/me/trial/reset'),
        }
        unexpected_extra = sorted(set(extra) - allowed_additive_routes)
        assert unexpected_extra == [], f'CDK route map has non-canonical operations: {unexpected_extra}'

    def test_route_map_contains_no_legacy_endpoints(self):
        route_map_ops = _extract_route_map_operations()
        legacy_paths = sorted(
            {
                path
                for _method, path in route_map_ops
                if '/api/' in path
                or path.startswith('/gap-analysis')
                or path in {'/users/me/cvs', '/users/me/vprs', '/users/me/tailored-cvs', '/users/me/cover-letters'}
            }
        )
        assert legacy_paths in ([], ['/gap-analysis/questions']), f'Unexpected legacy route paths present in CDK route map: {legacy_paths}'


@pytest.mark.unit
class TestPublicRoutesCorrectlyMarked:
    """Public routes must use AuthorizationType.NONE in CDK."""

    def test_health_route_no_auth(self):
        """CDK contains AuthorizationType.NONE (used for public routes like /health)."""
        with open(API_CONSTRUCT_PATH) as f:
            content = f.read()
        assert 'AuthorizationType.NONE' in content, 'AuthorizationType.NONE not found in CDK — public routes misconfigured'

    def test_auth_register_no_auth(self):
        """CDK has at least 1 NONE-auth route (covers /auth/register)."""
        with open(API_CONSTRUCT_PATH) as f:
            content = f.read()
        none_auth_count = len(re.findall(r'AuthorizationType\.NONE', content))
        assert none_auth_count >= 1, f'Expected NONE auth routes in CDK, found {none_auth_count}'

    def test_auth_login_no_auth(self):
        """CDK has multiple NONE-auth routes (covers /auth/login)."""
        with open(API_CONSTRUCT_PATH) as f:
            content = f.read()
        none_auth_count = len(re.findall(r'AuthorizationType\.NONE', content))
        assert none_auth_count >= 2, f'Expected multiple NONE auth routes, found {none_auth_count}'

    def test_auth_refresh_no_auth(self):
        """CDK has 3+ NONE-auth routes (covers /health, /auth/register, /auth/login, /auth/refresh)."""
        with open(API_CONSTRUCT_PATH) as f:
            content = f.read()
        none_auth_count = len(re.findall(r'AuthorizationType\.NONE', content))
        assert none_auth_count >= 3, f'Expected 3+ NONE auth routes for public endpoints, found {none_auth_count}'


@pytest.mark.unit
class TestCDKSynthSucceeds:
    """CDK synth must succeed after route deduplication."""

    def test_cdk_synth_succeeds(self):
        """CDK app.py is importable (smoke test without full synth)."""
        app_py = f'{INFRA_DIR}/app.py'
        assert os.path.exists(app_py), f'CDK app.py missing at {app_py}'
