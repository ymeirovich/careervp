# L6.3 — Update Swagger Contract Results

**Date:** 2026-02-27  
**Step:** L6.3  
**Invariant:** I7  
**Status:** ✅ Completed

## Compliance Rules Reviewed

- `docs/refactor/specs/api_contract_spec.yaml`
  - contract synchronization with deployed API
  - canonical route/operation surface consistency
- `docs/beta/STRICT_CHECKLIST_MAPPED_TO_SWAGGER.md`
  - route-level verification requirements

## Validation Executed

- Export from deployed staging stack:
  - `uv run --directory src/backend python generate_openapi.py --out-destination ../../docs/swagger --out-filename careervp-api-staging-v1.json --stack-name CareerVpCrudStaging`
  - Result: success
- Contract checks on exported file:
  - `jq '.paths | keys | length' docs/swagger/careervp-api-staging-v1.json` -> `26` paths
  - `jq '[.paths | to_entries[] | .value | keys[] | select(. != "parameters")] | length' docs/swagger/careervp-api-staging-v1.json` -> `30` operations
  - `jq '[.paths | keys[] | select(startswith("/api/"))] | length' docs/swagger/careervp-api-staging-v1.json` -> `0`
- OpenAPI surface audit vs frozen spec:
  - `operation_count`: `30`
  - `frozen_operation_count`: `30`
  - `missing_method_paths`: `[]`
  - `extra_method_paths`: `[]`
  - `operation_surface_matches_frozen`: `true`

## Evidence

- `docs/swagger/careervp-api-staging-v1.json`
- `docs/beta/evidence/I7_routes/staging-openapi-route-audit-2026-02-27.json`

## Conclusion

- L6.3 PASS. Staging OpenAPI now matches the canonical 30-operation contract with no `/api/*` routes.
