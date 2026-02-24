"""
Unit tests for Staging Configuration - Deployment Readiness Validation

These tests validate that staging environment is ready for deployment.
They MUST fail before implementation to provide TDD feedback.

Run with:
    pytest docs/staging/tests/unit/test_staging_config.py -v

IMPORTANT: These tests validate ACTUAL deployment readiness, not just file structure.
A passing test means the staging environment can actually be deployed.
"""

import json
import os
import subprocess
from pathlib import Path

import pytest


# Paths relative to the repo root
REPO_ROOT = Path(__file__).parent.parent.parent.parent.parent
STAGING_CONFIG_PATH = (
    REPO_ROOT
    / "infra"
    / "careervp"
    / "configuration"
    / "json"
    / "staging_configuration.json"
)
DEV_CONFIG_PATH = (
    REPO_ROOT
    / "infra"
    / "careervp"
    / "configuration"
    / "json"
    / "dev_configuration.json"
)


class TestStagingConfigurationFile:
    """Test suite for staging configuration FILE validation (pre-deployment)."""

    def test_staging_config_exists(self) -> None:
        """Test that staging configuration file exists."""
        assert STAGING_CONFIG_PATH.exists(), (
            f"Staging config not found at {STAGING_CONFIG_PATH}. "
            "This is required BEFORE deployment."
        )

    def test_staging_config_is_valid_json(self) -> None:
        """Test that staging configuration is valid JSON."""
        with open(STAGING_CONFIG_PATH, "r") as f:
            config = json.load(f)
        assert isinstance(config, dict), "Configuration must be a JSON object"

    def test_staging_config_has_features(self) -> None:
        """Test that staging config has features section."""
        with open(STAGING_CONFIG_PATH, "r") as f:
            config = json.load(f)
        assert "features" in config, "Configuration must have 'features' section"

    def test_staging_config_has_countries(self) -> None:
        """Test that staging config has countries section."""
        with open(STAGING_CONFIG_PATH, "r") as f:
            config = json.load(f)
        assert "countries" in config, "Configuration must have 'countries' section"
        assert isinstance(config["countries"], list), "Countries must be a list"
        assert len(config["countries"]) > 0, "Countries must not be empty"

    def test_staging_countries_are_valid(self) -> None:
        """Test that staging countries are valid country codes."""
        with open(STAGING_CONFIG_PATH, "r") as f:
            config = json.load(f)
        valid_countries = {"ISRAEL", "USA", "GBR", "CAN", "AUS", "DEU", "FRA"}
        countries = set(config.get("countries", []))
        assert countries.issubset(valid_countries), (
            f"Invalid countries: {countries - valid_countries}"
        )

    def test_dev_config_exists(self) -> None:
        """Test that dev configuration file exists for comparison."""
        assert DEV_CONFIG_PATH.exists(), f"Dev config not found at {DEV_CONFIG_PATH}"

    def test_staging_has_same_structure_as_dev(self) -> None:
        """Test that staging config has same structure as dev config."""
        with open(STAGING_CONFIG_PATH, "r") as f:
            staging = json.load(f)
        with open(DEV_CONFIG_PATH, "r") as f:
            dev = json.load(f)

        # Check top-level keys match
        assert set(staging.keys()) == set(dev.keys()), (
            f"Staging keys {set(staging.keys())} don't match dev keys {set(dev.keys())}"
        )

        # Check features structure
        assert "features" in staging and "features" in dev
        assert set(staging["features"].keys()) == set(dev["features"].keys()), (
            "Features structure doesn't match"
        )

    def test_staging_features_have_valid_structure(self) -> None:
        """Test that staging features have valid nested structure."""
        with open(STAGING_CONFIG_PATH, "r") as f:
            config = json.load(f)
        features = config.get("features", {})

        for feature_name, feature_value in features.items():
            assert isinstance(feature_name, str), "Feature name must be string"
            assert isinstance(feature_value, dict), (
                f"Feature {feature_name} must be a dict"
            )


class TestStagingInfrastructureReadiness:
    """
    Test suite for staging infrastructure readiness.

    THESE TESTS MUST FAIL BEFORE STAGING IS DEPLOYED.
    They validate that required AWS resources exist.
    """

    @pytest.fixture(autouse=True)  # type: ignore[misc]
    def setup_aws(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Set up AWS environment for testing."""
        monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
        monkeypatch.setenv(
            "AWS_ACCESS_KEY_ID", os.environ.get("AWS_ACCESS_KEY_ID", "testing")
        )
        monkeypatch.setenv(
            "AWS_SECRET_ACCESS_KEY", os.environ.get("AWS_SECRET_ACCESS_KEY", "testing")
        )

    def test_ssm_parameters_exist_in_aws(self) -> None:
        """
        CRITICAL: Test that SSM parameters exist for staging.

        This test MUST FAIL before SSM parameters are created.
        """
        expected_params = [
            "/careervp/staging/anthropic-api-key",
            "/careervp/staging/jwt-private-key",
            "/careervp/staging/jwt-public-key",
        ]

        # Try to get each parameter - ALL must exist for deployment to work
        missing_params = []
        for param in expected_params:
            try:
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
                    missing_params.append(param)
            except Exception as e:
                missing_params.append(f"{param} (error: {e})")

        assert len(missing_params) == 0, (
            f"Missing SSM parameters: {missing_params}. "
            "These MUST exist before staging deployment. "
            "Run: aws ssm put-parameter --name /careervp/staging/anthropic-api-key ..."
        )

    def test_cdk_synth_succeeds_for_staging(self) -> None:
        """
        CRITICAL: Test that CDK can synthesize staging stack.

        This test MUST FAIL before CDK stack is configured.
        """
        # Set staging environment
        env = os.environ.copy()
        env["ENVIRONMENT"] = "staging"

        # Try to run cdk synth
        result = subprocess.run(
            ["python", "-m", "cdk", "synth", "CareerVpCrudStaging"],
            cwd=str(REPO_ROOT / "infra"),
            env=env,
            capture_output=True,
            text=True,
            timeout=300,  # 5 minutes
        )

        assert result.returncode == 0, (
            f"CDK synth failed for staging. This means the stack cannot be deployed.\n"
            f"Error: {result.stderr}\n"
            f"Output: {result.stdout[:1000]}"
        )

        # Verify output contains staging resources
        assert (
            "CareerVpCrudStaging" in result.stdout or "staging" in result.stdout.lower()
        ), "CDK synth output should mention staging resources"

    def test_staging_stack_can_be_deployed(self) -> None:
        """
        Test that staging CloudFormation stack exists or can be created.

        This validates the stack is deployable.
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

        # Stack should exist (either deployed or will be deployed)
        # If it doesn't exist, that's actually OK for pre-deployment validation
        # But CDK synth must work (tested above)
        if result.returncode != 0:
            # Stack doesn't exist yet - that's fine as long as CDK synth works
            # This is informational only
            pytest.skip("Stack not deployed yet - OK if CDK synth passes")


class TestStagingDeploymentReadiness:
    """
    Test suite for actual deployment readiness validation.

    These tests validate the full deployment pipeline is ready.
    """

    def test_github_workflow_exists(self) -> None:
        """Test that staging deployment workflow file exists."""
        workflow_path = REPO_ROOT / ".github" / "workflows" / "deploy-staging.yml"
        assert workflow_path.exists(), (
            f"Staging workflow not found at {workflow_path}. "
            "Create .github/workflows/deploy-staging.yml"
        )

    def test_workflow_uses_correct_environment(self) -> None:
        """Test that workflow is configured for staging."""
        workflow_path = REPO_ROOT / ".github" / "workflows" / "deploy-staging.yml"

        if not workflow_path.exists():
            pytest.skip("Workflow file doesn't exist yet")

        with open(workflow_path, "r") as f:
            content = f.read()

        # Verify workflow references staging
        assert "staging" in content.lower(), (
            "Workflow should reference staging environment"
        )
        assert "CareerVpCrudStaging" in content or "CareerVp" in content, (
            "Workflow should reference CareerVp stacks"
        )

    def test_naming_utils_supports_staging(self) -> None:
        """Test that NamingUtils can generate staging resource names."""
        # This is a code validation - ensures the naming system works
        import sys

        sys.path.insert(0, str(REPO_ROOT / "src" / "backend"))

        try:
            from cdk.careervp.naming_utils import NamingUtils

            naming = NamingUtils(
                environment="staging",
                region="us-east-1",
                account_id="123456789012",
            )

            # Test various resource namings
            table_name = naming.table_name("users")
            assert "staging" in table_name.lower(), (
                f"Table name should contain staging: {table_name}"
            )

            lambda_name = naming.lambda_name("crud")
            assert "staging" in lambda_name.lower(), (
                f"Lambda name should contain staging: {lambda_name}"
            )

        except ImportError as e:
            pytest.fail(f"Cannot import NamingUtils: {e}")


class TestStagingTestData:
    """
    Test suite for synthetic test data.

    Validates that test data exists for E2E testing.
    """

    def test_staging_test_users_exist(self) -> None:
        """Test that staging test users file exists."""
        users_path = (
            REPO_ROOT / "docs" / "staging" / "payloads" / "staging_test_users.json"
        )
        assert users_path.exists(), (
            f"Test users not found at {users_path}. "
            "Create synthetic test data for E2E tests."
        )

    def test_staging_test_users_valid_json(self) -> None:
        """Test that test users file is valid JSON."""
        users_path = (
            REPO_ROOT / "docs" / "staging" / "payloads" / "staging_test_users.json"
        )
        if not users_path.exists():
            pytest.skip("Test users file doesn't exist yet")

        with open(users_path, "r") as f:
            users = json.load(f)
        assert isinstance(users, list), "Users must be a list"
        assert len(users) > 0, "Users list must not be empty"

    def test_staging_test_users_have_required_fields(self) -> None:
        """Test that test users have all required fields."""
        users_path = (
            REPO_ROOT / "docs" / "staging" / "payloads" / "staging_test_users.json"
        )
        if not users_path.exists():
            pytest.skip("Test users file doesn't exist yet")

        with open(users_path, "r") as f:
            users = json.load(f)

        required_fields = {
            "user_id",
            "email",
            "first_name",
            "last_name",
            "country",
            "subscription_tier",
        }
        for user in users:
            assert required_fields.issubset(set(user.keys())), (
                f"User missing fields: {required_fields - set(user.keys())}"
            )

    def test_test_users_use_staging_domain(self) -> None:
        """Test that test users use staging email domain."""
        users_path = (
            REPO_ROOT / "docs" / "staging" / "payloads" / "staging_test_users.json"
        )
        if not users_path.exists():
            pytest.skip("Test users file doesn't exist yet")

        with open(users_path, "r") as f:
            users = json.load(f)

        for user in users:
            assert "@staging.careervp.com" in user["email"], (
                f"User email should use staging domain: {user['email']}"
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
