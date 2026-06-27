from __future__ import annotations

import json
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


def test_tavily_ssm_env_injected_into_company_research_lambdas(
    synthesized_template: Template,
) -> None:
    expected = "/careervp/dev/tavily-api-key"
    cr_handler_env = _lambda_env_by_handler(
        synthesized_template,
        "careervp.handlers.company_research_handler.lambda_handler",
    )
    cr_worker_env = _lambda_env_by_handler(
        synthesized_template,
        "careervp.handlers.company_research_worker_handler.lambda_handler",
    )

    assert cr_handler_env["TAVILY_API_KEY_SSM_PARAM"] == expected
    assert cr_worker_env["TAVILY_API_KEY_SSM_PARAM"] == expected
    assert cr_worker_env["COMPANY_RESEARCH_CACHE_TABLE_NAME"]


def test_company_research_nested_stack_scopes_tavily_and_cache_policy(
    company_research_template: Template,
) -> None:
    policies = company_research_template.find_resources("AWS::IAM::Policy")
    policy_blob = json.dumps(policies)

    assert "ssm:GetParameter" in policy_blob
    assert "tavily-api-key" in policy_blob
    assert 'Resource": "*' not in policy_blob
    assert "dynamodb:GetItem" in policy_blob
    assert "dynamodb:PutItem" in policy_blob
    assert "dynamodb:UpdateItem" in policy_blob
    assert "dynamodb:Query" in policy_blob


def test_tavily_observability_alarms_have_sns_actions(
    company_research_template: Template,
) -> None:
    alarms = company_research_template.find_resources("AWS::CloudWatch::Alarm")
    by_name = {
        props["Properties"].get("AlarmName"): props["Properties"]
        for props in alarms.values()
    }

    expected_names = {
        "careervp-tavily-search-failure-dev",
        "careervp-company-research-all-sources-failed-dev",
    }
    assert expected_names <= set(by_name)

    for alarm_name in expected_names:
        alarm = by_name[alarm_name]
        assert alarm["Namespace"] == "careervp_kpi"
        assert alarm["AlarmActions"], f"{alarm_name} missing SNS alarm action"
