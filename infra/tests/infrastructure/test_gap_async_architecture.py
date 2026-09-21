"""Gap-question generation is async: submit (gap-api) enqueues, gap-worker (SQS)
runs the LLM call outside the 30s API Gateway budget it used to exceed under real
input (HANDOFF-09)."""

from __future__ import annotations

from typing import Any, Mapping

from aws_cdk.assertions import Template

GAP_HANDLER = "careervp.handlers.gap_handler.lambda_handler"


def _gap_handler_lambdas(template: Template) -> list[Mapping[str, Any]]:
    return [
        resource
        for resource in template.find_resources("AWS::Lambda::Function").values()
        if resource["Properties"].get("Handler") == GAP_HANDLER
    ]


def test_gap_api_and_worker_share_one_pre_provisioned_queue(
    features_template: Template,
) -> None:
    """gap-api (submit) and gap-worker (SQS consumer) both use the
    gap-analysis queue that already existed in infra, unused, before this
    change — no new queue was created."""
    gap_lambdas = _gap_handler_lambdas(features_template)
    assert len(gap_lambdas) == 2, (
        f"expected gap-api and gap-worker (2 Lambdas sharing {GAP_HANDLER}), found {len(gap_lambdas)}"
    )

    submit_candidates = [
        fn
        for fn in gap_lambdas
        if "SQS_QUEUE_URL"
        in fn["Properties"].get("Environment", {}).get("Variables", {})
    ]
    assert len(submit_candidates) == 1, (
        "expected exactly one submit Lambda able to enqueue the worker"
    )

    queues = features_template.find_resources("AWS::SQS::Queue")
    gap_queue_logical_ids = [
        logical_id for logical_id in queues if "GapAnalysisQueue" in logical_id
    ]
    assert len(gap_queue_logical_ids) == 1, (
        "expected exactly one gap-analysis queue (pre-provisioned, not newly created)"
    )


def test_gap_worker_consumes_the_queue_with_a_generous_timeout(
    features_template: Template,
) -> None:
    """The worker exists specifically so the LLM call is no longer bound by the
    30s API Gateway budget — pin that it actually has a longer timeout and a
    real SQS event source on the gap-analysis queue."""
    worker_candidates = [
        fn
        for fn in _gap_handler_lambdas(features_template)
        if fn["Properties"].get("Timeout", 0) > 30
    ]
    assert len(worker_candidates) == 1, (
        "expected exactly one gap-question worker Lambda (timeout > 30s)"
    )
    assert worker_candidates[0]["Properties"]["Timeout"] >= 120

    event_sources = features_template.find_resources("AWS::Lambda::EventSourceMapping")
    matching_mappings = [
        mapping
        for mapping in event_sources.values()
        if "GapAnalysisQueue" in str(mapping["Properties"].get("EventSourceArn", {}))
    ]
    assert len(matching_mappings) == 1, (
        "expected exactly one SQS event source mapping on the gap-analysis queue"
    )


def test_gap_worker_is_not_an_api_gateway_integration_target(
    features_template: Template, synthesized_template: Template
) -> None:
    """The worker is SQS-triggered only — it must never also be reachable as an
    API Gateway route (that would put the 30s budget right back). API Gateway
    methods live in the parent stack, not the features nested stack."""
    worker_candidates = [
        fn
        for fn in _gap_handler_lambdas(features_template)
        if fn["Properties"].get("Timeout", 0) > 30
    ]
    worker_function_name = worker_candidates[0]["Properties"]["FunctionName"]

    methods = synthesized_template.find_resources("AWS::ApiGateway::Method")
    assert methods, "expected the parent template to contain API Gateway methods"
    for method in methods.values():
        integration = method["Properties"].get("Integration", {})
        uri = integration.get("Uri", {})
        assert worker_function_name not in str(uri), (
            f"gap-worker ({worker_function_name}) must not be an API Gateway integration target"
        )
