from __future__ import annotations

from aws_cdk.assertions import Template


def test_monitoring_includes_company_research_latency_alarm(
    synthesized_template: Template,
) -> None:
    """Ensure the CrudMonitoring dashboard adds latency alarms for the new Lambda."""
    alarms = synthesized_template.find_resources("AWS::CloudWatch::Alarm")
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
