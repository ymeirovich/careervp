"""Environment-coupling guards, parameterized over every declared environment.

A test pinned to a single environment (``dev``) cannot catch a bug that only
manifests when a *different* environment is deployed — that is exactly how
the P-26 ``dev`` -> ``devx`` rename silently disabled the artifact chain.
Every test below synthesizes ``dev``, ``devx`` and ``prod`` independently.
See docs/handoff/2026-09-21-HANDOFF-09-environment-coupling.md.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import pytest
from aws_cdk import App, Environment, NestedStack
from aws_cdk.assertions import Template

from careervp.environments import ENVIRONMENTS, profile
from careervp.naming_utils import NamingUtils
from careervp.service_stack import ServiceStack

ACCOUNT_ID = "123456789012"
REGION = "us-east-1"

# CDK-framework-owned custom-resource Lambdas (e.g. the S3 BucketNotificationsHandler)
# run generated provider code we do not own and cannot inject ENVIRONMENT into. They
# have no FunctionName literal (CDK auto-names them), unlike every application Lambda.
_FRAMEWORK_OWNED_HANDLER_PREFIXES = ("index.",)


def _build_service_stack(environment: str) -> ServiceStack:
    app = App(context={"p26_rehome_features": "true"})
    naming = NamingUtils(environment=environment, region=REGION, account_id=ACCOUNT_ID)
    return ServiceStack(
        scope=app,
        id=naming.stack_id("crud"),
        env=Environment(account=ACCOUNT_ID, region=REGION),
        is_production_env=False,
        naming=naming,
        stack_feature="crud",
    )


def _all_templates(stack: ServiceStack) -> list[Template]:
    templates = [Template.from_stack(stack)]
    for construct in stack.node.find_all():
        if isinstance(construct, NestedStack):
            templates.append(Template.from_stack(construct))
    return templates


def _iter_string_literals(node: Any) -> Iterator[str]:
    if isinstance(node, str):
        yield node
    elif isinstance(node, dict):
        for value in node.values():
            yield from _iter_string_literals(value)
    elif isinstance(node, list):
        for value in node:
            yield from _iter_string_literals(value)


def _iter_lambda_functions(templates: list[Template]) -> Iterator[dict[str, Any]]:
    for template in templates:
        for resource in template.find_resources("AWS::Lambda::Function").values():
            yield resource


@pytest.fixture(scope="module", params=sorted(ENVIRONMENTS))
def env_name(request: pytest.FixtureRequest) -> str:
    return request.param


@pytest.fixture(scope="module")
def env_stack(env_name: str) -> ServiceStack:
    return _build_service_stack(env_name)


@pytest.fixture(scope="module")
def env_templates(env_stack: ServiceStack) -> list[Template]:
    return _all_templates(env_stack)


def test_no_foreign_environment_suffix_in_template(
    env_name: str, env_templates: list[Template]
) -> None:
    """A template synthesized for one environment must never name a resource
    belonging to another declared environment (e.g. a devx Lambda whose table
    name literal ends in ``-dev``)."""
    foreign = {e for e in ENVIRONMENTS if e != env_name}
    for template in env_templates:
        template_json = template.to_json()
        for literal in _iter_string_literals(template_json):
            for other in foreign:
                # Compare on the full ``-{env}`` suffix, never a bare substring
                # or startswith — "dev" is a substring of "devx" itself.
                assert not literal.endswith(f"-{other}"), (
                    f"{env_name} template references {other} resource: {literal}"
                )


def test_every_lambda_declares_its_environment(
    env_name: str, env_templates: list[Template]
) -> None:
    """Every synthesized Lambda must be able to name its own deploy
    environment — the root cause of the subscription_repository bug was that
    only one Lambda out of ~30 had ENVIRONMENT set at all."""
    for fn in _iter_lambda_functions(env_templates):
        handler = fn["Properties"].get("Handler", "")
        if handler.startswith(_FRAMEWORK_OWNED_HANDLER_PREFIXES):
            continue
        env_vars = fn["Properties"].get("Environment", {}).get("Variables", {})
        function_name = fn["Properties"].get("FunctionName", "<unnamed>")
        assert env_vars.get("ENVIRONMENT") == env_name, (
            f"{function_name} cannot name itself: ENVIRONMENT="
            f"{env_vars.get('ENVIRONMENT')!r}, expected {env_name!r}"
        )


def test_profile_raises_for_an_undeclared_environment() -> None:
    """A new environment name must be a synth-time error, not a silent
    ``false`` — the exact property that would have caught P-26's ``dev`` ->
    ``devx`` rename before it shipped."""
    with pytest.raises(ValueError, match="No profile for 'staging'"):
        profile('staging')


def test_capability_flags_match_declared_profile(
    env_name: str, env_templates: list[Template]
) -> None:
    """A Lambda that consumes ARTIFACT_CHAIN_ENABLED must receive exactly the
    value declared for its environment in environments.py — not a guess based
    on the environment's literal name."""
    want = profile(env_name)
    for fn in _iter_lambda_functions(env_templates):
        env_vars = fn["Properties"].get("Environment", {}).get("Variables", {})
        if "ARTIFACT_CHAIN_ENABLED" not in env_vars:
            continue
        function_name = fn["Properties"].get("FunctionName", "<unnamed>")
        assert env_vars["ARTIFACT_CHAIN_ENABLED"] == str(want.artifact_chain).lower(), (
            f"{function_name} ARTIFACT_CHAIN_ENABLED does not match the "
            f"declared profile for {env_name!r}"
        )
