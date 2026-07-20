# Amendment Proposal — P-32 cost-anomaly monitor is an AWS account singleton

> Emitted per scope-lock §0.3. This is a proposal awaiting human validation. It
> does not edit either `project-scope-lock` twin, change infrastructure, or
> authorize a deployment. Per §0.3/A3 the contract twins are write-protected
> from agent sessions and must be human-committed.

| Field | Value |
|---|---|
| **clause_id** | `P-32` (Wave 0 budgets + cost-anomaly sub-slice, step 0.56) |
| **tag** | `TARGET`; no IMMUTABLE invariant, locked decision, or frontend-contract item is changed |
| **semver level** | **PATCH** proposed — `2.6.0` → `2.6.1`. See "Semver rationale" below; MINOR is defensible if you read "which environments build it" as scope rather than mechanism. |
| **affected contract twins** | `project-scope-lock.md`, `project-scope-lock.yaml` (both updated together, with a §12 / `change_log` row) |
| **affected code** | `infra/careervp/monitoring.py` — `_build_cost_observability` split into `_build_budget` (all envs) + `_build_cost_anomaly` (owning env only) |
| **affected tests** | `infra/tests/infrastructure/test_p32_budgets_cost_anomaly.py` (+2 tests), `infra/tests/infrastructure/conftest.py` (+`devx_service_stack`, `devx_monitoring_template` fixtures) |
| **affected runbooks** | `runbooks/p32-budgets-cost-anomaly-runbook.md`, `runbooks/wave-1-status.md` row 1.4 |
| **requires adversarial review?** | **No.** The amendment removes an unsatisfiable requirement rather than relaxing a guarantee; the account's observable cost-anomaly coverage is unchanged. Human sign-off is still mandatory. |

## Proposed decision

P-32's cost-anomaly monitor is built **only in the environment that owns the AWS
account's single monitor** (`dev`). Every other environment continues to build
its own **budget** unchanged.

Concretely, in `infra/careervp/monitoring.py`:

```python
_P32_ANOMALY_OWNER_ENVIRONMENT = "dev"

def _build_cost_observability(self, notification_topic, naming) -> None:
    self._build_budget(notification_topic, naming)
    if naming.environment == _P32_ANOMALY_OWNER_ENVIRONMENT:
        self._build_cost_anomaly(notification_topic, naming)
```

The `scratch_settings is None` guard on the call site is unchanged.

## Why the amendment is needed

P-32 as locked at v2.2.1 places `budgets.CfnBudget` **and**
`ce.CfnAnomalyMonitor`/`CfnAnomalySubscription` in one method that every
non-scratch environment invokes. **That requirement is not satisfiable on a
single AWS account.**

AWS Cost Anomaly Detection permits exactly **one `DIMENSIONAL`/`SERVICE`
anomaly monitor per AWS account** — the "watch every AWS service" monitor. The
limit is enforced on the *account*, not on the monitor name, so P-32's correct,
env-scoped naming (`naming.resource_name("cost-obs", "anomaly-monitor")`) does
not avoid the collision. A second environment requesting
`careervp-cost-obs-anomaly-monitor-devx` — a name nobody was using — still
fails, because `careervp-cost-obs-anomaly-monitor-dev` already occupies the
account's single slot.

The budget is **not** affected: budget names are genuinely unique per account,
so each environment can and should keep its own.

| Resource | Uniqueness scope | Can each env have one? |
|---|---|---|
| `AWS::Budgets::Budget` | account, **by name** (env-scoped) | **Yes** |
| `AWS::CE::AnomalyMonitor` (DIMENSIONAL) | account, **name ignored** | **No — one per account** |
| `AWS::CE::AnomalySubscription` | account, by name | Only as many as there are monitors |

One account-wide monitor is also correct on its own merits: N per-environment
monitors would each alert on the same account-level spend, paging a human
multiple times for the same dollars.

## Live evidence captured 2026-07-19 / 2026-07-20

Account `788159322332`, region `us-east-1`.

- `CareerVpCrudDevx` creation failed at **`2026-07-19T20:13:20Z`**. Filtering
  cascade noise (`ResourceStatusReason != 'Resource creation cancelled'`), the
  **entire** failure history is one event:
  > `Embedded stack ...MonitoringNestedStack... was not successfully created: The following resource(s) failed to create: [P32AnomalyMonitor].`

  The other ~50 `FAILED` events are downstream cancellations.
- `aws ce get-anomaly-monitors` returns exactly **one** monitor account-wide:
  `careervp-cost-obs-anomaly-monitor-dev`
  (`arn:aws:ce::788159322332:anomalymonitor/0a6605a2-...`), type `DIMENSIONAL`,
  dimension `SERVICE`.
- `aws budgets describe-budgets` returns only
  `careervp-cost-obs-monthly-budget-dev` — no devx budget collision exists,
  confirming the budget half must **not** be gated.
- Stack lifecycle shows **three** create attempts on 2026-07-19
  (18:03:41Z, 19:53:07Z, 20:02:05Z); the stack is currently
  `ROLLBACK_COMPLETE` with termination protection `true`.
- The P-26 nested-stack scope fix (commit `528d69d`, 19:35Z) **was already in
  place** for the final attempt and worked: `CrudFeaturesNestedStack` reached
  full creation at 20:08:32Z, and no "Unresolved resource dependencies" error
  appears anywhere in the event history. That root cause is closed; this one was
  diagnosed at the same time but never reached code.

## Semver rationale

**PATCH is proposed** because the amendment does not change what P-32 delivers.
The account still has exactly one service-wide cost-anomaly monitor with a $10
absolute-impact threshold and `IMMEDIATE` SNS delivery to the shared P-21
monitoring topic — the same observable outcome the locked clause requires, and
the same resources already deployed and evidenced in
`docs/evidence/p32-budgets-cost-anomaly-live-20260717T141148Z.json`. What
changes is the removal of an implication ("every non-scratch environment builds
its own monitor") that was never achievable on one AWS account and had no
deployed instance. This is the same category as v2.2.1's ownership move: an
implementation-reality correction, human-decided.

**Choose MINOR (`2.7.0`) instead** if you consider "which environments build a
resource" to be scope rather than delivery mechanism. Nothing else in the
proposal changes under that reading.

## Consequence for the P-32 evidence gate

`validate_cost_anomaly_evidence` (`src/backend/scripts/deploy_evidence.py`) is
unchanged and still applies — but it can now only be satisfied from `dev`. If
the post-deploy evidence capture is ever run against a non-`dev` environment it
will correctly find no monitor. The runbook should say so explicitly; that
runbook edit is in scope for this amendment but is not a contract twin.

## What this proposal does NOT do

- Does not change the budget in any environment (amount, thresholds, or SNS routing).
- Does not change the monitor's threshold, frequency, dimension, or owner tag
  (`_P32_ANOMALY_OWNER_TAG = "runner"`, the v1.0/P-23 tag-drift fix, is untouched).
- Does not touch the P-32 remainder (tags / correlation-id / log-retention /
  request validators), still Wave 5.
- Does not re-tier P-32, edit any wave array, or alter `scratch_settings` handling.
- Does not authorize any deployment, cleanup, or cutover.

## Proposed contract edits (for human application)

**1. `project-scope-lock.yaml` line 5** — `version: 2.6.0` → `version: 2.6.1`

**2. `project-scope-lock.yaml` clause `P-32` (line 110)** — append to the existing `note:`:

```
 v2.6.1/A16: the Wave-0 cost-anomaly monitor is built ONLY in the account's owning environment (dev; infra/careervp/monitoring.py _P32_ANOMALY_OWNER_ENVIRONMENT). AWS permits one DIMENSIONAL/SERVICE anomaly monitor per ACCOUNT and enforces it on the account rather than the monitor name, so P-32's correct env-scoped naming does not avoid the collision -- CareerVpCrudDevx failed create at 2026-07-19T20:13:20Z with P32AnomalyMonitor AlreadyExists. The per-environment budget is unaffected and still built everywhere (_build_budget). Post-deploy evidence capture is therefore dev-only.
```

**3. `project-scope-lock.yaml` `change_log`** — append:

```yaml
  - {version: 2.6.1, date: "2026-07-20", change: "PATCH (human-decided, by §0.3; implementation-reality correction, no scope/tier change). P-32's Wave-0 cost-anomaly monitor is now built only in the owning environment (dev) instead of every non-scratch environment. AWS Cost Anomaly Detection permits exactly one DIMENSIONAL/SERVICE monitor per AWS ACCOUNT and enforces the limit on the account, not the monitor name -- so the clause as written was unsatisfiable for any second environment despite correct env-scoped naming. Evidence: CareerVpCrudDevx create failed 2026-07-19T20:13:20Z, sole root event 'P32AnomalyMonitor ... AlreadyExists' (~50 further FAILED events were 'Resource creation cancelled' cascade); aws ce get-anomaly-monitors shows one account-wide monitor, careervp-cost-obs-anomaly-monitor-dev. The per-environment AWS::Budgets::Budget is NOT affected (budget names are per-account unique) and is still built in every environment -- _build_cost_observability now splits into _build_budget (all envs) + _build_cost_anomaly (owning env only). Observable outcome for the account is unchanged: one service-wide monitor, $10 absolute-impact threshold, IMMEDIATE SNS to the P-21 topic. Post-deploy evidence capture (validate_cost_anomaly_evidence) is consequently dev-only; runbooks/p32-budgets-cost-anomaly-runbook.md updated to say so. Also landed alongside (no contract impact): scripts/ci/preflight_deploy_check.py, which detects account-singleton and account-global-name collisions across parent AND nested templates before a change set is formed -- the gap that let this reach a real create, since DescribeChangeSet cannot see inside nested TemplateURLs or check account-level uniqueness. P-32 remainder (tags/correlation-id/log-retention/validators) untouched, still Wave 5. No IMMUTABLE invariant reversed; no locked decision reversed; no frontend-contract item broken; no clause re-tiered."}
```

**4. `project-scope-lock.md`** — mirror the version bump, the `P-32` note, and the
§12 change-log row so `check_scope_lock_integrity.py` sees matched twins.

---

**Human sign-off required.** Per §0.3/A3, apply with:

```
Scope-Lock-Approved-By: <name> 2026-07-20
```
