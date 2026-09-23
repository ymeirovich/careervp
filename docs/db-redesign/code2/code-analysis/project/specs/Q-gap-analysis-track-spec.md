---
spec_id: Q-GAP-TRACK
title: "Gap Analysis fixes — CR-first, real CV, Sonnet, CR/KB wiring"
status: draft
owner: backend
tier: feature
# Multi-clause spec: list-valued scope_lock_clause + per-clause tooling map.
# This is the SANCTIONED multi-clause form (scope-lock §8.5, codified v1.5.0/A7) — scope-diff.py
# handles the list (covers every listed clause) and requires a tooling entry per listed clause.
scope_lock_clause: [Q-01, Q-02, Q-03, Q-04]
tooling:
  Q-02: {claude_code: {model: sonnet, effort: medium}, codex: {model: gpt-5-codex, reasoning: medium}}  # mechanical
  Q-03: {claude_code: {model: sonnet, effort: medium}, codex: {model: gpt-5-codex, reasoning: medium}}  # mechanical
  Q-04: {claude_code: {model: sonnet, effort: medium}, codex: {model: gpt-5-codex, reasoning: medium}}  # wiring
  Q-01: {claude_code: {model: opus,   effort: xhigh},  codex: {model: gpt-5-codex, reasoning: high}}    # hard: chain reorder
format_note: "RED tests are TDD-first, not optional; RED-test descriptions inline (v1.3.0); pytest files written at IMPLEMENT in the real careervp repo. Each clause below carries an AC-### Given/When/Then block (§8.5)."
---

# Spec — Track Q: Gap Analysis fixes (CR-first, real CV, Sonnet, CR/KB wiring)

- **Status:** SPEC ONLY — do **not** implement here. Apply under TDD in the redesign implementation wave (Wave 4, `Q-*`).
- **Governs clauses:** `Q-01` (CR-first chain reorder), `Q-02` (real CV), `Q-03` (Sonnet via router), `Q-04` (CR + KB wiring into gap). Model/effort per clause in the frontmatter above.
- **Code anchor:** `github.com/ymeirovich/careervp @ 4f7c294`. All file:line refs are at that commit.
- **Env note for the implementer:** backend requires Python **≥3.13** + `uv` (`src/backend/pyproject.toml`). Run tests via `uv run pytest` in `src/backend/`. (The analysis env had only Python 3.9 / no uv — set this up first.)
- **TDD contract:** each fix below lists the **RED test(s) to write and watch fail FIRST**, then the minimal GREEN change. No production edit without a failing test first (per `superpowers:test-driven-development`).
- **Constraints (all clauses):** never break the §3 frontend contract; keep every LLM call inside the `>70%` margin (C-2) via per-step digests; one reversible, flag-gated change at a time; characterization test before touching current behavior.

---

## Q-02 — Inject the REAL CV into gap-question generation
**Bug (confirmed):** gap generation runs on a hardcoded STUB CV, never the user's real parsed CV.
- `gap_handler.py:528-533` `_build_user_cv_prompt_payload(cv_id, focus_areas)` returns a static dict (`full_name:'Candidate'`, `skills=focus_areas`, one fake `'Current Company'/'Engineer'` experience). `cv_id` is smuggled into the fake item, never used to load anything.
- Passed to `generate_gap_questions(user_cv=...)` at `gap_handler.py:165,179-185` → `gap_analysis.py:282` `create_gap_analysis_user_prompt`.
- Correct loader exists: `DynamoDalHandler.get_cv_by_id(user_id, cv_id) -> UserCV | None` (`dynamo_dal_handler.py:208-233`). VPR does it right: `cv_dal.get_cv(user_id)` + guard (`vpr_worker_handler.py:400-413,440`).

**Fix (GREEN, minimal):**
1. In `gap_handler.py`, resolve the CV table and build a `DynamoDalHandler` (mirror the jobs-repo accessor pattern already in the handler).
2. Rewrite `_build_user_cv_prompt_payload` to take `user_id` **and** `cv_id`, call `dal.get_cv_by_id(user_id, cv_id)`, and on success return `user_cv.model_dump(mode='json')` mapped to the dict keys the active prompt reads (`personal_info.full_name`, `work_experience[].company/role/responsibilities`, `skills`, `education`).
3. On `None`/DAL error: return the **§3 contract item-10 error envelope** `{error|message, classification, error_code, field}` with **HTTP status `404`** and `error_code = "cv_not_found"` — do **not** silently ship the stub, and do **not** return a bare/non-envelope error (that reproduces the F-05 `[object Object]` class). Log a warning. *(No "logged-fallback" alternative — the response is exactly the item-10 envelope + 404; a single pinned behavior, not an OR.)*
4. Update the call site `gap_handler.py:165` → `_build_user_cv_prompt_payload(user_id=user_id, cv_id=cv_id, focus_areas=focus_areas)`.
- `generate_gap_questions` signature is unchanged (still a dict).

**RED tests to write first (watch fail):**
- `test_gap_payload_is_characterization_stub` — asserts current behavior: payload `full_name == 'Candidate'` and contains `'Current Company'`. (Documents the bug; invert after the fix.)
- `test_gap_loads_real_cv_moto` *(real-key-schema, moto-backed — the primary correctness test; supersedes hand-mocking)* — seed a **moto `cvs-table` with the ACTUAL live key schema** (`pk/sk` + `userId/cvId`, per live-truth) holding one known `UserCV` (real name + real experience/skills); call the handler with that `user_id`+`cv_id`; assert the prompt string passed into the model **contains the real candidate name + a real experience bullet** and **does NOT contain** `'Candidate'`/`'Current Company'`. Rationale (test-strategy §1): hand-mocked resolver dicts are exactly what hid P-01 — this test drives the real `get_cv_by_id` against a real key schema.
- `test_gap_loads_real_cv_by_id` *(unit companion, patch-based)* — patch `DynamoDalHandler.get_cv_by_id` to return a known `UserCV`; assert `get_cv_by_id` called with the request's `user_id` + `cv_id`. (Kept as a fast unit check; the moto test above is the authoritative one.)
- `test_gap_missing_cv_errors_not_stub` — `get_cv_by_id` returns `None` → assert the response is the **§3 item-10 envelope with HTTP 404 and `error_code == "cv_not_found"`** (assert the exact envelope keys + status), and that the payload is **never** the `'Candidate'` stub. (No "or logged fallback" branch.)

**AC-Q02-1** — *Given* a valid `user_id`+`cv_id` for a stored real CV, *When* gap questions are generated, *Then* the model prompt contains the real candidate identity (name + ≥1 real experience bullet) and contains neither `'Candidate'` nor `'Current Company'`, and `get_cv_by_id` was called with that `user_id`+`cv_id`.
**AC-Q02-2** — *Given* a `cv_id` that resolves to `None` (missing/stale CV), *When* gap questions are requested, *Then* the endpoint returns HTTP `404` with the §3 item-10 envelope `{error|message, classification, error_code: "cv_not_found", field}` and never a stubbed success. *(Carries §3 contract item 10.)*
**AC-Q02-3** — *Given* the gap request/response wire shape, *When* this fix ships, *Then* the shape is unchanged (no frontend-contract change; oracle green on the gap endpoint).

**Done-when:** all RED tests pass (incl. the moto real-key-schema test); ruff/mypy clean; AC-Q02-1..3 hold; oracle green on the gap endpoint.

---

## Q-03 — Route Gap Analysis to Sonnet (Strategic) via the LLMRouter
**Bug (confirmed):** gap runs on **Haiku**. `gap_analysis.py:283` instantiates the plain `LLMClient()`, `:286` calls `.generate(prompt=...)` with no model; `LLMClient.generate` defaults `DEFAULT_MODEL='claude-haiku-4-5-20251001'` (`llm_client.py:22,99`). It bypasses `LLMRouter`, whose spec classifies Gap as STRATEGIC→Sonnet (`utils/llm_client.py:5-6,39,177-179`).

**Fix (GREEN — Option A, spec-consistent):** in `gap_analysis.py`, replace the plain client with the router:
- import `TaskMode, get_llm_router` from `careervp.logic.utils.llm_client`;
- call `get_llm_router().invoke(mode=TaskMode.STRATEGIC, system_prompt=..., user_prompt=..., max_tokens=4096, temperature=0.3)`;
- feed the returned `.data['text']` into `_extract_questions` (already handles a `{'text':...}` dict). Routing to `SONNET_MODEL_ID` is then automatic, plus router cost caps/metrics.
- **Decision (pinned — no floating decider): use Option A (router).** Option B (`model_name='claude-sonnet-4-6'` on the plain client) is recorded ONLY as an emergency revert, not an implementer's choice; it loses cost caps and MUST NOT ship as the primary path.
- **Binding gate (v1.5.0/A13): Gap→Sonnet MUST NOT enable in production until Q-10 real token metering exists** to measure cost-per-gap against the C-2 headroom; **default to Haiku until then**, and the router config keeps a `TaskMode`→Haiku revert lever. A **degraded (empty-CR) gap MUST route to Haiku, never Sonnet** (see Q-01 / L-5 — Sonnet is paid for the CR-fed lift).

**RED tests to write first:**
- `test_gap_uses_strategic_router` — spy/patch `get_llm_router().invoke`; call `generate_gap_questions`; assert it was invoked with `mode == TaskMode.STRATEGIC` (and NOT the plain `LLMClient.generate`).
- `test_gap_resolves_sonnet_model` — assert the router resolves `TaskMode.STRATEGIC` → `SONNET_MODEL_ID` (guards against a silent Haiku regression).

**Measure the added value (separate, non-blocking):** fixed eval set of ~20–30 (CV, JD) pairs; generate under Haiku vs Sonnet with inputs held constant; rubric + LLM-judge (temp 0) scoring on relevance/specificity/priority-tagging; downstream FVS-lift signal; compare vs ~2¢/run cost delta. Records the "worth it" decision. (See `Q-08` eval harness.)

**AC-Q03-1** — *Given* a gap-question generation request with a non-empty CR block and Q-10 metering live, *When* it runs, *Then* it is invoked via `get_llm_router().invoke(mode=TaskMode.STRATEGIC, …)` and the router resolves `SONNET_MODEL_ID` (not the plain Haiku default).
**AC-Q03-2** — *Given* Q-10 metering is NOT yet live, OR the CR block is empty (degraded path), *When* gap runs, *Then* it routes to Haiku, never Sonnet.
**AC-Q03-3** — *Given* measured Q-10 cost data, *When* Sonnet is enabled, *Then* measured cost-per-gap keeps cost-per-app within the C-2 headroom; if it does not, the `TaskMode`→Haiku revert lever is flipped.

**Done-when:** both tests pass; AC-Q03-1..3 hold; the eval harness produces a scored Haiku-vs-Sonnet comparison; measured (Q-10, not `len/4`) margin still `>70%` with the Q-04 digest inputs.

---

## Q-04 — Wire Company Research + KB recall INTO the gap prompt (wiring, not template rewrite — validated)
**Validated:** the **active** builder `create_gap_analysis_user_prompt(user_cv, job_posting)` (`gap_analysis_prompt.py:46`) **already** reads and renders:
- `company_research = job_posting.get('company_research')` → "# Company Research Context" block (`:54,91-97`);
- `recurring_themes` and `previous_gap_responses` (the KB-recall slots).
All three are **unfed** — the handler's `_build_job_prompt_payload` (`gap_handler.py:536-561`) only sets `company_name/role_title/requirements/responsibilities`. So CR-into-gap and KB-into-gap are **wiring jobs** (pass the values through); **no template change** for the active builder. *(Only the unused typed `build_user_prompt` at `:30-38` would need a template change — do not migrate to it as part of this.)*

**The CR digest — DEFINED (no `<digested CR>` hand-wave; v1.5.0):**
- **Field list (projected subset of the CR artifact, NEVER the raw ~15k-token Tavily dump):** `company_name`, `industry`, `company_size`, `recent_news` (top 3 headlines only), `culture_values`, `tech_stack`, `interview_signals`. This is the "store rich, project lean" projection (invariant §4).
- **Explicit token cap:** **1,200 tokens** for the CR digest block (mirrors the KB cap; one shared cap constant `CR_DIGEST_TOKEN_CAP = 1200`).
- **Counting method:** count with the **target model's real tokenizer** (the Q-10 meter once step 0.75 lands; until then the Anthropic tokenizer for the routed model) — **never `len/4`**. Truncate **deterministically by dropping lowest-priority fields first** in this order: `recent_news` → `tech_stack` → `interview_signals` → `culture_values`, until the block is ≤ cap. (Deterministic so the test asserts an exact resulting token count, not "under the cap".)

**Fix (GREEN):**
- CR-into-gap: in `gap_handler.py`, fetch the completed CR for the application (from the shared CR cache/artifact — see Q-01 ordering), build the digest above, and set `job_posting['company_research'] = cr_digest`.
- KB-into-gap: set `job_posting['recurring_themes']` and `['previous_gap_responses']` from the `ProfileRecallService` — **the recall interface defined by clause `Q-05`** (this spec depends on Q-05; if Q-05's service is not yet built, pass empty/None → the block renders nothing, a safe no-op) — under the same 1,200-token cap and counting method.

**RED tests to write first:**
- `test_gap_prompt_includes_company_research_when_provided` — provide a CR digest; assert the built prompt contains the "Company Research Context" block content; assert it's ABSENT when not provided.
- `test_gap_prompt_includes_recalled_kb_when_provided` — provide `recurring_themes` + `previous_gap_responses`; assert they render; absent when empty.
- `test_gap_cr_digest_respects_token_cap` — provide an oversized CR artifact; assert the injected digest is **≤ 1,200 tokens by the real tokenizer** AND that the highest-priority fields (`company_name`, `industry`, `company_size`) survive while the lowest-priority fields drop **in the defined order** (assert the exact fields present at the cap boundary — not a vague "under the cap").

**AC-Q04-1** — *Given* a completed CR artifact for the application, *When* the gap prompt is built, *Then* `job_posting['company_research']` is the defined 7-field digest, ≤ 1,200 tokens by the real tokenizer, and the "Company Research Context" block renders.
**AC-Q04-2** — *Given* an oversized CR, *When* the digest is built, *Then* fields drop in the order `recent_news`→`tech_stack`→`interview_signals`→`culture_values` until ≤ cap, and `company_name`/`industry`/`company_size` always survive.
**AC-Q04-3** — *Given* Q-05 recall not yet built, *When* gap runs, *Then* the KB slots are empty/None and the block is a safe no-op; gap request/response wire shape unchanged.

**Done-when:** tests pass; the digest is ≤ cap by the real tokenizer (not `len/4`); AC-Q04-1..3 hold; gap request/response wire shape unchanged (internal-only inputs).

---

## Q-01 — Reorder the artifact chain: Company Research FIRST
**Decision (L-5):** on new-application submit, generate CR **first, to completion**, then gap; CR is reused by all downstream artifacts. Current chain runs `gap → company_research → vpr` (CR after gap), which is *why* gap can't consume CR today.

**Scope note (larger than the localized fixes):** this touches the submit flow + the Step Functions artifact chain / `artifact_dependency` state machine — NOT just `gap_handler`. Treat as its own spec slice with characterization tests of the current chain first. Investigate before designing the GREEN change:
- the SFN chain definition / `artifact_chain_construct` and `artifact_dependency_utils.py` state transitions;
- how CR is currently triggered (async worker) and where gap is enqueued;
- the dependency-resolver gate (`resolve_dependencies`) so gap now declares CR as an upstream dependency.

**CR failure semantics (L-5 rider, v1.5.0/A8 — CR is SOFT-blocking, not hard-blocking):** CR runs first *to completion OR a documented degraded fallback*. On CR `failed` or timeout `> N` seconds (**default `N = 180s`**, matching the SFN heartbeat; tuned via `O-7`), gap proceeds **degraded** with an empty CR block (the prompt builder renders nothing for an absent block — safe no-op, validated in Q-04) and **routes to Haiku, never Sonnet** (Sonnet is paid for the CR-fed lift — running it on empty inputs is the worst cost/quality trade). The application status surfaces CR's failure **additively** via a named status field/enum value that the F-01 oracle confirms the frontend tolerates. This prevents a Tavily/CR-worker outage from stalling every submit behind a dead upstream.

**RED tests to write first (after characterizing current order):**
- `test_chain_runs_cr_before_gap` — drive the chain for a new application; assert CR reaches `completed` before gap generation is invoked (assert ordering via the dependency state / invocation spy).
- `test_gap_receives_completed_cr` — assert that when gap runs, the resolved CR artifact is available and passed into the gap payload (ties to Q-04).
- `test_chain_reorder_is_reversible` — behind a feature flag; flag off → legacy order; flag on → CR-first. (Reversible, flag-gated per guardrails.)
- `test_chain_cr_failure_degrades_not_blocks` — force CR to `failed`; assert gap **still runs** with an empty CR block (does NOT stall/block the chain), the application status surfaces the CR failure additively, and gap routed to **Haiku** (not Sonnet).
- `test_chain_cr_timeout_policy` — hold CR past `N` (=180s) without completing; assert the degraded path triggers at the timeout boundary (gap proceeds degraded + Haiku), NOT a hang; assert the timeout constant is `N`, not an ad-hoc value.

**AC-Q01-1** — *Given* a new-application submit with the CR-first flag on, *When* the chain runs, *Then* CR completes before gap is invoked and gap receives the completed CR (Q-04 digest).
**AC-Q01-2** — *Given* CR `failed` or exceeding `N=180s`, *When* the chain runs, *Then* gap proceeds degraded (empty CR block, routed to Haiku), the chain does NOT stall, and status surfaces the CR failure additively (oracle-confirmed field).
**AC-Q01-3** — *Given* the CR-first flag off, *When* the chain runs, *Then* legacy order is preserved (reversible); `cdk diff` shows zero stateful replacements; downstream artifacts still receive CR; frontend contract unchanged.

**Done-when:** all five tests pass; AC-Q01-1..3 hold; the reorder is flag-gated and reversible; `cdk diff` zero stateful replacements; frontend contract unchanged. **Depends on** `O-2` (CR cache-key granularity) and `O-7` (confirm/tune `N` + the submit→questions latency budget) being resolved first.

---

## Sequencing within Wave 4
1. `Q-02` (real CV) + `Q-03` (Sonnet router) — localized, low-risk, land first.
2. `Q-04` wiring — depends on a CR source being available.
3. `Q-01` chain reorder — the architectural piece; makes CR actually present pre-gap; resolve `O-2` first.
4. `Q-05` KB recall service feeds `Q-04`'s KB slots; `Q-08` eval harness scores `Q-03`.

All land behind flags with characterization tests first; none may weaken a test to pass or alter the gap endpoint's request/response contract.
