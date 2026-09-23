---
spec_id: P-23-CANARY-ROLLBACK
title: "Lambda alias/version and CodeDeploy canary rollback"
status: draft
owner: infra
tier: T1
scope_lock_clause: P-23
claude_code: {model: opus, effort: high}
codex: {model: gpt-5-codex, reasoning: high}
format_note: "AUTHOR ONLY. RED tests are inline descriptions; pytest files are written later at IMPLEMENT time."
---

# Spec - P-23: Canary/Rollback

## Problem Statement

P-04 and later handler changes need a Lambda-code rollback lever. P-23 provides alias+version and CodeDeploy canary rollback for Lambda changes, while explicitly not pretending to roll back API Gateway authorizer/method control-plane changes.

## Evidence

- `infra/careervp/api_construct.py:901-2040` creates many API Lambdas without visible CodeDeploy deployment groups.
- `rg` evidence for `CodeDeploy`, `DeploymentGroup`, and `LambdaDeployment` in infra returned no current deployment-group wiring.
- `src/backend/careervp/handlers/api_gateway_authorizer.py:34` exists as an authorizer handler surface where resolver metrics/canary checks may attach after P-24.
- Scope-lock P-04 says CodeDeploy is the lever for handler fallback removal only, not API-Gateway authorizer changes.

## Fix Plan

1. Publish versions and create stable aliases for Lambda functions that serve public/API routes.
2. Add CodeDeploy deployment groups with canary config and rollback alarms.
3. Add per-outcome auth/resolver alarms needed by P-04/P-24, not aggregate 401-only alarms.
4. Document separate revert paths: Lambda alias rollback via CodeDeploy; API Gateway authorizer/stage rollback via stage redeploy.

## RED Tests to Write First

- `test_p23_api_lambdas_have_alias_and_version`: synth and assert each API Lambda has an alias pointing to a published version.
- `test_p23_codedeploy_groups_exist_for_api_lambdas`: assert deployment groups exist with canary configuration.
- `test_p23_rollback_alarms_include_auth_resolver_failure`: assert alarms include resolver-failure/per-outcome signals, not only aggregate 401 rate.
- `test_p23_revert_runbook_distinguishes_lambda_from_api_gateway`: assert runbook text names CodeDeploy for Lambda changes and API stage redeploy for authorizer changes.

## Acceptance Criteria

**AC-P23-1** - Given a Lambda handler deployment, when errors breach alarm thresholds during canary, then CodeDeploy rolls the alias back to the previous version.

**AC-P23-2** - Given an API Gateway authorizer/stage configuration change, when rollback is needed, then the runbook uses stage/deployment rollback, not Lambda CodeDeploy.

## Done-when

All RED tests pass; rollback runbook is fire-drillable; `cdk diff` zero stateful replacement; naming validator passes.

## Sequencing / Dependencies

Must precede P-04/P-05. Does not replace P-27/P-28 deploy safety.

