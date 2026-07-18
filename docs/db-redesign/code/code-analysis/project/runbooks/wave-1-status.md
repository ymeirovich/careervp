# Wave 1 — Status Ledger

**Read this file FIRST before starting any Wave-1 prompt.** `wave-1-prompts.md` describes what
*should* happen; this file describes what *actually* happened, and is what every prompt checks
before starting its own work (see `RUNBOOK-RULES.md`, rules 2–3). Update your own row when you
finish a step or stop on a problem — do not leave this file stale for the next session to trip
over.

Rows are listed in dependency order. Before starting a step, read the row above it (or the rows
it depends on per `wave-1-prompts.md` §2) — if any of them show an open problem, resolve that
first.

| Step | Clause(s) | Status (plain English) | Open problem for the next step | Commit | Date |
|---|---|---|---|---|---|
| 1.0 | P-23 | Blocked: the P-23 code and tests are ready, but the required live diff also proposes replacing two existing Cost Explorer anomaly resources. Do not deploy or start the next spine step. | Human must resolve the deployed `owner: runner` versus local `owner: yitzchak` tag drift on `AWS::CE::AnomalyMonitor` and `AWS::CE::AnomalySubscription`, then re-run `cdk diff CareerVpCrudDev` and prove zero stateful replacements. | `81db09b` (RED tests only) | 2026-07-18 |
| 1.3c-gate | P-11 (enable WAF in all envs) | not started | — | — | — |
| 1.3c | P-07, P-11 (rate-rule content) | not started | — | — | — |
| 1.3a | P-08 | not started | — | — | — |
| 1.3b | P-10 | not started | — | — | — |
| 1.2 | P-06 | not started | — | — | — |
| 1.3d | P-26 Job-1 | amendment landed; engineering not started | The v2.5.0 amendment recording Job-1's Wave-1 tracking is committed (`project-scope-lock.yaml`/`.md` both at v2.5.0). The precondition check in Prompt 1.3d is satisfied — normal step preconditions (1.3c-gate landed, spine free) still apply before starting. | `0a0cb81` | 2026-07-18 |
| 1.4 | P-09 | not started | — | — | — |
| 1.1 | P-04, P-05 | not started | — | — | — |
| 1.5 | P-22 | not started | — | — | — |
| GATE | — | not started | — | — | — |

## Standing notes carried into every step (do not lose these)

- The two IMMUTABLE laws (never move the live RestApi or the Cognito user pool) apply to every
  row above that touches `infra/`. See `wave-1-prompts.md` for the exact logical ids.
- `api_construct.py` is edited by most of these steps — never run two steps that touch it at the
  same time. See `wave-1-prompts.md` §2 for the current serialization order.
