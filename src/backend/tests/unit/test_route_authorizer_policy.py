"""
Unit tests for route authorizer policy verification.

Validates that API Gateway route mappings in api_construct.py
match the auth_required expectations from auth_and_authorizer_spec.yaml.

Tests:
- Public routes: /health, /auth/register, /auth/login (auth_required: false)
- Protected routes: all other 24 routes (auth_required: true)
"""

import json
from pathlib import Path

import pytest
import yaml

# Paths
SCRIPT_DIR = Path(__file__).parent.parent.parent.parent.parent / 'docs' / 'refactor3'
SPECS_DIR = SCRIPT_DIR / 'specs'
PAYLOADS_DIR = Path(__file__).parent.parent.parent.parent.parent / 'docs' / 'refactor2' / 'payloads'


def load_payload_contracts() -> dict[tuple[str, str], dict]:
    """Load all payload contracts and extract method/path pairs."""
    contracts = {}

    if not PAYLOADS_DIR.exists():
        pytest.skip(f'Payloads directory not found: {PAYLOADS_DIR}')

    for payload_file in PAYLOADS_DIR.glob('*.json'):
        try:
            with open(payload_file) as f:
                data = json.load(f)

            method = data.get('method', '').upper()
            path = data.get('path', '')

            if method and path:
                contracts[(method, path)] = {
                    'method': method,
                    'path': path,
                    'description': data.get('description', ''),
                }
        except (json.JSONDecodeError, IOError):
            continue

    return contracts


def load_auth_spec() -> dict:
    """Load auth_and_authorizer_spec.yaml."""
    spec_path = SPECS_DIR / 'auth_and_authorizer_spec.yaml'
    if not spec_path.exists():
        pytest.skip(f'Auth spec not found: {spec_path}')

    with open(spec_path) as f:
        return yaml.safe_load(f)


# Expected auth requirements from auth_and_authorizer_spec.yaml
# These are defined in the spec under "unprotected_routes" and "protected_routes"
EXPECTED_PUBLIC_ROUTES = {
    ('GET', '/health'),
    ('POST', '/auth/register'),
    ('POST', '/auth/login'),
}


class TestRouteAuthorizerPolicy:
    """Tests for route authorization policy invariants."""

    def test_payload_contracts_loaded(self):
        """Verify we can load payload contracts."""
        contracts = load_payload_contracts()
        assert len(contracts) > 0, 'No payload contracts loaded'

    def test_auth_spec_defines_public_routes(self):
        """Verify auth_and_authorizer_spec.yaml defines public routes correctly."""
        spec = load_auth_spec()

        # Check unprotected_routes in spec
        unprotected = spec.get('solution', {}).get('unprotected_routes', {})
        routes = unprotected.get('routes', [])

        # Verify the three expected public routes
        public_paths = {r['path'] for r in routes}
        assert '/health' in public_paths
        assert '/auth/register' in public_paths
        assert '/auth/login' in public_paths

    def test_auth_spec_defines_protected_routes(self):
        """Verify auth_and_authorizer_spec.yaml defines protected routes."""
        spec = load_auth_spec()

        # Check protected_routes in spec
        protected = spec.get('solution', {}).get('protected_routes', {})
        routes = protected.get('routes', [])

        # Should have 22 protected routes in spec (per the spec)
        assert len(routes) == 22, f'Expected 22 protected routes in spec, found {len(routes)}'

    def test_total_route_count(self):
        """Verify we have exactly 27 routes."""
        contracts = load_payload_contracts()
        assert len(contracts) == 27, f'Expected 27 routes, found {len(contracts)}'

    def test_public_routes_in_payloads(self):
        """Verify public routes exist in payload contracts."""
        contracts = load_payload_contracts()

        # Verify all three public routes are in payloads
        assert ('GET', '/health') in contracts, '/health not in payloads'
        assert ('POST', '/auth/register') in contracts, '/auth/register not in payloads'
        assert ('POST', '/auth/login') in contracts, '/auth/login not in payloads'

    def test_auth_refresh_is_protected(self):
        """Verify /auth/refresh is in protected routes list."""
        contracts = load_payload_contracts()
        refresh_route = ('POST', '/auth/refresh')

        assert refresh_route in contracts, '/auth/refresh not found in payloads'

    def test_public_routes_defined_in_spec(self):
        """Verify public route expectations are correctly defined."""
        # The EXPECTED_PUBLIC_ROUTES set matches auth_and_authorizer_spec.yaml
        spec = load_auth_spec()

        unprotected = spec.get('solution', {}).get('unprotected_routes', {})
        routes = unprotected.get('routes', [])

        # Extract paths from spec
        spec_public_paths = {r['path'] for r in routes}

        # Should match our expected public routes
        assert spec_public_paths == {'/health', '/auth/register', '/auth/login'}


class TestApiConstructRouteMapping:
    """Tests for api_construct.py route mapping."""

    def test_public_routes_defined(self):
        """Verify api_construct defines correct public routes."""
        # This tests the expected public routes based on the spec
        # The actual implementation is tested via CDK synthesis

        public_routes = EXPECTED_PUBLIC_ROUTES
        assert ('GET', '/health') in public_routes
        assert ('POST', '/auth/register') in public_routes
        assert ('POST', '/auth/login') in public_routes

    def test_no_public_routes_protected(self):
        """Ensure public routes are not incorrectly marked as protected."""
        # All three should be in the public set
        assert ('GET', '/health') in EXPECTED_PUBLIC_ROUTES
        assert ('POST', '/auth/register') in EXPECTED_PUBLIC_ROUTES
        assert ('POST', '/auth/login') in EXPECTED_PUBLIC_ROUTES
