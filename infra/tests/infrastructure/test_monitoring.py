from __future__ import annotations

from aws_cdk.assertions import Template


def test_monitoring_includes_company_research_latency_alarm(
    monitoring_template: Template,
) -> None:
    """Ensure the CrudMonitoring dashboard adds latency alarms for the new Lambda."""
    alarms = monitoring_template.find_resources("AWS::CloudWatch::Alarm")
    matching = [
        props
        for props in alarms.values()
        if "careervp-company-research-lambda-dev"
        in props["Properties"].get("AlarmName", "")
    ]
    assert matching, "Latency alarm for careervp-company-research-lambda-dev not found"


def test_monitoring_sns_topic_encrypted(synthesized_template: Template) -> None:
    """SNS topic used for alarms must be encrypted with a KMS key."""
    topics = synthesized_template.find_resources("AWS::SNS::Topic")
    encrypted_topics = [
        props
        for props in topics.values()
        if props["Properties"].get("KmsMasterKeyId") is not None
    ]
    assert encrypted_topics, "Monitoring SNS topic missing KMS encryption"


def test_monitoring_includes_dynamodb_validation_exception_alarm(
    monitoring_template: Template,
) -> None:
    """Ensure monitoring captures DynamoDB ValidationException spikes from Lambda logs."""
    metric_filters = monitoring_template.find_resources("AWS::Logs::MetricFilter")
    assert metric_filters, (
        "Expected CloudWatch metric filters for Lambda error patterns"
    )

    validation_filters = [
        props
        for props in metric_filters.values()
        if "ValidationException" in str(props["Properties"].get("FilterPattern", ""))
    ]
    assert validation_filters, (
        "No CloudWatch metric filter found for DynamoDB ValidationException"
    )

    alarms = monitoring_template.find_resources("AWS::CloudWatch::Alarm")
    assert any(
        "DynamoValidationException" in str(props["Properties"].get("AlarmName", ""))
        for props in alarms.values()
    ), "No CloudWatch alarm found for DynamoDB ValidationException spikes"


def test_monitoring_includes_cost_per_application_alarm(
    monitoring_template: Template,
) -> None:
    alarms = monitoring_template.find_resources("AWS::CloudWatch::Alarm")
    matching = [
        props["Properties"]
        for props in alarms.values()
        if props["Properties"].get("Threshold") == 0.375
        and props["Properties"].get("ComparisonOperator") == "GreaterThanThreshold"
    ]
    assert matching, "No CloudWatch alarm found for Q-10 cost-per-application threshold"
