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

import json
from pathlib import Path
from typing import Any

from aws_cdk.assertions import Template

from careervp.crud_features_nested_stack import CrudFeaturesNestedStack

DEVX_AMPLIFY_ORIGIN = "https://db-redesign.d3j2wnm8g5clnw.amplifyapp.com"
CDK_JSON_PATH = Path(__file__).resolve().parents[2] / "cdk.json"


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


def test_cdk_json_context_allowed_origins_includes_db_redesign() -> None:
    """AC-P07-6b: the value that actually reaches a real `cdk deploy`.

    `ApiConstruct.allowed_origins` reads `self.node.try_get_context("allowed_origins")`
    FIRST, falling back to a hardcoded default only when that context key is absent.
    The CDK CLI always merges `cdk.json`'s `context` block into every real `cdk
    synth`/`cdk deploy` invocation, and `cdk.json` has this key set — so for any real
    deploy, the Python-level default string is dead code and `cdk.json` is the actual
    source of truth. A test against `devx_service_stack` alone (constructed with a bare
    `App(context=...)` that never loads `cdk.json`) cannot see this: it validates the
    fallback, not what actually ships. This test caught exactly that gap — the first
    version of this fix edited only the Python default, passed its own test, but had
    zero effect on a real deploy because `cdk.json` still held the old list.
    """
    context = json.loads(CDK_JSON_PATH.read_text(encoding="utf-8"))["context"]
    origins = context["allowed_origins"].split(",")
    assert DEVX_AMPLIFY_ORIGIN in origins, (
        f"cdk.json's context.allowed_origins is what a real `cdk deploy` actually uses "
        f"(it overrides the Python default in api_construct.py). "
        f"{DEVX_AMPLIFY_ORIGIN} is missing. Registered: {origins}"
    )
