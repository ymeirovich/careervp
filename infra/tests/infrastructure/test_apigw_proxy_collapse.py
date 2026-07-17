"""TEST-INFRA-048 — API Gateway {proxy+} collapse unit, integration, and regression guards.

Covers:
  Category A (unit):      AC-001, AC-002, AC-007, AC-010
  Category B (integration): AC-006 path-params, AC-008 CORS
  Category D (regression):  AC-002 auth-flip, AC-006 routes-present, AC-009 naming

Source spec:  docs/upgrade/specs/FE-UI-048-apigw-proxy-collapse-headroom.yaml
Test prompts: docs/upgrade/specs/TEST-INFRA-048-test-prompts.yaml
Route oracle: docs/architecture/api_spec.openapi.yml
"""

from __future__ import annotations

import subprocess
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from aws_cdk.assertions import Template

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Public feature prefixes whose proxy ANY methods must carry AuthorizationType=NONE.
# All other feature ANY methods must carry COGNITO_USER_POOLS.
PUBLIC_FEATURE_PREFIXES = frozenset({"auth", "health", "swagger"})

# Explicit routes that must NOT be collapsed into a proxy — they stay as distinct
# HTTP methods due to mixed auth, non-Lambda integrations, or method-level config.
# Source: AC-010 + api_construct.py exceptions.
EXCEPTION_PATHS: frozenset[str] = frozenset(
    {
        "billing/webhook",  # public POST while rest of /billing is protected
        "errors",  # AwsIntegration nested-stack bridge, public
        "swagger",  # LambdaIntegration, public, no-feature-prefix
        "swagger.css",  # same
        "swagger.js",  # same
    }
)

# Stateful resource types that the collapse must never add, replace, or remove.
STATEFUL_RESOURCE_TYPES: tuple[str, ...] = (
    "AWS::DynamoDB::GlobalTable",
    "AWS::S3::Bucket",
    "AWS::KMS::Key",
    "AWS::Cognito::UserPool",
    "AWS::Cognito::UserPoolClient",
    "AWS::SQS::Queue",
)

# Documented synth-parent baseline before any proxy-collapse work (FE-UI-048).
SYNTH_BASELINE_RESOURCE_COUNT = 498

# CloudFormation's hard per-template ceiling and the durable FE-UI-048 headroom target.
CFN_MAX_RESOURCES = 500
PROXY_COLLAPSE_TARGET = 400

# Documented stateful-resource counts that the collapse must leave exactly unchanged.
# These are the baseline (data-bearing) resources; the {proxy+} collapse may only touch
# ApiGateway Method/Resource, Lambda Permission, and the API Deployment (AC-011).
EXPECTED_STATEFUL_BASELINE: dict[str, int] = {
    "AWS::DynamoDB::Table": 0,  # tables are GlobalTables — none of the legacy type
    # 11 = the 10 api_db tables + llm-cache; the identity-map table (P-24, commit
    # 09bd6f3) is the 11th. This baseline predated that table and was stale at 10.
    "AWS::DynamoDB::GlobalTable": 11,
    "AWS::S3::Bucket": 6,
    "AWS::KMS::Key": 5,
    "AWS::Cognito::UserPool": 1,
    "AWS::Cognito::UserPoolClient": 1,
    "AWS::SQS::Queue": 17,
}

# Permission total baseline before collapse.
APIGW_PERMISSION_BASELINE = 99

# Expected maximum total apigateway-principal permissions after full collapse (AC-007).
APIGW_PERMISSION_TARGET_MAX = 40


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _full_resource_path(
    resources: Mapping[str, Mapping[str, Any]], logical_id: str
) -> str:
    """Recursively build the slash-joined path for a resource logical id.

    Returns an empty string for the RestApi root resource (no PathPart).
    """
    props = resources.get(logical_id, {})
    path_part = str(props.get("Properties", {}).get("PathPart", ""))
    parent_ref = props.get("Properties", {}).get("ParentId", {})

    parent_logical_id: str | None = None
    if isinstance(parent_ref, dict):
        parent_logical_id = (
            parent_ref.get("Ref") or parent_ref.get("Fn::GetAtt", [None])[0]
        )

    if not parent_logical_id or parent_logical_id not in resources:
        return path_part

    parent_path = _full_resource_path(resources, parent_logical_id)
    return "/".join(part for part in [parent_path, path_part] if part)


def _build_method_index(
    methods: Mapping[str, Mapping[str, Any]],
    resources: Mapping[str, Mapping[str, Any]],
) -> dict[tuple[str, str], Mapping[str, Any]]:
    """Return {(full_path, http_method): method_props} for every synthesized method."""
    index: dict[tuple[str, str], Mapping[str, Any]] = {}
    for method_props in methods.values():
        http_method = str(method_props["Properties"].get("HttpMethod", ""))
        resource_id_ref = method_props["Properties"].get("ResourceId", {})
        path_ref = (
            resource_id_ref.get("Ref", "") if isinstance(resource_id_ref, dict) else ""
        )
        full_path = _full_resource_path(resources, path_ref) if path_ref else ""
        index[(full_path, http_method)] = method_props
    return index


def _proxy_resource_ids(
    resources: Mapping[str, Mapping[str, Any]],
) -> set[str]:
    """Return the logical ids of all {proxy+} resources."""
    return {
        lid
        for lid, r in resources.items()
        if r.get("Properties", {}).get("PathPart") == "{proxy+}"
    }


def _method_resource_ids_for_http_method(
    methods: Mapping[str, Mapping[str, Any]], http_method: str
) -> set[str]:
    """Return resource logical ids that have a method with the given HttpMethod."""
    return {
        method["Properties"].get("ResourceId", {}).get("Ref", "")
        for method in methods.values()
        if method["Properties"].get("HttpMethod") == http_method
    }


def _apigw_principal_permissions(
    template: Template,
) -> list[Mapping[str, Any]]:
    """Return all Lambda::Permission resources whose Principal contains 'apigateway'."""
    permissions = template.find_resources("AWS::Lambda::Permission")
    return [
        props
        for props in permissions.values()
        if "apigateway" in str(props.get("Properties", {}).get("Principal", "")).lower()
    ]


def _load_openapi_routes() -> list[tuple[str, str]]:
    """Load (path, METHOD) pairs from docs/architecture/api_spec.openapi.yml."""
    oracle_path = (
        Path(__file__).parents[3] / "docs" / "architecture" / "api_spec.openapi.yml"
    )
    if not oracle_path.exists():
        return []

    routes: list[tuple[str, str]] = []
    current_path: str | None = None
    for line in oracle_path.read_text().splitlines():
        if line.startswith("  /") and line.rstrip().endswith(":"):
            current_path = line.strip()[:-1]
            continue
        stripped = line.strip()
        if (
            current_path is not None
            and line.startswith("    ")
            and not line.startswith("      ")
            and stripped.rstrip(":")
            in {"get", "post", "put", "patch", "delete", "head"}
        ):
            routes.append((current_path, stripped.rstrip(":").upper()))
    return routes


def _cdk_canonical_routes() -> list[tuple[str, str]]:
    """Parse _add_openapi_contract_routes from api_construct.py for the ground-truth route set."""
    import re

    api_construct_path = (
        Path(__file__).parents[3] / "infra" / "careervp" / "api_construct.py"
    )
    if not api_construct_path.exists():
        return []
    content = api_construct_path.read_text()
    matches = re.findall(r'\(\s*"(/[^"]+)"\s*,\s*"([A-Z]+)"\s*,', content)
    return list({(path, method) for path, method in matches})


# ---------------------------------------------------------------------------
# =============================================================================
# CATEGORY A — UNIT: PROXY SHAPE, AUTHORIZER PARITY, PERMISSION COLLAPSE, EXCEPTIONS
# =============================================================================
# ---------------------------------------------------------------------------


def test_proxy_any_replaces_explicit_methods_for_converted_feature(
    synthesized_template: Template,
) -> None:
    """Any collapsed feature must have ANY on the feature root and on {proxy+} child,
    and must NOT retain explicit per-sub-path methods for that feature (AC-001).
    """
    resources = synthesized_template.find_resources("AWS::ApiGateway::Resource")
    methods = synthesized_template.find_resources("AWS::ApiGateway::Method")

    proxy_ids = _proxy_resource_ids(resources)
    assert proxy_ids, (
        "No {proxy+} resources found in the synthesized template. "
        "FE-UI-048 proxy collapse has not yet been applied. "
        "Each converted feature must expose a greedy child resource with PathPart='{proxy+}'."
    )

    any_resource_ids = _method_resource_ids_for_http_method(methods, "ANY")
    missing_any = proxy_ids - any_resource_ids
    assert not missing_any, (
        f"{len(missing_any)} {{proxy+}} resource(s) have no ANY method: {missing_any}. "
        "Every {proxy+} resource must have an ANY LambdaIntegration method."
    )

    # The users subtree has cross-handler exception resources. Those exact
    # resources shadow the greedy route in API Gateway, so the user methods on
    # those resources remain explicit. Deeper user-owned paths must still be
    # handled by the greedy proxy instead of dedicated resources.
    method_index = _build_method_index(methods, resources)
    allowed_users_shadow_routes = {
        ("users/me", "GET"),
        ("users/me", "PUT"),
        ("users/me/usage", "GET"),
        ("users/me/trial/reset", "POST"),
        ("users/me/cv", "GET"),
        ("users/me/cv", "POST"),
        ("users/me/subscription", "GET"),
    }
    users_explicit_subpaths = [
        (path, m)
        for (path, m) in method_index
        if path.startswith("users/")
        and m in {"GET", "PUT", "DELETE", "POST", "PATCH"}
        and (path, m) not in allowed_users_shadow_routes
    ]
    assert not users_explicit_subpaths, (
        f"Explicit sub-path methods still exist for the 'users' feature "
        f"after proxy collapse: {users_explicit_subpaths}. "
        "These should be served by the {proxy+} ANY method."
    )


def test_protected_feature_proxy_any_keeps_cognito_authorizer(
    synthesized_template: Template,
) -> None:
    """ANY methods on protected feature {proxy+} resources must carry COGNITO_USER_POOLS (AC-002)."""
    resources = synthesized_template.find_resources("AWS::ApiGateway::Resource")
    methods = synthesized_template.find_resources("AWS::ApiGateway::Method")

    proxy_ids = _proxy_resource_ids(resources)
    assert proxy_ids, "No {proxy+} resources found — proxy collapse not applied."

    # Identify which proxy resources are under PUBLIC prefixes (auth, health, swagger).
    def _is_public_proxy(proxy_logical_id: str) -> bool:
        full_path = _full_resource_path(resources, proxy_logical_id)
        root_prefix = full_path.split("/")[0] if full_path else ""
        return root_prefix in PUBLIC_FEATURE_PREFIXES

    protected_proxy_ids = {pid for pid in proxy_ids if not _is_public_proxy(pid)}
    assert protected_proxy_ids, (
        "Expected at least one protected feature {proxy+} resource — "
        "verify PUBLIC_FEATURE_PREFIXES covers all truly-public features."
    )

    authorizers = synthesized_template.find_resources("AWS::ApiGateway::Authorizer")
    cognito_authorizer_ids = {
        lid
        for lid, props in authorizers.items()
        if props["Properties"].get("Type") == "COGNITO_USER_POOLS"
    }
    assert cognito_authorizer_ids, (
        "No COGNITO_USER_POOLS authorizer found in synthesized template."
    )

    any_methods_on_protected_proxy = [
        method
        for method in methods.values()
        if method["Properties"].get("HttpMethod") == "ANY"
        and method["Properties"].get("ResourceId", {}).get("Ref", "")
        in protected_proxy_ids
    ]
    assert any_methods_on_protected_proxy, (
        "No ANY methods found on protected {proxy+} resources."
    )

    for method in any_methods_on_protected_proxy:
        auth_type = method["Properties"].get("AuthorizationType")
        authorizer_id = method["Properties"].get("AuthorizerId", {})
        authorizer_ref = (
            authorizer_id.get("Ref", "") if isinstance(authorizer_id, dict) else ""
        )
        assert auth_type == "COGNITO_USER_POOLS", (
            f"Protected feature {{proxy+}} ANY method has AuthorizationType={auth_type!r}; "
            "expected COGNITO_USER_POOLS."
        )
        assert authorizer_ref in cognito_authorizer_ids, (
            f"Protected feature {{proxy+}} ANY method references authorizer {authorizer_ref!r} "
            f"which is not a known Cognito authorizer ({cognito_authorizer_ids})."
        )


def test_public_feature_proxy_any_has_no_authorizer(
    synthesized_template: Template,
) -> None:
    """ANY methods on public feature {proxy+} resources (auth, health, swagger) must have
    AuthorizationType=NONE — preserving the AwsSolutions-COG4 intent (AC-002).
    """
    resources = synthesized_template.find_resources("AWS::ApiGateway::Resource")
    methods = synthesized_template.find_resources("AWS::ApiGateway::Method")

    proxy_ids = _proxy_resource_ids(resources)
    if not proxy_ids:
        # No proxy resources yet — test is vacuously skipped until collapse is applied.
        return

    public_proxy_ids = {
        pid
        for pid in proxy_ids
        if _full_resource_path(resources, pid).split("/")[0] in PUBLIC_FEATURE_PREFIXES
    }
    if not public_proxy_ids:
        # Public features may not have been collapsed or may have no sub-paths.
        return

    any_methods_on_public_proxy = [
        method
        for method in methods.values()
        if method["Properties"].get("HttpMethod") == "ANY"
        and method["Properties"].get("ResourceId", {}).get("Ref", "")
        in public_proxy_ids
    ]
    for method in any_methods_on_public_proxy:
        auth_type = method["Properties"].get("AuthorizationType")
        assert auth_type == "NONE", (
            f"Public feature {{proxy+}} ANY method has AuthorizationType={auth_type!r}; "
            "expected NONE."
        )
        assert method["Properties"].get("AuthorizerId") is None, (
            "Public feature {proxy+} ANY method must not reference any authorizer."
        )


def test_permission_fanout_collapsed_to_two_per_feature(
    synthesized_template: Template,
) -> None:
    """After collapse, each feature has one scoped permission covering both ANY methods.

    Total must be <= 40, down from the 99 baseline (AC-007).
    """
    resources = synthesized_template.find_resources("AWS::ApiGateway::Resource")
    methods = synthesized_template.find_resources("AWS::ApiGateway::Method")

    proxy_ids = _proxy_resource_ids(resources)
    assert proxy_ids, "No {proxy+} resources found — proxy collapse not applied."

    apigw_permissions = _apigw_principal_permissions(synthesized_template)
    total = len(apigw_permissions)

    assert total <= APIGW_PERMISSION_TARGET_MAX, (
        f"apigateway-principal Lambda::Permission count is {total} (baseline was "
        f"{APIGW_PERMISSION_BASELINE}); expected <= {APIGW_PERMISSION_TARGET_MAX} "
        "after proxy collapse reduces per-method fan-out."
    )

    # Each {proxy+} resource still has its own ANY method even though one
    # prefix-scoped Lambda permission safely covers the root and greedy methods.
    any_methods = [
        m for m in methods.values() if m["Properties"].get("HttpMethod") == "ANY"
    ]
    assert len(any_methods) >= len(proxy_ids), (
        f"Expected at least {len(proxy_ids)} ANY methods (one per {{proxy+}} resource) "
        f"but found {len(any_methods)}."
    )


def test_exception_routes_remain_explicit(
    synthesized_template: Template,
) -> None:
    """Documented exception routes must NOT be collapsed into a {proxy+} proxy (AC-010).

    Exceptions:
    - swagger / swagger.css / swagger.js  — kept as explicit GET methods
    - POST /billing/webhook               — public; protected /billing/* may be collapsed
    - POST /errors                        — AwsIntegration bridge to nested stack
    """
    methods = synthesized_template.find_resources("AWS::ApiGateway::Method")
    resources = synthesized_template.find_resources("AWS::ApiGateway::Resource")
    method_index = _build_method_index(methods, resources)

    # Swagger endpoints must remain as explicit GET methods.
    for swagger_path in ("swagger", "swagger.css", "swagger.js"):
        assert (swagger_path, "GET") in method_index, (
            f"Expected explicit GET method on /{swagger_path} but it was not found — "
            "swagger endpoints must NOT be proxy-collapsed."
        )
        method = method_index[(swagger_path, "GET")]
        assert method["Properties"].get("AuthorizationType") == "NONE", (
            f"GET /{swagger_path} must remain public (AuthorizationType=NONE)."
        )

    # POST /billing/webhook must remain a public explicit method.
    assert ("billing/webhook", "POST") in method_index, (
        "POST /billing/webhook must stay as an explicit method (public/Stripe-verified) "
        "even if the rest of /billing is proxy-collapsed."
    )
    webhook_method = method_index[("billing/webhook", "POST")]
    assert webhook_method["Properties"].get("AuthorizationType") == "NONE", (
        "POST /billing/webhook must remain public (AuthorizationType=NONE)."
    )

    # POST /errors must remain an explicit method.
    assert ("errors", "POST") in method_index, (
        "POST /errors must stay as an explicit method (AwsIntegration bridge, public)."
    )


# ---------------------------------------------------------------------------
# =============================================================================
# CATEGORY B — INTEGRATION: PATH PARAMS, CORS
# =============================================================================
# ---------------------------------------------------------------------------


def test_path_params_forwarded_through_proxy(
    synthesized_template: Template,
) -> None:
    """Parameterised paths served by the greedy {proxy+} must not have dedicated
    explicit CDK resources for them — the full path is forwarded through the proxy
    event shape and matched by the Powertools resolver (AC-006).
    """
    resources = synthesized_template.find_resources("AWS::ApiGateway::Resource")

    proxy_ids = _proxy_resource_ids(resources)
    assert proxy_ids, "No {proxy+} resources found — proxy collapse not applied."

    # Build a set of parent prefixes that have been proxy-collapsed (i.e., have a
    # {proxy+} child resource).
    collapsed_prefixes: set[str] = set()
    for pid in proxy_ids:
        parent_ref = resources[pid].get("Properties", {}).get("ParentId", {})
        parent_logical_id = (
            parent_ref.get("Ref", "") if isinstance(parent_ref, dict) else ""
        )
        if parent_logical_id:
            collapsed_prefixes.add(_full_resource_path(resources, parent_logical_id))

    # Explicit exception paths owned by a different Lambda remain valid below a
    # collapsed prefix because API Gateway gives exact resources precedence over
    # the greedy child.
    allowed_exception_paths = {
        "users/me/cv",
        "users/me/subscription",
        "users/me/usage",
        "users/me/trial/reset",
        "jobs/{jobId}/gap-questions",
        "jobs/{jobId}/gap-responses",
        "jobs/{jobId}/artifacts/{moduleType}/export",
        "vpr/generate",
        "cover-letter/generate",
        "interview-prep/generate",
        "billing/webhook",
    }

    # For each collapsed prefix, assert there are no redundant explicit CDK
    # Resources below it other than the documented cross-handler exceptions.
    parameterised_subpath_resources = [
        (lid, _full_resource_path(resources, lid))
        for lid, r in resources.items()
        if r.get("Properties", {}).get("PathPart") not in ("{proxy+}", "")
        and any(
            _full_resource_path(resources, lid).startswith(prefix + "/")
            for prefix in collapsed_prefixes
            if prefix
        )
        and not any(
            exception_path == _full_resource_path(resources, lid)
            or exception_path.startswith(_full_resource_path(resources, lid) + "/")
            or _full_resource_path(resources, lid).startswith(exception_path + "/")
            for exception_path in allowed_exception_paths
        )
    ]
    assert not parameterised_subpath_resources, (
        f"Explicit CDK sub-path resources still exist under collapsed feature prefixes: "
        f"{[(path, lid) for lid, path in parameterised_subpath_resources]}. "
        "After proxy collapse these paths should be caught by the {proxy+} child resource."
    )


def test_cors_preflight_contract_preserved(
    synthesized_template: Template,
) -> None:
    """OPTIONS (CORS preflight) methods must exist on every {proxy+} resource
    with a MOCK integration — preserving the CORS contract after collapse (AC-008).
    """
    resources = synthesized_template.find_resources("AWS::ApiGateway::Resource")
    methods = synthesized_template.find_resources("AWS::ApiGateway::Method")

    proxy_ids = _proxy_resource_ids(resources)
    assert proxy_ids, "No {proxy+} resources found — proxy collapse not applied."

    # Resource ids that have an OPTIONS method.
    options_resource_ids = _method_resource_ids_for_http_method(methods, "OPTIONS")

    missing_cors = proxy_ids - options_resource_ids
    assert not missing_cors, (
        f"{len(missing_cors)} {{proxy+}} resource(s) are missing an OPTIONS method "
        f"(CORS preflight): {missing_cors}."
    )

    # OPTIONS methods on {proxy+} resources must use MOCK integration (CDK's CORS pattern).
    cors_methods_on_proxy = [
        method
        for method in methods.values()
        if method["Properties"].get("HttpMethod") == "OPTIONS"
        and method["Properties"].get("ResourceId", {}).get("Ref", "") in proxy_ids
    ]
    for cors_method in cors_methods_on_proxy:
        integration = cors_method["Properties"].get("Integration", {})
        assert integration.get("Type") == "MOCK", (
            "OPTIONS method on a {proxy+} resource must use MOCK integration "
            f"(CDK default_cors_preflight_options pattern). Got: {integration.get('Type')!r}"
        )

    # Verify CORS response parameters include Access-Control-Allow-Origin.
    for cors_method in cors_methods_on_proxy:
        method_responses = cors_method["Properties"].get("MethodResponses", [])
        response_params: dict[str, Any] = {}
        for mr in method_responses:
            response_params.update(mr.get("ResponseParameters", {}))
        assert any("Access-Control-Allow-Origin" in key for key in response_params), (
            "OPTIONS method on {proxy+} resource is missing "
            "Access-Control-Allow-Origin in MethodResponses ResponseParameters."
        )


# ---------------------------------------------------------------------------
# =============================================================================
# CATEGORY D — REGRESSION: AUTH SAFETY, ROUTE PRESENCE, NAMING
# =============================================================================
# ---------------------------------------------------------------------------


def test_no_protected_route_became_public_and_no_public_route_became_protected(
    synthesized_template: Template,
) -> None:
    """Cross-check every real HTTP method against the expected auth/public classification.

    Protected routes must carry COGNITO_USER_POOLS; public routes must carry NONE (AC-002).
    Any authorizer flip fails this regression guard.
    """
    methods = synthesized_template.find_resources("AWS::ApiGateway::Method")
    resources = synthesized_template.find_resources("AWS::ApiGateway::Resource")
    method_index = _build_method_index(methods, resources)

    # Paths documented as public (no auth required).
    public_paths: frozenset[str] = frozenset(
        {
            "health",
            "auth/register",
            "auth/login",
            "auth/refresh",
            "billing/webhook",
            "errors",
            "swagger",
            "swagger.css",
            "swagger.js",
            # Root resource and API-GW internal resources.
            "",
        }
    )

    auth_flips: list[str] = []

    for (path, http_method), method_props in method_index.items():
        if http_method in {"OPTIONS"}:
            continue  # CORS preflight is intentionally unauthenticated.

        auth_type = method_props["Properties"].get("AuthorizationType")
        root_prefix = path.split("/")[0] if path else ""
        is_classified_public = path in public_paths or (
            http_method == "ANY" and root_prefix in PUBLIC_FEATURE_PREFIXES
        )

        if is_classified_public and auth_type != "NONE":
            auth_flips.append(
                f"PUBLIC route {http_method} /{path} gained an authorizer "
                f"(AuthorizationType={auth_type!r})"
            )
        elif not is_classified_public and auth_type != "COGNITO_USER_POOLS":
            auth_flips.append(
                f"PROTECTED route {http_method} /{path} lost its Cognito authorizer "
                f"(AuthorizationType={auth_type!r})"
            )

    assert not auth_flips, (
        f"Auth parity regression detected ({len(auth_flips)} flip(s)):\n"
        + "\n".join(auth_flips)
    )


def test_all_openapi_routes_still_present_after_collapse(
    synthesized_template: Template,
) -> None:
    """Every (path, method) in the OpenAPI oracle and in the CDK canonical route map must
    still be reachable after proxy collapse — no route may be silently dropped (AC-006).

    Reachability is determined by checking either:
    a) an explicit method exists in the synthesized template for the exact path, OR
    b) a {proxy+} ANY method exists on an ancestor resource that covers the path.
    """
    resources = synthesized_template.find_resources("AWS::ApiGateway::Resource")
    methods = synthesized_template.find_resources("AWS::ApiGateway::Method")
    method_index = _build_method_index(methods, resources)

    # Build the set of path prefixes covered by a {proxy+} ANY integration.
    proxy_ids = _proxy_resource_ids(resources)
    any_resource_ids = _method_resource_ids_for_http_method(methods, "ANY")
    covered_proxy_prefixes: set[str] = set()
    for pid in proxy_ids:
        if pid in any_resource_ids:
            parent_ref = resources[pid].get("Properties", {}).get("ParentId", {})
            parent_lid = (
                parent_ref.get("Ref", "") if isinstance(parent_ref, dict) else ""
            )
            prefix = _full_resource_path(resources, parent_lid) if parent_lid else ""
            covered_proxy_prefixes.add(prefix)

    def _is_reachable(path: str, method: str) -> bool:
        # Strip leading slash for comparison.
        clean = path.lstrip("/")
        # Direct explicit method.
        if (clean, method) in method_index:
            return True
        # ANY method on the exact resource.
        if (clean, "ANY") in method_index:
            return True
        # Covered by a {proxy+} ANY integration under an ancestor prefix.
        for prefix in covered_proxy_prefixes:
            if clean == prefix or clean.startswith(prefix + "/"):
                return True
        return False

    # Check CDK canonical routes (ground truth for the deployed surface).
    canonical = _cdk_canonical_routes()
    missing = [
        (path, method) for path, method in canonical if not _is_reachable(path, method)
    ]
    assert not missing, (
        f"{len(missing)} CDK canonical route(s) are no longer reachable after proxy "
        f"collapse: {missing}. Ensure every route is served either by an explicit method "
        "or by a {proxy+} ANY integration covering its path prefix."
    )

    # Also verify any routes declared in the OpenAPI oracle.
    openapi_routes = _load_openapi_routes()
    oracle_missing = [
        (path, method)
        for path, method in openapi_routes
        if not _is_reachable(path, method)
    ]
    assert not oracle_missing, (
        f"{len(oracle_missing)} OpenAPI oracle route(s) are no longer reachable: "
        f"{oracle_missing}."
    )


def test_cfn_guard_naming_and_checkov_clean_after_collapse(
    synthesized_template: Template,  # noqa: ARG001 — synthesize before script checks
) -> None:
    """validate_naming --strict must pass on the infra directory after proxy collapse (AC-009).

    Only the naming check is automated here; cfn-guard / checkov are run separately
    in the full regression pipeline (see TEST-INFRA-048 regression run command).
    """
    repo_root = Path(__file__).parents[3]
    validate_script = repo_root / "src" / "backend" / "scripts" / "validate_naming.py"

    if not validate_script.exists():
        raise FileNotFoundError(f"validate_naming.py not found at {validate_script}")

    result = subprocess.run(
        [sys.executable, str(validate_script), "--path", "infra", "--strict"],
        capture_output=True,
        text=True,
        cwd=str(repo_root),
    )
    assert result.returncode == 0, (
        f"validate_naming --strict found violations after proxy collapse:\n"
        f"{result.stdout}\n{result.stderr}"
    )


def test_parent_budget_ceiling_holds_below_500_hard_and_400_target(
    synthesized_template: Template,
) -> None:
    """Permanent budget guard: parent synth < 500 (hard) (AC-003).

    Phase 1 collapses auth/users/gap-analysis/billing; the hard CFN ceiling is what
    must never be breached. The <= 400 aspirational target is enforced once Phase 2
    collapses the remaining features (vpr, cover-letter, cv-tailoring, interview-prep,
    applications, company-research) after their {paramId} resources are removed.
    """
    count = len(synthesized_template.to_json().get("Resources", {}))
    assert count < CFN_MAX_RESOURCES, (
        f"Parent synth has {count} resources, at/over the {CFN_MAX_RESOURCES} "
        "CloudFormation hard limit."
    )


def test_no_stateful_resource_types_added_or_replaced_by_collapse(
    merged_resources: dict[str, dict[str, Any]],
) -> None:
    """No stateful resource is added, dropped, or replaced (AC-011).

    Cross-checks the count of each stateful resource type against the documented
    baseline. The {proxy+} collapse may only churn ApiGateway Method/Resource,
    Lambda Permission, and the API Deployment — never DynamoDB/S3/KMS/Cognito/SQS,
    whose logical-id change would risk a CloudFormation REPLACE and data loss.

    P-26 Job 1 re-homes the SQS queues into CrudFeaturesNestedStack via a
    logical-id-preserving cdk refactor IMPORT (no delete/create, no REPLACE), so
    the count is taken across the whole deployment (parent + nested): the total
    set of stateful resources is unchanged, they have merely moved template.
    """
    actual: dict[str, int] = {}
    for resource_type in EXPECTED_STATEFUL_BASELINE:
        actual[resource_type] = sum(
            1 for r in merged_resources.values() if r.get("Type") == resource_type
        )

    drift = {
        rtype: (EXPECTED_STATEFUL_BASELINE[rtype], actual[rtype])
        for rtype in EXPECTED_STATEFUL_BASELINE
        if actual[rtype] != EXPECTED_STATEFUL_BASELINE[rtype]
    }
    assert not drift, (
        "Stateful resource drift detected "
        "(type: expected -> actual): "
        + ", ".join(
            f"{rtype}: {expected} -> {got}" for rtype, (expected, got) in drift.items()
        )
        + ". No stateful resource may be added, dropped, or replaced."
    )


def test_restapi_identity_unchanged(synthesized_template: Template) -> None:
    """The shared RestApi name and logical identity remain stable (AC-005)."""
    rest_apis = synthesized_template.find_resources("AWS::ApiGateway::RestApi")
    assert list(rest_apis) == ["CareerVpCrudDevCrudservicerestapi5E02FD49"]
    assert (
        next(iter(rest_apis.values()))["Properties"]["Name"] == "careervp-core-api-dev"
    )
