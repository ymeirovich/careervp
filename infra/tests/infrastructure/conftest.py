from __future__ import annotations

import pytest
from aws_cdk import App, Environment
from aws_cdk.assertions import Template

from careervp.naming_utils import NamingUtils
from careervp.service_stack import ServiceStack


@pytest.fixture(scope="module")
def synthesized_template() -> Template:
    """Synthesize the ServiceStack once for infra assertions."""
    app = App()
    naming = NamingUtils(
        environment="dev", region="us-east-1", account_id="123456789012"
    )
    stack = ServiceStack(
        scope=app,
        id=naming.stack_id("crud"),
        env=Environment(account="123456789012", region="us-east-1"),
        is_production_env=False,
        naming=naming,
        stack_feature="crud",
    )
    return Template.from_stack(stack)
