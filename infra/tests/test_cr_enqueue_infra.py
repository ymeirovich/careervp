"""
TEST-FE-053 Category D: CDK template assertions for CR enqueue infra.

SC6: CR handler Lambda has COMPANY_RESEARCH_QUEUE_URL env var and a scoped
     sqs:SendMessage IAM statement (no wildcard Resource).
SC7: Template synthesises without exception (no dependency cycle).
"""

from __future__ import annotations

from typing import Any
from collections.abc import Mapping

import pytest
from aws_cdk import App, Environment
from aws_cdk.assertions import Template

from careervp.naming_utils import NamingUtils
from careervp.service_stack import ServiceStack


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def service_stack() -> ServiceStack:
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
    return Template.from_stack(service_stack)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _resources(
    template: Template, resource_type: str
) -> Mapping[str, Mapping[str, Any]]:
    return template.find_resources(resource_type)


def _all_iam_statements(template: Template) -> list[Mapping[str, Any]]:
    statements: list[Mapping[str, Any]] = []
    for policy in _resources(template, "AWS::IAM::Policy").values():
        doc = policy["Properties"].get("PolicyDocument", {})
        for stmt in doc.get("Statement", []):
            if isinstance(stmt, dict):
                statements.append(stmt)
    return statements


def _actions(statement: Mapping[str, Any]) -> list[str]:
    raw = statement.get("Action", [])
    if isinstance(raw, str):
        return [raw]
    if isinstance(raw, list):
        return [a for a in raw if isinstance(a, str)]
    return []


def _resource_is_scoped(resource_value: Any) -> bool:
    """Return True when the Resource field is NOT a bare wildcard '*'."""
    if resource_value == "*":
        return False
    if isinstance(resource_value, list):
        return "*" not in resource_value
    return True


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_synth_no_cycle(service_stack: ServiceStack) -> None:
    """SC7: Template.from_stack succeeds — no dependency cycle in the stack."""
    template = Template.from_stack(service_stack)
    lambdas = _resources(template, "AWS::Lambda::Function")
    assert len(lambdas) > 0, "Expected at least one Lambda function in the stack"


def test_cr_handler_has_queue_url_env(synthesized_template: Template) -> None:
    """SC6: The CR handler Lambda has COMPANY_RESEARCH_QUEUE_URL in its environment."""
    lambdas = _resources(synthesized_template, "AWS::Lambda::Function")

    found = False
    for resource in lambdas.values():
        env = resource["Properties"].get("Environment", {}).get("Variables", {})
        if "COMPANY_RESEARCH_QUEUE_URL" in env:
            found = True
            break

    assert found, "No Lambda function has COMPANY_RESEARCH_QUEUE_URL in its environment"


def test_sqs_send_scoped_to_cr_queue(synthesized_template: Template) -> None:
    """SC6: At least one IAM statement grants sqs:SendMessage on a non-wildcard resource."""
    statements = _all_iam_statements(synthesized_template)

    scoped_send_found = False
    for stmt in statements:
        actions = _actions(stmt)
        has_send = any("sqs:SendMessage" in a or a == "sqs:*" for a in actions)
        if not has_send:
            continue
        resource = stmt.get("Resource")
        if resource is not None and _resource_is_scoped(resource):
            scoped_send_found = True
            break

    assert scoped_send_found, (
        "Expected at least one sqs:SendMessage grant scoped to a specific queue ARN"
    )


def test_no_wildcard_sqs(synthesized_template: Template) -> None:
    """SC6: No IAM statement grants sqs:SendMessage on Resource='*'."""
    statements = _all_iam_statements(synthesized_template)

    for stmt in statements:
        actions = _actions(stmt)
        has_send = any("sqs:SendMessage" in a for a in actions)
        if not has_send:
            continue
        resource = stmt.get("Resource")
        if resource == "*" or (isinstance(resource, list) and "*" in resource):
            pytest.fail(f"Found sqs:SendMessage on wildcard Resource: {stmt}")
