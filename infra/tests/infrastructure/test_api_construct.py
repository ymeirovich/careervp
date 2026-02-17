from __future__ import annotations

from aws_cdk.assertions import Template

from careervp import constants


def test_company_research_lambda_configuration(synthesized_template: Template) -> None:
    """Ensure the new Lambda uses the required handler, timeout, and memory settings."""
    all_functions = synthesized_template.find_resources("AWS::Lambda::Function")
    functions = {
        logical_id: props
        for logical_id, props in all_functions.items()
        if props["Properties"].get("Handler")
        == "careervp.handlers.company_research_handler.lambda_handler"
    }
    assert functions, "Company research Lambda was not synthesized"

    # Validate key properties on the single function
    lambda_props = next(iter(functions.values()))
    assert (
        lambda_props["Properties"]["FunctionName"]
        == "careervp-company-research-lambda-dev"
    )
    assert lambda_props["Properties"]["Timeout"] == 60
    assert lambda_props["Properties"]["MemorySize"] == 512


def test_company_research_api_route_exists(synthesized_template: Template) -> None:
    """Validate that API Gateway defines the /api/company-research POST route."""
    resources = synthesized_template.find_resources("AWS::ApiGateway::Resource")
    company_research_ids = {
        logical_id
        for logical_id, props in resources.items()
        if props["Properties"].get("PathPart") == constants.GW_RESOURCE_COMPANY_RESEARCH
    }
    assert company_research_ids, "API Gateway resource /company-research missing"

    # confirm there is a POST method associated with the company research Lambda
    methods = synthesized_template.find_resources("AWS::ApiGateway::Method")
    company_research_methods = [
        logical_id
        for logical_id, props in methods.items()
        if props["Properties"].get("HttpMethod") == "POST"
        and props["Properties"].get("ResourceId", {}).get("Ref") in company_research_ids
    ]
    assert company_research_methods, "No POST method found for /company-research"


def test_llm_cache_table_configuration(synthesized_template: Template) -> None:
    """Ensure LLM cache table is created with TTL and on-demand billing."""
    tables = synthesized_template.find_resources("AWS::DynamoDB::GlobalTable")
    llm_cache_tables = [
        props
        for props in tables.values()
        if props["Properties"].get("TableName") == "careervp-llm-cache-dev"
    ]
    assert llm_cache_tables, "LLM cache table was not synthesized"

    table_props = llm_cache_tables[0]["Properties"]
    assert table_props["BillingMode"] == "PAY_PER_REQUEST"
    ttl_spec = table_props.get("TimeToLiveSpecification")
    assert ttl_spec is not None
    assert ttl_spec["AttributeName"] == "expires_at"
    assert ttl_spec["Enabled"] is True


def test_lambda_role_has_llm_cache_permissions(synthesized_template: Template) -> None:
    """Ensure Lambda execution role has least-privilege LLM cache read/write access."""
    tables = synthesized_template.find_resources("AWS::DynamoDB::GlobalTable")
    llm_cache_logical_ids = [
        logical_id
        for logical_id, props in tables.items()
        if props["Properties"].get("TableName") == "careervp-llm-cache-dev"
    ]
    assert llm_cache_logical_ids, "LLM cache table logical ID not found"
    llm_cache_logical_id = llm_cache_logical_ids[0]

    roles = synthesized_template.find_resources("AWS::IAM::Role")
    cache_policy_found = False

    for role in roles.values():
        inline_policies = role["Properties"].get("Policies", [])
        if not isinstance(inline_policies, list):
            continue

        for policy in inline_policies:
            if policy.get("PolicyName") != "llm_cache_table":
                continue

            statements = policy["PolicyDocument"]["Statement"]
            for statement in statements:
                actions = statement.get("Action", [])
                if not isinstance(actions, list):
                    continue

                required_actions = {
                    "dynamodb:GetItem",
                    "dynamodb:PutItem",
                    "dynamodb:DeleteItem",
                }
                if not required_actions.issubset(set(actions)):
                    continue

                resource = statement.get("Resource")
                if (
                    isinstance(resource, dict)
                    and resource.get("Fn::GetAtt", [None, None])[0]
                    == llm_cache_logical_id
                    and resource.get("Fn::GetAtt", [None, None])[1] == "Arn"
                ):
                    cache_policy_found = True
                    break
            if cache_policy_found:
                break
        if cache_policy_found:
            break

    assert cache_policy_found, (
        "No least-privilege IAM policy found for LLM cache table access"
    )
