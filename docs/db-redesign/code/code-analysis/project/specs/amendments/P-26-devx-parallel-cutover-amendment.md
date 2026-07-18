# Amendment Proposal — P-26 `dev` parallel `-devx` cutover

> Emitted per scope-lock §0.3. This is a proposal awaiting human validation. It
> does not edit either `project-scope-lock` twin, change infrastructure, or
> authorize a deployment/cutover/decommission.

| Field | Value |
|---|---|
| **clause_id** | `P-26` (dev-only Job-1/Job-2 mechanism) and `O-9` live-current-state correction |
| **tag** | `TARGET`; no IMMUTABLE invariant, locked decision, or frontend-contract item is changed |
| **semver level** | **MINOR** — refines how a TARGET is delivered in disposable pre-launch `dev`; the O-9 fact correction is PATCH-level, but the release includes the P-26 refinement |
| **affected contract twins** | `project-scope-lock.md`, `project-scope-lock.yaml` (both must be updated together, version `2.5.0` → `2.6.0`, with a §12 / `change_log` row) |
| **affected specs/runbooks** | `specs/P-26-blue-green-api-spec.md`, `runbooks/wave-1-status.md` rows 1.3d/1.4, `runbooks/p28-human-gated-deploy-runbook.md`, and the P-26 devx handoff |
| **affected tests** | Replace resource-import-shape assertions with fresh-devx topology and "devx does not claim the shared domain before cutover" assertions; retain the protected-resource/replacement-report tests for the human-only flip |
| **requires adversarial review?** | **No** for the contract amendment: existing `dev` data/accounts may be discarded by the stated human decision, while staging/prod guarantees remain unchanged. Human sign-off is still mandatory. |

## Proposed decision

For the **`dev` environment only**, declare the existing pre-launch data and
Cognito accounts disposable. Supersede P-26 Job-1's live resource-import
mechanism with a parallel `CareerVpCrudDevx` deployment using
`ENVIRONMENT=devx` and `p26_rehome_features=true` from its first creation.
Validate it on its raw execute-api URL, then perform the P-28 human-only
base-path-mapping cutover to the stable `api.dev.careervp.com` domain. Only
after successful smoke, frontend Cognito configuration, and explicit human
approval may the old `CareerVpCrudDev` stack be decommissioned.

This decision does **not** authorize moving/replacing an existing RestApi or
Cognito pool in place. It permits a fresh, isolated devx stack and an eventual
human-gated deletion of the old disposable dev environment. It does **not**
relax the P-26 data/Cognito preservation requirements for `staging` or `prod`.

## Why the amendment is needed

The currently locked P-26 materials require preservation of the existing dev
tables, buckets, and Cognito pool, and the Wave-1 ledger therefore tracks a
human-gated `cdk refactor` import. The recorded human decision in
`runbooks/p26-devx-parallel-cutover-handoff.md` changes that delivery mechanism:
fresh devx resources are now preferred because the live dev state is declared
disposable. This is a mechanism/risk-class change to a TARGET and must be
recorded before code or deployment work proceeds.

## Live evidence captured 2026-07-18

All commands used account `788159322332`, region `us-east-1` (STS identity:
`presgen_user`).

- `verify_aws_state.py --mode deployed` passed for the old `dev` Lambda,
  DynamoDB tables, and CV bucket.
- `dig` resolves `api.dev.careervp.com` to
  `d-ufdp03t4f1.execute-api.us-east-1.amazonaws.com`, but API Gateway lists
  only `dev-api.careervp.com` and `stage-api.careervp.com`; `get-domain-name
  api.dev.careervp.com` returns `NotFoundException`.
- ACM certificate
  `d93bafb3-fe1a-4faa-9335-a9e868646bdb` for `api.dev.careervp.com` is
  `ISSUED` but has an empty `InUseBy` list. The custom-domain health request
  failed name resolution in the deployment host, while the old raw endpoint
  `https://4xe2tdq8z6.execute-api.us-east-1.amazonaws.com/prod/health`
  returned HTTP 200.
- `CareerVpCrudDev` is `UPDATE_COMPLETE`, but its CloudFormation
  termination-protection flag is `false`. This does not authorize deletion;
  it corrects the handoff's assumption that a protection lift already exists.

Plain English: the proposed safe handover point does not exist in AWS right
now, so a devx cutover cannot be prepared safely until the old custom-domain
state is reconciled.

## Required human commit contents if approved

1. Update both scope-lock twins to `2.6.0`, adding an identical dated change
   log entry that records the dev-only disposable-data decision, the devx
   parallel-stack mechanism, and the O-9 live-state correction.
2. Change P-26 wording only for `dev`: devx may create fresh tables/buckets/
   Cognito from birth; staging/prod retain the no-loss guarantee. Remove the
   live-resource-import requirement from the active dev path, but retain its
   evidence and code as historical/inactive until separately retired.
3. Change O-9 from resolved to blocked/current-state-drift until an AWS
   `AWS::ApiGateway::DomainName` plus `BasePathMapping` for
   `api.dev.careervp.com` exists and the live frontend seam is verified.
4. Include the human approval trailer in the human-executed commit:

   ```text
   Scope-Lock-Approved-By: <name> 2026-07-18
   ```

After that commit, update the dependent P-26 spec and runbook, implement the
domain-claim gate and its tests, and run the required synth/diff/naming checks
before any devx create change set. The base-path flip and old-stack retirement
remain separate human-only approvals.

## Decision record

**Status:** pending explicit human scope-lock approval.

