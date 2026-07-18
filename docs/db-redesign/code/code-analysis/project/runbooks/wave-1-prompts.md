# Wave 1 — Security/auth launch-blockers (copy-paste runbook)

> **Generated:** 2026-07-17, against `redesign-execution-plan.md` v2.0.0, **after the Wave-0
> GATE passed** (commit `2dfd0b5`). Wave 1 step 1.0's only dependency (0.7) is satisfied, so
> this file is now authorized (a wave's prompt file is only generated once the prior GATE is
> truly verified — the rule Prompt F set in `wave-0-closeout-prompts.md`).
>
> **Branch:** `db-redesign` · **Repo:** `/Users/yitzchak/Documents/dev/careervp`
> **Canonical docs tree:** `docs/db-redesign/code/` (`code1`/`code2` are stale artifacts — ignore)
>
> **Two companion files every prompt below depends on — read both before starting anything:**
> - [`RUNBOOK-RULES.md`](./RUNBOOK-RULES.md) — the six standing rules every prompt in every wave
>   follows (commit message, status ledger, carryover handling, prerequisite checks, self-check
>   against this file and the contract, plain-language flags). This is not optional reading — the
>   two standard blocks it defines are baked into every prompt below.
> - [`wave-1-status.md`](./wave-1-status.md) — the LIVE status ledger. This file (the one you're
>   reading) describes *intent*; that one describes *what actually happened*. Always check it
>   before starting a prompt, and always update it when a prompt finishes or stops.

---

## 0. READ FIRST — the meta-lesson still holds

The Wave-0 status ledger was wrong **three times in a row** for a systematic reason (two infra
test dirs, a scope-diff blind spot, "code exists" mistaken for "done"). That defect class is
fixed, but the discipline it forced is permanent: **every prompt below opens with a
verify-before-acting preamble.** Trust git history, the file on disk, and a command you just
ran — never a status column, a memory, or a prior runbook's "current state" paragraph.

**Proof it still matters — the execution plan is ALREADY stale for Wave 1:**

| Claim (redesign-execution-plan.md, 2026-07-17 status note) | Reality (verified 2026-07-17, this pass) |
|---|---|
| "1.3d / P-26 Job-1: the whole migration, genuinely not started. Parent 411." | **PARTIALLY DONE.** Commit `dd33025` re-homed **77 named feature resources** into `CrudFeaturesNestedStack` (Job-1 resource-import **PREPARED**). Commit `7fe3c4d` deployed `CareerVpCrudDev` with `CrudFeatures` staged as an **empty nested stack first**, and ran **P-30 smoke 4/4 green** against the **live custom domain** `https://api.dev.careervp.com`. So the *repoint precondition* (O-9 / dead DNS) is **resolved**, and the count-relief is *prepared*, not *unstarted*. |
| "api.dev.careervp.com DNS is dead (LM-1)." | **RESOLVED.** P-30 smoke in `7fe3c4d` passed *through* `https://api.dev.careervp.com` — the custom domain is live and serving. |
| "P-24 authorizer may be latent/uninstantiated." | `7fe3c4d` explicitly **restored P-24 to dormant-by-design** by removing an unintended instantiation. Re-verify it stayed dormant after every api_construct.py edit this wave. |

Current offline synth (this pass) reports the **parent `CareerVpCrudDev` at 412 resources** with
**no `CrudFeaturesNestedStack` template present in `cdk.out`** — i.e. the re-homing that landed in
`dd33025` is *not reflected in the working-tree synth*. Whether HEAD toggled it back to the empty
staged form, or `cdk.out` is simply stale, is exactly the kind of thing **1.3d's prompt must
resolve by running `cdk synth` + `cdk diff` against live**, not by trusting this paragraph. Do not
assume — verify.

### 0.1 — Validated against `project-scope-lock.yaml` v2.4.0 (2026-07-18 pass) — two findings

**Finding 1 (process, flag to human before running 1.3d as "Wave 1"): P-26 is a Wave-0 clause in
the lock file, not Wave-1.** `project-scope-lock.yaml:173` (`wave_0_guardrails`) lists `P-26`
explicitly, and separately embeds `cfn_headroom_nested_stacks` inside `ordered_gates`
(`:170`, pulled into `wave_0_guardrails` via `:173`). `wave_1_security` (`:175`) is the exact list
`[P-23, P-04, P-05, P-06, P-07, P-08, P-09, P-10, P-11, P-22]` — **P-26 is absent from it.** The
invariant list itself encodes the ceiling as IMMUTABLE:
`stateful_RETAIN_deletion_protection_no_live_pk_sk_change_max_400_cfn` (`:72`) — "max 400" is not
a soft target there, it's an architectural invariant. Corroborating this,
`test_p26_blue_green_api.py`'s own `PARENT_HEADROOM_TARGET` check is explicitly **warn-only**
*"until the Job-1 resource-import decomposition lands"* — i.e. the test suite treats Job-1 as the
precondition for the 400-ceiling to become a hard gate at all.

`redesign-execution-plan.md`'s 2026-07-17 status note unilaterally declared step 0.65 **"DEFERRED
TO WAVE 1"** and added a new Wave-1 table row (1.3d) — and the "Wave 0 GATE PASSED" commit
(`2dfd0b5`) let Wave 0 close with 0.65 in that deferred state. **Neither move has a corresponding
entry in `project-scope-lock.yaml`'s `change_log`** (last entry is `v2.4.0`, 2026-07-12 — five days
before the Wave-0 GATE commit) — `wave_0_guardrails` and `wave_1_security` are both unchanged.
Per the lock file's own `amendment_protocol.deviation_loop` (`:228-233`): *"stop at clause, never
silently deviate → emit amendment proposal → human validates and confirms → update both twins
same commit + changelog + version bump."* That never happened here. This is exactly the class of
silent drift `project-scope-lock.yaml` exists to catch — **`redesign-execution-plan.md` is not even
in the document's own `authority_hierarchy`** (`:12-18`); it's an operational runbook, not a
contract amendment, and cannot unilaterally move a clause across a wave boundary.

**This does not mean Prompt 1.3d is engineering-wrong** — sequencing P-26 Job-1 before P-09/P-14/
P-17/P-21 is exactly what the P-26 clause note itself says (`"MUST precede P-09/P-14/P-17/P-21"`,
`:104`), and finishing it before Wave-1's additive work (P-23 aliases, P-09 roles, etc.) is sound
regardless of which wave number it's filed under. **It means the paperwork was missing.**

**Status 2026-07-18 (human approved the fix):** the amendment has been **drafted and edited** into
both `project-scope-lock.yaml` and `project-scope-lock.md` — `v2.5.0`, a new `change_log` row on
both files, and a `wave_1_carryover` note on the P-26 backlog entry recording that Job-1's
execution is tracked as this file's step 1.3d while P-26 the clause stays a Wave-0 guardrail
clause (nothing moved wave, nothing re-tiered). **These edits are in the working tree but not yet
committed** — the contract's own self-protection rule requires a human-executed commit carrying a
`Scope-Lock-Approved-By:` trailer, which an agent session cannot supply on the human's behalf.
**Before starting Prompt 1.3d, confirm the commit actually landed** (`git log -1 --
project-scope-lock.yaml` should show version 2.5.0). `wave-1-status.md`'s row for 1.3d tracks
this — check it first.

**Finding 2 (correctness, fixed below): P-11's "all envs" requirement is NOT file-isolated from
`api_construct.py`.** `project-scope-lock.yaml:88` states P-11's `current_state` as
`prod-only_no_rate_rule` — confirmed in code: `api_construct.py:303-311` gates the entire
`WafToApiGatewayConstruct` instantiation behind `if is_production_env:`. WAF currently **does not
exist in dev at all.** Turning it on for dev/staging means editing that exact `api_construct.py`
gate — not merely adding a rate rule inside `waf_construct.py`. The original Prompt 1.3c below
claimed lane P2 (P-07+P-11) was "isolated from `api_construct.py`, safe to run in parallel" — that
claim was **wrong for the P-11 half** and is corrected below: the `is_production_env` gate removal
is now called out as a small, explicitly-serialized spine touch-point (see the updated Prompt 1.3c
and the concurrency diagram in §2).

### The two IMMUTABLE laws (every prompt, no exceptions)

1. **NEVER** move the `service-rest-api` RestApi in place or across stacks. Logical id
   `CareerVpCrudDevCrudservicerestapi5E02FD49` must stay byte-identical. A cross-stack move is a
   CFN delete+create → the `execute-api` id/URL changes → **908 live dev users lose the backend**
   until Amplify rebuilds.
2. **NEVER** move or replace the Cognito `AWS::Cognito::UserPool` → unrecoverable loss of 908
   accounts.

Both are locked by `src/backend/tests/infrastructure/test_p26_blue_green_api.py` (green). **Never
weaken a test to make a step pass** (scope-lock §0.3). Every api_construct.py edit this wave must
end with those guards still green and both logical ids byte-stable.

### Deploy safety is already armed — respect it

- **P-27/P-28 (commit `66159a8`):** stack policies deny `Update:Replace`/`Delete` on RestApi /
  Table / Bucket / UserPool / Stack; `deploy.yml` is split `create-change-set` (automation) →
  `execute-change-set` (requires `environment: human`); `changeset_replacement_report.py`
  auto-fails on `Replacement:True` for protected types. **No agent session executes a deploy.**
  Every prompt that touches CDK ends by handing a prepared change set to the human (P-28).
- **P-12/P-13 (`567320d`) RETAIN + deletion_protection + PITR** are live on the stateful
  resources — the safety net under the 1.3d refactor.

### Verified toolchain / repo facts (use these exact invocations)

- Backend checks: `cd src/backend && uv run ruff format . && uv run ruff check --fix . && uv run mypy careervp --strict`
- Backend unit: `cd src/backend && uv run pytest tests/unit/ -v --tb=short`
- Infra: `cd infra && uv sync && cdk synth` · naming: `python src/backend/scripts/validate_naming.py --path infra --strict`
- **Two infra test dirs (the standing trap):** `infra/tests/infrastructure/` AND
  `src/backend/tests/infrastructure/`. Run BOTH. `scope-diff.py` now scans both (fixed `585a8eb`).
- Coverage: `cd src/backend && make coverage-tests` — enforced_baseline is a **failing gate**;
  ratchet_target is **report-only** until a human-approved §12 bump. Wave-0 exit distances:
  overall 72.22/53.71 (target 80/70), core 72.93/54.95 (85/80), supporting 72.01/50.78 (78/70).
  **Wave 1 must not regress the enforced baseline; every prompt reports its delta.**
- CI has **no ambient AWS region** — reproduce region-sensitive runs with `env -u AWS_DEFAULT_REGION ...`.
- Commit/merge helpers: `scripts/git/safe_commit.sh "<msg>"`, `scripts/git/safe_merge_to_main.sh <branch>`.
  Do **not** use `gh pr merge --delete-branch` in this repo.

### Specs are AUTHORED; Wave 1 is IMPLEMENT

Every Wave-1 clause already has a spec in `specs/` (status `draft`, `format_note: AUTHOR ONLY —
RED tests are inline descriptions; pytest files written later at IMPLEMENT time`). So Wave-1
prompts drive the **IMPLEMENT** phase: turn each spec's "RED Tests to Write First" into failing
tests, then write the minimal GREEN code. The TDD firewall (§3) applies.

**The one exception — P-22 has NO spec.** `specs/` has no `P-22-*` file. Prompt 1.5 therefore
authors a tiny spec first, then implements. Flagged in §1 and §4.

---

## 1. Real remaining Wave-1 work (the honest scope)

| # | Clause(s) | Step | Spec | Real remaining work |
|---|---|---|---|---|
| 1.0 | P-23 | Canary/alias + CodeDeploy rollback + auth/resolver alarms — **FIRST** | `P-23-canary-rollback-spec.md` ✅ | Full implement (no CodeDeploy wiring exists today). |
| 1.3c-gate | P-11 | Remove the `is_production_env` gate so WAF exists in every env | `P-08-P-10-P-11-cors-waf-spec.md` ✅ | Tiny — one `api_construct.py` line. Spine, land early (§0.1 Finding 2). |
| 1.3c | P-07, P-11 | Cognito MFA + SPA `implicit`→auth-code+PKCE + drop `COGNITO_ADMIN` + WAF rate-rule content | `P-07-cognito-hardening-spec.md` ✅ · `P-08-P-10-P-11-cors-waf-spec.md` (P-11) ✅ | Full implement + **FE cutover soak** — must finish+soak **before 1.1**. File-isolated once 1.3c-gate lands. |
| 1.3a | P-08 | CV/generated bucket CORS `*` → locked origins (pilot) | `P-08-P-10-P-11-cors-waf-spec.md` ✅ | Full implement (low blast radius). Feeds 1.3b. |
| 1.3b | P-10 | API-GW CORS `ALL_ORIGINS` → allow-list (keep GatewayResponse `*` exception) | `P-08-P-10-P-11-cors-waf-spec.md` ✅ | Full implement. **Gated on 1.3a + P-30 exact-origin smoke.** |
| 1.2 | P-06 | Secrets → SSM/Secrets-Mgr references + runtime cached fetch | `P-06-secrets-spec.md` ✅ | Full implement. |
| 1.3d | P-26 Job-1 | **Hard blocker.** Finish human-gated `cdk refactor`/resource-import count-relief | `P-26-blue-green-api-spec.md` ✅ + amendment ✅ | **Mostly EXECUTE + verify** — re-home PREPARED (`dd33025`), empty nested stack deployed (`7fe3c4d`). Confirm dry-run is IMPORT-clean, human-execute, prove parent < 400, invariants byte-stable, P-30 green. Blocks P-09/P-14/P-17/P-21. **§0.1 Finding 1: still a Wave-0 clause in the lock file — needs a human amendment before this counts as "Wave 1."** |
| 1.4 | P-09 | One IAM role per Lambda, ARN-scoped, env-suffixed | `P-09-iam-per-function-spec.md` ✅ | Full implement. **Blocked by 1.3d; serialize vs P-26.** |
| 1.1 | P-04, P-05 | Remove `x-user-id` fallback + delete dead `AUTHORIZER_DISABLED` + IDOR owner checks on every authed route | `P-04-P-05-auth-idor-spec.md` ✅ | Full implement. **Gated on 1.0 landed AND 1.3c soaked.** Most correctness-critical step. |
| 1.5 | P-22 | OIDC in `cdk-diff.yml` (kill long-lived keys) | **MISSING** ❌ | **Author the spec first**, then implement (tiny CI change). |

**Only 1.3d is largely execute-and-verify** (and even then, needs its wave-placement amendment
per §0.1). The other eight-and-a-bit are genuine TDD implement cycles.

---

## 2. Execution model — sessions, order, concurrency (the parallelization answer)

### The Wave-1 contention hotspot: `api_construct.py`

**Six-and-a-half of nine clauses edit `infra/careervp/api_construct.py`.** Two Codex agents
editing it on separate branches = a guaranteed merge collision at integration. This single fact
drives the whole concurrency plan. **Corrected per §0.1 Finding 2:** P-11's "all envs" flip touches
`api_construct.py:303-311` too — only its rate-rule *content* lives in `waf_construct.py`.

| Clause | Primary files | Touches `api_construct.py`? |
|---|---|---|
| 1.0 P-23 | `api_construct.py` (aliases/CodeDeploy on API Lambdas) | **YES** |
| 1.2 P-06 | `api_construct.py` (JWT env sites 925-928…), `constants.py` | **YES** |
| 1.3b P-10 | `api_construct.py:356-358` (default CORS) | **YES** |
| 1.3d P-26 Job-1 | `api_construct.py` (re-home Lambdas → nested), `app.py` | **YES** |
| 1.4 P-09 | `api_construct.py:516-821` (roles) + every Lambda def | **YES** |
| 1.1 P-04 | `src/backend/handlers/**` + `api_construct.py:1720` (env delete) | **YES** |
| **1.3c-waf P-11** | `api_construct.py:303-311` (`if is_production_env:` gate) | **YES — one line, tiny** |
| 1.3c-cognito P-07 | `cognito_construct.py`, `src/frontend/**` | no |
| 1.3c-waf-rule P-11 | `waf_construct.py` (rate-rule content) | no |
| **1.3a P-08** | `s3_stack.py`, `api_db_construct.py`, `frontend_stack.py` | **no** |
| **1.5 P-22** | `.github/workflows/cdk-diff.yml` | **no** |

### Three parallel Codex lanes + one serialized spine

```
  PARALLEL (file-isolated — run as 3 concurrent Codex tasks/branches, any time):
    Lane P1:  1.5  P-22          (author tiny spec → implement CI OIDC)
    Lane P2:  1.3c P-07 + waf_construct.py rate-rule content   ── must FINISH + SOAK before 1.1
    Lane P3:  1.3a P-08          (S3 CORS pilot)

  SERIALIZED SPINE (all edit api_construct.py — ONE AT A TIME, each rebased on the prior):
    1.0 P-23  (FIRST — the rollback lever everything leans on)
        ▼
    1.3c-waf P-11's is_production_env gate  (ONE LINE — squeeze in here; do not block on it)
        ▼
    1.3b P-10  (API-GW CORS, after 1.3a P-08 merges + smoke green)
        ▼
    1.3d P-26 Job-1  (human-gated cdk refactor EXECUTE; hard-blocks P-09)
        ▼
    1.4 P-09  (per-fn roles — easiest once Lambdas are re-homed)
        ▼
    1.2 P-06  (secrets)   [flexible: may slot anywhere after 1.0 in the spine]
        ▼
    1.1 P-04/P-05  (auth cleanup + IDOR — LAST; needs 1.0 landed + 1.3c soaked)
```

**Why the P-11 gate-removal is a spine insertion, not part of lane P2:** it's a one-line edit to a
file five other clauses are actively rewriting. Land it early (right after 1.0, before the file
gets busier) as its own tiny commit — the CloudWatch rate-rule tuning (the substantive P-11 work)
stays in lane P2 against `waf_construct.py`, fully parallel. Don't let this one line block lane P2
from starting; land it opportunistically whenever the spine has a free slot.

### Hard orderings (do not reorder)

- **1.0 P-23 first.** P-04's fallback removal is a Lambda change; its revert lever is the P-23
  canary. No canary → no safe P-04.
- **1.3c soak before 1.1.** Stale implicit-flow tokens must not meet newly-strict auth mid-migration
  (v2.0.0/A5). The FE PKCE cutover must be deployed and soaked first.
- **1.3d before 1.4.** P-09 adds one role per Lambda; do it after the Lambdas settle into their
  nested homes. P-09 is hard-blocked on 1.3d per the plan.
- **1.3a before 1.3b.** P-08 is the low-blast-radius CORS pilot; P-10 (API-GW) follows with a
  pre-staged inverse change set + `max-age→60s` first.
- **1.1 last.** It depends on both 1.0 (landed) and 1.3c (soaked).

### Concurrency ceiling

Run **at most 3 parallel Codex lanes** (P1/P2/P3) + **1 active spine session**. Never two
api_construct.py editors at once — including the one-line P-11 gate removal. When a spine step
merges, rebase the next spine step on it before starting — the file will have moved under you.

### Subagents

Same rule as Wave 0: do **not** delegate a whole prompt to a subagent (cold start, summary-only
return, you lose mid-flight course-correction). **One good use:** a read-only recon subagent for
the two big enumeration searches — P-05's *"build the route×handler owner matrix from the live
`route_map`"* and P-09's *"enumerate every Lambda + its exact required ARNs."* Output is a compact
list; never let a subagent write CDK or handlers.

---

## 3. The TDD firewall (why each clause is two sessions)

Requirement: **tests must fail before the spec is implemented, and the author of the tests must
not be the author of the code.** For each clause:

- **Session A (RED):** read the spec's *"RED Tests to Write First"*, write those as real pytest/
  vitest files, derive every assertion from the **spec's AC-### lines** (cite them in comments),
  prove they **FAIL for the right reason** (not an import/collection error), commit tests only.
- **Session B (GREEN):** a **fresh session** reads the failing tests as a contract it did not write
  and may not edit. If a test looks wrong → **STOP + §0.3 amendment**, never a quiet edit.

Each prompt below is written so you can run it as A-then-B in two sessions (recommended for 1.0,
1.1, 1.3d, 1.4 — the high-blast-radius ones) or, for the small isolated clauses (1.3a, 1.5), as a
single session that still writes RED first and pastes the failing output before going GREEN.

---

## Codex model targeting (new family — translate the specs' `gpt-5-codex` labels)

The specs' frontmatter still says `codex: {model: gpt-5-codex, reasoning: ...}` (old naming).
Translate to the current family using the rubric in §5, weighted by each step's risk profile:

| # | Clause | Risk profile | Claude Code | **Codex (target)** | Escalate to |
|---|---|---|---|---|---|
| 1.0 | P-23 | CDK rollback lever, security-adjacent | opus / high | **5.6 Terra, high** | Sol if CodeDeploy alarm wiring fights synth |
| 1.3c-gate | P-11 | one-line api_construct.py gate removal | sonnet / med | **5.4, medium** | — (trivial) |
| 1.3c | P-07/P-11 | auth-flow migration + FE cutover + WAF rate-rule | opus / high¹ | **5.6 Sol, high** | — (already flagship) |
| 1.3a | P-08 | small iac CORS pilot | sonnet / med | **5.4, medium** | 5.5 if origin audit sprawls |
| 1.3b | P-10 | API CORS, 401-visibility blast radius | sonnet / med | **5.6 Terra, high** | Sol if GatewayResponse trap bites |
| 1.2 | P-06 | secrets + ARN-scoped IAM | sonnet / med | **5.5, medium** | Sol if IAM scoping gets subtle |
| 1.3d | P-26 Job-1 | live-user resource-import migration | opus / xhigh | **5.6 Sol, xhigh** | — (flagship, hardest in wave) |
| 1.4 | P-09 | IAM per fn, high blast, rewrites api_construct | opus / high | **5.6 Terra, high** | Sol if least-privilege proofs stall |
| 1.1 | P-04/P-05 | AUTH + IDOR, most correctness-critical | opus / high | **5.6 Sol, high→xhigh** | — (flagship) |
| 1.5 | P-22 | CI OIDC, tiny, no spec | sonnet / med | author **5.5 med** → implement **5.4-mini, low** | — |

¹ **Uplift from the spec's `sonnet/med`.** P-07 crosses the FE↔BE boundary with a dual-flow soak;
the *cutover judgment* wants Opus/Sol. The mechanical WAF-rate-rule and MFA-config portions are
genuinely sonnet-grade — split them if you want to spend the flagship budget only where it earns.

---

## PROMPT 1.0 — P-23 canary/alias + CodeDeploy rollback (FIRST)

**Model/effort:** Claude Code `opus / high` · Codex `GPT-5.6 Terra, high`
**Deps:** 0.7 (satisfied). **Touches:** `api_construct.py` (spine). **Serialize** vs all api_construct.py editors.

```
Implement clause P-23 per specs/P-23-canary-rollback-spec.md. VERIFY BEFORE ACTING — the status
ledger has been wrong repeatedly; confirm current state from git + a command you just ran.

STANDING CHECK (see runbooks/RUNBOOK-RULES.md) — before anything else: open
runbooks/wave-1-status.md. This is the first step in the wave, so there is no prior row to check —
but confirm your OWN dependency (Wave-0 GATE passed / step 0.7) is really true with a live command,
not by trusting this file.

WHY FIRST: P-04's x-user-id fallback removal (step 1.1) is a Lambda change whose ONLY safe revert
lever is a CodeDeploy canary rollback. No canary => no safe auth cleanup. P-23 also provides the
per-outcome auth/resolver alarms P-04/P-24 depend on. It must land before 1.1.

TDD FIREWALL: write the RED tests first (from the spec's "RED Tests to Write First"), prove they
FAIL, commit tests only; a FRESH session writes the GREEN code. If you run it as one session, still
paste the RED failure output before writing any construct code.

RED TESTS (derive assertions from the spec's AC-P23-1/AC-P23-2; cite the AC line in each test):
- test_p23_api_lambdas_have_alias_and_version   (each API Lambda: alias -> published version)
- test_p23_codedeploy_groups_exist_for_api_lambdas   (deployment groups w/ canary config)
- test_p23_rollback_alarms_include_auth_resolver_failure
    (alarms include per-outcome resolver-failure signals — NOT aggregate 401-rate; a mis-resolved
     sub can 401 like token-expiry OR serve wrong-tenant 200s)
- test_p23_revert_runbook_distinguishes_lambda_from_api_gateway
    (runbook: CodeDeploy for Lambda code/config; API-GW authorizer/authorizationType change =
     STAGE-LEVEL API-GW redeploy, NOT a Lambda-alias canary)
Plus the synthetic canary the plan calls for: assert a known `sub` resolves to its expected
`user_id` (a P-24 resolver correctness probe, per step 1.0's text).

GREEN: publish versions + stable aliases for public/API-route Lambdas; add CodeDeploy deployment
groups with canary + rollback alarms; wire the per-outcome auth/resolver-failure alarm; write the
revert runbook naming both levers separately.

GUARDRAILS / STOP:
- IMMUTABLE: RestApi logical id CareerVpCrudDevCrudservicerestapi5E02FD49 byte-stable; Cognito
  UserPool untouched. Do NOT instantiate the P-24 custom authorizer (still dormant-by-design).
- Do NOT deploy. `cdk diff` must show ZERO stateful replacement. Hand the change set to the human.
- If aliasing a Lambda forces a replacement of anything stateful -> STOP, §0.3.

VERIFY:
cd infra && uv sync && cdk synth
cd src/backend && uv run pytest tests/infrastructure -k "p23 or p26" -v   # P-23 green; P-26 guards still green
cd infra && uv run pytest tests/infrastructure -v                         # no infra regressions
cd src/backend && uv run ruff format . && uv run ruff check --fix . && uv run mypy careervp --strict
python src/backend/scripts/validate_naming.py --path infra --strict
cd infra && cdk diff CareerVpCrudDev                                       # zero stateful replacement

SCOPE-LOCK CHECK-IN: python3 docs/db-redesign/code/code-analysis/project/scope-diff.py  # P-23 test_written/implemented
COVERAGE: report line/branch delta vs enforced_baseline (report-only; do not edit the gate).

OUTPUT REQUIRED:
1. A git commit message.
2. RED failure output (pasted) if this session wrote the tests.
3. The two revert levers, stated explicitly (CodeDeploy alias rollback vs API-GW stage redeploy).
4. IF clean: "1.0 P-23 landed. 1.1 (P-04) now has its rollback lever." IF a replacement or
   IMMUTABLE breach surfaced: STOP, §0.3 amendment, do not guess.

ALSO REQUIRED (standing rule for every wave prompt — see runbooks/RUNBOOK-RULES.md):
- Compare what you actually built against (a) this prompt's own instructions and (b) P-23's entry
  in project-scope-lock.yaml. If everything matches, say so in one plain sentence.
- If ANYTHING drifted, STOP — do not fix it yourself. Write one plain-English sentence (what
  should have happened, what actually happened, why it matters), THEN the technical detail, and
  flag it for human review. Do not mark the step done.
- Update runbooks/wave-1-status.md: this step's row gets a plain-English status, the commit,
  today's date, and anything the NEXT step (1.3c-gate) must resolve first (or "none").
```

---

## PROMPT 1.3c-gate — P-11 WAF `is_production_env` removal (spine, tiny, land early)

**Model/effort:** Claude Code `sonnet / medium` · Codex `GPT-5.4, medium`
**Deps:** 1.0 landed (or run right after — negligible risk). **Touches:** `api_construct.py:303-311` ONLY (spine, one line). **Serialize** vs other api_construct.py editors; land it fast to get out of the way.

```
Fix P-11's current_state (project-scope-lock.yaml:88: "prod-only_no_rate_rule"). VERIFY BEFORE
ACTING: confirm api_construct.py:303-311 still gates WafToApiGatewayConstruct behind
`if is_production_env:` before touching it.

STANDING CHECK (see runbooks/RUNBOOK-RULES.md) — before anything else: open
runbooks/wave-1-status.md. Check the row for step 1.0 — if it shows an open problem, resolve that
first. Confirm 1.0 (P-23) is actually landed with a live command (git log), not by trusting this
file.

RED TEST: test_p11_waf_webacl_exists_in_non_production_envs — synth a dev-env stack; assert a
WafToApiGatewayConstruct / CfnWebACL exists (today it does NOT — dev has zero WAF).

GREEN: remove the `is_production_env` gate so WafToApiGatewayConstruct instantiates in every env.
Do NOT touch the WebACL's rule content here — that's Prompt 1.3c's job in waf_construct.py, done
in parallel. This prompt is scoped to the ONE gate condition, nothing else, so it lands fast and
frees the file for the next spine step.

GUARDRAILS / STOP: IMMUTABLE laws hold. cdk diff zero stateful replacement (a new WebACL + 
association in dev/staging are additive, not replacements of anything existing). Do NOT deploy.

VERIFY:
cd infra && uv sync && cdk synth && cdk diff CareerVpCrudDev
cd src/backend && uv run pytest tests/infrastructure -k "p11 or waf" -v

OUTPUT REQUIRED: commit message; RED failure output; "1.3c-gate landed — WAF now instantiates in
all envs. Rate-rule content lands via Prompt 1.3c (parallel, waf_construct.py). Spine free for the
next step."

ALSO REQUIRED (standing rule for every wave prompt — see runbooks/RUNBOOK-RULES.md):
- Compare what you built against this prompt AND P-11's entry in project-scope-lock.yaml; say
  plainly whether they match.
- If anything drifted, STOP, explain in one plain sentence first then technical detail, flag for
  human review, do not mark done.
- Update runbooks/wave-1-status.md's row for this step (plain-English status, commit, date, and
  anything the NEXT step must resolve first — note that lane P2's Prompt 1.3c depends on this).
```

---

## PROMPT 1.3c — P-07 Cognito hardening + P-11 WAF rate-rule content (parallel lane P2)

**Model/effort:** Claude Code `opus / high` (cutover) + `sonnet / med` (WAF/MFA config) · Codex `GPT-5.6 Sol, high`
**Deps:** 0.1 (done). **Touches:** `cognito_construct.py`, `waf_construct.py`, `src/frontend/**`. **Corrected per §0.1 Finding 2:** this prompt does NOT touch `api_construct.py` — the `is_production_env` gate is a separate spine step (Prompt 1.3c-gate, above), because a shared-file edit five other clauses are also rewriting cannot be "parallel." Once 1.3c-gate lands, WAF exists in every env and this prompt's rate-rule work (entirely inside `waf_construct.py`) is genuinely file-isolated. **Must FINISH + SOAK (the P-07 half) before Prompt 1.1.**

```
Implement P-07 per specs/P-07-cognito-hardening-spec.md and P-11's rate-rule per the WAF section of
specs/P-08-P-10-P-11-cors-waf-spec.md. VERIFY BEFORE ACTING.

PRECONDITION: Prompt 1.3c-gate has landed (WAF instantiates in every env, not just prod). If it
hasn't, the rate-rule you add here has nothing to attach to in dev — check first.

STANDING CHECK (see runbooks/RUNBOOK-RULES.md) — before anything else: open
runbooks/wave-1-status.md and check 1.3c-gate's row. If it shows an open problem, resolve that
first. Confirm 1.3c-gate is really landed with a live `cdk synth` against dev, not by trusting
this file.

CRITICAL SEQUENCING: the P-07 cutover must COMPLETE and SOAK before step 1.1's P-04 auth cleanup.
Stale implicit-flow tokens must not meet newly-strict auth mid-migration (v2.0.0/A5).

STEP 0 — verify-before-remove (do this FIRST, it can HALT the P-07 half):
  grep src/frontend for signin.user.admin, AssociateSoftwareToken, UpdateUserAttributes,
  ChangePassword, TOTP enrollment. Classify each COGNITO_ADMIN-requiring call as
  none | backend_proxy | temporarily_allowed. If a live self-service flow needs the scope and no
  backend proxy exists -> STOP, emit a §0.3 amendment or keep the scope with a migration plan.
  Do NOT remove COGNITO_ADMIN blind.

RED TESTS (cite AC-P07-1..4):
- test_p07_frontend_scope_usage_inventory_complete
- test_p07_app_client_supports_code_pkce_before_implicit_removed  (code + implicit COEXIST during window)
- test_p07_public_spa_client_has_no_cognito_admin_after_cutover
- test_p07_mfa_rollout_has_grace_state                            (optional/enrollment grace before enforced)
- test_p07_401_contract_still_refreshes_once                      (F-01 oracle: 401 -> exactly one refresh -> sign-out)
- test_p11_waf_rate_rule_exists_all_envs                          (RateBasedStatement present + associated to API stage — needs 1.3c-gate landed first)

GREEN (ordered — DUAL-FLOW MIGRATION, never a hard flip):
1. Enable authorization-code + PKCE while KEEPING implicit grant (migration window).
2. Cut src/frontend auth config to code+PKCE FIRST; run FE checks; deploy; SOAK.
3. Remove implicit + remove COGNITO_ADMIN ONLY after soak proves no implicit tokens remain.
4. MFA optional -> enforced with an enrollment GRACE window (never immediate lockout).
5. P-11: add a rate-based rule to waf_construct.py's WebACL (env-tuned threshold) — the WebACL
   itself and its API association already exist in every env once 1.3c-gate has landed.

GUARDRAILS / STOP:
- Do NOT move the Cognito user pool. Do NOT change any API response shape; auth failures keep the
  §3 item-10 flat envelope + one-refresh-then-sign-out.
- Do NOT touch api_construct.py — if the rate rule needs anything beyond waf_construct.py, STOP,
  that's a scope surprise, coordinate with the spine instead of editing it from this lane.
- Do NOT deploy. cdk diff zero stateful replacement. Hand change set to human.

VERIFY:
cd src/frontend && npm run typecheck && npm run test:unit && npm run test:integration
cd infra && uv sync && cdk synth && cdk diff CareerVpCrudDev
cd src/backend && uv run pytest tests/infrastructure -k "p07 or p11 or waf or cognito" -v
python src/backend/scripts/validate_naming.py --path infra --strict
SCOPE-LOCK: scope-diff.py -> P-07 and P-11 test_written/implemented.

OUTPUT REQUIRED:
1. A git commit message.
2. The frontend scope-usage inventory (the none/backend_proxy/temporarily_allowed classification).
3. RED failure output if this session wrote tests.
4. EXPLICIT soak status: "PKCE cutover deployed + soaked, implicit+COGNITO_ADMIN removed" vs
   "migration window OPEN — implicit still enabled; 1.1 (P-04) MUST NOT START until soak completes."

ALSO REQUIRED (standing rule for every wave prompt — see runbooks/RUNBOOK-RULES.md):
- Compare what you built against this prompt AND against P-07's and P-11's entries in
  project-scope-lock.yaml; say plainly whether they match.
- If anything drifted, STOP, explain in one plain sentence first then technical detail, flag for
  human review, do not mark done.
- Update runbooks/wave-1-status.md's row for this step. If the soak is still open, that IS the
  "open problem for the next step" — write it there explicitly so Prompt 1.1 sees it and refuses
  to start.
```

---

## PROMPT 1.3a — P-08 CV/generated bucket CORS pilot (parallel lane P3)

**Model/effort:** Claude Code `sonnet / medium` · Codex `GPT-5.4, medium`
**Deps:** 0.1 (done). **Touches:** `s3_stack.py`, `api_db_construct.py`, `frontend_stack.py` — **isolated from api_construct.py, safe to parallelize.** **Feeds Prompt 1.3b.**

```
Implement P-08 per the S3 section of specs/P-08-P-10-P-11-cors-waf-spec.md. VERIFY BEFORE ACTING.
This is the LOW-BLAST-RADIUS CORS PILOT — land it before touching API-GW CORS (1.3b).

STANDING CHECK (see runbooks/RUNBOOK-RULES.md) — before anything else: open
runbooks/wave-1-status.md. This lane has no prior Wave-1 step it depends on (dep is 0.1, already
done) — but skim the ledger for anything flagged against files you're about to touch.

RED TESTS (cite AC-P08-1):
- test_p08_s3_cors_has_no_wildcard_origin   (CV/generated buckets: no AllowedOrigins "*")
Audit the S3 CORS rules at api_db_construct.py:184,561, s3_stack.py:40,63, frontend_stack.py:48.

GREEN: replace wildcard CORS on CV/generated buckets with explicit per-env frontend origins
(localhost ONLY for dev). Keep request/response payloads unchanged.

GUARDRAILS / STOP:
- Do NOT deploy. cdk diff zero stateful replacement (a bucket must NOT be replaced). Hand to human.
- Do NOT touch api_construct.py — that's 1.3b's territory; keep this lane file-isolated.

VERIFY:
cd infra && uv sync && cdk synth && cdk diff CareerVpCrudDev
cd src/backend && uv run pytest tests/infrastructure -k "p08 or cors" -v
python src/backend/scripts/validate_naming.py --path infra --strict
SCOPE-LOCK: scope-diff.py -> P-08 test_written/implemented.

OUTPUT REQUIRED:
1. A git commit message.
2. RED failure output.
3. IF clean: "1.3a P-08 CORS pilot landed. 1.3b P-10 (API-GW CORS) may proceed in the spine after
   a P-30 exact-origin smoke."

ALSO REQUIRED (standing rule for every wave prompt — see runbooks/RUNBOOK-RULES.md):
- Compare what you built against this prompt AND P-08's entry in project-scope-lock.yaml; say
  plainly whether they match.
- If anything drifted, STOP, explain in one plain sentence first then technical detail, flag for
  human review, do not mark done.
- Update runbooks/wave-1-status.md's row for this step, including anything Prompt 1.3b needs to
  know before it starts.
```

---

## PROMPT 1.3b — P-10 API-GW CORS allow-list (spine, after 1.3a)

**Model/effort:** Claude Code `sonnet / medium` · Codex `GPT-5.6 Terra, high`
**Deps:** 1.3a landed + P-30 exact-origin smoke green. **Touches:** `api_construct.py:356-358` (spine). **Serialize** vs all api_construct.py editors.

```
Implement P-10 per the API-GW section of specs/P-08-P-10-P-11-cors-waf-spec.md. VERIFY BEFORE
ACTING. Preconditions: 1.3a (P-08 pilot) merged; a P-30 OPTIONS+GET exact-origin preflight probe is
GREEN; a pre-staged INVERSE change set is ready; set max-age -> 60s FIRST.

STANDING CHECK (see runbooks/RUNBOOK-RULES.md) — before anything else: open
runbooks/wave-1-status.md and check 1.3a's row. If it shows an open problem, resolve that first.
Confirm 1.3a is really merged and the P-30 smoke is really green with a live command, not by
trusting this file.

THE TRAP: tightening the GatewayResponse ACAO '*' makes every 401 CORS-opaque and KILLS contract
§10's 401 -> refresh -> sign-out flow. KEEP the GatewayResponse '*' as a CODIFIED EXCEPTION.

RED TESTS (cite AC-P10-1/AC-P10-2):
- test_p10_api_cors_success_allowlist_only     (default CORS origins == env allow-list, not ALL_ORIGINS)
- test_p10_gateway_401_cors_exception_is_documented  (GatewayResponse keeps enough CORS for a
    browser-visible 401 + refresh retry; if a wildcard remains it is ONLY on GatewayResponse)
- test_p30_exact_origin_smoke_required_before_cors_cutover  (checklist blocks P-10 until smoke green)
Also fix the poisoned cors-no-wildcard.regression.test.ts before any spec fan-out depends on it.

GREEN: replace api_construct.py:356-358 ALL_ORIGINS for SUCCESS responses with the env allow-list;
leave the GatewayResponse wildcard exception in place and asserted.

GUARDRAILS / STOP:
- IMMUTABLE laws hold. Do NOT deploy. cdk diff zero stateful replacement. Inverse change set staged.
- If the exact-origin smoke is not green -> STOP, do not cut over.

VERIFY:
cd infra && uv sync && cdk synth && cdk diff CareerVpCrudDev
cd src/backend && uv run pytest tests/infrastructure -k "p10 or cors or p26" -v
cd src/frontend && npm run test:integration     # 401 refresh-once still green
SCOPE-LOCK: scope-diff.py -> P-10 test_written/implemented.

OUTPUT REQUIRED:
1. A git commit message.  2. RED failure output.  3. The inverse-change-set path + smoke evidence.
4. IF clean: "1.3b P-10 landed, GatewayResponse 401 exception preserved."

ALSO REQUIRED (standing rule for every wave prompt — see runbooks/RUNBOOK-RULES.md):
- Compare what you built against this prompt AND P-10's entry in project-scope-lock.yaml; say
  plainly whether they match, paying special attention to the GatewayResponse exception — that's
  the one place a "correct-looking" change can silently break the frontend contract.
- If anything drifted, STOP, explain in one plain sentence first then technical detail, flag for
  human review, do not mark done.
- Update runbooks/wave-1-status.md's row for this step.
```

---

## PROMPT 1.2 — P-06 secrets out of Lambda env (spine)

**Model/effort:** Claude Code `sonnet / medium` · Codex `GPT-5.5, medium` (escalate to Sol if ARN scoping gets subtle)
**Deps:** 0.1 (done). **Touches:** `api_construct.py` (JWT env sites), `constants.py`, a runtime secret provider. **Serialize** vs api_construct.py editors.

```
Implement P-06 per specs/P-06-secrets-spec.md. VERIFY BEFORE ACTING.

STANDING CHECK (see runbooks/RUNBOOK-RULES.md) — before anything else: open
runbooks/wave-1-status.md. This step slots in anywhere after 1.0 in the spine — check the row for
whichever spine step landed most recently, and confirm the spine is actually free (no other
api_construct.py editor mid-session) before starting.

RED TESTS (cite AC-P06-1..3):
- test_p06_lambda_env_has_no_plaintext_jwt_key_material   (synth: no PEM markers / resolved key text)
- test_p06_secret_env_values_are_references_only          (JWT+webhook env == /careervp/{env}/... paths or SM ARNs)
- test_p06_runtime_secret_provider_fetches_with_decryption (WithDecryption=True; cached per exec env; never logs secret)
- test_p06_iam_secret_access_is_arn_scoped                (no Resource:"*" on secret grants)

GREEN: keep only parameter NAMES / Secrets-Mgr ARNs in Lambda env (JWT private/public at
api_construct.py:925-928,1407-1410,1809-1812,1887-1890,1927-1930,1992-1995; webhook already
name-only at 2569-2573 — the target pattern). Add a shared cached runtime secret provider that
fetches with decryption. Grant ssm:GetParameter(WithDecryption)/secretsmanager:GetSecretValue
ARN-scoped, env-suffixed, only to the functions that need it. Preserve current+previous webhook
secret for rotation. No request/response shape change.

GUARDRAILS / STOP: IMMUTABLE laws hold. Do NOT deploy. cdk diff zero stateful replacement. Do NOT
change auth identity semantics (that's P-04/P-24). If a secret grant can't avoid Resource:"*" for a
genuinely unknown ARN, document WHY in the test, don't silently wildcard.

VERIFY:
cd infra && uv sync && cdk synth && cdk diff CareerVpCrudDev
cd src/backend && uv run pytest tests/infrastructure -k "p06 or secret" -v && uv run pytest tests/unit -k p06 -v
cd src/backend && uv run ruff format . && uv run ruff check --fix . && uv run mypy careervp --strict
python src/backend/scripts/validate_naming.py --path infra --strict
SCOPE-LOCK: scope-diff.py -> P-06 test_written/implemented.  COVERAGE: report delta vs enforced_baseline.

OUTPUT REQUIRED: commit message; RED failure output; explicit "no plaintext secret in synthesized
Lambda env" statement; the runtime provider's cache scope. IF clean: "1.2 P-06 landed."

ALSO REQUIRED (standing rule for every wave prompt — see runbooks/RUNBOOK-RULES.md):
- Compare what you built against this prompt AND P-06's entry in project-scope-lock.yaml; say
  plainly whether they match.
- If anything drifted (especially any Resource:"*" grant left in place), STOP, explain in one
  plain sentence first then technical detail, flag for human review, do not mark done.
- Update runbooks/wave-1-status.md's row for this step.
```

---

## PROMPT 1.3d — P-26 Job-1 count-relief: EXECUTE the prepared resource-import (spine; hard blocker)

**Model/effort:** Claude Code `opus / xhigh` · Codex `GPT-5.6 Sol, xhigh` — hardest step; 908-user blast radius. **Deps:** 0.7 (satisfied). **Touches:** `api_construct.py`, `app.py` (spine). **Human-gated execute.**

```
Finish P-26 Job-1 count-relief. VERIFY BEFORE ACTING — the execution-plan status note for this row
is STALE. Confirm the REAL current state from git + a command you just ran, do not trust the table.

STANDING CHECK (see runbooks/RUNBOOK-RULES.md) — before anything else, in this order:
1. Open runbooks/wave-1-status.md and check its row for this step (1.3d). It records that a
   contract amendment (project-scope-lock.yaml v2.5.0) must be COMMITTED before this step is
   allowed to run — the contract file otherwise still files this work under Wave 0, and running it
   here without that commit would repeat the exact undocumented-drift problem that amendment fixes.
   Run `git log -1 -- project-scope-lock.yaml` and confirm the top commit's message references
   v2.5.0 / P-26 wave tracking. If it does NOT, STOP — do not proceed with the engineering below
   until a human has committed that amendment.
2. Once confirmed, check whichever spine step landed most recently for any open problem, and
   confirm 1.3c-gate (P-11) has landed so the spine is clear.

KNOWN-BUT-VERIFY current state (2026-07-17):
- Commit dd33025 re-homed 77 named feature resources into CrudFeaturesNestedStack (Job-1 import
  PREPARED). Commit 7fe3c4d deployed CareerVpCrudDev with CrudFeatures staged as an EMPTY nested
  stack first, and ran P-30 smoke 4/4 GREEN against the LIVE custom domain https://api.dev.careervp.com.
- BUT offline synth this pass shows parent CareerVpCrudDev = 412 and NO CrudFeaturesNestedStack
  template in cdk.out. So EITHER HEAD toggled the re-homing back to the empty staged form, OR
  cdk.out is stale. RESOLVE THIS FIRST with `cdk synth` + `cdk diff CareerVpCrudDev` against live —
  do not proceed on assumption.
- P-24 authorizer was restored dormant-by-design in 7fe3c4d — confirm it stays dormant here.

The RED outcome tests already exist (c6fa939 / dd33025):
  src/backend/tests/infrastructure/test_p26_job1_resource_import_outcomes.py (5 tests)
  src/backend/tests/infrastructure/test_p26_blue_green_api.py (12 guard tests, incl. RestApi
  logical-id + Cognito singular + <500 + PARENT_HEADROOM_TARGET=400 warn-only).
DO NOT rewrite these. If one seems wrong -> STOP, §0.3 amendment; never weaken a test to pass.

MECHANISM (amendment ACCEPTED 2026-07-15, Option A): human-gated `cdk refactor` resource-import,
physical-id PRESERVED (no delete/create). CDK CLI 2.1105.0, UNSTABLE feature (--unstable required).
  cd infra && cdk refactor --unstable=refactor --dry-run     # inspect computed mapping
  # --override-file to correct where CDK guesses; --revert exists; RETAIN(567320d) is the net.

REMAINING WORK (mostly EXECUTE + verify, not fresh authoring):
1. Resolve the synth/live discrepancy above; get the working tree to the intended re-homed shape.
2. cdk refactor --dry-run: mapping must show IMPORT with physical-ids PRESERVED, ZERO DELETE+CREATE,
   and RestApi + Cognito must NOT appear in the mapping at all.
3. Prove parent CareerVpCrudDev drops BELOW 400 with the 77 resources in CrudFeatures; no template >=500.
4. Hand the prepared mapping + templates + the P-28 DescribeChangeSet Replacement report to the
   HUMAN to execute. After human execution: re-run P-30 smoke (must stay 4/4 green through
   https://api.dev.careervp.com).

STOP CONDITIONS (any -> STOP, §0.3):
- RestApi or Cognito appears in the refactor mapping AT ALL (IMMUTABLE breach).
- dry-run shows DELETE+CREATE (not IMPORT) for any named resource.
- Any template >= 500, or parent still >= 400 after re-homing.
- No AWS creds -> report honestly, do not fake a mapping. (cdk refactor reads live stack state.)

STRONGLY RECOMMENDED: rehearse on the 0.64 scratch rig (scratch_deployment.py, eu-west-1, ~5.5min,
tears down to zero) BEFORE the human touches dev. That rig was built for exactly this.

VERIFY:
cd infra && uv sync && cdk synth      # RestApi id BYTE-STABLE; parent < 400
cd infra && cdk refactor --unstable=refactor --dry-run
cd src/backend && uv run pytest tests/infrastructure -k "p26 or p24 or identity_surrogate" -v
cd infra && uv run pytest tests/infrastructure -k "p26 or nested_split or artifact_chain" -v
cd src/backend && uv run ruff format . && uv run ruff check --fix . && uv run mypy careervp --strict

DO NOT EXECUTE against AWS (no cdk deploy, no refactor without --dry-run, no ExecuteChangeSet).

OUTPUT REQUIRED:
1. A git commit message.
2. Parent resource count BEFORE/AFTER + the exact 77-resource re-home list + which artifact-chain
   export locks are broken/re-imported + the prepared refactor artifact path awaiting human execution.
3. The rollback lever (cdk refactor --revert + RETAIN net), stated explicitly.
4. IF clean: "1.3d P-26 Job-1 PREPARED and dry-run IMPORT-clean, parent < 400. Human executes;
   then P-30 smoke; then 1.4 P-09 is unblocked." IF a live-truth contradiction surfaces: STOP, §0.3.

ALSO REQUIRED (standing rule for every wave prompt — see runbooks/RUNBOOK-RULES.md):
- Compare what you built against this prompt AND P-26's entry in project-scope-lock.yaml
  (including the wave_1_carryover note); say plainly whether they match.
- If anything drifted — especially RestApi/Cognito appearing in the mapping, or the parent
  staying ≥400 — STOP, explain in one plain sentence first then technical detail, flag for human
  review, do not mark done.
- Update runbooks/wave-1-status.md's row for this step. If the human hasn't executed the refactor
  yet, that IS the open problem for 1.4 (P-09) — write it there explicitly.
```

---

## PROMPT 1.4 — P-09 one IAM role per function (spine, after 1.3d)

**Model/effort:** Claude Code `opus / high` · Codex `GPT-5.6 Terra, high` (escalate to Sol if least-privilege proofs stall). **Deps:** 1.3d landed (hard block). **Touches:** `api_construct.py:516-821` + every Lambda def (spine). **Serialize** vs P-26 — never concurrent.

```
Implement P-09 per specs/P-09-iam-per-function-spec.md. VERIFY BEFORE ACTING. HARD-BLOCKED until
1.3d (P-26 Job-1 count-relief) has landed — do this AFTER the Lambdas settle into their nested homes,
so per-function roles are added to a parent stack with headroom, not one at 412.

STANDING CHECK (see runbooks/RUNBOOK-RULES.md) — before anything else: open
runbooks/wave-1-status.md and check 1.3d's row. If it shows the human hasn't executed the refactor
yet, or ANY open problem, STOP — do not start this step. Confirm with a live `cdk synth` that the
parent template is actually below 400, not by trusting this file or the ledger's last note.

OPTIONAL recon subagent (read-only): "enumerate every Lambda CDK creates + its exact required
data-plane/control-plane ARNs (table/queue/bucket/state-machine/topic/parameter)." Compact list out;
never let it write CDK.

RED TESTS (cite AC-P09-1..3):
- test_p09_every_lambda_has_unique_role   (len(unique role refs) == len(functions), minus documented
    service-managed exceptions)
- test_p09_role_names_are_env_suffixed_kebab_case  (careervp-role-{service}-{feature}-{env})
- test_p09_no_known_arn_permission_uses_resource_star  (DDB/S3/SQS/SNS/SSM/SFN with known ARNs: Resource != "*")
- test_p09_billing_and_export_do_not_use_default_roles

GREEN: one explicit env-suffixed role per function (via NamingUtils/constants); least-privilege
policies scoped to exact ARNs; retire the shared policy machinery at api_construct.py:516-821 and
the billing/export default-role fallback; drop the broad dynamodb:Scan at :661 from the shared role.

GUARDRAILS / STOP: IMMUTABLE laws hold (this adds many resources to the parent — confirm no template
>= 500 AFTER 1.3d's relief; if it breaches, STOP, the ordering assumption failed). Do NOT deploy.
cdk diff zero stateful replacement. Checkov/Bandit stay green.

VERIFY:
cd infra && uv sync && cdk synth && cdk diff CareerVpCrudDev
cd src/backend && uv run pytest tests/infrastructure -k "p09 or iam or p26" -v
python src/backend/scripts/validate_naming.py --path infra --strict
cd src/backend && uv run ruff format . && uv run ruff check --fix . && uv run mypy careervp --strict
SCOPE-LOCK: scope-diff.py -> P-09 test_written/implemented.

OUTPUT REQUIRED: commit message; RED failure output; role-count == function-count proof; the ARN
scoping table. IF clean: "1.4 P-09 landed, least-privilege per function." IF template >= 500: STOP.

ALSO REQUIRED (standing rule for every wave prompt — see runbooks/RUNBOOK-RULES.md):
- Compare what you built against this prompt AND P-09's entry in project-scope-lock.yaml; say
  plainly whether they match.
- If anything drifted — especially any remaining Resource:"*" grant, or the template breaching
  500 — STOP, explain in one plain sentence first then technical detail, flag for human review,
  do not mark done.
- Update runbooks/wave-1-status.md's row for this step.
```

---

## PROMPT 1.1 — P-04/P-05 auth cleanup + IDOR owner checks (spine, LAST)

**Model/effort:** Claude Code `opus / high` · Codex `GPT-5.6 Sol, high→xhigh` — most correctness-critical step in the wave. **Deps:** 1.0 (P-23) LANDED **and** 1.3c (P-07 PKCE) SOAKED. **Touches:** `src/backend/handlers/**` + `api_construct.py:1720`. **Serialize** vs api_construct.py editors.

```
Implement P-04 + P-05 per specs/P-04-P-05-auth-idor-spec.md. VERIFY BEFORE ACTING. This is the most
correctness-critical step in Wave 1 — an IDOR miss serves wrong-tenant data.

HARD PRECONDITIONS (confirm both, do not start otherwise):
- 1.0 P-23 has LANDED (the canary is the revert lever for the x-user-id removal — a Lambda change).
- 1.3c P-07 PKCE cutover has DEPLOYED + SOAKED (stale implicit tokens must not meet strict auth mid-migration).

STANDING CHECK (see runbooks/RUNBOOK-RULES.md) — before anything else: open
runbooks/wave-1-status.md and check the rows for 1.0 and 1.3c. If EITHER shows an open problem —
especially "soak still open" on 1.3c — STOP, do not start this step. This is the most
correctness-critical step in the wave; starting it early is exactly the mistake this rule exists
to prevent.

RECON SUBAGENT (read-only, recommended): "build the route x handler ownership matrix from the LIVE
CDK route_map (api_construct.py:2864-2936), excluding only documented public routes: /health, auth
routes, /billing/webhook (2811-2817), error reports." Do NOT enumerate from stale docs — the spec
requires the table be generated from the live route_map. Check the matrix in as evidence.

TDD FIREWALL STRONGLY ADVISED: RED session writes the tests + the checked-in matrix and proves them
failing; a FRESH GREEN session removes the fallbacks + enforces owner checks. The cross-tenant
negative must be REAL (seed tenant A + tenant B, assert B never sees A's data), not a mock that
asserts nothing.

RED TESTS (cite AC-P04-1/2, AC-P05-1/2):
- test_p04_no_x_user_id_fallbacks_remain        (scan handlers/**: zero x-user-id outside fixtures/docs)
- test_p04_no_authorizer_disabled_runtime_switch (scan infra/ + src/backend/: AUTHORIZER_DISABLED absent)
- test_p05_route_matrix_has_owner_assertion_for_every_authenticated_route
- test_p05_cross_tenant_authenticated_routes_deny (parametrized over EVERY authed route; B -> 403/404, never A's data)
- test_p05_error_envelope_is_flat               (IDOR denial keeps §3 item-10 FLAT envelope, no nested error.code)

GREEN:
- P-04: delete x-user-id / body / query / path user_id trust and the dead AUTHORIZER_DISABLED env at
  api_construct.py:1720. Identity comes ONLY from validated JWT claims or the P-24 resolver context.
- P-05: every authed handler resolves records by authenticated owner; another tenant's job_id/
  artifact_id/cv_id/vpr_id/application_id -> 403/404 with the flat envelope.
- Add the P-24 resolver-failure metric HOOK expectation (do NOT implement P-24 here; do NOT
  instantiate the custom authorizer). Aggregate 401-rate is NOT sufficient.

GUARDRAILS / STOP:
- NO route shape / enum / envelope change except correct denials. F-01 oracle MUST stay green.
- Do NOT rebuild AUTHORIZER_DISABLED as a lever. Do NOT invent a second identity authority (P-24 owns sub->user_id).
- IMMUTABLE laws hold. Any infra edit: cdk diff zero stateful replacement + validate_naming --verbose.
- Do NOT deploy.

VERIFY:
cd src/backend && uv run pytest tests/unit -k "p04 or p05 or idor or owner" -v
cd src/backend && uv run pytest tests/integration -k "cross_tenant or owner" -v
cd src/frontend && npm run test:integration        # F-01 oracle: 401 + flat envelope still green
cd infra && uv sync && cdk synth && cdk diff CareerVpCrudDev
cd src/backend && uv run ruff format . && uv run ruff check --fix . && uv run mypy careervp --strict
python src/backend/scripts/validate_naming.py --path infra --verbose
SCOPE-LOCK: scope-diff.py -> P-04 and P-05 test_written/implemented.  COVERAGE: report delta vs baseline.

OUTPUT REQUIRED:
1. A git commit message.  2. RED failure output.  3. The checked-in route x handler owner matrix path.
4. Explicit confirmation the cross-tenant negative seeds two real tenants.  5. IF clean:
   "1.1 P-04/P-05 landed; x-user-id + AUTHORIZER_DISABLED gone; every authed route owner-enforced;
   F-01 oracle green." IF a precondition (P-23 landed / P-07 soaked) is unmet: STOP, do not start.

ALSO REQUIRED (standing rule for every wave prompt — see runbooks/RUNBOOK-RULES.md):
- Compare what you built against this prompt AND P-04's and P-05's entries in
  project-scope-lock.yaml; say plainly whether they match.
- If anything drifted — especially any route left without an owner check, or the F-01 oracle
  breaking — STOP, explain in one plain sentence first then technical detail (a wrong-tenant data
  leak is the single worst outcome in this wave), flag for human review, do not mark done.
- Update runbooks/wave-1-status.md's row for this step.
```

---

## PROMPT 1.5 — P-22 OIDC in cdk-diff.yml (parallel lane P1) — AUTHOR SPEC FIRST

**Model/effort:** author `sonnet / med` (Codex `GPT-5.5, med`) → implement `sonnet / med` (Codex `GPT-5.4-mini, low`). **Deps:** 0.1 (done). **Touches:** `.github/workflows/cdk-diff.yml` — **isolated, safe to parallelize.**

```
Implement P-22 (OIDC in cdk-diff.yml, kill long-lived AWS keys). VERIFY BEFORE ACTING.

STANDING CHECK (see runbooks/RUNBOOK-RULES.md) — before anything else: open
runbooks/wave-1-status.md. This lane has no prior Wave-1 step it depends on — but skim the ledger
for anything flagged against `.github/workflows/`.

STEP 0 — THE SPEC IS MISSING. specs/ has NO P-22-*.md file (every other Wave-1 clause has one).
Author specs/P-22-oidc-cdk-diff-spec.md FIRST, in the exact house style of the sibling specs
(frontmatter: spec_id, status: draft, scope_lock_clause: P-22, format_note; then Problem Statement,
Evidence [cite .github/workflows/cdk-diff.yml + how AWS creds are injected today], Fix Plan, RED
Tests to Write First, Acceptance Criteria AC-P22-1.., Done-when, Sequencing). Keep it AUTHOR-ONLY;
do not write pytest in the spec.

RED TESTS then GREEN (from the spec you just authored):
- Assert cdk-diff.yml uses aws-actions/configure-aws-credentials with role-to-assume + an OIDC
  federated trust, and that NO long-lived aws-access-key-id / aws-secret-access-key secrets are
  referenced by the workflow.
- Assert permissions: id-token: write is present (required for OIDC).
GREEN: convert the workflow to GitHub OIDC role assumption; remove the long-lived key secrets.

GUARDRAILS / STOP: CI-only change; touch no application code, no other workflow, no api_construct.py.
This is a real IAM trust relationship on AWS (the OIDC provider + role) — that account-side setup is
a HUMAN task; document it in the spec's Done-when, do not fake it. If cdk-diff.yml already uses OIDC,
say so and the clause is a no-op-verify.

VERIFY:
python3 docs/db-redesign/code/code-analysis/project/scope-diff.py   # P-22 now spec_written->test_written
# lint the workflow if actionlint is available; otherwise assert via the test file.

OUTPUT REQUIRED:
1. Two commits (spec author; then RED+GREEN) or one clearly-sectioned commit.
2. RED failure output.
3. The human account-side setup step (OIDC provider + role trust) named explicitly.
4. IF clean: "1.5 P-22 spec authored + OIDC landed in cdk-diff.yml; long-lived keys removed."

ALSO REQUIRED (standing rule for every wave prompt — see runbooks/RUNBOOK-RULES.md):
- Compare what you built against this prompt AND P-22's entry in project-scope-lock.yaml; say
  plainly whether they match.
- If anything drifted, STOP, explain in one plain sentence first then technical detail, flag for
  human review, do not mark done.
- Update runbooks/wave-1-status.md's row for this step.
```

---

## Wave-1 GATE (run after 1.0–1.5 all land)

**Model/effort:** Claude Code `opus / high` — adjudicate, don't transcribe. **Deps:** all prompts clean.

```
Run the Wave-1 exit gate. VERIFY EVERY ROW against git + files on disk — the ledger has been wrong
before. Do not transcribe the table; adjudicate it.

STANDING CHECK (see runbooks/RUNBOOK-RULES.md) — before anything else: open
runbooks/wave-1-status.md in full. Every row for 1.0 through 1.5 must show a landed status with no
open problem. If ANY row shows an open problem or a status other than "landed"/"done", STOP — this
gate cannot legitimately run yet. Do not adjudicate a wave that the ledger itself says is
incomplete.

1. scope-diff.py full run: every Wave-1 clause (P-04,P-05,P-06,P-07,P-08,P-09,P-10,P-11,P-22,P-23)
   resolves to test_written/implemented. (P-22 needs its newly-authored spec + tests.)
2. Both infra test dirs green: cd infra && uv run pytest tests/infrastructure -v ; and
   cd src/backend && uv run pytest tests/infrastructure -v.
3. Backend unit + integration green (cross-tenant IDOR negatives included). Frontend oracle green
   (401 refresh-once + flat envelope survived the CORS + auth changes).
4. make coverage-tests: enforced_baseline PASSES (no regression); report distance to ratchet_target.
5. IMMUTABLE re-check: RestApi + Cognito logical ids byte-stable; P-24 authorizer still dormant.
6. 1.3d actually landed: parent CareerVpCrudDev < 400 after human execution + P-30 smoke green;
   P-09 was unblocked by it. If 1.3d only PREPARED (human hasn't executed) -> Wave 1 is AMBER;
   say so and name P-09/P-14/P-17/P-21 as still-blocked.
7. Reconcile redesign-execution-plan.md Wave-1 Status column to VERIFIED REALITY, dated narrative
   line per row (match the 0.55/0.75 style).

GUARDRAILS: do NOT edit project-scope-lock.md/.yaml without the twin-sync ceremony (§12 changelog +
version bump + Scope-Lock-Approved-By: Yitzchak Meirovich trailer), human-approved only. Do NOT mark
a row verified you did not personally prove this session. If any clause is not verified, say so and
STOP — do not generate wave-2-prompts.md on an amber gate.

OUTPUT: a single "Wave 1 GATE PASSED" (or "AMBER") commit message (docs-only status sync); an
explicit list of anything still open with its Wave-2 home; IF clean: "Wave 1 verified. Wave 2
(reliability/money) step 2.0 dependency (1.*) satisfied — wave-2-prompts.md may be generated."

ALSO REQUIRED (standing rule for every wave prompt — see runbooks/RUNBOOK-RULES.md):
- Update runbooks/wave-1-status.md's GATE row with the final plain-English verdict.
- If you generate wave-2-prompts.md, it MUST link runbooks/RUNBOOK-RULES.md the same way this
  file does, and MUST come with a fresh runbooks/wave-2-status.md ledger seeded before any Wave-2
  prompt is written — see RUNBOOK-RULES.md's closing section, "For whoever writes the next wave's
  prompt file."
```

---

## 4. Issues you should weigh

1. **`api_construct.py` is the wave's contention hotspot** — six clauses edit it. The parallelism
   ceiling is real: 3 isolated Codex lanes (P-22, P-07/P-11, P-08) + 1 serialized spine. Do not let
   two agents edit it concurrently, and rebase each spine step on the prior before starting.
2. **P-22 has no spec.** Prompt 1.5 authors one first. If you'd rather keep spec authoring a human
   step, do it before dispatching lane P1.
3. **The execution-plan status note for 1.3d is already stale** (77 resources re-homed, empty
   nested stack deployed, custom domain live). This is the same "code exists ≠ done / ledger lags"
   trap from Wave 0 — 1.3d's prompt resolves it by synth+diff, not by trusting any paragraph here.
4. **1.3d needs live AWS creds** — `cdk refactor` reads deployed stack state; it cannot be fully
   prepared offline. Rehearse on the 0.64 scratch rig (eu-west-1) before the human touches dev.
5. **P-07 soak gates P-04.** Don't let the parallel lane P2 finish "green in CI" get mistaken for
   "soaked in dev." 1.1 must not start until the PKCE cutover has actually soaked.
6. **The P-10 GatewayResponse trap** kills the §3 401→refresh→sign-out contract if the ACAO
   wildcard is tightened. Keep it as a codified, asserted exception.
7. **P-09 after P-26, never during.** P-09 adds one role per Lambda to the parent stack; run it only
   after 1.3d's count-relief lands, and confirm no template ≥ 500 afterward.
8. **Coverage:** Wave 1 adds security tests (mostly positive for the ratchet), but the auth/IDOR
   handlers (`cover_letter_handler.py`, `interview_prep_handler.py`, `cv_tailoring_handler.py`,
   the 0%-covered DAL files) are exactly where branch coverage is thin. Wave 1's cross-tenant
   parametrization is a good chance to close some of the 16-25% branch gap — report the delta,
   don't retro-bump the gate.
9. **`Scope-Lock-Approved-By:`** friction with the scope-lock-guard CI workflow — expect it on any
   clause that turns out to need a §0.3 amendment (most likely P-07's COGNITO_ADMIN removal if a
   live self-service flow needs the scope).

---

## 5. Codex Model Family (reference — retained for future waves)

The current Codex family should be understood roughly like this:

| Codex option | Best mental model | Use it for |
|---|---|---|
| GPT-5.4 mini | Fast junior/mid-level implementer | Small edits, straightforward tests, repetitive changes |
| GPT-5.4 | Strong general-purpose engineer | Normal feature work, debugging, refactors |
| GPT-5.5 | More autonomous senior engineer | Larger changes, ambiguous bugs, multi-step implementation |
| GPT-5.6 Terra | Strong model optimized toward balance | Most serious daily engineering where cost/speed still matter |
| GPT-5.6 Sol | Flagship/principal engineer | Hard architecture, deep debugging, security, migrations, long-horizon tasks |
| GPT-5.6 Luna | Cost-sensitive/high-volume model | Repetitive or lower-risk work |

**The analogy — models are engineers:**
- 5.4 mini: a competent technician
- 5.4: a senior engineer
- 5.5: a senior engineer who is better at taking ownership of a messy task
- 5.6 Terra: a very strong generalist you can use every day
- 5.6 Sol: the principal engineer you bring in when the system is subtle or the cost of being wrong is high
- 5.6 Luna: the efficient engineer for high-volume routine work

**Reasoning level is how long you let that engineer investigate before acting.** A weak model at max
reasoning is a junior given an afternoon to overthink; a strong model at low reasoning is a principal
asked to fix one typo and leave.

**Corrected recommendations for CareerVP:**
- Tiny code change, test update, docs: **GPT-5.4 mini, low/medium**
- Normal backend/frontend feature: **GPT-5.4 or GPT-5.5, medium**
- CDK change, API contract change, cross-layer bug: **GPT-5.5 or GPT-5.6 Terra, high**
- Auth, security, concurrency, migration, production incident: **GPT-5.6 Sol, high/xhigh**
- Large unfamiliar subsystem: **GPT-5.6 Terra first, then Sol** if architecture stays ambiguous
- Repetitive test generation / mechanical migration: **GPT-5.4 mini or Luna, low/medium**

**The key correction:** 5.5 and 5.6 are *model upgrades, not merely higher reasoning settings*. Use
the model selector to choose the engineer; use effort to decide how much investigation that engineer
performs.

**Codex ↔ Claude Code analogue:**

| Codex | Claude Code analogue |
|---|---|
| 5.4 mini / Luna | Haiku-like efficiency tier |
| 5.4 / Terra | Sonnet-like daily driver |
| 5.5 | Strong Sonnet or lighter Opus territory |
| 5.6 Sol | Opus territory |
| High/xhigh effort | Explicit deep planning, investigation, verification |

(A workflow analogy, not a benchmark equivalence.)

**Practical rule:** *Start with 5.4 or 5.5 at medium. Move to 5.6 Terra at high when the task spans
multiple layers. Use 5.6 Sol at high or xhigh when correctness matters more than speed or quota.*
For Claude: *Sonnet by default; Opus when the problem needs architecture, subtle debugging, or
sustained autonomous work — and ask it to investigate deeply, not merely "fix this."*
