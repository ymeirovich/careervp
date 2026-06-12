"""TEST-INFRA-001 — flat-stack deploy-safety guards (FE-UI-036 reverted).

The FE-UI-036 nested-stack split was reverted: every resource it relocated
(worker Lambdas, log groups, the Step Functions state machine, all alarms and
dashboards) carries an explicit physical name and is already deployed in the
parent ``CareerVpCrudDev`` stack. CloudFormation cannot move a named resource to
a different stack in a single deploy — it creates the new one before deleting
the old, which fails with "resource already exists" (the cdk-deploy failure on
ui-upgrade@8926a90).

These tests lock in the deploy-safe topology and guard against re-introducing
the split without a CloudFormation resource-import migration:
  * no nested stacks may exist in the synthesized parent template;
  * the explicitly-named resources must stay in the parent;
  * stateful resources (DynamoDB/S3/KMS) must never drift across a boundary.

Re-doing FE-UI-036 for headroom requires `cdk import` / a CFN stack-refactor
migration first, then this guard should be updated alongside it.
"""

from __future__ import annotations

from typing import Any, cast

from aws_cdk.assertions import Template

# Stateful resource types that must never live in a nested stack: relocating one
# changes its logical id and risks CloudFormation REPLACE (data loss).
STATEFUL_RESOURCE_TYPES = (
    "AWS::DynamoDB::Table",
    "AWS::DynamoDB::GlobalTable",
    "AWS::S3::Bucket",
    "AWS::KMS::Key",
)

# CloudFormation's hard per-template ceiling.
CFN_MAX_RESOURCES = 500


def _resource_types(template: Template) -> dict[str, dict[str, Any]]:
    return cast(dict[str, dict[str, Any]], template.to_json().get("Resources", {}))


# § flat_topology_guard -------------------------------------------------------
def test_parent_declares_no_nested_stacks(synthesized_template: Template) -> None:
    """Deploy-safety: the split is reverted, so no nested stacks may be emitted.

    Re-introducing a nested stack would relocate already-deployed, explicitly
    named resources and reproduce the "already exists" cdk-deploy failure.
    """
    nested = synthesized_template.find_resources("AWS::CloudFormation::Stack")
    assert not nested, (
        f"Expected a flat parent stack with no nested stacks, found {list(nested)}. "
        f"Relocating deployed named resources needs a CFN resource-import migration."
    )


def test_parent_resource_count_below_cfn_hard_limit(
    synthesized_template: Template,
) -> None:
    """Parent must stay below the 500-resource hard limit.

    NOTE: the flat revert sits near the ceiling (~497). The FE-UI-036 headroom
    work should be redone as an import-based migration before adding many more
    resources.
    """
    count = len(_resource_types(synthesized_template))
    assert count < CFN_MAX_RESOURCES, (
        f"Parent template has {count} resources, at/over the {CFN_MAX_RESOURCES} "
        f"hard limit — headroom must be reclaimed via a nested-stack import migration."
    )


def test_state_machine_lives_in_parent(synthesized_template: Template) -> None:
    """The Step Functions state machine stays in the parent (already deployed)."""
    synthesized_template.resource_count_is("AWS::StepFunctions::StateMachine", 1)


def test_monitoring_dashboards_and_alarms_stay_in_parent(
    synthesized_template: Template,
) -> None:
    """Explicitly-named dashboards/alarms stay in the parent (already deployed)."""
    assert synthesized_template.find_resources("AWS::CloudWatch::Dashboard")
    assert synthesized_template.find_resources("AWS::CloudWatch::Alarm")


# § no_stateful_drift ---------------------------------------------------------
def test_parent_retains_stateful_resources(synthesized_template: Template) -> None:
    """The parent keeps the DynamoDB tables, S3 buckets, and KMS keys."""
    resources = _resource_types(synthesized_template)
    counts = {
        t: sum(1 for r in resources.values() if r["Type"] == t)
        for t in STATEFUL_RESOURCE_TYPES
    }
    assert counts["AWS::DynamoDB::GlobalTable"] > 0, "DynamoDB tables left the parent"
    assert counts["AWS::S3::Bucket"] > 0, "S3 buckets left the parent"
    assert counts["AWS::KMS::Key"] > 0, "KMS keys left the parent"


def test_company_research_worker_stays_in_parent(
    synthesized_template: Template,
) -> None:
    """The CR worker uses the shared role + grant_task_response, so it stays in the
    parent — relocating it would give the shared role a back-edge into the
    artifact chain (the FE-UI-035 cycle)."""
    functions = synthesized_template.find_resources("AWS::Lambda::Function")
    handlers = {props["Properties"].get("Handler") for props in functions.values()}
    assert (
        "careervp.handlers.company_research_worker_handler.lambda_handler" in handlers
    ), "Company-research worker must remain in the parent stack"


def test_async_workers_stay_in_parent(
    synthesized_template: Template,
) -> None:
    """Previously deployed async workers stay in the parent until a migration path exists."""
    functions = synthesized_template.find_resources("AWS::Lambda::Function")
    handlers = {props["Properties"].get("Handler") for props in functions.values()}
    assert "careervp.handlers.cv_tailoring_handler.handler" in handlers
    assert "careervp.handlers.cover_letter_handler.lambda_handler" in handlers
    assert "careervp.handlers.interview_prep_handler.lambda_handler" in handlers
