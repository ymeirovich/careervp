# L6.2 — Remove Duplicate API Gateway Routes Results

**Date:** 2026-02-27  
**Step:** L6.2  
**Invariant:** I7  
**Status:** ⛔ Blocked (`cdk diff` executes but includes unrelated non-route drift; gate requires route-only deletions)

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
  - Runbook-aligned rerun: `cd infra && JSII_RUNTIME_PACKAGE_CACHE=/tmp/jsii-cache JSII_SILENCE_WARNING_UNTESTED_NODE_VERSION=1 uv run cdk synth --app='python app.py'`
  - Result: pass
- CDK diff:
  - `cd infra && JSII_RUNTIME_PACKAGE_CACHE=/tmp/jsii-cache JSII_SILENCE_WARNING_UNTESTED_NODE_VERSION=1 AWS_REGION=us-east-1 CDK_DEFAULT_ACCOUNT=788159322332 CDK_DEFAULT_REGION=us-east-1 npx cdk diff --app='.venv/bin/python app.py'`
  - Result: command succeeded, but diff contained unexpected non-route changes:
    - owner tags (`runner` -> `yitzchak`) across many resources
    - Lambda asset hash (`Code.S3Key`) updates
    - API deployment replacement
  - Route deletions-only expectation was not met.
  - Evidence: `docs/beta/evidence/I7_routes/cdk-diff-2026-02-27.txt`
  - Runbook-aligned rerun: `cd infra && JSII_RUNTIME_PACKAGE_CACHE=/tmp/jsii-cache JSII_SILENCE_WARNING_UNTESTED_NODE_VERSION=1 AWS_REGION=us-east-1 CDK_DEFAULT_ACCOUNT=788159322332 CDK_DEFAULT_REGION=us-east-1 uv run cdk diff --app='python app.py'`
  - Evidence: `docs/beta/evidence/I7_routes/cdk-diff-uv-2026-02-27.txt`

## Conclusion

- L6.2 remains blocked until `cdk diff` is clean for route changes (only expected deletions/no unrelated drift), or the unrelated drift is separately resolved/approved.
