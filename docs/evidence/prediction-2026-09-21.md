# Prediction — merge `tools/proof-harness` → `db-redesign`, 2026-09-21

Written and committed before push/PR/merge (HANDOFF-11 ordering rule). Covers
`git diff origin/db-redesign..HEAD` as of commit `f96ad31` — confirmed by
`git merge-base origin/db-redesign HEAD` to equal `origin/db-redesign`'s tip
(`7c08d89`), i.e. this is the full and exact delta the merge will ship.

Rollback target (Phase 0.3): `7c08d89286d181885ebefd49702159c0d5d08667`
(deployed stack reports it with a spurious `-dirty` suffix — known stamping
bug, `src/backend/Makefile:28`, not evidence of an actual dirty deploy).

## Baseline note

Phase 1's `make journey` reached **4 of 9** (J4 passing), not the 3 of 9 this
handoff document predicted when it was written. Root cause, confirmed from
the proof's `browser_diagnostics`: `journey.spec.ts` was rewritten in the same
commit as the async gap-analysis fix (`f96ad31`) — real SysAid CV/job fixtures
replaced the synthetic ones, and J4's manual reload-loop was dropped. Run
against the still-old deployed backend, J3's diagnostics show the expected
504 on `POST /gap-analysis/questions` (the known synchronous-Lambda timeout),
but the backend kept running past the API Gateway timeout and persisted
before J4's now-generous wait (`2 × GENERATION_TIMEOUT_MS`) expired — so J4
passed by timing luck, not because anything is fixed pre-merge. This baseline
(4 of 9) is accepted as-is per operator direction: Phase 1 and Phase 4 both
run the identical already-committed test file, so the before/after
*comparison* stays valid even though the absolute number doesn't match the
stale prediction in this doc's own preamble.

## Per-change predictions

### 1. `d825f84` — `ENVIRONMENT` on every Lambda, `resource_env()` raises instead of defaulting

**Expect:** Every `-devx` Lambda reports `ENVIRONMENT=devx`. Pre-merge reading
(today): of the ~31 `-devx` Lambdas, ~30 report `Environment.Variables.ENVIRONMENT
= None` (the fix isn't deployed yet). Post-merge, that count should be zero.

**Command:**
```bash
for fn in $(aws lambda list-functions --region us-east-1 \
    --query 'Functions[?ends_with(FunctionName,`-devx`)].FunctionName' --output text); do
  printf '%-48s %s\n' "$fn" "$(aws lambda get-function-configuration --region us-east-1 \
    --function-name "$fn" --query 'Environment.Variables.ENVIRONMENT' --output text)"
done | grep -v ' devx$'
```
Expect: empty output.

**Also expect:** `get_subscription failed` stops appearing in
`careervp-gap-api-lambda-devx` logs after the deploy timestamp (pre-merge
reading today: 4 occurrences in the trailing 24h — `SubscriptionRepository`
was silently reading the `-dev` table). Command from HANDOFF-11's reference
table, `--start-time` set to the post-deploy timestamp.

**Do NOT expect:** the journey number to move on this alone — J4 is a
timeout/architecture issue (see #3 below), not a quota/subscription failure.

### 2. `d825f84` — capability table (`infra/careervp/environments.py`)

**Expect:** synth fails loudly on an unknown environment name.

**Command:** `ENVIRONMENT=nonsense cdk synth` (from `infra/`) → `ValueError:
No profile for 'nonsense'; add a row to environments.py`

**Do NOT expect:** any devx runtime change from this alone — `devx`'s profile
(`artifact_chain=True, api_custom_domain=False`) matches what devx's
ad-hoc `naming.environment == "dev"` checks already produced for api_custom_domain
(False, since devx ≠ "dev") and produces `artifact_chain=True`, which is a
**change** — see #3.

### 3. `d825f84` — artifact chain enabled for devx

Previously `_artifact_chain_enabled()` defaulted `ARTIFACT_CHAIN_ENABLED` to
`"true"` only when `naming.environment == "dev"` — devx silently got `false`.
The new capability table declares `devx: artifact_chain=True`, so devx now
defaults to `true`.

**Expect:** `ARTIFACT_CHAIN_ENABLED=true` on devx Lambdas that read it, and the
artifact-chain state machine becomes invokable (though nothing in the current
journey exercises it — J1-J4 don't touch VPR/cover-letter/interview-prep
generation, which is where the chain's second consumer,
`company_research_worker_handler.py:385`, lives).

**Command:**
```bash
aws stepfunctions list-executions \
  --state-machine-arn arn:aws:states:us-east-1:788159322332:stateMachine:careervp-artifact-chain-statemachine-devx \
  --query 'length(executions)' --output text
```
Pre-merge reading (today): `0`. **Do not expect this to move** — nothing in
J1-J4 invokes the chain, so a still-`0` count post-merge is consistent with
the flag simply being enabled, not evidence the chain runs end-to-end.

**Do NOT expect:** `9 of 9` from this alone.

### 4. `f96ad31` — async gap-question generation (HANDOFF-09 Step 2.4)

This is the change most likely to move the headline number, and the one this
handoff's own reference table didn't yet know about when it was written.

**Expect:**
- `POST /gap-analysis/questions` returns `202` and a `PENDING` row, not a
  synchronous result. `gap_handler.py`'s `generate_questions` no longer makes
  the LLM call inline.
- A new `careervp-gap-worker-lambda-devx` Lambda exists, SQS-triggered off the
  existing (previously unused) gap-analysis queue.
- The gap-analysis frontend page polls every 3s and shows a distinct
  "generating" state instead of a naked empty state.
- **J4 passes deterministically** (worker completes off the request path,
  page polls until done) rather than by the timing-luck mechanism seen in the
  Phase 1 baseline. J3 should no longer show a `504` in its diagnostics,
  since `generate_questions` returns immediately instead of racing the API
  Gateway integration timeout.

**Commands:**
```bash
# confirm the worker Lambda exists and is SQS-triggered
aws lambda get-function-configuration --region us-east-1 \
  --function-name careervp-gap-worker-lambda-devx --query 'Timeout' --output text
# expect: 300

# confirm no J3 504 in the post-deploy journey proof's browser_diagnostics
```

**Do NOT expect:** J5-J9 to change. They are gated on VPR/cover-letter/
interview-prep/export, none of which this merge touches. They remain
unmeasured against deployed code either way (J5 fails on a UI-locator issue
unrelated to this merge — `module-card-companyResearch`'s CTA never reaching
"view" text within the poll window — pre-existing per Phase 1's proof).

### 5. `0c04fc9` — GlobalTable gate fix (CI-tooling only)

**Expect:** no devx runtime change. `changeset_replacement_report.py` and
`preflight.py` are CI/local tooling, not deployed Lambda code. Already
reflected in Phase 1's baseline (`preflight` ran the fixed script per
HANDOFF-11 §Phase 1 note).

**Do NOT expect:** any journey or Lambda-configuration change attributable to
this commit.

### 6. `a491884` / dead-code sweep scripts (`dead_code.py`, `dead_api.py`, `table_map.py`)

**Expect:** no runtime change — these are standalone analysis scripts under
`src/backend/scripts/`, not imported by any handler. They match the deploy
path filter (`src/backend/**`) and will trigger a `CareerVpCrudDevx` deploy
with zero behavioral effect, same class of false-positive trigger CLAUDE.md
warns about for test-only/doc-only changes.

**Do NOT expect:** any observable difference from these files' presence.

### 7. `7fe2348` — environment-coupling test guards

**Expect:** no runtime change — test-only commit (6 new/changed test files,
zero non-test files).

## Headline number

**Predicted: 5 of 9.** J1-J4 pass (J4 now deterministic instead of lucky);
J5 continues to fail on the same pre-existing UI-locator issue visible in the
Phase 1 baseline, unrelated to anything in this merge. If J5 also passes,
that is a bonus this prediction did not anticipate and should be called out,
not quietly accepted as expected.

If the chain (`ARTIFACT_CHAIN_ENABLED`) being on causes J5-J9 to newly reach
and pass, say plainly that this is the artifact chain doing what it was built
for, not evidence gap-question generation had anything to do with it —
different subsystems.
