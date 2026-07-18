"""RED-first tests for clause P-22 - OIDC in cdk-diff.yml.

Spec: docs/db-redesign/code/code-analysis/project/specs/P-22-oidc-cdk-diff-spec.md
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import yaml  # type: ignore[import-untyped]

REPO_ROOT = Path(__file__).resolve().parents[4]
CDK_DIFF_YML = REPO_ROOT / '.github' / 'workflows' / 'cdk-diff.yml'
AWS_CREDENTIALS_ACTION = 'aws-actions/configure-aws-credentials@v4'
LONG_LIVED_AWS_CREDENTIAL_TOKENS = (
    'AWS_ACCESS_KEY_ID',
    'AWS_SECRET_ACCESS_KEY',
    'aws-access-key-id',
    'aws-secret-access-key',
)


def _load_workflow() -> dict[str, Any]:
    return cast(dict[str, Any], yaml.safe_load(CDK_DIFF_YML.read_text(encoding='utf-8')))


def _workflow_steps() -> list[dict[str, Any]]:
    workflow = _load_workflow()
    jobs = cast(dict[str, Any], workflow.get('jobs', {}))
    cdk_diff_job = cast(dict[str, Any], jobs.get('cdk-diff', {}))
    return cast(list[dict[str, Any]], cdk_diff_job.get('steps', []))


def _aws_credentials_step() -> dict[str, Any]:
    for step in _workflow_steps():
        if step.get('uses') == AWS_CREDENTIALS_ACTION:
            return step
    raise AssertionError(f'P-22: cdk-diff.yml must use {AWS_CREDENTIALS_ACTION}')


def test_p22_cdk_diff_uses_oidc_role_assumption() -> None:
    step = _aws_credentials_step()
    with_config = cast(dict[str, Any], step.get('with', {}))

    assert with_config.get('role-to-assume'), 'P-22: cdk-diff.yml must assume an IAM role via GitHub OIDC'
    assert 'aws-access-key-id' not in with_config, 'P-22: long-lived access-key auth must be removed'
    assert 'aws-secret-access-key' not in with_config, 'P-22: long-lived secret-key auth must be removed'


def test_p22_cdk_diff_has_id_token_permission() -> None:
    workflow = _load_workflow()
    permissions = cast(dict[str, Any], workflow.get('permissions', {}))

    assert permissions.get('id-token') == 'write', 'P-22: GitHub OIDC requires permissions.id-token: write'


def test_p22_cdk_diff_workflow_has_no_long_lived_aws_secret_references() -> None:
    text = CDK_DIFF_YML.read_text(encoding='utf-8')

    for token in LONG_LIVED_AWS_CREDENTIAL_TOKENS:
        assert token not in text, f'P-22: cdk-diff.yml must not reference {token}'
