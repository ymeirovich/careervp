# CareerVP Redesign — Execution Plan (ordered runbook)

- **Version:** 1.3.0 · **Created:** 2026-07-05 · **Amended:** 2026-07-09 (v1.1.0 nets-first Wave 0, P-25, P-26, serialization, deviation handling; v1.2.0 homed 6 orphaned clauses P-03/P-13/P-21/T-03/T-04/T-07, O-4 resolved; v1.3.0 retired the TEST-###-test-prompts.yaml format for the proven Q-gap pattern, step 0.4 runs via Workflow)
- **Layer:** sits BELOW the contract, ABOVE the specs. Does **not** supersede
  [`project-scope-lock.md`](./project-scope-lock.md) — the scope-lock wins on any conflict
  (authority §0.2). This plan only *orders* the contract's clauses into copy-paste steps.
- **Purpose:** so you never have to figure out *what* to do or *when*. Run the steps in order.
  Each step names its spec file, its test artifact, the **model + effort for both Claude Code and
  OpenAI Codex**, its dependencies, and its wave gate.

## How to run this

**You (human):** paste `handoff.md`, attach `project-scope-lock.yaml` + this file, say **"begin"**
(or **"continue"**). Then only (1) answer when the agent asks you to decide an open question
(`O-#`), and (2) approve each wave gate. **You do not run steps or load context by hand.**

**The agent self-orchestrates** (this is what keeps context from rotting — it's the agent's job,
not yours): it works the steps top-to-bottom and, **for each step, spawns a FRESH subagent** loaded
with only that step's scope-lock clause (by ID from the YAML) + its spec + the few files it touches.
The orchestrator itself holds only this plan's **status board**, never all 63 clauses. Sessions are
resumable from the board — if one ends, "continue" resumes it.

**Step types** (tells the agent what a row means):
- **SETUP** (`spec: runbook`) — run terminal commands; no spec, no TDD (e.g. 0.1).
- **AUTHOR** — write ONE spec file, from its YAML clause, using `specs/Q-gap-analysis-track-spec.md`
  as the template (frontmatter + Problem Statement + Evidence + numbered Fix Plan + `AC-###` +
  **inline RED-test descriptions** — no separate test-prompt file; see §"Spec/test authoring rules").
- **IMPLEMENT** — open the spec; in the real `careervp` repo, write the RED test(s) it described
  **first** (TDD, watch them fail); then the minimal GREEN code.
- **GATE** (end of each wave) — run `scope-diff.py` (T-09) + the executable oracle (F-01) + coverage/CI.

**Dependencies (`Deps` column):**
- A numeric dep (e.g. `0.6`) = another step that must be `verified` first.
- An **`O-#` dep = an OPEN QUESTION the agent must ask YOU to decide before that step** (it never
  guesses). Your answer is recorded into the scope-lock (O-# → decided). Step **0.0** below makes
  this explicit so it's not a surprise.

**Why a dropped requirement is caught even if a subagent slips** (safety net = on-disk +
deterministic, never attention-based): contract = external memory (clauses re-read by ID); each spec
copies in its own `AC-###` + frontend-contract slice; TDD locks each requirement as a test;
`scope-diff.py` audits every clause for spec/test/impl coverage; the oracle enforces the frontend
contract globally; wave gates re-verify against the contract before advancing.

## Spec/test authoring rules (apply to EVERY spec — v1.3.0, matches the proven exemplar)
- **Decision 2026-07-09 (option B):** the `TEST-###-test-prompts.yaml` format is **retired** — no
  working example of it existed anywhere and it contradicted the one real exemplar.
- **Format:** one Markdown file per spec — YAML frontmatter + Problem Statement + Evidence
  (`file:line`) + Fix Plan (numbered) + `AC-###` Given/When/Then. **RED-test descriptions (exact
  test name + exact assertions) live inline in the spec body** under "RED tests to write first" —
  they are the implementer's brief, not a standalone artifact.
- **The actual pytest files** are written at the **IMPLEMENT** step, under TDD, **in the real
  `careervp` repo** — never in this docs project.
- **Every** spec frontmatter MUST include:
  ```yaml
  scope_lock_clause: Q-02          # the join key for the drift checker
  claude_code: {model: opus, effort: high}     # opus|sonnet ; effort low|medium|high|xhigh
  codex: {model: gpt-5-codex, reasoning: high} # reasoning low|medium|high
  ```
- Specs are **copy-paste**: a fresh subagent executes the Fix Plan + RED tests verbatim, no
  interpretation needed (this is also the §8.6 self-sufficiency acceptance check).

## Model + effort convention (map task-class → both tools)
| Task class | Examples | Claude Code | Codex |
|---|---|---|---|
| **Mechanical** | config/IaC edits (RETAIN, throttle, tags, log retention, SNS sub), prompt-slot wiring, doc updates | `sonnet` / effort **medium** | `gpt-5-codex` / reasoning **medium** |
| **Standard** | handlers, DAL, repositories, most tests, contract/oracle tests | `opus` / effort **high** | `gpt-5-codex` / reasoning **high** |
| **Hard** | single-table `core` migration + classifier + parity, chain reorder, identity surrogate, CFN decomposition, adversarial reviews | `opus` / effort **xhigh** | `gpt-5-codex` / reasoning **high (max)** |

## Concurrency & serialization (v1.1.0; step-0.4 mechanism decided v1.3.0)
- **Spec authoring parallelizes** — each spec is a distinct file; fan out one subagent per clause.
  **Decided (human opt-in, 2026-07-09): step 0.4 runs via the `Workflow` tool**, not a plain
  `Agent`-tool fan-out. Reason: a plain `Agent` call only overrides `model`; it inherits whatever
  effort the session is on, so a batch can't mix e.g. `sonnet/medium` (mechanical specs) with
  `opus/xhigh` (hard specs) in one pass. `Workflow`'s `agent()` helper accepts both `{model, effort}`
  per call, matching the per-clause frontmatter table exactly (`pipeline(clauses, c => agent(authorPrompt(c), {model: c.tooling.model, effort: c.tooling.effort, schema: SPEC_SCHEMA}))`).
  Each clause's `{model,effort}` comes from its own frontmatter/tooling table (see the exemplar +
  the Model+effort convention below) — the workflow script reads it, it isn't hardcoded per clause.
- **Implementation mostly serializes** — most P-clauses edit the same CFN templates. **Rule (scope-lock §9.2, PR block-list §9.3): never let two steps edit the same CFN template file concurrently.** Templates: `api_construct.py`, `api_db_construct.py`, `cognito_construct.py`, `monitoring.py`, `waf_construct.py`. The `Touches` column flags them; run those steps one at a time (or in isolated git worktrees, merged sequentially). Pure-Python/handler/test/doc steps may run in parallel.
- **Wave gates are hard barriers** — never parallelize across a gate.

## Deviation & amendment handling (v1.1.0 — the contract self-heals with human validation)
When any step's subagent **cannot satisfy its clause as written**, or **live truth contradicts a `current_state`**, it does NOT silently deviate. It follows the loop (scope-lock §0.3):
1. **STOP at the clause.** Do not edit the spec to match code; do not weaken a test.
2. **Emit an Amendment Proposal:** `{clause_id, tag (IMMUTABLE/TARGET/OPEN), what changed, why + evidence cite, semver level (patch/minor/major), affected specs/tests}`.
3. **Human validates and confirms** — no auto-apply.
4. On confirm: update **both twins** (MD+YAML) in one commit + §12 change-log row + version bump.
5. **Propagate** to dependent specs/tests, then re-run `scope-diff.py`.
- Amendments to an IMMUTABLE invariant, locked decision, or frontend-contract item require an **adversarial review** first.
- **CI anti-pattern guards** (scope-lock §9.3): `scope-diff.py` fails on a spec contradicting its clause; coverage-drop fails on a weakened test; an amendment with no evidence+decision rationale is rejected.

---

## Ordered steps

> `spec`: TO-AUTHOR = write it first (exemplar + format above); AUTHORED = file exists.
> `status`: `not_started | spec_written | test_written | implemented | verified`.

### Wave 0 — Guardrails & truth (do first; unblocks everything) — **NETS BEFORE SCAFFOLDING**
> Reordered v1.1.0: the drift nets (`scope-diff.py` 0.2, oracle 0.3) are built **before** mass spec
> authoring (0.4), so a mis-authored spec is caught the moment it's written — not steps later.
> `touches` flags CFN-template files → those steps run **serially** (never parallel-edit one template).

| # | Clause(s) | Step | Spec / test | Claude | Codex | Deps | Touches | Status |
|---|---|---|---|---|---|---|---|---|
| 0.0 | O-1..O-6 | **Agent asks the human to decide the open questions that block near-term steps** (O-4 blocks 0.7; O-2 blocks the KB steps). Record each answer into the scope-lock (O-# → decided). O-1, O-5 (Wave 6) and O-3, O-6 may stay open until their wave. | runbook | — | — | — | — | not_started |
| 0.1 | — | Re-clone `github.com/ymeirovich/careervp @ 4f7c294`; **anchor confirmation** (`git rev-parse HEAD == 4f7c294`, else re-anchor via amendment); Py≥3.13+uv; baseline `recon.py --env dev` (confirm no drift vs findings-register live section) | runbook | sonnet/med | codex/med | — | — | not_started |
| 0.1.5 | T-04 | **Author `test-strategy.md`** (taxonomy, coverage gates, oracle design, characterization-first, per-wave gates, spec/test acceptance gate). Defines what every `TEST-###` conforms to (id-homes **T-04**). | `test-strategy.md` (AUTHORED) | opus/high | codex/high | 0.1 | — | not_started |
| 0.1.6 | P-03 | **Map the `/api/*` surface** — enumerate from CDK route_map + staging export; grep `src/frontend` (expect zero); tag each path carry\|drop; assert `/api/*` absent from dev/prod synth | `specs/P-03-api-surface-spec.md` (TO-AUTHOR) | sonnet/med | codex/med | 0.1 | — | not_started |
| 0.2 | T-09, T-07, T-06 | **NET:** author `scope-diff.py` (clause↔spec↔test↔impl checker); **wire the 8 CI gates** (ruff·mypy --strict·pytest·cdk synth<400·Checkov·Bandit·pip-audit·CodeQL) + scope-diff + oracle (**T-07**); author the **spec-coverage ledger** | `TEST-INFRA-diff`, `specs/spec-coverage-ledger.md` | opus/high | codex/high | 0.1.5 | — | not_started |
| 0.3 | F-01 | **NET:** executable oracle skeleton (Zod mirror of `lib/types.ts` + Pydantic `model_json_schema()`→ajv + MSW) | `specs/F-frontend-oracle-spec.md` | opus/high | codex/high | 0.1.5 | — | not_started |
| 0.4 | T-06 | **Scaffold all spec files** (TO-AUTHOR list below) — now checked by the nets on write; fan-out-safe (one subagent per clause, distinct files) | per-clause `specs/*.md` | opus/high | codex/high | 0.2, 0.3 | — | not_started |
| 0.5 | T-01, T-02, T-03 | Enable branch coverage; make autouse `mock_artifact_dependency_resolver`/`mock_company_research_load` opt-in; moto real key schemas; **wire the differentiated coverage gates** (core 85/80, supporting 78/70, overall 80/70 — **T-03**) | `TEST-DEBT-cov` | opus/high | codex/high | 0.1 | — | not_started |
| 0.6 | P-12, P-13 | RETAIN + deletion_protection on all stateful (the smallest safe first slice); **remove dead RETAIN stacks never instantiated** (**P-13**) | `specs/P-12-retain-spec.md` | sonnet/med | codex/med | 0.1 | `api_db_construct.py`, `app.py` (serial) | not_started |
| 0.63 | P-21 | **SNS alarms → subscribed on-call topic** (currently 0 subscribers) — pre-migration gate | `specs/P-21-sns-subscribers-spec.md` (TO-AUTHOR) | sonnet/med | codex/med | 0.1 | `monitoring.py` (serial) | not_started |
| 0.65 | P-26 | **CFN nested-stack decomposition** — nest the whole `RestApi` (~175 API-GW resources → 1) + feature Lambdas into per-feature nested stacks; props not `Fn::ImportValue`. **Before any additive wave.** Verify frontend still resolves the invoke URL (retained logical id or custom domain+ACM). | `specs/P-26-cfn-decomposition-spec.md` (TO-AUTHOR) | opus/xhigh | codex/high(max) | 0.6 | `api_construct.py`, `app.py` (serial) | not_started |
| 0.7 | P-24 | Identity surrogate `user_id` scaffolding + `sub→user_id` resolution (conservative link-by-verified-email default until O-4 decided) | `specs/P-24-identity-surrogate-spec.md` | opus/xhigh | codex/high | 0.65, O-4 | `cognito_construct.py`, authorizer (serial) | not_started |

### Wave 1 — Security/auth launch-blockers
| # | Clause(s) | Step | Claude | Codex | Deps |
|---|---|---|---|---|---|
| 1.1 | P-04, P-05 | Remove `x-user-id`/`AUTHORIZER_DISABLED`; enforce owner check (IDOR) | opus/high | codex/high | 0.7 |
| 1.2 | P-06 | Secrets → SSM/Secrets Mgr | sonnet/med | codex/med | 0.1 |
| 1.3 | P-07, P-08, P-10, P-11 | Cognito MFA; CORS lock (bucket + API GW); WAF+rate rule all envs | sonnet/med | codex/med | 0.1 |
| 1.4 | P-09 | One IAM role per fn (retire shared role) | opus/high | codex/high | 0.1 |
| 1.5 | P-22 | OIDC in `cdk-diff.yml` | sonnet/med | codex/med | 0.1 |

### Wave 2 — Reliability / money
| # | Clause(s) | Step | Claude | Codex | Deps |
|---|---|---|---|---|---|
| 2.0 | P-25 | **Payment-provider port + `MockProvider`** (checkout/portal/verify-webhook/fetch-subscription/list-events). Mock signs test webhooks + returns realistic objects; preserves FE checkout/portal URL contract. All 2.1+ billing codes against the port. `StripeProvider` deferred (config swap). | opus/high | codex/high | 1.* |
| 2.1 | P-14, P-15 | Idempotency wired (webhook + workers, via the port's event id); kill money-path Scan (customer-id → GSI) | opus/high | codex/high | 2.0 |
| 2.2 | P-16, P-17, P-18 | Concurrency bounds; `ReportBatchItemFailures`; visibility ≥6× | sonnet/med | codex/med | 0.1 |
| 2.3 | P-19 | SFN retry/heartbeat/JitterStrategy FULL | sonnet/med | codex/med | 0.1 |
| 2.4 | P-20 | Raise API throttle | sonnet/med | codex/med | 0.1 |
| 2.5 | P-23, P-02 | Alias+version + CodeDeploy canary; fix billing-reconcile handler | opus/high | codex/high | 0.1 |

### Wave 3 — DB seams (fixes the actual break P-01)
| # | Clause(s) | Step | Claude | Codex | Deps |
|---|---|---|---|---|---|
| 3.1 | D-H2, D-H3 | Single key-authority repository; surface ValidationException | opus/high | codex/high | 0.6 |
| 3.2 | D-H4, P-01 | Stored canonical `artifact_id` + resolved upstreams → fixes cover-letter/interview-prep | opus/high | codex/high | 3.1 |
| 3.3 | D-H7 | Eliminate request-path Scans | opus/high | codex/high | 3.1 |
| 3.4 | D-M1, D-M2, D-M3, D-M5, D-M6, D-Q | God-class split; stop dual-key CV write; minimized GSI; retire userEmail PK; access-pattern doc; quick wins | opus/high | codex/high | 3.1 |

### Wave 4 — Generation quality (Track Q + frontend fixes)
| # | Clause(s) | Step | Spec | Claude | Codex | Deps |
|---|---|---|---|---|---|---|
| 4.1 | Q-02 | Gap real-CV injection | `specs/Q-gap-analysis-track-spec.md` (AUTHORED) | sonnet/med | codex/med | 3.2 |
| 4.2 | Q-03 | Gap → Sonnet via router | same | sonnet/med | codex/med | 4.1 |
| 4.3 | Q-04 | Wire CR + KB into gap prompt | same | sonnet/med | codex/med | 4.1, 4.6 |
| 4.4 | Q-01 | Reorder chain: CR first | same | opus/xhigh | codex/high | 3.*, O-2 |
| 4.5 | Q-07, Q-09 | Recreate knowledge-table on `user_id` key; CR margin guard | TO-AUTHOR | sonnet/med | codex/med | 0.7 |
| 4.6 | Q-05 | Cross-app KB recall (MVP, DynamoDB) | `specs/Q-05-knowledge-base-spec.md` (TO-AUTHOR) | opus/high | codex/high | 3.1, O-2 |
| 4.7 | Q-08 | LLM eval harness (promptfoo + golden set) | TO-AUTHOR | opus/high | codex/high | 4.2 |
| 4.8 | F-02..F-06 | Fix the 4 live contract bugs; encode 10 contract items as assertions | `specs/F-contract-fixes-spec.md` (TO-AUTHOR) | opus/high | codex/high | 0.5 |

### Wave 5 — Cost/observability + Tier-2 tail
| # | Clause(s) | Step | Claude | Codex | Deps |
|---|---|---|---|---|---|
| 5.1 | CMK, field-PII, X-01 | CMK on Dynamo/S3; field-level PII encryption; account-close delete-all | opus/high | codex/high | 3.* |
| 5.2 | Tier-2 obs | Log retention, alarms, tagging, request validators | sonnet/med | codex/med | 0.1 |
| 5.3 | low-effort/high-value | ARM64, minimized GSI, dead-resource deletion, F-07 | sonnet/med | codex/med | — |
| 5.4 | T-05 | mutmut mutation spot-check on core | sonnet/med | codex/med | 3.* |

### Wave 6 — Committed, gated (post-launch)
| # | Clause(s) | Step | Claude | Codex | Deps |
|---|---|---|---|---|---|
| 6.1 | D-H8, D-H6 | Full single-table `core` collapse (expand→dual-write→backfill→dual-read→contract) | opus/xhigh | codex/high | O-1, O-5, all Wave 3 |
| 6.2 | Q-06 | KB Phase 2 — S3 Vectors (swap ranker only) | opus/high | codex/high | 4.6, O-6 |

---

## Specs still TO-AUTHOR (Wave-0 step 0.4 produces these; Gap spec is the exemplar)
Track P: P-03 (api-surface), P-12, P-13, P-21 (SNS), P-24, **P-25 (payment port + mock)**, **P-26 (CFN decomposition)**, P-04/05 (auth), P-09 (IAM), P-14/15 (money), P-17/18/19 (reliability), P-23.
Track D: D-H2/H3/H4, D-H7, D-M*, D-H8. Track Q: Q-05 (KB), Q-07, Q-08. Track F: F-01 (oracle),
F-02..F-06 (contract). Track T: spec-coverage-ledger, scope-diff. Track X: X-01.
Each carries model/effort in its frontmatter; RED-test descriptions inline (v1.3.0 — no separate test-prompt file).

## Traceability (how specs/tests stay true to production — clause T-09)
`scope-diff.py` reads `project-scope-lock.yaml` and, for each `backlog[].id`, resolves:
`spec_exists? test_exists? impl_state?` by scanning spec/test frontmatter for `scope_lock_clause`.
Outputs: coverage (clauses with no spec), scope-creep (specs with no clause), and a status board
mirroring this plan's `status` columns. Runs in CI + on demand = your periodic drift diff.
