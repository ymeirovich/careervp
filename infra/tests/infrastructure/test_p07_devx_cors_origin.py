"""P-07 (step 1.6, live-verification follow-up) — devx CORS allow-list must include
the db-redesign Amplify origin.

scope_lock_clause: P-07

Why this exists: adding the db-redesign origin to Cognito's CallbackURLs/LogoutURLs
(cognito_construct.py) makes the OAuth login succeed, but it does not touch the
*separate* API Gateway/Lambda CORS allow-list (`ApiConstruct.allowed_origins`, wired
into every feature Lambda's `ALLOWED_ORIGINS` env var). Discovered via a live HAR
capture: a real login on devx completed successfully end to end (authorize, hosted
UI, callback, token exchange all 200/302 as expected), but every authenticated API
call afterwards failed with a browser-level CORS rejection (Chrome reports this as
`net::ERR_FAILED` / status 0, with no response headers, because Chrome intentionally
hides response details once a request fails the CORS check) — because
`https://db-redesign.d3j2wnm8g5clnw.amplifyapp.com` was never added to
`ApiConstruct.allowed_origins`. Confirmed live: the deployed
`careervp-user-api-lambda-devx` Lambda's `ALLOWED_ORIGINS` env var lacks this origin.
"""

from __future__ import annotations

from typing import Any

from aws_cdk.assertions import Template

from careervp.crud_features_nested_stack import CrudFeaturesNestedStack

DEVX_AMPLIFY_ORIGIN = "https://db-redesign.d3j2wnm8g5clnw.amplifyapp.com"


def _lambda_resource_by_handler(template: Template, handler: str) -> dict[str, Any]:
    functions = template.find_resources("AWS::Lambda::Function")
    matches = [
        r for r in functions.values() if r["Properties"].get("Handler") == handler
    ]
    assert matches, f"Lambda handler not synthesized: {handler}"
    return matches[0]


def test_devx_user_api_cors_allows_db_redesign_origin(
    devx_service_stack: Any,
) -> None:
    """AC-P07-6: the devx-deployed user-api Lambda's CORS allow-list includes the
    db-redesign Amplify origin, matching the Cognito callback URL already registered.
    """
    feature_stack = next(
        c
        for c in devx_service_stack.node.find_all()
        if isinstance(c, CrudFeaturesNestedStack)
    )
    template = Template.from_stack(feature_stack)
    lambda_resource = _lambda_resource_by_handler(
        template, "careervp.handlers.user_handler.lambda_handler"
    )
    env_vars = lambda_resource["Properties"].get("Environment", {}).get("Variables", {})
    allowed_origins = env_vars.get("ALLOWED_ORIGINS", "")
    origins = allowed_origins.split(",")

    assert DEVX_AMPLIFY_ORIGIN in origins, (
        f"devx API calls will be rejected by browser CORS after a successful login: "
        f"{DEVX_AMPLIFY_ORIGIN} is not in ALLOWED_ORIGINS. Registered: {origins}"
    )
