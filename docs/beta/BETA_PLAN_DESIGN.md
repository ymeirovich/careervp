# CareerVP Beta Plan Design

@spec `docs/best_practices/yaml/prompt_optimization_spec.yaml`
@spec `docs/best_practices/yaml/prompt_optimization_cdk_spec.yaml`
@spec `docs/best_practices/yaml/code_quality_security_spec.yaml`
@pattern `infra/careervp/*.py`
@pattern `src/backend/careervp/handlers/*_handler.py`

## 1. Goal and Deadline
- Goal: working frontend + backend for beta testing in 14 days.
- Deadline target: 2026-03-11.
- Constraint: frontend design is pending; implementation must be modular so screens can be dropped in without API redesign.

## 2. Scope for Beta

### 2.1 In Scope (Must Ship)
- Authentication: register, login, refresh, protected routes.
- Core job-application workflow:
  - CV upload/list/select.
  - Job create/list/get.
  - Gap questions + responses.
  - VPR generate + status.
  - CV tailoring generate + status.
  - Cover letter generate + status.
  - Interview prep generate + status.
- User profile basics (`/users/me`).
- Staging and subdomain usability (`dev.careervp.com`, `stage.careervp.com`).
- Operational visibility for Claude usage/cost at Lambda level.
- Trial constraints: 14-day trial, 3 applications.

### 2.2 Out of Scope (Post-Beta)
- Full Step Functions replatform (keep current async primitives).
- Full admin dashboard implementation.
- Advanced collaboration, analytics, and V1.1+/V2 features.

## 3. Required Inputs from Existing Requirements

### 3.1 Original Requirements to Carry Forward
- Lambda instrumentation monitoring Claude API usage:
  - Per request: model, input/output tokens, cost estimate, agent/task name, user_id, app/job id.
  - Daily aggregation and alerting for cost spikes.
- Cognito + API Gateway authentication/authorization:
  - Use auth context as identity source only (never payload).
  - Consistent protected/public route policy.
- Custom domains:
  - Map `dev.careervp.com` and `stage.careervp.com` to API Gateway `/prod`.
  - API Gateway custom domain security policy TLS 1.2.
- Trial + conversion:
  - 14-day opt-out trial with 3 included applications.
  - Subscription/usage endpoints needed for conversion path.

### 3.2 Non-Negotiable Security Rules (From Specs)
- `AUTH_NEVER_TRUST_PAYLOAD`: user_id from auth context only.
- `AUTH_NO_BYPASS`: no auth disable flags.
- `AUTH_USE_MIDDLEWARE`: protected routes must consistently enforce auth.
- `SEC_CORS_RESTRICTION`: no wildcard CORS in prod/staging.
- `SEC_NO_EVENT_LOGGING`: do not log full auth-bearing events.
- `IAM_001` and `IAM_002`: least-privilege IAM and no hardcoded secrets.

## 4. Architecture Approach for Beta

### 4.1 Backend Strategy
- Keep existing Lambda + API Gateway + DynamoDB + SQS async pipeline.
- Do not introduce broad architectural churn (Step Functions migration) before beta.
- Add an application-centric facade where needed for frontend simplicity, while preserving current internal handlers.
- Freeze endpoint contracts after day 4 of implementation.

### 4.2 Frontend Strategy (Design Pending)
- Build frontend shell immediately using typed API client and route guards.
- Implement by capability modules so visual design can be layered in:
  - `auth`, `profile`, `cvs`, `jobs`, `gap-analysis`, `artifacts`, `billing`.
- Use polling-ready state management from day 1 (for async artifact flows).
- Design handoff integration model:
  - Replace module-level presentation components, keep data hooks and client contracts unchanged.

## 5. 14-Day High-Level Plan

### Phase A: Foundation (Days 1-4)
- Finalize beta API contract and route policy (public vs protected).
- Implement/validate domain mapping plan in CDK and DNS handoff.
- Build frontend app skeleton + auth/session scaffolding.
- Create contract tests for happy path and auth failures.

### Phase B: Core Workflow (Days 5-9)
- Implement frontend pages/hooks for:
  - CV upload/list.
  - Job create/list/get.
  - Gap questions/responses.
  - VPR/artifact generate + status polling.
- Backend gap closure for any missing request/response fields needed by UI.
- Add retry/error-state UX for async processing.

### Phase C: Trial + Conversion + Observability (Days 10-12)
- Implement usage tracking and enforcement:
  - Decrement free-trial application credits.
  - Block when credits exhausted.
  - Return upgrade-required response shape.
- Implement minimum billing/subscription API surface for beta conversion.
- Implement Lambda instrumentation + daily rollup + CloudWatch/SNS alerts.

### Phase D: Stabilization and Release (Days 13-14)
- End-to-end beta flow testing on staging subdomain.
- Security/quality verification against spec rules.
- Freeze deployable build, rollback checklist, and beta sign-off.

## 6. Strict Implementation Checklist

Reference:
- `docs/beta/STRICT_CHECKLIST_MAPPED_TO_SWAGGER.md`

### 6.1 Infra/CDK
- [ ] Add API Gateway custom domains + base path mapping for dev/stage.
- [ ] Enforce TLS 1.2 on API Gateway domain policy.
- [ ] Output DNS target values for Cloudflare.
- [ ] Validate `cdk synth` and `cdk diff` with no unintended deletions.

### 6.2 Auth/Cognito
- [ ] Choose final auth source for beta:
  - Option A: keep current custom JWT authorizer and harden.
  - Option B: move to Cognito JWT authorizer now (only if complete within 14-day window).
- [ ] Ensure all protected routes enforce one consistent authorizer path.
- [ ] Add/validate auth middleware coverage on all protected handlers.
- [ ] Add contract tests for 401/403 behavior.

### 6.3 Lambda Instrumentation
- [ ] Implement token/cost tracking utility for Anthropic calls.
- [ ] Persist records to DynamoDB usage table.
- [ ] Emit CloudWatch metrics by agent/task/model.
- [ ] Add daily rollup Lambda + EventBridge schedule.
- [ ] Add SNS alerts for cost thresholds and anomaly spikes.

### 6.4 Trial/Conversion
- [ ] Enforce 14-day trial and 3-application free limit.
- [ ] Expose user usage/subscription state for frontend.
- [ ] Implement minimum Stripe checkout + webhook path for conversion.
- [ ] Add upgrade-required API response contract.

### 6.5 Frontend (Design-Pending Execution)
- [ ] Scaffold app architecture, environments, auth/session, API client.
- [ ] Implement workflow pages with placeholder visual components.
- [ ] Integrate final design components after handoff without API changes.
- [ ] Add loading, empty, and failure states for all async pages.

### 6.6 Test and Release Gates
- [ ] Happy path e2e: register/login -> CV -> job -> gap -> VPR -> artifacts.
- [ ] Trial-limit e2e: user blocked at 0 credits.
- [ ] Auth e2e: protected routes reject invalid/missing tokens.
- [ ] Staging smoke via custom subdomain.
- [ ] Observability smoke: token metrics and rollup records present.

## 7. New Endpoints Required for Beta Conversion UX

### 7.1 Required New Endpoints
- `POST /auth/logout`
- `POST /auth/forgot-password`
- `POST /auth/reset-password`
- `GET /users/me/usage` (trial days left, credits remaining, applications used)
- `GET /users/me/subscription` (plan, status, renewal/trial end)
- `POST /subscription/create-checkout`
- `POST /subscription/portal`
- `POST /webhooks/stripe`
- `GET /artifacts/{artifactId}/download?format=docx`

### 7.2 Optional but Strongly Recommended
- `GET /applications`
- `GET /applications/{applicationId}`
- `POST /applications/{applicationId}/regenerate`
- `POST /applications/{applicationId}/finalize`

## 8. What Remains from Agentic Architecture (Post-Beta Track)
- Step Functions state machine as primary orchestrator.
- Explicit Stage-6 quality-validator gating in pipeline.
- Three-agent verification for hallucination control on critical artifacts.
- Full multi-agent state and memory threading across application lifecycle.
- Full admin/reporting framework beyond minimal beta observability.

## 9. Frontend Design Handoff Integration Plan
- Handoff input expected:
  - Page layouts, component states, responsive behavior, interaction specs.
- Engineering integration sequence:
  1. Bind final visuals to existing view-model hooks.
  2. Keep API client and contracts stable.
  3. Complete accessibility and responsiveness pass.
  4. Run e2e regression after each major screen batch.
- Risk mitigation:
  - If design arrives late, ship functional low-fidelity UI with complete workflow and swap styling incrementally.

## 10. Decisions Needed This Week
- Auth decision for beta: custom JWT hardening vs Cognito migration now.
- Payment depth for beta: checkout + webhook only vs full portal/billing history.
- Frontend stack finalization (recommended: Next.js + TypeScript + query cache + schema validation).
- Canonical API route prefix decision (`/api/*` or non-prefix), then freeze.
