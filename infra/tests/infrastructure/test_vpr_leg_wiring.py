from __future__ import annotations

import json
from typing import Any, Mapping

from aws_cdk.assertions import Template

from careervp.service_stack import ServiceStack


def _resources(
    template: Template, resource_type: str
) -> Mapping[str, Mapping[str, Any]]:
    return template.find_resources(resource_type)


def _state_machine_definition(template: Template) -> str:
    machines = _resources(template, "AWS::StepFunctions::StateMachine")
    matches = [
        machine
        for machine in machines.values()
        if machine["Properties"].get("StateMachineName")
        == "careervp-artifact-chain-statemachine-dev"
    ]
    assert len(matches) == 1
    return json.dumps(matches[0]["Properties"]["DefinitionString"])


def _lambda_role_logical_id(lambda_resource: Mapping[str, Any]) -> str:
    role_ref = lambda_resource["Properties"].get("Role")
    if isinstance(role_ref, dict) and isinstance(role_ref.get("Fn::GetAtt"), list):
        logical_id = role_ref["Fn::GetAtt"][0]
        if isinstance(logical_id, str) and logical_id:
            return logical_id
    raise AssertionError("Lambda role reference could not be resolved from template")


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


def _vpr_sqs_worker_role(template: Template) -> str:
    matches = [
        resource
        for resource in _resources(template, "AWS::Lambda::Function").values()
        if resource["Properties"].get("Handler")
        == "careervp.handlers.vpr_worker_handler.lambda_handler"
        and resource["Properties"].get("FunctionName")
        == "careervp-vpr-sqs-worker-lambda-dev"
    ]
    assert len(matches) == 1
    return _lambda_role_logical_id(matches[0])


def test_start_vpr_has_no_short_heartbeat(synthesized_template: Template) -> None:
    definition = _state_machine_definition(synthesized_template)

    assert "StartVPR" in definition
    assert "HeartbeatSecondsPath" not in definition
    assert 'HeartbeatSeconds":300' not in definition


def test_vpr_worker_role_has_send_task_response(synthesized_template: Template) -> None:
    role_logical_id = _vpr_sqs_worker_role(synthesized_template)
    actions = {
        action
        for statement in _policy_statements_for_role(
            synthesized_template, role_logical_id
        )
        for action in _actions(statement)
    }

    assert "states:SendTaskSuccess" in actions
    assert "states:SendTaskFailure" in actions


def test_no_dependency_cycle_after_grant(service_stack: ServiceStack) -> None:
    Template.from_stack(service_stack)
