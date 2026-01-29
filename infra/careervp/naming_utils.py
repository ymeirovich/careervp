"""Utility helpers for generating deterministic CareerVP resource names."""

from __future__ import annotations

import hashlib
import os
import re
from dataclasses import dataclass

from careervp import constants

_ENV_ALIAS = {
    "prod": "prod",
    "production": "prod",
    "dev": "dev",
    "development": "dev",
    "staging": "staging",
}

_REGION_CODE_MAP = {
    "us-east-1": "use1",
    "us-east-2": "use2",
    "us-west-1": "usw1",
    "us-west-2": "usw2",
    "ca-central-1": "cac1",
    "eu-central-1": "euc1",
    "eu-west-1": "euw1",
    "eu-west-2": "euw2",
    "eu-west-3": "euw3",
    "eu-north-1": "eun1",
    "eu-south-1": "eus1",
    "sa-east-1": "sae1",
    "ap-east-1": "ape1",
    "ap-south-1": "aps1",
    "ap-south-2": "aps2",
    "ap-southeast-1": "apse1",
    "ap-southeast-2": "apse2",
    "ap-southeast-3": "apse3",
    "ap-southeast-4": "apse4",
    "ap-northeast-1": "apne1",
    "ap-northeast-2": "apne2",
    "ap-northeast-3": "apne3",
    "af-south-1": "afs1",
    "me-south-1": "mes1",
    "me-central-1": "mec1",
}


def _slug(value: str) -> str:
    sanitized = re.sub(r"[^a-z0-9-]+", "-", value.lower()).strip("-")
    sanitized = re.sub(r"-{2,}", "-", sanitized)
    if not sanitized:
        raise ValueError("Value must contain alphanumeric characters.")
    return sanitized


def _normalize_environment(value: str) -> str:
    slug = _slug(value)
    return _ENV_ALIAS.get(slug, slug)


def _pascal(value: str) -> str:
    parts = re.split(r"[-_\s]+", value)
    return "".join(part.capitalize() for part in parts if part)


@dataclass
class NamingUtils:
    """Centralized helper for generating AWS physical names."""

    environment: str = constants.ENVIRONMENT
    prefix: str = constants.SERVICE_PREFIX
    region: str | None = None
    account_id: str | None = None

    def __post_init__(self) -> None:
        self.environment = _normalize_environment(self.environment)
        self.region = (
            self.region
            or os.getenv("CDK_DEFAULT_REGION")
            or os.getenv("AWS_DEFAULT_REGION")
            or "us-east-1"
        ).lower()
        self.account_id = (
            self.account_id or os.getenv("CDK_DEFAULT_ACCOUNT") or "000000000000"
        )

    def resource_name(self, feature: str, resource_type: str) -> str:
        """Generic resource name formatter."""
        return (
            f"{self.prefix}-{_slug(feature)}-{_slug(resource_type)}-{self.environment}"
        )

    def lambda_name(self, feature: str) -> str:
        return self.resource_name(feature, "lambda")

    def table_name(self, feature: str) -> str:
        return self.resource_name(feature, "table")

    def api_name(self, feature: str) -> str:
        return self.resource_name(feature, "api")

    def topic_name(self, feature: str) -> str:
        return self.resource_name(feature, "topic")

    def queue_name(self, feature: str) -> str:
        return self.resource_name(feature, "queue")

    def bus_name(self, feature: str) -> str:
        return self.resource_name(feature, "bus")

    def role_name(self, service: str, feature: str) -> str:
        return (
            f"{self.prefix}-role-{_slug(service)}-{_slug(feature)}-{self.environment}"
        )

    def stack_id(self, feature: str) -> str:
        return f"CareerVp{_pascal(feature)}{_pascal(self.environment)}"

    def bucket_name(self, purpose: str, hash_override: str | None = None) -> str:
        suffix = self._bucket_suffix(hash_override)
        return f"{self.prefix}-{self.environment}-{_slug(purpose)}-{self._region_code()}-{suffix}"

    def _bucket_suffix(self, hash_override: str | None) -> str:
        if hash_override:
            return _slug(hash_override)[:6]
        hasher = hashlib.sha256()
        hasher.update(
            f"{self.account_id}-{self.region}-{self.environment}".encode("utf-8")
        )
        return hasher.hexdigest()[:6]

    def _region_code(self) -> str:
        region_key = (self.region or "").lower()
        if region_key in _REGION_CODE_MAP:
            return _REGION_CODE_MAP[region_key]
        compact = region_key.replace("-", "")
        if len(compact) >= 4:
            return compact[:4]
        return compact.ljust(4, "0")
