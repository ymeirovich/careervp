"""RED contract for P-17 DLQ depth alarms."""

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
EXPECTED_DLQ_NAMES = {
    'careervp-vpr-jobs-dlq-dlq-devx',
    'careervp-cover-letter-jobs-dlq-dlq-devx',
    'careervp-interview-prep-jobs-dlq-dlq-devx',
    'careervp-cv-upload-dlq-devx',
    'careervp-gap-analysis-dlq-devx',
    'careervp-company-research-dlq-devx',
    'careervp-cv-upload-worker-dlq-devx',
    'careervp-cv-tailor-worker-dlq-devx',
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


def _queue_name_from_alarm_dimension(alarm: dict[str, Any]) -> Any:
    for dimension in alarm.get('Properties', {}).get('Dimensions', []) or []:
        if dimension.get('Name') == 'QueueName':
            return dimension.get('Value')
    return None


def test_p17_all_eight_dlqs_have_depth_alarms() -> None:
    """P-17 done-when: all eight DLQs alarm on native SQS visible-message depth."""
    resources = _all_resources()
    queue_names = {resource.get('Properties', {}).get('QueueName') for resource in resources.values() if resource.get('Type') == 'AWS::SQS::Queue'}
    missing_queues = EXPECTED_DLQ_NAMES - queue_names
    assert not missing_queues, f'P-17 expected these eight DLQs to exist before alarming: {sorted(missing_queues)}'

    alarms_by_queue = {
        _queue_name_from_alarm_dimension(resource): resource
        for resource in resources.values()
        if resource.get('Type') == 'AWS::CloudWatch::Alarm'
        and resource.get('Properties', {}).get('Namespace') == 'AWS/SQS'
        and resource.get('Properties', {}).get('MetricName') == 'ApproximateNumberOfMessagesVisible'
    }

    missing_alarms = sorted(name for name in EXPECTED_DLQ_NAMES if name not in alarms_by_queue)
    assert not missing_alarms, f'P-17 expected one native SQS ApproximateNumberOfMessagesVisible alarm per DLQ; missing alarms for {missing_alarms}'
    for queue_name in sorted(EXPECTED_DLQ_NAMES):
        properties = alarms_by_queue[queue_name]['Properties']
        assert properties.get('Threshold') == 1, f'P-17 {queue_name} DLQ alarm Threshold must be 1'
        assert properties.get('EvaluationPeriods') == 1, f'P-17 {queue_name} DLQ alarm EvaluationPeriods must be 1'
