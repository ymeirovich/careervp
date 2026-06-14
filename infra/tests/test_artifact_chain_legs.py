from __future__ import annotations

import json
from typing import Any, Mapping

import pytest
from aws_cdk import App, Environment
from aws_cdk.assertions import Template

from careervp.naming_utils import NamingUtils
from careervp.service_stack import ServiceStack


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
    return json.dumps(matches[0]["Properties"]["DefinitionString"]).replace('\\"', '"')


def _queue_names(template: Template) -> str:
    return json.dumps(
        [
            queue["Properties"].get("QueueName")
            for queue in _resources(template, "AWS::SQS::Queue").values()
        ]
    )


def _lambda_role_logical_id(lambda_resource: Mapping[str, Any]) -> str:
    role_ref = lambda_resource["Properties"].get("Role")
    if isinstance(role_ref, dict) and isinstance(role_ref.get("Fn::GetAtt"), list):
        logical_id = role_ref["Fn::GetAtt"][0]
        if isinstance(logical_id, str) and logical_id:
            return logical_id
    raise AssertionError("Lambda role reference could not be resolved from template")


def _lambda_role_by_handler_and_name(
    template: Template, handler: str, function_name: str
) -> str:
    matches = [
        resource
        for resource in _resources(template, "AWS::Lambda::Function").values()
        if resource["Properties"].get("Handler") == handler
        and resource["Properties"].get("FunctionName") == function_name
    ]
    assert len(matches) == 1
    return _lambda_role_logical_id(matches[0])


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


def test_generate_final_artifacts_parallel_follows_cv_tailoring(
    synthesized_template: Template,
) -> None:
    definition = _state_machine_definition(synthesized_template)

    assert "StartCVTailoring" in definition
    assert "GenerateFinalArtifacts" in definition
    assert '"Type":"Parallel"' in definition
    assert '"Next":"GenerateFinalArtifacts"' in definition
    assert '"ResultPath":"$.final_artifacts_result"' in definition


def test_cover_letter_branch_uses_task_token_and_full_context(
    synthesized_template: Template,
) -> None:
    definition = _state_machine_definition(synthesized_template)

    assert "StartCoverLetter" in definition
    assert "careervp-cover-letter-jobs-queue-dev" in _queue_names(synthesized_template)
    assert "states:::sqs:sendMessage.waitForTaskToken" in definition
    assert '"vpr_id.$":"$.vpr_result.vpr_id"' in definition
    assert (
        '"company_context.$":"$.company_research_result.company_context"' in definition
    )
    assert '"task_token.$":"$$.Task.Token"' in definition


def test_interview_prep_branch_uses_task_token_and_vpr_id(
    synthesized_template: Template,
) -> None:
    definition = _state_machine_definition(synthesized_template)

    assert "StartInterviewPrep" in definition
    assert "careervp-interview-prep-jobs-queue-dev" in _queue_names(
        synthesized_template
    )
    assert '"vpr_id.$":"$.vpr_result.vpr_id"' in definition
    assert '"task_token.$":"$$.Task.Token"' in definition


def test_final_artifact_failures_route_to_artifact_failure_handlers(
    synthesized_template: Template,
) -> None:
    definition = _state_machine_definition(synthesized_template)

    assert "HandleCoverLetterFailure" in definition
    assert '"artifact_type":"cover_letter"' in definition
    assert "HandleInterviewPrepFailure" in definition
    assert '"artifact_type":"interview_prep"' in definition
    assert '"ResultPath":"$.cover_letter_error"' in definition
    assert '"ResultPath":"$.interview_prep_error"' in definition
    assert '"ResultPath":"$.final_artifacts_error"' in definition


def test_worker_task_response_iam_is_scoped_and_template_has_no_cycle(
    service_stack: ServiceStack,
    synthesized_template: Template,
) -> None:
    Template.from_stack(service_stack)
    for handler, function_name in (
        (
            "careervp.handlers.cover_letter_handler.lambda_handler",
            "careervp-cover-letter-worker-lambda-dev",
        ),
        (
            "careervp.handlers.interview_prep_handler.lambda_handler",
            "careervp-interview-prep-worker-lambda-dev",
        ),
    ):
        role_id = _lambda_role_by_handler_and_name(
            synthesized_template, handler, function_name
        )
        statements = _policy_statements_for_role(synthesized_template, role_id)
        task_response_statements = [
            statement
            for statement in statements
            if {"states:SendTaskSuccess", "states:SendTaskFailure"}.issubset(
                set(_actions(statement))
            )
        ]
        assert len(task_response_statements) == 1
        assert all("states:*" not in _actions(statement) for statement in statements)
        resource = json.dumps(task_response_statements[0].get("Resource"))
        assert "*" not in resource
        assert "ArtifactChainStateMachine" in resource
