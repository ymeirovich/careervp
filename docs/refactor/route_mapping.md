# Route Mapping: Current Handlers to OpenAPI Contract

Date: 2026-02-18
Scope: `src/backend/careervp/handlers/`

## 1) Current `@app.*` decorator audit

Command used:
`rg -n "@app\." src/backend/careervp/handlers | rg -v "lambda_handler"`

Raw matches:

| File | Decorator | Notes |
|------|-----------|-------|
| `src/backend/careervp/handlers/cv_upload_handler.py` | `@app.post('/api/cv')` | HTTP route decorator |
| `src/backend/careervp/handlers/utils/rest_api_resolver.py` | `@app.exception_handler(DynamicConfigurationException)` | Exception handler, not an API route |
| `src/backend/careervp/handlers/utils/rest_api_resolver.py` | `@app.exception_handler(InternalServerException)` | Exception handler, not an API route |

## 2) Current-to-OpenAPI route mapping

| Current Route | OpenAPI Path | Handler |
|---------------|--------------|---------|
| `/api/cv` | `/users/me/cv` | `cv_upload_handler.py` |
| `/api/vpr` | `/vpr/generate` | `vpr_submit_handler.py` |
| `/api/vpr/status/{job_id}` | `/vpr/{vprId}` | `vpr_status_handler.py` |

Implementation note:
- Only `/api/cv` is currently registered with an explicit `@app.post(...)` decorator in this handlers tree.
- `vpr_submit_handler.py` and `vpr_status_handler.py` implement paths in `lambda_handler` logic/comments rather than `@app.*` route decorators.

## 3) `/v1` prefix validation

Result: no handler `@app.*` decorators contain `/v1`.

Rationale:
- OpenAPI server base URL includes `/v1` (API Gateway stage/base path concern).
- Handler route decorators should stay stage-agnostic.
