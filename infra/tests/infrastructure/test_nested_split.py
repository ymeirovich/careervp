"""TEST-INFRA-001 — nested-stack split guards (FE-UI-036).

These tests lock in the CloudFormation nested-stack split that keeps every
template comfortably below the 500-resource hard limit, and guard against the
two failure modes the split must avoid: a single template creeping back toward
500, and a stateful resource (DynamoDB/S3/KMS) drifting across a stack boundary
(which would change its logical id and risk REPLACE / data loss).
"""

from __future__ import annotations

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


def _resource_types(template: Template) -> dict[str, dict]:
    return template.to_json().get("Resources", {})


# § nested_split_assertions ---------------------------------------------------
def test_parent_declares_three_nested_stacks(synthesized_template: Template) -> None:
    """The parent must contain exactly the three FE-UI-036 nested stacks."""
    nested = synthesized_template.find_resources("AWS::CloudFormation::Stack")
    assert len(nested) == 3, (
        f"Expected 3 nested stacks (Monitoring, ArtifactChain, AsyncWorkers), "
        f"found {len(nested)}: {list(nested)}"
    )


def test_parent_resource_count_below_info_threshold(
    synthesized_template: Template,
) -> None:
    """Parent must stay well under 500 — below the configured 480 info threshold."""
    count = len(_resource_types(synthesized_template))
    assert count < 480, (
        f"Parent template has {count} resources; the split must keep it under the "
        f"480 'approaching maximum' info threshold (hard CloudFormation limit 500)."
    )


def test_every_template_below_cfn_hard_limit(
    synthesized_template: Template,
    monitoring_template: Template,
    artifact_chain_template: Template,
    async_workers_template: Template,
) -> None:
    """No template — parent or nested — may approach the 500-resource hard limit."""
    for name, template in (
        ("parent", synthesized_template),
        ("monitoring", monitoring_template),
        ("artifact_chain", artifact_chain_template),
        ("async_workers", async_workers_template),
    ):
        count = len(_resource_types(template))
        assert count < CFN_MAX_RESOURCES, (
            f"{name} template has {count} resources, at/over the {CFN_MAX_RESOURCES} "
            f"hard limit"
        )


def test_state_machine_lives_in_artifact_chain_nested_stack(
    artifact_chain_template: Template,
    synthesized_template: Template,
) -> None:
    """The Step Functions state machine moved into the ArtifactChain nested stack."""
    artifact_chain_template.resource_count_is("AWS::StepFunctions::StateMachine", 1)
    synthesized_template.resource_count_is("AWS::StepFunctions::StateMachine", 0)


def test_async_workers_present_in_nested_stack(
    async_workers_template: Template,
) -> None:
    """The relocated workers and their event-source mappings live in the nested stack."""
    functions = async_workers_template.find_resources("AWS::Lambda::Function")
    handlers = {props["Properties"].get("Handler") for props in functions.values()}
    assert "careervp.handlers.cv_tailoring_handler.handler" in handlers
    assert "careervp.handlers.cover_letter_handler.lambda_handler" in handlers
    assert "careervp.handlers.interview_prep_handler.lambda_handler" in handlers


# § nested_split_no_replacement ----------------------------------------------
def test_stateful_resources_stay_in_parent(
    monitoring_template: Template,
    artifact_chain_template: Template,
    async_workers_template: Template,
) -> None:
    """No DynamoDB table, S3 bucket, or KMS key may be created in a nested stack.

    Moving a stateful resource across the boundary changes its logical id and
    risks a CloudFormation REPLACE. This is the static guard behind the
    ``cdk diff`` no-replacement acceptance criterion.
    """
    for name, template in (
        ("monitoring", monitoring_template),
        ("artifact_chain", artifact_chain_template),
        ("async_workers", async_workers_template),
    ):
        resources = _resource_types(template)
        offenders = {
            logical_id: res["Type"]
            for logical_id, res in resources.items()
            if res["Type"] in STATEFUL_RESOURCE_TYPES
        }
        assert not offenders, (
            f"{name} nested stack contains stateful resources that must stay in the "
            f"parent (replacement risk): {offenders}"
        )


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
    ArtifactChain nested stack (the FE-UI-035 cycle, across the boundary)."""
    functions = synthesized_template.find_resources("AWS::Lambda::Function")
    handlers = {props["Properties"].get("Handler") for props in functions.values()}
    assert (
        "careervp.handlers.company_research_worker_handler.lambda_handler" in handlers
    ), "Company-research worker must remain in the parent stack"
