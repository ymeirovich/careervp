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
def monitoring_template(service_stack: ServiceStack) -> Template:
    """The approved phase-1 monitoring nested stack template."""
    return Template.from_stack(service_stack.monitoring_nested_stack)


@pytest.fixture(scope="module")
def ai_assist_template(service_stack: ServiceStack) -> Template:
    """The AI-assist nested stack template."""
    return Template.from_stack(service_stack.ai_assist_nested_stack)


@pytest.fixture(scope="module")
def error_report_template(service_stack: ServiceStack) -> Template:
    """The client error-report nested stack template."""
    return Template.from_stack(service_stack.error_report_nested_stack)


@pytest.fixture(scope="module")
def company_research_template(service_stack: ServiceStack) -> Template:
    """The company-research Tavily wiring nested stack template."""
    return Template.from_stack(service_stack.company_research_nested_stack)
