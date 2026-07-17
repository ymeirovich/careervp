# P-26 Job 1 — Resource-Import Refactor: PREPARED (not executed)

- **Date (UTC):** 2026-07-17T18:22:21Z
- **Branch:** db-redesign
- **Account / region:** 788159322332 / us-east-1 (dev)
- **Amendment:** `P-26-job1-resource-import-amendment.md` — Option A ACCEPTED (2026-07-15)
- **Mechanism:** human-gated CloudFormation resource-import (`cdk refactor`), physical ids preserved, logical ids preserved byte-for-byte. **Nothing executed against AWS.**

## What this change does

Decompose AROUND the RestApi (Job 1): move every explicitly-named, non-stateful
feature resource out of the near-limit `CareerVpCrudDev` parent template into a
single new nested stack, `CrudFeaturesNestedStack`, leaving the RestApi, the
Cognito user pool, and every DynamoDB table / S3 bucket exactly where they are.

- **Parent template: 410 → 251 resources** (well under the < 400 headroom target;
  no template ≥ 500 — Job 2 NOT triggered).
- **77 explicitly-named resources re-homed** (verified: absent from parent,
  present in `CrudFeatures`, physical name preserved, logical id byte-identical):
  - 30 `AWS::Lambda::Function`
  - 29 `AWS::Logs::LogGroup`
  - 17 `AWS::SQS::Queue`
  - 1 `AWS::StepFunctions::StateMachine` (`careervp-artifact-chain-statemachine-dev`)
- The shared Lambda role (`careervp-role-lambda-core-dev`,
  `CareerVpCrudDevCrudServiceRoleArn305AAC1B`) is re-homed with the Lambdas that
  assume it (logical id preserved), so its default policy's grants stay acyclic.

The authoritative physical-name → logical-id map is
[infra/careervp/rehome_map.py](../../infra/careervp/rehome_map.py) (generated from
the RED-test contract). The re-home is applied by
[infra/careervp/crud_features_nested_stack.py](../../infra/careervp/crud_features_nested_stack.py)
+ `ApiConstruct._rehome_feature_logical_ids()`.

## Export locks broken / re-imported in the same transaction

The artifact-chain state machine granted `states:StartExecution` /
`states:SendTaskSuccess|Failure|Heartbeat` to the submit + worker Lambdas
(`api_construct.py:2156-2193`). Under the old topology those grants were in-parent;
naively splitting them would compile to `Export`/`Fn::ImportValue` locks that
"cannot be removed while consumed."

**Resolution:** the state machine AND all nine grant targets (vpr-submit,
cover-letter-api, interview-prep-api, cv-tailor, gap-api, cr-worker, vpr-sqs-worker,
cover-letter-worker, interview-prep-worker) are re-homed into the **same** nested
stack, so every grant is now an **intra-stack** edge — no cross-stack Export/Import
lock is created at all. Verified: `states:StartExecution`, `states:SendTaskSuccess`,
`states:SendTaskFailure` all resolve inside the `CrudFeatures` template.

The one inline reference that would have formed a parent↔nested cycle — the shared
role's inline `vpr_jobs_queue` grant — was moved to the role's separate default
policy (`ApiConstruct._grant_vpr_jobs_queue_access()`).

## Invariants held (verified)

- **RestApi never moved** — logical id `CareerVpCrudDevCrudservicerestapi5E02FD49`
  byte-stable in the parent (12 guard tests green).
- **Cognito user pool never moved/replaced** (guard tests green).
- **Zero stateful movement:** no DynamoDB table, S3 bucket, or KMS key relocated;
  merged stateful counts unchanged (11 GlobalTables, 6 buckets, 5 KMS, 1 pool, 17
  SQS — the SQS move is a logical-id-preserving import, no REPLACE).
- **No dependency cycle;** `cdk synth --all` exits 0.

## P-24 authorizer Lambda (accounted for)

`careervp-api-authorizer-lambda-dev` (`CareerVpCrudDevCrudApiAuthorizerLambda`) is
the dormant P-24 custom authorizer. Its builder existed but was never called, and
it is **not deployed live** (verified: `aws lambda get-function` →
ResourceNotFoundException). It is now instantiated (dormant — NOT attached to the
RestApi; Cognito remains the authorizer) inside `CrudFeatures`. On the human
deploy it is therefore an **additive CREATE**, not a resource-import; it changes no
request handling.

## Verification results

| Check | Result |
|---|---|
| Prompt B RED tests (`test_p26_job1_resource_import_outcomes.py`) | 5/5 GREEN (unedited) |
| Original guard tests (`test_p26_blue_green_api.py`) | 12/12 GREEN |
| `infra/tests/infrastructure` | 131 passed |
| `src/backend/tests/infrastructure` | 32 passed |
| `ruff format` + `ruff check` + `mypy --strict` | clean |
| `cdk synth --all` | exit 0, RestApi id byte-stable, parent 251 |

## cdk refactor dry-run — honest status (NOT a clean auto-mapping)

`cd infra && cdk refactor --unstable=refactor --dry-run` does **not** auto-produce
a clean IMPORT mapping. Its content-digest matcher cannot pair a 77-resource
cascade move (re-homing the shared role + introducing cross-stack references
ripples through many resource digests), so it lists resources as unmatched and
exits with *"A refactor operation cannot add, remove or update resources. Only
resource moves and renames are allowed."* This is the exact case the amendment/
step brief anticipated for `--override-file`, **not** a P-26 defect and **not** a
DELETE+CREATE of any named resource (logical ids + physical names are preserved,
so the deploy-time op is an IMPORT). Per the brief's "do not fake a mapping," no
green dry-run is claimed here.

**Human P-28 step:** finalize the `--override-file` and run the dry-run against the
live account. A draft (source side `CareerVpCrudDev.<logicalId>` + destination
logical ids authoritative; the `CrudFeatures` nested-stack destination name must be
confirmed and the auxiliary Permission/EventInvokeConfig/Policy resources
reconciled) is at
[p26-job1-refactor-override-DRAFT.json](./p26-job1-refactor-override-DRAFT.json).
Override-file format (aws-cdk v2.1105): `{"environments":[{"account","region",
"resources":{"<srcStack>.<srcLogicalId>":"<destStack>.<destLogicalId>"}}]}`.

## Rollback lever

- **Before execution:** nothing is deployed; the change is code-only. Revert the
  commit.
- **During/after the human `cdk refactor` execute:** `cdk refactor --revert`
  (valid only when a mapping file was provided) reverses the move.
- **Safety net:** the re-homed stateful-adjacent resources (SQS KMS keys, buckets,
  tables) are `RETAIN` in dev; the RestApi and Cognito pool are never in the
  mapping, so a botched refactor cannot drop the 908 live users' backend or
  accounts. The parent's P-27 termination protection and the per-resource stack
  policy remain in force.

## Next steps (per step 0.65)

Human executes the refactor (with the finalized override-file) → run P-30 smoke →
Prompt E.
