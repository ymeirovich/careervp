# Claims Ledger

Every contested claim about this system, with the observation that settles it.

**Why this exists.** In this project, disputes have been settled *exclusively* by
observations neither party controlled — a metric, a grep count, a deployed response,
a decoded token, a synth diff. Never by argument quality, and never by agreement
between agents. Agreement between two LLMs reading the same repo is *correlated*
evidence, not corroboration: treat unanimity with the same suspicion as conflict.

## Rules

1. **Classify before arguing.**
   - **O — Observable.** A command exists that returns a value today. **Nobody is
     permitted to hold an opinion.** Run it.
   - **E — Experimental.** Needs an action to produce evidence. Design the smallest
     experiment that could come back either way.
   - **J — Judgment.** No observation settles it. A human decides; agents supply
     costed options, never verdicts.
2. **Every claim ships with its falsifier** — "the observation that would prove me
   wrong is ___". A claim without one is an opinion.
3. **Predict before observing.** Write the expected output *first*, then run. If the
   result differs and the claimant explains why it was always consistent with their
   view, that rationalisation is now on the record.
4. **Unresolvable and blocking → take the reversible option.**
5. **Enumerate exhaustively over a defined surface.** Targeted investigation finds
   what you already suspect; enumeration finds what you don't. N1 (72/72 failures)
   was found by listing every Lambda, not by suspecting the CV worker.

## Status values

`OPEN` · `OBSERVED` (evidence in, verdict recorded) · `HUMAN` (awaiting decision) ·
`CLOSED`

---

## Open claims

### C-01 — Do the remaining 5 CV readers resolve CVs from `cvs-table`?
- **Type** E · **Status** OPEN · **Claimant** Claude (Stage 1 repoint)
- **Falsifier** Any reader returns "CV not found" / `UpstreamMissingError('cv')`
  after the repoint, while the dual-write is still running.
- **Prediction** All 5 resolve. `user-api` already PASSED (gate f).
- **Settled by** Each stage's own gate: gap → Stage 3, ai-assist → Stage 4,
  vpr-worker → Stage 5, cv-tailoring → Stage 6, cover-letter/interview-prep → 7–8.
- **Note** Deliberately NOT settled in Stage 1: 5 of 6 readers sit behind upstream
  artifact gates, so verifying them in Stage 1 means running the whole journey.
  Gates Stage-1 closeout (steps 4b/5/6).

### C-02 — Does the sync parse path fully replace the deleted S3 worker?
- **Type** E · **Status** **OBSERVED 2026-08-08 — prediction CONFIRMED** · **Claimant**
  Claude + audit (agreed — was correlated; now confirmed by an independent instrument)
- **Falsifier** A DLQ message whose user has **no** CV row; or a CV-bucket producer
  that bypasses `cv_upload_handler`.
- **Prediction** All 22 DLQ users have CVs. Zero bypass producers (only writer is
  `cv_upload_handler.py:133`; `user_handler.py:270` deletes only; frontend has no
  presigned upload).
- **Observed** Read non-destructively (`--visibility-timeout 0`, 23/23 recovered,
  nothing consumed). **Correction: 23 messages naming 5 distinct users, not 22
  naming 22.** All 5 users have CV rows in both tables. At object granularity
  (`source_file_key`) 22/23 match; the 1 miss
  (`8428d4e8-…/cdc0b0b2-….txt`, 113 B, 2026-08-01T15:28:20Z) is a request the API
  answered with **HTTP 500** — honest failure, not silent loss, and the worker could
  not have rescued it (100 % lifetime failure). Falsifier 2: **zero** bypass
  producers — only two Lambdas get `CV_BUCKET_NAME` and both run the *same* handler;
  the worker holds `grant_read` only (`api_construct.py:1905`).
- **Residual (J)** The worker's 300 s timeout vs the API's shorter one suggests it
  may have been the intended large-file path. Deleting breaks nothing today, but
  converts "large CVs accidentally broken" → "large CVs unsupported."
- **Spawned** → **N22** (below): 2 orphaned S3 objects, no reaper.

### C-03 — What fraction of 4xx is security vs contract?
- **Type** O · **Status** **OBSERVED 2026-08-08 — prediction REFUTED** (headline
  settled; per-endpoint *post-fix* answer still open, see below)
- **Falsifier** n/a — it's a measurement.
- **Why it matters** The audit's single largest caveat, and the input to confidence
  #5 (measured 23.7 % aggregate 2xx). Also explains `/interview-prep/generate` at
  6 % and `/cover-letter/generate` at 12 %, which are suspected to be dominated by
  401s plus pre-fix 409s from before 2026-08-03.
- **Prediction** Both generate endpoints are **auth-dominated**; >60 % of their
  non-2xx is 401/403.
- **Observed** **Security 4xx = 10 of 199 (5 %). Contract 4xx = 189 of 199 (95 %).**
  Both target endpoints have **zero** 401 and **zero** 403.
  `/interview-prep/generate` 26 calls → 2 2xx, **19×400**, 4×409, 1×5xx.
  `/cover-letter/generate` 21 calls → 3 2xx, 6×400, **12×409**.
  Also refuted: the audit's guess that `/users/me*` GETs are "very likely dominated
  by 401s" — in this window they are 93/93, 51/51 and 51/51, i.e. **100 % 2xx**.
- **Instrument — the prompt's premise was wrong.** The Stage-0 access log holds only
  **33 records, all 2026-08-05**, and **zero** on either target endpoint; it cannot
  answer this. The answer came from the **pre-existing** execution log
  `API-Gateway-Execution-Logs_ymzhvcxod0/prod` (retention *never expires*, 21,914
  records, 1,310 correlated requests, 2026-07-20 → 2026-08-05), which was already
  installed and already held the answer.
- **Still open** Every 400 (and all but one 409) lands on **2026-08-01**, before the
  2026-08-03 F-DEVX-1 fixes. Windowed strictly after 2026-08-03 as instructed there
  are **2** requests total. Whether a *live, post-fix* contract defect remains is
  settled by Stage 3+ traffic, not by this query.

### C-04 — Is the cover-letter read cross-tenant exploitable today?
- **Type** O · **Status** OPEN · **Claimant** Claude (S3)
- **Claim** `read_cover_letter_by_artifact_id` takes no `user_id`; isolation rests
  only on cover letters being *accidentally* partitioned by Cognito sub.
- **Falsifier** User A reads user B's cover letter with a known `artifactId` and
  gets 200.
- **Prediction** 404/403 today (the partition key is the tenant key), and **200
  after the Stage 7 repartition unless ownership lands first**. If the prediction
  is wrong and it already returns 200, this is a live vulnerability, not a latent
  one — escalate immediately.
- **Status** **OBSERVED 2026-08-08 — prediction CONFIRMED. No escalation.**
- **Observed** Two real Cognito identities. User A = `848834a8-…` (owns all four
  devx cover letters); user B = `14683418-30a1-7018-9421-49a6fe0a7f78` (registered
  for this test at explicit human approval, one account, waiving the no-register
  rule). B attempted all three cover letters:

  | request | user B | user A (control) |
  |---|---|---|
  | `GET /cover-letter/{id}/status` | **404** `COVER_LETTER_NOT_FOUND` ×3 | **200** ×3 |
  | `GET /cover-letters` | 200, **0 items** | 200, **4 items** |

  The control matters: without it a 404 could just mean "route always 404s". It
  does not — the owner gets 200 on the same ids in the same minute.
  (`GET /cover-letter/{id}` without `/status` returns 403 `DEFAULT_4XX` for **both**
  users; it is not a real route and proves nothing either way.)
- **Latent risk unchanged, and now evidenced.** Isolation holds only because
  `applicationId` currently *equals* the owner's Cognito sub. The Stage 7
  repartition replaces that value with a real application id, at which point
  `read_cover_letter_by_artifact_id` — which still takes no `user_id` — loses its
  tenant key. **Ownership must land before the repartition**, exactly as P3→P4
  ordering states.

### C-05 — Does the 8 KB WAF body limit block anything else?
- **Type** O · **Status** **OBSERVED 2026-08-08 — prediction SPLIT** (log half
  CONFIRMED, ranking REFUTED) · **Claimant** Claude
- **Context** `SizeRestrictions_BODY` blocked every body > ~8 KB. It is why no real
  CV ever reached the parser. Stage 0/1 raised it for devx only.
- **Falsifier** Every other endpoint's realistic max payload is under the limit.
- **Prediction** Zero non-CV `SizeRestrictions_BODY` in the logs;
  `POST /jobs/{id}/gap-responses` with 10 answers is the most likely second victim.
- **Observed (log half — CONFIRMED)** Full 14-day WAF retention, 1,011 records:
  **zero** `SizeRestrictions_BODY` on any non-CV path. Only `/prod/users/me/cv`
  (5 BLOCK + 1 COUNT). The single COUNT is the 2026-08-05 20:47:54 upload, which
  also proves the Stage-1 override is live:
  `{"ruleId":"SizeRestrictions_BODY","action":"COUNT","overriddenAction":"BLOCK"}`.
- **Observed (ranking — REFUTED)** `gap-responses` is **fourth**, not first.
  `api_models.py` has **13 request models and zero `max_length`** — nothing in the
  API contract bounds any body. Ranked by realistic max: `POST /users/me/cv`
  (53,602 B observed) > `POST /ai/assist` (`current_text` unbounded; measured VPR
  artifacts reach **19,704 B**) > `PATCH /cv-tailoring/{id}` (bare `json.loads`,
  **no model at all**) > `POST /jobs/{id}/gap-responses` (~8–12 KB) > `POST /jobs`.
  Separately: `cv_tailoring_models.py:35` permits `max_length=50_000` — the internal
  contract allows a body **six times** the WAF limit.

### N22 — Orphaned CV objects in S3 (new, 2026-08-08, flagged not fixed)
- **Type** O · **Status** OBSERVED · **Claimant** Claude (from the C-02 correlation)
- **Evidence** Reconciling the CV bucket against `cvs-table`: **2 orphans**, zero
  dangling rows. `cv_upload_handler` PUTs to S3 (`:132`) *before* the DynamoDB write
  (`:188`), so any failure after the PUT leaks the object; per N5 the S3 reaper is a
  no-op. Low severity in devx, a real leak in prod.

### C-06 — Do `artifact-failure-handler` / `cr-failure-handler` share N1's shape?
- **Type** O · **Status** **OBSERVED 2026-08-08 — prediction CONFIRMED, CLOSED**
- **Claim** Both are never-invoked, so an N1-shaped bug (non-HTTP trigger, API-only
  handler, no `Records` branch) would be invisible.
- **Falsifier** Both branch on `Records`/`eventSource`.
- **Prediction** Both are purpose-written for a direct Step Functions payload and do
  **not** parse an API-Gateway event ⇒ no N1 shape.
- **Observed** Neither touches `httpMethod`, `body`, `Records` or `eventSource`.
  The falsifier as written is the wrong test — Step Functions never sends `Records`.
  The test that matters is payload/parser agreement, and it holds exactly:
  `HandleCRFailure` sends `TaskInput.from_json_path_at("$")` and the handler reads
  `user_id`/`job_id` (`cr_failure_handler.py:35-39`); the five artifact states send
  `{"artifact_type": …, "context": object_at("$")}` and the handler reads exactly
  that (`artifact_failure_handler.py:33-40`). Every `add_catch` writes its error to
  a `result_path` beside `$`, so the ids survive into the failure branch.
  **No N1-shaped bug.**
- **Flagged not fixed** `HandleFinalArtifactsFailure` passes
  `artifact_type="final_artifacts"`, which no artifact type corresponds to;
  `update_artifact_status` accepts any string, so it writes a junk map key.

### C-07 — Is `/users/me/cv` a duplicate-creation bug, not just slow?
- **Type** E · **Status** OPEN · **Claimant** Claude (new, from Stage 1 evidence)
- **Context** 16,884 ms observed against the 29 s ceiling (~12 s headroom), at the
  head of the journey. Per N17 the Lambda keeps running after the client 504s.
- **Falsifier** A forced timeout leaves **no** CV row → then it is only a latency
  problem.
- **Prediction** The write completes, the client sees a 504, the user retries, and
  a duplicate CV is created.

### C-08 — Does re-homing tailored CVs break AI-Assist?
- **Type** E · **Status** OPEN · **Claimant** Claude (S1, code-read only)
- **Claim** 8 `ARTIFACT#CV_TAILORED` rows live in users-table; AI-Assist's
  `_load_tailored_cv` would miss them after the artifacts repoint, so
  `cover_letter` and `interview_prep` assist stay broken.
- **Falsifier** AI-Assist resolves a tailored CV after the Stage 4 env fix without
  re-homing.
- **Settled by** Stage 4 / Stage 6 gates.

### C-09 — Delete: implement or defer to V2?
- **Type** **J** · **Status** HUMAN · **Claimant** audit (N4)
- **Evidence** 1 DELETE route in a 49-route API; 5 of 6 artifact types have no
  delete path; no DynamoDB reaper (the S3 reaper is a no-op — N5); no frontend
  DELETE call.
- **Not a probability.** The earlier "40 % confidence in CRUD" was a category error:
  the question is not whether Delete works, it is whether Delete exists.

### C-10 — Is Hebrew in scope for launch?
- **Type** **J** · **Status** HUMAN · **Claimant** audit (N16)
- **Evidence** V1 scope per `CLAUDE.md` is English + Hebrew. 52 live `language`
  values, all `en`. Never exercised end to end.

---

## Settled claims (calibration record)

| # | claim | claimant | type | verdict | settled by |
|---|---|---|---|---|---|
| S-01 | "AI Assist degrades quietly without VPR" | Claude | O | **REFUTED** — it raises `UpstreamMissingError` for 3 of 4 types | read `REQUIRED_UPSTREAM` |
| S-02 | "Second defect found in company research" | Claude | O | **REFUTED** — the test account did not own the application | decoded JWT `sub` vs row owner |
| S-03 | "DP-C already settled; `TABLE_SCHEMA_MISMATCH` is emitted" | Codex | O | **REFUTED** — VPR methods bypassed `_dal_failure_result` | grep call sites |
| S-04 | "Fix AI-Assist by repointing `VPR_TABLE_NAME`" | Codex | O | **REFUTED** — nothing reads that variable | grep for readers → 0 |
| S-05 | "Cover letter works after the canonical write" | Claude | E | **REFUTED twice** — missing artifact id, then `Decimal` not serialisable | deploying |
| S-06 | "1419 tests green ⇒ the path works" | Claude | O | **REFUTED** — CV worker 72/72 failures while suite green | CloudWatch metrics |
| S-07 | "CV worker fails 66/66" | audit | O | **CORRECTED** → 72/72, then 75/75 | CloudWatch metrics |
| S-08 | "WAF blocks at 8192 bytes" (inferred) | — | O | **CONFIRMED by name**, not by inference | read rule `SizeRestrictions_BODY` |
| S-09 | "The WAF change is contained to devx" | Stage 0/1 | E | **CONFIRMED** | synthesised all 3 envs, diffed |
| S-10 | "The CV worker is redundant" | Claude | O | **CONFIRMED** — same handler, no `Records` branch, sync path parses at :154 | code read + 100 % lifetime failure |
| S-11 | "The two generate endpoints' 4xx is auth-dominated (>60 % 401/403)" | Claude (C-03) | O | **REFUTED** — 5 % security, 95 % contract; zero 401/403 on both | execution-log request-id join, n=1310 |
| S-12 | "`/users/me*` GETs are very likely dominated by 401s" | audit (N14 caveat) | O | **REFUTED** — 93/93, 51/51, 51/51 all 2xx in window | same join |
| S-13 | "`gap-responses` is the most likely second WAF victim" | Claude (C-05) | O | **REFUTED** — it ranks 4th; `/ai/assist` and `PATCH /cv-tailoring` are worse | 22-route enumeration + measured artifact sizes |
| S-14 | "Zero non-CV `SizeRestrictions_BODY` blocks" | Claude (C-05) | O | **CONFIRMED** | 1,011 WAF records, full retention |
| S-15 | "The failure handlers may share N1's shape" | audit (C-06) | O | **REFUTED** — payload and parser agree exactly on all six states | code read of chain + handlers |
| S-16 | "All 22 DLQ users have CVs; zero bypass producers" | Claude+audit (C-02) | E | **CONFIRMED** (counts corrected to 23 msgs / 5 users) | non-destructive DLQ read + `source_file_key` join |

### Per-agent calibration so far

**Claude:** 7 claims refuted by observation (S-01, S-02, S-05 ×2, S-06, S-11, S-13),
2 confirmed (S-14, S-16). Two of three F-DEVX-1 commits were fixes for bugs shipped
hours earlier. Five of six confidence numbers were 20–30 points high; the only
well-calibrated one was where explicit evidence of ignorance existed.

*2026-08-08 addendum.* The pattern in S-11/S-13 is the same one: when asked to
predict *which* cause dominates, Claude reached for the socially safe answer (auth
noise; the endpoint the prompt already suspected) rather than the one the data
supports. Both were wrong in the same direction — toward "nothing is really broken".
Separately, during Stage-1 4a, Claude misattributed 45 self-inflicted test failures
to pre-existing changes before isolating them; the correction is recorded in
[`wave3-typeo-closure-stage1-4a-stage2-20260808.md`](../../../../evidence/wave3-typeo-closure-stage1-4a-stage2-20260808.md) §6.

**Codex:** 2 claims refuted by observation (S-03, S-04), both by a single grep, both
stated as established fact.

**Implication:** never let either agent close a Type-O question by reasoning.
