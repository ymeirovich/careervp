"""CareerVP Infrastructure Constants."""

from __future__ import annotations

import os
from pathlib import Path

# =============================================================================
# SERVICE IDENTITY
# =============================================================================
SERVICE_NAME = "CareerVP"
SERVICE_PREFIX = "careervp"
SERVICE_NAME_TAG = "service"
OWNER_TAG = "owner"
ENVIRONMENT = os.getenv("ENVIRONMENT", "dev")
STACK_FEATURE = os.getenv("CAREERVP_STACK_FEATURE", "crud")
API_FEATURE = os.getenv("CAREERVP_API_FEATURE", "core")
MONITORING_FEATURE = os.getenv("CAREERVP_MONITORING_FEATURE", "monitoring")

# =============================================================================
# DYNAMODB TABLES
# =============================================================================
USERS_TABLE_NAME = "users"
SESSIONS_TABLE_NAME = "sessions"
JOBS_TABLE_NAME = "jobs"
IDEMPOTENCY_TABLE_NAME = "idempotency"
LLM_CACHE_TABLE_NAME = "llm-cache"
CVS_TABLE_NAME = "cvs"
APPLICATIONS_TABLE_NAME = "applications"
GAP_RESPONSES_TABLE_NAME = "gap-responses"
KNOWLEDGE_TABLE_NAME = "knowledge"
ARTIFACTS_TABLE_NAME = "artifacts"
COMPANY_RESEARCH_CACHE_TABLE_NAME = "company-research-cache"

# Output keys for CDK
TABLE_NAME_OUTPUT = "UsersTableOutput"
SESSIONS_TABLE_OUTPUT = "SessionsTableOutput"
IDEMPOTENCY_TABLE_NAME_OUTPUT = "IdempotencyTableOutput"
JOBS_TABLE_OUTPUT = "JobsTableOutput"
LLM_CACHE_TABLE_OUTPUT = "LlmCacheTableOutput"
CVS_TABLE_OUTPUT = "CvsTableOutput"
APPLICATIONS_TABLE_OUTPUT = "ApplicationsTableOutput"
GAP_RESPONSES_TABLE_OUTPUT = "GapResponsesTableOutput"
KNOWLEDGE_TABLE_OUTPUT = "KnowledgeTableOutput"
ARTIFACTS_TABLE_OUTPUT = "ArtifactsTableOutput"
COMPANY_RESEARCH_CACHE_TABLE_OUTPUT = "CompanyResearchCacheTableOutput"

# Lambda environment variable keys
LLM_CACHE_TABLE_NAME_ENV = "LLM_CACHE_TABLE_NAME"

# =============================================================================
# SQS QUEUES
# =============================================================================
# VPR Async Architecture queues
VPR_JOBS_QUEUE = "vpr-jobs"
VPR_JOBS_DLQ = "vpr-jobs-dlq"
CV_UPLOAD_QUEUE = "cv-upload"
GAP_ANALYSIS_QUEUE = "gap-analysis"
COVER_LETTER_JOBS_QUEUE = "cover-letter-jobs"
COVER_LETTER_JOBS_DLQ = "cover-letter-jobs-dlq"
INTERVIEW_PREP_JOBS_QUEUE = "interview-prep-jobs"
INTERVIEW_PREP_JOBS_DLQ = "interview-prep-jobs-dlq"
# Artifact Chain async queues (FE-UI-031)
COMPANY_RESEARCH_QUEUE = "company-research"
CV_TAILORING_QUEUE = "cv-tailoring"

# =============================================================================
# S3 BUCKETS
# =============================================================================
# VPR Async Architecture buckets
VPR_RESULTS_BUCKET = "vpr-results"
GENERATED_BUCKET_NAME = "generated"
STATIC_BUCKET_NAME = "static"
BACKUPS_BUCKET_NAME = "backups"
LOGS_BUCKET_NAME = "logs"
ARTIFACTS_BUCKET_NAME = "artifacts"

# =============================================================================
# LAMBDA FUNCTIONS
# =============================================================================
# VPR Async Architecture Lambdas
VPR_SUBMIT_LAMBDA = "vpr-submit"
VPR_WORKER_LAMBDA = "vpr-worker"
VPR_STATUS_LAMBDA = "vpr-status"

# VPR Async Lambda features
VPR_SUBMIT_FEATURE = "vpr-submit"
VPR_WORKER_FEATURE = "vpr-worker"
VPR_STATUS_FEATURE = "vpr-status"

# =============================================================================
# S3 BUCKETS
# =============================================================================
CV_BUCKET_NAME = "cvs"
OUTPUTS_BUCKET_NAME = "outputs"
CV_BUCKET_OUTPUT = "CVBucketOutput"

# =============================================================================
# API GATEWAY
# =============================================================================
APIGATEWAY = "Apigateway"
API_ROOT_RESOURCE = "api"
GW_RESOURCE = "cv"
GW_RESOURCE_VPR = "vpr"
GW_RESOURCE_USERS = "users"
GW_RESOURCE_COMPANY_RESEARCH = "company-research"
GW_RESOURCE_CV_TAILORING = "cv-tailoring"

# Swagger
SWAGGER_RESOURCE = "swagger"
SWAGGER_CSS_RESOURCE = "swagger.css"
SWAGGER_JS_RESOURCE = "swagger.js"
SWAGGER_URL = "SwaggerURL"

# =============================================================================
# LAMBDA FUNCTIONS
# =============================================================================
CV_PARSER_LAMBDA = "CVParser"
CV_PARSER_FEATURE = "cv-parser"
VPR_GENERATOR_LAMBDA = "VPRGenerator"
VPR_GENERATOR_FEATURE = "vpr-generator"
CV_TAILOR_LAMBDA = "CVTailor"
COVER_LETTER_LAMBDA = "CoverLetter"
COMPANY_RESEARCH_LAMBDA = "CompanyResearch"
COMPANY_RESEARCH_FEATURE = "company-research"
LAMBDA_SERVICE_NAME = "lambda"

# Artifact Chain Lambdas + state machine (FE-UI-031)
COMPANY_RESEARCH_WORKER_FEATURE = "company-research-worker"
CR_FAILURE_HANDLER_FEATURE = "cr-failure-handler"
ARTIFACT_FAILURE_HANDLER_FEATURE = "artifact-failure-handler"
ARTIFACT_CHAIN_STATE_MACHINE_FEATURE = "artifact-chain"
ARTIFACT_CHAIN_ARN_OUTPUT = "ArtifactChainStateMachineArn"

LAMBDA_LAYER_NAME = "common"
API_HANDLER_LAMBDA_MEMORY_SIZE = 512  # MB - increased for CV parsing
API_HANDLER_LAMBDA_TIMEOUT = 60  # seconds - increased for LLM calls
LAMBDA_BASIC_EXECUTION_ROLE = "AWSLambdaBasicExecutionRole"
SERVICE_ROLE_ARN = "ServiceRoleArn"

# =============================================================================
# OBSERVABILITY
# =============================================================================
METRICS_NAMESPACE = "careervp_kpi"
METRICS_DIMENSION_KEY = "service"
POWERTOOLS_SERVICE_NAME = "POWERTOOLS_SERVICE_NAME"
POWERTOOLS_TRACE_DISABLED = "POWERTOOLS_TRACE_DISABLED"
POWER_TOOLS_LOG_LEVEL = "LOG_LEVEL"
MONITORING_TOPIC = "MonitoringTopic"

# =============================================================================
# APP CONFIG (Feature Flags)
# =============================================================================
CONFIGURATION_NAME = "careervp_config"
CONFIGURATION_MAX_AGE_MINUTES = "5"

# =============================================================================
# BILLING LAMBDA
# =============================================================================
BILLING_LAMBDA = "billing"
BILLING_FEATURE = "billing"
EXPORT_FEATURE = "export"
BILLING_RECONCILE_LAMBDA = "billing-reconcile"
BILLING_RECONCILE_FEATURE = "billing-reconcile"

# SQS — webhook partial-failure DLQ
BILLING_WEBHOOK_DLQ = "billing-webhook-dlq"

# =============================================================================
# SSM PARAMETERS
# =============================================================================
ANTHROPIC_API_KEY_SSM_PARAM = f"/careervp/{ENVIRONMENT}/anthropic-api-key"
ANTHROPIC_API_KEY_ENV_VAR = "ANTHROPIC_API_KEY_SSM_PARAM"

# =============================================================================
# LLM MODEL IDs  — update here + cdk deploy to swap models, no code change needed
# =============================================================================
STRATEGIC_MODEL_ID = "claude-sonnet-4-6"  # VPR, Gap Analysis
TEMPLATE_MODEL_ID = (
    "claude-haiku-4-5-20251001"  # CV Tailoring, Cover Letter, Interview Prep
)
STRATEGIC_MODEL_ID_ENV_VAR = "STRATEGIC_MODEL_ID"
TEMPLATE_MODEL_ID_ENV_VAR = "TEMPLATE_MODEL_ID"

# Payment provider — webhook secrets (primary + previous for zero-downtime rotation)
WEBHOOK_SECRET_SSM_PARAM = f"/careervp/{ENVIRONMENT}/payment-provider-webhook-secret"
WEBHOOK_SECRET_PREVIOUS_SSM_PARAM = (
    f"/careervp/{ENVIRONMENT}/payment-provider-webhook-secret-previous"
)
WEBHOOK_SECRET_ENV_VAR = "PAYMENT_PROVIDER_WEBHOOK_SECRET_SSM_PARAM"
WEBHOOK_SECRET_PREVIOUS_ENV_VAR = "PAYMENT_PROVIDER_WEBHOOK_SECRET_PREVIOUS_SSM_PARAM"

# Payment provider — price IDs
PRICE_ID_MONTHLY_SSM_PARAM = f"/careervp/{ENVIRONMENT}/payment-provider-price-monthly"
PRICE_ID_QUARTERLY_SSM_PARAM = (
    f"/careervp/{ENVIRONMENT}/payment-provider-price-quarterly"
)

# =============================================================================
# BUILD PATHS
# =============================================================================
project_root = Path(__file__).parent.parent.parent
BUILD_FOLDER = str(project_root / "src" / "backend" / ".build" / "lambdas")
COMMON_LAYER_BUILD_FOLDER = str(
    project_root / "src" / "backend" / ".build" / "common_layer"
)
