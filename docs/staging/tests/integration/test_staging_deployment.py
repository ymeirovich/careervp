"""
Integration tests for Staging Deployment - Actual AWS Validation

These tests validate the staging environment deployment by:
1. Verifying SSM parameters exist in AWS
2. Checking CDK can synthesize the staging stack
3. Verifying the stack is deployed and functional
4. Testing actual API endpoints

CRITICAL: These tests MUST FAIL before staging is fully deployed.
They validate ACTUAL AWS resources, not mocks.

Run with:
    pytest docs/staging/tests/integration/test_staging_deployment.py -v
    # Or with AWS credentials:
    AWS_ACCESS_KEY_ID=xxx AWS_SECRET_ACCESS_KEY=xxx pytest docs/staging/tests/integration/...

Prerequisites:
- AWS credentials configured
- Staging environment deployed (for post-deployment validation)
"""

import os
import subprocess
from pathlib import Path

import pytest


# Mark all tests as integration tests
pytestmark = pytest.mark.integration

# Get repo root
REPO_ROOT = Path(__file__).parent.parent.parent.parent.parent


class TestStagingSSMParameters:
    """
    Test suite for staging SSM parameters - ACTUAL AWS VALIDATION.

    These tests validate SSM parameters exist in the real AWS account.
    """

    @pytest.fixture(autouse=True)  # type: ignore[misc]
    def setup_aws_credentials(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Set up AWS credentials from environment."""
        # Use provided credentials or skip if not available
        if "AWS_ACCESS_KEY_ID" not in os.environ:
            pytest.skip(
                "AWS credentials not provided - set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY"
            )

        monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")

    def test_ssm_anthropic_api_key_exists(self) -> None:
        """
        CRITICAL: Test that Anthropic API key SSM parameter exists.

        This parameter is REQUIRED for any AI functionality.
        """
        result = subprocess.run(
            [
                "aws",
                "ssm",
                "get-parameter",
                "--name",
                "/careervp/staging/anthropic-api-key",
                "--region",
                "us-east-1",
                "--with-decryption",
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )

        assert result.returncode == 0, (
            f"SSM parameter /careervp/staging/anthropic-api-key does not exist. "
            f"This is REQUIRED for staging deployment.\n"
            f"Error: {result.stderr}"
        )

    def test_ssm_jwt_private_key_exists(self) -> None:
        """
        CRITICAL: Test that JWT private key SSM parameter exists.

        This parameter is REQUIRED for authentication.
        """
        result = subprocess.run(
            [
                "aws",
                "ssm",
                "get-parameter",
                "--name",
                "/careervp/staging/jwt-private-key",
                "--region",
                "us-east-1",
                "--with-decryption",
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )

        assert result.returncode == 0, (
            f"SSM parameter /careervp/staging/jwt-private-key does not exist. "
            f"This is REQUIRED for staging deployment.\n"
            f"Error: {result.stderr}"
        )

    def test_ssm_jwt_public_key_exists(self) -> None:
        """
        CRITICAL: Test that JWT public key SSM parameter exists.

        This parameter is REQUIRED for authentication.
        """
        result = subprocess.run(
            [
                "aws",
                "ssm",
                "get-parameter",
                "--name",
                "/careervp/staging/jwt-public-key",
                "--region",
                "us-east-1",
                "--with-decryption",
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )

        assert result.returncode == 0, (
            f"SSM parameter /careervp/staging/jwt-public-key does not exist. "
            f"This is REQUIRED for staging deployment.\n"
            f"Error: {result.stderr}"
        )

    def test_all_required_ssm_parameters_exist(self) -> None:
        """
        Test that ALL required SSM parameters exist.

        This is the comprehensive check - ALL must pass.
        """
        required_params = [
            "/careervp/staging/anthropic-api-key",
            "/careervp/staging/jwt-private-key",
            "/careervp/staging/jwt-public-key",
        ]

        missing = []
        for param in required_params:
            result = subprocess.run(
                [
                    "aws",
                    "ssm",
                    "get-parameter",
                    "--name",
                    param,
                    "--region",
                    "us-east-1",
                    "--with-decryption",
                ],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode != 0:
                missing.append(param)

        assert len(missing) == 0, (
            f"Missing required SSM parameters: {missing}. "
            "ALL parameters must exist before staging is operational."
        )


class TestStagingCDKStack:
    """
    Test suite for staging CDK stack synthesis - ACTUAL VALIDATION.

    These tests validate the CDK stack can actually synthesize.
    """

    @pytest.fixture(autouse=True)  # type: ignore[misc]
    def setup_environment(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Set up staging environment variables."""
        monkeypatch.setenv("ENVIRONMENT", "staging")
        monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")

    def test_cdk_synth_staging_succeeds(self) -> None:
        """
        CRITICAL: Test that CDK can synthesize the staging stack.

        This MUST succeed for deployment to work.
        """
        env = os.environ.copy()
        env["ENVIRONMENT"] = "staging"

        result = subprocess.run(
            ["python", "-m", "cdk", "synth", "CareerVpCrudStaging"],
            cwd=str(REPO_ROOT / "infra"),
            env=env,
            capture_output=True,
            text=True,
            timeout=300,
        )

        assert result.returncode == 0, (
            f"CDK synth FAILED for CareerVpCrudStaging.\n"
            f"This means the staging stack cannot be deployed.\n"
            f"STDERR: {result.stderr}\n"
            f"STDOUT: {result.stdout[:2000]}"
        )

        # Verify it's actually staging output
        output = result.stdout.lower()
        assert "staging" in output or "careervpcrudstaging" in output.lower(), (
            "CDK output should contain staging references"
        )

    def test_cdk_diff_shows_expected_changes(self) -> None:
        """
        Test that CDK diff can run for staging stack.

        This validates the stack is configured correctly.
        """
        env = os.environ.copy()
        env["ENVIRONMENT"] = "staging"

        result = subprocess.run(
            ["python", "-m", "cdk", "diff", "CareerVpCrudStaging"],
            cwd=str(REPO_ROOT / "infra"),
            env=env,
            capture_output=True,
            text=True,
            timeout=60,
        )

        # Diff returns non-zero if there are changes (expected for new deployment)
        # But it should still run without errors
        if result.returncode != 0:
            # Check if it's "no changes" vs actual error
            if "No changes" in result.stdout or "No changes" in result.stderr:
                pass  # No changes is fine
            elif "Error" in result.stderr or "error" in result.stderr.lower():
                pytest.fail(f"CDK diff error: {result.stderr}")

        # Should complete without exception
        assert "RuntimeError" not in result.stderr
        assert "Exception" not in result.stderr


class TestStagingStackDeployment:
    """
    Test suite for staging CloudFormation stack - ACTUAL AWS VALIDATION.

    These tests validate the stack is actually deployed.
    """

    @pytest.fixture(autouse=True)  # type: ignore[misc]
    def check_aws_credentials(self) -> None:
        """Skip if AWS credentials not available."""
        if "AWS_ACCESS_KEY_ID" not in os.environ:
            pytest.skip("AWS credentials not provided")

    def test_cloudformation_stack_exists(self) -> None:
        """
        Test that CareerVpCrudStaging CloudFormation stack exists.

        This validates the stack was deployed.
        """
        result = subprocess.run(
            [
                "aws",
                "cloudformation",
                "describe-stacks",
                "--stack-name",
                "CareerVpCrudStaging",
                "--region",
                "us-east-1",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )

        assert result.returncode == 0, (
            f"Stack CareerVpCrudStaging does not exist.\n"
            f"Run: cd infra && ENVIRONMENT=staging python -m cdk deploy CareerVpCrudStaging\n"
            f"Error: {result.stderr}"
        )

    def test_stack_is_in_create_complete_or_update_complete_status(self) -> None:
        """
        Test that the stack is in a successful state.

        Stack must be CREATE_COMPLETE or UPDATE_COMPLETE.
        """
        result = subprocess.run(
            [
                "aws",
                "cloudformation",
                "describe-stacks",
                "--stack-name",
                "CareerVpCrudStaging",
                "--region",
                "us-east-1",
                "--query",
                "Stacks[0].StackStatus",
                "--output",
                "text",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.returncode != 0:
            pytest.skip("Stack not deployed yet")

        status = result.stdout.strip()
        valid_statuses = {"CREATE_COMPLETE", "UPDATE_COMPLETE"}

        assert status in valid_statuses, (
            f"Stack status is {status}, expected one of {valid_statuses}. "
            f"Stack may have failed to deploy."
        )

    def test_stack_has_api_gateway_output(self) -> None:
        """
        Test that the stack outputs include API Gateway URL.

        This is required for API access.
        """
        result = subprocess.run(
            [
                "aws",
                "cloudformation",
                "describe-stacks",
                "--stack-name",
                "CareerVpCrudStaging",
                "--region",
                "us-east-1",
                "--query",
                "Stacks[0].Outputs[?OutputKey=='ApiGatewayUrl'].OutputValue",
                "--output",
                "text",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.returncode != 0:
            pytest.skip("Stack not deployed yet")

        api_url = result.stdout.strip()
        assert api_url, (
            "Stack should have ApiGatewayUrl output. Check CDK stack configuration."
        )
        assert "amazonaws.com" in api_url or "execute-api" in api_url, (
            f"API URL should be valid: {api_url}"
        )


class TestStagingResources:
    """
    Test suite for staging resources - ACTUAL AWS VALIDATION.

    These tests validate individual AWS resources exist.
    """

    @pytest.fixture(autouse=True)  # type: ignore[misc]
    def check_aws_credentials(self) -> None:
        """Skip if AWS credentials not available."""
        if "AWS_ACCESS_KEY_ID" not in os.environ:
            pytest.skip("AWS credentials not provided")

    def test_dynamodb_tables_exist_for_staging(self) -> None:
        """
        Test that DynamoDB tables exist with staging suffix.

        Expected tables: careervp-users-table-staging, etc.
        """
        result = subprocess.run(
            [
                "aws",
                "dynamodb",
                "list-tables",
                "--region",
                "us-east-1",
                "--query",
                "TableNames",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )

        assert result.returncode == 0, (
            f"Failed to list DynamoDB tables: {result.stderr}"
        )

        # Extract table names
        import json

        tables = json.loads(result.stdout)

        # Check for staging tables
        staging_tables = [t for t in tables if "staging" in t.lower()]

        assert len(staging_tables) > 0, (
            f"No staging DynamoDB tables found. Expected tables with '-staging' suffix.\n"
            f"Available tables: {tables}"
        )

    def test_lambda_functions_exist_for_staging(self) -> None:
        """
        Test that Lambda functions exist with staging suffix.
        """
        result = subprocess.run(
            [
                "aws",
                "lambda",
                "list-functions",
                "--region",
                "us-east-1",
                "--query",
                "Functions[].FunctionName",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )

        assert result.returncode == 0, (
            f"Failed to list Lambda functions: {result.stderr}"
        )

        import json

        functions = json.loads(result.stdout)

        # Check for staging functions
        staging_functions = [f for f in functions if "staging" in f.lower()]

        assert len(staging_functions) > 0, (
            f"No staging Lambda functions found. Expected functions with 'staging' in name.\n"
            f"Available functions: {functions[:10]}..."  # Show first 10
        )

    def test_api_gateway_exists_for_staging(self) -> None:
        """
        Test that API Gateway exists for staging.
        """
        result = subprocess.run(
            [
                "aws",
                "apigateway",
                "get-rest-apis",
                "--region",
                "us-east-1",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )

        assert result.returncode == 0, f"Failed to list APIs: {result.stderr}"

        import json

        apis = json.loads(result.stdout)

        # Check for staging API
        staging_apis = [
            a for a in apis.get("items", []) if "staging" in a.get("name", "").lower()
        ]

        assert len(staging_apis) > 0, (
            f"No staging API Gateway found. Expected API with 'staging' in name.\n"
            f"Available APIs: {[a.get('name') for a in apis.get('items', [])]}"
        )


class TestStagingConfigurationLoading:
    """
    Integration tests for staging configuration loading.

    These tests validate configuration is loaded correctly at runtime.
    """

    def test_staging_config_loads_successfully(self) -> None:
        """
        Test that staging configuration can be loaded by the application.
        """
        config_path = (
            REPO_ROOT
            / "infra"
            / "careervp"
            / "configuration"
            / "json"
            / "staging_configuration.json"
        )

        assert config_path.exists(), f"Staging config not found at {config_path}"

        import json

        with open(config_path, "r") as f:
            config = json.load(f)

        assert "features" in config, "Config must have features"
        assert "countries" in config, "Config must have countries"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
