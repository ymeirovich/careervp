# Runbook — P-29 Pre-Deploy Evidence Pack

**Clause:** P-29 · **Step:** 0.61 · **Gate:** must run green BEFORE deploy #1 (step 0.6 RETAIN flip) and before the P-26 blue/green migration.

The evidence pack captures a reproducible golden "before" state so that any risky
deploy can be verified (and, if needed, reversed) against a known baseline. It is
**read-only** for inspection; the only mutating actions are additive: on-demand
DynamoDB backups and an S3 sync of the unversioned upload bucket.

Tooling:
- Collector / gate: `src/backend/scripts/evidence_pack.py`
- Shared deploy-gate validators: `src/backend/scripts/deploy_evidence.py`
- Output: timestamped JSON under `docs/evidence/`

## What is captured

| Section | Source | Notes |
|---|---|---|
| `cloudformation` | `aws cloudformation get-template` / `describe-stacks` for each stack in `infra/app.py` | template + deployed resource ids |
| `api_gateway` | `aws apigateway get-rest-apis` / `get-domain-names` / `get-base-path-mappings` / `get-stages` | domain, base path, stage, deployment id |
| `lambda_env` | `aws lambda get-function-configuration` | **secret-like values redacted**, key names kept |
| `cognito` | `aws cognito-idp describe-user-pool` / `describe-user-pool-client` | callback/logout URLs, app-client config (P-07 drift guard) |
| `amplify` | `aws amplify get-app` / `get-branch` | **exact `NEXT_PUBLIC_API_URL`** + classified kind (raw vs custom-domain) |
| `bucket_cors` | `aws s3api get-bucket-cors` | upload bucket CORS before changes |
| `dns` | `dig +short api.{env}.careervp.com` (external, Cloudflare) | O-9/P-26 precondition |
| `dynamodb_backups` | `aws dynamodb create-backup` | **records backup ARNs** (gate fails closed if absent) |
| `s3_sync` | `aws s3 sync s3://<uploads> <dest>` | unversioned upload bucket → backup destination |

## Preview the shape offline (no AWS)

```bash
cd src/backend
uv run python scripts/evidence_pack.py --dry-run --out-dir /tmp/evidence-preview
```

This writes a fixture pack and runs the gate so you can see the exact JSON
structure and confirm the gate logic before touching AWS.

## Live capture (human, AWS credentials required)

> Deploy is human-gated (P-28). This collector does not deploy anything, but it
> does create DynamoDB backups and sync S3, so run it with a role that has
> read + `dynamodb:CreateBackup` + `s3:GetObject`/`PutObject` on the backup bucket.

1. Assume the read/backup role (NOT the execute-change-set role).
2. Run the per-section AWS CLI captures above for the target env (`dev` first).
   For each live table, run `aws dynamodb create-backup` and record the returned
   `BackupArn` into the `dynamodb_backups` section.
3. Run `aws s3 sync` from the uploads bucket to the backup destination; record
   the object count.
4. Assemble the sections into the evidence JSON (same shape as `--dry-run`) and
   validate:
   ```bash
   uv run python -c "import json,sys; \
     sys.path.insert(0,'scripts'); import evidence_pack as e; \
     ev=json.load(open('docs/evidence/<pack>.json')); \
     errs=e.validate_evidence(ev); print(errs or 'GATE PASSED'); sys.exit(1 if errs else 0)"
   ```
5. The gate **fails closed**: a missing section or missing DynamoDB backup ARN
   blocks the deploy. Do not proceed to step 0.6 until it prints `GATE PASSED`.

## Relationship to other gates

- **P-30 smoke harness** (`scripts/smoke_harness.py`) records the live-wire proof
  the pack references for API health/CORS/auth/upload.
- **P-21 subscription evidence** (`deploy_evidence.validate_sns_subscription_confirmed`)
  is a sibling fail-closed gate: an alarm topic with only a `PendingConfirmation`
  subscription does not satisfy the pre-migration gate.
