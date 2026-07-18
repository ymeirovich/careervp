# P-26 Job 1 — Resource-Import Refactor: PREPARED (refresh of 2026-07-17 prep)

- **Date (UTC):** 2026-07-18
- **Supersedes:** `p26-job1-refactor-prep-20260717T182221Z.md` (its 410→251 counts are stale).
- **Branch:** db-redesign · **Account/region:** 788159322332 / us-east-1 (dev)
- **Mechanism:** human-gated CloudFormation resource-import (`cdk refactor`), physical ids
  preserved, logical ids preserved byte-for-byte. **Nothing executed against AWS this pass**
  (only read-only `cdk synth`, `cdk diff`, and `cdk refactor --dry-run`).
- **CDK CLI actually installed:** 2.1100.3 (the Jul-17 doc/step brief assumed 2.1105.0;
  `cdk refactor --unstable=refactor` is present and works in 2.1100.3).

## Corrected counts (verified this pass)

| Metric | Jul-17 doc | **Verified 2026-07-18** |
|---|---|---|
| Parent `CareerVpCrudDev`, flag OFF | 410 | **489** |
| Parent `CareerVpCrudDev`, flag ON (re-homed) | 251 | **295** (< 400 ✅) |
| `CrudFeatures` nested, flag ON | — | **195** resources |
| Named byte-stable imports | 77 | **76** + 1 dormant P-24 authorizer (additive) |
| Largest template | — | 295 (< 500 ✅ — Job 2 NOT triggered) |

The parent grew ~79 since Jul-17 because P-23 canary (19 CodeDeploy DeploymentGroups + 19
aliases + 40 alarms), P-11 WAF (all-env), and P-06 IAM all deployed in the interim.

## Deploy-state truth (this is what the earlier recordkeeping got wrong)

Live dev **is current with HEAD's substantive infrastructure.** A flag-OFF `cdk diff` of HEAD
against live `CareerVpCrudDev` shows **zero substantive change**: no P-06 JWT/SSM env-var diff, no
P-08/P-10 CORS diff, no P-11 WAF-rule diff. The entire diff is:
- **owner-tag drift**: live `owner=runner` (CI deploy) vs a local synth `owner=yitzchak`
  (`utils.get_username()` = `getpass.getuser()`, stamped in `service_stack.py`);
- **Lambda code asset-hash churn** (local re-bundle) + CDK metadata;
- 20 hash-rotated `Lambda::Version` + 1 `ApiGateway::Deployment` (inherent churn).

**Zero `[!]` stateful replacement. No DynamoDB table / S3 bucket / Cognito pool destroyed,
replaced, or substantively changed.** => P-06/P-08/P-10/P-11/P-23 are DEPLOYED.

## The flag

`p26_rehome_features` is a **CDK context flag** (`api_construct.py`, default OFF). OFF → resources
stay in the parent, `CrudFeatures` synthesizes EMPTY (staged live by `7fe3c4d`). ON
(`-c p26_rehome_features=true`) → the 76 named resources populate `CrudFeatures` with byte-stable
logical ids and `_rehome_feature_logical_ids()` pins them. Nothing was toggled back; re-homing was
always flag-gated and dormant.

## Invariants held (verified this pass — offline)

- **RestApi never moves** — `CareerVpCrudDevCrudservicerestapi5E02FD49` byte-identical in the parent
  OFF and ON; absent from `CrudFeatures`.
- **Cognito never moves** — pool `CareerVpCrudDevCognitoUserPool42C0A4E4` + client
  `...UserPoolClientFD4D0C15` byte-identical in the parent; absent from `CrudFeatures`.
- **76 named resources** leave the parent and enter `CrudFeatures` with identical logical ids;
  their 121 auxiliary children (Version/Permission/EventInvokeConfig/Policy) move with them.
- **P-24 authorizer stays dormant** — `CareerVpCrudDevCrudApiAuthorizerLambda` absent from every
  template (latent, not deployed; additive CREATE only if ever enabled).
- Gate `infra/scripts/p26_refactor_gate.py --synth-on cdk.out.on` → **PASS** (G1 parent 295<400,
  G2 no template≥500, G3 immutables, G4 76 byte-stable, G6 P-24 dormant).

## Tests (green this pass)

| Check | Result |
|---|---|
| `src/backend` p26/p24/identity_surrogate | 21 passed |
| `infra` p26/nested_split/artifact_chain | 19 passed |
| gate script ruff + mypy --strict | clean |

## Why `cdk refactor --dry-run` is not auto-clean from a laptop

`cdk refactor` forbids add/remove/**update** and matches resources by content digest. The owner-tag
(`runner`↔`yitzchak`) + Lambda asset-hash drift between a local synth and the CI-deployed live stack
makes even non-moving resources (Cognito, tables) look "updated," so it aborts with *"A refactor
operation cannot add, remove or update resources."* This is a run-from-the-wrong-context artifact,
NOT undeployed features and NOT a DELETE+CREATE. Fix: run it where synth == live for non-movers.

## How to run it (see the handoff runbook for the full gated procedure)

`docs/db-redesign/code/code-analysis/project/runbooks/p26-job1-refactor-handoff.md` +
`.github/workflows/p26-refactor.yml` (plan → human gate → apply). Kickoff, in short:
1. Ensure live is HEAD deployed **from CI** (owner=runner). If unsure, redeploy HEAD via
   `deploy.yml` (workflow_dispatch) first.
2. Run `p26-refactor.yml` with `mode=plan` → the gate must be GREEN.
3. Approve `mode=apply` (env `deploy-dev` reviewer; `confirm_stack=CareerVpCrudDev`).
4. P-30 smoke must stay 4/4 green through https://api.dev.careervp.com.

Override-file (fallback only; prefer the auto-computed mapping):
`docs/evidence/p26-job1-refactor-override.json` (76 mappings; destination nested-stack token
`CareerVpCrudDevCareerVpCrudDevCrudCrudFeaturesCEE268DE` — CONFIRM against the dry-run output).

## Rollback lever

- **Before execute:** nothing deployed — don't approve apply; or `git` revert the flag-gated code.
- **After execute:** `cdk refactor "$STACK_NAME" --unstable=refactor --revert` (valid only when a
  mapping/override file was provided) reverses the move.
- **Safety net:** re-homed stateful-adjacent resources are `RETAIN` in dev (`567320d`); RestApi +
  Cognito are never in the mapping, so a botched refactor cannot drop the live users' backend or
  accounts. Parent P-27 termination protection + per-resource stack policy remain in force.
