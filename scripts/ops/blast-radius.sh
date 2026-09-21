#!/usr/bin/env bash
# What actually happens if I do this? Computed, not recalled.
#
# Exists because on 2026-09-20 a merge of a one-file workflow PR into main
# triggered an ungated `make deploy` that deleted ~70 resources in
# CareerVpCrudDev -- including the CrudFeatures nested stack, the WAF WebACL and
# the API Gateway custom domain. The fact that main auto-deploys had been
# written down hours earlier and was not connected to the action.
#
# Usage:
#   scripts/ops/blast-radius.sh push main       # what fires when main advances
#   scripts/ops/blast-radius.sh merge main      # a PR merging INTO main == push main
#   scripts/ops/blast-radius.sh push db-redesign
#   scripts/ops/blast-radius.sh pull_request main
set -euo pipefail

EVENT="${1:-}"; REF="${2:-}"
[ -n "$EVENT" ] && [ -n "$REF" ] || { echo "usage: $0 <push|merge|pull_request> <branch>"; exit 1; }
[ "$EVENT" = "merge" ] && EVENT="push"   # merging into X advances X

# The workflows that govern an event on REF are REF's own workflows, not the
# ones in this working tree. Read them from git when the remote ref exists.
WFDIR=".github/workflows"
TMPD=""
if git rev-parse --verify --quiet "origin/$REF" >/dev/null 2>&1; then
  TMPD=$(mktemp -d)
  for f in $(git ls-tree -r "origin/$REF" --name-only | grep '^\.github/workflows/.*\.ya\?ml$'); do
    git show "origin/$REF:$f" > "$TMPD/$(basename "$f")" 2>/dev/null || true
  done
  WFDIR="$TMPD"
  echo "  (reading workflows from origin/$REF, not the working tree)"
fi
trap '[ -n "$TMPD" ] && rm -rf "$TMPD"' EXIT

echo "BLAST RADIUS — event=$EVENT ref=$REF"
echo

python3 - "$EVENT" "$REF" "$WFDIR" <<'PY'
import sys, yaml, pathlib, fnmatch
event, ref, wfdir = sys.argv[1], sys.argv[2], sys.argv[3]
DEPLOYS = ('make deploy', 'cdk deploy', 'execute-change-set', 'execute-changeset')
fires, deploys = [], []

for f in sorted(pathlib.Path(wfdir).glob('*.y*ml')):
    try: d = yaml.safe_load(f.read_text())
    except Exception: continue
    if not isinstance(d, dict): continue
    on = d.get('on') or d.get(True)
    if not isinstance(on, dict): continue
    trig = on.get(event)
    if trig is None and event not in on: continue
    brs = (trig or {}).get('branches') if isinstance(trig, dict) else None
    if brs is not None and not any(fnmatch.fnmatch(ref, b) for b in brs): continue
    paths = (trig or {}).get('paths') if isinstance(trig, dict) else None
    fires.append((f.name, paths))
    for jname, j in (d.get('jobs') or {}).items():
        if not isinstance(j, dict): continue
        runs = ' '.join(str(s.get('run','')) for s in (j.get('steps') or []) if isinstance(s, dict))
        if any(k in runs for k in DEPLOYS):
            executes = 'make deploy' in runs or 'execute-change' in runs
            deploys.append((f.name, jname, j.get('environment'), executes,
                            (j.get('env') or {}).get('STACK_NAME') or (d.get('env') or {}).get('STACK_NAME')))

print(f"  workflows that fire: {len(fires)}")
for n, paths in fires:
    if paths:
        print(f"    - {n}   \033[33mONLY IF changed paths match:\033[0m {', '.join(paths)}")
    else:
        print(f"    - {n}")
print()
if not deploys:
    print("  DEPLOY JOBS: none. This event changes no AWS infrastructure.")
else:
    print(f"  \033[31mDEPLOY JOBS: {len(deploys)}\033[0m")
    for wf, job, env, ex, stack in deploys:
        gate = f"environment={env}" if env else "\033[31mNO ENVIRONMENT GATE\033[0m"
        kind = "\033[31mCREATE+EXECUTE\033[0m" if ex else "changeset only (no execute)"
        print(f"    - {wf} :: {job}")
        print(f"        stack : {stack or '(from inputs)'}")
        print(f"        gate  : {gate}")
        if env and isinstance(env, str):
            open('/tmp/.br-envs','a').write(f"environment={env}\n")
        print(f"        action: {kind}")
PY

echo
echo "  Workflow enabled-state (a disabled workflow does not fire at all):"
if command -v gh >/dev/null 2>&1; then
  gh workflow list --all --json name,state,path --jq \
    '.[] | select(.state != "active") | "    DISABLED: \(.name)  (\(.path))"' 2>/dev/null || true
  gh workflow list --all --json state --jq '[.[]|select(.state!="active")]|length' 2>/dev/null \
    | grep -q '^0$' && echo "    (all workflows active)"
fi

echo
echo "  Are those environment gates REAL? (live check — an environment with 0"
echo "  protection rules does not gate anything, it just labels the job)"
for E in $(grep -oE "environment=[a-z-]+" /tmp/.br-envs 2>/dev/null | cut -d= -f2 | sort -u); do
  R=$(gh api "repos/:owner/:repo/environments/$E" \
      --jq '"\(.protection_rules|length) rules, \(.protection_rules|map(select(.type=="required_reviewers"))|length) reviewer-rules"' 2>/dev/null) \
    || R="DOES NOT EXIST (GitHub auto-creates it unprotected on first use)"
  case "$R" in
    "0 rules"*|"DOES NOT"*) printf "    \033[31m%-18s %s\033[0m\n" "$E" "$R" ;;
    *)                      printf "    \033[32m%-18s %s\033[0m\n" "$E" "$R" ;;
  esac
done
rm -f /tmp/.br-envs

echo
echo "  Amplify branches that auto-build (live check):"
if command -v aws >/dev/null 2>&1; then
  aws amplify list-branches --app-id d3j2wnm8g5clnw --region us-east-1 \
    --query "branches[?branchName=='$REF' && enableAutoBuild].[branchName,stage]" \
    --output text 2>/dev/null | sed 's/^/    - /' || echo "    (amplify query failed)"
  [ -z "$(aws amplify list-branches --app-id d3j2wnm8g5clnw --region us-east-1 \
      --query "branches[?branchName=='$REF' && enableAutoBuild].branchName" --output text 2>/dev/null)" ] \
    && echo "    none"
else
  echo "    (aws cli unavailable)"
fi
echo
echo "  UNDO: CloudFormation has no automatic rollback after a successful update."
echo "        Reversal = redeploy the prior template from the branch that produced it."
