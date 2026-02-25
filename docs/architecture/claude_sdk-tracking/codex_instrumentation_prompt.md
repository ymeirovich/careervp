ROLE: AWS Lambda Instrumentation Engineer — CareerVP Token Tracking Integration
MODEL: sonnet  # multi-service, IAM changes, CDK modifications → medium-high complexity

CONTEXT:
A token tracking system has been designed for CareerVP's multi-agent Claude pipeline.
Six implementation files exist and must be integrated into the current codebase.
The system captures per-agent token usage and cost from the Anthropic SDK response object
at zero prompt overhead — no prompt changes required.

@file careervp-instrumentation/lambda_layer/token_tracker.py
@file careervp-instrumentation/agents/vpr_strategist.py
@file careervp-instrumentation/infrastructure/token_tracking_tables.py
@file careervp-instrumentation/functions/daily_rollup/lambda_function.py
@file careervp-instrumentation/dashboards/query_examples.py
@file careervp-instrumentation/MIGRATION_GUIDE.py

PROBLEM:
The codebase has no per-agent token visibility. All 8 agent Lambdas call
client.messages.create() directly. Costs are only visible in aggregate daily
CSVs from Anthropic's console, not per-agent, per-application, or per-user.

SOLUTION:
Integrate the instrumentation files into the existing project structure, adapting
paths, module names, CDK patterns, and imports to match what is already there.
vpr_strategist.py is a reference implementation showing the complete pattern —
apply the same pattern to all 8 agents.

---

THINK:
1. Read the project structure — find handler locations, CDK stack files, existing
   DynamoDB table definitions, Lambda layer patterns, Step Functions state machine,
   and the API Gateway entry point where Cognito auth is processed
2. Identify the existing Anthropic client instantiation pattern across all agents —
   note the variable name used (client, anthropic_client, etc.)
3. Locate the Step Functions execution input — confirm whether user_id currently
   flows through states or must be added
4. Check existing CDK constructs for DynamoDB table and Lambda layer patterns —
   token_tracking_tables.py contains CloudFormation YAML; translate to matching CDK Python
5. Verify the IAM execution role pattern — find how existing agent Lambda roles are
   defined to know where to attach AgentTokenTrackingPolicy
6. Check if EventBridge scheduled rules already exist in the CDK stack
7. Identify the reporting/admin module location for query_examples.py

---

THEN:

## Step 1: Lambda Layer

Place `token_tracker.py` in the correct layer directory for this project.
If the project uses `aws_cdk.aws_lambda_python_alpha.PythonLayerVersion`, match that pattern.
If it uses a zip-based layer, place in the appropriate build directory.

The layer requires: `boto3` (already in Lambda runtime), `anthropic` SDK.
Check existing layer requirements — add `anthropic` only if not already present.

Register the layer in CDK:
- Name: `careervp-token-tracker`
- Compatible runtime: Python 3.11 (or match existing agents)
- Add to Layers list of all 8 agent Lambda functions

## Step 2: DynamoDB Tables

Add two tables to the existing CDK DynamoDB construct (adapt from token_tracking_tables.py):

Table 1: `careervp-token-usage`
  PK: application_id (S), SK: {timestamp_ms}#{agent_name} (S)
  GSIs: user-id-index (PK: user_id, SK: sk), agent-name-index (PK: agent_name, SK: sk)
  TTL attribute: ttl_epoch
  PITR: enabled
  Billing: PAY_PER_REQUEST

Table 2: `careervp-daily-cost-rollup`
  PK: date_agent (S), SK: model (S)
  Billing: PAY_PER_REQUEST

Pass table names to agent Lambdas as environment variables:
  TOKEN_USAGE_TABLE, DAILY_ROLLUP_TABLE
Follow the existing pattern for environment variable injection — do not hardcode names.

## Step 3: IAM Policy

Add `AgentTokenTrackingPolicy` to all 8 agent Lambda execution roles:
  - dynamodb:PutItem on TokenUsageTable ARN
  - cloudwatch:PutMetricData scoped to namespace CareerVP/TokenUsage

Match the existing IAM grant pattern in this codebase (grant_write, add_to_policy,
or inline policy — use whichever is already established).

## Step 4: Agent Instrumentation — All 8 Agents

Using vpr_strategist.py as the reference, apply to every agent Lambda:

  CHANGE 1 (import):
    Remove:  from anthropic import Anthropic  (or equivalent)
    Add:     from token_tracker import TrackedAnthropicClient

  CHANGE 2 (client instantiation):
    Remove:  client = Anthropic(api_key=os.environ['ANTHROPIC_API_KEY'])
    Add:     tracker = TrackedAnthropicClient(
                 agent_name=AGENT_NAMES[<this_agent>],  # from MIGRATION_GUIDE registry
                 application_id=event['application_id'],
                 user_id=event.get('user_id', 'unknown'),
             )

  CHANGE 3 (API call):
    Remove:  response = client.messages.create(model=..., ...)
    Add:     response = tracker.create(model=..., ..., _stage="primary_generation")

  CHANGE 4 (return value — optional but recommended):
    Add to return dict: "agent_totals": tracker.get_totals()

  Label self-correction and multi-stage calls with distinct _stage values:
    _stage="primary_generation"
    _stage="self_correction_attempt_1"
    _stage="stage6_meta_evaluation"
    (see vpr_strategist.py for full pattern)

Agent name registry (use exact strings for consistency):
  cv-parser, company-research, gap-analysis-question-generator,
  vpr-strategist, cv-tailor, cover-letter-writer,
  interview-prep-generator, quality-validator

## Step 5: user_id Threading

The token tracker requires user_id on every agent invocation.
Source: Cognito JWT `sub` claim, extracted at the API Gateway entry Lambda.

At the orchestrator entry point (where Step Functions execution is started):
  claims = event.get('requestContext', {}).get('authorizer', {}).get('claims', {})
  user_id = claims.get('sub', 'anonymous')

Add user_id to the Step Functions execution input JSON.
In the state machine definition, thread user_id through every state's Parameters block.
Match the existing parameter passing pattern — do not restructure the state machine.

## Step 6: Daily Rollup Lambda

Add `functions/daily_rollup/lambda_function.py` as a new Lambda function in CDK:
  Name: careervp-daily-cost-rollup
  Runtime: Python 3.11
  Timeout: 300s
  Memory: 512MB
  Trigger: EventBridge scheduled rule — cron(0 1 * * ? *)  [01:00 UTC daily]
  Environment: TOKEN_USAGE_TABLE, DAILY_ROLLUP_TABLE, ALERT_TOPIC_ARN, DAILY_COST_THRESHOLD
  IAM: dynamodb:Scan on TokenUsageTable, dynamodb:PutItem on DailyCostRollupTable,
       sns:Publish on CostAlertTopic, cloudwatch:PutMetricData

## Step 7: SNS Alert Topic + CloudWatch Alarms

Add to CDK (adapt from token_tracking_tables.py):

SNS Topic: careervp-cost-alerts
  Pass alert email as CDK context variable or SSM parameter — do not hardcode

CloudWatch Alarm 1: VPR single-call cost > $1.00
  Namespace: CareerVP/TokenUsage, Metric: CostMilliUSD
  Dimension: AgentName=vpr-strategist, Threshold: 1000, Period: 300s

CloudWatch Alarm 2: Daily total tokens > 10M
  Namespace: CareerVP/TokenUsage, Metric: TotalTokens
  Statistic: Sum, Period: 86400s, Threshold: 10000000

## Step 8: Query Helpers

Place `query_examples.py` functions in the appropriate reporting or admin module.
Adapt import paths. These are utility functions — expose via an internal API endpoint
or admin Lambda if the project has one, otherwise place as a standalone utility module.

---

CONSTRAINTS:

DO:
  - Match all existing naming conventions, file structure, and CDK patterns exactly
  - Use existing base classes, decorators, and IAM grant methods already in the project
  - Preserve all existing agent functionality — these are additive changes only
  - Validate user_id is sourced from Cognito auth context per AUTH_NEVER_TRUST_PAYLOAD rule
  - Use environment variables for all table names, topic ARNs, and thresholds
  - Add type hints to all new functions per TYPE_HINTS_REQUIRED rule
  - Catch specific exceptions in token tracking error paths — never bare except:
  - Wrap DynamoDB and CloudWatch calls in try/except with logger.error() — tracking
    failures must never propagate to the agent's primary execution path

DO NOT:
  - Change any agent prompt content, structure, or intent
  - Introduce new external dependencies beyond what token_tracker.py already requires
  - Hardcode table names, ARNs, account IDs, or region strings
  - Suppress CDK Nag warnings without a written justification string
  - Use wildcard IAM actions or resources
  - Extract user_id from event body or query parameters

PROHIBITED:
  - `except:` bare
  - `actions=["dynamodb:*"]` or any wildcard IAM
  - `payload.get('user_id')` or `event.get('user_id')` for identity
  - Hardcoded table names: `table_name = "careervp-token-usage"`
  - `log_event=True` on any Lambda decorator

---

OUTPUT:
  Modify:
    - CDK stack file(s) — tables, layer, rollup Lambda, alarms, IAM grants
    - All 8 agent Lambda handler files — import swap + client swap + _stage labels
    - Step Functions state machine — user_id in input and all state Parameters
    - API Gateway entry Lambda — Cognito sub extraction + user_id in SFN input
    - requirements.txt / pyproject.toml — add anthropic if not present

  Create:
    - lambda_layer/token_tracker.py (or equivalent layer path)
    - functions/daily_rollup/lambda_function.py
    - Reporting utility module with query_examples.py functions
    - INSTRUMENTATION_REPORT.md (see format below)

  INSTRUMENTATION_REPORT.md must contain:
    - AGENTS INSTRUMENTED: agent name, file path, _stage labels added
    - CDK CHANGES: resource name, change type, rule satisfied
    - USER_ID THREADING: entry point identified, states updated
    - CONFLICTS: anything in the reference files that could not be applied as-is, with resolution
    - SKIPPED: any step not applicable, with reason
    - VERIFY: exact commands to confirm instrumentation is working

---

VERIFY:
  # CDK validates cleanly
  npx cdk synth --app='python app.py'

  # Layer size within limits
  du -sh <layer_build_path>/

  # No forbidden patterns introduced
  grep -r "except:" src/backend/careervp/agents/
  grep -r "payload.get.*user_id" src/backend/careervp/
  grep -r "actions.*\*" infrastructure/

  # Token records appear after a test invocation
  aws dynamodb scan --table-name careervp-token-usage --max-items 5

  # Metrics appear in CloudWatch
  aws cloudwatch list-metrics --namespace CareerVP/TokenUsage

  # Rollup Lambda executes cleanly
  aws lambda invoke --function-name careervp-daily-cost-rollup \
    --payload '{"target_date":"<yesterday>"}' /tmp/rollup_out.json \
    && cat /tmp/rollup_out.json
