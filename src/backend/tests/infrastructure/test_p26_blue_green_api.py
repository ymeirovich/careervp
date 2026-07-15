"""P-26 (Blue/Green API + CFN decomposition) — TDD-first invariant guard tests.

scope_lock_clause: P-26

These are the RED tests the P-26 spec
(``docs/db-redesign/code/code-analysis/project/specs/P-26-blue-green-api-spec.md``)
lists under "RED tests to write first". They are written as **fail-closed
invariant guards** for the two non-negotiable laws of the clause:

  1. NEVER move the existing ``AWS::ApiGateway::RestApi`` in place or across
     stacks — a cross-stack move is a CFN delete+create that changes the
     ``execute-api`` id/URL and takes 908 live dev users offline.
  2. NEVER move / replace the Cognito ``AWS::Cognito::UserPool`` — an
     unrecoverable loss of 908 accounts.

They synthesize ``CareerVpCrudDev`` (the live 908-user stack) and assert the
RestApi logical id / invoke URL, per-template CFN-limit headroom, the stable
custom-domain seam, and the Cognito pool are all intact. Job-2 tests exercise
the already-shipped P-28 replacement-report auto-fail gate and assert the
base-path FLIP / old-API RETIRE are not automation-executable.

NOTE (Job-1 status): the Job-1 *decomposition* (moving feature Lambdas into
per-feature nested stacks) is **BLOCKED pending an Amendment Proposal** — see
``specs/amendments/P-26-job1-resource-import-amendment.md``. Live truth
(``infra/careervp/api_construct.py`` builds every feature Lambda/log-group with an
explicit physical name, already deployed, and the artifact-chain state machine
export-locks the workers) contradicts the spec's "additive plain-change-set move"
mechanism; a safe relocation requires a human-gated CloudFormation
resource-import (``cdk refactor``) migration. These guard tests are the safety
net that a later resource-import migration must keep green.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

import pytest

os.environ.setdefault('JSII_RUNTIME_PACKAGE_CACHE', '/tmp/jsii-cache')

try:
    from aws_cdk import App, Environment
    from aws_cdk.assertions import Template

    CDK_AVAILABLE = True
except Exception:  # pragma: no cover - environment guard
    CDK_AVAILABLE = False

pytestmark = pytest.mark.skipif(not CDK_AVAILABLE, reason='aws-cdk not available')

REPO_ROOT = Path(__file__).resolve().parents[4]
INFRA_SRC = str(REPO_ROOT / 'infra')
CI_SCRIPTS = str(REPO_ROOT / 'scripts' / 'ci')

# The live, deployed dev RestApi logical id. This is the 908-user backend's
# execute-api anchor: if a refactor moves the RestApi across a stack boundary,
# CDK re-hashes this construct path and this constant changes — which is exactly
# the catastrophe these tests exist to prevent.
DEV_REST_API_LOGICAL_ID = 'CareerVpCrudDevCrudservicerestapi5E02FD49'
DEV_CUSTOM_DOMAIN = 'api.dev.careervp.com'
CFN_TEMPLATE_RESOURCE_LIMIT = 500
PARENT_HEADROOM_TARGET = 400  # warn-only, per spec (not a failing gate)


def _dev_stack() -> Any:
    if INFRA_SRC not in sys.path:
        sys.path.insert(0, INFRA_SRC)

    from careervp.naming_utils import NamingUtils  # type: ignore[import-not-found]
    from careervp.service_stack import ServiceStack  # type: ignore[import-not-found]

    app = App()
    naming = NamingUtils(environment='dev', region='us-east-1', account_id='788159322332')
    return ServiceStack(
        scope=app,
        id=naming.stack_id('crud'),
        env=Environment(account='788159322332', region='us-east-1'),
        is_production_env=False,
        naming=naming,
        stack_feature='crud',
    )


def _parent_template() -> Template:
    return Template.from_stack(_dev_stack())


# --------------------------------------------------------------------------- #
# Law 1 — the RestApi is never moved in place or across stacks.
# --------------------------------------------------------------------------- #
def test_rest_api_present_and_singular_in_parent() -> None:
    """Exactly one RestApi lives in the parent (guards add/remove/move).

    A NEW RestApi in the parent (Job-2 forbidden) or a removed/moved RestApi
    both trip this.
    """
    rest_apis = _parent_template().find_resources('AWS::ApiGateway::RestApi')
    assert len(rest_apis) == 1, f'expected exactly one RestApi in the CareerVpCrudDev parent template, found {len(rest_apis)}: {sorted(rest_apis)}'


def test_rest_api_logical_id_unchanged() -> None:
    """The RestApi logical id equals the committed, deployed dev id.

    MUST FAIL if any refactor moves the RestApi across a stack boundary (which
    re-hashes the construct path → changes the execute-api id and invoke URL).
    """
    rest_apis = _parent_template().find_resources('AWS::ApiGateway::RestApi')
    assert list(rest_apis) == [DEV_REST_API_LOGICAL_ID], (
        'RestApi logical id drifted from the deployed dev anchor '
        f'{DEV_REST_API_LOGICAL_ID!r} to {sorted(rest_apis)!r}; a changed logical '
        'id means a changed execute-api id/URL and 908 users lose the backend.'
    )


def test_invoke_url_outputs_reference_the_rest_api() -> None:
    """The Apigateway + RawApiInvokeUrl outputs derive from the in-parent RestApi.

    Proves the published invoke URL is byte-derived from the unchanged RestApi
    ``Ref`` — not from a moved/replaced API.
    """
    template = _parent_template()
    outputs = template.to_json().get('Outputs', {})
    referenced: list[str] = []
    for name in ('Apigateway', 'RawApiInvokeUrl'):
        assert name in outputs, f'missing CfnOutput {name!r}'
        blob = repr(outputs[name].get('Value'))
        assert DEV_REST_API_LOGICAL_ID in blob, f'output {name!r} does not reference the RestApi logical id {DEV_REST_API_LOGICAL_ID!r}'
        referenced.append(name)
    assert referenced == ['Apigateway', 'RawApiInvokeUrl']


# --------------------------------------------------------------------------- #
# CFN 500-resource hard limit — no single template may reach it.
# --------------------------------------------------------------------------- #
def test_no_single_template_reaches_cfn_limit() -> None:
    """No synthesized template (parent or nested) reaches the 500 hard limit.

    MUST FAIL if a NEW RestApi subtree (~+175 resources) is mistakenly added to
    the near-limit parent instead of its own stack.
    """
    stack = _dev_stack()
    templates: dict[str, Template] = {'CareerVpCrudDev(parent)': Template.from_stack(stack)}
    for attr in (
        'monitoring_nested_stack',
        'ai_assist_nested_stack',
        'error_report_nested_stack',
        'company_research_nested_stack',
    ):
        nested = getattr(stack, attr, None)
        if nested is not None:
            templates[attr] = Template.from_stack(nested)

    counts = {name: len(t.to_json().get('Resources', {})) for name, t in templates.items()}
    for name, count in counts.items():
        assert count < CFN_TEMPLATE_RESOURCE_LIMIT, (
            f'template {name} has {count} resources — at/over the CFN hard limit of {CFN_TEMPLATE_RESOURCE_LIMIT}'
        )

    parent_count = counts['CareerVpCrudDev(parent)']
    if parent_count >= PARENT_HEADROOM_TARGET:
        # Warn-only per spec: the <400 headroom target is NOT a failing gate
        # until the Job-1 resource-import decomposition lands.
        import warnings

        warnings.warn(
            f'parent template at {parent_count} resources (>= {PARENT_HEADROOM_TARGET} '
            'headroom target); Job-1 decomposition (blocked pending amendment) is '
            'needed before the additive waves P-09/P-14/P-17/P-21.',
            stacklevel=2,
        )


# --------------------------------------------------------------------------- #
# The stable custom-domain seam (the base-path FLIP linchpin).
# --------------------------------------------------------------------------- #
def test_custom_domain_is_regional_and_maps_to_rest_api() -> None:
    """DomainName is REGIONAL + TLS_1_2 + env-name; BasePathMapping → RestApi+stage.

    The custom domain is the stable frontend seam that makes a later base-path
    swap invisible to the Amplify build. (O-8 env-scoping to ``api.{env}`` is
    still hardcoded ``dev`` — tracked in the amendment; asserted here as the
    resolved dev value.)
    """
    template = _parent_template()

    domains = template.find_resources('AWS::ApiGateway::DomainName')
    assert len(domains) == 1, f'expected one custom DomainName, found {sorted(domains)}'
    domain_props = next(iter(domains.values()))['Properties']
    assert domain_props['DomainName'] == DEV_CUSTOM_DOMAIN
    assert domain_props['EndpointConfiguration']['Types'] == ['REGIONAL'], (
        'custom domain must be REGIONAL — an EDGE domain breaks the regional API-GW SNI/cert seam'
    )
    assert domain_props['SecurityPolicy'] == 'TLS_1_2'

    mappings = template.find_resources('AWS::ApiGateway::BasePathMapping')
    assert len(mappings) == 1, f'expected one BasePathMapping, found {sorted(mappings)}'
    mapping_props = next(iter(mappings.values()))['Properties']
    assert mapping_props['RestApiId']['Ref'] == DEV_REST_API_LOGICAL_ID, (
        'base-path mapping must point at the in-parent RestApi (still the OLD api until a human-only flip)'
    )
    assert 'Stage' in mapping_props, 'base-path mapping must bind a deployment stage'

    outputs = template.to_json().get('Outputs', {})
    assert 'ApiDevRegionalDomainName' in outputs, 'missing CfnOutput exposing the regional target domain for the Cloudflare CNAME'


# --------------------------------------------------------------------------- #
# Law 2 — the Cognito user pool is never touched (AC-P26-8).
# --------------------------------------------------------------------------- #
def test_cognito_user_pool_present_and_singular() -> None:
    """Exactly one Cognito UserPool exists in the parent (never moved/replaced)."""
    pools = _parent_template().find_resources('AWS::Cognito::UserPool')
    assert len(pools) == 1, (
        f'expected exactly one Cognito UserPool, found {len(pools)}: {sorted(pools)}; moving/replacing it is an unrecoverable loss of 908 accounts'
    )


# --------------------------------------------------------------------------- #
# Job 2 — the human-only base-path FLIP gate (P-28 replacement report).
# --------------------------------------------------------------------------- #
def _build_report(changeset: dict[str, Any]) -> tuple[dict[str, Any], bool]:
    if CI_SCRIPTS not in sys.path:
        sys.path.insert(0, CI_SCRIPTS)
    from changeset_replacement_report import (  # type: ignore[import-not-found]
        build_report,
    )

    return build_report(changeset)


def _change(logical_id: str, rtype: str, replacement: str, action: str = 'Modify') -> dict[str, Any]:
    return {
        'ResourceChange': {
            'LogicalResourceId': logical_id,
            'ResourceType': rtype,
            'Action': action,
            'Replacement': replacement,
        }
    }


@pytest.mark.parametrize(
    'rtype',
    [
        'AWS::ApiGateway::RestApi',
        'AWS::DynamoDB::Table',
        'AWS::S3::Bucket',
        'AWS::Cognito::UserPool',
    ],
)
def test_p28_report_auto_fails_on_protected_replacement(rtype: str) -> None:
    """A change set replacing any protected stateful type auto-fails the gate."""
    changeset = {'Changes': [_change('X', rtype, 'True')]}
    report, auto_fail = _build_report(changeset)
    assert auto_fail is True
    assert report['auto_fail'] is True


def test_p28_report_passes_on_basepath_only_flip() -> None:
    """The legitimate flip touches ONLY the BasePathMapping and passes the gate."""
    changeset = {
        'Changes': [
            _change(
                'ApiDevBasePathMapping',
                'AWS::ApiGateway::BasePathMapping',
                'False',
            )
        ]
    }
    report, auto_fail = _build_report(changeset)
    assert auto_fail is False
    assert report['auto_fail'] is False


# --------------------------------------------------------------------------- #
# The base-path FLIP and old-API RETIRE are human-only (never automation).
# --------------------------------------------------------------------------- #
def test_flip_and_retire_are_not_automation_executable() -> None:
    """No CI job runs ExecuteChangeSet without a human ``environment:`` gate.

    The base-path flip and the old-API retire both execute through the shared
    human-gated ``execute-change-set-*`` job. Any job that actually runs an
    ``execute-change-set`` (aws) or ``execute-changeset`` (make) command MUST
    carry an ``environment:`` approval gate; the create/describe jobs (read-only)
    must not.
    """
    import yaml

    workflow = REPO_ROOT / '.github' / 'workflows' / 'deploy.yml'
    doc = yaml.safe_load(workflow.read_text(encoding='utf-8'))
    jobs = doc.get('jobs') or {}
    assert jobs, 'deploy.yml has no jobs'

    executor_jobs: list[str] = []
    for job_id, job in jobs.items():
        runs = [step.get('run', '') for step in (job.get('steps') or []) if isinstance(step, dict) and step.get('run')]
        executes = any(('cloudformation execute-change-set' in r) or ('make execute-changeset' in r) for r in runs)
        if executes:
            executor_jobs.append(job_id)
            assert job.get('environment'), (
                f'job {job_id!r} runs ExecuteChangeSet but has no human environment: gate — the flip/retire would be automation-executable'
            )

    assert executor_jobs, 'expected at least one human-gated execute-change-set job in deploy.yml'
