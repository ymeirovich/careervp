# Topology Decision Record: CareerVpCrudDev Nested Stack Refactor

Date: 2026-06-12
Stack: `CareerVpCrudDev`
Region: `us-east-1`
Environment: `dev`
Input inventory: `docs/upgrade/stack-refactor-inventory-careervpcruddev-dev-us-east-1.md`

## Decision

Use a conservative phased nested-stack topology that moves only stateless, leaf-like, Stack Refactoring-compatible resources first.

Phase 1 should move only monitoring resources into `MonitoringNestedStack`.

Do not move DynamoDB tables / GlobalTables, S3 buckets, KMS keys, Cognito, API Gateway core resources, shared IAM roles, broadly referenced queues, or any unsupported Stack Refactoring resource type out of the parent stack.

Do not include Cognito in this refactor. The live stack is drifted on the Cognito user-pool client callback URLs, but Cognito remains in the parent with the same logical ID and same template properties.

Do not include the two drifted CloudWatch dashboards in Phase 1 unless their tag drift is reconciled first, or unless the Phase 1 resource mapping explicitly excludes them.

## Current Baseline

Current synthesized parent resource count from the inventory:

| Template | Resource count |
|---|---:|
| `CareerVpCrudDev` parent | 497 |

Major parent hotspots:

| Resource type | Count | Refactor disposition |
|---|---:|---|
| `AWS::ApiGateway::Method` | 114 | Keep parent; unsupported by Stack Refactoring |
| `AWS::Lambda::Permission` | 98 | Keep parent; poor API boundary and immutable type risk |
| `AWS::ApiGateway::Resource` | 65 | Keep parent with API Gateway |
| `AWS::Lambda::Function` | 30 | Move only after per-slice compatibility analysis |
| `AWS::Logs::LogGroup` | 30 | Move only when attached to a safe leaf slice |
| `AWS::Lambda::EventInvokeConfig` | 27 | Keep parent; unsupported by Stack Refactoring |
| `AWS::SQS::Queue` | 19 | Keep parent; shared messaging backbone |
| `AWS::CloudWatch::Alarm` | 16 | Phase 1 candidate |
| `AWS::DynamoDB::GlobalTable` | 10 | Keep parent; unsupported and stateful |
| `AWS::S3::Bucket` | 6 | Keep parent; stateful and paired with custom resources |
| `AWS::KMS::Key` | 5 | Keep parent; stateful encryption anchor |

## Parent Resource Policy

The parent stack keeps:

| Area | Reason |
|---|---|
| DynamoDB tables / GlobalTables | Stateful; `AWS::DynamoDB::GlobalTable` is explicitly unsupported |
| S3 buckets | Stateful; current buckets are paired with custom resources |
| KMS keys | Stateful/high-blast-radius encryption anchors |
| Cognito | Shared auth surface; current drift is on `UserPoolClient` |
| API Gateway core resources | `AWS::ApiGateway::Method` is explicitly unsupported |
| Shared IAM roles | Broadly referenced by parent Lambdas and policies |
| Broadly referenced queues and DLQs | Shared messaging backbone for several workers |
| Unsupported Stack Refactoring types | Cannot be moved by this migration path |

## Dependency Direction By Candidate

### Phase 1: `MonitoringNestedStack`

Dependency direction:

```text
MonitoringNestedStack -> parent RestApi
MonitoringNestedStack -> parent Lambda functions
MonitoringNestedStack -> parent Lambda log groups
MonitoringNestedStack -> parent DynamoDB tables
MonitoringNestedStack -> parent monitoring/SNS parent boundary only if topic/key stay parent
parent -> MonitoringNestedStack internals: none
```

Decision: accept as Phase 1.

Justification:

- Monitoring resources observe parent resources; they do not provide runtime dependencies back to the application.
- Dashboards, alarms, and metric filters are stateless or readily recreatable.
- Inventory identifies the monitoring slice as supported by Stack Refactoring when limited to dashboards, alarms, and metric filters.
- The graph is one-way: nested depends on parent. The parent does not need an alarm ARN, dashboard name, or metric filter reference to create API, Lambda, DynamoDB, S3, Cognito, or queue resources.

Phase 1 boundary:

| Include | Exclude |
|---|---|
| `AWS::CloudWatch::Dashboard` resources that are not drifted, or drift-reconciled dashboards | Drifted dashboards until tag drift is reconciled or explicitly accepted |
| `AWS::CloudWatch::Alarm` monitoring resources | SNS topic and KMS key unless confirmed compatible and drift-free |
| `AWS::Logs::MetricFilter` resources owned by `CrudMonitoring` | Any Lambda, API Gateway, DynamoDB, S3, KMS, Cognito, SQS, IAM, or AppConfig resource |

Expected parent count:

| Step | Parent count |
|---|---:|
| Baseline | 497 |
| After Phase 1 monitoring-only refactor | approximately 472 |

The expected count uses the inventory's monitoring slice estimate of about 25 moved parent resources. The final synthesized parent may differ by one resource depending on whether the nested stack resource itself is counted in the same comparison.

### Optional Phase 1b: `WafNestedStack`

Dependency direction if enabled:

```text
WafNestedStack -> parent API Gateway stage
parent -> WafNestedStack internals: none expected
```

Decision: reject for current `dev` stack and do not use for headroom planning.

Justification:

- Inventory shows WAF contributes 0 resources in current `dev` synth.
- If enabled, `AWS::WAFv2::WebACL` is explicitly unsupported by Stack Refactoring.
- Although the dependency graph is leaf-like, the resource type support blocks the refactor path.

Expected parent count:

| Step | Parent count |
|---|---:|
| After Phase 1 monitoring-only refactor | approximately 472 |
| After WAF consideration in dev | approximately 472 |

### Deferred: `ArtifactChainNestedStack`

Current dependency direction:

```text
ArtifactChainNestedStack -> parent company_research_queue
ArtifactChainNestedStack -> parent vpr_jobs_queue
ArtifactChainNestedStack -> parent cv_tailoring_queue
ArtifactChainNestedStack -> parent failure-handler Lambdas, if handlers stay parent
ArtifactChainNestedStack -> parent log KMS key

parent gap_api_func -> ArtifactChainNestedStack state machine ARN
parent gap_api_func -> ArtifactChainNestedStack state machine start-execution grant
parent company_research_worker_func -> ArtifactChainNestedStack state machine ARN
parent company_research_worker_func -> ArtifactChainNestedStack state machine task-response grant
```

Decision: defer. Do not include in Phase 1.

Rejected design:

```text
parent gap API / CR worker depends on nested state machine
nested state machine depends on parent queues / workers / handlers
```

This design creates a bidirectional parent-child dependency risk. CloudFormation can order a parent creating a child that consumes parent parameters, or a parent consuming child outputs, but it cannot resolve a cycle where parent resources must be updated with nested internals while nested resources require parent resources that are themselves blocked by the parent update.

Additional blockers from the inventory:

- Prior artifact-chain slice included `AWS::Lambda::EventInvokeConfig`, which is unsupported.
- Prior artifact-chain slice included `AWS::IAM::Policy`, which type metadata marks `NON_PROVISIONABLE`.

Safe preconditions before reconsidering:

1. Produce a dependency graph proving the nested artifact chain consumes only already-existing parent resources whose definitions do not depend on artifact-chain outputs.
2. Keep all grants that mutate parent Lambda roles/policies in the parent, or prove generated IAM policy resources are Stack Refactoring-compatible.
3. Remove unsupported `AWS::Lambda::EventInvokeConfig` from the move scope.
4. Confirm the parent can receive the state machine ARN without creating a parent-to-child dependency cycle.

Expected parent count if later proven safe:

| Step | Parent count |
|---|---:|
| After Phase 1 | approximately 472 |
| After later artifact-chain refactor | approximately 460 |

This estimate assumes roughly 13 artifact-chain resources move and one nested-stack resource remains in the parent. It is not approved for execution.

### Deferred: `AsyncWorkersNestedStack`

Dependency direction:

```text
AsyncWorkersNestedStack -> parent queues and DLQs
AsyncWorkersNestedStack -> parent DynamoDB tables / streams
AsyncWorkersNestedStack -> parent S3 buckets
AsyncWorkersNestedStack -> parent KMS keys
AsyncWorkersNestedStack -> parent shared IAM role, if reused
parent -> AsyncWorkersNestedStack internals: must remain none
```

Decision: defer unless Phase 1 does not create enough headroom and a follow-up compatibility inventory finds a supported move subset.

Justification:

- Workers are higher churn than monitoring.
- Current worker resources include unsupported `AWS::Lambda::EventInvokeConfig`.
- Current worker resources include `AWS::IAM::Policy`, which the inventory flags as likely incompatible with Stack Refactoring.
- CV upload worker has S3 notification coupling; moving it can cause the parent bucket notification custom resource to depend on a nested Lambda.

Rejected designs:

- Moving worker Lambdas while leaving parent bucket notifications or parent EventSourceMappings that reference nested Lambda internals.
- Moving worker IAM policies that CloudFormation Stack Refactoring cannot move.
- Moving workers if any parent API, queue, S3 notification, or table stream resource must be updated using nested outputs in the same refactor.

Expected parent count if later proven safe:

| Step | Parent count |
|---|---:|
| After Phase 1 | approximately 472 |
| After later async-worker refactor | approximately 442 |
| After later artifact-chain plus async-worker refactors | approximately 430 |

These estimates use the inventory's previous async-worker slice of roughly 31 resources and artifact-chain slice of roughly 13 resources, minus one parent nested-stack resource per added nested stack. They are not approved for execution because the current modeled slices include unsupported resource types.

## Final Phase Ordering

| Phase | Action | Status | Expected parent count |
|---|---|---|---:|
| 0 | Keep stateful/shared/unsupported resources in parent | Required | 497 |
| 1 | Move monitoring-only supported resources to `MonitoringNestedStack` | Approved first phase | approximately 472 |
| 1b | Consider WAF | Rejected for dev / unsupported if enabled | approximately 472 |
| 2 | Re-inventory additional stateless, supported, leaf resources outside WAF/artifact/async | Required before chasing `< 400` | unknown |
| 3 | Reconsider `ArtifactChainNestedStack` only after cycle proof and unsupported-type exclusion | Deferred | approximately 460 if safe |
| 4 | Reconsider `AsyncWorkersNestedStack` only if more headroom is needed and a supported subset exists | Deferred | approximately 430 if safe after artifact |

This ordering maximizes resource-count headroom within the current risk constraints. It takes the only confirmed low-risk headroom now, rejects unsupported WAF, and avoids moving artifact-chain or worker resources until their graph and resource-type blockers are resolved.

Important conclusion: the confirmed safe plan creates useful headroom but does not reach the earlier parent `< ~400` target. Reaching `< ~400` requires a second inventory for additional stateless, supported, non-API, non-stateful resource families. The old monitoring + artifact + async split would only land around the low 430s and is not currently Stack Refactoring-compatible as modeled.

## Phase 1 Exact Scope

Phase 1 scope is intentionally narrow:

1. Create or synthesize `MonitoringNestedStack` containing only Stack Refactoring-supported monitoring resources.
2. Include `AWS::CloudWatch::Alarm` resources owned by `CrudMonitoring`.
3. Include `AWS::Logs::MetricFilter` resources owned by `CrudMonitoring`.
4. Include `AWS::CloudWatch::Dashboard` resources only after resolving the known dashboard tag drift or explicitly excluding drifted dashboards from the mapping.
5. Keep monitoring SNS topic and its KMS key in the parent unless a separate type/support check proves they can be moved with no drift and no policy back-edge.
6. Do not move any resource that creates, invokes, authorizes, encrypts, stores, routes, authenticates, queues, or mutates application data.
7. Do not change physical names, logical IDs of unmoved parent resources, Lambda code/config, Cognito callback URLs, API routes, table definitions, bucket definitions, or queue definitions in the same operation.

Phase 1 dependency rule:

```text
Nested may reference parent resources.
Parent must not reference nested monitoring resources.
```

## Rollback Strategy For Dev

Before execution:

1. Confirm `verify_aws_state.py --mode deployed --env dev` still passes.
2. Confirm `CareerVpCrudDev` is `UPDATE_COMPLETE`.
3. Capture current templates and stack-refactor inputs in `docs/upgrade/` or an equivalent immutable handoff location.
4. Do not reconcile Cognito drift as part of this rollback plan.

If `create-stack-refactor` or `execute-stack-refactor` fails before resource movement:

1. Do not deploy unrelated changes.
2. Cancel or abandon the failed stack refactor.
3. Keep the current parent-only topology.
4. Re-synth and compare against the captured baseline before retrying.

If Phase 1 executes and monitoring behavior is wrong:

1. Use CloudFormation Stack Refactoring again to move the Phase 1 monitoring resources back into `CareerVpCrudDev`, preserving original physical resource names and template properties.
2. If a monitoring resource cannot be moved back cleanly, delete and recreate only the stateless monitoring resource in dev.
3. Do not touch DynamoDB, S3, KMS, Cognito, API Gateway, shared IAM roles, or queues during monitoring rollback.

If the parent stack enters rollback:

1. Let CloudFormation complete rollback.
2. Verify final stack status and resource drift.
3. Re-run the naming validator before any subsequent deploy attempt:

```bash
python src/backend/scripts/validate_naming.py --path infra --verbose
python src/backend/scripts/validate_naming.py --path infra --strict
```

Dev-specific blast radius:

- Monitoring dashboards, alarms, and metric filters are acceptable to recreate if rollback-by-refactor is blocked.
- Application data stores, encryption keys, Cognito, API Gateway, and queues are not acceptable rollback casualties.
- No `cdk deploy` should be run until Stack Refactoring validation and resource mappings are reviewed.

## Validation Gates Before Any Deployment

Run after any CDK change and before deploy:

```bash
python src/backend/scripts/validate_naming.py --path infra --verbose
python src/backend/scripts/validate_naming.py --path infra --strict
```

Required review gates:

1. `cdk synth` shows the parent count near the expected Phase 1 count.
2. Stack Refactoring preview contains only Phase 1 monitoring resources.
3. No resource mapping includes Cognito, DynamoDB, S3, KMS, API Gateway methods, AppConfig, WAF, Lambda EventInvokeConfig, IAM Policy, or custom resources.
4. No parent resource gains a dependency on nested monitoring internals.
5. Drifted CloudWatch dashboards are reconciled or excluded.
6. `cdk diff` does not show replacement of any stateful resource.
