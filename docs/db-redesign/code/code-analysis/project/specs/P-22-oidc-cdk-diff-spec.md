---
spec_id: P-22-OIDC-CDK-DIFF
title: "OIDC in cdk-diff.yml (kill long-lived AWS keys)"
status: draft
owner: infra
tier: T1
scope_lock_clause: P-22
claude_code: {model: sonnet, effort: medium}
codex: {model: gpt-5-codex, reasoning: medium}
format_note: "AUTHOR ONLY. RED tests are inline descriptions; pytest files are written later at IMPLEMENT time."
---

# Spec - P-22: OIDC in cdk-diff.yml

## Problem Statement

The CDK diff pull-request workflow currently authenticates to AWS with long-lived access-key secrets. P-22 replaces those static credentials with GitHub OIDC role assumption so the workflow receives short-lived credentials scoped by an IAM role trust policy.

## Evidence

- `.github/workflows/cdk-diff.yml:34-42` uses `aws-actions/configure-aws-credentials@v4`.
- `.github/workflows/cdk-diff.yml:40-41` injects AWS credentials from `${{ secrets.AWS_ACCESS_KEY_ID }}` and `${{ secrets.AWS_SECRET_ACCESS_KEY }}`.
- `.github/workflows/cdk-diff.yml:6-9` grants `contents: read` and `pull-requests: write`, but does not grant `id-token: write`, so GitHub cannot mint an OIDC token for AWS STS.

## Fix Plan

1. Add `id-token: write` to `.github/workflows/cdk-diff.yml` permissions.
2. Change the `Configure AWS credentials` step to use `role-to-assume` with a GitHub secret containing the cdk-diff IAM role ARN.
3. Remove all references to long-lived AWS access-key and secret-access-key secrets from the workflow.
4. Document the AWS account-side setup as human-owned: create or confirm the GitHub OIDC provider and create a role trust policy that allows this repository's pull-request workflow subject to assume the cdk-diff role.

## RED Tests to Write First

- `test_p22_cdk_diff_uses_oidc_role_assumption`: parse `.github/workflows/cdk-diff.yml` and assert the AWS credentials step uses `aws-actions/configure-aws-credentials@v4`, has `role-to-assume`, and does not have `aws-access-key-id` or `aws-secret-access-key`.
- `test_p22_cdk_diff_has_id_token_permission`: parse `.github/workflows/cdk-diff.yml` and assert top-level `permissions.id-token` is `write`.
- `test_p22_cdk_diff_workflow_has_no_long_lived_aws_secret_references`: read `.github/workflows/cdk-diff.yml` as text and assert it does not reference `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `aws-access-key-id`, or `aws-secret-access-key`.

## Acceptance Criteria

**AC-P22-1** - Given a pull request that triggers `cdk-diff.yml`, when AWS credentials are configured, then GitHub assumes an IAM role via OIDC using `role-to-assume`.

**AC-P22-2** - Given the cdk-diff workflow source, when it is inspected, then no long-lived AWS access key or secret key is referenced.

**AC-P22-3** - Given the GitHub OIDC flow, when the workflow requests an identity token, then `permissions.id-token: write` is present.

**AC-P22-4** - Given the real AWS account, when the workflow runs, then a human-created IAM OIDC provider and role trust policy allow only the intended GitHub repository/ref subject to assume the cdk-diff role.

## Done-when

All RED tests pass; `.github/workflows/cdk-diff.yml` uses `role-to-assume` and `id-token: write`; the workflow no longer references long-lived AWS key secrets; `scope-diff.py` reports P-22 as `test_written`; and a human has created or verified the AWS IAM OIDC provider plus the cdk-diff role trust policy for this repository.

## Sequencing / Dependencies

This is a CI-only change with no application-code dependency. It touches only `docs/db-redesign/code/code-analysis/project/specs/P-22-oidc-cdk-diff-spec.md`, `.github/workflows/cdk-diff.yml`, the P-22 workflow tests, and the Wave-1 status ledger. Do not modify application code, any other workflow, or `infra/careervp/api_construct.py`.
