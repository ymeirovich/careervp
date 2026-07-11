#!/usr/bin/env python3
import os

from aws_cdk import App, Environment
from careervp.frontend_stack import FrontendStack
from careervp.naming_utils import NamingUtils
from careervp.service_stack import ServiceStack

from careervp import constants

# P-28: Hard-pin account and region — fail fast on a wrong-profile deploy.
# The solo/single-account model (O-8, scope-lock live_anchor) means account/region are
# NOT inferred from ambient env/session/STS. Ambient inference silently targets the wrong
# account when the wrong AWS profile is active; here we bind a constant and ABORT if an
# ambient account/region is present and disagrees. Env-agnostic synth is DISABLED for this
# repo: `env_value` is always set, never None. A future multi-account expansion adds an
# allow-list, not a revert to ambient inference.
PINNED_ACCOUNT = "788159322332"
PINNED_REGION = "us-east-1"

_inferred_account = os.environ.get("CDK_DEFAULT_ACCOUNT") or os.environ.get(
    "AWS_DEFAULT_ACCOUNT"
)
if _inferred_account and _inferred_account != PINNED_ACCOUNT:
    raise SystemExit(
        f"P-28 FAIL-FAST: resolved account {_inferred_account!r} does not match the "
        f"pinned account {PINNED_ACCOUNT!r}. Wrong AWS profile — aborting before any "
        "CDK synthesis / CloudFormation API call to prevent a cross-account deploy."
    )

_inferred_region = os.environ.get("CDK_DEFAULT_REGION") or os.environ.get(
    "AWS_DEFAULT_REGION"
)
if _inferred_region and _inferred_region != PINNED_REGION:
    raise SystemExit(
        f"P-28 FAIL-FAST: resolved region {_inferred_region!r} does not match the "
        f"pinned region {PINNED_REGION!r}. Wrong region — aborting."
    )

account = PINNED_ACCOUNT
region = PINNED_REGION

environment = os.getenv("ENVIRONMENT", constants.ENVIRONMENT)
stack_feature = os.getenv("CAREERVP_STACK_FEATURE", constants.STACK_FEATURE)
naming = NamingUtils(environment=environment, region=region, account_id=account)
app = App()

# P-28: env is ALWAYS bound to the pinned account/region — never None (no env-agnostic synth).
env_value = Environment(account=account, region=region)

my_stack = ServiceStack(
    scope=app,
    id=naming.stack_id(stack_feature),
    env=env_value,
    is_production_env=environment in ("prod", "production"),
    naming=naming,
    stack_feature=stack_feature,
)

_domain_map = {
    "prod": "app.careervp.com",
    "production": "app.careervp.com",
    "stage": "stage.careervp.com",
    "dev": "dev.careervp.com",
}
frontend_domain = os.getenv(
    "FRONTEND_DOMAIN", _domain_map.get(environment, "dev.careervp.com")
)

FrontendStack(
    scope=app,
    construct_id=f"CareerVpFrontend-{environment.capitalize()}",
    env=env_value,
    environment=environment,
    domain=frontend_domain,
    is_production=environment in ("prod", "production"),
)

app.synth()
