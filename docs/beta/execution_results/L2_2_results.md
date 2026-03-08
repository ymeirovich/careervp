# L2.2 — API Gateway Cognito Authorizer Results

**Date:** 2026-02-27  
**Step:** Configure API Gateway Cognito Authorizer  
**Test file:** `tests/infrastructure/test_l2_api_gateway_authorizer.py`  
**Invariant:** I3, I4 (authorizer side)

## Test-First Sequence

1. RED baseline:
   - Command: `cd src/backend && JSII_RUNTIME_PACKAGE_CACHE=/tmp/jsii-cache .venv/bin/pytest tests/infrastructure/test_l2_api_gateway_authorizer.py -v --tb=short`
   - Result: failed (stack used TOKEN/CUSTOM authorizer path).
2. Implementation:
   - Replaced TOKEN Lambda authorizer with `CognitoUserPoolsAuthorizer`.
   - Updated protected route authorization type from `CUSTOM` to `COGNITO_USER_POOLS`.
   - Kept `GET /health` and `POST /auth/register|login|refresh` public (`AuthorizationType.NONE`).
3. GREEN validation:
   - Command: `cd src/backend && JSII_RUNTIME_PACKAGE_CACHE=/tmp/jsii-cache .venv/bin/pytest tests/infrastructure/test_l2_api_gateway_authorizer.py -q`
   - Result: `5 passed`.

## Regression Validation

- Backend infra subset:
  - `cd src/backend && JSII_RUNTIME_PACKAGE_CACHE=/tmp/jsii-cache .venv/bin/pytest tests/infrastructure/test_l2_cognito_user_pool.py tests/infrastructure/test_l2_api_gateway_authorizer.py -q`
  - Result: `10 passed`.
- Infra test suite:
  - `cd infra && JSII_RUNTIME_PACKAGE_CACHE=/tmp/jsii-cache .venv/bin/pytest tests -q`
  - Result: `15 passed`.
