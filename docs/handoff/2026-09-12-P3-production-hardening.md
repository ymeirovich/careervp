# P3 — Production & scale hardening

**Model: Opus 5, xhigh effort. Runs in parallel with P2 — they touch different
code. Escalate the final triage to Fable 5 (see "Handback" at the end).**
**Prerequisite: read `docs/handoff/2026-09-12-P0-COMMON.md` first — it is binding.**

**Validation obligation (P0 §1):** every finding cited below came from
unvalidated automated analysis. Open each file before designing around it. If P1
refuted a finding, it is out of scope — and if P1 refuted the *framing*, say so
rather than proceeding.

---

You are answering one question for a pre-launch serverless app (AWS Lambda +
DynamoDB + API Gateway + Anthropic LLM calls), about to attempt its first
production deployment:

**What breaks in production, at what scale, and in what order?**

There is no production environment yet and no real customer data. The app targets
a 91% gross margin (per `CLAUDE.md`), which makes duplicate LLM spend a
correctness bug, not a cost nit.

## Read first

- `docs/handoff/2026-09-12-RECON-FINDINGS.md` — ~100 cited findings
- `docs/handoff/2026-09-12-P1-VERDICTS.md` if present — **anything REFUTED there
  is out of scope**
- `docs/HARNESS.md` — how this project proves things

**Scope boundary:** P2 owns the table-authority and key-scheme work (root causes
R1, R2, R4). Do not design those. You own R3, R5, R6 and everything security,
cost, and load related.

## Part 1 — the load model (do this first; it orders everything else)

Build a concrete failure timeline. For **10, 100, 1,000, and 10,000 users**,
state what breaks, with the arithmetic shown. Anchor it in the real numbers:

- API Gateway throttle is 20 rps / 40 burst (`infra/careervp/api_construct.py:456-479`)
- AI workers are capped at `reserved_concurrent_executions=5` (`:1774,2022,2085,2159,2882`)
- DynamoDB is on-demand everywhere
- The 8 `Limit`+`FilterExpression` sites (inventory S13) are latent until
  rows-per-user grows — compute *when* they start returning false "not found"
- Unpaginated queries (S14) break at the 1MB page boundary — compute how many
  artifacts that is
- `COVER_LETTER_LEGACY_READ_ENABLED` defaults `true` on three Lambdas, escalating
  every canonical miss to a full table **scan** (`dynamo_dal_handler.py:618,780`;
  `api_construct.py:2079,2923,3000`)

I want a table: user count → what fails → why → estimated cost or latency impact.
Where you cannot compute a number, say UNKNOWN and name the measurement that
would settle it. Do not invent numbers.

## Part 2 — the three hardening tracks

### Track A — error handling (root cause R3, ~40 findings)

`except Exception: pass` is the default idiom in this codebase. Infra failure
becomes "not found" becomes HTTP 404 or, worse, HTTP 200 with fabricated content.
The worst instances:

- `gap_analysis.py:299-305` — LLM parse failure → 10 **fabricated template
  questions** returned as `200 GAP_QUESTIONS_GENERATED` and persisted
- `vpr_generator.py:469-517` — 10 sites where malformed LLM output degrades to
  canned boilerplate with `overall_fit_score=50`, billed, no error signal
- `vpr_status_handler.py:435-448` — cancel returns `{'status': 'cancelled'}` with
  all three writes swallowed; generation and billing continue
- `cv_tailoring_handler.py:1019-1047` — three swallows → `return None` → 404 on a
  DynamoDB throttle

Design the **policy**, then apply it. Not "add logging" — a decision procedure
for when a failure may be swallowed (rare, and it must be a semantic no-op), when
it must become a 5xx, and when it must fail the SQS message so the DLQ catches
it. Then specify the mechanism that keeps the policy true over time (lint rule,
a shared `Result` discipline, a test that greps — your call, cheapest that works).

Explicitly address: **a user-facing success response must never contain content
the system fabricated because a dependency failed.** That invariant currently has
at least three live violations.

### Track B — async, idempotency, and LLM bounds (R5 + cost)

- **S15**: `dal/idempotency_repository.py:36-49` implements a correct atomic
  claim, but only `company_research_worker_handler.py:92` calls it. The
  cover-letter, interview-prep, and VPR workers have none. SQS redelivery —
  triggered normally by visibility-timeout expiry on a slow LLM call — re-runs
  full paid generation. Design the adoption, including what the idempotency key
  is per worker and what happens on claim-release.
- **S5/S18**: gap-analysis, interview-prep, and CV-tailoring run synchronous LLM
  work behind API Gateway's hard 29s cap. `cv_tailoring_handler` returns
  `HTTP 202 ACCEPTED` with `'estimated_time_seconds': 0` while running fully
  synchronously. VPR already went async via SQS — specify the conversion for the
  others, reusing that pattern rather than inventing a second one.
- **S16**: `logic/llm_client.py:122-128` accepts a `timeout` parameter and
  discards it (`_ = timeout`); the client is built with no timeout at all
  (`:92`). Meanwhile `logic/utils/llm_client.py:146-150` sets `timeout=180.0,
  max_retries=3` and then stacks another 3-retry decorator at `:186` → 9 attempts
  × 180s. **Two divergent LLM clients coexist.** Decide whether they merge or
  divide cleanly, and bound every call.
- **S17**: `interview_prep.py` requests up to 15 questions with 150-300 word
  answers against a hardcoded `max_tokens=4096` — the first attempt truncates
  deterministically, wasting a full round-trip every time. (Note: `MAX_QUESTIONS
  = 15` also contradicts the documented 10-question cap in `CLAUDE.md` — flag
  which is authoritative, don't silently pick.)

### Track C — security

Ordered by exploitability, not by category:

1. **S0a / S0b** — the two live cross-tenant VPR reads. If P1 confirmed them,
   these are fix-before-anything-else. Verify the fix closes both the export path
   and the S3-fallback path, and add a test that fails if a future branch drops
   `user_id` again.
2. **S1 / S2** — `cv_tailoring_handler.py:418-422` (unscoped `get_vpr` on a
   body-supplied `vpr_id`) and `:301-318` (`_is_sfn_invoke` takes `user_id` from
   the event body, evaluated before auth, with a guard that is also true for API
   Gateway HTTP API **v2** payloads).
3. **S3 / S4 / S5** — `logic/auth_service.py`: the `test-` prefix backdoor at
   `:184-188`, ephemeral RSA keys reachable outside local dev at `:153-163`, and
   JWT verification with no `issuer`, no `audience`, and no `jti` (so revocation
   is impossible) at `:369-374`.
4. **S9** — full CV and full prompt context logged at INFO
   (`interview_prep_handler.py:834,1003-1008`); full request and response bodies
   at DEBUG (`cv_tailoring_handler.py:83-90,1247-1252`). Same class as the
   already-closed F-DEVX-2.
5. **S26** — prompt injection. Scraped third-party web text and unbounded
   user free-text reach prompts with no delimiting; `gap_analysis.py:281-286` and
   `interview_prep.py:93` **concatenate system and user prompts into a single
   user-role message**, so there is no privileged channel at all. Six-stage VPR
   chains stage N's output into stage N+1.
6. **S12** — Cognito ID token in a JS-readable, non-`Secure` cookie
   (`AuthContext.tsx:30-34`).

Plus one infra item that will bite on first prod deploy: the WAF 8KB body-size
fix is gated to devx only (`waf_construct.py:20-42,61`,
`_LARGE_BODY_ENVIRONMENTS = frozenset({"devx"})`). **dev, staging, and prod still
carry the bug that blocked every real CV upload.**

### Track D — the trust-boundary sweep

The recon that produced the inventory was backend-heavy. Security has **not**
been evaluated at every touchpoint. Complete the sweep — for each boundary,
state whether validation/authorization is present, absent, or unverifiable, with
citations, and what the failure looks like if absent:

| # | Boundary | Specific things to check |
|---|---|---|
| 1 | Browser / UI | XSS sinks, `dangerouslySetInnerHTML`, TipTap paste sanitization (`components/RichTextEditor/`), CSP headers, token storage (S12) |
| 2 | Frontend input validation | Any field validated client-side only is unvalidated in reality — enumerate them |
| 3 | API Gateway | Request validators/models, WAF (devx-only body fix), CORS (`cors_utils.py:6` module-global origin set by only 20 of 35 handlers), throttling, GatewayResponse ACAO wildcards |
| 4 | Lambda in/out | Input bounds and output scrubbing per handler; env/SSM secret handling; what reaches logs |
| 5 | DynamoDB | Expression injection, key construction from user input, encryption at rest (AWS-owned keys today, no CMK), PII in keys (`knowledge` table keys on `userEmail`) |
| 6 | S3 | Presigned URL scope and TTL (S0a/S0b both hand out presigned VPR URLs), bucket policies, and the two **unversioned** buckets (`api_db_construct.py:256,746`) |
| 7 | SQS / Step Functions | Message integrity — several workers take `user_id` verbatim from the body; is the queue writable from outside the pipeline? |
| 8 | CloudWatch | Who can read logs containing full CVs and prompt context (S9)? Is 1-day retention a control or an accident? |
| 9 | Supply chain / CI | Dependency audit; whether CI can deploy without a human (`deploy.yml:37` hardcodes `STACK_NAME: CareerVpCrudDev` on the push-to-main path, which would void P-28's human-only execute gate) |

Note the frontend boundaries (1, 2) are the least-examined surface in the entire
codebase. Give them real attention rather than a checklist pass.

### Track E — stability & performance beyond the defect list

Distinct from the load model in Part 1 — this is about steady-state behavior:

- **Cold start and client lifecycle.** `dal/dynamo_dal_handler.py:83-87` builds a
  fresh `boto3.session.Session()` on *every* call; several handlers
  `import boto3` inside function bodies. One cover-letter POST is claimed to
  construct over a dozen clients. Quantify, then fix.
- **Module-level state across warm invocations.** `cors_utils.py` (per-request
  origin in a module global) and the `@lru_cache` ephemeral RSA keypair
  (`auth_service.py:84-93`) are the dangerous ones; ~12 lazy-init singletons are
  probably benign. Separate them.
- **Retry storms.** Two LLM clients with stacked retry decorators (S16) can reach
  9 attempts × 180s. Bound end-to-end, not per-layer, and make the bound
  observable.
- **Alarm coverage for the failures you're fixing.** If a swallowed error becomes
  a 5xx, something must page. What CloudWatch alarms are needed, and what is the
  on-call story for a solo operator?

## Part 3 — the pre-production gate

Produce a checklist of what must be true before the first `prod` deploy. Each
item needs a **command that proves it**, not a claim. Build on the existing
harness (`make preflight`, `make journey`, `make review`) rather than inventing a
parallel mechanism. Call out anything the harness cannot currently prove — that
gap is itself a deliverable.

## Output

Per `P0-COMMON.md` §4, ending with the traceability table and the
ADDITIONS / REDUCTIONS / UNKNOWNS lists.

Plus:

1. The load-failure table (Part 1).
2. Per track (A–E): the policy/design, the ordered change list, and the test that
   keeps it fixed. Same commit discipline as P2 — each change independently
   committable and revertible, each naming its RED test and the S-numbers it
   closes.
3. The Track D trust-boundary table: boundary → control present? → evidence →
   severity if absent.
4. The pre-production gate checklist.
5. **A single ranked list: "fix in this order, and here is what each one buys."**
   This is the deliverable the human will actually work from. Rank across all
   five tracks — do not present five parallel lists.

## Constraints

- Design and plan. **Do not edit source files in this session** — except that if
  you confirm a SEV-0 cross-tenant leak is live and unfixed, say so at the very
  top of your report in plain language. Do not bury it.
- Cite file:line for every claim about current behavior, and open the file first.
  Do not inherit citations from the inventory unchecked.
- Label OBSERVATION / INFERENCE / OPINION.
- Cost the options on judgment calls; the human decides.

## Handback

When your ranked list is done, it goes to **Fable 5 (high effort)** for a final
triage pass with one question: *"Of these, which actually block a first
production launch for a pre-launch app with zero users, and which are
post-launch hardening?"* Write your ranked list so that question can be answered
from it — i.e. make the blast radius and the trigger condition explicit for every
item.
