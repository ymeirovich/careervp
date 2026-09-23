# CareerVP — Project Scope Lock (Contract)

- **Version:** 1.3.0
- **Frozen:** 2026-07-05 (v1.0.0) · last amended 2026-07-09 (v1.3.0)
- **Code anchor:** `github.com/ymeirovich/careervp` @ commit `4f7c294` (the analysis commit)
- **Live anchor:** AWS acct `788159322332`, `us-east-1`, `dev` stage (no `prod` exists yet — go-live is a first deploy)
- **Machine-checkable twin:** [`project-scope-lock.yaml`](./project-scope-lock.yaml) — same clause IDs; the periodic diff runs against the YAML.
- **Status:** IMMUTABLE. Change only via the amendment process in §0.3.

---

## 0. Control

### 0.1 Purpose
This document is the **single immutable contract** that keeps specs, tests, and implementation true across a long development series. Specs and tests are validated against it; drift from it is a defect in the spec/test, not in this document. It is **exhaustive** (every known feature and finding is listed and prioritized) and describes a **complete path to production**, robust to partially-implemented work.

### 0.2 Authority hierarchy (what wins on conflict)
1. **This document** (and its YAML twin) — wins over everything below on any conflict.
2. `handoff.md` — locked post-council decisions.
3. `careervp-architecture-v2.md` (arch truth) + `careervp-architecture-deepdive.md` (companion). **`careervparchitecture.md` (v1) is DEPRECATED — never cite.**
4. `findings-register.md` (scope), `coverage-matrix.md §2` (frontend contract), `redesign-runbook.md` (migration mechanics).
5. `requirements.md`, `features.md`, `db-upgrade-priorities.md`.
6. **Live truth** (`recon.py` output, code @ `4f7c294`) supersedes any static/aspirational claim — e.g. the best-practice guide's inline "✅ repo already does this" annotations are **aspirational and often false**; trust `recon.py` + code.
7. **Non-authoritative / do-not-build-from:** `docs/features/*`, `docs/swagger/careervp-api-v1.yaml` (drifted). The frontend contract oracle = `src/frontend/` code, not any spec doc.

### 0.3 Amendment process (immutability)
- No clause changes silently. Every change: bump `Version`, add a dated row to §12 Change Log, and update both MD and YAML in the same commit.
- Each clause is tagged `IMMUTABLE` (invariant — a violation is always a defect), `TARGET` (a state to reach), or `OPEN` (undecided — must be resolved before its dependent spec is written; never guessed).
- `current_state` vs `target` are recorded separately so partial implementation shows as partial, never as scope loss.

**Principle:** the contract is immutable to **drift** (silent, unversioned change), not to **learning**. Amendments are welcome; unrecorded changes are the defect. The contract changes at the *speed of decisions*, not the speed of code. Map = this contract; trail markers = specs; a washed-out trail → re-mark the trail (fix the spec), only re-draw the map when the destination or a hard constraint changed.

**Semver discipline:**
- **PATCH** (x.x.+1) — clarification / typo / `current_state` refresh. No scope change.
- **MINOR** (x.+1.0) — add a clause; refine a `TARGET`; resolve an `OPEN`.
- **MAJOR** (+1.0.0) — change an `IMMUTABLE` invariant or locked decision; drop a feature; break a frontend-contract item.

**Deviation → amendment loop (built into the spec/test/impl process — see execution-plan "Deviation & amendment handling"):** when a step's subagent cannot satisfy a clause as written, or live truth contradicts a `current_state`:
1. **Stop at the clause — never silently deviate.**
2. **Emit an Amendment Proposal:** `{clause_id, tag, what changed, why + evidence cite, semver level, affected specs/tests}`.
3. **Human validates and confirms** — no auto-apply.
4. **Update both twins in the same commit** + §12 change-log row + version bump.
5. **Propagate** to dependent specs/tests, then re-run `scope-diff.py`.
- **Adversarial review required** before committing any amendment to an `IMMUTABLE` invariant, locked decision, or frontend-contract item (§9.2).

**Anti-patterns (hard-rejected — §9.3):** editing a *spec* to match the *code* instead of amending the contract when a decision changed · amending the contract *retroactively to rubber-stamp* what got built · weakening a test to pass. Amendments must cite evidence **and** a decision rationale, never "matches code."

### 0.4 Canonical ID space (kills the 3-namespace drift)
Every backlog item has ONE canonical ID (`P-##`, `D-##`, `Q-##`, `T-##`, `F-##`, `X-##`). The `crosswalk` field maps each to its legacy IDs (`finding #`, `NFR-*`, `DB-*`) so the three parallel namespaces collapse into one. LOE = `Lo/Md/Hi`. Priority tier = `T1/T2/T3/OUT`.

---

## 1. Fixed constraints (the physics — IMMUTABLE)
| ID | Constraint |
|---|---|
| C-1 | Scale ceiling **< 10k concurrent**. Design for it; do not over-engineer past it. |
| C-2 | **> 70% profit margin** maintained. LLM tokens are the lever, not infra. |
| C-3 | **Solo maintainer** — penalize big-bang / high-coordination work; favor incremental, reversible steps. |
| C-4 | **DynamoDB is kept** (decision closed — not re-litigated). |
| C-5 | Security-conscious, **no GDPR gold-plating**; lightweight DSAR (export/delete) only. |
| C-6 | **Backend + API contract only.** Frontend out of scope except where a change alters the API request/response contract. |
| C-7 | **No `prod` exists** — going live is a genuine first prod deploy. All work targets `dev` (the proving ground) until certified (§7.4). |
| C-8 | **Shared personal AWS account** (`788159322332`) — amplified IAM blast radius; `{env}`-scoped everything. |

## 2. Locked decisions (do-not-re-litigate — IMMUTABLE)
| ID | Decision |
|---|---|
| L-1 | **Identity/tenant key = internal immutable surrogate `user_id`** (own UUID). Resolve one-or-many Cognito `sub`s (Google/Facebook/password, linked by verified email) → `user_id` at the edge. *(Supersedes the earlier "key by Cognito sub"; chosen because social IdP is on the roadmap and this avoids re-keying the DB later.)* |
| L-2 | **Cognito-only auth** — retire the self-managed RS256 path; identity derives **only** from validated JWT claims (never a header/body field). Social IdP (Google/Facebook) planned; account-link by verified email. |
| L-3 | **Single-table `core` = STAGED-COMMITTED.** Do the decoupling seams first (one key-authority repository, kill the 3-schema drift, stop dual-key CV writes, retire the PII PK) → yields a production-ready best-practice data layer; **then** the full physical `core` collapse as a committed later wave with a go/no-go metric gate. |
| L-4 | **Billing live = launch-critical** (paid launch). |
| L-5 | **Company Research runs FIRST**, on new-application submit, to completion — **then** gap analysis; CR is reused by all downstream artifacts. Requires reordering the artifact chain to `CR → gap → vpr → {cv, cover, interview}`. |
| L-6 | **Gap Analysis → Sonnet (Strategic)**, gated on fixing its inputs first (real CV + CR). |
| L-7 | Priorities `T1/T2/T3`; effort `Lo/Md/Hi`. |

## 3. Frontend can't-break contract (IMMUTABLE) — `coverage-matrix.md §2`
The redesign is a data-layer + internal-identifier change that MUST keep API response shapes stable, **or version the route**. Internal PK is free to change; the wire contract is not.

1. `application_id == job_id` (one identifier, two names).
2. `artifact_id` is the round-tripped opaque key; a hub `artifact_id` MUST be resolvable by the status endpoint.
3. `vpr_id` = VPR's hub `artifact_id`; **CV-tailoring sends `vpr_id: null` (never omitted)** — null-vs-absent is load-bearing.
4. Status enum string-compared/unversioned (`pending|processing|completed|failed|cancelled|expired` + `not_generated`, `edited`); **changes must be additive.**
5. PATCH optimistic concurrency: echo `result.*` + `version` + `updated_at`; **HTTP 409 on stale `base_version`.**
6. `request_id` primacy (`request_id ?? job_id`).
7. Nested `result` shapes preserved (VPR/CV/IP/CL trees).
8. Presigned `download_url` + `status:'expired'` signal.
9. Existing shape polymorphism tolerated, must not worsen.
10. Error envelope (`error|message`, `classification`, `error_code`, `field`); 401 → one silent refresh-retry then sign-out.

**Oracle rule:** the authoritative contract = what `src/frontend/` actually calls + CDK `route_map` + handlers — NOT any OpenAPI/swagger doc (both are drifted).

**⚠️ Four live contract mismatches already exist** (real bugs — see F-02..F-05): VPR `download_url` missing from backend model; status enum lacks `cancelled/expired`; `vpr_id` required-non-null vs FE sends `null` (→422); error envelope nested vs FE expects flat (→`[object Object]`).

## 4. Architectural invariants (IMMUTABLE)
- Identity from validated JWT claims → `user_id` surrogate only; the DAL enforces the tenant partition key (IDOR structurally impossible); never re-fetch by a client-supplied `*_artifact_id`.
- A single **key-authority repository** is the sole key-builder; env-var table-precedence routing (`ARTIFACTS_TABLE_NAME → DYNAMODB_TABLE_NAME → TABLE_NAME`) is abolished; no new table alias.
- One typed home + one stored key per artifact type.
- Large bodies (VPR JSON, CV files) stay in **S3 with a pointer** (400KB / cost); "store rich, project lean" — storage shape ≠ prompt shape, both versioned.
- **Shared/cross-user data never lives in `core`** (partitioned by `USER#{user_id}`): Company Research cache (keyed by company), LLM cache, idempotency stay separate tables.
- One IAM role per function, ARN-scoped, `{env}`-suffixed; no `Resource:"*"` where ARNs are known.
- Every SQS consumer reports `batchItemFailures`; visibility timeout **≥ 6× function timeout**; `max_concurrency` on rate-limited consumers; DLQ + depth alarm on every queue.
- All stateful resources `RETAIN` + `deletion_protection`; no PK/SK change on a live table; no template > ~400 CFN resources.
- Vectors (if built) are a derived, rebuildable, tenant-filtered index — never the system of record; a single retrieval service is the only query path.

---

## 5. Canonical prioritized backlog (exhaustive)
> Full per-clause detail (deps, DoD, acceptance, current_state, verification) lives in the YAML twin. This is the readable index. `⟡` = belongs to both Track P and Track D.

### Track P — Production launch-blockers (T1 unless noted)
| ID | Item | LOE | Crosswalk |
|---|---|---|---|
| P-01 | Cover letter + interview prep FAIL — 3-schema / `vpr_id` routing defect ⟡ | Hi | #1, FR-F3/F4 |
| P-02 | Billing reconcile entrypoint mismatch (`Handler` ≠ `lambda_handler`) | Lo | #2, FR-I3 |
| P-03 | Map the `/api/*` surface before redesign (verify staging-only) | Lo | #3 |
| P-04 | Remove `x-user-id` header bypass + `AUTHORIZER_DISABLED` switch | Md | #4, NFR-SEC-1 |
| P-05 | IDOR — `get_job` (and peers) enforce owner/`user_id` | Md | #5, NFR-SEC-2 |
| P-06 | JWT key + webhook secret out of Lambda env → SSM SecureString/Secrets Mgr | Md | #6, NFR-SEC-3 |
| P-07 | Cognito MFA + advanced security (ATP) | Lo | #7, NFR-SEC-6 |
| P-08 | CV bucket CORS `*` → locked origins | Lo | #8, NFR-SEC-7 |
| P-09 | One IAM role per function (retire the shared ~20-fn role; fix billing/export default roles) | Hi | #9, NFR-SEC-4 |
| P-10 | API GW CORS `ALL_ORIGINS` → allow-list | Lo | #10, NFR-SEC-7 |
| P-11 | WAF in all envs + rate-based rule | Md | #11, NFR-SEC-5 |
| P-12 | `RemovalPolicy.RETAIN` + `deletion_protection` on all tables/buckets; fix backups bucket auto-delete ⟡ | Md | #12, NFR-DATA-1, DB-H1 |
| P-13 | Remove dead `RETAIN` stacks never instantiated | Lo | #13, DB-L1 |
| P-14 | Idempotency wired on billing webhook + at-least-once workers (keyed on stable business id) | Md | #14, NFR-REL-1, DB-H5 |
| P-15 | Eliminate billing `Scan` on the money path ⟡ | Md | #15, NFR-SCALE-2, DB-H7 |
| P-16 | Reserved/`max_concurrency` bounds on rate-limited consumers | Lo | #16, NFR-REL-3 |
| P-17 | `ReportBatchItemFailures` on all SQS consumers; wire the 8 unreaped DLQs | Md | #17, NFR-REL-4 |
| P-18 | SQS visibility timeout ≥ 6× Lambda timeout | Lo | #18, NFR-REL-2 |
| P-19 | Step Functions retry/heartbeat: `MaxAttempts`/`BackoffRate`, `JitterStrategy: FULL`, `StartVPR` heartbeat | Md | #19, NFR-REL-5 |
| P-20 | Raise API throttle from 2 rps / burst 10 (self-DoS) to a real target | Lo | #20, NFR-SCALE-1 |
| P-21 | SNS alarms → subscribed on-call topic (currently 0 subscribers) | Lo | #21, NFR-OBS-1 |
| P-22 | CI/CD: replace long-lived keys in `cdk-diff.yml` with OIDC | Lo | #22, NFR-DEP-x |
| P-23 | Alias+version + CodeDeploy canary/rollback | Md | #23, NFR-DEP-x |
| P-24 | **Identity surrogate `user_id` layer** (resolve `sub`→`user_id`; social-IdP account-linking) | Hi | L-1, NFR-SEC-1 |
| P-25 | **Payment-provider port + `MockProvider`** (plug-n-play; `StripeProvider` deferred). All billing (P-02/14/15, I1–I4) codes against the port; Mock signs test webhooks + returns realistic subscription/customer objects; preserves FE checkout/portal URL contract; swap to Stripe behind config later | Md | L-4, FR-I1/I2 |
| P-26 | **CFN nested-stack decomposition** — nest the whole `RestApi` (~175 API-GW resources → 1 parent entry) + feature Lambdas into per-feature nested stacks; refs via constructor props, not `Fn::ImportValue`. **Must precede P-09/P-14/P-17/P-21** (they add resources to a stack at 415/500). Contract-touching: RestApi recreate can change the invoke URL → mitigate via retained logical id or custom domain + ACM; verify frontend resolves | Md | #8 |

### Track D — DB best-practice / single-table (seams = T1/T2; full collapse = committed later wave)
| ID | Item | LOE | Crosswalk |
|---|---|---|---|
| D-H2 | Single key-authority repository (`TableRegistry`/`CoreRepository`) — sole key-builder | Md | DB-H2 |
| D-H3 | Surface swallowed `ValidationException` (no false "not found") | Lo | DB-Q1/H3 |
| D-H4 | Stored canonical `artifact_id` + pass resolved upstreams (contract-touching) | Md | DB-H4 |
| D-H7 | Eliminate request-path `Scan`s | Md | DB-H7, #15 |
| D-M1 | Split the 1,128-LOC DAL god-class | Md | DB-M1 |
| D-M2 | Stop dual-key CV write (recon: `cvs` has both `pk/sk` + `userId/cvId`) | Lo | DB-M2 |
| D-M3 | Minimized GSI projections | Lo | DB-M3 |
| D-M5 | Retire `userEmail` PII partition key (knowledge/gap tables) | Md | DB-M5 |
| D-M6 | Access-pattern inventory doc (schema contract) | Lo | DB-M6 |
| D-Q* | Quick wins: connection reuse, pagination, schema-enforced TTL, PITR 7d→35d | Lo | DB-Q2..Q6 |
| D-H8 | **Full single-table `core` collapse** (committed later wave; contract-touching; re-justify gate) | Hi | DB-H8, #48 |
| D-H6 | `TransactWriteItems` for multi-item invariants | Md | DB-H6 |
| D-L* | LOW: delete dead resources, `_SingletonMeta` removal, `api_storage_adapter` collapse, `BatchGetItem` audit | Lo | DB-L1..L7 |

### Track Q — Generation quality / LLM
| ID | Item | LOE | Crosswalk |
|---|---|---|---|
| Q-01 | Reorder artifact chain: **CR first** (on submit) → gap → vpr → {cv, cover, interview} | Md | L-5 |
| Q-02 | Fix Gap **real-CV** injection (load via `get_cv_by_id`; stop the `'Candidate'` stub) — TDD, test-first | Lo | new (`gap_handler.py:528-533`) |
| Q-03 | Route Gap Analysis to **Sonnet** via `LLMRouter` `TaskMode.STRATEGIC` (currently Haiku) | Lo | new (`gap_analysis.py:283-286`) |
| Q-04 | Feed CR into **all consumers** (gap, VPR, cover, interview) via existing prompt slots; per-step **digests** to protect margin | Md | L-5, C-2 |
| Q-05 | **Cross-application knowledge base (MVP)** — distil prior gap answers + validated CV bullets + VPR differentiators into `PFACT` items in per-user `core`; recall = rolling digest + top-K under **1,200-token cap**; DynamoDB brute-force rank; tenant-filtered; non-PII key | Hi | FR-K1, new |
| Q-06 | KB **Phase 2** — S3 Vectors cosine top-K (swap ranker only), flag-gated | Hi | ragvector, FR-K1 |
| Q-07 | Recreate deployed `knowledge-table` on the `user_id`/`sub` key (currently declares `userEmail`, empty); retire mis-wired `/knowledge-base` route | Lo | #K, DB-M5 |
| Q-08 | LLM output-quality evals (promptfoo + golden dataset + LLM-judge @ temp 0 + FVS gate + OWASP-LLM red-team) | Md | T-05 |
| Q-09 | Company Research margin guard (~15k Tavily tokens/gen → truncate / `include_raw_content:false`) | Lo | cost-model |

### Track T — Testing & spec coverage
| ID | Item | LOE | Crosswalk |
|---|---|---|---|
| T-01 | **Enable branch coverage** (currently 0) | Lo | NFR-DEP |
| T-02 | **Retire the autouse `mock_artifact_dependency_resolver`** (opt-in); drive resolver/routing tests against real key schemas (moto) | Md | coverage-matrix §3 |
| T-03 | Coverage gates: core 85%/80% (line/branch), supporting 75–80%/70%, glue ~60%/excluded; overall CI gate 80%/70% | Lo | §8.1 |
| T-04 | Full test taxonomy: unit, **contract, characterization, integration, IaC, idempotency, migration-parity, LLM-eval, load/perf, security/SAST, smoke/canary** | Md | §8.3 |
| T-05 | Mutation-testing spot-check (`mutmut`) on core tier | Lo | §8.1 |
| T-06 | **Spec-coverage ledger** + author ~15–20 per-feature specs (Tier-1 first), derived from route_map + frontend calls (NOT drifted docs) | Hi | new, §8.4 |
| T-07 | 8 CI gates: ruff, mypy --strict, pytest, cdk synth, Checkov, Bandit, pip-audit, CodeQL | Lo | agentic-guide |
| T-08 | **Execution plan** — ordered runbook sequencing every clause into copy-paste steps w/ model+effort ([`redesign-execution-plan.md`](./redesign-execution-plan.md)) | Lo | new |
| T-09 | **`scope-diff.py` drift checker** — maps clause↔spec↔test↔impl_state from frontmatter `scope_lock_clause`; CI gate + periodic diff | Md | §11 |

### Track F — Frontend contract validation
| ID | Item | LOE | Crosswalk |
|---|---|---|---|
| F-01 | **Executable oracle:** Zod mirror of `src/frontend/lib/types.ts` + `safeParse` (frontend-truth) + Pydantic `model_json_schema()`→ajv (backend-truth), wired via MSW in CI; nightly Playwright vs dev | Md | coverage-matrix §2 |
| F-02 | Fix: VPR `download_url` missing from `VPRStatusResult` (`api_models.py:173`) | Lo | live bug |
| F-03 | Fix: status enum lacks `cancelled/expired` in backend `Literal` (`api_models.py:182`) | Lo | live bug, contract #4 |
| F-04 | Fix: `vpr_id` required-non-null vs FE sends `null` → 422 (`api_models.py:282`) | Lo | live bug, contract #3 |
| F-05 | Fix: error envelope nested vs FE-expected flat → `[object Object]` (`api_models.py:511`) | Lo | live bug, contract #10 |
| F-06 | Encode all 10 contract items as executable assertions | Md | contract §3 |
| F-07 | Regenerate OpenAPI from live/route_map; mark `careervp-api-v1.yaml` + `docs/features/*` non-authoritative | Lo | oracle rule |

### Track X — cross-cutting / compliance
| ID | Item | LOE | Crosswalk |
|---|---|---|---|
| X-01 | Account-close **delete-all-my-data** (export already exists; delete the full `USER#{user_id}` collection + S3 objects + Cognito user). T2 | Md | DSAR (C-5) |

## 6. Out of scope
### 6.1 Explicit deviations (documented, intentional — OUT)
- Global Tables (multi-region).
- **Data-residency partitioning** (deferred — revisit only for a contractual EU customer).
- Heavy formal-DSAR tooling (audit workflow, verified-request process) — lightweight export/delete stays IN.

### 6.2 In scope now (moved OUT→IN this round)
- **CMK** on DynamoDB/S3 (was Tier-4). Now T2.
- **Field-level PII encryption** (was Tier-4). Now T2.
- **Account-close "delete-all-my-data"** (clause `X-01`). Artifact **export already exists** — the only DSAR gap is a full data delete on account closure. T2.
- **Data residency: confirmed OUT** — stored in `us-east-1` only for now; revisit only for a contractual EU customer.

### 6.3 Deferred / bounded tracks
- **RAG/vectors** — only as KB Phase 2 (Q-06), derived index, flag-gated; OpenSearch Serverless rejected (idle cost).
- **Artifact compression** — measure-first; digest projections (already partly used) formalized under Q-04.
- **Sonnet-5 migration** — VPR-pilot-only, gated on the two blockers (`temperature=0.65` 400-error; the `SONNET_MODEL_ID` CI assertion) + real-token measurement + intro-pricing window (2026-08-31). Gap→Sonnet (Q-03) is separate and approved.

## 7. Complete path to production
### 7.1 Non-negotiable ordered gates (before any migration)
1. RETAIN + deletion-protection (P-12) — the smallest safe first slice.
2. CFN headroom — nested-stack decomposition (root ~415/500) before adding resources.
3. Schema recon (`recon.py` — DONE 2026-07-05; re-run before dual-write).
4. SNS subscriber verification (P-21).
5. Token/cost measurement baseline (C-2 guard).
6. Rehearsed rollback + drift-visibility.

### 7.2 Waves
- **Wave 0 — Guardrails & truth (nets FIRST, then scaffold):** re-clone source + **anchor confirmation** (`HEAD==4f7c294` + re-run `recon.py`); **author `test-strategy.md`**; build the drift nets — `scope-diff.py` (T-09) + spec-coverage ledger (T-06) + executable oracle skeleton (F-01) — **before** scaffolding specs; then scaffold all specs; branch coverage + retire autouse mock (T-01/T-02); RETAIN + deletion-protection (P-12); **CFN nested-stack decomposition (P-26) before any additive resource work**; identity surrogate scaffolding (P-24). *(Nets precede scaffolding so a mis-authored spec is caught immediately — see execution-plan Wave 0.)*
- **Wave 1 — Security/auth launch-blockers:** P-04..P-11, P-22.
- **Wave 2 — Reliability/money:** P-14..P-20, P-23, P-02.
- **Wave 3 — DB seams:** D-H2/H3/H4/H7, D-M1/M2/M3/M5/M6, D-Q*; fixes P-01 (the actual break).
- **Wave 4 — Generation quality:** Q-01 (chain reorder), Q-02/Q-03 (gap CV+Sonnet), Q-04 (CR everywhere), Q-05 (KB MVP), Q-07, Q-08/Q-09; frontend fixes F-02..F-06.
- **Wave 5 — Cost/observability + Tier-2 tail:** CMK, field-PII, DSAR export/delete, log retention, alarms, tagging, low-effort/high-value Tier-3 picks.
- **Wave 6 (committed, gated) — Full `core` collapse:** D-H8/H6 via expand→dual-write→backfill→dual-read→contract; KB Phase 2 (Q-06) optional.

### 7.3 Launch freeze line
**Freeze = all Track-P T1 (P-01..P-24) + all Tier-2 + cherry-picked low-effort/high-value** (criteria: cost↓, perf↑, security↑, durability/reliability↑ — e.g. ARM64, minimized GSI projections, dead-resource deletion). The full `core` collapse (Wave 6) and KB Phase 2 are **post-launch**. Everything below the line stays listed and prioritized.

### 7.4 Prod-promotion certification (DoD for standing up prod)
All freeze-line items closed **AND** NFRs met **AND** test suite green with real key-schema coverage (branch on, autouse mock retired) **AND** executable oracle green **AND** `cdk diff` shows zero stateful replacements.

## 8. Definition of Done / quality gates
### 8.1 Coverage (sourced: Google/AWS/BullseyeCoverage — 100% is an anti-pattern)
- Core generation/orchestration: **85% line / 80% branch.** Supporting: 75–80% / 70%. Glue: ~60% or excluded. LLM output: **evals, not coverage.**
- CI gate starts **80% line / 70% branch overall**; branch coverage enabled; autouse mock retired; `mutmut` spot-check on core.
### 8.2 CI gates (all must pass — never "agent says done")
ruff · mypy --strict · pytest · `cdk synth` (+ resource-count <400) · Checkov · Bandit · pip-audit · CodeQL · executable-oracle · `cdk diff` zero-stateful-replacement.
### 8.3 Test types required
unit · contract · characterization · integration (real services, not mocks) · IaC/CDK · idempotency/replay · migration-parity · LLM-eval (promptfoo + golden set + judge @ temp 0 + red-team) · load/perf · security/SAST · smoke/canary.
### 8.4 Spec completeness
Every endpoint + async behavior has a spec row (request/response models, error codes, acceptance criteria, edge cases). Every FR maps to ≥1 spec row and vice-versa. Each artifact spec carries its slice of the §3 frontend contract as acceptance criteria. A feature is "spec-complete" only when its acceptance criteria are an executable test.

### 8.5 Spec/test authoring rules (IMMUTABLE — apply to EVERY spec and test file)
- **Format (v1.3.0 — matches the proven `Q-gap-analysis-track-spec.md` exemplar, not a claimed-but-never-built convention):** a spec is one Markdown file, YAML frontmatter + Problem Statement + Evidence (`file:line`) + numbered Fix Plan + `AC-###` Given/When/Then. **RED-test descriptions (exact name + exact assertions) live inline in the spec body** under a "RED tests to write first" section — they are the brief, not the artifact. The **actual pytest files are written during the IMPLEMENT step**, under TDD (write it, watch it fail, then make it pass), **in the real `careervp` repo** — never as a standalone file in this docs project. *(Retired: the `TEST-###-test-prompts.yaml` copy-paste-prompt format — no working example of it ever existed; it contradicted the one real exemplar.)*
- **Ordering:** every spec/test slots into [`redesign-execution-plan.md`](./redesign-execution-plan.md) (T-08) as a numbered step; do steps in order.
- **Mandatory frontmatter (the join key + tool routing):**
  ```yaml
  scope_lock_clause: Q-02
  claude_code: {model: opus|sonnet, effort: low|medium|high|xhigh}
  codex: {model: gpt-5-codex, reasoning: low|medium|high}
  ```
  Model/effort per the task-class table in the execution plan. A spec/test without `scope_lock_clause` is out of contract; without the tool block it is incomplete.

### 8.6 Spec/test acceptance gate (validating the specs & tests themselves — detail in [`test-strategy.md §8`](./test-strategy.md))
A spec/test is accepted only when ALL five pass:
1. **Structural** — `scope-diff.py`: required frontmatter present, `scope_lock_clause` exists here, no orphan spec (spec with no clause), no uncovered clause (clause with no spec).
2. **Contract-consistency** — the spec's `AC-###` do not contradict the clause's acceptance/verification; a `contract_impact` clause's spec MUST carry its §3 frontend-contract slice.
3. **Self-sufficiency** — a fresh subagent given ONLY the spec + clause + named files can implement it with zero further questions. If it must ask, the spec is underspecified → reject.
4. **Adversarial refuter** — a second agent tries to break the spec (ambiguity, missing edge cases, contradiction). Mandatory for auth/IAM/data specs.
5. **Test-validity** — red-green (fails pre-impl, passes post) + `mutmut` on core + characterization proven against `4f7c294`; traceability round-trip (FR → spec → test → clause, both directions).

## 9. Guardrails
### 9.1 On this document
Immutable + amendment-only (§0.3); single authority hierarchy; one canonical ID per clause; every clause tagged IMMUTABLE/TARGET/OPEN; current-state ≠ target; commit-anchored; live truth supersedes static.
### 9.2 Imposed on all spec/test/impl work
- Frontend contract can't break — version a route instead of changing a response shape.
- `expand → dual-write → backfill → dual-read → contract`; no live PK/SK change in one deploy; RETAIN + backup before risky steps; one reversible, flag-gated change at a time.
- `cdk diff` zero-stateful-replacement is a first-class check; CI <400 resources/template; refs via constructor props, never `Fn::ImportValue`.
- Tests drive **real key schemas** (moto); **never weaken a test to pass**; branch coverage on; characterization test before each migration change.
- `{env}`-scoped IAM; one role per fn; no `Resource:"*"`; no secrets in env; server-side quota (14-day/3-app trial).
- Spawn an **adversarial review** for auth/IAM/data-layer diffs, and before committing any amendment to an IMMUTABLE/locked/frontend-contract clause (§0.3).
- **Serialize steps that touch the same CFN template file** (`api_construct.py`, `api_db_construct.py`, `cognito_construct.py`, `monitoring.py`, `waf_construct.py`) — never let parallel subagents edit one template concurrently. Pure-Python/handler/test/doc steps may parallelize.
### 9.3 PR block-list (hard reject — `redesign-runbook.md`)
A single deploy that renames/removes a live table/GSI/bucket or changes PK/SK · read path switched to `core` before backfill+reconciliation complete · big-bang cutover with no canary/flag/rollback · `removal_policy=DESTROY` reintroduced · unthrottled migration batch vs live capacity · new resources added to an already-near-full stack (>400) · IAM scoped across environments (no `{env}` suffix) · **parallel edits to one CFN template file** · **a spec edited to match code without a contract amendment** · **the contract amended retroactively to rubber-stamp already-built code** · **a test weakened to pass.**

## 10. Open-questions register (must resolve before the dependent spec — do NOT guess)
| ID | Question | Blocks |
|---|---|---|
| O-1 | Full `core` collapse (D-H8) go/no-go metric threshold — what evidence justifies Wave 6? | D-H8 |
| O-2 | CR cache-key granularity: company-only (max reuse) vs company+role (relevance)? | Q-01/Q-04 |
| O-3 | Cutover/downtime tolerance + retention window (from a fresh `recon.py` / product call). | Wave 3/6 |
| ~~O-4~~ | **RESOLVED 2026-07-09** — social-IdP account-linking: auto-link a new `sub` to an existing `user_id` **only when the IdP asserts `email_verified=true` AND email matches**; otherwise no auto-link (step-up "sign in with your original method to link"); conflicts → earliest-created `user_id`; all links audit-logged. Adversarial review required on the P-24 spec. | P-24 (unblocked) |
| O-5 | `jobs`/`applications` — fold into `core` or keep as focused tables? | D-H8 |
| O-6 | KB Phase-2 embedding model + dimension + min-cosine reuse threshold. | Q-06 |

## 11. Traceability & drift-check protocol
- The **YAML twin** is the machine-checkable index: each clause = `{id, title, tier, track, status, loe, deps, crosswalk, contract_impact, acceptance, current_state, verification}`.
- **Periodic diff:** for each clause, map implemented specs/tests → clause ID → `{not_started | spec_written | test_written | implemented | verified}`. Partial completion shows as partial. A spec/test with no clause ID, or a clause a spec contradicts, is a drift defect.
- Verification sources: `recon.py` (live DB), `cdk synth`/`diff`, the executable oracle, the CI gate results — never self-report.

## 12. Change log
| Version | Date | Change |
|---|---|---|
| 1.0.0 | 2026-07-05 | Initial contract frozen at code `4f7c294`. |
| 1.1.0 | 2026-07-09 | **MINOR.** Added **P-25** (payment-provider port + `MockProvider`, plug-n-play, Stripe deferred) and **P-26** (CFN nested-stack decomposition — was a documented gate with no clause). Extended §0.3 with semver + the deviation→proposal→human-confirm amendment loop + anti-patterns. Added **§8.6** spec/test acceptance gate. Added guardrails: serialize CDK-template-touching steps (§9.2) + new §9.3 anti-pattern rejects. Wave-0 reordered so the drift nets (T-09, F-01) precede spec scaffolding; added anchor confirmation + `test-strategy.md` + P-26. Authored [`test-strategy.md`](./test-strategy.md). No IMMUTABLE clause changed; no launch-blocker re-tiered. |
| 1.2.0 | 2026-07-09 | **MINOR** (applied by protocol: structured proposal → human confirm). **(A)** Resolved **O-4** (social-IdP linking — verified-email-only auto-link + step-up + earliest-`user_id` conflict rule + audit log; recorded on P-24). **(B)** Homed 6 orphaned clauses surfaced by a reference audit: **P-03/P-13/P-21/T-07** given Wave-0 steps; **T-03/T-04** id-linked to steps 0.5/0.1.5. **(C)** Fixed `best-preactice`→`best-practice` typo in historical `redesign/` docs. Anchor confirmed (`4f7c294`, 541 py, HEAD==anchor). No IMMUTABLE clause changed; no launch-blocker re-tiered. |
| 1.3.0 | 2026-07-09 | **MINOR** (human-decided, option B). **Retired** the never-built `TEST-###-test-prompts.yaml` claim; **§8.5 now matches the proven `Q-gap` exemplar** — RED-test descriptions inline in the spec body, real pytest files written during IMPLEMENT in the real repo. Recorded: spec-authoring (execution-plan step 0.4) fan-out runs via the **Workflow tool** (human opt-in) for true per-clause `{model,effort}`, not model-only via a plain `Agent` fan-out. No IMMUTABLE clause changed; no launch-blocker re-tiered. |
