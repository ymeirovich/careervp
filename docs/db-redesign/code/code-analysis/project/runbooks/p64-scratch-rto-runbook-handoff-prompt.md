# Handoff Prompt — Create Step 0.64 Scratch Recreate RTO Runbook

Use this prompt in a fresh coding-agent session to create the actual runbook for measuring Step
0.64 from-scratch recreate RTO. This handoff is for runbook creation only. Do not deploy AWS
resources, create change sets, mutate CloudFormation stacks, write SSM secrets, create Cognito
users, or destroy resources while authoring the runbook.

## Required Model / Reasoning

Minimum acceptable model for this handoff:

- Orchestrator: `gpt-5.6-sol`, reasoning `high`.
- Use `xhigh` only if the same session is also asked to implement the CDK scratch path and teardown
  automation after the runbook is accepted.

Token-optimized delegation:

- Use subagents only for bounded, non-overlapping research or implementation prompts.
- Default subagent inheritance is acceptable for runbook authoring.
- If the tool supports explicit model overrides, use the split below in the generated runbook:
  - CDK scratch deploy path worker: `gpt-5.6-sol`, `high`.
  - Teardown/cleanup worker: `gpt-5.6-sol`, `high`.
  - Smoke/auth worker: `gpt-5.6-terra`, `high`.
  - Evidence/docs worker: `gpt-5.6-terra`, `medium`.
  - Safety/refuter reviewer: `gpt-5.6-sol`, `high`.

## Context

Repository: `/Users/yitzchak/Documents/dev/careervp`

Relevant contract/runbook files:

- `docs/db-redesign/code/code-analysis/project/project-scope-lock.md`
- `docs/db-redesign/code/code-analysis/project/project-scope-lock.yaml`
- `docs/db-redesign/code/code-analysis/project/redesign-execution-plan.md`
- `docs/db-redesign/code/code-analysis/project/runbooks/wave-0-prompts.md`
- `docs/db-redesign/code/code-analysis/project/runbooks/p28-human-gated-deploy-runbook.md`
- `docs/db-redesign/code/code-analysis/project/runbooks/p29-evidence-pack-runbook.md`

Relevant implementation files:

- `infra/app.py`
- `infra/careervp/service_stack.py`
- `infra/careervp/frontend_stack.py`
- `infra/careervp/api_construct.py`
- `infra/careervp/api_db_construct.py`
- `infra/careervp/constants.py`
- `infra/careervp/naming_utils.py`
- `infra/careervp/configuration/configuration_construct.py`
- `src/backend/scripts/smoke_harness.py`
- `src/backend/scripts/evidence_pack.py`
- `scripts/ci/check_scope_lock_integrity.py`

Facts already established:

- Step 0.6 has landed in commit `567320d`: `feat: RETAIN stateful DynamoDB/S3 resources, remove dead RETAIN stacks (P-12/P-13)`.
- Step 0.61 and 0.62 have landed in commit `926a061`: P-29 evidence pack and P-30 smoke harness.
- Incremental redeploy RTO is already recorded as approximately 7 minutes, with CFN update itself approximately 67-83 seconds.
- Missing measurement: from-scratch recreate RTO for the P-26 blue/green scenario.
- The human has decided:
  - Measure only the API/service stack.
  - `eu-west-1` is acceptable as the proxy region.
  - Use the real Anthropic key.
  - Create a CDK destroy workaround where feasible; otherwise provide explicit teardown instructions.
  - `eu-west-1` is ready for deploy.
  - Follow the current scope-lock CI guard for documentation updates.

Known technical blockers to encode in the runbook:

- `infra/app.py` hard-pins `PINNED_REGION = "us-east-1"` and rejects ambient `eu-west-1`.
- `infra/app.py` always instantiates both `ServiceStack` and `FrontendStack`; the measurement should
  deploy only the API/service stack.
- `ApiConstruct` currently creates the `api.dev.careervp.com` custom domain for every non-production
  environment; scratch deploys must skip this.
- `ServiceStack` sets `termination_protection = True`.
- P-12 sets stateful resources to `RemovalPolicy.RETAIN` and DynamoDB deletion protection.
- P-30 `authed_upload` calls `/users/me/cv`; that path invokes the CV parser and LLM router, so a
  full P-30 pass requires a real Anthropic key available to the scratch Lambdas.
- `ConfigurationStore` loads `infra/careervp/configuration/json/{environment}_configuration.json`;
  a unique scratch environment needs a config strategy, such as reusing `test_configuration.json`
  or creating an explicit scratch config.
- `scripts/ci/check_scope_lock_integrity.py` rejects any diff touching `project-scope-lock.md` or
  `.yaml` unless both twins change, YAML `meta.version` increases, YAML changelog gains a row, and
  the commit message includes `Scope-Lock-Approved-By: <name> <date>`.

## Task

Create the actual runbook file:

`docs/db-redesign/code/code-analysis/project/runbooks/p64-scratch-recreate-rto-runbook.md`

The runbook must be complete enough that a future `gpt-5.6-sol high` session can execute it start to
finish with human approval for live AWS mutations. It must include exact prompts for subagents to
implement the missing CDK scratch path, smoke/auth procedure, teardown workaround, evidence capture,
and scope-lock documentation update.

Do not implement the CDK scratch path in this handoff session. The deliverable is the runbook with
implementation prompts and operator steps.

## Required Runbook Structure

The runbook must include these sections.

### 1. Purpose And Non-Goals

State that the purpose is to measure from-scratch API/service-stack recreate RTO for Step 0.64, using
`eu-west-1` as an accepted proxy, without touching live `dev` resources.

Non-goals:

- Do not measure frontend/CloudFront.
- Do not deploy or mutate the live `CareerVpCrudDev` stack.
- Do not use `dev` as the scratch environment name.
- Do not create or repoint custom domains.
- Do not leave scratch resources running after the measurement.

### 2. Success Criteria

Success requires all of:

- Scratch API/service stack reaches CloudFormation `CREATE_COMPLETE`.
- Deploy timing is recorded with UTC start/end timestamps and CFN event-derived duration.
- Raw API Gateway invoke URL is captured.
- Scratch Cognito user/token or equivalent accepted auth path is prepared.
- P-30 smoke harness passes against the raw invoke URL:
  - `health`
  - `cors_exact_origin`
  - `authed_read`
  - unauthenticated rejection
  - `authed_upload`
- Teardown completes, or every retained/protected resource that remains is listed with exact cleanup
  commands and owner action.
- Evidence JSON/Markdown records timestamp, region, account, stack name, env name, git commit, method,
  commands, smoke result, deploy duration, and teardown result.
- Scope-lock documentation update follows the current CI guard.

### 3. Operator Inputs

Require the human to provide or confirm:

- Scratch environment name, recommended format: `rto-euw1-YYYYMMDD`.
- AWS account ID, expected `788159322332` unless the human provides a separate scratch account.
- Region: `eu-west-1`.
- Anthropic key source and whether the runbook should copy from `/careervp/dev/anthropic-api-key` or
  require the human to write `/careervp/{scratch_env}/anthropic-api-key`.
- Confirmation that `eu-west-1` is bootstrapped for CDK.
- Confirmation that live `dev` resources must not be touched.
- Human approval point before every AWS mutation.

### 4. Subagent Orchestration Plan

Include a subagent table with:

- Subagent name.
- Model/reasoning.
- Write ownership.
- Task.
- Required output.
- Blocks/blocked-by relationships.

The table must use disjoint write sets:

- CDK scratch path worker owns `infra/` implementation and infra tests only.
- Smoke/auth worker owns runbook smoke/auth command procedure only unless explicitly told to add helper scripts.
- Teardown worker owns cleanup procedure and any optional cleanup helper script only.
- Evidence/docs worker owns evidence template and scope-lock update instructions only.
- Safety/refuter owns review output only.

### 5. Implementation Prompts To Embed

The runbook must contain copy-paste prompts for the following workers.

#### Prompt A — CDK Scratch API/Service Stack Path

Prompt requirements:

- Implement a scratch-only deployment path for API/service stack in `eu-west-1`.
- Do not weaken live P-28 protections.
- Do not alter live `dev` defaults.
- Avoid custom domain creation.
- Avoid frontend stack creation.
- Use unique physical names via `NamingUtils` and scratch environment suffix.
- Resolve or document configuration JSON strategy.
- Decide whether scratch mode disables termination protection and retained/deletion-protected policies,
  or keeps them and relies on explicit teardown. Prefer teardown-safe scratch overrides only if they
  are gated by a clearly named scratch flag and cannot affect `dev`, `stage`, or `prod`.
- Add tests proving:
  - default app behavior remains pinned to `us-east-1`;
  - scratch path can synthesize `eu-west-1`;
  - scratch path does not synthesize `FrontendStack`;
  - scratch path does not synthesize API custom domain;
  - scratch physical resource names are not `dev` names;
  - any scratch teardown override cannot apply outside scratch.
- Run required infra checks:
  - `uv run mypy <changed_python_files> --strict`
  - `uv run ruff format <changed_python_files>`
  - `uv run ruff check <changed_python_files> --fix`
  - `python src/backend/scripts/validate_naming.py --path infra --verbose`
  - relevant infra pytest
  - `cdk synth` for the scratch app path

#### Prompt B — Smoke/Auth Procedure

Prompt requirements:

- Produce exact commands to:
  - discover API base URL from CloudFormation output or API Gateway;
  - create or confirm a scratch Cognito user;
  - obtain a token for `SMOKE_TOKEN`;
  - set `API_BASE`, `SMOKE_ORIGIN`, and P-30 env vars;
  - ensure the Anthropic key is available through the scratch SSM parameter used by deployed Lambdas;
  - run `src/backend/scripts/smoke_harness.py`;
  - write smoke evidence under `docs/evidence/`.
- Explain that a full P-30 upload path uses real Anthropic and may incur LLM cost.
- Include fallback diagnosis steps for:
  - 401/403 auth failure;
  - CORS exact-origin mismatch;
  - LLM/Anthropic SSM failure;
  - CV upload stored in S3 but parser failure;
  - API Gateway propagation delay.

#### Prompt C — Deploy Timing Procedure

Prompt requirements:

- Produce exact timed deploy steps with human approval before mutation.
- Capture:
  - local command start time UTC;
  - command end time UTC;
  - CloudFormation stack create start/end from `describe-stack-events`;
  - stack outputs;
  - stack ARN and stack ID;
  - git commit SHA;
  - `cdk diff` or synth artifact reference before deploy.
- Use only scratch stack names.
- Include a STOP condition if any command targets `us-east-1`, `CareerVpCrudDev`, `CareerVpFrontend-Dev`,
  `api.dev.careervp.com`, or physical resource names ending `-dev`.

#### Prompt D — Teardown And Cleanup

Prompt requirements:

- Produce exact teardown steps.
- Include two paths:
  - automated `cdk destroy` path when scratch resources are deletion-safe;
  - manual cleanup path for retained/deletion-protected resources.
- Manual cleanup must include:
  - disable CloudFormation termination protection for scratch stack only;
  - remove stack policy if any scratch policy was applied;
  - disable DynamoDB deletion protection for scratch tables;
  - empty scratch S3 buckets;
  - delete scratch S3 buckets;
  - delete scratch DynamoDB tables;
  - delete scratch SQS queues, Lambda functions, log groups, IAM roles, API Gateway RestApi, Cognito
    user pool/domain, AppConfig resources, Step Functions, SNS topics, and nested stacks as applicable;
  - verify no resources remain by stack tag/name prefix.
- Include a hard safety rule: every cleanup command must filter by scratch env name and region.
- Include commands to produce a final cleanup evidence report.

#### Prompt E — Evidence And Scope-Lock Documentation

Prompt requirements:

- Define the evidence file format.
- Define where to write evidence, recommended:
  - `docs/evidence/p64-scratch-recreate-rto-<timestamp>.json`
  - optional human-readable summary under `docs/evidence/p64-scratch-recreate-rto-<timestamp>.md`
- Define the `project-scope-lock.md` and `.yaml` factual update:
  - record incremental RTO approximately 7 minutes with existing citation;
  - record from-scratch recreate RTO with timestamp and method;
  - cite evidence file path;
  - follow current CI guard: update both twins, bump version, add changelog row, include
    `Scope-Lock-Approved-By: Yitzchak Meirovich <date>` in commit message.
- Include commands to run:
  - `python scripts/ci/check_scope_lock_integrity.py --base origin/main`
  - `python docs/db-redesign/code/code-analysis/project/scope-diff.py`

#### Prompt F — Safety/Refuter Review

Prompt requirements:

- Review all planned code/runbook changes before any deploy.
- Fail the plan if:
  - any target is live `dev`;
  - any custom domain is created;
  - frontend stack is included;
  - teardown does not cover retained/protected resources;
  - P-30 cannot pass with the documented inputs;
  - scope-lock update violates current CI guard;
  - any command lacks region/account/env scoping.
- Output a go/no-go table and exact remediation items.

### 6. Human Approval Gates

The runbook must require human approval before:

- writing or copying Anthropic key to scratch SSM;
- deploying the scratch stack;
- creating a scratch Cognito user;
- running P-30 against the live scratch API;
- disabling termination protection;
- deleting retained resources;
- editing scope-lock twins.

### 7. Exact Command Template

The runbook must include a command transcript template with placeholders for:

- `SCRATCH_ENV`
- `SCRATCH_REGION`
- `SCRATCH_ACCOUNT`
- `STACK_NAME`
- `GIT_SHA`
- `ANTHROPIC_PARAM`
- `API_BASE`
- `SMOKE_ORIGIN`
- `SMOKE_TOKEN`
- `EVIDENCE_PATH`

Commands must be explicit and auditable. Do not use broad wildcard deletes. Any destructive command
must be scoped to scratch region and scratch environment name.

### 8. Verification Commands For The Runbook Creation PR

Because this handoff creates documentation only, require:

- `git diff --check`
- `rg -n "CareerVpCrudDev|CareerVpFrontend-Dev|api.dev.careervp.com|us-east-1|eu-west-1|Scope-Lock-Approved-By|ANTHROPIC" docs/db-redesign/code/code-analysis/project/runbooks/p64-scratch-recreate-rto-runbook.md`

If the runbook author edits Python or infra files, they must additionally run the relevant mypy,
ruff, pytest, naming validator, and CDK synth commands from AGENTS.md.

## Output Required From The Runbook Authoring Session

The runbook author must output:

1. Path to the created runbook.
2. List of modified files.
3. Verification commands run and results.
4. Whether any implementation was done. Expected answer for this handoff: no implementation, runbook only.
5. Recommended commit message.

## Stop Conditions

Stop and report instead of authoring a misleading runbook if:

- The repo already has a complete Step 0.64 scratch recreate runbook and this handoff would duplicate it.
- The current CDK code has changed such that the known blockers above are no longer accurate.
- The scope-lock guard no longer requires twin-sync/version/changelog/approval trailer.
- The P-30 harness no longer exercises `/users/me/cv` or no longer requires LLM-backed parsing.
- The human's stated decisions conflict with the current scope-lock.

