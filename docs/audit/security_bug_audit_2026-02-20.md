# CareerVP Security and Bug Audit

- Date: 2026-02-20
- Scope: `careervp` (backend code, dependency graph, synthesized infrastructure)
- Evidence bundle: `/tmp/careervp_review_20260220_173319`

## Executive Summary

- Critical findings: 1
- High findings: 1
- Medium findings: 4
- Low findings: 1

Core quality gates were green (`ruff`, `mypy`, unit/integration tests, `semgrep`), but security and infrastructure scans surfaced several meaningful issues requiring remediation.

## Scan Baseline (What Passed)

- `uv run ruff check .` -> pass
- `uv run mypy careervp --config-file mypy.ini` -> pass
- `uv run pytest tests/unit -q --tb=short` -> pass (`199 passed`)
- `uv run pytest tests/integration -q --tb=short` -> pass (`14 passed, 2 skipped`)
- `uvx semgrep --config p/python --config p/secrets careervp` -> pass (`0 findings`)

## Findings and Recommended Remediation

### F-001 (Critical) - Potential auth bypass / user impersonation path

- Evidence:
  - API methods are added without authorizer/method auth config in `infra/careervp/api_construct.py:1433` and `infra/careervp/api_construct.py:1440`.
  - Multiple handlers accept `x-user-id` directly:
    - `src/backend/careervp/handlers/cv_upload_handler.py:266`
    - `src/backend/careervp/handlers/gap_handler.py:319`
    - `src/backend/careervp/handlers/cover_letter_handler.py:217`
    - `src/backend/careervp/handlers/interview_prep_handler.py:178`
    - `src/backend/careervp/handlers/company_research_handler.py:226`
  - `checkov` reported `CKV_AWS_59` on 35 API methods in synthesized template.
- Risk:
  - If API Gateway auth is not enforced for protected routes, attacker-controlled headers can impersonate users.
- Recommended remediation:
  1. Add a default API authorizer for protected routes in CDK and set method authorization explicitly.
  2. Remove `x-user-id` fallback in deployed environments; allow only explicit local-dev bypass guarded by a strict env flag (for example, `LOCAL_DEV_AUTH_BYPASS=true`) and fail closed otherwise.
  3. Keep public routes explicitly unauthenticated (`/auth/*`, `/health`, Swagger assets) with documented exceptions.
  4. Add integration tests asserting:
     - protected endpoints return `401` without bearer token
     - protected endpoints reject `x-user-id` spoofing in deployed mode
     - public endpoints remain reachable as intended

### F-002 (High) - JWT configuration mismatch and ephemeral signing keys

- Evidence:
  - Infra sets `JWT_SECRET`/`JWT_ALGORITHM` in `infra/careervp/api_construct.py:1340`.
  - Auth service expects `JWT_PRIVATE_KEY`/`JWT_PUBLIC_KEY`, else generates ephemeral RSA keys in `src/backend/careervp/logic/auth_service.py:133` and `src/backend/careervp/logic/auth_service.py:136`.
  - Reproduction showed token minted before key reset cannot be validated after key regeneration.
- Risk:
  - Inconsistent auth behavior across runtimes/cold starts.
  - Operational risk from implicit key generation in deployed environments.
- Recommended remediation:
  1. Standardize on one JWT strategy (recommended: RS256 with managed key material).
  2. Store signing/verification keys in SSM/Secrets Manager and inject `JWT_PRIVATE_KEY`/`JWT_PUBLIC_KEY` via CDK.
  3. Remove unused/mismatched `JWT_SECRET`/`JWT_ALGORITHM` env vars from infra.
  4. In non-local environments, fail fast if required JWT keys are missing (do not auto-generate).
  5. Add startup and integration tests to verify cross-instance token validation.

### F-003 (Medium) - Vulnerable Python dependency (production)

- Evidence:
  - `pip-audit` found `cryptography 46.0.3` vulnerable to `CVE-2026-26007`, fix `46.0.5`.
  - Pin currently in `src/backend/lambda_requirements.txt:107`.
- Risk:
  - Known vulnerable crypto library in runtime dependencies.
- Recommended remediation:
  1. Upgrade `cryptography` to `>=46.0.5`.
  2. Regenerate lock/exported requirements (`uv lock`, `uv export` flow).
  3. Re-run `pip-audit` in CI as a merge gate.

### F-004 (Medium) - Node dependency vulnerabilities in CDK dependency tree

- Evidence:
  - `npm audit --omit=dev` reported 4 vulnerabilities (3 high, 1 moderate), including:
    - `minimatch` (`GHSA-3ppc-4f35-3m26`) via `aws-cdk-lib`
    - `ajv` (`GHSA-2g4f-4pwh-qvx6`) via `aws-cdk-lib`
  - Root dependencies in `package.json:3` and `package.json:4`.
- Risk:
  - Supply-chain exposure in build/deploy toolchain.
- Recommended remediation:
  1. Upgrade `aws-cdk-lib` and `cdk-monitoring-constructs` to versions that resolve vulnerable transitive deps.
  2. If major-version bump is required, test with:
     - `npx cdk synth`
     - `npx cdk diff`
     - backend/integration regression tests
  3. Add nightly/PR `npm audit` checks with policy thresholds.

### F-005 (Medium) - Infrastructure hardening gaps (126 failed Checkov checks)

- Evidence:
  - `checkov` summary: 126 failed / 316 passed.
  - Representative misses:
    - API stage access logging/X-Ray: `infra/careervp/api_construct.py:231`
    - SQS queues using `SQS_MANAGED` vs KMS-managed: `infra/careervp/api_construct.py:781`, `infra/careervp/api_construct.py:795`
    - S3 logging/versioning findings across synthesized buckets
    - Lambda log group encryption and other lambda hardening controls
- Risk:
  - Reduced observability and weaker default security posture.
- Recommended remediation:
  1. Enable API Gateway access logs and X-Ray at stage level.
  2. Migrate queue encryption from `SQS_MANAGED` to `KMS_MANAGED` where feasible.
  3. Enable versioning and logging for non-ephemeral S3 buckets.
  4. Encrypt CloudWatch log groups with KMS where policy requires.
  5. Classify residual findings as:
     - must-fix
     - acceptable-with-compensating-control
     - false-positive
  6. For accepted exceptions, add explicit scanner suppressions with rationale and owner.

### F-006 (Low) - Bandit low-severity code issues

- Evidence:
  - Broad exception swallow: `src/backend/careervp/handlers/company_research_handler.py:296`
  - Runtime `assert` in handlers:
    - `src/backend/careervp/handlers/vpr_status_handler.py:130`
    - `src/backend/careervp/handlers/vpr_worker_handler.py:57`
- Risk:
  - Reduced diagnosability and potential behavior changes under optimized Python execution.
- Recommended remediation:
  1. Replace broad `except Exception: continue` with narrower exceptions + structured warning logs.
  2. Replace runtime `assert` with explicit validation and controlled error path.
  3. For scanner false positives that are semantically safe, annotate with targeted `# nosec` and justification.

## Prioritized Remediation Plan

### Phase 1 (Immediate, merge-blocking)

1. Close auth bypass risk:
   - enforce authorizers on protected routes
   - remove deployed `x-user-id` fallback
2. Fix JWT config/key strategy mismatch and remove implicit production key generation.
3. Upgrade `cryptography` to fixed version and verify.

### Phase 2 (Short-term hardening)

1. Upgrade Node/CDK dependency chain to remove `npm audit` highs.
2. Address highest-value Checkov controls (API logs/X-Ray, queue encryption, critical bucket settings).

### Phase 3 (Sustained guardrails)

1. Add CI security jobs:
   - `pip-audit` (prod+dev deps)
   - `npm audit --omit=dev`
   - `checkov` on synthesized templates
2. Track accepted exceptions in-repo with owner, expiry date, and rationale.

## Re-Verification Commands

```bash
# Python quality + tests
cd /Users/yitzchak/Documents/dev/careervp/src/backend
uv run ruff check .
uv run mypy careervp --config-file mypy.ini
uv run pytest tests/unit -q --tb=short
uv run pytest tests/integration -q --tb=short

# Dependency audits
uvx --python 3.13 pip-audit -r lambda_requirements.txt
cd /Users/yitzchak/Documents/dev/careervp
npm audit --omit=dev --audit-level=high

# IaC audit
cd /Users/yitzchak/Documents/dev/careervp/src/backend
mkdir -p .build/lambdas && touch .build/lambdas/.placeholder
cd /Users/yitzchak/Documents/dev/careervp/infra
npx cdk synth
uvx checkov -d cdk.out --framework cloudformation
```
