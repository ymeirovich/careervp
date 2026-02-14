#!/bin/bash
#
# CloudFormation State Guard Script
# Ensures AWS CloudFormation stack is in a deployable state before CDK deployment.
# Handles stuck updates, failed rollbacks, and orphaned changesets.
#
# Usage: .github/scripts/cfn-guard.sh <stack_name> <aws_region>
# Example: .github/scripts/cfn-guard.sh CareerVpCrudDev us-east-1
#

set -euo pipefail

STACK_NAME="${1:-}"
REGION="${2:-us-east-1}"

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() { echo -e "${GREEN}[CFN-GUARD]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[CFN-GUARD]${NC} $1"; }
log_error() { echo -e "${RED}[CFN-GUARD]${NC} $1"; }

# Validate inputs
if [ -z "$STACK_NAME" ]; then
    log_error "Usage: $0 <stack_name> <aws_region>"
    log_error "Stack name is required"
    exit 1
fi

echo "=========================================="
log_info "CloudFormation State Guard Starting"
echo "Stack: $STACK_NAME"
echo "Region: $REGION"
echo "=========================================="

# Step 1: Check if stack exists and get current status
log_info "Checking stack status..."
STATUS=$(aws cloudformation describe-stacks \
    --stack-name "$STACK_NAME" \
    --region "$REGION" \
    --query "Stacks[0].StackStatus" \
    --output text 2>/dev/null) || STATUS="NOT_FOUND"

log_info "Current stack status: $STATUS"

# Step 2: Handle non-existent stack
if [ "$STATUS" = "NOT_FOUND" ]; then
    log_info "Stack does not exist. Proceeding with initial deployment."
    exit 0
fi

# Step 3: Wait for in-progress operations to complete
if [[ "$STATUS" == *"_IN_PROGRESS"* ]]; then
    log_warn "Stack is in $STATUS state. Waiting for completion..."
    log_info "This may take several minutes..."

    # Try both wait commands - one will match the current operation type
    aws cloudformation wait stack-create-complete \
        --stack-name "$STACK_NAME" \
        --region "$REGION" 2>/dev/null || true

    aws cloudformation wait stack-update-complete \
        --stack-name "$STACK_NAME" \
        --region "$REGION" 2>/dev/null || true

    # Re-check status after waiting
    NEW_STATUS=$(aws cloudformation describe-stacks \
        --stack-name "$STACK_NAME" \
        --region "$REGION" \
        --query "Stacks[0].StackStatus" \
        --output text 2>/dev/null) || NEW_STATUS="UNKNOWN"

    log_info "Stack status after wait: $NEW_STATUS"

    if [[ "$NEW_STATUS" == *"_IN_PROGRESS"* ]]; then
        log_error "Stack is still in progress after waiting. Manual intervention required."
        exit 1
    fi
fi

# Step 4: Handle UPDATE_ROLLBACK_FAILED state
if [ "$STATUS" = "UPDATE_ROLLBACK_FAILED" ]; then
    log_warn "Stack is stuck in UPDATE_ROLLBACK_FAILED. Attempting recovery..."
    log_info "Running continue-update-rollback..."

    if aws cloudformation continue-update-rollback \
        --stack-name "$STACK_NAME" \
        --region "$REGION" 2>/dev/null; then
        log_info "Rollback continuation initiated. Waiting for completion..."
        aws cloudformation wait stack-rollback-complete \
            --stack-name "$STACK_NAME" \
            --region "$REGION" 2>/dev/null || true
    else
        log_error "Failed to continue rollback. Stack requires manual intervention."
        exit 1
    fi
fi

# Step 5: Handle CREATE_ROLLBACK_FAILED state
if [ "$STATUS" = "CREATE_ROLLBACK_FAILED" ]; then
    log_warn "Stack is stuck in CREATE_ROLLBACK_FAILED. Deleting for clean deploy..."
    if aws cloudformation delete-stack \
        --stack-name "$STACK_NAME" \
        --region "$REGION" 2>/dev/null; then
        log_info "Stack deletion initiated. Waiting for completion..."
        aws cloudformation wait stack-delete-complete \
            --stack-name "$STACK_NAME" \
            --region "$REGION" 2>/dev/null || true
        log_info "Stack deleted successfully. Ready for fresh deployment."
        exit 0
    else
        log_error "Failed to delete stack. Manual intervention required."
        exit 1
    fi
fi

# Step 6: Cleanup orphaned/failed changesets
# This is the PRIMARY fix for "Member must not be null" errors
log_info "Checking for orphaned changesets..."

# First, check for changesets that are still in progress
IN_PROGRESS_CHANGESETS=$(aws cloudformation list-change-sets \
    --stack-name "$STACK_NAME" \
    --region "$REGION" \
    --query "Summaries[?Status==\`CREATE_IN_PROGRESS\`].ChangeSetId" \
    --output text 2>/dev/null) || IN_PROGRESS_CHANGESETS=""

if [ -n "$IN_PROGRESS_CHANGESETS" ]; then
    log_warn "Found changeset(s) in CREATE_IN_PROGRESS state. Waiting for completion..."
    echo "$IN_PROGRESS_CHANGESETS" | tr '\t' '\n' | while read -r changeset_id; do
        if [ -n "$changeset_id" ]; then
            log_info "  Waiting for changeset: $changeset_id"
            # Wait for the changeset to complete (either succeed or fail)
            while true; do
                CS_STATUS=$(aws cloudformation describe-change-set \
                    --change-set-name "$changeset_id" \
                    --region "$REGION" \
                    --query "Status" \
                    --output text 2>/dev/null) || CS_STATUS="UNKNOWN"
                log_info "  Changeset status: $CS_STATUS"
                if [ "$CS_STATUS" = "CREATE_COMPLETE" ] || [ "$CS_STATUS" = "FAILED" ]; then
                    break
                fi
                log_info "  Waiting 30 seconds..."
                sleep 30
            done
        fi
    done
    log_info "In-progress changesets have completed."
fi

# Now clean up all failed/obsolete changesets
CHANGESET_IDS=$(aws cloudformation list-change-sets \
    --stack-name "$STACK_NAME" \
    --region "$REGION" \
    --query "Summaries[?Status==\`FAILED\` || Status==\`OBSOLETE\`].ChangeSetId" \
    --output text 2>/dev/null) || CHANGESET_IDS=""

if [ -n "$CHANGESET_IDS" ]; then
    log_warn "Found stuck changesets. Cleaning up..."
    echo "$CHANGESET_IDS" | tr '\t' '\n' | while read -r changeset_id; do
        if [ -n "$changeset_id" ]; then
            log_info "  Deleting changeset: $changeset_id"
            aws cloudformation delete-change-set \
                --change-set-name "$changeset_id" \
                --region "$REGION" 2>/dev/null || log_warn "  Failed to delete changeset: $changeset_id"
        fi
    done
    log_info "Changeset cleanup complete."
else
    log_info "No orphaned changesets found."
fi

# Step 7: Final status check
FINAL_STATUS=$(aws cloudformation describe-stacks \
    --stack-name "$STACK_NAME" \
    --region "$REGION" \
    --query "Stacks[0].StackStatus" \
    --output text 2>/dev/null) || FINAL_STATUS="UNKNOWN"

# In busy repos we can briefly observe an in-progress status even after changesets settle.
# Retry/poll before failing to avoid false negatives.
if [[ "$FINAL_STATUS" == *"_IN_PROGRESS"* ]]; then
    log_warn "Stack is in $FINAL_STATUS at final check. Polling for stabilization..."
    ATTEMPTS=0
    MAX_ATTEMPTS=20
    while [[ "$FINAL_STATUS" == *"_IN_PROGRESS"* ]] && [ "$ATTEMPTS" -lt "$MAX_ATTEMPTS" ]; do
        ATTEMPTS=$((ATTEMPTS + 1))
        log_info "  Poll attempt $ATTEMPTS/$MAX_ATTEMPTS; waiting 15 seconds..."
        sleep 15
        FINAL_STATUS=$(aws cloudformation describe-stacks \
            --stack-name "$STACK_NAME" \
            --region "$REGION" \
            --query "Stacks[0].StackStatus" \
            --output text 2>/dev/null) || FINAL_STATUS="UNKNOWN"
        log_info "  Current status: $FINAL_STATUS"
    done
fi

echo "=========================================="
if [[ "$FINAL_STATUS" == *"_IN_PROGRESS"* ]]; then
    log_error "Stack is still in progress. Aborting."
    exit 1
fi

if [[ "$FINAL_STATUS" == *"_FAILED"* ]] || [[ "$FINAL_STATUS" == *"ROLLBACK"* ]]; then
    log_error "Stack is in failed state: $FINAL_STATUS. Manual intervention required."
    exit 1
fi

log_info "Stack is ready for deployment. Status: $FINAL_STATUS"
log_info "CloudFormation State Guard - PASSED"
echo "=========================================="

exit 0
