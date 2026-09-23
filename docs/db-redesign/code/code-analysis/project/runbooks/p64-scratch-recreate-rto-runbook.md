# Step 0.64 — Scratch API/Service-Stack Recreate RTO Runbook

**Status:** execution runbook; live execution requires the human approvals below

**Target:** a unique scratch API/service stack in `eu-west-1`

**Never target:** live `dev`, `CareerVpCrudDev`, `CareerVpFrontend-Dev`, or `api.dev.careervp.com`

This runbook separates implementation/review from live execution. Authoring or reviewing it does
not authorize any AWS mutation. A future orchestrator should use `gpt-5.6-sol` with `high`
reasoning. Use `xhigh` only if that same session is explicitly asked to implement both the CDK
scratch path and teardown automation after this runbook is accepted.

## 1. Purpose And Non-Goals

The purpose is to measure Step 0.64's **from-scratch API/service-stack recreate RTO** for the P-26
blue/green scenario. `eu-west-1` is the human-accepted proxy region. The run must use an isolated
scratch environment and raw API Gateway invoke URL without touching live `dev` resources.

Non-goals:

- Do not measure the frontend, Amplify, CloudFront, or `FrontendStack`.
- Do not deploy, update, replace, or otherwise mutate live `CareerVpCrudDev`.
- Do not use `dev` as the scratch environment name or produce physical names ending in `-dev`.
- Do not create, repoint, validate, or delete a custom domain or DNS record.
- Do not leave scratch resources running after the measurement.
- Do not weaken P-27/P-28 protections or change the default live deployment behavior.
- Do not treat this proxy measurement as a production-region disaster-recovery proof; record the
  region and method with the result.

## 2. Success Criteria

Step 0.64 succeeds only when all of the following are true:

- The scratch API/service stack reaches CloudFormation `CREATE_COMPLETE`.
- UTC deploy-command start/end and CloudFormation event-derived create start/end/duration are
  recorded. Keep both durations; do not substitute one for the other.
- The raw `https://<rest-api-id>.execute-api.eu-west-1.amazonaws.com/<stage>` invoke URL is captured.
- A scratch Cognito user and token, or an equivalent auth path accepted by the deployed authorizer,
  is prepared without reusing a live user's credentials.
- P-30 passes against the raw invoke URL: `health`, `cors_exact_origin`, `authed_read`, its embedded
  unauthenticated 401/403 rejection assertion, and `authed_upload`.
- Teardown completes, or every retained/protected resource left behind is recorded with its exact
  identifier, exact cleanup command, owner, and required action.
- Evidence JSON and optional Markdown record timestamp, region, account, stack name, environment,
  git commit, method, commands, smoke result, deploy duration, and teardown result.
- The factual scope-lock update follows the current twin-sync/version/changelog/approval guard.

Any failed smoke leg or incomplete cleanup makes the run **incomplete**, not a successful RTO
measurement. Preserve partial evidence and remediate; never report a bare timing number as success.

### 2.1 Known Scratch-vs-Live Topology Divergences

The scratch stack is deliberately not byte-identical to the live service stack. Record these in the
evidence `caveats` array; they mean the measured number slightly **understates** a true live recreate.

| Divergence | Live | Scratch | Effect on P-30 |
|---|---|---|---|
| CV bucket S3 event notification (`Custom::S3BucketNotifications` + CDK `BucketNotificationsHandler` Lambda, its role and policy) | present | absent | none — `POST /users/me/cv` performs the S3 put, LLM parse, and DynamoDB write synchronously in the request handler; the async worker is not on the P-30 path |
| API Gateway access-log group, execution logging, `AWS::ApiGateway::Account` | present | absent | none — avoids the regional account-level CloudWatch role |
| Budgets / Cost Anomaly / API custom domain / certificate / base-path mapping / `FrontendStack` | present | absent | none — out of scope per §1 |

No other resource type is removed in scratch. Everything else differs only by physical name,
region, removal policy, deletion protection, and the `scratch-disabled-*` literals in §7.

## 3. Operator Inputs

The human must provide or confirm these values before implementation begins:

| Input | Required value or decision |
|---|---|
| Scratch environment | Recommended `rto-euw1-YYYYMMDD`; must not equal `dev`, `stage`, `staging`, `prod`, or `production` |
| AWS account | Expected `788159322332`, unless the human explicitly supplies a separate scratch account |
| Region | Exactly `eu-west-1` |
| Anthropic key source | Human chooses either a server-side copy from `/careervp/dev/anthropic-api-key` or a human write to `/careervp/{scratch_env}/anthropic-api-key` |
| CDK bootstrap | Human confirms the selected account/`eu-west-1` is bootstrapped |
| Live-resource exclusion | Human reconfirms that no live `dev` resource may be touched |
| Mutation approvals | Human approval is required immediately before every AWS-mutating command or command group |

Record the confirmations in the evidence Markdown. Do not print, shell-trace, commit, or place the
Anthropic value in evidence. If copying the live parameter, perform a server-side/operator-controlled
copy whose stdout contains only parameter metadata, or have the human write the scratch parameter.

Residual exposure to accept or mitigate: the §7.3 and §7.5 commands pass the Anthropic key and the
Cognito password as CLI arguments, so they are briefly visible in the local process table (`ps`) to
other users of the same workstation. They do not reach shell history (the history stores the
unexpanded `"$VAR"`), logs, evidence, or CloudTrail (SSM redacts `Value`). On a single-user
workstation this is acceptable; on a shared host, pass the value via `--cli-input-json file://…`
using a `0600` temp file and delete it afterwards.

## 4. Subagent Orchestration Plan

Use subagents only for the bounded work below. Default model inheritance is acceptable if explicit
overrides are unavailable. Do not let workers edit overlapping files. The orchestrator owns the
final merge, approval gates, and live transcript.

| Subagent | Model / reasoning | Write ownership | Task | Required output | Blocks / blocked by |
|---|---|---|---|---|---|
| `cdk_scratch_path` | `gpt-5.6-sol` / `high` | `infra/` implementation and infra tests only | Implement and test isolated service-only scratch synthesis/deploy path | Diff, tests/checks, exact synth/deploy interface, cleanup-policy decision | Blocks deploy, smoke/auth, teardown; blocked by operator inputs |
| `smoke_auth` | `gpt-5.6-terra` / `high` | Runbook smoke/auth command procedure only; no helper script unless explicitly reassigned a unique path | Validate exact URL, Cognito, token, SSM, and P-30 procedure | Auditable commands, required outputs, diagnosis matrix | Blocks live smoke; blocked by scratch-path outputs |
| `deploy_timing` | `gpt-5.6-sol` / `high` | Review output or a uniquely assigned runbook timing subsection only | Validate timed deploy/capture method and STOP checks | Exact transcript and duration derivation | Blocks deploy; blocked by scratch-path interface |
| `teardown_cleanup` | `gpt-5.6-sol` / `high` | Cleanup procedure and an optional uniquely named cleanup helper only | Prove automated and manual cleanup cover protected/retained resources | Dry-run inventory, exact commands, residual-verification procedure | Blocks deploy go/no-go; blocked by scratch-path policy decision |
| `evidence_docs` | `gpt-5.6-terra` / `medium` | Evidence template and scope-lock update instructions only | Define evidence and guarded factual contract update | Schema/template, twin update checklist, validation commands | Blocks closure; evidence blocked by live run |
| `safety_refuter` | `gpt-5.6-sol` / `high` | Review output only | Adversarially review synthesized templates and all commands | Go/no-go table with exact remediation | Blocks every live mutation; blocked by all other worker outputs |

Recommended sequence: run `cdk_scratch_path`, `smoke_auth`, `deploy_timing`, `teardown_cleanup`, and
`evidence_docs` within their dependencies; then run `safety_refuter` after their outputs are merged.
Do not parallelize edits to this runbook. No worker may perform a live AWS mutation while preparing
its output.

## 5. Implementation Prompts To Embed

### Prompt A — CDK Scratch API/Service Stack Path

```text
You are the CDK scratch-path worker for CareerVP Step 0.64. Work only in infra/ implementation and
infra tests. Read AGENTS.md, .clauderules, the Step 0.64 runbook, project-scope-lock twins, P-28,
P-29, infra/app.py, ServiceStack, ApiConstruct, ApiDbConstruct, ConfigurationStore, constants, and
NamingUtils before editing. Test first. Do not deploy, create a change set, or mutate AWS.

Implement a clearly gated scratch-only API/service-stack deployment path that can synthesize and,
after separate human approval, deploy to eu-west-1. Preserve default app behavior: live/default
account remains pinned, default region remains us-east-1, live dev defaults remain unchanged, and
P-27/P-28 protections are not weakened. Scratch mode must reject dev, stage/staging, prod/production
environment names and must require an explicit scratch flag, explicit account, explicit eu-west-1,
and a unique scratch environment suffix.

In scratch mode instantiate ServiceStack only: never FrontendStack. Do not synthesize an ACM
certificate, API Gateway custom DomainName, BasePathMapping, or api.dev.careervp.com. Use
NamingUtils for unique physical names with the scratch environment suffix; no physical name may be
a dev name or end in -dev. Add a raw API invoke URL output if one is not already unambiguously
available.

Resolve the ConfigurationStore JSON issue explicitly. Prefer an explicit, tested configuration
source parameter that lets scratch reuse the committed test_configuration.json without pretending
the environment is test; alternatively add a documented scratch config strategy. Do not silently
fall back to dev_configuration.json.

Inventory every environment-scoped SSM lookup used during synthesis or runtime, not only Anthropic.
The current code also looks up scratch-scoped JWT keys and payment-provider values. Either document
the exact scratch-safe prerequisites or add a clearly gated scratch strategy that avoids importing
live values. Do not silently resolve scratch lookups from dev and do not expose secret material.

Decide whether scratch mode makes resources teardown-safe by disabling top-level termination
protection and changing scratch-only retained/deletion-protected policies, or keeps those policies
and requires explicit teardown. Prefer teardown-safe overrides only when they are gated by a
clearly named scratch flag whose constructor/API checks make it impossible to apply to dev,
stage/staging, prod/production. Never change live defaults. Inventory every RETAIN resource in the
service and nested stacks; do not limit the review to ApiDbConstruct.

Add tests proving all of the following:
1. default app behavior remains pinned to us-east-1;
2. explicit scratch mode can synthesize eu-west-1;
3. scratch synthesis contains no FrontendStack;
4. scratch synthesis contains no API custom domain, certificate, or base-path mapping;
5. scratch physical names are unique and are not dev names;
6. any scratch termination/removal/deletion-protection override cannot apply outside scratch;
7. invalid scratch env/account/region combinations fail closed;
8. the chosen configuration JSON strategy is explicit and tested.

Before handing off, run for every changed Python file:
  uv run mypy <changed_python_files> --strict
  uv run ruff format <changed_python_files>
  uv run ruff check <changed_python_files> --fix
Then run:
  python src/backend/scripts/validate_naming.py --path infra --verbose
  python src/backend/scripts/validate_naming.py --path infra --strict
  <relevant infra pytest commands>
  <exact cdk synth command for the scratch app path>
Inspect the synthesized templates and report the stack name, outputs, scratch flag/interface,
configuration strategy, resource-retention behavior, and all commands/results. Do not claim success
if a check fails. Do not edit PROGRESS.md, plan.md, or scope-lock twins because no live measurement
has landed yet.
```

### Prompt B — Smoke/Auth Procedure

```text
You are the smoke/auth procedure worker for CareerVP Step 0.64. Do not mutate AWS. Own only the
runbook smoke/auth procedure unless the orchestrator explicitly assigns a unique helper-script path.
Read AGENTS.md, the Step 0.64 runbook, the implemented scratch interface and synthesized outputs,
CognitoConstruct, ApiConstruct routes, Lambda SSM wiring, and src/backend/scripts/smoke_harness.py.

Produce copy-paste commands, with placeholders and read-only discovery first, to:
- discover the raw API base URL from CloudFormation outputs, falling back to API Gateway discovery;
- discover UserPoolId and ClientId from scratch-stack outputs;
- after a named human approval, create or confirm a scratch-only Cognito user;
- obtain a token accepted by the deployed authorizer and export it as SMOKE_TOKEN without writing it
  to evidence or shell history;
- export API_BASE, SMOKE_ORIGIN, and every relevant P-30 environment variable;
- verify that the deployed Lambdas reference /careervp/{scratch_env}/anthropic-api-key and that the
  parameter exists, without printing its value;
- inventory every other scratch-scoped SSM prerequisite needed for synthesis/runtime (including
  JWT and payment-provider lookups in the current code), and state how it is supplied or safely
  bypassed in scratch mode without borrowing live values;
- after a named human approval, run src/backend/scripts/smoke_harness.py and write smoke evidence
  under docs/evidence/.

Use only the raw execute-api URL. The exact SMOKE_ORIGIN must be present in the scratch CORS allow
list. Explain that authed_upload POSTs /users/me/cv, invokes the CV parser/LLM router, uses the real
Anthropic service, persists data, and can incur LLM cost. Never use a live Cognito user.

Include exact fallback diagnosis commands and interpretations for: 401/403 token/user-pool/client
failure; exact-origin CORS mismatch; missing or unauthorized Anthropic SSM access; S3 object written
but parser/LLM failure; and API Gateway deployment/propagation delay. Identify which diagnostics are
read-only and which require a fresh human approval. Return commands, expected outputs, and STOP
conditions; do not run them.
```

### Prompt C — Deploy Timing Procedure

```text
You are the deploy-timing worker for CareerVP Step 0.64. Do not mutate AWS. Read AGENTS.md, the Step
0.64 runbook, P-28, the accepted scratch implementation, its tests, cdk.json, and synthesized
templates. Own review output or only the uniquely assigned timing subsection.

Produce an exact, auditable timed-deploy transcript. Require a human approval immediately before the
deploy mutation. Before approval, capture identity/region, git SHA, the synth artifact path, cdk
list, cdk diff (or explain the create-stack empty-baseline behavior), and a template scan proving
the target is scratch-only. Use only the exact scratch stack name.

Capture local UTC command start and end, exit status, CloudFormation CREATE_IN_PROGRESS and
CREATE_COMPLETE timestamps from describe-stack-events/describe-stacks, stack outputs, stack ARN and
stack ID. Define both command elapsed time and event-derived CloudFormation duration. Preserve raw
JSON evidence.

STOP before mutation if any command/template targets us-east-1, CareerVpCrudDev,
CareerVpFrontend-Dev, api.dev.careervp.com, a FrontendStack, a custom domain, or any physical resource
name ending -dev. Also stop on account/region mismatch, a pre-existing stack with the proposed name,
or an unreviewed synth diff. Return the complete transcript and expected output; do not deploy.
```

### Prompt D — Teardown And Cleanup

```text
You are the teardown/cleanup worker for CareerVP Step 0.64. Do not mutate AWS. Own only the cleanup
procedure and, if explicitly approved, one uniquely named optional cleanup helper. Read AGENTS.md,
the Step 0.64 runbook, accepted scratch implementation, every service/nested-stack template, and
all RemovalPolicy/deletion-protection/termination-protection settings.

Produce exact teardown steps for two paths:
A. automated cdk destroy when the accepted scratch implementation proves all resources deletion-safe;
B. manual cleanup for retained or deletion-protected resources.

Both paths must start with account/region/env assertions, read-only recursive CloudFormation
inventory (including nested stacks), and a human approval. For the manual path include exact,
ordered commands to: disable termination protection on the scratch top-level stack only; remove a
scratch stack policy if one exists; disable deletion protection on each explicitly identified
scratch DynamoDB table; empty each explicitly identified scratch S3 bucket, including versions and
delete markers if versioning is enabled; delete those buckets and tables; and delete scratch SQS
queues, Lambda functions, CloudWatch log groups, IAM roles/policies, API Gateway RestApi, Cognito user
pool/domain/client as applicable, AppConfig deployments/configuration profiles/environments/apps,
Step Functions state machines, SNS topics/subscriptions, KMS aliases/keys where safe, EventBridge
rules/buses, and nested stacks as applicable. Respect service dependency order and KMS scheduled
deletion semantics.

No broad wildcard delete is allowed. Every mutation must name a previously inventoried resource and
include --region eu-west-1; every identifier must contain or be CloudFormation-proven to belong to
the exact scratch environment. Never operate on dev, stage/staging, prod/production. Explain that
CloudFormation normally owns non-retained resources: prefer fixing DELETE_FAILED dependencies and
retrying scratch stack deletion over ad hoc deletion while the stack still owns them.

End with commands that produce a final JSON cleanup report containing stack status/absence,
recursive residual resources, tag/name-prefix searches, retained resources, command outcomes,
owner/action, and timestamp. A pending KMS deletion must be reported as residual scheduled cleanup,
not 'nothing remains'. Return dry-run inventory logic, exact commands, expected outputs, and hard
STOP conditions; do not execute cleanup.
```

### Prompt E — Evidence And Scope-Lock Documentation

```text
You are the evidence/docs worker for CareerVP Step 0.64. Do not mutate AWS. Own only the evidence
template and scope-lock update instructions. Read AGENTS.md, the Step 0.64 runbook, project-scope-lock
twins and their changelog/version, redesign-execution-plan, P-29, P-30, evidence_pack.py,
smoke_harness.py, check_scope_lock_integrity.py, and scope-diff.py.

Define the machine-readable evidence file at:
  docs/evidence/p64-scratch-recreate-rto-<UTC timestamp>.json
and an optional human-readable twin at:
  docs/evidence/p64-scratch-recreate-rto-<UTC timestamp>.md
The JSON must record timestamp, account, region, scratch env, stack name/ARN/ID, git SHA, method,
exact commands with secret values redacted, synth/diff artifact reference, local deploy start/end and
duration, CloudFormation start/end and duration, outputs/raw API URL, auth method without token,
Anthropic parameter name without value, P-30 evidence path/result/checks, teardown result, residual
resources with owner/action, approvals, and caveats.

After the live measurement and cleanup evidence exist, propose a factual update to BOTH
project-scope-lock.md and project-scope-lock.yaml: preserve the existing incremental RTO of about 7
minutes and its existing citation; add the measured from-scratch recreate RTO, UTC timestamp,
eu-west-1 proxy method, and evidence path. Do not overstate proxy equivalence. Under the current
guard, obtain human approval before editing, update both twins together, strictly bump YAML
meta.version, add a YAML change_log/changelog row, and use a commit message containing:
  Scope-Lock-Approved-By: Yitzchak Meirovich <date>
The approval is for the factual contract amendment and commit; do not fabricate it.

Require these validation commands after the approved twin update:
  python scripts/ci/check_scope_lock_integrity.py --base origin/main
  python docs/db-redesign/code/code-analysis/project/scope-diff.py
Also require applicable Markdown/YAML checks and git diff --check. Return the evidence schema,
example with placeholders, exact twin fields/sections to update, validation checklist, and suggested
approved commit message. Do not edit the twins before the measurement and explicit approval.
```

### Prompt F — Safety/Refuter Review

```text
You are the independent safety/refuter for CareerVP Step 0.64. You have read-only ownership. Review
AGENTS.md, the accepted runbook, all proposed code/tests/helpers, synthesized templates, cdk diff,
operator transcript, smoke/auth procedure, teardown inventory, evidence template, and scope-lock
instructions. Do not mutate AWS or edit files.

Fail the plan if any target is live dev; if any custom domain/certificate/base-path mapping or
frontend stack is created; if physical resources can use dev names; if teardown misses a retained,
deletion-protected, termination-protected, nested, KMS, or otherwise residual resource; if P-30
cannot pass with the documented Cognito/CORS/real-Anthropic inputs; if the scope-lock update violates
twin sync, version bump, changelog, or approval-trailer rules; or if any AWS command lacks exact
account, eu-west-1 region, scratch environment, and resource scoping.

Check that the scratch flag cannot affect dev/stage/prod, that no secret value enters logs/evidence,
that every mutation has an immediately preceding human approval, and that the timing definition is
reproducible. Output a go/no-go table with columns Check, Evidence, Verdict, and Exact remediation.
The overall verdict is NO-GO if any row is not PASS. Do not waive findings.
```

## 6. Human Approval Gates

The operator must stop and obtain a fresh, explicit human approval before each gate. Record who
approved, UTC time, action, account, region, environment, and resource identifiers in evidence.

| Gate | Approval required before |
|---|---|
| H1 | Writing or copying the real Anthropic key to scratch SSM |
| H2 | Deploying/creating the scratch stack |
| H3 | Creating or mutating a scratch Cognito user |
| H4 | Running P-30 against the live scratch API (API calls, LLM cost, S3/DynamoDB writes) |
| H5 | Disabling CloudFormation termination protection or removing a scratch stack policy |
| H6 | Destroying the stack or deleting any retained/protected scratch resource |
| H7 | Editing the two scope-lock contract twins |

Approval at one gate does not authorize later gates. Read-only identity, template, stack, event, log,
and inventory queries do not require mutation approval but must still be correctly scoped.

## 7. Exact Command Template

The implemented scratch path is selected only by the validated environment interface below. It uses
the normal `infra/cdk.json` app and requires no extra CDK arguments. Never run a placeholder
literally. Keep shell tracing disabled (`set +x`) while handling secrets or tokens.

The accepted scratch path requires only the Anthropic SSM parameter. Tavily, legacy JWT, and payment
provider inputs are explicit non-secret `scratch-disabled-*` literals in scratch mode, and their SSM
permissions/lookups are absent. Company-research routes are outside P-30 and must not be invoked in
this run. Any scratch template that contains a Tavily/JWT/payment SSM reference is STOP.

### 7.1 Bind and validate inputs

```bash
export SCRATCH_ENV='<rto-euw1-YYYYMMDD>'
export SCRATCH_REGION='eu-west-1'
export SCRATCH_ACCOUNT='<788159322332-or-approved-scratch-account>'
export SMOKE_ORIGIN='https://p64-scratch.invalid'
export CAREERVP_SCRATCH_MODE='true'
export CAREERVP_SCRATCH_ACCOUNT="$SCRATCH_ACCOUNT"
export CAREERVP_SCRATCH_REGION="$SCRATCH_REGION"
export CAREERVP_CONFIG_SOURCE='test'
export CAREERVP_SCRATCH_ORIGIN="$SMOKE_ORIGIN"
export ENVIRONMENT="$SCRATCH_ENV"
export STACK_NAME="$(cd infra && UV_PYTHON=python3.12 uv run python -c 'from careervp.naming_utils import NamingUtils; import os; print(NamingUtils(environment=os.environ["SCRATCH_ENV"], region=os.environ["SCRATCH_REGION"], account_id=os.environ["SCRATCH_ACCOUNT"]).stack_id("crud"))')"
export GIT_SHA="$(git rev-parse HEAD)"
export ANTHROPIC_PARAM="/careervp/${SCRATCH_ENV}/anthropic-api-key"
export EVIDENCE_PATH="docs/evidence/p64-scratch-recreate-rto-$(date -u +%Y%m%dT%H%M%SZ).json"
export AWS_REGION="$SCRATCH_REGION"
export AWS_DEFAULT_REGION="$SCRATCH_REGION"

test "$SCRATCH_REGION" = 'eu-west-1'
test "$SCRATCH_ENV" != 'dev'
test "$SCRATCH_ENV" != 'stage'
test "$SCRATCH_ENV" != 'staging'
test "$SCRATCH_ENV" != 'prod'
test "$SCRATCH_ENV" != 'production'
test "$STACK_NAME" != 'CareerVpCrudDev'
test "$STACK_NAME" != 'CareerVpFrontend-Dev'
case "$SCRATCH_ENV" in *-dev|dev-*) exit 64 ;; esac
case "$STACK_NAME" in *Dev|*Frontend*) exit 64 ;; esac

aws sts get-caller-identity --region "$SCRATCH_REGION" --output json
test "$(aws sts get-caller-identity --region "$SCRATCH_REGION" --query Account --output text)" = "$SCRATCH_ACCOUNT"
test "$AWS_REGION" = "$SCRATCH_REGION"
aws cloudformation describe-stacks --stack-name "$STACK_NAME" --region "$SCRATCH_REGION"
# Expected before a true from-scratch run: ValidationError / stack does not exist.
```

If the last command finds an existing stack, STOP. Do not update it and call that a recreate.

### 7.2 Synth, diff, and fail-closed template review (no mutation)

`cdk synth` is local. `cdk diff` performs **read-only** CloudFormation API calls against the target
account/region; `--no-change-set` keeps it from creating a change set. Neither mutates AWS, so
neither needs an H-gate, but both must already be scoped to the validated scratch inputs from §7.1.

```bash
cd infra
UV_PYTHON=python3.12 npx cdk list
UV_PYTHON=python3.12 npx cdk synth "$STACK_NAME"
UV_PYTHON=python3.12 npx cdk diff "$STACK_NAME" --no-change-set
cd ..

rg -n 'CareerVpCrudDev|CareerVpFrontend-Dev|api\.dev\.careervp\.com|AWS::ApiGateway::DomainName|AWS::ApiGateway::BasePathMapping|AWS::CloudFront::Distribution|us-east-1' infra/cdk.out
rg -n -- '-dev(["/]|$)' infra/cdk.out
# Both scans must be reviewed. Any actual target/reference forbidden by this runbook is STOP.
```

Store the exact synthesized template path and SHA-256 in evidence. A harmless code comment or asset
string match is not automatically a failure, but the safety reviewer must classify every match.

**Do not treat a SHA-256 mismatch against a previously recorded value as an automatic STOP.** Every
template carries a `CDKMetadata.Analytics` construct-inventory blob that changes with the resolved
`aws-cdk-lib`/CDK-CLI version even when the infrastructure is identical; because the nested-stack
`TemplateURL`s are content hashes, one Analytics change cascades into the parent SHA as well. Before
declaring drift, diff the templates ignoring `CDKMetadata` and the `cdk-hnb659fds-assets-*` hashes:

```bash
diff <(python3 -m json.tool '<previous-template.json>') <(python3 -m json.tool '<current-template.json>') \
  | grep -E '^[<>]' | grep -viE 'Analytics|cdk-hnb659fds-assets'
# Empty output = telemetry-only difference, not an infrastructure change.
# Any other line = real drift = STOP.
```

Always hash the artifact you are actually about to deploy and record *that* SHA in evidence; never
carry a SHA forward from an earlier session.

### 7.3 Anthropic SSM parameter (mutation; H1)

First verify the **synthesized** template expects exactly `$ANTHROPIC_PARAM` (the stack does not exist
yet at H1 — the Lambdas receive the parameter *name* as an environment variable and read it at
runtime, so there is no synth-time SSM lookup and H1 may precede H2). After H1, use **one** approved
path. Keep the value out of stdout and evidence.

Human-write path:

```bash
set +x
read -s ANTHROPIC_VALUE
aws ssm put-parameter --name "$ANTHROPIC_PARAM" --type SecureString --value "$ANTHROPIC_VALUE" --overwrite --region "$SCRATCH_REGION" --output json
unset ANTHROPIC_VALUE
```

Copy-from-dev path (operator-controlled; never echo the value):

```bash
set +x
ANTHROPIC_VALUE="$(aws ssm get-parameter --name '/careervp/dev/anthropic-api-key' --with-decryption --region 'us-east-1' --query 'Parameter.Value' --output text)"
aws ssm put-parameter --name "$ANTHROPIC_PARAM" --type SecureString --value "$ANTHROPIC_VALUE" --overwrite --region "$SCRATCH_REGION" --output json
unset ANTHROPIC_VALUE
```

The `us-east-1` read above is the only permitted live-region operation and requires H1 specifically
authorizing the read/copy. It must not mutate `dev`. If that exception is not approved, the human
must write the scratch value instead.

Read-only verification without secret disclosure:

```bash
aws ssm describe-parameters --parameter-filters "Key=Name,Option=Equals,Values=$ANTHROPIC_PARAM" --region "$SCRATCH_REGION" --query 'Parameters[].{Name:Name,Type:Type,LastModifiedDate:LastModifiedDate}' --output json
```

### 7.4 Timed scratch deploy (mutation; H2)

After the safety/refuter returns GO and the human grants H2 for the exact identifiers:

```bash
DEPLOY_STARTED_UTC="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
DEPLOY_STARTED_EPOCH="$(date -u +%s)"
cd infra
UV_PYTHON=python3.12 npx cdk deploy "$STACK_NAME" --require-approval never --outputs-file "../docs/evidence/${SCRATCH_ENV}-stack-outputs.json"
DEPLOY_EXIT=$?
cd ..
DEPLOY_ENDED_UTC="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
DEPLOY_ENDED_EPOCH="$(date -u +%s)"
DEPLOY_COMMAND_SECONDS="$((DEPLOY_ENDED_EPOCH-DEPLOY_STARTED_EPOCH))"
test "$DEPLOY_EXIT" -eq 0

aws cloudformation describe-stacks --stack-name "$STACK_NAME" --region "$SCRATCH_REGION" --output json > "docs/evidence/${SCRATCH_ENV}-describe-stacks.json"
aws cloudformation describe-stack-events --stack-name "$STACK_NAME" --region "$SCRATCH_REGION" --output json > "docs/evidence/${SCRATCH_ENV}-stack-events.json"
aws cloudformation describe-stacks --stack-name "$STACK_NAME" --region "$SCRATCH_REGION" --query 'Stacks[0].{StackId:StackId,StackStatus:StackStatus,CreationTime:CreationTime,Outputs:Outputs}' --output json
```

Derive the CloudFormation duration from the root stack's first `CREATE_IN_PROGRESS` event to its
`CREATE_COMPLETE` event. Do not use nested-resource duration or local command time in its place.

### 7.5 Discover raw URL and scratch auth (H3 for user mutation)

```bash
export USER_POOL_ID="$(aws cloudformation describe-stacks --stack-name "$STACK_NAME" --region "$SCRATCH_REGION" --query "Stacks[0].Outputs[?OutputKey=='UserPoolId'].OutputValue | [0]" --output text)"
export CLIENT_ID="$(aws cloudformation describe-stacks --stack-name "$STACK_NAME" --region "$SCRATCH_REGION" --query "Stacks[0].Outputs[?OutputKey=='ClientId'].OutputValue | [0]" --output text)"
export API_BASE="$(aws cloudformation describe-stacks --stack-name "$STACK_NAME" --region "$SCRATCH_REGION" --query "Stacks[0].Outputs[?OutputKey=='RawApiInvokeUrl'].OutputValue | [0]" --output text)"
# NOTE: do NOT resolve this via `cloudformation list-stack-resources`. That call paginates,
# and the AWS CLI applies --query *per page*, so `| [0]` yields one line per page
# ("None\ny7mtvv4nw6\nNone\nNone") instead of a single ID. Resolve by exact API name instead,
# which is a single page. Verified against the deployed scratch stack.
export REST_API_ID="$(aws apigateway get-rest-apis --region "$SCRATCH_REGION" --query "items[?name=='careervp-core-api-${SCRATCH_ENV}'].id | [0]" --output text)"
export API_STAGE="$(aws apigateway get-stages --rest-api-id "$REST_API_ID" --region "$SCRATCH_REGION" --query 'item[0].stageName' --output text)"
test "$API_BASE" = "https://${REST_API_ID}.execute-api.${SCRATCH_REGION}.amazonaws.com/${API_STAGE}/"
export API_BASE="${API_BASE%/}"

aws apigateway get-stages --rest-api-id "$REST_API_ID" --region "$SCRATCH_REGION" --output json
aws cognito-idp describe-user-pool --user-pool-id "$USER_POOL_ID" --region "$SCRATCH_REGION" --output json
aws cognito-idp describe-user-pool-client --user-pool-id "$USER_POOL_ID" --client-id "$CLIENT_ID" --region "$SCRATCH_REGION" --output json
```

After H3, create a unique scratch user and set a temporary operator-held password.

The scratch pool is built by `CognitoConstruct` with `sign_in_aliases=SignInAliases(email=True)`,
which CloudFormation renders as `UsernameAttributes: ["email"]`. **The username must therefore BE an
email address.** Passing a non-email username to `admin-create-user` fails with
`InvalidParameterException: Username should be an email`. `SMOKE_USERNAME` and `SMOKE_EMAIL` are the
same value on purpose — do not reintroduce a separate opaque username.

The password must satisfy the synthesized policy: min length 8, upper, lower, digit, no symbol
required.

```bash
export SMOKE_EMAIL="p64-${SCRATCH_ENV}-$(date -u +%Y%m%dT%H%M%SZ)@example.invalid"
export SMOKE_USERNAME="$SMOKE_EMAIL"
set +x
read -s SMOKE_PASSWORD
aws cognito-idp admin-create-user --user-pool-id "$USER_POOL_ID" --username "$SMOKE_EMAIL" --user-attributes "Name=email,Value=$SMOKE_EMAIL" 'Name=email_verified,Value=true' --message-action SUPPRESS --region "$SCRATCH_REGION" --query 'User.{Username:Username,UserStatus:UserStatus}' --output json
aws cognito-idp admin-set-user-password --user-pool-id "$USER_POOL_ID" --username "$SMOKE_EMAIL" --password "$SMOKE_PASSWORD" --permanent --region "$SCRATCH_REGION"
AUTH_JSON="$(aws cognito-idp initiate-auth --client-id "$CLIENT_ID" --auth-flow USER_PASSWORD_AUTH --auth-parameters "USERNAME=$SMOKE_EMAIL,PASSWORD=$SMOKE_PASSWORD" --region "$SCRATCH_REGION" --output json)"
export SMOKE_TOKEN="$(printf '%s' "$AUTH_JSON" | uv run python -c 'import json,sys; print(json.load(sys.stdin)["AuthenticationResult"]["IdToken"])')"
unset AUTH_JSON SMOKE_PASSWORD
```

The synthesized app client enables `ALLOW_USER_PASSWORD_AUTH`, `ALLOW_USER_SRP_AUTH`, and
`ALLOW_REFRESH_TOKEN_AUTH`, so `USER_PASSWORD_AUTH` is the correct flow. Re-prove this from the
accepted synth before H3; if it is absent, STOP. Never weaken a live client or use live credentials.

Expected, not an error: because the pool uses `UsernameAttributes: ["email"]`, `admin-create-user`
returns an internal **UUID** as `User.Username` (e.g. `b2050414-80a1-…`) while `$SMOKE_EMAIL` remains
the sign-in alias. Keep using `$SMOKE_EMAIL` for `admin-set-user-password`, `initiate-auth`, and the
§7.7 `admin-get-user` diagnosis — all accept the alias. `UserStatus` is `FORCE_CHANGE_PASSWORD` right
after creation and becomes `CONFIRMED` once `admin-set-user-password --permanent` runs.

### 7.6 P-30 smoke (live API mutation/cost; H4)

STOP here. Obtain and record a fresh H4 approval naming the exact approver, UTC time, account,
`eu-west-1`, scratch environment, raw API URL, Cognito user, expected S3/DynamoDB writes, and real
Anthropic cost. After the human provides that approval, bind its non-secret evidence reference and
fail closed if it is absent:

```bash
export H4_APPROVAL_RECEIPT='<recorded-H4-evidence-reference>'
test -n "$H4_APPROVAL_RECEIPT"
test "$H4_APPROVAL_RECEIPT" != '<recorded-H4-evidence-reference>'
test "$SMOKE_ORIGIN" = "$CAREERVP_SCRATCH_ORIGIN"
export SMOKE_HEALTH_PATH='/health'
export SMOKE_PROTECTED_PATH='/users/me'
export SMOKE_AUTHED_PATH='/users/me'
export SMOKE_UPLOAD_PATH='/users/me/cv'
export SMOKE_UPLOAD_FILE_NAME="p64-${SCRATCH_ENV}.txt"
export SMOKE_TIMEOUT_SECONDS='180'

PYTHONPATH=src/backend uv run python src/backend/scripts/smoke_harness.py --evidence-dir docs/evidence
```

Record the emitted smoke evidence path. The harness's `authed_read` leg includes the required
unauthenticated rejection check. Never store `$SMOKE_TOKEN` in evidence.

### 7.7 Diagnosis (read-only unless noted)

```bash
# 401/403: verify issuer/client/user and decode token claims locally without logging the token.
aws cognito-idp admin-get-user --user-pool-id "$USER_POOL_ID" --username "$SMOKE_USERNAME" --region "$SCRATCH_REGION" --output json
aws cognito-idp describe-user-pool-client --user-pool-id "$USER_POOL_ID" --client-id "$CLIENT_ID" --region "$SCRATCH_REGION" --output json

# CORS: expected response must echo exactly $SMOKE_ORIGIN, never '*'.
curl -sS -D - -o /dev/null -X OPTIONS "$API_BASE/users/me" -H "Origin: $SMOKE_ORIGIN" -H 'Access-Control-Request-Method: GET'

# SSM wiring: configuration only; allowlist non-secret keys. Never print all
# Environment.Variables because live JWT/payment values may be resolved into them.
aws lambda list-functions --region "$SCRATCH_REGION" --query "Functions[?ends_with(FunctionName, '-${SCRATCH_ENV}')].FunctionName" --output text |
tr '\t' '\n' |
while IFS= read -r function_name; do
  test -n "$function_name" || continue
  aws lambda get-function-configuration --function-name "$function_name" --region "$SCRATCH_REGION" --query '{FunctionName:FunctionName,AnthropicParam:Environment.Variables.ANTHROPIC_API_KEY_SSM_PARAM,TavilyParam:Environment.Variables.TAVILY_API_KEY_SSM_PARAM,CvBucket:Environment.Variables.CV_BUCKET_NAME}' --output json
done
aws ssm describe-parameters --parameter-filters "Key=Name,Option=Equals,Values=$ANTHROPIC_PARAM" --region "$SCRATCH_REGION" --output json

# Parser/LLM or post-upload failure: use exact scratch log groups and a bounded UTC window.
aws logs filter-log-events --log-group-name '<explicit-scratch-cv-parser-log-group>' --start-time '<epoch-ms>' --end-time '<epoch-ms>' --region "$SCRATCH_REGION" --output json

# Propagation: verify the deployed stage and retry only after read-only inspection.
aws apigateway get-stage --rest-api-id "$REST_API_ID" --stage-name "$API_STAGE" --region "$SCRATCH_REGION" --output json
```

If S3 contains the smoke object but parsing fails, record that partial write and the Lambda request
ID; do not call the P-30 leg passed. A fresh smoke retry incurs writes/LLM cost and requires a fresh H4.

### 7.8 Teardown path A — deletion-safe CDK destroy (H5/H6 as applicable)

The implemented scratch mode is intended to synthesize with top-level termination protection off,
all parent/nested deletion policies set to `Delete`, DynamoDB deletion protection off, S3
auto-empty resources present, Cognito/AppConfig implicit retains overridden, account-level API
Gateway logging and cost resources absent, and no unnamed Lambda providers. Re-prove every property
from the exact accepted synth before deploy and again before destroy.

**Step 1 — recursive inventory (read-only; no approval needed).** Run this block on its own. It
contains no mutation. Requires `bash` (process substitution); do not run it under `sh`.

```bash
export INVENTORY_DIR="docs/evidence/${SCRATCH_ENV}-teardown-inventory"
mkdir -p "$INVENTORY_DIR"
inventory_stack() {
  local stack_id="$1"
  local safe_name
  safe_name="$(printf '%s' "$stack_id" | sed 's/[^A-Za-z0-9._-]/_/g')"
  aws cloudformation list-stack-resources --stack-name "$stack_id" --region "$SCRATCH_REGION" --output json > "$INVENTORY_DIR/${safe_name}.json"
  while IFS= read -r nested_id; do
    test -n "$nested_id" && test "$nested_id" != 'None' || continue
    inventory_stack "$nested_id"
  done < <(aws cloudformation list-stack-resources --stack-name "$stack_id" --region "$SCRATCH_REGION" --query "StackResourceSummaries[?ResourceType=='AWS::CloudFormation::Stack'].PhysicalResourceId" --output text | tr '\t' '\n')
}
inventory_stack "$STACK_NAME"

aws cloudformation describe-stacks --stack-name "$STACK_NAME" --region "$SCRATCH_REGION" --query 'Stacks[0].EnableTerminationProtection' --output text
```

**Step 2 — termination protection (MUTATION; H5).** The accepted scratch synth already sets
`terminationProtection: false`, so the previous command is expected to print `False` and this step is
then **`not_applicable`** — skip it and record H5 as such. Run it **only** if the drift check printed
`True`, and only after a fresh H5 approval naming this exact stack:

```bash
aws cloudformation update-termination-protection --stack-name "$STACK_NAME" --no-enable-termination-protection --region "$SCRATCH_REGION"
```

**Step 3 — destroy (MUTATION; H6).** After H6 and only if the recursive accepted synth and deployed
inventory prove the scratch stack deletion-safe:

```bash
cd infra
UV_PYTHON=python3.12 npx cdk destroy "$STACK_NAME" --force
cd ..
aws cloudformation wait stack-delete-complete --stack-name "$STACK_NAME" --region "$SCRATCH_REGION"
```

### 7.9 Teardown path B — retained/protected manual cleanup (H5/H6)

Use CloudFormation inventory to fill explicit identifiers; never substitute a wildcard. Prefer stack
deletion first so CloudFormation removes owned non-retained resources. If a scratch stack policy was
applied, after H5 remove it from the scratch stack only:

```bash
aws cloudformation set-stack-policy --stack-name "$STACK_NAME" --stack-policy-body '{"Statement":[{"Effect":"Allow","Action":"Update:*","Principal":"*","Resource":"*"}]}' --region "$SCRATCH_REGION"
```

After H6, repeat these templates once for each **explicitly inventoried scratch resource** as needed:

```bash
aws dynamodb update-table --table-name '<scratch-table-name>' --no-deletion-protection-enabled --region "$SCRATCH_REGION"
aws dynamodb delete-table --table-name '<scratch-table-name>' --region "$SCRATCH_REGION"

aws s3api list-object-versions --bucket '<scratch-bucket-name>' --region "$SCRATCH_REGION" --output json
# Delete each listed object version/delete marker by exact key and version ID; then:
aws s3api delete-object --bucket '<scratch-bucket-name>' --key '<exact-key>' --version-id '<exact-version-id>' --region "$SCRATCH_REGION"
aws s3api delete-bucket --bucket '<scratch-bucket-name>' --region "$SCRATCH_REGION"

aws sqs delete-queue --queue-url '<scratch-queue-url>' --region "$SCRATCH_REGION"
aws lambda delete-function --function-name '<scratch-function-name>' --region "$SCRATCH_REGION"
aws logs delete-log-group --log-group-name '<scratch-log-group-name>' --region "$SCRATCH_REGION"
aws apigateway delete-rest-api --rest-api-id '<scratch-rest-api-id>' --region "$SCRATCH_REGION"
aws cognito-idp delete-user-pool-domain --domain '<scratch-domain-prefix>' --user-pool-id '<scratch-pool-id>' --region "$SCRATCH_REGION"
aws cognito-idp delete-user-pool-client --user-pool-id '<scratch-pool-id>' --client-id '<scratch-client-id>' --region "$SCRATCH_REGION"
aws cognito-idp delete-user-pool --user-pool-id '<scratch-pool-id>' --region "$SCRATCH_REGION"
aws stepfunctions delete-state-machine --state-machine-arn '<scratch-state-machine-arn>' --region "$SCRATCH_REGION"
aws sns unsubscribe --subscription-arn '<scratch-subscription-arn>' --region "$SCRATCH_REGION"
aws sns delete-topic --topic-arn '<scratch-topic-arn>' --region "$SCRATCH_REGION"
aws events remove-targets --rule '<scratch-rule-name>' --ids '<exact-target-id>' --event-bus-name '<scratch-bus-name>' --region "$SCRATCH_REGION"
aws events delete-rule --name '<scratch-rule-name>' --event-bus-name '<scratch-bus-name>' --region "$SCRATCH_REGION"

# AppConfig dependency order: deployments -> hosted versions/profile -> environment -> application.
aws appconfig stop-deployment --application-id '<scratch-app-id>' --environment-id '<scratch-app-env-id>' --deployment-number '<number>' --region "$SCRATCH_REGION"
aws appconfig delete-hosted-configuration-version --application-id '<scratch-app-id>' --configuration-profile-id '<scratch-profile-id>' --version-number '<number>' --region "$SCRATCH_REGION"
aws appconfig delete-configuration-profile --application-id '<scratch-app-id>' --configuration-profile-id '<scratch-profile-id>' --region "$SCRATCH_REGION"
aws appconfig delete-environment --application-id '<scratch-app-id>' --environment-id '<scratch-app-env-id>' --region "$SCRATCH_REGION"
aws appconfig delete-application --application-id '<scratch-app-id>' --region "$SCRATCH_REGION"

# IAM: detach/delete explicitly inventoried policies before deleting the scratch role.
aws iam detach-role-policy --role-name '<scratch-role-name>' --policy-arn '<scratch-policy-arn>' --region "$SCRATCH_REGION"
aws iam delete-role-policy --role-name '<scratch-role-name>' --policy-name '<scratch-inline-policy-name>' --region "$SCRATCH_REGION"
aws iam delete-role --role-name '<scratch-role-name>' --region "$SCRATCH_REGION"

# KMS deletion is asynchronous and must remain in the residual report.
aws kms delete-alias --alias-name '<scratch-alias>' --region "$SCRATCH_REGION"
aws kms schedule-key-deletion --key-id '<scratch-key-id>' --pending-window-in-days 7 --region "$SCRATCH_REGION"

# Delete an explicitly inventoried nested stack only after its dependencies/resources are handled.
aws cloudformation delete-stack --stack-name '<scratch-nested-stack-id>' --region "$SCRATCH_REGION"
```

The accepted scratch service uses rules on the default EventBridge bus and does not create a custom
bus. Remove exact scratch rule targets/rules if manual cleanup is required, but never run
`delete-event-bus` for `default`. The accepted scratch synth also omits account-level Budgets, Cost
Anomaly resources, and `AWS::ApiGateway::Account`; their presence is STOP, not an invitation to
delete shared account state.

S3 unversioned objects use `aws s3api delete-object` without `--version-id`, once per exact key.
Deleting the scratch SSM parameter is also a mutation covered by H6:

```bash
aws ssm delete-parameter --name "$ANTHROPIC_PARAM" --region "$SCRATCH_REGION"
```

### 7.10 Final residual verification and evidence

```bash
aws cloudformation describe-stacks --stack-name "$STACK_NAME" --region "$SCRATCH_REGION" --output json
aws resourcegroupstaggingapi get-resources --tag-filters "Key=environment,Values=$SCRATCH_ENV" --region "$SCRATCH_REGION" --output json > "docs/evidence/${SCRATCH_ENV}-tagged-residuals.json"
aws cloudformation list-stacks --stack-status-filter CREATE_COMPLETE UPDATE_COMPLETE DELETE_FAILED DELETE_IN_PROGRESS --region "$SCRATCH_REGION" --output json > "docs/evidence/${SCRATCH_ENV}-stack-residuals.json"
aws ssm describe-parameters --parameter-filters "Key=Name,Option=Equals,Values=$ANTHROPIC_PARAM" --region "$SCRATCH_REGION" --output json > "docs/evidence/${SCRATCH_ENV}-ssm-residuals.json"

# Service-specific residual inventories. Compare every result to the immutable
# recursive CloudFormation map captured before H6; a name match alone is never
# authority to delete a resource.
aws dynamodb list-tables --region "$SCRATCH_REGION" --query "TableNames[?ends_with(@, '-${SCRATCH_ENV}')]" --output json > "docs/evidence/${SCRATCH_ENV}-dynamodb-residuals.json"
aws s3api list-buckets --region "$SCRATCH_REGION" --query "Buckets[?contains(Name, '${SCRATCH_ENV}')].Name" --output json > "docs/evidence/${SCRATCH_ENV}-s3-residuals.json"
aws sqs list-queues --queue-name-prefix 'careervp-' --region "$SCRATCH_REGION" --output json > "docs/evidence/${SCRATCH_ENV}-sqs-residuals.json"
aws lambda list-functions --region "$SCRATCH_REGION" --query "Functions[?ends_with(FunctionName, '-${SCRATCH_ENV}')].{Name:FunctionName,Arn:FunctionArn}" --output json > "docs/evidence/${SCRATCH_ENV}-lambda-residuals.json"
aws lambda list-layers --region "$SCRATCH_REGION" --output json > "docs/evidence/${SCRATCH_ENV}-lambda-layer-inventory.json"
aws logs describe-log-groups --log-group-name-prefix '/aws/lambda/careervp-' --region "$SCRATCH_REGION" --output json > "docs/evidence/${SCRATCH_ENV}-logs-residuals.json"
aws apigateway get-rest-apis --region "$SCRATCH_REGION" --query "items[?name=='careervp-core-api-${SCRATCH_ENV}']" --output json > "docs/evidence/${SCRATCH_ENV}-apigateway-residuals.json"
aws apigateway get-domain-names --region "$SCRATCH_REGION" --output json > "docs/evidence/${SCRATCH_ENV}-apigateway-domain-inventory.json"
aws cognito-idp list-user-pools --max-results 60 --region "$SCRATCH_REGION" --query "UserPools[?contains(Name, '${SCRATCH_ENV}')]" --output json > "docs/evidence/${SCRATCH_ENV}-cognito-residuals.json"
aws appconfig list-applications --region "$SCRATCH_REGION" --output json > "docs/evidence/${SCRATCH_ENV}-appconfig-application-inventory.json"
aws appconfig list-deployment-strategies --region "$SCRATCH_REGION" --output json > "docs/evidence/${SCRATCH_ENV}-appconfig-strategy-inventory.json"
aws stepfunctions list-state-machines --region "$SCRATCH_REGION" --query "stateMachines[?ends_with(name, '-${SCRATCH_ENV}')]" --output json > "docs/evidence/${SCRATCH_ENV}-sfn-residuals.json"
aws sns list-topics --region "$SCRATCH_REGION" --query "Topics[?contains(TopicArn, '${SCRATCH_ENV}')]" --output json > "docs/evidence/${SCRATCH_ENV}-sns-residuals.json"
aws events list-rules --name-prefix 'careervp-' --event-bus-name default --region "$SCRATCH_REGION" --output json > "docs/evidence/${SCRATCH_ENV}-events-residuals.json"
aws kms list-aliases --region "$SCRATCH_REGION" --output json > "docs/evidence/${SCRATCH_ENV}-kms-alias-inventory.json"
# The 5 scratch KMS keys are created without aliases, so list-aliases will NOT surface
# them. Reconcile per exact key ID from $INVENTORY_DIR instead; each must be reported as
# a residual with its KeyState (PendingDeletion) and DeletionDate.
# Repeat once per inventoried AWS::KMS::Key physical ID:
aws kms describe-key --key-id '<inventoried-scratch-key-id>' --region "$SCRATCH_REGION" --query 'KeyMetadata.{KeyId:KeyId,KeyState:KeyState,DeletionDate:DeletionDate,PendingWindowInDays:PendingDeletionWindowInDays}' --output json
aws iam list-roles --region "$SCRATCH_REGION" --query "Roles[?contains(RoleName, '${SCRATCH_ENV}')]" --output json > "docs/evidence/${SCRATCH_ENV}-iam-residuals.json"
aws cloudwatch describe-alarms --alarm-name-prefix 'careervp-' --region "$SCRATCH_REGION" --output json > "docs/evidence/${SCRATCH_ENV}-alarm-residuals.json"
aws cloudwatch list-dashboards --dashboard-name-prefix 'careervp-' --region "$SCRATCH_REGION" --output json > "docs/evidence/${SCRATCH_ENV}-dashboard-residuals.json"
aws wafv2 list-web-acls --scope REGIONAL --region "$SCRATCH_REGION" --output json > "docs/evidence/${SCRATCH_ENV}-waf-inventory.json"
```

Resource Groups Tagging API and name-prefix queries are not exhaustive. Reconcile these raw service
inventories against every exact physical ID and resource type in `$INVENTORY_DIR`; for AppConfig,
KMS keys, EventBridge rules, Lambda event-source mappings, API subresources, Cognito clients/domains,
and IAM policies, issue the corresponding `get`/`list` call for each pre-recorded exact parent ID.
Every result and command outcome must enter `$EVIDENCE_PATH`. Scheduled KMS deletion and any retained
object count as residuals; any accepted-synth resource type without a reconciled result is STOP.

### 7.11 Evidence skeleton

```json
{
  "schema_version": "1.0",
  "timestamp_utc": "<UTC>",
  "account_id": "<SCRATCH_ACCOUNT>",
  "region": "eu-west-1",
  "scratch_environment": "<SCRATCH_ENV>",
  "stack": {"name": "<STACK_NAME>", "arn": "<ARN>", "id": "<ID>"},
  "git_sha": "<GIT_SHA>",
  "method": "scratch service-only CDK create in eu-west-1 proxy region; raw invoke URL; P-30; teardown",
  "artifacts": {"synth_template": "<path>", "synth_sha256": "<sha256>", "diff": "<path>"},
  "commands": [{"command": "<redacted command>", "started_utc": "<UTC>", "ended_utc": "<UTC>", "exit_code": 0}],
  "deploy": {
    "command_started_utc": "<UTC>", "command_ended_utc": "<UTC>", "command_duration_seconds": 0,
    "cfn_started_utc": "<UTC>", "cfn_ended_utc": "<UTC>", "cfn_duration_seconds": 0,
    "final_status": "CREATE_COMPLETE"
  },
  "outputs": {"api_base": "<raw URL>", "user_pool_id": "<id>", "client_id": "<id>"},
  "auth": {"method": "scratch Cognito user", "token_recorded": false},
  "anthropic": {"parameter_name": "<ANTHROPIC_PARAM>", "value_recorded": false, "real_service_cost_possible": true},
  "smoke": {"evidence_path": "<path>", "passed": true, "checks": ["health", "cors_exact_origin", "authed_read", "unauthenticated_rejection", "authed_upload"]},
  "teardown": {"status": "complete|partial|failed", "completed_utc": "<UTC>", "residuals": [], "owner_actions": []},
  "approvals": [
    {"gate": "H1", "status": "approved|not_used", "approver": "<human>", "approved_utc": "<UTC>", "scope": "<exact action/resources>"},
    {"gate": "H2", "status": "approved", "approver": "<human>", "approved_utc": "<UTC>", "scope": "<exact action/resources>"},
    {"gate": "H3", "status": "approved", "approver": "<human>", "approved_utc": "<UTC>", "scope": "<exact action/resources>"},
    {"gate": "H4", "status": "approved", "approver": "<human>", "approved_utc": "<UTC>", "scope": "<exact action/resources>"},
    {"gate": "H5", "status": "approved|not_applicable", "approver": "<human-or-null>", "approved_utc": "<UTC-or-null>", "scope": "<exact action/resources>"},
    {"gate": "H6", "status": "approved", "approver": "<human>", "approved_utc": "<UTC>", "scope": "<exact action/resources>"},
    {"gate": "H7", "status": "approved|pending", "approver": "<human-or-null>", "approved_utc": "<UTC-or-null>", "scope": "<exact action/resources>"}
  ],
  "caveats": [
    "eu-west-1 is a proxy region; result is not a us-east-1 production DR proof",
    "scratch omits the CV bucket S3 event notification and its CDK BucketNotificationsHandler Lambda/role/policy (see 2.1); the measured recreate slightly understates a live recreate",
    "scratch omits the API Gateway access log group, execution logging, and AWS::ApiGateway::Account",
    "scratch omits Budgets, Cost Anomaly, API custom domain/certificate/base-path mapping, and FrontendStack"
  ]
}
```

### 7.12 Scope-lock factual update (H7)

Only after evidence and cleanup are complete, obtain H7 and update both twins. Preserve the existing
approximately seven-minute incremental RTO and citation; add the from-scratch number, UTC date,
`eu-west-1` proxy method, and `$EVIDENCE_PATH`. Strictly bump YAML `meta.version` and add a YAML
`change_log`/`changelog` row.

```bash
python scripts/ci/check_scope_lock_integrity.py --base origin/main
python docs/db-redesign/code/code-analysis/project/scope-diff.py
git diff --check
```

The human-approved commit message must include an actual date:

```text
docs(P-64): record scratch recreate RTO evidence

Scope-Lock-Approved-By: Yitzchak Meirovich <YYYY-MM-DD>
```

## 8. Verification Commands For The Runbook Creation PR

This authoring handoff creates documentation only. Run:

```bash
git diff --check
rg -n "CareerVpCrudDev|CareerVpFrontend-Dev|api.dev.careervp.com|us-east-1|eu-west-1|Scope-Lock-Approved-By|ANTHROPIC" docs/db-redesign/code/code-analysis/project/runbooks/p64-scratch-recreate-rto-runbook.md
```

The `rg` command is an inspection inventory, not a zero-match assertion: this runbook intentionally
names forbidden targets in STOP rules and the approved regions in scoped commands. Review every hit.

If the authoring session edits any Python or `infra/` file, it is no longer documentation-only and
must additionally run all applicable AGENTS.md checks: per-file strict mypy, Ruff format/check,
relevant pytest, both naming validators after any CDK change, and the relevant scratch `cdk synth`.
Do not mark the task complete with any failing check.

## 9. Execution Stop Conditions

Stop and report a **BLOCKING ISSUE** rather than improvising when:

- the scratch path, specified construct, output, or command interface does not exist after the
  accepted implementation, or differs from this guide without an approved migration path;
- identity, account, region, environment, or stack name is ambiguous or mismatched;
- the pre-deploy stack-existence check finds `$STACK_NAME` already exists;
- synth/diff includes a frontend, custom domain, live identifier, or `-dev` physical name;
- scratch configuration would fall back to dev config implicitly;
- the safety/refuter verdict is NO-GO;
- the real Anthropic parameter cannot be safely supplied to the scratch Lambdas;
- P-30 cannot exercise all four wires against the raw URL;
- teardown cannot enumerate or safely remove every retained/protected resource;
- any proposed scope-lock edit lacks explicit H7 approval or cannot pass the current guard; or
- the human revokes or narrows an approval.

Preserve partial evidence, state the exact blocker and required human/architect action, and do not
guess an RTO.
