#!/usr/bin/env python3
import os

from aws_cdk import App, Environment
from boto3 import client, session
from careervp.naming_utils import NamingUtils
from careervp.service_stack import ServiceStack

from careervp import constants

# Prefer explicit env vars first; fall back to session/STS only if available.
account = os.environ.get("AWS_DEFAULT_ACCOUNT") or os.environ.get("CDK_DEFAULT_ACCOUNT")
region = os.environ.get("AWS_DEFAULT_REGION") or os.environ.get("CDK_DEFAULT_REGION")

# Try to infer region from the local session if still empty.
if not region:
    region = session.Session().region_name

# As a last resort, try STS for account if creds exist; otherwise allow env-agnostic synth.
if not account:
    try:
        account = client("sts").get_caller_identity().get("Account")
    except Exception:
        account = None

# Default region for local/CI synth if none found.
if not region:
    region = "us-east-1"

environment = os.getenv("ENVIRONMENT", constants.ENVIRONMENT)
stack_feature = os.getenv("CAREERVP_STACK_FEATURE", constants.STACK_FEATURE)
naming = NamingUtils(environment=environment, region=region, account_id=account or "")
app = App()

# Only bind explicit env when both account and region are known; otherwise synth env-agnostic.
env_value = Environment(account=account, region=region) if account and region else None

my_stack = ServiceStack(
    scope=app,
    id=naming.stack_id(stack_feature),
    env=env_value,
    is_production_env=environment in ("prod", "production"),
    naming=naming,
    stack_feature=stack_feature,
)

app.synth()
