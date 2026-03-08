"""
Unit tests for route smoke script.

Tests the smoke script's ability to:
- Parse payload contracts from docs/refactor3/payloads/
- Fail fast on first route mismatch
- Validate status codes and JSON responses
"""

import json
import os
import subprocess
from pathlib import Path

# Paths
SCRIPT_DIR = Path(__file__).parent.parent.parent.parent.parent / 'docs' / 'refactor3' / 'scripts'
PAYLOADS_DIR = SCRIPT_DIR.parent / 'payloads'
SMOKE_SCRIPT = SCRIPT_DIR / 'step_1.3_route_smoke.sh'


class TestSmokeScriptParsesPayloadContracts:
    """Tests for smoke script payload contract parsing."""

    def test_payloads_directory_exists(self):
        """Verify payloads directory exists."""
        assert PAYLOADS_DIR.exists(), f'Payloads directory not found: {PAYLOADS_DIR}'

    def test_payloads_count(self):
        """Verify we have 28 payload contracts."""
        json_files = list(PAYLOADS_DIR.glob('*.json'))
        assert len(json_files) == 28, f'Expected 28 payloads, found {len(json_files)}'

    def test_health_payload_structure(self):
        """Verify health_check.json has required fields."""
        health_file = PAYLOADS_DIR / 'health_check.json'
        assert health_file.exists(), 'health_check.json not found'

        with open(health_file) as f:
            data = json.load(f)

        assert data.get('method') == 'GET'
        assert data.get('path') == '/health'
        assert 'expected_response' in data
        assert data['expected_response'].get('status_code') == 200

    def test_job_list_payload_structure(self):
        """Verify job_list.json has required fields."""
        job_list_file = PAYLOADS_DIR / 'job_list.json'
        assert job_list_file.exists(), 'job_list.json not found'

        with open(job_list_file) as f:
            data = json.load(f)

        assert data.get('method') == 'GET'
        assert data.get('path') == '/jobs'
        assert 'expected_response' in data

    def test_auth_login_payload_structure(self):
        """Verify auth_login.json has required fields."""
        login_file = PAYLOADS_DIR / 'auth_login.json'
        assert login_file.exists(), 'auth_login.json not found'

        with open(login_file) as f:
            data = json.load(f)

        assert data.get('method') == 'POST'
        assert data.get('path') == '/auth/login'
        assert 'expected_response' in data

    def test_public_routes_in_payloads(self):
        """Verify public routes are defined in payloads."""
        public_routes = [
            'health_check',
            'auth_login',
            'auth_register',
        ]

        for route in public_routes:
            payload_file = PAYLOADS_DIR / f'{route}.json'
            assert payload_file.exists(), f'{route}.json not found'

    def test_smoke_script_exists(self):
        """Verify smoke script exists."""
        assert SMOKE_SCRIPT.exists(), f'Smoke script not found: {SMOKE_SCRIPT}'

    def test_smoke_script_is_executable(self):
        """Verify smoke script is executable."""
        assert os.access(SMOKE_SCRIPT, os.X_OK), 'Smoke script is not executable'


class TestSmokeScriptFailFastBehavior:
    """Tests for smoke script fail-fast behavior."""

    def test_script_fails_without_api_base(self):
        """Test script fails when API_BASE is not set."""
        # Remove API_BASE from environment
        env = os.environ.copy()
        env.pop('API_BASE', None)

        # Run script without arguments - it will try resolve_api_base.py which
        # will fail (either due to no API_BASE or no CloudFormation credentials)
        result = subprocess.run(
            [str(SMOKE_SCRIPT), '', 'test@example.com', 'password'],
            env=env,
            capture_output=True,
            text=True,
            timeout=10,
        )

        # Should fail (either due to missing API_BASE or AWS credentials)
        assert result.returncode != 0, 'Script should fail without API_BASE'

    def test_script_fails_without_credentials(self):
        """Test script fails when credentials are not provided."""
        env = os.environ.copy()
        env['API_BASE'] = 'https://api.example.com'
        env.pop('TEST_EMAIL', None)
        env.pop('TEST_PASSWORD', None)

        result = subprocess.run(
            [str(SMOKE_SCRIPT)],
            env=env,
            capture_output=True,
            text=True,
            timeout=10,
        )

        # Should fail due to missing credentials
        assert result.returncode != 0, 'Script should fail without credentials'

    def test_script_uses_payloads_directory(self):
        """Test script references payloads directory in its logic."""
        with open(SMOKE_SCRIPT) as f:
            content = f.read()

        # Verify script references payloads directory
        assert 'PAYLOADS_DIR' in content, 'Script should define PAYLOADS_DIR'
        assert 'payloads' in content.lower(), 'Script should reference payloads'

    def test_script_has_fail_fast_logic(self):
        """Test script has fail-fast behavior (|| exit 1)."""
        with open(SMOKE_SCRIPT) as f:
            content = f.read()

        # Check for fail-fast patterns
        assert 'set -e' in content or 'set -o errexit' in content, 'Script should use set -e for fail-fast'


class TestSmokeScriptContractValidation:
    """Tests for smoke script contract validation logic."""

    def test_health_payload_has_expected_status(self):
        """Verify health payload expects 200 status."""
        health_file = PAYLOADS_DIR / 'health_check.json'
        with open(health_file) as f:
            data = json.load(f)

        assert data['expected_response']['status_code'] == 200

    def test_auth_login_payload_has_expected_status(self):
        """Verify auth_login payload expects 200 status."""
        login_file = PAYLOADS_DIR / 'auth_login.json'
        with open(login_file) as f:
            data = json.load(f)

        assert data['expected_response']['status_code'] == 200

    def test_protected_routes_have_auth_headers(self):
        """Verify protected routes have Authorization in headers."""
        # Check a protected route like job_list
        job_file = PAYLOADS_DIR / 'job_list.json'
        with open(job_file) as f:
            data = json.load(f)

        # Protected routes should have Authorization header defined
        assert 'headers' in data, 'Protected route should have headers defined'
        assert 'Authorization' in data['headers'], 'Protected route should have Authorization header'
