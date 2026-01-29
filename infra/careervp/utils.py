import getpass
import os
from typing import cast

import careervp.constants as constants
from careervp.naming_utils import NamingUtils


def get_username() -> str:
    try:
        return getpass.getuser().replace(".", "-")
    except Exception:
        return "github"


def get_stack_name() -> str:
    environment = os.getenv("ENVIRONMENT", constants.ENVIRONMENT)
    region = os.getenv("CDK_DEFAULT_REGION") or os.getenv("AWS_DEFAULT_REGION")
    account_id = os.getenv("CDK_DEFAULT_ACCOUNT")
    feature = os.getenv("CAREERVP_STACK_FEATURE", constants.STACK_FEATURE)
    naming = NamingUtils(environment=environment, region=region, account_id=account_id)
    return cast(str, naming.stack_id(feature))


def get_construct_name(stack_prefix: str, construct_name: str) -> str:
    return f"{stack_prefix}-{construct_name}"[0:64]
