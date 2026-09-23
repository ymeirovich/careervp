# CareerVP Rebuild — Context Pack Addendum

**Read this AFTER `context-pack.md`.** That file is the current-state truth (the
defects, the DAL, the infra, the constraints). This addendum adds what a **parallel
rebuild** council needs: the full capability surface to reproduce, a proposed
MVP→parity carve, and the same-account coexistence contention points.

The current-state constraints in `context-pack.md §7` still bind — especially:
**keep DynamoDB**, **solo dev**, **>70% margin**, **security-conscious / no GDPR
gold-plating**, **backend + contract only**, **< 10k concurrent**.

**Rebuild-specific framing (decided by the owner):**
- Deliverable is **two-part**: (A) a **recommendation** on parallel-rebuild vs.
  in-place strangler-fig, then (B) the **how-to** for the rebuild path.
- Parity model: **corrected MVP first (walking skeleton) → waves to full parity.**
- Topology: **side-by-side in the SAME AWS account**, gradual routing, shared or
  copied data.

---

## 0. What changed since the last council (READ FIRST — RE-COUNCIL)

See `context-pack.md §0` for the full delta. For the **rebuild** decision specifically:
- The **clean target data model is now concretely specified** (`db-upgrade-priorities.md` `core` design):
  `PK=USER#{sub}`, CV at USER level (referenced not copied), per-app artifacts `APP#{appId}#ARTIFACT#{TYPE}#v{n}`,
  the **hot-partition GSI rule** (user-scoped or sparse; no `STATUS#{status}` GSI PK), edits via conditional
  `UpdateItem` on `version` (= the 409 contract), `CoreRepository` as sole key-builder, and the 3 caches kept
  out of `core`. A rebuild would build exactly this from day one — but so does the in-place `core` collapse
  (Phase 3), which now reuses the **already-proven CR (FE-UI-044) canonical-store migration pattern**.
- **Live re-verify 2026-07-08:** volumes still tiny (users 908 / artifacts 221 / everything else <150) → a
  parallel-rebuild's whole premise (avoid a risky migration of large live data) is weak: the in-place backfill
  is hours. This sharpens the rebuild-vs-in-place scorecard.
- **Same unresolved high-stakes assumptions apply to the rebuild's clean design** (context-pack §8): identity
  keying (`sub` vs surrogate `user_id`), knowledge-base keep/drop. The rebuild does NOT dodge them.

---

## 1. Full capability surface (what "feature parity" must reproduce)

Authoritative route map: `infra/careervp/api_construct.py`
(`_add_openapi_contract_routes` ~2814; public allowlist `public_paths` :2781).

### API surface (all Cognito-auth unless marked public)
- **Auth:** `POST /auth/register` (public), `/auth/login` (public), `/auth/refresh`,
  `/auth/logout`.
- **User/CV:** `GET|PUT /users/me`, `/users/me/usage`, `POST /users/me/trial/reset`,
  `POST /users/me/cv` (upload+parse), `GET|DELETE /users/me/cv[/{id}]`.
- **Jobs/Applications:** `POST|GET /jobs`, `GET /jobs/{id}`, `GET /applications/{id}`.
- **Gap:** `POST|GET /jobs/{id}/gap-questions`, `POST /jobs/{id}/gap-responses`
  (submitting responses **triggers the Step Functions chain**).
- **Artifacts (each: generate → status → list → cancel → patch):** `/vpr/*`,
  `/cv-tailoring/*`, `/cover-letter/*`, `/interview-prep/*`.
- **Company research:** `GET /company-research/{jobId}`, `POST /company-research/fetch`,
  `POST /company-research/{jobId}/cancel`.
- **Knowledge:** `GET|POST /knowledge-base`.
- **AI assist:** `POST /ai/assist` (field rewrite, no credit, 25s cap).
- **Billing:** `POST /billing/checkout`, `/billing/portal`,
  `POST /billing/webhook` (**public**, self-verifies signature).
- **Export:** `GET /jobs/{id}/artifacts/{type}/export?format=docx|pdf` (PDF = 501).
- **Ops:** `GET /health` (public), `POST /errors` (public), `/swagger*` (public).

### Two coexisting async models (both must be reproduced or consolidated)
- **A — per-artifact submit → SQS → worker (standalone):** VPR, cover-letter,
  interview-prep, company-research each have a queue + DLQ + worker. `vpr_dlq_handler`
  reaps orphans.
- **B — Step Functions chain** (`careervp-artifact-chain-{env}`, Standard, 2h):
  triggered on gap-response submit; uses `sqs:sendMessage.waitForTaskToken` into the
  *same* artifact queues; workers call `send_task_success/failure`. Stages:
  RouteStartAt (Choice, resume) → CompanyResearch (180s heartbeat) → VPR →
  (Choice: stop if VPR-only) → CVTailoring (sync invoke) → Parallel{CoverLetter,
  InterviewPrep} (300s heartbeat). Failure Lambdas: `cr_failure_handler`,
  `artifact_failure_handler`; hourly `artifact_cleanup_handler` reaper.

### Artifact dependency graph (`logic/artifact_dependency_resolver.py`, pure)
```
Base CV → gap_analysis → company_research → VPR ─┬→ cv_tailored
                                                 ├→ cover_letter (also needs company_research)
                                                 └→ interview_prep
```
Resolver returns `ready` / `upstream_required` (409) / `dependency_generating` (202);
dedups on `chain_execution_status == RUNNING`; VPR staleness vs. gap-response age.

### Cross-cutting capabilities
- **LLM infra:** `LLMRouter` — STRATEGIC→Sonnet (`claude-sonnet-4-6`: VPR, gap,
  CR-structuring), TEMPLATE→Haiku (`claude-haiku-4-5`: CV parse, tailoring, cover
  letter, interview prep). Prompt caching, DynamoDB `llm-cache` (7d), circuit breaker
  (5 fails/60s), CloudWatch cost metric ($0.25/run alert).
- **FVS validator** (`fvs_validator.py`): fact-verification + anti-AI-pattern scoring,
  min 90/100 — gates VPR / tailored-CV / cover-letter.
- **Quota/Trial:** 14-day / 3-application trial; access = active sub OR trial.
- **Company research:** Tavily search → scrape (SSRF-guarded) → LLM structuring;
  confidence gate 0.85; cross-user intel cache (183d profile / 120d news).

### External integrations a rebuild must reproduce
- **Anthropic** (Sonnet + Haiku, direct API), **Tavily** (web search),
  **payment provider** (abstract `PaymentProviderInterface`; only a `placeholder.py`
  stub exists today — no real Stripe/Paddle yet), **Cognito** (user pool + authorizer).
  No SES/email (Cognito handles auth mail). Frontend: Next.js/Amplify.

---

## 2. Proposed MVP → parity carve (for the council to critique, not accept)

- **MVP — corrected walking skeleton:** Cognito auth; CV upload→parse→persist;
  job create; **exactly one artifact end-to-end — VPR** (submit→SQS→worker→status→S3),
  because VPR is the hub of the dependency graph and exercises the full
  async+LLM+FVS+presigned stack; LLMRouter + circuit breaker + llm-cache; health +
  error reporting. **Excludes** Step Functions and Company Research deliberately.
- **Wave 2 — dependency graph:** gap-analysis + company research (Tavily + intel
  cache), the resolver, and the Step Functions chain (CR→VPR).
- **Wave 3 — full artifact suite:** tailored CV, cover letter, interview prep + the
  Parallel final stage (near-clones of the VPR pattern).
- **Wave 4 — monetization/lifecycle:** real payment provider, checkout/portal/
  webhook/reconcile, trial + quota, subscription-gated access. (Highest coexistence
  risk — see §3.)
- **Wave 5 — polish/ops:** export, AI-assist, knowledge-base, cleanup reaper,
  cancellation, WAF/monitoring, swagger.

---

## 3. Same-account coexistence contention (the crux of side-by-side)

- **`ServiceStack` is already at the 500-resource CFN ceiling** (see `context-pack.md
  §4 HIGH`). A second full platform in the same account **forces** nested-stack
  decomposition and hard resource budgeting — side-by-side is NOT free.
- **Payment webhook is a hard singleton.** `POST /billing/webhook` is one URL + one
  signing secret registered with the provider. Two platforms cannot both receive the
  same provider's live events. Options: provider test-mode / separate secret, or keep
  the rebuild on the placeholder until Wave 4.
- **Resource naming is env-suffixed** (`NamingUtils.table_name/bucket_name`,
  `careervp-*-{env}`). ⚠️ **If the rebuild reuses the live `env`, it binds directly
  onto production `users`/`applications`/`artifacts` tables and the `cvs` bucket and
  can corrupt prod data.** The rebuild MUST use a distinct `env`/feature suffix.
- **Cognito:** rebuild should provision its **own** pool (`careervp-users-{env}`);
  sharing a pool means shared identities/passwords — only if intentional.
- **SSM parameters** (Tavily key, webhook secrets) are shared by path — give the
  rebuild its own paths or it reads/rotates live secrets.
- **EventBridge singletons** — nightly billing reconcile + hourly artifact cleanup
  call the provider / delete S3 objects. Two copies over shared data = double-reconcile
  / double-reap. **Keep disabled in the rebuild until it has isolated data.**
- **Anthropic/Tavily** — stateless, no singleton constraint; only shared rate limits
  and cost attribution to watch (relevant to the >70% margin during coexistence).

---

## 4. Rebuild-specific open questions (flag if they change a recommendation)

1. **Shared vs. copied data during coexistence** — does the rebuild read/write the
   *same* DynamoDB tables as prod (risky, but no migration), or its own copy kept in
   sync via Streams CDC (safe, but doubles storage + sync complexity for a solo dev)?
2. **Traffic routing mechanism** — API Gateway stage/weighting, a header/cohort flag,
   or DNS? Who decides which users hit the rebuild?
3. **Parity verification** — is shadow/diff testing (mirror prod requests to the
   rebuild, compare outputs) in scope, or is manual per-wave acceptance enough for a
   solo dev?
4. **The two async models** — should the rebuild **consolidate** the standalone
   submit→SQS→worker path and the Step Functions chain into one model, or reproduce
   both? (Simplification opportunity vs. parity.)
5. **Payment provider** — the rebuild is a chance to implement the real provider
   cleanly; is that in the rebuild's critical path or still deferred behind the placeholder?
