from __future__ import annotations

from typing import Any

import pytest
from aws_cdk import App, Environment, NestedStack
from aws_cdk.assertions import Template

from careervp.crud_features_nested_stack import CrudFeaturesNestedStack
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
def rehome_service_stack() -> ServiceStack:
    """Build the ServiceStack with the P-26 rehome topology enabled."""
    app = App(context={"p26_rehome_features": "true"})
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
def rehome_synthesized_template(rehome_service_stack: ServiceStack) -> Template:
    """The parent template after the P-26 Job-1 rehome topology is enabled."""
    return Template.from_stack(rehome_service_stack)


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


@pytest.fixture(scope="module")
def features_template(rehome_service_stack: ServiceStack) -> Template:
    """The P-26 Job-1 CrudFeaturesNestedStack template.

    Job 1 re-homes every explicitly-named, non-stateful feature resource here
    (feature Lambdas + log groups, async SQS queues/DLQs, per-worker DLQs, the
    shared Lambda role, the artifact-chain state machine + failure handlers) with
    their deployed logical ids preserved byte-for-byte. Tests that formerly found
    these resources in the parent now look here.
    """
    feature_stack = next(
        c
        for c in rehome_service_stack.node.find_all()
        if isinstance(c, CrudFeaturesNestedStack)
    )
    return Template.from_stack(feature_stack)


@pytest.fixture(scope="module")
def merged_resources(rehome_service_stack: ServiceStack) -> dict[str, dict[str, Any]]:
    """Every CloudFormation resource across the parent and all nested templates.

    P-26 Job 1 spreads the deployment across the parent plus five nested stacks.
    Cross-cutting invariant checks (a Lambda's config, an IAM grant, an SQS DLQ
    wiring) may now resolve to whichever template owns the resource, so tests that
    only care that a resource EXISTS somewhere with the right shape merge here.
    """
    merged: dict[str, dict[str, Any]] = {}
    templates = [Template.from_stack(rehome_service_stack)]
    for construct in rehome_service_stack.node.find_all():
        if isinstance(construct, NestedStack):
            templates.append(Template.from_stack(construct))
    for template in templates:
        resources = template.to_json().get("Resources", {})
        for logical_id, resource in resources.items():
            merged[logical_id] = resource
    return merged
