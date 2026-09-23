#!/usr/bin/env bash
#
# cleanup_stack.sh — delete a CloudFormation stack, resiliently, and wait.
#
# WHY: a failed create leaves the stack in ROLLBACK_COMPLETE, a terminal state.
# CloudFormation refuses every further update, so the only way forward is a full
# delete. Two things make that slower than it should be by hand:
#
#   1. Termination protection is ON for every non-scratch CareerVP stack
#      (service_stack.py:62, asserted by P-27's test_p27_stack_policy.py), so a
#      plain `delete-stack` fails with a confusing error. It must be disabled
#      first. We keep protection ON in CDK deliberately — the P-27 invariant is
#      worth more than the one API call it costs here.
#   2. `delete-stack` is async. Racing the next deploy against an unfinished
#      delete produces a second, differently-confusing failure.
#
# This script does both, waits for the terminal state, and retries a DELETE_FAILED
# once while retaining the resources that blocked it (so a stuck resource does not
# strand the whole stack).
#
# Usage:
#   scripts/deploy/cleanup_stack.sh <stack-name> [--yes]
#
# Exit codes: 0 = stack absent (deleted or never existed), 1 = still present.

set -euo pipefail

STACK_NAME="${1:-}"
ASSUME_YES="${2:-}"

if [[ -z "$STACK_NAME" ]]; then
  echo "Usage: $0 <stack-name> [--yes]" >&2
  exit 2
fi

log() { printf '[cleanup] %s\n' "$*"; }
fail() { printf '[cleanup] ERROR: %s\n' "$*" >&2; exit 1; }

stack_status() {
  aws cloudformation describe-stacks --stack-name "$STACK_NAME" \
    --query 'Stacks[0].StackStatus' --output text 2>/dev/null || echo "ABSENT"
}

STATUS="$(stack_status)"

if [[ "$STATUS" == "ABSENT" ]]; then
  log "$STACK_NAME does not exist — nothing to clean up."
  exit 0
fi

log "$STACK_NAME is in $STATUS"

# Refuse to delete a healthy stack without explicit confirmation. Deleting a
# live CareerVpCrudDev by a typo'd argument is exactly the accident worth
# preventing, and this script is meant to be safe to run reflexively.
case "$STATUS" in
  CREATE_COMPLETE|UPDATE_COMPLETE|UPDATE_ROLLBACK_COMPLETE)
    if [[ "$ASSUME_YES" != "--yes" ]]; then
      fail "$STACK_NAME is HEALTHY ($STATUS). Refusing to delete without --yes.
       If you really mean to destroy a working stack, re-run:
         $0 $STACK_NAME --yes"
    fi
    log "healthy stack, --yes given; proceeding with delete"
    ;;
esac

# Report what is about to be lost, so the operator sees it before the wait.
RESOURCE_COUNT="$(aws cloudformation list-stack-resources --stack-name "$STACK_NAME" \
  --query 'length(StackResourceSummaries)' --output text 2>/dev/null || echo "unknown")"
log "stack holds $RESOURCE_COUNT resources"

# Surface the ORIGINAL failure before deleting the evidence. Cascade noise
# ("Resource creation cancelled") is filtered out — on the devx failure that was
# ~50 of the 51 FAILED events, and it buried the one line that mattered.
log "root failure(s), if any:"
aws cloudformation describe-stack-events --stack-name "$STACK_NAME" \
  --query "reverse(StackEvents[?contains(ResourceStatus,'FAILED') \
    && ResourceStatusReason!='Resource creation cancelled'] \
    | [].[LogicalResourceId,ResourceStatusReason])" \
  --output text 2>/dev/null | head -5 | sed 's/^/         /' || true

PROTECTED="$(aws cloudformation describe-stacks --stack-name "$STACK_NAME" \
  --query 'Stacks[0].EnableTerminationProtection' --output text 2>/dev/null || echo "False")"

if [[ "$PROTECTED" == "True" ]]; then
  log "disabling termination protection (P-27 keeps this ON in CDK by design)"
  aws cloudformation update-termination-protection \
    --stack-name "$STACK_NAME" --no-enable-termination-protection >/dev/null
fi

log "deleting $STACK_NAME ..."
aws cloudformation delete-stack --stack-name "$STACK_NAME"

log "waiting for delete to complete (this is the slow part; ~5-10 min typical)"
if aws cloudformation wait stack-delete-complete --stack-name "$STACK_NAME" 2>/dev/null; then
  log "$STACK_NAME deleted."
  exit 0
fi

# The waiter failed. Either the stack is genuinely gone (the waiter can report
# failure when the stack vanishes mid-poll) or a resource blocked the delete.
STATUS="$(stack_status)"
if [[ "$STATUS" == "ABSENT" ]]; then
  log "$STACK_NAME deleted."
  exit 0
fi

if [[ "$STATUS" == "DELETE_FAILED" ]]; then
  log "delete failed; identifying the resources that blocked it"
  RETAIN=$(aws cloudformation describe-stack-events --stack-name "$STACK_NAME" \
    --query "StackEvents[?ResourceStatus=='DELETE_FAILED'].LogicalResourceId" \
    --output text 2>/dev/null | tr '\t' '\n' | sort -u | tr '\n' ' ')

  if [[ -z "${RETAIN// }" ]]; then
    fail "$STACK_NAME is DELETE_FAILED but no blocking resource was reported.
       Inspect manually: aws cloudformation describe-stack-events --stack-name $STACK_NAME"
  fi

  log "retrying delete, retaining: $RETAIN"
  log "NOTE: retained resources survive as orphans and may themselves collide"
  log "      with the next deploy. Check them before redeploying."
  # shellcheck disable=SC2086
  aws cloudformation delete-stack --stack-name "$STACK_NAME" --retain-resources $RETAIN
  aws cloudformation wait stack-delete-complete --stack-name "$STACK_NAME" 2>/dev/null || true
fi

STATUS="$(stack_status)"
if [[ "$STATUS" == "ABSENT" ]]; then
  log "$STACK_NAME deleted."
  exit 0
fi

fail "$STACK_NAME is still present in state $STATUS. Manual intervention needed."
