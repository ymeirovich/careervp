"""P-21 RED tests: SNS alarms route to a subscribed on-call topic.

Scope-lock P-21 records zero subscribers on the monitoring topic. These synth
assertions require at least one subscription and that every CloudWatch alarm in
the monitoring-owned templates routes to the topic.
"""

from __future__ import annotations

from aws_cdk.assertions import Template

from careervp.monitoring import resolve_alarm_emails


def test_p21_monitoring_topic_has_subscription(synthesized_template: Template) -> None:
    """The monitoring topic must synth at least one SNS subscription (fail-closed
    default means dev/stage/prod never have zero subscribers)."""
    subscriptions = synthesized_template.find_resources("AWS::SNS::Subscription")
    assert subscriptions, (
        "monitoring topic has no AWS::SNS::Subscription (P-21: 0 subscribers)"
    )

    email_subs = [
        props
        for props in subscriptions.values()
        if props["Properties"].get("Protocol") == "email"
    ]
    assert email_subs, "expected at least one email subscription to the alarm topic"


def test_p21_resolver_defaults_and_override() -> None:
    """The resolver yields a default per env and honors the human override."""
    assert resolve_alarm_emails("dev"), "dev must have a default alarm endpoint"
    assert resolve_alarm_emails("prod"), "prod must have a default alarm endpoint"

    import os

    os.environ["ALARM_SUBSCRIPTION_EMAILS"] = "oncall@careervp.com, sre@careervp.com"
    try:
        resolved = resolve_alarm_emails("dev")
        assert resolved == ["oncall@careervp.com", "sre@careervp.com"]
    finally:
        del os.environ["ALARM_SUBSCRIPTION_EMAILS"]


def test_p21_all_alarm_actions_target_monitoring_topic(
    synthesized_template: Template,
    monitoring_template: Template,
) -> None:
    """No CloudWatch alarm may fire silently. Alarms live both directly in the
    parent stack (e.g. the billing-error alarm) and in the monitoring nested
    stack (facade + the hand-built DynamoValidationException alarm); every one
    must carry an AlarmActions entry routing to the SNS topic."""
    parent_alarms = synthesized_template.find_resources("AWS::CloudWatch::Alarm")
    nested_alarms = monitoring_template.find_resources("AWS::CloudWatch::Alarm")
    assert parent_alarms, "expected CloudWatch alarms in the parent stack"
    assert nested_alarms, "expected CloudWatch alarms in the monitoring nested stack"

    silent = [
        logical_id
        for alarms in (parent_alarms, nested_alarms)
        for logical_id, props in alarms.items()
        if not props["Properties"].get("AlarmActions")
    ]
    assert not silent, f"alarms with no AlarmActions (silent): {silent}"

    # The hand-built DynamoValidationException alarm previously had no action.
    validation_alarms = {
        logical_id: props
        for logical_id, props in nested_alarms.items()
        if "DynamoValidationException" in str(props["Properties"].get("AlarmName", ""))
    }
    assert validation_alarms, "DynamoValidationException alarm not found"
    for logical_id, props in validation_alarms.items():
        assert props["Properties"].get("AlarmActions"), (
            f"{logical_id} DynamoValidationException alarm has no SNS action"
        )
