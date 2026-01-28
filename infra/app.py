#!/usr/bin/env python3
import os

from aws_cdk import App, Environment
from boto3 import client, session
from careervp.naming_utils import NamingUtils
from careervp.service_stack import ServiceStack

from careervp import constants

account = (
    os.environ.get("AWS_DEFAULT_ACCOUNT")
    or client("sts").get_caller_identity()["Account"]
)
region = (
    os.environ.get("AWS_DEFAULT_REGION") or session.Session().region_name or "us-east-1"
)
environment = os.getenv("ENVIRONMENT", constants.ENVIRONMENT)
stack_feature = os.getenv("CAREERVP_STACK_FEATURE", constants.STACK_FEATURE)
naming = NamingUtils(environment=environment, region=region, account_id=account)
app = App()
my_stack = ServiceStack(
    scope=app,
    id=naming.stack_id(stack_feature),
    env=Environment(account=account, region=region),
    is_production_env=environment in ("prod", "production"),
    naming=naming,
    stack_feature=stack_feature,
)

app.synth()
