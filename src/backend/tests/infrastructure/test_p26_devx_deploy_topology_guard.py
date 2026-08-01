"""F-DEVX-7 topology guard — the ``devx`` build must re-home P-26 feature resources.

Defect: ``docs/evidence/wave3-32closeouta-devx-characterization-20260801T094608Z.md`` §5.7.
Scope-lock v2.6.0 requires ``CareerVpCrudDevx`` to be built with ``ENVIRONMENT=devx`` **and**
``-c p26_rehome_features=true`` from first creation.  ``p26_rehome_features`` is absent from
``infra/cdk.json``, and ``cdk`` runs from ``src/backend``, which has no ``cdk.json`` at all, so
the flag can only reach the app from the ``deploy-devx`` recipe itself.  When it does not, the
76 P-26 feature resources synthesize into the **parent** template with fresh logical ids and
CloudFormation aborts early-validation with 27 ``AWS::Logs::LogGroup`` "already exists" errors
plus ``careervp-api-canary-application-devx`` — because the nested stack already owns those
physical names.  Measured 2026-08-01: without the flag 490 parent resources / 32 parent log
groups / 0 nested; with it 260 / 2 / 30, matching 259 of the 261 deployed parent logical ids.

**This test never deploys and never calls AWS.**  It expands the recipe with ``make -n`` (no
side effects), feeds the ``--context`` pairs it finds into a local synth, and asserts on the
resulting **template topology** — not on the text of the command.  That is the ordering that
matters: a guard that grepped the Makefile for the flag would pass while the topology it is
supposed to protect was broken by any other route (a ``cdk.json`` default removed, the flag
renamed in ``api_construct.py``, ``CrudFeatures`` losing a resource).  Asserting placement
catches those; asserting the string does not.

The Makefile is the *input source* rather than a second assertion target, which is also what
makes the guard able to fail: drop ``--context p26_rehome_features=true`` from ``deploy-devx``
and the synth this test performs is the broken one, so the collision names appear in the parent
and every assertion below goes red.
"""

from __future__ import annotations

import os
import re
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
from aws_cdk import App, Environment, NestedStack
from aws_cdk.assertions import Template

BACKEND_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = BACKEND_ROOT.parents[1]
INFRA_SRC = str(REPO_ROOT / 'infra')

DEVX_ENVIRONMENT = 'devx'
DEVX_STACK_ID = 'CareerVpCrudDevx'
CRUD_FEATURES_CONSTRUCT_ID = 'CrudFeatures'

# The physical names CloudFormation refused to create twice (§5.7).  Every ``/aws/lambda/`` log
# group in the devx synth is a P-26 feature log group; the parent's only two log groups are the
# API Gateway access log and the WAF log, neither of which is re-homed.
FEATURE_LOG_GROUP_PREFIX = '/aws/lambda/careervp-'
MIN_REHOMED_LOG_GROUPS = 27
CODEDEPLOY_TYPE = 'AWS::CodeDeploy::Application'
LOG_GROUP_TYPE = 'AWS::Logs::LogGroup'


def _deploy_devx_context() -> dict[str, str]:
    """Return the ``--context`` pairs the ``deploy-devx`` recipe actually passes to ``cdk``.

    ``make -n`` expands variables without running anything, so this reads the real recipe
    (including ``$(DEVX_STACK_NAME)`` and ``$(_CDK_ALLOWED_ORIGINS)`` indirection) rather than a
    hand-copied duplicate of it that could drift.
    """
    completed = subprocess.run(
        ['make', '-n', 'deploy-devx'],
        cwd=BACKEND_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        pytest.fail(f'`make -n deploy-devx` failed ({completed.returncode}):\n{completed.stderr}')

    deploy_lines = [line for line in completed.stdout.splitlines() if re.search(r'\bcdk\s+deploy\b', line)]
    assert len(deploy_lines) == 1, f'expected exactly one `cdk deploy` line in the deploy-devx recipe, got {len(deploy_lines)}: {deploy_lines}'

    tokens = shlex.split(deploy_lines[0])
    context: dict[str, str] = {}
    for index, token in enumerate(tokens):
        if token in ('--context', '-c') and index + 1 < len(tokens):
            key, _, value = tokens[index + 1].partition('=')
            context[key] = value
    return context


def _synthesize_devx(context: dict[str, str]) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    """Synthesize the devx service stack locally; return ``(parent_resources, crud_features_resources)``.

    Mirrors ``infra/app.py``'s construction for ``ENVIRONMENT=devx`` — the stack id comes from
    ``NamingUtils`` exactly as it does there — but stays in-process: no ``cdk`` CLI, no bootstrap
    lookup, no credentials, no deploy.
    """
    if INFRA_SRC not in sys.path:
        sys.path.insert(0, INFRA_SRC)

    from careervp.naming_utils import NamingUtils  # type: ignore[import-not-found]
    from careervp.service_stack import ServiceStack  # type: ignore[import-not-found]

    account_id = '123456789012'
    region = 'us-east-1'
    app = App(context=dict(context))
    naming = NamingUtils(environment=DEVX_ENVIRONMENT, region=region, account_id=account_id)
    stack = ServiceStack(
        scope=app,
        id=naming.stack_id('crud'),
        env=Environment(account=account_id, region=region),
        is_production_env=False,
        naming=naming,
        stack_feature='crud',
    )
    assert stack.stack_name == DEVX_STACK_ID, f'devx synth built {stack.stack_name!r}, not {DEVX_STACK_ID!r}'

    crud_features = [
        construct for construct in stack.node.find_all() if isinstance(construct, NestedStack) and construct.node.id == CRUD_FEATURES_CONSTRUCT_ID
    ]
    assert len(crud_features) == 1, f'expected exactly one {CRUD_FEATURES_CONSTRUCT_ID} nested stack, found {len(crud_features)}'

    parent = Template.from_stack(stack).to_json().get('Resources', {})
    nested = Template.from_stack(crud_features[0]).to_json().get('Resources', {})
    return parent, nested


def _feature_log_group_names(resources: dict[str, dict[str, Any]]) -> set[str]:
    return {
        properties['LogGroupName']
        for properties in (resource.get('Properties', {}) for resource in resources.values())
        if isinstance(properties.get('LogGroupName'), str) and properties['LogGroupName'].startswith(FEATURE_LOG_GROUP_PREFIX)
    }


@pytest.fixture(scope='module')
def devx_templates() -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    return _synthesize_devx(_deploy_devx_context())


def test_devx_recipe_synthesizes_feature_log_groups_into_crud_features(
    devx_templates: tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]],
) -> None:
    """The nested stack owns the feature log groups — as the deployed devx stack does."""
    _parent, nested = devx_templates
    nested_names = _feature_log_group_names(nested)
    assert len(nested_names) >= MIN_REHOMED_LOG_GROUPS, (
        f'{CRUD_FEATURES_CONSTRUCT_ID} holds only {len(nested_names)} {FEATURE_LOG_GROUP_PREFIX}* log groups '
        f'(expected at least {MIN_REHOMED_LOG_GROUPS}); the devx build is not re-homing P-26 features. '
        f'See evidence §5.7.'
    )


def test_devx_recipe_leaves_no_feature_log_groups_in_the_parent(
    devx_templates: tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]],
) -> None:
    """The parent must not re-declare names the nested stack already owns.

    This is the assertion that maps onto the CloudFormation failure: each name here is one
    "resource ... already exists" early-validation error on the next ``make deploy-devx``.
    """
    parent, _nested = devx_templates
    collisions = _feature_log_group_names(parent)
    assert collisions == set(), (
        f'{len(collisions)} P-26 feature log group(s) synthesized into the {DEVX_STACK_ID} parent template; '
        f'each one is an "already exists" error on deploy. Offenders: {sorted(collisions)[:5]}'
    )
    parent_log_groups = {logical_id for logical_id, resource in parent.items() if resource.get('Type') == LOG_GROUP_TYPE}
    assert len(parent_log_groups) <= 2, (
        f'the devx parent should hold only the API Gateway access log and the WAF log group, '
        f'found {len(parent_log_groups)}: {sorted(parent_log_groups)}'
    )


def test_devx_recipe_places_the_p23_canary_application_in_crud_features(
    devx_templates: tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]],
) -> None:
    """``careervp-api-canary-application-devx`` was the 28th collision in §5.7."""
    parent, nested = devx_templates
    parent_apps = [logical_id for logical_id, resource in parent.items() if resource.get('Type') == CODEDEPLOY_TYPE]
    nested_apps = [logical_id for logical_id, resource in nested.items() if resource.get('Type') == CODEDEPLOY_TYPE]
    assert parent_apps == [], f'{CODEDEPLOY_TYPE} must not be in the devx parent template: {parent_apps}'
    assert len(nested_apps) == 1, f'expected the P-23 canary application in {CRUD_FEATURES_CONSTRUCT_ID}, found {nested_apps}'


def test_devx_recipe_carries_the_rehome_flag_from_no_cdk_json_default(
    devx_templates: tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]],
) -> None:
    """Pin *why* the recipe must carry the flag: nothing else supplies it.

    Not a substitute for the topology assertions above — a placement check cannot tell a reader
    that ``src/backend`` has no ``cdk.json`` and ``infra/cdk.json`` sets no default, which is the
    whole reason the recipe is the only place the flag can live.  If a later step adds the
    default to ``infra/cdk.json``, this fails and the comment above it gets rewritten rather than
    the fact being lost.
    """
    assert not (BACKEND_ROOT / 'cdk.json').exists(), 'src/backend/cdk.json now exists — re-derive where devx context comes from'
    infra_cdk_json = REPO_ROOT / 'infra' / 'cdk.json'
    assert infra_cdk_json.exists(), f'missing {infra_cdk_json}'
    assert 'p26_rehome_features' not in infra_cdk_json.read_text(encoding='utf-8'), (
        'infra/cdk.json now sets p26_rehome_features; the deploy-devx recipe is no longer the sole source '
        'and this guard needs re-deriving (infra/ is 3.4-owned — raise it, do not adjust it here)'
    )
    assert os.environ.get('CAREERVP_SCRATCH_MODE') is None, 'scratch mode alters app construction; run this guard outside scratch mode'
