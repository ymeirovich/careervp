# Wave 2 — Reliability / money (copy-paste runbook)

> **Generated:** 2026-07-24, against `redesign-execution-plan.md` and
> `project-scope-lock.yaml` v2.6.0, **after the Wave-1 GATE passed** (see the GATE row in
> [`wave-1-status.md`](./wave-1-status.md), 2026-07-24, all eight checks adjudicated live).
> Wave 2 step 2.0's only dependency (`1.*`) is satisfied, so this file is authorized.
>
> **Branch:** `db-redesign` · **Deploy target: `CareerVpCrudDevx`** (not `CareerVpCrudDev`)
> **Canonical docs tree:** `docs/db-redesign/code/` (`code1`/`code2` are stale — ignore)
>
> **Three companion files every prompt below depends on — read all three before starting:**
> - [`RUNBOOK-RULES.md`](./RUNBOOK-RULES.md) — the thirteen standing rules. Rules 9–13 are new as
>   of 2026-07-24 and change how this file is written; rule 11 is why most of it is skeletons.
> - [`wave-2-status.md`](./wave-2-status.md) — the LIVE ledger. This file describes *intent*;
>   that one describes *what actually happened*. Check it before starting, update it when you
>   finish or stop.
> - [`ISSUES.md`](../ISSUES.md) — the five **bets** this wave rests on (`B-2-1` … `B-2-5`).
>   Two of them are already known to be partly false. Read them before 2.0.

---

## 0. READ FIRST

### 0.1 — This file is deliberately incomplete, and that is the design

Per `RUNBOOK-RULES.md` rule 11: **step 2.0 is written in full. Every later step is a contractual
skeleton.** A skeleton carries its clause ids, its acceptance-criteria ids, its dependencies, its
deploy target, its done-when, and the bets it rests on — enough to see the whole wave and how it
wires together, not so much that it rots before it is run.

**Filling in a skeleton is a real step**, done by a session that has first read every ledger row
above it, so that deviations from earlier steps get absorbed rather than contradicted. The
clause ids, acceptance-criteria ids, and done-when in a skeleton come from the contract and the
spec and **may not be invented or widened at fill-in time**. If filling one in requires changing
its clause or its acceptance criteria, that is a rule-5 stop and a §0.3 amendment.

Why: `wave-1-prompts.md` was written whole, up front. It then needed three standing corrections, a
seven-row stale-citation table, a three-way split of step 1.1, and a supersession banner. In places
it now carries more correction than original text.

### 0.2 — Verify from live, not from docs

Wave 1 recorded this lesson three separate times — a deploy state read from a diff and corrected the
next day, two rounds of stale line-number citations, and a 30-day waiting period that was protecting
nothing. Then it found three more real bugs **only by deploying and logging in**, none of which any
amount of code reading would have surfaced. Trust git history, the file on disk, live AWS, and a
command you just ran. Never a status column or a prior runbook's "current state" paragraph —
**including this one.**

### 0.3 — `devx` is the primary environment. One thing about bet `B-2-4` is now decided; one is not.

**(2026-07-25, human decision.)** devx is now the primary development environment, and deploys
should go **only** to devx. This is not a new stack — devx is the same `CareerVpCrudDevx` this
wave already targets, which the P-26 v2.6.0 amendment describes as a parallel deployment created
with `ENVIRONMENT=devx` and `p26_rehome_features=true` — i.e. the revised architecture with
features rehomed into `CrudFeaturesNestedStack`, replacing the old flat/near-400-resource
`CareerVpCrudDev` shape. `CareerVpCrudDev` is being retired, not extended.

That resolves the *decision* half of bet `B-2-4`, but **not the code**:

1. **DECIDED, not yet implemented:** a merge to `main` still deploys to the OLD stack.
   `deploy.yml:37` sets `STACK_NAME: 'CareerVpCrudDev'` as a workflow-wide constant, and the
   `push: main` jobs still hardcode `ENVIRONMENT: dev`, `/careervp/dev/*` parameter reads, and
   `--env dev-live` parity. This is now a **known contradiction between policy and code**, not an
   open question — flip the push-to-`main` target to devx (or stop auto-deploying on push) as a
   dedicated, reviewed CI change; do not fold it silently into a Wave-2 payments step.
2. **DONE, verified live:** the approval gate now covers devx — the `devx` GitHub deployment
   environment exists with a required reviewer (verified 2026-07-25). See
   [`p28-human-gated-deploy-runbook.md`](./p28-human-gated-deploy-runbook.md) §2a.

**Until item 1 lands: Wave-2 deploys are manual-dispatch only** (already defaulted to `devx`), **and
no Wave-2 work merges to `main`** — merging today would still silently target the stack being
retired.

---

## 1. What Wave 2 contains

| # | Clause(s) | Plain-English step | Depends on | Detail |
|---|---|---|---|---|
| 2.0-RED / 2.0-GREEN | P-25 | Payment-provider port + a mock provider whose signature check is cryptographically real | Wave 1 | **full, below** |
| 2.0b | P-25b | Real Stripe provider + real signature verification | 2.0 | skeleton |
| 2.1 | P-14, P-15 | Don't process the same payment event twice; stop scanning the table on the money path | 2.0 | skeleton |
| 2.2 | P-16, P-17, P-18 | Stop silently losing queued work; bound concurrency; fix queue visibility timeouts | Wave 1 | skeleton |
| 2.3 | P-19 | Retry, heartbeat, and full jitter on the step-function workflows | Wave 1 | skeleton |
| 2.4 | P-20 | Raise the self-throttling API limit, sized from a real load measurement | Wave 1 | skeleton |
| 2.5 | P-02 | Fix the billing-reconcile entrypoint name mismatch | Wave 1 | skeleton |
| 2.7 | P-31 | Give scheduled-rule targets a dead-letter queue | Wave 1 | skeleton |
| GATE | — | Re-runnable wave demonstration + re-read all five bets | all | skeleton |

## 2. Serialization — which steps may not run at the same time

`infra/careervp/api_construct.py` is edited by **2.2, 2.4, and 2.7**. Never run two of those
concurrently — this is the rule Wave 1 violated when a commit titled as a CI change also edited that
file and silently made another step's change.

```
2.0-RED → 2.0-GREEN ─┬─→ 2.1 ─────────┐
                     │                 ├─→ GATE
                     └─→ 2.5 ──────────┤
                                       │
2.2 → 2.3 → 2.4 → 2.7 ─────────────────┘   (serial lane: all edit api_construct.py)

2.0b (freeze-line; before paid launch, NOT a GATE blocker)
```

The backend lane (2.0 → 2.1, 2.5) may run in parallel with the infrastructure lane.

**2.5 depends on 2.0 even though its diff is tiny.** It looks independent and is not: the
reconciliation service calls a provider method the port does not declare, and fixing its entrypoint
puts that call on a live schedule for the first time. See bet `B-2-5`.

### 2.1 — Documented order is not run order

**§1's table and the skeletons below are listed 2.0b, 2.1, 2.2, 2.3, 2.4, 2.5, 2.7 — that is
reading order, not execution order.** Running them top-to-bottom would be wrong in two ways:

- **The infra lane doesn't wait for 2.0 at all.** 2.2 → 2.3 → 2.4 → 2.7 depends only on Wave 1 and
  can start immediately — in parallel with 2.0-RED, not after it.
- **2.0b is written second but runs last, or later.** It's freeze-line — required before a *paid*
  launch, not before the GATE — so it can run any time after 2.0-GREEN, including after the wave
  closes. Reading it as "step two" and running it second would burn effort on real-Stripe work
  before the GATE actually needs it.

The one true ordering constraint is the diagram above. Concretely:

1. **2.0-RED → 2.0-GREEN** — sequential, blocks everything backend-side.
2. **In parallel with the above:** 2.2 → 2.3 → 2.4 → 2.7, strictly serial within itself (all edit
   `api_construct.py`), but this whole lane can start now.
3. **After 2.0-GREEN:** 2.1 and 2.5, in either order — both depend only on 2.0-GREEN, not on each
   other. (2.5 looks smaller but is not safer — see the note above.)
4. **GATE** once 2.0, 2.1, 2.2, 2.3, 2.4, 2.5, 2.7 are all done.
5. **2.0b** whenever, after 2.0-GREEN — before a paid launch, not before the GATE.

If two people or two sessions are available, the backend lane (step 1 above) and the infra lane
(step 2) are the actual parallelization opportunity this wave offers.

---

# PROMPT 2.0-RED — payment port + mock provider (tests only)

> **Clause:** P-25 · **Spec:** [`specs/P-25-payment-provider-spec.md`](../specs/P-25-payment-provider-spec.md)
> **Acceptance criteria:** AC-P25-1, AC-P25-2
> **Claude:** opus/high · **Codex:** gpt-5-codex/high (rule 15 — from `redesign-execution-plan.md` step 2.0)
> **Rule 7 applies — this is the money path.** RED and GREEN are two different sessions. This one
> writes tests only and carries an **absolute prohibition** on touching implementation files.

```
STANDING CHECK — before doing anything else: open runbooks/wave-2-status.md. This is the first
step of Wave 2, so there is no prior row; instead confirm the Wave-1 GATE row in
runbooks/wave-1-status.md actually says PASSED, and confirm it from git rather than from the
column — the Wave-1 GATE commit is a555e70 plus a docs-sync commit. Then confirm THIS step's own
prerequisites are met right now, using real commands (not memory, not this file):

  git log --oneline -3
  cd src/backend && uv run pytest tests/unit -q 2>&1 | tail -5
  ls careervp/payment_providers/

If the payment_providers package does not contain interface.py and placeholder.py, STOP and say so
in plain English.

BEFORE WRITING ANY TEST (rule 14): confirm, with a real command, that
docs/db-redesign/code/code-analysis/project/specs/P-25-payment-provider-spec.md exists, that its
"RED Tests to Write First" section names AC-P25-1 and AC-P25-2, and that each cited test states
exact assertion values (no "or", no undefined placeholders). This will most likely be true — the
spec was authored in Wave 0's step 0.4 fan-out, before Wave 2 began — but confirm it live rather
than trusting that history. If any of it is not true, STOP and say so; do not write tests against
a spec that does not say what it is testing.

You are implementing clause P-25, acceptance criteria AC-P25-1 and AC-P25-2, from
docs/db-redesign/code/code-analysis/project/specs/P-25-payment-provider-spec.md.

You are the RED session. You write TEST FILES ONLY. You may not edit any file under
src/backend/careervp/ except to READ it. Not temporarily, not "to see if it works." If you believe
an implementation file must change, write the test that proves it and stop.

--------------------------------------------------------------------------------
FIRST — settle three bets before writing any test. They are in ISSUES.md under "Wave-2 bets".
--------------------------------------------------------------------------------

BET B-2-5 ("billing already depends on the port, so this step is small") is ALREADY PARTLY FALSE,
and settling it first tells you how big this step actually is. Do this before anything else:

  1. Read src/backend/careervp/payment_providers/interface.py and list every method the
     PaymentProviderInterface Protocol declares.
  2. Read logic/billing_service.py and logic/webhook_service.py. Both inject the provider as
     `payment_provider: Any` — so strict type checking currently enforces NOTHING about the port.
  3. Change BOTH annotations from `Any` to `PaymentProviderInterface` and run:
        cd src/backend && uv run mypy careervp --strict
     Every call to a method the port does not declare will fail there.

  Two known ones already, both calling a method the Protocol DOES NOT DECLARE:
    - logic/webhook_service.py:115      retrieve_subscription(subscription_id)
    - logic/reconciliation_service.py:53  same call; its module docstring at :6 documents
                                          retrieve_subscription as part of the expected contract
  The Protocol declares exactly five methods: create_customer, create_checkout_session,
  create_portal_session, construct_webhook_event, get_price_map. The local variable in the webhook
  path is even named `stripe_sub`, so the concrete provider has already leaked into the consumer.
  This means AC-P25-1 ("billing logic uses the provider port, not concrete classes") currently
  reads as satisfied and is NOT.

  REPORT the full mismatch list before proceeding. If it is longer than those two call sites, say
  so plainly — that changes this step's size and the next session needs to know.

  NOTE the link to step 2.5: reconciliation_service is the consumer whose scheduled entrypoint has
  never run because of a handler-name mismatch. So a call to an undeclared port method has never
  executed in a deployed environment. Whoever fills in 2.5 must read this finding first — fixing
  the entrypoint before the port is reconciled puts that call on a live schedule for the first time.

  Then REVERT the annotation change. You are the RED session; that edit belongs to GREEN. You made
  it only to run the type checker as a diagnostic.

BET B-2-1 ("the mock's signature scheme is a faithful stand-in for Stripe's") decides the shape of
two of your tests. The port declares:

    construct_webhook_event(payload: bytes, signature: str, secret: str) -> WebhookEvent

`signature` is a SINGLE string. Stripe's real header is compound — a timestamp and one or more
digests in one value (`t=<unix>,v1=<hex>`), and replay rejection reads the timestamp OUT of that
header. Write your tests so the mock MUST parse timestamp and digest from that one compound string
and from nowhere else. If you instead write "bare hex digest, timestamp passed separately," the
replay test will be satisfiable by the mock and unsatisfiable by Stripe, and step 2.0b will rewrite
every test you are about to write.

BET B-2-2 ("the provider's event id is a stable, safe idempotency key") is the worst available
failure in this wave, so test it directly rather than assuming it. Note that webhook_service.py
ALREADY keys idempotency on event.event_id via record_payment_event(...), with commit-after-work
and a delete_payment_event release on failure. So the mechanism is partly built already — against a
mock that does not exist yet. If your mock issues a FRESH id per delivery attempt where Stripe
reuses ONE id across retries of the same event, every duplicate-suppression test will pass while the
real system double-charges on a provider retry.

--------------------------------------------------------------------------------
THEN — write these tests, and only these
--------------------------------------------------------------------------------

From the spec's "RED Tests to Write First", scoped to P-25 (the two P-25b tests belong to 2.0b):

  test_p25_billing_service_depends_on_provider_interface_only
      Inject a fake provider satisfying the Protocol; assert billing uses port methods only and
      names no concrete provider class. Cite AC-P25-1.

  test_p25_mock_webhook_rejects_tampered_signature
      Sign a payload, mutate the body, assert verification raises PaymentProviderError. Cite
      AC-P25-2.

  test_p25_mock_webhook_rejects_replay_timestamp
      A correctly-signed payload whose timestamp is outside tolerance must fail with a distinct
      replay error — timestamp read from the compound signature string. Cite AC-P25-2.
      State the exact tolerance as a named constant. No "or"-shaped assertions, no undefined
      values (spec_time_lint, project-scope-lock.yaml spec_test_acceptance).

  RESOLVED 2026-07-25 (was an open question in this prompt): test_p25_mock_event_id_is_stable_
  across_retries belongs to 2.1, NOT here. Do not write it in this session — see 2.1's skeleton
  below, which now owns it explicitly. Reasoning: this is a claim about the MockProvider's own
  retry behavior (an implementation detail 2.0-GREEN builds), and the thing actually load-bearing
  for bet B-2-2 is whether 2.1's idempotency wiring correctly consumes whatever id shape the
  provider emits — that is 2.1's job to prove, against a real table, not 2.0's job to prove against
  its own mock in isolation. Writing it here would test the mock against itself.

  test_p25_checkout_portal_contract_shape_preserved
      Assert checkout and portal responses carry the same URL fields the frontend consumes. Derive
      those from src/frontend, NOT from swagger — swagger is non-authoritative
      (project-scope-lock.yaml, non_authoritative).

RULE 13 — a test that has not been observed to fail is not a test. Run every test above and
capture the failure output VERBATIM. For each, state WHY it failed. A test failing on ImportError,
a collection error, or a missing fixture is NOT RED — it is broken, and it will go green later for
reasons unrelated to the fix. The mock provider does not exist yet, so an ImportError is the
expected FIRST result: structure the tests (or a minimal conftest skip-guard) so that each one
fails on ITS OWN ASSERTION, not on the import. Say explicitly which technique you used.

No real network calls in any test. Secrets stay under the P-06 rules — parameter NAME in the
environment, value fetched at runtime, never a literal.

--------------------------------------------------------------------------------
OUTPUT REQUIRED
--------------------------------------------------------------------------------
1. Confirmation (rule 14) that the spec existed, named AC-P25-1/AC-P25-2, and stated exact
   assertion values — or, if it did not, what you found and where you stopped.
2. The B-2-5 mismatch list (every port violation strict type checking found), in plain English
   first. Update the B-2-5 row in ISSUES.md with what you actually found.
3. Your B-2-1 decision: the exact signature-string format the tests require, written so 2.0b can
   check Stripe against it. Update B-2-1 in ISSUES.md.
4. Verbatim failure output for every test, with a one-line why for each.
5. Confirmation that ZERO files under src/backend/careervp/ were modified (`git diff --stat`).
6. A git commit message.

ALSO REQUIRED (standing rule for every wave prompt — see runbooks/RUNBOOK-RULES.md):
- Compare what you actually built against (a) this prompt's own instructions and (b) clause P-25
  in project-scope-lock.yaml. If everything matches, say so in one plain sentence.
- If ANYTHING drifted — extra work not asked for, required work skipped, or a test/rule had to be
  weakened — STOP. Do not fix it yourself. Write one plain-English sentence a non-engineer could
  follow (what should have happened, what actually happened, why it matters), THEN the technical
  detail, and flag it for human review. Do not mark the step done.
- Update runbooks/wave-2-status.md: add/update this step's row with a plain-English status, the
  commit, today's date, and anything the NEXT step must resolve first (or write "none").
```

---

# PROMPT 2.0-GREEN — make them pass

> **Clause:** P-25 · **Acceptance criteria:** AC-P25-1, AC-P25-2
> **Claude:** opus/high · **Codex:** gpt-5-codex/high (rule 15 — from `redesign-execution-plan.md` step 2.0)
> Run in a **FRESH session** that has not seen 2.0-RED's reasoning. `/clear` is the minimum; a
> separate invocation is preferred. The failing tests are a contract you did not write and **may
> not edit** — that clause is the entire firewall. No relaxing an assertion, no `xfail`, no `skip`.
> If a test looks genuinely *wrong* (not merely inconvenient), STOP and raise a §0.3 amendment.

```
STANDING CHECK — before doing anything else: open runbooks/wave-2-status.md and read the 2.0-RED
row. If it left anything open, deal with that FIRST. Confirm the RED tests exist and fail, right
now, with a real command — do not trust the ledger:

  cd src/backend && uv run pytest tests/unit/test_p25_payment_provider.py -q 2>&1 | tail -20

If they pass, or fail on import/collection errors rather than their own assertions, STOP.

You are implementing clause P-25 (AC-P25-1, AC-P25-2). You are the GREEN session. You may not edit
any test file written by 2.0-RED. Build:

1. MockProvider (careervp/payment_providers/mock_provider.py) implementing every method the
   PaymentProviderInterface Protocol declares, with a cryptographically real HMAC verification —
   compound signature string, timestamp parsed from it, replay rejection outside tolerance.
   Tampered body must fail. This is the whole point: a tautological check makes the negative test
   meaningless.
2. Reconcile the port with its actual consumers. The 2.0-RED row lists the mismatches strict type
   checking found. Both billing_service.py and webhook_service.py must be annotated
   `PaymentProviderInterface`, not `Any`, and must pass `mypy --strict`. Where a consumer calls a
   method the Protocol does not declare, the RIGHT fix is to add it to the Protocol — the port
   should describe what billing actually needs. Do not delete a working call to make types pass.
3. Preserve the checkout and portal response shapes the frontend consumes.

VERIFY: full backend unit + integration suites; ruff; mypy --strict; the coverage gate
(`make coverage-tests`, must stay at or above the enforced baseline); scope-diff.py reports P-25.
No deploy in this step — 2.0 is backend-only.

OUTPUT REQUIRED
1. Every RED test now passing, with output.
2. Confirmation that ZERO test files were modified (`git diff --stat` on the test paths).
3. The final Protocol method list, and which methods you ADDED to it and why.
4. A git commit message.

ALSO REQUIRED (standing rule for every wave prompt — see runbooks/RUNBOOK-RULES.md):
- Compare what you actually built against (a) this prompt's own instructions and (b) clause P-25
  in project-scope-lock.yaml. If everything matches, say so in one plain sentence.
- If ANYTHING drifted, STOP, write the plain-English sentence first, then the technical detail,
  and flag it for human review. Do not mark the step done.
- Update runbooks/wave-2-status.md with a plain-English status, the commit, today's date, and
  anything the NEXT step must resolve first (or write "none"). Also update the B-2-1, B-2-2 and
  B-2-5 rows in ISSUES.md with what is now settled.
```

---

---

# SKELETONS — fill in one at a time, when its dependencies have landed

Each skeleton below is **contractual**: its clause ids, acceptance-criteria ids, and done-when come
from `project-scope-lock.yaml` and the spec files. Filling one in means expanding it into a full
prompt in the shape of 2.0 above — adding the standing-check block, the concrete commands, and the
two standard output blocks — **without changing anything already written here.** If you cannot fill
it in without widening its clause, that is a rule-5 stop.

**Before filling in any skeleton:** read every ledger row above it in `wave-2-status.md`, and
re-read the bets it lists. Earlier steps will have found things this file could not know.

> **Fill-in progress:** 2.0b, 2.0b-mock, **2.1**, **2.5**, and **2.5a** are **already filled in**
> (each has its full prompt(s) below, immediately after its summary table) — 2.0-GREEN unblocked 2.0b and 2.1,
> 2.0b-GREEN (landed 2026-07-25) unblocked 2.0b-mock, 2.0b-mock-GREEN (landed 2026-07-25) was the last
> backend prerequisite before 2.1, and 2.1-GREEN (landed 2026-07-25) closed the 2.0→2.1 backend spine.
> 2.5 (P-02, filled in 2026-07-25) stopped correctly when its small RED-first change exposed larger
> runtime blockers; 2.5a-RED landed those blockers in `ec690b7`, and 2.5a-GREEN was filled in on
> 2026-07-25 from that immutable RED evidence. 2.2, 2.3, 2.4, and 2.7 (the infra lane) remain
> skeletons.

---

## 2.0b — Real payments

> **FILLED IN 2026-07-25** from the skeleton below (rule 11). The session that did so read the
> 2.0-RED and 2.0-GREEN ledger rows first; what those steps actually built is baked in below (the
> mock's centralized signature constants, the port now carrying `retrieve_subscription`). Split into
> RED and GREEN per rule 7 — this is the money path, and its freeze-line is the highest
> cost-of-being-wrong step in the wave.
>
> **Header values corrected against the plan, not copied from the stale skeleton.** The skeleton's
> `Claude / Codex` line read `opus/high · gpt-5-codex/high`. Both the execution-plan row 2.0b and
> the `P-25b` spec frontmatter now read **`opus/xhigh · gpt-5.3-codex/max`** (2026-07-25 taxonomy
> resolution — rule 16 wins, and 2.0b is `max` for "hardest quality-first work where the extra cost
> is justified by clear evaluation criteria: security-critical design review"). The corrected values
> are used below; the skeleton's were stale.

| | |
|---|---|
| **Clause** | P-25b |
| **Spec** | `specs/P-25-payment-provider-spec.md` |
| **Acceptance criteria** | AC-P25b-1 |
| **Claude / Codex** | opus/xhigh · gpt-5.3-codex/max |
| **Depends on** | 2.0-GREEN (landed — `MockProvider` + port `retrieve_subscription` in `a654821`) |
| **Deploy target** | none (backend only — no CDK, no devx deploy, so `B-2-4` does not gate this) |
| **Rule 7** | RED and GREEN separate — money path |
| **Bets** | `B-2-1` (settled by 2.0 at the mock level; this step is where it is *proven* against real Stripe) |

**In plain English.** Build the real Stripe provider and its real signature verification, so a paid
launch is not running untested verification code on the money path. This is a freeze-line: it is
required before any *paid* launch, **not** before the Wave-2 GATE, and it may not be skipped on the
grounds that the mock works.

**⚠️ rule-14 gap you must close FIRST.** The spec's two P-25b RED-test descriptions
(`test_p25b_stripe_provider_verifies_real_signature`, `test_p25b_paid_launch_gate_fails_without_stripe_provider`)
do **not** name exact assertion values — "assert valid passes and invalid fails" is not an exact
assertion. Per rule 14 you may not write tests against a spec that does not say what it is testing.
So 2.0b-RED's literal first task is to tighten those two descriptions in the spec (authoring the
test brief, which is allowed — it is the spec's RED-test section, not a scope-lock clause change),
using the concrete Stripe scheme the cross-check below confirms. Only then write the tests.

---

# PROMPT 2.0b-RED — real Stripe signature verification + launch gate (tests only)

> **Clause:** P-25b · **Spec:** [`specs/P-25-payment-provider-spec.md`](../specs/P-25-payment-provider-spec.md)
> **Acceptance criteria:** AC-P25b-1 · **Claude: opus/xhigh · Codex: gpt-5.3-codex/max**
> **Rule 7 applies — money path.** RED and GREEN are two different sessions. This one writes tests
> only and carries an **absolute prohibition** on touching implementation files.

```
STANDING CHECK — before doing anything else: open runbooks/wave-2-status.md and read the 2.0-RED and
2.0-GREEN rows. If either left something open, deal with it FIRST. Then confirm THIS step's
prerequisites are met right now, with real commands (not memory, not this file):

  cd src/backend && uv run pytest tests/unit/test_p25_payment_provider_port.py -q 2>&1 | tail -5
  ls careervp/payment_providers/           # interface.py + mock_provider.py must exist; stripe_provider.py must NOT
  python -c "from careervp.payment_providers.mock_provider import WEBHOOK_TIMESTAMP_TOLERANCE_SECONDS; print(WEBHOOK_TIMESTAMP_TOLERANCE_SECONDS)"

If the four P-25 tests are not green, or stripe_provider.py already exists, STOP and say so plainly.

BEFORE WRITING ANY TEST (rule 14): open specs/P-25-payment-provider-spec.md and confirm its
"RED Tests to Write First" section names AC-P25b-1's two tests. It does — but their descriptions do
NOT name exact assertion values, which rule 14 forbids writing tests against. Your FIRST task is to
tighten those two descriptions in the spec, then write the tests to match. Do not widen AC-P25b-1
or add clauses — you are authoring the test brief, not changing the contract (if you find you must
change AC-P25b-1 itself, that is a rule-5 stop + a §0.3 amendment, not an edit).

You are implementing clause P-25b (AC-P25b-1). You are the RED session: TEST FILES + the spec's
RED-test-brief tightening ONLY. You may not create or edit any file under
src/backend/careervp/payment_providers/ or any billing logic file, even "to see if it works."

--------------------------------------------------------------------------------
FIRST — the B-2-1 Stripe cross-check (settle it before tightening the spec)
--------------------------------------------------------------------------------

2.0-GREEN centralized the mock's signature constants in mock_provider.py:
  - compound header  t=<unix>,v1=<hex>   (WEBHOOK_SIGNATURE_MALFORMED on a bad shape)
  - signed payload   HMAC-SHA256(secret, f"{t}.{raw_payload_bytes}")   (period-joined, raw body)
  - replay window    WEBHOOK_TIMESTAMP_TOLERANCE_SECONDS = 300
  - distinct codes   WEBHOOK_TIMESTAMP_OUT_OF_TOLERANCE vs WEBHOOK_SIGNATURE_VERIFICATION_FAILED

Verify EACH against Stripe's own documented Stripe-Signature scheme (the official docs / SDK, not
the mock — the mock is what is being checked):
  1. Header format is t=<unix>,v1=<hex>[,v0=...]; the mock tolerates extra pairs — confirm that
     matches Stripe (rotation sends multiple v1). 
  2. Signed payload is exactly "{timestamp}.{payload}" over the RAW body bytes — confirm the mock
     builds the identical string, not payload-then-timestamp or a different separator.
  3. Default tolerance is 300s and is a value the CALLER reconstructs verification with (not one only
     Stripe's servers enforce).
Record the result in ISSUES.md's B-2-1 row. If all three match, B-2-1 is confirmed and StripeProvider
can verify against the same scheme the mock's tests already exercise. If ANY diverges, StripeProvider
must implement Stripe's real behavior (never inherit the mock's to "stay consistent"), that finding
is what proves B-2-1 FALSE rather than settled, and you note that 2.0-GREEN's mock tests need a
follow-up fix — flag it, do not fix it here.

--------------------------------------------------------------------------------
THEN — tighten the spec's two P-25b RED-test descriptions, then write exactly these tests
--------------------------------------------------------------------------------

Write them in src/backend/tests/unit/test_p25b_stripe_provider.py. Cite AC-P25b-1 in each. Derive
every assertion value from the cross-check above — no "or"-shaped assertions, no undefined
placeholders (spec_time_lint, project-scope-lock.yaml spec_test_acceptance).

  test_p25b_stripe_provider_verifies_real_signature
      Build a VALID Stripe-format header (t=<now>,v1=HMAC-SHA256(secret,"{t}.{payload}")) over a
      known payload with a test secret (a fixture secret, NOT a literal in the test body — P-06:
      parameter NAME in env, value at runtime). Assert StripeProvider.construct_webhook_event returns
      a WebhookEvent whose event_id/event_type match the payload. THEN, three distinct negatives,
      each asserting a DISTINCT error (not a generic "raises"):
        - tampered body (valid header, mutated payload)  -> signature-verification-failed code
        - wrong secret                                    -> signature-verification-failed code
        - stale timestamp within a valid digest           -> replay/out-of-tolerance code
      No real network call — signature verification is local HMAC. Do NOT call any Stripe API method.

  test_p25b_paid_launch_gate_fails_without_stripe_provider
      This is the FREEZE-LINE mechanism, and it must be able to fail (rule 13). Assert, structurally:
        (a) careervp.payment_providers.stripe_provider.StripeProvider is importable and structurally
            satisfies PaymentProviderInterface (all port methods present, including
            retrieve_subscription); AND
        (b) the three signature negatives above exist AND pass.
      Because StripeProvider does not exist yet, guard the import INSIDE the test and assert on its
      absence so the test fails on ITS OWN ASSERTION (a clear "StripeProvider missing → launch gate
      fails" message), NOT on a bare collection-time ImportError. State which technique you used.

RULE 13 — run every test, capture the failure output VERBATIM, and for each state WHY it failed. A
test that fails on ImportError/collection/missing-fixture is NOT red, it is broken; structure the
tests (or a minimal skip-guard) so each fails on its own assertion. The mock's four tests must STILL
be green after your run — you have added tests, not touched theirs.

--------------------------------------------------------------------------------
OUTPUT REQUIRED
--------------------------------------------------------------------------------
1. The B-2-1 cross-check result (match / diverge, per the three points), in plain English first;
   update the B-2-1 row in ISSUES.md.
2. The tightened P-25b RED-test descriptions as they now read in the spec (diff of that section).
3. The new test file, each assertion cited to AC-P25b-1.
4. Verbatim failure output for every new test + one-line why for each, AND proof the four P-25 mock
   tests are still green.
5. Confirmation that ZERO files under src/backend/careervp/ were modified (git diff --stat).
6. A git commit message.

ALSO REQUIRED (standing rule for every wave prompt — see runbooks/RUNBOOK-RULES.md):
- Compare what you actually built against (a) this prompt's own instructions and (b) clause P-25b
  in project-scope-lock.yaml. If everything matches, say so in one plain sentence.
- If ANYTHING drifted — extra work not asked for, required work skipped, or a test/rule had to be
  weakened — STOP. Do not fix it yourself. Write one plain-English sentence a non-engineer could
  follow (what should have happened, what actually happened, why it matters), THEN the technical
  detail, and flag it for human review. Do not mark the step done.
- Update runbooks/wave-2-status.md: add/update this step's row with a plain-English status, the
  commit, today's date, and anything the NEXT step must resolve first (or write "none").
```

---

# PROMPT 2.0b-GREEN — build StripeProvider, make the freeze-line hold

> Run in a **FRESH session** that has not seen 2.0b-RED's reasoning. `/clear` is the minimum; a
> separate invocation is preferred. The failing tests are a contract you did not write and **may not
> edit** — no relaxing an assertion, no `xfail`, no `skip`. If a test looks genuinely *wrong* (not
> merely inconvenient), STOP and raise a §0.3 amendment.
> **Clause:** P-25b · **Claude: opus/xhigh · Codex: gpt-5.3-codex/max**
>
> **CORRECTION (2026-07-25) — this step is NOT blocked by the MockProvider rotation gap.** A first
> GREEN attempt stopped, reading 2.0b-RED's ledger note ("resolve the mock rotation gap before
> continuing") as a hard prerequisite. Verified against the landed tests, it is not: both P-25b RED
> tests in `test_p25b_stripe_provider.py` exercise **`StripeProvider` only** (`provider =
> StripeProvider()`; the shared `_assert_signature_negatives` helper is always called with
> `provider.construct_webhook_event`). Neither references `MockProvider`. So this session builds
> StripeProvider self-contained and makes both tests pass with **zero mock edits and zero test
> edits**. The mock's proven multi-`v1` divergence (B-2-1) is real and has its own follow-up
> (skeleton `2.0b-mock` below — B-2-1's pre-committed fallback "make the mock conform"); it does
> **not** gate StripeProvider and must **not** be attempted inside this GREEN session.

```
STANDING CHECK — before doing anything else: open runbooks/wave-2-status.md and read the 2.0b-RED
row. It flags a proven MockProvider multi-v1 divergence — that is tracked as follow-up 2.0b-mock and
is NOT a prerequisite for this step (see the CORRECTION note above): the two P-25b tests exercise
StripeProvider only, so you build StripeProvider self-contained and touch neither mock_provider.py
nor any test file. Do not attempt the mock fix here. Confirm the RED tests exist and fail, right
now, with a real command:

  cd src/backend && uv run pytest tests/unit/test_p25b_stripe_provider.py -q 2>&1 | tail -20

If they pass, or fail on import/collection errors rather than their own assertions, STOP.

You are implementing clause P-25b (AC-P25b-1). You are the GREEN session. You may not edit the RED
test file, and you may not edit mock_provider.py (its rotation gap is 2.0b-mock's job, not yours).
Build:

1. careervp/payment_providers/stripe_provider.py — StripeProvider implementing
   PaymentProviderInterface (all methods the port declares, including retrieve_subscription).
   construct_webhook_event must verify the REAL Stripe signature scheme confirmed by 2.0b-RED's
   cross-check — INCLUDING the multi-v1 rotation behavior the cross-check proved the mock lacks:
     - Parse ALL v1 digests out of the compound header (Stripe emits one per active secret during
       rotation) and ACCEPT if ANY of them matches the computed HMAC — this is exactly the case the
       RED test's `_stripe_signature_header` puts the matching digest in the SECOND v1 slot to prove.
       Do NOT copy the mock's first-v1-only parse; that is the divergence being fixed here for
       StripeProvider (and, separately, for the mock in 2.0b-mock).
     - PREFER the official `stripe` SDK's verification (stripe.Webhook.construct_event /
       WebhookSignature.verify_header) IF `stripe` is already a project dependency. If it is NOT a
       dependency, that is a decision, not a default: adding a runtime dependency to the money path
       is a rule-5 flag — either implement Stripe's DOCUMENTED v1 HMAC scheme directly (the compound
       header + `{t}.{payload}` signing the cross-check validated, WITH multi-v1 acceptance) OR
       propose the dependency to the human. Do not silently `uv add stripe`. State which path you
       took and why. (Note: the official SDK handles multi-v1 for you; the direct path must
       implement it explicitly.)
     - Distinct error codes for tamper/wrong-secret vs replay/stale-timestamp, matching what the RED
       tests assert (WEBHOOK_SIGNATURE_VERIFICATION_FAILED vs WEBHOOK_TIMESTAMP_OUT_OF_TOLERANCE).
   The API-call methods (create_customer, create_checkout_session, retrieve_subscription, …) wrap
   real Stripe calls and are NOT exercised in unit tests (no network in tests); they must be present,
   typed, and pass mypy --strict, with Stripe errors mapped to PaymentProviderError. The signature
   path is the tested freeze-line.
2. Make test_p25b_paid_launch_gate_fails_without_stripe_provider PASS — StripeProvider now imports
   and satisfies the port, and the three signature negatives pass.

Secrets stay under P-06: the webhook secret is passed by value (resolved from the parameter store by
NAME upstream); no literal secret in the module. No real network call in any test.

VERIFY: the two P-25b tests pass AND the four P-25 mock tests still pass; full backend unit +
integration suites (zero regressions); ruff; mypy careervp --strict; the coverage gate
(make coverage-tests, at/above the enforced baseline); scope-diff reports P-25b.

OUTPUT REQUIRED
1. Both P-25b tests passing + the four P-25 tests still green, with output.
2. Confirmation that ZERO test files were modified (git diff --stat on tests/).
3. The signature-verification path you chose (official SDK vs documented-scheme direct) and the
   dependency decision, stated plainly.
4. A git commit message.

ALSO REQUIRED (standing rule for every wave prompt — see runbooks/RUNBOOK-RULES.md):
- Compare what you actually built against (a) this prompt's own instructions and (b) clause P-25b
  in project-scope-lock.yaml. If everything matches, say so in one plain sentence.
- If ANYTHING drifted, STOP, write the plain-English sentence first, then the technical detail, and
  flag it for human review. Do not mark the step done.
- Update runbooks/wave-2-status.md with a plain-English status, the commit, today's date, and
  anything the NEXT step must resolve first. In particular, record that StripeProvider now handles
  multi-v1 rotation correctly, but that B-2-1 stays FALSE until 2.0b-mock lands (the MockProvider
  still has the first-v1-only gap) — do not mark B-2-1 settled here.
- FREEZE-LINE confirmation (rule 5): state explicitly whether any part of the signature-verification
  path is untested when this session ends. If it is, that is a STOP condition, not a note for later
  — a paid launch must not run untested verification code (AC-P25b-1).
```

---

## 2.0b-mock — MockProvider multi-`v1` rotation conformance

> **FILLED IN 2026-07-25** from the skeleton below (rule 11). The session that did so read the
> 2.0-RED/GREEN and 2.0b-RED/GREEN ledger rows first and verified the mock's and StripeProvider's
> signature parsers live: `MockProvider._parse_signature` (`mock_provider.py:168`) keeps only the
> first `v1` (`elif key == 'v1' and value and digest is None:`), while `StripeProvider`
> (`stripe_provider.py:129`) already does `any(hmac.compare_digest(...) for provided_digest in
> provided_digests)` over ALL `v1` digests. This step brings the mock to that same behavior. Split
> into RED and GREEN per rule 7 — webhook verification is on the money path.
>
> **Header values (rule 16, no plan row).** `2.0b-mock` is a runbook-authored fallback, not a row in
> `redesign-execution-plan.md`, so its model tier is picked here, not copied. It stays
> **`sonnet/medium · gpt-5.3-codex/medium`**: the change is a small, mechanical mirror of
> already-landed, already-reviewed StripeProvider logic into a test-only provider that is INERT in
> production (nothing feeds the mock a multi-`v1` header). This is well below the `xhigh`/`max` bar
> that 2.0b's from-scratch real-Stripe verification earned. It is NOT `low`: it is still money-path
> webhook-verification code and a bet closure, so it gets a careful tier, not a cheap one.

| | |
|---|---|
| **Clause** | P-25 (MockProvider hardening) — executes bet `B-2-1`'s pre-committed fallback |
| **Spec** | `specs/P-25-payment-provider-spec.md` (add one RED-test brief; do not widen any AC) |
| **Acceptance criteria** | AC-P25-2 (webhook verification correctness) |
| **Claude / Codex** | sonnet/medium · gpt-5.3-codex/medium |
| **Depends on** | 2.0-GREEN landed (`a654821`). **File-isolated from 2.0b-GREEN** (`mock_provider.py` + `test_p25_payment_provider_port.py` vs `stripe_provider.py` + `test_p25b_stripe_provider.py`) — parallel-safe, but recommended AFTER 2.0b-GREEN (landed) since StripeProvider was the freeze-line. |
| **Deploy target** | none (backend only — no CDK, no devx deploy) |
| **Rule 7** | RED and GREEN separate — money path (webhook verification) |
| **Bets** | `B-2-1` — this step is what flips it from FALSE back to TRUE |

**Why this exists.** 2.0b-RED's cross-check proved `MockProvider._parse_signature` takes only the
FIRST `v1` digest and rejects a header whose matching digest is a later `v1` — but Stripe emits
multiple `v1` values during secret rotation and accepts if ANY matches. So the mock is not a
faithful stand-in for the rotation case (bet `B-2-1` is FALSE). It is currently **inert** — no
test or consumer feeds the mock a multi-`v1` header, so no existing test is wrong — but B-2-1's
written fallback is "make the mock conform to Stripe," and this step discharges it so B-2-1 can be
marked TRUE at the GATE (rule 9 re-reads it there).

**In plain English.** Teach the mock the same rotation rule the real Stripe provider already got in
2.0b-GREEN: when a webhook signature carries several candidate signatures, accept it if any one of
them matches, not only the first.

---

# PROMPT 2.0b-mock-RED — mock multi-`v1` rotation (test only)

> **Clause:** P-25 · **Spec:** [`specs/P-25-payment-provider-spec.md`](../specs/P-25-payment-provider-spec.md)
> **Acceptance criteria:** AC-P25-2 · **Claude: sonnet/medium · Codex: gpt-5.3-codex/medium**
> **Rule 7 applies — money path.** RED and GREEN are two different sessions. This one writes a test
> only and carries an **absolute prohibition** on touching implementation files.

```
STANDING CHECK — before doing anything else: open runbooks/wave-2-status.md and read the 2.0-GREEN,
2.0b-RED, and 2.0b-GREEN rows. All three must show landed/green. Then confirm THIS step's
prerequisites are met right now, with real commands (not memory, not this file):

  cd src/backend && uv run pytest tests/unit/test_p25_payment_provider_port.py tests/unit/test_p25b_stripe_provider.py -q 2>&1 | tail -5
  grep -n "digest is None" careervp/payment_providers/mock_provider.py     # the first-v1-only guard must still be present
  grep -n "any(hmac.compare_digest" careervp/payment_providers/stripe_provider.py   # StripeProvider's multi-v1 accept, the behavior you are mirroring

If the four P-25 mock tests + two P-25b StripeProvider tests are not all green, or the mock no longer
has the single-v1 guard, STOP and say so plainly — the premise (B-2-1 FALSE at the mock) has changed.

BEFORE WRITING ANY TEST (rule 14): open specs/P-25-payment-provider-spec.md, "RED Tests to Write
First". It does NOT yet name this rotation test with exact assertion values. Your FIRST task is to
add exactly ONE tightened RED-test brief for `test_p25_mock_webhook_accepts_matching_second_v1`
naming exact assertion values (the compound header shape, which v1 slot holds the matching digest,
and the exact success assertion — the returned WebhookEvent's event_id/event_type). This is
authoring the spec's RED-test brief, which is allowed; do NOT widen AC-P25-2 or add a clause. If you
find you must change AC-P25-2 itself, that is a rule-5 stop + a §0.3 amendment, not an edit.

You are implementing clause P-25 (AC-P25-2). You are the RED session: TEST FILE + the spec's
RED-test-brief tightening ONLY. You may not create or edit any file under
src/backend/careervp/payment_providers/, even "to see if it works."

--------------------------------------------------------------------------------
Write exactly this test — in test_p25_payment_provider_port.py (the mock's own file), NOT in
test_p25b_stripe_provider.py (that is StripeProvider's and off-limits)
--------------------------------------------------------------------------------

  test_p25_mock_webhook_accepts_matching_second_v1
      Sign a known payload with a test secret (a fixture secret, NOT a literal in the test body —
      P-06: parameter NAME in env, value resolved at runtime). Build a compound header
      `t=<now>,v1=<non-matching-garbage>,v1=<the real HMAC-SHA256(secret,"{t}.{payload}")>` — the
      MATCHING digest in the SECOND v1 slot, exactly the rotation case. Assert
      `MockProvider.construct_webhook_event(payload, header, secret)` returns a WebhookEvent whose
      event_id and event_type match the payload. Cite AC-P25-2.

      This must FAIL today on its OWN assertion, not on an import or collection error: the mock
      currently keeps only the first v1 (the garbage), so it raises PaymentProviderError with code
      WEBHOOK_SIGNATURE_VERIFICATION_FAILED. Capture that verbatim (rule 13) and say so.

RULE 13 — run the test, capture the failure output VERBATIM, and state WHY it failed (matching digest
is in the second v1 slot; mock reads only the first). A failure on ImportError/collection/missing
fixture is NOT red — structure the test so it fails on its assertion. The four existing P-25 mock
tests and both P-25b StripeProvider tests must STILL be green after your run — you added one test,
touched no implementation.

No real network calls. Secrets under P-06 (parameter NAME in env, value at runtime, never a literal).

--------------------------------------------------------------------------------
OUTPUT REQUIRED
--------------------------------------------------------------------------------
1. The tightened P-25 RED-test brief as it now reads in the spec (diff of that section).
2. The new test, cited to AC-P25-2.
3. Verbatim failure output + one-line why, AND proof the four P-25 + two P-25b tests are still green.
4. Confirmation that ZERO files under src/backend/careervp/ were modified (git diff --stat).
5. A git commit message.

ALSO REQUIRED (standing rule for every wave prompt — see runbooks/RUNBOOK-RULES.md):
- Compare what you actually built against (a) this prompt's own instructions and (b) clause P-25 in
  project-scope-lock.yaml. If everything matches, say so in one plain sentence.
- If ANYTHING drifted — extra work not asked for, required work skipped, or a test/rule had to be
  weakened — STOP. Do not fix it yourself. Write one plain-English sentence a non-engineer could
  follow (what should have happened, what actually happened, why it matters), THEN the technical
  detail, and flag it for human review. Do not mark the step done.
- Update runbooks/wave-2-status.md: add/update this step's row with a plain-English status, the
  commit, today's date, and what GREEN must resolve first. B-2-1 stays FALSE until GREEN lands.
```

---

# PROMPT 2.0b-mock-GREEN — make the mock accept any matching `v1`

> Run in a **FRESH session** that has not seen 2.0b-mock-RED's reasoning. `/clear` is the minimum; a
> separate invocation is preferred. The failing test is a contract you did not write and **may not
> edit** — no relaxing an assertion, no `xfail`, no `skip`. If the test looks genuinely *wrong* (not
> merely inconvenient), STOP and raise a §0.3 amendment.
> **Clause:** P-25 · **Claude: sonnet/medium · Codex: gpt-5.3-codex/medium**

```
STANDING CHECK — before doing anything else: open runbooks/wave-2-status.md and read the
2.0b-mock-RED row. If it left anything open, deal with it FIRST. Confirm the RED test exists and
fails, right now, with a real command — do not trust the ledger:

  cd src/backend && uv run pytest tests/unit/test_p25_payment_provider_port.py -q -k second_v1 2>&1 | tail -20

If it passes, or fails on import/collection errors rather than its own assertion, STOP.

You are implementing clause P-25 (AC-P25-2). You are the GREEN session. You may not edit the RED test
file, and you may not edit stripe_provider.py or test_p25b_stripe_provider.py (that is a different
step's file set). Build ONLY the mock change:

1. Fix careervp/payment_providers/mock_provider.py so `_parse_signature` (or its replacement) collects
   ALL `v1` digests from the compound header, and `construct_webhook_event` ACCEPTS when ANY of them
   matches the computed HMAC in constant time — mirroring StripeProvider's landed
   `any(hmac.compare_digest(expected, d) for d in provided_digests)` at stripe_provider.py:129. Keep
   the timestamp parse, the 300 s replay window (WEBHOOK_TIMESTAMP_OUT_OF_TOLERANCE), the malformed-
   header code (WEBHOOK_SIGNATURE_MALFORMED), and the verification-failed code
   (WEBHOOK_SIGNATURE_VERIFICATION_FAILED) exactly as they are — you are widening acceptance from
   first-v1 to any-v1, not changing any other behavior. A header with NO matching v1 must still fail
   with WEBHOOK_SIGNATURE_VERIFICATION_FAILED; a header missing t or all v1 must still be MALFORMED.

Do NOT change the constants, the WebhookEvent shape, or any other method. This is a webhook-
verification correctness fix, nothing else.

VERIFY: the new rotation test passes AND the four existing P-25 mock tests AND the two P-25b
StripeProvider tests still pass; full backend unit + integration suites (zero regressions); ruff;
mypy careervp --strict; the coverage gate (make coverage-tests, at/above the enforced baseline);
scope-diff reports P-25.

OUTPUT REQUIRED
1. The rotation test now passing + the four P-25 and two P-25b tests still green, with output.
2. Confirmation that ZERO test files were modified (git diff --stat on tests/), and that
   stripe_provider.py was NOT touched.
3. The mock signature-parse change, stated plainly (first-v1-only -> any-v1), and confirmation it
   mirrors StripeProvider rather than diverging.
4. A git commit message.

ALSO REQUIRED (standing rule for every wave prompt — see runbooks/RUNBOOK-RULES.md):
- Compare what you actually built against (a) this prompt's own instructions and (b) clause P-25 in
  project-scope-lock.yaml. If everything matches, say so in one plain sentence.
- If ANYTHING drifted, STOP, write the plain-English sentence first, then the technical detail, and
  flag it for human review. Do not mark the step done.
- Update runbooks/wave-2-status.md with a plain-English status, the commit, today's date, and
  "none" for the next step. **Flip B-2-1 to TRUE in ISSUES.md** with the evidence (mock now accepts
  any matching v1, mirroring StripeProvider; both providers now faithful to Stripe's rotation
  behavior). This is the one step authorized to settle B-2-1 — the GATE re-reads it (rule 9).
```

**Done-when.** The new mock rotation test passes; the four P-25 + two P-25b tests still pass; B-2-1
flips to TRUE in `ISSUES.md`; `mypy --strict`/ruff/coverage-gate clean.

---

## 2.1 — Don't charge twice; stop scanning the money path

> **FILLED IN 2026-07-25** from the skeleton below (rule 11). The session that did so read every
> Wave-2 ledger row through 2.0b-mock-GREEN first, and verified the current billing code live rather
> than trusting the contract's "table empty, unwired" line. What it found is baked into the prompts
> below and must still be re-confirmed from live at run time (§0.2):
> - **P-14 idempotency already exists in code.** `logic/webhook_service.py:82` keys on
>   `event.event_id` via `self._sub_repo.record_payment_event(event.event_id, event.event_type)`;
>   `dal/subscription_repository.py:279` does a conditional put into the idempotency table
>   (PK=`id`, TTL on `expiration`, default `ttl_seconds = 86400 * 7` = 7 days), and
>   `webhook_service.py:101` calls `delete_payment_event` to release the slot on failure. So the
>   webhook idempotency *mechanism* is built; this step proves it and settles whether anything
>   actually writes to that table in a deployed environment.
> - **The P-15 money-path Scan is real and located.** `dal/subscription_repository.py:103`
>   `get_subscription_by_customer_id` queries `EMAIL_INDEX_NAME` and then **falls back to
>   `self._table.scan(...)` at line 127** — that fallback is the webhook-path scan P-15 forbids.
>   Its own docstring says to prefer a `customer_id → user_id` lookup instead. The IAM
>   `dynamodb:Scan` grant is at `infra/careervp/api_construct.py:661`.
> - **`scan_active_subscriptions` (subscription_repository.py:374) is NOT this step's target.** It
>   is the batch *reconcile* path (2.5's entrypoint), not the interactive webhook money path. Drawing
>   that line — which scans are "money path" — is 2.1-RED's first job, and it must not silently
>   delete the reconcile scan to make a permission test pass.
> - **"Real table" = moto.** `tests/integration/` already uses `from moto import mock_aws`
>   (e.g. `test_p05_cross_tenant_idor.py:32`), so replay suppression can be proven against a real
>   DynamoDB table with the real GSI, no devx deploy required.
>
> **Header corrected against the spec frontmatter (rule 16).** The skeleton read
> `opus/high · gpt-5-codex/high`. The P-14/P-15 spec frontmatter (`tooling:`) reads
> `codex: {model: gpt-5.3-codex, reasoning: high}` for both clauses — same 2026-07-25 codex-family
> resolution 2.0b applied. Corrected below to **`opus/high · gpt-5.3-codex/high`**; `opus/high` is
> unchanged.
>
> **⚠️ Serialization deviation surfaced at fill-in (rule 5 flag, do not resolve silently).** §2 lists
> `api_construct.py` as edited only by 2.2, 2.4, and 2.7. But P-15 removes the `dynamodb:Scan` grant
> at `api_construct.py:661`, so **2.1 also edits `api_construct.py`** and joins that serial set: 2.1's
> GREEN must not run at the same time as any of 2.2/2.4/2.7. The backend lane is still parallel with
> the infra lane *for the RED session and for the P-14 DAL work*, but the one-line IAM removal is a
> shared-file edit. Whoever runs 2.1-GREEN confirms no infra-lane step is mid-flight on
> `api_construct.py` first, exactly as §2 requires.

| | |
|---|---|
| **Clauses** | P-14, P-15 |
| **Spec** | `specs/P-14-P-15-billing-idempotency-scan-spec.md` |
| **Acceptance criteria** | AC-P14-1, AC-P14-2, AC-P15-1 |
| **Claude / Codex** | opus/high · gpt-5.3-codex/high |
| **Depends on** | 2.0-GREEN (landed — `MockProvider` + port `retrieve_subscription`) |
| **Deploy target** | `CareerVpCrudDevx` (manual-dispatch only per §0.3; P-15 IAM change edits `api_construct.py` — see serialization flag above) |
| **Rule 7** | RED and GREEN separate — money path |
| **Bets** | `B-2-2` (the event id is a safe idempotency key — **this step settles it**) · `B-2-3` (resource count — check synth before/after; P-15 only removes a permission, adds no resource) |

**In plain English.** Make sure a payment event that arrives twice is only acted on once, and stop
the billing code from scanning the whole table to find a customer.

**Owns `test_p25_mock_event_id_is_stable_across_retries`** (reassigned from 2.0-RED, 2026-07-25 —
see that prompt's resolved note). Two deliveries of the SAME event, through the provider's own retry
path, must carry the same `event_id`, and the second delivery must be suppressed by this step's
idempotency wiring against a real table. This is the direct settlement of bet `B-2-2` — do not treat
it as optional or fold it silently into a differently-named test.

**Done-when.** A replayed webhook is provably suppressed against a real (moto) table, not a mock;
the customer-id lookup uses a named index/query with zero scans on the money path; the money-path
Lambda's IAM policy no longer includes `dynamodb:Scan`; the access pattern is recorded; `cdk diff`
shows zero stateful replacement and the naming validator passes if infra changed; synth resource
count is captured before and after (`B-2-3`).

---

# PROMPT 2.1-RED — billing idempotency + no-Scan money path (tests only)

> **Clause:** P-14, P-15 · **Spec:** [`specs/P-14-P-15-billing-idempotency-scan-spec.md`](../specs/P-14-P-15-billing-idempotency-scan-spec.md)
> **Acceptance criteria:** AC-P14-1, AC-P14-2, AC-P15-1 · **Claude: opus/high · Codex: gpt-5.3-codex/high**
> **Rule 7 applies — money path.** RED and GREEN are two different sessions. This one writes tests
> only (plus, where rule 14 requires it, tightening the spec's own RED-test briefs) and carries an
> **absolute prohibition** on touching implementation files.

```
STANDING CHECK — before doing anything else: open runbooks/wave-2-status.md and read the 2.0-GREEN,
2.0b-GREEN, and 2.0b-mock-GREEN rows. All must show landed/green (2.1 depends on 2.0-GREEN; the mock
work is what makes the reassigned B-2-2 test meaningful). Then confirm THIS step's prerequisites are
met right now, with real commands (not memory, not this file):

  git log --oneline -3
  cd src/backend && uv run pytest tests/unit/test_p25_payment_provider_port.py tests/unit/test_p25b_stripe_provider.py -q 2>&1 | tail -5
  python -c "from careervp.payment_providers.mock_provider import MockProvider; print('mock ok')"
  grep -n "record_payment_event\|delete_payment_event" careervp/logic/webhook_service.py
  grep -n "def get_subscription_by_customer_id\|\.scan(\|IndexName" careervp/dal/subscription_repository.py
  grep -n "dynamodb:Scan\|actions=\[.*Scan" infra/careervp/api_construct.py | head

If the P-25/P-25b provider tests are not green, or MockProvider is not importable, STOP and say so
plainly — the money-path port this step builds on is not there.

BEFORE WRITING ANY TEST (rule 14): open specs/P-14-P-15-billing-idempotency-scan-spec.md,
"RED Tests to Write First". It names five tests but several briefs do NOT state exact assertion
values ("a named GSI", "a deterministic retention window", "idempotent success"). Rule 14 forbids
writing tests against a brief that does not say what it is testing. Your FIRST authoring task is to
tighten those briefs IN THE SPEC to name exact values you derived live — the exact index/query path
used for the customer lookup, the exact TTL retention (the code today is 86400*7 = 7 days; state the
number, do not invent a new one), the exact money-path Lambda whose IAM you assert on, and the exact
"same recorded result" the replayed webhook returns. This is authoring the spec's RED-test brief,
which is allowed; do NOT widen AC-P14-1/AC-P14-2/AC-P15-1 or add a clause. If you find you must
change an AC itself, that is a rule-5 stop + a §0.3 amendment, not an edit.

You are implementing clauses P-14 and P-15 (AC-P14-1, AC-P14-2, AC-P15-1). You are the RED session:
TEST FILES + the spec's RED-test-brief tightening ONLY. You may not create or edit any file under
src/backend/careervp/ or infra/careervp/, even "to see if it works." If you believe an implementation
file must change, write the test that proves it and stop.

--------------------------------------------------------------------------------
FIRST — establish the live billing state (this is 2.1's first output, per the skeleton)
--------------------------------------------------------------------------------

The contract records this clause as "idempotency table empty, unwired," but the CODE path already
exists (webhook_service.py:82 records on event.event_id; subscription_repository.py:279 conditional-
puts with TTL). BOTH can be true — the mechanism can exist while nothing writes to the table in a
deployed environment. Determine which, from live evidence, and REPORT it before writing any test:
  1. Read webhook_service.py end to end. Confirm the claim/commit/release ordering
     (record_payment_event → work → delete on failure) and quote the lines.
  2. Read subscription_repository.py get_subscription_by_customer_id: the query-then-scan fallback at
     ~:113 (query EMAIL_INDEX_NAME) and ~:127 (scan). This scan IS the P-15 money-path target.
  3. Enumerate EVERY Scan on the billing path and classify each as money-path (webhook / interactive
     checkout / portal) vs batch-reconcile. scan_active_subscriptions (~:374) is the reconcile path —
     2.5's entrypoint — NOT this step's target; say so explicitly so GREEN does not delete it.
  4. Identify the money-path Lambda that carries the dynamodb:Scan IAM grant (api_construct.py:661)
     and confirm whether that same function also runs the reconcile path (if it does, removing Scan
     is coupled to 2.5 — flag it; do not resolve it here).
REPORT this classification in plain English first. If the scan surface is larger than the one webhook
fallback, say so — it changes the size of GREEN and the next session must know.

--------------------------------------------------------------------------------
THEN — tighten the briefs, then write exactly these tests
--------------------------------------------------------------------------------

Put the unit-level tests in src/backend/tests/unit/ and the IAM/synth test where the other
infrastructure synth tests live (src/backend/tests/infrastructure/ — confirm live). Cite the AC in
each. No real network calls. Secrets under P-06 (parameter NAME in env, value at runtime, never a
literal). Use moto (mock_aws) for the real-table tests, the pattern tests/integration already uses.

  test_p14_webhook_replay_same_event_id_single_side_effect        (AC-P14-1)
      Send the SAME signed event twice through the webhook path against a moto table with the real
      idempotency GSI. Assert EXACTLY ONE subscription mutation (assert the write/upsert is invoked
      once — count it) and that the second delivery returns the same deterministic idempotent-success
      response as the first (state the exact response). No second side effect.

  test_p14_worker_replay_same_business_id_single_artifact         (AC-P14-2)
      Invoke the worker path twice with the SAME stable business id (application_id + artifact type +
      operation, per the spec fix plan — NOT a request timestamp). Assert one side effect and exactly
      one idempotency record. Derive the stable-key shape from the code live; state it exactly.

  test_p15_billing_lookup_uses_query_not_scan                     (AC-P15-1)
      Patch the DynamoDB table so query() and scan() are observable. Drive the money-path
      customer/subscription lookup and assert it calls query() on the named index and NEVER calls
      scan(). Name the index explicitly.

  test_p15_iam_money_path_has_no_scan_permission                  (AC-P15-1)
      Synth the billing/webhook money-path Lambda's IAM policy and assert it does NOT include
      dynamodb:Scan. Name the exact logical construct asserted on. (This is the test that proves the
      api_construct.py:661 grant is gone — and the reason 2.1 joins the api_construct.py serial set.)

  test_p14_idempotency_ttl_is_set                                 (AC-P14-1)
      Assert idempotency records carry a TTL attribute (expiration) with the deterministic retention
      the code uses — 86400*7 seconds (7 days). State the exact number; no "or".

  test_p25_mock_event_id_is_stable_across_retries                 (AC-P14-1 / bet B-2-2)
      REASSIGNED HERE from 2.0-RED. Put it in src/backend/tests/unit/ (its own file or the P-25 file
      — your call, but it is a P-14/B-2-2 test, not a new P-25 clause). Deliver the SAME logical
      provider event TWICE through the provider's retry path (MockProvider) and assert BOTH carry the
      SAME event_id, THEN assert this step's idempotency wiring suppresses the second against a real
      (moto) table. A fresh id per attempt is the exact failure B-2-2 fears — this test is what proves
      it cannot happen. Do NOT rename it or fold it into another test.

RULE 13 — run every test, capture the failure output VERBATIM, and for each state WHY it failed. A
test that fails on ImportError/collection/missing-fixture is NOT red, it is broken; structure each
(or a minimal skip-guard) so it fails on ITS OWN assertion. State which technique you used. The
P-25/P-25b provider tests and the full existing suite must still be green after your run — you have
ADDED tests, not changed implementation.

--------------------------------------------------------------------------------
OUTPUT REQUIRED
--------------------------------------------------------------------------------
1. The live billing-state determination (idempotency wiring: mechanism-only vs actually-writing) and
   the full money-path-vs-reconcile Scan classification, in plain English first.
2. The tightened P-14/P-15 RED-test briefs as they now read in the spec (diff of that section).
3. The new test files, each assertion cited to its AC.
4. Verbatim failure output for every new test + one-line why for each, AND proof the P-25/P-25b
   tests and the rest of the suite are still green.
5. Confirmation that ZERO files under src/backend/careervp/ and infra/careervp/ were modified
   (git diff --stat).
6. A git commit message.

ALSO REQUIRED (standing rule for every wave prompt — see runbooks/RUNBOOK-RULES.md):
- Compare what you actually built against (a) this prompt's own instructions and (b) clauses P-14 and
  P-15 in project-scope-lock.yaml. If everything matches, say so in one plain sentence.
- If ANYTHING drifted — extra work not asked for, required work skipped, or a test/rule had to be
  weakened — STOP. Do not fix it yourself. Write one plain-English sentence a non-engineer could
  follow (what should have happened, what actually happened, why it matters), THEN the technical
  detail, and flag it for human review. Do not mark the step done.
- Update runbooks/wave-2-status.md: add/update this step's row with a plain-English status, the
  commit, today's date, and what GREEN must resolve first. B-2-2 stays open until GREEN lands.
```
---

# PROMPT 2.1-GREEN — key on the event id, kill the money-path Scan

> Run in a **FRESH session** that has not seen 2.1-RED's reasoning. `/clear` is the minimum; a
> separate invocation is preferred. The failing tests are a contract you did not write and **may not
> edit** — no relaxing an assertion, no `xfail`, no `skip`. If a test looks genuinely *wrong* (not
> merely inconvenient), STOP and raise a §0.3 amendment.
> **Clause:** P-14, P-15 · **Claude: opus/high · Codex: gpt-5.3-codex/high**
>
> **Serialization (from the fill-in flag above).** This step removes the `dynamodb:Scan` grant at
> `api_construct.py:661`, so it edits `api_construct.py` — a file the infra lane (2.2/2.4/2.7) also
> edits. Before touching that file, confirm no infra-lane step is mid-flight on it (§2). The P-14 DAL
> + idempotency work does not touch `api_construct.py` and is not gated by that.

```
STANDING CHECK — before doing anything else: open runbooks/wave-2-status.md and read the 2.1-RED row.
If it left anything open, deal with it FIRST — especially its money-path-vs-reconcile Scan
classification: you must remove ONLY the money-path scan, never scan_active_subscriptions (that is
2.5's reconcile path). Confirm the RED tests exist and fail, right now, with a real command:

  cd src/backend && uv run pytest tests/unit -q -k "p14 or p15 or event_id_is_stable" 2>&1 | tail -25
  cd src/backend && uv run pytest tests/infrastructure -q -k p15 2>&1 | tail -15

If they pass, or fail on import/collection errors rather than their own assertions, STOP.

You are implementing clauses P-14 and P-15 (AC-P14-1, AC-P14-2, AC-P15-1). You are the GREEN session.
You may not edit any test file written by 2.1-RED, nor the RED-tightened spec briefs. Build:

1. P-14 idempotency, proven end to end. The mechanism exists (record_payment_event / commit-after-
   work / delete_payment_event release on failure). Make the webhook-replay and worker-replay tests
   pass against a real (moto) table: key webhook idempotency by provider event id + provider name;
   key worker idempotency by the stable business id (application_id + artifact type + operation +
   provider event id where applicable), NEVER by request timestamp. A replayed webhook returns the
   same recorded result with no duplicate side effect. Keep the TTL retention the RED test pinned
   (86400*7). Preserve MockProvider's stable-event-id-across-retries behavior (bet B-2-2) — if the
   mock issues a fresh id per attempt, fix the mock, do not weaken the test.

2. P-15 no money-path Scan. Replace the get_subscription_by_customer_id scan fallback
   (subscription_repository.py:~127) with a customer-id/subscription-id GSI query path (the infra at
   api_db_construct.py already defines an idempotency-key-index; confirm which index serves
   customer_id → subscription and use a named Query, add one only if the spec's evidence shows it is
   needed and P-26 headroom allows — B-2-3). Remove the dynamodb:Scan grant from the money-path
   Lambda at api_construct.py:661. Do NOT remove scan_active_subscriptions or any grant the reconcile
   path (2.5) still needs — if the same Lambda serves both, that coupling is a rule-5 stop: flag it,
   do not force it.

3. Preserve the checkout and portal response shapes the frontend consumes (no contract drift).

VERIFY: every RED test passes (unit + infrastructure); the P-25/P-25b provider tests still pass; full
backend unit + integration suites (zero regressions); frontend suites if any contract file changed;
ruff; mypy careervp --strict; the coverage gate (make coverage-tests, at/above the enforced
baseline); scope-diff reports P-14 and P-15. If infra changed: cdk synth clean, `cdk diff` shows ZERO
stateful replacement, the naming validator passes, and you capture the synth resource count BEFORE and
AFTER (B-2-3 — P-15 only removes a permission, so the count must not rise). No merge to main (§0.3);
any deploy is manual-dispatch devx only, and the money-path proof is the moto real-table test, not a
live charge.

OUTPUT REQUIRED
1. Every RED test now passing (unit + infrastructure), with output, plus the P-25/P-25b tests still
   green.
2. Confirmation that ZERO test files and ZERO RED-authored spec briefs were modified (git diff --stat).
3. The customer-lookup access pattern you landed (which named index, query shape), stated plainly,
   and the before/after synth resource count.
4. A git commit message.

ALSO REQUIRED (standing rule for every wave prompt — see runbooks/RUNBOOK-RULES.md):
- Compare what you actually built against (a) this prompt's own instructions and (b) clauses P-14 and
  P-15 in project-scope-lock.yaml. If everything matches, say so in one plain sentence.
- If ANYTHING drifted, STOP, write the plain-English sentence first, then the technical detail, and
  flag it for human review. Do not mark the step done.
- Update runbooks/wave-2-status.md with a plain-English status, the commit, today's date, and
  anything the NEXT step (2.5, then GATE) must resolve first. **Settle bet B-2-2 in ISSUES.md** with
  the evidence (event id stable across retries AND the second delivery suppressed against a real
  table) — this is the step authorized to close B-2-2; the GATE re-reads it (rule 9). Record the
  money-path/reconcile Scan coupling finding for 2.5 if the same Lambda serves both.
```

**Done-when.** All P-14/P-15 RED tests pass (unit + infrastructure) and the P-25/P-25b tests stay
green; a replayed webhook is provably suppressed against a real (moto) table; the money-path
customer lookup uses a named Query with zero scans and the money-path Lambda has no `dynamodb:Scan`
IAM grant; `cdk diff` zero stateful replacement + naming validator pass if infra changed; synth
resource count not raised (`B-2-3`); bet `B-2-2` settled in `ISSUES.md`.

---

## 2.2 — Stop silently losing queued work (skeleton)

| | |
|---|---|
| **Clauses** | P-16, P-17, P-18 |
| **Spec** | `specs/P-16-P-17-P-18-P-19-reliability-spec.md` |
| **Claude / Codex** | sonnet/med · gpt-5-codex/med |
| **Depends on** | Wave 1 |
| **Deploy target** | `CareerVpCrudDevx` |
| **Serialization** | edits `api_construct.py` — do not run alongside 2.4 or 2.7 |
| **Bets** | `B-2-3` — **this is the step most likely to test the resource ceiling** (eight dead-letter queues plus alarms) |

**In plain English.** When a batch of queued work partly fails, the system currently loses the
failed items silently. Report per-item failures, wire up the eight dead-letter queues that exist but
are not connected, bound how many of each consumer can run at once, and make queue visibility
timeouts at least six times the function timeout.

**Done-when.** Per-item batch failure reporting on every consumer; all eight dead-letter queues
wired with alarms; reserved concurrency set (currently zero of thirty-one); visibility timeout at
least 6× on every queue. Synth resource count captured **before and after**.

---

> **FILLED IN 2026-07-25** from the skeleton above (rule 11), by a session that first read every
> Wave-2 ledger row through 2.5a-GREEN (HEAD `e919e06`). Five things it resolved at fill-in, each of
> which the runner must still re-confirm live (§0.2), none of which widens the skeleton's clauses:
>
> - **This is a RED/GREEN split (rule 7), and the skeleton did not say so.** P-17 is
>   "stop silently losing queued work" — data durability. Rule 7 makes RED and GREEN two different
>   sessions with the test-writer/code-writer firewall. This is NOT the small-isolated-clause carve-out
>   2.5 used: it spans eight queues, six-plus consumers, two infra files, and one real handler behavior.
>   So 2.2 is written below as **2.2-RED** then **2.2-GREEN**, exactly like 2.0/2.1.
>
> - **P-19 is NOT in this step.** The spec `specs/P-16-P-17-P-18-P-19-reliability-spec.md` covers four
>   clauses; step 2.2 is P-16, P-17, P-18 only (AC-P16-1, AC-P17-1, AC-P18-1). The
>   `test_p19_sfn_retries_use_full_jitter_and_start_vpr_heartbeat` brief and every Step-Functions
>   heartbeat/jitter change belong to **2.3** (P-19). Writing any P-19 test or touching
>   `artifact_chain_construct.py` here is scope drift — a rule-5 stop.
>
> - **The spec's RED-test list is underspecified in two places (rule 14) — RED fixes the spec FIRST.**
>   (a) `test_p16_..._have_max_concurrency` says "max concurrency/reserved concurrency for each
>   rate-limited worker" — an `or`-shaped assertion with no worker list and no value. (b) The
>   done-when and Fix-Plan step 6 require "all eight DLQs wired with alarms," but the RED-test list
>   has **no alarm test at all**. Both are rule-14 gaps: RED authors/tightens those spec briefs as a
>   separate visible action before writing tests, never folded into the test-writing step.
>
> - **GREEN edits two infra files, and only one is in the documented serial set (rule-5 flag, do not
>   resolve silently).** §2 lists `api_construct.py` as the serialized file (2.2/2.4/2.5/2.7) — that
>   holds the VPR / cover-letter / interview-prep queues + event sources. But the CV-upload / gap /
>   company-research queues live in `/Users/yitzchak/Documents/dev/careervp/infra/careervp/api_db_construct.py`,
>   which **no other Wave-2 step edits** (verified: zero editing references in this prompt file). So
>   2.2-GREEN edits both; it must still hold the `api_construct.py` serialization lock (confirm no
>   2.4/2.5/2.7/2.1-GREEN mid-flight), and note `api_db_construct.py` is 2.2-exclusive.
>
> - **Header corrected against the execution plan (rules 15/16).** The skeleton reads
>   `sonnet/med · gpt-5-codex/med`. `redesign-execution-plan.md` line 284 and the spec's own
>   `tooling:` block both read **`sonnet/medium · gpt-5.3-codex/medium`** ("normal implementation
>   across a few files, established SQS/Lambda reliability patterns — rule 16 `medium`"). The
>   skeleton's `gpt-5-codex` is a stale slug (rule 16 forbids it); the corrected slug is used below.

---

# PROMPT 2.2-RED — pin the reliability contract in failing tests (tests only, no implementation)

> **Clause:** P-16, P-17, P-18 · **Spec:** [/Users/yitzchak/Documents/dev/careervp/docs/db-redesign/code/code-analysis/project/specs/P-16-P-17-P-18-P-19-reliability-spec.md](/Users/yitzchak/Documents/dev/careervp/docs/db-redesign/code/code-analysis/project/specs/P-16-P-17-P-18-P-19-reliability-spec.md)
> **Acceptance criteria:** AC-P16-1, AC-P17-1, AC-P18-1 (NOT AC-P19-1 — that is step 2.3) · **Claude: sonnet/medium · Codex: gpt-5.3-codex/medium**
> **Rule 7 — RED/GREEN split (P-17 is data durability).** This is the RED session. It writes **test files and spec-brief edits only**, touches **zero** files under `/Users/yitzchak/Documents/dev/careervp/infra/careervp/` or `/Users/yitzchak/Documents/dev/careervp/src/backend/careervp/`, observes every test fail on its OWN assertion (rule 13), and commits tests only. GREEN is a separate fresh session that has not seen this reasoning and may not edit these tests.
> **Rule 17 — every file named below is a full path from the repo root.** Keep it that way in anything you add.

```
STANDING CHECK — before doing anything else: open
/Users/yitzchak/Documents/dev/careervp/docs/db-redesign/code/code-analysis/project/runbooks/wave-2-status.md
and read the rows through 2.5a-GREEN. This infra lane depends only on Wave 1, not on the 2.0/2.1/2.5
billing lane — but if any api_construct.py step (2.4, 2.5, 2.7, or a straggling 2.1-GREEN) shows an
OPEN row, note it: this RED session does not edit api_construct.py so it is safe now, but 2.2-GREEN
will, and must not overlap them. Then confirm THIS step's prerequisites are met right now, with real
commands (not memory, not this file):

  cd /Users/yitzchak/Documents/dev/careervp && git log --oneline -3
  # the six generation queues + their DLQs + event sources exist to test against:
  grep -n "SqsEventSource\|visibility_timeout\|dead_letter_queue\|DeadLetterQueue\|report_batch_item_failures\|reserved_concurrent\|max_concurrency" /Users/yitzchak/Documents/dev/careervp/infra/careervp/api_construct.py
  grep -n "SqsEventSource\|visibility_timeout\|dead_letter_queue\|DeadLetterQueue\|report_batch_item_failures\|reserved_concurrent\|max_concurrency" /Users/yitzchak/Documents/dev/careervp/infra/careervp/api_db_construct.py
  # the one worker that already returns the desired shape, to copy its pattern in the handler test:
  grep -n "batchItemFailures\|itemIdentifier" /Users/yitzchak/Documents/dev/careervp/src/backend/careervp/handlers/company_research_worker_handler.py

Confirm live, and STOP with a plain-English sentence if any is not true:
  - the eight DLQs exist but their event-source mappings do NOT yet set report_batch_item_failures
    (if they already do, the durability gap is closed and this step is smaller than written — say so);
  - no reserved / max concurrency is configured on the rate-limited workers (the "0 of 31" state);
  - at least one visibility timeout is currently below 6x its consumer's timeout (the "1x" state the
    spec's current_state records — if all are already >= 6x, say so and note P-18 may be a no-op test).

BEFORE WRITING ANY TEST (rule 14): confirm, with a real command, that
/Users/yitzchak/Documents/dev/careervp/docs/db-redesign/code/code-analysis/project/specs/P-16-P-17-P-18-P-19-reliability-spec.md
exists, that it has a "RED Tests to Write First" section naming AC-P16-1 / AC-P17-1 / AC-P18-1, and
that each cited test names EXACT assertion values (no "or", no undefined placeholders). It does NOT
today — two briefs are underspecified (see below). So your FIRST visible action is to tighten the
spec, as its own edit, before you write a single test.
```

You are implementing clauses P-16, P-17, P-18. This is the RED half of a rule-7 split. Do the two
things below **in order** and keep them as separate visible steps.

--------------------------------------------------------------------------------
STEP 1 — tighten the spec's two underspecified RED briefs (rule 14), as its own edit
--------------------------------------------------------------------------------

Edit ONLY the "RED Tests to Write First" section of
/Users/yitzchak/Documents/dev/careervp/docs/db-redesign/code/code-analysis/project/specs/P-16-P-17-P-18-P-19-reliability-spec.md.
Do not touch its clause list, its Acceptance Criteria, or the P-19 brief.

  (1) `test_p16_rate_limited_consumers_have_max_concurrency` currently reads
      "max concurrency/reserved concurrency for each rate-limited worker" — an `or` with no worker
      list and no number. Pin all three:
        - ENUMERATE, from the live event sources you grepped above, exactly which workers are
          rate-limited (the ones whose work calls an externally rate-limited API — Anthropic model
          calls and Tavily search — e.g. VPR generation, cover letter, interview prep, CV tailoring,
          gap analysis, company research). List them by their construct/function id, from source, not
          from memory.
        - CHOOSE ONE mechanism, not "or": event-source `max_concurrency` (SQS scaling bound) OR
          function `reserved_concurrent_executions`. Pick the one that actually bounds concurrent
          consumers for these SQS workers and say why in one line. The test asserts THAT mechanism.
        - SET AN EXACT NUMBER per worker, justified against the downstream limit it protects (the
          external API's concurrency/rate budget), not invented "to be safe." Write the number and
          its one-line justification into the brief. GREEN implements exactly this number; it may not
          choose its own.
  (2) The done-when ("all eight DLQs wired with alarms") and Fix-Plan step 6 require DLQ depth alarms,
      but there is NO alarm test in the RED list. ADD one brief:
        - `test_p17_all_eight_dlqs_have_depth_alarms`: synth both stacks and assert each of the eight
          DLQs has a CloudWatch alarm on its `ApproximateNumberOfMessagesVisible` metric with an
          exact threshold and evaluation period. Name the exact threshold in the brief. The alarm MUST
          use the native SQS metric — Fix-Plan step 6's constraint "without using low-cardinality
          STATUS#{status} GSI patterns" means do not build depth detection off a DynamoDB GSI scan.

If pinning any of these would require changing an Acceptance Criterion (not just a test brief), STOP —
that is a §0.3 amendment, not a spec-brief tightening. Commit this spec edit as its own visible change
(it may ride in the same RED commit, but call it out).

--------------------------------------------------------------------------------
STEP 2 — write the RED tests and observe each fail on its OWN assertion (rule 13)
--------------------------------------------------------------------------------

Put the synth/IaC assertions where the infrastructure synth tests live — confirm the directory live
(ls /Users/yitzchak/Documents/dev/careervp/src/backend/tests/infrastructure/, the same place 2.1's
IAM synth test landed) — and the handler-behavior test where the worker unit/integration tests live
(confirm live). No real network or AWS calls; synth the template / use moto (mock_aws), the pattern
those directories already use. Secrets, if any surface, are parameter-NAME-in-env only (P-06).

Write exactly these five, and NOT `test_p19_*` (that is step 2.3):

  test_p16_rate_limited_consumers_have_max_concurrency          (AC-P16-1)
      Synth the event sources / functions and assert the EXACT mechanism + number you pinned in
      STEP 1 for EACH enumerated rate-limited worker. RED: current state is "0 of 31 reserved" — the
      property is absent, so the assertion fails naming the worker with no bound.

  test_p17_all_sqs_event_sources_report_batch_item_failures     (AC-P17-1, infra half)
      Synth every SQS Lambda event-source mapping and assert `FunctionResponseTypes` includes exactly
      `ReportBatchItemFailures`. RED: the mappings do not set it, so the property is missing.

  test_p17_worker_handlers_return_batch_item_failures           (AC-P17-1, behavior half)
      Call each generation worker handler (enumerate them from source) with a batch containing one
      failing record among good ones, and assert the return is exactly
      `{'batchItemFailures': [{'itemIdentifier': <failed-message-id>}]}` — only the failed id, in that
      exact shape (copy the proven pattern in
      /Users/yitzchak/Documents/dev/careervp/src/backend/careervp/handlers/company_research_worker_handler.py).
      RED: the workers that do not yet report partial failure either raise or return nothing, so the
      assertion fails on shape. Guard so a missing handler fails on the test's assertion, not a raw
      ImportError.

  test_p18_visibility_timeout_at_least_6x_lambda_timeout         (AC-P18-1)
      Synth every queue + its consuming function and assert, per pair,
      `visibility_timeout_seconds >= 6 * function_timeout_seconds`. RED: at least one pair violates it
      today (the spec's "1x" current_state). Assert on the real numbers read from synth, no "or".

  test_p17_all_eight_dlqs_have_depth_alarms                      (done-when: DLQ alarms)
      The brief you added in STEP 1. RED: no alarms exist, so the synth has zero alarms on the DLQ
      metric and the assertion fails counting them.

RULE 13 — run all five, capture the failure output VERBATIM, and for EACH state why it failed (which
property/shape/number is absent). A test that fails on a missing FIXTURE, a collection error, or a
typo in its own imports is NOT red, it is broken — structure each to fail on its OWN assertion about
the synthesized template or the handler return. The full existing suite (backend unit + integration +
both infrastructure dirs) must still be GREEN after this step — you have ADDED tests and tightened a
spec, and changed ZERO implementation. Prove it with `git diff --stat`: only test files under
`.../tests/` and the one spec file may appear; ZERO files under `infra/careervp/` or
`src/backend/careervp/`.

Do NOT implement anything. Do NOT wire a single DLQ, set a single concurrency bound, change a single
visibility timeout, or add a `batchItemFailures` return. That is 2.2-GREEN, in a different session.

--------------------------------------------------------------------------------
OUTPUT REQUIRED
--------------------------------------------------------------------------------
- The live prerequisite confirmations (the greps), in plain English first: DLQs exist but unwired,
  concurrency unset, at least one visibility timeout under 6x.
- The spec-brief tightening from STEP 1: the enumerated rate-limited workers, the ONE concurrency
  mechanism chosen and why, the exact per-worker number and its justification, and the exact DLQ-alarm
  threshold — as the diff to the spec's RED-test section.
- The five new test files, and the verbatim RED failure output for EACH with a one-line why. State
  the technique you used to make each fail on its own assertion rather than on import/collection.
- `git diff --stat` proving only test files + the one spec file changed; ZERO implementation/infra.
- A git commit message (tests + spec brief only).

ALSO REQUIRED (standing rule for every wave prompt — see
/Users/yitzchak/Documents/dev/careervp/docs/db-redesign/code/code-analysis/project/runbooks/RUNBOOK-RULES.md):
- Compare what you actually built against (a) this prompt's own instructions and (b) clauses P-16,
  P-17, P-18 in
  /Users/yitzchak/Documents/dev/careervp/docs/db-redesign/code/code-analysis/project/project-scope-lock.yaml.
  If everything matches, say so in one plain sentence. Confirm you wrote NO P-19 test.
- If ANYTHING drifted — extra work not asked for, required work skipped, or a test/rule weakened —
  STOP. Do not fix it yourself. Write one plain-English sentence a non-engineer could follow (what
  should have happened, what actually happened, why it matters), THEN the technical detail, and flag
  it for human review. Do not mark the step done.
- Update
  /Users/yitzchak/Documents/dev/careervp/docs/db-redesign/code/code-analysis/project/runbooks/wave-2-status.md:
  add a `2.2-RED` row with a plain-English status, the commit, today's date, and what 2.2-GREEN must
  resolve first (the api_construct.py serialization lock; the exact concurrency numbers it must
  implement verbatim; the B-2-3 resource-count baseline to measure against).

---

# PROMPT 2.2-GREEN — implement the reliability contract (fresh session; may not edit the tests)

> **Clause:** P-16, P-17, P-18 · **Spec:** [/Users/yitzchak/Documents/dev/careervp/docs/db-redesign/code/code-analysis/project/specs/P-16-P-17-P-18-P-19-reliability-spec.md](/Users/yitzchak/Documents/dev/careervp/docs/db-redesign/code/code-analysis/project/specs/P-16-P-17-P-18-P-19-reliability-spec.md)
> **Acceptance criteria:** AC-P16-1, AC-P17-1, AC-P18-1 (NOT AC-P19-1 — that is step 2.3) · **Claude: sonnet/medium · Codex: gpt-5.3-codex/medium**
> **Rule 7 — this is the GREEN session.** It runs FRESH, having NOT seen 2.2-RED's reasoning. It reads the five failing tests as a contract it did not write and **may not edit** — no relaxing an assertion, no changing the pinned concurrency number, no `xfail`/`skip`, no adding an exclusion. If a test looks genuinely WRONG (not merely inconvenient), STOP and raise a §0.3 amendment; never a quiet edit.
> **Rule 17 — every file named below is a full path from the repo root.**

```
STANDING CHECK — before doing anything else: open
/Users/yitzchak/Documents/dev/careervp/docs/db-redesign/code/code-analysis/project/runbooks/wave-2-status.md
and read the 2.2-RED row plus every api_construct.py-editing row (2.4, 2.5, 2.7, 2.1-GREEN). This step
edits api_construct.py, so it JOINS that serial set (§2) — if any of those rows is OPEN / mid-flight,
STOP: you may not edit api_construct.py concurrently. It ALSO edits api_db_construct.py, which no
other Wave-2 step edits, so no second lock is needed there. Then confirm 2.2-RED actually landed and
the five tests are RED right now, with a real command (not this file):

  cd /Users/yitzchak/Documents/dev/careervp/src/backend && uv run pytest \
    tests/infrastructure -k "p16 or p17 or p18" tests -k "p17_worker" -q
  # expect: the five 2.2 tests FAIL on their assertions; the rest of the suite passes.

Read the pinned values out of the tests and the spec BEFORE coding — the exact concurrency mechanism
and per-worker number, and the DLQ-alarm threshold — and implement THOSE. You do not get to choose
them; RED already did, and you may not edit the tests to match a different choice.
```

You are implementing clauses P-16, P-17, P-18 — the GREEN half. Make all five RED tests pass with the
smallest infra + handler changes that satisfy them, touching NO test file and NO spec file.

--------------------------------------------------------------------------------
THE WORK — four changes, all sized by the tests, none wider
--------------------------------------------------------------------------------

1. **P-16 concurrency bounds.** For each rate-limited worker the RED test names, set the EXACT
   mechanism + number the test asserts, in
   /Users/yitzchak/Documents/dev/careervp/infra/careervp/api_construct.py (VPR / cover-letter /
   interview-prep) and
   /Users/yitzchak/Documents/dev/careervp/infra/careervp/api_db_construct.py (CV / gap /
   company-research). Do not bound workers the test does not name.

2. **P-17 partial-failure reporting — both halves.**
   (a) Set `report_batch_item_failures=True` on every SQS event-source mapping the infra test checks
       (so `FunctionResponseTypes: [ReportBatchItemFailures]` appears in synth).
   (b) In each generation worker handler that does not yet do it, return
       `{'batchItemFailures': [{'itemIdentifier': <failed-message-id>}, ...]}` listing ONLY the failed
       records — copy the proven pattern in
       /Users/yitzchak/Documents/dev/careervp/src/backend/careervp/handlers/company_research_worker_handler.py.
       A partial failure must NOT re-drive the whole batch.

3. **P-18 visibility timeout.** Raise every violating queue's `visibility_timeout` to at least 6x its
   consumer's function timeout — the exact rule the test asserts. Changing a queue's visibility
   timeout is an in-place update; confirm `cdk diff` shows no stateful replacement of the queue.

4. **DLQ depth alarms.** Add a CloudWatch alarm on `ApproximateNumberOfMessagesVisible` for each of
   the eight DLQs, at the threshold the RED alarm test asserts. Native SQS metric only — no DynamoDB
   `STATUS#{status}` GSI scan (Fix-Plan step 6).

Do NOT touch `/Users/yitzchak/Documents/dev/careervp/infra/careervp/artifact_chain_construct.py`,
Step Functions retry/heartbeat, or `JitterStrategy` — that is P-19 / step 2.3. If you find P-16/17/18
cannot pass without a P-19 change, that is a rule-5 stop: flag it, do not fold it in.

--------------------------------------------------------------------------------
B-2-3 — the resource-ceiling bet this step is most likely to break (measure it)
--------------------------------------------------------------------------------

Capture the synth resource count BEFORE and AFTER your changes and put both in the output. Baseline
from the 2.1-GREEN ledger row: 257 parent + 11 AiAssist nested + 231 CrudFeatures nested = 499.
Adding ~8 alarms must not push the parent template or ANY nested stack to the 500-resource
CloudFormation ceiling. If any stack lands at 490+, STOP and flag B-2-3 as tripped — do not shave the
contract to fit; that is a human decision about nested-stack decomposition, recorded in ISSUES.md.

--------------------------------------------------------------------------------
VERIFY (fresh evidence, all of it)
--------------------------------------------------------------------------------
- The five 2.2 tests now PASS; `git diff --stat -- **/tests` is EMPTY (no test edited) and the spec
  file is unchanged.
- Full backend unit + integration suites: zero regressions. Both infrastructure test dirs green.
- `cd /Users/yitzchak/Documents/dev/careervp/src/backend` — ruff format + check clean;
  `uv run mypy careervp --strict` clean; `make coverage-tests` gate exit 0 at/above the enforced
  baseline.
- `cd /Users/yitzchak/Documents/dev/careervp/infra && uv sync && cdk synth` clean; `cdk diff` shows
  the concurrency / batch-response / visibility / alarm additions and ZERO stateful replacement
  (queues and their DLQs updated in place, never replaced — replacing a live queue drops in-flight
  messages, the exact silent loss P-17 exists to stop).
- Naming validator: `python /Users/yitzchak/Documents/dev/careervp/src/backend/scripts/validate_naming.py --path infra --strict` exit 0.
- scope-diff still resolves the Wave-2 clauses with no new orphan/drift.
- NO deploy and NO merge from this session (§0.3). Any devx deploy is a separate human-gated
  manual `workflow_dispatch` to `CareerVpCrudDevx` ONLY.

--------------------------------------------------------------------------------
OUTPUT REQUIRED
--------------------------------------------------------------------------------
- Proof the five tests were RED before your changes and PASS after (both runs' output).
- The BEFORE/AFTER synth resource counts (parent + each nested), with the B-2-3 verdict in one line.
- `git diff --stat` proving no test file and no spec file changed, and exactly the two infra files +
  the worker handler file(s) did.
- The full verification results above.
- A git commit message.

ALSO REQUIRED (standing rule for every wave prompt — see
/Users/yitzchak/Documents/dev/careervp/docs/db-redesign/code/code-analysis/project/runbooks/RUNBOOK-RULES.md):
- Compare what you actually built against (a) this prompt's own instructions and (b) clauses P-16,
  P-17, P-18 in
  /Users/yitzchak/Documents/dev/careervp/docs/db-redesign/code/code-analysis/project/project-scope-lock.yaml.
  If everything matches, say so in one plain sentence. Confirm you changed NOTHING for P-19.
- If ANYTHING drifted — extra work not asked for, required work skipped, or a test/rule had to be
  weakened — STOP. Do not fix it yourself. Write one plain-English sentence a non-engineer could
  follow (what should have happened, what actually happened, why it matters), THEN the technical
  detail, and flag it for human review. Do not mark the step done.
- Update
  /Users/yitzchak/Documents/dev/careervp/docs/db-redesign/code/code-analysis/project/runbooks/wave-2-status.md:
  add a `2.2-GREEN` row with a plain-English status, the commit, today's date, the B-2-3 measured
  headroom, and what 2.3 must resolve first (it depends on 2.2 in the same lane and also edits infra —
  confirm the api_construct.py lock is free) or "none".

---

# PROMPT 2.2-RED-fix — §0.3-approved correction to the P-17 worker test (tests only)

> **Clause:** P-17 · **Spec:** [/Users/yitzchak/Documents/dev/careervp/docs/db-redesign/code/code-analysis/project/specs/P-16-P-17-P-18-P-19-reliability-spec.md](/Users/yitzchak/Documents/dev/careervp/docs/db-redesign/code/code-analysis/project/specs/P-16-P-17-P-18-P-19-reliability-spec.md)
> **Acceptance criteria:** AC-P17-1 (worker half only) · **Claude: sonnet/medium · Codex: gpt-5.3-codex/low**
> **Why this prompt exists.** 2.2-GREEN correctly STOPPED (rule 7): the landed 2.2-RED
> `test_p17_worker_handlers_return_batch_item_failures` drove `CvTailorWorkerLambda` with fabricated SQS
> records, but that Lambda is a **DynamoDB-stream** consumer (`/Users/yitzchak/Documents/dev/careervp/infra/careervp/api_construct.py:1951`, `DynamoEventSource`), so the SQS-`itemIdentifier` contract is false for it. A human §0.3 review (recorded 2026-07-26 in [/Users/yitzchak/Documents/dev/careervp/docs/db-redesign/code/code-analysis/project/runbooks/wave-2-status.md](/Users/yitzchak/Documents/dev/careervp/docs/db-redesign/code/code-analysis/project/runbooks/wave-2-status.md), "2.2 P-17 CV-tailor §0.3 decision") APPROVED correcting the test. **This is the ONLY circumstance under which a landed RED test may be edited — a dated §0.3 approval exists.** No other 2.2 test may be touched.
> **Rule 17 — every file named below is a full path from the repo root.**

```
STANDING CHECK — before doing anything else: open
/Users/yitzchak/Documents/dev/careervp/docs/db-redesign/code/code-analysis/project/runbooks/wave-2-status.md
and confirm the "2.2 P-17 CV-tailor §0.3 decision (2026-07-26)" section exists and says SPLIT — if it
does not, STOP: you have no authority to edit a landed RED test. Then confirm the mismatch is still
real with a real command:

  cd /Users/yitzchak/Documents/dev/careervp
  grep -n "DynamoEventSource\|SqsEventSource" infra/careervp/api_construct.py | sed -n '1,40p'
  grep -rn "CvTailor\|cv_tailor\|msg-failed" src/backend/tests/ | grep -i p17

Confirm live and STOP if untrue: CvTailorWorkerLambda is wired by DynamoEventSource (api_construct.py
:1951), and the P-17 worker test currently enumerates it among SQS workers.
```

Make EXACTLY this correction, nothing more:

1. In the landed P-17 worker test file (find it via the grep above), remove `CvTailorWorkerLambda`
   from the set of workers driven with SQS records and asserted for an SQS
   `{'batchItemFailures': [{'itemIdentifier': <messageId>}]}` return. The test must now enumerate ONLY
   the four real SQS workers: `VprSqsWorkerLambda`, `CoverLetterWorkerLambda`, `InterviewPrepWorkerLambda`,
   `CompanyResearchWorkerLambda` (company-research is the already-passing reference case).
2. Do NOT touch the P-16 concurrency test — CV-tailor legitimately stays in the
   `reserved_concurrent_executions=5` set there (reserved concurrency applies to any rate-limited
   Lambda; P-16 is not about event-source type). Do NOT touch the P-17 infra test, P-18, the DLQ-alarm
   test, or any implementation file.
3. Re-run and OBSERVE the corrected worker test still RED on its own assertions for the four SQS
   workers (three of them lack the pattern; company-research passes). Capture verbatim output.

VERIFY: `git diff --stat` shows ONLY the one P-17 worker test file changed — ZERO under
`infra/careervp/` or `src/backend/careervp/`, ZERO other test files. Ruff + `mypy --strict` clean on it.

OUTPUT REQUIRED
- The live confirmation CV-tailor is a DynamoEventSource consumer, plain English first.
- The one-file diff, and the corrected test's verbatim RED output with a one-line why per case.
- `git diff --stat` proving the single-file scope.
- A git commit message.
- Update [/Users/yitzchak/Documents/dev/careervp/docs/db-redesign/code/code-analysis/project/runbooks/wave-2-status.md](/Users/yitzchak/Documents/dev/careervp/docs/db-redesign/code/code-analysis/project/runbooks/wave-2-status.md):
  set the `2.2-RED-fix` row DONE with the commit, and note 2.2-GREEN may now resume fresh.

---

## 2.2b — CV-tailor stream partial-failure (skeleton, post-2.2 follow-up)

| | |
|---|---|
| **Clause** | P-17 (CV-tailor stream flavor) |
| **Spec** | `specs/P-16-P-17-P-18-P-19-reliability-spec.md` (needs a stream-shaped brief added at fill-in) |
| **Claude / Codex** | sonnet/medium · gpt-5.3-codex/medium |
| **Depends on** | 2.2-GREEN (landed) |
| **Deploy target** | `CareerVpCrudDevx` |
| **Serialization** | edits `api_construct.py` (the CvTailor DynamoEventSource) — joins the api_construct.py serial set |
| **Bets** | none new |

**In plain English.** CV-tailor processes DynamoDB-stream records, not SQS. It already bisects a bad
batch and routes the poison record to its DLQ (`bisect_batch_on_error=True` + `on_failure=SqsDlq`,
`api_construct.py:1956-1958`), so there is no silent loss today. This step decides whether P-17's
clause additionally requires per-record `ReportBatchItemFailures` on the stream source — and if so,
adds it with the CORRECT stream shape (`itemIdentifier` = record **sequence number**, a DynamoDB-stream
record in the test, NOT an SQS record).

**Fill-in note (rule 11).** First answer the yes/no: does P-17 (`project-scope-lock.yaml`) require
per-record reporting on top of bisect+DLQ for a low-throughput stream consumer? If bisect+DLQ already
satisfies "no silent loss," this step may be a documented no-op that records that finding rather than
adding machinery. If it does require reporting, RED writes a stream-shaped test first (rule 7 carve-out
or split, decided at fill-in), GREEN adds `report_batch_item_failures=True` to the DynamoEventSource
and the sequence-number return in the handler.

**Done-when.** Either a recorded finding that CV-tailor's existing bisect+DLQ satisfies P-17 (with the
GATE stopping-condition note already in the §0.3 section), or a stream-shaped `ReportBatchItemFailures`
contract added and proven, with `cdk diff` zero stateful replacement.

---

## 2.3 — Retry and heartbeat on the workflows (skeleton)

| | |
|---|---|
| **Clause** | P-19 |
| **Spec** | `specs/P-16-P-17-P-18-P-19-reliability-spec.md` |
| **Claude / Codex** | sonnet/med · gpt-5-codex/med |
| **Depends on** | 2.2 (same lane) |
| **Deploy target** | `CareerVpCrudDevx` |
| **Bets** | `B-2-3` |

**In plain English.** The long-running generation workflows have no retry policy, no heartbeat, and
no jitter — so a transient failure kills a job and simultaneous retries pile up.

**Done-when.** Retry with full jitter and a heartbeat on the workflow steps, including the
VPR start step. The 180-second timeout this project already settled on for the research step is the
heartbeat interval — do not pick a new number.

---

> **FILLED IN 2026-07-25** from the skeleton above (rule 11), by the session that filled 2.2, after
> reading the SFN construct live. Four things it resolved, each re-confirmable live (§0.2), none
> widening the clause:
>
> - **The skeleton's "no retry policy" is STALE (rule-5 flag).** Every task in
>   /Users/yitzchak/Documents/dev/careervp/infra/careervp/artifact_chain_construct.py ALREADY calls
>   `add_retry(errors=["States.TaskFailed"], interval=30s, max_attempts=2|3, backoff_rate=2.0)` —
>   cover-letter `:158`, interview-prep `:186`, cv-tailoring `:227`, StartVPR `:251`,
>   company-research `:286`. So P-19's real, narrow gap is **two** things, not a from-scratch retry
>   build: (a) NO `jitter_strategy` is set on any `add_retry` (so simultaneous retries still
>   thundering-herd), and (b) StartVPR (`:238`, an `SqsSendMessage` WAIT_FOR_TASK_TOKEN) has an
>   `add_retry` but **no `heartbeat_timeout`**, while cover-letter (`:144`=300s), interview-prep
>   (`:175`=300s) and company-research (`:275`=180s) do. Confirm this live; if jitter is already set,
>   the step is smaller still.
>
> - **This is a SINGLE-SESSION RED-first step (rule-7 carve-out), not a split.** Unlike 2.2, P-19 is
>   ~6 lines of SFN configuration in one file — `jitter_strategy=sfn.JitterStrategy.FULL` on each
>   `add_retry`, plus one `heartbeat_timeout` on StartVPR. That is the "small isolated clause"
>   carve-out `RUNBOOK-RULES.md` rule 7 sanctions (the same one 2.5 used): one session writes the
>   failing test first, sees it red (rule 13), then implements. It touches no money/tenancy/auth path.
>
> - **The "same lane, all edit api_construct.py" serialization is STALE for 2.3 (rule-5 flag).** 2.3
>   edits ONLY `artifact_chain_construct.py`; it does NOT touch `api_construct.py` or
>   `api_db_construct.py` (the files 2.2 edits). So 2.3 has **zero file contention with 2.2/2.4/2.5/2.7**
>   and needs none of the api_construct.py lock. The `Depends on 2.2` is sequencing on the shared spec,
>   not a file lock — see the "roll-in" note below. B-2-3 is a near-no-op here: jitter and heartbeat
>   are task *properties*, not new resources, so 2.3 adds ~0 to the resource count (confirm with
>   `cdk diff`).
>
> - **The done-when's heartbeat number needs pinning (rule 14).** The spec's P-19 brief says "StartVPR
>   heartbeat" with no value; the skeleton says use the settled **180 s** research number, "do not pick
>   a new number." But the existing heartbeats are mixed (300 s / 300 s / 180 s). RED pins StartVPR's
>   heartbeat to the settled 180 s value in the spec brief before writing the test, and records why
>   180 (StartVPR waits on the async VPR worker, the same class of long external step as research).
>
> **Roll-in (answers "what from 2.2 can 2.3 reuse without context rot").** 2.3 may be run in the SAME
> session immediately AFTER 2.2-GREEN lands, and should reuse that context: same spec file, same
> reliability subsystem, same `cdk synth`/`cdk diff`/naming-validator/coverage discipline, same devx
> deploy target. This does NOT break the rule-7 firewall because (i) 2.3 is a sanctioned single-session
> carve-out, so its test-writer legitimately is its code-writer, and (ii) 2.2-GREEN wrote no tests, so
> nothing it reasoned about contaminates a test it must treat as a contract. The one hard guardrail:
> 2.3 must still write its P-19 test and SEE IT RED (rule 13) before adding jitter/heartbeat, and must
> not retro-edit any 2.2 test. Header corrected to `sonnet/medium · gpt-5.3-codex/medium` (rules 15/16;
> execution-plan line 285), same as 2.2.

---

# PROMPT 2.3 — full jitter + StartVPR heartbeat on the workflows (single session, RED-first)

> **Clause:** P-19 · **Spec:** [/Users/yitzchak/Documents/dev/careervp/docs/db-redesign/code/code-analysis/project/specs/P-16-P-17-P-18-P-19-reliability-spec.md](/Users/yitzchak/Documents/dev/careervp/docs/db-redesign/code/code-analysis/project/specs/P-16-P-17-P-18-P-19-reliability-spec.md)
> **Acceptance criteria:** AC-P19-1 (P-16/17/18 are step 2.2 — do not touch them here) · **Claude: sonnet/medium · Codex: gpt-5.3-codex/medium**
> **Rule 7 — single session, RED-first (small-isolated-clause carve-out).** The whole change is `JitterStrategy: FULL` on the existing retries plus one `StartVPR` heartbeat, all in one file. One session may write the failing test first, observe it red (rule 13), then implement. If the change turns out larger than that — anything touching a handler, a queue, or a second file — STOP and split it.
> **Rule 17 — every file named below is a full path from the repo root.**

```
STANDING CHECK — before doing anything else: open
/Users/yitzchak/Documents/dev/careervp/docs/db-redesign/code/code-analysis/project/runbooks/wave-2-status.md
and read the 2.2-GREEN row. 2.3 depends on 2.2 landing (shared reliability spec); if 2.2-GREEN is not
done, STOP. 2.3 edits ONLY artifact_chain_construct.py, which no other Wave-2 step edits, so there is
no api_construct.py lock to wait on. Then confirm THIS step's gap is real right now, with real commands:

  cd /Users/yitzchak/Documents/dev/careervp
  grep -n "add_retry\|jitter_strategy\|JitterStrategy\|heartbeat_timeout\|StartVPR" infra/careervp/artifact_chain_construct.py

Confirm live, and STOP with a plain-English sentence if any is not true:
  - every add_retry currently has NO jitter_strategy (if any already sets JitterStrategy.FULL, say so);
  - the StartVPR task has an add_retry but NO heartbeat_timeout, while the other long tasks do.

BEFORE WRITING ANY TEST (rule 14): confirm, with a real command, that the spec above exists and its
"RED Tests to Write First" section names AC-P19-1 with EXACT values. The StartVPR heartbeat value is
underspecified today — pin it FIRST (see STEP 1) as its own visible spec edit, before writing the test.
```

You are implementing clause P-19. SINGLE RED-first session. Do the three steps below in order.

--------------------------------------------------------------------------------
STEP 1 — pin the StartVPR heartbeat value in the spec (rule 14), as its own edit
--------------------------------------------------------------------------------

Edit ONLY the P-19 brief in the "RED Tests to Write First" section of
/Users/yitzchak/Documents/dev/careervp/docs/db-redesign/code/code-analysis/project/specs/P-16-P-17-P-18-P-19-reliability-spec.md.
Set the StartVPR heartbeat to the settled **180 seconds** (the research-step number the project already
uses at artifact_chain_construct.py:275 — do NOT pick a new number), and state in one line why 180
(StartVPR waits on the async VPR worker, the same long-external-step class as research). Also make the
brief assert `JitterStrategy: FULL` on EVERY retry, not "some." Do not touch the P-16/17/18 briefs or
any Acceptance Criterion. If pinning this needs an AC change, STOP — that is a §0.3 amendment.

--------------------------------------------------------------------------------
STEP 2 — write the RED test and observe it fail on its OWN assertion (rule 13)
--------------------------------------------------------------------------------

Put it where 2.2's synth tests live (confirm live:
/Users/yitzchak/Documents/dev/careervp/src/backend/tests/infrastructure/). Synth the state machine and
read its definition — no AWS calls.

  test_p19_sfn_retries_use_full_jitter_and_start_vpr_heartbeat   (AC-P19-1)
      Synth the artifact-chain state machine definition and assert, on the test's OWN assertions:
        - EVERY Retry entry carries `JitterStrategy: FULL` (enumerate the retriers from the synthesized
          definition; none may be missing it);
        - each Retry still carries its existing `MaxAttempts` and `BackoffRate` (unchanged: 2/2.0,
          except company-research 3/2.0 — read them from source, assert the real numbers, no "or");
        - the StartVPR state has a `HeartbeatSeconds` of exactly 180.
      RED: no retry sets JitterStrategy today and StartVPR has no heartbeat, so the assertions fail
      naming the missing property. Guard so a missing state fails on the test's assertion, not a raw
      KeyError.

RULE 13 — run it, capture the failure output VERBATIM, state why it failed (JitterStrategy absent;
StartVPR HeartbeatSeconds absent). A test that fails on a collection error or a bad import is NOT red,
it is broken — make it fail on its own assertion about the synthesized definition. The full existing
suite must still be green (you ADDED a test, changed no implementation — prove with `git diff --stat`:
only the test file and the spec file, ZERO under infra/careervp/).

--------------------------------------------------------------------------------
STEP 3 — implement: FULL jitter on every retry + the StartVPR heartbeat
--------------------------------------------------------------------------------

In /Users/yitzchak/Documents/dev/careervp/infra/careervp/artifact_chain_construct.py ONLY:
  - Add `jitter_strategy=sfn.JitterStrategy.FULL` to EVERY `add_retry(...)` call (`:158`, `:186`,
    `:227`, `:251`, `:286`) — do not change interval, max_attempts, or backoff_rate.
  - Add `heartbeat_timeout=sfn.Timeout.duration(Duration.seconds(180))` to the StartVPR task (`:238`),
    matching the pattern the other long tasks already use.

Do NOT touch api_construct.py, api_db_construct.py, any handler, any queue, or the P-16/17/18 work —
that is step 2.2. If P-19 cannot pass without touching them, that is a rule-5 stop: flag it.

VERIFY (fresh evidence): the RED test now passes; `git diff --stat -- **/tests` empty except the one
new test file; full backend unit + integration suites green (zero regressions); both infrastructure
test dirs green; `cd /Users/yitzchak/Documents/dev/careervp/infra && uv sync && cdk synth` clean;
`cdk diff` shows ONLY the jitter/heartbeat property additions and ZERO stateful replacement and ~0
resource-count change (B-2-3: properties, not resources); ruff + `mypy careervp --strict` clean;
`make coverage-tests` gate exit 0 at/above baseline; naming validator
(python /Users/yitzchak/Documents/dev/careervp/src/backend/scripts/validate_naming.py --path infra
--strict) exit 0; scope-diff resolves P-19. No deploy, no merge from this session (§0.3).

--------------------------------------------------------------------------------
OUTPUT REQUIRED
--------------------------------------------------------------------------------
- The live confirmation of the gap (the grep), plain English first: retries exist, jitter absent,
  StartVPR heartbeat absent.
- The spec-brief pin from STEP 1 (the 180 s heartbeat + FULL-on-every-retry), as the spec diff.
- The new test file and its verbatim RED failure output with a one-line why, BEFORE the fix.
- The test passing after the fix, with output; the full verification results; the `cdk diff` showing
  ~0 resource-count change (B-2-3 verdict in one line).
- `git diff --stat` proving only the test file, the spec file, and artifact_chain_construct.py changed.
- A git commit message.

ALSO REQUIRED (standing rule for every wave prompt — see
/Users/yitzchak/Documents/dev/careervp/docs/db-redesign/code/code-analysis/project/runbooks/RUNBOOK-RULES.md):
- Compare what you actually built against (a) this prompt's own instructions and (b) clause P-19 in
  /Users/yitzchak/Documents/dev/careervp/docs/db-redesign/code/code-analysis/project/project-scope-lock.yaml.
  If everything matches, say so in one plain sentence. Confirm you changed NOTHING for P-16/17/18.
- If ANYTHING drifted — extra work not asked for, required work skipped, or a test/rule had to be
  weakened — STOP. Do not fix it yourself. Write one plain-English sentence a non-engineer could
  follow (what should have happened, what actually happened, why it matters), THEN the technical
  detail, and flag it for human review. Do not mark the step done.
- Update
  /Users/yitzchak/Documents/dev/careervp/docs/db-redesign/code/code-analysis/project/runbooks/wave-2-status.md:
  add a `2.3` row with a plain-English status, the commit, today's date, and what 2.4 must resolve
  first (2.4 edits api_construct.py — confirm that lock is free) or "none".

---

## 2.4 — Raise the self-throttling limit (skeleton)

| | |
|---|---|
| **Clause** | P-20 |
| **Spec** | `specs/P-20-throttle-load-spec.md` |
| **Claude / Codex** | sonnet/med · gpt-5-codex/med |
| **Depends on** | 2.2, 2.3 (same lane) |
| **Deploy target** | `CareerVpCrudDevx` |
| **Serialization** | edits `api_construct.py` |
| **Bets** | `B-2-3` |

**In plain English.** The API currently throttles itself at 2 requests/second with a burst of 10,
which is a self-inflicted outage. Raise it — but size the new number from a measurement, not a
guess.

**Done-when.** A minimal load harness exists (one hub read plus one generation flow, asserting a
99th-percentile latency), the new throttle is derived from its output, and the harness emits
startup latency so the future single-table go/no-go decision has data to use.

**Fill-in note.** The number is an output of this step, not an input. A prompt that names the new
throttle value up front has skipped the point.

---

## 2.5 — Fix the billing-reconcile entrypoint

> **FILLED IN 2026-07-25** from the skeleton below (rule 11). The session that did so read every
> Wave-2 ledger row through 2.1-GREEN first, and verified the bug live rather than trusting the
> skeleton's prose. What it found is baked into the prompt below and must still be re-confirmed from
> live at run time (§0.2):
> - **The mismatch is exact and located.**
>   `/Users/yitzchak/Documents/dev/careervp/infra/careervp/api_construct.py:3088` configures the
>   Lambda with `handler="careervp.handlers.billing_reconcile_handler.handler"`, but
>   `/Users/yitzchak/Documents/dev/careervp/src/backend/careervp/handlers/billing_reconcile_handler.py`
>   defines **`lambda_handler`** (line 34) and no `handler` symbol at all. So AWS Lambda cannot
>   import the configured entrypoint — the 02:00 `BillingReconcileScheduleRule`
>   (`api_construct.py:3106`) has never successfully run a reconcile.
> - **The repo convention is `.lambda_handler`.** 29 handler files define `lambda_handler`; only the
>   `billing_handler` and `cv_tailoring_handler` infra rows use `.handler` (and those two modules do
>   define a `handler` symbol). `billing_reconcile_handler` does not — it is the one broken row. The
>   convention-matching fix is therefore to change the infra string to `.lambda_handler`, not to add
>   a `handler` alias to the module (which would spread the minority form). GREEN picks; both are
>   recorded below with their consequences.
> - **B-2-5's port dependency is already satisfied.**
>   `/Users/yitzchak/Documents/dev/careervp/src/backend/careervp/logic/reconciliation_service.py`
>   calls `retrieve_subscription(...)`; 2.0-GREEN added that method to the `PaymentProviderInterface`
>   Protocol (landed — see the 2.0-GREEN ledger row). So putting the reconcile call on a live schedule
>   is now type-safe. Re-confirm live in the STANDING CHECK; if it were somehow not there, 2.5 is
>   blocked regardless of how small it looks.
>
> **⚠️ Serialization deviation surfaced at fill-in (rule 5 flag, do not resolve silently).** §2 lists
> `api_construct.py` as edited only by 2.2, 2.4, and 2.7. But the recommended fix edits the Handler
> string at `api_construct.py:3088`, so **that fix makes 2.5 edit `api_construct.py` too** and joins
> that serial set — 2.5's edit must not run at the same time as 2.1-GREEN or any of 2.2/2.4/2.7. The
> alternative fix (a `handler` alias in the handler module) does **not** touch `api_construct.py`.
> Whichever GREEN chooses, it states which, and if it edits `api_construct.py` it first confirms no
> other api_construct.py step is mid-flight (§2), exactly as 2.1 had to.
>
> **Header corrected against the execution plan (rules 15/16).** The skeleton read
> `opus/high · gpt-5-codex/high`. `redesign-execution-plan.md`'s own Wave-2 row for step 2.5 (line
> 287) reads **`opus/high · gpt-5.3-codex/low`**, with an explicit downgrade note (lines 290–296): a
> `Handler` attribute typo fix is neither ambiguous nor hard to get right once the bad value is
> found, so Codex reasoning stays `low` even though the file is billing-adjacent; Claude Code's
> `opus/high` is unchanged (expensive framing/citation effort, cheap mechanical edit). The corrected
> values are used below; the skeleton's `gpt-5-codex/high` was stale.

| | |
|---|---|
| **Clause** | P-02 |
| **Spec** | **none — mechanical-inline by design.** `/Users/yitzchak/Documents/dev/careervp/docs/db-redesign/code/code-analysis/project/redesign-execution-plan.md`'s step-0.4 status note (line 338) lists P-02 among the intentionally uncovered clauses (same pattern as P-22), and `scope-diff.py` reports it as a known mechanical-inline uncovered clause, not an orphan. Verified live again while filling this in (rule 14): `ls /Users/yitzchak/Documents/dev/careervp/docs/db-redesign/code/code-analysis/project/specs/` has no `P-02-*` file. Do not treat this as a missing spec to hunt for — this step's done-when below is what a spec would otherwise state. |
| **Acceptance criteria** | none authored (mechanical-inline); the three done-when bullets below are the contract this step is checked against, alongside clause P-02 in `project-scope-lock.yaml` |
| **Claude / Codex** | opus/high · gpt-5.3-codex/low |
| **Depends on** | 2.0-GREEN (landed — the port declares `retrieve_subscription`, which the reconcile path calls; see B-2-5), otherwise independent of every other Wave-2 step |
| **Deploy target** | `CareerVpCrudDevx` (manual-dispatch only per §0.3; the live-scheduled-run observation is a human/deploy follow-up, not a code-session deliverable) |
| **Rule 7** | single session, RED-first — the small-isolated-clause carve-out (see prompt header) |
| **Bets** | none new. B-2-5 is already settled by 2.0-GREEN; this step is where its reconcile call first goes live |

**In plain English.** The scheduled billing-reconciliation function points at a handler name that
does not match the code, so it has never run. Fix the name so the entrypoint resolves, prove it runs
the reconcile the way the 02:00 schedule triggers it, and leave the one-time live observation as a
human deploy check.

**Done-when.** The configured entrypoint matches the actual handler; an integration test invokes it
the way the schedule does (the exact event shape the rule sends) against a real (moto) table; a real
scheduled run is observed in logs (human/deploy follow-up, recorded in the ledger, not gating the
code landing).

**Fill-in note.** The smallest step in the wave by diff size — but not the safest. Do not bundle it
into another step to "save a deploy": that is exactly the cross-contamination Wave 1 flagged.

---

# PROMPT 2.5 — fix the billing-reconcile entrypoint (single session, RED-first)

> **Clause:** P-02 · **Spec:** none — mechanical-inline by design (see the section table above; the three done-when bullets are the contract)
> **Acceptance criteria:** none authored · **Claude: opus/high · Codex: gpt-5.3-codex/low**
> **Rule 7 — single session, RED-first.** This is the "small isolated clause" carve-out (`RUNBOOK-RULES.md` rule 7): the whole change is one entrypoint name plus its integration test, so one session may write the failing test first, observe it fail, then fix. RED-first discipline is still mandatory — you write and run the test and see it red (rule 13) BEFORE you touch the entrypoint. It is billing-adjacent, so if the change turns out to be anything larger than "make the configured entrypoint resolve and prove it runs," STOP and split it.
> **Rule 17 — every file named below is a full path from the repo root.** Keep it that way in anything you add.

```
STANDING CHECK — before doing anything else: open
/Users/yitzchak/Documents/dev/careervp/docs/db-redesign/code/code-analysis/project/runbooks/wave-2-status.md
and read the 2.0-GREEN and 2.1-GREEN rows (2.5 depends on 2.0-GREEN's port reconciliation; 2.1-GREEN
also edits api_construct.py, so if it is mid-flight you must not edit that file concurrently). If
either left something open for 2.5, deal with it FIRST. Then confirm THIS step's prerequisites are
met right now, with real commands (not memory, not this file):

  cd /Users/yitzchak/Documents/dev/careervp && git log --oneline -3
  grep -n 'handler="careervp.handlers.billing_reconcile_handler' /Users/yitzchak/Documents/dev/careervp/infra/careervp/api_construct.py
  grep -n "^def lambda_handler\|^def handler\|^handler = " /Users/yitzchak/Documents/dev/careervp/src/backend/careervp/handlers/billing_reconcile_handler.py
  grep -n "retrieve_subscription" /Users/yitzchak/Documents/dev/careervp/src/backend/careervp/payment_providers/interface.py
  grep -n "retrieve_subscription" /Users/yitzchak/Documents/dev/careervp/src/backend/careervp/logic/reconciliation_service.py

Confirm live, and STOP with a plain-English sentence if any is not true:
  - the infra Handler string still ends in `.handler` (the bug is still present — if it already reads
    `.lambda_handler`, this step is already done; say so and stop);
  - the handler module defines `lambda_handler` and NOT `handler`;
  - the port `PaymentProviderInterface` declares `retrieve_subscription` (2.0-GREEN landed — without
    it, putting reconcile live is not type-safe and 2.5 is blocked).

RULE 14 ADAPTATION — there is NO P-02 spec, by design. Do not go hunting for one and do not stop on
its absence. Confirm the absence is the DOCUMENTED intentional one, not an oversight, with a real
command:

  ls /Users/yitzchak/Documents/dev/careervp/docs/db-redesign/code/code-analysis/project/specs/ | grep -i p-02   # expect: no output
  grep -n "P-02" /Users/yitzchak/Documents/dev/careervp/docs/db-redesign/code/code-analysis/project/redesign-execution-plan.md

The execution plan's step-0.4 status note must list P-02 as intentionally mechanical-inline. If it
does NOT, that is a rule-5 stop — flag it; do not invent a spec or improvise. The three done-when
bullets in this prompt are the contract this step is checked against, together with clause P-02 in
/Users/yitzchak/Documents/dev/careervp/docs/db-redesign/code/code-analysis/project/project-scope-lock.yaml.

You are implementing clause P-02. This is a SINGLE RED-first session (rule 7 carve-out). You WRITE
THE FAILING TEST FIRST and observe it red before editing any entrypoint.

--------------------------------------------------------------------------------
FIRST — write the RED tests and observe them fail (rule 13), before any fix
--------------------------------------------------------------------------------

Put the integration test where the other billing integration tests live — confirm the directory live
(ls /Users/yitzchak/Documents/dev/careervp/src/backend/tests/integration/) — and the synth assertion
where the infrastructure synth tests live (confirm live: the same place 2.1's IAM test landed,
/Users/yitzchak/Documents/dev/careervp/src/backend/tests/infrastructure/). No real network calls;
use moto (mock_aws), the pattern tests/integration already uses. Secrets are parameter-NAME-in-env
only (P-06), never a literal.

  test_p02_reconcile_configured_entrypoint_resolves            (done-when #1)
      Synth the stack (or read the synthesized template) and extract the BillingReconcileLambda's
      `Handler` property. Split it into module + attribute and assert, on the test's OWN assertion
      (not an uncaught ImportError), that importlib can import the module and getattr finds a CALLABLE
      of that exact name. RED: the configured attribute is `handler`, which does not exist on
      careervp.handlers.billing_reconcile_handler, so the assertion fails with a clear message naming
      the missing attribute. This is the test that pins done-when #1.

  test_p02_reconcile_runs_via_configured_entrypoint            (done-when #2)
      "Invoke it the way the schedule does." Read the SAME `Handler` string from synth, resolve it to
      the callable (guarding so a missing attribute fails on this test's assertion, not a raw
      AttributeError), then invoke it against a moto table with the EXACT event the rule sends —
      `{"detail": {"action": "reconcile_subscriptions"}}` (confirm the shape live at
      /Users/yitzchak/Documents/dev/careervp/infra/careervp/api_construct.py:3106, the
      RuleTargetInput). Assert the reconcile path actually executes (e.g. it returns the
      reconcile_all summary dict / the counts shape reconcile_all produces — read
      /Users/yitzchak/Documents/dev/careervp/src/backend/careervp/logic/reconciliation_service.py:37
      live and assert on what it really returns, exact shape, no "or"). RED: fails at resolution
      because the configured entrypoint is unreachable; GREEN makes the same configured path both
      resolve and run the reconcile.

RULE 13 — run both tests, capture the failure output VERBATIM, and for EACH state why it failed (the
configured `.handler` attribute does not exist). A test that fails on a missing FIXTURE or a typo in
the test's own imports is NOT red, it is broken — structure each so it fails on ITS OWN assertion
about the configured entrypoint. State which technique you used. The full existing suite must still
be green after this step — you have ADDED tests, not changed implementation yet.

--------------------------------------------------------------------------------
THEN — make the configured entrypoint match the real handler (the whole fix)
--------------------------------------------------------------------------------

Make both RED tests pass with the SMALLEST change that makes the configured entrypoint resolve and
run. Two options; pick one, state which, and do not do more than one:

  (A) RECOMMENDED — convention-matching. Change the Handler string at
      /Users/yitzchak/Documents/dev/careervp/infra/careervp/api_construct.py:3088 from
      `careervp.handlers.billing_reconcile_handler.handler` to
      `careervp.handlers.billing_reconcile_handler.lambda_handler`, matching the 29-handler repo
      convention and the function that actually exists. THIS EDITS api_construct.py — so first
      confirm no other api_construct.py step (2.1-GREEN, 2.2, 2.4, 2.7) is mid-flight (§2), and note
      in the ledger that 2.5 joined that serial set (the rule-5 flag from the fill-in banner).

  (B) Alternative — module alias. Add `handler = lambda_handler` in
      /Users/yitzchak/Documents/dev/careervp/src/backend/careervp/handlers/billing_reconcile_handler.py.
      This does NOT touch api_construct.py (no serialization concern) but spreads the minority
      `.handler` form. If you choose this, say why you preferred it over (A).

Do NOT change anything in reconciliation_service.py or the reconcile behavior itself — the port was
already reconciled by 2.0-GREEN. If you find the reconcile logic itself needs a change to run, that
is larger than P-02 and a rule-5 stop: flag it, do not fold it in.

VERIFY: both RED tests now pass; the full backend unit + integration suites (zero regressions); the
backend and infra infrastructure test directories green if you touched infra; ruff format+check;
`mypy careervp --strict`; the coverage gate (make coverage-tests, at/above the enforced baseline);
scope-diff still resolves the Wave-2 clauses. If you edited api_construct.py: `cd
/Users/yitzchak/Documents/dev/careervp/infra && uv sync && cdk synth` clean, `cdk diff` shows the
Handler-string change and ZERO stateful replacement, and the naming validator passes
(python /Users/yitzchak/Documents/dev/careervp/src/backend/scripts/validate_naming.py --path infra
--strict). No merge to main (§0.3); no deploy from this session — the live-scheduled-run observation
(done-when #3) is a human/deploy follow-up.

--------------------------------------------------------------------------------
OUTPUT REQUIRED
--------------------------------------------------------------------------------
1. The live confirmation of the mismatch (the two grep outputs), in plain English first.
2. The new test files, and the verbatim RED failure output for each with a one-line why, BEFORE the
   fix — plus proof the rest of the suite was green at that point.
3. The one-option fix you applied (A or B), stated explicitly, and — if (A) — the api_construct.py
   serialization confirmation.
4. Both tests now passing, with output, and the full verification run results.
5. Confirmation of exactly which files changed (git diff --stat) — it should be the one test file(s)
   plus exactly one of {api_construct.py, billing_reconcile_handler.py}, nothing else.
6. A git commit message.

ALSO REQUIRED (standing rule for every wave prompt — see
/Users/yitzchak/Documents/dev/careervp/docs/db-redesign/code/code-analysis/project/runbooks/RUNBOOK-RULES.md):
- Compare what you actually built against (a) this prompt's own instructions and (b) clause P-02 in
  /Users/yitzchak/Documents/dev/careervp/docs/db-redesign/code/code-analysis/project/project-scope-lock.yaml.
  If everything matches, say so in one plain sentence.
- If ANYTHING drifted — extra work not asked for, required work skipped, or a test/rule had to be
  weakened — STOP. Do not fix it yourself. Write one plain-English sentence a non-engineer could
  follow (what should have happened, what actually happened, why it matters), THEN the technical
  detail, and flag it for human review. Do not mark the step done.
- Update
  /Users/yitzchak/Documents/dev/careervp/docs/db-redesign/code/code-analysis/project/runbooks/wave-2-status.md:
  add/update this step's row with a plain-English status, the commit, today's date, and what the NEXT
  step (the GATE) must resolve first — including the still-pending done-when #3 (a real scheduled run
  observed in devx logs), which is the one human/deploy follow-up this code session cannot close.
```

**Done-when.** Both RED tests pass; the billing-reconcile Lambda's configured `Handler` resolves to
the real callable and runs the reconcile against a moto table with the schedule's exact event shape;
the reconcile behavior itself is unchanged; `cdk diff` shows zero stateful replacement and the naming
validator passes if `api_construct.py` changed; done-when #3 (a real scheduled run observed in devx
logs) is recorded in the ledger as the remaining human/deploy follow-up.

---

## 2.5a — Repair the runtime blockers exposed by P-02

> **ADDED 2026-07-25 after 2.5 stopped correctly on rule 5.** This is the separate follow-up that
> the original 2.5 prompt required if making the configured entrypoint resolve exposed a reconcile
> behavior defect. It does not rewrite or weaken 2.5: the accepted P-02 entrypoint tests remain
> unchanged, and 2.5 stays incomplete until this follow-up makes them green.
>
> The work has two existing contract homes. The invalid active-subscription scan blocks P-02's
> already-written done-when requirement that the scheduled entrypoint run reconciliation against a
> moto table. Configuration-based provider selection is already required by AC-P25-1. Therefore
> this is a delivery split across P-02 and P-25, not a new product requirement. If
> `/Users/yitzchak/Documents/dev/careervp/docs/db-redesign/code/code-analysis/project/scope-diff.py`
> or a human reviewer
> concludes otherwise, STOP and use the §0.3 amendment process; do not silently invent a new clause.
>
> **Why RED/GREEN are separate here.** The original P-02 handler-name change qualified for rule 7's
> small mechanical carve-out. This follow-up does not: it crosses DynamoDB expression behavior,
> payment-provider selection, two billing handlers, and CDK environment configuration. It touches
> money and persisted billing state, so 2.5a-RED and 2.5a-GREEN run in separate fresh sessions.

| | |
|---|---|
| **Clause** | P-02, P-25 |
| **Spec** | P-25: `/Users/yitzchak/Documents/dev/careervp/docs/db-redesign/code/code-analysis/project/specs/P-25-payment-provider-spec.md`; P-02: none, mechanical-inline by the documented exception in `/Users/yitzchak/Documents/dev/careervp/docs/db-redesign/code/code-analysis/project/redesign-execution-plan.md` |
| **Acceptance criteria** | AC-P25-1 plus P-02 done-when #2 (the scheduled entrypoint runs reconciliation against a real moto table) |
| **Claude / Codex** | opus/high · gpt-5.3-codex/high — the Claude tier follows the existing P-25/P-02 rows; Codex `high` follows rule 16 because the defect crosses handler, provider, DAL, tests, and infrastructure |
| **Depends on** | 2.5 stopped with its RED evidence and option-A Handler change preserved; P-25/P-25b providers already landed |
| **Deploy target** | No deploy in RED or GREEN. After GREEN and full verification, P-02's existing human follow-up deploys only to `CareerVpCrudDevx` and observes one real scheduled run. |
| **Serialization** | RED edits tests only. GREEN will edit `/Users/yitzchak/Documents/dev/careervp/infra/careervp/api_construct.py`, so it joins the 2.2/2.4/2.5/2.7 serial set and may not overlap another edit to that file. |
| **Bets** | none new — the scan and provider-selection failures are observed facts, not unsettled beliefs |

**In plain English.** The schedule can now find the handler, but the job still cannot reconcile:
DynamoDB rejects its active-subscription filter, and the deployed configuration says
`PAYMENT_PROVIDER=placeholder` while the handlers ignore that setting and construct an inert
placeholder directly. Pin both failures with independent tests, then repair them without weakening
the original P-02 tests.

**Done-when.** A real moto scan returns only active current-subscription rows; configuration selects
`MockProvider` for devx and can select `StripeProvider` through a parameter-name-only secret seam;
unsupported placeholder configuration fails closed; the scheduled entrypoint processes one active
subscription with the exact result `{"status": "ok", "checked": 1, "updated": 0, "errors": 0}`;
the original P-02 entrypoint tests pass unchanged; and the full verification matrix is green before
the existing human scheduled-run follow-up.

---

# PROMPT 2.5a-RED — pin the billing-reconcile runtime blockers (tests only)

> **Clause:** P-02, P-25
> · **Spec:** P-25:
> `/Users/yitzchak/Documents/dev/careervp/docs/db-redesign/code/code-analysis/project/specs/P-25-payment-provider-spec.md`;
> P-02: none, mechanical-inline by documented exception
> · **Acceptance criteria:** AC-P25-1 plus P-02 done-when #2
> · **Claude: opus/high · Codex: gpt-5.3-codex/high**
>
> **Rule 7 RED firewall.** This session writes tests only. It may create or edit files only under
> `/Users/yitzchak/Documents/dev/careervp/src/backend/tests/` and update
> `/Users/yitzchak/Documents/dev/careervp/docs/db-redesign/code/code-analysis/project/runbooks/wave-2-status.md`.
> It must make ZERO changes under `/Users/yitzchak/Documents/dev/careervp/src/backend/careervp/` or
> `/Users/yitzchak/Documents/dev/careervp/infra/careervp/`. GREEN runs in a fresh session and may
> not edit any RED test or either accepted P-02 entrypoint test.
>
> **Rule 17.** Every file named below is a full path from the repository root. Keep that property in
> anything you add.

```
STANDING CHECK — before doing anything else: open
/Users/yitzchak/Documents/dev/careervp/docs/db-redesign/code/code-analysis/project/runbooks/wave-2-status.md.
Read every row through 2.5, including the dated "2.5 blocker delivery decision" below the table. If
the dependency chain left a different unresolved problem, deal with that FIRST — do not start this
step with unfinished business hidden behind it. Then confirm THIS step's prerequisites are actually
met right now, using real commands (not memory, not this file):

  cd /Users/yitzchak/Documents/dev/careervp
  git status --short --branch
  git log --oneline -5
  grep -n "Attr('#s')\\|ExpressionAttributeNames" /Users/yitzchak/Documents/dev/careervp/src/backend/careervp/dal/subscription_repository.py
  grep -n "PlaceholderPaymentProvider\\|PAYMENT_PROVIDER" /Users/yitzchak/Documents/dev/careervp/src/backend/careervp/handlers/billing_handler.py /Users/yitzchak/Documents/dev/careervp/src/backend/careervp/handlers/billing_reconcile_handler.py /Users/yitzchak/Documents/dev/careervp/infra/careervp/api_construct.py
  grep -n "^class MockProvider\\|^class StripeProvider" /Users/yitzchak/Documents/dev/careervp/src/backend/careervp/payment_providers/mock_provider.py /Users/yitzchak/Documents/dev/careervp/src/backend/careervp/payment_providers/stripe_provider.py
  git diff -- /Users/yitzchak/Documents/dev/careervp/src/backend/tests/infrastructure/test_p02_billing_reconcile_entrypoint.py /Users/yitzchak/Documents/dev/careervp/src/backend/tests/integration/test_p02_billing_reconcile_entrypoint.py

Confirm all of these live, or STOP in plain English:
  - the accepted P-02 tests exist and the final git-diff command is empty;
  - the scan still combines Attr('#s') with an explicit #s -> status name mapping;
  - both billing handlers still construct PlaceholderPaymentProvider directly;
  - the synthesized billing and billing-reconcile environments still say
    PAYMENT_PROVIDER=placeholder;
  - MockProvider and StripeProvider both exist and satisfy the already-landed port.

Run the cheapest live-state confirmation without printing any secret value:

  aws lambda get-function-configuration \
    --function-name careervp-billing-reconcile-lambda-dev \
    --region us-east-1 \
    --query '[Handler,Environment.Variables.PAYMENT_PROVIDER,Environment.Variables.PAYMENT_PROVIDER_PLACEHOLDER]' \
    --output json

This is read-only evidence. If credentials or network access are unavailable, record that fact and
continue from the source+synth evidence; do not replace it with a real invocation or any AWS write.

BEFORE WRITING ANY TEST (rule 14): confirm, with real commands, that
/Users/yitzchak/Documents/dev/careervp/docs/db-redesign/code/code-analysis/project/specs/P-25-payment-provider-spec.md
exists; that its "RED Tests to Write First" section names AC-P25-1; and that it contains exact briefs
for test_p25_configured_provider_factory_selects_mock_and_stripe,
test_p25_devx_billing_lambdas_configure_mock_provider, and
test_p25_active_reconcile_uses_configured_provider. Each brief must state exact values and have no
"or"-shaped assertion. If any check fails, STOP — fix the spec in a separate visible docs action;
do not write tests against an underspecified brief.

RULE 14 ADAPTATION FOR P-02: P-02 intentionally has no spec. Confirm the documented exception:

  ls /Users/yitzchak/Documents/dev/careervp/docs/db-redesign/code/code-analysis/project/specs/ | grep -i p-02
  grep -n "intentionally mechanical-inline\\|P-02" /Users/yitzchak/Documents/dev/careervp/docs/db-redesign/code/code-analysis/project/redesign-execution-plan.md

The first command must return no P-02 spec and the second must show the documented mechanical-inline
exception. If not, STOP for §0.3 review. P-02's existing done-when #2 in
/Users/yitzchak/Documents/dev/careervp/docs/db-redesign/code/code-analysis/project/runbooks/wave-2-prompts.md
is the exact contract for the scan leg; do not invent additional P-02 behavior.
```

You are writing RED tests only. Do not import or call a real provider endpoint, do not alter the
accepted P-02 tests, and do not change any implementation or infrastructure file.

## 1. Add the focused scan regression

Create
`/Users/yitzchak/Documents/dev/careervp/src/backend/tests/integration/test_p02_billing_reconcile_runtime.py`
using `moto.mock_aws`. Add:

`test_p02_scan_active_subscriptions_filters_real_moto_table`

- Create a real moto users table with `pk` and `sk`.
- Insert exactly three rows:
  - `pk=USER#active`, `sk=SUBSCRIPTION#CURRENT`, `status=active`;
  - `pk=USER#inactive`, `sk=SUBSCRIPTION#CURRENT`, `status=inactive`;
  - `pk=USER#other`, `sk=PROFILE`, `status=active`.
- Construct the real
  `/Users/yitzchak/Documents/dev/careervp/src/backend/careervp/dal/subscription_repository.py`
  repository against that table and call `scan_active_subscriptions()`.
- Guard `ClientError` and fail on the test's own assertion with a message that includes the DynamoDB
  error code and message. An uncaught `ValidationException` is a broken RED harness, not accepted
  RED evidence.
- Assert the exact returned primary-key list is `["USER#active"]`.

RED reason: boto3 treats `Attr('#s')` as the literal attribute name `#s`, creates a second name
placeholder for it, and DynamoDB rejects the separately supplied unused `#s -> status` mapping.

## 2. Pin configuration-based provider selection

Create
`/Users/yitzchak/Documents/dev/careervp/src/backend/tests/unit/test_p25_configured_provider.py`.
Implement the spec's exact
`test_p25_configured_provider_factory_selects_mock_and_stripe` brief:

- Guard import of
  `/Users/yitzchak/Documents/dev/careervp/src/backend/careervp/payment_providers/factory.py`
  inside the test and assert the module exposes a callable `get_payment_provider`; a missing module
  or callable must fail on this test's own assertion, not during collection.
- With `PAYMENT_PROVIDER=mock`, assert the exact concrete result type is `MockProvider`.
- With `PAYMENT_PROVIDER=stripe` and
  `PAYMENT_PROVIDER_API_KEY_SSM_PARAM=/careervp/test/payment-provider-api-key`, patch the runtime
  secret resolver to return a generated fixture secret. Assert it receives exactly that parameter
  name, no secret value enters the environment, and the returned type is `StripeProvider`
  configured with the resolved value. Make no HTTP call.
- Parameterize the unsupported values as exactly `["placeholder", "bogus"]`; for each, assert exact
  `PaymentProviderError.code == "PAYMENT_PROVIDER_CONFIGURATION_ERROR"`.

RED reason: no configured-provider factory exists; both handlers directly construct the placeholder.

## 3. Pin the devx Lambda configuration

Create
`/Users/yitzchak/Documents/dev/careervp/src/backend/tests/infrastructure/test_p25_provider_selection.py`.
Synthesize the devx stack using the established infrastructure-test fixture/pattern and locate
exactly these physical functions:

- `careervp-billing-lambda-devx`;
- `careervp-billing-reconcile-lambda-devx`.

Add `test_p25_devx_billing_lambdas_configure_mock_provider` and assert for both:

- `PAYMENT_PROVIDER == "mock"`;
- `PAYMENT_PROVIDER_PLACEHOLDER` is absent;
- `PAYMENT_PROVIDER_API_KEY_SSM_PARAM` is absent;
- `STRIPE_SECRET_KEY` is absent;
- the generated provider-secret fixture value is absent.

Guard missing/duplicate functions and missing environment mappings with the test's own assertions.

RED reason: both Lambdas currently synthesize `PAYMENT_PROVIDER == "placeholder"`.

## 4. Prove an active scheduled reconciliation reaches the configured provider

In
`/Users/yitzchak/Documents/dev/careervp/src/backend/tests/integration/test_p02_billing_reconcile_runtime.py`,
add `test_p25_active_reconcile_uses_configured_provider` exactly as tightened in
`/Users/yitzchak/Documents/dev/careervp/docs/db-redesign/code/code-analysis/project/specs/P-25-payment-provider-spec.md`.

- Reuse the synthesized Handler-resolution technique from the accepted
  `/Users/yitzchak/Documents/dev/careervp/src/backend/tests/integration/test_p02_billing_reconcile_entrypoint.py`
  without editing that file.
- Create the exact three-row moto table from step 1.
- Set `PAYMENT_PROVIDER=mock`.
- Invoke the synthesized callable with exactly
  `{"detail": {"action": "reconcile_subscriptions"}}` and a real Lambda-like context.
- Guard handler resolution, `ClientError`, `NotImplementedError`, and provider configuration errors
  so failure lands on this test's own assertion and names the failing layer.
- Assert the exact result is
  `{"status": "ok", "checked": 1, "updated": 0, "errors": 0}`.
- Patch HTTP clients to fail immediately if called; assert zero external network calls.

RED reason: the scan is invalid and the handler ignores `PAYMENT_PROVIDER`, so an active row cannot
be reconciled through the configured provider.

## 5. Observe RED and prove there are no unrelated regressions

Run the four new tests together and capture every failure verbatim:

```bash
cd /Users/yitzchak/Documents/dev/careervp/src/backend
uv run pytest \
  tests/integration/test_p02_billing_reconcile_runtime.py \
  tests/unit/test_p25_configured_provider.py \
  tests/infrastructure/test_p25_provider_selection.py -vv
```

For each test, state one exact failure reason. Import/collection/fixture errors and uncaught
`ClientError`/`NotImplementedError` are not accepted RED.

Run the previously accepted P-02 tests separately and record their current state:

```bash
cd /Users/yitzchak/Documents/dev/careervp/src/backend
uv run pytest \
  tests/infrastructure/test_p02_billing_reconcile_entrypoint.py \
  tests/integration/test_p02_billing_reconcile_entrypoint.py -vv
```

The resolution test should pass and the scheduled-invocation test may retain its already-recorded
scan failure. Do not edit either test.

Prove the rest of the pre-existing suites remain green by excluding only that already-known blocked
P-02 integration file and the new RED files:

```bash
cd /Users/yitzchak/Documents/dev/careervp/src/backend
uv run pytest tests/unit tests/integration \
  --ignore=tests/integration/test_p02_billing_reconcile_entrypoint.py \
  --ignore=tests/integration/test_p02_billing_reconcile_runtime.py \
  --ignore=tests/unit/test_p25_configured_provider.py -v --tb=short
uv run pytest tests/infrastructure \
  --ignore=tests/infrastructure/test_p25_provider_selection.py -v --tb=short
```

Run the mandatory test-file checks:

```bash
cd /Users/yitzchak/Documents/dev/careervp/src/backend
uv run ruff format \
  tests/integration/test_p02_billing_reconcile_runtime.py \
  tests/unit/test_p25_configured_provider.py \
  tests/infrastructure/test_p25_provider_selection.py
uv run ruff check \
  tests/integration/test_p02_billing_reconcile_runtime.py \
  tests/unit/test_p25_configured_provider.py \
  tests/infrastructure/test_p25_provider_selection.py --fix
uv run mypy \
  tests/integration/test_p02_billing_reconcile_runtime.py \
  tests/unit/test_p25_configured_provider.py \
  tests/infrastructure/test_p25_provider_selection.py --strict
```

Run the drift checker and record only the step-relevant result plus the known global baseline:

```bash
cd /Users/yitzchak/Documents/dev/careervp
python /Users/yitzchak/Documents/dev/careervp/docs/db-redesign/code/code-analysis/project/scope-diff.py --json
```

P-02 and P-25 must remain `test_written`, with no orphan spec or new tooling error. The repository
already has a global non-zero `--ci` baseline for unrelated uncovered clauses; do not fix or hide
those inside 2.5a.

Finally prove the RED firewall:

```bash
cd /Users/yitzchak/Documents/dev/careervp
git diff --stat
git diff --exit-code -- src/backend/careervp infra/careervp
git diff --exit-code -- \
  src/backend/tests/infrastructure/test_p02_billing_reconcile_entrypoint.py \
  src/backend/tests/integration/test_p02_billing_reconcile_entrypoint.py
```

No deploy, synth mutation, merge, or implementation edit is authorized in RED.

## OUTPUT REQUIRED

1. Plain-English confirmation of the two defects before technical output.
2. The exact new test files and the verbatim RED output for every new test, with a one-line reason
   for each.
3. The accepted P-02 test output, explicitly confirming neither accepted file changed.
4. Pre-existing-suite results using the exact exclusions above.
5. Ruff-format, Ruff-check, and strict-mypy results for all new tests.
6. The step-relevant scope-diff result and the unchanged global drift baseline.
7. `git diff --stat` plus proof that ZERO implementation/infrastructure files and ZERO accepted
   P-02 test files changed.
8. A git commit message; use `test: pin billing reconcile runtime blockers` unless the actual
   test-only scope justifies a more accurate message.

ALSO REQUIRED (standing rule for every wave prompt — see
/Users/yitzchak/Documents/dev/careervp/docs/db-redesign/code/code-analysis/project/runbooks/RUNBOOK-RULES.md):
- Compare what you actually built against (a) this prompt's own instructions and (b) clauses P-02
  and P-25 in
  /Users/yitzchak/Documents/dev/careervp/docs/db-redesign/code/code-analysis/project/project-scope-lock.yaml.
  If everything matches, say so in one plain sentence.
- If ANYTHING drifted — extra work not asked for, required work skipped, a test/rule weakened, or
  `/Users/yitzchak/Documents/dev/careervp/docs/db-redesign/code/code-analysis/project/scope-diff.py`
  says this delivery split needs a new clause — STOP. Do not fix it yourself. Write one
  plain-English sentence a non-engineer could follow, then the technical detail, and flag it for
  human §0.3 review. Do not mark the step done.
- Update
  /Users/yitzchak/Documents/dev/careervp/docs/db-redesign/code/code-analysis/project/runbooks/wave-2-status.md:
  update the 2.5a-RED row with plain-English status, the commit, today's date, and exactly what the
  fresh 2.5a-GREEN session must resolve first.

---

## 2.5a-GREEN — repair the billing-reconcile runtime blockers

> **FILLED IN 2026-07-25 after RED landed (rule 11).** The fill-in session read every
> `/Users/yitzchak/Documents/dev/careervp/docs/db-redesign/code/code-analysis/project/runbooks/wave-2-status.md`
> row through 2.5a-RED, verified `ec690b7` is an ancestor of HEAD, inspected all three RED files and
> both accepted P-02 files, and confirmed those five files have no post-commit diff. The exact RED
> failures recorded in the ledger are baked into the prompt below.
>
> **Name-only live check, 2026-07-25.** A read-only `aws ssm describe-parameters` query returned
> exactly `/careervp/devx/payment-provider-price-monthly`,
> `/careervp/devx/payment-provider-price-quarterly`,
> `/careervp/devx/payment-provider-webhook-secret`, and
> `/careervp/devx/payment-provider-webhook-secret-previous`. It retrieved no values. There is no
> devx payment-provider API-key parameter today, which is consistent with devx selecting
> `MockProvider`; GREEN must not create one, fetch one, or add its name/value to either devx Lambda.
>
> **Compatibility tripwire found during fill-in (rule 5).** The accepted
> `/Users/yitzchak/Documents/dev/careervp/src/backend/tests/integration/test_p02_billing_reconcile_entrypoint.py`
> invokes an empty-table reconcile without setting `PAYMENT_PROVIDER`. The new 2.5a RED active-row
> test does set it to `mock`. GREEN may not weaken fail-closed provider selection, silently default
> an absent setting, edit either test, or inject a shell-only environment value just to obtain a
> green run. Run the accepted test immediately after wiring the handler. If it now fails solely
> because its immutable harness omits the required setting, STOP for human §0.3 review: that is a
> real conflict between an older accepted test and AC-P25-1, not permission to guess a default.

| | |
|---|---|
| **Clause** | P-02, P-25 |
| **Spec** | P-25: `/Users/yitzchak/Documents/dev/careervp/docs/db-redesign/code/code-analysis/project/specs/P-25-payment-provider-spec.md`; P-02: none, mechanical-inline by documented exception |
| **Acceptance criteria** | AC-P25-1 plus P-02 done-when #2 |
| **Claude / Codex** | opus/high · gpt-5.3-codex/high |
| **Rule 7 firewall** | Run only in a fresh session after 2.5a-RED lands. GREEN may not edit the three RED files or either accepted P-02 entrypoint test. If a test looks wrong, STOP for §0.3 review. |
| **Depends on** | 2.5a-RED landed with all new tests failing on their own intended assertions and the remaining suites green |
| **Deploy target** | No deploy in GREEN. The existing P-02 human follow-up deploys only after all verification passes. |
| **Serialization** | Edits `/Users/yitzchak/Documents/dev/careervp/infra/careervp/api_construct.py`; may not overlap 2.2, 2.4, 2.5, 2.7, or another template edit. |
| **Files expected** | `/Users/yitzchak/Documents/dev/careervp/src/backend/careervp/dal/subscription_repository.py`; `/Users/yitzchak/Documents/dev/careervp/src/backend/careervp/payment_providers/factory.py`; `/Users/yitzchak/Documents/dev/careervp/src/backend/careervp/handlers/billing_handler.py`; `/Users/yitzchak/Documents/dev/careervp/src/backend/careervp/handlers/billing_reconcile_handler.py`; `/Users/yitzchak/Documents/dev/careervp/infra/careervp/api_construct.py`; `/Users/yitzchak/Documents/dev/careervp/docs/db-redesign/code/code-analysis/project/runbooks/wave-2-status.md` only beyond those |
| **Bets** | none new |

**In plain English.** Make DynamoDB's active-subscription filter valid, make both billing handlers
obey one fail-closed provider configuration seam, configure devx to use the real-HMAC MockProvider,
and prove one active scheduled subscription is reconciled without a network call.

**Done-when.** Every 2.5a-RED test and both accepted P-02 tests pass unchanged; the provider factory
selects mock and Stripe exactly as AC-P25-1 specifies while placeholder/unknown values fail closed;
both devx billing Lambdas synthesize `PAYMENT_PROVIDER=mock`; the scan returns only the active
current-subscription row; the exact active scheduled result is
`{"status": "ok", "checked": 1, "updated": 0, "errors": 0}`; full backend unit/integration and both
infrastructure suites pass; Ruff and strict mypy pass; the coverage gate passes; and
`/Users/yitzchak/Documents/dev/careervp/docs/db-redesign/code/code-analysis/project/scope-diff.py`
still reports P-02 and P-25 as `test_written` with no orphan spec or new tooling error. The script's
pre-existing global non-zero baseline for unrelated uncovered clauses must be recorded, not fixed
inside 2.5a. Lambda artifacts are rebuilt before synth; `cdk synth` is clean; `cdk diff` shows only
the intended Handler/provider environment changes with ZERO stateful replacement; verbose and
strict naming validation pass; no real provider/network call occurs in tests; no deploy or merge
occurs.

---

# PROMPT 2.5a-GREEN — make scheduled billing reconciliation work through configuration

> **Clause:** P-02, P-25
> · **Spec:** P-25:
> `/Users/yitzchak/Documents/dev/careervp/docs/db-redesign/code/code-analysis/project/specs/P-25-payment-provider-spec.md`;
> P-02: none, mechanical-inline by documented exception
> · **Acceptance criteria:** AC-P25-1 plus P-02 done-when #2
> · **Claude: opus/high · Codex: gpt-5.3-codex/high**
>
> **Rule 7 GREEN firewall.** Run in a **FRESH session** that did not write 2.5a-RED. The three RED
> files from `ec690b7` and both accepted P-02 files from `2eae38b` are immutable. Do not relax an
> assertion, add `xfail`/`skip`, change a fixture, or edit a spec brief. If any test is genuinely
> wrong rather than inconvenient, STOP for human §0.3 review.
>
> **Rule 17.** Every file named below is a full path from the repository root. Keep that property in
> anything you add.

```
STANDING CHECK — before doing anything else: open
/Users/yitzchak/Documents/dev/careervp/docs/db-redesign/code/code-analysis/project/runbooks/wave-2-status.md.
Read every row through 2.5a-RED and the dated "2.5 blocker delivery decision." The 2.5a-RED row must
show commit ec690b7 with five assertion-level failures and zero implementation/infra edits. If it
left a different problem open, handle that FIRST.

Confirm the dependency and immutable-test state with real commands:

  cd /Users/yitzchak/Documents/dev/careervp
  git status --short --branch
  git log --oneline -5
  git merge-base --is-ancestor ec690b7 HEAD
  git show --stat --oneline ec690b7
  git diff --exit-code ec690b7 -- \
    src/backend/tests/integration/test_p02_billing_reconcile_runtime.py \
    src/backend/tests/unit/test_p25_configured_provider.py \
    src/backend/tests/infrastructure/test_p25_provider_selection.py
  git diff --exit-code 2eae38b -- \
    src/backend/tests/infrastructure/test_p02_billing_reconcile_entrypoint.py \
    src/backend/tests/integration/test_p02_billing_reconcile_entrypoint.py

Every diff command must be empty. If not, STOP: GREEN does not own those changes. Also confirm that
no serialized infrastructure step is in flight: the 2.2, 2.4, and 2.7 ledger rows must still say
not started, and this command must show no pre-existing edit:

  cd /Users/yitzchak/Documents/dev/careervp
  git diff --exit-code -- infra/careervp/api_construct.py

If another session is editing that file, STOP rather than overlap it.

Confirm the failures live before changing implementation:

  cd /Users/yitzchak/Documents/dev/careervp/src/backend
  uv run pytest \
    tests/integration/test_p02_billing_reconcile_runtime.py \
    tests/unit/test_p25_configured_provider.py \
    tests/infrastructure/test_p25_provider_selection.py -vv

Expected: four named tests collect as five cases and all five fail on their own guarded assertions:
the scan and active reconcile name the unused #s mapping; both parameterized factory cases name the
missing careervp.payment_providers.factory module; and devx synth reports placeholder instead of
mock. Import/collection/fixture failures or a different failing layer are not the accepted RED
contract — STOP and explain the mismatch.

RULE 14 / RULE 7 CONTRACT CHECK — GREEN writes no tests, but it still verifies the authored source
of the immutable P-25 tests. Confirm with real commands that
/Users/yitzchak/Documents/dev/careervp/docs/db-redesign/code/code-analysis/project/specs/P-25-payment-provider-spec.md
exists, its "RED Tests to Write First" section names AC-P25-1, and it contains the exact briefs for
test_p25_configured_provider_factory_selects_mock_and_stripe,
test_p25_devx_billing_lambdas_configure_mock_provider, and
test_p25_active_reconcile_uses_configured_provider:

  cd /Users/yitzchak/Documents/dev/careervp
  test -f docs/db-redesign/code/code-analysis/project/specs/P-25-payment-provider-spec.md
  rg -n "RED Tests to Write First|AC-P25-1|test_p25_configured_provider_factory_selects_mock_and_stripe|test_p25_devx_billing_lambdas_configure_mock_provider|test_p25_active_reconcile_uses_configured_provider" \
    docs/db-redesign/code/code-analysis/project/specs/P-25-payment-provider-spec.md
  ls docs/db-redesign/code/code-analysis/project/specs/ | rg -i 'p-02' || true
  rg -n "intentionally mechanical-inline|P-02" \
    docs/db-redesign/code/code-analysis/project/redesign-execution-plan.md

P-02 must still have no spec for the documented mechanical-inline reason. Do not author one here.

Inspect the exact live implementation boundary before coding:

  cd /Users/yitzchak/Documents/dev/careervp
  sed -n '395,430p' src/backend/careervp/dal/subscription_repository.py
  sed -n '1,90p' src/backend/careervp/handlers/billing_handler.py
  sed -n '1,75p' src/backend/careervp/handlers/billing_reconcile_handler.py
  sed -n '1,90p' src/backend/careervp/logic/utils/secret_provider.py
  sed -n '55,175p' src/backend/careervp/payment_providers/interface.py
  sed -n '2945,3040p' infra/careervp/api_construct.py
  sed -n '3070,3110p' infra/careervp/api_construct.py

State the boundary before editing. Authorized production files are exactly:
  /Users/yitzchak/Documents/dev/careervp/src/backend/careervp/dal/subscription_repository.py
  /Users/yitzchak/Documents/dev/careervp/src/backend/careervp/payment_providers/factory.py
  /Users/yitzchak/Documents/dev/careervp/src/backend/careervp/handlers/billing_handler.py
  /Users/yitzchak/Documents/dev/careervp/src/backend/careervp/handlers/billing_reconcile_handler.py
  /Users/yitzchak/Documents/dev/careervp/infra/careervp/api_construct.py

The only additional tracked file authorized is:
  /Users/yitzchak/Documents/dev/careervp/docs/db-redesign/code/code-analysis/project/runbooks/wave-2-status.md

Do not edit a test, provider implementation, service, protocol, constants module, scope-lock file,
spec, workflow, or dependency manifest. If the GREEN implementation needs another tracked file,
that is a rule-5 stop; name it and explain why before proceeding.
```

Before editing, repeat the cheapest live secret check without retrieving or printing any value:

```bash
cd /Users/yitzchak/Documents/dev/careervp
aws ssm describe-parameters \
  --parameter-filters Key=Name,Option=BeginsWith,Values=/careervp/devx/payment-provider \
  --region us-east-1 \
  --query 'sort_by(Parameters,&Name)[].Name' \
  --output text
```

Record only the names. On 2026-07-25 they were the two price parameters and current/previous
webhook-secret parameters; there was no API-key parameter. If credentials or network access are
unavailable, record that and continue from this dated name-only evidence. Do not call
`get-parameter`, do not use `--with-decryption`, and do not create/copy any parameter. If an API-key
parameter now exists, record its name only; devx still selects `MockProvider` and neither Lambda may
receive that name or its value in this step.

You are implementing clauses P-02 and P-25 (AC-P25-1 plus P-02 done-when #2). You are the GREEN
session. Make the immutable RED tests pass with the following minimal implementation.

## 1. Repair only the invalid active-subscription expression

In
`/Users/yitzchak/Documents/dev/careervp/src/backend/careervp/dal/subscription_repository.py`,
keep the existing pagination, table, return type, and exact two filters. Replace the literal
`Attr('#s')` usage with a valid boto3 expression over the real `status` attribute, and remove the
now-invalid manual `ExpressionAttributeNames` mapping. The method must still filter:

- `sk == "SUBSCRIPTION#CURRENT"`;
- `status == "active"`.

Do not replace this reconciliation scan with a query, remove pagination, change the money-path GSI,
or touch IAM. P-15 deliberately preserved this separate scheduled-reconcile scan.

Run the focused test immediately:

```bash
cd /Users/yitzchak/Documents/dev/careervp/src/backend
uv run pytest \
  tests/integration/test_p02_billing_reconcile_runtime.py \
  -vv -k scan_active_subscriptions
```

It must return exactly `["USER#active"]`.

## 2. Add one fail-closed configured-provider factory

Create
`/Users/yitzchak/Documents/dev/careervp/src/backend/careervp/payment_providers/factory.py`.
Expose exactly one public function:

`get_payment_provider() -> PaymentProviderInterface`

It must:

- read `PAYMENT_PROVIDER`;
- return a new `MockProvider` only for the exact supported value `mock`;
- for the exact supported value `stripe`, require
  `PAYMENT_PROVIDER_API_KEY_SSM_PARAM`, pass that parameter **name** to the existing
  `/Users/yitzchak/Documents/dev/careervp/src/backend/careervp/logic/utils/secret_provider.py`
  resolver, and construct `StripeProvider` with the resolved value;
- raise `PaymentProviderError` with exact code
  `PAYMENT_PROVIDER_CONFIGURATION_ERROR` for `placeholder`, `bogus`, any other unknown value,
  a missing/blank provider selection, or a missing/blank Stripe parameter name;
- never read `STRIPE_SECRET_KEY`, never place the resolved value into `os.environ`, never log it,
  and never make a network call while selecting a provider.

Use the existing resolver seam; do not add a second SSM client, cache, secret abstraction, provider
registry, dependency, or placeholder fallback. Translate only configuration-selection failures
needed to keep the public factory error code stable; do not swallow arbitrary provider/runtime
errors.

Run the immutable factory test:

```bash
cd /Users/yitzchak/Documents/dev/careervp/src/backend
uv run pytest tests/unit/test_p25_configured_provider.py -vv
```

Both parameterized cases must pass, including the exact resolver-call and no-secret-in-environment
assertions.

## 3. Wire both billing handlers through the factory

In
`/Users/yitzchak/Documents/dev/careervp/src/backend/careervp/handlers/billing_handler.py`
and
`/Users/yitzchak/Documents/dev/careervp/src/backend/careervp/handlers/billing_reconcile_handler.py`:

- remove direct construction/import of `PlaceholderPaymentProvider`;
- call `get_payment_provider()` when each existing cold-start service singleton is created;
- use the configured provider for `BillingService`, `WebhookService`, and
  `ReconciliationService`;
- preserve the existing service singletons, handler signatures, Powertools decorators, webhook
  secret resolution, event routing, response shapes, and Handler → Logic → DAL separation.

Do not edit
`/Users/yitzchak/Documents/dev/careervp/src/backend/careervp/logic/billing_service.py`,
`/Users/yitzchak/Documents/dev/careervp/src/backend/careervp/logic/webhook_service.py`, or
`/Users/yitzchak/Documents/dev/careervp/src/backend/careervp/logic/reconciliation_service.py`;
2.0-GREEN already typed those consumers against `PaymentProviderInterface`.

Run the active-row contract:

```bash
cd /Users/yitzchak/Documents/dev/careervp/src/backend
uv run pytest \
  tests/integration/test_p02_billing_reconcile_runtime.py \
  -vv -k active_reconcile
```

It must return exactly `{"status": "ok", "checked": 1, "updated": 0, "errors": 0}` and record zero
external HTTP calls.

Then run both accepted P-02 tests **without** injecting `PAYMENT_PROVIDER` in the shell:

```bash
cd /Users/yitzchak/Documents/dev/careervp/src/backend
env -u PAYMENT_PROVIDER -u PAYMENT_PROVIDER_API_KEY_SSM_PARAM \
  uv run pytest \
    tests/infrastructure/test_p02_billing_reconcile_entrypoint.py \
    tests/integration/test_p02_billing_reconcile_entrypoint.py -vv
```

This is the compatibility tripwire identified during prompt fill-in. Do not edit either accepted
test, do not add a permissive default, and do not rerun with a shell-only `PAYMENT_PROVIDER=mock`
to conceal the failure. If the accepted empty-table invocation now fails solely because it omits
the required provider selection, STOP for human §0.3 review and update the ledger with the exact
conflict. Do not proceed to infrastructure or mark GREEN complete. If both pass unchanged through
a contract-valid mechanism already present in the repository, state that mechanism explicitly.

## 4. Configure only devx billing Lambdas for MockProvider

Only after the compatibility tripwire passes, edit
`/Users/yitzchak/Documents/dev/careervp/infra/careervp/api_construct.py`.
For the billing API Lambda and billing-reconcile Lambda, make devx synthesize
`PAYMENT_PROVIDER=mock`. Preserve every existing table, webhook-secret-name, price, timeout, role,
Handler, schedule, and alarm setting.

The devx environment for either Lambda must not contain:

- `PAYMENT_PROVIDER_PLACEHOLDER`;
- `PAYMENT_PROVIDER_API_KEY_SSM_PARAM`;
- `STRIPE_SECRET_KEY`;
- any secret value.

Do not create an SSM parameter or an SSM API-key permission: devx uses `MockProvider`, and the live
name-only check shows no devx API-key parameter. Do not configure Stripe for stage/prod, deploy any
environment, or change the scheduled event. If the shared construct cannot express the devx-only
selection without changing another environment's provider contract, STOP and report that scope
conflict instead of silently widening this step.

Run the immutable synth test:

```bash
cd /Users/yitzchak/Documents/dev/careervp/src/backend
uv run pytest tests/infrastructure/test_p25_provider_selection.py -vv
```

## 5. Run the complete GREEN verification matrix

First run all five immutable contract files together:

```bash
cd /Users/yitzchak/Documents/dev/careervp/src/backend
uv run pytest \
  tests/integration/test_p02_billing_reconcile_runtime.py \
  tests/unit/test_p25_configured_provider.py \
  tests/infrastructure/test_p25_provider_selection.py \
  tests/infrastructure/test_p02_billing_reconcile_entrypoint.py \
  tests/integration/test_p02_billing_reconcile_entrypoint.py -vv
```

Then prove the prior provider contracts and full repository suites remain green:

```bash
cd /Users/yitzchak/Documents/dev/careervp/src/backend
uv run pytest \
  tests/unit/test_p25_payment_provider_port.py \
  tests/unit/test_p25b_stripe_provider.py \
  tests/unit/test_p25_mock_event_id_is_stable_across_retries.py -vv
uv run pytest tests/unit tests/integration -v --tb=short
uv run pytest tests/infrastructure -v --tb=short
cd /Users/yitzchak/Documents/dev/careervp/infra
uv run pytest tests/infrastructure -v --tb=short
```

Run mandatory format, lint, and strict type checks on every changed Python file, then the
repository-wide Ruff cleanup required by the project rules:

```bash
cd /Users/yitzchak/Documents/dev/careervp/src/backend
uv run ruff format \
  careervp/dal/subscription_repository.py \
  careervp/payment_providers/factory.py \
  careervp/handlers/billing_handler.py \
  careervp/handlers/billing_reconcile_handler.py
uv run ruff check \
  careervp/dal/subscription_repository.py \
  careervp/payment_providers/factory.py \
  careervp/handlers/billing_handler.py \
  careervp/handlers/billing_reconcile_handler.py --fix
uv run mypy \
  careervp/dal/subscription_repository.py \
  careervp/payment_providers/factory.py \
  careervp/handlers/billing_handler.py \
  careervp/handlers/billing_reconcile_handler.py --strict
uv run mypy careervp --strict
uv run ruff format .
uv run ruff check --fix .

cd /Users/yitzchak/Documents/dev/careervp/infra
uv run ruff format careervp/api_construct.py
uv run ruff check careervp/api_construct.py --fix
uv run mypy careervp/api_construct.py --strict
uv run ruff format .
uv run ruff check --fix .
```

Run the enforced coverage gate and scope checker:

```bash
cd /Users/yitzchak/Documents/dev/careervp/src/backend
make coverage-tests

cd /Users/yitzchak/Documents/dev/careervp
python /Users/yitzchak/Documents/dev/careervp/docs/db-redesign/code/code-analysis/project/scope-diff.py --json
```

Coverage must remain at or above every enforced baseline. Scope-diff must keep P-02 and P-25
`test_written`, with zero orphan specs and zero tooling errors. Record the known global uncovered
baseline; do not edit either scope-lock twin or unrelated clauses.

Rebuild the Lambda artifact before synth so the asset contains the new factory and handler imports:

```bash
cd /Users/yitzchak/Documents/dev/careervp/src/backend
make build
test -f .build/lambdas/careervp/payment_providers/factory.py
```

If Docker is unavailable, STOP and report the missing verification prerequisite; do not synthesize a
stale artifact.

Run both naming validators after the infrastructure change:

```bash
cd /Users/yitzchak/Documents/dev/careervp
python src/backend/scripts/validate_naming.py --path infra --verbose
python src/backend/scripts/validate_naming.py --path infra --strict
```

Finally synthesize and diff the only authorized target:

```bash
cd /Users/yitzchak/Documents/dev/careervp/infra
uv sync
ENVIRONMENT=devx uv run cdk synth CareerVpCrudDevx -c p26_rehome_features=true
ENVIRONMENT=devx uv run cdk diff CareerVpCrudDevx -c p26_rehome_features=true
```

The diff may show only the intended provider-environment changes (plus the already-landed P-02
Handler correction if live devx does not yet have it), with ZERO stateful replacement and no new
resource. The RestApi and Cognito user-pool logical identities must remain byte-stable. If the diff
contains any other change, STOP; do not deploy it.

No deploy, merge to `main`, real Lambda invocation, real provider call, SSM write, or secret read is
authorized in GREEN. P-02 done-when #3 remains a human-only, human-gated devx deploy followed by one
real scheduled billing-reconcile log observation.

## OUTPUT REQUIRED

1. Plain-English confirmation of the five original RED failures, their commit, and the empty
   immutable-file diffs.
2. The name-only devx SSM result, explicitly confirming no value was retrieved.
3. The exact implementation files changed and the boundary chosen before coding.
4. All five 2.5a cases and both accepted P-02 tests passing unchanged; if the compatibility
   tripwire fires, the exact §0.3 stop report instead.
5. The provider factory matrix: `mock`, `stripe`, `placeholder`, `bogus`, missing/blank, including
   the exact error code and proof the Stripe secret value never enters the environment.
6. The exact active-row scan result and exact scheduled reconciliation result, plus zero external
   HTTP calls.
7. Full unit/integration, both infrastructure suites, prior P-25/P-25b regressions, coverage, Ruff,
   and strict-mypy results.
8. Scope-diff's P-02/P-25 result and the unchanged known global baseline.
9. Lambda artifact rebuild proof, devx synth/diff summary, zero stateful replacement, zero new
   resource, byte-stable immutable logical ids, and both naming-validator results.
10. `git diff --stat` and explicit proof that all five immutable test files, both scope-lock twins,
    specs, provider implementations, services, constants, workflows, and dependency manifests are
    unchanged.
11. A git commit message; use `fix: repair configured billing reconciliation` unless the actual
    implementation scope justifies a more accurate message.

ALSO REQUIRED (standing rule for every wave prompt — see
/Users/yitzchak/Documents/dev/careervp/docs/db-redesign/code/code-analysis/project/runbooks/RUNBOOK-RULES.md):
- Compare what you actually built against (a) this prompt's own instructions and (b) clauses P-02
  and P-25 in
  /Users/yitzchak/Documents/dev/careervp/docs/db-redesign/code/code-analysis/project/project-scope-lock.yaml.
  If everything matches, say so in one plain sentence.
- If ANYTHING drifted — extra work not asked for, a required item skipped, an immutable test/spec
  brief weakened, a permissive provider default added, or the delivery split no longer fits P-02
  and P-25 — STOP. Do not fix it yourself. Write one plain-English sentence a non-engineer can
  follow, then the technical detail, and flag it for human §0.3 review. Do not mark GREEN done.
- Update
  /Users/yitzchak/Documents/dev/careervp/docs/db-redesign/code/code-analysis/project/runbooks/wave-2-status.md:
  replace the 2.5a-GREEN row with the plain-English result, commit, today's date, and what the next
  step must resolve first. Even on success, carry forward P-02 done-when #3: human-gated deploy only
  to `CareerVpCrudDevx`, then observe one real scheduled billing-reconcile run in devx logs.

---

## 2.7 — Dead-letter queues for scheduled rules (skeleton)

| | |
|---|---|
| **Clause** | P-31 |
| **Spec** | `specs/P-31-eventbridge-dlq-spec.md` |
| **Claude / Codex** | sonnet/med · gpt-5-codex/med |
| **Depends on** | 2.2 (same lane) |
| **Deploy target** | `CareerVpCrudDevx` |
| **Serialization** | edits `api_construct.py` |
| **Bets** | `B-2-3` |

**In plain English.** The two scheduled rules (hourly cleanup, 2am reconcile) drop their work
silently if the target fails. Give them a dead-letter queue.

**Done-when.** Both rule targets have a dead-letter queue with an alarm; a deliberately failing
target is observed landing in it.

---

## GATE — Wave 2 close-out (skeleton)

| | |
|---|---|
| **Depends on** | 2.0, 2.1, 2.2, 2.3, 2.4, 2.5a-GREEN, completed 2.5 including its human scheduled-log observation, and 2.7 (2.0b is freeze-line, not a gate blocker) |
| **Claude / Codex** | opus/high · gpt-5-codex/high — not in `redesign-execution-plan.md`'s wave table (the GATE is a verification script, not an authored implementation clause), so picked via `RUNBOOK-RULES.md` rule 16 rather than copied from a plan row. Reasoning: cross-cutting orchestration across scope-diff, two test suites, the coverage gate, two immutable-invariant checks, a live AWS resource-count read, the deploy smoke harness, and the bets ledger — needs careful sequencing and, per rule 13, must itself be proven to fail on purpose before it's trusted, which is more than one verification pass. That lands it at `high`, not `xhigh`/`max`: it is read-only against AWS (no CFN mutation, no auth/tenancy code path), and it sits at the same tier as the two precedents it calls into — P-30's smoke harness (step 0.62) and T-09/T-07/T-06's scope-diff+oracle (step 0.2), both already `opus/high · gpt-5-codex/high` in the plan. |
| **Rule 12** | this gate is a **script**, not a reading |

**In plain English.** Wave 2 closes when someone who was not here can run one command and get the
same answer twice.

**Build `src/backend/scripts/wave_gate.py`** (rule 12) — modelled on `smoke_harness.py`, which is
the right instrument and the right precedent. It emits a dated evidence file under `docs/evidence/`
and exits non-zero on any failure. Checks that genuinely need a human print `HUMAN REQUIRED` and
fail until their evidence file exists. **A gate script that honestly covers six of eight checks is
worth more than one that pretends to cover eight.**

**Must cover, at minimum:**

1. Every Wave-2 clause resolves in `scope-diff.py`.
2. Both infrastructure test directories green — `src/backend/tests/infrastructure` **and**
   `infra/tests/infrastructure`. Wave 1's gate went amber on exactly this: one directory was
   forgotten in earlier waves.
3. Backend unit + integration + frontend suites green.
4. The coverage gate passes at or above the enforced baseline, with distance to target reported.
5. The two immutable laws hold — API and user-pool logical ids byte-stable.
6. Live resource count on `CareerVpCrudDevx` under 400, read from AWS, not from synth.
7. The deploy smoke harness at 4/4 against devx.
8. **All five bets re-read and their status recorded** (rule 9). A bet that is still open at the
   gate is either settled here or converted into a deferral with a stopping condition (rule 10).

**Also required.** Confirm `ISSUES.md` I-06 (the admin scope on the browser login client) still
carries its stopping condition and has not quietly been extended again.
