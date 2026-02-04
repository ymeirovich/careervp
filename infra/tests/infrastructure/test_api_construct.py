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
