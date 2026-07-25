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

> **Fill-in progress:** 2.0b is **already filled in** (its full RED + GREEN prompts are below,
> immediately after its summary table) — 2.0-GREEN having landed unblocked it. 2.1 through 2.7
> remain skeletons.

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

```
STANDING CHECK — before doing anything else: open runbooks/wave-2-status.md and read the 2.0b-RED
row. If it left anything open (in particular, whether the B-2-1 cross-check found a divergence),
deal with that FIRST. Confirm the RED tests exist and fail, right now, with a real command:

  cd src/backend && uv run pytest tests/unit/test_p25b_stripe_provider.py -q 2>&1 | tail -20

If they pass, or fail on import/collection errors rather than their own assertions, STOP.

You are implementing clause P-25b (AC-P25b-1). You are the GREEN session. You may not edit the RED
test file. Build:

1. careervp/payment_providers/stripe_provider.py — StripeProvider implementing
   PaymentProviderInterface (all methods the port declares, including retrieve_subscription).
   construct_webhook_event must verify the REAL Stripe signature scheme confirmed by 2.0b-RED's
   cross-check:
     - PREFER the official `stripe` SDK's verification (stripe.Webhook.construct_event /
       WebhookSignature.verify_header) IF `stripe` is already a project dependency. If it is NOT a
       dependency, that is a decision, not a default: adding a runtime dependency to the money path
       is a rule-5 flag — either implement Stripe's DOCUMENTED v1 HMAC scheme directly (identical to
       what the cross-check validated in mock_provider.py) OR propose the dependency to the human.
       Do not silently `uv add stripe`. State which path you took and why.
     - Distinct error codes for tamper/wrong-secret vs replay/stale-timestamp, matching what the RED
       tests assert.
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
  anything the NEXT step must resolve first (or write "none"). Also record in ISSUES.md that B-2-1
  is now proven against the real provider (or, if the cross-check diverged, what changed).
- FREEZE-LINE confirmation (rule 5): state explicitly whether any part of the signature-verification
  path is untested when this session ends. If it is, that is a STOP condition, not a note for later
  — a paid launch must not run untested verification code (AC-P25b-1).
```

---

## 2.1 — Don't charge twice; stop scanning the money path (skeleton)

| | |
|---|---|
| **Clauses** | P-14, P-15 |
| **Spec** | `specs/P-14-P-15-billing-idempotency-scan-spec.md` |
| **Claude / Codex** | opus/high · gpt-5-codex/high |
| **Depends on** | 2.0-GREEN |
| **Deploy target** | `CareerVpCrudDevx` |
| **Rule 7** | RED and GREEN separate — money path |
| **Bets** | `B-2-2` (the event id is a safe idempotency key) · `B-2-3` (resource count) |

**In plain English.** Make sure a payment event that arrives twice is only acted on once, and stop
the billing code from scanning the whole table to find a customer.

**Known before you start.** `logic/webhook_service.py` already keys on `event.event_id` via
`record_payment_event(...)`, with commit-after-work and a `delete_payment_event` release on failure.
The contract records this clause's state as "table empty, unwired." **Both may be true** — the code
path may exist while nothing writes to the table in a deployed environment. Establish which, from
live, before writing anything. That determination is this step's first output.

**Done-when.** A replayed webhook is provably suppressed against a real table (not a mock); the
customer-id lookup uses a named index with zero scans on the money path; the access pattern is
recorded. Resource count checked after the change (`B-2-3`).

**Owns `test_p25_mock_event_id_is_stable_across_retries`** (reassigned from 2.0-RED, 2026-07-25 —
see that prompt's resolved note). Two deliveries of the SAME event, through the provider's own
retry path, must carry the same `event_id`, and the second delivery must be suppressed by this
step's idempotency wiring against a real table. This is the direct settlement of bet `B-2-2` — do
not treat it as optional or fold it silently into a differently-named test.

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

## 2.5 — Fix the billing-reconcile entrypoint (skeleton)

| | |
|---|---|
| **Clause** | P-02 |
| **Spec** | **none — mechanical-inline by design.** `redesign-execution-plan.md`'s own step-0.4 status note lists P-02 among the intentionally uncovered clauses (same pattern as P-22). Verified live (rule 14) while writing this skeleton: `ls specs/` has no `P-02-*` file. Do not treat this as a missing spec to hunt for — this step's done-when below is what a spec would otherwise state. |
| **Claude / Codex** | opus/high · gpt-5-codex/high |
| **Depends on** | Wave 1 (independent of every other Wave-2 step) |
| **Deploy target** | `CareerVpCrudDevx` |
| **Bets** | none |

**In plain English.** The scheduled billing-reconciliation function points at a handler name that
does not match the code, so it has never run.

**Done-when.** The configured entrypoint matches the actual handler; an integration test invokes it
the way the schedule does; a real scheduled run is observed in logs.

**⚠️ Not as independent as it looks — read this before filling it in.** `logic/reconciliation_service.py`
calls `retrieve_subscription(...)` on the payment provider, and the port **does not declare that
method** (see bet `B-2-5`). Because this entrypoint has never run, that call has never executed in a
deployed environment. Fixing the entrypoint name puts it on a live schedule for the first time.
**2.0-GREEN must have reconciled the port first.** If 2.0 has not landed, this step is blocked
regardless of how small it looks.

**Fill-in note.** The smallest step in the wave by diff size — but not the safest. Do not bundle it
into another step to "save a deploy": that is exactly the cross-contamination Wave 1 flagged.

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
| **Depends on** | 2.0, 2.1, 2.2, 2.3, 2.4, 2.5, 2.7 (2.0b is freeze-line, not a gate blocker) |
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
