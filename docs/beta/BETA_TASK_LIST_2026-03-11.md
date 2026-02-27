# CareerVP Beta Structured Outline (Deadline: 2026-03-11)

## 1. Decision Statement (Go/No-Go Rule)
### 1.1 Core Claim (Falsifiable)
- By **Wednesday, March 11, 2026**, a new user can register/login and complete one full job application workflow on staging with no operator intervention.
- Workflow scope: CV upload/list -> job create/list/get -> gap questions/responses -> VPR generate/status -> CV tailoring generate/status -> cover letter generate/status -> interview prep generate/status.

### 1.2 Hard Launch Rule
- Launch only if all `R1-R6` invariants pass and all P0 tasks are complete.
- If any hard invariant fails, launch is blocked.

### 1.3 Baseline Facts
- Current OpenAPI v1 contract: 27 core operations.
- Existing core happy-path e2e exists.
- Beta scope documents require trial enforcement, staging subdomains, and operational visibility.

## 2. Scope Cutline
### 2.1 Must-Ship (P0)
- End-to-end workflow correctness.
- Security/auth integrity.
- Contract fidelity between deployed API and published API docs.
- Trial enforcement (14 days, 3 applications, correct counting trigger).
- Functional frontend shell for the full workflow.
- Staging subdomain readiness and release gates.
- Operational observability sufficient for beta support.

### 2.2 Should-Ship If Time Allows (P1)
- Auth lifecycle additions: logout, forgot/reset password.
- Subscription visibility and checkout entry points.
- Artifact download endpoint for docx export.

### 2.3 Explicitly Deferred (P2)
- Application dashboard/finalization abstractions beyond the core flow.
- Expanded billing portal/history UX.
- Post-beta architecture features (full Step Functions replatform, advanced analytics/admin).

## 3. Invariant Table (Non-Negotiable Requirements)
| ID | Invariant | Pass Metric | Evidence Artifact |
|---|---|---|---|
| R1 | End-to-end workflow correctness | >=95% pass over 50 staging runs | E2E run report + run logs |
| R2 | Single workflow state truth | One canonical application state model used across job/gap/artifacts | State model spec + transition tests |
| R3 | Contract fidelity | Deployed API equals frozen published OpenAPI | Contract diff report from deployed stage |
| R4 | Auth/security integrity | No identity from payload/header in protected routes; strict CORS allowlist; consistent 401/403 | Security negative test suite + auth matrix |
| R5 | Trial enforcement correctness | Correct 14-day/3-application behavior under concurrency and retries | Trial race test report + usage snapshots |
| R6 | Operational readiness | Alerts, metrics, and rollback exercised in staging | Ops drill report + alert evidence |

## 4. Architecture Choices Required To Satisfy Invariants
### 4.1 Contract and Routing
- Freeze one canonical route style and deprecate duplicate route surfaces.
- Treat deployed stage contract as source of truth; regenerate docs from deployment.

### 4.2 State Modeling
- Introduce a canonical `Application` lifecycle model binding:
  - `job`
  - `gap question generation`
  - `gap response submission`
  - `artifact generation states`
  - `trial usage accounting`
- Define legal state transitions and failure/retry behavior.

### 4.3 Auth and Security
- Enforce authorizer/JWT-context identity extraction only.
- Remove fallback identity extraction from payload or debug headers on protected routes.
- Apply environment-specific CORS allowlists with no wildcard in staging/prod.

### 4.4 Trial and Billing Boundary
- Trial enforcement is P0.
- Payments/subscriptions are P1 unless trial enforcement depends on billing linkage for correctness.

### 4.5 Frontend Strategy
- Functional, low-fidelity UI is acceptable for beta.
- Contract stability and workflow completeness outrank visual finalization.

## 5. Evidence Map (Proof Pack Required Before Sign-Off)
### 5.1 Proof Set
- `P1`: 50-run workflow execution report from staging.
- `P2`: OpenAPI contract extracted from deployed stage + repo diff.
- `P3`: Auth abuse test report (forged identity, cross-tenant access, missing token).
- `P4`: Trial concurrency/race-limit report.
- `P5`: Async reliability report (delays, retries, failures, idempotency).
- `P6`: Ops drill report (alert fired, triage performed, rollback validated).

### 5.2 Traceability Rule
- Every invariant `R1-R6` must link to at least one proof artifact.
- No invariant can be marked pass without machine-generated evidence.

## 6. Risks and Strong Counterarguments
### 6.1 Primary Risks
- Passing contract checks without validating runtime semantics.
- Split state across handlers/tables causing trial and workflow drift.
- Security regressions from mixed auth extraction patterns.
- Schedule compression (13-day practical window).
- Staging contract/doc mismatch creating frontend churn late in sprint.

### 6.2 Strongest Dissent Position
- "This is checklist compliance without runtime reliability; launch should be blocked until state consistency, auth invariants, and concurrency behavior are proven with data."

### 6.3 Response Strategy
- Convert each dissent point into an invariant-bound test/evidence item.
- If evidence cannot be produced, scope is cut or launch is blocked.

## 7. Task Backlog Mapped To Invariants
### 7.1 P0 Tasks
| Task ID | Task | Invariant(s) | Output |
|---|---|---|---|
| T1 | Freeze route strategy and deprecate duplicate surfaces | R3 | Frozen API route policy |
| T2 | Regenerate OpenAPI/Swagger from deployed stage | R3 | Published frozen contract artifact |
| T3 | Enforce auth-context-only identity extraction across protected handlers | R4 | Auth hardening PR + tests |
| T4 | Remove wildcard CORS in staging/prod paths | R4 | CORS policy implementation + tests |
| T5 | Define and implement canonical application state model | R2, R5 | State model spec + implementation |
| T6 | Implement trial usage ledger + atomic limit checks | R5 | Trial enforcement implementation |
| T7 | Add `GET /users/me/usage` with standardized response shape | R5 | Usage endpoint + contract tests |
| T8 | Remove placeholder artifact/status behavior from beta path | R1, R2 | Runtime-correct artifact flows |
| T9 | Frontend functional shell for full workflow | R1, R3 | End-to-end usable beta UI |
| T10 | Staging domain/TLS readiness and smoke test | R6 | Staging readiness report |
| T11 | Cost/usage instrumentation and alerting | R6 | Metrics + alarms + dashboard |
| T12 | Execute final regression and go/no-go evaluation | R1-R6 | Sign-off package |

### 7.2 P1 Tasks
| Task ID | Task | Output |
|---|---|---|
| T13 | `POST /auth/logout` | Endpoint + tests |
| T14 | `POST /auth/forgot-password` and `POST /auth/reset-password` | Endpoint set + tests |
| T15 | `GET /users/me/subscription` | Endpoint + contract |
| T16 | `POST /subscription/create-checkout` and `POST /subscription/portal` | Checkout/portal API |
| T17 | `POST /webhooks/stripe` | Webhook handler + verification tests |
| T18 | `GET /artifacts/{artifactId}/download` docx | Download capability |

### 7.3 P2 Deferred Tasks
| Task ID | Task | Reason Deferred |
|---|---|---|
| T19 | `/applications` listing and detail/finalize/regenerate flow | Not required for core beta claim |
| T20 | Full billing UX depth | Not critical to beta readiness definition |

## 8. Fallback Plan If Schedule Slips
### 8.1 Cut Order
- Cut order 1: all P2.
- Cut order 2: P1 payment/password-reset extensions.
- Never cut: any work tied to `R1-R6`.

### 8.2 Last-Week Survival Mode
- Freeze all non-critical refactors.
- Accept low-fidelity UI.
- Allow only blocker fixes tied to hard invariants.

## 9. Most Logical Presentation Sequence (For Stakeholders)
1. Decision statement and hard launch rule.
2. Scope cutline (P0/P1/P2).
3. Invariant table (`R1-R6`).
4. Architecture choices required for invariants.
5. Task backlog mapped to invariants.
6. Evidence map and required proof artifacts.
7. Risks, dissent position, and response strategy.
8. Fallback plan and cut order.
9. Final sign-off asks.

## 10. Runbook and Spec Generation Inputs
### 10.1 Runbook Inputs To Produce Next Stage
- Frozen contract artifact (OpenAPI generated from deployed stage).
- Invariant-to-test matrix.
- Environment prerequisites and deployment order.
- Test execution order and rollback procedure.
- Alert thresholds and incident response steps.

### 10.2 Specs To Generate Next Stage
- `beta_execution_runbook.md`
- `beta_api_contract_freeze_spec.yaml`
- `beta_application_state_model_spec.yaml`
- `beta_trial_enforcement_spec.yaml`
- `beta_auth_security_spec.yaml`
- `beta_release_gate_spec.yaml`

### 10.3 Minimum Metadata Required Per Spec
- Purpose.
- Owner.
- Preconditions.
- Inputs and outputs.
- Pass/fail criteria.
- Linked invariant IDs.

## 11. Final Sign-Off Ask
### 11.1 Required Sign-Off Roles
- Product/Architecture.
- Backend.
- Frontend.
- QA.
- Operations.

### 11.2 Sign-Off Condition
- All P0 tasks complete.
- All invariants `R1-R6` passed with attached evidence artifacts.
- Explicit go/no-go decision recorded with date and approvers.

## 12. Ownership and Operating Cadence (Runbook Seed)
### 12.1 Ownership Matrix
| Area | Primary Owner | Backup Owner | Core Deliverable |
|---|---|---|---|
| Contract and route freeze | Backend | Architecture | Frozen OpenAPI + route policy |
| Auth/security hardening | Backend | QA | Auth/CORS security test report |
| Application state model | Architecture | Backend | State model spec + transitions |
| Trial enforcement | Backend | Product | Trial ledger + usage endpoint |
| Frontend workflow shell | Frontend | Backend | End-to-end UI workflow |
| Staging/release operations | Operations | Backend | Smoke, rollback, and readiness report |
| Evidence packaging | QA | Operations | Sign-off evidence bundle |

### 12.2 Daily Cadence
- Daily standup: task status by `T1-T20`.
- Daily contract check: deployed-vs-frozen diff.
- Daily risk review: unresolved invariant blockers.
- Daily evidence update: append new proof artifacts.
- Daily end-of-day decision: `on-track`, `scope-cut-needed`, or `launch-at-risk`.

### 12.3 Evidence Bundle Layout
- `docs/beta/evidence/`
- `docs/beta/evidence/R1_workflow/`
- `docs/beta/evidence/R2_state_model/`
- `docs/beta/evidence/R3_contract/`
- `docs/beta/evidence/R4_security/`
- `docs/beta/evidence/R5_trial/`
- `docs/beta/evidence/R6_operations/`

### 12.4 Required Metadata Per Evidence File
- `artifact_id`
- `invariant_id`
- `generated_at` (UTC ISO-8601)
- `environment` (`staging`, `dev`, `local`)
- `source` (test suite/script/job name)
- `result` (`pass`, `fail`)
- `owner`
