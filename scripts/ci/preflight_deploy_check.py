#!/usr/bin/env python3
"""Pre-flight account-collision check for a synthesized CloudFormation stack.

WHY THIS EXISTS
---------------
The P-28 change-set gate (``changeset_replacement_report.py``) validates the
*shape* of a deploy: what is added, what is replaced, whether a protected
resource type is being destroyed. It answers that question correctly. It cannot
answer a different one -- "can these resources actually be created in this AWS
account right now?" -- because:

  * Nested-stack templates are opaque ``TemplateURL`` pointers at change-set
    time. CloudFormation does not resolve them until the real create, so any
    defect inside a nested template is invisible to ``DescribeChangeSet``.
  * Nothing in the change-set API checks account-level name uniqueness,
    account-level singleton limits, or service quotas.

The result is a class of failure that passes every gate and then takes the whole
stack down deep into a multi-minute create, forcing a full teardown and redeploy.
CareerVpCrudDevx hit exactly this on 2026-07-19T20:13:20Z: a clean change-set
report (292 Add, 0 replacements, ``auto_fail: false``) followed by
``P32AnomalyMonitor ... AlreadyExists`` nine minutes into the create, because AWS
Cost Anomaly Detection permits ONE DIMENSIONAL/SERVICE monitor per *account* and
``dev`` already owned it. The env-scoped name did not help -- the limit is not
enforced on the name.

This script closes that gap: it reads every synthesized template (parent AND
nested), finds resources whose uniqueness is scoped to the AWS account rather
than to the stack, and asks AWS whether each one is already taken. It runs in
seconds and is read-only.

USAGE
-----
    python scripts/ci/preflight_deploy_check.py \\
        --template-dir infra/cdk.out \\
        --stack CareerVpCrudDevx

Exit codes: 0 = clear to deploy, 1 = blocking conflict, 2 = usage/AWS error.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

try:
    import boto3
    from botocore.exceptions import ClientError, NoCredentialsError
except ImportError:  # pragma: no cover - dependency is declared in infra/
    print("error: boto3 is required (cd infra && uv sync)", file=sys.stderr)
    raise SystemExit(2) from None


# A stack in one of these states cannot be updated and cannot be re-created
# under the same name. It must be deleted first -- which, for a stack with
# termination protection on (every non-scratch CareerVP stack, per P-27), also
# requires disabling that protection. scripts/deploy/cleanup_stack.sh does both.
TERMINAL_STACK_STATES = {
    "ROLLBACK_COMPLETE",
    "ROLLBACK_FAILED",
    "CREATE_FAILED",
    "DELETE_FAILED",
}


@dataclass
class Finding:
    """One pre-flight result. ``blocking`` findings fail the run."""

    check: str
    logical_id: str
    detail: str
    remedy: str
    blocking: bool = True


@dataclass
class Context:
    """Everything the individual checks need, resolved once."""

    stack_name: str
    account_id: str
    region: str
    resources: dict[str, dict[str, Any]]
    owned_physical_ids: set[str] = field(default_factory=set)
    session: Any = None


def load_templates(template_dir: Path) -> dict[str, dict[str, Any]]:
    """Merge every template in a cdk.out directory into one resource map.

    Both ``*.template.json`` (parent) and ``*.nested.template.json`` are read.
    Nested templates matter most here: the resource that broke the devx deploy
    lived in MonitoringNestedStack, where the change-set gate could not see it.
    """
    templates = sorted(template_dir.glob("*.template.json"))
    if not templates:
        raise SystemExit(
            f"error: no *.template.json found in {template_dir}. Run `cdk synth` first."
        )

    merged: dict[str, dict[str, Any]] = {}
    for path in templates:
        try:
            body = json.loads(path.read_text())
        except json.JSONDecodeError as exc:
            raise SystemExit(f"error: {path} is not valid JSON: {exc}") from exc
        for logical_id, resource in (body.get("Resources") or {}).items():
            # Logical ids are unique per template, not across templates; qualify
            # with the filename so a collision cannot silently drop a resource.
            merged[f"{path.stem}/{logical_id}"] = resource
    return merged


def by_type(ctx: Context, resource_type: str) -> list[tuple[str, dict[str, Any]]]:
    return [
        (logical_id, resource.get("Properties") or {})
        for logical_id, resource in ctx.resources.items()
        if resource.get("Type") == resource_type
    ]


def literal(value: Any) -> str | None:
    """Return a property only when it is a plain literal.

    Intrinsics (``{"Ref": ...}``, ``{"Fn::Join": ...}``) resolve at deploy time
    and cannot be checked against AWS from here, so they are skipped rather than
    guessed at.
    """
    return value if isinstance(value, str) else None


# --------------------------------------------------------------------------
# checks
# --------------------------------------------------------------------------


def check_stack_state(ctx: Context) -> list[Finding]:
    """A terminal-state stack blocks the deploy before anything else matters."""
    cfn = ctx.session.client("cloudformation")
    try:
        stacks = cfn.describe_stacks(StackName=ctx.stack_name)["Stacks"]
    except ClientError as exc:
        if "does not exist" in str(exc):
            return []  # fresh create, nothing to clean up
        raise

    status = stacks[0]["StackStatus"]
    if status in TERMINAL_STACK_STATES:
        protected = stacks[0].get("EnableTerminationProtection", False)
        note = " (termination protection is ON)" if protected else ""
        return [
            Finding(
                check="stack-state",
                logical_id=ctx.stack_name,
                detail=f"stack is in {status}{note} and cannot be deployed into",
                remedy=(
                    f"scripts/deploy/cleanup_stack.sh {ctx.stack_name} (disables termination protection, deletes, waits)"
                ),
            )
        ]
    return []


def check_cost_anomaly_monitor(ctx: Context) -> list[Finding]:
    """AWS permits ONE DIMENSIONAL/SERVICE anomaly monitor per AWS account.

    The constraint is enforced on the account, not on the monitor name, so an
    env-scoped name does NOT avoid the collision. This is the check that would
    have caught the 2026-07-19 devx failure before the 20-minute create cycle.
    """
    monitors = by_type(ctx, "AWS::CE::AnomalyMonitor")
    dimensional = [
        (logical_id, props)
        for logical_id, props in monitors
        if props.get("MonitorType") == "DIMENSIONAL"
    ]
    if not dimensional:
        return []

    ce = ctx.session.client("ce")
    try:
        existing = ce.get_anomaly_monitors()["AnomalyMonitors"]
    except ClientError as exc:
        return [
            Finding(
                check="ce-anomaly-monitor",
                logical_id=dimensional[0][0],
                detail=f"could not list existing anomaly monitors: {exc}",
                remedy="grant ce:GetAnomalyMonitors, or verify manually",
                blocking=False,
            )
        ]

    existing_dimensional = [
        monitor for monitor in existing if monitor.get("MonitorType") == "DIMENSIONAL"
    ]
    findings: list[Finding] = []
    for logical_id, props in dimensional:
        name = literal(props.get("MonitorName"))
        already_ours = any(
            monitor.get("MonitorArn") in ctx.owned_physical_ids
            for monitor in existing_dimensional
        )
        if existing_dimensional and not already_ours:
            owner = existing_dimensional[0].get("MonitorName", "<unnamed>")
            findings.append(
                Finding(
                    check="ce-anomaly-monitor",
                    logical_id=logical_id,
                    detail=(
                        f"account {ctx.account_id} already has a DIMENSIONAL "
                        f"anomaly monitor ({owner!r}); AWS allows exactly one "
                        f"per account, so creating {name!r} will fail with "
                        "AlreadyExists regardless of its name"
                    ),
                    remedy=(
                        "gate this resource to the owning environment (monitoring.py: _P32_ANOMALY_OWNER_ENVIRONMENT)"
                    ),
                )
            )
    return findings


def check_budget_names(ctx: Context) -> list[Finding]:
    """Budget names are unique per account -- but they ARE env-scoped, so this
    should normally pass. It exists to catch a regression in naming."""
    budget_resources = by_type(ctx, "AWS::Budgets::Budget")
    if not budget_resources:
        return []

    client = ctx.session.client("budgets")
    findings: list[Finding] = []
    for logical_id, props in budget_resources:
        name = literal((props.get("Budget") or {}).get("BudgetName"))
        if not name or name in ctx.owned_physical_ids:
            continue
        try:
            client.describe_budget(AccountId=ctx.account_id, BudgetName=name)
        except ClientError as exc:
            if exc.response["Error"]["Code"] in {
                "NotFoundException",
                "ResourceNotFoundException",
            }:
                continue
            continue  # permission problems are not this check's business
        findings.append(
            Finding(
                check="budget-name",
                logical_id=logical_id,
                detail=f"budget {name!r} already exists in {ctx.account_id}",
                remedy="rename, or delete the orphaned budget",
            )
        )
    return findings


def check_cognito_domain(ctx: Context) -> list[Finding]:
    """Cognito hosted-UI domain prefixes are unique across ALL AWS accounts in
    a region, not just yours -- the widest uniqueness scope in the stack."""
    domains = by_type(ctx, "AWS::Cognito::UserPoolDomain")
    if not domains:
        return []

    client = ctx.session.client("cognito-idp")
    findings: list[Finding] = []
    for logical_id, props in domains:
        domain = literal(props.get("Domain"))
        if not domain:
            continue
        try:
            described = client.describe_user_pool_domain(Domain=domain)
        except ClientError:
            continue
        description = described.get("DomainDescription") or {}
        pool_id = description.get("UserPoolId")
        if pool_id and pool_id not in ctx.owned_physical_ids:
            findings.append(
                Finding(
                    check="cognito-domain",
                    logical_id=logical_id,
                    detail=(
                        f"domain prefix {domain!r} is already claimed "
                        f"(user pool {pool_id}); prefixes are globally unique "
                        "across all AWS accounts in this region"
                    ),
                    remedy="choose a different domain prefix for this environment",
                )
            )
    return findings


def check_named_iam_roles(ctx: Context) -> list[Finding]:
    """Explicit RoleNames are account-global. CDK-generated names are skipped."""
    client = ctx.session.client("iam")
    findings: list[Finding] = []
    for logical_id, props in by_type(ctx, "AWS::IAM::Role"):
        name = literal(props.get("RoleName"))
        if not name or name in ctx.owned_physical_ids:
            continue
        try:
            client.get_role(RoleName=name)
        except ClientError:
            continue  # NoSuchEntity (good) or AccessDenied (not our problem)
        findings.append(
            Finding(
                check="iam-role-name",
                logical_id=logical_id,
                detail=f"IAM role {name!r} already exists in this account",
                remedy="delete the orphaned role, or confirm it belongs to this stack",
            )
        )
    return findings


def check_dynamodb_table_names(ctx: Context) -> list[Finding]:
    """Explicit DynamoDB TableNames are account+region-scoped.

    A prior stack delete can leave these behind (``DeletionPolicy: Retain`` is
    standard for stateful tables), so the next create collides on the literal
    name even though the owning stack is gone. This is the class of failure
    that hit CareerVpCrudDevx on 2026-07-20: 11 orphaned tables from a deleted
    stack blocked change-set creation.
    """
    client = ctx.session.client("dynamodb")
    findings: list[Finding] = []
    for logical_id, props in by_type(ctx, "AWS::DynamoDB::GlobalTable"):
        name = literal(props.get("TableName"))
        if not name or name in ctx.owned_physical_ids:
            continue
        try:
            client.describe_table(TableName=name)
        except ClientError as exc:
            if exc.response["Error"]["Code"] == "ResourceNotFoundException":
                continue
            continue  # permission problems are not this check's business
        findings.append(
            Finding(
                check="dynamodb-table-name",
                logical_id=logical_id,
                detail=f"DynamoDB table {name!r} already exists in {ctx.account_id}",
                remedy=(
                    f"delete the orphaned table (aws dynamodb delete-table --table-name {name}), or confirm it belongs to this stack"
                ),
            )
        )
    return findings


def check_s3_bucket_names(ctx: Context) -> list[Finding]:
    """S3 bucket names are globally unique across ALL AWS accounts.

    Same orphan-after-delete failure mode as DynamoDB tables: a bucket left
    behind by ``DeletionPolicy: Retain`` blocks the next create on the same
    literal name.
    """
    client = ctx.session.client("s3")
    findings: list[Finding] = []
    for logical_id, props in by_type(ctx, "AWS::S3::Bucket"):
        name = literal(props.get("BucketName"))
        if not name or name in ctx.owned_physical_ids:
            continue
        try:
            client.head_bucket(Bucket=name)
        except ClientError as exc:
            if exc.response["Error"]["Code"] in {"404", "NoSuchBucket"}:
                continue
            continue  # permission problems (403 on a bucket we don't own) too
        findings.append(
            Finding(
                check="s3-bucket-name",
                logical_id=logical_id,
                detail=f"S3 bucket {name!r} already exists",
                remedy=(
                    f"delete the orphaned bucket (aws s3 rb s3://{name} --force), or confirm it belongs to this stack"
                ),
            )
        )
    return findings


def check_alarm_subscribers(ctx: Context) -> list[Finding]:
    """P-21 invariant: a synthesized stack is never left with zero alarm
    subscribers. ``resolve_alarm_emails`` returns [] for any environment absent
    from its default map, which fails silently rather than at deploy time."""
    if by_type(ctx, "AWS::SNS::Subscription"):
        return []
    return [
        Finding(
            check="alarm-subscribers",
            logical_id="<monitoring topic>",
            detail=(
                "no AWS::SNS::Subscription in any template -- this environment's "
                "monitoring topic will have zero subscribers, so every alarm is "
                "silent (P-21 invariant)"
            ),
            remedy="export ALARM_SUBSCRIPTION_EMAILS=... before synth",
            blocking=False,
        )
    ]


CHECKS = (
    check_stack_state,
    check_cost_anomaly_monitor,
    check_budget_names,
    check_cognito_domain,
    check_named_iam_roles,
    check_dynamodb_table_names,
    check_s3_bucket_names,
    check_alarm_subscribers,
)


def collect_owned_physical_ids(session: Any, stack_name: str) -> set[str]:
    """Physical ids already owned by this stack, including nested stacks.

    A resource that this stack already owns is an update, not a collision.
    """
    cfn = session.client("cloudformation")
    owned: set[str] = set()
    pending = [stack_name]
    seen: set[str] = set()

    while pending:
        current = pending.pop()
        if current in seen:
            continue
        seen.add(current)
        try:
            pages = cfn.get_paginator("list_stack_resources").paginate(
                StackName=current
            )
            for page in pages:
                for summary in page["StackResourceSummaries"]:
                    physical_id = summary.get("PhysicalResourceId")
                    if physical_id:
                        owned.add(physical_id)
                    if summary["ResourceType"] == "AWS::CloudFormation::Stack":
                        if physical_id:
                            pending.append(physical_id)
        except ClientError:
            continue  # stack absent or unreadable -> nothing owned
    return owned


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--template-dir",
        type=Path,
        required=True,
        help="cdk.out directory holding the synthesized templates",
    )
    parser.add_argument("--stack", required=True, help="target stack name")
    parser.add_argument("--region", default=None)
    parser.add_argument(
        "--json", dest="as_json", action="store_true", help="emit findings as JSON"
    )
    args = parser.parse_args()

    resources = load_templates(args.template_dir)

    try:
        session = boto3.Session(region_name=args.region)
        account_id = session.client("sts").get_caller_identity()["Account"]
    except (ClientError, NoCredentialsError) as exc:
        print(f"error: could not resolve AWS identity: {exc}", file=sys.stderr)
        return 2

    ctx = Context(
        stack_name=args.stack,
        account_id=account_id,
        region=session.region_name or "us-east-1",
        resources=resources,
        owned_physical_ids=collect_owned_physical_ids(session, args.stack),
        session=session,
    )

    findings: list[Finding] = []
    for check in CHECKS:
        try:
            findings.extend(check(ctx))
        except Exception as exc:  # a broken check must not mask the others
            findings.append(
                Finding(
                    check=check.__name__,
                    logical_id="-",
                    detail=f"check raised {type(exc).__name__}: {exc}",
                    remedy="investigate; this check did not run",
                    blocking=False,
                )
            )

    blocking = [finding for finding in findings if finding.blocking]
    warnings = [finding for finding in findings if not finding.blocking]

    if args.as_json:
        print(
            json.dumps(
                {
                    "stack": args.stack,
                    "account": account_id,
                    "templates_scanned": len(list(args.template_dir.glob("*.json"))),
                    "resources_scanned": len(resources),
                    "auto_fail": bool(blocking),
                    "blocking": [vars(f) for f in blocking],
                    "warnings": [vars(f) for f in warnings],
                },
                indent=2,
            )
        )
        return 1 if blocking else 0

    print(f"pre-flight: {args.stack} in account {account_id} ({ctx.region})")
    print(f"  scanned {len(resources)} resources across parent + nested templates")

    for finding in warnings:
        print(f"\n  WARN  [{finding.check}] {finding.logical_id}")
        print(f"        {finding.detail}")
        print(f"        -> {finding.remedy}")

    for finding in blocking:
        print(f"\n  BLOCK [{finding.check}] {finding.logical_id}")
        print(f"        {finding.detail}")
        print(f"        -> {finding.remedy}")

    if blocking:
        print(f"\nRESULT: {len(blocking)} blocking conflict(s). Do not deploy.")
        return 1

    print("\nRESULT: clear to deploy.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
