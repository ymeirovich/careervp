# Handoff — CareerVP: write tests & specs (Phase: Test/Spec authoring)

> **Contract v1.5.0 (amended 2026-07-11 — eval-council conditions applied):** the 2026-07-11 local
> eval council (below) returned SOUND-WITH-CONDITIONS; v1.5.0 landed its 14 amendments (A1–A14) —
> P-26 blue/green API migration (never move the RestApi in place), P-28 CI-pipeline closure, contract
> files write-protected from agent sessions, P-04 real rollback (P-23 first + resolver-failure alarm),
> P-07 SPA-client hardening, new P-25b (real Stripe before paid launch) + D-H9 (finish FE-UI-044),
> GSI-cardinality invariant, CR soft-blocking fallback, gate 3/5 restructure. Blocking subset before
> starting: A1/A2/A3 + the exemplar patch + the two 15-min console tasks (Budgets, branch protection).
> Earlier history: v1.1.0 added P-25 (payment-provider port + mock, Stripe
> deferred) + P-26 (CFN nested-stack decomposition), reordered Wave 0 (nets before scaffolding),
> authored `test-strategy.md`, formalized the amendment/deviation loop + CDK-serialization rule;
> v1.2.0 resolved O-4 (social-IdP linking) + homed 6 orphaned clauses (P-03/P-13/P-21/T-03/T-04/T-07);
> v1.3.0 retired the `TEST-###-test-prompts.yaml` format for inline RED-test descriptions + set step
> 0.4 spec-authoring to run via the Workflow tool; v1.4.0 added 9 gap-fill clauses (P-27..P-32,
> Q-10, Q-11, X-02) closing orphaned NFRs — deploy-safety gates (stack policy, credential split,
> evidence pack, smoke harness) in Wave 0, real token metering (Q-10) in Wave 2, prompt-injection
> hardening (X-02) in Wave 4. Backlog 74 clauses. See `gap-closure-checklist.md` for post-completion validation.
>
> **Optional pre-execution QA (independent):** `project/eval-council-prompt.md` runs a local Fable
> council that grades THIS plan for risks/gaps (uses the Fable infra-mitigation plan + a 2026-07-11
> live recon as evidence — see `redesign/evidence/`). Its output splits into spec/runbook fixes and
> contract amendments (§0.3). Not required to "begin," but recommended before committing to Wave 1.

## HOW YOU RUN THIS (human — simple)
Start a Claude Code session, **paste this file**, **attach `project-scope-lock.yaml` +
`redesign-execution-plan.md` + `test-strategy.md`**, and say **"begin"** (or **"continue"** to
resume). That's it.
Re-paste in a new session anytime to resume — the plan's on-disk **status board** is the memory,
so no place is lost and no single session holds the whole redesign.

**Your four jobs after "begin"** (corrected v1.5.0 — the old "only two jobs" text omitted the two
most safety-critical duties, which would let a compliant operator rubber-stamp deploys or let the
orchestrator find its own deploy path):
1. **Decide open questions** — answer when the agent asks you to resolve an `O-#` (O-1..O-8); the
   answer is recorded into the scope-lock. Never let the agent guess.
2. **Approve each wave gate** — after `scope-diff.py` + oracle + coverage report green.
3. **Execute every `ExecuteChangeSet` yourself** (P-28) — the orchestrator prepares change sets with
   `CreateChangeSet` only; *you* run the mutation, after reading the machine-parsed
   `DescribeChangeSet` Replacement report (auto-fail on `Replacement:True` for
   RestApi/Table/Bucket/UserPool). This includes the human-only base-path/domain flip in P-26.
4. **Confirm every amendment** (§0.3) — when a step hits a deviation the agent emits an Amendment
   Proposal; *you* validate and commit it (the contract files are write-protected from agent
   sessions — v1.5.0/A3). No auto-apply.
You still do NOT manually load context or run implementation steps — the agent self-orchestrates those.

## WHAT THE AGENT DOES (you don't do this by hand)
- Works `redesign-execution-plan.md` **top-to-bottom**. For **each step it spawns a FRESH subagent**
  loaded with only that step's scope-lock clause (by ID from the YAML) + its spec + the few files it
  touches — so no context ever holds the whole redesign, and requirements can't rot.
- Writes/tests under **TDD**, updates the step's `Status`, then moves on.
- **On an open-question dependency (e.g. a dep listed as `O-4`): STOP and ASK the human to decide —
  never guess.** Record the answer into the scope-lock (O-# → decided), then proceed.
- **On a deviation (can't satisfy a clause as written, or live truth contradicts `current_state`):
  STOP, emit an Amendment Proposal, and wait for human confirmation** — never edit a spec to match
  code or weaken a test (scope-lock §0.3, execution-plan "Deviation & amendment handling").
- **Serialize steps that touch the same CFN template file** (the `Touches` column); parallelize spec
  authoring and independent pure-Python/test steps only.
- At each **wave gate**, run `scope-diff.py` + the executable oracle + coverage and report before
  continuing.
- The orchestrator keeps only the thin status board in context; work happens in the subagents.

**Contract:** the Project Scope Lock (`project-scope-lock.md`/`.yaml`) is the immutable source of
truth — the agent re-reads the specific clause per step. Read it first.

---

## 0. GOVERNING CONTRACT — the Project Scope Lock (read first, obey always)
- **`~/Documents/code/code-analysis/project/project-scope-lock.md`** (human-readable) and its
  machine-checkable twin **`project-scope-lock.yaml`** are the **single immutable contract**.
  They win over every other doc on conflict (authority hierarchy in §0.2).
- **Run order:** **`project/redesign-execution-plan.md`** is the ordered runbook (clause `T-08`) —
  work its numbered steps top-to-bottom. It tells you *what to do and when*, and the **model +
  effort for both Claude Code and Codex** per step. You do NOT invent an order.
- **Specs live in `project/specs/`.** **`project/specs/Q-gap-analysis-track-spec.md` already exists**
  (Track Q gap fixes) — it is BOTH the completed spec for `Q-01..Q-04` AND the **worked exemplar**
  for every other spec you author. The remaining specs are listed as `TO-AUTHOR` in the execution
  plan; author them in the **v1.3.0 format** (frontmatter + Problem Statement + Evidence `file:line`
  + numbered Fix Plan + `AC-###` Given/When/Then + **inline RED-test descriptions** under a "RED
  tests to write first" section — the actual pytest files are written at IMPLEMENT time in the real
  `careervp` repo, under TDD). **The `TEST-###-test-prompts.yaml` / copy-paste `prompt:`-block format
  is RETIRED (v1.3.0) — no working example ever existed; do NOT author prompt blocks.** Each spec
  carries the mandatory frontmatter (scope-lock §8.5): `scope_lock_clause` (single, OR a list +
  a per-clause `tooling:` map for multi-clause specs), `claude_code:{model,effort}`,
  `codex:{model,reasoning}`.
- **How it plugs into the plan/spec/test cycle:**
  1. Every plan item, spec, and test **cites a scope-lock clause ID** (`P-##`, `D-##`, `Q-##`,
     `T-##`, `F-##`). A spec/test with no clause ID is out of contract.
  2. Every spec's **done-when** = that clause's `acceptance` + `verification` from the YAML.
  3. Each artifact spec carries its slice of the **§3 frontend can't-break contract** as
     acceptance criteria.
  4. **Periodic drift diff:** map implemented specs/tests → clause ID → impl_state
     (`not_started|spec_written|test_written|implemented|verified`) against the YAML. Partial
     completion shows as partial; a clause a spec contradicts is a drift defect.
  5. **Never guess** an `OPEN` item (§10) — resolve it (with the user) before writing its
     dependent spec.
- Do **not** edit the scope-lock except via its amendment process (§0.3). If reality forces a
  change, amend the contract first, then the specs.

## 1. Context
CareerVP is an AWS-serverless (CDK/Python) app that turns a CV + job posting into a chain of AI
artifacts, plus billing/trial. **Full source = `github.com/ymeirovich/careervp` @ `4f7c294`**
(the analysis commit; ~541 py files, 301 frontend files) — clone it; the scratchpad checkout is
sometimes a stripped partial (verify `find -name '*.py' | wc -l`). Backend: API Gateway →
Cognito authorizer → ~31 Lambdas → DynamoDB (multi-table) → SQS/Step Functions → workers →
S3/Anthropic/Tavily. **Chain (target order): `company research → gap analysis → VPR →
{tailored CV, cover letter, interview prep}`** (CR now runs FIRST — see L-5). Frontend: Next.js
(`src/frontend/`, the active tree; ignore the stale sibling `frontend/`). AWS acct 788159322332,
us-east-1; only `dev` + `staging` exist (no prod yet). AWS CLI + read-only creds available.

**OPERATING CONSTRAINT — dev-only until prod-ready:** ALL work targets `dev` (the proving
ground). Do NOT create/deploy `prod` until `dev` is **certified** (scope-lock §7.4): all
freeze-line items closed + NFRs met + test suite green with real key-schema coverage +
executable oracle green + `cdk diff` zero stateful replacements. RETAIN + backups before any
destructive/migration step (dev holds real data: users 908, artifacts 221, jobs 144).

## 2. Goal of this phase
Finalize the test + spec foundation to begin implementation. Deliverables:
1. **`test-strategy.md`** (leads — the safety net that guarantees "don't break the UI").
2. **Per-component specs** (one per scope-lock backlog clause), goal→context→constraints→done-when,
   Tier-1 first, each citing its clause ID.
3. **The spec-coverage ledger** (clause `T-06`) proving every feature has a spec.
4. Update existing tests to best practices and remove the outstanding issues (§7).

## 3. Locked decisions (do not re-litigate — mirror scope-lock §2)
- **Identity/tenant key = internal immutable surrogate `user_id`** (own UUID); resolve Cognito
  `sub`(s) → `user_id` at the edge. Chosen because **Google/Facebook social IdP is planned** —
  this avoids re-keying the DB later. *(Supersedes the earlier "key by Cognito sub".)*
- **Cognito-only** auth (retire self-managed RS256); identity only from validated JWT.
- **Single-table `core` = STAGED-COMMITTED:** seams first (key-authority repo, kill 3-schema
  drift, stop dual-key CV write, retire PII PK) → production-ready best-practice layer; then the
  full `core` collapse as a **committed later wave** with a go/no-go gate (`D-H8`, OPEN O-1).
- **Company Research runs FIRST** on new-application submit, then gap; reused by all downstream
  artifacts (reorder chain — `Q-01`, `L-5`).
- **Gap Analysis → Sonnet** (Strategic), gated on fixing its inputs first (real CV `Q-02`, CR).
- Paid launch (billing live) → launch-critical. Frontend out of scope except API-contract changes.
- **In scope now:** CMK on Dynamo/S3, field-level PII encryption, lightweight DSAR (export/delete).
  **Out:** Global Tables, data-residency partitioning, heavy formal-DSAR tooling.
- Priorities `T1/T2/T3`; effort `Lo/Md/Hi`.

## 4. Read these first
- **`~/Documents/code/code-analysis/project/project-scope-lock.{md,yaml}`** — the contract (above).
- `findings-register.md` — full finding scope + Live-verification section.
- `coverage-matrix.md` — functionality surface + the frontend can't-break contract (§2).
- `requirements.md`, `features.md`, `db-upgrade-priorities.md` — the ledgers (mapped into the
  scope-lock canonical IDs via each clause's `crosswalk`).
- Architecture truth: **`careervp-architecture-v2.md`** (+ `careervp-architecture-deepdive.md`).
  **`careervparchitecture.md` (v1) is DEPRECATED — do not cite.**
- `recon.py` — read-only live recon (re-run: `AWS_PROFILE=… python3 recon.py --env dev`).
- Best-practice guides: `~/Documents/code/best-practice/` (AWS serverless + agentic-dev). Note the
  guide's inline "✅ repo already does this" is aspirational and often false — trust recon/code.
- In the repo: `docs/db-redesign/01-artifact-table-routing-and-vpr-id-model.md` (identifier dossier).

## 5. The five tracks (scope-lock §5)
- **P** — production launch-blockers (P-01..P-24, incl. the identity surrogate P-24).
- **D** — DB single-table (seams T1/T2; full collapse D-H8 committed later).
- **Q** — LLM generation quality (CR-first reorder, Gap real-CV + Sonnet, CR-into-all-consumers,
  cross-application knowledge base, evals).
- **T** — testing & spec coverage (coverage gates, taxonomy, spec ledger, retire autouse mock).
- **F** — frontend contract (executable oracle + the 4 live bugs F-02..F-05).

## 6. Verified ground truth (live recon 2026-07-05 + code @ 4f7c294)
- 10 tables PAY_PER_REQUEST; PITR ON except `llm-cache`; deletion protection FALSE on all;
  volumes tiny (users 908, artifacts 221, jobs 144, rest <20; `idempotency` & `knowledge` empty).
- Multi-schema drift physically present (artifacts carry applicationId/artifactId + pk/sk + job_id;
  cvs dual-key pk/sk + userId/cvId; users table holds mixed ARTIFACT#/PROFILE/CV collections).
- 2 rps throttle; WAF not attached (dev); SNS 0 subscribers; Cognito MFA OFF; CV bucket CORS `*`;
  0/31 reserved concurrency; JWT keys in env; billing-reconcile Handler mismatch; StartVPR no SFN heartbeat.
- **Gap Analysis (code-confirmed):** runs on **Haiku** (`gap_analysis.py:283-286`, plain LLMClient),
  feeds a **STUB CV** (`gap_handler.py:528-533`, `full_name:'Candidate'`), and its prompt already has
  **unfed** slots for `company_research`, `recurring_themes`, `previous_gap_responses`
  (`gap_analysis_prompt.py:54,91-97`) — CR/KB injection is a wiring job.
- **Company Research IS built** (async worker + Tavily) and runs in the chain — but currently AFTER
  gap (hence CR-first reorder). Shared cache keyed by company (cross-user reuse).
- **4 live frontend↔backend contract bugs** (F-02..F-05): VPR `download_url` missing from
  `VPRStatusResult`; status enum lacks `cancelled/expired`; `vpr_id` required-non-null vs FE sends
  `null` (→422); error envelope nested vs FE-expected flat (→`[object Object]`).

## 7. Outstanding test issues to REMOVE (clauses T-01/T-02/T-04)
- Autouse `tests/conftest.py::mock_artifact_dependency_resolver` (+ `mock_company_research_load`)
  neutralizes ~30 handler tests → make **opt-in**; drive real `resolve_dependencies` against
  **moto tables with actual key schemas** (pk/sk, applicationId/artifactId, job_id). The 78.45%
  line coverage is a vanity metric until this is fixed.
- **Enable branch coverage** (currently 0).
- Missing: whole-chain-to-persisted-result; replay idempotency gate (webhook + workers);
  `ReportBatchItemFailures` gate; cross-tenant isolation negative test; the executable oracle (F-01).

## 8. Coverage targets & test taxonomy (scope-lock §8 — research-backed)
- **Differentiated coverage:** core generation/orchestration **85% line / 80% branch**; supporting
  75–80% / 70%; glue ~60% or excluded; **LLM output = evals, not coverage.** CI gate starts
  **80% line / 70% branch overall**. Add `mutmut` spot-check on core. (100% is an anti-pattern.)
- **Test types required:** unit · contract · characterization · integration (real services) ·
  IaC/CDK · idempotency/replay · migration-parity · **LLM-eval** (promptfoo + golden dataset +
  LLM-judge @ temp 0 + FVS gate + OWASP-LLM red-team) · load/perf · security/SAST · smoke/canary.
- **Executable oracle (F-01):** Zod mirror of `src/frontend/lib/types.ts` + `safeParse`
  (frontend-truth) + Pydantic `model_json_schema()` → ajv (backend-truth), wired via MSW in CI +
  nightly Playwright vs dev. This is how "don't break the UI" is proven.

## 9. Task
1. Write `test-strategy.md`: (a) the spec-coverage ledger derived from CDK `route_map` + frontend
   calls + SFN + queues (NOT the drifted swagger/features docs); (b) characterization tests before
   each change; (c) the fixes in §7; (d) the executable oracle (F-01); (e) per-wave hard gates.
   Every done-when ties to a scope-lock clause acceptance.
2. **Follow `project/redesign-execution-plan.md` in order** — it sequences every clause into
   numbered steps with model/effort for both tools. Author each `TO-AUTHOR` spec in the
   `docs/upgrade/specs/` format, using `project/specs/Q-gap-analysis-track-spec.md` as the exemplar;
   each spec cites its `scope_lock_clause`, names AWS resources touched, carries the frontend-contract
   slice as acceptance, and has the `claude_code`/`codex` frontmatter (scope-lock §8.5). **RED-test
   descriptions live inline in the spec body** (v1.3.0 — matches the exemplar; the earlier
   `TEST-###-test-prompts.yaml` idea was retired, no working example ever existed). Actual pytest
   files are written at IMPLEMENT time, in the real repo, under TDD. Step 0.4 (mass spec authoring)
   runs via the **Workflow tool** for true per-clause model/effort (human opt-in, 2026-07-09).
3. Build **`scope-diff.py`** (clause `T-09`) + the spec-coverage ledger (`T-06`) so drift is
   machine-checkable, and update existing tests to remove the §7 issues.

## 10. Reasoning-effort guidance
- **Lo/medium:** mechanical config/IaC edits (RETAIN, throttle, tags, log retention, SNS sub,
  quick wins, the Gap real-CV + Sonnet wiring).
- **High:** the seams (key-authority repo, god-class split), IAM role split, idempotency/
  transactions, CR-first chain reorder, the executable oracle, the cross-app KB MVP.
- **xhigh:** the single-table `core` migration design + legacy→core classifier + parity verification;
  contradiction-resolution when amending the scope-lock.

## 11. Guardrails (scope-lock §9)
- Read-only AWS for validation; never destructive. Never break the frontend contract; version a
  route if a response shape must change. `expand→dual-write→backfill→dual-read→contract`; no live
  PK/SK change in one deploy; RETAIN + backup before risky steps; one reversible flag-gated change.
- `cdk diff` zero-stateful-replacement + CI <400 resources/template are first-class checks. Tests
  drive real key schemas; **never weaken a test to pass**. For auth/IAM/data-layer diffs spawn an
  adversarial review. Obey the scope-lock PR block-list (§9.3).
