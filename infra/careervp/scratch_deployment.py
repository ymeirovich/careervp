"""Fail-closed settings for the isolated P-64 scratch deployment path."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from urllib.parse import urlparse


PINNED_ACCOUNT = "788159322332"
PINNED_REGION = "us-east-1"
SCRATCH_REGION = "eu-west-1"
_RESERVED_ENVIRONMENTS = {"dev", "stage", "staging", "prod", "production"}
_SCRATCH_ENVIRONMENT_PATTERN = re.compile(
    r"^rto-euw1-[0-9]{8}(?:-[a-z0-9][a-z0-9-]*)?$"
)


@dataclass(frozen=True)
class ScratchDeploymentSettings:
    """Validated deployment inputs shared by ``app.py`` and ``ServiceStack``."""

    account: str
    region: str
    environment: str
    configuration_source: str
    allowed_origin: str
    scratch_mode: bool = True

    def __post_init__(self) -> None:
        if not self.scratch_mode:
            return
        if not self.account or not re.fullmatch(r"[0-9]{12}", self.account):
            raise ValueError("scratch account must be an explicit 12-digit account ID")
        if self.region != SCRATCH_REGION:
            raise ValueError(f"scratch region must be exactly {SCRATCH_REGION}")
        if self.environment in _RESERVED_ENVIRONMENTS:
            raise ValueError(
                f"scratch environment {self.environment!r} is reserved for a live tier"
            )
        # A reserved token anywhere in the environment would leak into every physical
        # name (e.g. 'rto-euw1-20260712-dev' mints '...-dev' resources), so reject it
        # here rather than relying on the runbook's shell guard.
        if _RESERVED_ENVIRONMENTS.intersection(self.environment.split("-")):
            raise ValueError(
                f"scratch environment {self.environment!r} must not contain a "
                "live-tier token (dev, stage, staging, prod, production)"
            )
        if not _SCRATCH_ENVIRONMENT_PATTERN.fullmatch(self.environment):
            raise ValueError(
                "scratch environment must match rto-euw1-YYYYMMDD[-unique-suffix]"
            )
        if len(self.environment) > 40:
            raise ValueError("scratch environment must be at most 40 characters")
        if self.configuration_source != "test":
            raise ValueError("scratch configuration source must be explicitly 'test'")
        parsed_origin = urlparse(self.allowed_origin)
        if (
            parsed_origin.scheme not in {"http", "https"}
            or not parsed_origin.netloc
            or parsed_origin.path not in {"", "/"}
            or parsed_origin.query
            or parsed_origin.fragment
            or "dev.careervp.com" in parsed_origin.netloc
            or "stage.careervp.com" in parsed_origin.netloc
            or "app.careervp.com" in parsed_origin.netloc
        ):
            raise ValueError(
                "scratch allowed origin must be an isolated HTTP(S) origin"
            )

    @classmethod
    def default(cls) -> ScratchDeploymentSettings:
        """Return the unchanged live/default deployment posture."""
        return cls(
            account=PINNED_ACCOUNT,
            region=PINNED_REGION,
            environment="dev",
            configuration_source="dev",
            allowed_origin="",
            scratch_mode=False,
        )

    @classmethod
    def from_environment(
        cls,
        live_account: str = PINNED_ACCOUNT,
        live_region: str = PINNED_REGION,
    ) -> ScratchDeploymentSettings:
        """Resolve an explicitly flagged scratch path or the pinned live default."""
        raw_flag = os.environ.get("CAREERVP_SCRATCH_MODE")
        if raw_flag is None:
            live_environment = os.environ.get("ENVIRONMENT", "dev")
            return cls(
                account=live_account,
                region=live_region,
                environment=live_environment,
                configuration_source=live_environment,
                allowed_origin="",
                scratch_mode=False,
            )
        if raw_flag != "true":
            raise ValueError("CAREERVP_SCRATCH_MODE must be exactly 'true' when set")

        required = {
            "account": "CAREERVP_SCRATCH_ACCOUNT",
            "region": "CAREERVP_SCRATCH_REGION",
            "environment": "ENVIRONMENT",
            "configuration_source": "CAREERVP_CONFIG_SOURCE",
            "allowed_origin": "CAREERVP_SCRATCH_ORIGIN",
        }
        missing = [
            env_name for env_name in required.values() if not os.environ.get(env_name)
        ]
        if missing:
            raise ValueError(
                "scratch mode requires explicit inputs: " + ", ".join(sorted(missing))
            )
        return cls(
            account=os.environ[required["account"]],
            region=os.environ[required["region"]],
            environment=os.environ[required["environment"]],
            configuration_source=os.environ[required["configuration_source"]],
            allowed_origin=os.environ[required["allowed_origin"]],
        )


def ssm_parameter_name(environment: str, suffix: str) -> str:
    """Build an environment-scoped SSM parameter name without live fallback."""
    return f"/careervp/{environment}/{suffix}"


def validate_scratch_boundary(
    settings: ScratchDeploymentSettings,
    *,
    environment: str,
    region: str | None = None,
    account: str | None = None,
) -> None:
    """Reject scratch-only lower-level behavior outside the validated target."""
    if not settings.scratch_mode:
        raise ValueError("scratch settings must enable scratch mode")
    if settings.environment != environment:
        raise ValueError("scratch settings environment mismatch")
    if region is not None and settings.region != region:
        raise ValueError("scratch settings region mismatch")
    if account is not None and settings.account != account:
        raise ValueError("scratch settings account mismatch")
