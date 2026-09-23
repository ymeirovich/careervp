---
spec_id: P-09-IAM-PER-FUNCTION
title: "One IAM role per Lambda with env-scoped ARN policies"
status: draft
owner: infra
tier: T1
scope_lock_clause: P-09
claude_code: {model: opus, effort: high}
codex: {model: gpt-5-codex, reasoning: high}
format_note: "AUTHOR ONLY. RED tests are inline descriptions; pytest files are written later at IMPLEMENT time."
---

# Spec - P-09: IAM Per Function

## Problem Statement

Many functions share broad policy machinery. P-09 requires one IAM role per function, env-suffixed role names, and ARN-scoped permissions with no wildcard resources where ARNs are known. This is infra-only but has high blast radius and must follow P-26 headroom.

## Evidence

- `infra/careervp/api_construct.py:516-821` builds shared policy documents for groups of Lambda capabilities including jobs, idempotency, knowledge, company research cache, LLM cache, and SSM parameters.
- `infra/careervp/api_construct.py:661` includes `dynamodb:Scan`, which should not be part of a broad shared role after least-privilege split.
- `infra/careervp/api_construct.py:901-2040` creates many API Lambdas that must receive distinct roles.
- `infra/careervp/naming_utils.py:103-111` provides resource naming helpers; roles must follow `careervp-role-{service}-{feature}-{env}` via `NamingUtils`/constants.
- Scope-lock invariant requires one IAM role per function, ARN-scoped, `{env}`-suffixed, no `Resource:"*"` where ARNs are known.

## Fix Plan

1. Inventory every Lambda function created by CDK and its required data-plane/control-plane permissions.
2. Create one explicit role per function with env-suffixed physical role name derived from constants/naming utils.
3. Attach least-privilege policies scoped to exact table, queue, bucket, state machine, topic, and parameter ARNs.
4. Remove shared role reuse and default-role fallbacks for billing/export functions.
5. Serialize this with P-26 because it edits `api_construct.py` and adds resources to the parent stack.

## RED Tests to Write First

- `test_p09_every_lambda_has_unique_role`: synth template and assert `len(unique role refs) == len(lambda functions)` except documented service-managed exceptions.
- `test_p09_role_names_are_env_suffixed_kebab_case`: assert every role name starts `careervp-role-` and ends `-{env}`.
- `test_p09_no_known_arn_permission_uses_resource_star`: inspect IAM policies; for DynamoDB/S3/SQS/SNS/SSM/StepFunctions actions with known resources, assert `Resource != "*"`.
- `test_p09_billing_and_export_do_not_use_default_roles`: assert billing/export Lambdas have explicit roles.

## Acceptance Criteria

**AC-P09-1** - Given synthesized Lambdas, when roles are inspected, then every function has a unique explicit role.

**AC-P09-2** - Given IAM policies, when resources are known at synth time, then policies scope to ARNs and never use wildcard resources.

**AC-P09-3** - Given role physical names, when naming validator runs, then all role names satisfy the kebab-case env-suffix convention.

## Done-when

All RED tests pass; `cdk diff` shows zero stateful replacement; naming validator passes; Checkov/Bandit remain green.

## Sequencing / Dependencies

Must wait for P-26 parent-stack headroom and should not run concurrently with other `api_construct.py` edits.

