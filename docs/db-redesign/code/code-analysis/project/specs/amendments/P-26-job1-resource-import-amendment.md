# Amendment Proposal — P-26 Job 1 decomposition mechanism

> Emitted per scope-lock **§0.3** ("Deviation & amendment handling"). This is a
> **proposal awaiting human validation** — it does **not** edit the spec, weaken
> a test, or touch `project-scope-lock.{md,yaml}`. The Job-1 decomposition is
> **STOPPED at the clause** until a human decides.

| Field | Value |
|---|---|
| **clause_id** | `P-26` (Job 1 — "decompose AROUND the RestApi") |
| **tag** | `TARGET` (method/mechanism of the movable-resource decomposition; the two P-26 **IMMUTABLE** invariants are untouched — see below) |
| **semver level** | **minor** (changes *how* Job 1 executes and its risk class; preserves clause intent + every invariant + every test) |
| **affected specs** | `specs/P-26-blue-green-api-spec.md` — Job 1 §"Fix (GREEN)", Job-1 §"Verify", RED test `test_rest_api_logical_id_and_url_unchanged_after_decompose`, AC-P26-1, AC-P26-2, Done-when |
| **affected tests** | `src/backend/tests/infrastructure/test_p26_blue_green_api.py` (guard tests already landed; no change needed — they remain the safety net for the amended mechanism) |
| **requires adversarial review?** | **No.** No IMMUTABLE invariant, locked decision, or frontend-contract item is amended. The RestApi-never-moves and Cognito-never-moves laws are strengthened, not weakened. |

---

## What changed (the live-truth contradiction)

The spec's Job 1 defines the decomposition as **"the minimal GREEN CDK change"**
that moves feature Lambdas/alarms/non-stateful resources into per-feature nested
stacks as an **additive, reversible** operation, and its Verify expects a
`cdk diff` showing **"the moved resources as create-in-nested / delete-from-parent
for non-stateful resources only."** The §"Sequencing law" classes Job 1 as
"additive/reversible and land[s] first."

**Live truth contradicts that mechanism.** Every movable resource in the parent
carries an **explicit physical name** and is **already deployed** in
`CareerVpCrudDev`, so a plain cross-stack move via a normal `cdk deploy` /
change set is a CloudFormation **"resource already exists"** CREATE failure — not
a clean, executable `create-in-nested / delete-from-parent`.

### Evidence (grounded, at HEAD `28411d4`)

1. **The prior engineer already documented this exact failure mode in-code** —
   `infra/careervp/api_construct.py:2105-2114`:
   > *"…these resources carry explicit physical names … and are already deployed
   > in CareerVpCrudDev, so relocating them into a nested stack makes
   > CloudFormation try to CREATE new resources under the same physical names — a
   > 'resource already exists' failure. Only the Monitoring nested stack
   > (auto-named alarms/dashboards) is split out for the 500-resource ceiling;
   > explicitly-named resources must stay put absent a CloudFormation
   > resource-import migration."*

2. **Every candidate feature Lambda + log group is explicitly named.** e.g.
   `function_name=self.naming.lambda_name("cv-upload-worker")` and
   `log_group_name=f"/aws/lambda/{function_name}"`
   (`api_construct.py:1456-1471`, and identically for `vpr-worker`,
   `cv-tailor-worker`, `cover-letter-worker`, `interview-prep-worker`,
   `vpr-dlq-handler`, the artifact-chain handlers, etc.).

3. **The workers are export-locked by the parent artifact-chain state machine.**
   The state machine grants `grant_start_execution` / `grant_task_response` to the
   submit + worker Lambdas (`api_construct.py:2156-2193`). Moving a worker to a
   nested stack compiles those grants to `Export`/`Fn::ImportValue` locks —
   which "cannot be removed while consumed" (spec §"Cross-stack refs"), the same
   class of lock the spec only anticipates for the **Job-2 RETIRE**, not Job 1.

4. **The one clean split was already harvested.** Only auto-named
   alarms/dashboards were nested (`MonitoringNestedStack`, 27 resources); there is
   no remaining large auto-named, unlocked subtree to move by a plain change set.

### The resource-count check itself is NOT contradicted

Live per-template synth (offline `cdk synth --all`, HEAD `28411d4`) confirms the
spec's `current_state: root_415_of_500_4_nested` within tolerance — **no** count
contradiction, and **no** template near the 500 limit:

| Template | Resources |
|---|---|
| `CareerVpCrudProd` (parent) | **421** ← tightest |
| `CareerVpCrudDev` (parent) | **410** (409 via in-test env-synth) |
| `CareerVpCrudRtoEuw1…` (parent) | 407 |
| Dev Monitoring nested | 27 |
| Dev AiAssist / ErrorReport nested | 7 / 7 |
| Dev CompanyResearch nested | 4 |

(FYI for the human: **prod is the tightest at 421/500**, ~79 headroom — worth
noting when the additive waves P-09/P-14/P-17/P-21 land.)

## Why this is a STOP, not a silent deviation

Proceeding would force one of two forbidden moves:

- **(a)** Ship a nested-stack move that synth-reduces the count but that we *know*
  fails on deploy ("resource already exists") — handing the human a broken change
  set. Dishonest and unsafe.
- **(b)** Silently switch to a CloudFormation **resource-import** (`cdk refactor`)
  migration — a materially different, human-gated, **non-additive/non-plainly-
  reversible** operation the spec does not describe or sanction for Job 1. The
  step brief forbids this: *"do not guess."*

Per §0.3 the correct action is to **STOP at the clause and emit this proposal.**

## Proposed resolution (for human decision)

**Option A — recommended.** Redefine Job 1's mechanism as a **human-gated
CloudFormation resource-import / `cdk refactor` migration** (a P-28-class
*prepared-but-not-executed* change), NOT an automation-executed additive change:

- Because the movable Lambdas/log-groups/queues carry explicit physical names and
  are already deployed, the only safe relocation is CFN stack refactoring
  (resource-import), which **preserves the physical resource** (no delete/create,
  no "already exists", no ARN/URL/data change) while re-homing its logical id into
  a nested stack. This is exactly the path the pre-existing
  `cdk.out/*MonitoringNestedStack*.refactor*.template.json` artifacts already
  evidence.
- Automation **prepares** the refactor mapping + templates and emits the P-28
  `DescribeChangeSet` Replacement report (auto-fail already wired,
  `scripts/ci/changeset_replacement_report.py`); a **human** executes the
  `cdk refactor` / import. The artifact-chain **export locks**
  (`api_construct.py:2156-2193`) must be broken/re-imported in the same
  transaction.
- Update the Job-1 Verify wording: `cdk diff` will show **import/refactor
  (physical-id preserved)**, not `create-in-nested / delete-from-parent`.

**Option B.** Narrow Job 1 to auto-named resources only → negligible relief
(Monitoring already nested); does not unblock the additive waves. *Rejected as
insufficient.*

**Option C.** Add per-feature nested stacks for **future** feature Lambdas only,
and migrate the existing explicitly-named ones opportunistically via Option-A
resource-import as each feature is next touched. Splits the risk over time.

## Invariants preserved (unchanged by any option)

- **IMMUTABLE:** the `service-rest-api` RestApi is never moved in place or across
  stacks (logical id `CareerVpCrudDevCrudservicerestapi5E02FD49`, invoke URL
  byte-stable). Locked by `test_rest_api_logical_id_unchanged`.
- **IMMUTABLE:** the Cognito `AWS::Cognito::UserPool` is never moved/replaced.
  Locked by `test_cognito_user_pool_present_and_singular`.
- No single template may reach 500. Locked by
  `test_no_single_template_reaches_cfn_limit`.

## Status of the rest of step 0.65 (unblocked, delivered alongside this proposal)

- **Job 0 (custom-domain seam):** already live in CDK + O-9 resolved (0.64b,
  commit `425e0bd`); guarded by `test_custom_domain_is_regional_and_maps_to_rest_api`.
  O-8 env-scoping (`api.{env}` vs hardcoded `dev`) folded into this amendment's
  follow-up.
- **Job 2 (blue/green NEW RestApi):** **NOT triggered.** Job 1 is the CFN-limit
  relief; a NEW RestApi is only stood up "if API-GW resource count must still
  shrink after Job 1." With every parent < 500 and Job 1 pending the mechanism
  decision, no new RestApi is created. The human-only FLIP + RETIRE machinery
  (P-27 stack policy, P-28 create/execute split + Replacement auto-fail) already
  exists from step 0.55 and is guarded by
  `test_p28_report_auto_fails_on_protected_replacement` /
  `test_p28_report_passes_on_basepath_only_flip` /
  `test_flip_and_retire_are_not_automation_executable`.

## Prepared change sets awaiting human ExecuteChangeSet (P-28)

**None.** No deploy artifact is handed off. Job 1's migration is blocked pending
this amendment's resolution; Job 2 is not triggered.

---

## DECISION — human validation (2026-07-15)

**Option A ACCEPTED** by the human owner (Yitzchak Meirovich) per §0.3. The
§0.3 STOP on P-26 Job 1 is **lifted**.

- **Mechanism (redefined):** Job 1's decomposition is a **human-gated
  CloudFormation resource-import / `cdk refactor` migration** (a P-28-class
  *prepared-but-not-executed* change), NOT an automation-executed additive
  change set. The movable Lambdas/log-groups/queues carry explicit physical
  names and are already deployed, so resource-import (physical-id preserved,
  no delete/create, no "already exists") is the only safe relocation. The
  artifact-chain **export locks** (`api_construct.py:2156-2193`) must be
  broken/re-imported in the same transaction.
- **Semver:** MINOR (per the proposal — clause intent + every IMMUTABLE
  invariant + every test preserved). No adversarial review required (no
  IMMUTABLE invariant, locked decision, or frontend-contract item weakened;
  the RestApi-never-moves and Cognito-never-moves laws are strengthened).
- **Job-1 Verify wording (superseded):** `cdk diff` will show
  **import/refactor (physical-id preserved)**, not `create-in-nested /
  delete-from-parent`. This wording change is authored into
  `specs/P-26-blue-green-api-spec.md` at **step 0.65 (P-26) IMPLEMENT time** —
  step 0.65 remains `not_started`; accepting Option A does not itself execute
  the migration.
- **Guard tests unchanged:** `src/backend/tests/infrastructure/test_p26_blue_green_api.py`
  remains the fail-closed safety net for the amended mechanism (RestApi logical
  id / invoke URL, per-template CFN headroom, Cognito pool, P-28 replacement
  auto-fail). No test weakened.
- **Options B/C:** not adopted (B insufficient; C available opportunistically
  as each explicitly-named feature Lambda is next touched, executed via the
  Option-A resource-import path).
