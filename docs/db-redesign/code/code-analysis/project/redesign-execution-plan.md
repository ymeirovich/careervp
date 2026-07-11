# CareerVP Redesign — Execution Plan (ordered runbook)

- **Version:** 2.0.0 · **Created:** 2026-07-05 · **Amended:** 2026-07-11 (v1.1.0 nets-first Wave 0, P-25, P-26, serialization, deviation handling; v1.2.0 homed 6 orphaned clauses + O-4; v1.3.0 retired TEST-###-test-prompts.yaml for the Q-gap pattern + Workflow step 0.4; v1.4.0 added 9 gap-fill clauses P-27..P-32/Q-10/Q-11/X-02; **v2.0.0 applied the eval-council conditions — P-26 blue/green rewrite (0.65) + deploy-safety dependency wiring (0.6←0.61/0.62), Q-02 validation gate (0.35) before mass fan-out, F-06 folded into the oracle (0.3), budgets slice + Q-10 metering + RTO fire-drill pulled to Wave 0, P-23 first + step-1.3 CORS split + 31-handler table in Wave 1, D-H9 + parity harness in Wave 3, CR margin guard before CR-first reorder in Wave 4, deduped TO-AUTHOR list, operator safe-pause addendum**)
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

**Human-throughput budget (v2.0.0 — the unmodeled critical resource is *your* approval bandwidth):**
the solo human owns four recurring duties (O-# decisions, wave gates, every `ExecuteChangeSet`, every
amendment) — and Wave 0 alone front-loads ~2 opus/xhigh deploys + ~20 spec acceptances (each with a
mandatory refuter for auth/IAM/data). To avoid the "tired approver rubber-stamps" failure mode:
**batch the refuter output for one review sitting per wave**, and treat a per-wave human-touch count
as a real budget line, not a footnote. If a spec is rejected twice, escalate its `{model,effort}`
rather than re-authoring blind.

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
- Specs are **self-sufficient**: a fresh subagent given only the spec + clause + named files can
  implement it with **zero open questions** — enforced by the §8.6 gate-3 `questions: []` dry-run.
  For most (localized) clauses this means the Fix Plan + RED tests run verbatim. **A hard clause may
  legitimately carry an explicit *investigation brief*** (e.g. Q-01's "characterize the current SFN
  chain first, then design the GREEN change") — that is still self-sufficient (the brief names
  exactly what to investigate and where), it is just not literally copy-paste. "Self-sufficient" is
  the real bar; "copy-paste" was an overstatement for the hard clauses.

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

## Operator continuity & safe pause (v2.0.0 — bus factor 1 by design)
This is a solo program with human-only execute gates, so it can stop at any time. **Safe-pause rule: never stop mid-deploy.** The dangerous state is a partially-executed change set with the P-27 stack policy relaxed (e.g. mid-P-26-retire) — that is the worst place to walk away. Before pausing:
1. Finish or roll back any in-flight `ExecuteChangeSet` — never leave a stack in `UPDATE_IN_PROGRESS`/`UPDATE_ROLLBACK_FAILED`.
2. **Reinstate the P-27 stack policy** if it was lifted for a retire/replace step.
3. Confirm the status board reflects the true last-`verified` step (the board is the resume memory).
4. Leave no half-applied CORS/auth flip on a live wave (each 1.x sub-step is individually revertible — land on a boundary).
Resume by re-pasting `handoff.md` + attachments and saying "continue".

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
| 0.3 | F-01, **F-06** | **NET:** executable oracle (Zod mirror of `lib/types.ts` + Pydantic `model_json_schema()`→ajv + MSW) **carrying all 10 contract items as executable assertions (F-06 folded in here — v2.0.0/A11, no longer deferred to Wave 4)**, incl. the behavioral legs `vpr_id: null`-vs-absent and 409-on-stale-`base_version` — so a Wave-3 contract-touching change can't pass a "green" oracle that simply has no assertion for the touched item | `specs/F-frontend-oracle-spec.md` | opus/high | codex/high | 0.1.5 | — | not_started |
| 0.35 | Q-02 | **GATE — pattern-validation experiment (v2.0.0/A11, blocks 0.4):** run ONE full author→IMPLEMENT red-green cycle against the existing `Q-gap` exemplar's Q-02 slice (write the RED tests in the real repo, watch fail, minimal GREEN, watch pass) **before** mass spec fan-out. If the exemplar pattern doesn't hold on a real cycle, fix the exemplar/§8.5-§8.6 before authoring ~20 more specs in its image. | `specs/Q-gap-analysis-track-spec.md` (Q-02) | sonnet/med | codex/med | 0.3 | — | verified |
| 0.4 | T-06 | **Scaffold all spec files** (TO-AUTHOR list below) — now checked by the nets on write; fan-out-safe (one subagent per clause, distinct files). **Blocked on 0.35 passing.** | per-clause `specs/*.md` | opus/high | codex/high | 0.2, 0.3, 0.35 | — | verified |
| 0.5 | T-01, T-02, T-03 | Enable branch coverage; make autouse `mock_artifact_dependency_resolver`/`mock_company_research_load` opt-in; moto real key schemas; **wire the differentiated coverage gates** (core 85/80, supporting 78/70, overall 80/70 — **T-03**) | `TEST-DEBT-cov` | opus/high | codex/high | 0.1 | — | not_started |
| 0.55 | P-27, P-28 | **Deploy-safety gates + CI pipeline closure (human-run, "5-min-today", BEFORE any change set):** CFN stack policy (deny Replace/Delete on RestApi/DynamoDB/S3/Cognito/nested) + termination protection (**P-27**); automation read-only + `CreateChangeSet`-only, **human-only `ExecuteChangeSet`**, hard-pin account/region in `app.py`; **branch-protect `main` + a GitHub deployment environment with a required human reviewer + `concurrency: group=deploy, max=1` WITHOUT `cancel-in-progress`; the approval artifact = the machine-parsed `DescribeChangeSet` Replacement report, auto-fail on `Replacement:True` for RestApi/Table/Bucket/UserPool** (**P-28**, v2.0.0/A2 — else the human-only execute gate is decorative) | `specs/P-27-cfn-stack-policy-spec.md`, `specs/P-28-deploy-identity-spec.md` (TO-AUTHOR) | sonnet/med | codex/med | 0.1 | `app.py`, stack config (serial) | not_started |
| 0.56 | P-32 (budgets slice) | **AWS Budgets + Cost-Anomaly Detection (human console task, alongside P-27 — v2.0.0/A11):** a retry-storm/runaway-chain must not burn unbounded LLM spend unmonitored through Waves 0–4 while the known duplicate-AI-spend defect (#18) is unfixed until Wave 2. (Tagging/correlation-ID/validators stay in Wave 5's P-32 remainder.) | `specs/P-32-budgets-slice-spec.md` (TO-AUTHOR) | sonnet/med | codex/med | 0.1 | — | not_started |
| 0.61 | P-29 | **Pre-deploy evidence snapshot pack** (golden-state capture) + on-demand DynamoDB backups + external S3 sync of the unversioned upload bucket. **Runs BEFORE deploy #1 (v2.0.0/A11+F6): re-dep'd on 0.55, not 0.6 — the golden "before" must exist before the first RETAIN flip.** | `specs/P-29-evidence-pack-spec.md` (TO-AUTHOR) | sonnet/med | codex/med | 0.55 | — | not_started |
| 0.62 | P-30 | **4-wire deploy smoke harness** (health · OPTIONS+GET exact-origin · authed read · presigned upload); **baseline green BEFORE deploy #1 (re-dep'd on 0.55)** | `specs/P-30-smoke-harness-spec.md` (TO-AUTHOR) | opus/high | codex/high | 0.55 | — | not_started |
| 0.63 | P-21 | **SNS alarms → subscribed on-call topic** (currently 0 subscribers) — pre-migration gate | `specs/P-21-sns-subscribers-spec.md` (TO-AUTHOR) | sonnet/med | codex/med | 0.55 | `monitoring.py` (serial) | not_started |
| 0.6 | P-12, P-13 | RETAIN + deletion_protection on all stateful (the smallest safe first slice — **deploy #1**); **remove dead RETAIN stacks never instantiated** (**P-13**). **Now gated on evidence pack + smoke baseline (deps 0.61, 0.62) so the discipline starts at deploy #1.** | `specs/P-12-retain-spec.md` | sonnet/med | codex/med | 0.55, 0.61, 0.62 | `api_db_construct.py`, `app.py` (serial) | not_started |
| 0.64 | — | **Rollback fire-drill (v2.0.0/A11):** incremental redeploy RTO is **already measured ≈7 min (2026-07-11 recon; CFN update ~67–83s + CI overhead)** — the remaining value here is to measure the **from-scratch recreate** case (the P-26 blue/green scenario, which couldn't be measured from expired events). Write both numbers down. | runbook | — | — | 0.6, 0.61, 0.62 | — | not_started |
| 0.64b | P-26 (domain slice), O-9 | **Custom domain + DNS foundation — the P-26 repoint precondition (v2.1.1).** *(a) CDK (AUTHOR/IMPLEMENT):* per-env, endpoint type **REGIONAL** — ACM cert `api.{env}.careervp.com` (`us-east-1`, DNS-validated), `AWS::ApiGateway::DomainName`, `AWS::ApiGateway::BasePathMapping` → RestApi+stage. *(b) MANUAL in Cloudflare (human — DNS is external, NameCheap+Cloudflare):* add the ACM validation CNAME, then a CNAME `api.{env}` → the API-GW regional target domain, **both "DNS only" / grey-cloud (never proxied)**. Request+validate the cert FIRST, then reference its ARN in CDK so the deploy doesn't block. *(c)* **Fix the broken `Deploy Frontend` workflow (O-9, failing since 2026-05-03)** — it was still a static S3/CloudFront export while the real frontend is Amplify SSR. *(d)* Repoint `NEXT_PUBLIC_API_URL` → `https://api.{env}.careervp.com`, rebuild, P-30 smoke. **Evidence received 2026-07-11:** `dev` cert ISSUED (`arn:aws:acm:us-east-1:788159322332:certificate/d93bafb3-fe1a-4faa-9335-a9e868646bdb`); `dig +short api.dev.careervp.com` resolves to `d-ufdp03t4f1.execute-api.us-east-1.amazonaws.com.`; Amplify env var set to `https://api.dev.careervp.com` and redeployed green. **Remaining:** fixed GitHub Deploy Frontend workflow green + P-30 smoke through the custom domain. | `specs/P-26-cfn-decomposition-spec.md` (domain slice; TO-AUTHOR at 0.4) | opus/high | codex/high | 0.62 | `api_construct.py`, `app.py` (serial) | in_progress |
| 0.65 | P-26 | **CFN decomposition + safe blue/green API migration (v2.0.0/A1 — NEVER move the RestApi in place)** — decompose *around* the `RestApi` (feature Lambdas/alarms → per-feature nested stacks). If API-GW count must shrink: (1) **custom domain + ACM first** (`us-east-1` cert for edge-optimized; ordered cert→DNS-validate→domain→base-path-map to OLD api→Route53→await propagation→**then** Amplify rebuild+repoint — a named, gated cross-C-6 frontend deliverable, not a trivial env poke); (2) **NEW `RestApi` in its OWN stack** (never in the 415/500 parent), verify via P-30 4-wire against its raw invoke URL; (3) **human-only base-path/domain flip**; (4) **retire old API in a later gated deploy — requires a human-gated `SetStackPolicy` to lift P-27 on that one delete, then reinstate** (and break any CDK Export/`ImportValue` locks first). **Precondition: read the P-29 evidence pack to confirm what `NEXT_PUBLIC_API_URL` resolves to** (recon: `api.dev.careervp.com` DNS is **dead**, so it's almost certainly the raw `execute-api` URL). **⚠️ Blocked by O-9: the frontend-CI deploy pipeline is broken (since 2026-05-03) — fix it first, or the repoint can't happen; wire the custom-domain DNS + base-path-mapping IN CDK.** **Do NOT move the Cognito pool.** **Before any additive wave.** | `specs/P-26-cfn-decomposition-spec.md` (TO-AUTHOR at 0.4 — the domain slice + the decomposition; **do not author now, author in the step-0.4 fan-out**) | opus/xhigh | codex/high(max) | 0.64b, 0.6, 0.61, 0.62, 0.63, 0.64 | `api_construct.py`, `app.py` (serial) | not_started |
| 0.7 | P-24 | Identity surrogate `user_id` scaffolding + `sub→user_id` resolution (conservative link-by-verified-email default; O-4 decided). **Do NOT move the Cognito pool** (P-26/P-24 shared exclusion). | `specs/P-24-identity-surrogate-spec.md` | opus/xhigh | codex/high | 0.65, 0.62, O-4 | `cognito_construct.py`, authorizer (serial) | not_started |
| 0.75 | Q-10 | **Real token metering** (retire `len/4`) + cost-per-app metric + anomaly alarm — **pulled from Wave 2 (v2.0.0/A11): pure-Python instrumentation, no payment-port dep; a measured margin baseline must accrue before the Wave-4 Sonnet decisions (Sonnet-5 intro-pricing deadline 2026-08-31).** Tag traffic origin (dev-eval vs product) + measure prompt-cache hit-rate (live `llm-cache` is at 0 items — the cache offset in the ~88% estimate currently delivers nothing). **Record a `PRICE_PER_APP` constant (v2.0.0 Layer-2 item 2 — the C-2 ">70% margin" gate has a cost numerator but NO revenue denominator anywhere, so the check is currently uncomputable) and derive the anomaly-alarm threshold from it (`cost-per-app > 0.30 × PRICE_PER_APP ⇒ alarm`). ⚠️ The actual price/plan-revenue number is a HUMAN INPUT — the spec author must ask, not guess it.** | `specs/Q-10-token-metering-spec.md` (TO-AUTHOR) | opus/high | codex/high | 0.1 | — | not_started |

### Wave 1 — Security/auth launch-blockers
> **Resequenced v2.0.0 (A4/A5/F-SEC-4):** P-23 (a real rollback lever) lands FIRST, before the P-04 auth flip; step 1.3 is split so the CORS blast radius isn't one "mechanical" sweep; P-07's SPA-client grant-flow cutover is sequenced ahead of P-04.

| # | Clause(s) | Step | Claude | Codex | Deps |
|---|---|---|---|---|---|
| 1.0 | P-23 | **FIRST — canary/alias + CodeDeploy rollback + the alarms P-04 depends on.** Alias+version + CodeDeploy canary; **plus a P-24 resolver-failure metric + a per-outcome auth alarm (NOT aggregate 401-rate — a mis-resolved `sub` can 401 like a benign token-expiry OR serve wrong-tenant 200s) + a synthetic canary asserting a known `sub` resolves to its expected `user_id`.** Note the correct revert lever *per artifact*: a CodeDeploy canary rolls back Lambda code/config, NOT an API-GW authorizer/`authorizationType` change — that revert is a stage-level API-GW redeploy. | opus/high | codex/high | 0.7 |
| 1.1 | P-04, P-05 | Remove `x-user-id` fallback + delete dead `AUTHORIZER_DISABLED` env var; enforce owner check (IDOR). **P-04 recon-simplified (2026-07-11): Cognito auth is ALREADY enforced in dev and `AUTHORIZER_DISABLED` is dead config — so P-04 is delete-only cleanup, not a risky enforcement flip.** The remaining handler change (x-user-id fallback removal) is a Lambda change → P-23 canary IS the right lever for it (the API-GW authorizer is already on and untouched). Alarm on P-24 resolver-failure signals, not aggregate-401. **P-05 (A5/F-SEC-1): the spec MUST carry an exhaustive route×handler table for all ~31 handlers (from CDK `route_map`) with a per-handler owner-check assertion, and a parametrized cross-tenant negative over EVERY authenticated route** (the future spec-author subagent produces the table from the live route_map — do not enumerate from stale docs). **Sequencing: P-07's SPA-client grant-flow cutover + soak (1.3c) must be complete before this enforcement flip** (stale implicit-flow tokens must not meet newly-strict auth mid-migration). | opus/high | codex/high | 1.0 |
| 1.2 | P-06 | Secrets → SSM/Secrets Mgr | sonnet/med | codex/med | 0.1 |
| 1.3a | P-08 | **CORS pilot — CV bucket `*` → locked origins (seconds-scale revert).** Land first as the low-blast-radius pilot before touching API-GW CORS. | sonnet/med | codex/med | 0.1 |
| 1.3b | P-10 | **API GW CORS `ALL_ORIGINS` → allow-list.** Preconditions: runtime OPTIONS+GET exact-origin preflight probe green (P-30 wire), a **pre-staged inverse change set**, `max-age → 60s` first. **Keep the `GatewayResponse` ACAO `'*'` as a codified exception** (tightening it makes every 401 CORS-opaque → kills contract §10's 401→refresh→sign-out). **Fix the poisoned `cors-no-wildcard.regression.test.ts` before any spec fan-out depends on it.** | sonnet/med | codex/med | 1.3a |
| 1.3c | P-07, P-11 | Cognito MFA (rolled **optional→enforced** with an enrollment grace window) + **SPA-client hardening: `implicit_code_grant`→auth-code+PKCE and remove `COGNITO_ADMIN`** (A5 — verify no live self-service flow uses the scope FIRST; dual-flow migration window, cut `src/frontend` over FIRST then remove implicit; **this whole cutover must complete + soak before 1.1's P-04 flip**); WAF+rate rule all envs. | sonnet/med | codex/med | 0.1 |
| 1.4 | P-09 | One IAM role per fn (retire shared role) | opus/high | codex/high | 0.1 |
| 1.5 | P-22 | OIDC in `cdk-diff.yml` | sonnet/med | codex/med | 0.1 |

### Wave 2 — Reliability / money
| # | Clause(s) | Step | Claude | Codex | Deps |
|---|---|---|---|---|---|
| 2.0 | P-25 | **Payment-provider port + `MockProvider`** (checkout/portal/verify-webhook/fetch-subscription/list-events). **Mock's `verify_webhook` MUST implement a real HMAC check that REJECTS a tampered signature** (v2.0.0/A6 — so the negative test is meaningful, not tautological); preserves FE checkout/portal URL contract. All 2.1+ billing codes against the port. | opus/high | codex/high | 1.* |
| 2.0b | P-25b | **Real `StripeProvider` + signature verification + idempotency negative test — freeze-line, before any *paid* launch** (v2.0.0/A6). Not "deferred, swap later": a paid launch (L-4) must not run untested signature-verification code on the money path. | opus/high | codex/high | 2.0 |
| 2.1 | P-14, P-15 | Idempotency wired (webhook + workers, via the port's event id); kill money-path Scan (customer-id → GSI) | opus/high | codex/high | 2.0 |
| 2.2 | P-16, P-17, P-18 | Concurrency bounds; `ReportBatchItemFailures`; visibility ≥6× | sonnet/med | codex/med | 0.1 |
| 2.3 | P-19 | SFN retry/heartbeat/JitterStrategy FULL | sonnet/med | codex/med | 0.1 |
| 2.4 | P-20 | Raise API throttle. **Fold in a minimal load/perf harness (v2.0.0 Layer-2 item 3): a locust smoke — hub read + one generate flow, p99 assert — so the throttle target is sized from data, not guessed; emit bootstrap-latency so O-1's D-H8 go/no-go metric actually gets measured (via P-32's correlation-ID/metrics work).** | sonnet/med | codex/med | 0.1 |
| 2.5 | P-02 | Fix billing-reconcile handler (`Handler` ≠ `lambda_handler`). *(P-23 canary moved to Wave 1 step 1.0.)* | opus/high | codex/high | 0.1 |
| 2.7 | P-31 | EventBridge rule targets get a DLQ (cleanup 1h, reconcile 02:00) | sonnet/med | codex/med | 0.1 |
> *(Q-10 real token metering moved to Wave-0 step 0.75 — no payment-port dependency, and a measured baseline must precede the Wave-4 Sonnet decisions.)*

### Wave 3 — DB seams (fixes the actual break P-01)
| # | Clause(s) | Step | Claude | Codex | Deps |
|---|---|---|---|---|---|
| 3.1 | D-H2, D-H3 | Single key-authority repository; surface ValidationException. **Also build the reusable dual-read migration-parity harness here (v2.0.0/A14) — the key-authority chokepoint; reused by 3.2/3.4/3.5.** | opus/high | codex/high | 0.6 |
| 3.2 | D-H4, P-01 | Stored canonical `artifact_id` + resolved upstreams → fixes cover-letter/interview-prep. **Migration-parity gated (A14): every pre-migration `artifact_id` must still resolve via the status endpoint post-cutover (dual-read until contract phase); legacy-id probe in the oracle.** | opus/high | codex/high | 3.1 |
| 3.3 | D-H7 | Eliminate request-path Scans | opus/high | codex/high | 3.1 |
| 3.4 | D-M1, D-M2, D-M3, D-M5, D-M6, D-Q | God-class split; stop dual-key CV write; minimized GSI; retire userEmail PK; **access-pattern doc (D-M6 now proves every §1a endpoint + §1b/§1c async maps to a named Query/GSI, zero Scan, incl. status-by-`artifact_id` + sparse in-flight index — hard dep of D-H8)**; quick wins. D-M2/D-M5 migration-parity gated. | opus/high | codex/high | 3.1 |
| 3.5 | D-H9 | **Complete the in-flight FE-UI-044 CR canonical-store migration (v2.0.0/A10):** verify backfill of the 239 legacy items, confirm dual-read parity (harness from 3.1), retire the legacy `users-table` CR read path — closes the dual-read-fallback family that is the root of the P-01 drift. | opus/high | codex/high | 3.1 |

### Wave 4 — Generation quality (Track Q + frontend fixes)
| # | Clause(s) | Step | Spec | Claude | Codex | Deps |
|---|---|---|---|---|---|---|
| 4.1 | Q-02 | Gap real-CV injection | `specs/Q-gap-analysis-track-spec.md` (AUTHORED) | sonnet/med | codex/med | 3.2 |
| 4.2 | Q-03 | Gap → Sonnet via router. **MUST NOT enable in prod until Q-10 metering (0.75) exists to measure cost-per-gap; default Haiku until then (v2.0.0/A13).** | same | sonnet/med | codex/med | 4.1, 0.75 |
| 4.3 | Q-04 | Wire CR + KB into gap prompt. **The CR digest is defined in the exemplar (field list + explicit token cap + counting method), not `<digested CR>` (v2.0.0).** | same | sonnet/med | codex/med | 4.1, 4.6 |
| 4.4 | Q-01 | Reorder chain: CR first. **CR is soft-blocking (A8): on CR fail/timeout > N (default 180s, O-7) gap proceeds degraded with an empty CR block AND routes to Haiku, never Sonnet; status surfaces CR failure additively (named enum/field, oracle-checked). Depends on the CR margin guard (4.5) landing first so the ~15k-token CR ingest is truncated before submit volume multiplies it.** | same | opus/xhigh | codex/high | 3.*, 4.5, O-2, O-7 |
| 4.5 | Q-07, Q-09 | Recreate knowledge-table on `user_id` key; **CR margin guard (Q-09 truncation / `include_raw_content:false`) — pulled ahead of 4.4 (v2.0.0/cost-F7) so CR volume is bounded before the CR-first reorder multiplies it.** | TO-AUTHOR | sonnet/med | codex/med | 0.7 |
| 4.6 | Q-05 | Cross-app KB recall (MVP, DynamoDB) | `specs/Q-05-knowledge-base-spec.md` (TO-AUTHOR) | opus/high | codex/high | 3.1, O-2 |
| 4.7 | Q-08 | LLM eval harness (promptfoo + golden set). **Owns authoring + versioning the golden dataset (contents + PII provenance — do NOT use raw user CVs as fixtures without a sanitization/consent decision).** | TO-AUTHOR | opus/high | codex/high | 4.2 |
| 4.8 | F-02..F-05 | Fix the 4 live contract bugs. *(F-06's all-10 executable assertions moved to Wave-0 step 0.3 — v2.0.0/A11.)* | `specs/F-contract-fixes-spec.md` (TO-AUTHOR) | opus/high | codex/high | 0.5 |
| 4.9 | X-02 | **Prompt-injection hardening** — delimit untrusted input (CV/JD/Tavily CR) in artifact prompts; XSS-encode generated fields; preserve+test SSRF guard (tested by 4.7 red-team). **⚠️ End-to-end XSS closure (v2.0.0 Layer-2 item 6): backend encoding (X-02) is owned here, but the XSS *sink* is the frontend `dangerouslySetInnerHTML`-class render — out of scope by C-6. This is a cross-boundary risk: add ONE explicit FE verification task (does `src/frontend` safely render an artifact field carrying an injection payload?) — flagged, NOT silently pulled into backend scope. Without it, end-to-end XSS closure is unprovable from this plan.** | `specs/X-02-prompt-injection-spec.md` (TO-AUTHOR) | opus/high | codex/high | 4.7 |
| 4.10 | Q-11 | Prompt-cache breakpoints + bound artifact `max_tokens` + bound Tavily input | `specs/Q-11-cost-bounds-spec.md` (TO-AUTHOR) | sonnet/med | codex/med | 0.75 |

### Wave 5 — Cost/observability + Tier-2 tail
| # | Clause(s) | Step | Claude | Codex | Deps |
|---|---|---|---|---|---|
| 5.1 | CMK, field-PII, X-01 | CMK on Dynamo/S3; field-level PII encryption; account-close delete-all | opus/high | codex/high | 3.* |
| 5.2 | Tier-2 obs, P-32 remainder | Log retention, alarms, tagging, request validators; app-wide `Tags.of` + correlation-ID propagation (**P-32**, NFR-COST-3/OBS-3). *(AWS Budgets + Cost-Anomaly slice moved to Wave-0 step 0.56 — v2.0.0/A11; bootstrap-latency emission for O-1 folded into the correlation-ID/metrics work here, feeding P-20's harness at 2.4.)* | sonnet/med | codex/med | 0.1 |
| 5.3 | low-effort/high-value | ARM64, minimized GSI, dead-resource deletion, F-07 | sonnet/med | codex/med | — |
| 5.4 | T-05 | mutmut mutation spot-check on core | sonnet/med | codex/med | 3.* |

### Wave 6 — Committed, gated (post-launch)
| # | Clause(s) | Step | Claude | Codex | Deps |
|---|---|---|---|---|---|
| 6.1 | D-H8, D-H6 | Full single-table `core` collapse (expand→dual-write→backfill→dual-read→contract) | opus/xhigh | codex/high | O-1, O-5, all Wave 3 |
| 6.2 | Q-06 | KB Phase 2 — S3 Vectors (swap ranker only) | opus/high | codex/high | 4.6, O-6 |

---

## Specs still TO-AUTHOR (Wave-0 step 0.4 produces these; Gap spec is the exemplar)
> **Status 2026-07-11:** step 0.4 fan-out is closed. The listed grouped spec files now exist under `docs/db-redesign/code/code-analysis/project/specs/`, with inline RED-test descriptions and `scope_lock_clause` frontmatter. `scope-diff.py` reports no orphan specs and no multi-clause tooling errors. It still reports global uncovered clauses for intentionally mechanical-inline or future-wave items: `P-02`, `P-22`, `D-H6`, `D-H8`, `D-L`, `Q-06`, `T-01`, `T-02`, `T-03`, `T-04`, `T-05`, `T-08`, `F-07`.
> **Deduped + counted (v2.0.0 — the previous list double-listed Q-08/X-01/Q-05/Q-07 and enumerated clauses, not files).** Specs are **per-feature files** that may group several clauses (multi-clause form, §8.5 — the `Q-gap` exemplar already covers Q-01..Q-04 in one file). **~20 spec files**, reconciled with T-06's estimate (T-06 updated to "~20 grouped per-feature specs"). Tier-1 first. The AUTHORED exemplar (`Q-gap`) is not on this list. Purely-mechanical config edits (e.g. a one-line throttle bump) may be handled inline by their runbook step without a standalone spec.

**Track P (14 files):** P-03 (api-surface) · P-04+P-05 (auth/IDOR — incl. the 31-handler route×handler table) · P-06 (secrets) · P-07 (cognito hardening) · P-08+P-10+P-11 (CORS+WAF) · P-09 (IAM per-fn) · P-12+P-13 (RETAIN) · P-14+P-15 (money idempotency+Scan) · P-16+P-17+P-18+P-19 (SQS/SFN reliability) · P-20 (throttle+load harness) · P-21 (SNS) · P-23 (canary/rollback) · P-24 (identity surrogate) · **P-25+P-25b (payment port + real Stripe)** · P-26 (CFN blue/green **+ the custom-domain/DNS slice for 0.64b**) · P-27+P-28 (deploy safety + pipeline closure) · P-29 (evidence pack) · P-30 (smoke harness) · P-31 (EB DLQ) · P-32 (cost/obs; budgets slice authored early at 0.56). *(P-22 OIDC = a mechanical CI edit, inline.)*
**Track D (5 files):** D-H2+D-H3 (key-authority + parity harness) · D-H4 (canonical `artifact_id`) · D-H7 (Scans) · D-M* + D-Q (seams bundle) · **D-H9 (FE-UI-044 completion)**. *(D-H8 collapse = Wave-6, its own spec then.)*
**Track Q (5 files):** Q-05 (KB MVP) · Q-07+Q-09 (knowledge-table + CR margin guard) · Q-08 (evals + golden dataset) · **Q-10 (token metering — authored early for 0.75)** · Q-11 (cost bounds).
**Track F (2 files):** F-01 (oracle, now carrying the F-06 all-10 assertions) · F-02..F-05 (contract fixes). *(F-07 OpenAPI regen = mechanical, inline.)*
**Track T (2 files):** scope-diff.py + spec-coverage-ledger.
**Track X (2 files):** X-01 (DSAR delete) · X-02 (prompt-injection hardening).

Each carries model/effort in its frontmatter; RED-test descriptions inline (v1.3.0 — no separate test-prompt file).

## Traceability (how specs/tests stay true to production — clause T-09)
`scope-diff.py` reads `project-scope-lock.yaml` and, for each `backlog[].id`, resolves:
`spec_exists? test_exists? impl_state?` by scanning spec/test frontmatter for `scope_lock_clause`.
Outputs: coverage (clauses with no spec), scope-creep (specs with no clause), and a status board
mirroring this plan's `status` columns. Runs in CI + on demand = your periodic drift diff.
