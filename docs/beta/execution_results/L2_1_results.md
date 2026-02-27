# L2.1 — Cognito User Pool Results

**Date:** 2026-02-27  
**Step:** Create CDK Cognito User Pool  
**Test file:** `tests/infrastructure/test_l2_cognito_user_pool.py`  
**Invariant:** I3

## Test-First Sequence

1. RED baseline:
   - Command: `cd src/backend && JSII_RUNTIME_PACKAGE_CACHE=/tmp/jsii-cache .venv/bin/pytest tests/infrastructure/test_l2_cognito_user_pool.py tests/infrastructure/test_l2_api_gateway_authorizer.py -v --tb=short`
   - Result: `10 failed` (no Cognito resources/outputs present).
2. Implementation:
   - Added `infra/careervp/cognito_construct.py`.
   - Wired Cognito construct and outputs in `infra/careervp/service_stack.py`.
   - Migrated API authorizer wiring in `infra/careervp/api_construct.py` to Cognito.
3. GREEN validation:
   - Command: `cd src/backend && JSII_RUNTIME_PACKAGE_CACHE=/tmp/jsii-cache .venv/bin/pytest tests/infrastructure/test_l2_cognito_user_pool.py -q`
   - Result: all L2.1 assertions pass.

## Additional Validation

- CDK synth command:
  - `cd infra && JSII_RUNTIME_PACKAGE_CACHE=/tmp/jsii-cache npx cdk synth --app='.venv/bin/python app.py'`
  - Result: synth succeeded; outputs include `UserPoolId` and `ClientId`.

## Notes

- Added `infra/careervp/configuration/json/test_configuration.json` so test-environment stack synthesis is deterministic.
- Added targeted `cdk_nag` suppressions for beta-phase Cognito/public-route exceptions in `ServiceStack`.
