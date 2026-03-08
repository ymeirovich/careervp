#!/usr/bin/env bash
# Preflight checks for Phase 2 live CV tailoring test against deployed API.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
cd "${ROOT_DIR}"

if [[ -f ".env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source ".env"
  set +a
fi

: "${AWS_DEFAULT_REGION:=us-east-1}"
PAYLOAD_PATH="${PAYLOAD_PATH:-docs/refactor/payloads/phase3_cv_tailoring_test.json}"
API_BASE="${API_BASE:-}"
TOKEN="${TOKEN:-}"
TEST_USER_ID="${TEST_USER_ID:-}"
TABLE_NAME="${TABLE_NAME:-}"
CV_TAILOR_FUNCTION_NAME="${CV_TAILOR_FUNCTION_NAME:-careervp-cvtailor-lambda-dev}"
API_NAME_HINT="${API_NAME_HINT:-careervp-core-api-dev}"

fail() {
  echo "ERROR: $*" >&2
  exit 1
}

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || fail "Missing required command: $1"
}

require_cmd curl
require_cmd jq
require_cmd aws

if [[ ! -f "${PAYLOAD_PATH}" ]]; then
  fail "Payload file not found: ${PAYLOAD_PATH}"
fi

if [[ -z "${API_BASE}" ]]; then
  if [[ "${API_NAME_HINT}" == *"stage"* || "${API_NAME_HINT}" == *"staging"* ]]; then
    API_BASE="https://stage-api.careervp.com"
  else
    API_BASE="https://dev-api.careervp.com"
  fi
fi

if [[ -z "${API_BASE}" ]]; then
  api_id="$(
    aws apigateway get-rest-apis --region "${AWS_DEFAULT_REGION}" --limit 500 \
      | jq -r --arg api_name "${API_NAME_HINT}" '.items[] | select(.name == $api_name) | .id' \
      | head -n1
  )"
  if [[ -n "${api_id}" ]]; then
    API_BASE="https://${api_id}.execute-api.${AWS_DEFAULT_REGION}.amazonaws.com/prod"
  fi
fi

if [[ -z "${API_BASE}" ]]; then
  fail "API_BASE is missing and could not be auto-discovered."
fi

if [[ -z "${TEST_USER_ID}" ]]; then
  TEST_USER_ID="$(jq -r '.user_id // empty' "${PAYLOAD_PATH}")"
fi
if [[ -z "${TEST_USER_ID}" ]]; then
  fail "TEST_USER_ID is missing and payload has no user_id."
fi

if [[ -z "${TABLE_NAME}" ]]; then
  TABLE_NAME="$(
    aws lambda get-function-configuration \
      --function-name "${CV_TAILOR_FUNCTION_NAME}" \
      --region "${AWS_DEFAULT_REGION}" \
      | jq -r '.Environment.Variables.TABLE_NAME // empty'
  )"
fi
if [[ -z "${TABLE_NAME}" ]]; then
  fail "TABLE_NAME is missing and could not be discovered from Lambda env."
fi

echo "Preflight configuration:"
echo "  API_BASE=${API_BASE}"
echo "  PAYLOAD_PATH=${PAYLOAD_PATH}"
echo "  TEST_USER_ID=${TEST_USER_ID}"
echo "  TABLE_NAME=${TABLE_NAME}"
if [[ -n "${TOKEN}" && "${TOKEN}" != "your-jwt-token" ]]; then
  echo "  TOKEN=SET (len=${#TOKEN})"
else
  echo "  TOKEN=NOT_SET_OR_PLACEHOLDER"
fi

jq -e '
  (.cv_id | type == "string") and
  (.cv_id | length > 0) and
  (.job_description | type == "string") and
  (.job_description | length >= 50)
' "${PAYLOAD_PATH}" >/dev/null
echo "PASS: payload contract looks valid"

swagger_status="$(curl -s -o /tmp/preflight_phase2_swagger.out -w "%{http_code}" -m 20 "${API_BASE}/swagger" || true)"
if [[ "${swagger_status}" == "000" ]]; then
  fail "API_BASE is unreachable: ${API_BASE}"
fi
echo "PASS: API reachable (GET /swagger -> HTTP ${swagger_status})"

item_exists="$(
  aws dynamodb get-item \
    --table-name "${TABLE_NAME}" \
    --region "${AWS_DEFAULT_REGION}" \
    --key "{\"pk\":{\"S\":\"${TEST_USER_ID}\"},\"sk\":{\"S\":\"CV\"}}" \
    | jq -r 'if .Item == null then "no" else "yes" end'
)"
if [[ "${item_exists}" != "yes" ]]; then
  fail "No CV item found for TEST_USER_ID=${TEST_USER_ID} in ${TABLE_NAME} (pk/sk lookup)."
fi
echo "PASS: CV exists for user in DynamoDB"

probe_payload='{"cv_id":"cv-probe","job_description":"too short"}'
declare -a auth_args
auth_args=()
if [[ -n "${TOKEN}" && "${TOKEN}" != "your-jwt-token" ]]; then
  auth_args=(-H "Authorization: Bearer ${TOKEN}")
fi

if [[ ${#auth_args[@]} -gt 0 ]]; then
  probe_status="$(
    curl -s -o /tmp/preflight_phase2_probe.out -w "%{http_code}" -m 30 -X POST "${API_BASE}/api/cv-tailoring" \
      -H "Content-Type: application/json" \
      -H "X-User-Id: ${TEST_USER_ID}" \
      "${auth_args[@]}" \
      -d "${probe_payload}" || true
  )"
else
  probe_status="$(
    curl -s -o /tmp/preflight_phase2_probe.out -w "%{http_code}" -m 30 -X POST "${API_BASE}/api/cv-tailoring" \
      -H "Content-Type: application/json" \
      -H "X-User-Id: ${TEST_USER_ID}" \
      -d "${probe_payload}" || true
  )"
fi

if [[ "${probe_status}" == "401" ]]; then
  fail "Auth probe failed with 401. Provide valid TOKEN or enable AUTHORIZER_DISABLED fallback."
fi
if [[ "${probe_status}" == "403" || "${probe_status}" == "404" ]]; then
  fail "Route/auth mismatch on ${API_BASE}/api/cv-tailoring (HTTP ${probe_status})."
fi
if [[ "${probe_status}" == "000" ]]; then
  fail "Auth probe request failed to execute."
fi
echo "PASS: auth/route probe returned HTTP ${probe_status}"

echo
echo "Preflight complete. Suggested exports:"
echo "  export API_BASE=\"${API_BASE}\""
echo "  export TEST_USER_ID=\"${TEST_USER_ID}\""
echo "  export TABLE_NAME=\"${TABLE_NAME}\""
