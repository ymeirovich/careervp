"""
CareerVP Backend Constants.

Centralized constants for backend logic modules. These MUST stay in sync with
infra/careervp/constants.py to prevent "String Mismatch" errors between
CDK-provisioned resources and runtime code.

Usage:
    from careervp.logic.utils.constants import USERS_TABLE_NAME, CV_BUCKET_NAME
"""

from __future__ import annotations

import os
import re
from typing import Final

# =============================================================================
# ENVIRONMENT
# =============================================================================
# Environment is determined at runtime from Lambda environment variables
# Defaults to 'dev' for local development


def _slugify(value: str) -> str:
    sanitized = re.sub(r'[^a-z0-9-]+', '-', value.lower()).strip('-')
    sanitized = re.sub(r'-{2,}', '-', sanitized)
    if not sanitized:
        raise ValueError('Value must include alphanumeric characters.')
    return sanitized


def _normalize_environment(value: str) -> str:
    slug = _slugify(value)
    if slug in {'production', 'prod'}:
        return 'prod'
    if slug in {'development', 'dev'}:
        return 'dev'
    return slug


ENVIRONMENT: Final[str] = _normalize_environment(os.environ.get('ENVIRONMENT', 'dev'))

# =============================================================================
# SERVICE IDENTITY
# =============================================================================
SERVICE_NAME: Final[str] = 'CareerVP'
SERVICE_PREFIX: Final[str] = 'careervp'


def get_resource_name(
    feature: str,
    resource_type: str,
    environment: str | None = None,
) -> str:
    """
    Build a careervp-{feature}-{resource_type}-{env} physical resource name.

    Args:
        feature: Semantic feature or domain identifier (e.g., 'users', 'cv-parser')
        resource_type: Resource type (lambda, table, role, etc.)
        environment: Optional environment override.
    """
    env_value = _normalize_environment(environment or ENVIRONMENT)
    return f'{SERVICE_PREFIX}-{_slugify(feature)}-{_slugify(resource_type)}-{env_value}'


def get_table_name(feature: str) -> str:
    """
    Generate a table name following the naming convention.

    Args:
        feature: The feature identifier (e.g., 'users', 'sessions')

    Returns:
        Table name in format: careervp-{feature}-table-{env}
    """
    return get_resource_name(feature, 'table')


def get_bucket_name(purpose: str, region_code: str = 'local', suffix: str = 'dev') -> str:
    """
    Generate a bucket name following the naming convention.

    Args:
        purpose: The bucket purpose (e.g., 'cvs', 'outputs')
        region_code: Short region code for uniqueness (default: local)
        suffix: Hash or differentiator suffix (default: dev)

    Returns:
        Bucket name in format: careervp-{env}-{purpose}-{region_code}-{hash}
    """
    return f'{SERVICE_PREFIX}-{ENVIRONMENT}-{_slugify(purpose)}-{_slugify(region_code)}-{_slugify(suffix)}'


def get_lambda_name(feature: str) -> str:
    """
    Generate a Lambda function name following the naming convention.

    Args:
        feature: The feature identifier (e.g., 'cv-parser', 'vpr-generator')

    Returns:
        Lambda name in format: careervp-{feature}-lambda-{env}
    """
    return get_resource_name(feature, 'lambda')


# =============================================================================
# DYNAMODB TABLES
# =============================================================================
# Table names follow the pattern: careervp-{feature}-table-{env}
# These are resolved at runtime using environment variables set by CDK
# Fallback values match the naming convention for local development

USERS_TABLE_NAME: Final[str] = os.environ.get(
    'USERS_TABLE_NAME',
    get_table_name('users'),
)

SESSIONS_TABLE_NAME: Final[str] = os.environ.get(
    'SESSIONS_TABLE_NAME',
    get_table_name('sessions'),
)

JOBS_TABLE_NAME: Final[str] = os.environ.get(
    'JOBS_TABLE_NAME',
    get_table_name('jobs'),
)

IDEMPOTENCY_TABLE_NAME: Final[str] = os.environ.get(
    'IDEMPOTENCY_TABLE_NAME',
    get_table_name('idempotency'),
)

# =============================================================================
# S3 BUCKETS
# =============================================================================
# Bucket names follow the pattern: careervp-{env}-{purpose}-{region}-{hash}
# These are resolved at runtime using environment variables set by CDK

CV_BUCKET_NAME: Final[str] = os.environ.get(
    'CV_BUCKET_NAME',
    get_bucket_name('cvs'),
)

OUTPUTS_BUCKET_NAME: Final[str] = os.environ.get(
    'OUTPUTS_BUCKET_NAME',
    get_bucket_name('outputs'),
)

# =============================================================================
# API GATEWAY RESOURCES
# =============================================================================
GW_RESOURCE_CV: Final[str] = 'cv'
GW_RESOURCE_VPR: Final[str] = 'vpr'
GW_RESOURCE_USERS: Final[str] = 'users'

# =============================================================================
# LAMBDA FUNCTION NAMES
# =============================================================================
# Function names follow the pattern: careervp-{feature}-lambda-{env}
CV_PARSER_LAMBDA: Final[str] = os.environ.get(
    'CV_PARSER_LAMBDA',
    get_lambda_name('cv-parser'),
)
VPR_GENERATOR_LAMBDA: Final[str] = os.environ.get(
    'VPR_GENERATOR_LAMBDA',
    get_lambda_name('vpr-generator'),
)
CV_TAILOR_LAMBDA: Final[str] = os.environ.get(
    'CV_TAILOR_LAMBDA',
    get_lambda_name('cv-tailor'),
)
COVER_LETTER_LAMBDA: Final[str] = os.environ.get(
    'COVER_LETTER_LAMBDA',
    get_lambda_name('cover-letter'),
)

# =============================================================================
# OBSERVABILITY
# =============================================================================
METRICS_NAMESPACE: Final[str] = 'careervp_kpi'
METRICS_DIMENSION_KEY: Final[str] = 'service'

# =============================================================================
# APP CONFIG (Feature Flags)
# =============================================================================
CONFIGURATION_NAME: Final[str] = 'careervp_config'
CONFIGURATION_MAX_AGE_MINUTES: Final[str] = '5'

# =============================================================================
# LLM CONFIGURATION
# =============================================================================
# Model identifiers for LLM routing
LLM_MODEL_SONNET: Final[str] = 'claude-sonnet-4-20250514'
LLM_MODEL_HAIKU: Final[str] = 'claude-3-5-haiku-20241022'

# Default model for VPR generation (uses Sonnet for quality)
DEFAULT_VPR_MODEL: Final[str] = LLM_MODEL_SONNET

# Default model for CV parsing (uses Haiku for speed)
DEFAULT_CV_PARSER_MODEL: Final[str] = LLM_MODEL_HAIKU
