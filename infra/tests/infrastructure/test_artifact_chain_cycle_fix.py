from __future__ import annotations

from typing import Any, Mapping

from aws_cdk.assertions import Template

from careervp.service_stack import ServiceStack


CR_FAILURE_HANDLER = "careervp.handlers.cr_failure_handler.lambda_handler"
ARTIFACT_FAILURE_HANDLER = "careervp.handlers.artifact_failure_handler.lambda_handler"


def _artifact_chain_template(service_stack: ServiceStack) -> Template:
    # The artifact-chain failure handlers, their dedicated role, and the state
    # machine live in the PARENT stack (the FE-UI-036 nested-stack split was
    # reverted because the resources are already deployed under explicit names).
    return Template.from_stack(service_stack)


def _resources(
    template: Template, resource_type: str
) -> Mapping[str, Mapping[str, Any]]:
    return template.find_resources(resource_type)


def _lambda_role_logical_id(lambda_resource: Mapping[str, Any]) -> str:
    role_ref = lambda_resource["Properties"].get("Role")
    if isinstance(role_ref, dict) and isinstance(role_ref.get("Fn::GetAtt"), list):
        logical_id = role_ref["Fn::GetAtt"][0]
        if isinstance(logical_id, str) and logical_id:
            return logical_id
    raise AssertionError("Lambda role reference could not be resolved from template")


def _lambda_by_handler(template: Template, handler: str) -> Mapping[str, Any]:
    matches = [
        resource
        for resource in _resources(template, "AWS::Lambda::Function").values()
        if resource["Properties"].get("Handler") == handler
    ]
    assert len(matches) == 1, (
        f"Expected one Lambda with handler {handler}, found {len(matches)}"
    )
    return matches[0]


def _actions(statement: Mapping[str, Any]) -> list[str]:
    actions = statement.get("Action", [])
    if isinstance(actions, str):
        return [actions]
    if isinstance(actions, list):
        return [action for action in actions if isinstance(action, str)]
    return []


def _policy_statements_for_role(
    template: Template, role_logical_id: str
) -> list[Mapping[str, Any]]:
    statements: list[Mapping[str, Any]] = []
    for policy in _resources(template, "AWS::IAM::Policy").values():
        roles = policy["Properties"].get("Roles", [])
        if not any(
            isinstance(role, dict) and role.get("Ref") == role_logical_id
            for role in roles
        ):
            continue
        policy_statements = (
            policy["Properties"].get("PolicyDocument", {}).get("Statement", [])
        )
        if isinstance(policy_statements, dict):
            statements.append(policy_statements)
        elif isinstance(policy_statements, list):
            statements.extend(
                statement
                for statement in policy_statements
                if isinstance(statement, dict)
            )
    return statements


def test_template_synthesizes_without_dependency_cycle(
    service_stack: ServiceStack,
) -> None:
    Template.from_stack(service_stack)


def test_failure_handlers_use_dedicated_role_not_shared_service_role(
    service_stack: ServiceStack,
) -> None:
    template = _artifact_chain_template(service_stack)
    cr_function = _lambda_by_handler(template, CR_FAILURE_HANDLER)
    artifact_function = _lambda_by_handler(template, ARTIFACT_FAILURE_HANDLER)

    cr_role = _lambda_role_logical_id(cr_function)
    artifact_role = _lambda_role_logical_id(artifact_function)

    assert cr_role == artifact_role
    # In the parent stack the logical id carries the construct-path prefix
    # (CareerVpCrudDevCrud...), so match the dedicated role by substring rather
    # than prefix. Both handlers must use FailureHandlerRole, not the shared
    # CrudServiceRole.
    assert "FailureHandlerRole" in cr_role
    assert "ServiceRoleArn" not in cr_role


def test_dedicated_failure_handler_role_has_no_stepfunctions_permission(
    service_stack: ServiceStack,
) -> None:
    template = _artifact_chain_template(service_stack)
    role_logical_id = _lambda_role_logical_id(
        _lambda_by_handler(template, CR_FAILURE_HANDLER)
    )

    statements = _policy_statements_for_role(template, role_logical_id)
    assert statements, (
        "Dedicated failure-handler role has no synthesized policy statements"
    )
    assert not any(
        action.startswith("states:")
        for statement in statements
        for action in _actions(statement)
    )


def test_dedicated_role_is_least_privilege_on_applications_table(
    service_stack: ServiceStack,
) -> None:
    template = _artifact_chain_template(service_stack)
    role_logical_id = _lambda_role_logical_id(
        _lambda_by_handler(template, CR_FAILURE_HANDLER)
    )

    dynamodb_statements = [
        statement
        for statement in _policy_statements_for_role(template, role_logical_id)
        if any(action.startswith("dynamodb:") for action in _actions(statement))
    ]

    assert dynamodb_statements, "Dedicated role missing DynamoDB grants"
    assert any(
        "dynamodb:UpdateItem" in _actions(statement)
        for statement in dynamodb_statements
    )
    assert all(
        "ApplicationsTable" in str(statement.get("Resource", ""))
        for statement in dynamodb_statements
    )
    assert not any(
        resource_name in str(statement.get("Resource", ""))
        for statement in dynamodb_statements
        for resource_name in (
            "jobs",
            "artifacts",
            "vpr",
            "coverletter",
            "interviewprep",
        )
    )


def test_shared_role_still_has_stepfunctions_grants(
    synthesized_template: Template,
) -> None:
    shared_role_ids = [
        logical_id
        for logical_id in _resources(synthesized_template, "AWS::IAM::Role")
        if "ServiceRoleArn" in logical_id
    ]
    assert len(shared_role_ids) == 1
    statements = _policy_statements_for_role(synthesized_template, shared_role_ids[0])
    actions = {action for statement in statements for action in _actions(statement)}

    assert "states:StartExecution" in actions
    assert {
        "states:SendTaskSuccess",
        "states:SendTaskFailure",
        "states:SendTaskHeartbeat",
    }.issubset(actions)


def test_failure_handler_role_name_follows_convention(
    service_stack: ServiceStack,
) -> None:
    template = _artifact_chain_template(service_stack)
    role_logical_id = _lambda_role_logical_id(
        _lambda_by_handler(template, CR_FAILURE_HANDLER)
    )
    role = _resources(template, "AWS::IAM::Role")[role_logical_id]

    assert role["Properties"]["RoleName"] == "careervp-role-lambda-failure-handler-dev"
