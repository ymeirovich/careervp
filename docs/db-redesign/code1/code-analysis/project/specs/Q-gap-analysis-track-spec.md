---
spec_id: Q-GAP-TRACK
title: "Gap Analysis fixes — CR-first, real CV, Sonnet, CR/KB wiring"
status: draft
owner: backend
tier: feature
scope_lock_clause: [Q-01, Q-02, Q-03, Q-04]
# per-clause model+effort for both tools (execution-plan convention); this doc = the exemplar
tooling:
  Q-02: {claude_code: {model: sonnet, effort: medium}, codex: {model: gpt-5-codex, reasoning: medium}}  # mechanical
  Q-03: {claude_code: {model: sonnet, effort: medium}, codex: {model: gpt-5-codex, reasoning: medium}}  # mechanical
  Q-04: {claude_code: {model: sonnet, effort: medium}, codex: {model: gpt-5-codex, reasoning: medium}}  # wiring
  Q-01: {claude_code: {model: opus,   effort: xhigh},  codex: {model: gpt-5-codex, reasoning: high}}    # hard: chain reorder
format_note: "copy-paste; follows docs/upgrade/specs convention; RED tests are TDD-first, not optional"
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
3. On `None`/DAL error: return a 404-style error (`cv not found`) — do **not** silently ship the stub; log a warning.
4. Update the call site `gap_handler.py:165` → `_build_user_cv_prompt_payload(user_id=user_id, cv_id=cv_id, focus_areas=focus_areas)`.
- `generate_gap_questions` signature is unchanged (still a dict).

**RED tests to write first (watch fail):**
- `test_gap_payload_is_characterization_stub` — asserts current behavior: payload `full_name == 'Candidate'` and contains `'Current Company'`. (Documents the bug; invert after the fix.)
- `test_gap_loads_real_cv_by_id` — patch `DynamoDalHandler.get_cv_by_id` to return a known `UserCV` (real name + real experience/skills); assert the prompt string passed into the model **contains the real candidate name + a real experience bullet** and **does NOT contain** `'Candidate'`/`'Current Company'`; assert `get_cv_by_id` called with the request's `user_id` + `cv_id`.
- `test_gap_missing_cv_errors_not_stub` — `get_cv_by_id` returns `None` → assert a `cv not found` error response (or logged fallback), never a silent stub.

**Done-when:** the three tests pass; ruff/mypy clean; no frontend-contract change (gap request/response shape unchanged).

---

## Q-03 — Route Gap Analysis to Sonnet (Strategic) via the LLMRouter
**Bug (confirmed):** gap runs on **Haiku**. `gap_analysis.py:283` instantiates the plain `LLMClient()`, `:286` calls `.generate(prompt=...)` with no model; `LLMClient.generate` defaults `DEFAULT_MODEL='claude-haiku-4-5-20251001'` (`llm_client.py:22,99`). It bypasses `LLMRouter`, whose spec classifies Gap as STRATEGIC→Sonnet (`utils/llm_client.py:5-6,39,177-179`).

**Fix (GREEN — Option A, spec-consistent):** in `gap_analysis.py`, replace the plain client with the router:
- import `TaskMode, get_llm_router` from `careervp.logic.utils.llm_client`;
- call `get_llm_router().invoke(mode=TaskMode.STRATEGIC, system_prompt=..., user_prompt=..., max_tokens=4096, temperature=0.3)`;
- feed the returned `.data['text']` into `_extract_questions` (already handles a `{'text':...}` dict). Routing to `SONNET_MODEL_ID` is then automatic, plus router cost caps/metrics.
- (Option B — pass `model_name='claude-sonnet-4-6'` to the plain client — is the fallback if the router migration is deferred; loses cost caps.)

**RED tests to write first:**
- `test_gap_uses_strategic_router` — spy/patch `get_llm_router().invoke`; call `generate_gap_questions`; assert it was invoked with `mode == TaskMode.STRATEGIC` (and NOT the plain `LLMClient.generate`).
- `test_gap_resolves_sonnet_model` — assert the router resolves `TaskMode.STRATEGIC` → `SONNET_MODEL_ID` (guards against a silent Haiku regression).

**Measure the added value (separate, non-blocking):** fixed eval set of ~20–30 (CV, JD) pairs; generate under Haiku vs Sonnet with inputs held constant; rubric + LLM-judge (temp 0) scoring on relevance/specificity/priority-tagging; downstream FVS-lift signal; compare vs ~2¢/run cost delta. Records the "worth it" decision. (See `Q-08` eval harness.)

**Done-when:** both tests pass; the eval harness produces a scored Haiku-vs-Sonnet comparison; margin still `>70%` with the digest inputs from Q-04.

---

## Q-04 — Wire Company Research + KB recall INTO the gap prompt (wiring, not template rewrite — validated)
**Validated:** the **active** builder `create_gap_analysis_user_prompt(user_cv, job_posting)` (`gap_analysis_prompt.py:46`) **already** reads and renders:
- `company_research = job_posting.get('company_research')` → "# Company Research Context" block (`:54,91-97`);
- `recurring_themes` and `previous_gap_responses` (the KB-recall slots).
All three are **unfed** — the handler's `_build_job_prompt_payload` (`gap_handler.py:536-561`) only sets `company_name/role_title/requirements/responsibilities`. So CR-into-gap and KB-into-gap are **wiring jobs** (pass the values through); **no template change** for the active builder. *(Only the unused typed `build_user_prompt` at `:30-38` would need a template change — do not migrate to it as part of this.)*

**Fix (GREEN):**
- CR-into-gap: in `gap_handler.py`, fetch the completed CR for the application (from the shared CR cache/artifact — see Q-01 ordering) and set `job_posting['company_research'] = <digested CR>`. Project via a digest to protect margin (C-2).
- KB-into-gap: set `job_posting['recurring_themes']` and `['previous_gap_responses']` from the `ProfileRecallService` (clause `Q-05`), under the 1,200-token cap. If recall is not yet built, pass empty/None (block renders nothing — safe no-op).

**RED tests to write first:**
- `test_gap_prompt_includes_company_research_when_provided` — provide `job_posting['company_research']`; assert the built prompt contains the "Company Research Context" block content; assert it's ABSENT when not provided.
- `test_gap_prompt_includes_recalled_kb_when_provided` — provide `recurring_themes` + `previous_gap_responses`; assert they render; absent when empty.
- `test_gap_cr_kb_injection_respects_token_cap` — provide oversized CR/KB; assert the injected block is truncated/digested under the cap.

**Done-when:** tests pass; margin guard holds; gap request/response wire shape unchanged (internal-only inputs).

---

## Q-01 — Reorder the artifact chain: Company Research FIRST
**Decision (L-5):** on new-application submit, generate CR **first, to completion**, then gap; CR is reused by all downstream artifacts. Current chain runs `gap → company_research → vpr` (CR after gap), which is *why* gap can't consume CR today.

**Scope note (larger than the localized fixes):** this touches the submit flow + the Step Functions artifact chain / `artifact_dependency` state machine — NOT just `gap_handler`. Treat as its own spec slice with characterization tests of the current chain first. Investigate before designing the GREEN change:
- the SFN chain definition / `artifact_chain_construct` and `artifact_dependency_utils.py` state transitions;
- how CR is currently triggered (async worker) and where gap is enqueued;
- the dependency-resolver gate (`resolve_dependencies`) so gap now declares CR as an upstream dependency.

**RED tests to write first (after characterizing current order):**
- `test_chain_runs_cr_before_gap` — drive the chain for a new application; assert CR reaches `completed` before gap generation is invoked (assert ordering via the dependency state / invocation spy).
- `test_gap_receives_completed_cr` — assert that when gap runs, the resolved CR artifact is available and passed into the gap payload (ties to Q-04).
- `test_chain_reorder_is_reversible` — behind a feature flag; flag off → legacy order; flag on → CR-first. (Reversible, flag-gated per guardrails.)

**Done-when:** tests pass; the reorder is flag-gated and reversible; `cdk diff` shows zero stateful replacements; downstream artifacts (VPR/CV/cover/interview) still receive CR; frontend contract unchanged. **Depends on** open question `O-2` (CR cache-key granularity) being resolved first.

---

## Sequencing within Wave 4
1. `Q-02` (real CV) + `Q-03` (Sonnet router) — localized, low-risk, land first.
2. `Q-04` wiring — depends on a CR source being available.
3. `Q-01` chain reorder — the architectural piece; makes CR actually present pre-gap; resolve `O-2` first.
4. `Q-05` KB recall service feeds `Q-04`'s KB slots; `Q-08` eval harness scores `Q-03`.

All land behind flags with characterization tests first; none may weaken a test to pass or alter the gap endpoint's request/response contract.
