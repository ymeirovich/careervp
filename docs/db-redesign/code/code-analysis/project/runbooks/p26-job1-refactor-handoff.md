# P-26 Job-1 `cdk refactor` — Execution Handoff (HUMAN-GATED)

**Goal:** relocate the **76 named, non-stateful feature resources** out of the near-limit
`CareerVpCrudDev` parent template into the `CrudFeatures` nested stack via a CloudFormation
**resource-import** (`cdk refactor`) — physical ids and logical ids preserved byte-for-byte, **no
delete/create**. This drops the parent **489 → 295** and unblocks 1.4 / P-09.

This is Wave-1 step **1.3d** (P-26 Job-1). Engineering is already committed and dormant behind the
CDK context flag `p26_rehome_features`; only the human-gated refactor **execution** remains.

---

## 0. The two IMMUTABLE laws (a breach here = STOP, do not execute)

1. The live **RestApi** (`CareerVpCrudDevCrudservicerestapi5E02FD49`) is NEVER moved/replaced —
   moving it changes `https://api.dev.careervp.com`.
2. The live **Cognito** user pool (`CareerVpCrudDevCognitoUserPool42C0A4E4`) + client
   (`...UserPoolClientFD4D0C15`) are NEVER moved/replaced — moving them locks out the live users.

Both must stay in the parent and must NOT appear in the refactor mapping at all.

---

## 1. Preconditions (verify before doing anything)

- [ ] `git log -1 -- .../project/project-scope-lock.yaml` history includes the **v2.5.0** amendment
      (`0a0cb81`) filing Job-1 under Wave-1 (later bookkeeping commits touch the file too — check
      the file is at `version: 2.5.0`, not just the top commit subject).
- [ ] Spine clear: 1.3c-gate / P-11 landed (`8f94b83`); no open blocker in the row above 1.3d.
- [ ] **Live is HEAD deployed FROM CI (owner tag = `runner`).** Check:
      `AWS_REGION=us-east-1 npx cdk diff CareerVpCrudDev` should show ONLY owner-tag
      (`runner`↔your-user) + Lambda asset-hash churn, **zero `[!]` replacement, zero substantive
      property diff.** If it shows real property changes, HEAD is not fully deployed — deploy it
      first via `deploy.yml` (workflow_dispatch) before refactoring.
- [ ] Gate is green offline:
      `cd infra && npx cdk synth CareerVpCrudDev -c p26_rehome_features=true --output cdk.out.on`
      then `uv run python scripts/p26_refactor_gate.py --synth-on cdk.out.on` → **PASS**.

---

## 2. Why you cannot dry-run cleanly from a laptop

`cdk refactor` refuses any add/remove/**update** and matches resources by content digest. The
`owner` tag is `getpass.getuser()` (`runner` in CI, your username locally) and Lambda code
re-bundles to fresh hashes locally, so from a laptop **every** resource — even non-moving Cognito
and DynamoDB tables — looks "updated" and the refactor aborts. **Run it where the synth matches
live:** the CI runner (owner=`runner`, same `make build` hashes as the deploy). That is what the
`p26-refactor.yml` workflow is for. (Local fallback: `export USER=runner` and re-deploy HEAD from
that same shell so asset hashes match, then refactor — but CI is the supported path.)

---

## 3. Kickoff via CI (supported path)

Workflow: `.github/workflows/p26-refactor.yml`. It mirrors the P-28 gated deploy: PLAN uses the
read-only `AWS_ROLE`; APPLY uses `AWS_EXECUTE_ROLE` behind the `deploy-dev` environment reviewer.

### 3a. PLAN (read-only)
```
gh workflow run p26-refactor.yml -f mode=plan
```
The PLAN job: `make build` → synth flag-ON → `cdk refactor --dry-run` → **enforces the gate**
(`p26_refactor_gate.py`). It uploads the parent + CrudFeatures templates and the dry-run log as a
build artifact. **The gate must be GREEN.** Download the artifact and read the dry-run mapping.

### 3b. GATE — confirm ALL of these in the PLAN output (any failure → STOP)
- Parent `CareerVpCrudDev` < **400** (expect 295); no template ≥ **500**.
- **RestApi and Cognito do NOT appear** in the refactor mapping.
- Every named resource is a **MOVE/rename** (logical id preserved) — **zero DELETE+CREATE / zero
  Replacement**.
- The dormant **P-24 authorizer** (`CareerVpCrudDevCrudApiAuthorizerLambda`) is absent everywhere.
- `p26_refactor_gate.py` prints `=== P-26 REFACTOR GATE: PASS ===` (exit 0).

If the gate fails on **G5 "refactor log reports FAILURE"**, live still differs from the CI synth
(owner-tag/asset-hash) — redeploy HEAD from CI (`deploy.yml`) then re-run PLAN. Do NOT proceed.

### 3c. APPLY (human-gated execute)
```
gh workflow run p26-refactor.yml -f mode=apply -f confirm_stack=CareerVpCrudDev
```
- `confirm_stack` must equal `CareerVpCrudDev` or the job self-aborts.
- The `deploy-dev` environment **required reviewer** must approve the run (read the PLAN artifact /
  the P-28 DescribeChangeSet Replacement report first).
- APPLY re-synths, **re-runs the gate** (defense in depth), then executes
  `cdk refactor "$STACK_NAME" --unstable=refactor --force -c p26_rehome_features=true`
  (add `-f override_file=docs/evidence/p26-job1-refactor-override.json` ONLY if PLAN showed the
  auto-matcher mis-guessing — prefer the auto-computed mapping).
- APPLY then runs **P-30 smoke** against `https://api.dev.careervp.com` — must be **4/4 green**.

---

## 4. Post-execute verification (must all hold)

- [ ] `cdk refactor` reported success; the 76 resources now live in the `CrudFeatures` nested stack
      with unchanged physical names (spot-check: `aws lambda get-function --function-name
      careervp-auth-api-lambda-dev` still resolves).
- [ ] **P-30 smoke 4/4 green** (health, exact-origin CORS, authed read + unauth reject, authed
      upload/read-back) through `https://api.dev.careervp.com`.
- [ ] `npx cdk diff CareerVpCrudDev -c p26_rehome_features=true` is now clean (only tag/hash churn).
- [ ] Parent stack live resource count < 400.

---

## 5. Rollback lever (requirements + invocation)

**Requirements to be able to roll back (ensure these BEFORE apply):**
- The refactor was run **with a mapping** (auto-computed or `--override-file`) — `--revert` is only
  valid when a mapping file was provided. If you rely on the auto-computed mapping, save the
  effective mapping from the run so `--revert` can consume it.
- Re-homed stateful-adjacent resources (SQS + their KMS keys) are `RETAIN` in dev (`567320d`) —
  verify still in effect.
- Parent **P-27 termination protection** + per-resource stack policy in force.

**To roll back:**
- **Before execute:** nothing deployed — simply do not approve APPLY (or `git` revert the
  flag-gated code so a future deploy keeps resources in the parent).
- **After execute (move went wrong / smoke red):**
  ```
  cd infra
  npx cdk refactor CareerVpCrudDev --unstable=refactor --revert -c p26_rehome_features=true
  ```
  Then re-run P-30 smoke to confirm the reverted topology still serves traffic.
- **Safety net:** RestApi + Cognito are never in the mapping, so even a botched refactor cannot drop
  the live users' backend or accounts; stateful tables/buckets are never moved.

---

## 6. After success — update recordkeeping

- Set `wave-1-status.md` row **1.3d** to Done (refactor executed; smoke green; parent < 400) with
  the run URL + smoke evidence path.
- Unblock row **1.4 / P-09** (parent now has headroom).
- Drift-check the executed change against P-26's `project-scope-lock.yaml` entry (Wave-0 guardrail +
  `wave_1_carryover`); flag any mismatch in plain language before technical detail; do not mark done
  if RestApi/Cognito appeared in the mapping or the parent stayed ≥ 400.

---

## Artifacts

| Artifact | Path |
|---|---|
| CI workflow | `.github/workflows/p26-refactor.yml` |
| Gate validator | `infra/scripts/p26_refactor_gate.py` |
| Override candidate (fallback) | `docs/evidence/p26-job1-refactor-override.json` |
| Prep + proof | `docs/evidence/p26-job1-refactor-prep-20260718.md` |
| Logical-id map (source of truth = tests) | `infra/careervp/rehome_map.py` |
