from __future__ import annotations

from typing import Any, Mapping, cast

from aws_cdk.assertions import Template


SUBMIT_LAMBDAS: tuple[tuple[str, str], ...] = (
    (
        "careervp.handlers.vpr_submit_handler.lambda_handler",
        "careervp-vpr-submit-lambda-dev",
    ),
    (
        "careervp.handlers.cover_letter_submit_handler.lambda_handler",
        "careervp-cover-letter-api-lambda-dev",
    ),
    (
        "careervp.handlers.interview_prep_submit_handler.lambda_handler",
        "careervp-interview-prep-api-lambda-dev",
    ),
    (
        "careervp.handlers.cv_tailoring_handler.handler",
        "careervp-cvtailor-lambda-dev",
    ),
)


def _resources(
    template: Template, resource_type: str
) -> Mapping[str, Mapping[str, Any]]:
    return template.find_resources(resource_type)


def _lambda_by_handler_and_name(
    template: Template, handler: str, function_name: str
) -> Mapping[str, Any]:
    matches = [
        resource
        for resource in _resources(template, "AWS::Lambda::Function").values()
        if resource["Properties"].get("Handler") == handler
        and resource["Properties"].get("FunctionName") == function_name
    ]
    assert len(matches) == 1, (
        f"Expected one Lambda with handler {handler} and name {function_name}, found {len(matches)}"
    )
    return matches[0]


def _lambda_role_logical_id(lambda_resource: Mapping[str, Any]) -> str:
    role_ref = lambda_resource["Properties"].get("Role")
    if isinstance(role_ref, dict) and isinstance(role_ref.get("Fn::GetAtt"), list):
        logical_id = role_ref["Fn::GetAtt"][0]
        if isinstance(logical_id, str) and logical_id:
            return logical_id
    raise AssertionError("Lambda role reference could not be resolved from template")


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


def _actions(statement: Mapping[str, Any]) -> list[str]:
    actions = statement.get("Action", [])
    if isinstance(actions, str):
        return [actions]
    if isinstance(actions, list):
        return [action for action in actions if isinstance(action, str)]
    return []


def _resource_refs_artifact_chain(resource: Any) -> bool:
    return "ArtifactChainStateMachine" in str(resource)


def test_submit_lambdas_have_chain_env_and_artifacts_table(
    synthesized_template: Template,
) -> None:
    for handler, function_name in SUBMIT_LAMBDAS:
        lambda_resource = _lambda_by_handler_and_name(
            synthesized_template, handler, function_name
        )
        env_vars = cast(
            dict[str, Any],
            lambda_resource["Properties"].get("Environment", {}).get("Variables", {}),
        )

        assert "ARTIFACTS_TABLE_NAME" in env_vars, (
            f"{function_name} missing ARTIFACTS_TABLE_NAME"
        )
        assert env_vars.get("ARTIFACT_CHAIN_ENABLED") == "true", (
            f"{function_name} must enable artifact chain in dev"
        )
        assert _resource_refs_artifact_chain(
            env_vars.get("STEP_FUNCTIONS_CHAIN_ARN")
        ), f"{function_name} missing chain ARN env"


def test_submit_lambda_roles_can_start_chain_on_specific_arn(
    synthesized_template: Template,
) -> None:
    for handler, function_name in SUBMIT_LAMBDAS:
        lambda_resource = _lambda_by_handler_and_name(
            synthesized_template, handler, function_name
        )
        role_logical_id = _lambda_role_logical_id(lambda_resource)
        statements = _policy_statements_for_role(synthesized_template, role_logical_id)
        matching = [
            statement
            for statement in statements
            if "states:StartExecution" in _actions(statement)
            and _resource_refs_artifact_chain(statement.get("Resource"))
        ]

        assert matching, (
            f"{function_name} role missing states:StartExecution on artifact chain ARN"
        )
        assert all(statement.get("Resource") != "*" for statement in matching)
