#!/bin/bash
#
# Wait for API Availability Script
# Polls the API Gateway endpoint with exponential backoff until it becomes available.
# Prevents premature smoke tests that fail due to DNS propagation delays.
#
# Usage: .github/scripts/wait-for-api.sh <aws_region> <stack_name>
# Example: .github/scripts/wait-for-api.sh us-east-1 CareerVpCrudDev
#

set -euo pipefail

REGION="${1:-us-east-1}"
STACK_NAME="${2:-}"

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() { echo -e "${GREEN}[WAIT-API]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WAIT-API]${NC} $1"; }
log_error() { echo -e "${RED}[WAIT-API]${NC} $1"; }

# Validate inputs
if [ -z "$STACK_NAME" ]; then
    log_error "Usage: $0 <aws_region> <stack_name>"
    log_error "Stack name is required"
    exit 1
fi

echo "=========================================="
log_info "Waiting for API Availability"
echo "Stack: $STACK_NAME"
echo "Region: $REGION"
echo "=========================================="

# Get API Gateway URL from CloudFormation outputs
log_info "Fetching API Gateway endpoint..."
API_URL=$(aws cloudformation describe-stacks \
    --stack-name "$STACK_NAME" \
    --region "$REGION" \
    --query "Stacks[0].Outputs[?OutputKey=='ApiGateway'].OutputValue" \
    --output text 2>/dev/null) || API_URL=""

if [ -z "$API_URL" ] || [ "$API_URL" = "None" ]; then
    log_warn "Could not find ApiGateway output. Trying Apigateway..."
    API_URL=$(aws cloudformation describe-stacks \
        --stack-name "$STACK_NAME" \
        --region "$REGION" \
        --query "Stacks[0].Outputs[?OutputKey=='Apigateway'].OutputValue" \
        --output text 2>/dev/null) || API_URL=""
fi

if [ -z "$API_URL" ] || [ "$API_URL" = "None" ]; then
    log_error "Could not find API Gateway URL in stack outputs"
    log_error "Stack may not have completed deployment"
    exit 1
fi

log_info "API Gateway URL: $API_URL"

# Health endpoint check
HEALTH_ENDPOINT="${API_URL}health"
SWAGGER_ENDPOINT="${API_URL}swagger"

# Exponential backoff parameters
MAX_RETRIES=12           # Total wait time: ~3 minutes with exponential backoff
INITIAL_DELAY=5          # Start with 5 seconds
MAX_DELAY=60            # Cap at 60 seconds

retry_count=0
current_delay=$INITIAL_DELAY

log_info "Checking API availability with exponential backoff..."
log_info "Health endpoint: $HEALTH_ENDPOINT"

while [ $retry_count -lt $MAX_RETRIES ]; do
    retry_count=$((retry_count + 1))

    # Try health endpoint first, then swagger as fallback
    http_code=$(curl -sf -o /dev/null -w "%{http_code}" \
        --connect-timeout 10 \
        --max-time 30 \
        "$HEALTH_ENDPOINT" 2>/dev/null) || http_code="000"

    if [ "$http_code" = "200" ]; then
        log_info "API health check passed! (HTTP $http_code)"
        echo "=========================================="
        log_info "API is available and healthy"
        echo "=========================================="
        exit 0
    fi

    # Try swagger endpoint as fallback
    http_code_swagger=$(curl -sf -o /dev/null -w "%{http_code}" \
        --connect-timeout 10 \
        --max-time 30 \
        "$SWAGGER_ENDPOINT" 2>/dev/null) || http_code_swagger="000"

    if [ "$http_code_swagger" = "200" ]; then
        log_info "Swagger endpoint responding. API is available. (HTTP $http_code_swagger)"
        echo "=========================================="
        log_info "API is available"
        echo "=========================================="
        exit 0
    fi

    log_warn "Attempt $retry_count/$MAX_RETRIES: API not yet available (HTTP: health=$http_code, swagger=$http_code_swagger)"
    log_info "Waiting ${current_delay}s before retry..."

    sleep $current_delay

    # Exponential backoff with cap
    if [ $current_delay -lt $MAX_DELAY ]; then
        current_delay=$((current_delay * 2))
        if [ $current_delay -gt $MAX_DELAY ]; then
            current_delay=$MAX_DELAY
        fi
    fi
done

log_error "API did not become available after $MAX_RETRIES attempts"
log_error "Total wait time exceeded. Manual intervention may be required."
echo "=========================================="
log_warn "Proceeding with smoke test anyway - it may fail"
echo "=========================================="
exit 0  # Don't fail the workflow, let the smoke test handle it
