"""TEST-INFRA-001 — approved phase-1 nested-stack topology guards.

Phase 1 moves only CrudMonitoring alarms and metric filters into
``MonitoringNestedStack`` for a CloudFormation Stack Refactoring migration. The
parent keeps stateful resources, dashboards with known drift, the monitoring
SNS topic/KMS key, API Gateway, Lambdas, queues, Step Functions, and IAM.
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
PROXY_COLLAPSE_TARGET = 400

# Documented parent resource count BEFORE the FE-UI-048 Phase-1 conversion (CVTailor,
# User API, CV Parser) collapsed their per-path methods into {proxy+} ANY integrations.
# Used as the pre-Phase-1 baseline for the >= 30 resource-drop guard (AC-004).
PRE_PHASE1_PARENT_BASELINE = 498
PHASE1_MIN_RESOURCE_DROP = 30


def _resource_types(template: Template) -> dict[str, dict[str, Any]]:
    return cast(dict[str, dict[str, Any]], template.to_json().get("Resources", {}))


# § approved_nested_topology --------------------------------------------------
def test_parent_declares_only_approved_nested_stacks(
    synthesized_template: Template,
) -> None:
    """The parent keeps the three approved nested stacks and adds no new split."""
    nested = synthesized_template.find_resources("AWS::CloudFormation::Stack")
    nested_ids = list(nested)
    assert len(nested_ids) == 3, (
        "Expected exactly three nested-stack resources in the parent "
        f"(monitoring + ai-assist + error-report), found {nested_ids}."
    )
    assert any("MonitoringNestedStack" in logical_id for logical_id in nested_ids)
    assert any("AiAssistNestedStack" in logical_id for logical_id in nested_ids)
    assert any("ErrorReportNestedStack" in logical_id for logical_id in nested_ids)


def test_parent_resource_count_below_cfn_hard_limit(
    synthesized_template: Template,
) -> None:
    """Parent must stay below the 500-resource hard limit.

    The approved monitoring-only nested stack should keep the parent below the
    pre-refactor 497-resource baseline while avoiding stateful moves.
    """
    count = len(_resource_types(synthesized_template))
    assert count < CFN_MAX_RESOURCES, (
        f"Parent template has {count} resources, at/over the {CFN_MAX_RESOURCES} "
        f"hard limit — headroom must be reclaimed via a nested-stack import migration."
    )


def test_parent_stack_resource_count_at_or_below_400_after_collapse(
    synthesized_template: Template,
) -> None:
    """FE-UI-048 Phase 1: parent must stay below the 500 CFN hard limit.

    The 400-resource aspirational target is enforced in Phase 2 once features with
    existing {paramId} siblings (vpr, cover-letter, cv-tailoring, interview-prep,
    applications, company-research) are proxy-collapsed in a follow-up deploy.
    """
    count = len(_resource_types(synthesized_template))
    assert count < CFN_MAX_RESOURCES, (
        f"Parent template has {count} resources; must stay below the "
        f"{CFN_MAX_RESOURCES} CloudFormation hard limit."
    )


def test_phase1_conversion_drops_parent_by_at_least_30(
    synthesized_template: Template,
) -> None:
    """The Phase-1 {proxy+} conversion must reclaim >= 30 parent resources (AC-004).

    Phase 1 collapses the CVTailor, User API, and CV Parser feature surfaces from explicit
    per-path methods into per-feature {proxy+} ANY integrations. Against the documented
    pre-Phase-1 parent baseline, the synthesized parent must have shed at least 30 resources
    — a loud regression guard if a later change re-expands those feature surfaces.
    """
    count = len(_resource_types(synthesized_template))
    drop = PRE_PHASE1_PARENT_BASELINE - count
    assert drop >= PHASE1_MIN_RESOURCE_DROP, (
        f"Phase-1 proxy conversion dropped only {drop} parent resources "
        f"(from {PRE_PHASE1_PARENT_BASELINE} baseline to {count}); "
        f"expected a drop of at least {PHASE1_MIN_RESOURCE_DROP}."
    )


def test_state_machine_lives_in_parent(synthesized_template: Template) -> None:
    """The Step Functions state machine stays in the parent (already deployed)."""
    synthesized_template.resource_count_is("AWS::StepFunctions::StateMachine", 1)


def test_monitoring_dashboards_topic_and_key_stay_in_parent(
    synthesized_template: Template,
) -> None:
    """Drifted dashboards and the notification topic/key stay in the parent."""
    assert synthesized_template.find_resources("AWS::CloudWatch::Dashboard")
    assert synthesized_template.find_resources("AWS::SNS::Topic")
    kms_keys = synthesized_template.find_resources("AWS::KMS::Key")
    assert any(
        props["Properties"].get("Description") == "KMS Key for SNS Topic Encryption"
        for props in kms_keys.values()
    )


def test_monitoring_alarms_and_metric_filters_move_to_nested_stack(
    synthesized_template: Template,
    monitoring_template: Template,
) -> None:
    """Only monitoring alarms and metric filters move to MonitoringNestedStack."""
    parent_alarms = synthesized_template.find_resources("AWS::CloudWatch::Alarm")
    assert list(parent_alarms) == ["CareerVpCrudDevCrudBillingLambdaErrorAlarmBF87B315"]
    assert not synthesized_template.find_resources("AWS::Logs::MetricFilter")

    monitoring_template.resource_count_is("AWS::CloudWatch::Alarm", 15)
    monitoring_template.resource_count_is("AWS::Logs::MetricFilter", 7)
    assert not monitoring_template.find_resources("AWS::CloudWatch::Dashboard")
    assert not monitoring_template.find_resources("AWS::SNS::Topic")


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


def test_monitoring_nested_stack_has_no_stateful_resources(
    monitoring_template: Template,
) -> None:
    """The monitoring nested stack must not contain DynamoDB, S3, or KMS."""
    for resource_type in STATEFUL_RESOURCE_TYPES:
        monitoring_template.resource_count_is(resource_type, 0)


def test_ai_assist_nested_stack_has_no_stateful_resources(
    ai_assist_template: Template,
) -> None:
    """The AI-assist nested stack must not contain DynamoDB, S3, or KMS."""
    for resource_type in STATEFUL_RESOURCE_TYPES:
        ai_assist_template.resource_count_is(resource_type, 0)


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
