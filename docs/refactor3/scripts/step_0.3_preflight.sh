#!/bin/bash
#
# Preflight Health & Auth Validation Script
#
# Validates API readiness by checking:
#   1. GET /health returns 200 with expected JSON keys
#   2. POST /auth/login returns 200 with expected JSON keys
#
# Usage:
#   ./step_0.3_preflight.sh <API_BASE> <TEST_EMAIL> <TEST_PASSWORD>
#   API_BASE=https://api.example.com/v1 ./step_0.3_preflight.sh test@example.com password123
#
# Exit codes:
#   0 - All checks passed
#   1 - One or more checks failed

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PAYLOADS_DIR="$(dirname "$SCRIPT_DIR")/payloads"

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

fail() {
    log_error "$1"
    exit 1
}

# Load JSON payload and extract expected status code
load_expected_status() {
    local payload_file="$1"
    python3 -c "
import json
import sys
with open('$payload_file') as f:
    data = json.load(f)
    print(data.get('expected_response', {}).get('status_code', ''))
"
}

# Load JSON payload and extract expected body keys
load_expected_keys() {
    local payload_file="$1"
    python3 -c "
import json
import sys
with open('$payload_file') as f:
    data = json.load(f)
    body = data.get('expected_response', {}).get('body', {})
    # Get top-level keys (supports nested objects like 'services')
    keys = list(body.keys())
    print(','.join(keys))
"
}

# Validate response has required keys
validate_response_keys() {
    local response_json="$1"
    local expected_keys="$2"
    local endpoint="$3"

    # Get actual keys from response
    local actual_keys
    actual_keys=$(python3 -c "
import json
import sys
data = json.loads('$response_json')
keys = list(data.keys())
print(','.join(sorted(keys)))
" 2>/dev/null || echo "")

    # Check each expected key exists
    local missing_keys=""
    IFS=',' read -ra EXPECTED <<< "$expected_keys"
    for key in "${EXPECTED[@]}"; do
        if ! echo "$actual_keys" | grep -q "$key"; then
            if [[ -z "$missing_keys" ]]; then
                missing_keys="$key"
            else
                missing_keys="$missing_keys, $key"
            fi
        fi
    done

    if [[ -n "$missing_keys" ]]; then
        echo "Missing keys: $missing_keys"
        return 1
    fi

    return 0
}

# =============================================================================
# Main Preflight Checks
# =============================================================================

main() {
    local api_base="${1:-${API_BASE:-}}"
    local test_email="${2:-${TEST_EMAIL:-}}"
    local test_password="${3:-${TEST_PASSWORD:-}}"

    # Validate inputs
    if [[ -z "$api_base" ]]; then
        fail "API_BASE is required. Pass as argument or set API_BASE env var."
    fi

    if [[ -z "$test_email" ]] || [[ -z "$test_password" ]]; then
        fail "TEST_EMAIL and TEST_PASSWORD are required. Pass as arguments or set env vars."
    fi

    log_info "Starting preflight validation..."
    log_info "API_BASE: $api_base"
    echo ""

    local health_payload="$PAYLOADS_DIR/health_check.json"
    local login_payload="$PAYLOADS_DIR/auth_login.json"

    # Verify payload files exist
    if [[ ! -f "$health_payload" ]]; then
        fail "Health payload not found: $health_payload"
    fi
    if [[ ! -f "$login_payload" ]]; then
        fail "Login payload not found: $login_payload"
    fi

    # =============================================================================
    # Check 1: GET /health
    # =============================================================================
    log_info "Checking GET /health..."

    local expected_health_status
    expected_health_status=$(load_expected_status "$health_payload")
    local expected_health_keys
    expected_health_keys=$(load_expected_keys "$health_payload")

    local health_response
    local health_status

    health_response=$(curl -s -w "\n%{http_code}" "$api_base/health" 2>/dev/null || echo "")
    health_status=$(echo "$health_response" | tail -n1)
    health_response=$(echo "$health_response" | sed '$d')

    # Validate status code
    if [[ "$health_status" != "$expected_health_status" ]]; then
        fail "GET /health failed: expected status $expected_health_status, got $health_status"
    fi

    # Validate JSON keys
    local key_validation
    key_validation=$(validate_response_keys "$health_response" "$expected_health_keys" "/health" || true)

    if [[ -n "$key_validation" ]]; then
        fail "GET /health failed: $key_validation"
    fi

    log_info "  Status: $health_status (expected: $expected_health_status)"
    log_info "  Keys: $expected_health_keys"
    log_info "  Result: PASS"
    echo ""

    # =============================================================================
    # Check 2: POST /auth/login
    # =============================================================================
    log_info "Checking POST /auth/login..."

    local expected_login_status
    expected_login_status=$(load_expected_status "$login_payload")
    local expected_login_keys
    expected_login_keys=$(load_expected_keys "$login_payload")

    local login_response
    local login_status

    login_response=$(curl -s -w "\n%{http_code}" \
        -X POST "$api_base/auth/login" \
        -H "Content-Type: application/json" \
        -d "{\"email\":\"$test_email\",\"password\":\"$test_password\"}" 2>/dev/null || echo "")

    login_status=$(echo "$login_response" | tail -n1)
    login_response=$(echo "$login_response" | sed '$d')

    # Validate status code
    if [[ "$login_status" != "$expected_login_status" ]]; then
        fail "POST /auth/login failed: expected status $expected_login_status, got $login_status"
    fi

    # Validate JSON keys
    key_validation=$(validate_response_keys "$login_response" "$expected_login_keys" "/auth/login" || true)

    if [[ -n "$key_validation" ]]; then
        fail "POST /auth/login failed: $key_validation"
    fi

    log_info "  Status: $login_status (expected: $expected_login_status)"
    log_info "  Keys: $expected_login_keys"
    log_info "  Result: PASS"
    echo ""

    # =============================================================================
    # All Checks Passed
    # =============================================================================
    log_info "All preflight checks passed!"
    exit 0
}

# Run main with all arguments
main "$@"
