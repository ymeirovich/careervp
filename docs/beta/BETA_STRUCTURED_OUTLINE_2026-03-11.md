# CareerVP Beta Structured Outline (Deadline: 2026-03-11)

@spec `docs/best_practices/yaml/prompt_optimization_spec.yaml`
@spec `docs/best_practices/yaml/code_quality_security_spec.yaml`
@pattern `infra/careervp/*.py`
@pattern `src/backend/careervp/handlers/*_handler.py`
@ref `docs/beta/BETA_PLAN_DESIGN.md`
@ref `docs/beta/BETA_TASK_LIST_2026-03-11.md`
@ref `docs/beta/STRICT_CHECKLIST_MAPPED_TO_SWAGGER.md`
@ref `docs/swagger/careervp-core-api-dev-prod-swagger-apigateway.json`
@ref `docs/architecture/prompt-improvement/CareerVP_Agentic_Architecture.md`

## 1. Decision Statement (Go/No-Go Rule)

### 1.1 Core Claim (Falsifiable)

By **Wednesday, March 11, 2026**, a new user can — using only a browser on `stage.careervp.com`:

1. Register and authenticate via **Cognito**.
2. Upload a CV and create a job application.
3. Receive **AI-generated** gap analysis questions (not templates).
4. Submit gap responses.
5. Retrieve five **AI-generated** artifacts: VPR, tailored CV, cover letter, interview prep, and gap analysis.
6. Each artifact is **stored, listable, and re-retrievable** via its list endpoint.
7. All of the above under **TLS 1.2**, with **trial enforcement active** (14-day / 3-application limit), and with **no hardcoded or template outputs** in any production path.

**Claim boundaries:**
- "AI-generated" means the response is produced by a Claude API call with user-specific context. A response matching known template patterns (e.g., `"Generated cover letter for request {id}"`, `"What quantifiable examples show your impact in core competency N"`) is a claim failure.
- "Stored, listable, and re-retrievable" means `GET /type` returns a non-empty array containing the artifact ID returned by the generate endpoint.
- "No operator intervention" means no manual DynamoDB edits, no Lambda restarts, no parameter changes during the workflow.

### 1.2 Hard Launch Rule

- Launch only if **all I1-I8 invariants pass** with attached machine-generated evidence less than 24 hours old.
- If any invariant fails, launch is **blocked** with specific remediation required.
- No invariant can be waived without explicit sign-off with rationale recorded.

### 1.3 Baseline Facts (Current State of Evidence)

Source: `live-test-results3.log` (2026-02-23 run), Swagger JSON (27 deployed routes).

| Fact | Source | Implication |
|---|---|---|
| 27 endpoints return 2xx | live-test-results3.log | HTTP layer works; does not prove semantic correctness |
| 3 of 5 generators return templates, not AI output | live-test-results3.log (Cover Letter, Interview Prep, Gap Analysis) | Core claim fails today |
| List endpoints return empty arrays after generation | live-test-results3.log (`vprs: []`, `cover_letters: []`) | Persistence is broken or artifacts are not linked |
| Tests run with `Auth Enabled: false` | live-test-results3.log header | Auth has never been validated in integration |
| CV Tailoring returns `cv_id: null`, ATS score 7 | live-test-results3.log | Below 8.0 target; null ID means artifact not persisted |
| VPR is the only working AI endpoint | live-test-results3.log (35s async, real output, S3 URL) | Proves the async pattern works; other generators don't use it |
| Company Research takes 150 seconds | live-test-results3.log | Exceeds any reasonable UX SLA |
| Health check reports `"bedrock": "healthy"` | live-test-results3.log | Infrastructure metadata is stale (migrated to Anthropic API) |
| Duplicate route surfaces exist | Swagger JSON (`/api/cv` vs `/users/me/cv`, `/api/vpr` vs `/vpr/generate`) | Contract ambiguity; frontend can call wrong route |
| Auth uses custom JWT authorizer, not Cognito | BETA_PLAN_DESIGN.md §6.2 | Decision: migrate to Cognito JWT authorizer |
| CVTable and DynamoDalHandler coexist | REFACTOR2_PLAN.md | Silent failure risk from CVTable pattern |
| No trial enforcement exists | Not implemented anywhere | Core claim §7 fails today |
| No application state model exists | Not designed | No state recovery on page reload |
| No edit, delete, or regenerate endpoints exist | Swagger JSON | User cannot correct or redo artifacts |

---

## 2. Precondition Audit

These are things that are currently **false** and must become true before sprint work makes sense. Work built on unresolved preconditions produces false progress.

### 2.1 Precondition Table

| ID | Precondition | Current State | Evidence of Falsehood | Resolution Layer |
|---|---|---|---|---|
| PC1 | All 5 generators produce real AI output | 3 of 5 return templates/placeholders | `live-test-results3.log`: Cover Letter returns literal string, Interview Prep returns template STAR, Gap Analysis returns parameterized template | Layer 0 |
| PC2 | Generated artifacts are persisted and listable | List endpoints return `[]` after generation | `live-test-results3.log`: `vprs: []`, `cover_letters: []` post-generation | Layer 1 |
| PC3 | Auth is tested with auth enabled | Tests run with `Auth Enabled: false` | `live-test-results3.log` header line | Layer 2 |
| PC4 | Cognito is the auth provider | Custom JWT authorizer; Cognito decision deferred | `BETA_PLAN_DESIGN.md` §6.2 lists as open choice | Layer 2 |
| PC5 | Health check reflects actual infrastructure | Reports `"bedrock": "healthy"` | `live-test-results3.log` health check response | Layer 1 |
| PC6 | Single DAL pattern across all handlers | CVTable (silent failures) and DynamoDalHandler (proper) coexist | `REFACTOR2_PLAN.md` documents the split | Layer 1 |
| PC7 | No duplicate route surfaces | `/api/cv` vs `/users/me/cv`, `/api/vpr` vs `/vpr/generate`, etc. | Swagger JSON shows both sets active | Layer 2 |

### 2.2 Precondition Resolution Requirements

- Each precondition gets a **binary pass/fail test** defined in the invariant table.
- All preconditions resolved in Layers 0-2 must pass before Layer 3+ work begins.
- Precondition resolution is tracked daily with evidence artifacts.

---

## 3. Scope Cutline

### 3.1 Must-Ship (P0)

All items required for the core claim (§1.1) and invariants (§4) to pass.

| Area | Scope |
|---|---|
| Auth | Cognito registration, login, token refresh, protected route enforcement |
| CV | Upload, list, select |
| Job | Create, list, get |
| Gap Analysis | AI-generated questions from CV + job context; response submission |
| VPR | Generate (async), status polling, retrieve, list |
| CV Tailoring | Generate (async), status polling, retrieve, list |
| Cover Letter | Generate (AI, not template), status polling, retrieve, list |
| Interview Prep | Generate (AI, not template), status polling, retrieve, list |
| Persistence | All generated artifacts stored and listable |
| Application State | Canonical lifecycle model with state recovery on page reload |
| Trial Enforcement | 14-day / 3-application limit with atomic credit checks |
| Usage Endpoint | `GET /users/me/usage` (trial days left, credits remaining, applications used) |
| Route Surface | Single canonical route per operation; duplicates removed |
| Frontend Shell | Functional workflow UI with polling, loading/error/empty states, state recovery |
| Staging | `stage.careervp.com` with TLS 1.2, custom domain, smoke tested |
| Observability | Lambda instrumentation for Claude API token/cost tracking; alerts |

### 3.2 Should-Ship If Time Allows (P1)

| Item | Dependency |
|---|---|
| `POST /auth/logout` | Cognito integration (Layer 2) |
| `POST /auth/forgot-password` + `POST /auth/reset-password` | Cognito integration (Layer 2) |
| `GET /users/me/subscription` | Trial model (Layer 5) |
| `POST /subscription/create-checkout` + `POST /subscription/portal` | Stripe integration |
| `POST /webhooks/stripe` | Stripe integration |
| `GET /artifacts/{artifactId}/download?format=docx` | Artifact persistence (Layer 1) |

### 3.3 Explicitly Deferred (P2)

| Item | Reason Deferred |
|---|---|
| `/applications` listing and detail/finalize/regenerate flow | Not required for core beta claim |
| Full billing portal/history UX | Not critical to beta readiness |
| Step Functions replatform | Explicitly out of scope (BETA_PLAN_DESIGN.md §2.2) |
| Full admin dashboard | Post-beta feature |
| Advanced analytics and collaboration | V2 feature set |
| Edit/regenerate/delete artifacts | Not in core claim; requires application state model maturity |

---

## 4. Invariant Table (Non-Negotiable Requirements)

### 4.1 Invariants

Each invariant is framed as a **falsifiable statement** with a specific failure detector.

| ID | Invariant | Falsification Test | Pass Metric |
|---|---|---|---|
| I1 | Every generator endpoint calls Claude and returns non-template output | Regex scan for known template strings (`"Generated cover letter for request"`, `"What quantifiable examples show your impact in core competency"`, `"Situation for question"`, `"describe a relevant STAR example"`) across 50 runs | 0 template matches in 50 runs |
| I2 | Every generated artifact is persisted to DynamoDB and retrievable via its list endpoint | For each artifact type: generate → immediate list → assert non-empty array with matching artifact ID | 100% roundtrip success across 50 runs |
| I3 | Cognito JWT authorizer is the sole identity source on all protected routes | Hit every protected route with: (a) no token → 401, (b) expired token → 401, (c) valid token for wrong user → 403 or scoped data, (d) valid token → 200 | All 4 scenarios pass on all protected routes |
| I4 | No payload-based or header-based identity fallback exists in any handler | Static analysis: grep all protected handlers for `event['body']` user_id extraction, `X-User-Id` header extraction, `event.get('requestContext', {}).get('identity')` patterns | 0 matches across all protected handlers |
| I5 | Trial enforcement blocks application #4 and post-14-day access | Create user → exhaust 3 applications → assert 4th returns upgrade-required. Simulate day-15 → assert access blocked. Concurrent create test (5 parallel requests at limit boundary) → assert no overcount | All 3 sub-tests pass |
| I6 | Frontend state survives page reload at every workflow step | At each of 7 workflow steps (CV upload, job create, gap questions, gap responses, artifact generation, artifact viewing, artifact listing): execute reload → assert user returns to same state with no data loss | 7/7 steps pass reload test |
| I7 | One canonical route per operation, no duplicate surfaces | Count deployed API Gateway routes and compare to frozen spec. Assert no `/api/*` shadow routes exist alongside `/resource/*` routes for the same operation | Route count matches spec exactly |
| I8 | Async operations complete within SLA and polling returns real status transitions | For VPR, CV Tailoring, Cover Letter, Interview Prep, Gap Analysis: measure p50/p95/p99 latency over 50 runs. Assert status transitions through `pending → processing → completed` (not stuck at any state). Assert: VPR < 90s, CV Tailoring < 60s, Cover Letter < 60s, Interview Prep < 60s, Company Research < 90s | All SLAs met at p95; all status transitions observed |

### 4.2 Invariant-to-Proof Traceability

| Invariant | Proof Artifact(s) | Codex Invariant Mapping |
|---|---|---|
| I1 | E1: `generator-output-audit.json` | R1 (strengthened: template detection) |
| I2 | E2: `persistence-roundtrip-report.json` | R1, R2 (strengthened: explicit roundtrip) |
| I3 | E3: `auth-abuse-matrix.json` | R4 (locked to Cognito) |
| I4 | E4: `identity-extraction-audit.txt` | R4 (strengthened: static analysis) |
| I5 | E5: `trial-enforcement-report.json` | R5 (unchanged) |
| I6 | E6: `state-recovery-matrix.json` | NEW (no Codex equivalent) |
| I7 | E7: `route-surface-diff.txt` | R3 (strengthened: duplicate detection) |
| I8 | E8: `async-sla-report.json` | R1 (new dimension: latency + transitions) |

### 4.3 Relationship to Codex Invariants (R1-R6)

| Codex ID | Codex Description | Disposition |
|---|---|---|
| R1 | End-to-end workflow correctness | Split into I1 (generator reality), I2 (persistence), I8 (async SLA) |
| R2 | Single workflow state truth | Covered by I2 (persistence) and I6 (state recovery) |
| R3 | Contract fidelity | Refined as I7 (route surface) |
| R4 | Auth/security integrity | Split into I3 (Cognito enforcement) and I4 (no identity fallback) |
| R5 | Trial enforcement correctness | Preserved as I5 |
| R6 | Operational readiness | Addressed in Layer 6 tasks; evidence via staging smoke and ops drill |

---

## 5. Evidence Proof Pack

### 5.1 Required Proof Artifacts

| ID | Artifact | Proves | How Generated | Format |
|---|---|---|---|---|
| E1 | `generator-output-audit.json` | I1 | Automated test script: 50 runs × 5 generators against staging. Each response scanned against template regex patterns. | JSON: `{ generator, run_id, is_template: bool, template_match: string|null, response_excerpt }` |
| E2 | `persistence-roundtrip-report.json` | I2 | Automated test: for each artifact type, generate → wait for completion → list → assert ID present. 50 runs. | JSON: `{ artifact_type, run_id, generated_id, list_contains_id: bool, list_response_length }` |
| E3 | `auth-abuse-matrix.json` | I3 | Security test suite against staging with Cognito enabled. Each protected route tested with 4 token scenarios. | JSON: `{ route, method, scenario, expected_status, actual_status, pass: bool }` |
| E4 | `identity-extraction-audit.txt` | I4 | Static grep across all handler source files. Pattern: `event['body'].*user_id`, `headers.*X-User-Id`, `event.get('requestContext').*identity`. | Text: grep output with file:line for any matches. Empty = pass. |
| E5 | `trial-enforcement-report.json` | I5 | Trial test suite: (a) create user, generate 3 applications, attempt 4th; (b) simulate day-15 expiry; (c) 5 concurrent creates at limit boundary. | JSON: `{ test_name, expected_outcome, actual_outcome, pass: bool }` |
| E6 | `state-recovery-matrix.json` | I6 | Frontend E2E suite (Playwright/Cypress): at each workflow step, execute page reload, assert correct state restoration. | JSON: `{ step_name, pre_reload_state, post_reload_state, data_preserved: bool, pass: bool }` |
| E7 | `route-surface-diff.txt` | I7 | `aws apigateway get-resources` output diffed against frozen spec. Flag any route that exists in deployment but not in spec, or vice versa. | Text: diff output. Empty diff = pass. |
| E8 | `async-sla-report.json` | I8 | 50-run timing capture for all async operations. Record status transition timestamps. Calculate p50/p95/p99. | JSON: `{ operation, run_id, status_transitions: [{status, timestamp}], total_ms, sla_met: bool }` |

### 5.2 Freshness and Validity Rules

| Rule | Requirement |
|---|---|
| Maximum evidence age at sign-off | 24 hours |
| Evidence environment | Must be `staging` (not `dev` or `local`) |
| Evidence must reflect | HEAD commit of deployed stage |
| Re-run trigger | Any deployment to staging after evidence generation |
| Storage location | `docs/beta/evidence/` |

### 5.3 Evidence Bundle Layout

```
docs/beta/evidence/
├── I1_generators/
│   └── generator-output-audit.json
├── I2_persistence/
│   └── persistence-roundtrip-report.json
├── I3_auth/
│   └── auth-abuse-matrix.json
├── I4_identity/
│   └── identity-extraction-audit.txt
├── I5_trial/
│   └── trial-enforcement-report.json
├── I6_state_recovery/
│   └── state-recovery-matrix.json
├── I7_routes/
│   └── route-surface-diff.txt
├── I8_async_sla/
│   └── async-sla-report.json
└── SIGN_OFF.md
```

---

## 6. Architecture Decisions (Locked for Beta)

These decisions are **closed**. They are not open for debate during the sprint. Reopening any decision requires explicit justification and schedule impact assessment.

### 6.1 Auth: Cognito JWT Authorizer

**Decision:** Migrate from custom JWT Lambda authorizer to Cognito JWT authorizer on API Gateway.

**Rationale:**
- User stated: "Cognito should be implemented and integrated at this stage."
- `BETA_PLAN_DESIGN.md` §3.1: "Cognito + API Gateway authentication/authorization."
- `BETA_PLAN_DESIGN.md` §3.2: `AUTH_NEVER_TRUST_PAYLOAD`, `AUTH_NO_BYPASS`, `AUTH_USE_MIDDLEWARE`.
- Cognito provides registration, login, token refresh, password reset out of the box.
- Eliminates custom token generation/validation code as attack surface.

**Implementation scope:**
- Cognito User Pool + App Client.
- API Gateway Cognito JWT authorizer replacing custom Lambda authorizer.
- All protected handlers extract identity from `event['requestContext']['authorizer']['claims']` only.
- Remove all `X-User-Id` header fallback and `event['body']` identity extraction from protected handlers.
- Frontend: Cognito SDK (Amplify Auth or `amazon-cognito-identity-js`) for registration, login, token refresh.

**Spec to generate:** `beta_auth_cognito_spec.yaml`

### 6.2 Orchestration: Frontend-Driven with Backend State Recovery

**Decision:** Frontend drives the workflow sequence. Backend provides a state recovery endpoint.

**Rationale:**
- No Step Functions; DynamoDB state machine is the current async primitive.
- Frontend already needs to manage polling for async operations.
- User requirement: "If I choose a frontend designed orchestrator, there must be a state monitor if the user reloads the page."
- 13-day timeline does not allow backend orchestration layer to be designed, built, and tested.

**Implementation scope:**
- Frontend chains: auth → CV upload → job create → gap questions → gap responses → trigger artifact generation → poll each artifact → display results.
- Backend: canonical Application state model in DynamoDB.
  - State recovery: `GET /applications/{applicationId}` returns current workflow step + all completed artifact references.
  - On page reload: frontend calls state recovery endpoint, determines current step, resumes UI at that step.
- Artifact generation: frontend fires all 4 artifact generation requests (VPR, CV Tailoring, Cover Letter, Interview Prep) after gap response submission. Backend processes independently. Frontend polls each.

**Critical constraint:** State recovery endpoint must return enough information for the frontend to reconstruct the UI at any workflow step without re-executing previous steps.

**Spec to generate:** `beta_application_state_model_spec.yaml`

### 6.3 DAL: DynamoDalHandler as Canonical Pattern

**Decision:** DynamoDalHandler is the single DAL pattern. CVTable is deprecated and replaced.

**Rationale:**
- CVTable uses silent failure patterns (swallow exceptions, return empty).
- DynamoDalHandler has proper error handling, observability, and consistent interface.
- Two competing DAL patterns create unpredictable behavior under failure conditions.

**Implementation scope:**
- Audit all handlers for CVTable usage.
- Replace with DynamoDalHandler calls.
- Verify error propagation (no silent swallows).

**Spec to generate:** Included in `beta_execution_runbook.md` Layer 1 tasks.

### 6.4 Route Surface: Single Canonical Set

**Decision:** Freeze one canonical route surface. Remove duplicate routes.

**Rationale:**
- Current Swagger shows duplicates: `/api/cv` vs `/users/me/cv`, `/api/vpr` vs `/vpr/generate`, `/api/cv-tailoring` vs `/cv-tailoring/generate`.
- Duplicate routes cause contract ambiguity, test duplication, and frontend confusion.
- `BETA_PLAN_DESIGN.md` §4.1: "Freeze endpoint contracts after day 4 of implementation."
- `BETA_PLAN_DESIGN.md` §10: "Canonical API route prefix decision (`/api/*` or non-prefix), then freeze."

**Implementation scope:**
- Choose canonical route set (decision needed: `/api/*` prefix or resource-based).
- Remove non-canonical routes from API Gateway.
- Update Swagger/OpenAPI to reflect canonical routes only.
- Regenerate API client for frontend from frozen contract.
- Contract freeze after Layer 2 completion (target: Day 6).

**Spec to generate:** `beta_api_contract_freeze_spec.yaml`

### 6.5 Async Pattern: SQS + Worker Lambda + Status Polling

**Decision:** Keep existing async pattern for long-running operations. Do not introduce Step Functions.

**Rationale:**
- VPR already uses this pattern and is the only fully working AI endpoint.
- `BETA_PLAN_DESIGN.md` §2.2: "Full Step Functions replatform: Out of Scope."
- Proven pattern: request → SQS → Worker Lambda → DynamoDB status update → frontend polls `GET /status`.

**Implementation scope:**
- Ensure all async generators (VPR, CV Tailoring, Cover Letter, Interview Prep, Gap Analysis) use the same SQS + Worker + Polling pattern.
- Each async operation must transition through: `pending → processing → completed` (or `failed`).
- Frontend polls at configurable interval (recommended: 3s initial, exponential backoff to 10s, timeout at 5 minutes).

### 6.6 Application State Model

**Decision:** Introduce a canonical Application lifecycle model in DynamoDB.

**Rationale:**
- No application state model exists today.
- Frontend state recovery (I6) requires knowing which workflow step the user is on.
- Trial counting (I5) requires knowing when an application is "created" vs "in progress" vs "completed."
- Without a state model, trial credits can be double-counted or under-counted.

**Lifecycle states:**
```
created → cv_selected → job_created → gap_questions_generated → gap_responses_submitted → artifacts_generating → artifacts_completed
```

**Failure states:**
```
Any state → failed (with error detail and retry eligibility)
```

**DynamoDB schema (conceptual):**
```
PK: USER#{userId}
SK: APP#{applicationId}
Attributes:
  - status: string (lifecycle state)
  - cv_id: string
  - job_id: string
  - gap_question_set_id: string
  - gap_response_set_id: string
  - artifacts: map { vpr_id, cv_tailoring_id, cover_letter_id, interview_prep_id }
  - artifact_statuses: map { vpr: "completed", cv_tailoring: "processing", ... }
  - created_at: ISO-8601
  - updated_at: ISO-8601
  - trial_credit_charged: boolean
```

**Spec to generate:** `beta_application_state_model_spec.yaml`

---

## 7. Dependency-Ordered Task Backlog

Tasks are ordered by **what unblocks what**. Nothing downstream is valid if its upstream dependency is broken. Each task references the invariant(s) it satisfies and the precondition(s) it resolves.

### 7.0 Layer 0: Generator Reality

**Unblocks:** Everything. If generators return templates, the core claim is false regardless of all other work.

**Resolves:** PC1

**Satisfies:** I1, I8

| Task ID | Task | Detail | Output |
|---|---|---|---|
| L0.1 | Fix Cover Letter generator to call Claude | Current: returns `"Generated cover letter for request {id}"`. Required: call Claude with CV summary, job description, gap responses, company context. Use Sonnet 4.5. | Handler returns AI-generated cover letter |
| L0.2 | Fix Interview Prep generator to call Claude | Current: returns template STAR (`"Situation for question 1"`). Required: call Claude with CV, job description, VPR analysis. Generate role-specific questions with STAR-framework model answers. | Handler returns AI-generated interview prep |
| L0.3 | Fix Gap Analysis generator to call Claude | Current: returns parameterized templates (`"What quantifiable examples show your impact in core competency N"`). Required: call Claude with parsed CV and job description. Generate questions with `[CV IMPACT]`/`[INTERVIEW ONLY]` tags per architecture spec. | Handler returns AI-generated gap questions |
| L0.4 | Validate CV Tailoring AI output quality | Current: returns data but `cv_id: null`, ATS score 7 (below 8.0 target), relevance 6.7%. Required: fix null cv_id, validate scores above threshold, confirm AI rewriting (not pass-through). | CV Tailoring returns valid cv_id, ATS >= 8.0 |
| L0.5 | Reduce Company Research latency | Current: 150 seconds. Required: < 90 seconds or make fully async with polling. Investigate: is this a prompt issue, API timeout, or unnecessary sequential calls? | Company Research < 90s or async with polling |

**Codex task mapping:** T8 (partial — Codex says "remove placeholder behavior" but doesn't specify which generators are broken or why).

### 7.1 Layer 1: Persistence and Data Integrity

**Unblocks:** List/retrieve endpoints, state model, frontend data display.

**Depends on:** Layer 0 (generators must produce real output to persist).

**Resolves:** PC2, PC5, PC6

**Satisfies:** I2

| Task ID | Task | Detail | Output |
|---|---|---|---|
| L1.1 | Fix artifact persistence in DynamoDB | Generated artifacts must be written to DynamoDB with correct keys so list endpoints return them. Investigate: are generators writing to the correct table/index? Is the GSI for user-scoped queries configured? | All list endpoints return generated artifacts |
| L1.2 | Unify DAL: DynamoDalHandler everywhere | Audit all handlers for CVTable usage. Replace with DynamoDalHandler. Verify error propagation (no silent swallows). Test: induce a DynamoDB failure and confirm the handler returns a 5xx, not a 200 with empty data. | Single DAL pattern; CVTable removed |
| L1.3 | Fix health check endpoint | Remove stale `"bedrock": "healthy"` reference. Report actual infrastructure: Anthropic API connectivity, DynamoDB table status, SQS queue status, Cognito pool status (after Layer 2). | Health check reflects real infrastructure |
| L1.4 | Validate all list endpoints return correct data | For each artifact type: generate → poll until complete → call list → assert artifact appears. This is the E2 proof artifact generation test, run as part of Layer 1 validation. | Persistence roundtrip test passes for all types |

**Codex task mapping:** T8 (partial), T5 (partial — state model is Layer 3).

### 7.2 Layer 2: Auth and Route Surface (Cognito)

**Unblocks:** Frontend auth, security invariants, trial enforcement (identity-dependent).

**Depends on:** None (can start in parallel with Layer 0 from Day 3).

**Resolves:** PC3, PC4, PC7

**Satisfies:** I3, I4, I7

| Task ID | Task | Detail | Output |
|---|---|---|---|
| L2.1 | Create Cognito User Pool + App Client | Configure user pool with email verification, password policy, required attributes (email, name). Create app client with SRP auth flow. Configure token expiration (access: 1hr, refresh: 30d). | Cognito User Pool ARN, App Client ID |
| L2.2 | Configure API Gateway Cognito JWT Authorizer | Replace custom Lambda authorizer with Cognito JWT authorizer on API Gateway. Configure issuer URL and audience. Apply to all protected routes. | API Gateway uses Cognito authorizer |
| L2.3 | Update all protected handlers for Cognito claims | All handlers extract identity from `event['requestContext']['authorizer']['claims']['sub']` (Cognito user ID) and `event['requestContext']['authorizer']['claims']['email']`. Remove all `X-User-Id` header extraction. Remove all `event['body']` user_id extraction. Remove all `AUTH_NO_BYPASS` flag checks. | Identity comes exclusively from Cognito claims |
| L2.4 | Register and login endpoints via Cognito | `POST /auth/register`: Cognito SignUp + auto-confirm or email verification flow. `POST /auth/login`: Cognito InitiateAuth (USER_SRP_AUTH). `POST /auth/refresh`: Cognito InitiateAuth with REFRESH_TOKEN. Map Cognito responses to existing API response contracts. | Auth endpoints use Cognito |
| L2.5 | Deduplicate route surface | Choose canonical route set. Remove non-canonical routes from API Gateway and CDK. Update OpenAPI spec. Candidates for removal: `/api/cv` (keep `/users/me/cv`), `/api/vpr` (keep `/vpr/generate`), `/api/cv-tailoring` (keep `/cv-tailoring/generate`). Decision required on prefix convention. | Single canonical route per operation |
| L2.6 | Enforce TLS 1.2 on API Gateway custom domains | Current: TLS 1.0 security policy. Required: `TLS_1_2` minimum version on all custom domain configurations in CDK. | API Gateway custom domains enforce TLS 1.2 |
| L2.7 | CORS allowlist (no wildcard in staging/prod) | Configure API Gateway CORS to allow only `stage.careervp.com`, `dev.careervp.com`, `careervp.com`. No wildcard `*` in staging or prod. Per `BETA_PLAN_DESIGN.md` §3.2: `SEC_CORS_RESTRICTION`. | Environment-specific CORS allowlist |
| L2.8 | Enable auth in test suite | Remove `Auth Enabled: false` bypass. All integration/E2E tests must use real Cognito tokens. Create test user provisioning script. | Test suite runs with auth enabled |
| L2.9 | Contract freeze | After L2.5 completion: export OpenAPI from deployed stage, freeze as canonical contract, generate typed API client for frontend. No route changes after this point without explicit approval. | Frozen OpenAPI spec + generated client |

**Codex task mapping:** T1 (freeze routes), T2 (regenerate OpenAPI), T3 (auth-context-only), T4 (CORS).

### 7.3 Layer 3: Application State Model

**Unblocks:** Frontend state recovery, trial counting, artifact lifecycle tracking.

**Depends on:** Layer 1 (persistence must work), Layer 2 (identity must be Cognito-based).

**Satisfies:** I6 (partial — frontend must implement recovery UI)

| Task ID | Task | Detail | Output |
|---|---|---|---|
| L3.1 | Design canonical Application lifecycle | Define states: `created → cv_selected → job_created → gap_questions_generated → gap_responses_submitted → artifacts_generating → artifacts_completed`. Define failure states and retry eligibility. Define legal transitions (no skipping steps). | State model spec document |
| L3.2 | Implement Application table in DynamoDB | Create DynamoDB table/GSI for Application records. Schema per §6.6. Implement CRUD operations via DynamoDalHandler. | Application state persistence |
| L3.3 | Implement state transition logic | Each workflow step (CV select, job create, gap generate, gap respond, artifact generate) updates Application state atomically. Use DynamoDB conditional writes to enforce legal transitions. | Atomic state transitions |
| L3.4 | Implement state recovery endpoint | `GET /applications/{applicationId}` returns: current state, all completed artifact references, all intermediate data (CV ID, job ID, gap question set, etc.). Frontend uses this on page reload to reconstruct UI position. | State recovery endpoint |
| L3.5 | Implement application list endpoint | `GET /applications` returns all applications for the authenticated user, with current state and summary data. Needed for frontend to show application history and resume incomplete applications. | Application list endpoint |
| L3.6 | Wire trial counting to application state | Trial credit is charged on `created` transition (not on individual artifact generation). DynamoDB conditional write: decrement credit only if `trial_credit_charged` is false for this application. Prevents double-counting on retry/regenerate. | Trial counting tied to application lifecycle |

**Codex task mapping:** T5 (application state model), T6 (partial — trial ledger).

### 7.4 Layer 4: Frontend Shell

**Unblocks:** E2E user workflow, state recovery proof (I6), visual demo for stakeholders.

**Depends on:** Layer 2 (auth + frozen contract), Layer 3 (state model + recovery endpoint).

**Satisfies:** I6 (full — implements recovery UI)

| Task ID | Task | Detail | Output |
|---|---|---|---|
| L4.1 | Scaffold app + Cognito auth integration | Next.js + TypeScript (per `BETA_PLAN_DESIGN.md` §10 recommendation). Cognito SDK for registration, login, token refresh, route guards. Environment config for dev/staging/prod Cognito pool IDs. | App skeleton with working auth |
| L4.2 | Generate typed API client from frozen contract | Use OpenAPI Generator or similar tool with the frozen contract from L2.9. All API calls go through this client. No manual `fetch` to API endpoints. | Typed API client |
| L4.3 | Implement state monitor (page reload recovery) | On every page load: call `GET /applications/{id}` (or `GET /applications` to find active application). Compare server state to current page. If mismatch: redirect to correct workflow step. If no active application: show dashboard/start screen. | State recovery on reload |
| L4.4 | Implement workflow pages | Module structure: auth → profile → CV management → job creation → gap questions → gap responses → artifact generation (with parallel polling) → artifact viewing. Each page handles: loading state, error state, empty state, data state. | Complete workflow UI |
| L4.5 | Implement polling for async operations | Poll each artifact status endpoint at 3s initial, exponential backoff to 10s, timeout at 5 minutes. Show progress indicators per artifact. Handle: still processing, completed (show result), failed (show retry option). | Polling UI with progress indicators |
| L4.6 | Loading, error, and empty states | Every page that loads data must handle: (a) loading spinner during fetch, (b) error message with retry on API failure, (c) empty state with call-to-action when no data exists, (d) data display when results exist. | Complete state handling |

**Codex task mapping:** T9 (Codex had this as a single task "Frontend functional shell for full workflow" — now decomposed into 6 subtasks).

### 7.5 Layer 5: Trial Enforcement

**Unblocks:** Conversion path, trial invariant proof.

**Depends on:** Layer 3 (application state model — trial counts applications, not artifacts).

**Satisfies:** I5

| Task ID | Task | Detail | Output |
|---|---|---|---|
| L5.1 | Implement atomic credit check + decrement | DynamoDB conditional write: on Application `created` transition, decrement user's remaining credits. Condition: `remaining_credits > 0`. If condition fails: return `{ "error": "trial_limit_reached", "upgrade_url": "..." }` with HTTP 403. | Atomic trial enforcement |
| L5.2 | Implement trial expiry check | On every protected API call (or at application creation): check if user's trial start date + 14 days < now. If expired: return `{ "error": "trial_expired", "upgrade_url": "..." }` with HTTP 403. | Time-based trial enforcement |
| L5.3 | Implement `GET /users/me/usage` | Response: `{ "trial_days_remaining": int, "applications_used": int, "applications_remaining": int, "trial_expires_at": ISO-8601 }`. Query: user's trial start date + application count from Application table. | Usage endpoint |
| L5.4 | Race condition test | 5 concurrent `POST /applications` requests at the limit boundary (2 credits remaining, 5 simultaneous creates). Assert: exactly 2 succeed, 3 return 403. DynamoDB conditional writes should handle this atomically. | Concurrency test passes |

**Codex task mapping:** T6 (trial usage ledger), T7 (`GET /users/me/usage`).

### 7.6 Layer 6: Operational Readiness

**Unblocks:** Launch confidence, incident response capability.

**Depends on:** Layers 0-5 (operational tooling wraps working system).

**Satisfies:** Codex R6

| Task ID | Task | Detail | Output |
|---|---|---|---|
| L6.1 | Configure custom domains + DNS | Map `dev.careervp.com` and `stage.careervp.com` to API Gateway `/prod`. CDK custom domain with `TLS_1_2` security policy. Output DNS CNAME target values for Cloudflare configuration. Validate with `curl -v https://stage.careervp.com/health`. | Custom domains live and verified |
| L6.2 | Lambda instrumentation for Claude API cost | Per-request logging: model, input/output tokens, cost estimate, agent name, user_id, application_id. Write to DynamoDB usage table. Per `BETA_PLAN_DESIGN.md` §3.1. | Token/cost tracking per request |
| L6.3 | Daily cost aggregation + alerting | EventBridge scheduled Lambda: aggregate daily token/cost records. Emit CloudWatch custom metrics. SNS alert for: daily cost > $X threshold, single-request cost anomaly (> 3σ), error rate > 5%. | Cost visibility and alerting |
| L6.4 | Staging smoke test | Script that exercises: register → login → upload CV → create job → generate gap questions → submit responses → generate all artifacts → poll to completion → verify all list endpoints → verify trial decrement. Run against `stage.careervp.com`. | Staging smoke script + pass report |
| L6.5 | Rollback procedure | Document: (a) how to deploy previous version via CDK, (b) how to verify rollback success, (c) what data migrations are/aren't reversible. Test: deploy current version, deploy previous version, verify system works. | Rollback procedure documented and tested |
| L6.6 | Regenerate OpenAPI from deployed stage | After all backend changes complete: export actual deployed API contract from API Gateway. Diff against frozen spec (L2.9). Any differences must be reconciled or documented. This is proof artifact E7. | Deployed-vs-frozen contract diff |

**Codex task mapping:** T10 (staging domain), T11 (instrumentation), T2 (regenerate OpenAPI).

### 7.7 Layer 7: Evidence Generation and Sign-Off

**Unblocks:** Launch decision.

**Depends on:** All previous layers complete.

| Task ID | Task | Detail | Output |
|---|---|---|---|
| L7.1 | Generate E1: generator-output-audit.json | Run 50-iteration test against staging. Each iteration generates all 5 artifact types. Scan responses for template patterns. | E1 artifact |
| L7.2 | Generate E2: persistence-roundtrip-report.json | Run 50-iteration test: generate → poll → list → verify ID present. | E2 artifact |
| L7.3 | Generate E3: auth-abuse-matrix.json | Run auth security suite: every protected route × 4 token scenarios. | E3 artifact |
| L7.4 | Generate E4: identity-extraction-audit.txt | Run static analysis grep across all handler source. | E4 artifact |
| L7.5 | Generate E5: trial-enforcement-report.json | Run trial test suite: 3-app exhaust, day-15 expiry, concurrent creates. | E5 artifact |
| L7.6 | Generate E6: state-recovery-matrix.json | Run frontend E2E: 7 workflow steps × page reload. | E6 artifact |
| L7.7 | Generate E7: route-surface-diff.txt | Run `aws apigateway get-resources` diff against frozen spec. | E7 artifact |
| L7.8 | Generate E8: async-sla-report.json | Run 50-iteration timing capture for all async operations. | E8 artifact |
| L7.9 | Package sign-off bundle | Compile all E1-E8 into `docs/beta/evidence/`. Verify all pass. Generate `SIGN_OFF.md` with invariant × proof matrix, all timestamps, environment details. | Sign-off package |
| L7.10 | Go/no-go decision | All 8 proof artifacts pass → **GO**. Any artifact fails → **BLOCKED** with specific invariant ID, failure detail, and remediation required. | Recorded decision with date |

**Codex task mapping:** T12 (final regression and go/no-go).

---

## 8. Schedule Mapping

### 8.1 13-Day Timeline

Start date: Thursday, February 27, 2026. End date: Wednesday, March 11, 2026.

| Day | Date | Layer | Key Milestones | Parallel Track |
|---|---|---|---|---|
| 1 | Feb 27 (Thu) | L0 | Begin generator fixes (Cover Letter, Interview Prep, Gap Analysis) | — |
| 2 | Feb 28 (Fri) | L0 + L1 | Continue generator fixes; begin persistence audit | — |
| 3 | Mar 1 (Sat) | L0 + L1 | Generator fixes complete (target); persistence fixes in progress | L2 begins (Cognito setup) |
| 4 | Mar 2 (Sun) | L1 + L2 | Persistence validated; DAL unified; Cognito user pool + authorizer configured | — |
| 5 | Mar 3 (Mon) | L2 + L3 | Handler auth migration; route dedup; begin Application state model | — |
| 6 | Mar 4 (Tue) | L2 + L3 | Auth complete; contract freeze (L2.9); state model implementation | L4 begins (frontend scaffold) |
| 7 | Mar 5 (Wed) | L3 + L4 | State recovery endpoint; frontend auth integration | — |
| 8 | Mar 6 (Thu) | L4 + L5 | Frontend workflow pages; trial enforcement begins | — |
| 9 | Mar 7 (Fri) | L4 + L5 | **CUT TRIGGER DAY** — Frontend polling + state recovery; trial enforcement complete | Decision: on-track or scope-cut |
| 10 | Mar 8 (Sat) | L4 + L6 | Frontend completion; operational instrumentation begins | — |
| 11 | Mar 9 (Sun) | L6 | Custom domains, staging smoke, rollback test | — |
| 12 | Mar 10 (Mon) | L7 | Evidence generation: all 8 proof artifacts | — |
| 13 | Mar 11 (Tue) | L7 | Sign-off package; go/no-go decision | — |

### 8.2 Critical Path

```
L0 (generators) → L1 (persistence) → L3 (state model) → L4 (frontend) → L7 (evidence)
```

**Parallel path:** L2 (auth/Cognito) starts Day 3, independent of L0/L1 until handlers need auth migration.

**Second parallel path:** L5 (trial) depends on L3 but can start as soon as L3.6 is available.

### 8.3 Cut Triggers

| Trigger Point | Condition | Action |
|---|---|---|
| Day 5 | L0 not complete (generators still returning templates) | Escalate. Consider: are generators fixable or do they need rewrite? Assess if 8 remaining days are sufficient. |
| Day 7 | L2 not complete (Cognito not integrated) | Cut P1 auth endpoints (logout, forgot-password, reset-password). Accept Cognito basic flow only. |
| Day 9 | L3 not complete (no state model) | **Hard decision point.** Options: (a) ship without state recovery (I6 fails, launch blocked), (b) implement minimal state recovery (application status only, no artifact-level tracking), (c) extend deadline. |
| Day 9 | L4 < 50% complete | Accept lowest-fidelity UI. Cut all visual polish. Functional-only workflow. |
| Day 11 | L6 not complete | Accept minimal observability. Ship health check + basic CloudWatch. Cut daily rollup and SNS alerts. |

### 8.4 Fallback Plan and Cut Order

**Cut order 1 (first to go):** All P2 deferred items. Already cut.

**Cut order 2:** P1 payment/subscription endpoints (Stripe checkout, webhook, portal). These are independent of the core claim.

**Cut order 3:** P1 auth lifecycle (logout, forgot-password, reset-password). Cognito supports these out-of-box; frontend can omit the UI and users can use Cognito hosted UI as fallback.

**Cut order 4:** Artifact download endpoint (`GET /artifacts/{id}/download?format=docx`). Nice to have; not in core claim.

**Never cut:** Any work tied to invariants I1-I8. If an invariant cannot pass, launch is blocked — not silently scoped down.

### 8.5 Last-Week Survival Mode (Day 10+)

- Freeze all non-critical refactors.
- Accept low-fidelity UI (functional, not polished).
- Allow only blocker fixes tied to invariant failures.
- No new features, no "while we're at it" improvements.
- Daily evidence check: which proof artifacts can be generated today?

---

## 9. Risks and Adversarial Pre-Mortem

### 9.1 Primary Risks

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Generator fixes take longer than 3 days (prompt engineering + testing) | Medium | Critical — blocks everything | Start Day 1; VPR's working pattern is the template. If a generator can't be fixed in 3 days, assess whether the prompt or the handler architecture is the root cause. |
| Cognito migration breaks existing test infrastructure | Medium | High — blocks auth validation | L2.8 (enable auth in tests) is explicitly called out. Create test user provisioning script before switching authorizer. |
| Application state model design takes too long | Medium | High — blocks frontend state recovery and trial | L3.1 is a design task. Timebox to 4 hours. The schema in §6.6 is a starting point, not a research project. |
| Frontend team capacity is insufficient for 6 tasks in 4-5 days | High | Medium — UI quality drops | Accept low-fidelity. Prioritize: auth (L4.1), state recovery (L4.3), workflow pages (L4.4), polling (L4.5). Cut: visual polish, advanced error states. |
| Company Research 150s latency is unfixable in timeline | Medium | Low — not in core claim artifacts | Make it async with polling. If still too slow, demote to P1 and exclude from beta workflow. |
| DAL unification (CVTable removal) causes regressions | Low | High — breaks persistence | L1.2 is explicit. Test each handler after migration. Run E2 proof as validation. |
| Contract freeze (Day 6) happens before all routes are correct | Medium | High — frontend builds on wrong contract | L2.5 (route dedup) must complete before L2.9 (freeze). Enforce: no freeze until route audit passes. |

### 9.2 Strongest Dissent Position

> "You have 13 calendar days. Layer 0 alone — making 3 generators actually call Claude — is a multi-day effort because you need to understand why they're returning templates. Is it a feature flag? A fallback path? An unfinished handler? Then you need to write, test, and deploy real implementations. Layer 2 (Cognito migration) is a 2-3 day effort with API Gateway reconfiguration, Cognito user pool setup, and handler migration. Layer 3 (state model) doesn't exist at all — it needs design, implementation, and integration. You're looking at 8-10 days of Layer 0-3 work before you even start the frontend. That leaves 3-5 days for frontend, trial, ops, and evidence. The schedule doesn't work unless you cut scope or extend."

### 9.3 Prepared Counter-Arguments

| Attack | Defense | Evidence Required |
|---|---|---|
| "Generators are template stubs — this is vaporware" | Layer 0 is first priority. Nothing else starts until generators are real. VPR proves the async+Claude pattern works; other generators need to follow the same pattern. | E1: `generator-output-audit.json` with 0 template matches |
| "Auth bypass in tests means security is untested" | Cognito integration is Layer 2. Test suite auth enablement is L2.8. Auth abuse matrix is a required proof artifact. | E3: `auth-abuse-matrix.json` with all scenarios passing |
| "No state model means no reliable workflow" | Layer 3 builds it with explicit state recovery endpoint. The schema is defined (§6.6). This is implementation, not research. | E6: `state-recovery-matrix.json` with 7/7 steps passing |
| "Timeline is impossible" | Explicit cut order defined. Day 9 is a hard decision point. If Layers 0-3 aren't done by Day 9, launch is formally blocked — not silently slipped. Parallel tracks (L2 starts Day 3) compress the critical path. | Schedule adherence tracked daily |
| "Frontend state will break on reload" | I6 invariant specifically tests reload at every step. If it fails, launch is blocked. State recovery endpoint (L3.4) is the mechanism. | E6: `state-recovery-matrix.json` |
| "Trial enforcement will have race conditions" | DynamoDB conditional writes handle atomicity. Explicit concurrency test (L5.4) with 5 parallel requests at limit boundary. | E5: `trial-enforcement-report.json` with concurrency sub-test passing |
| "You're building too much in 13 days" | Core claim is narrow: one user, one workflow, five artifacts. No admin, no billing, no dashboard. P1/P2 are explicitly deferred. | Scope cutline (§3) is the defense |

---

## 10. Spec Generation Matrix

### 10.1 Specs To Generate (From This Outline)

| Spec ID | Spec Name | Generated From | Depends On |
|---|---|---|---|
| S1 | `beta_execution_runbook.md` | §7 (full task backlog), §8 (schedule) | All sections |
| S2 | `beta_api_contract_freeze_spec.yaml` | §6.4 (route surface), §7.2 L2.5/L2.9 | Swagger JSON + route decision |
| S3 | `beta_application_state_model_spec.yaml` | §6.6 (state model), §7.3 (Layer 3 tasks) | §6.2 (orchestration decision) |
| S4 | `beta_trial_enforcement_spec.yaml` | §7.5 (Layer 5 tasks), invariant I5 | §6.6 (state model — trial counts applications) |
| S5 | `beta_auth_cognito_spec.yaml` | §6.1 (Cognito decision), §7.2 (Layer 2 tasks) | Cognito architecture |
| S6 | `beta_release_gate_spec.yaml` | §5 (evidence proof pack), §7.7 (Layer 7 tasks) | All invariants defined |
| S7 | `beta_frontend_shell_spec.yaml` | §6.2 (orchestration), §7.4 (Layer 4 tasks) | Frozen contract (S2), state model (S3) |
| S8 | `beta_async_sla_spec.yaml` | §6.5 (async pattern), invariant I8 | Generator implementations (Layer 0) |

### 10.2 Minimum Metadata Per Spec

Every generated spec must include:

| Field | Description |
|---|---|
| `purpose` | What this spec defines and why |
| `owner` | Who is responsible for implementation |
| `preconditions` | What must be true before this spec can be implemented |
| `inputs` | What data/decisions this spec consumes |
| `outputs` | What artifacts this spec produces |
| `pass_criteria` | How to determine if implementation satisfies this spec |
| `fail_criteria` | What constitutes a failure |
| `linked_invariants` | Which invariants (I1-I8) this spec satisfies |
| `linked_tasks` | Which tasks (L0.1-L7.10) this spec covers |
| `linked_evidence` | Which proof artifacts (E1-E8) validate this spec |

### 10.3 Spec Generation Order

Specs must be generated in dependency order:

```
S5 (auth/cognito) ──┐
                     ├── S2 (contract freeze) ── S7 (frontend)
S3 (state model) ───┘                               │
     │                                               │
     └── S4 (trial) ────────────────────────────────┘
                                                     │
S8 (async SLA) ─────────────────────────────────────┘
                                                     │
S1 (execution runbook) ─────────────────────────────┘
                                                     │
S6 (release gate) ──────────────────────────────────┘
```

---

## 11. Ownership and Operating Cadence

### 11.1 Ownership Matrix

| Area | Layer(s) | Primary Owner | Core Deliverable |
|---|---|---|---|
| Generator fixes | L0 | Backend | 5 generators calling Claude with real output |
| Persistence + DAL | L1 | Backend | Artifacts stored and listable; single DAL |
| Cognito + auth + routes | L2 | Backend + Infra | Cognito authorizer on all protected routes |
| Application state model | L3 | Architecture + Backend | State model, recovery endpoint, trial integration |
| Frontend shell | L4 | Frontend | End-to-end UI with state recovery |
| Trial enforcement | L5 | Backend | Atomic credit checks, usage endpoint |
| Operational readiness | L6 | Operations + Infra | Custom domains, instrumentation, rollback |
| Evidence + sign-off | L7 | QA + Operations | 8 proof artifacts, sign-off package |

### 11.2 Daily Cadence

| Activity | Purpose |
|---|---|
| Daily status by layer (not by task category) | Track critical path progress |
| Daily precondition check | Are PC1-PC7 resolved? |
| Daily evidence update | Can any proof artifacts be generated today? |
| Daily risk review | Any unresolved invariant blockers? |
| Daily end-of-day decision | `on-track` / `scope-cut-needed` / `launch-at-risk` |

### 11.3 Go/No-Go Gate

**Required for GO:**
- All P0 tasks (L0-L7) complete.
- All invariants I1-I8 passed with evidence artifacts E1-E8 attached.
- All evidence < 24 hours old, generated from staging environment.
- Explicit decision recorded with date, approvers, and any conditions.

**Automatic NO-GO:**
- Any invariant fails with no remediation path within remaining time.
- Any precondition (PC1-PC7) unresolved.
- Evidence older than 24 hours at decision time.

---

## 12. Runbook Generation Inputs

This section provides the inputs required for the execution runbook (`S1`) to be generated from this outline.

### 12.1 Environment Prerequisites

| Prerequisite | Detail |
|---|---|
| AWS Account | With permissions for: API Gateway, Lambda, DynamoDB, SQS, Cognito, CloudWatch, SNS, S3, Route 53 / Cloudflare DNS |
| Cognito User Pool | Created per L2.1 spec |
| DynamoDB Tables | Existing tables + new Application table (L3.2) + Usage table (L6.2) |
| SQS Queues | Existing queues for async processing |
| S3 Buckets | Existing bucket for artifact storage (VPR uses this today) |
| Anthropic API Key | In SSM Parameter Store (not environment variables, not hardcoded) |
| Custom Domains | `dev.careervp.com`, `stage.careervp.com` DNS configured |
| CDK | Deployed and validated (`cdk synth`, `cdk diff` with no unintended deletions) |

### 12.2 Deployment Order

```
1. Cognito User Pool + App Client (L2.1)
2. API Gateway Cognito Authorizer (L2.2)
3. Handler auth migration (L2.3) — deploy updated handlers
4. Route deduplication (L2.5) — deploy API Gateway changes
5. Application state model table (L3.2) — deploy DynamoDB table
6. Generator fixes (L0.1-L0.5) — deploy updated handlers
7. Persistence fixes (L1.1-L1.4) — deploy updated handlers
8. State model endpoints (L3.3-L3.5) — deploy new handlers
9. Trial enforcement (L5.1-L5.3) — deploy updated handlers
10. Custom domains + TLS (L6.1) — deploy API Gateway config
11. Instrumentation (L6.2-L6.3) — deploy monitoring Lambda
12. Frontend (L4.1-L4.6) — deploy to hosting
```

### 12.3 Test Execution Procedures

| Test Suite | When To Run | What It Validates | Tool |
|---|---|---|---|
| Generator output audit (E1) | After L0 complete | I1 — no template outputs | Custom test script |
| Persistence roundtrip (E2) | After L1 complete | I2 — artifacts stored and listable | Custom test script |
| Auth abuse matrix (E3) | After L2 complete | I3 — Cognito enforcement | Security test suite |
| Identity extraction audit (E4) | After L2.3 complete | I4 — no fallback patterns | Static analysis grep |
| Trial enforcement (E5) | After L5 complete | I5 — credit limits and expiry | Trial test suite |
| State recovery matrix (E6) | After L4.3 complete | I6 — page reload recovery | Playwright/Cypress E2E |
| Route surface diff (E7) | After L6.6 complete | I7 — no duplicate routes | AWS CLI + diff |
| Async SLA report (E8) | After L0 + L1 complete | I8 — latency and status transitions | 50-run timing script |
| Staging smoke (L6.4) | After all layers | Full workflow on staging | End-to-end smoke script |

### 12.4 Rollback Procedures

| Scenario | Rollback Action | Verification |
|---|---|---|
| Bad Lambda deployment | `cdk deploy` with previous version tag | Smoke test passes |
| Cognito misconfiguration | Revert authorizer to previous (or temporarily disable while fixing) | Auth test suite passes |
| DynamoDB schema issue | Table schemas are additive; rollback by deploying previous handler code | CRUD operations pass |
| API Gateway route error | `cdk deploy` with previous API definition | Route diff matches expected |
| Frontend deployment failure | Deploy previous build to hosting | UI accessible and functional |

### 12.5 Alert Thresholds

| Alert | Threshold | Channel | Severity |
|---|---|---|---|
| Daily Claude API cost | > $50/day (adjust based on expected beta volume) | SNS → email | Warning |
| Single-request cost anomaly | > $2/request (3σ above mean) | CloudWatch alarm | Warning |
| Lambda error rate | > 5% errors in 5-minute window | CloudWatch alarm → SNS | Critical |
| API Gateway 5xx rate | > 1% in 5-minute window | CloudWatch alarm → SNS | Critical |
| DynamoDB throttling | > 0 throttled requests in 1-minute window | CloudWatch alarm | Warning |
| Async operation timeout | Any operation > 5 minutes | Application-level logging | Warning |

---

## 13. Security Checklist (From BETA_PLAN_DESIGN.md §3.2)

Explicit mapping of security rules to implementation tasks.

| Rule ID | Rule | Implementation Task | Verification |
|---|---|---|---|
| `AUTH_NEVER_TRUST_PAYLOAD` | user_id from auth context only | L2.3 | E4: identity-extraction-audit.txt |
| `AUTH_NO_BYPASS` | No auth disable flags | L2.3, L2.8 | E3: auth-abuse-matrix.json |
| `AUTH_USE_MIDDLEWARE` | Protected routes must consistently enforce auth | L2.2 | E3: auth-abuse-matrix.json |
| `SEC_CORS_RESTRICTION` | No wildcard CORS in prod/staging | L2.7 | Manual verification + E3 |
| `SEC_NO_EVENT_LOGGING` | Do not log full auth-bearing events | L2.3 (audit during migration) | Code review |
| `IAM_001` | Least-privilege IAM | CDK review | CDK diff audit |
| `IAM_002` | No hardcoded secrets | L2.3 (audit during migration) | Static analysis grep |

---

## 14. Known Gaps and Open Decisions

### 14.1 Decisions Required Before Sprint Start

| Decision | Options | Recommendation | Impact If Delayed |
|---|---|---|---|
| Canonical route prefix | `/api/*` prefix OR resource-based (e.g., `/vpr/generate`) | Resource-based (matches current VPR pattern, which is the only working AI endpoint) | Blocks L2.5, L2.9 (contract freeze) |
| Cognito email verification | Immediate verification OR auto-confirm for beta | Auto-confirm for beta (reduces friction for testers) | Blocks L2.1 |
| Company Research disposition | Fix latency OR make async OR demote to P1 | Make async with polling (consistent with other generators) | Blocks L0.5 |

### 14.2 Known Technical Debt Carried Into Beta

| Debt Item | Risk | Mitigation for Beta |
|---|---|---|
| No Step Functions orchestration | State consistency depends on frontend + conditional writes | Application state model (L3) with explicit transitions |
| No FVS quality validator | AI output quality not systematically verified | Manual review of E1 generator output audit |
| No edit/delete/regenerate | Users cannot correct artifacts | Deferred to P2; beta testers aware this is v1 |
| Single-region deployment | No failover | Acceptable for beta scale |
| No rate limiting | Potential abuse | Cognito + trial enforcement provide basic limits |

---

## Appendix A: Task ID Cross-Reference (This Outline ↔ Codex Task List)

| This Outline | Codex Task ID | Codex Task Description | Changes Made |
|---|---|---|---|
| L0.1-L0.5 | T8 | Remove placeholder artifact/status behavior | Decomposed into 5 specific generator fixes with root cause from live test data |
| L1.1-L1.4 | T5 (partial) | Define and implement canonical application state model | Separated persistence (L1) from state model (L3) |
| L2.1-L2.4 | T3 | Enforce auth-context-only identity extraction | Expanded to full Cognito migration per user decision |
| L2.5 | T1 | Freeze route strategy and deprecate duplicate surfaces | Unchanged scope |
| L2.6-L2.7 | T4 | Remove wildcard CORS in staging/prod paths | Added TLS 1.2 enforcement |
| L2.9 | T2 | Regenerate OpenAPI/Swagger from deployed stage | Moved to after route dedup; added client generation |
| L3.1-L3.6 | T5 | Define and implement canonical application state model | Expanded: added state recovery endpoint (I6), application list, trial wiring |
| L4.1-L4.6 | T9 | Frontend functional shell for full workflow | Decomposed into 6 subtasks; added state monitor requirement |
| L5.1-L5.4 | T6, T7 | Trial usage ledger + usage endpoint | Added concurrency test; tied counting to application lifecycle |
| L6.1 | T10 | Staging domain/TLS readiness and smoke test | Separated into domain config (L6.1) and smoke test (L6.4) |
| L6.2-L6.3 | T11 | Cost/usage instrumentation and alerting | Unchanged scope |
| L7.1-L7.10 | T12 | Execute final regression and go/no-go evaluation | Expanded: 8 specific proof artifacts instead of generic regression |
| — | T13-T18 | P1 tasks (logout, password reset, subscription, Stripe, download) | Preserved as P1 in §3.2 |
| — | T19-T20 | P2 tasks (applications listing, billing UX) | Preserved as P2 in §3.3 |

## Appendix B: New Tasks Not In Codex Original

| Task ID | Task | Why Added |
|---|---|---|
| L0.1-L0.3 | Fix specific generators to call Claude | Codex T8 was generic; live test data revealed 3 specific generators returning templates |
| L0.5 | Reduce Company Research latency | 150s latency discovered in live test data; not mentioned in Codex |
| L1.2 | DAL unification | CVTable vs DynamoDalHandler split documented in REFACTOR2_PLAN; not in Codex |
| L1.3 | Fix health check | Stale bedrock reference discovered in live test data; not in Codex |
| L2.1-L2.2 | Cognito setup | Codex deferred Cognito decision; user locked it as "implement now" |
| L2.8 | Enable auth in tests | Tests running with `Auth Enabled: false` discovered in live test data; not in Codex |
| L3.4 | State recovery endpoint | User requirement: "there must be a state monitor if the user reloads the page" |
| L3.5 | Application list endpoint | Required for frontend to show history and resume incomplete applications |
| L3.6 | Wire trial to application lifecycle | Prevents double-counting; not in Codex |
| L4.3 | State monitor (page reload) | User requirement; creates invariant I6 |
| L5.4 | Race condition test | Explicit concurrency test for trial enforcement; I5 sub-test |
