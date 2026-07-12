#!/usr/bin/env python3
import os

from aws_cdk import App, Environment
from careervp.frontend_stack import FrontendStack
from careervp.naming_utils import NamingUtils
from careervp.scratch_deployment import (
    PINNED_ACCOUNT as SCRATCH_MODULE_PINNED_ACCOUNT,
    PINNED_REGION as SCRATCH_MODULE_PINNED_REGION,
    ScratchDeploymentSettings,
)
from careervp.service_stack import ServiceStack

from careervp import constants

# P-28 live/default pins remain literal and auditable in this entry point.
PINNED_ACCOUNT = "788159322332"
PINNED_REGION = "us-east-1"
assert PINNED_ACCOUNT == SCRATCH_MODULE_PINNED_ACCOUNT
assert PINNED_REGION == SCRATCH_MODULE_PINNED_REGION


def _validate_ambient_identity(settings: ScratchDeploymentSettings) -> None:
    inferred_account = os.environ.get("CDK_DEFAULT_ACCOUNT") or os.environ.get(
        "AWS_DEFAULT_ACCOUNT"
    )
    if inferred_account and inferred_account != settings.account:
        raise SystemExit(
            f"P-28 FAIL-FAST: resolved account {inferred_account!r} does not match "
            f"the explicit account {settings.account!r}. Wrong AWS profile — aborting."
        )

    inferred_region = os.environ.get("CDK_DEFAULT_REGION") or os.environ.get(
        "AWS_DEFAULT_REGION"
    )
    if inferred_region and inferred_region != settings.region:
        raise SystemExit(
            f"P-28 FAIL-FAST: resolved region {inferred_region!r} does not match "
            f"the explicit region {settings.region!r}. Wrong region — aborting."
        )


def build_app(settings: ScratchDeploymentSettings) -> App:
    """Build the pinned live app or the explicitly isolated scratch service app."""
    _validate_ambient_identity(settings)
    stack_feature = os.getenv("CAREERVP_STACK_FEATURE", constants.STACK_FEATURE)
    naming = NamingUtils(
        environment=settings.environment,
        region=settings.region,
        account_id=settings.account,
    )
    # No `context=` override here: the CDK CLI loads cdk.json into CDK_CONTEXT_JSON and
    # applies it *after* constructor context, so a scratch value passed here would be
    # silently replaced by the live allowed_origins list. Scratch reads its origin from
    # the validated ScratchDeploymentSettings instead, never from context.
    app = App()
    env_value = Environment(account=settings.account, region=settings.region)

    ServiceStack(
        scope=app,
        id=naming.stack_id(stack_feature),
        env=env_value,
        is_production_env=settings.environment in ("prod", "production"),
        naming=naming,
        stack_feature=stack_feature,
        scratch_settings=settings if settings.scratch_mode else None,
    )

    if not settings.scratch_mode:
        domain_map = {
            "prod": "app.careervp.com",
            "production": "app.careervp.com",
            "stage": "stage.careervp.com",
            "dev": "dev.careervp.com",
        }
        frontend_domain = os.getenv(
            "FRONTEND_DOMAIN",
            domain_map.get(settings.environment, "dev.careervp.com"),
        )
        FrontendStack(
            scope=app,
            construct_id=f"CareerVpFrontend-{settings.environment.capitalize()}",
            env=env_value,
            environment=settings.environment,
            domain=frontend_domain,
            is_production=settings.environment in ("prod", "production"),
        )
    return app


def main() -> None:
    try:
        settings = ScratchDeploymentSettings.from_environment(
            live_account=PINNED_ACCOUNT,
            live_region=PINNED_REGION,
        )
    except ValueError as error:
        raise SystemExit(f"P-64 SCRATCH FAIL-CLOSED: {error}") from error
    build_app(settings).synth()


if __name__ == "__main__":
    main()


__all__ = ["PINNED_ACCOUNT", "PINNED_REGION", "build_app", "main"]
