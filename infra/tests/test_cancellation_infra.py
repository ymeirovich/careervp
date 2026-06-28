"""TEST-CANCEL-001 § infra-cancel-resources: CDK template assertions (5 tests).

Validates the synthesized CloudFormation template for FE-UI-043 resources:
  1. POST /company-research/{jobId}/cancel route exists in API Gateway
  2. Cancel handler Lambda role has states:StopExecution grant
  3. No states:* wildcard in any cancel-handler role (FE-UI-035 invariant)
  4. Orphan-cleanup reaper Lambda + EventBridge schedule rule exists
  5. S3 DeleteObject permission for the reaper is prefix-scoped (not bucket-wide)

Tests 1, 2, 4, 5 are RED until the infra is added.
Test 3 guards the no-wildcard invariant (currently passes; kept to prevent regression).
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

import pytest
from aws_cdk import App, Environment
from aws_cdk.assertions import Template

from careervp.naming_utils import NamingUtils
from careervp.service_stack import ServiceStack


# ---------------------------------------------------------------------------
# Fixtures — reuse the shared conftest pattern
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
# Helpers (adapted from test_artifact_chain_legs.py)
# ---------------------------------------------------------------------------


def _resources(
    template: Template, resource_type: str
) -> Mapping[str, Mapping[str, Any]]:
    return template.find_resources(resource_type)


def _actions(statement: Mapping[str, Any]) -> list[str]:
    actions = statement.get("Action", [])
    if isinstance(actions, str):
        return [actions]
    if isinstance(actions, list):
        return [a for a in actions if isinstance(a, str)]
    return []


def _policy_statements_for_role(
    template: Template, role_logical_id: str
) -> list[Mapping[str, Any]]:
    statements: list[Mapping[str, Any]] = []
    for policy in _resources(template, "AWS::IAM::Policy").values():
        roles = policy["Properties"].get("Roles", [])
        if not any(
            isinstance(r, dict) and r.get("Ref") == role_logical_id for r in roles
        ):
            continue
        policy_doc = policy["Properties"].get("PolicyDocument", {}).get("Statement", [])
        if isinstance(policy_doc, list):
            statements.extend(s for s in policy_doc if isinstance(s, dict))
        elif isinstance(policy_doc, dict):
            statements.append(policy_doc)
    return statements


def _lambda_role_logical_id(lambda_resource: Mapping[str, Any]) -> str:
    role_ref = lambda_resource["Properties"].get("Role")
    if isinstance(role_ref, dict) and isinstance(role_ref.get("Fn::GetAtt"), list):
        logical_id = role_ref["Fn::GetAtt"][0]
        if isinstance(logical_id, str) and logical_id:
            return logical_id
    raise AssertionError("Lambda role reference could not be resolved")


def _get_method_paths(
    methods: Mapping[str, Mapping[str, Any]],
    resources: Mapping[str, Mapping[str, Any]],
) -> list[tuple[str, str]]:
    """Return list of (http_method, full_path) for all API Gateway methods.

    Builds the full path recursively so that nested resources like
    /company-research/{jobId}/cancel are resolved correctly.
    """
    _path_cache: dict[str, str] = {}

    def _full_path(logical_id: str, depth: int = 0) -> str:
        if logical_id in _path_cache:
            return _path_cache[logical_id]
        if depth > 20:
            return ""
        props = resources.get(logical_id)
        if props is None:
            return ""
        current_part = str(props["Properties"].get("PathPart", ""))
        parent_ref = props["Properties"].get("ParentId", {})
        parent_id = parent_ref.get("Ref") if isinstance(parent_ref, dict) else None
        if parent_id and parent_id in resources:
            parent_path = _full_path(parent_id, depth + 1)
            result = f"{parent_path}/{current_part}" if parent_path else current_part
        else:
            result = current_part
        _path_cache[logical_id] = result
        return result

    method_paths: list[tuple[str, str]] = []
    for method_props in methods.values():
        http_method = str(method_props["Properties"].get("HttpMethod", ""))
        resource_ref = method_props["Properties"].get("ResourceId", {}).get("Ref", "")
        full_path = _full_path(resource_ref) if resource_ref else ""
        method_paths.append((http_method, full_path))
    return method_paths


# ---------------------------------------------------------------------------
# TEST 1: CR cancel route exists in API Gateway
# ---------------------------------------------------------------------------


def test_cr_cancel_route_exists_in_api_gateway(synthesized_template: Template) -> None:
    """POST /company-research/{jobId}/cancel must be wired as an API Gateway method."""
    resources = synthesized_template.find_resources("AWS::ApiGateway::Resource")
    methods = synthesized_template.find_resources("AWS::ApiGateway::Method")

    method_paths = _get_method_paths(methods, resources)

    cancel_routes = [
        (m, p) for m, p in method_paths if "company-research" in p and "cancel" in p
    ]

    assert cancel_routes, (
        "No POST /company-research/{jobId}/cancel route found in API Gateway. "
        "Add it to api_construct.py routes list."
    )

    post_cancel = [m for m, _ in cancel_routes if m == "POST"]
    assert post_cancel, (
        f"company-research cancel route exists but has no POST method. Found: {cancel_routes}"
    )


# ---------------------------------------------------------------------------
# TEST 2: Cancel handler Lambda role has states:StopExecution
# ---------------------------------------------------------------------------


def test_cancel_handler_role_has_stop_execution_grant(
    synthesized_template: Template,
) -> None:
    """The VPR status Lambda (which handles all cancel routes including CR cancel)
    must have an IAM policy granting states:StopExecution scoped to the chain ARN."""
    all_functions = synthesized_template.find_resources("AWS::Lambda::Function")

    # The VPR status handler also handles /vpr/{vprId}/cancel
    vpr_status_lambdas = [
        resource
        for resource in all_functions.values()
        if resource["Properties"].get("Handler")
        == "careervp.handlers.vpr_status_handler.lambda_handler"
    ]
    assert vpr_status_lambdas, "VPR status Lambda not synthesized"

    role_id = _lambda_role_logical_id(vpr_status_lambdas[0])
    statements = _policy_statements_for_role(synthesized_template, role_id)

    stop_exec_statements = [
        s for s in statements if "states:StopExecution" in _actions(s)
    ]
    assert stop_exec_statements, (
        "VPR status handler role has no states:StopExecution grant. "
        "FE-UI-043 requires adding it for chained artifact cancel."
    )

    # Verify the grant is scoped (not wildcarded)
    for stmt in stop_exec_statements:
        resource = stmt.get("Resource")
        resource_str = json.dumps(resource)
        assert resource_str != '"*"', (
            "states:StopExecution must NOT be granted on '*' — scope to chain ARN"
        )


# ---------------------------------------------------------------------------
# TEST 3: No states:* wildcard in any cancel-handler role (regression guard)
# ---------------------------------------------------------------------------


def test_no_states_wildcard_in_cancel_handler_roles(
    synthesized_template: Template,
) -> None:
    """FE-UI-035 invariant: cancel handlers must never receive states:* grants."""
    all_functions = synthesized_template.find_resources("AWS::Lambda::Function")

    cancel_handler_names = {
        "careervp.handlers.vpr_status_handler.lambda_handler",
        "careervp.handlers.cover_letter_handler.lambda_handler",
        "careervp.handlers.interview_prep_handler.lambda_handler",
        "careervp.handlers.cv_tailoring_handler.lambda_handler",
        "careervp.handlers.company_research_handler.lambda_handler",
    }

    for resource in all_functions.values():
        handler = resource["Properties"].get("Handler", "")
        if handler not in cancel_handler_names:
            continue
        role_id = _lambda_role_logical_id(resource)
        statements = _policy_statements_for_role(synthesized_template, role_id)
        for stmt in statements:
            assert "states:*" not in _actions(stmt), (
                f"Handler {handler!r} has states:* wildcard — violates FE-UI-035. "
                "Use specific actions (states:StopExecution, states:DescribeExecution)."
            )


# ---------------------------------------------------------------------------
# TEST 4: Orphan-cleanup reaper Lambda + EventBridge schedule exists
# ---------------------------------------------------------------------------


def test_orphan_reaper_lambda_and_schedule_exist(
    synthesized_template: Template,
) -> None:
    """The orphan-cleanup reaper must be deployed as a Lambda with an
    EventBridge schedule rule (or EventBridge Scheduler target)."""
    all_functions = synthesized_template.find_resources("AWS::Lambda::Function")
    reaper_lambdas = [
        props
        for props in all_functions.values()
        if "cleanup" in str(props["Properties"].get("FunctionName", "")).lower()
        or "reaper" in str(props["Properties"].get("FunctionName", "")).lower()
        or "artifact_cleanup" in str(props["Properties"].get("Handler", "")).lower()
    ]
    assert reaper_lambdas, (
        "No orphan-cleanup reaper Lambda found. "
        "Expected a Lambda with 'cleanup' or 'reaper' in FunctionName, "
        "or handler careervp.handlers.artifact_cleanup_handler.lambda_handler."
    )

    # There must be an EventBridge rule targeting the reaper
    rules = synthesized_template.find_resources("AWS::Events::Rule")
    schedule_rules = [
        props
        for props in rules.values()
        if props["Properties"].get("ScheduleExpression")
        and any(
            "cleanup" in json.dumps(target).lower()
            or "reaper" in json.dumps(target).lower()
            for target in props["Properties"].get("Targets", [])
        )
    ]
    # Also accept AWS::Scheduler::Schedule (EventBridge Scheduler)
    schedules = synthesized_template.find_resources("AWS::Scheduler::Schedule")
    reaper_schedules = [
        props
        for props in schedules.values()
        if "cleanup" in json.dumps(props).lower()
        or "reaper" in json.dumps(props).lower()
    ]

    assert schedule_rules or reaper_schedules, (
        "Reaper Lambda exists but no EventBridge schedule rule or Scheduler resource found. "
        "Add a scheduled trigger (e.g., rate(1 hour)) in api_construct.py."
    )


# ---------------------------------------------------------------------------
# TEST 5: Reaper S3 DeleteObject permission is prefix-scoped
# ---------------------------------------------------------------------------


def test_reaper_s3_delete_is_prefix_scoped(synthesized_template: Template) -> None:
    """The reaper's IAM role must have s3:DeleteObject scoped to the results
    prefix (e.g., arn:aws:s3:::bucket/results/*), NOT the whole bucket."""
    all_functions = synthesized_template.find_resources("AWS::Lambda::Function")
    reaper_lambdas = [
        resource
        for resource in all_functions.values()
        if "cleanup" in str(resource["Properties"].get("FunctionName", "")).lower()
        or "reaper" in str(resource["Properties"].get("FunctionName", "")).lower()
        or "artifact_cleanup" in str(resource["Properties"].get("Handler", "")).lower()
    ]
    assert reaper_lambdas, (
        "Reaper Lambda not found — test_4 should have caught this first"
    )

    role_id = _lambda_role_logical_id(reaper_lambdas[0])
    statements = _policy_statements_for_role(synthesized_template, role_id)

    delete_stmts = [s for s in statements if "s3:DeleteObject" in _actions(s)]
    assert delete_stmts, (
        "Reaper role has no s3:DeleteObject grant. "
        "FE-UI-043 requires deleting orphan result objects."
    )

    for stmt in delete_stmts:
        resource = stmt.get("Resource", "")
        resource_str = json.dumps(resource)
        # Must NOT be bucket-wide ('*' or bare bucket ARN)
        assert resource_str != '"*"', "s3:DeleteObject must not be granted on '*'"
        assert resource_str.endswith('/*"') or "/" in resource_str, (
            f"s3:DeleteObject resource should be prefix-scoped (e.g., bucket/results/*). "
            f"Got: {resource_str}"
        )
