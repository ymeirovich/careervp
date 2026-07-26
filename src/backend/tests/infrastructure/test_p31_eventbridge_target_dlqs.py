"""RED contract for P-31 EventBridge target DLQs."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

os.environ.setdefault('JSII_RUNTIME_PACKAGE_CACHE', '/tmp/jsii-cache')
os.environ.setdefault('JSII_SILENCE_WARNING_UNTESTED_NODE_VERSION', '1')

from aws_cdk import App, Environment, NestedStack
from aws_cdk.assertions import Template

REPO_ROOT = Path(__file__).resolve().parents[4]
INFRA_SRC = str(REPO_ROOT / 'infra')
EXPECTED_CLEANUP_DLQ_NAME = 'careervp-artifact-cleanup-schedule-dlq-dlq-devx'
EXPECTED_BILLING_RECONCILE_DLQ_NAME = 'careervp-billing-reconcile-schedule-dlq-dlq-devx'
EXPECTED_EVENTBRIDGE_DLQ_NAMES = {
    EXPECTED_CLEANUP_DLQ_NAME,
    EXPECTED_BILLING_RECONCILE_DLQ_NAME,
}


def _all_resources() -> dict[str, dict[str, Any]]:
    sys.path = [path for path in sys.path if path != INFRA_SRC]
    sys.path.insert(0, INFRA_SRC)
    for module_name, module in list(sys.modules.items()):
        if module_name == 'careervp' or module_name.startswith('careervp.'):
            module_file = str(getattr(module, '__file__', '') or '')
            if not module_file.startswith(INFRA_SRC):
                sys.modules.pop(module_name, None)

    from careervp.naming_utils import NamingUtils  # type: ignore[import-untyped]
    from careervp.service_stack import ServiceStack  # type: ignore[import-untyped]

    app = App(context={'p26_rehome_features': 'true'})
    naming = NamingUtils(
        environment='devx',
        region='us-east-1',
        account_id='788159322332',
    )
    stack = ServiceStack(
        scope=app,
        id=naming.stack_id('crud'),
        env=Environment(account='788159322332', region='us-east-1'),
        is_production_env=False,
        naming=naming,
        stack_feature='crud',
    )
    templates = [Template.from_stack(stack)]
    templates.extend(Template.from_stack(construct) for construct in stack.node.find_all() if isinstance(construct, NestedStack))
    return {logical_id: resource for template in templates for logical_id, resource in template.to_json().get('Resources', {}).items()}


def _event_rule_by_schedule(resources: dict[str, dict[str, Any]], schedule_expression: str) -> dict[str, Any]:
    matches = [
        resource
        for resource in resources.values()
        if resource.get('Type') == 'AWS::Events::Rule' and resource.get('Properties', {}).get('ScheduleExpression') == schedule_expression
    ]
    assert len(matches) == 1, f'AC-P31-1 expected one EventBridge rule with schedule {schedule_expression}; found {len(matches)}'
    return matches[0]


def _first_target(rule: dict[str, Any], schedule_expression: str) -> dict[str, Any]:
    targets = rule.get('Properties', {}).get('Targets')
    assert isinstance(targets, list) and targets, f'AC-P31-1 rule {schedule_expression} must have at least one target'
    target = targets[0]
    assert isinstance(target, dict), f'AC-P31-1 rule {schedule_expression} target must synthesize as an object'
    return target


def _dlq_logical_id_from_target(target: dict[str, Any], schedule_expression: str) -> str:
    dead_letter_config = target.get('DeadLetterConfig')
    assert isinstance(dead_letter_config, dict), f'AC-P31-1 rule {schedule_expression} target missing DeadLetterConfig'
    arn = dead_letter_config.get('Arn')
    if isinstance(arn, dict) and isinstance(arn.get('Fn::GetAtt'), list) and arn['Fn::GetAtt']:
        return str(arn['Fn::GetAtt'][0])
    if isinstance(arn, dict) and isinstance(arn.get('Ref'), str):
        return str(arn['Ref'])
    raise AssertionError(f'AC-P31-1 rule {schedule_expression} DeadLetterConfig.Arn must resolve via Ref or Fn::GetAtt; got {arn!r}')


def _queue_name_from_alarm_dimension(alarm: dict[str, Any]) -> Any:
    for dimension in alarm.get('Properties', {}).get('Dimensions', []) or []:
        if dimension.get('Name') == 'QueueName':
            return dimension.get('Value')
    return None


def test_p31_cleanup_rule_target_has_dlq() -> None:
    """AC-P31-1: the hourly cleanup EventBridge target has an SQS DLQ."""
    resources = _all_resources()
    queues = {logical_id: resource for logical_id, resource in resources.items() if resource.get('Type') == 'AWS::SQS::Queue'}
    schedule_expression = 'rate(1 hour)'
    target = _first_target(_event_rule_by_schedule(resources, schedule_expression), schedule_expression)
    dlq_logical_id = _dlq_logical_id_from_target(target, schedule_expression)
    assert dlq_logical_id in queues, f'AC-P31-1 cleanup DeadLetterConfig.Arn points at missing SQS queue {dlq_logical_id}'


def test_p31_billing_reconcile_target_has_dlq() -> None:
    """AC-P31-1: the 02:00 billing reconcile EventBridge target has an SQS DLQ."""
    resources = _all_resources()
    queues = {logical_id: resource for logical_id, resource in resources.items() if resource.get('Type') == 'AWS::SQS::Queue'}
    schedule_expression = 'cron(0 2 * * ? *)'
    target = _first_target(_event_rule_by_schedule(resources, schedule_expression), schedule_expression)
    dlq_logical_id = _dlq_logical_id_from_target(target, schedule_expression)
    assert dlq_logical_id in queues, f'AC-P31-1 billing reconcile DeadLetterConfig.Arn points at missing SQS queue {dlq_logical_id}'


def test_p31_eventbridge_dlqs_have_depth_alarms() -> None:
    """AC-P31-2: schedule DLQs alarm on native SQS visible-message depth."""
    resources = _all_resources()
    queue_names = {resource.get('Properties', {}).get('QueueName') for resource in resources.values() if resource.get('Type') == 'AWS::SQS::Queue'}
    missing_queues = EXPECTED_EVENTBRIDGE_DLQ_NAMES - queue_names
    assert not missing_queues, f'AC-P31-2 expected these EventBridge target DLQs to exist before alarming: {sorted(missing_queues)}'

    alarms_by_queue = {
        _queue_name_from_alarm_dimension(resource): resource
        for resource in resources.values()
        if resource.get('Type') == 'AWS::CloudWatch::Alarm'
        and resource.get('Properties', {}).get('Namespace') == 'AWS/SQS'
        and resource.get('Properties', {}).get('MetricName') == 'ApproximateNumberOfMessagesVisible'
    }

    missing_alarms = sorted(name for name in EXPECTED_EVENTBRIDGE_DLQ_NAMES if name not in alarms_by_queue)
    assert not missing_alarms, (
        f'AC-P31-2 expected one native SQS ApproximateNumberOfMessagesVisible alarm per schedule DLQ; missing alarms for {missing_alarms}'
    )
    for queue_name in sorted(EXPECTED_EVENTBRIDGE_DLQ_NAMES):
        properties = alarms_by_queue[queue_name]['Properties']
        assert properties.get('Threshold') == 1, f'AC-P31-2 {queue_name} DLQ alarm Threshold must be 1'
        assert properties.get('EvaluationPeriods') == 1, f'AC-P31-2 {queue_name} DLQ alarm EvaluationPeriods must be 1'


def test_p31_dlq_names_follow_naming_convention() -> None:
    """P-31 naming precedent: schedule DLQ names are explicit env-scoped kebab-case names."""
    resources = _all_resources()
    queue_names = {resource.get('Properties', {}).get('QueueName') for resource in resources.values() if resource.get('Type') == 'AWS::SQS::Queue'}
    missing_queues = EXPECTED_EVENTBRIDGE_DLQ_NAMES - queue_names
    assert not missing_queues, f'P-31 expected schedule DLQ queues to exist before checking names: {sorted(missing_queues)}'
    for queue_name in sorted(EXPECTED_EVENTBRIDGE_DLQ_NAMES):
        assert queue_name.startswith('careervp-'), f'P-31 DLQ name must start with careervp-: {queue_name}'
        assert queue_name.endswith('-devx'), f'P-31 DLQ name must end with -devx: {queue_name}'
