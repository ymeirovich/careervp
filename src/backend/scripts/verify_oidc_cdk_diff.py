"""Verify the P-22 GitHub OIDC role for cdk-diff.yml is actually usable.

Complements tests/infra/test_p22_oidc_cdk_diff.py (which only checks the
workflow YAML's shape). This checks the AWS-side role/trust-policy that the
workflow depends on at runtime, and — best-effort — that the GitHub secret it
reads exists. It cannot fully simulate a live GitHub Actions OIDC token
locally, so it validates every precondition that would make that assumption
succeed or fail, rather than performing the assumption itself.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from typing import Any, Final

import boto3
from botocore.exceptions import BotoCoreError, ClientError

GITHUB_REPO: Final[str] = 'ymeirovich/careervp'
OIDC_PROVIDER_URL: Final[str] = 'token.actions.githubusercontent.com'
EXPECTED_AUDIENCE: Final[str] = 'sts.amazonaws.com'
EXPECTED_SUBJECT: Final[str] = f'repo:{GITHUB_REPO}:pull_request'
GITHUB_SECRET_NAME: Final[str] = 'AWS_CDK_DIFF_ROLE_ARN'
FORBIDDEN_ACTIONS: Final[tuple[str, ...]] = (
    'cloudformation:CreateChangeSet',
    'cloudformation:ExecuteChangeSet',
    'cloudformation:DeleteStack',
    'cloudformation:UpdateStack',
    'cloudformation:CreateStack',
)


def _account_id(sts_client: Any) -> str:
    identity: str = sts_client.get_caller_identity()['Account']
    return identity


def _find_role_by_trust_policy(iam_client: Any, account_id: str) -> tuple[str | None, list[str]]:
    """Return (role_name_or_None, notes) for the role trusting the GitHub OIDC provider for this repo."""
    provider_arn = f'arn:aws:iam::{account_id}:oidc-provider/{OIDC_PROVIDER_URL}'
    notes: list[str] = []
    paginator = iam_client.get_paginator('list_roles')
    for page in paginator.paginate():
        for role in page['Roles']:
            doc = role['AssumeRolePolicyDocument']
            for statement in doc.get('Statement', []):
                principal = statement.get('Principal', {})
                federated = principal.get('Federated', '')
                federated_values = federated if isinstance(federated, list) else [federated]
                if provider_arn in federated_values:
                    return role['RoleName'], notes
    return None, notes


def _check_trust_policy(doc: dict[str, Any], account_id: str, results: list[tuple[bool, str]]) -> None:
    provider_arn = f'arn:aws:iam::{account_id}:oidc-provider/{OIDC_PROVIDER_URL}'
    statements = doc.get('Statement', [])
    matching = None
    for statement in statements:
        principal = statement.get('Principal', {})
        federated = principal.get('Federated', '')
        federated_values = federated if isinstance(federated, list) else [federated]
        if provider_arn in federated_values:
            matching = statement
            break

    if matching is None:
        results.append((False, f'❌ Trust policy does not federate {provider_arn}'))
        return
    results.append((True, f'✅ Trust policy federates {provider_arn}'))

    action = matching.get('Action', '')
    action_ok = action == 'sts:AssumeRoleWithWebIdentity' or 'sts:AssumeRoleWithWebIdentity' in action
    results.append((action_ok, f'{"✅" if action_ok else "❌"} Action is sts:AssumeRoleWithWebIdentity (found: {action!r})'))

    condition = matching.get('Condition', {})
    aud = condition.get('StringEquals', {}).get(f'{OIDC_PROVIDER_URL}:aud')
    aud_ok = aud == EXPECTED_AUDIENCE
    results.append((aud_ok, f'{"✅" if aud_ok else "❌"} aud condition == {EXPECTED_AUDIENCE!r} (found: {aud!r})'))

    sub_string_equals = condition.get('StringEquals', {}).get(f'{OIDC_PROVIDER_URL}:sub')
    sub_string_like = condition.get('StringLike', {}).get(f'{OIDC_PROVIDER_URL}:sub')
    sub_value = sub_string_equals or sub_string_like
    sub_ok = sub_value == EXPECTED_SUBJECT
    results.append(
        (
            sub_ok,
            f'{"✅" if sub_ok else "❌"} sub condition scoped to {EXPECTED_SUBJECT!r} '
            f'(found: {sub_value!r}) — an unscoped or wildcard sub lets ANY repo assume this role',
        )
    )


def _check_permissions(iam_client: Any, role_name: str, results: list[tuple[bool, str]]) -> None:
    forbidden_found: list[str] = []

    for policy_name in iam_client.list_role_policies(RoleName=role_name).get('PolicyNames', []):
        policy = iam_client.get_role_policy(RoleName=role_name, PolicyName=policy_name)
        statements = policy['PolicyDocument'].get('Statement', [])
        for statement in statements:
            actions = statement.get('Action', [])
            actions = [actions] if isinstance(actions, str) else actions
            forbidden_found.extend(a for a in actions if a in FORBIDDEN_ACTIONS or a == '*')

    for policy_arn_entry in iam_client.list_attached_role_policies(RoleName=role_name).get('AttachedPolicies', []):
        results.append((False, f'⚠️ Managed policy attached: {policy_arn_entry["PolicyName"]} — verify it is not overly broad'))

    if forbidden_found:
        results.append((False, f'❌ Role grants forbidden/deploy actions: {sorted(set(forbidden_found))}'))
    else:
        results.append((True, '✅ No CreateChangeSet/ExecuteChangeSet/DeleteStack/UpdateStack/CreateStack/"*" actions found'))


def _check_github_secret(results: list[tuple[bool, str]]) -> None:
    try:
        proc = subprocess.run(
            ['gh', 'secret', 'list', '--repo', GITHUB_REPO],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
    except (FileNotFoundError, subprocess.SubprocessError) as exc:
        results.append((True, f'⚠️ Could not check GitHub secret (gh CLI unavailable/unauthenticated: {exc}) — skipped, not a failure'))
        return

    if proc.returncode != 0:
        results.append((True, f'⚠️ `gh secret list` failed ({proc.stderr.strip()}) — skipped, not a failure'))
        return

    found = any(line.split()[0] == GITHUB_SECRET_NAME for line in proc.stdout.splitlines() if line.strip())
    results.append((found, f'{"✅" if found else "❌"} GitHub secret {GITHUB_SECRET_NAME} {"exists" if found else "NOT FOUND"} in {GITHUB_REPO}'))


def verify_oidc(role_name: str | None) -> int:
    iam_client = boto3.client('iam')
    sts_client = boto3.client('sts')
    results: list[tuple[bool, str]] = []

    try:
        account_id = _account_id(sts_client)
    except (ClientError, BotoCoreError) as exc:
        print(f'❌ Could not resolve AWS account (no/invalid credentials?): {exc}')
        return 1

    try:
        oidc_providers = iam_client.list_open_id_connect_providers()['OpenIDConnectProviderList']
    except (ClientError, BotoCoreError) as exc:
        print(f'❌ Could not list OIDC providers: {exc}')
        return 1

    provider_arn = f'arn:aws:iam::{account_id}:oidc-provider/{OIDC_PROVIDER_URL}'
    provider_exists = any(p['Arn'] == provider_arn for p in oidc_providers)
    results.append((provider_exists, f'{"✅" if provider_exists else "❌"} OIDC provider {OIDC_PROVIDER_URL} exists in account {account_id}'))

    resolved_role_name = role_name
    if resolved_role_name is None:
        resolved_role_name, _ = _find_role_by_trust_policy(iam_client, account_id)

    if resolved_role_name is None:
        results.append((False, '❌ No IAM role found trusting the GitHub OIDC provider — has the P-22 role been created?'))
        for _success, message in results:
            print(message)
        print('\n❌ OIDC verification FAILED')
        return 1

    results.append((True, f'✅ Found candidate role: {resolved_role_name}'))

    try:
        role = iam_client.get_role(RoleName=resolved_role_name)['Role']
    except (ClientError, BotoCoreError) as exc:
        print(f'❌ Could not read role {resolved_role_name}: {exc}')
        return 1

    _check_trust_policy(role['AssumeRolePolicyDocument'], account_id, results)
    _check_permissions(iam_client, resolved_role_name, results)
    _check_github_secret(results)

    for _success, message in results:
        print(message)

    if all(success for success, _ in results):
        print('\n✨ OIDC verification PASSED')
        return 0
    print('\n❌ OIDC verification FAILED')
    return 1


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Verify the P-22 GitHub OIDC cdk-diff role.')
    parser.add_argument(
        '--role-name',
        default=None,
        help='IAM role name to check (default: auto-discover by trust-policy federation).',
    )
    parser.add_argument('--json', action='store_true', help='Also print machine-readable JSON summary to stderr.')
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = _parse_args(argv)
    exit_code = verify_oidc(role_name=args.role_name)
    if args.json:
        print(json.dumps({'passed': exit_code == 0}), file=sys.stderr)
    sys.exit(exit_code)


if __name__ == '__main__':
    main()
