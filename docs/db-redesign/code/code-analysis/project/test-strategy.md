# CareerVP — Test Strategy (the safety net)

- **Version:** 1.0.0 · **Created:** 2026-07-09
- **Layer:** sits BELOW the contract, BESIDE the execution plan. Does **not** supersede
  [`project-scope-lock.md`](./project-scope-lock.md) (authority §0.2). It *operationalizes*
  the scope-lock's quality gates (§8) and the coverage-matrix frontend contract (§2) into a
  concrete testing program that every per-spec `TEST-###` file conforms to.
- **Prime directive:** **don't break the UI.** The frontend can't-break contract (scope-lock §3)
  is the invariant every test protects. When a response shape must change, version the route —
  never mutate it.
- **Authored at execution-plan step 0.1.5** — before any spec is scaffolded, because it defines
  the taxonomy, gates, and format those specs' tests must follow.

---

## 1. Philosophy

- **Pyramid, adapted.** Many unit → fewer integration → few e2e. Two CareerVP-specific twists:
  1. **LLM output is evaluated, not covered** — artifact quality is measured by evals (promptfoo +
     golden set + judge@temp0 + FVS + red-team), never by line coverage.
  2. **Legacy code is characterized before it is changed** — the shipped-but-untested routing/gate
     path (where the P-01 defect lives) gets characterization tests capturing *current* behavior at
     `4f7c294` first, so a refactor can't silently change behavior.
- **Coverage is differentiated, not maximized.** 100% is an anti-pattern; gates below are sourced
  from Google/AWS/BullseyeCoverage guidance (scope-lock §8.1).
- **Tests drive real key schemas.** DAL/repository tests run against **moto with the actual live
  key schemas** (`pk/sk`, `applicationId/artifactId`, `job_id`) — hand-mocked dicts are banned;
  they are why the 78.45% line coverage was a vanity metric.
- **Never weaken a test to pass** (scope-lock §9.2). A failing test is a finding, not an obstacle.

---

## 2. Test taxonomy (the 14 types, each mapped to CareerVP)

| # | Type | Purpose | Tooling | Where it applies in CareerVP | "Good" looks like |
|---|---|---|---|---|---|
| 1 | **Unit** | Isolated logic & DAL correctness | pytest + moto (real key schemas) | key-builder/`CoreRepository`, resolver, FVS, circuit breaker, quota/trial math | behavior-focused, no hidden global state (`_SingletonMeta` removed), branch on |
| 2 | **Contract** | Frontend can't-break contract (10 items) | Zod (FE truth) ↔ Pydantic `model_json_schema()`→ajv (BE truth), MSW | every endpoint the FE calls; the 4 live bugs F-02..F-05 | oracle green on all 10 items; `vpr_id: null`-vs-absent preserved |
| 3 | **Characterization** | Pin *current* behavior of legacy before change | pytest against `4f7c294` | the routing/gate/chain path (P-01), god-class before D-M1 split | captures actual output incl. bugs; changes become visible diffs |
| 4 | **Integration (real services)** | Cross-component correctness | moto/local DynamoDB, real SQS/SFN where feasible | submit→SQS→worker→persist; whole-chain-to-persisted-result | asserts ONE stored key, not three; real key schemas |
| 5 | **IaC / CDK** | Infra invariants | `cdk synth` assertions, Checkov, cdk-nag | RETAIN present, per-fn roles, no wildcard IAM, WAF attached, **resource count < 400/template** | synth fails on any invariant breach |
| 6 | **Idempotency / replay** | At-least-once safety | pytest replay harness | billing webhook (provider event id), every worker | replay same event twice → single effect |
| 7 | **Migration-parity** | Safe expand→…→contract | dual-read comparison harness | Track D seams, Wave 6 `core` collapse | legacy read == core read for every item, throttled vs live capacity |
| 8 | **LLM-eval** | Artifact quality & safety | promptfoo + versioned golden dataset + LLM-judge@temp0 + FVS gate + OWASP-LLM red-team | VPR, gap, tailored-CV, cover-letter, interview-prep, ai-assist | passes golden set; FVS ≥ threshold; no prompt-injection escape |
| 9 | **Load / perf** | No self-DoS; capacity | locust/artillery + CloudWatch | API throttle (P-20), concurrency bounds (P-16), bootstrap-latency (D-H8 trigger) | p99 within budget; throttle sized to target; no stampede |
| 10 | **Security / SAST** | No auth/IAM/injection holes | Bandit, CodeQL, pip-audit, gitleaks | cross-tenant IDOR negatives, `x-user-id` bypass, secret scan | zero IDOR; no client-supplied identity path; no secrets in env |
| 11 | **Smoke / canary** | Post-deploy liveness | synthetic canary + CodeDeploy hooks | `/health`, canary deploy gate (P-23) | canary blocks a bad rollout; auto-rollback works |
| 12 | **Mutation** | Validate the tests themselves | `mutmut` spot-check | core generation/orchestration tier | surviving mutants investigated; catches non-asserting tests |
| 13 | **E2E (full)** | Real FE↔BE round-trip | nightly Playwright vs dev | the hub read + a generate flow end to end | matches the contract oracle against a live stack |
| 14 | **Regression** | Nothing already-working breaks | CI gate = unit + contract + characterization on every PR | all of the above, accumulated | the standing suite is green before merge |

---

## 3. Coverage gates (scope-lock §8.1)

| Tier | Line | Branch |
|---|---|---|
| Core generation / orchestration | 85% | 80% |
| Supporting | 78% | 70% |
| Glue | ~60% | excluded |
| LLM output | evals, not coverage | — |
| **CI gate (overall)** | **80%** | **70%** |

Preconditions (Wave-0 step 0.5): **enable branch coverage** (currently 0); **retire the autouse
`mock_artifact_dependency_resolver`/`mock_company_research_load`** (make opt-in), driving real
`resolve_dependencies` against moto real key schemas; add `mutmut` spot-check on core.

---

## 4. The executable oracle (F-01) — how "don't break the UI" is proven

- **FE truth:** Zod mirror of `src/frontend/lib/types.ts` + `safeParse`.
- **BE truth:** Pydantic `model_json_schema()` → ajv.
- **Wiring:** MSW in CI (every changed response validated both directions) + nightly Playwright vs dev.
- **Encodes all 10 contract items (F-06)** as executable assertions, including the load-bearing
  `vpr_id: null`-vs-absent and the 409-on-stale-`base_version`.
- The oracle is a **net that must exist before mass spec authoring** (execution-plan step 0.3).

---

## 5. Characterization-first rule

Before **any** migration or refactor step (Track D, Wave 6, the god-class split), write a
characterization test that captures current behavior at `4f7c294`. The refactor is correct only
when the characterization tests still pass (behavior preserved) or their diffs are the *intended*
change, reviewed and recorded.

---

## 6. Per-wave hard gates (barriers — must be green to advance)

Every wave ends with: `scope-diff.py` clean (no orphan spec, no uncovered clause) · the executable
oracle green on every touched contract item · coverage gate met · the 8+ CI gates green
(ruff · mypy --strict · pytest · cdk synth <400 · Checkov · Bandit · pip-audit · CodeQL ·
oracle · `cdk diff` zero-stateful-replacement). Never parallelize across a gate.

---

## 7. Spec/test format (v1.3.0 — matches the proven exemplar, not a claimed-but-unbuilt convention)

- **Decision (2026-07-09, option B):** the `TEST-###-test-prompts.yaml` copy-paste-prompt format
  was retired — no working example of it existed anywhere, and it contradicted the one real
  exemplar (`specs/Q-gap-analysis-track-spec.md`).
- **Actual format:** one spec = one Markdown file (frontmatter + Problem Statement + Evidence +
  numbered Fix Plan + `AC-###`). **RED-test descriptions (exact test name + exact assertions)
  live inline in the spec body**, under a "RED tests to write first" section — they are the brief
  handed to the implementer, not a standalone artifact.
- **The actual pytest files** are written during the **IMPLEMENT** step, under TDD (write it,
  watch it fail RED, then make it pass GREEN), **in the real `careervp` repo** — never authored
  as a file in this docs project.
- Mandatory spec frontmatter (the join key + tool routing):
  ```yaml
  scope_lock_clause: Q-02
  claude_code: {model: opus, effort: high}
  codex: {model: gpt-5-codex, reasoning: high}
  ```
- Tests come from `src/frontend` calls + CDK `route_map` + handlers — **never** the drifted
  swagger/features docs.

---

## 8. Spec/test acceptance gate (validating the specs & tests themselves)

A spec/test is accepted only when all five pass:
1. **Structural** — `scope-diff.py`: required frontmatter, clause exists, no orphan, no uncovered.
2. **Contract-consistency** — `AC-###` doesn't contradict the clause; `contract_impact: true` →
   carries the frontend-contract slice.
3. **Self-sufficiency** — a fresh subagent given only the spec + clause + named files can implement
   it with zero further questions (if it must ask, the spec is underspecified — reject).
4. **Adversarial refuter** — a second agent tries to break the spec (ambiguity, missing edge cases,
   contradiction). Mandatory for auth/IAM/data specs.
5. **Test-validity** — red-green (fail pre-impl, pass post) + `mutmut` on core + characterization
   proven against `4f7c294`; traceability round-trip (FR → spec → test → clause, both directions).

---

## 9. Outstanding test debt to clear (scope-lock T-01/T-02/T-04)

- Autouse `tests/conftest.py::mock_artifact_dependency_resolver` (+ `mock_company_research_load`)
  neutralizes ~30 handler tests → make **opt-in**; drive real resolver against moto real key schemas.
- Enable branch coverage (currently 0).
- Missing: whole-chain-to-persisted-result · replay idempotency gate (webhook + workers) ·
  `ReportBatchItemFailures` gate · cross-tenant isolation negative · the executable oracle (F-01).
