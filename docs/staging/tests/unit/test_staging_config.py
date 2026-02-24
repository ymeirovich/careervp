"""
Unit tests for Staging Configuration

These tests validate the staging configuration files and ensure they
follow the same structure as the dev configuration.

Run with:
    pytest docs/staging/tests/unit/test_staging_config.py -v
"""

import json
import os
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


class TestStagingConfiguration:
    """Test suite for staging configuration validation."""

    def test_staging_config_exists(self) -> None:
        """Test that staging configuration file exists."""
        assert STAGING_CONFIG_PATH.exists(), (
            f"Staging config not found at {STAGING_CONFIG_PATH}"
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


class TestStagingEnvironmentVariables:
    """Test suite for staging environment variable handling."""

    def test_environment_variable_defaults_to_dev(self) -> None:
        """Test that default environment is dev when not set."""
        env = os.environ.get("ENVIRONMENT", "dev")
        assert env == "dev", "Default environment should be dev"

    def test_staging_environment_can_be_set(self) -> None:
        """Test that staging environment can be set via env var."""
        os.environ["ENVIRONMENT"] = "staging"
        try:
            from cdk.careervp.naming_utils import NamingUtils

            naming = NamingUtils(environment="staging")
            assert naming.environment == "staging"
        finally:
            os.environ.pop("ENVIRONMENT", None)


class TestStagingNaming:
    """Test suite for staging resource naming."""

    def test_naming_utils_creates_staging_resources(self) -> None:
        """Test that NamingUtils creates resources with staging suffix."""
        os.environ["ENVIRONMENT"] = "staging"
        try:
            from cdk.careervp.naming_utils import NamingUtils

            naming = NamingUtils(
                environment="staging", region="us-east-1", account_id="123456789012"
            )

            # Test table naming
            table_name = naming.table_name("users")
            assert table_name.endswith("-staging"), (
                f"Table name should end with -staging: {table_name}"
            )

            # Test lambda naming
            lambda_name = naming.lambda_name("crud")
            assert lambda_name.endswith("-staging"), (
                f"Lambda name should end with -staging: {lambda_name}"
            )

            # Test stack ID
            stack_id = naming.stack_id("crud")
            assert "Staging" in stack_id, f"Stack ID should contain Staging: {stack_id}"
        finally:
            os.environ.pop("ENVIRONMENT", None)

    def test_staging_bucket_naming(self) -> None:
        """Test that staging buckets are named correctly."""
        os.environ["ENVIRONMENT"] = "staging"
        try:
            from cdk.careervp.naming_utils import NamingUtils

            naming = NamingUtils(
                environment="staging", region="us-east-1", account_id="123456789012"
            )

            bucket_name = naming.bucket_name("cvs")
            assert "staging" in bucket_name, (
                f"Bucket name should contain staging: {bucket_name}"
            )
        finally:
            os.environ.pop("ENVIRONMENT", None)


class TestSyntheticData:
    """Test suite for synthetic test data."""

    def test_staging_test_users_exist(self) -> None:
        """Test that staging test users file exists."""
        users_path = (
            REPO_ROOT / "docs" / "staging" / "payloads" / "staging_test_users.json"
        )
        assert users_path.exists(), f"Test users not found at {users_path}"

    def test_staging_test_users_valid_json(self) -> None:
        """Test that test users file is valid JSON."""
        users_path = (
            REPO_ROOT / "docs" / "staging" / "payloads" / "staging_test_users.json"
        )
        with open(users_path, "r") as f:
            users = json.load(f)
        assert isinstance(users, list), "Users must be a list"
        assert len(users) > 0, "Users list must not be empty"

    def test_staging_test_users_have_required_fields(self) -> None:
        """Test that test users have all required fields."""
        users_path = (
            REPO_ROOT / "docs" / "staging" / "payloads" / "staging_test_users.json"
        )
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

    def test_staging_test_jobs_exist(self) -> None:
        """Test that staging test jobs file exists."""
        jobs_path = (
            REPO_ROOT / "docs" / "staging" / "payloads" / "staging_test_jobs.json"
        )
        assert jobs_path.exists(), f"Test jobs not found at {jobs_path}"

    def test_staging_test_jobs_valid_json(self) -> None:
        """Test that test jobs file is valid JSON."""
        jobs_path = (
            REPO_ROOT / "docs" / "staging" / "payloads" / "staging_test_jobs.json"
        )
        with open(jobs_path, "r") as f:
            jobs = json.load(f)
        assert isinstance(jobs, list), "Jobs must be a list"
        assert len(jobs) > 0, "Jobs list must not be empty"

    def test_staging_test_jobs_have_required_fields(self) -> None:
        """Test that test jobs have all required fields."""
        jobs_path = (
            REPO_ROOT / "docs" / "staging" / "payloads" / "staging_test_jobs.json"
        )
        with open(jobs_path, "r") as f:
            jobs = json.load(f)

        required_fields = {
            "job_id",
            "title",
            "company",
            "country",
            "job_type",
            "experience_level",
        }
        for job in jobs:
            assert required_fields.issubset(set(job.keys())), (
                f"Job missing fields: {required_fields - set(job.keys())}"
            )

    def test_test_users_use_staging_domain(self) -> None:
        """Test that test users use staging email domain."""
        users_path = (
            REPO_ROOT / "docs" / "staging" / "payloads" / "staging_test_users.json"
        )
        with open(users_path, "r") as f:
            users = json.load(f)

        for user in users:
            assert "@staging.careervp.com" in user["email"], (
                f"User email should use staging domain: {user['email']}"
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
