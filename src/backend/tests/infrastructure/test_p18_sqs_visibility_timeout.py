"""RED contract for P-18 SQS visibility timeout ratios."""

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
DEFAULT_SQS_VISIBILITY_TIMEOUT_SECONDS = 30


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


def _ref_logical_id(value: Any) -> str:
    if isinstance(value, dict) and isinstance(value.get('Ref'), str):
        return str(value['Ref'])
    raise AssertionError(f'AC-P18-1 expected Ref logical id, got {value!r}')


def _getatt_logical_id(value: Any) -> str:
    if isinstance(value, dict) and isinstance(value.get('Fn::GetAtt'), list) and value['Fn::GetAtt']:
        return str(value['Fn::GetAtt'][0])
    raise AssertionError(f'AC-P18-1 expected Fn::GetAtt logical id, got {value!r}')


def test_p18_visibility_timeout_at_least_6x_lambda_timeout() -> None:
    """AC-P18-1: every SQS queue visibility timeout is at least 6x its consumer timeout."""
    resources = _all_resources()
    queues = {logical_id: resource for logical_id, resource in resources.items() if resource.get('Type') == 'AWS::SQS::Queue'}
    functions = {logical_id: resource for logical_id, resource in resources.items() if resource.get('Type') == 'AWS::Lambda::Function'}
    sqs_mappings = {
        logical_id: resource
        for logical_id, resource in resources.items()
        if resource.get('Type') == 'AWS::Lambda::EventSourceMapping'
        and isinstance(resource.get('Properties', {}).get('EventSourceArn'), dict)
        and 'Fn::GetAtt' in resource.get('Properties', {}).get('EventSourceArn', {})
    }

    assert sqs_mappings, 'AC-P18-1 expected at least one SQS Lambda event source mapping'
    for mapping_id, mapping in sorted(sqs_mappings.items()):
        properties = mapping.get('Properties', {})
        queue_id = _getatt_logical_id(properties.get('EventSourceArn'))
        function_id = _ref_logical_id(properties.get('FunctionName'))
        queue = queues[queue_id]
        function = functions[function_id]
        visibility_timeout_seconds = int(queue.get('Properties', {}).get('VisibilityTimeout', DEFAULT_SQS_VISIBILITY_TIMEOUT_SECONDS))
        function_timeout_seconds = int(function.get('Properties', {}).get('Timeout'))
        assert visibility_timeout_seconds >= 6 * function_timeout_seconds, (
            f'AC-P18-1 {mapping_id} queue {queue_id} visibility_timeout_seconds={visibility_timeout_seconds} '
            f'must be >= 6 * function {function_id} timeout_seconds={function_timeout_seconds}'
        )
