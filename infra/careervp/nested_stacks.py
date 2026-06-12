"""Nested-stack boundaries for CareerVP (FE-UI-036).

CareerVpCrudDev sat at 495+/500 CloudFormation resources — one addition away
from CloudFormation's hard per-template limit. To keep deploys atomic
(``make deploy`` still deploys everything) while escaping that ceiling, leaf,
outbound-only subtrees are relocated into ``aws_cdk.NestedStack`` instances.
Each nested stack is its own template with its own 500-resource budget; the
parent only counts one ``AWS::CloudFormation::Stack`` resource per nested stack.

Cardinal rule (see FE-UI-036): nested-stack references must form a DAG. All
shared, widely-referenced resources (the shared ``lambda_role``, DynamoDB
tables, S3 buckets, SQS queues + DLQs, KMS keys, API Gateway, Cognito) stay in
the PARENT. A nested stack may reference parent resources downward (CDK wires
those as ``CfnParameter`` automatically); the parent must never depend back on a
nested stack's internals except through an explicit nested-stack output
consumed by a *different* parent resource.

These classes are intentionally thin: resources are attached to them by passing
the nested stack as the ``scope`` argument to the existing builder methods on
``ApiConstruct``. This keeps the (already validated) construction logic in one
place while moving the emitted resources into a separate template. Stateful
resources (DynamoDB/S3/KMS) are never created under these scopes — only
stateless Lambdas, log groups, IAM roles/policies, alarms, dashboards, and the
Step Functions state machine.
"""

from __future__ import annotations

from typing import Any

from aws_cdk import NestedStack, Stack
from cdk_nag import NagSuppressions
from constructs import Construct

# Canonical cdk-nag suppressions for CareerVP. The ``AwsSolutionsChecks`` aspect
# is added on the parent ServiceStack and propagates into nested stacks, but
# stack-level NagSuppressions do NOT propagate across the nested-stack boundary.
# This single source of truth is therefore applied to the parent AND to every
# nested stack so relocated resources keep their existing, reviewed suppressions.
NAG_SUPPRESSIONS: list[dict[str, str]] = [
    {"id": "AwsSolutions-IAM4", "reason": "policy for cloudwatch logs."},
    {"id": "AwsSolutions-IAM5", "reason": "policy for cloudwatch logs."},
    {"id": "AwsSolutions-APIG2", "reason": "lambda does input validation"},
    {"id": "AwsSolutions-APIG1", "reason": "not mandatory in a sample blueprint"},
    {"id": "AwsSolutions-APIG3", "reason": "not mandatory in a sample blueprint"},
    {"id": "AwsSolutions-APIG6", "reason": "not mandatory in a sample blueprint"},
    {
        "id": "AwsSolutions-APIG4",
        "reason": "authorization not mandatory in a sample blueprint",
    },
    {
        "id": "AwsSolutions-COG1",
        "reason": "Beta policy intentionally allows no-symbol passwords for UX.",
    },
    {
        "id": "AwsSolutions-COG3",
        "reason": "Advanced security mode rollout deferred for beta hardening phase.",
    },
    {
        "id": "AwsSolutions-COG4",
        "reason": "Public auth/health/swagger routes are intentionally unauthenticated.",
    },
    {"id": "AwsSolutions-L1", "reason": "False positive"},
    {
        "id": "AwsSolutions-S1",
        "reason": "CV bucket access logs not needed in dev; enable in production",
    },
    {
        "id": "AwsSolutions-SQS4",
        "reason": "VPR async queues are internal, SSL not required",
    },
    {
        "id": "AwsSolutions-SQS3",
        "reason": "Worker DLQs are terminal destinations and should not chain DLQs",
    },
    {
        "id": "AwsSolutions-SF1",
        "reason": (
            "Artifact chain logs at ERROR level by design (FE-UI-031) to control "
            "CloudWatch costs; execution data logging is intentionally disabled."
        ),
    },
    {
        "id": "AwsSolutions-SF2",
        "reason": "X-Ray tracing is enabled on the artifact-chain state machine.",
    },
]


def apply_nag_suppressions(stack: Stack) -> None:
    """Apply the canonical CareerVP nag suppressions to a (nested or parent) stack."""
    NagSuppressions.add_stack_suppressions(stack, NAG_SUPPRESSIONS)


class ArtifactChainNestedStack(NestedStack):
    """Holds the artifact-chain failure handlers, their dedicated role, and the
    Step Functions state machine (FE-UI-031/035).

    The state machine references parent queues (downward) and is consumed by the
    parent ``gap_api_func`` / company-research worker through a state-machine ARN
    that those parent Lambdas read — a parent->nested edge to a leaf, not a
    cycle. The shared ``lambda_role``-backed company-research worker stays in the
    parent so the shared role never gains a back-edge into this stack.
    """

    def __init__(self, scope: Construct, construct_id: str, **kwargs: Any) -> None:
        super().__init__(scope, construct_id, **kwargs)


class AsyncWorkersNestedStack(NestedStack):
    """Holds the queue/stream-driven async worker Lambdas (cv-tailor,
    cover-letter, interview-prep, vpr-sqs-worker, vpr-dlq-handler, vpr-worker).

    Every worker here is triggered by a parent SQS queue, parent DynamoDB stream,
    or invoked manually — never by an S3 bucket notification (that would make the
    parent bucket depend on a nested Lambda). Their EventSourceMappings are
    children of the Lambda (nested) and reference parent queues/streams downward.
    The cv-upload worker (S3-triggered) deliberately stays in the parent.
    """

    def __init__(self, scope: Construct, construct_id: str, **kwargs: Any) -> None:
        super().__init__(scope, construct_id, **kwargs)
