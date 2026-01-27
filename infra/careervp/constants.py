"""
CareerVP Infrastructure Constants.
All service names, table names, and resource identifiers.
"""

from pathlib import Path

# =============================================================================
# SERVICE IDENTITY
# =============================================================================
SERVICE_NAME = "CareerVP"
SERVICE_NAME_TAG = "service"
OWNER_TAG = "owner"
ENVIRONMENT = "dev"

# =============================================================================
# DYNAMODB TABLES
# =============================================================================
USERS_TABLE_NAME = "users"
SESSIONS_TABLE_NAME = "sessions"
JOBS_TABLE_NAME = "jobs"
IDEMPOTENCY_TABLE_NAME = "idempotency"

# Output keys for CDK
TABLE_NAME_OUTPUT = "UsersTableOutput"
SESSIONS_TABLE_OUTPUT = "SessionsTableOutput"
IDEMPOTENCY_TABLE_NAME_OUTPUT = "IdempotencyTableOutput"

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
GW_RESOURCE = "cv"
GW_RESOURCE_VPR = "vpr"
GW_RESOURCE_USERS = "users"

# Swagger
SWAGGER_RESOURCE = "swagger"
SWAGGER_CSS_RESOURCE = "swagger.css"
SWAGGER_JS_RESOURCE = "swagger.js"
SWAGGER_URL = "SwaggerURL"

# =============================================================================
# LAMBDA FUNCTIONS
# =============================================================================
CV_PARSER_LAMBDA = "CVParser"
VPR_GENERATOR_LAMBDA = "VPRGenerator"
CV_TAILOR_LAMBDA = "CVTailor"
COVER_LETTER_LAMBDA = "CoverLetter"

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
# BUILD PATHS
# =============================================================================
project_root = Path(__file__).parent.parent.parent
BUILD_FOLDER = str(project_root / "src" / "backend" / ".build" / "lambdas")
COMMON_LAYER_BUILD_FOLDER = str(
    project_root / "src" / "backend" / ".build" / "common_layer"
)
