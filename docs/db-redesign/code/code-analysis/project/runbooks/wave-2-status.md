# Wave 2 — Status Ledger

**Read this file FIRST before starting any Wave-2 prompt.** `wave-2-prompts.md` describes what
*should* happen; this file describes what *actually* happened, and is what every prompt checks
before starting its own work (see `RUNBOOK-RULES.md`, rules 2–3). Update your own row when you
finish a step or stop on a problem — do not leave this file stale for the next session to trip
over.

Rows are listed in dependency order. Before starting a step, read the row above it (or the rows
it depends on per `wave-2-prompts.md` §2) — if any of them show an open problem, resolve that
first.

**Deploy target for this entire wave: `CareerVpCrudDevx`.** Not `CareerVpCrudDev`. See the bet
`B-2-4` in `ISSUES.md` — one deploy path still targets the old stack and must be settled before
2.0 deploys anything.

| Step | Clause(s) | Status (plain English) | Open problem for the next step | Commit | Date |
|---|---|---|---|---|---|
| 2.0 | P-25 | not started | — | — | — |
| 2.0b | P-25b | not started | — | — | — |
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
| B-2-1 | The mock provider's signature scheme is a faithful stand-in for Stripe's | 2.0, before 2.1 starts | open |
| B-2-2 | The provider's event id is a stable, safe idempotency key | 2.0/2.1 | open |
| B-2-3 | Wave 2's added resources stay under the CloudFormation ceiling | every additive step | open |
| B-2-4 | "Deploy" means devx | before 2.0 deploys | **open — currently false on the merge path** |
| B-2-5 | Billing already depends on the port, so 2.0 is small | first hour of 2.0 | **open — already FALSE: two consumers call a method the port never declares** |

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
- Carried in from Wave 1, still open: the browser login client still holds the admin scope and the
  insecure grant (`ISSUES.md` I-06). It does **not** gate Wave 2. It gates staging promotion, and
  it now has a written stopping condition.
- A red backend unit test predates this wave: the AI-assist path reports zero tokens
  (`ISSUES.md` I-05). It belongs to the token-metering clause, not to any Wave-2 step. Do not
  silence it inside a Wave-2 prompt.
- **(2026-07-24) devx is missing SSM parameters that dev has.** Verified live against account
  788159322332: `/careervp/devx/` holds only `anthropic-api-key` and the two payment price ids.
  Missing versus dev: `tavily-api-key`, `jwt-private-key`, `jwt-public-key`,
  `payment-provider-webhook-secret`, and `payment-provider-webhook-secret-previous`.
  - The **tavily and JWT** parameters are now seeded automatically (create-if-missing) by the
    enriched `create-change-set-other` job in `.github/workflows/deploy.yml` on the next devx
    deploy — no action needed.
  - The **webhook secret** parameters are seeded by NEITHER deploy path (dev's are not in the
    workflow either — they were placed some other way). Wave-2 step 2.1 fetches this secret at
    runtime for webhook verification. **Before 2.1 deploys, a human must create
    `/careervp/devx/payment-provider-webhook-secret` (and `-previous`)** — the value is the mock
    provider's signing secret settled in 2.0, so this is a 2.0→2.1 handoff item, not a blocker
    for 2.0 (which is backend-only and deploys nothing). Recorded here so it is not discovered as
    a runtime 500 the way the anthropic key was in step 1.4.
