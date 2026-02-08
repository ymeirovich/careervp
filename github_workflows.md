GitHub Actions Strategy for CareerVP
====================================

Goals
-----
- Keep AWS serverless (Lambda + API Gateway + DynamoDB + S3) deploys stable across dev → staging → prod.
- Enforce TDD: fast local feedback, exhaustive CI (unit + integration + regression), and infra safety checks.
- Make failures explicit and actionable (clear gates, artifacts, and rollback hooks).

Runtimes & Build Determinism
----------------------------
- Align workflow Python with Lambda target (pick 3.13 or 3.14 and use consistently in all jobs + uv caches).
- Pin Node 22 for CDK tooling; pin npm lockfiles. Add cache keys that include `python-version` and lockfile hash.
- Generate and commit lockfiles (uv/pip, npm) to avoid dependency drift; prefer exact pins for prod paths.

Workflow Line‑Up
----------------
- **PR Validation (`pull_request` → `main`)** – never deploys; runs fast but complete quality bar.
- **Dev Deploy (`push` to `main`)** – reuses validation, then deploys to dev with post-deploy smoke.
- **Staging/Prod Deploy (`workflow_dispatch` or `tag`)** – manual approval for prod; promotes built artifacts from main.
- **Nightly Maintenance (`schedule`)** – CodeQL, Scorecard, pip-audit/npm audit, `cdk diff`, coverage/cost drift.
- **Hotfix (`workflow_dispatch` with `ref`)** – validation + targeted deploy to selected env.

Event Filters (keep runs cheap)
-------------------------------
- PR paths: `src/backend/**`, `infra/**`, `.github/workflows/**`, `docs/specs/**` trigger full validation; docs-only short-circuit after format check.
- Push to main: always run dev deploy; cancel superseded runs via `concurrency: group: deploy-dev-${{ github.ref }}, cancel-in-progress: true`.
- Tags `v*.*.*`: stage→prod promotion.
- `paths-ignore`: `**/*.md` except `docs/specs/**` and `plan.md`.

Job Blocks and Required Checks
------------------------------
1) **Setup**
   - Python (Lambda version) via uv; Node 22 for CDK; cache uv/pip, npm, ruff/mypy.
2) **Fast Quality Gates (fail fast)**
   - `ruff format --check` + `ruff check --fix --exit-non-zero-on-fix`.
   - `mypy --strict`.
   - `python src/backend/scripts/validate_naming.py --path infra --strict` (Gatekeeper).
   - `uv run pytest tests/unit -q` (moto for AWS mocks).
3) **Contract & Spec**
   - `cdk synth` (detect template regressions).
   - OpenAPI drift: `oasdiff` + `make compare-openapi` when API touched.
4) **Integration / Regression**
   - PR: `pytest tests/integration -m "not slow"`; main/tag: full integration + regression suites.
   - E2E (`make e2e`) after deploy; fail if smoke fails.
5) **Security & Supply Chain**
   - CodeQL on PR/push main and weekly.
   - `pip-audit` + `npm audit --production`.
   - OSSF Scorecard nightly (already present).
   - Optional SBOM: `cyclonedx-py`/`cyclonedx-npm`, upload as artifact.
6) **Coverage**
   - `pytest --cov` → `coverage.xml`; upload to Codecov; enforce floors (80% backend, 90% critical modules from plan.md).
7) **Deploy & Post-Deploy**
   - OIDC `aws-actions/configure-aws-credentials` with per-env roles.
   - `cdk deploy --require-approval never` (dev/stage); prod via manual approval + change set summary.
   - Post-deploy: health endpoint + `python src/backend/scripts/verify_aws_state.py --mode deployed`.
8) **Failure Handling**
   - Stop downstream on first failing gate.
   - On deploy failure, upload `cdk.out`, CloudFormation events; optional guarded `make destroy` for cleanup.

Local vs CI Test Selection
--------------------------
- **Before commit (local)**: `ruff format`, `ruff check`, `mypy --strict <touched>`, `pytest tests/unit/<area>`, `validate_naming.py --strict` if infra touched.
- **Before PR**: full unit + targeted integration (`tests/integration` touched), `cdk synth`, OpenAPI drift if API changed.
- **PR CI**: fast gates + unit + light integration; no deploy.
- **Main/Tag CI**: full suite (unit + integration + regression), coverage, cdk synth, deploy, post-deploy smoke + AWS state verifier, OpenAPI validation.

Workflow Sketches (per file)
----------------------------
- `.github/workflows/pr-validate.yml`
  - on: `pull_request` to `main` with paths filter.
  - jobs: setup → lint/typecheck → unit → light integration → cdk synth → openapi drift (if API paths changed) → coverage upload.
- `.github/workflows/deploy-dev.yml`
  - on: `push` to `main`.
  - jobs: call reusable validation via `workflow_call`; configure AWS OIDC → `cdk deploy` (dev) → post-deploy smoke + `verify_aws_state.py --mode deployed` → e2e happy-path.
- `.github/workflows/deploy-stage-prod.yml`
  - on: `workflow_dispatch` (env input) or `tag v*.*.*`.
  - requires: reusable validation; manual approval for prod; run regression + OpenAPI validation; produce change set summary artifact; promote same artifact bundle built on main.
- `.github/workflows/nightly-maintenance.yml`
  - on: `schedule: "0 6 * * *"` UTC.
  - jobs: CodeQL, Scorecard, pip-audit/npm audit, `cdk diff` (no deploy), cost/coverage drift report to summary/Slack.
- `.github/workflows/_reusable-ci.yml`
  - expose `workflow_call` inputs (run_integration, run_deploy, environment); holds shared setup + gates to avoid drift.

Env, Secrets, and Protection
----------------------------
- Per-environment OIDC roles: `AWS_ROLE_DEV`, `AWS_ROLE_STAGE`, `AWS_ROLE_PROD`; least privilege per env.
- Required secrets: `CODECOV_TOKEN`, `STRIPE_WEBHOOK_SECRET`, `ANTHROPIC_API_KEY`, optional `SLACK_WEBHOOK`.
- Branch protection: require PR workflow status, CodeQL, Scorecard; disallow force-push to main.
- Mask CloudFormation outputs; never echo secrets.

Flake and Stability Controls
----------------------------
- Pin random seeds (`PYTEST_ADDOPTS=--randomly-seed=12345` if pytest-randomly) and add retries/backoff around fresh AWS resources.
- Mark true flakes with `@pytest.mark.flaky` and track in issues.
- Use `concurrency` to cancel superseded PR/main runs.

Security & Supply Chain Extras
------------------------------
- Nightly `pip-audit` and `npm audit`; fail on high/critical.
- SBOM generation (CycloneDX) uploaded as artifact; optional signing of artifacts if added later.
- Keep Scorecard and CodeQL; fix filename `codeql-analysis.yml` (remove double .yml).

Deploy Safety Nets
------------------
- Post-deploy smoke (health endpoint) + `verify_aws_state.py --mode deployed`.
- For prod: manual approval step with change set summary; rollbacks documented; keep `make destroy` guarded and non-default.
- Drift watch: nightly `cdk diff` and OpenAPI drift; notify via summary or Slack.

Observability & Cost
--------------------
- Ensure log retention set in CDK; add CloudWatch alarms (error rate, p99 latency, cost budget) and include alarm lint check in nightly.
- Consider cost guard: budget alert and simple cost-per-request metric emitted by Lambdas (can be validated in integration tests).

Artifact Promotion
------------------
- Build once on main, store artifact (lambda zips/CDK synth output), reuse for stage/prod; avoid rebuilding on prod.
- Upload `cdk.out`, coverage, SARIF, SBOM as artifacts for traceability.

Docs & Templates
----------------
- Keep this guide referenced from CONTRIBUTING; add short HOWTO for re-running workflows with debug logs.
- Optional: auto-labeler/triage workflow for issues/PRs; remove `comment_issues.yml` if it adds noise.

Why This Matches plan.md
------------------------
- Honors mandatory commands (ruff, mypy, pytest, naming validator).
- Enforces AWS naming guardrail before any deploy.
- Covers unit, integration, regression, OpenAPI drift, and post-deploy AWS verification required for stable serverless rollout.
- Adds determinism, flake controls, and supply-chain checks aligned with the phased plan and TDD expectations.

Phase-Specific Workflow Guidance
--------------------------------
Use these as blueprints when creating workflow files; compose from the job blocks above and gate deploys by environment.

- **Phase 0: Infrastructure Reset & Naming Guardrails**
  - PR workflow: setup → ruff/mypy → `validate_naming.py --strict --path infra` → unit tests touching infra helpers → `cdk synth`.
  - Deploy (main): reuse validation → `make deploy` (dev) → post-deploy `verify_aws_state.py --mode deployed`; on failure optionally `make destroy` (guarded).
  - Nightly: `cdk diff` only (no deploy) + Scorecard/CodeQL already scheduled.

- **Phase 8: Company Research**
  - PR: lint/typecheck; unit for `company_*`, `web_scraper`, `web_search`; integration with mocked HTTP; `cdk synth`; OpenAPI drift if API changes.
  - Main deploy: validation → deploy dev → smoke call company-research endpoint → `verify_aws_state.py`.
  - Optional nightly: short integration against dev API with read-only fixtures.

- **Interim Branch: feature/gap-remediation (between Phases 8 → 9)**
  - Workflow trigger: `pull_request` and `push` on `feature/gap-remediation`.
  - Jobs: reuse PR validation, plus targeted integration suite for gap-analysis + company-research interactions; require `pytest tests/integration -k "gap or company_research"` and `cdk synth`.
  - Deploy: allow optional `workflow_dispatch` to deploy to a transient env (e.g., `ENV=gap-remediation`) using separate OIDC role `AWS_ROLE_GAP_SANDBOX`; run smoke on gap-analysis + CV tailoring endpoints to ensure compatibility.
  - Artifact retention: upload coverage, `cdk.out`, and OpenAPI diff for this branch to catch interface drift before Phase 9.

- **Phase 9: CV Tailoring**
  - PR: lint/mypy; unit prompt tests; integration with DAL/S3 mocks; OpenAPI drift if endpoint touched.
  - Main deploy: validation → deploy → smoke tailored-CV endpoint; ensure S3 key naming validated.

- **Phase 10: Cover Letter**
  - PR: lint/mypy; unit prompt assembly; integration for S3/DAL; OpenAPI drift.
  - Main deploy: validation → deploy → smoke cover-letter endpoint; coverage upload.

- **Phase 11: Gap Analysis**
  - PR: lint/mypy; unit question generation; integration storing/retrieving responses; OpenAPI drift.
  - Main deploy: validation → deploy → smoke gap-analysis endpoint; DynamoDB write/read check.

- **Phase 12: Interview Prep**
  - PR: lint/mypy; unit STAR formatting/questions; integration chain questions→responses→report; OpenAPI drift.
  - Main deploy: validation → deploy → smoke /interview-prep/{questions,responses,report}; ensure S3 report upload.

- **Phase 13: Knowledge Base**
  - PR: lint/mypy; unit DAL; integration moto S3+Dynamo size limits.
  - Main deploy: validation → deploy → smoke upload/list/delete via API.

- **Phase 14: Authentication (Cognito)**
  - PR: lint/mypy; unit token parsing; integration with moto/localstack; secret scan.
  - Stage deploy (manual approval): validation → deploy → smoke signup/login → protected endpoint check.
  - Prod deploy: manual approval + change set summary; keep post-deploy smoke minimal with test user pool.

- **Phase 15: Payments (Stripe)**
  - PR: lint/mypy; unit webhook signature; integration with Stripe test payloads; secret scan.
  - Stage deploy: validation → deploy → replay Stripe event fixture; verify DynamoDB/subscription state.
  - Prod: manual approval; disable live keys in lower envs; artifacts of webhook logs uploaded.

- **Phase 16: Notifications (SES/SNS)**
  - PR: lint/mypy; unit template rendering; integration moto SES/SNS.
  - Stage deploy: validation → deploy → smoke send to sandbox email; alarm on bounce rate optional.

- **Phase 17: CICD Pipeline Hardening**
  - PR: changes to workflows go through `pr-validate`; run `act` locally if desired; ensure reusable workflow version bump.
  - Nightly: CodeQL/Scorecard/pip-audit/npm audit + `cdk diff` + coverage drift summary.

- **Phase 18: Frontend SPA**
  - PR: npm lint/test/build; optional preview deploy to S3/CloudFront (separate workflow); no backend deploy.
  - Main: build once, upload artifact; dev/stage deploy to buckets with cache invalidation; Playwright smoke against dev API.

- **Phase 19: Monitoring & Observability**
  - PR: lint/mypy for logging/cost trackers; `cfn-lint` for alarm stacks.
  - Nightly: `cdk diff` on monitoring stacks; optional synthetic check hitting health endpoint.

- **Phase 20: Security & Compliance**
  - Nightly/weekly: CodeQL, Scorecard, pip-audit, npm audit, optional container scan; WAF rule lint if codified.
  - Stage deploy: validation → deploy WAF/policies → smoke with sample blocked request; prod behind approval.
