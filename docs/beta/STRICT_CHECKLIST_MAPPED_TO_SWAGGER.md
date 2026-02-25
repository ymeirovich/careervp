# Strict Checklist Mapped To Current Swagger

@spec `docs/best_practices/yaml/prompt_optimization_spec.yaml`
@spec `docs/best_practices/yaml/code_quality_security_spec.yaml`
@pattern `docs/swagger/careervp-core-api-dev-prod-swagger-apigateway.json`

## 1. Definition
A **Strict Checklist Mapped To Current Swagger** is a release-control document where every checklist item is explicitly tied to one or more paths and methods from the deployed Swagger contract.

It is "strict" because:
- each checklist item must map to a concrete API route;
- each mapped route must have pass/fail criteria;
- no feature is marked complete unless its mapped routes pass validation;
- missing routes are tracked as explicit "NEW endpoint required" items.

## 2. Why This Exists
- Prevents scope drift between product requirements and real API surface.
- Gives frontend and backend one shared source of truth during integration.
- Makes beta readiness measurable by route-level completion, not by broad status claims.
- Reduces regressions when routes are refactored or moved.

## 3. What Gets Mapped
For each user workflow step, map:
- `workflow_step`: UX action (for example, "Submit gap responses").
- `swagger_route`: path + method from Swagger.
- `handler_owner`: backend module/owner.
- `auth_policy`: public/protected and expected status on unauthorized requests.
- `request_contract`: minimum required fields and validation expectations.
- `response_contract`: expected status codes and minimum response shape.
- `frontend_dependency`: page/hook/component that depends on this route.
- `test_gate`: unit/integration/e2e checks required before sign-off.

## 4. Primary Use Cases

### 4.1 Beta Delivery Tracking
Use it to answer: "Are all routes needed for beta user journey actually working?"

### 4.2 Frontend Integration Planning
Use it to sequence frontend implementation by proven API readiness.

### 4.3 Release Gate and Regression Control
Use it as a hard gate before staging and beta sign-off.

### 4.4 API Refactor Safety
When renaming/removing routes, use the checklist to detect broken workflow dependencies.

### 4.5 Security and Auth Verification
Use mapped auth policy to confirm all protected routes enforce the expected authorizer behavior.

## 5. How To Use It (Operational)
1. Export or regenerate current Swagger from deployed API.
2. Enumerate all workflow steps for beta (auth -> CV -> job -> gap -> VPR -> artifacts -> trial/upgrade).
3. Map each step to existing Swagger routes.
4. Mark gaps as `NEW endpoint required`.
5. Attach pass/fail criteria and tests to each mapped route.
6. Run test gates in staging and update checklist status.
7. Freeze API contract after the agreed cutoff date for frontend stability.

## 6. Example Mapping Format

| Workflow Step | Swagger Route | Status | Required For Beta | Notes |
|---|---|---|---|---|
| Login | `POST /auth/login` | Existing | Yes | Must return access/refresh contract |
| Upload CV | `POST /users/me/cv` | Existing | Yes | Enforce auth + file validation |
| Generate VPR | `POST /vpr/generate` | Existing | Yes | Async job creation + ID returned |
| Poll VPR | `GET /vpr/{vprId}` | Existing | Yes | Must support pending/processing/completed |
| View trial usage | `GET /users/me/usage` | NEW required | Yes | Needed for 3-credit UX |
| Start checkout | `POST /subscription/create-checkout` | NEW required | Yes | Needed for conversion |

## 7. Rules for "Strict" Compliance
- Do not mark a workflow step complete without route-level verification.
- Do not treat undocumented routes as production contract.
- Do not skip unauthorized-path tests for protected routes.
- Do not add frontend calls to non-frozen routes after contract freeze.
- Do not allow identity from payload in any mapped protected route.

## 8. Current Known Gaps (From Existing Swagger Context)
The current deployed Swagger includes core generation routes, but for trial-to-paid conversion it still needs new endpoints such as:
- `GET /users/me/usage`
- `GET /users/me/subscription`
- `POST /subscription/create-checkout`
- `POST /subscription/portal`
- `POST /webhooks/stripe`
- `POST /auth/logout`
- `POST /auth/forgot-password`
- `POST /auth/reset-password`

## 9. Ownership and Update Cadence
- Product/Architecture: defines workflow steps and required outcomes.
- Backend: owns route implementation status and contract tests.
- Frontend: owns workflow integration status and UX error-state handling.
- QA: owns staging gate verification.

Update cadence:
- daily during beta sprint;
- mandatory update after any API contract change;
- mandatory update before deploy freeze.

