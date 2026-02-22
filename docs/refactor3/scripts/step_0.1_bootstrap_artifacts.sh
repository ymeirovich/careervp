#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
REF2_DIR="$ROOT_DIR/docs/refactor2"
REF3_DIR="$ROOT_DIR/docs/refactor3"

log() { printf '[step_0.1_bootstrap] %s\n' "$*"; }
err() { printf '[step_0.1_bootstrap][ERROR] %s\n' "$*" >&2; }

ensure_dir() {
  local d="$1"
  if [[ ! -d "$d" ]]; then
    mkdir -p "$d"
    log "created directory: ${d#$ROOT_DIR/}"
  else
    log "directory exists: ${d#$ROOT_DIR/}"
  fi
}

copy_if_missing() {
  local src="$1"
  local dst="$2"
  if [[ ! -f "$src" ]]; then
    err "source missing: ${src#$ROOT_DIR/}"
    return 1
  fi
  if [[ -f "$dst" ]]; then
    log "file exists (unchanged): ${dst#$ROOT_DIR/}"
  else
    cp "$src" "$dst"
    log "created file: ${dst#$ROOT_DIR/}"
  fi
}

ensure_file_if_missing() {
  local file="$1"
  local content="$2"
  if [[ ! -f "$file" ]]; then
    printf '%s\n' "$content" > "$file"
    log "created file: ${file#$ROOT_DIR/}"
  else
    log "file exists (unchanged): ${file#$ROOT_DIR/}"
  fi
}

ensure_dir "$REF3_DIR/specs"
ensure_dir "$REF3_DIR/payloads"
ensure_dir "$REF3_DIR/tests"
ensure_dir "$REF3_DIR/validations"
ensure_dir "$REF3_DIR/scripts"

# Map refactor2 specs -> required refactor3 specs
copy_if_missing "$REF2_DIR/specs/api_contract_spec.yaml" "$REF3_DIR/specs/api_contract_spec.yaml"
copy_if_missing "$REF2_DIR/specs/auth_spec.yaml" "$REF3_DIR/specs/auth_and_authorizer_spec.yaml"
copy_if_missing "$REF2_DIR/specs/api_contract_spec.yaml" "$REF3_DIR/specs/route_mapping_spec.yaml"
copy_if_missing "$REF2_DIR/specs/async_processing_spec.yaml" "$REF3_DIR/specs/async_flow_spec.yaml"
copy_if_missing "$REF2_DIR/specs/dal_migration_spec.yaml" "$REF3_DIR/specs/dal_alignment_spec.yaml"
copy_if_missing "$REF2_DIR/specs/api_contract_spec.yaml" "$REF3_DIR/specs/validation_spec.yaml"
copy_if_missing "$REF2_DIR/specs/api_contract_spec.yaml" "$REF3_DIR/specs/release_gate_spec.yaml"

# Copy all payloads from refactor2 to refactor3 if missing
while IFS= read -r -d '' src; do
  name="$(basename "$src")"
  copy_if_missing "$src" "$REF3_DIR/payloads/$name"
done < <(find "$REF2_DIR/payloads" -maxdepth 1 -type f -name '*.json' -print0 | sort -z)

# Ensure required test and validation docs exist (create only if missing)
ensure_file_if_missing "$REF3_DIR/tests/unit_tests.md" "# REFACTOR3 Unit Tests"
ensure_file_if_missing "$REF3_DIR/tests/integration_tests.md" "# REFACTOR3 Integration Tests"
ensure_file_if_missing "$REF3_DIR/tests/e2e_tests.md" "# REFACTOR3 E2E Tests"
ensure_file_if_missing "$REF3_DIR/tests/contract_gate_tests.md" "# REFACTOR3 Contract Gate Tests"
ensure_file_if_missing "$REF3_DIR/validations/phase_exit_gates.md" "# REFACTOR3 Phase Exit Gates"
ensure_file_if_missing "$REF3_DIR/validations/endpoint_2xx_scorecard.md" "# REFACTOR3 Endpoint 2xx Scorecard"
ensure_file_if_missing "$REF3_DIR/validations/deployment_validation.md" "# REFACTOR3 Deployment Validation"

# Required file inventory validation
required_files=(
  "$REF3_DIR/specs/api_contract_spec.yaml"
  "$REF3_DIR/specs/auth_and_authorizer_spec.yaml"
  "$REF3_DIR/specs/route_mapping_spec.yaml"
  "$REF3_DIR/specs/async_flow_spec.yaml"
  "$REF3_DIR/specs/dal_alignment_spec.yaml"
  "$REF3_DIR/specs/validation_spec.yaml"
  "$REF3_DIR/specs/release_gate_spec.yaml"
  "$REF3_DIR/tests/unit_tests.md"
  "$REF3_DIR/tests/integration_tests.md"
  "$REF3_DIR/tests/e2e_tests.md"
  "$REF3_DIR/tests/contract_gate_tests.md"
  "$REF3_DIR/validations/phase_exit_gates.md"
  "$REF3_DIR/validations/endpoint_2xx_scorecard.md"
  "$REF3_DIR/validations/deployment_validation.md"
)

missing_count=0
for f in "${required_files[@]}"; do
  if [[ ! -f "$f" ]]; then
    err "required file missing: ${f#$ROOT_DIR/}"
    missing_count=$((missing_count + 1))
  fi
done

payload_count=$(find "$REF3_DIR/payloads" -maxdepth 1 -type f -name '*.json' | wc -l | tr -d ' ')
if [[ "$payload_count" != "27" ]]; then
  err "payload contract count must be 27, found: $payload_count"
  exit 1
fi

if [[ "$missing_count" -ne 0 ]]; then
  err "required artifact validation failed with $missing_count missing files"
  exit 1
fi

log "payload contract count verified: 27"
log "bootstrap completed successfully"
