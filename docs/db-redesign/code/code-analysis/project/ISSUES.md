# Issues Tracker

Known issues surfaced during the redesign that are **real but deliberately deferred** — each
is parked here rather than silently absorbed into whatever step happened to find it.

This file is *not* the contract. Nothing here is a scope-lock clause, and nothing here is a
commitment. It is the holding pen: an issue leaves this file either by being promoted into a
scope-lock clause (via the §0.3 amendment protocol) or by being closed with a reason.

| Field | Meaning |
|-------|---------|
| **Found** | When and by which step the issue surfaced |
| **Severity** | `high` (will bite a real user), `medium` (will bite an operator), `low` (hygiene) |
| **Disposition** | What we decided to do *for now*, and why that is defensible |
| **Trigger** | The condition that should force this back onto the table |
| **Stopping condition** | When the trigger fires and the work still is not done — what smaller thing ships instead. Added 2026-07-24 per `RUNBOOK-RULES.md` rule 10. Must be observable (a date, or a state you can query), never a judgement call. |

This file also holds the **bets** each wave rests on (`RUNBOOK-RULES.md` rule 9) — beliefs that
are load-bearing, might be false, and each carry the check that would disprove them and the
fallback decided in advance. Bets are numbered `B-<wave>-<n>` and are **re-read at that wave's
gate**. A bet that turns out to underwrite a locked decision gets promoted into
`project-scope-lock.yaml` by human amendment; agents may write here but never there.

---

## I-01 — No presigned-upload route: CV upload is inline base64 through Lambda

- **Found:** 2026-07-12, step 0.64b (running the P-30 smoke harness against the custom domain).
- **Severity:** medium — becomes **high** the first time a user uploads a large scanned CV.
- **Status:** OPEN, deferred.

**What is true.** The API has no presigned-upload endpoint. `POST /users/me/cv` takes the file
inline as base64 `cv_content` and the handler performs the S3 `put_object` itself
(`src/backend/careervp/handlers/cv_upload_handler.py`). All 58 deployed routes were enumerated:
no upload/presign surface exists anywhere. The only presigned URLs in the system are for
**download** (`export_handler`, `vpr_status_handler`, and frontend-contract rule 8).

**Why it matters.** Inline base64 through API Gateway + Lambda inherits two hard ceilings:
API Gateway caps the request payload at **10 MB**, Lambda at **6 MB** synchronous — and base64
inflates the payload by ~33%, so the *effective* file limit is roughly **4.5 MB**. A scanned-PDF
CV clears that easily. The failure mode is a hard 413 with no graceful path, and it is invisible
in dev because test CVs are small.

**How this was discovered.** P-30's 4th wire was written as `presigned_upload` against an endpoint
that never existed and was never planned — it 404'd identically on the custom domain *and* on the
raw `execute-api` URL. The wire was repointed to the real upload path (scope-lock v2.3.0). That
fixes the *canary*; it does not fix the *ceiling*, which is this issue.

**Disposition.** Not fixed now, deliberately. A presigned-PUT upload path is a real feature
(new route + handler + bucket CORS + a frontend change to do the direct PUT), and Wave 0 is
guardrails-and-truth. P-30 is a deploy-canary clause, not a feature clause — building a feature
inside it would be exactly the scope smuggling the contract exists to prevent.

**Trigger — promote to a clause when any of these is true:**
- a real user hits the ~4.5 MB ceiling (watch for 413s on `POST /users/me/cv`), **or**
- OCR / scanned-PDF ingest is picked up (it is V2-deferred today, and it *guarantees* large files), **or**
- Wave 4's NFR-SCALE work is scheduled — this belongs in that conversation.

---

## I-02 — The P-30 upload wire has a per-run side effect: an AI parse and a persisted CV row

- **Found:** 2026-07-12, step 0.64b (implementing the wire-4 repoint).
- **Severity:** low now, medium once the canary runs on every deploy as intended.
- **Status:** OPEN, accepted for now.

**What is true.** `POST /users/me/cv` does not just write to S3 — it then calls `parse_cv`, which
invokes the AI parser, and persists a CV row. So every P-30 smoke run costs one Haiku parse and
leaves a CV behind for the smoke user. The dev smoke user already carries **13** accumulated CVs.

**Why it is accepted.** This *is* the real user write path, and a canary that does not exercise
the real path is a canary that lies. The cost is genuinely small (one Haiku call on a ~200-byte
document). The pollution is confined to one synthetic user and is not user-visible.

**Why it is still an issue.** P-30's whole point is "baseline green **before and after** each
change" — so the run count is 2× every risky deploy, forever, and the CV rows grow without bound.
An unbounded-growth test fixture is the kind of thing that is free until it is suddenly not.

**Trigger — fix when any of these is true:**
- the smoke harness is wired into CI/CD to run automatically (right now it is human-invoked), **or**
- the smoke user's CV count starts affecting the read-back assertion's latency, **or**
- the AI-parse cost shows up in the P-32 cost-anomaly monitor.

**Likely fix.** A teardown step (`DELETE` the CV the wire just created — note this needs a delete
route that may not exist), or a dedicated smoke tenant with a short S3/DynamoDB TTL.

---

## I-03 — "Deploy Frontend" does not deploy the frontend

- **Found:** 2026-07-12, step 0.64b (getting the workflow green for O-9).
- **Severity:** low — naming/expectation hazard, not a defect.
- **Status:** OPEN, cosmetic.

**What is true.** After the 3d28d7d rewrite, `.github/workflows/deploy-frontend.yml` runs
typecheck + unit + integration + `next build`. It does **not** deploy: Amplify deploys itself from
its own branch webhook. The workflow is a *build-validation gate*, and its old S3-sync deploy path
(which is what had been failing since 2026-05-03 with `Credentials could not be loaded` — it used
OIDC creds that were never wired up) was correctly deleted.

**Why it matters.** A workflow named "Deploy Frontend" that is green will be read by a future
operator as "the frontend deployed." It did not. That misreading is exactly how a bad build reaches
users under a green check.

**Disposition.** Renaming a workflow is trivial but touches CI identity (branch protection required
checks reference workflow names), so it is not worth doing mid-O-9. Rename to
`Validate Frontend Build` when CI required-checks are next touched.

**Also noted (trivial):** the workflow emits a Node 20 deprecation warning
(`actions/checkout@v4`, `actions/setup-node@v4` are being forced onto Node 24). Harmless today;
bump the action majors when convenient.

---

## I-04 — The frontend build gate does not run on feature branches

- **Found:** 2026-07-12, step 0.64b.
- **Severity:** low.
- **Status:** OPEN.

**What is true.** `deploy-frontend.yml` triggers on `push` to **main** (path-filtered to
`src/frontend/**`) plus manual `workflow_dispatch`. So frontend regressions on a feature branch are
not caught by *this* workflow until they land on main — the point at which Amplify also picks them up.

**Why it is not urgent.** Frontend typecheck/unit/integration are covered on branches by the other
CI workflows (`ui-upgrade-checks`, `db-redesign-checks`), so the coverage gap is narrower than it
looks. This is about the *gate* being main-only, not about the checks being absent.

**Trigger.** Fold into the same pass as I-03 (CI required-checks review).

---

## I-05 — A backend unit test is red on `db-redesign`: AI-assist reports 0 tokens

- **Found:** 2026-07-12, step 0.64b (running the mandatory backend suite before committing).
- **Severity:** medium — it is either a real metering bug or a stale test, and we do not yet know which.
- **Status:** OPEN, **not** introduced by 0.64b.

**What is true.** `tests/unit/test_ai_assist_handler.py::test_success_returns_200_with_resolved_context`
fails on `assert body['tokens'] >= 1` with `assert 0 >= 1`. The rest of the suite is green
(1330 passed / 1 failed). Confirmed pre-existing by stashing the 0.64b changes and re-running on a
clean tree — it fails identically, so it is not fallout from the smoke-harness work.

**Why it matters — and why it should not just be silenced.** The assertion is about **token
metering**, and Q-10 ("real token metering; retire the `len/4` estimate") is a T1 launch-blocker
clause tied to NFR-COST-1 and the 91% margin target. A handler reporting `tokens: 0` is exactly the
symptom Q-10 exists to eliminate. So the honest reading is: this is either (a) the AI-assist path
genuinely not metering tokens — in which case it is a real Q-10 defect wearing a test's clothes —
or (b) a test whose mock stopped supplying a usage block. Those have very different fixes, and
guessing between them is how a cost bug ships.

**Disposition.** Left red, deliberately, and surfaced here rather than fixed inside an unrelated
step (0.64b is the O-9/custom-domain slice; fixing a metering bug in it would be scope smuggling —
and "make the test pass" is the specific temptation to avoid until (a) vs (b) is settled).

**Trigger.** Diagnose before Q-10's step runs — Q-10 cannot be evidenced as done while this is red.
Start by checking whether the handler reads a real `usage` block from the Anthropic response or
still falls back to an estimate.

---

## I-06 — The browser login client still holds the admin scope and the insecure grant

- **Found:** 2026-07-18, step 1.3c. Tracked until now only as a row in `redesign-execution-plan.md`.
- **Severity:** high — an admin-level scope on a public browser client is a privilege-escalation
  primitive, and the insecure grant puts tokens in URLs.
- **Status:** OPEN, deferred.

**What is true.** Removing `COGNITO_ADMIN` and the implicit grant from the browser client requires
backend endpoints for password change and two-factor enrollment first. The scope-usage inventory in
commit `4228346` classifies all five current usages as `temporarily_allowed` and **none** as
`backend_proxy`. Remove the scope before those endpoints exist and password change and two-factor
enrollment break for real users.

**Why it is here now.** It was deferred on 2026-07-18 with a home and a trigger but no stopping
condition, and the migration window has been open ever since. It also never entered this file,
which is the one place deferrals are supposed to live — so the mechanism built to catch exactly
this case was bypassed by that case. Recorded here per `RUNBOOK-RULES.md` rule 10.

**Disposition.** Not fixed in Wave 1 or Wave 2. It does not gate either: the Wave-1 auth work
removed a header-trust fallback and a dead environment variable and never touched the login flows.
It stops being theoretical at staging promotion, where three real accounts are in scope.

**Trigger.** Staging promotion.

**Stopping condition.** If the backend password-change and two-factor-enrollment endpoints are not
built when staging is otherwise ready to promote, staging promotes anyway in this reduced form:
the implicit grant is **disabled**, the admin scope is **retained**, and self-service password
change and two-factor enrollment are **turned off in the staging interface** — three users,
administrator reset instead. Worse product, bounded risk, and the window closes on the half that
actually leaks tokens. This is a pre-authorised fallback, not permission to skip the work; the
endpoints remain required before any production promotion or paid launch.

---

# Wave-2 bets

Per `RUNBOOK-RULES.md` rule 9. Each is a belief Wave 2 rests on that could be false, with the check
that would show it and the fallback decided now. **All five are re-read at the Wave-2 gate.** They
are ordered by how much downstream work they delete if wrong, not by severity.

---

## B-2-1 — The mock provider's signature scheme is a faithful stand-in for Stripe's

- **Load-bearing for:** 2.0, 2.0b, 2.1. Deletes the most work if wrong.

**The belief.** A signature check built for the mock provider can be replaced by Stripe's without
changing the port's shape or the tests written against it.

**Why it is a bet and not a fact.** The port declares
`construct_webhook_event(payload: bytes, signature: str, secret: str)` — a *single* signature
string (`payment_providers/interface.py`). Stripe's real header is compound: a timestamp and one or
more signatures in one value (`t=...,v1=...`), and replay rejection needs the timestamp *out of that
header*. If the mock is implemented as "signature is a bare hex digest" and takes its timestamp from
somewhere else, then the replay-rejection test required by the spec is written against a shape
Stripe cannot satisfy, and step 2.0b rewrites both the provider and the tests. The whole point of
the mock's signature check being cryptographically real (rather than tautological) is defeated if it
is real in a different scheme.

**The check.** Before 2.1 starts, diff the mock's header format against Stripe's documented
`Stripe-Signature` format and confirm the mock parses timestamp and digest out of one compound
string. Concretely: `construct_webhook_event` must reject a payload whose digest is valid but whose
timestamp is outside tolerance, with the timestamp read from the `signature` argument and nowhere
else.

**The fallback.** Write Stripe's verification first and make the mock conform to it, rather than the
reverse. Cheap now — the compound-header parse is a few lines. A rewrite of every idempotency and
replay test later.

**Settled 2026-07-25 (step 2.0-RED) — canonical format fixed, written so 2.0b can check Stripe
against it.** A SINGLE compound string `t=<unix>,v1=<hex>`, where
`v1 = HMAC-SHA256(secret, f"{t}.{payload}")` over the exact raw body bytes; freshness window = 300 s
(named constant `WEBHOOK_TIMESTAMP_TOLERANCE_SECONDS`). This is Stripe's `Stripe-Signature` scheme.
The RED tests (`src/backend/tests/unit/test_p25_payment_provider_port.py`) encode it in a local
`_sign()` helper and FORCE the mock to read the timestamp out of that one string: the replay test
signs a *stale* timestamp into the signature while leaving the payload body's `created` field
*fresh*, so a mock that reads the body — or skips the timestamp — is rejected. Proven to have teeth
in a scratch harness: a body-ignoring mock fails the tamper test; a no-timestamp-check mock fails the
replay test. **2.0b's remaining job:** confirm real Stripe uses `t`/`v1`, HMAC over `{t}.{payload}`,
default tolerance 300 s — if any differs, the port shape and these tests change at 2.0b, not in 2.1.
Status: open → format decided; Stripe cross-check is 2.0b's.

**Implemented 2026-07-25 (step 2.0-GREEN).** The scheme is now real code, not just a decided format:
`careervp/payment_providers/mock_provider.py:MockProvider.construct_webhook_event` parses
`t=<unix>,v1=<hex>` out of the single signature string, recomputes
`HMAC-SHA256(secret, f"{t}.{payload}")` over the raw body bytes, constant-time-compares
(`hmac.compare_digest`), and only then rejects a timestamp outside `WEBHOOK_TIMESTAMP_TOLERANCE_SECONDS`
(300 s) with code `WEBHOOK_TIMESTAMP_OUT_OF_TOLERANCE`. The two RED negative tests
(`rejects_tampered_signature`, `rejects_replay_timestamp`) now pass against this real check, so the
"cryptographically real, not tautological" requirement is satisfied in code. **Unchanged for 2.0b:**
the Stripe cross-check against these exact constants is still owed before 2.1 — they are named
constants in `mock_provider.py`, so 2.0b diffs against one file.

**Cross-checked 2026-07-25 (step 2.0b-RED) — B-2-1 is FALSE because rotation handling diverges.**

1. **Header format: DIVERGES at multiple-`v1` verification.** Stripe documents one compound
   `Stripe-Signature` header containing `t=<unix>` plus one or more `v1=<hex>` values, with other
   scheme pairs such as `v0` ignored. During a signing-secret roll Stripe emits one `v1` per active
   secret, and its official Python SDK collects every `v1` and accepts when *any* one matches.
   `MockProvider._parse_signature`, by contrast, retains only the first `v1`. A live probe with a
   non-matching first `v1`, matching second `v1`, and extra `v0` produced:
   `REJECTED_MATCHING_SECOND_V1 code=WEBHOOK_SIGNATURE_VERIFICATION_FAILED`. The mock tolerates the
   extra pairs syntactically but does not reproduce Stripe's rotation behavior.
2. **Signed payload: MATCH.** Stripe constructs `signed_payload` as the decimal timestamp, one
   period, then the exact raw request body, and computes HMAC-SHA256 with the endpoint secret.
   The mock constructs the identical byte sequence:
   `f'{timestamp}.'.encode('utf-8') + payload`.
3. **Tolerance: MATCH.** Stripe's official libraries default to five minutes (`300` seconds), and
   verification is reconstructed by the caller from the raw payload, signature header, endpoint
   secret, and optional tolerance. The mock's
   `WEBHOOK_TIMESTAMP_TOLERANCE_SECONDS = 300` therefore matches this caller-side replay window.

Official sources: [Stripe manual signature verification](https://docs.stripe.com/webhooks#verify-manually),
[Stripe replay prevention and secret rolling](https://docs.stripe.com/webhooks#preventing-replay-attacks),
and [stripe-python webhook verifier](https://github.com/stripe/stripe-python/blob/master/stripe/_webhook.py).

**Required consequence (flagged; not fixed in this RED session):** `StripeProvider` must implement
Stripe's real any-matching-`v1` behavior and must not inherit the mock's first-`v1` limitation.
The 2.0-GREEN mock tests need a follow-up RED test for a matching second `v1`, followed by a separate
GREEN fix to the mock parser. Points 2 and 3 need no follow-up.

**Sequencing correction 2026-07-25 (orchestrator).** The two consequences above are **independent**,
and the mock fix does **not** gate `StripeProvider`:
- Both P-25b RED tests (`test_p25b_stripe_provider.py:126,159`) exercise `StripeProvider` **only**
  (`provider = StripeProvider()`; `_assert_signature_negatives` always receives
  `provider.construct_webhook_event`). Neither touches `MockProvider`. So **2.0b-GREEN builds
  StripeProvider self-contained with any-matching-`v1`** and makes both tests pass with zero mock and
  zero test edits — it is unblocked. (A first 2.0b-GREEN attempt stopped, reading the 2.0b-RED
  ledger cell as requiring the mock fix first; that cell was over-scoped and is corrected in
  `wave-2-status.md`.)
- The mock's first-`v1`-only gap is real but **currently INERT** — no test or consumer feeds the
  mock a multi-`v1` header, so no existing test is wrong. It is tracked as **follow-up `2.0b-mock`**
  in `wave-2-prompts.md` (this bet's pre-committed "make the mock conform" fallback), file-isolated
  from `stripe_provider.py` and therefore parallel-safe, recommended after 2.0b-GREEN. **B-2-1 stays
  FALSE until 2.0b-mock lands**; the GATE re-reads it (rule 9).

**Proven against the real provider 2026-07-25 (step 2.0b-GREEN).** `StripeProvider` now implements
the cross-checked Stripe behavior independently: it collects every `v1` from the compound header
and accepts when any digest constant-time-matches the HMAC over `{timestamp}.{raw_payload}`. The
P-25b test header places a non-matching digest first and the matching digest second, and both the
real-signature test and paid-launch gate pass against that provider. The official `stripe` SDK was
not in `pyproject.toml` or `uv.lock`, so no money-path dependency was silently added; the provider
uses the documented scheme directly, while its API-call methods use the already-present `httpx`
runtime dependency. Tampered body, wrong secret, and a valid digest signed 301 seconds ago execute
the distinct frozen negative paths with no network call. **B-2-1 remains FALSE:** this proves the
real provider is correct, but the mock remains first-`v1`-only until the separate `2.0b-mock`
RED/GREEN follow-up lands.

**Settled TRUE 2026-07-25 (step 2.0b-mock-GREEN).** `MockProvider` now conforms to the same rotation
behavior as `StripeProvider`: `_parse_signature` collects all non-empty `v1` digests from the
compound header, and `construct_webhook_event` accepts when any provided digest constant-time-matches
the expected HMAC over `{timestamp}.{raw_payload}`. The mock no longer verifies only the first `v1`;
a header with a non-matching first `v1` and matching second `v1` now passes, while no matching `v1`
still fails with `WEBHOOK_SIGNATURE_VERIFICATION_FAILED` and missing `t`/all `v1` remains
`WEBHOOK_SIGNATURE_MALFORMED`. Evidence: `test_p25_mock_webhook_accepts_matching_second_v1` passes,
all five P-25 mock tests pass, and both P-25b StripeProvider tests remain green. Both providers are
now faithful to Stripe's secret-rotation behavior, so B-2-1 is TRUE.

---

## B-2-2 — The provider's event id is a stable, safe idempotency key

- **Load-bearing for:** 2.1 (the money path).

**The belief.** `WebhookEvent.event_id` is unique per real-world event, stable across provider
retries of the same event, and different across genuinely distinct events.

**Why it is a bet.** Step 2.1 wires idempotency "via the port's event id." The existing webhook
service already keys on it — `record_payment_event(event.event_id, event.event_type)` returns
whether the event is new, with a commit-after-work release on failure. So the mechanism is partly
built *already*, against a mock whose ids are generated locally. If the mock issues a fresh id per
delivery attempt where Stripe reuses one, every duplicate-suppression test passes while the real
system double-charges on a provider retry. That is the single worst failure available in this wave.

**The check.** Assert directly that two deliveries of the *same* event carry the same `event_id`,
and that the second is suppressed — using the mock's own retry path, not two hand-built payloads.
Then confirm against Stripe's documented retry semantics that its `evt_` id is stable across
retries of one event.

**The fallback.** If the ids are not stable, key idempotency on a digest of the verified raw payload
instead of on `event_id`, and record that as the port's contract. Decide this before 2.1 writes its
tests, not after.

**Addressed 2026-07-25 (step 2.0-RED) — decision fixed now; the strong test is assigned to 2.1.**
The footgun ("a FRESH id per delivery attempt where Stripe reuses ONE id") lives in the mock's event
*generation/emission* surface. Clause P-25 scopes the mock to "signs test webhooks + returns
realistic subscription/customer objects"; it has no retry/emission API, and inventing one at 2.0 to
test it would over-reach the clause (rule 5). A 2.0-only test over `construct_webhook_event` parsing
could assert only "same payload → same id", which is trivially green for any id-from-payload mock and
does NOT exercise the footgun — the weak version the prompt forbids. So
`test_p25_mock_event_id_is_stable_across_retries` is deliberately NOT in the 2.0 RED file; it moves
to **2.1** (the money path, which this bet is load-bearing for and where the emission + idempotency
wiring lives). **Decision fixed now (the bet's job):** `WebhookEvent.event_id` MUST be stable across
provider retries of one event; idempotency keys on it (`record_payment_event`). If a provider cannot
guarantee a stable id, idempotency keys on a digest of the verified raw payload instead — decided now,
before 2.1 writes its tests, per this bet's own fallback. Status: open (test lands in 2.1).

**Parsing side confirmed 2026-07-25 (step 2.0-GREEN); emission side still 2.1's.**
`MockProvider.construct_webhook_event` derives `WebhookEvent.event_id` from the verified body's `id`
field (`body.get('id', …)`), so "same verified payload → same `event_id`" holds by construction on the
parse path — consistent with the decision above. This is exactly the *weak* half the RED note flagged:
it does NOT exercise the fresh-id-per-delivery-attempt footgun, which lives in the mock's
emission/retry surface (not built at 2.0). So the strong
`test_p25_mock_event_id_is_stable_across_retries` remains **assigned to 2.1**, together with the
digest-fallback wiring if a real provider's id turns out unstable. Status: unchanged — open, test lands
in 2.1; nothing at 2.0-GREEN moved it.

---

## B-2-3 — Wave 2's added resources stay under the CloudFormation ceiling

- **Load-bearing for:** 2.1, 2.2, 2.7 — and the reason to check early rather than at the gate.

**The belief.** Wave 2's additive infrastructure fits without another decomposition.

**Why it is a bet.** This exact ceiling has already bitten once: it was filed as a minor guardrail
and turned out to hard-block four clauses, discovered mid-Wave-1, costing a contract amendment and a
parallel-stack redesign. Wave 2 is the most additive wave remaining — eight dead-letter queues,
reserved concurrency across consumers, EventBridge target queues, and their alarms. The current
devx stack is 211 physical resources (100 parent, 11 in one nested stack, **100 in the features
nested stack**). That 100 is close enough to matter.

**The check.** `cdk synth` resource count **after every additive step**, not once at the gate. The
`resource_count<400` continuous-integration gate already exists; this makes it a per-step
observation so the trend is visible before it is a wall.

**The fallback.** If a step would cross the line, that step splits its resources into a new nested
stack of its own rather than growing the features stack — decided now, so it is a planned move
rather than an emergency redesign. Never move the API or the user pool.

---

## B-2-4 — "Deploy" means devx

- **Load-bearing for:** every Wave-2 step that reaches AWS.
- **Status (2026-07-25): decision made, code not yet updated.** See below.

**The belief.** Wave-2 code lands on `CareerVpCrudDevx` and nowhere else.

**Why it was a bet.** It was false on one path. `deploy.yml` sets `STACK_NAME: 'CareerVpCrudDev'`
as a workflow-wide constant and the push-to-`main` jobs hardcode the old environment, its
parameter-store paths, and its parity target. Manual dispatch maps targets correctly and refuses
to guess; merging did not. Separately, the approval gate was bound to a deployment environment
named `deploy-dev`, which did not cover devx deploys at all.

**Resolved (2026-07-25), human decision: devx is the primary development environment; deploys
should go only to devx.** `CareerVpCrudDev` is being retired, not extended — devx is the P-26
v2.6.0 parallel-stack architecture (`ENVIRONMENT=devx`, `p26_rehome_features=true`, features
rehomed into `CrudFeaturesNestedStack`), already proven at 211 resources against the old shape's
near-400. This settles the *decision* this bet was checking for.

**What is actually true right now, checked live:**
- ✅ The `devx` GitHub deployment environment exists with a required reviewer (verified
  2026-07-25) — see `runbooks/p28-human-gated-deploy-runbook.md` §2a.
- ✅ Manual `workflow_dispatch` now defaults to `devx` and correctly maps every target.
- ❌ **`deploy.yml`'s push-to-`main` path still targets `CareerVpCrudDev`.** This is now a known
  contradiction between policy and code, not an open question — the decision is made, the CI
  change to act on it is not. Do not read "decided" as "done."

**The fallback, still in force:** Wave-2 deploys are manual-dispatch only (already defaults to
`devx`), and **no Wave-2 work merges to `main`** until the push-to-`main` target is fixed —
merging today would still silently deploy to the stack being retired.

---

## B-2-5 — Billing already depends on the port, so 2.0 is small

- **Load-bearing for:** the effort estimate on 2.0, and on 2.1 inheriting a clean seam.

**The belief.** The payment port exists and its consumers already use it, so the first step is
mostly adding a mock provider.

**Why it is a bet — and it is already false.** The consumers inject the provider, but typed as
`Any` (`logic/billing_service.py`, `logic/webhook_service.py`), so **nothing enforces the port** —
strict type checking cannot see a mismatch. And there is one, in **two** consumers:

- `logic/webhook_service.py:115` — `self._payment_provider.retrieve_subscription(subscription_id)`
- `logic/reconciliation_service.py:53` — the same call, and its module docstring (`:6`) documents
  `retrieve_subscription(...)` as a step in the expected provider contract

`retrieve_subscription` is **not declared by the Protocol at all** — the port declares exactly five
methods (`create_customer`, `create_checkout_session`, `create_portal_session`,
`construct_webhook_event`, `get_price_map`). The local variable in the webhook path is even named
`stripe_sub`, so the concrete provider has already leaked into the consumer. The acceptance
criterion "billing logic uses the provider port, not concrete classes" therefore reads as satisfied
and is not.

**This also links to step 2.5.** The reconciliation service is the one whose entrypoint never runs
because of a handler-name mismatch — so a consumer that depends on an undeclared port method has
never executed in a deployed environment. Fixing 2.5 without first reconciling the port would put
that call on a live schedule for the first time.

**The check.** Change both annotations from `Any` to `PaymentProviderInterface` and run strict type
checking. Every call to a method the port does not declare fails there and then. That is the real
inventory of the gap, and it takes minutes.

**Status 2026-07-25 — CHECK RUN. The mismatch list is longer than `retrieve_subscription` — the
fallback is now in effect.** Diagnostic edit made and reverted in the same session (billing_service.py,
webhook_service.py, reconciliation_service.py annotated `PaymentProviderInterface`, `uv run mypy
careervp --strict` run, then `git checkout --` on all three — confirmed zero net diff). Full result:

1. `logic/webhook_service.py:119` — `retrieve_subscription(subscription_id)`, undeclared. (Line
   drifted from the `:115` cited above — re-verify line numbers live, not from this file, same
   discipline Wave 1 used throughout.)
2. `logic/reconciliation_service.py:54` — same undeclared call. (Drifted from `:53`.)
3. **NEW — not previously known.** `logic/billing_service.py:78` —
   `create_checkout_session(customer_id=customer_id, ...)` where `customer_id` is typed
   `str | None` (the return of `_get_or_create_customer_id`, a `tuple[str, None] |
   tuple[None, dict]` union) but the Protocol requires `customer_id: str`. Not an undeclared
   method — the method exists — but strict typing cannot prove `customer_id` is non-`None` at the
   call site through the `if error is not None: return error` tuple-unpack guard. `Any` swallowed
   this silently; it is a real narrowing gap, not a false positive — the fix is either an
   `assert customer_id is not None` after the guard or restructuring the guard's return so mypy can
   narrow it, GREEN's call which one.
4. Two `redundant-cast` findings at `webhook_service.py:63,66` — `cast(WebhookEvent, ...)` around
   both `construct_webhook_event(...)` calls in `_verify_webhook` is now provably redundant once
   the provider is typed `PaymentProviderInterface` (the cast existed only to satisfy mypy against
   `Any`). Not a port mismatch — a cleanup GREEN should make while it has the file open.

So: **2 previously-known undeclared-method call sites, 1 new nullable-argument gap, 2 cosmetic
cleanups.** Per the fallback below, this is enough to make 2.0 cover reconciling the port with all
three real gaps — not just the two already known.

**The fallback.** If the mismatch list is longer than `retrieve_subscription`, 2.0 grows to cover
reconciling the port with its actual consumers, and 2.1 waits. Better to learn that in the first
hour of 2.0 than during the idempotency work.

**Settled 2026-07-25 (step 2.0-RED) — tier-2 check as designed; the mismatch IS longer, so 2.0 is
bigger than "add a mock".** All THREE consumers (`billing_service`, `webhook_service`,
`reconciliation_service`) were annotated from `Any` to `PaymentProviderInterface`, `mypy --strict`
was run, then reverted (RED session — the edit belongs to GREEN). The pristine tree is mypy-clean, so
every finding below is the port enforcement, nothing pre-existing. **5 errors in 3 files:**

1. `webhook_service.py:115` — `retrieve_subscription(...)`: `"PaymentProviderInterface" has no
   attribute "retrieve_subscription"`. *(known)*
2. `reconciliation_service.py:53` — `retrieve_subscription(...)`: same. *(known)*
3. `billing_service.py:76` — **NEW.** `create_checkout_session(customer_id=...)` receives
   `str | None`, but the port requires `str`. `_get_or_create_customer_id` returns
   `tuple[str, None] | tuple[None, dict]`, and mypy cannot narrow `customer_id` to `str` after the
   `if error is not None: return error` guard. A latent None-on-the-checkout-path type gap the `Any`
   annotation hid — not an undeclared method, a real defect the port surfaces.
4. `webhook_service.py:63` and `:66` — two `Redundant cast to "WebhookEvent"`: once the port is
   typed, `construct_webhook_event` returns `WebhookEvent` and the two `cast()`s become redundant.
   Artifacts of the annotation, not violations (they prove the port return type now flows); GREEN
   deletes them when it makes the annotation permanent.

**So GREEN's 2.0 must:** declare `retrieve_subscription` on the port (or refactor both consumers off
it), fix the `customer_id` narrowing, and drop the two casts. The belief stays FALSE and the effort
is a little larger than the bet's own "two call sites" estimate. **Note the 2.5 link (unchanged):**
`reconciliation_service` is the consumer whose scheduled entrypoint has never run (handler-name
mismatch), so this undeclared-port call has never executed deployed — whoever does 2.5 must reconcile
the port BEFORE fixing the entrypoint, or that call goes live for the first time.

**CLOSED 2026-07-25 (step 2.0-GREEN) — port reconciled, all five findings fixed.**
`retrieve_subscription(subscription_id: str) -> dict[str, Any]` is now declared on
`PaymentProviderInterface` (the port describes what billing needs, per the prompt's "add it to the
Protocol" guidance) and implemented on `MockProvider` + `PlaceholderPaymentProvider`. All THREE
consumers are annotated `PaymentProviderInterface` instead of `Any`
(`billing_service`, `webhook_service`, `reconciliation_service`). The `billing_service:76`
`customer_id: str | None` gap is fixed by changing `_get_or_create_customer_id` to return
`str | dict[str, Any]` (str on success, error-dict otherwise), so strict typing narrows
`customer_id` to `str` at the `create_checkout_session` call with no dead branch. The two redundant
`cast(WebhookEvent, …)` in `webhook_service` are removed now that `construct_webhook_event` returns
`WebhookEvent` through the typed port. `mypy careervp --strict` clean (131 files), full unit 1360
passed. **2.5 link now DISCHARGED at the port level:** the undeclared-port call is gone, so fixing
the reconciliation entrypoint in 2.5 no longer puts an unenforced call on a live schedule — 2.5 still
owns the handler-name fix itself. Status: **settled — belief was FALSE, port now enforced.**
