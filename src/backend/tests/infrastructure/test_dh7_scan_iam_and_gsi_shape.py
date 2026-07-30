"""D-H7 synth contracts — AC-DH7-1 (IAM half) and AC-DH7-2 (GSI shape).

Spec: ``docs/db-redesign/code/code-analysis/project/specs/D-H7-request-path-scans-spec.md``
(pinned 2026-07-29 by step 3.3-SPEC).  Bet ``B-3-8`` settled **FALSE** — no request-path Scan
is 3.3's own to remove — so D-H7/3.3 is a guard-rail step.  ``test_dh7_no_status_only_gsi_partition_key``
is a day-one GUARD; ``test_dh7_no_scan_in_runtime_handlers_or_dal`` (Part B) is the **single
assertion in all of 3.3 that is RED before the fix and GREEN after**.

This module holds the two halves of D-H7 that need a CDK synth.  Part A of
``test_dh7_no_scan_in_runtime_handlers_or_dal`` — the static AST source guard — lives in
``tests/unit/test_dh7_request_path_scans.py`` under the *same test name*.  Both halves belong
to AC-DH7-1 per DP-2 (source **and** the one explicit ``dynamodb:Scan`` grant); Part B is not
a fourth D-H7 test and carries no identity of its own.  Selecting the D-H7 suite therefore
requires **both** pytest roots::

    uv run pytest tests/unit tests/infrastructure -q -k "dh7"

``pytest tests/unit -k dh7`` alone is a false green — it silently skips everything here.

Template collection reuses the ``test_p15_billing_iam.py`` precedent (parent stack plus every
nested stack, unioned), which the spec endorses as the right *pattern* for finding a role
across parent and nested templates.  Only that test's action-set **breadth** is wrong for
D-H7 — see the ⛔ note on ``_artifacts_table_statements``.

OUT OF SCOPE for 3.3, so 3.3-GREEN inherits the boundary explicitly:

* The **22** implicit ``grant_read_data`` / ``grant_read_write_data`` calls in
  ``api_construct.py``, which include ``dynamodb:Scan`` implicitly and reach the shared role's
  attached ``...DefaultPolicy...``.  They are **3.4's**, per DP-2.  Nothing here asserts on
  them, and nothing here may require them narrowed.
* ``dal/dynamo_dal_handler.py:800`` (3.5), ``dal/subscription_repository.py:415`` (retained by
  Wave-2 ``2.1-GREEN``), ``scripts/cr_migration_backfill.py:261`` (offline, deleted at 3.5).
* The knowledge table's ``entity-index`` partition-key shape — **D-M5** (3.4) and **Q-07**
  (Wave 4).
* The three residues ``3.1-GREEN`` recorded and everything ``3.2-GREEN`` listed with a named
  owner; auth / trial / user-pool keying (Wave-6 D-H8); the D-M god-class split (3.4).

Scope-lock D-H7 is ``verification: integration``.  A passing synth suite does **not** discharge
the clause — 3.3-GREEN inherits Wave-3's undeployed debt against ``CareerVpCrudDevx`` and must
record it rather than claim closure (Evidence E-8).
"""

from __future__ import annotations

import json
import os
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any

os.environ.setdefault('JSII_RUNTIME_PACKAGE_CACHE', '/tmp/jsii-cache')

from aws_cdk import App, Environment, NestedStack
from aws_cdk.assertions import Template

REPO_ROOT = Path(__file__).resolve().parents[4]
INFRA_SRC = str(REPO_ROOT / 'infra')

_SCAN_ACTION = 'dynamodb:Scan'
_ARTIFACTS_POLICY_NAME = 'artifacts_table'

# The surviving action list after 3.3-GREEN removes ``api_construct.py:941``.  Order included,
# so neither a re-added Scan nor a silently-widened action list passes.
_EXPECTED_ARTIFACTS_ACTIONS: list[str] = [
    'dynamodb:PutItem',
    'dynamodb:GetItem',
    'dynamodb:UpdateItem',
    'dynamodb:DeleteItem',
    'dynamodb:Query',
]

# Tables are ``dynamodb.TableV2``, which synthesizes to ``AWS::DynamoDB::GlobalTable``.
# ``AWS::DynamoDB::Table`` has a live count of **0**, so an assertion written against it finds
# no resources and passes vacuously (Evidence E-4).  Precedent for the correct type:
# ``infra/tests/infrastructure/test_p12_p13_retain_stateful.py:19-21``.
_GLOBAL_TABLE_TYPE = 'AWS::DynamoDB::GlobalTable'
_LEGACY_TABLE_TYPE = 'AWS::DynamoDB::Table'
_EXPECTED_GLOBAL_TABLE_COUNT = 11

# The frozen 8-entry GSI baseline, verified against the synthesized template on 2026-07-30.
# A **set of (IndexName, KeySchema) pairs**, never a name-keyed dict: entries 2 and 5 share the
# name ``user_id-index`` on *different* tables (users and jobs) with *different* key schemas,
# and a dict would silently collapse them and lose one.
#
# ``entity-index`` is a NAMED, OWNED EXCEPTION recorded here rather than hidden.  Its partition
# key ``knowledgeType`` is neither user-scoped nor obviously high-cardinality.  It is not 3.3's:
# AC-DH7-2 is scoped to *"new indexes for replacements"* and this index is pre-existing; it has
# zero live callers in ``careervp/``; and the knowledge table's key shape is already owned by
# **D-M5** (3.4) and **Q-07** (Wave 4).
_GSI_BASELINE: set[tuple[str, tuple[tuple[str, str], ...]]] = {
    ('email-index', (('email', 'HASH'),)),
    ('user_id-index', (('user_id', 'HASH'), ('sk', 'RANGE'))),
    ('customer-id-index', (('customer_id', 'HASH'),)),
    ('idempotency-key-index', (('idempotency_key', 'HASH'),)),
    ('user_id-index', (('user_id', 'HASH'),)),
    ('status-index', (('userId', 'HASH'), ('status', 'RANGE'))),
    ('entity-index', (('knowledgeType', 'HASH'), ('entityId', 'RANGE'))),
    ('type-index', (('applicationId', 'HASH'), ('artifactType', 'RANGE'))),
}


def _build_stack() -> Any:
    if INFRA_SRC not in sys.path:
        sys.path.insert(0, INFRA_SRC)

    from careervp.naming_utils import NamingUtils  # type: ignore[import-not-found]
    from careervp.service_stack import ServiceStack  # type: ignore[import-not-found]

    # ``p26_rehome_features`` matches the topology the spec pinned against: with the flag on,
    # P-26 Job 1 re-homes the shared Lambda role into ``CrudFeaturesNestedStack``, which is why
    # an IAM assertion against the parent template alone passes vacuously (Evidence E-4).
    app = App(context={'p26_rehome_features': 'true'})
    naming = NamingUtils(environment='dev', region='us-east-1', account_id='123456789012')
    return ServiceStack(
        scope=app,
        id=naming.stack_id('crud'),
        env=Environment(account='123456789012', region='us-east-1'),
        is_production_env=False,
        naming=naming,
        stack_feature='crud',
    )


def _parent_and_all_resources() -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    """Return ``(parent_resources, parent_plus_every_nested_stack_resources)``.

    The union is the ``test_p15_billing_iam.py`` collection technique.  It is used for the IAM
    assertion because the shared Lambda role's home is topology-dependent: with
    ``p26_rehome_features`` on it sits in ``CrudFeaturesNestedStack``, with the flag off it sits
    in the parent.  Collecting both makes the assertion non-vacuous either way, and the test
    additionally asserts the policy was found at all.
    """
    stack = _build_stack()
    parent = Template.from_stack(stack).to_json().get('Resources', {})
    nested: dict[str, dict[str, Any]] = {}
    for construct in stack.node.find_all():
        if isinstance(construct, NestedStack):
            nested.update(Template.from_stack(construct).to_json().get('Resources', {}))
    return parent, {**parent, **nested}


def _artifacts_table_statements(resources: Mapping[str, Mapping[str, Any]]) -> list[tuple[str, dict[str, Any]]]:
    """Return ``(role_logical_id, statement)`` for the inline ``artifacts_table`` policy only.

    ⛔ **SCOPED TO THE INLINE STATEMENT ON PURPOSE.  It must never be unioned with the role's
    attached ``...DefaultPolicy...``.**  The obvious thing to copy is
    ``test_p15_billing_iam.py``'s ``_role_policy_actions`` helper, which deliberately unions a
    role's inline ``Policies`` with every standalone ``AWS::IAM::Policy`` referencing that role.
    For this shared role that union contains ``dynamodb:Scan`` from a **second, independent
    source** — the 22 implicit ``grant_read_data`` / ``grant_read_write_data`` calls that are
    **3.4's** (Evidence E-3 F-2).  Verified live 2026-07-30 under the rehome topology: inline
    has Scan True, attached ``ServiceRoleArnDefaultPolicy2B096FD3`` has Scan True, union has
    Scan True.  A union-style assertion therefore stays RED after 3.3 removes
    ``api_construct.py:941``, and 3.3-GREEN may not edit this test — the step would dead-end in
    a §0.3 amendment.  The P-15 precedent is the right *pattern* for finding a role across
    parent and nested templates, and the wrong *breadth* for this assertion.

    The attached default policy's ``dynamodb:Scan`` is asserted **nowhere** in this module,
    deliberately: it is 3.4's residue, and a hard "Scan is still present there" companion
    assertion — which the spec permits but does not require — would invert into a landmine that
    3.4 could only clear by editing a D-H7 test.  It is recorded here instead, so the 22-grant
    surface is proven-and-owned rather than silently assumed, and so no future reader mistakes
    this test for full IAM closure.

    Takes its input as a parameter so the assertion is provable against a hand-built template
    without touching any implementation file.
    """
    matched: list[tuple[str, dict[str, Any]]] = []
    for logical_id, resource in resources.items():
        if resource.get('Type') != 'AWS::IAM::Role':
            continue
        for policy in resource.get('Properties', {}).get('Policies', []) or []:
            if policy.get('PolicyName') != _ARTIFACTS_POLICY_NAME:
                continue
            for statement in policy.get('PolicyDocument', {}).get('Statement', []) or []:
                matched.append((logical_id, statement))
    return matched


def assert_no_artifacts_table_scan_grant(resources: Mapping[str, Mapping[str, Any]]) -> None:
    """AC-DH7-1 (IAM half): the inline ``artifacts_table`` policy must not permit Scan."""
    matched = _artifacts_table_statements(resources)
    assert matched, f'AC-DH7-1: inline policy {_ARTIFACTS_POLICY_NAME!r} not found; assertion would pass vacuously'

    for role_logical_id, statement in matched:
        actions = statement.get('Action', [])
        actions = [actions] if isinstance(actions, str) else list(actions)
        assert _SCAN_ACTION not in actions, (
            f'AC-DH7-1: role {role_logical_id} inline policy {_ARTIFACTS_POLICY_NAME!r} still permits {_SCAN_ACTION}: {actions}. '
            'No source path scans the artifacts table, so this grant is wider than any caller needs; '
            'remove the literal "dynamodb:Scan" at infra/careervp/api_construct.py:941.'
        )
        assert actions == _EXPECTED_ARTIFACTS_ACTIONS, (
            f'AC-DH7-1: role {role_logical_id} inline policy {_ARTIFACTS_POLICY_NAME!r} action list must be exactly '
            f'{_EXPECTED_ARTIFACTS_ACTIONS} (order included), got {actions}'
        )

        # Resources unchanged, so the fix narrows actions without quietly narrowing scope: the
        # statement still covers the artifacts table ARN *and* its ``type-index``.
        statement_resources = statement.get('Resource', [])
        statement_resources = [statement_resources] if isinstance(statement_resources, (str, dict)) else list(statement_resources)
        assert len(statement_resources) == 2, (
            f'AC-DH7-1: {_ARTIFACTS_POLICY_NAME!r} must still cover exactly the table ARN and its type-index, got {statement_resources}'
        )
        rendered = [json.dumps(entry, sort_keys=True) for entry in statement_resources]
        assert 'ArtifactsTable' in rendered[0], (
            f'AC-DH7-1: {_ARTIFACTS_POLICY_NAME!r} first resource must remain the artifacts table ARN, got {rendered[0]}'
        )
        assert '/index/type-index' in rendered[1], (
            f'AC-DH7-1: {_ARTIFACTS_POLICY_NAME!r} second resource must remain the type-index ARN, got {rendered[1]}'
        )


def gsi_pairs(resources: Mapping[str, Mapping[str, Any]]) -> set[tuple[str, tuple[tuple[str, str], ...]]]:
    """Collect ``(IndexName, KeySchema)`` for every GSI on every GlobalTable in ``resources``."""
    pairs: set[tuple[str, tuple[tuple[str, str], ...]]] = set()
    for resource in resources.values():
        if resource.get('Type') != _GLOBAL_TABLE_TYPE:
            continue
        for gsi in resource.get('Properties', {}).get('GlobalSecondaryIndexes', []) or []:
            key_schema = tuple((str(key['AttributeName']), str(key['KeyType'])) for key in gsi.get('KeySchema', []))
            pairs.add((str(gsi.get('IndexName')), key_schema))
    return pairs


def assert_no_status_partition_key(resources: Mapping[str, Mapping[str, Any]]) -> None:
    """AC-DH7-2 (a): no GSI partition key is ``status`` or ``status#``-prefixed.

    Takes its input as a parameter so the assertion is provable against a hand-built template
    without touching any implementation file.
    """
    offenders: list[str] = []
    for logical_id, resource in resources.items():
        if resource.get('Type') != _GLOBAL_TABLE_TYPE:
            continue
        for gsi in resource.get('Properties', {}).get('GlobalSecondaryIndexes', []) or []:
            for key in gsi.get('KeySchema', []):
                if key.get('KeyType') != 'HASH':
                    continue
                attribute = str(key.get('AttributeName', '')).lower()
                if attribute == 'status' or attribute.startswith('status#'):
                    offenders.append(f'{logical_id}::{gsi.get("IndexName")} HASH={key.get("AttributeName")!r}')
    assert not offenders, (
        f'AC-DH7-2: low-cardinality status partition key(s) on GSI(s): {offenders}. '
        'A GSI partition key must be user-scoped, high-cardinality or sparse — never the status enum.'
    )


def assert_frozen_gsi_baseline(resources: Mapping[str, Mapping[str, Any]]) -> None:
    """AC-DH7-2 (b): the ``(IndexName, KeySchema)`` set equals the frozen 8-entry baseline.

    Set equality, not containment, so an **added** GSI fails and a **removed** GSI also fails —
    a removal is a deliberate schema decision that must be re-recorded, not absorbed.

    Takes its input as a parameter so the assertion is provable against a hand-built template
    without touching any implementation file.
    """
    found = gsi_pairs(resources)
    added = sorted(found - _GSI_BASELINE)
    removed = sorted(_GSI_BASELINE - found)
    assert found == _GSI_BASELINE, (
        f'AC-DH7-2: GSI baseline drift — added {added}, removed {removed}. '
        'A new GSI needs a recorded partition-key shape decision before this baseline is updated.'
    )


def test_dh7_no_scan_in_runtime_handlers_or_dal() -> None:
    """AC-DH7-1 (Part B): the artifacts-table Lambda role must not be granted dynamodb:Scan.

    **NOT A GUARD.  This is the one assertion in 3.3 that is RED before the fix and GREEN
    after** — the single behaviour-adjacent change in the step.  ``dynamodb:Scan`` is live in
    the inline ``artifacts_table`` policy (``infra/careervp/api_construct.py:932-950``, literal
    at ``:941``) and 3.3-GREEN removes it.  It sits under AC-DH7-1 because DP-2 resolved that
    AC to mean source **and** this one grant.  No source path scans the artifacts table
    (Evidence E-1 records zero artifacts-table scans), so the grant is demonstrably wider than
    any caller needs, and no test covered it before this one.

    Part A of this test — the static AST source guard over ``careervp/{handlers,dal,logic}`` —
    is in ``tests/unit/test_dh7_request_path_scans.py`` under this same name.

    The role is matched by the presence of inline ``PolicyName == 'artifacts_table'``, never by
    logical id: the live id is ``CareerVpCrudDevCrudServiceRoleArn305AAC1B``, whose
    ``CareerVpCrudDev`` prefix is environment-derived and whose ``305AAC1B`` suffix is a CDK
    hash, so hard-coding it would fail under the ``devx`` target for the wrong reason.

    3.3-GREEN owes the ``B-3-4`` proof alongside the fix: isolated template diff, HEAD vs
    change-stashed, zero replacement markers on stateful resources, with the only expected
    difference being the removal of that single ``Action`` element.
    """
    _parent, all_resources = _parent_and_all_resources()
    assert all_resources, 'AC-DH7-1: template collection returned zero resources; assertions would pass vacuously'
    assert_no_artifacts_table_scan_grant(all_resources)


def test_dh7_no_status_only_gsi_partition_key() -> None:
    """AC-DH7-2: no GSI is partitioned on status, and the 8-GSI baseline is frozen.

    **GUARD — frozen-enumeration regression guard, ALREADY SATISFIED, green on day one.**
    Reason: ``status-index`` is a red herring — its partition key is ``userId`` and ``status``
    sits in the **sort** position (``infra/careervp/api_db_construct.py:384-393``).  Nothing is
    fixed here; the point is that a future GSI cannot slip past.

    A broader assertion — "every GSI partition key is user-scoped, high-cardinality or sparse" —
    was **considered and deliberately REJECTED** at 3.3-SPEC.  ``entity-index`` is partitioned on
    ``knowledgeType``, a type enum, so that assertion would FAIL on day one and could only be
    made green by reshaping the knowledge table, which belongs to **D-M5** (3.4) and **Q-07**
    (Wave 4).  Writing it here would be scope drift, not rigour.  ``entity-index`` is instead a
    named, owned exception recorded IN the frozen baseline — enumerated, never hidden.

    The two pinned assertions, in order: (a) no GSI's partition key is ``status`` or
    ``status#``-prefixed — the prohibition the clause actually states; (b) set equality against
    the frozen 8-entry ``(IndexName, KeySchema)`` baseline, so a newly added GSI fails rather
    than slipping past.

    The resource set is asserted non-empty first: tables are ``TableV2`` and synthesize as
    ``AWS::DynamoDB::GlobalTable``, so an assertion written against ``AWS::DynamoDB::Table``
    finds 0 resources and passes vacuously (Evidence E-4).
    """
    parent, _all_resources = _parent_and_all_resources()

    global_tables = {logical_id: resource for logical_id, resource in parent.items() if resource.get('Type') == _GLOBAL_TABLE_TYPE}
    assert global_tables, f'AC-DH7-2: zero {_GLOBAL_TABLE_TYPE} resources found; every assertion below would pass vacuously'
    assert len(global_tables) == _EXPECTED_GLOBAL_TABLE_COUNT, (
        f'AC-DH7-2 expected {_EXPECTED_GLOBAL_TABLE_COUNT} {_GLOBAL_TABLE_TYPE} resources, found {len(global_tables)}'
    )
    legacy_tables = [logical_id for logical_id, resource in parent.items() if resource.get('Type') == _LEGACY_TABLE_TYPE]
    assert not legacy_tables, (
        f'AC-DH7-2: tables are TableV2/{_GLOBAL_TABLE_TYPE}; unexpected {_LEGACY_TABLE_TYPE} resources would split this assertion: {legacy_tables}'
    )

    assert_no_status_partition_key(parent)
    assert_frozen_gsi_baseline(parent)
