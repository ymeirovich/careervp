from __future__ import annotations

import json
from typing import Any, Mapping

from aws_cdk.assertions import Template


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


def _actions(statement: Mapping[str, Any]) -> list[str]:
    actions = statement.get("Action", [])
    if isinstance(actions, str):
        return [actions]
    if isinstance(actions, list):
        return [action for action in actions if isinstance(action, str)]
    return []


def test_cv_tailoring_queue_removed(synthesized_template: Template) -> None:
    queues = _resources(synthesized_template, "AWS::SQS::Queue")
    queue_names = json.dumps(
        [queue["Properties"].get("QueueName") for queue in queues.values()]
    )

    assert "cv-tailoring" not in queue_names


def test_start_cv_tailoring_is_lambda_invoke(features_template: Template) -> None:
    definition = _state_machine_definition(features_template)

    assert "StartCVTailoring" in definition
    assert "function:careervp-cvtailor-lambda-dev" in definition
    assert "states:::sqs:sendMessage.waitForTaskToken" in definition
    assert "cv-tailoring" not in definition


def test_state_machine_can_invoke_cv_worker(features_template: Template) -> None:
    policies = _resources(features_template, "AWS::IAM::Policy")
    found = False
    for policy in policies.values():
        statements = policy["Properties"].get("PolicyDocument", {}).get("Statement", [])
        if isinstance(statements, dict):
            statements = [statements]
        if not isinstance(statements, list):
            continue
        for statement in statements:
            if not isinstance(statement, dict):
                continue
            if "lambda:InvokeFunction" not in _actions(statement):
                continue
            if "careervp-cvtailor-lambda-dev" in json.dumps(statement.get("Resource")):
                found = True
                break
        if found:
            break

    assert found, (
        "State machine role missing lambda:InvokeFunction permission for CV tailoring Lambda"
    )
