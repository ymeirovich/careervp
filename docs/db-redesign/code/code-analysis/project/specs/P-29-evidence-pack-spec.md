---
spec_id: P-29-EVIDENCE-PACK
title: "Pre-deploy evidence snapshot pack and on-demand backups"
status: draft
owner: infra
tier: T1
scope_lock_clause: P-29
claude_code: {model: sonnet, effort: medium}
codex: {model: gpt-5-codex, reasoning: medium}
format_note: "AUTHOR ONLY. RED tests are inline descriptions; pytest files are written later at IMPLEMENT time."
---

# Spec - P-29: Evidence Pack and Backups

## Problem Statement

Before risky deploys, CareerVP needs a reproducible golden-state snapshot: templates, API Gateway domain/base-path/deployment ids, Lambda env, Cognito config, Amplify env, bucket CORS, external DNS, on-demand DynamoDB backups, and external S3 sync for unversioned uploads.

## Evidence

- `infra/app.py:39-65` instantiates deployed stacks; these are the templates to snapshot.
- `infra/careervp/api_construct.py:254-279` exposes the dev API custom-domain target output needed by O-9/P-26.
- `infra/careervp/api_construct.py:356-370` configures RestApi CORS/throttle settings that must be captured before changes.
- `infra/careervp/cognito_construct.py:39-58` holds callback/logout URLs and app-client config that must not drift before P-07.
- Scope-lock P-29 requires template, API-GW, Lambda env, Cognito, Amplify, bucket CORS, Route53/Cloudflare, DynamoDB backup, and S3 sync evidence.

## Fix Plan

1. Implement a read-only evidence collector that writes timestamped JSON/YAML under `docs/evidence/`.
2. Capture CloudFormation templates and deployed stack resource ids.
3. Capture API Gateway domain/base-path/stage/deployment id and `NEXT_PUBLIC_API_URL` as deployed in Amplify.
4. Capture Lambda env keys with sensitive values redacted.
5. Trigger on-demand DynamoDB backups for live tables and record backup ARNs.
6. Sync unversioned upload bucket contents to an external/backup bucket or documented local snapshot path.

## RED Tests to Write First

- `test_p29_evidence_pack_contains_required_sections`: run collector in dry-run with fixtures; assert sections `cloudformation`, `api_gateway`, `lambda_env`, `cognito`, `amplify`, `bucket_cors`, `dns`, `dynamodb_backups`, `s3_sync` exist.
- `test_p29_evidence_redacts_secret_values`: fixture Lambda env includes secret-like keys; assert output redacts values and keeps key names.
- `test_p29_blocks_deploy_without_backup_arns`: deploy gate fixture lacking DynamoDB backup ARNs fails.
- `test_p29_records_next_public_api_url`: assert Amplify env capture includes exact `NEXT_PUBLIC_API_URL` value and timestamp.

## Acceptance Criteria

**AC-P29-1** - Given a risky deploy, when the gate runs, then a fresh evidence pack exists before any change set execution.

**AC-P29-2** - Given stateful resources, when backups/sync are captured, then DynamoDB backup ARNs and S3 sync evidence are recorded and human-readable.

**AC-P29-3** - Given O-9/P-26, when `NEXT_PUBLIC_API_URL` is inspected, then the pack states whether frontend points at raw execute-api or `https://api.{env}.careervp.com`.

## Done-when

All RED tests pass; collector is read-only except backup/sync actions; no production code changes; any AWS access is human-approved during implementation.

## Sequencing / Dependencies

Wave 0 precondition before P-12 deploy #1 and P-26.

