# L6.3 — Update Swagger Contract Results

**Date:** 2026-02-27  
**Step:** L6.3  
**Invariant:** I7  
**Status:** ⛔ Blocked (staging OpenAPI fetch works, but route count is 1; expected 30 canonical routes)

## Compliance Rules Reviewed

- `docs/refactor/specs/api_contract_spec.yaml`:
  - maintain synchronized OpenAPI contract
  - keep route contract aligned with canonical API surface
- `docs/beta/STRICT_CHECKLIST_MAPPED_TO_SWAGGER.md`:
  - route-level verification required before completion

## Validation Executed

- Attempt with runbook stack name:
  - `python src/backend/generate_openapi.py --out-destination docs/swagger --out-filename careervp-api-staging-v1.json --stack-name CareervpStack-staging`
  - Result: failed (`ValidationError`: stack does not exist)
- Regeneration from actual staging stack:
  - `python src/backend/generate_openapi.py --out-destination docs/swagger --out-filename careervp-api-staging-v1.json --stack-name CareerVpCrudStaging`
  - Result: success (`Swagger JSON saved to docs/swagger/careervp-api-staging-v1.json`)
- Contract checks:
  - `jq '.paths | keys | length' docs/swagger/careervp-api-staging-v1.json` -> `1`
  - `jq -r '.paths | keys[]' docs/swagger/careervp-api-staging-v1.json | rg '^/api/'` -> no matches
  - Evidence: `docs/beta/evidence/I7_routes/staging-openapi-route-audit-2026-02-27.json`

## Local Artifact State

- Existing file present: `docs/swagger/careervp-api-staging-v1.json`
- File refreshed successfully from deployed staging stack.
- Current staging contract contains only one path: `/users/me/cv`.

## Conclusion

- L6.3 remains blocked until deployed staging route surface matches the 30-route canonical contract required by I7.
