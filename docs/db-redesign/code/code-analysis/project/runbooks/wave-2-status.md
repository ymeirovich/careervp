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
