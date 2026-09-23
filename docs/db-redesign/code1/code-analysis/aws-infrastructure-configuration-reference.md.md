CareerVP — AWS Infrastructure Configuration Reference
Purpose: a precise, line-cited breakdown of every AWS resource provisioned by the CareerVP CDK app, as currently defined in code (not as documented elsewhere). Built for validating a future redesign against the AWS Well-Architected Framework. Values are transcribed directly from source — where a value is not explicitly set, that is stated rather than guessed.

Source: infra/careervp/*.py (AWS CDK, Python). All line numbers refer to the files as of this audit.

How to read this doc: each AWS service has its own section with one subsection per resource. A "Critical Findings" section up top collects everything that looks like a bug, inconsistency, or Well-Architected gap — surfaced while extracting the configuration, not assumed. Treat every finding as unverified against runtime behavior — this is a static-code read, not a cdk synth/deployed-account diff.

0. Critical Findings (read this first)
These were surfaced incidentally while extracting configuration and are worth resolving before using this document to validate a redesign — a redesign that "fixes" the wrong copy of a duplicated table, or "fixes" already-dead code, wastes effort.

#	Finding	Where	Why it matters
1	Duplicate, conflicting table/bucket definitions. api_db_construct.py (TableV2/Bucket, active) and dynamodb_stack.py/s3_stack.py (legacy Table/Bucket) both define CVs, Applications, Gap Responses, and Knowledge tables, and a CVs bucket — using the same generated physical name but different partition/sort key attribute names, different billing-mode APIs, and opposite removal policies (DESTROY vs RETAIN).	api_db_construct.py:248-373, dynamodb_stack.py:30-95, s3_stack.py:29-50	If both stacks deploy, CloudFormation name collision fails the deploy or overwrites schema. If only one deploys, the other is dead code with a misleading schema. Confirm which stack is actually in the deployed app (infra/app.py) before trusting either schema.
2	MFA is off. No mfa= kwarg on the Cognito User Pool → CDK default Mfa.OFF.	cognito_construct.py:14-29	Career/resume data (PII) protected by password-only auth.
3	MonitoringNestedStack builds zero dashboards. create_dashboards=False is hardcoded, and the dashboard-factory logic means no alarm dashboard, regular dashboard, or summary dashboard gets created via that nested stack — only alarms/metrics/log-filters.	monitoring.py:214-224, 250	Anyone expecting a CloudWatch dashboard from this stack won't find one; only CrudMonitoring instantiated directly in api_construct.py (mode="dashboards") builds visuals, and it only watches 7 of 30+ Lambdas.
4	Step Functions execution-data logging is deliberately disabled (include_execution_data=False, LogLevel.ERROR only) — an explicit cost-control tradeoff, cdk-nag-suppressed (AwsSolutions-SF1).	artifact_chain_construct.py:332-337; service_stack.py:190-193	Debugging a failed/stuck artifact-chain execution after the fact will be hard — no state input/output is logged, only errors.
5	StartVPR task has no heartbeat_timeout, while its sibling tasks (StartCompanyResearch 180s, StartCoverLetter/StartInterviewPrep 300s) all do — despite a module comment noting VPR is the slowest step.	artifact_chain_construct.py:236-256	A stuck VPR worker with no heartbeat can hang the state machine execution indefinitely (bounded only by the 2-hour overall state-machine timeout).
6	AppConfig deployment strategy is "all at once." Growth factor 100%, deployment duration 0 minutes, final bake time 0 minutes.	configuration/configuration_construct.py:50-59	A bad feature-flag config change rolls out to 100% of traffic instantly with no automatic rollback window — the opposite of AppConfig's progressive-rollout value proposition.
7	Two Lambda-level DLQs are constructed but never wired up. cover_letter_worker_dlq and interview_prep_worker_dlq are created but never passed as on_failure=SqsDlq(...) to their workers' SQS event sources (unlike cv_tailor_worker_dlq, which is correctly wired). billing_webhook_dlq is constructed and never referenced again anywhere.	api_construct.py:1585-1590, 1657-1662, 2505-2513	Failed batches for those two workers, and any billing-webhook failure path, have no dead-letter capture — silent message loss on repeated failure.
8	vpr_worker_func has no event source at all, despite a comment claiming it's "triggered exclusively by the SQS worker DLQ recovery path."	api_construct.py:1414-1479	Function is deployed but structurally unreachable via any AWS event source in this file — either dead code or wired outside this file (needs runtime confirmation).
9	Inconsistent Lambda IAM role assignment. billing_lambda, billing_reconcile_lambda, and export_lambda have no role= kwarg, so each gets its own CDK auto-generated default execution role instead of the shared, audited lambda_role every other handler uses.	api_construct.py:2515-2604	Breaks the single-role least-privilege review pattern; these three Lambdas' permissions must be audited separately from the rest.
10	Environment-gated auth bypass baked into infrastructure. cv_tailoring_func's AUTHORIZER_DISABLED env var is set to "true" whenever constants.ENVIRONMENT != "prod".	api_construct.py:1720-1722	An authorization bypass switch is a legitimate dev convenience, but it living in the CDK construct (not a per-request debug flag) means any environment misconfigured as non-"prod" silently disables authorization for this endpoint.
11	Two dead/unused constructs remain in the codebase: a Lambda-based custom authorizer (_add_api_authorizer_lambda) that's fully built but never attached (the API uses CognitoUserPoolsAuthorizer instead), and vpr_generator_func, explicitly set to None at the call site ("Placeholder for backward compatibility").	api_construct.py:1949-1976, 100, 928-976	Dead code inflates the CDK app and the attack surface under review; confirm intent to delete before the redesign, don't silently port it forward.
12	WAF is production-only. WafToApiGatewayConstruct is only instantiated if is_production_env:.	api_construct.py:240-248	Dev/stage API Gateway has zero WAF protection — inconsistent security posture across environments, worth an explicit decision rather than a default.
13	Over-broad IAM: sqs_kms_access uses Resource: "*" for kms:Decrypt/kms:GenerateDataKey, rather than scoping to the three actual SQS KMS key ARNs (SQSKey, CoverLetterSQSKey, InterviewPrepSQSKey) that exist in the same file.	api_construct.py:771-782	Least-privilege gap — the specific key ARNs are known at synth time and could be scoped.
14	A "backups" bucket is configured to self-destruct. RemovalPolicy.DESTROY + auto_delete_objects=True on the bucket whose stated purpose is backup storage.	api_db_construct.py:594-627	Tearing down the stack deletes the backups meant to protect against that exact scenario.
15	Comment/value mismatches (possible drift): the VPR-results-bucket docstring says "7 days → Delete" but the actual lifecycle rule expires objects at 365 days; company_research_worker_func's timeout comment claims alignment with a "180s heartbeat" but the literal timeout is 120s.	api_db_construct.py:540, 553-559; api_construct.py:2338-2339	Comments no longer match code — a common signal of a change that didn't get fully threaded through, worth double-checking intent before carrying forward in a redesign.
16	No llm_cache conflict, but no "TTL enforcement" either. Every documented TTL duration (90 days on CVs, 365 days on Gap Responses/Knowledge, 30 days on Company Research Cache, "24 hours" on Jobs) is only a code comment — the actual expiry timestamp is written by application code at item-write time, not enforced by CDK/DynamoDB schema.	throughout api_db_construct.py	If application code has a bug and never sets/refreshes the TTL attribute, data will not expire as documented. Worth a redesign-time check of where these attributes are actually written.
1. Naming Conventions (naming_utils.py)
All physical resource names are generated by a shared NamingUtils helper rather than hardcoded — important context for reading every "name pattern" cited below.

Resource type	Pattern	Source
DynamoDB table	resource_name(feature, "table") → f"{prefix}-{slug(feature)}-table-{environment}"	naming_utils.py:88-98
S3 bucket	f"{prefix}-{environment}-{slug(purpose)}-{region_code}-{suffix}"	naming_utils.py:135-137
S3 results bucket (VPR)	same format as bucket name, via a dedicated results_bucket_name method	naming_utils.py:117-122
Region code	Mapped via _REGION_CODE_MAP (e.g. us-east-1 → use1); else first 4 chars of region with dashes stripped, padded with 0	naming_utils.py:148-155
Suffix	hash_override[:6] (slugged) if provided, else first 6 hex chars of sha256(f"{account_id}-{region}-{environment}")	naming_utils.py:139-146
Environment normalization	prod/production → prod; dev/development → dev; staging → staging; else slugified as-is	naming_utils.py:12-18, 57-59
Default region	CDK_DEFAULT_REGION env var → AWS_DEFAULT_REGION → "us-east-1"	naming_utils.py:78-83
Default account ID	CDK_DEFAULT_ACCOUNT env var → literal "000000000000"	naming_utils.py:84-86
Feature-name strings and SERVICE_PREFIX/ENVIRONMENT come from constants.py (§14 below): SERVICE_PREFIX = "careervp", ENVIRONMENT = os.getenv("ENVIRONMENT", "dev").

2. API Gateway
Construct: aws_apigateway.RestApi, logical id service-rest-api, var self.rest_api — api_construct.py:320-368

Property	Value	Line
API name	naming.api_name(constants.API_FEATURE) (computed)	323
Description	"CareerVP API - AI-powered job application assistant"	324
CORS allow origins	Cors.ALL_ORIGINS (*) — comment: "gated at Lambda layer"	326
CORS allow methods	Cors.ALL_METHODS	327
CORS allow headers	Content-Type, Authorization, X-Amz-Date, X-Api-Key, X-Amz-Security-Token	328-334
CORS max age	1 hour	335
Throttling — rate limit	2 requests/sec	338
Throttling — burst limit	10	339
X-Ray tracing	Enabled	340
Metrics	Enabled	341
Logging level	MethodLoggingLevel.INFO	342
Access log destination	Dedicated ApiGatewayAccessLogGroup (retention 1 day, DESTROY, KMS-encrypted with the shared logs key)	313-319, 343-345
Access log format	Custom JSON: requestId, extendedRequestId, ip, caller, user, requestTime, httpMethod, resourcePath, status, protocol, responseLength, integrationStatus, integrationErrorMessage, authorizerError	346-365
CloudWatch role	Enabled	367
Usage plans / API keys	None defined anywhere in the file — the stage throttling settings above are the only rate control	—
Output: CfnOutput (constants.APIGATEWAY) = rest_api.url — lines 370-372

Gateway error responses (api_construct.py:375-406)
4x GatewayResponse (DEFAULT_4_XX, DEFAULT_5_XX, UNAUTHORIZED, ACCESS_DENIED), all with:

Headers: Access-Control-Allow-Origin: '*', Access-Control-Allow-Headers: 'Content-Type,Authorization', Access-Control-Allow-Methods: 'GET,POST,PUT,DELETE,OPTIONS'
Body template: {"error": <code>, "code": <code>, "request_id": "$context.requestId"}
Authorizer
CognitoUserPoolsAuthorizer id CognitoAuth — identity_source = method.request.header.Authorization, pool = the Cognito user pool (api_construct.py:442-451).

Public (unauthenticated) routes — exactly: /health, /auth/register, /auth/login, /auth/refresh, /billing/webhook, /errors (api_construct.py:2781-2790). Every other route requires AuthorizationType.COGNITO.

Integration pattern: all routes use AwsIntegration(service="lambda", proxy=True, integration_http_method="POST", path="2015-03-31/functions/{arn}/invocations") — Lambda-proxy, not native LambdaIntegration (api_construct.py:2803-2812).

Lambda invoke permissions are deduplicated per top-level path prefix (/{first_segment}/*), not per exact route (api_construct.py:2677-2726).

Swagger routes (unauthenticated, api_construct.py:279-310)
Path	Method	Handler
/swagger	GET	cv_upload_func
/swagger.css	GET	cv_upload_func
/swagger.js	GET	cv_upload_func
Feature-prefix proxy routes ({proxy+} + root, ANY, api_construct.py:2728-2836)
Path prefix	Handler	Auth
/auth	auth_api_func	None
/users	user_api_func	Cognito
/gap-analysis	gap_api_func	Cognito
/billing	billing_lambda	Cognito
Explicit route map (api_construct.py:2841-2912)
Path	Method	Handler
/health	GET	health_api_func
/users/me	GET, PUT	user_api_func
/users/me/usage	GET	user_api_func
/users/me/trial/reset	POST	user_api_func
/users/me/cv	POST	cv_upload_func
/users/me/cv	GET	user_api_func
/users/me/subscription	GET	billing_lambda
/jobs	POST, GET	job_api_func
/jobs/{jobId}	GET	job_api_func
/jobs/{jobId}/gap-questions	POST, GET	gap_api_func
/jobs/{jobId}/gap-responses	POST	gap_api_func
/applications/{application_id}	GET	application_api_func
/vpr/generate	POST	vpr_submit_func
/vpr/{vprId}/status	GET	vpr_status_func
/vpr/{vprId}/cancel	POST	vpr_status_func
/vprs	GET	vpr_status_func
/cv-tailoring/generate	POST	cv_tailoring_func
/cv-tailoring/{cvTailoringId}/status	GET	cv_tailoring_func
/cv-tailoring/{cvTailoringId}/cancel	POST	cv_tailoring_func
/cv-tailoring/{cvTailoringId}	DELETE, PATCH	cv_tailoring_func
/cv-tailorings	GET	cv_tailoring_func
/cover-letter/generate	POST	cover_letter_api_func
/cover-letter/{coverLetterId}/status	GET	cover_letter_status_func
/cover-letter/{coverLetterId}/cancel	POST	cover_letter_status_func
/cover-letter/{coverLetterId}	PATCH	cover_letter_status_func
/cover-letters	GET	cover_letter_status_func
/interview-prep/generate	POST	interview_prep_api_func
/interview-prep/{interviewPrepId}/status	GET	interview_prep_status_func
/interview-prep/{interviewPrepId}/cancel	POST	interview_prep_status_func
/interview-prep/{interviewPrepId}	PATCH	interview_prep_status_func
/interview-preps	GET	interview_prep_status_func
/company-research/{jobId}	GET	company_research_func
/company-research/{jobId}/cancel	POST	company_research_func
/company-research/fetch	POST	company_research_func
/knowledge-base	GET	company_research_func
/billing/webhook	POST	billing_lambda
/jobs/{jobId}/artifacts/{moduleType}/export	GET	export_lambda
/ai/assist	POST	ai_assist_lambda (nested stack)
/errors	POST	error_report_lambda (nested stack)
3. Lambda Functions
Unless noted, every function uses: runtime=PYTHON_3_13, code=Code.from_asset(constants.BUILD_FOLDER), architecture=X86_64, logging_format=JSON, system_log_level=INFO, dedicated LogGroup with retention=ONE_DAY, removal_policy=DESTROY, encryption_key=<shared logs KMS key>. Env vars listed are the distinguishing/notable ones per function — most also receive a common block of POWERTOOLS_* and shared-table-name variables.

3.1 API-facing handlers (api_construct.py)
Function	Handler	Timeout	Memory	Retries	Role	Trigger	Line
cv_upload_func (CVParser)	cv_upload_handler.lambda_handler	60s	512 MB	0	shared lambda_role	POST /users/me/cv, swagger routes	864-926
vpr_submit_func	vpr_submit_handler.lambda_handler	30s	256 MB	0	shared	POST /vpr/generate	1132-1186
vpr_status_func	vpr_status_handler.lambda_handler	10s	128 MB	0	shared	GET /vpr/{id}/status, POST /vpr/{id}/cancel, GET /vprs	1188-1240
company_research_func	company_research_handler.lambda_handler	60s	512 MB	0	shared	GET/POST /company-research/*, GET /knowledge-base	978-1025
auth_api_func	auth_handler.lambda_handler	30s	256 MB	0	shared	proxy /auth (unauthenticated)	1755-1797
health_api_func	health_handler.lambda_handler	10s	128 MB	0	shared	GET /health (unauthenticated)	1799-1831
user_api_func	user_handler.lambda_handler	30s	256 MB	0	shared	proxy /users, /users/me*	1833-1872
job_api_func	job_handler.lambda_handler	30s	256 MB	0	shared	/jobs, /jobs/{jobId}	1874-1912
application_api_func	application_handler.lambda_handler	30s	256 MB	0	shared	GET /applications/{id}	1914-1947
gap_api_func	gap_handler.lambda_handler	30s	256 MB	0	shared	proxy /gap-analysis, gap-question/response routes	1978-2015
cover_letter_api_func	cover_letter_submit_handler.lambda_handler	60s	256 MB	0	shared	POST /cover-letter/generate	2355-2392
cover_letter_status_func	cover_letter_handler.lambda_handler	30s	256 MB	0	shared	cover-letter status/cancel/patch/list	2432-2467
interview_prep_api_func	interview_prep_submit_handler.lambda_handler	60s	256 MB	0	shared	POST /interview-prep/generate	2394-2430
interview_prep_status_func	interview_prep_handler.lambda_handler	30s	256 MB	0	shared	interview-prep status/cancel/patch/list	2469-2503
cv_tailoring_func (CVTailor)	cv_tailoring_handler.handler	120s	512 MB	0	shared	cv-tailoring generate/status/cancel/delete/patch/list	1683-1753
billing_lambda	billing_handler.handler	30s	256 MB	0	auto-generated default role (not shared)	proxy /billing, /users/me/subscription, POST /billing/webhook	2515-2563
export_lambda	export_handler.lambda_handler	29s	512 MB	0	auto-generated default role	GET /jobs/{jobId}/artifacts/{moduleType}/export	2565-2604
Notable env vars:

cv_tailoring_func: AUTHORIZER_DISABLED = "true" when constants.ENVIRONMENT != "prod" (see Finding #10).
auth_api_func: JWT_PRIVATE_KEY/JWT_PUBLIC_KEY pulled from SSM at synth time (StringParameter.value_for_string_parameter), plus COGNITO_CLIENT_ID/COGNITO_USER_POOL_ID.
billing_lambda: PAYMENT_PROVIDER_WEBHOOK_SECRET_SSM_PARAM + _PREVIOUS, PRICE_ID_MONTHLY/PRICE_ID_QUARTERLY (all SSM param names), PAYMENT_PROVIDER = "placeholder".
3.2 Async workers (api_construct.py)
Function	Handler	Timeout	Memory	Retries	Trigger	DLQ wired?	Line
cv_upload_worker_func	cv_upload_handler.lambda_handler	300s	512 MB	2	S3 OBJECT_CREATED on CV bucket	Yes — cv_upload_worker_dlq (Lambda-native async DLQ)	1348-1412
vpr_sqs_worker_func	vpr_worker_handler.lambda_handler	10 min	1024 MB	2	SQS vpr_jobs_queue, batch size 1	Via queue's own DLQ (max receive 3)	1242-1302
vpr_dlq_handler_func	vpr_dlq_handler.lambda_handler	30s	128 MB	not set (default)	SQS vpr_jobs_dlq, batch size 1	— (consumes the DLQ itself)	1304-1346
vpr_worker_func	vpr_worker_handler.lambda_handler	10 min	1024 MB	2	none configured (Finding #8)	n/a	1414-1479
cv_tailor_worker_func	cv_tailoring_handler.handler	300s	512 MB	2	DynamoDB Streams on artifacts_table, batch size 1, bisect-on-error	Yes — on_failure=SqsDlq(cv_tailor_worker_dlq)	1481-1537
cover_letter_worker_func	cover_letter_handler.lambda_handler	300s	512 MB	2	SQS cover_letter_jobs_queue, batch size 1	No — cover_letter_worker_dlq built but unattached (Finding #7)	1539-1611
interview_prep_worker_func	interview_prep_handler.lambda_handler	300s	512 MB	2	SQS interview_prep_jobs_queue, batch size 1	No — interview_prep_worker_dlq built but unattached (Finding #7)	1613-1681
company_research_worker_func	company_research_worker_handler.lambda_handler	120s (comment says "aligned to 180s heartbeat" — mismatch, Finding #15)	512 MB	0	SQS company_research_queue, batch size 1	Via queue's own DLQ (max receive 3)	2297-2353
3.3 Step Functions failure handlers & housekeeping (api_construct.py)
Function	Handler	Timeout	Memory	Role	Purpose	Line
cr_failure_handler_func	cr_failure_handler.lambda_handler	30s	128 MB	dedicated failure_handler_role (no states:*)	Company-research chain failure → sets company_research_error=true, state=cr_failed	2223-2256
artifact_failure_handler_func	artifact_failure_handler.lambda_handler	30s	128 MB	dedicated failure_handler_role	Generic chain failure handler for VPR/CV/cover-letter/interview-prep/final-artifacts branches	2258-2295
artifact_cleanup_func	artifact_cleanup_handler.lambda_handler	5 min	256 MB	shared	Deletes stale VPR result objects (results/*)	2158-2190
billing_reconcile_lambda	billing_reconcile_handler.handler	300s	256 MB	auto-generated default role	Daily subscription reconciliation	2606-2638
EventBridge-triggered:

artifact_cleanup_func: rate-based rule, every 1 hour (ArtifactCleanupSchedule, api_construct.py:2145-2150), no input payload.
billing_reconcile_lambda: cron hour=2, minute=0 → 02:00 UTC daily (BillingReconcileScheduleRule, api_construct.py:2640-2654), input {"detail": {"action": "reconcile_subscriptions"}}.
3.4 Nested-stack Lambdas
Function	File	Handler	Timeout	Memory	Role	Trigger
ai_assist_lambda	ai_assist_nested_stack.py:14-233	ai_assist_handler.lambda_handler	25s	512 MB	dedicated AiAssistRole	POST /ai/assist
error_report_lambda	error_report_nested_stack.py:14-124	error_report_handler.lambda_handler	10s	128 MB	dedicated ErrorReportRole	POST /errors
Both nested-stack Lambdas: PYTHON_3_13, X86_64, Tracing.ACTIVE, JSON logging, retry_attempts=0, dedicated 1-day log group encrypted with the shared logs KMS key.

ai_assist_lambda env vars (full list): POWERTOOLS_SERVICE_NAME="careervp-ai-assist", LOG_LEVEL="INFO", ARTIFACTS_TABLE_NAME/CVS_TABLE_NAME/USERS_TABLE_NAME/VPR_TABLE_NAME all mapped to users_table.table_name (single-table design), APPLICATIONS_TABLE_NAME, JOBS_TABLE_NAME, GAP_RESPONSES_TABLE_NAME, COMPANY_RESEARCH_TABLE_NAME (=artifacts_table), ALLOWED_ORIGINS, LLM_CACHE_TABLE_NAME, ANTHROPIC_API_KEY_SSM_PARAM, STRATEGIC_MODEL_ID="claude-sonnet-4-6", TEMPLATE_MODEL_ID="claude-haiku-4-5-20251001", AI_ASSIST_MODEL="claude-haiku-4-5-20251001", AI_ASSIST_TIMEOUT_SECONDS="25" (ai_assist_nested_stack.py:71-112).

ai_assist_lambda IAM: log-write, X-Ray (Resource:*), scoped dynamodb:GetItem/Query on users_table+applications_table+artifacts_table+gap_responses_table (+GSIs where applicable), GetItem on jobs_table, full CRUD on llm_cache_table, ssm:GetParameter scoped to the Anthropic key parameter, and an API-Gateway invoke resource policy scoped to POST /ai/assist (ai_assist_nested_stack.py:115-193). cdk-nag suppressions: AwsSolutions-IAM5, AwsSolutions-L1.

error_report_lambda env vars: POWERTOOLS_SERVICE_NAME="careervp-client-errors", LOG_LEVEL="INFO", ALLOWED_ORIGINS (error_report_nested_stack.py:72-76). IAM: log-write + X-Ray only (comment: "this handler only logs; needs CloudWatch Logs + X-Ray and nothing else"), plus invoke resource policy scoped to POST /errors (error_report_nested_stack.py:80-96).

3.5 Dead / unused code (not deployed)
vpr_generator_func — fully implemented (_add_vpr_lambda_integration, api_construct.py:928-976: handler vpr_handler.lambda_handler, 120s timeout, 1024 MB) but forced to None at the call site, api_construct.py:100 ("Placeholder for backward compatibility").
Lambda authorizer — _add_api_authorizer_lambda (api_construct.py:1949-1976: handler api_gateway_authorizer.lambda_handler, 10s, 256 MB) is defined but never invoked; the API uses CognitoUserPoolsAuthorizer instead.
4. DynamoDB Tables
See Finding #1 — tables 4-7 below have two conflicting definitions. Both are shown; confirm which is actually deployed before treating either as ground truth.

4.1 Users Table (api_db_construct.py:81-129)
Name pattern: {prefix}-users-table-{env}
Partition key: pk (String); Sort key: sk (String)
GSIs: email-index (PK email, projection ALL); user_id-index (PK user_id, SK sk, projection ALL)
Billing: on-demand · PITR: enabled, 7 days · Contributor Insights: enabled (THROTTLED_KEYS)
TTL: not set · Stream: not set · Removal policy: DESTROY
4.2 Idempotency Table (api_db_construct.py:131-152)
Partition key: id (String), no sort key · Billing: on-demand · PITR: enabled, 35 days
TTL attribute: expiration (duration set by application code, not schema) · Removal policy: DESTROY
4.3 Jobs Table / VPR Jobs (api_db_construct.py:201-246)
Partition key: job_id (String), no sort key
GSIs: idempotency-key-index (PK idempotency_key); user_id-index (PK user_id) — both projection ALL
Billing: on-demand · PITR: enabled, 7 days
Stream: NEW_AND_OLD_IMAGES (comment: "drives async worker execution")
TTL attribute: ttl; docstring says 24-hour job data lifetime (app-enforced, not schema) · Removal policy: DESTROY
4.4 CVs Table — CONFLICTING DEFINITIONS
(a) Active — api_db_construct.py:248-272: PK userId, SK cvId; on-demand; PITR 7d; TTL attr expiration (90-day intent, app-enforced); DESTROY. (b) Legacy — dynamodb_stack.py:30-44: PK user_email, SK cv_id — different attribute names; PAY_PER_REQUEST; no PITR; RETAIN.

4.5 Applications Table — CONFLICTING DEFINITIONS
(a) Active — api_db_construct.py:274-309: PK userId, SK applicationId; GSI status-index (PK userId, SK status); on-demand; PITR 7d; DESTROY. (b) Legacy — dynamodb_stack.py:47-61: PK user_email, SK application_id; no GSI; PAY_PER_REQUEST; no PITR; RETAIN.

4.6 Gap Responses Table — CONFLICTING DEFINITIONS
(a) Active — api_db_construct.py:311-335: PK userId, SK questionId; on-demand; PITR 7d; TTL attr expiration (365-day intent); DESTROY. (b) Legacy — dynamodb_stack.py:64-78: PK user_email, SK application_id (differs from (a)'s questionId); PAY_PER_REQUEST; no TTL, no PITR; RETAIN.

4.7 Knowledge Table — CONFLICTING DEFINITIONS
(a) Active — api_db_construct.py:337-373: PK userEmail, SK knowledgeType; GSI entity-index (PK knowledgeType, SK entityId); on-demand; PITR 7d; TTL attr expiration (365-day intent); DESTROY. (b) Legacy — dynamodb_stack.py:81-95: PK user_email, SK entity_type (differs from (a)'s knowledgeType); no GSI; PAY_PER_REQUEST; no TTL; RETAIN.

4.8 Artifacts Table (api_db_construct.py:375-413 — only definition)
PK applicationId, SK artifactId; GSI type-index (PK applicationId, SK artifactType, projection ALL)
Stream: NEW_AND_OLD_IMAGES (comment: "fan out to async document workers")
On-demand; PITR 7d; TTL attr expiration (90-day intent); DESTROY
4.9 Company Research Cache Table (api_db_construct.py:415-440 — only definition)
PK cacheKey, no sort key; on-demand; PITR 7d
TTL attr expiresAt (30-day intent); DESTROY
4.10 LLM Cache Table (api_construct.py:453-480 — the only table literally built in api_construct.py)
Name: {prefix}-llm-cache-{env} · PK cache_key (String) · Billing: on-demand
TTL attribute: expires_at
PITR: conditional — enabled with 7-day recovery only if is_production_env, else disabled
Removal policy: DESTROY regardless of environment
CDK defaults worth stating explicitly
TableV2/legacy Table default encryption when omitted: AWS-owned key (no customer-visible KMS key).
PITR default when omitted: disabled. Contributor Insights default when omitted: disabled.
No Tags.of(...)/tags= appears on any table in any of these files.
5. S3 Buckets
See Finding #1 — the CV bucket has two conflicting definitions.

5.1 CV Bucket — CONFLICTING DEFINITIONS
(a) Active — api_db_construct.py:154-199: SSE-S3, versioned=False, BLOCK_ALL, enforce_ssl=True. CORS: PUT,POST,GET / origins ["*"] (comment: "restrict in production") / max_age=3000s. Lifecycle: → Glacier at 7 days, expire at 30 days. Removal: DESTROY, auto-delete objects. (b) Legacy — s3_stack.py:29-50: SSE-S3, versioned=True (conflicts with (a)), BLOCK_ALL. CORS: origins ["https://careervp.com","http://localhost:3000"] / methods GET,PUT,DELETE / no max_age. No lifecycle rules. enforce_ssl not set (CDK default False — not enforced, unlike (a)). Removal: RETAIN.

5.2 VPR Results Bucket (api_db_construct.py:537-575 — only definition)
SSE-S3, versioned=True, BLOCK_ALL, enforce_ssl=True
CORS: GET only / origins ["https://careervp.com","http://localhost:3000","https://*.amplifyapp.com"] / max_age=3000s
Lifecycle: expire at 365 days, no transitions (docstring says "7 days → Delete" — mismatch, see Finding #15)
Removal: DESTROY, auto-delete objects
5.3 Static Bucket (api_db_construct.py:577-592 — only definition)
SSE-S3, versioned=False, BLOCK_ALL, enforce_ssl=True, no CORS, no lifecycle rules (explicit by design per docstring)
Removal: DESTROY, auto-delete objects
5.4 Backups Bucket (api_db_construct.py:594-627 — only definition)
SSE-S3, versioned=True, BLOCK_ALL, enforce_ssl=True, no CORS
Lifecycle: → Infrequent Access at 30 days, → Glacier at 90 days, no expiration
Removal: DESTROY, auto-delete objects = True — see Finding #14 (backups bucket configured to self-destroy on stack teardown)
5.5 Logs Bucket (api_db_construct.py:629-661 — only definition)
SSE-S3, versioned=True, BLOCK_ALL, enforce_ssl=True, no CORS
Lifecycle: → IA at 180 days, → Glacier at 365 days, no expiration
Removal: DESTROY, auto-delete objects
5.6 Artifacts Bucket (api_db_construct.py:663-695 — only definition)
SSE-S3, versioned=True, BLOCK_ALL, enforce_ssl=True, no CORS
Lifecycle: → IA at 90 days, → Glacier at 180 days, no expiration
Removal: DESTROY, auto-delete objects
5.7 Generated Bucket (s3_stack.py:52-69 — only definition)
SSE-S3, versioned=True, BLOCK_ALL, public_read_access=False
CORS: origins ["https://careervp.com","http://localhost:3000"] / methods GET,PUT / no max_age
enforce_ssl not set (CDK default False) · No lifecycle rules · Removal: RETAIN
5.8 Frontend Bucket (frontend_stack.py:39-55 — see §10)
6. SQS Queues
All queues use receive_message_wait_time=20s (long polling) unless noted. Visibility timeout must exceed downstream Lambda timeout — noted per queue.

6.1 VPR Jobs Queue / DLQ (api_construct.py:1027-1057)
Queue: KMS-encrypted (dedicated SQSKey, rotation on, RETAIN), visibility_timeout=10 min, DLQ after 3 receives
DLQ: SQS_MANAGED encryption, default 4-day retention (not overridden)
Event source: vpr_sqs_worker_func, batch size 1, no batching window, report_batch_item_failures not set (defaults False)
DLQ handler: vpr_dlq_handler_func consumes the DLQ directly, batch size 1
6.2 Cover Letter Jobs Queue / DLQ (api_construct.py:1059-1088)
Queue: KMS-encrypted (dedicated CoverLetterSQSKey), visibility_timeout=300s, DLQ after 3 receives
DLQ: SQS_MANAGED encryption — not wired as on_failure to the worker's event source (Finding #7)
Event source: cover_letter_worker_func, batch size 1
6.3 Interview Prep Jobs Queue / DLQ (api_construct.py:1090-1119)
Queue: KMS-encrypted (dedicated InterviewPrepSQSKey), visibility_timeout=300s, DLQ after 3 receives
DLQ: SQS_MANAGED encryption — not wired as on_failure (Finding #7)
Event source: interview_prep_worker_func, batch size 1
6.4 Company Research Queue (defined in ApiDbConstruct, consumed in api_construct.py:2348-2352)
Event source: company_research_worker_func, batch size 1
company_research_func (API handler) granted sqs:SendMessage only
6.5 Worker DLQs (generic factory, api_construct.py:1121-1130)
retention_period=14 days, QueueEncryption.KMS_MANAGED. Four instances: cv_upload_worker_dlq, cv_tailor_worker_dlq, cover_letter_worker_dlq, interview_prep_worker_dlq. Only the first two are actually wired to their consumer's failure path (Lambda-native DLQ for cv_upload_worker_func; on_failure=SqsDlq(...) on the DynamoDB-stream source for cv_tailor_worker_func) — see Finding #7 for the other two.

6.6 Billing Webhook DLQ (api_construct.py:2505-2513)
retention_period=14 days, KMS_MANAGED — constructed, never referenced again (Finding #7).

6.7 CV Upload / Gap Analysis / Company Research queues (from ApiDbConstruct, per initial inventory)
Six primary queues + DLQs total exist across the app; CV upload and gap analysis queues use visibility_timeout=390s (comment: "must exceed Lambda timeout + 60s buffer"), max receive count 5; company research queue uses 120s visibility timeout, max receive count 3.

7. Step Functions — Artifact Chain (artifact_chain_construct.py)
State machine name: artifact-chain feature slug via NamingUtils · Type: STANDARD · Overall timeout: 2 hours
X-Ray tracing: enabled · Logging: dedicated log group (ONE_WEEK retention, DESTROY, KMS-encrypted), LogLevel.ERROR only, include_execution_data=False (Finding #4) · Removal policy: DESTROY
Chain topology
RouteStartAt (Choice on $.start_at: "vpr" → StartVPR; else → StartCompanyResearch) → StartCompanyResearch (SQS + WAIT_FOR_TASK_TOKEN, 180s heartbeat) → StartVPR (SQS + WAIT_FOR_TASK_TOKEN, no heartbeat set, Finding #5) → AfterVPRRequestedArtifact (Choice: if only VPR requested, Succeed; else continue) → StartCVTailoring (synchronous LambdaInvoke) → GenerateFinalArtifacts (Parallel: StartCoverLetter + StartInterviewPrep, both SQS + WAIT_FOR_TASK_TOKEN, 300s heartbeat each).

Retry policies
Task	Errors	Interval	Max attempts	Backoff
StartCompanyResearch	CRRetryableError	120s	3	2.0x
StartVPR	States.TaskFailed	30s	2	2.0x
StartCVTailoring	States.TaskFailed	30s	2	2.0x
StartCoverLetter	States.TaskFailed	30s	2	2.0x
StartInterviewPrep	States.TaskFailed	30s	2	2.0x
No retry on the GenerateFinalArtifacts Parallel state itself.

Catch / failure handlers
Every task has a dedicated failure-handler Lambda invocation: StartCompanyResearch → HandleCRFailure (catches CRHardFail+States.TaskFailed); StartVPR/StartCVTailoring/StartCoverLetter/StartInterviewPrep/GenerateFinalArtifacts → their respective handlers on States.ALL.

Injected dependencies (not created by this construct): the four SQS queues, cv_tailoring_func, cr_failure_handler, artifact_failure_handler, logs_kms_key.

Cross-references from api_construct.py: grant_start_execution on vpr_submit_func, cover_letter_api_func, interview_prep_api_func, cv_tailoring_func, gap_api_func; grant_task_response on the four SQS workers; cancel-scoped states:StopExecution/DescribeExecution on the five status-checking functions. ARTIFACT_CHAIN_ENABLED defaults to "true" only in dev, else "false" (overridable via env var).

8. Cognito
File: cognito_construct.py

Property	Value
User Pool name	careervp-users-{environment}
Self sign-up	Enabled
Sign-in	Email only
Auto-verify	Email
Account recovery	Email only
Password policy	Min length 8; lowercase/uppercase/digits required; symbols not required
MFA	Off (CDK default — Finding #2)
Lambda triggers	None
User Pool Client name	careervp-client-{environment}
Generate secret	False
Auth flows	user_srp, user_password (not admin_user_password, not custom)
OAuth flows	Authorization code grant, implicit code grant (not client credentials)
OAuth scopes	ADMIN, EMAIL, OPENID, PHONE, PROFILE
Callback URLs (5)	localhost:3000/callback, app.careervp.com/callback, dev.careervp.com/callback, an Amplify preview URL, stage.careervp.com/callback
Logout URLs (5)	Same 5 hosts, root path
Identity providers	Cognito only
Access/ID token validity	1 hour each
Refresh token validity	30 days
Domain prefix	careervp-{environment}
Note in source: callback/logout URLs were deliberately captured from the live dev User Pool Client (ticket "FE-UI-037 step 0") so a parent cdk deploy doesn't revert live auth config.

9. WAF
File: waf_construct.py

Scope: REGIONAL · Default action: Allow · Only associated if is_production_env (Finding #12)
Managed rule groups, priority order, all override_action=none:
AWSManagedRulesCommonRuleSet
AWSManagedRulesAmazonIpReputationList
AWSManagedRulesAnonymousIpList
AWSManagedRulesKnownBadInputsRuleSet
No custom rate-limiting rules, no custom IP sets
Logging: dedicated log group aws-waf-logs-{web_acl_name}, retention 2 weeks, DESTROY; resource policy allows iam.AnyPrincipal() to write logs (broad — worth reviewing); CfnLoggingConfiguration wired to the Web ACL
10. CloudFront / Frontend
File: frontend_stack.py

S3 bucket: careervp-frontend-{environment} · BLOCK_ALL · versioned=True · CORS GET,HEAD from https://{domain}, max_age=3600 · Removal: RETAIN in production, DESTROY otherwise; auto_delete_objects = not is_production.

Origin: S3OriginAccessControl (OAC, not legacy OAI) — modern, correct pattern.

Distribution: viewer protocol REDIRECT_TO_HTTPS; cache policy CACHING_OPTIMIZED (managed); origin request policy / allowed methods / cached methods / price class / default root object all not explicitly set (CDK defaults: ALLOW_GET_HEAD, CACHE_GET_HEAD, PRICE_CLASS_ALL, index.html); compression enabled. Custom error responses: 403→200 and 404→200, both to /index.html (SPA routing), 0s cache TTL.

ACM certificate — only created if all three are true: region is us-east-1, a hosted zone name resolves, and enable_custom_domain is truthy. Domain careervp.com (hardcoded, not the stack's domain param), SAN *.careervp.com, DNS validation.

enable_custom_domain gating (exact): CDK context key enable_custom_domain → env var ENABLE_CUSTOM_DOMAIN → values "true"/"1"/"yes" enable it; defaults to disabled. Distribution only gets domain_names/certificate if the certificate was actually created — so this one flag gates both ACM and the CloudFront alias.

Route53: A-alias record to the CloudFront distribution, only created if enable_custom_domain is true and the hosted-zone lookup succeeds (wrapped in try/except — any lookup failure silently skips record creation).

Stack outputs: CloudFrontUrl, BucketName, DistributionId.

11. KMS Keys
Key	Purpose	Rotation	Removal	Notes
CloudWatchLogsKey (api_construct.py:408-440)	Encrypts nearly every Lambda's log group + API Gateway access logs (35+ consumers)	Enabled	RETAIN	Resource policy scoped via kms:EncryptionContext:aws:logs:arn condition to logs.{region}.amazonaws.com
SQSKey (api_construct.py:1029-1034)	VPR jobs queue encryption	Enabled	RETAIN	—
CoverLetterSQSKey (api_construct.py:1070-1075)	Cover letter queue encryption	Enabled	RETAIN	—
InterviewPrepSQSKey (api_construct.py:1101-1106)	Interview prep queue encryption	Enabled	RETAIN	—
MonitoringKey (monitoring.py:65-70)	SNS topic (alarm notifications) encryption	Enabled	DESTROY, 7-day pending window	No explicit key policy set (CDK default)
DLQs use AWS-managed KMS (KMS_MANAGED) or SQS_MANAGED, not these customer keys. The shared sqs_kms_access IAM policy (§13) is scoped to Resource: "*" rather than these specific key ARNs — Finding #13.

12. CloudWatch (Logs, Alarms, Dashboards)
Log groups
Nearly every Lambda gets a dedicated log group, RetentionDays.ONE_DAY, RemovalPolicy.DESTROY, encrypted with CloudWatchLogsKey. Exceptions: the Step Functions log group uses ONE_WEEK; the WAF log group uses TWO_WEEKS.

Alarms — via CrudMonitoring (monitoring.py, high/low-level facades)
High-level dashboard: API Gateway 5xx fault-rate alarm, max error rate threshold 1% (only if alarms enabled). Custom KPI metric ValidCreateOrderEvents (namespace careervp_kpi), daily period — informational, not alarmed.
Low-level dashboard: per-monitored-Lambda p90 latency alarm, threshold 3 seconds; log-metric-filter alarm on literal pattern "ERROR" in each function's logs; per-function DynamoValidationException metric filter + alarm (threshold 1, 1 evaluation period, 1 datapoint, NOT_BREACHING on missing data, comparison operator not set → CDK default GREATER_THAN_OR_EQUAL_TO_THRESHOLD). DynamoDB table monitoring on db and idempotency_table (PAY_PER_REQUEST billing mode), no explicit thresholds (facade defaults).
Monitored Lambdas (only 7 of 30+): cv_upload_func, vpr_submit_func, company_research_func, cv_tailoring_func, gap_api_func, cover_letter_api_func, interview_prep_api_func (api_construct.py:221-238, mode="dashboards").
MonitoringNestedStack hardcodes create_dashboards=False → builds no dashboards at all through that path (Finding #3); alarms/metrics/log-filters still apply per mode (default "all").
Billing alarm: BillingLambdaErrorAlarm — metric_errors, 5-min period, sum statistic, threshold 1, 1 evaluation period, NOT_BREACHING.
Company research alarms (company_research_nested_stack.py): TavilySearchFailureAlarm (threshold 5, 3 eval periods, 2 datapoints-to-alarm, 5-min period) and CompanyResearchAllSourcesFailedAlarm (threshold 0, i.e. any occurrence, 1/1, 5-min period). Both notify via SNS action on the shared notification_topic.
DynamoValidationException metric filters use FilterPattern.literal('"ValidationException"') per monitored function.
Dashboards
Two MonitoringFacade-driven dashboards ("Order REST API High Level Dashboard", "Orders REST API Low Level Dashboard" — dashboard titles reference "Order(s)", likely inherited from a template, not renamed for CareerVP) — only produced via the direct CrudMonitoring instantiation in api_construct.py, not via MonitoringNestedStack.

13. SNS
Topic	File	Encryption	Subscriptions	Purpose
{id}alarms (monitoring topic)	monitoring.py:73-89	MonitoringKey (KMS)	None defined	Alarm notification target; resource policy allows cloudwatch.amazonaws.com to publish
notification_topic	passed into company_research_nested_stack.py, defined elsewhere (likely same monitoring topic)	—	None defined	Company-research failure alarms
No .add_subscription(...) call exists anywhere in the read files — meaning no one is actually subscribed to receive these alarm notifications (email/SMS/Lambda/etc.) unless wired outside the files reviewed here. Worth confirming at redesign time.

14. EventBridge
Rule	Schedule	Target	Input	Line
ArtifactCleanupSchedule	Rate: every 1 hour	artifact_cleanup_func	None	api_construct.py:2145-2150
BillingReconcileScheduleRule	Cron: hour=2, minute=0 (02:00 UTC daily)	billing_reconcile_lambda	{"detail": {"action": "reconcile_subscriptions"}}	api_construct.py:2640-2654
15. IAM
Shared lambda_role (api_construct.py:501-819)
Assumed by lambda.amazonaws.com; managed policy AWSLambdaBasicExecutionRole; 20 inline policy statements covering scoped CRUD on every DynamoDB table (with GSI ARNs where applicable — artifacts_table additionally grants Scan), scoped S3 object/list actions on every bucket, VPR-queue send/receive/delete, ssm:GetParameter scoped to the Anthropic key parameter, and Cognito admin actions (AdminConfirmSignUp, AdminGetUser, AdminUserGlobalSignOut) scoped to the user pool ARN. One over-broad statement: sqs_kms_access on Resource: "*" (Finding #13).

Used by: every handler/worker Lambda except billing_lambda, billing_reconcile_lambda, export_lambda (auto-generated default roles — Finding #9), cr_failure_handler_func/artifact_failure_handler_func (dedicated failure_handler_role), and the two nested-stack Lambdas (their own dedicated roles).

failure_handler_role (api_construct.py:2204-2221)
Deliberately narrow: AWSLambdaBasicExecutionRole + applications_table.grant_read_write_data. Explicitly excludes states:* permissions by design, to avoid a CloudFormation dependency cycle with the Step Functions stack.

Dedicated roles: AiAssistRole, ErrorReportRole
See §3.4 for their exact grants — each scoped tightly to only what its Lambda needs.

CompanyResearchTavilyAccessPolicy (company_research_nested_stack.py:64-90)
Standalone CfnPolicy attached to the (imported) company-research role: ssm:GetParameter scoped to the Tavily key parameter, plus DynamoDB CRUD scoped to company_research_cache_table.

16. SSM Parameter Store
All referenced by the app but not created by CDK (assumed to be provisioned out-of-band):

Parameter	Pattern	Consumed by
Anthropic API key	/careervp/{environment}/anthropic-api-key	lambda_role-holders, ai_assist_lambda, cv_tailoring_func, several workers
Tavily API key	/careervp/{environment}/tavily-api-key	Company research Lambda + worker
JWT private/public keys	not a documented fixed path in the files read — pulled via StringParameter.value_for_string_parameter at synth time	auth_api_func, user_api_func, cv_upload_func
Payment provider webhook secret (current + previous)	/careervp/{environment}/payment-provider-webhook-secret[-previous]	billing_lambda
Price IDs (monthly/quarterly)	/careervp/{environment}/payment-provider-price-{monthly,quarterly}	billing_lambda
None of these are provisioned as SecureString vs String from what's visible in CDK (SSM parameter values are managed outside CDK) — worth confirming parameter type and rotation posture directly in the AWS account.

17. AppConfig (configuration/configuration_construct.py)
Application name: f"{construct_id}{service_name}" (truncated to 64 chars)
Environment name: the raw environment string (e.g. "dev"); deletion protection bypassed
Deployment strategy: linear, growth factor 100%, deployment duration 0 min, final bake time 0 min — i.e. instant 100% rollout, no automatic rollback window (Finding #6)
Configuration type: FREEFORM (not FEATURE_FLAGS)
Content source: local JSON file at synth time — configuration/json/{environment}_configuration.json
Validation: a Pydantic model check at CDK synth time (FeatureFlagsConfiguration.model_validate_json(...)), not a native AWS AppConfig JSON_SCHEMA/LAMBDA validator resource
18. Nested Stacks — summary
Nested stack	Creates	Notably does NOT create
AiAssistNestedStack	ai_assist_lambda, dedicated role, dedicated log group	Tables/queues (all passed in as props)
ErrorReportNestedStack	error_report_lambda, dedicated role, dedicated log group	Same — minimal footprint by design (comment: parent stack near the CFN 500-resource limit)
CompanyResearchNestedStack	IAM policy (CompanyResearchTavilyAccessPolicy), 2 CloudWatch alarms	The Lambdas themselves (imported via props)
MonitoringNestedStack	Alarms/metrics/log-filters per mode (default "all")	Any dashboards (create_dashboards=False hardcoded — Finding #3)
19. ServiceStack wiring (service_stack.py)
Instantiation order: ConfigurationStore → CognitoConstruct → ApiConstruct (receives the AppConfig application name + Cognito pool/client) → MonitoringNestedStack (watches 7 named Lambdas + the two core tables) → AiAssistNestedStack (routes registered on self.api after the nested stack's Lambda exists) → ErrorReportNestedStack (same pattern) → CompanyResearchNestedStack.

allowed_origins resolution (identical logic, duplicated in two places — service_stack.py and again inside api_construct.py's billing/export Lambdas): CDK context key allowed_origins, falling back to a hardcoded 7-URL list (Amplify preview URLs + app/dev/stage.careervp.com + localhost:3000).

Environment conditionality: the only environment-conditional constructor param visible at this layer is is_production_env: bool, forwarded straight into ApiConstruct — no branching logic lives in ServiceStack itself.

cdk-nag: AwsSolutionsChecks(verbose=True) applied stack-wide, with explicit suppressions for IAM4/IAM5 (wildcards), a full set of API Gateway checks (APIG1/2/3/4/6), Cognito checks (COG1/3/4), L1 (Python 3.13 false positive), S1 (bucket logging), SQS3/4 (DLQ/encryption), and SF1 (Step Functions logging — explicitly tied to the cost-control decision in Finding #4).

Tags: service=CareerVP, owner=<current user>, feature=<stack feature, default "crud">.

20. constants.py — reference table
Selected AWS-relevant constants (not exhaustive — see source for the full list):

Constant	Value
SERVICE_NAME	"CareerVP"
SERVICE_PREFIX	"careervp"
ENVIRONMENT	os.getenv("ENVIRONMENT", "dev")
STACK_FEATURE	os.getenv("CAREERVP_STACK_FEATURE", "crud")
Table name constants	users, sessions, jobs, idempotency, llm-cache, cvs, applications, gap-responses, knowledge, artifacts, company-research-cache
Queue name constants	vpr-jobs[-dlq], cv-upload, gap-analysis, cover-letter-jobs[-dlq], interview-prep-jobs[-dlq], company-research, cv-tailoring
Bucket name constants	vpr-results, generated, static, backups, logs, artifacts, cvs (=CV_BUCKET_NAME), outputs
API_HANDLER_LAMBDA_MEMORY_SIZE	512 MB
API_HANDLER_LAMBDA_TIMEOUT	60 seconds
METRICS_NAMESPACE	"careervp_kpi"
CONFIGURATION_NAME	"careervp_config"
CONFIGURATION_MAX_AGE_MINUTES	"5"
ANTHROPIC_API_KEY_SSM_PARAM	/careervp/{ENVIRONMENT}/anthropic-api-key
TAVILY_API_KEY_SSM_PARAM	/careervp/{ENVIRONMENT}/tavily-api-key
STRATEGIC_MODEL_ID	"claude-sonnet-4-6"
TEMPLATE_MODEL_ID	"claude-haiku-4-5-20251001"
WEBHOOK_SECRET_SSM_PARAM	/careervp/{ENVIRONMENT}/payment-provider-webhook-secret
PRICE_ID_MONTHLY_SSM_PARAM / ..._QUARTERLY_SSM_PARAM	/careervp/{ENVIRONMENT}/payment-provider-price-{monthly,quarterly}
BUILD_FOLDER	src/backend/.build/lambdas (relative to repo root)
No literal region/account constants exist — both are resolved dynamically at synth time via NamingUtils / CDK Aws.REGION / Aws.ACCOUNT_ID.

Appendix: What this document does not verify
Deployed state. This is a static read of CDK source, not a cdk diff or cdk synth against a live account. Duplicate-table conflicts (Finding #1), unused constructs, and "not wired up" DLQs are all code-level observations — confirm against the actually-deployed stack (infra/app.py for which stacks are synthesized) before acting on them.
Application-level enforcement of documented TTLs, encryption of data-at-rest beyond what's visible in CDK props, and SSM parameter types/rotation — these live outside the CDK layer and weren't inspected here.
Cost. No pricing/cost data was extracted; this is configuration only.