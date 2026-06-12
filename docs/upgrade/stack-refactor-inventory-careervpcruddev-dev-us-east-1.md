# CareerVpCrudDev Stack Refactor Migration Inventory

Date: 2026-06-12  
Stack: `CareerVpCrudDev`  
Region: `us-east-1`  
Environment: `dev`  
Mode: read-only analysis, no deploy, no resource mutations

## Scope

This inventory prepares a CloudFormation Stack Refactoring migration for `CareerVpCrudDev` using the CloudFormation Stack Refactoring API, not `cdk import`.

Inputs reviewed:

- `AGENTS.md`
- `docs/upgrade/specs/FE-UI-036-nested-stack-split.yaml`
- current `infra` source and synth output
- commit `8926a90`
- live CloudFormation stack metadata and drift status
- AWS CloudFormation Stack Refactoring docs

## Baseline

Local synth baseline from the current branch:

- Command: `cd infra && npx cdk synth CareerVpCrudDev`
- Result: synth passed
- Parent template resource count: `497`
- Synth warning: `Number of resources: 497 is approaching allowed maximum of 600`

Current parent template type hotspots:

| Resource type | Count |
|---|---:|
| `AWS::ApiGateway::Method` | 114 |
| `AWS::Lambda::Permission` | 98 |
| `AWS::ApiGateway::Resource` | 65 |
| `AWS::Lambda::Function` | 30 |
| `AWS::Logs::LogGroup` | 30 |
| `AWS::Lambda::EventInvokeConfig` | 27 |
| `AWS::SQS::Queue` | 19 |
| `AWS::CloudWatch::Alarm` | 16 |
| `AWS::IAM::Role` | 14 |
| `AWS::IAM::Policy` | 12 |
| `AWS::DynamoDB::GlobalTable` | 10 |
| `AWS::S3::Bucket` | 6 |
| `AWS::KMS::Key` | 5 |

Live stack status from `aws cloudformation describe-stacks --stack-name CareerVpCrudDev --region us-east-1`:

- Stack status: `UPDATE_COMPLETE`
- Drift status: `DRIFTED`
- Last drift check: `2026-06-12T16:37:10Z`

Known drift from `describe-stack-resource-drifts`:

- `CareerVpCrudDevCognitoUserPoolUserPoolClientFD4D0C15`
- Type: `AWS::Cognito::UserPoolClient`
- Drift state: `MODIFIED`
- Physical ID: `7blipbarsisbctqh6hlsj46sqa`
- Actual callback URLs include localhost, prod, dev, stage, and Amplify URLs; template still expects `https://example.com`

## What 8926a90 Previously Moved

Commit `8926a90` synthesized these templates:

| Template | Resource count |
|---|---:|
| `CareerVpCrudDev.template.json` | 434 |
| `...CrudMonitoring....nested.template.json` | 25 |
| `...CrudArtifactChain....nested.template.json` | 13 |
| `...CrudAsyncWorkers....nested.template.json` | 31 |

That earlier split would reduce the current parent from `497` to about `428` if recreated unchanged. It regains headroom, but it does not meet FE-UI-036's `parent < ~400` target anymore.

## Inventory

### Parent Must Keep

These should remain in the parent for this migration:

| Area | Why it stays | Current examples |
|---|---|---|
| API Gateway surface | `AWS::ApiGateway::Method` is explicitly unsupported by Stack Refactoring | `careervp-core-api-dev`, 114 methods, 65 resources, deployment, stage |
| Cognito | shared auth surface; current stack is drifted on `UserPoolClient` | user pool `us-east-1_WiHMRqLpe`, client `careervp-client-dev`, domain `careervp-dev` |
| Shared core Lambda role | many parent Lambdas depend on it; moving it creates wide blast radius | `careervp-role-lambda-core-dev` |
| DynamoDB tables | stateful; `AWS::DynamoDB::GlobalTable` is explicitly unsupported | `careervp-users-table-dev`, `careervp-idempotency-table-dev`, `careervp-jobs-table-dev`, `careervp-cvs-table-dev`, `careervp-applications-table-dev`, `careervp-gap-responses-table-dev`, `careervp-knowledge-table-dev`, `careervp-artifacts-table-dev`, `careervp-company-research-cache-table-dev`, `careervp-llm-cache-dev` |
| S3 buckets | stateful; each bucket is paired with unsupported custom resources | `careervp-dev-cvs-use1-11503d`, `careervp-dev-vpr-results-use1-11503d`, `careervp-dev-static-use1-11503d`, `careervp-dev-backups-use1-11503d`, `careervp-dev-logs-use1-11503d`, `careervp-dev-artifacts-use1-11503d` |
| SQS queues and DLQs | shared messaging backbone; many workers point at them | 19 queues including `careervp-vpr-jobs-queue-dev`, `careervp-company-research-queue-dev`, `careervp-cv-tailoring-queue-dev` |
| KMS keys | stateful / high-blast-radius encryption anchors | log key plus queue/topic keys |
| Core API Lambdas | tied to API Gateway methods and permissions | auth, health, user, job, application, gap, CV upload, VPR submit/status, company research, cover letter API, interview prep API |
| Company research worker | FE-UI-035/036 logic keeps it in parent to avoid a back-edge into the artifact-chain stack | `careervp-company-research-worker-lambda-dev` |
| CV upload worker | S3 notification source would make the parent bucket depend on a nested Lambda | `careervp-cv-upload-worker-lambda-dev` |

Approximate remaining parent resource count after recreating the old FE-UI-036 split: `428`.

### Monitoring Nested Candidate

Status: good first migration slice.

| Field | Value |
|---|---|
| Approximate count moved | `25` |
| Resource types | `AWS::CloudWatch::Dashboard` x2, `AWS::CloudWatch::Alarm` x15, `AWS::Logs::MetricFilter` x7, plus metadata |
| Physical names | dashboards `CareerVpCrudDev-CrudHighFacade`, `CareerVpCrudDev-CrudLowFacade`; alarm families for `careervp-core-api-dev`, `careervp-cv-parser-lambda-dev`, `careervp-vpr-submit-lambda-dev`, `careervp-company-research-lambda-dev`, `careervp-cvtailor-lambda-dev`, `careervp-gap-api-lambda-dev`, `careervp-cover-letter-api-lambda-dev`, `careervp-interview-prep-api-lambda-dev` |
| Dependency direction | nested depends downward on parent API Gateway, parent Lambdas, parent log groups, and parent DynamoDB tables; parent does not depend back on nested internals |
| Supportability | all moved resource types here are `FULLY_MUTABLE` and not on the explicit unsupported list |

Important boundary: in `8926a90`, the SNS topic and its KMS key stayed in the parent. Only dashboards, alarms, and metric filters moved.

### WAF Nested Candidate

Status: not applicable in `dev`, and unsupported if enabled.

| Field | Value |
|---|---|
| Approximate count moved | `0` in current `dev` synth |
| Resource types if enabled | `AWS::WAFv2::WebACL`, `AWS::WAFv2::WebACLAssociation`, `AWS::WAFv2::LoggingConfiguration`, CloudWatch Logs policy/log group |
| Physical names if enabled | would be based on `careervp-core-waf-dev` / `aws-waf-logs-*` naming |
| Dependency direction | WAF would depend downward on parent API Gateway stage |
| Supportability | blocked: `AWS::WAFv2::WebACL` is explicitly unsupported by Stack Refactoring |

### Async Worker Nested Candidate

Status: previously moved in `8926a90`, but not currently safe as-is for Stack Refactoring.

| Field | Value |
|---|---|
| Approximate count moved | `31` |
| Resource types | `AWS::Lambda::Function` x6, `AWS::Logs::LogGroup` x6, `AWS::Lambda::EventInvokeConfig` x5, `AWS::Lambda::EventSourceMapping` x5, `AWS::IAM::Role` x4, `AWS::IAM::Policy` x4, plus metadata |
| Physical names | `careervp-vpr-sqs-worker-lambda-dev`, `careervp-vpr-dlq-handler-lambda-dev`, `careervp-vpr-worker-lambda-dev`, `careervp-cv-tailor-worker-lambda-dev`, `careervp-cover-letter-worker-lambda-dev`, `careervp-interview-prep-worker-lambda-dev` |
| Dependency direction | nested depends downward on parent queues, parent DynamoDB stream/table ARNs, parent artifacts/results buckets, and parent worker DLQs; parent should not depend back |
| Supportability | blocked as currently modeled: `AWS::Lambda::EventInvokeConfig` is explicitly unsupported, and `AWS::IAM::Policy` is not `FULLY_MUTABLE` (`NON_PROVISIONABLE`) |

Boundary note: the worker DLQs stayed in the parent in `8926a90`; only the worker Lambdas and their immediate child resources moved.

### Artifact-Chain Candidate

Status: previously moved in `8926a90`, but not currently safe as-is for Stack Refactoring.

| Field | Value |
|---|---|
| Approximate count moved | `13` |
| Resource types | `AWS::Lambda::Function` x2, `AWS::Logs::LogGroup` x3, `AWS::Lambda::EventInvokeConfig` x2, `AWS::IAM::Role` x2, `AWS::IAM::Policy` x2, `AWS::StepFunctions::StateMachine` x1, plus metadata |
| Physical names | `careervp-cr-failure-handler-lambda-dev`, `careervp-artifact-failure-handler-lambda-dev`, `careervp-artifact-chain-statemachine-dev`, `careervp-role-lambda-failure-handler-dev` |
| Dependency direction | nested depends downward on parent queues and parent log KMS key; parent depends upward on the nested state machine ARN for `gap_api_func` env wiring and `grant_start_execution`; parent company-research worker also needs `grant_task_response` on the nested state machine |
| Supportability | blocked as currently modeled: contains unsupported `AWS::Lambda::EventInvokeConfig`; also includes `AWS::IAM::Policy`, which is not `FULLY_MUTABLE` |

Important boundary: the company-research worker stayed in the parent in `8926a90` specifically to avoid recreating the FE-UI-035 cycle across a stack boundary.

### Do Not Move / Unsupported / Stateful

| Type or area | Why not |
|---|---|
| `AWS::DynamoDB::GlobalTable` | explicitly unsupported by Stack Refactoring; also stateful |
| `AWS::ApiGateway::Method` | explicitly unsupported; blocks moving API route trees |
| `AWS::Lambda::EventInvokeConfig` | explicitly unsupported; blocks the prior async/artifact slices as implemented |
| `AWS::WAFv2::WebACL` | explicitly unsupported |
| `AWS::AppConfig::ConfigurationProfile`, `AWS::AppConfig::Deployment`, `AWS::AppConfig::Environment` | explicitly unsupported |
| `Custom::S3AutoDeleteObjects`, `Custom::S3BucketNotifications` | custom resources are not suitable for this refactor path |
| `AWS::S3::Bucket` | `FULLY_MUTABLE` in type metadata, but stateful and paired with unsupported custom resources; keep parent |
| `AWS::KMS::Key` | `FULLY_MUTABLE` in type metadata, but stateful / high blast radius; keep parent |
| Cognito auth resources | not explicitly unsupported, but current stack drift is on `UserPoolClient`; avoid touching in this migration |
| API-integrated core Lambdas | moving them would drag in API Gateway methods/permissions and create poor refactor boundaries |

## Unsupported and Risky Types Present in the Current Parent

Current parent contains these Stack Refactoring blockers or likely blockers:

| Resource type | Count | Status |
|---|---:|---|
| `AWS::ApiGateway::Method` | 114 | explicitly unsupported |
| `AWS::DynamoDB::GlobalTable` | 10 | explicitly unsupported |
| `AWS::Lambda::EventInvokeConfig` | 27 | explicitly unsupported |
| `AWS::AppConfig::ConfigurationProfile` | 1 | explicitly unsupported |
| `AWS::AppConfig::Deployment` | 1 | explicitly unsupported |
| `AWS::AppConfig::Environment` | 1 | explicitly unsupported |
| `Custom::S3AutoDeleteObjects` | 6 | custom resource, avoid |
| `Custom::S3BucketNotifications` | 1 | custom resource, avoid |
| `AWS::IAM::Policy` | 12 | not `FULLY_MUTABLE`; likely incompatible with refactor validation |

Relevant AWS type metadata checked with `aws cloudformation describe-type`:

- `AWS::S3::Bucket`: `FULLY_MUTABLE`
- `AWS::KMS::Key`: `FULLY_MUTABLE`
- `AWS::Cognito::UserPool`: `FULLY_MUTABLE`
- `AWS::Cognito::UserPoolClient`: `FULLY_MUTABLE`
- `AWS::ApiGateway::RestApi`: `FULLY_MUTABLE`
- `AWS::StepFunctions::StateMachine`: `FULLY_MUTABLE`
- `AWS::Logs::MetricFilter`: `FULLY_MUTABLE`
- `AWS::IAM::Policy`: `NON_PROVISIONABLE`
- `AWS::Lambda::Permission`: `IMMUTABLE`

## Drift Finding

AWS documentation does not state that the entire source stack must be drift-free before `create-stack-refactor`. The published requirements are:

- refactor only reorganizes existing resources
- no resource config changes in the same operation
- only `FULLY_MUTABLE` resource types are eligible
- CloudFormation validates templates and reports unsupported resources during refactor creation

Interpretation for this stack:

- The current `MODIFIED` Cognito client is not a documented global hard stop by itself.
- It is still a practical blocker for any migration that touches Cognito or depends on a clean no-op template state.
- Because Cognito stays in the parent anyway, the drift does not block a monitoring-only slice directly, but it does mean the parent stack is not in a clean baseline state.

## Recommended First Migration Slice

Recommendation: move only the monitoring slice first.

Why this is the best first slice:

- It is the only FE-UI-036 slice confirmed here to consist solely of supported `FULLY_MUTABLE` resource types.
- It avoids stateful resources.
- It avoids the drifted Cognito client.
- It avoids unsupported `AWS::ApiGateway::Method`, `AWS::DynamoDB::GlobalTable`, `AWS::Lambda::EventInvokeConfig`, and `AWS::IAM::Policy`.
- Its dependency graph is strictly one-way: nested observes parent resources only.

Expected result of that first slice:

- Parent resource count roughly `497 -> 472`
- New nested template count about `25`
- No Lambda code/config changes mixed into the migration

## Blockers

1. The live stack is currently drifted on `AWS::Cognito::UserPoolClient`.
2. The old FE-UI-036 split is no longer enough to reach `parent < 400`; recreated unchanged it only gets the parent to about `428`.
3. The previously planned `artifact-chain` and `async-workers` slices are not Stack Refactoring-compatible as currently modeled because they include unsupported `AWS::Lambda::EventInvokeConfig` resources and likely-incompatible `AWS::IAM::Policy` resources.
4. Any WAF slice is blocked because `AWS::WAFv2::WebACL` is explicitly unsupported.
5. API Gateway route trees cannot be used for headroom recovery because `AWS::ApiGateway::Method` is explicitly unsupported.
6. All DynamoDB tables must stay in the parent because `AWS::DynamoDB::GlobalTable` is explicitly unsupported.
7. S3 buckets should stay in the parent because they are stateful and the current implementation also includes custom resources for auto-delete and notifications.

## Next Step After This Inventory

Before any execution planning:

1. Decide whether the immediate objective is `some headroom now` or the stricter `parent < 400`.
2. If the goal is `some headroom now`, prepare a Monitoring-only Stack Refactor preview with `create-stack-refactor`.
3. If the goal is `parent < 400`, do a second inventory for additional stateless, supported, non-API, non-stateful resource families outside FE-UI-036. The old three-slice plan is no longer enough.
4. Resolve or explicitly accept the Cognito client drift before executing any refactor on the stack.

## External References

- AWS CloudFormation Stack Refactoring: https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/stack-refactoring.html
- AWS CloudFormation `CreateStackRefactor` API: https://docs.aws.amazon.com/AWSCloudFormation/latest/APIReference/API_CreateStackRefactor.html
- AWS CloudFormation `list-stack-refactor-actions`: https://docs.aws.amazon.com/cli/latest/reference/cloudformation/list-stack-refactor-actions.html
