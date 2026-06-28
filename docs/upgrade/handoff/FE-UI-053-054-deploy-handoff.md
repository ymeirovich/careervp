# /goal FE-UI-053-054 Deploy + Smoke
# Model: opus | Effort: medium
# Prereq: FE-UI-053-backend-handoff gate AND FE-UI-054-frontend-handoff DoD both confirmed

GOAL: Verify live AWS state, review cdk diff, deploy (user approval gate), smoke test
end-to-end. This session makes real AWS changes. Stop and report before each
irreversible action.

## LIVE STATE TO RE-VERIFY BEFORE ANY DEPLOY (state may have drifted)

Run each; compare to expected; STOP and report any mismatch before proceeding.

1. Worker event-source mapping still ENABLED:
   aws lambda list-event-source-mappings \
     --function-name careervp-company-research-worker-lambda-dev \
     --region us-east-1 \
     --query 'EventSourceMappings[].{State:State,Source:EventSourceArn}' \
     --output json
   Expected: State='Enabled', Source contains 'careervp-company-research-queue-dev'.

2. Queue exists and is reachable:
   aws sqs get-queue-url \
     --queue-name careervp-company-research-queue-dev \
     --region us-east-1
   Expected: QueueUrl returned, no error.

3. DLQ exists:
   aws sqs get-queue-url \
     --queue-name careervp-company-research-dlq-dev \
     --region us-east-1
   Expected: QueueUrl returned.

4. Current handler Lambda has NO queue env yet (proving deploy is still needed):
   aws lambda get-function-configuration \
     --function-name careervp-company-research-lambda-dev \
     --region us-east-1 \
     --query 'Environment.Variables.COMPANY_RESEARCH_QUEUE_URL' \
     --output text
   Expected: 'None' (not yet deployed). If already set, skip deploy of env var — infra is ahead.

5. Artifacts table exists and is accessible:
   aws dynamodb describe-table \
     --table-name careervp-artifacts-table-dev \
     --region us-east-1 \
     --query 'Table.TableStatus' --output text
   Expected: ACTIVE.

## EXPECTED CDK DIFF (scope check — stop if diff is larger than this)

Expected delta (FE-UI-053 R4 only):
  ~ AWS::IAM::Policy  (scoped sqs:SendMessage on CR queue ARN added to CR handler role)
  ~ AWS::Lambda::Function  (COMPANY_RESEARCH_QUEUE_URL env var added to CR handler)

If diff includes changes outside the CR handler IAM + env: STOP. Report what changed
and get user approval before deploying. Do not deploy unexpected infra changes.

## APPROVAL GATE — do not proceed past this point without explicit user approval

Report the live-state verification results and cdk diff output to the user.
State: "Ready to deploy. Diff is scoped to CR handler IAM + env var only.
Awaiting your approval to run cdk deploy."

## DEPLOY

cd infra && npx cdk deploy --require-approval never 2>&1 | tee /tmp/cdk-deploy-output.txt
(Adjust stack name to match repo convention if needed — check cdk.json for app entry.)
Expected: UPDATE_COMPLETE on the stack; no rollback.

If deploy fails: read the CloudFormation failure reason from the output before
attempting any fix. Report the error + root cause to user before retrying.

## SMOKE TEST — end-to-end verification

Wait 30s after deploy completes before starting smoke tests (Lambda config propagation).

Step S1 — POST enqueues and returns 202:
  Get a valid auth token (check repo for how other e2e tests obtain tokens).
  Use a known jobId from dev environment.
  POST /company-research/fetch with {job_id, company_name, url}.
  Assert: HTTP 202, body has {status:'processing', request_id}.
  Assert: handler Lambda CloudWatch has a new invocation log within 60s:
    aws logs tail /aws/lambda/careervp-company-research-lambda-dev \
      --since 5m --region us-east-1

Step S2 — processing row written:
  aws dynamodb get-item \
    --table-name careervp-artifacts-table-dev \
    --key '{"applicationId":{"S":"JOB_ID"},"artifactId":{"S":"ARTIFACT#COMPANY_RESEARCH#JOB_ID"}}' \
    --region us-east-1
  Assert: Item exists with status='processing'.

Step S3 — worker Lambda fires within 60s:
  aws logs tail /aws/lambda/careervp-company-research-worker-lambda-dev \
    --since 5m --region us-east-1
  Assert: new invocation log with the job_id present.

Step S4 — GET reflects terminal status (poll until terminal or 5min):
  GET /company-research/{jobId} every 30s. Assert: eventually returns
  status='completed' (data present) or status='failed' (not 'processing' forever).
  Report which terminal state and the confidence score from worker logs if visible.

Step S5 — Frontend smoke (manual or playwright):
  Load /applications/{jobId}/company-research in browser.
  Reload mid-poll. Assert: polling resumes without re-triggering POST.
  Navigate away and return. Assert: same.

## DEFINITION OF DONE
- [ ] All 5 live-state checks passed before deploy.
- [ ] cdk diff scoped to CR handler IAM + env only; user approved.
- [ ] Deploy UPDATE_COMPLETE.
- [ ] S1: POST returns 202 + handler log visible.
- [ ] S2: processing row in DynamoDB immediately post-POST.
- [ ] S3: worker Lambda invoked within 60s.
- [ ] S4: GET reaches terminal state (completed or failed); never perpetual processing.
- [ ] S5: reload + navigate-away-return both resume without re-triggering POST.
- [ ] Report final smoke result to user before closing session.
