# Wave-1 Parallel-Work Handoff — 2026-07-19

**Why this file exists:** 1.1 (P-04/P-05) cannot start yet — it is hard-gated on a 30-day
refresh-token soak per [`wave-1-status.md`](./wave-1-status.md) row 1.3c, and that soak has not
even started (the PKCE frontend is implemented locally but **not deployed** as of 2026-07-18).
Waiting idle is not required: the tracks below are genuinely independent of the soak and should
run now. Do not start Wave-1 GATE from this file — GATE requires every row 1.0–1.5 "landed," and
1.1 will show "not started" until the soak clears.

**Branch:** `db-redesign` · **Repo:** `/Users/yitzchak/Documents/dev/careervp`

**Two companion files every track below depends on — read both first:**
- [`RUNBOOK-RULES.md`](./RUNBOOK-RULES.md) — the six standing rules (status ledger, prerequisite
  checks, self-check against contract, plain-language flags).
- [`wave-1-status.md`](./wave-1-status.md) — the LIVE status ledger. Read it before touching
  anything below; update your own row when you finish or stop.

---

## Track A — Finish 1.4/P-09: verify the devx deploy, then start P-09

**Status as of hand-off: `CareerVpCrudDevx` deploy is currently IN PROGRESS (human-executed).**
Do not re-run or re-form the change set — it is already executing. Your job starts once it
finishes.

STANDING CHECK — before doing anything else: open `wave-1-status.md`, read row 1.4 in full (it
records the prepared 292-addition, zero-replacement change set and the fact execution was
human-only/out of scope for that step). Confirm the deploy's current state with a real command
(`aws cloudformation describe-stacks --stack-name CareerVpCrudDevx`) — do not assume it finished
just because this handoff says it was "in progress" at write time.

1. Poll/confirm `CareerVpCrudDevx` reaches `CREATE_COMPLETE` (or `UPDATE_COMPLETE`). If it instead
   shows `ROLLBACK_*` or `CREATE_FAILED`, STOP — do not attempt a fix yourself; flag it for human
   review with the stack event that caused the failure.
2. Once complete, run the P-30 4-wire smoke harness (`scripts/smoke_harness.py`) against devx's
   own endpoint (not `api.dev.careervp.com` — devx must not be reachable at the shared domain;
   confirm that too, per the domain-claim guard at `api_construct.py:327`). Expect 4/4 PASS,
   matching the pattern already proven for `CareerVpCrudDev`.
3. Assess devx's live resource count (`aws cloudformation describe-stack-resources` or equivalent)
   against the target the runbook cites for starting P-09 — write the actual number down, don't
   estimate.
4. If smoke is green and the count assessment is done, begin P-09 implementation work per its spec
   (`specs/P-09-*.md` — locate via `project-scope-lock.yaml`). P-09 has no dependency on the P-07
   soak; it was only sequenced after 1.3d/1.4 to avoid editing `api_construct.py` concurrently with
   the devx creation.

OUTPUT REQUIRED:
- Plain-English devx deploy outcome (complete / failed) with the CloudFormation status and
  timestamp.
- P-30 smoke result (4/4 or which wire failed).
- Resource count found, and whether it clears the threshold for P-09.
- If P-09 work was started: same commit-message + scope-lock comparison discipline as every other
  Wave-1 prompt (see `RUNBOOK-RULES.md` blocks).
- Update `wave-1-status.md` row 1.4 (deploy outcome) and open a new row for whatever P-09 work
  begins, or explicitly write "P-09 not started, reason: ___" if the count/smoke didn't clear.

---

## Track B — Start the P-07 soak clock (human-gated; flag, don't execute alone)

This is the single highest-leverage action for unblocking 1.1 sooner: **the 30-day soak has not
begun** because the PKCE frontend is implemented but not deployed (`wave-1-status.md` row 1.3c,
2026-07-18). Every day this stays undeployed pushes 1.1's earliest possible start back by the same
day.

1. Confirm current deploy state of the PKCE frontend change with a real command — do not trust the
   status-ledger prose alone (rule 4). Check the actual frontend deploy pipeline / Amplify build
   for the commit that lands 1.3c's authorization-code + S256 PKCE change.
2. This is a live-traffic auth change (implicit + code flow coexist, MFA optional with TOTP grace)
   — deployment itself is a human decision, not something to trigger unilaterally. Prepare
   everything needed for a human to say go: current CI/test status on that commit, rollback plan
   (if any), and confirmation that implicit + `COGNITO_ADMIN` remain enabled during the soak (per
   spec — they must stay on until the soak completes and the backend auth service replacement for
   password-change/TOTP-enrollment is approved).
3. Once the human deploys, record the deploy timestamp explicitly in `wave-1-status.md` row 1.3c —
   that timestamp is what starts the 30-day clock. Do not let the ledger say "not deployed" once it
   is; do not let it say "deployed" until a live command confirms it.

OUTPUT REQUIRED:
- Plain-English: is the PKCE frontend deployed, yes/no, and if not, exactly what is blocking a
  human decision to deploy it right now.
- If deployed this session: the deploy timestamp, and the date 30 days from it (the earliest 1.1
  can legitimately start).
- Update `wave-1-status.md` row 1.3c with the real state and, once deployed, the soak start/end
  dates.

---

## Track C — Pre-write RED tests for 1.1 (P-04/P-05), do not implement GREEN

Nothing about this needs the soak — only the GREEN implementation (removing the `x-user-id`
fallback, enforcing PKCE-only) is soak-gated. Writing and proving the RED tests now means 1.1 can
start GREEN work the moment the soak clears, instead of losing another session to test-authoring.

STANDING CHECK — read `wave-1-status.md` row 1.1 ("not started") and the P-04/P-05 spec(s) cited
in `project-scope-lock.yaml` before writing anything.

1. Follow the TDD-firewall pattern used elsewhere in this runbook (see `wave-1-prompts.md`'s 1.0
   prompt): derive RED test assertions from the spec's own "RED Tests to Write First" /
   acceptance-criteria section, citing each AC id in the test.
2. Write the tests, run them, paste the FAILURE output (proving they fail against current code —
   the `x-user-id` fallback is still present).
3. Commit **tests only** — no implementation code. A fresh session (after the soak clears) writes
   GREEN.
4. Do NOT touch the soak-gated items: implicit flow and `COGNITO_ADMIN` must stay enabled; do not
   write any test that would only pass after they're removed prematurely.

OUTPUT REQUIRED:
- List of RED tests written, each with its AC citation.
- Pasted RED failure output.
- Commit message (tests-only).
- Update `wave-1-status.md` row 1.1: change from "not started" to "RED tests written, GREEN
  blocked on P-07 soak (see row 1.3c for clock status)."

---

## Guardrails that apply to all three tracks

- IMMUTABLE laws still apply: never move the live RestApi or Cognito user pool (see
  `wave-1-prompts.md` for exact logical ids).
- `api_construct.py` is the wave's contention hotspot — Track A (P-09) may need to touch it. Do
  not run Track A's implementation step concurrently with any other session editing that file.
- None of these tracks may start Wave-1 GATE. GATE requires 1.1 landed; these tracks make 1.1
  landable sooner, they don't substitute for it.
- Per `RUNBOOK-RULES.md` rule 5: if any track's actual output drifts from its instructions or from
  `project-scope-lock.yaml`, stop and flag it in plain English first — do not quietly fix or mark
  done.
