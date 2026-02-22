#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
REF3_DIR="$ROOT_DIR/docs/refactor3"

pass_count=0
fail_count=0

check_dir() {
  local d="$1"
  if [[ -d "$d" ]]; then
    printf 'PASS dir  %s\n' "${d#$ROOT_DIR/}"
    pass_count=$((pass_count + 1))
  else
    printf 'FAIL dir  %s\n' "${d#$ROOT_DIR/}"
    fail_count=$((fail_count + 1))
  fi
}

check_file() {
  local f="$1"
  if [[ -f "$f" ]]; then
    printf 'PASS file %s\n' "${f#$ROOT_DIR/}"
    pass_count=$((pass_count + 1))
  else
    printf 'FAIL file %s\n' "${f#$ROOT_DIR/}"
    fail_count=$((fail_count + 1))
  fi
}

check_dir "$REF3_DIR/specs"
check_dir "$REF3_DIR/payloads"
check_dir "$REF3_DIR/tests"
check_dir "$REF3_DIR/validations"
check_dir "$REF3_DIR/scripts"

for file in \
  "$REF3_DIR/specs/api_contract_spec.yaml" \
  "$REF3_DIR/specs/auth_and_authorizer_spec.yaml" \
  "$REF3_DIR/specs/route_mapping_spec.yaml" \
  "$REF3_DIR/specs/async_flow_spec.yaml" \
  "$REF3_DIR/specs/dal_alignment_spec.yaml" \
  "$REF3_DIR/specs/validation_spec.yaml" \
  "$REF3_DIR/specs/release_gate_spec.yaml" \
  "$REF3_DIR/tests/unit_tests.md" \
  "$REF3_DIR/tests/integration_tests.md" \
  "$REF3_DIR/tests/e2e_tests.md" \
  "$REF3_DIR/tests/contract_gate_tests.md" \
  "$REF3_DIR/validations/phase_exit_gates.md" \
  "$REF3_DIR/validations/endpoint_2xx_scorecard.md" \
  "$REF3_DIR/validations/deployment_validation.md"
do
  check_file "$file"
done

payload_count=$(find "$REF3_DIR/payloads" -maxdepth 1 -type f -name '*.json' | wc -l | tr -d ' ')
if [[ "$payload_count" == "27" ]]; then
  printf 'PASS payload_count %s\n' "$payload_count"
  pass_count=$((pass_count + 1))
else
  printf 'FAIL payload_count expected=27 actual=%s\n' "$payload_count"
  fail_count=$((fail_count + 1))
fi

printf 'SUMMARY pass=%d fail=%d\n' "$pass_count" "$fail_count"

if [[ "$fail_count" -ne 0 ]]; then
  exit 1
fi
