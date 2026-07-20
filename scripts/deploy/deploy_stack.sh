#!/usr/bin/env bash
#
# deploy_stack.sh — synth -> pre-flight -> change set -> (human gate) -> execute.
#
# WHY: the P-28 flow already splits create-change-set from execute-change-set and
# reads a Replacement report before approving. That gate is sound but incomplete:
# it validates the SHAPE of a deploy, not whether the resources can actually be
# created in this AWS account. Two failure classes slip straight through it —
# defects inside nested templates (opaque TemplateURLs at change-set time) and
# account-level name/singleton collisions (never checked at all). Both only
# surface many minutes into a real create and take the whole stack down.
#
# This script inserts preflight_deploy_check.py between synth and change-set
# creation, so those failures cost seconds instead of a full create + rollback +
# teardown + redeploy cycle.
#
# The human gate is preserved: without --execute this script PREPARES only. It
# never executes a change set on its own. That matches P-28's human-only-execute
# invariant (runbooks/p28-human-gated-deploy-runbook.md §2).
#
# Usage:
#   ENVIRONMENT=devx scripts/deploy/deploy_stack.sh CareerVpCrudDevx
#   ENVIRONMENT=devx scripts/deploy/deploy_stack.sh CareerVpCrudDevx --execute
#
# Env:
#   ENVIRONMENT                 required (dev | devx | stage | prod)
#   ALARM_SUBSCRIPTION_EMAILS   recommended for any env absent from
#                               monitoring.py's _DEFAULT_ALARM_EMAILS map
#                               (devx is absent -> zero alarm subscribers)
#   CDK_CONTEXT                 extra -c flags (default: p26_rehome_features=true)

set -euo pipefail

STACK_NAME="${1:-}"
MODE="${2:-prepare}"

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
INFRA_DIR="$REPO_ROOT/infra"
BACKEND_DIR="$REPO_ROOT/src/backend"
CDK_OUT="$INFRA_DIR/cdk.out"
CDK_CONTEXT="${CDK_CONTEXT:--c p26_rehome_features=true}"
CHANGE_SET_NAME="deploy-$(date -u +%Y%m%dT%H%M%SZ)"
EVIDENCE_DIR="$REPO_ROOT/docs/evidence"

if [[ -z "$STACK_NAME" ]]; then
  echo "Usage: ENVIRONMENT=<env> $0 <stack-name> [--execute]" >&2
  exit 2
fi
if [[ -z "${ENVIRONMENT:-}" ]]; then
  echo "ERROR: ENVIRONMENT must be set (dev | devx | stage | prod)" >&2
  exit 2
fi

log()  { printf '\n[deploy] === %s ===\n' "$*"; }
info() { printf '[deploy] %s\n' "$*"; }
fail() { printf '[deploy] ERROR: %s\n' "$*" >&2; exit 1; }

# P-21: any environment missing from monitoring.py's default map resolves to zero
# alarm subscribers, which fails silently rather than at deploy time.
if [[ -z "${ALARM_SUBSCRIPTION_EMAILS:-}" ]]; then
  case "$ENVIRONMENT" in
    dev|stage|staging|prod|production) ;;
    *) info "WARN: $ENVIRONMENT has no default alarm email and \
ALARM_SUBSCRIPTION_EMAILS is unset — alarms will have no subscriber (P-21)." ;;
  esac
fi

# ---------------------------------------------------------------------------
log "0/6 stack state"
# ---------------------------------------------------------------------------
STATUS="$(aws cloudformation describe-stacks --stack-name "$STACK_NAME" \
  --query 'Stacks[0].StackStatus' --output text 2>/dev/null || echo "ABSENT")"
info "$STACK_NAME is $STATUS"

case "$STATUS" in
  ROLLBACK_COMPLETE|ROLLBACK_FAILED|CREATE_FAILED|DELETE_FAILED)
    fail "$STACK_NAME is in terminal state $STATUS and cannot be deployed into.
       Clean it up first:  scripts/deploy/cleanup_stack.sh $STACK_NAME"
    ;;
esac

IS_CREATE="false"
[[ "$STATUS" == "ABSENT" || "$STATUS" == "REVIEW_IN_PROGRESS" ]] && IS_CREATE="true"

# ---------------------------------------------------------------------------
log "1/6 build Lambda artifacts"
# ---------------------------------------------------------------------------
# `cdk synth`/`deploy` reads compiled Lambda code from src/backend/.build/lambdas
# (infra/careervp/api_construct.py points AssetCode there). That directory is
# gitignored build output, not checked in, so synth fails with "Cannot find
# asset" on any machine/container that hasn't run this. deploy.yml's CI jobs
# call `make build` for the same reason (.github/workflows/deploy.yml:68,289).
command -v docker >/dev/null 2>&1 || fail "docker is required for 'make build' \
(it builds Lambda deps inside the Lambda base image for a reproducible, \
correct-platform artifact) — start Docker Desktop and retry."
docker info >/dev/null 2>&1 || fail "docker is installed but not running — \
start Docker Desktop and retry."

cd "$BACKEND_DIR"
make build || fail "make build failed — see output above"
info "Lambda artifacts built -> $BACKEND_DIR/.build/lambdas"

# ---------------------------------------------------------------------------
log "2/6 synth"
# ---------------------------------------------------------------------------
cd "$INFRA_DIR"
# shellcheck disable=SC2086
ENVIRONMENT="$ENVIRONMENT" uv run cdk synth "$STACK_NAME" $CDK_CONTEXT >/dev/null \
  || fail "cdk synth failed"
info "synth OK -> $CDK_OUT"

# ---------------------------------------------------------------------------
log "3/6 pre-flight account-collision check"
# ---------------------------------------------------------------------------
# This is the step the P-28 gate cannot perform. It reads the nested templates
# too, and asks AWS whether each account-scoped name/singleton is already taken.
cd "$REPO_ROOT"
if ! uv run --project infra python scripts/ci/preflight_deploy_check.py \
      --template-dir "$CDK_OUT" --stack "$STACK_NAME"; then
  fail "pre-flight found blocking conflicts. Fix them before forming a change set —
       these WILL fail the create after several minutes, not at change-set time."
fi

# ---------------------------------------------------------------------------
log "4/6 create change set"
# ---------------------------------------------------------------------------
cd "$INFRA_DIR"
# shellcheck disable=SC2086
ENVIRONMENT="$ENVIRONMENT" uv run cdk deploy "$STACK_NAME" --no-execute \
  --change-set-name "$CHANGE_SET_NAME" $CDK_CONTEXT \
  || fail "change-set creation failed"
info "change set: $CHANGE_SET_NAME"

# ---------------------------------------------------------------------------
log "5/6 P-28 Replacement report"
# ---------------------------------------------------------------------------
mkdir -p "$EVIDENCE_DIR"
# NOTE: ${VAR,,} is bash 4+; macOS ships bash 3.2, so lowercase via tr.
STACK_SLUG="$(printf '%s' "$STACK_NAME" | tr '[:upper:]' '[:lower:]')"
CHANGESET_JSON="$EVIDENCE_DIR/${STACK_SLUG}-changeset-${CHANGE_SET_NAME}.json"
aws cloudformation describe-change-set \
  --stack-name "$STACK_NAME" --change-set-name "$CHANGE_SET_NAME" \
  > "$CHANGESET_JSON"

cd "$REPO_ROOT"
uv run --project infra python scripts/ci/changeset_replacement_report.py \
  --changeset "$CHANGESET_JSON" \
  || fail "Replacement report auto-failed. Do NOT execute this change set."
info "evidence: $CHANGESET_JSON"

if [[ "$MODE" != "--execute" ]]; then
  cat <<EOF

[deploy] PREPARED — nothing executed.

  Review the Replacement report above (confirm auto_fail: false), then run:

    ENVIRONMENT=$ENVIRONMENT $0 $STACK_NAME --execute

  Or execute the already-formed change set directly:

    aws cloudformation execute-change-set \\
      --stack-name $STACK_NAME --change-set-name $CHANGE_SET_NAME

EOF
  exit 0
fi

# ---------------------------------------------------------------------------
log "6/6 execute"
# ---------------------------------------------------------------------------
# --disable-rollback for ephemeral stacks only: on failure the stack stops at
# CREATE_FAILED with whatever it managed to create still standing, instead of
# CFN immediately tearing all of that back down again (the "ROLLBACK_IN_PROGRESS
# / Resource creation cancelled" cascade that buried the real error on
# 2026-07-19). That buys two things: the failed resources are inspectable
# (describe-stack-events, or the console) before anything is deleted, and you
# skip paying for the rollback teardown before you even get to run cleanup.
#
# There is no in-place retry from CREATE_FAILED — CloudFormation will not accept
# another create-change-set/execute against a stack in that state, and there is
# no "continue rollback" for a stack that never reached a good state (that verb
# only applies to UPDATE_ROLLBACK_FAILED). Delete-then-recreate is the only path,
# which is exactly what cleanup_stack.sh does: it treats CREATE_FAILED the same
# as ROLLBACK_COMPLETE (disable termination protection if needed, delete, wait).
# Long-lived environments (dev/stage/prod) keep default rollback instead: a
# stack that always lands in a clean terminal state matters more there than
# inspectability or iteration speed.
# NOTE: expanding an empty array under `set -u` is an unbound-variable error in
# bash 3.2 (macOS default), so this is a plain string rather than an array.
ROLLBACK_ARG=""
if [[ "$ENVIRONMENT" == "devx" ]]; then
  ROLLBACK_ARG="--disable-rollback"
  info "ephemeral env: --disable-rollback (failed resources preserved for triage)"
fi

# shellcheck disable=SC2086
aws cloudformation execute-change-set \
  --stack-name "$STACK_NAME" --change-set-name "$CHANGE_SET_NAME" $ROLLBACK_ARG

WAITER="stack-update-complete"
[[ "$IS_CREATE" == "true" ]] && WAITER="stack-create-complete"
info "waiting ($WAITER) — a full create runs ~15-25 min"

if aws cloudformation wait "$WAITER" --stack-name "$STACK_NAME"; then
  log "DEPLOY COMPLETE"
  aws cloudformation describe-stacks --stack-name "$STACK_NAME" \
    --query 'Stacks[0].Outputs' --output table
  exit 0
fi

# Failed. Show the ROOT cause, not the cascade. On the 2026-07-19 devx failure
# ~50 of 51 FAILED events were "Resource creation cancelled" noise around a
# single real failure, which is why the real one was easy to miss.
log "DEPLOY FAILED — root cause"
aws cloudformation describe-stack-events --stack-name "$STACK_NAME" \
  --query "reverse(StackEvents[?contains(ResourceStatus,'FAILED') \
    && ResourceStatusReason!='Resource creation cancelled'] \
    | [].[Timestamp,LogicalResourceId,ResourceStatusReason])" \
  --output text | head -10

cat <<EOF

[deploy] Next steps:
  1. Fix the root cause above in code (not at the AWS CLI level).
  2. If a new account-level collision caused it, add a check to
     scripts/ci/preflight_deploy_check.py so it can never cost a cycle again.
  3. scripts/deploy/cleanup_stack.sh $STACK_NAME
  4. Re-run this script.

EOF
exit 1
