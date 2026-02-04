"""
Unit tests for VPR async deployment validation.

Tests cover:
- AWS resource naming conventions
- OIDC configuration validation
- Security group rules validation
- Environment variable configuration
- Lambda function configurations (timeout, memory, concurrency)
- DynamoDB table configurations
- S3 bucket configurations
"""

import pytest
import json
import re
from typing import Dict, List, Any
from unittest.mock import Mock, patch


class DeploymentValidator:
    """Validates VPR async infrastructure deployment."""

    # Resource naming patterns
    RESOURCE_PATTERNS = {
        "queue": r"^careervp-vpr-jobs-queue-(dev|staging|prod)$",
        "dlq": r"^careervp-vpr-jobs-dlq-(dev|staging|prod)$",
        "lambda_submit": r"^careervp-vpr-submit-lambda-(dev|staging|prod)$",
        "lambda_worker": r"^careervp-vpr-worker-lambda-(dev|staging|prod)$",
        "lambda_status": r"^careervp-vpr-status-lambda-(dev|staging|prod)$",
        "table": r"^careervp-vpr-jobs-(dev|staging|prod)$",
        "bucket": r"^careervp-vpr-results-(dev|staging|prod)$",
        "role": r"^careervp-vpr-(submit|worker|status)-role-(dev|staging|prod)$",
    }

    # Lambda configurations
    LAMBDA_CONFIGS = {
        "submit": {"timeout": 30, "memory": 256, "ephemeral_storage": 512},
        "worker": {
            "timeout": 900,  # 15 minutes
            "memory": 3008,
            "ephemeral_storage": 10240,  # 10 GB
        },
        "status": {"timeout": 30, "memory": 256, "ephemeral_storage": 512},
    }

    # Required environment variables per Lambda
    REQUIRED_ENV_VARS = {
        "submit": [
            "JOBS_TABLE_NAME",
            "VPR_JOBS_QUEUE_URL",
            "IDEMPOTENCY_KEY_EXPIRY_HOURS",
        ],
        "worker": [
            "JOBS_TABLE_NAME",
            "VPR_RESULTS_BUCKET",
            "CLAUDE_API_KEY",
            "ENABLE_CLAUDE_CACHING",
        ],
        "status": [
            "JOBS_TABLE_NAME",
            "VPR_RESULTS_BUCKET",
            "PRESIGNED_URL_EXPIRY_SECONDS",
        ],
    }

    def __init__(self, environment: str):
        """Initialize validator.

        Args:
            environment: Deployment environment (dev, staging, prod)
        """
        if environment not in ["dev", "staging", "prod"]:
            raise ValueError(f"Invalid environment: {environment}")
        self.environment = environment
        self.errors = []
        self.warnings = []

    def validate_resource_names(self, resources: Dict[str, str]) -> bool:
        """Validate resource naming conventions.

        Args:
            resources: Dict of resource_type -> name mappings

        Returns:
            True if all resources match naming conventions
        """
        for resource_type, name in resources.items():
            if resource_type not in self.RESOURCE_PATTERNS:
                self.warnings.append(f"Unknown resource type: {resource_type}")
                continue

            pattern = self.RESOURCE_PATTERNS[resource_type]
            if not re.match(pattern, name):
                self.errors.append(
                    f"Resource '{name}' does not match pattern for {resource_type}: {pattern}"
                )

        return len(self.errors) == 0

    def validate_lambda_config(self, lambda_name: str, config: Dict[str, Any]) -> bool:
        """Validate Lambda function configuration.

        Args:
            lambda_name: Lambda function name (submit, worker, status)
            config: Configuration dict with timeout, memory, env_vars

        Returns:
            True if configuration is valid
        """
        if lambda_name not in self.LAMBDA_CONFIGS:
            self.errors.append(f"Unknown Lambda function: {lambda_name}")
            return False

        expected = self.LAMBDA_CONFIGS[lambda_name]

        # Validate timeout
        if config.get("timeout") != expected["timeout"]:
            self.errors.append(
                f"{lambda_name}: timeout should be {expected['timeout']}s, "
                f"got {config.get('timeout')}s"
            )

        # Validate memory
        if config.get("memory") != expected["memory"]:
            self.errors.append(
                f"{lambda_name}: memory should be {expected['memory']}MB, "
                f"got {config.get('memory')}MB"
            )

        # Validate ephemeral storage
        if "ephemeral_storage" in expected:
            if config.get("ephemeral_storage") != expected["ephemeral_storage"]:
                self.warnings.append(
                    f"{lambda_name}: ephemeral_storage mismatch "
                    f"(expected {expected['ephemeral_storage']}, "
                    f"got {config.get('ephemeral_storage')})"
                )

        return len(self.errors) == 0

    def validate_lambda_environment_variables(
        self, lambda_name: str, env_vars: Dict[str, str]
    ) -> bool:
        """Validate Lambda environment variables.

        Args:
            lambda_name: Lambda function name
            env_vars: Environment variables dict

        Returns:
            True if all required variables present
        """
        if lambda_name not in self.REQUIRED_ENV_VARS:
            return True

        required = self.REQUIRED_ENV_VARS[lambda_name]
        missing = [var for var in required if var not in env_vars]

        if missing:
            self.errors.append(
                f"{lambda_name} Lambda missing environment variables: {', '.join(missing)}"
            )

        # Validate specific variable values
        if lambda_name == "worker":
            if "CLAUDE_API_KEY" in env_vars:
                if not env_vars["CLAUDE_API_KEY"]:
                    self.errors.append(f"{lambda_name}: CLAUDE_API_KEY is empty")

        return len(self.errors) == 0

    def validate_lambda_concurrency(
        self, lambda_name: str, reserved_concurrency: int
    ) -> bool:
        """Validate Lambda concurrency settings.

        Args:
            lambda_name: Lambda function name
            reserved_concurrency: Reserved concurrency value

        Returns:
            True if concurrency is valid
        """
        # Worker Lambda should have reserved concurrency
        if lambda_name == "worker":
            if reserved_concurrency <= 0:
                self.errors.append(
                    f"{lambda_name}: reserved_concurrency must be > 0, got {reserved_concurrency}"
                )
            elif reserved_concurrency > 10:
                self.warnings.append(
                    f"{lambda_name}: reserved_concurrency {reserved_concurrency} may be high"
                )

        return len(self.errors) == 0

    def validate_dynamodb_table(self, table_config: Dict[str, Any]) -> bool:
        """Validate DynamoDB table configuration.

        Args:
            table_config: Table configuration dict

        Returns:
            True if table configuration is valid
        """
        # Validate table name
        if not re.match(self.RESOURCE_PATTERNS["table"], table_config.get("name", "")):
            self.errors.append(
                f"Table name '{table_config.get('name')}' does not match pattern"
            )

        # Validate partition key
        if table_config.get("partition_key") != "job_id":
            self.errors.append(
                f"Table partition key should be 'job_id', got '{table_config.get('partition_key')}'"
            )

        # Validate GSI for idempotency key lookups
        gsi_names = [
            gsi.get("name") for gsi in table_config.get("global_secondary_indexes", [])
        ]
        if "idempotency-key-index" not in gsi_names:
            self.errors.append("Table missing GSI: idempotency-key-index")

        # Validate TTL attribute
        if table_config.get("ttl_attribute") != "ttl":
            self.warnings.append(
                f"Table TTL attribute should be 'ttl', got '{table_config.get('ttl_attribute')}'"
            )

        # Validate billing mode
        if self.environment == "prod":
            # Prod should use provisioned or on-demand with limits
            if table_config.get("billing_mode") not in [
                "PROVISIONED",
                "PAY_PER_REQUEST",
            ]:
                self.errors.append(
                    f"Table billing_mode should be PROVISIONED or PAY_PER_REQUEST, "
                    f"got {table_config.get('billing_mode')}"
                )

        return len(self.errors) == 0

    def validate_s3_bucket(self, bucket_config: Dict[str, Any]) -> bool:
        """Validate S3 bucket configuration.

        Args:
            bucket_config: Bucket configuration dict

        Returns:
            True if bucket configuration is valid
        """
        # Validate bucket name
        if not re.match(
            self.RESOURCE_PATTERNS["bucket"], bucket_config.get("name", "")
        ):
            self.errors.append(
                f"Bucket name '{bucket_config.get('name')}' does not match pattern"
            )

        # Validate public access block
        if not bucket_config.get("block_public_access"):
            self.errors.append("S3 bucket must have public access block enabled")

        # Validate versioning
        if bucket_config.get("versioning") != True:
            self.warnings.append("S3 bucket should have versioning enabled")

        # Validate encryption
        if not bucket_config.get("encryption"):
            self.errors.append("S3 bucket must have encryption enabled")

        # Validate lifecycle rules
        lifecycle_rules = bucket_config.get("lifecycle_rules", [])
        if not lifecycle_rules:
            self.warnings.append(
                "S3 bucket should have lifecycle rules (e.g., delete old results)"
            )
        else:
            # Check for result cleanup rule
            has_cleanup = any(
                rule.get("expiration_days", 0) <= 30 for rule in lifecycle_rules
            )
            if not has_cleanup:
                self.warnings.append(
                    "S3 bucket should have rule to delete results after ~24-30 days"
                )

        return len(self.errors) == 0

    def validate_sqs_configuration(self, queue_config: Dict[str, Any]) -> bool:
        """Validate SQS queue configuration.

        Args:
            queue_config: Queue configuration dict

        Returns:
            True if queue configuration is valid
        """
        # Validate queue name
        if not re.match(self.RESOURCE_PATTERNS["queue"], queue_config.get("name", "")):
            self.errors.append(
                f"Queue name '{queue_config.get('name')}' does not match pattern"
            )

        # Validate visibility timeout (should allow worker time)
        visibility = queue_config.get("visibility_timeout_seconds", 0)
        if visibility < 900:  # Should be at least 15 minutes
            self.errors.append(
                f"Queue visibility_timeout should be >= 900s (15 min), got {visibility}s"
            )

        # Validate message retention (should be at least 24 hours)
        retention = queue_config.get("message_retention_seconds", 0)
        if retention < 86400:  # 24 hours
            self.warnings.append(
                f"Queue message_retention should be >= 86400s (24h), got {retention}s"
            )

        # Validate DLQ configuration
        dlq_url = queue_config.get("dead_letter_queue_url")
        if not dlq_url:
            self.errors.append("Queue must have dead-letter queue configured")

        dlq_name = queue_config.get("dead_letter_queue_name")
        if dlq_name and not re.match(self.RESOURCE_PATTERNS["dlq"], dlq_name):
            self.errors.append(f"DLQ name '{dlq_name}' does not match pattern")

        return len(self.errors) == 0

    def validate_oidc_configuration(self, oidc_config: Dict[str, Any]) -> bool:
        """Validate OIDC configuration for GitHub Actions.

        Args:
            oidc_config: OIDC configuration dict

        Returns:
            True if OIDC configuration is valid
        """
        required_fields = ["provider_arn", "audience", "role_arn"]

        missing = [f for f in required_fields if f not in oidc_config]
        if missing:
            self.errors.append(
                f"OIDC configuration missing fields: {', '.join(missing)}"
            )

        # Validate ARN formats
        provider_arn = oidc_config.get("provider_arn", "")
        if provider_arn and not provider_arn.startswith("arn:aws:iam::"):
            self.errors.append(f"Invalid provider_arn format: {provider_arn}")

        role_arn = oidc_config.get("role_arn", "")
        if role_arn and not role_arn.startswith("arn:aws:iam::"):
            self.errors.append(f"Invalid role_arn format: {role_arn}")

        # Validate audience
        audience = oidc_config.get("audience", "")
        if audience and not audience.startswith("sts.amazonaws.com"):
            self.warnings.append(
                f"OIDC audience should typically be 'sts.amazonaws.com', got '{audience}'"
            )

        return len(self.errors) == 0

    def validate_security_group_rules(self, sg_config: Dict[str, Any]) -> bool:
        """Validate security group rules.

        Args:
            sg_config: Security group configuration dict

        Returns:
            True if rules are valid
        """
        # Lambda to SQS doesn't need explicit SG rules (same VPC)
        # Lambda to S3 doesn't need explicit SG rules (VPC endpoint or NAT)
        # Lambda to DynamoDB doesn't need explicit SG rules (managed service)

        # Check if restricted to VPC endpoints
        vpc_endpoint_sg = sg_config.get("restrict_to_vpc_endpoints")
        if not vpc_endpoint_sg:
            self.warnings.append(
                "SQS/S3/DynamoDB access should be restricted to VPC endpoints"
            )

        return len(self.errors) == 0

    def validate_cloudwatch_alarms(self, alarms: List[Dict[str, Any]]) -> bool:
        """Validate CloudWatch alarm configuration.

        Args:
            alarms: List of alarm configuration dicts

        Returns:
            True if alarms are properly configured
        """
        required_alarms = [
            "dlq-messages",
            "worker-errors",
            "worker-timeout",
            "queue-depth",
            "lambda-throttles",
        ]

        alarm_names = [a.get("name", "") for a in alarms]
        missing = [
            a for a in required_alarms if not any(a in name for name in alarm_names)
        ]

        if missing:
            self.warnings.append(
                f"Missing recommended CloudWatch alarms: {', '.join(missing)}"
            )

        # Validate alarm thresholds
        for alarm in alarms:
            if "dlq-messages" in alarm.get("name", ""):
                if alarm.get("threshold") != 1:
                    self.errors.append(
                        f"DLQ alarm threshold should be 1, got {alarm.get('threshold')}"
                    )

        return len(self.errors) == 0

    def validate_iam_permissions(self, role_config: Dict[str, Any]) -> bool:
        """Validate IAM role permissions.

        Args:
            role_config: Role configuration dict

        Returns:
            True if permissions are correctly configured
        """
        policies = role_config.get("policies", [])

        # Check for least privilege
        for policy in policies:
            actions = policy.get("actions", [])
            if "*" in actions:
                self.warnings.append(f"Role has wildcard actions: consider restricting")

        return True

    def validate_all(self, deployment_config: Dict[str, Any]) -> tuple:
        """Run all validation checks.

        Args:
            deployment_config: Complete deployment configuration

        Returns:
            Tuple of (is_valid, errors, warnings)
        """
        self.errors = []
        self.warnings = []

        # Validate each component
        if "resources" in deployment_config:
            self.validate_resource_names(deployment_config["resources"])

        if "lambdas" in deployment_config:
            for name, config in deployment_config["lambdas"].items():
                self.validate_lambda_config(name, config)
                self.validate_lambda_environment_variables(
                    name, config.get("environment", {})
                )
                if "reserved_concurrency" in config:
                    self.validate_lambda_concurrency(
                        name, config["reserved_concurrency"]
                    )

        if "dynamodb" in deployment_config:
            self.validate_dynamodb_table(deployment_config["dynamodb"])

        if "s3" in deployment_config:
            self.validate_s3_bucket(deployment_config["s3"])

        if "sqs" in deployment_config:
            self.validate_sqs_configuration(deployment_config["sqs"])

        if "oidc" in deployment_config:
            self.validate_oidc_configuration(deployment_config["oidc"])

        if "security_groups" in deployment_config:
            self.validate_security_group_rules(deployment_config["security_groups"])

        if "cloudwatch_alarms" in deployment_config:
            self.validate_cloudwatch_alarms(deployment_config["cloudwatch_alarms"])

        if "iam_roles" in deployment_config:
            self.validate_iam_permissions(deployment_config["iam_roles"])

        is_valid = len(self.errors) == 0
        return is_valid, self.errors, self.warnings


class TestResourceNamingValidation:
    """Test resource naming convention validation."""

    def test_valid_queue_names(self):
        """Test validation of valid SQS queue names."""
        validator = DeploymentValidator("dev")

        valid_names = {
            "queue": "careervp-vpr-jobs-queue-dev",
            "queue": "careervp-vpr-jobs-queue-staging",
            "queue": "careervp-vpr-jobs-queue-prod",
        }

        assert validator.validate_resource_names(valid_names)

    def test_invalid_queue_names(self):
        """Test detection of invalid queue names."""
        validator = DeploymentValidator("dev")

        invalid_names = {
            "queue": "vpr-jobs-queue",  # Missing prefix
            "queue": "careervp-vpr-jobs-queue",  # Missing environment
            "queue": "careervp-vpr-jobs-queue-staging",  # Wrong environment
        }

        assert not validator.validate_resource_names(invalid_names)
        assert len(validator.errors) > 0

    def test_valid_lambda_names(self):
        """Test validation of Lambda function names."""
        validator = DeploymentValidator("prod")

        valid_names = {
            "lambda_submit": "careervp-vpr-submit-lambda-prod",
            "lambda_worker": "careervp-vpr-worker-lambda-prod",
            "lambda_status": "careervp-vpr-status-lambda-prod",
        }

        assert validator.validate_resource_names(valid_names)

    def test_invalid_lambda_names(self):
        """Test detection of invalid Lambda names."""
        validator = DeploymentValidator("dev")

        invalid_names = {
            "lambda_submit": "careervp-vpr-submit-dev",  # Missing -lambda-
            "lambda_worker": "vpr-worker-lambda-dev",  # Missing prefix
        }

        assert not validator.validate_resource_names(invalid_names)

    def test_valid_dynamodb_table_names(self):
        """Test validation of DynamoDB table names."""
        validator = DeploymentValidator("staging")

        valid_names = {"table": "careervp-vpr-jobs-staging"}

        assert validator.validate_resource_names(valid_names)

    def test_valid_s3_bucket_names(self):
        """Test validation of S3 bucket names."""
        validator = DeploymentValidator("prod")

        valid_names = {"bucket": "careervp-vpr-results-prod"}

        assert validator.validate_resource_names(valid_names)


class TestLambdaConfigValidation:
    """Test Lambda function configuration validation."""

    def test_valid_submit_lambda_config(self):
        """Test valid submit Lambda configuration."""
        validator = DeploymentValidator("dev")

        config = {"timeout": 30, "memory": 256, "ephemeral_storage": 512}

        assert validator.validate_lambda_config("submit", config)

    def test_invalid_submit_lambda_timeout(self):
        """Test detection of invalid timeout."""
        validator = DeploymentValidator("dev")

        config = {
            "timeout": 60,  # Should be 30
            "memory": 256,
            "ephemeral_storage": 512,
        }

        assert not validator.validate_lambda_config("submit", config)
        assert any("timeout" in e for e in validator.errors)

    def test_valid_worker_lambda_config(self):
        """Test valid worker Lambda configuration."""
        validator = DeploymentValidator("dev")

        config = {"timeout": 900, "memory": 3008, "ephemeral_storage": 10240}

        assert validator.validate_lambda_config("worker", config)

    def test_valid_status_lambda_config(self):
        """Test valid status Lambda configuration."""
        validator = DeploymentValidator("dev")

        config = {"timeout": 30, "memory": 256, "ephemeral_storage": 512}

        assert validator.validate_lambda_config("status", config)


class TestEnvironmentVariableValidation:
    """Test Lambda environment variable validation."""

    def test_submit_lambda_required_vars(self):
        """Test submit Lambda has required environment variables."""
        validator = DeploymentValidator("dev")

        env_vars = {
            "JOBS_TABLE_NAME": "careervp-vpr-jobs-dev",
            "VPR_JOBS_QUEUE_URL": "https://sqs.us-east-1.amazonaws.com/123/queue",
            "IDEMPOTENCY_KEY_EXPIRY_HOURS": "24",
        }

        assert validator.validate_lambda_environment_variables("submit", env_vars)

    def test_submit_lambda_missing_vars(self):
        """Test detection of missing environment variables."""
        validator = DeploymentValidator("dev")

        env_vars = {
            "JOBS_TABLE_NAME": "careervp-vpr-jobs-dev"
            # Missing VPR_JOBS_QUEUE_URL and IDEMPOTENCY_KEY_EXPIRY_HOURS
        }

        assert not validator.validate_lambda_environment_variables("submit", env_vars)
        assert len(validator.errors) > 0

    def test_worker_lambda_required_vars(self):
        """Test worker Lambda has required environment variables."""
        validator = DeploymentValidator("dev")

        env_vars = {
            "JOBS_TABLE_NAME": "careervp-vpr-jobs-dev",
            "VPR_RESULTS_BUCKET": "careervp-vpr-results-dev",
            "CLAUDE_API_KEY": "sk-ant-xxx",
            "ENABLE_CLAUDE_CACHING": "true",
        }

        assert validator.validate_lambda_environment_variables("worker", env_vars)

    def test_worker_lambda_empty_api_key(self):
        """Test detection of empty Claude API key."""
        validator = DeploymentValidator("dev")

        env_vars = {
            "JOBS_TABLE_NAME": "careervp-vpr-jobs-dev",
            "VPR_RESULTS_BUCKET": "careervp-vpr-results-dev",
            "CLAUDE_API_KEY": "",
            "ENABLE_CLAUDE_CACHING": "true",
        }

        assert not validator.validate_lambda_environment_variables("worker", env_vars)
        assert any("CLAUDE_API_KEY" in e and "empty" in e for e in validator.errors)

    def test_status_lambda_required_vars(self):
        """Test status Lambda has required environment variables."""
        validator = DeploymentValidator("dev")

        env_vars = {
            "JOBS_TABLE_NAME": "careervp-vpr-jobs-dev",
            "VPR_RESULTS_BUCKET": "careervp-vpr-results-dev",
            "PRESIGNED_URL_EXPIRY_SECONDS": "3600",
        }

        assert validator.validate_lambda_environment_variables("status", env_vars)


class TestDynamoDBValidation:
    """Test DynamoDB table configuration validation."""

    def test_valid_jobs_table(self):
        """Test valid jobs table configuration."""
        validator = DeploymentValidator("dev")

        config = {
            "name": "careervp-vpr-jobs-dev",
            "partition_key": "job_id",
            "global_secondary_indexes": [{"name": "idempotency-key-index"}],
            "ttl_attribute": "ttl",
            "billing_mode": "PAY_PER_REQUEST",
        }

        assert validator.validate_dynamodb_table(config)

    def test_invalid_partition_key(self):
        """Test detection of invalid partition key."""
        validator = DeploymentValidator("dev")

        config = {
            "name": "careervp-vpr-jobs-dev",
            "partition_key": "id",  # Should be job_id
            "global_secondary_indexes": [{"name": "idempotency-key-index"}],
            "ttl_attribute": "ttl",
            "billing_mode": "PAY_PER_REQUEST",
        }

        assert not validator.validate_dynamodb_table(config)

    def test_missing_gsi(self):
        """Test detection of missing GSI."""
        validator = DeploymentValidator("dev")

        config = {
            "name": "careervp-vpr-jobs-dev",
            "partition_key": "job_id",
            "global_secondary_indexes": [],  # Missing idempotency-key-index
            "ttl_attribute": "ttl",
            "billing_mode": "PAY_PER_REQUEST",
        }

        assert not validator.validate_dynamodb_table(config)


class TestS3BucketValidation:
    """Test S3 bucket configuration validation."""

    def test_valid_results_bucket(self):
        """Test valid S3 bucket configuration."""
        validator = DeploymentValidator("dev")

        config = {
            "name": "careervp-vpr-results-dev",
            "block_public_access": True,
            "versioning": True,
            "encryption": True,
            "lifecycle_rules": [{"expiration_days": 30}],
        }

        assert validator.validate_s3_bucket(config)

    def test_missing_public_access_block(self):
        """Test detection of missing public access block."""
        validator = DeploymentValidator("dev")

        config = {
            "name": "careervp-vpr-results-dev",
            "block_public_access": False,  # Should be True
            "versioning": True,
            "encryption": True,
            "lifecycle_rules": [{"expiration_days": 30}],
        }

        assert not validator.validate_s3_bucket(config)

    def test_missing_encryption(self):
        """Test detection of missing encryption."""
        validator = DeploymentValidator("dev")

        config = {
            "name": "careervp-vpr-results-dev",
            "block_public_access": True,
            "versioning": True,
            "encryption": False,  # Should be True
            "lifecycle_rules": [{"expiration_days": 30}],
        }

        assert not validator.validate_s3_bucket(config)


class TestSQSValidation:
    """Test SQS queue configuration validation."""

    def test_valid_queue_configuration(self):
        """Test valid SQS queue configuration."""
        validator = DeploymentValidator("dev")

        config = {
            "name": "careervp-vpr-jobs-queue-dev",
            "visibility_timeout_seconds": 900,
            "message_retention_seconds": 86400,
            "dead_letter_queue_url": "https://sqs.us-east-1.amazonaws.com/123/dlq",
            "dead_letter_queue_name": "careervp-vpr-jobs-dlq-dev",
        }

        assert validator.validate_sqs_configuration(config)

    def test_insufficient_visibility_timeout(self):
        """Test detection of insufficient visibility timeout."""
        validator = DeploymentValidator("dev")

        config = {
            "name": "careervp-vpr-jobs-queue-dev",
            "visibility_timeout_seconds": 300,  # Should be >= 900
            "message_retention_seconds": 86400,
            "dead_letter_queue_url": "https://sqs.us-east-1.amazonaws.com/123/dlq",
            "dead_letter_queue_name": "careervp-vpr-jobs-dlq-dev",
        }

        assert not validator.validate_sqs_configuration(config)

    def test_missing_dlq(self):
        """Test detection of missing DLQ."""
        validator = DeploymentValidator("dev")

        config = {
            "name": "careervp-vpr-jobs-queue-dev",
            "visibility_timeout_seconds": 900,
            "message_retention_seconds": 86400,
            "dead_letter_queue_url": None,  # Should have DLQ
            "dead_letter_queue_name": None,
        }

        assert not validator.validate_sqs_configuration(config)


class TestOIDCValidation:
    """Test OIDC configuration validation."""

    def test_valid_oidc_config(self):
        """Test valid OIDC configuration for GitHub Actions."""
        validator = DeploymentValidator("dev")

        config = {
            "provider_arn": "arn:aws:iam::123456789012:oidc-provider/token.actions.githubusercontent.com",
            "audience": "sts.amazonaws.com",
            "role_arn": "arn:aws:iam::123456789012:role/github-actions-role",
        }

        assert validator.validate_oidc_configuration(config)

    def test_missing_required_fields(self):
        """Test detection of missing OIDC fields."""
        validator = DeploymentValidator("dev")

        config = {
            "provider_arn": "arn:aws:iam::123456789012:oidc-provider/token.actions.githubusercontent.com"
            # Missing audience and role_arn
        }

        assert not validator.validate_oidc_configuration(config)

    def test_invalid_arn_format(self):
        """Test detection of invalid ARN format."""
        validator = DeploymentValidator("dev")

        config = {
            "provider_arn": "invalid-arn",  # Should start with arn:aws:iam::
            "audience": "sts.amazonaws.com",
            "role_arn": "arn:aws:iam::123456789012:role/github-actions-role",
        }

        assert not validator.validate_oidc_configuration(config)


class TestLambdaConcurrencyValidation:
    """Test Lambda concurrency settings."""

    def test_worker_lambda_reserved_concurrency(self):
        """Test worker Lambda has reserved concurrency."""
        validator = DeploymentValidator("dev")

        assert validator.validate_lambda_concurrency("worker", 5)

    def test_worker_lambda_zero_concurrency(self):
        """Test detection of zero reserved concurrency."""
        validator = DeploymentValidator("dev")

        assert not validator.validate_lambda_concurrency("worker", 0)

    def test_worker_lambda_high_concurrency(self):
        """Test warning for high reserved concurrency."""
        validator = DeploymentValidator("dev")

        assert validator.validate_lambda_concurrency("worker", 20)
        assert len(validator.warnings) > 0


class TestCloudWatchAlarmValidation:
    """Test CloudWatch alarm configuration."""

    def test_valid_alarms(self):
        """Test valid alarm configuration."""
        validator = DeploymentValidator("dev")

        alarms = [
            {"name": "careervp-vpr-dlq-alarm", "threshold": 1},
            {"name": "careervp-vpr-worker-errors", "threshold": 5},
            {"name": "careervp-vpr-worker-timeout", "threshold": 1},
            {"name": "careervp-vpr-queue-depth", "threshold": 50},
            {"name": "careervp-vpr-lambda-throttles", "threshold": 1},
        ]

        assert validator.validate_cloudwatch_alarms(alarms)

    def test_invalid_dlq_threshold(self):
        """Test detection of invalid DLQ threshold."""
        validator = DeploymentValidator("dev")

        alarms = [
            {"name": "careervp-vpr-dlq-alarm", "threshold": 5}  # Should be 1
        ]

        assert not validator.validate_cloudwatch_alarms(alarms)


class TestFullDeploymentValidation:
    """Test complete deployment validation."""

    def test_valid_deployment_config(self):
        """Test validation of complete valid deployment."""
        validator = DeploymentValidator("dev")

        config = {
            "resources": {
                "queue": "careervp-vpr-jobs-queue-dev",
                "dlq": "careervp-vpr-jobs-dlq-dev",
                "lambda_submit": "careervp-vpr-submit-lambda-dev",
                "lambda_worker": "careervp-vpr-worker-lambda-dev",
                "lambda_status": "careervp-vpr-status-lambda-dev",
                "table": "careervp-vpr-jobs-dev",
                "bucket": "careervp-vpr-results-dev",
            },
            "lambdas": {
                "submit": {
                    "timeout": 30,
                    "memory": 256,
                    "ephemeral_storage": 512,
                    "environment": {
                        "JOBS_TABLE_NAME": "careervp-vpr-jobs-dev",
                        "VPR_JOBS_QUEUE_URL": "https://sqs.us-east-1.amazonaws.com/123/queue",
                        "IDEMPOTENCY_KEY_EXPIRY_HOURS": "24",
                    },
                },
                "worker": {
                    "timeout": 900,
                    "memory": 3008,
                    "ephemeral_storage": 10240,
                    "reserved_concurrency": 5,
                    "environment": {
                        "JOBS_TABLE_NAME": "careervp-vpr-jobs-dev",
                        "VPR_RESULTS_BUCKET": "careervp-vpr-results-dev",
                        "CLAUDE_API_KEY": "sk-ant-xxx",
                        "ENABLE_CLAUDE_CACHING": "true",
                    },
                },
                "status": {
                    "timeout": 30,
                    "memory": 256,
                    "ephemeral_storage": 512,
                    "environment": {
                        "JOBS_TABLE_NAME": "careervp-vpr-jobs-dev",
                        "VPR_RESULTS_BUCKET": "careervp-vpr-results-dev",
                        "PRESIGNED_URL_EXPIRY_SECONDS": "3600",
                    },
                },
            },
            "dynamodb": {
                "name": "careervp-vpr-jobs-dev",
                "partition_key": "job_id",
                "global_secondary_indexes": [{"name": "idempotency-key-index"}],
                "ttl_attribute": "ttl",
                "billing_mode": "PAY_PER_REQUEST",
            },
            "s3": {
                "name": "careervp-vpr-results-dev",
                "block_public_access": True,
                "versioning": True,
                "encryption": True,
                "lifecycle_rules": [{"expiration_days": 30}],
            },
            "sqs": {
                "name": "careervp-vpr-jobs-queue-dev",
                "visibility_timeout_seconds": 900,
                "message_retention_seconds": 86400,
                "dead_letter_queue_url": "https://sqs.us-east-1.amazonaws.com/123/dlq",
                "dead_letter_queue_name": "careervp-vpr-jobs-dlq-dev",
            },
            "oidc": {
                "provider_arn": "arn:aws:iam::123456789012:oidc-provider/token.actions.githubusercontent.com",
                "audience": "sts.amazonaws.com",
                "role_arn": "arn:aws:iam::123456789012:role/github-actions-role",
            },
            "cloudwatch_alarms": [
                {"name": "careervp-vpr-dlq-alarm", "threshold": 1},
                {"name": "careervp-vpr-worker-errors", "threshold": 5},
            ],
        }

        is_valid, errors, warnings = validator.validate_all(config)

        assert is_valid
        assert len(errors) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
