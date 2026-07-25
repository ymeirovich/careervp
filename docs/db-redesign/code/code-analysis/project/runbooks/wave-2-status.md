# Wave 2 — Status Ledger

**Read this file FIRST before starting any Wave-2 prompt.** `wave-2-prompts.md` describes what
*should* happen; this file describes what *actually* happened, and is what every prompt checks
before starting its own work (see `RUNBOOK-RULES.md`, rules 2–3). Update your own row when you
finish a step or stop on a problem — do not leave this file stale for the next session to trip
over.

Rows are listed in dependency order. Before starting a step, read the row above it (or the rows
it depends on per `wave-2-prompts.md` §2) — if any of them show an open problem, resolve that
first.

**Deploy target: `CareerVpCrudDevx` — and as of 2026-07-25, project-wide, not just this wave.**
Human decision: devx is the primary development environment; deploys should go only to devx.
`CareerVpCrudDev` is being retired. devx is the P-26 v2.6.0 parallel-stack architecture
(`ENVIRONMENT=devx`, `p26_rehome_features=true`, features rehomed into `CrudFeaturesNestedStack`),
not a second copy of the old shape. See `ISSUES.md` bet `B-2-4` — the *decision* is made and
verified live in two places (devx GitHub environment + required reviewer confirmed; manual
dispatch defaults to devx); **the push-to-`main` CI path still targets the old stack** and needs
its own dedicated fix, tracked there, not fixed as a side effect of a Wave-2 step.

| Step | Clause(s) | Status (plain English) | Open problem for the next step | Commit | Date |
|---|---|---|---|---|---|
| 2.0-RED | P-25 | **RED landed. Four RED tests in `src/backend/tests/unit/test_p25_payment_provider_port.py`, all four observed failing on their own assertions (not ImportError/collection error); ZERO files under `src/backend/careervp/` modified (`git diff --stat` clean). Spec-before-test (rule 14) verified live. Bets B-2-5/B-2-1/B-2-2 settled — see ISSUES.md.** Full unit suite: 4 failed (these) / 1356 passed, no regressions; ruff+mypy clean on the new file; `mypy careervp --strict` still 130/130 clean. | **2.0-GREEN runs in a FRESH session (rule 7); may NOT edit the RED file.** B-2-5 grew: GREEN must also fix a `customer_id: str \| None` gap at `billing_service.py:76` and drop 2 redundant casts in `webhook_service.py` (`:63`,`:66`), on top of reconciling `retrieve_subscription`. `test_p25_mock_event_id_is_stable_across_retries` was intentionally omitted → assigned to **2.1** (B-2-2). **2.0b** must cross-check the B-2-1 signature format (`t=,v1=`, HMAC over `{t}.{payload}`, tol 300s) against real Stripe before 2.1. | pending — see commit message in session output | 2026-07-25 |
| 2.0-GREEN | P-25 | **GREEN landed. All four RED tests in `test_p25_payment_provider_port.py` now PASS (`4 passed`), ZERO test files modified (`git diff --stat` on `src/backend/tests/` is empty). Built `careervp/payment_providers/mock_provider.py:MockProvider` with real Stripe-shape HMAC verification (compound `t=,v1=` header, timestamp read from the signature, replay rejected outside 300 s with code `WEBHOOK_TIMESTAMP_OUT_OF_TOLERANCE`, tampered body fails the digest). Added `retrieve_subscription(subscription_id: str) -> dict[str, Any]` to the `PaymentProviderInterface` Protocol (the one method B-2-5's consumers called but the port never declared) and to `PlaceholderPaymentProvider`. Annotated all THREE consumers (`billing_service`, `webhook_service`, `reconciliation_service`) `PaymentProviderInterface` not `Any`; fixed the `billing_service` `customer_id: str\|None` gap by making `_get_or_create_customer_id` return `str \| dict`; dropped the two redundant `cast`s in `webhook_service`. FE checkout/portal URL shapes preserved. VERIFY: full unit 1360 passed; `make coverage-tests` 1523 passed, gate exit 0 and every tier at/above baseline (overall 72.49/54.01 ≥ 70/51; core 73.00/55.14 ≥ 71/53; supporting 72.55/51.47 ≥ 70/48); ruff format+check clean; `mypy careervp --strict` clean (131 files); scope-diff reports P-25 (spec+test present). One transparent extension flagged (see next-step column) — otherwise matches prompt + clause P-25.** | **Transparency (rule 5/6): prompt named `billing_service.py` + `webhook_service.py` for the `Any`→`PaymentProviderInterface` annotation; GREEN also annotated `reconciliation_service.py` — the third actual consumer of `retrieve_subscription` (B-2-5 lists all three) and squarely inside instruction #2's header "reconcile the port with its actual consumers." Same one-line change, makes the seam correct not weaker, no test touched. Recorded for human review, step still marked done.** For 2.0b: cross-check the B-2-1 format (`t=,v1=`, HMAC over `{t}.{payload}`, tol 300 s) against real Stripe — the mock's constants live in `mock_provider.py` (`WEBHOOK_TIMESTAMP_TOLERANCE_SECONDS`). For 2.1: the B-2-2 stable-event-id test still lands there. `scope-diff` impl_state still reads `test_written` because the P-25 clause line sets no `impl_state:` field (scope-diff reads that field, not source) — flipping it is a human clause edit (rule 8), not a GREEN action. | pending — see commit message in session output | 2026-07-25 |
| 2.0b-RED | P-25b | **RED landed. Tightened only P-25b's two rule-14 RED-test briefs, then added exactly two tests in `test_p25b_stripe_provider.py`; both collect and fail on their own guarded AC-P25b-1 assertions because `StripeProvider` is absent (not ImportError/collection/fixture failure). B-2-1 cross-check: signed payload and caller-side 300 s tolerance MATCH Stripe, but multiple-`v1` secret-rotation handling DIVERGES, so B-2-1 is FALSE; `ISSUES.md` records the official-doc/SDK evidence and live probe. Existing P-25 mock tests remain `4 passed`; new file ruff+mypy strict clean; scope-diff recognizes P-25b as `test_written`; ZERO files under `src/backend/careervp/` modified.** | **CORRECTED 2026-07-25 (orchestrator, evidence-based — the earlier wording of this cell over-scoped the mock fix as a blocker, and a first 2.0b-GREEN attempt correctly stopped on it; the wording was wrong, not the code).** The two P-25b tests exercise **`StripeProvider` ONLY** (`provider = StripeProvider()`; `_assert_signature_negatives` always called with `provider.construct_webhook_event`) — verified in `test_p25b_stripe_provider.py:126,159`. So **2.0b-GREEN is UNBLOCKED now**: build `StripeProvider` self-contained with multi-`v1` acceptance (its own RED test asserts the match in the second `v1` slot), touching neither `mock_provider.py` nor any test file. The proven mock first-`v1`-only divergence is a real but **INERT** gap (nothing feeds the mock a multi-`v1` header, so no existing test is wrong); it is tracked as new follow-up **2.0b-mock** (B-2-1's pre-committed "make the mock conform" fallback), file-isolated and parallel-safe, recommended after 2.0b-GREEN. B-2-1 stays FALSE until 2.0b-mock lands. B-2-2's stable event-id/idempotency negative remains assigned to 2.1. | pending — see commit message in session output | 2026-07-25 |
| 2.0b-GREEN | P-25b | **GREEN landed. `StripeProvider` now implements all six `PaymentProviderInterface` methods, including `retrieve_subscription`; real API methods use the existing `httpx` dependency to call Stripe REST endpoints and map configuration, timeout, network, authentication, rate-limit, API, and invalid-response failures to `PaymentProviderError`. Because the official `stripe` SDK is not a project dependency, webhook verification uses Stripe's documented v1 HMAC scheme directly with no dependency addition: exact raw bytes signed as `{timestamp}.{payload}`, ALL `v1` digests parsed, any constant-time match accepted, 300 s stale rejection, and distinct tamper/wrong-secret vs replay codes. Both P-25b RED tests pass and prove the matching digest may be the SECOND `v1`; all four P-25 tests remain green; ZERO test files and ZERO mock files modified. Full unit+integration: 1525 passed / 30 skipped / 4 xfailed / 1 xpassed. Coverage gate exit 0: overall 72.34/53.90, core 73.00/55.14, supporting 72.15/51.16, all above enforced baselines. Ruff clean; `mypy careervp --strict` clean (132 files); scope-diff reports P-25b `test_written`. The prompt and locked P-25b clause match. FREEZE LINE: no AC-P25b-1 signature-verification case is untested — valid multi-v1 rotation, tampered body, wrong secret, and stale signed timestamp all execute locally with no network call.** | **NEXT: run 2.0b-mock as its own fresh RED/GREEN follow-up before 2.1: MockProvider still accepts only its first `v1`, so B-2-1 stays FALSE until that lands. StripeProvider itself handles multi-`v1` correctly. B-2-2's stable event-id/idempotency negative remains assigned to 2.1.** | pending — see commit message in session output | 2026-07-25 |
| 2.0b-mock-RED | P-25 (mock hardening) | **RED landed. Tightened exactly one P-25 RED-test brief, then added exactly one mock-file test, `test_p25_mock_webhook_accepts_matching_second_v1`, in `src/backend/tests/unit/test_p25_payment_provider_port.py`. The test collects and fails on its own AC-P25-2 assertion because the matching digest is in the SECOND `v1` slot while `MockProvider` still verifies only the first `v1`, raising `PaymentProviderError.code == "WEBHOOK_SIGNATURE_VERIFICATION_FAILED"`. The four earlier P-25 mock tests plus both P-25b StripeProvider tests remain green; ZERO files under `src/backend/careervp/` modified. B-2-1 stays FALSE until GREEN lands.** | **GREEN must resolve first:** teach `MockProvider` to accept any matching `v1` digest, mirroring StripeProvider's multi-`v1` behavior, without editing tests or StripeProvider. | pending — see commit message in session output | 2026-07-25 |
| 2.0b-mock-GREEN | P-25 (mock hardening) | **GREEN landed. `MockProvider` now collects all `v1` digests from the compound webhook signature and accepts when any digest constant-time-matches the HMAC over `{timestamp}.{raw_payload}`, mirroring StripeProvider's rotation behavior instead of verifying only the first `v1`. The RED `second_v1` test now passes (`1 passed / 4 deselected`), all five P-25 mock tests pass, and both P-25b StripeProvider tests still pass. ZERO test files modified (`git diff --stat -- src/backend/tests tests` empty) and `stripe_provider.py` was not touched (`git diff --stat -- src/backend/careervp/payment_providers/stripe_provider.py` empty). Full backend unit suite: 1363 passed / 15 skipped / 4 xfailed / 1 xpassed. Full backend integration suite: 163 passed / 15 skipped. Coverage gate exit 0: 1526 passed / 30 skipped / 4 xfailed / 1 xpassed; overall 72.34/53.90, core 73.00/55.14, supporting 72.15/51.16. Ruff format/check clean; `mypy careervp --strict` clean (132 files); scope-diff reports P-25 and P-25b with spec+test present. Prompt instructions and locked clause P-25 match; no drift. B-2-1 is now TRUE.** | none | pending — commit message: `fix: accept rotated mock webhook signatures` | 2026-07-25 |
| 2.1 | P-14, P-15 | not started | — | — | — |
| 2.2 | P-16, P-17, P-18 | not started | — | — | — |
| 2.3 | P-19 | not started | — | — | — |
| 2.4 | P-20 | not started | — | — | — |
| 2.5 | P-02 | not started — **blocked on 2.0**, despite a tiny diff (see `B-2-5`) | — | — | — |
| 2.7 | P-31 | not started | — | — | — |
| GATE | — | not started | — | — | — |

---

## Bets this wave rests on — re-read every one at the GATE

Full text in `ISSUES.md` under "Wave-2 bets". Rule 9 requires the gate to re-read them, not just
the rows above.

| Bet | Belief | Settled by | Status |
|---|---|---|---|
| B-2-1 | The mock provider's signature scheme is a faithful stand-in for Stripe's | 2.0, then 2.0b-RED cross-check, then 2.0b-mock | **TRUE (settled 2026-07-25, 2.0b-mock-GREEN): header/`{t}.{payload}`/300 s match Stripe, and MockProvider now accepts ANY matching `v1` digest in constant time, mirroring StripeProvider and Stripe's secret-rotation behavior.** |
| B-2-2 | The provider's event id is a stable, safe idempotency key | 2.0/2.1 | **decision fixed 2026-07-25 (2.0-RED): stable-across-retries else digest fallback; stable-id TEST assigned to 2.1** |
| B-2-3 | Wave 2's added resources stay under the CloudFormation ceiling | every additive step | open |
| B-2-4 | "Deploy" means devx | before 2.0 deploys | **decision made 2026-07-25 (devx primary); GitHub environment + required reviewer live-verified via `gh api`; merge-to-main CI still needs the matching fix (`deploy.yml:37,194` still hardcode the old stack)** |
| B-2-5 | Billing already depends on the port, so 2.0 is small | first hour of 2.0 | **settled 2026-07-25 (2.0-RED then closed by 2.0-GREEN): FALSE — 3 findings (2× `retrieve_subscription` + `customer_id: str\|None`) + 2 cast cleanups; 2.0 larger than the "two call sites" estimate; all 3 fixed in 2.0-GREEN** |

---

## Standing notes carried into every step (do not lose these)

- The two IMMUTABLE laws (never move the live API, never move the Cognito user pool) apply to
  every row that touches `infra/`.
- `api_construct.py` is edited by several of these steps — never run two steps that touch it at
  the same time. See `wave-2-prompts.md` §2 for the serialization order.
- **Deploy target is `CareerVpCrudDevx`.** Anything pointed at `api.dev.careervp.com` is talking
  to the OLD stack. Use the raw invoke URL
  `https://ymzhvcxod0.execute-api.us-east-1.amazonaws.com/prod/` until the human-only base-path
  flip happens.
- **(2026-07-25) Amplify's `db-redesign` branch already targets devx — but only as live AWS
  state, not as code.** Verified via `aws amplify get-branch --app-id d3j2wnm8g5clnw
  --branch-name db-redesign`: `NEXT_PUBLIC_API_URL` is the devx raw invoke URL,
  `NEXT_PUBLIC_COGNITO_USER_POOL_ID` is `us-east-1_bAZ6jb6HP` (devx pool), domain is
  `careervp-devx.auth...`. This was set by hand in Wave-1 step 1.6; `infra/careervp/
  frontend_stack.py` does not manage Amplify branches or their env vars at all (zero matches
  for `amplify`/`Branch(` in that file) — so nothing in the repo documents this, and nothing
  prevents someone clearing the override in the Amplify console ("use app defaults") and
  silently reverting the branch to the dev pool / `api.dev.careervp.com` (the APP-LEVEL
  defaults, confirmed still dev via `aws amplify get-app`). **This is out-of-band state exactly
  like the SSM parity note above — verify from live before trusting either.** Not a Wave-2
  blocker; recorded so the drift risk is known rather than rediscovered.
  Separately, `.github/workflows/deploy-frontend.yml` (validate-only, does not deploy — see
  `ISSUES.md` I-03) still hardcodes dev-pool fallback values, but only triggers on push to
  `main`, so it never runs against `db-redesign` and this has no live effect.
  **The GitHub deployment environment `devx` (Settings → Environments) governs NEITHER of the
  above.** It gates exactly one thing: the `execute-change-set-other` job in `deploy.yml` — the
  backend CloudFormation approval step. Amplify has no concept of a GitHub environment and never
  reads it.
- Carried in from Wave 1, still open: the browser login client still holds the admin scope and the
  insecure grant (`ISSUES.md` I-06). It does **not** gate Wave 2. It gates staging promotion, and
  it now has a written stopping condition.
- A red backend unit test predates this wave: the AI-assist path reports zero tokens
  (`ISSUES.md` I-05). It belongs to the token-metering clause, not to any Wave-2 step. Do not
  silence it inside a Wave-2 prompt.
- **(2026-07-24) devx SSM parameters — full parity with dev, verified live.** Human confirmation:
  **parameter keys and secrets are the same for dev and devx.** devx originally held only
  `anthropic-api-key` and the two payment price ids; the five missing values
  (`tavily-api-key`, `jwt-private-key`, `jwt-public-key`, `payment-provider-webhook-secret`,
  `payment-provider-webhook-secret-previous`) were copied from `/careervp/dev/*` to
  `/careervp/devx/*` this session, preserving type (read with `--with-decryption` into a shell var,
  never logged — the same pattern step 1.4 used for the anthropic key). `get-parameters-by-path`
  now shows dev↔devx parity (`dev minus devx` is empty). **No Wave-2 step has a parameter
  prerequisite** — in particular the webhook secret is NOT a 2.0→2.1 handoff; it already holds
  dev's value. The enriched `create-change-set-other` seeding (create-if-missing) will now skip all
  of these because they exist, so it cannot generate a divergent ephemeral JWT for devx.
