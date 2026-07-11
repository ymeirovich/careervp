"""RED-first tests for clause P-27 — CFN stack policy document.

Spec: docs/db-redesign/code/code-analysis/project/specs/P-27-cfn-stack-policy-spec.md

Asserts infra/cfn_stack_policy.json denies Update:Replace/Update:Delete on the stateful
resource types (RestApi, all DynamoDB Tables, all S3 Buckets, Cognito UserPool, nested CFN
stacks) using the AUTHORITATIVE CloudFormation stack-policy form
(Resource:"*" + Condition.StringEquals/StringLike on ResourceType) with a catch-all
Allow Update:* so non-stateful resources stay updatable. The `LogicalResourceId/<type>`
form the draft spec floated is invalid CFN and must NOT appear.

(Termination-protection on the CDK stacks is asserted in
infra/tests/infrastructure/test_p27_stack_policy.py, which runs in the infra venv.)
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

# src/backend/tests/infra/ -> repo root
REPO_ROOT = Path(__file__).resolve().parents[4]
STACK_POLICY_PATH = REPO_ROOT / 'infra' / 'cfn_stack_policy.json'

PROTECTED_ACTIONS = {'Update:Replace', 'Update:Delete'}
PROTECTED_TYPES = [
    'AWS::ApiGateway::RestApi',
    'AWS::DynamoDB::Table',
    'AWS::S3::Bucket',
    'AWS::Cognito::UserPool',
    'AWS::CloudFormation::Stack',
]


def _load_policy() -> dict:
    assert STACK_POLICY_PATH.exists(), f'P-27: stack policy document missing at {STACK_POLICY_PATH}'
    return json.loads(STACK_POLICY_PATH.read_text(encoding='utf-8'))


def _actions(stmt: dict) -> set[str]:
    action = stmt.get('Action', [])
    return {action} if isinstance(action, str) else set(action)


def _resource_types(stmt: dict) -> set[str]:
    cond = stmt.get('Condition', {})
    types: set[str] = set()
    for op in ('StringEquals', 'StringLike'):
        rt = cond.get(op, {}).get('ResourceType')
        if rt is None:
            continue
        types |= {rt} if isinstance(rt, str) else set(rt)
    return types


def _deny_statements_for_type(policy: dict, resource_type: str) -> list[dict]:
    matches: list[dict] = []
    for stmt in policy.get('Statement', []):
        if stmt.get('Effect') != 'Deny':
            continue
        for rt in _resource_types(stmt):
            if rt == resource_type or (rt.endswith('*') and resource_type.startswith(rt[:-1])):
                matches.append(stmt)
                break
    return matches


def test_stack_policy_denies_replace_on_rest_api() -> None:
    policy = _load_policy()
    denies = _deny_statements_for_type(policy, 'AWS::ApiGateway::RestApi')
    assert denies, 'P-27: no Deny statement targets AWS::ApiGateway::RestApi'
    assert any('Update:Replace' in _actions(s) for s in denies), 'P-27: RestApi Deny does not cover Update:Replace'


def test_stack_policy_denies_delete_on_dynamo() -> None:
    policy = _load_policy()
    denies = _deny_statements_for_type(policy, 'AWS::DynamoDB::Table')
    assert denies, 'P-27: no Deny statement targets AWS::DynamoDB::Table by resource type'
    assert any(PROTECTED_ACTIONS <= _actions(s) for s in denies), 'P-27: DynamoDB Table Deny must cover BOTH Update:Replace AND Update:Delete'


def test_stack_policy_blocks_s3_bucket_delete() -> None:
    policy = _load_policy()
    denies = _deny_statements_for_type(policy, 'AWS::S3::Bucket')
    assert denies, 'P-27: no Deny statement targets AWS::S3::Bucket by resource type'
    assert any('Update:Delete' in _actions(s) for s in denies), 'P-27: S3 Bucket Deny does not cover Update:Delete'


def test_stack_policy_blocks_cognito_pool_delete() -> None:
    policy = _load_policy()
    denies = _deny_statements_for_type(policy, 'AWS::Cognito::UserPool')
    assert denies, 'P-27: no Deny statement targets AWS::Cognito::UserPool by resource type'
    assert any('Update:Delete' in _actions(s) for s in denies), 'P-27: Cognito UserPool Deny does not cover Update:Delete (908 live accounts)'


def test_stack_policy_blocks_nested_cfn_stack() -> None:
    policy = _load_policy()
    denies = _deny_statements_for_type(policy, 'AWS::CloudFormation::Stack')
    assert denies, 'P-27: no Deny statement targets AWS::CloudFormation::Stack (nested)'
    assert any(PROTECTED_ACTIONS <= _actions(s) for s in denies), 'P-27: nested CFN Stack Deny must cover Update:Replace AND Update:Delete'


def test_stack_policy_has_catch_all_allow() -> None:
    """AC-P27-4: non-stateful resources stay updatable via the catch-all Allow."""
    policy = _load_policy()
    allows = [s for s in policy.get('Statement', []) if s.get('Effect') == 'Allow']
    assert any(s.get('Resource') == '*' and 'Update:*' in _actions(s) for s in allows), 'P-27: missing catch-all `Allow Update:* on *`'


def test_stack_policy_uses_authoritative_condition_form() -> None:
    """The invalid `LogicalResourceId/AWS::<Type>` form must NOT be used."""
    raw = STACK_POLICY_PATH.read_text(encoding='utf-8')
    assert 'LogicalResourceId/AWS::' not in raw, (
        'P-27: uses the invalid LogicalResourceId/<type> form; protect-by-type must use Condition.ResourceType'
    )


def test_stack_policy_is_valid_cfn_shape() -> None:
    """SetStackPolicy accepts only a top-level Statement list — no stray comment keys."""
    policy = _load_policy()
    assert set(policy.keys()) == {'Statement'}, (
        'P-27: cfn_stack_policy.json must contain ONLY the Statement key so '
        'SetStackPolicy accepts it verbatim (runbook lives in the README, not the JSON)'
    )
    for stmt in policy['Statement']:
        assert stmt.get('Principal') == '*', "P-27: Principal must be '*'"


@pytest.mark.parametrize('resource_type', PROTECTED_TYPES)
def test_every_protected_type_denies_both_actions(resource_type: str) -> None:
    policy = _load_policy()
    denies = _deny_statements_for_type(policy, resource_type)
    assert any(PROTECTED_ACTIONS <= _actions(s) for s in denies), (
        f'P-27: {resource_type} must have a Deny covering both Update:Replace and Update:Delete'
    )


def test_human_apply_runbook_present() -> None:
    """The HUMAN-APPLIED SetStackPolicy runbook + P-26 lift/reinstate cross-ref exists."""
    readme = REPO_ROOT / 'infra' / 'cfn_stack_policy.README.md'
    assert readme.exists(), 'P-27: infra/cfn_stack_policy.README.md runbook missing'
    text = readme.read_text(encoding='utf-8')
    assert 'HUMAN-APPLIED' in text, 'P-27: runbook must be marked HUMAN-APPLIED'
    assert 'set-stack-policy' in text, 'P-27: runbook must show the set-stack-policy command'
    assert 'P-26' in text, 'P-27: runbook must cross-reference the P-26 temporary-lift procedure'
