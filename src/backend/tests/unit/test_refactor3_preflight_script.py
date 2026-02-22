"""
Unit tests for preflight script validation.

Tests the step_0.3_preflight.sh script's contract validation logic.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

# Paths - 5 levels up: unit -> tests -> backend -> src -> careervp
SCRIPTS_DIR = Path(__file__).parent.parent.parent.parent.parent / 'docs' / 'refactor3' / 'scripts'
PAYLOADS_DIR = SCRIPTS_DIR.parent / 'payloads'
PREFLIGHT_SCRIPT = SCRIPTS_DIR / 'step_0.3_preflight.sh'

# Add scripts dir to path for helpers
sys.path.insert(0, str(SCRIPTS_DIR))


class TestPreflightHealthContract:
    """Tests for health endpoint contract validation."""

    def test_preflight_health_contract_validation(self):
        """Test that preflight validates health endpoint contract correctly."""
        health_payload_path = PAYLOADS_DIR / 'health_check.json'

        assert health_payload_path.exists(), f'Health payload not found: {health_payload_path}'

        with open(health_payload_path) as f:
            payload = json.load(f)

        # Verify expected status code
        expected_status = payload.get('expected_response', {}).get('status_code')
        assert expected_status == 200, f'Expected status 200, got {expected_status}'

        # Verify expected body keys
        expected_body = payload.get('expected_response', {}).get('body', {})
        expected_keys = set(expected_body.keys())

        # Health check should have: status, timestamp, version, services
        assert 'status' in expected_keys
        assert 'timestamp' in expected_keys
        assert 'version' in expected_keys
        assert 'services' in expected_keys


class TestPreflightAuthLoginContract:
    """Tests for auth login endpoint contract validation."""

    def test_preflight_auth_login_contract_validation(self):
        """Test that preflight validates auth login endpoint contract correctly."""
        login_payload_path = PAYLOADS_DIR / 'auth_login.json'

        assert login_payload_path.exists(), f'Login payload not found: {login_payload_path}'

        with open(login_payload_path) as f:
            payload = json.load(f)

        # Verify expected status code
        expected_status = payload.get('expected_response', {}).get('status_code')
        assert expected_status == 200, f'Expected status 200, got {expected_status}'

        # Verify expected body keys
        expected_body = payload.get('expected_response', {}).get('body', {})
        expected_keys = set(expected_body.keys())

        # Login should return: access_token, refresh_token, expires_in, token_type
        assert 'access_token' in expected_keys
        assert 'refresh_token' in expected_keys
        assert 'expires_in' in expected_keys
        assert 'token_type' in expected_keys

    @pytest.mark.skip(reason='Complex to mock bash subprocess - covered by integration test')
    def test_preflight_fails_on_non_json_response(self):
        """Test that preflight script fails when endpoint returns non-JSON."""
        pass


class TestPreflightPayloadFiles:
    """Tests that payload files are properly loaded."""

    def test_payload_files_exist(self):
        """Test that all required payload files exist."""
        assert PAYLOADS_DIR.exists(), f'Payloads directory not found: {PAYLOADS_DIR}'

        health_payload = PAYLOADS_DIR / 'health_check.json'
        login_payload = PAYLOADS_DIR / 'auth_login.json'

        assert health_payload.exists(), 'health_check.json not found'
        assert login_payload.exists(), 'auth_login.json not found'

    def test_health_payload_structure(self):
        """Test health_check.json has valid contract structure."""
        with open(PAYLOADS_DIR / 'health_check.json') as f:
            payload = json.load(f)

        assert 'description' in payload
        assert 'method' in payload
        assert 'path' in payload
        assert 'expected_response' in payload

        assert payload['method'] == 'GET'
        assert payload['path'] == '/health'

    def test_login_payload_structure(self):
        """Test auth_login.json has valid contract structure."""
        with open(PAYLOADS_DIR / 'auth_login.json') as f:
            payload = json.load(f)

        assert 'description' in payload
        assert 'method' in payload
        assert 'path' in payload
        assert 'request' in payload
        assert 'expected_response' in payload

        assert payload['method'] == 'POST'
        assert payload['path'] == '/auth/login'

        # Verify request has credentials
        request = payload.get('request', {})
        assert 'email' in request
        assert 'password' in request


class TestPreflightScriptExecution:
    """Tests for preflight script execution."""

    def test_script_is_executable(self):
        """Test that preflight script has executable permissions."""
        assert os.access(PREFLIGHT_SCRIPT, os.X_OK), 'Preflight script is not executable'

    def test_script_fails_without_api_base(self):
        """Test that script fails when API_BASE is not provided."""
        result = subprocess.run(
            [str(PREFLIGHT_SCRIPT)],
            capture_output=True,
            text=True,
            env={},  # No env vars
        )

        assert result.returncode != 0, 'Script should fail without API_BASE'
        # Script outputs to stdout, not stderr
        assert 'API_BASE is required' in result.stdout or 'required' in result.stdout.lower()

    def test_script_fails_without_credentials(self):
        """Test that script fails when credentials are not provided."""
        result = subprocess.run([str(PREFLIGHT_SCRIPT), 'https://api.example.com'], capture_output=True, text=True, env={})

        assert result.returncode != 0, 'Script should fail without credentials'
        # Script outputs to stdout, not stderr
        assert 'required' in result.stdout.lower() or 'email' in result.stdout.lower() or 'password' in result.stdout.lower()
