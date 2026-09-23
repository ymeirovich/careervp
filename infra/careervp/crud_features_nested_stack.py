"""P-26 Job 1 — CrudFeaturesNestedStack.

The ``CareerVpCrudDev`` parent template sits near the 500-resource CloudFormation
hard limit, blocking the additive waves (P-09/P-14/P-17/P-21). P-26 Job 1
decomposes AROUND the RestApi: every explicitly-named, non-stateful feature
resource (feature Lambdas + their log groups, the async SQS queues/DLQs, the
per-worker DLQs, the artifact-chain state machine + failure handlers) is
re-homed into this single nested stack, while the RestApi, the Cognito user
pool, the shared Lambda role, and every DynamoDB table / S3 bucket stay in the
parent (moving any of those is a stateful/URL-changing replacement — forbidden).

Because those resources are already deployed under explicit physical names, the
relocation is a human-gated CloudFormation resource-import (``cdk refactor``,
amendment Option A), NOT a plain additive change set: the physical resource is
preserved (no delete/create, no "resource already exists") and its deployed
logical id is preserved byte-for-byte via :func:`careervp.rehome_map.rehome`.
This construct is only the scope the re-homed resources are parented under; the
resource graph itself is authored by ``ApiConstruct``/``ApiDbConstruct`` so the
existing wiring (env vars, grants, event sources, routes) is unchanged.
"""

from __future__ import annotations

from typing import Any

from aws_cdk import NestedStack
from cdk_nag import NagSuppressions
from constructs import Construct

from .naming_utils import NamingUtils


class CrudFeaturesNestedStack(NestedStack):
    """Holds the P-26 Job-1 re-homed feature resources off the parent stack."""

    def __init__(
        self,
        scope: Construct,
        id_: str,
        *,
        naming: NamingUtils,
        **kwargs: Any,
    ) -> None:
        super().__init__(scope, id_, **kwargs)
        self.naming = naming
        self._add_nag_suppressions()

    def _add_nag_suppressions(self) -> None:
        """Carry the parent's accepted cdk-nag suppressions to the re-homed resources.

        The Lambdas, roles, and queues in this stack were previously in the parent
        ServiceStack, where these exact suppressions were already accepted. Stack-
        level suppressions do not propagate across a nested-stack boundary, so the
        same set is re-declared here — the security posture of these resources is
        unchanged by the P-26 Job-1 relocation; only their template moved.
        """
        NagSuppressions.add_stack_suppressions(
            self,
            [
                {"id": "AwsSolutions-IAM4", "reason": "policy for cloudwatch logs."},
                {"id": "AwsSolutions-IAM5", "reason": "policy for cloudwatch logs."},
                {"id": "AwsSolutions-L1", "reason": "False positive"},
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
                    "reason": "Artifact chain logs at ERROR level by design (FE-UI-031) to control CloudWatch costs; execution data logging is intentionally disabled.",
                },
            ],
        )
