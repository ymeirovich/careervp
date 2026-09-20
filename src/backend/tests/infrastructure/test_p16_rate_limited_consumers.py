"""RED contract for P-16 rate-limited worker concurrency bounds."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

os.environ.setdefault('JSII_RUNTIME_PACKAGE_CACHE', '/tmp/jsii-cache')
os.environ.setdefault('JSII_SILENCE_WARNING_UNTESTED_NODE_VERSION', '1')

from aws_cdk import App, Environment, NestedStack
from aws_cdk.assertions import Template

from tests.import_isolation import careervp_root

REPO_ROOT = Path(__file__).resolve().parents[4]
INFRA_SRC = str(REPO_ROOT / 'infra')

EXPECTED_RESERVED_CONCURRENCY = 5
RATE_LIMITED_WORKERS = {
    'VprSqsWorkerLambda': 'careervp-vpr-sqs-worker-lambda-devx',
    'CoverLetterWorkerLambda': 'careervp-cover-letter-worker-lambda-devx',
    'InterviewPrepWorkerLambda': 'careervp-interview-prep-worker-lambda-devx',
    'CvTailorWorkerLambda': 'careervp-cv-tailor-worker-lambda-devx',
    'CompanyResearchWorkerLambda': 'careervp-company-research-worker-lambda-devx',
}


def _all_resources() -> dict[str, dict[str, Any]]:
    with careervp_root(INFRA_SRC):
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


def test_p16_rate_limited_consumers_have_max_concurrency() -> None:
    """AC-P16-1: every rate-limited generation worker has reserved concurrency 5."""
    resources = _all_resources()
    lambda_functions = {
        resource.get('Properties', {}).get('FunctionName'): (logical_id, resource)
        for logical_id, resource in resources.items()
        if resource.get('Type') == 'AWS::Lambda::Function'
    }

    for construct_id, function_name in RATE_LIMITED_WORKERS.items():
        assert function_name in lambda_functions, f'AC-P16-1 missing {construct_id} function {function_name}'
        logical_id, function_resource = lambda_functions[function_name]
        actual = function_resource.get('Properties', {}).get('ReservedConcurrentExecutions')
        assert actual == EXPECTED_RESERVED_CONCURRENCY, (
            f'AC-P16-1 {construct_id} ({logical_id}, {function_name}) must set '
            f'ReservedConcurrentExecutions={EXPECTED_RESERVED_CONCURRENCY}; got {actual!r}'
        )
