# L6.2 — Remove Duplicate API Gateway Routes Results

**Date:** 2026-02-27  
**Step:** L6.2  
**Invariant:** I7  
**Status:** ✅ Completed

## Compliance Rules Reviewed

- `docs/best_practices/yaml/cicd_spec.yaml`
  - `CICD_CDK_SYNTH` (rule_7_1): synth before deploy
  - `CICD_DIFF_CHECK` (rule_7_2): diff review before deploy
- `docs/refactor/specs/api_contract_spec.yaml`
  - canonical route contract and duplicate route removal

## Validation Executed

- Route literal check:
  - `rg -n '"/api/' infra/careervp/api_construct.py`
  - Result: no matches
- Unit tests:
  - `cd src/backend && uv run pytest tests/unit/test_l6_route_dedup.py -q`
  - Result: `18 passed`
- CDK synth:
  - `cd infra && ENVIRONMENT=staging ... uv run cdk synth --app='python app.py'`
  - Result: pass
- CDK diff (pre-deploy snapshot):
  - `cd infra && ENVIRONMENT=staging ... uv run cdk diff CareerVpCrudStaging --app='python app.py'`
  - Result: showed expected migration updates (route cleanup + auth/lambda changes pending deployment)
  - Evidence: `docs/beta/evidence/I7_routes/cdk-diff-uv-2026-02-27-l6-continue.txt`
- Staging deploy:
  - `cd infra && ENVIRONMENT=staging ... uv run cdk deploy CareerVpCrudStaging --app='python app.py' --require-approval never --concurrency 1`
  - Result: success; deprecated `/api/*` resources removed and stack reached `UPDATE_COMPLETE`
- CDK diff (post-deploy gate):
  - `cd infra && ENVIRONMENT=staging ... uv run cdk diff CareerVpCrudStaging --app='python app.py'`
  - Result: `There were no differences`
  - Evidence: `docs/beta/evidence/I7_routes/cdk-diff-uv-2026-02-27-post-deploy.txt`

## Conclusion

- L6.2 PASS. Duplicate `/api/*` route surface has been removed from deployed staging, and post-deploy infrastructure diff is clean.
