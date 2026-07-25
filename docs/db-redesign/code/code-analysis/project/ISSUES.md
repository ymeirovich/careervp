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

**The fallback.** If the mismatch list is longer than `retrieve_subscription`, 2.0 grows to cover
reconciling the port with its actual consumers, and 2.1 waits. Better to learn that in the first
hour of 2.0 than during the idempotency work.
