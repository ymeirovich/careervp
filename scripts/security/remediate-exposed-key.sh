#!/usr/bin/env bash
# Remediate the exposed AdministratorAccess key AKIA3PAPU3DODGMPMWNS (careervp_user).
#
# WHAT IS ACTUALLY EXPOSED (measured 2026-09-21):
#   docs/evidence/astra-pass-b/iam-authorization-details.json (23.3 MB, public
#   remote) contains the key ID as an IAM *tag name*, plus a full
#   get-account-authorization-details dump: account id 788159322332 and 456 IAM
#   ARNs. It contains NO secret access key -- that API never returns one. So the
#   public exposure is reconnaissance, not a usable credential. The key itself is
#   still AdministratorAccess and still active, which is why it is rotated here.
#
# THE ONLY CONSUMER (measured): origin/main .github/workflows/cdk-diff.yml, which
#   passes secrets.AWS_ACCESS_KEY_ID. Every other workflow, on every branch,
#   already uses OIDC. The GitHub OIDC provider already exists in the account.
#
# Usage:  ./remediate-exposed-key.sh <phase>          # dry run, prints commands
#         APPLY=1 ./remediate-exposed-key.sh <phase>  # actually execute
# Phases: 0-verify 1-oidc 2-deactivate 3-delete 4-purge-history

set -euo pipefail

KEY_ID="AKIA3PAPU3DODGMPMWNS"
KEY_USER="careervp_user"
ACCOUNT="788159322332"
REGION="us-east-1"
BIG_FILE="docs/evidence/astra-pass-b/iam-authorization-details.json"
APPLY="${APPLY:-0}"

run() {
  if [ "$APPLY" = "1" ]; then echo "+ $*"; "$@"
  else echo "  [dry-run] $*"; fi
}
ok()   { printf '  \033[32m✓\033[0m %s\n' "$*"; }
bad()  { printf '  \033[31m✗\033[0m %s\n' "$*"; }
die()  { bad "$*"; exit 1; }

phase0() {
  echo "PHASE 0 — verify the premises before changing anything"
  aws sts get-caller-identity >/dev/null 2>&1 || die "no usable AWS credentials"
  local me; me=$(aws sts get-caller-identity --query Arn --output text)
  ok "authenticated as $me"
  [ "$(aws sts get-caller-identity --query Account --output text)" = "$ACCOUNT" ] \
    || die "wrong AWS account -- expected $ACCOUNT"
  ok "account $ACCOUNT confirmed"

  local status
  status=$(aws iam list-access-keys --user-name "$KEY_USER" \
    --query "AccessKeyMetadata[?AccessKeyId=='$KEY_ID'].Status" --output text 2>/dev/null || true)
  [ -n "$status" ] || die "key $KEY_ID not found on $KEY_USER -- already deleted?"
  ok "key exists, status=$status"

  # Refuse to proceed if this script is running AS the key being rotated.
  [ "$me" = "arn:aws:iam::$ACCOUNT:user/$KEY_USER" ] \
    && die "you are authenticated AS $KEY_USER -- rotate from a different identity"
  ok "not running as the key under rotation"

  aws iam list-open-id-connect-providers --output text \
    | grep -q "token.actions.githubusercontent.com" \
    || die "GitHub OIDC provider missing -- phase 1 would break CI"
  ok "GitHub OIDC provider present"

  local consumers
  consumers=$(git show origin/main:.github/workflows/cdk-diff.yml 2>/dev/null \
    | grep -c "secrets.AWS_ACCESS_KEY_ID" || true)
  if [ "$consumers" -gt 0 ]; then
    bad "main's cdk-diff.yml STILL uses static keys -- run phase 1 first"
  else
    ok "main's cdk-diff.yml no longer uses static keys"
  fi
  echo
  echo "  Last used:"
  aws iam get-access-key-last-used --access-key-id "$KEY_ID" \
    --query 'AccessKeyLastUsed.[LastUsedDate,ServiceName]' --output text
}

phase1() {
  echo "PHASE 1 — put the OIDC version of cdk-diff.yml on main (removes the last consumer)"
  echo "  tools/proof-harness already has the OIDC version. Port that one file."
  run git fetch origin main
  run git worktree add -b security/oidc-cdk-diff /tmp/oidc-fix origin/main
  run cp .github/workflows/cdk-diff.yml /tmp/oidc-fix/.github/workflows/cdk-diff.yml
  echo "  [then] cd /tmp/oidc-fix && git add -A && git commit && git push -u origin HEAD"
  echo "  [then] gh pr create --base main --title 'security: use OIDC in cdk-diff, drop static admin keys'"
  echo
  echo "  GATE: do not proceed to phase 2 until that PR is MERGED and one"
  echo "        cdk-diff run has SUCCEEDED on main using the role."
}

phase2() {
  echo "PHASE 2 — deactivate the key (REVERSIBLE: reactivate with --status Active)"
  local consumers
  consumers=$(git show origin/main:.github/workflows/cdk-diff.yml 2>/dev/null \
    | grep -c "secrets.AWS_ACCESS_KEY_ID" || true)
  [ "$consumers" -eq 0 ] || die "main still consumes the static key -- finish phase 1"
  run aws iam update-access-key --user-name "$KEY_USER" \
      --access-key-id "$KEY_ID" --status Inactive
  echo
  echo "  GATE: wait 3-7 days. Watch for AccessDenied:"
  echo "    aws cloudtrail lookup-events --region $REGION --max-results 50 \\"
  echo "      --lookup-attributes AttributeKey=Username,AttributeValue=$KEY_USER"
  echo "  If anything breaks:"
  echo "    aws iam update-access-key --user-name $KEY_USER --access-key-id $KEY_ID --status Active"
}

phase3() {
  echo "PHASE 3 — delete the key and the vestigial GitHub secrets (IRREVERSIBLE)"
  local status
  status=$(aws iam list-access-keys --user-name "$KEY_USER" \
    --query "AccessKeyMetadata[?AccessKeyId=='$KEY_ID'].Status" --output text)
  [ "$status" = "Inactive" ] || die "key is '$status', not Inactive -- do phase 2 and wait"
  ok "key is Inactive"
  run aws iam delete-access-key --user-name "$KEY_USER" --access-key-id "$KEY_ID"
  run gh secret delete AWS_ACCESS_KEY_ID
  run gh secret delete AWS_SECRET_ACCESS_KEY
  echo
  echo "  Also remove the tag that leaked the id in the first place:"
  run aws iam untag-user --user-name "$KEY_USER" --tag-keys "$KEY_ID"
  echo
  echo "  RECOMMENDED, separate decision: $KEY_USER holds AdministratorAccess via"
  echo "  the AdminAccess group (7 members). A deploy identity rarely needs *:*."
  echo "    aws iam remove-user-from-group --user-name $KEY_USER --group-name AdminAccess"
}

phase4() {
  echo "PHASE 4 — purge the dump from git history (REWRITES PUBLIC HISTORY)"
  echo "  Deleting the file in a new commit does NOT remove it; it stays in every"
  echo "  old commit and in every clone. This needs a rewrite + force-push."
  echo
  echo "  Coordinate first: every collaborator must re-clone afterwards."
  echo
  run git clone --mirror "git@github.com:ymeirovich/careervp.git" /tmp/careervp-purge.git
  echo "  [then, in /tmp/careervp-purge.git]"
  echo "    git filter-repo --invert-paths --path '$BIG_FILE'"
  echo "    git push --force --mirror"
  echo
  echo "  Then ask GitHub Support to purge cached views of the old objects, and"
  echo "  treat the account id + IAM topology as disclosed regardless -- a rewrite"
  echo "  does not un-publish what was already fetched."
  echo
  echo "  Cheaper alternative if a rewrite is unacceptable: leave history alone,"
  echo "  delete the file going forward, and rely on phases 2-3 having made the"
  echo "  key useless. The residual exposure is then the IAM map, not access."
}

case "${1:-}" in
  0-verify)     phase0 ;;
  1-oidc)       phase1 ;;
  2-deactivate) phase2 ;;
  3-delete)     phase3 ;;
  4-purge-history) phase4 ;;
  *) echo "usage: [APPLY=1] $0 {0-verify|1-oidc|2-deactivate|3-delete|4-purge-history}"; exit 1 ;;
esac
