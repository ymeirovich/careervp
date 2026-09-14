"""K9 regression: the artifact-cleanup Lambda must actually receive the jobs
table name it requires at runtime.

Live metrics before this fix: 336 errors across 336 invocations in 14 days,
matching MissingTableEnvError in the logs — artifact_cleanup_handler.py calls
require_table_env('DYNAMODB_TABLE_NAME', purpose='jobs'), but its environment
came from `**self._build_shared_table_env()` plus VPR_RESULTS_BUCKET_NAME,
and _build_shared_table_env never included DYNAMODB_TABLE_NAME (or any
jobs-table entry at all) — the cleanup job had never once succeeded.

No fallback default is added here deliberately (see the handler's own
comment) — that would hide the next occurrence of exactly this bug. This
test is the "alarm" for it: it fails if the variable — or the IAM grant that
lets the handler actually use it — goes missing again.
"""

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


def _find_artifact_cleanup_function(resources: dict[str, dict[str, Any]]) -> dict[str, Any]:
    candidates = [
        resource
        for logical_id, resource in resources.items()
        if resource.get('Type') == 'AWS::Lambda::Function' and 'ArtifactCleanup' in logical_id
    ]
    assert len(candidates) == 1, f'K9 expected exactly one ArtifactCleanup Lambda function, found {len(candidates)}'
    return candidates[0]


def test_k9_artifact_cleanup_lambda_has_jobs_table_env_var() -> None:
    """K9 done-when: the deployed Lambda's environment actually carries
    DYNAMODB_TABLE_NAME — the exact key artifact_cleanup_handler.py's
    require_table_env('DYNAMODB_TABLE_NAME', purpose='jobs') reads — and it
    points at the real jobs table, not just any table sharing that key name
    elsewhere in the codebase (DYNAMODB_TABLE_NAME is reused for different
    tables across other Lambdas)."""
    resources = _all_resources()
    function = _find_artifact_cleanup_function(resources)
    env_vars = function['Properties']['Environment']['Variables']
    assert 'DYNAMODB_TABLE_NAME' in env_vars, (
        'K9: ArtifactCleanup Lambda is missing DYNAMODB_TABLE_NAME — this is exactly the '
        'defect that produced 336/336 failed invocations (MissingTableEnvError).'
    )

    jobs_table_import_base = _find_jobs_table_cross_stack_import_base(resources)
    value = env_vars['DYNAMODB_TABLE_NAME']
    assert jobs_table_import_base in str(value), (
        f'K9: ArtifactCleanup Lambda has DYNAMODB_TABLE_NAME set, but not to the jobs table '
        f'(expected a reference containing {jobs_table_import_base!r}, got {value!r})'
    )


def _find_jobs_table_cross_stack_import_base(resources: dict[str, dict[str, Any]]) -> str:
    """The jobs table is defined in a nested db stack; this "crud" stack (and
    every Lambda in it) only ever sees it via a CloudFormation cross-stack
    import parameter, not a direct AWS::DynamoDB::Table resource — so there's
    no table logical id to key off here. Every already-correct consumer (e.g.
    vpr_submit, vpr_status, the VPR SQS worker) carries VPR_JOBS_TABLE_NAME
    set to `{"Ref": "referenceto...jobsXXXXXXXX Ref"}`; the shared base of
    that import name (without the trailing Ref/Arn suffix) is what a matching
    IAM grant's Resource field will also reference.
    """
    for resource in resources.values():
        if resource.get('Type') != 'AWS::Lambda::Function':
            continue
        env_vars = resource.get('Properties', {}).get('Environment', {}).get('Variables', {})
        ref = env_vars.get('VPR_JOBS_TABLE_NAME')
        if isinstance(ref, dict) and isinstance(ref.get('Ref'), str) and ref['Ref'].endswith('Ref'):
            return ref['Ref'][: -len('Ref')]
    raise AssertionError('K9: could not find any Lambda already wired to the jobs table via VPR_JOBS_TABLE_NAME to derive the cross-stack import name from')


def test_k9_artifact_cleanup_lambda_can_read_write_jobs_table() -> None:
    """The env var alone isn't enough — the reaper reads (get_job, scan_by_status)
    and writes (update_job_status) the jobs table specifically, so it needs an
    IAM grant naming that table's ARN, not just any DynamoDB grant (the
    pre-existing applications-table grant alone would make a looser assertion
    pass without actually fixing K9)."""
    resources = _all_resources()
    function = _find_artifact_cleanup_function(resources)
    jobs_table_import_base = _find_jobs_table_cross_stack_import_base(resources)

    role_arn_ref = function['Properties']['Role']
    role_logical_id = role_arn_ref['Fn::GetAtt'][0] if isinstance(role_arn_ref, dict) else None
    assert role_logical_id, 'K9: could not resolve the ArtifactCleanup Lambda execution role'

    policies_on_role = [
        resource
        for resource in resources.values()
        if resource.get('Type') == 'AWS::IAM::Policy'
        and any(
            ref.get('Ref') == role_logical_id
            for ref in resource.get('Properties', {}).get('Roles', [])
            if isinstance(ref, dict)
        )
    ]

    jobs_table_actions: set[str] = set()
    for policy in policies_on_role:
        for statement in policy['Properties']['PolicyDocument']['Statement']:
            resource_field = statement.get('Resource', [])
            if isinstance(resource_field, (dict, str)):
                resource_field = [resource_field]
            references_jobs_table = any(jobs_table_import_base in str(entry) for entry in resource_field)
            if not references_jobs_table:
                continue
            statement_actions = statement.get('Action', [])
            if isinstance(statement_actions, str):
                statement_actions = [statement_actions]
            jobs_table_actions.update(statement_actions)

    assert jobs_table_actions, (
        'K9: no IAM policy statement on the ArtifactCleanup Lambda role references the '
        'jobs table at all — DYNAMODB_TABLE_NAME can be set and every jobs_repo call '
        'would still fail with AccessDenied.'
    )
    assert 'dynamodb:GetItem' in jobs_table_actions or 'dynamodb:Query' in jobs_table_actions, (
        'K9: ArtifactCleanup Lambda role has no read grant on the jobs table '
        '(jobs_repo.get_job/scan_by_status)'
    )
    assert 'dynamodb:UpdateItem' in jobs_table_actions or 'dynamodb:PutItem' in jobs_table_actions, (
        'K9: ArtifactCleanup Lambda role has no write grant on the jobs table '
        '(jobs_repo.update_job_status)'
    )
