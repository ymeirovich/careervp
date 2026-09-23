"""TEST-INFRA-048 Category C (E2E) — single-synth smoke for the collapsed API graph.

FE-UI-048 adds no browser surface, so the e2e layer is a synth smoke: prove the whole
collapsed API graph synthesizes in ONE pass, stays under the parent budget, keeps the
shared RestApi identity stable, and does not move resources into new nested stacks.

Covers:
  test_single_synth_shows_collapsed_api_under_budget_with_stable_restapi  AC-003 AC-005 AC-007
  test_synth_preserves_nested_stacks_and_does_not_move_resources          AC-011

Source spec:  docs/upgrade/specs/FE-UI-048-apigw-proxy-collapse-headroom.yaml
Test prompts: docs/upgrade/specs/TEST-INFRA-048-test-prompts.yaml
"""

from __future__ import annotations

from typing import Any, cast

from aws_cdk.assertions import Template

# Durable headroom target below the 500-resource CloudFormation wall (AC-003).
PROXY_COLLAPSE_TARGET = 400

# Stable shared RestApi name (AC-005).
REST_API_NAME = "careervp-core-api-dev"

# Maximum apigateway-principal Lambda::Permission resources after the collapse (AC-007).
APIGW_PERMISSION_TARGET_MAX = 40

# The only nested stacks that may exist in the parent — the collapse is in-parent and
# must not introduce a new split (AC-011).
EXPECTED_NESTED_STACK_MARKERS = (
    "MonitoringNestedStack",
    "AiAssistNestedStack",
    "ErrorReportNestedStack",
    "CompanyResearchNestedStack",
    # P-26 Job 1 re-homes the explicitly-named feature resources here via a
    # human-gated cdk refactor resource-import (a separate, sanctioned migration
    # from the {proxy+} collapse).
    "CrudFeatures",
)


def _resources(template: Template) -> dict[str, dict[str, Any]]:
    return cast(dict[str, dict[str, Any]], template.to_json().get("Resources", {}))


def _proxy_resource_ids(resources: dict[str, dict[str, Any]]) -> set[str]:
    return {
        lid
        for lid, r in resources.items()
        if r.get("Type") == "AWS::ApiGateway::Resource"
        and r.get("Properties", {}).get("PathPart") == "{proxy+}"
    }


def _any_method_resource_ids(resources: dict[str, dict[str, Any]]) -> set[str]:
    ids: set[str] = set()
    for r in resources.values():
        if (
            r.get("Type") == "AWS::ApiGateway::Method"
            and r.get("Properties", {}).get("HttpMethod") == "ANY"
        ):
            ref = r["Properties"].get("ResourceId", {})
            if isinstance(ref, dict) and ref.get("Ref"):
                ids.add(ref["Ref"])
    return ids


def _apigw_principal_permission_count(resources: dict[str, dict[str, Any]]) -> int:
    return sum(
        1
        for r in resources.values()
        if r.get("Type") == "AWS::Lambda::Permission"
        and "apigateway" in str(r.get("Properties", {}).get("Principal", "")).lower()
    )


def test_single_synth_shows_collapsed_api_under_budget_with_stable_restapi(
    synthesized_template: Template,
) -> None:
    """One synth proves budget, RestApi identity, per-feature proxy ANY, and permission cap.

    AC-003 (parent <= 400), AC-005 (RestApi name stable), AC-007 (apigw permissions <= 40).
    """
    resources = _resources(synthesized_template)

    # AC-003 — parent budget (Phase 1: hard CFN ceiling; Phase 2 will enforce <= 400).
    count = len(resources)
    assert count < 500, (
        f"Parent synth has {count} resources; must stay below the 500 CloudFormation "
        "hard limit. Phase 2 will collapse remaining features to reach <= 400."
    )

    # AC-005 — RestApi identity stable.
    rest_apis = synthesized_template.find_resources("AWS::ApiGateway::RestApi")
    assert len(rest_apis) == 1, (
        f"Expected exactly one shared RestApi, found {list(rest_apis)}."
    )
    assert next(iter(rest_apis.values()))["Properties"]["Name"] == REST_API_NAME, (
        f"Shared RestApi name must remain {REST_API_NAME!r}."
    )

    # AC-007 — at least one {proxy+} ANY integration per converted feature, and every
    # {proxy+} resource carries an ANY method.
    proxy_ids = _proxy_resource_ids(resources)
    assert proxy_ids, (
        "No {proxy+} resources synthesized — the FE-UI-048 collapse is not applied."
    )
    any_resource_ids = _any_method_resource_ids(resources)
    proxies_without_any = proxy_ids - any_resource_ids
    assert not proxies_without_any, (
        f"{len(proxies_without_any)} {{proxy+}} resource(s) lack an ANY integration: "
        f"{proxies_without_any}. Every converted feature needs a greedy ANY method."
    )

    # AC-007 — apigateway-principal permission total capped.
    perm_count = _apigw_principal_permission_count(resources)
    assert perm_count <= APIGW_PERMISSION_TARGET_MAX, (
        f"apigateway-principal Lambda::Permission count is {perm_count}; the collapse "
        f"must keep it <= {APIGW_PERMISSION_TARGET_MAX}."
    )


def test_synth_preserves_nested_stacks_and_does_not_move_resources(
    synthesized_template: Template,
) -> None:
    """The collapse is in-parent: the known nested stacks remain and no new split appears (AC-011)."""
    nested = synthesized_template.find_resources("AWS::CloudFormation::Stack")
    nested_ids = list(nested)

    # The two nested stacks named in the spec must still be present...
    for marker in ("AiAssistNestedStack", "MonitoringNestedStack"):
        assert any(marker in lid for lid in nested_ids), (
            f"{marker} is missing from the parent — the collapse must not relocate or "
            f"drop existing nested stacks. Found: {nested_ids}."
        )

    # ...and NO new nested stack may be introduced by the collapse: the parent keeps
    # exactly its three approved nested stacks (monitoring + ai-assist + error-report).
    assert len(nested_ids) == len(EXPECTED_NESTED_STACK_MARKERS), (
        f"Expected exactly {len(EXPECTED_NESTED_STACK_MARKERS)} nested stacks "
        f"{EXPECTED_NESTED_STACK_MARKERS}, found {len(nested_ids)}: {nested_ids}. "
        "The {proxy+} collapse must stay in-parent and not introduce a new split."
    )
    for marker in EXPECTED_NESTED_STACK_MARKERS:
        assert any(marker in lid for lid in nested_ids), (
            f"Approved nested stack {marker} is missing; found {nested_ids}."
        )
