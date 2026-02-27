# L6.2 — Remove Duplicate API Gateway Routes Results

**Date:** 2026-02-27  
**Step:** L6.2  
**Invariant:** I7  
**Status:** ⛔ Blocked (CDK diff requires AWS credentials in this environment)

## Compliance Rules Reviewed

- `docs/best_practices/yaml/cicd_spec.yaml`
  - `CICD_CDK_SYNTH` (rule_7_1): synth before deploy
  - `CICD_DIFF_CHECK` (rule_7_2): diff review before deploy
- `docs/refactor/specs/api_contract_spec.yaml`
  - route contract consistency and canonical route policy

## Validation Executed

- Route literal check:
  - `rg -n '"/api/' infra/careervp/api_construct.py`
  - Result: no matches
- Unit tests:
  - `cd src/backend && .venv/bin/pytest tests/unit/test_l6_route_dedup.py -v --tb=short`
  - Result: `15 passed`
- CDK synth:
  - `cd infra && HOME=/tmp JSII_RUNTIME_PACKAGE_CACHE=/tmp/jsii-cache JSII_SILENCE_WARNING_UNTESTED_NODE_VERSION=1 npx cdk synth --app='.venv/bin/python app.py'`
  - Result: pass (with non-blocking warnings)
- CDK diff:
  - `cd infra && HOME=/tmp JSII_RUNTIME_PACKAGE_CACHE=/tmp/jsii-cache JSII_SILENCE_WARNING_UNTESTED_NODE_VERSION=1 CDK_DEFAULT_ACCOUNT=123456789012 CDK_DEFAULT_REGION=us-east-1 AWS_REGION=us-east-1 npx cdk diff --app='.venv/bin/python app.py' --no-lookups`
  - Result: failed (`Need to perform AWS calls ... but no credentials have been configured`)

## Conclusion

- L6.2 cannot be marked complete until `cdk diff` is executed successfully with valid AWS credentials.
