#!/usr/bin/env bash
# CareerVP AWS CLI smoke & CRUD tests for CV Parser, VPR Generator, and Company Research.
# Usage: bash src/backend/tests/aws_cli_smoke.sh [env]
# Requires: aws CLI, jq, python3, base64; .env with AWS + Anthropic creds.

set -euo pipefail
VERBOSE="${VERBOSE:-0}"

if [[ "$VERBOSE" == "1" ]]; then
  set -x
fi

ENVIRONMENT="${1:-dev}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")"/../../.. && pwd)"
export PYTHONPATH="${ROOT}/src/backend:${PYTHONPATH:-}"
export AWS_PAGER=""  # prevent aws cli from paging output

# Load .env without leaking secrets to stdout
if [[ -f "${ROOT}/.env" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "${ROOT}/.env"
  set +a
fi

AWS_REGION="${AWS_DEFAULT_REGION:-us-east-1}"
ACCOUNT_EXPECTED="${AWS_DEFAULT_ACCOUNT:-}"

CV_LAMBDA="${CV_PARSER_LAMBDA:-careervp-cv-parser-lambda-${ENVIRONMENT}}"
COMPANY_LAMBDA="${COMPANY_RESEARCH_LAMBDA:-careervp-company-research-lambda-${ENVIRONMENT}}"

USERS_TABLE="${USERS_TABLE_NAME:-careervp-users-table-${ENVIRONMENT}}"
IDEMPOTENCY_TABLE="${IDEMPOTENCY_TABLE_NAME:-careervp-idempotency-table-${ENVIRONMENT}}"

require_bin() {
  command -v "$1" >/dev/null 2>&1 || { echo "Missing required binary: $1" >&2; exit 1; }
}

require_bin aws
require_bin jq
require_bin python3
require_bin base64

log() { printf '>> %s\n' "$*"; }
debug() { if [[ "$VERBOSE" == "1" ]]; then printf '[debug] %s\n' "$*"; fi; }

decode_log_result() {
  local encoded="$1"
  python3 - <<'PY'
import base64, os, sys
data = os.environ.get("LOG_RESULT", "")
if not data:
    sys.exit(0)
try:
    print(base64.b64decode(data).decode("utf-8", errors="replace"))
except Exception as exc:
    print(f"[log decode failed] {exc}")
PY
}

get_lambda_env() {
  local fn="$1" key="$2"
  aws lambda get-function-configuration \
    --function-name "$fn" \
    --query "Environment.Variables.${key}" \
    --output text \
    --region "$AWS_REGION" 2>/dev/null
}

resolve_cv_bucket() {
  if [[ -n "${CV_BUCKET_NAME:-}" && "${CV_BUCKET_NAME}" != "None" ]]; then
    echo "$CV_BUCKET_NAME"
    return
  fi

  local from_lambda
  from_lambda="$(get_lambda_env "$CV_LAMBDA" "CV_BUCKET_NAME")"
  if [[ -n "$from_lambda" && "$from_lambda" != "None" ]]; then
    echo "$from_lambda"
    return
  fi

  aws s3api list-buckets --query "Buckets[?starts_with(Name, 'careervp-${ENVIRONMENT}-cvs')].Name | [0]" --output text
}

assert_status_ok() {
  local status="$1" context="$2" response_file="${3:-}" log_meta_file="${4:-}"
  if [[ ! "$status" =~ ^[0-9]+$ ]]; then
    echo "FAIL: ${context} returned non-numeric status: ${status}" >&2
    exit 1
  fi
  if [[ "$status" -ge 200 && "$status" -lt 300 ]]; then
    log "${context}: OK (${status})"
  else
    echo "FAIL: ${context} returned status ${status}" >&2
    # Print response body for debugging
    if [[ -n "$response_file" && -f "$response_file" ]]; then
      echo "=== Response Body ===" >&2
      cat "$response_file" >&2
    fi
    # Decode and print Lambda logs for debugging
    if [[ -n "$log_meta_file" && -f "$log_meta_file" ]]; then
      local log_result
      log_result="$(jq -r '.LogResult // empty' "$log_meta_file")"
      if [[ -n "$log_result" ]]; then
        echo "=== Lambda Logs ===" >&2
        decode_log_result "$log_result" >&2 || true
      fi
    fi
    exit 1
  fi
}

preflight() {
  log "Preflight: aws sts get-caller-identity"
  local ident
  ident="$(aws sts get-caller-identity --region "$AWS_REGION")"
  echo "$ident" | jq .
  if [[ -n "$ACCOUNT_EXPECTED" ]]; then
    local account_actual
    account_actual="$(echo "$ident" | jq -r '.Account')"
    [[ "$account_actual" == "$ACCOUNT_EXPECTED" ]] || { echo "Account mismatch: expected ${ACCOUNT_EXPECTED}, got ${account_actual}" >&2; exit 1; }
  fi
  debug "Caller identity: ${ident}"
}

check_resources() {
  log "Checking required resources exist"
  aws lambda get-function --function-name "$CV_LAMBDA" --region "$AWS_REGION" >/dev/null
  aws lambda get-function --function-name "$COMPANY_LAMBDA" --region "$AWS_REGION" >/dev/null
  aws dynamodb describe-table --table-name "$USERS_TABLE" --region "$AWS_REGION" >/dev/null
  aws dynamodb describe-table --table-name "$IDEMPOTENCY_TABLE" --region "$AWS_REGION" >/dev/null
  local bucket
  bucket="$(resolve_cv_bucket)"
  [[ -n "$bucket" && "$bucket" != "None" ]] || { echo "CV bucket not found" >&2; exit 1; }
  log "Resolved CV bucket: ${bucket}"
  debug "Resources: CV_LAMBDA=${CV_LAMBDA} COMPANY_LAMBDA=${COMPANY_LAMBDA} USERS_TABLE=${USERS_TABLE} IDEMPOTENCY_TABLE=${IDEMPOTENCY_TABLE}"
}

_update_lambda_env_var() {
  local fn="$1"
  local key="$2"
  local value="$3"
  local current env_file="/tmp/lambda_env_$$.json"

  current="$(aws lambda get-function-configuration \
    --function-name "$fn" \
    --query 'Environment.Variables' \
    --output json \
    --region "$AWS_REGION")"
  if [[ "$current" == "null" || -z "$current" ]]; then
    current="{}"
  fi

  # Use Python to safely construct JSON with the API key value
  python3 - "$current" "$key" "$value" "$env_file" <<'PY'
import sys, json
current = json.loads(sys.argv[1])
key = sys.argv[2]
value = sys.argv[3]
env_file = sys.argv[4]
current[key] = value
env_wrapper = {"Variables": current}
with open(env_file, 'w') as f:
    json.dump(env_wrapper, f)
PY

  # Avoid echoing secrets when VERBOSE=1
  local xtrace_state
  xtrace_state="$(set +o | grep xtrace || true)"
  set +x
  aws lambda update-function-configuration \
    --function-name "$fn" \
    --environment "file://${env_file}" \
    --region "$AWS_REGION" >/dev/null
  rm -f "$env_file"
  eval "$xtrace_state"
}

ensure_anthropic_env() {
  log "Checking ANTHROPIC_API_KEY on Lambdas"
  local local_key
  local_key="${ANTHROPIC_API_KEY:-}"
  if [[ -z "$local_key" ]]; then
    echo "FAIL: ANTHROPIC_API_KEY not set locally (check .env)." >&2
    exit 1
  fi
  debug "Local ANTHROPIC_API_KEY length: ${#local_key}"

  local lambdas=("$CV_LAMBDA" "$COMPANY_LAMBDA")
  local missing=()
  for fn in "${lambdas[@]}"; do
    local key
    key="$(get_lambda_env "$fn" "ANTHROPIC_API_KEY")"
    debug "Lambda $fn ANTHROPIC_API_KEY: ${key:+SET (${#key} chars)}${key:-NOT SET}"
    if [[ -z "$key" || "$key" == "None" ]]; then
      missing+=("$fn")
    fi
  done

  if [[ "${#missing[@]}" -eq 0 ]]; then
    log "All Lambdas have ANTHROPIC_API_KEY set"
  elif [[ "${AUTO_SET_LAMBDA_ENV:-0}" == "1" ]]; then
    log "Setting ANTHROPIC_API_KEY on: ${missing[*]}"
    for fn in "${missing[@]}"; do
      _update_lambda_env_var "$fn" "ANTHROPIC_API_KEY" "$local_key"
    done
    log "ANTHROPIC_API_KEY updated. Waiting 45s for AWS to apply changes..."
    sleep 45
  else
    echo "FAIL: Missing ANTHROPIC_API_KEY on: ${missing[*]}" >&2
    echo "Set it or re-run with AUTO_SET_LAMBDA_ENV=1 to apply automatically." >&2
    exit 1
  fi
}

run_verify_script() {
  log "Running verify_aws_state.py --mode deployed --env ${ENVIRONMENT}"
  python3 "${ROOT}/src/backend/scripts/verify_aws_state.py" --mode deployed --env "$ENVIRONMENT"
}

test_s3_crud() {
  local bucket key
  bucket="$(resolve_cv_bucket)"
  key="cli-smoke/probe-$(date +%s).txt"
  log "S3 put/head/delete s3://${bucket}/${key} (boto3)"
  python3 - <<PY
import os
from botocore.config import Config
import boto3

bucket = "${bucket}"
key = "${key}"
region = os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION") or "us-east-1"

config = Config(connect_timeout=5, read_timeout=10, retries={"max_attempts": 3})
s3 = boto3.client("s3", region_name=region, config=config)
body = f"CLI smoke S3 check at {os.popen('date -Iseconds').read().strip()}\\n"

s3.put_object(Bucket=bucket, Key=key, Body=body.encode("utf-8"))
s3.head_object(Bucket=bucket, Key=key)
s3.delete_object(Bucket=bucket, Key=key)
print("S3 CRUD OK")
PY
  debug "S3 CRUD finished for ${bucket}/${key}"
}

test_cv_parser_lambda() {
  log "Testing CV Parser Lambda"
  local user_id="cli-smoke-user"
  local cv_text="Seasoned product engineer with 10+ years leading cross-functional teams, shipping cloud products, improving reliability, and mentoring engineers across distributed environments."
  local file_b64
  file_b64="$(printf '%s' "$cv_text" | base64)"
  local body_json
  body_json="$(jq -n --arg uid "$user_id" --arg b64 "$file_b64" '{user_id:$uid, file_content:$b64, file_type:"txt"}')"
  # Build proper API Gateway event with required fields for Powertools
  local event
  event="$(jq -cn --arg body "$body_json" '{
    body: $body,
    path: "/api/cv",
    httpMethod: "POST",
    headers: {"Content-Type": "application/json"},
    requestContext: {
      requestId: "smoke-test-request",
      stage: "prod"
    },
    isBase64Encoded: false
  }')"
  log "Event prepared"
  local outfile="/tmp/cv_parser_response.json"
  log "Invoking ${CV_LAMBDA}"
  aws lambda invoke \
    --function-name "$CV_LAMBDA" \
    --payload "$event" \
    --cli-binary-format raw-in-base64-out \
    "$outfile" \
    --region "$AWS_REGION" \
    --log-type Tail \
    --query '{FunctionError:FunctionError,LogResult:LogResult}' \
    --output json > /tmp/cv_parser_invoke_meta.json
  log "Testing 4"
  local status body success source_key
  status="$(jq -r '.statusCode // empty' "$outfile")"
  if [[ -z "$status" ]]; then
    echo "FAIL: CV parser response missing statusCode" >&2
    cat "$outfile" >&2
    LOG_RESULT="$(jq -r '.LogResult // empty' /tmp/cv_parser_invoke_meta.json)"
    export LOG_RESULT
    decode_log_result "$LOG_RESULT" >&2 || true
    exit 1
  fi
  body="$(jq -r '.body' "$outfile")"
  success="$(printf '%s' "$body" | jq -r '.success')"
  assert_status_ok "$status" "CV parser status" "$outfile" "/tmp/cv_parser_invoke_meta.json"
  [[ "$success" == "true" ]] || { echo "CV parser returned success=false" >&2; cat "$outfile"; exit 1; }
  source_key="$(printf '%s' "$body" | jq -r '.user_cv.source_file_key // empty')"
  if [[ -n "$source_key" ]]; then
    log "Testing if"
    local bucket
    bucket="$(resolve_cv_bucket)"
    log "Verifying S3 object ${bucket}/${source_key}"
    aws s3api head-object --bucket "$bucket" --key "$source_key" --region "$AWS_REGION" >/dev/null
  fi

  log "Checking DynamoDB CV item for ${user_id}"
  aws dynamodb get-item \
    --table-name "$USERS_TABLE" \
    --key "{\"pk\":{\"S\":\"${user_id}\"},\"sk\":{\"S\":\"CV\"}}" \
    --query 'Item.pk.S' \
    --output text \
    --region "$AWS_REGION" >/dev/null
  debug "CV parser response body: ${body}"
  log "CV Parser Lambda test completed"
}

test_vpr_generator_lambda() {
  log "Testing VPR Generator Lambda (Anthropic API handshake)"
  local user_id="cli-smoke-user"
  local app_id="cli-smoke-app"
  local job_post
  job_post="$(cat <<'JSON'
{
  "company_name": "Natural Intelligence",
  "role_title": "Learning & Development Manager",
  "language": "en",
  "responsibilities": [
    "Lead organizational development strategy aligned with company goals",
    "Design leadership development programs across all levels",
    "Analyze survey data to drive decision-making"
  ],
  "requirements": [
    "5+ years in L&D or organizational development",
    "Experience implementing AI tools in learning programs",
    "Strong project management skills"
  ],
  "nice_to_have": [
    "HRBP experience",
    "Hebrew and English communication"
  ]
}
JSON
)"
  local vpr_body
  vpr_body="$(jq -c --arg app "$app_id" --arg uid "$user_id" --argjson jp "$job_post" '{application_id:$app, user_id:$uid, job_posting:$jp, gap_responses:[]}' )"
  local event
  event="$(jq -cn --arg body "$vpr_body" '{body:$body, path:"/api/vpr", httpMethod:"POST"}')"
  local outfile="/tmp/vpr_response.json"

  log "Invoking ${VPR_LAMBDA}"
  aws lambda invoke \
    --function-name "$VPR_LAMBDA" \
    --payload "$event" \
    --cli-binary-format raw-in-base64-out \
    "$outfile" \
    --region "$AWS_REGION" \
    --log-type Tail \
    --query '{FunctionError:FunctionError,LogResult:LogResult}' \
    --output json > /tmp/vpr_invoke_meta.json

  local status body success vpr_text
  status="$(jq -r '.statusCode // empty' "$outfile")"
  if [[ -z "$status" ]]; then
    echo "FAIL: VPR response missing statusCode" >&2
    cat "$outfile" >&2
    LOG_RESULT="$(jq -r '.LogResult // empty' /tmp/vpr_invoke_meta.json)"
    export LOG_RESULT
    decode_log_result "$LOG_RESULT" >&2 || true
    exit 1
  fi
  body="$(jq -r '.body' "$outfile")"
  success="$(printf '%s' "$body" | jq -r '.success')"
  assert_status_ok "$status" "VPR generator status" "$outfile" "/tmp/vpr_invoke_meta.json"

  # Verify Anthropic API returned actual content (not just a successful HTTP response)
  vpr_text="$(printf '%s' "$body" | jq -r '.data.vpr // empty')"
  if [[ -z "$vpr_text" || "$vpr_text" == "null" ]]; then
    echo "FAIL: VPR response missing Anthropic completion (empty vpr field)" >&2
    printf '%s\n' "$body" | jq . >&2
    LOG_RESULT="$(jq -r '.LogResult // empty' /tmp/vpr_invoke_meta.json)"
    export LOG_RESULT
    decode_log_result "$LOG_RESULT" >&2 || true
    exit 1
  fi

  log "Anthropic API handshake verified - received $(echo "$vpr_text" | wc -c) chars of VPR content"

  [[ "$success" == "true" ]] || { echo "VPR generator returned success=false"; cat "$outfile"; exit 1; }

  log "Checking DynamoDB VPR artifact"
  aws dynamodb get-item \
    --table-name "$USERS_TABLE" \
    --key "{\"pk\":{\"S\":\"${app_id}\"},\"sk\":{\"S\":\"ARTIFACT#VPR#v1\"}}" \
    --query 'Item.pk.S' \
    --output text \
    --region "$AWS_REGION" >/dev/null
  debug "VPR generator response body: ${body}"
}

test_company_research_lambda() {
  local body_json
  body_json="$(jq -n '{
    company_name:"Acme Corp",
    domain:"acme.com",
    job_posting_text:"We are hiring to scale values-driven products.",
    max_sources:2
  }')"
  # Build proper API Gateway event with required fields for Powertools
  local event
  event="$(jq -cn --arg body "$body_json" '{
    body: $body,
    path: "/api/company-research",
    httpMethod: "POST",
    headers: {"Content-Type": "application/json"},
    requestContext: {
      requestId: "smoke-test-company-research",
      stage: "prod"
    },
    isBase64Encoded: false
  }')"
  local outfile="/tmp/company_research_response.json"

  log "Invoking ${COMPANY_LAMBDA}"
  aws lambda invoke \
    --function-name "$COMPANY_LAMBDA" \
    --payload "$event" \
    --cli-binary-format raw-in-base64-out \
    "$outfile" \
    --region "$AWS_REGION" \
    --log-type Tail \
    --query '{FunctionError:FunctionError,LogResult:LogResult}' \
    --output json > /tmp/company_research_invoke_meta.json

  local status body code
  status="$(jq -r '.statusCode // empty' "$outfile")"
  if [[ -z "$status" ]]; then
    echo "FAIL: Company research response missing statusCode" >&2
    cat "$outfile" >&2
    LOG_RESULT="$(jq -r '.LogResult // empty' /tmp/company_research_invoke_meta.json)"
    export LOG_RESULT
    decode_log_result "$LOG_RESULT" >&2 || true
    exit 1
  fi
  body="$(jq -r '.body' "$outfile")"
  code="$(printf '%s' "$body" | jq -r '.code // empty')"
  # Accept 200 (complete) or 206/207 style partial content
  if [[ "$status" -ge 200 && "$status" -lt 300 ]]; then
    log "Company research status OK (${status}) code=${code}"
  else
    echo "Company research failed with status ${status}" >&2
    cat "$outfile"
    exit 1
  fi
  debug "Company research response body: ${body}"
}

test_anthropic_via_api_gateway() {
  log "Testing Anthropic API handshake via API Gateway"
  local api_url
  api_url="$(aws cloudformation describe-stacks \
    --stack-name CareerVpCrudDev \
    --query "Stacks[0].Outputs[?OutputKey=='Apigateway'].OutputValue" \
    --output text \
    --region "$AWS_REGION" 2>/dev/null)" || api_url=""

  if [[ -z "$api_url" || "$api_url" == "None" ]]; then
    echo "FAIL: Could not fetch API Gateway URL from CareerVpCrudDev stack" >&2
    echo "Ensure stack is deployed and has Apigateway output" >&2
    exit 1
  fi

  local endpoint="${api_url}api/vpr"
  log "API Gateway URL: ${endpoint}"

  local job_post
  job_post="$(cat <<'JSON' | tr -d '\n'
{"company_name":"TestCorp","role_title":"Senior Engineer","language":"en","responsibilities":["Build and maintain web applications"],"requirements":["5+ years experience"],"nice_to_have":[]}
JSON
)"

  local payload
  payload="$(jq -c --arg app "api-smoke-app" --arg uid "api-smoke-user" --argjson jp "$job_post" '{application_id:$app, user_id:$uid, job_posting:$jp, gap_responses:[]}')"

  local response_file="/tmp/vpr_api_response.json"
  local http_code

  log "Calling VPR endpoint via API Gateway..."
  http_code="$(curl -s -o "$response_file" -w "%{http_code}" -X POST "$endpoint" \
    -H "Content-Type: application/json" \
    -H "Accept: application/json" \
    -d "$payload" \
    --region "$AWS_REGION")"

  if [[ ! "$http_code" =~ ^[0-9]+$ ]]; then
    echo "FAIL: Invalid HTTP response code: $http_code" >&2
    exit 1
  fi

  if [[ "$http_code" -lt 200 || "$http_code" -ge 300 ]]; then
    echo "FAIL: VPR endpoint returned HTTP $http_code" >&2
    cat "$response_file" >&2
    exit 1
  fi

  # Verify Anthropic returned actual content
  local body success vpr_content
  body="$(cat "$response_file")"
  success="$(printf '%s' "$body" | jq -r '.success' 2>/dev/null)"
  vpr_content="$(printf '%s' "$body" | jq -r '.data.vpr // empty' 2>/dev/null)"

  if [[ "$success" != "true" ]]; then
    echo "FAIL: VPR endpoint returned success=false" >&2
    printf '%s\n' "$body" | jq . >&2
    exit 1
  fi

  if [[ -z "$vpr_content" || "$vpr_content" == "null" ]]; then
    echo "FAIL: VPR response missing Anthropic completion (empty vpr field)" >&2
    printf '%s\n' "$body" | jq . >&2
    exit 1
  fi

  log "Anthropic handshake via API Gateway verified! HTTP $http_code, VPR content: $(echo -n "$vpr_content" | wc -c) chars"
}

test_anthropic_ping() {
  log "Anthropic key probe (short, low-cost)"
  python3 - <<'PY'
import os, json
from careervp.logic.utils.llm_client import LLMRouter, TaskMode

api_key = os.environ.get("ANTHROPIC_API_KEY")
if not api_key:
    raise SystemExit("ANTHROPIC_API_KEY not set")

router = LLMRouter(api_key=api_key)
resp = router.invoke(
    mode=TaskMode.TEMPLATE,
    system_prompt="You are a health check.",
    user_prompt="Reply with a one-word status: READY.",
    max_tokens=16,
    temperature=0.0,
)
print(json.dumps(resp.model_dump(), indent=2))
if not resp.success:
    raise SystemExit("Anthropic probe failed")
PY
}

main() {
  log "Starting AWS CLI smoke (env=${ENVIRONMENT}, region=${AWS_REGION}, verbose=${VERBOSE})"
  preflight
  check_resources
  ensure_anthropic_env
  run_verify_script
  test_s3_crud
  test_cv_parser_lambda
  test_company_research_lambda
  # VPR uses async architecture (submit/status/worker) - no standalone Lambda
  # test_anthropic_via_api_gateway  # Requires VPR endpoint
  test_anthropic_ping
  log "All smoke tests completed"
}

main "$@"
