# Fable infra-mitigation plan — FINDINGS DIGEST (evidence for the eval council)

> This is a **distilled digest** of `fable-infra-mitigation-plan.md` (62 KB verbatim, kept on disk
> for drill-down). It is **evidence, not gospel** — an independent deployment-safety analysis (5
> Claude roles) of shipping P-04/P-08/P-10/P-12/P-26/Track-D without breaking the live Amplify
> frontend. Verify its load-bearing claims against the live-truth file before adopting any of them.

## Load-bearing claims (VERIFY — several are already checked in live-truth-2026-07-11.md)
- **CFN ceiling:** claims parent stack **476/500**, calls the register's 415 "stale." → **Live check
  says 415/500 deployed** (476 is likely a post-`cdk synth`-with-additions figure). Treat 415 as baseline.
- **Dead rollback lever:** `AUTHORIZER_DISABLED` (api_construct.py:1720) set on ONE lambda, claims
  **zero readers** in backend → P-04's "instant revert" is really a 15–30 min redeploy. **Unverified
  live** (needs a repo grep — see live-truth open items).
- **DESTROY everywhere:** all tables + buckets `RemovalPolicy.DESTROY`, `auto_delete_objects=True`,
  even the backups bucket; PITR 7d, llm-cache none. (Matches register; RETAIN = P-12.)
- **Three-layer CORS:** Lambda (`cors_utils.py`, exact-string match, NO wildcard), S3, API GW each
  match differently → a wildcard list passes template assertions but fails at runtime. Keep the
  `GatewayResponse` ACAO `'*'` (safe for 401s; tightening it makes every 401 CORS-opaque).
- **Cognito unbackupable:** user-pool replacement deletes all users (no password-hash export);
  callback URLs already drift from live console.
- **Deploy pipeline risk:** `deploy.yml` auto-deploys dev on every push to `main` with
  `cancel-in-progress: true`; a second merge can cancel mid-CFN-update. `app.py:13-27` infers
  account/region from ambient env → wrong `AWS_PROFILE` deploys to the wrong account.

## Mechanical mitigations the Fable plan proposes (the "missing gates")
1. **CFN stack policy** — deny `Update:Replace`/`Update:Delete` on RestApi, all DynamoDB, all S3,
   Cognito UserPool, and the nested `AWS::CloudFormation::Stack`s.
2. **Termination protection** on all stacks.
3. **IAM credential split** — agents get `CreateChangeSet` + `Describe*/Get*/List*` only; deny
   `ExecuteChangeSet`/`UpdateStack`/`cognito-idp:*`/etc. **Humans-only `ExecuteChangeSet`.**
4. **Hard-pin account/region** in `app.py` (fail fast on mismatch).
5. **Evidence snapshot pack** (read-only) — live template, stack-resources map, API-GW domain/
   base-path-mapping/deploymentId/OpenAPI export, Route53, per-Lambda env, Cognito config, Amplify
   env, bucket CORS, **on-demand DynamoDB backups**, external S3 sync of the unversioned upload bucket.
6. **4-wire smoke harness** — health · OPTIONS+GET with exact Origin assertion · authed read ·
   presigned upload; baseline green before any change.
7. **P-08 before P-10** (smaller blast radius, seconds-revert, validates the oracle gate first).
8. **P-26 blue/green** — never move the RestApi; stand up a NEW one beside it, verify via raw
   `execute-api` URL, re-point base-path mapping, retire old API in a later deploy.

## Revised deploy sequence (gist)
Step 0 (human, blocking): termination protection + stack policy + evidence pack + P-12 (DESTROY→
RETAIN, deletion_protection, drop auto_delete, version buckets) + smoke baseline + credential split.
→ Step 1 Wave-0 nets. → Step 2 P-08 (S3 CORS). → Step 3 P-10 (API/Lambda CORS; max-age→60s first;
pre-stage inverse change set). → Step 4 P-04 (rebuild the flag as a real runtime-read lever; fire-
drill revert RTO; watch 401 rate ≥24h). → Step 5 P-26 (blue/green). → Step 6 P-07 MFA (low-risk).

## The plan's own stated assumptions/unknowns
- Effort scored **"for a team of 2–3"; "a human executes every `ExecuteChangeSet`" is non-negotiable**
  per all five roles. (⚠️ CareerVP is solo, C-3 — reconcile.)
- Live-deployed stack assumed to match `db-redesign` HEAD (drift likely: Cognito callback URLs,
  Amplify env, possibly auth already ON). Fire-drill redeploy from an old SHA may fail (rotted locks).
