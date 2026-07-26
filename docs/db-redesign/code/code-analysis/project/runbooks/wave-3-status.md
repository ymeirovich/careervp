# Wave 3 — Status Ledger

**Read this file FIRST before starting any Wave-3 prompt.** `wave-3-prompts.md` describes what
*should* happen; this file describes what *actually* happened, and is what every prompt checks
before starting its own work (see `RUNBOOK-RULES.md`, rules 2–3). Update your own row when you
finish a step or stop on a problem — do not leave this file stale for the next session to trip
over.

Rows are listed in dependency order. Before starting a step, read the row above it (or the rows
it depends on per `wave-3-prompts.md` §2) — if any of them show an open problem, resolve that
first.

---

## ⛔ HARD BARRIER — Wave 3 is authored but NOT yet authorized to RUN

**This ledger and `wave-3-prompts.md` were authored on 2026-07-26 *ahead of* the Wave-2 GATE, by an
explicit human decision to prepare Wave 3 in parallel (authoring is gate-safe: no code, no test, no
deploy crosses the barrier).** Per `redesign-execution-plan.md` — *"Wave gates are hard barriers —
never parallelize across a gate"* — **no Wave-3 prompt below may be executed until the `GATE` row in
[`/Users/yitzchak/Documents/dev/careervp/docs/db-redesign/code/code-analysis/project/runbooks/wave-2-status.md`](./wave-2-status.md)
reads PASSED.** At authoring time it reads `not started`, and the Wave-2 close-out still has open
human-gated items (the AC-P31-1 DLQ live-delivery drill, the P-02 / P-20 devx deploys, and bet
`B-2-3` — the CFN resource ceiling). The first Wave-3 session to run must re-confirm the Wave-2
GATE from git and from that ledger, not from this paragraph.

---

**Deploy target: `CareerVpCrudDevx`** (project-wide since 2026-07-25 — `CareerVpCrudDev` is being
retired). Anything pointed at `api.dev.careervp.com` is talking to the OLD stack; use the raw invoke
URL `https://ymzhvcxod0.execute-api.us-east-1.amazonaws.com/prod/` until the human-only base-path
flip happens. **No Wave-3 work merges to `main`** — the push-to-`main` CI path still targets the old
stack (Wave-2 bet `B-2-4`, item 1, still open).

| Step | Clause(s) | Status (plain English) | Open problem for the next step | Commit | Date |
|---|---|---|---|---|---|
| 3.1-RED | D-H2, D-H3 | not started | — | — | — |
| 3.1-GREEN | D-H2, D-H3 | not started | — | — | — |
| 3.2 | D-H4, P-01 | not started (skeleton — fill in after 3.1-GREEN lands) | — | — | — |
| 3.3 | D-H7 | not started (skeleton — fill in after 3.1-GREEN lands) | — | — | — |
| 3.4 | D-M1, D-M2, D-M3, D-M5, D-M6, D-Q | not started (skeleton — fill in after 3.1-GREEN lands) | — | — | — |
| 3.5 | D-H9 | not started (skeleton — fill in after 3.1-GREEN lands) | — | — | — |
| GATE | — | not started | — | — | — |

---

## Wave-3 bets (rule 9 — SEED list, promote to `ISSUES.md` before the wave runs)

Rule 9 requires every belief a wave rests on to be written down *before* its prompts run, with the
cheapest check that would disprove it and the fallback decided now. The seeds below are a starting
point authored alongside this ledger; **the first session to actually run Wave 3 must promote them
into `/Users/yitzchak/Documents/dev/careervp/docs/db-redesign/code/code-analysis/project/ISSUES.md`
as `B-3-*` and re-read them at the GATE.** They are not yet load-bearing decisions — they are the
questions Wave 3 must answer cheaply before building on the answers.

| Bet | Belief (stated so it could be false) | Cheapest check (rule 9 ladder) | Fallback if false |
|---|---|---|---|
| B-3-1 | The migration-parity harness (built in 3.1) can assert *exact* public-projection equality between a legacy read and the canonical read for every migrated slice, with no benign diffs. | Tier 3 — one minimal moto test: seed one legacy + one canonical record for a single artifact type, run the harness, inspect the diff. | If projections differ for benign reasons (field ordering, internal-only attrs), the harness normalizes against a **documented** internal-field allowlist before asserting — decided now, not improvised per slice. |
| B-3-2 | The swallowed `ValidationException`s D-H3 targets are actually reachable on the request path, not dead defensive `except` blocks. | Tier 1 — grep the DAL/handler `except` sites that convert `ValidationException`→`None`/404; Tier 3 — a moto test forcing a malformed key. | If unreachable, D-H3 ships as a guard-rail + regression test (surface-and-log), not a behavior change; record that it changed nothing live and why. |
| B-3-3 | The "239 legacy CR items" figure D-H9 (3.5) backfills is still accurate at Wave-3 time. | Tier 1 — live count of legacy `users-table` CR items in **devx** before 3.5 starts. | Re-derive the count from live; backfill whatever the live count actually is, and record the delta from 239. |
| B-3-4 | Wave-3's GSI changes (3.4 minimized GSI, retire `userEmail` PK) stay under the CFN resource ceiling and cause zero stateful replacement. Carries `B-2-3` forward. | Tier 4 — `cdk diff` per infra-touching step; assert zero replacement markers on stateful resources. | Sequence the GSI add/remove as separate gated deploys (add new → dual-read → drop old), never a single replacing change. |

---

## Standing notes carried into every step (do not lose these)

- **The two IMMUTABLE laws apply to every row that touches `infra/`:** never move the live API
  (`RestApi`), never move the Cognito user pool. Internal PK/SK/table changes are fine; the API
  Gateway logical id and the Cognito pool logical id stay byte-stable.
- **Frontend §3 identifiers and response shapes may not drift.** D-H2/D-H4/D-M all change *internal*
  keying; none of that is an API change. The executable oracle (Wave-0 step 0.3,
  `/Users/yitzchak/Documents/dev/careervp/docs/db-redesign/code/code-analysis/project/specs/F-frontend-oracle-spec.md`)
  is the contract check — a Wave-3 change that alters a §3 identifier is a rule-5 stop.
- **Migration-parity discipline (v2.0.0/A14) governs 3.2, 3.4, and 3.5:** dual-read until an explicit
  contract phase; every pre-migration `artifact_id` (and CR id) must still resolve via the status
  endpoint post-cutover. The harness 3.1 builds is the instrument that proves this — it is reused by
  3.2/3.4/3.5, not re-invented each time.
- **`CoreRepository` / `TableRegistry` (created by 3.1) is the Wave-3 contention hotspot** — the
  analogue of `api_construct.py` in Wave 2. Every later step extends it. Never run two steps that
  edit it at the same time; see `wave-3-prompts.md` §2 for the serialization order.
- **Deploy target is `CareerVpCrudDevx`; deploys are manual-dispatch only; nothing merges to
  `main`** (Wave-2 `B-2-4` item 1 open). Anything at `api.dev.careervp.com` is the OLD stack.
- Carried in from earlier waves, still open, none of which gate Wave 3: **P-07b** (browser admin
  scope + implicit grant — gates STAGING, has a written stopping condition); **I-05** (AI-assist
  token-metering red test — belongs to the metering clause, do not silence it inside a Wave-3 step);
  **I-06** (login client admin scope). Do not fix these as a side effect of a Wave-3 step.
