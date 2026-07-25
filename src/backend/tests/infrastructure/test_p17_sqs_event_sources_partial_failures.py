"""RED contract for P-17 SQS event source partial batch failure reporting."""

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


def _is_sqs_event_source_mapping(mapping: dict[str, Any]) -> bool:
    event_source_arn = mapping.get('Properties', {}).get('EventSourceArn')
    return isinstance(event_source_arn, dict) and isinstance(event_source_arn.get('Fn::GetAtt'), list)


def test_p17_all_sqs_event_sources_report_batch_item_failures() -> None:
    """AC-P17-1 infra half: every SQS event source reports per-record failures."""
    resources = _all_resources()
    mappings = {
        logical_id: resource
        for logical_id, resource in resources.items()
        if resource.get('Type') == 'AWS::Lambda::EventSourceMapping' and _is_sqs_event_source_mapping(resource)
    }

    assert mappings, 'AC-P17-1 expected at least one SQS Lambda event source mapping'
    for logical_id, mapping in sorted(mappings.items()):
        actual = mapping.get('Properties', {}).get('FunctionResponseTypes')
        assert actual == ['ReportBatchItemFailures'], (
            f"AC-P17-1 {logical_id} must set FunctionResponseTypes to exactly ['ReportBatchItemFailures']; got {actual!r}"
        )
