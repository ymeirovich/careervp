#!/usr/bin/env bash
set -euo pipefail

# Continuous runner for docs/refactor/live_tests/run_all_tests.py
# Usage:
#   bash scripts/diagnostics/run_live_tests_loop.sh --env dev
#   bash scripts/diagnostics/run_live_tests_loop.sh --env stage --mode smoke --interval 60
#   bash scripts/diagnostics/run_live_tests_loop.sh --env stage --test users --interval 30

ENV_NAME="dev"
MODE="full"
TEST_NAME=""
INTERVAL="90"
STOP_ON_FAIL="false"
VERBOSE="false"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --env)
      ENV_NAME="$2"; shift 2 ;;
    --mode)
      MODE="$2"; shift 2 ;;
    --test)
      TEST_NAME="$2"; shift 2 ;;
    --interval)
      INTERVAL="$2"; shift 2 ;;
    --stop-on-fail)
      STOP_ON_FAIL="true"; shift ;;
    --verbose)
      VERBOSE="true"; shift ;;
    *)
      echo "Unknown argument: $1" >&2
      exit 2 ;;
  esac
done

case "$ENV_NAME" in
  dev)
    API_BASE="https://dev-api.careervp.com"
    ;;
  stage|staging)
    API_BASE="https://stage-api.careervp.com"
    ;;
  *)
    echo "--env must be dev or stage" >&2
    exit 2
    ;;
esac

RUNNER="docs/refactor/live_tests/run_all_tests.py"
SUMMARY_DIR="/tmp/careervp-live-tests/${ENV_NAME}"
mkdir -p "$SUMMARY_DIR"

iter=0
while true; do
  iter=$((iter + 1))
  ts="$(date -u +%Y%m%dT%H%M%SZ)"
  summary_json="${SUMMARY_DIR}/summary-${ts}.json"

  echo
  echo "============================================================"
  echo "Iteration: ${iter}"
  echo "UTC Time : ${ts}"
  echo "Env      : ${ENV_NAME}"
  echo "API_BASE : ${API_BASE}"
  echo "Mode     : ${MODE}"
  [[ -n "$TEST_NAME" ]] && echo "Test     : ${TEST_NAME}"
  echo "Summary  : ${summary_json}"
  echo "============================================================"

  cmd=(python "$RUNNER" --summary-json "$summary_json")
  if [[ -n "$TEST_NAME" ]]; then
    cmd+=(--test "$TEST_NAME")
  else
    cmd+=(--mode "$MODE")
  fi
  [[ "$VERBOSE" == "true" ]] && cmd+=(--verbose)

  set +e
  API_BASE="$API_BASE" "${cmd[@]}"
  rc=$?
  set -e

  echo "Exit code: ${rc}"
  if [[ "$rc" -ne 0 && "$STOP_ON_FAIL" == "true" ]]; then
    echo "Stopping on failure (--stop-on-fail)."
    exit "$rc"
  fi

  echo "Sleeping ${INTERVAL}s... (Ctrl+C to stop)"
  sleep "$INTERVAL"
done
