from __future__ import annotations

import pytest
from aws_cdk import App, Environment
from aws_cdk.assertions import Template

from careervp.naming_utils import NamingUtils
from careervp.service_stack import ServiceStack


@pytest.fixture(scope="module")
def service_stack() -> ServiceStack:
    """Build the ServiceStack once for infra assertions."""
    app = App()
    naming = NamingUtils(
        environment="dev", region="us-east-1", account_id="123456789012"
    )
    return ServiceStack(
        scope=app,
        id=naming.stack_id("crud"),
        env=Environment(account="123456789012", region="us-east-1"),
        is_production_env=False,
        naming=naming,
        stack_feature="crud",
    )


@pytest.fixture(scope="module")
def synthesized_template(service_stack: ServiceStack) -> Template:
    """The parent CareerVpCrudDev template (API Gateway, tables, buckets, core Lambdas)."""
    return Template.from_stack(service_stack)


@pytest.fixture(scope="module")
def monitoring_template(synthesized_template: Template) -> Template:
    """Monitoring (dashboards, alarms, metric filters) lives in the parent stack.

    The FE-UI-036 nested-stack split was reverted: every relocated resource
    carries an explicit physical name and is already deployed in the parent, so
    CloudFormation cannot move it to a nested stack without a resource-import
    migration. Monitoring therefore resolves to the parent template.
    """
    return synthesized_template
