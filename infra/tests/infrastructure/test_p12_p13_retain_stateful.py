"""P-12/P-13 RED tests: stateful resources RETAIN + deletion protection.

Wave 0 deploy #1 (see specs/P-12-P-13-retain-stateful-spec.md). Every
DynamoDB table and S3 bucket must survive a stack deletion/replacement, and
any dead RETAIN-flagged stack module must not be relied on for that safety
claim if it's never instantiated.
"""

from __future__ import annotations

import importlib

from aws_cdk.assertions import Template


def test_p12_all_dynamodb_tables_retain_and_deletion_protected(
    synthesized_template: Template,
) -> None:
    # TableV2 synthesizes to AWS::DynamoDB::GlobalTable (even single-region).
    tables = synthesized_template.find_resources("AWS::DynamoDB::GlobalTable")
    assert tables, "expected at least one AWS::DynamoDB::GlobalTable resource"

    for logical_id, table in tables.items():
        assert table["DeletionPolicy"] == "Retain", (
            f"{logical_id} DeletionPolicy must be Retain"
        )
        assert table["UpdateReplacePolicy"] == "Retain", (
            f"{logical_id} UpdateReplacePolicy must be Retain"
        )
        replicas = table["Properties"]["Replicas"]
        for replica in replicas:
            assert replica.get("DeletionProtectionEnabled") is True, (
                f"{logical_id} replica {replica.get('Region')} must have "
                "DeletionProtectionEnabled=true"
            )


def test_p12_all_stateful_buckets_retain_no_auto_delete(
    synthesized_template: Template,
) -> None:
    buckets = synthesized_template.find_resources("AWS::S3::Bucket")
    assert buckets, "expected at least one AWS::S3::Bucket resource"

    for logical_id, bucket in buckets.items():
        assert bucket["DeletionPolicy"] == "Retain", (
            f"{logical_id} DeletionPolicy must be Retain"
        )
        assert bucket["UpdateReplacePolicy"] == "Retain", (
            f"{logical_id} UpdateReplacePolicy must be Retain"
        )

    # auto_delete_objects provisions a Custom::S3AutoDeleteObjects resource
    # per bucket; none should exist once buckets are retained.
    auto_delete_resources = synthesized_template.find_resources(
        "Custom::S3AutoDeleteObjects"
    )
    assert not auto_delete_resources, (
        "no bucket should have an auto-delete-objects custom resource "
        f"once retained: {list(auto_delete_resources)}"
    )


def test_p13_dead_retain_stacks_not_instantiated_or_removed() -> None:
    for dead_module in ("careervp.dynamodb_stack", "careervp.s3_stack"):
        try:
            importlib.import_module(dead_module)
        except ModuleNotFoundError:
            continue
        else:
            raise AssertionError(
                f"{dead_module} must be removed (P-13): it is not instantiated "
                "by app.py/service_stack.py and its RETAIN posture is not a "
                "real safety guarantee"
            )
