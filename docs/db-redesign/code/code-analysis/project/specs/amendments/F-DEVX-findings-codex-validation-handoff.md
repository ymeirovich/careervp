# Handoff — independent validation of the F-DEVX-* findings (for Codex)

**Written:** 2026-08-01 by the Wave-3 step 3.2-CLOSEOUT-A session (claude-opus-5)
**Branch:** `db-redesign` · **Repo root:** `/Users/yitzchak.meirovich/Documents/code5/careervp`
**Prior session's commits:** `ea5eb74`, `fe8a40d`, `2491f7b`, `f05c8e8`, `f4c9797`, `427a472`

---

## 0. Your stance

**Do not confirm this analysis. Try to break it.**

A prior session ran a live characterization against two AWS stacks and produced seven findings
(`F-DEVX-1` … `F-DEVX-7`) plus a root-cause claim. That analysis was done under time pressure, by
one agent, with no second pair of eyes, and it **changed its own conclusion twice** as new evidence
arrived. Treat every claim below as a hypothesis with a name attached, not as a finding.

You are asked for **your own diagnosis and your own remediation plan**, derived from the live
system and the code — not a review of the plan in §6. If you arrive somewhere different, say so
plainly and show why. A refutation is a more valuable outcome here than a confirmation.

Three specific reasons to be suspicious of the prior work:

1. It never read a single CloudWatch log line. The whole root cause is inferred from env vars,
   table key schemas, and HTTP responses. **The claimed `ValidationException` was never observed.**
2. Its first published diagnosis was wrong (it said "the VPR is never registered"; the VPR is in
   fact written, to a different table). It self-corrected, but that means its instinct for this
   subsystem was demonstrably off at least once.
3. It is the same agent that produced the artifacts it would be reviewing. It has a stake.

---

## 1. What the prior session was asked to do, and what it actually changed

Step 3.2-CLOSEOUT-A was scoped to: commit two adversarial-review reports, add `application_id` to
two broken live-API fixtures, correct one sentence in a spec, clear a merge blocker, deploy to
devx, run the live-API suites, and write a characterization baseline. It was **explicitly
forbidden** from fixing the interview-prep worker path or removing regeneration code.

Total product-code change: **zero**. The only non-doc change is two lines:

```
tests/integration/test_full_pipeline_integration.py
tests/e2e/test_e2e_happy_path_full_job_application.py
   +  'application_id': job_id      # added to the /interview-prep/generate body
```

Everything else is docs, evidence, and the ledger. **Confirm this yourself** —
`git diff --stat a8ef789..HEAD` — because the rest of this document assumes the findings are
observations of a pre-existing system, not consequences of this session.

It also **deployed `CareerVpCrudDevx`** (2026-08-01T09:12:51Z). That is AWS state, not git state,
and reverting the commits does not undo it.

---

## 2. Environment and access

| | |
|---|---|
| devx API base | `https://ymzhvcxod0.execute-api.us-east-1.amazonaws.com/prod/` |
| dev API base | `https://4xe2tdq8z6.execute-api.us-east-1.amazonaws.com/prod/` |
| Region | `us-east-1` · Account `788159322332` |
| devx last deploy | 2026-08-01T09:12:51Z (this session, by hand) |
| dev last deploy | 2026-07-30T10:26Z (CI, pre-repoint — **never touched by this session**) |

`dev` is the control. It has carried v3.0.0 since 2026-07-27 and this session never deployed it.
Any finding reproducible on `dev` cannot have been caused by this session.

Both stacks self-register users through the API, so no credentials are needed — but see
`F-DEVX-2`: you must use the `id_token`, not the `access_token`.

Evidence files, all committed:

```
docs/evidence/wave3-32closeouta-devx-characterization-20260801T094608Z.md            (narrative)
                                                              ....json               (devx run)
                                                              ....confirm-run.json   (devx, application_id passed)
                                                              ....dev-control-run.json (dev control)
                                                              ....probe.py           (the probe)
```

---

## 3. The claims. Attack these.

Each is stated so it can be falsified, with the evidence behind it and an honest confidence level.

### CLAIM 1 — `F-DEVX-1`: cover letter and interview prep are unreachable because the VPR is written to one table and read from another. **Confidence: high on the mechanism, medium on completeness.**

The asserted mechanism:

```
_ARTIFACTS_ENV_CHAIN        = ('ARTIFACTS_TABLE_NAME', 'DYNAMODB_TABLE_NAME', 'TABLE_NAME')
_LEGACY_ARTIFACTS_ENV_CHAIN = (                        'DYNAMODB_TABLE_NAME', 'TABLE_NAME')
                                      table_registry.py:124-125
```

In `careervp-vpr-worker-lambda-devx`:
`ARTIFACTS_TABLE_NAME = careervp-artifacts-table-devx` but
`DYNAMODB_TABLE_NAME  = careervp-users-table-devx`.

So the **full** chain and the **legacy** chain resolve to *different physical tables inside the
same Lambda*. `save_vpr`/`get_vpr` use the legacy `pk`/`sk` key grammar
(`dynamo_dal_handler.py:306`, `:332`, `:355`). Of the 11 devx tables, the **only** one keyed
`pk`/`sk` is `careervp-users-table-devx`; the artifacts table is keyed `applicationId`/`artifactId`.

```
 WRITE  vpr-worker  ──save_vpr──▶  users-table   {pk: <app_id>, sk: ARTIFACT#VPR#v1}   SUCCEEDS
 READ   ip-api      ──get_vpr───▶  artifacts-table   Key('pk').eq(<app_id>)            cannot match
                                        └─ presumed ValidationException
                                             └─ swallowed: `except Exception: return None`
                                                (artifact_dependency_utils.py:41-45)
                                                  └─ resolver: "vpr missing" ──▶ 409
```

**Direct evidence:** for application `5ebd442d-41e7-4df6-a985-2b873ccea216`,
`careervp-users-table-devx` contains exactly one item at `pk=5ebd442d-…, sk=ARTIFACT#VPR#v1`;
`careervp-artifacts-table-devx` contains none.

**Attack it here:**
- The `ValidationException` is **inferred, never observed.** Pull the CloudWatch logs for
  `careervp-interview-prep-api-lambda-devx` around the probe runs and find out what actually
  happens. It may be something else entirely — an empty query result, an ownership check, a
  `_is_stale` rejection. `_is_stale` in particular is unexamined and could produce the same 409.
- Is `careervp-users-table-devx` genuinely the wrong destination, or is it the intended "core"
  table mid-migration and the *artifacts* table the newcomer? The prior session assumed the
  artifacts table is canonical. That assumption is load-bearing and unverified.
- Does this reproduce on **staging and prod**? Only dev and devx were checked. If the env wiring
  differs there, the blast radius is completely different and so is the urgency.

### CLAIM 2 — the CV-tailoring exception is explained by chain divergence, not by absence of the bug. **Confidence: medium. This is the weakest link.**

`cv_tailored` depends on `vpr` (`artifact_dependency_resolver.py:52-57`) and
`cv_tailoring_handler.py:349` calls the *same* `resolve_handler_dependencies`. Yet CV-tailoring
**succeeded** while cover letter and interview prep 409'd on the same VPR. If the bug were simply
"the read is broken", CV-tailoring should have failed too.

The offered explanation is that the two handlers resolve their table by different chains:

```
cv_tailoring_handler.py:347   table_registry.resolve_legacy_artifacts_table_name()   → legacy chain
interview_prep_submit_handler.py:135-144   table_name from _resolve_submit_preconditions  → ?
```

The prior session **did not finish tracing** `_resolve_submit_preconditions`, so the second half of
this explanation is unverified. **Trace it.** If both handlers in fact resolve the same table, this
claim collapses and CLAIM 1's mechanism needs rethinking.

### CLAIM 3 — `F-DEVX-2`: the live-API suites send the wrong token type. **Confidence: very high.**

`e2e_helpers.py:118` and `integration_helpers.py:152` both take `access_token` from the login
response. Controlled comparison, same user, same second: `access_token` → **401**,
`id_token` → **200**. Reproduced on both stacks.

**Attack it here:** is the *product* correct and only the tests wrong? Check what the real
frontend sends (`src/frontend`). If the frontend also sends the access token, this is a product
bug and far more serious than "stale tests".

### CLAIM 4 — `F-DEVX-3` / `F-DEVX-4`: the suites use stale request shapes and poll routes that don't exist. **Confidence: high on the facts, low on the interpretation.**

Facts: `/users/me/cv` needs `{cv_content,file_name}`; `/jobs` needs
`{title,company_name,description}` with a required, reachability-checked `url`;
`/company-research/fetch` needs `{job_id}`. All four artifact status routes are `/{id}/status`
and the bare `/{id}` GET does not exist (a bare `GET /vpr/{id}` returns `403 DEFAULT_4XX`, which
reads like an auth failure but is an unrouted method).

**Attack the interpretation:** "the tests are stale" and "there are two competing contracts" both
fit this evidence. Check the frontend and `contract/schemas/` before accepting the first reading.

### CLAIM 5 — `F-DEVX-5`: `/gap-analysis/questions` sits on the 29 s API Gateway ceiling. **Confidence: high.**

Observed: 27 965 ms (200), 29 222 ms (504), 29 257 ms (504), 29 218 ms (504), 28 238 ms (200) on
devx; **3 of 3 timeouts** on dev. When it 504s the chain silently empties and the failure surfaces
three wires later as `gap_response_ids must not be empty`.

### CLAIM 6 — `F-DEVX-6`: CV parse 500s when the extractor emits `WorkExperience.company = None`. **Confidence: low — observed once.**

`WorkExperience.company` is a required `str` and the docstring marks it IMMUTABLE. Seen once with
a CV that named no employer. May be model-dependent or flaky. **Reproduce before trusting.**

### CLAIM 7 — `F-DEVX-7`: `make deploy-devx` cannot deploy devx. **Confidence: very high.**

The target added in `a8ef789` omits `-c p26_rehome_features=true`, which scope-lock v2.6.0
requires; the flag is absent from `infra/cdk.json`, and `cdk` runs from `src/backend`, which has no
`cdk.json`. Without it, 76 P-26 resources synthesize into the parent stack with new logical ids and
CloudFormation aborts with 27 × "LogGroup … already exists" plus the CodeDeploy application. Synth
proof: **without** the flag 32 parent / 0 nested log groups; **with** it 2 parent / 30 nested,
logical ids matching the deployed stack. Implication: CI's `deploy-backend-dev` fails on every push
touching `src/backend/**` or `infra/**`.

---

## 4. What was NOT checked — gaps you should close

1. **CloudWatch logs. None. At all.** The single biggest gap. The original step prompt explicitly
   asked for worker logs and they were never pulled.
2. **Staging and prod env wiring.** Only dev and devx.
3. **What the frontend actually sends** on any wire. Everything about "stale tests" rests on
   comparing tests to backend models, with the real client never inspected.
4. **`_is_stale` and `_is_owned_by`** in the resolver — both can independently produce the same
   409 and neither was examined.
5. **Whether any of this is already known.** `ISSUES.md`, the D-H2/D-H4 specs and prior wave
   ledgers were not searched for these symptoms. Some may already have owners.
6. **Pre-existing data.** The users table holds VPRs under the legacy grammar. Nobody has counted
   them or decided what happens to them under a fix.
7. **Interview-prep worker path (F1).** Never exercised — the request never reached a 202, so the
   F1 finding neither reproduced nor was cleared.

---

## 5. Reproduction

```bash
cd "$(git rev-parse --show-toplevel)"

# the suites, as the step prompt specified (expect: 8 failed, 4 passed, 12 skipped -- all 401)
cd src/backend && API_BASE=https://ymzhvcxod0.execute-api.us-east-1.amazonaws.com/prod/ \
  uv run pytest tests/integration/test_full_pipeline_integration.py tests/e2e/ -v

# the probe that produced the baseline (walks the same wires with the id_token)
API_BASE=https://ymzhvcxod0.execute-api.us-east-1.amazonaws.com/prod/ STACK_LABEL=CareerVpCrudDevx \
  .venv/bin/python ../../docs/evidence/wave3-32closeouta-devx-characterization-20260801T094608Z.probe.py /tmp/out.json

# the env-var divergence at the heart of CLAIM 1
aws lambda get-function-configuration --function-name careervp-vpr-worker-lambda-devx \
  --region us-east-1 --query 'Environment.Variables.[ARTIFACTS_TABLE_NAME,DYNAMODB_TABLE_NAME]'

# every devx table's key schema
for t in $(aws dynamodb list-tables --region us-east-1 \
    --query "TableNames[?contains(@,'devx')]" --output text | tr '\t' '\n'); do
  printf "%-46s " "$t"
  aws dynamodb describe-table --table-name $t --region us-east-1 \
    --query 'Table.KeySchema[].AttributeName' --output text | tr '\t' '/'; echo
done

# F-DEVX-7: synth with and without the flag, compare log-group placement
ENVIRONMENT=devx npx cdk synth CareerVpCrudDevx --app "src/backend/.venv/bin/python infra/app.py" -q
ENVIRONMENT=devx npx cdk synth CareerVpCrudDevx --app "src/backend/.venv/bin/python infra/app.py" \
  -c p26_rehome_features=true -q
```

Note the probe creates real records in devx/dev. Both are pre-launch disposable per scope-lock
v2.6.0, but the AI calls cost money — a full run is ~2 minutes and several model invocations.

---

## 6. The prior session's remediation plan — **read this last, and only after forming your own**

Deliberately placed at the end so it does not anchor you. Skip it entirely if you'd rather stay
clean.

| # | Proposed fix | Size | Proposed owner |
|---|---|---|---|
| 2 | `access_token` → `id_token` in two helpers | 2 lines | free-standing |
| 4 | poll `/{id}/status` not `/{id}` | ~4 lines | free-standing |
| 3 | correct 3 payload shapes | ~15 lines | free-standing |
| 1a | stop swallowing schema errors in `get_artifact` | ~5 lines | D-H2/D-H4 |
| 1b | route VPR reads/writes through `TableRegistry`/`CoreRepository` on canonical keys | real work | D-H2/D-H4 |
| 7 | add `-c p26_rehome_features=true` to `deploy-devx` | 1 line | 3.4 (`infra/` lock) |
| 5 | make gap-analysis async (`202` + poll) | design | needs a human decision |
| 6 | handle `company=None` | ~5 lines | needs a human decision |

Its explicit warning: **do not "fix" 1b by repointing `DYNAMODB_TABLE_NAME`** — existing VPRs live
in the users table under the legacy grammar, so flipping the variable orphans them and relocates
the breakage rather than removing it.

**Say so if you think this plan is wrong, mis-ordered, or missing something.**

---

## 7. Constraints you must respect

These are repo rules, not preferences. `docs/db-redesign/code/code-analysis/project/runbooks/RUNBOOK-RULES.md`
is authoritative; `runbooks/wave-3-status.md` is the ledger and must be read before acting.

- **Do not edit either `project-scope-lock` twin** (`.yaml` / `.md`) — §0.3 write-protection, a
  human commits those.
- **Do not edit `src/backend/tests/unit/test_dh4_p01_canonical_artifact.py`** — pinned RED test.
- **`infra/` is 3.4's lock.** `F-DEVX-7`'s one-line fix lives there. Propose it; don't take it
  unilaterally.
- **Do not fix the interview-prep worker path** (3.5/D-H9) or **remove regeneration code**
  (3.6/D-H10). Both are owned and not yet authorized.
- Any commit touching a scope-locked surface needs a `Scope-Lock-Approved-By:` trailer, and
  `python3 scripts/ci/check_scope_lock_integrity.py --base origin/main --head HEAD` must return
  `OK` before merge.
- Mandatory pre-commit checks by changed path are in `CLAUDE.md`.

---

## 8. Lessons learned — traps this codebase and this environment actually set

Every one of these cost the prior session real time or nearly produced a wrong result.

**On the system:**

1. **A skipped suite reads exactly like a passing suite.** `4 passed, 20 skipped` is what
   `pytest` prints when `API_BASE` is unset and every meaningful test opts out. This is how two
   broken fixtures survived a full GREEN step. Always check *what ran*, not the exit code.
2. **`except Exception: return None` is how outages hide.** In
   `artifact_dependency_utils.py:41-45` it converts a hard schema mismatch into "upstream not
   ready yet". A mis-wired table becomes indistinguishable from a user who hasn't clicked
   Generate. Look for this pattern elsewhere before assuming the codebase is healthy.
3. **One env var can mean two tables in the same Lambda.** `DYNAMODB_TABLE_NAME` sits in both the
   full and legacy chains. 3.1-GREEN's ledger row predicted exactly this hazard and left it as
   recorded residue; it has now bitten. Never assume two call sites resolving "the artifacts
   table" reach the same table.
4. **A completed status does not mean a stored artifact.** The VPR reports `completed` from the
   jobs table while no canonical artifact exists. Status and storage are separate systems here.
5. **`GET` on an unrouted API Gateway path returns `403 DEFAULT_4XX`**, which looks like an
   authorization failure and is not. Check `aws apigateway get-resources` before debugging auth.
6. **A 504 three wires upstream surfaces as a validation error downstream.** The gap-analysis
   timeout presents as `gap_response_ids must not be empty` on a completely different endpoint.

**On the tooling:**

7. **`cmd > log 2>&1; echo "EXIT=$?"` reports the exit code of `echo`.** The prior session's first
   devx deploy "succeeded" with exit 0 while `make` had failed on a missing Docker daemon. Capture
   the real status.
8. **Never hand-write `allowed_origins`.** The prior session passed an invented value to
   `cdk deploy` and would have narrowed CORS on devx; it caught this and killed the run before any
   changeset executed, then re-ran reading the value from `infra/cdk.json` as the Makefile does.
9. **devx requires `-c p26_rehome_features=true`.** Without it you do not get a failed deploy, you
   get a *misleading* one — early-validation errors about resources "already existing".
10. **A ledger row cannot contain its own commit hash.** Land the row, then fix the hash in a
    following commit — and remember that commit moves the tip, so it needs the approval trailer
    too. The trailer mitigation decays on every subsequent commit; the real fix (making the
    integrity checker iterate the commit range) is round-1 defect **N2**, owned by **P-28**.
11. **Backticks inside `git commit -m` get shell-substituted.** Use `-F` with a file.
12. **P-23 canary deploys make devx slow.** `LambdaCanary10Percent5Minutes` across ~18 deployment
    groups; budget ~17 minutes and don't assume a stall is a hang.

---

## 9. What to deliver

1. **Your own diagnosis** of why cover letter and interview prep fail, derived independently.
   State where you agree with CLAIM 1, where you don't, and what you found that it missed.
2. **Your own remediation plan** — ordered, with sizes, owners, risks, and explicitly what you
   would *not* do.
3. **A verdict per claim** (1–7): CONFIRMED / PARTIALLY CONFIRMED / REFUTED / UNPROVEN, each with
   the evidence that decided it. `UNPROVEN` is a legitimate and useful verdict.
4. **Clarifying questions.** Ask them — do not guess and proceed. Likely candidates: is the
   artifacts table or the users table canonical; is prod affected; who owns `F-DEVX-1`; should the
   legacy-grammar VPRs already in the users table be migrated, abandoned, or dual-read.
5. **Issues to consider** that this handoff didn't raise. Assume there are some.

**Two things worth your scepticism above all:** the unobserved `ValidationException` in CLAIM 1,
and the half-traced CV-tailoring explanation in CLAIM 2. If either fails, the headline finding
needs rebuilding.
