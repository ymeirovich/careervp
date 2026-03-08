#!/usr/bin/env bash
set -euo pipefail

DEV_HOST="${DEV_HOST:-dev-api.careervp.com}"
STAGE_HOST="${STAGE_HOST:-stage-api.careervp.com}"
DEV_API_BASE="${DEV_API_BASE:-https://${DEV_HOST}/prod}"
STAGE_API_BASE="${STAGE_API_BASE:-https://${STAGE_HOST}/prod}"

check_dns() {
  local host="$1"
  echo "===== DNS ${host}"
  dig +short "${host}" || true
}

check_health() {
  local name="$1"
  local url="$2/health"

  echo "===== HEALTH ${name} (${url})"
  local headers body code
  headers="$(mktemp)"
  body="$(mktemp)"
  code="$(curl -sS -o "${body}" -D "${headers}" -w "%{http_code}" "${url}" || true)"

  echo "HTTP ${code}"
  rg -n "^server:|^cf-ray:|^content-type:" -i "${headers}" || true
  echo "BODY:"
  head -c 300 "${body}" || true
  echo

  rm -f "${headers}" "${body}"
}

check_protected() {
  local name="$1"
  local base="$2"

  # Unauthenticated probe: expect auth failure (401/403) when route is reachable.
  local path="/users/me"
  local url="${base}${path}"

  echo "===== PROTECTED ${name} (${url})"
  local headers body code
  headers="$(mktemp)"
  body="$(mktemp)"
  code="$(curl -sS -o "${body}" -D "${headers}" -w "%{http_code}" "${url}" || true)"

  echo "HTTP ${code}"
  rg -n "^server:|^cf-ray:|^content-type:" -i "${headers}" || true
  echo "BODY:"
  head -c 300 "${body}" || true
  echo

  rm -f "${headers}" "${body}"
}

check_dns "${DEV_HOST}"
check_dns "${STAGE_HOST}"

check_health "dev" "${DEV_API_BASE}"
check_health "stage" "${STAGE_API_BASE}"

check_protected "dev" "${DEV_API_BASE}"
check_protected "stage" "${STAGE_API_BASE}"
