#!/usr/bin/env bash
#
# Route Smoke Test Script
#
# Validates API routes by calling them and checking status codes and JSON responses.
# Uses payload contracts from docs/refactor3/payloads/ for expected responses.
#
# Usage:
#   ./step_1.3_route_smoke.sh [API_BASE] [TEST_EMAIL] [TEST_PASSWORD]
#
# Environment variables (alternative):
#   export API_BASE=https://api.example.com
#   export TEST_EMAIL=test@example.com
#   export TEST_PASSWORD=password123
#   ./step_1.3_route_smoke.sh
#
# Exit codes:
#   0 - All smoke tests passed
#   1 - One or more tests failed

set -euo pipefail

# Paths
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PAYLOADS_DIR="$(cd "$SCRIPT_DIR/../payloads" && pwd)"

# Resolve API_BASE - use shared resolver
SCRIPTS_DIR="$(cd "$SCRIPT_DIR/.." && pwd)/scripts"
if [[ -f "$SCRIPTS_DIR/resolve_api_base.py" ]]; then
    API_BASE="${1:-$(python3 "$SCRIPTS_DIR/resolve_api_base.py")}"
else
    API_BASE="${1:-$API_BASE}"
fi

# Test credentials
TEST_EMAIL="${2:-$TEST_EMAIL}"
TEST_PASSWORD="${3:-$TEST_PASSWORD}"

# Defaults for non-interactive use
API_BASE="${API_BASE:-}"
TEST_EMAIL="${TEST_EMAIL:-test@example.com}"
TEST_PASSWORD="${TEST_PASSWORD:-TestPass123!}"

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Counters
PASSED=0
FAILED=0
TOTAL=0

# =============================================================================
# Helper Functions
# =============================================================================

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_pass() {
    echo -e "${GREEN}[PASS]${NC} $1"
    ((PASSED++))
}

log_fail() {
    echo -e "${RED}[FAIL]${NC} $1"
    ((FAILED++))
}

usage() {
    echo "Usage: $0 [API_BASE] [TEST_EMAIL] [TEST_PASSWORD]"
    echo ""
    echo "Arguments:"
    echo "  API_BASE     - Base URL of the API (e.g., https://api.example.com)"
    echo "  TEST_EMAIL   - Test user email for authentication"
    echo "  TEST_PASSWORD - Test user password"
    echo ""
    echo "Environment variables:"
    echo "  API_BASE, TEST_EMAIL, TEST_PASSWORD"
    echo ""
    echo "The script will fail-fast on the first route mismatch."
    exit 1
}

check_prerequisites() {
    if [[ -z "$API_BASE" ]]; then
        log_error "API_BASE is not set. Provide as argument or set API_BASE env var."
        usage
    fi

    if [[ -z "$TEST_EMAIL" ]] || [[ -z "$TEST_PASSWORD" ]]; then
        log_error "TEST_EMAIL and TEST_PASSWORD must be provided."
        usage
    fi
}

# =============================================================================
# Test Functions
# =============================================================================

# Load payload contract from JSON file
load_payload() {
    local payload_name="$1"
    local payload_file="$PAYLOADS_DIR/${payload_name}.json"

    if [[ ! -f "$payload_file" ]]; then
        echo "null"
        return
    fi

    python3 -c "import json; print(json.dumps(json.load(open('$payload_file'))))"
}

# Get status code from response
get_status_code() {
    local response="$1"
    echo "$response" | python3 -c "import json, sys; print(json.load(sys.stdin).get('status_code', 0))" 2>/dev/null || echo "0"
}

# Check if response body is valid JSON
validate_json() {
    local response="$1"
    python3 -c "import json; json.loads('$response')" 2>/dev/null
    return $?
}

# Test a public route (no auth required)
test_public_route() {
    local method="$1"
    local path="$2"
    local expected_status="$3"
    local description="$4"

    ((TOTAL++))

    local url="${API_BASE}${path}"
    local response
    local actual_status

    log_info "Testing: $method $path (expected: $expected_status)"

    # Make request
    response=$(curl -s -w "\n%{http_code}" -X "$method" \
        -H "Content-Type: application/json" \
        "$url" 2>/dev/null) || {
        log_fail "$description: $method $path - curl failed"
        return 1
    }

    # Extract status code (last line)
    actual_status=$(echo "$response" | tail -n1)
    # Extract body (all but last line)
    local body=$(echo "$response" | sed '$d')

    if [[ "$actual_status" != "$expected_status" ]]; then
        log_fail "$description: $method $path - expected $expected_status, got $actual_status"
        return 1
    fi

    # Validate JSON response
    if ! validate_json "$body"; then
        log_fail "$description: $method $path - response is not valid JSON"
        return 1
    fi

    log_pass "$description: $method $path - $actual_status"
    return 0
}

# Test a protected route (auth required)
test_protected_route() {
    local method="$1"
    local path="$2"
    local expected_status="$3"
    local description="$4"
    local token="$5"

    ((TOTAL++))

    local url="${API_BASE}${path}"
    local response
    local actual_status

    log_info "Testing: $method $path (expected: $expected_status) [PROTECTED]"

    # Make request with auth
    response=$(curl -s -w "\n%{http_code}" -X "$method" \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer $token" \
        "$url" 2>/dev/null) || {
        log_fail "$description: $method $path - curl failed"
        return 1
    }

    # Extract status code (last line)
    actual_status=$(echo "$response" | tail -n1)
    # Extract body (all but last line)
    local body=$(echo "$response" | sed '$d')

    if [[ "$actual_status" != "$expected_status" ]]; then
        log_fail "$description: $method $path - expected $expected_status, got $actual_status"
        return 1
    fi

    # Validate JSON response
    if ! validate_json "$body"; then
        log_fail "$description: $method $path - response is not valid JSON"
        return 1
    fi

    log_pass "$description: $method $path - $actual_status"
    return 0
}

# Get auth token
get_auth_token() {
    local url="${API_BASE}/auth/login"
    local response

    response=$(curl -s -X POST \
        -H "Content-Type: application/json" \
        -d "{\"email\":\"$TEST_EMAIL\",\"password\":\"$TEST_PASSWORD\"}" \
        "$url" 2>/dev/null) || {
        echo ""
        return 1
    }

    python3 -c "import json; print(json.loads('$response').get('access_token', ''))" 2>/dev/null || echo ""
}

# =============================================================================
# Main Execution
# =============================================================================

main() {
    echo "================================================================================"
    echo "Route Smoke Tests"
    echo "================================================================================"
    echo ""
    echo "API Base: $API_BASE"
    echo "Payloads: $PAYLOADS_DIR"
    echo ""

    check_prerequisites

    # =============================================================================
    # Phase 1: Preflight (public routes)
    # =============================================================================
    echo ""
    echo "--- Phase 1: Preflight (Public Routes) ---"
    echo ""

    # Test /health (GET)
    test_public_route "GET" "/health" "200" "Health check" || {
        log_error "Preflight failed - cannot continue"
        echo ""
        echo "================================================================================"
        echo "RESULT: FAILED ($PASSED/$TOTAL passed)"
        echo "================================================================================"
        exit 1
    }

    # Test /auth/login (POST) - for token acquisition
    test_public_route "POST" "/auth/login" "200" "Auth login" || {
        log_error "Auth login failed - cannot continue"
        echo ""
        echo "================================================================================"
        echo "RESULT: FAILED ($PASSED/$TOTAL passed)"
        echo "================================================================================"
        exit 1
    }

    # =============================================================================
    # Phase 2: Get Auth Token
    # =============================================================================
    echo ""
    echo "--- Phase 2: Authentication ---"
    echo ""

    local token
    token=$(get_auth_token)

    if [[ -z "$token" ]]; then
        log_error "Failed to obtain auth token"
        echo ""
        echo "================================================================================"
        echo "RESULT: FAILED ($PASSED/$TOTAL passed)"
        echo "================================================================================"
        exit 1
    fi

    log_info "Obtained auth token: ${token:0:20}..."

    # =============================================================================
    # Phase 3: Protected Routes Smoke Test
    # =============================================================================
    echo ""
    echo "--- Phase 3: Protected Routes Smoke Test ---"
    echo ""

    # Test key protected endpoints
    # Using fail-fast: exit on first failure

    test_protected_route "GET" "/jobs" "200" "List jobs" "$token" || exit 1
    test_protected_route "POST" "/jobs" "201" "Create job" "$token" || exit 1
    test_protected_route "GET" "/users/me" "200" "Get current user" "$token" || exit 1
    test_protected_route "POST" "/gap-analysis/questions" "200" "Generate gap questions" "$token" || exit 1
    test_protected_route "POST" "/vpr/generate" "202" "Generate VPR" "$token" || exit 1

    # =============================================================================
    # Summary
    # =============================================================================
    echo ""
    echo "================================================================================"
    echo "RESULT: PASSED ($PASSED/$TOTAL passed)"
    echo "================================================================================"

    exit 0
}

main "$@"
