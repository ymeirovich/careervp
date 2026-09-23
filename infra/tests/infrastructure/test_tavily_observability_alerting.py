from __future__ import annotations

from collections.abc import Mapping
from typing import Any, cast

from aws_cdk.assertions import Template


def _lambda_env_by_handler(template: Template, handler: str) -> Mapping[str, Any]:
    functions = template.find_resources("AWS::Lambda::Function")
    matches = [
        resource["Properties"].get("Environment", {}).get("Variables", {})
        for resource in functions.values()
        if resource["Properties"].get("Handler") == handler
    ]
    assert matches, f"Lambda handler not synthesized: {handler}"
    return cast(Mapping[str, Any], matches[0])


def _company_research_policy_statements(
    company_research_template: Template,
) -> list[dict[str, Any]]:
    policies = company_research_template.find_resources("AWS::IAM::Policy")
    statements: list[dict[str, Any]] = []
    for policy in policies.values():
        policy_statements = (
            policy["Properties"].get("PolicyDocument", {}).get("Statement", [])
        )
        if isinstance(policy_statements, dict):
            statements.append(cast(dict[str, Any], policy_statements))
        elif isinstance(policy_statements, list):
            statements.extend(
                cast(dict[str, Any], statement)
                for statement in policy_statements
                if isinstance(statement, dict)
            )
    assert statements, (
        "No IAM policy statements synthesized in company-research nested stack"
    )
    return statements


def _actions(statement: dict[str, Any]) -> list[str]:
    actions = statement.get("Action", [])
    if isinstance(actions, str):
        return [actions]
    if isinstance(actions, list):
        return [action for action in actions if isinstance(action, str)]
    return []


def _resources(statement: dict[str, Any]) -> list[Any]:
    resources = statement.get("Resource", [])
    if isinstance(resources, list):
        return resources
    return [resources]


def _alarms_by_name(company_research_template: Template) -> dict[str, dict[str, Any]]:
    alarms = company_research_template.find_resources("AWS::CloudWatch::Alarm")
    return {
        props["Properties"].get("AlarmName"): cast(dict[str, Any], props["Properties"])
        for props in alarms.values()
    }


def test_cr_handler_and_worker_have_tavily_env_var(
    features_template: Template,
) -> None:
    expected = "/careervp/dev/tavily-api-key"
    cr_handler_env = _lambda_env_by_handler(
        features_template,
        "careervp.handlers.company_research_handler.lambda_handler",
    )
    cr_worker_env = _lambda_env_by_handler(
        features_template,
        "careervp.handlers.company_research_worker_handler.lambda_handler",
    )

    assert cr_handler_env["TAVILY_API_KEY_SSM_PARAM"] == expected
    assert cr_worker_env["TAVILY_API_KEY_SSM_PARAM"] == expected


def test_cr_worker_has_cache_table_env(features_template: Template) -> None:
    cr_worker_env = _lambda_env_by_handler(
        features_template,
        "careervp.handlers.company_research_worker_handler.lambda_handler",
    )
    assert cr_worker_env["COMPANY_RESEARCH_CACHE_TABLE_NAME"]


def test_ssm_get_parameter_scoped_to_tavily_arn(
    company_research_template: Template,
) -> None:
    statements = _company_research_policy_statements(company_research_template)
    matches = [
        statement
        for statement in statements
        if _actions(statement) == ["ssm:GetParameter"]
    ]
    assert matches, (
        "Expected a scoped ssm:GetParameter statement for the Tavily parameter"
    )
    assert matches == [
        {
            "Effect": "Allow",
            "Action": "ssm:GetParameter",
            "Resource": "arn:aws:ssm:us-east-1:123456789012:parameter/careervp/dev/tavily-api-key",
        }
    ]


def test_no_wildcard_iam_added(company_research_template: Template) -> None:
    statements = _company_research_policy_statements(company_research_template)
    for statement in statements:
        assert "ssm:*" not in _actions(statement)
        for resource in _resources(statement):
            assert resource != "*"


def test_cr_worker_can_read_write_cache_table(
    company_research_template: Template,
) -> None:
    statements = _company_research_policy_statements(company_research_template)
    ddb_statements = [
        statement
        for statement in statements
        if {"dynamodb:GetItem", "dynamodb:PutItem", "dynamodb:UpdateItem"}
        <= set(_actions(statement))
    ]
    assert ddb_statements, (
        "Expected cache-table read/write statement on the CR worker role"
    )
    for statement in ddb_statements:
        resources = _resources(statement)
        assert len(resources) == 1
        resource = resources[0]
        assert isinstance(resource, dict)
        assert "Ref" in resource


def test_tavily_failure_alarm_exists(
    company_research_template: Template,
) -> None:
    alarm = _alarms_by_name(company_research_template)[
        "careervp-tavily-search-failure-dev"
    ]
    assert alarm["MetricName"] == "TavilySearchFailure"
    assert alarm["Namespace"] == "careervp_kpi"
    assert alarm["AlarmActions"]


def test_all_sources_failed_alarm_exists(
    company_research_template: Template,
) -> None:
    alarm = _alarms_by_name(company_research_template)[
        "careervp-company-research-all-sources-failed-dev"
    ]
    assert alarm["MetricName"] == "CompanyResearchAllSourcesFailed"
    assert alarm["Namespace"] == "careervp_kpi"
    assert alarm["AlarmActions"]


def test_alarms_reference_a_topic(company_research_template: Template) -> None:
    alarms = _alarms_by_name(company_research_template)
    for alarm_name in (
        "careervp-tavily-search-failure-dev",
        "careervp-company-research-all-sources-failed-dev",
    ):
        actions = alarms[alarm_name]["AlarmActions"]
        assert actions, f"{alarm_name} missing SNS alarm action"
        first_action = actions[0]
        assert isinstance(first_action, dict)
        assert "Ref" in first_action


def test_template_synthesizes_without_cycle(
    company_research_template: Template,
) -> None:
    assert company_research_template.find_resources("AWS::IAM::Policy")
