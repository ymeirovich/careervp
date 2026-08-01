# Wave 3 — F-DEVX remediation run order and prompts

**Authored 2026-08-01.** The complete, ordered set. Step 4 lives in
`wave-3-corrective-slice-prompts.md`; every other step's prompt is here.

Kept separate from `wave-3-prompts.md` because that file has uncommitted user edits.

**Context for every step below:** prod will live in **the same AWS account** as dev/devx/staging.
No prod stack exists today, so nothing here is incident response — but every security and
isolation item is a **launch blocker**, and same-account prod makes step 5 materially more
serious than it first looked.

## How to actually run these

**These are eleven separate sessions, not one prompt.** Each `## Step` below contains exactly one
fenced ` ``` ` block. That block is a whole prompt for a whole session.

For each run, in order:

1. Find the run's row in the table below and note its **Claude** and **Codex** values.
2. Open a **fresh session** and set that model and effort **before** pasting anything. The model is
   a session setting; it cannot be changed by text inside the prompt.
3. Copy the fenced block — **only** the fenced block, not the `>` header above it — and paste it as
   the first message.
4. Let it finish. It will update `wave-3-status.md` as its last act.
5. Read that ledger row before starting the next run. If it recorded an open problem, resolve that
   first — every prompt's `STANDING CHECK` will stop on it anyway.

**Never run two steps in one session.** Beyond the model differing, rule 7 requires RED and GREEN to
be separate sessions, and a session that has already written implementation cannot credibly write
tests that fail first.

The `>` header above each block carries the run number, model pair, and rule-15/16 provenance. It is
metadata for you, not instructions for the agent — that is why it sits outside the fence.

**Run 5 is not a prompt.** It is a human decision on DP-A…DP-E, and run 6 cannot start without it.
**Run 8 is not a prompt either** — it is a human-gated destructive operation.

## Execution order

Model/effort is derived from **rule 18** (Claude tier) and **rule 16** (Codex tier), not chosen
freely. Copy the pair verbatim into each prompt header per rule 15.

| Run | Step id | Prompt lives in | Fixes | Claude | Codex |
|---:|---|---|---|---|---|
| 1 | `3.FIX-DEPLOY` | this file, Step 1 | F-DEVX-7 | `opus/medium` | `gpt-5.3-codex/medium` |
| 2 | `3.FIX-HARNESS` | this file, Step 2 | F-DEVX-2, -3, -4 | `opus/medium` | `gpt-5.3-codex/medium` |
| 3 | `3.FIX-SECURITY` | this file, Step 3 | F-DEVX-8, token log | `opus/high` | `gpt-5.3-codex/high` |
| 4 | `3.CORR-SPEC` | corrective-slice file §1 | F-DEVX-1 (pin) | `opus/high` | `gpt-5.3-codex/high` |
| 5 | **human decision** | — | DP-A…DP-E, esp. DP-D | — | — |
| 6 | `3.CORR-RED` | corrective-slice file §2 | F-DEVX-1 (tests) | `opus/high` | `gpt-5.3-codex/high` |
| 7 | `3.CORR-GREEN` | corrective-slice file §3 | F-DEVX-1 (impl) | **`fable/xhigh`** | `gpt-5.3-codex/xhigh` |
| 8 | `3.FIX-LEGACY-PURGE` | this file, Step 4b | the 89 legacy VPRs | **human-gated** | — |
| 9 | `3.FIX-ISOLATION` | this file, Step 5 | Codex §11 | `opus/high` | `gpt-5.3-codex/high` |
| 10 | `3.FIX-VERIFY` | this file, Step 6b | closing gate | `opus/high` | `gpt-5.3-codex/high` |
| — | `3.FIX-GAPASYNC` | decision-gated, Step 7 | F-DEVX-5 | `opus/high` → impl may be `fable/high` | `gpt-5.3-codex/high` |
| — | `3.FIX-NULLPOLICY` | decision-gated, Step 7 | F-DEVX-6 | `opus/medium` | `gpt-5.3-codex/medium` |
| 11 | resume Wave 3 | `wave-3-prompts.md` | — | as already recorded | as already recorded |

### Why these tiers — the routing is rule-driven, not taste

**Only run 7 goes to Fable.** Rule 18 routes to Fable when all three hold: implementation against
an already-pinned spec, long-horizon and multi-file, and a blast radius that justifies 2× cost.
`3.CORR-GREEN` is the textbook case — rule 18's own example of justifying blast radius is
*"key authority, data shape, irreversible deletion"*, which is precisely this step.

**Rule 18 forbids Fable everywhere else here, and the exclusions are explicit:**
- `3.CORR-RED` — *"RED steps. Never route to Fable."* Rule 14 already removed the judgment.
- `3.FIX-SECURITY` — *"Anything security-focused… the P-04/P-05 IDOR work."* Fable's cyber
  classifiers can decline outright, and its bug-finding gains **exclude** security analysis.
- `3.FIX-ISOLATION` — same clause: *"any auth or secrets slice."*
- `3.CORR-SPEC` — *"Steps whose real blocker is a human decision."* DP-D stops and asks.
- `3.FIX-DEPLOY`, `3.FIX-HARNESS` — census/recon and test repair; rule 18 calls paying 2× for
  mechanical completeness *"the exact waste rule 16 forbids."*
- `3.FIX-VERIFY` — *"GATE steps."*

**Two hard gates before writing `fable` into run 7** (rule 18): confirm the org has **30-day data
retention** — under ZDR every Fable request returns `400 invalid_request_error` regardless of
payload — and treat a **refusal as a normal outcome**, HTTP 200 with `stop_reason: "refusal"`, not
an error. If run 7 fails instantly with a 400 and the payload looks fine, check retention before
debugging anything else.

**Prompt shape for run 7** (rule 18): keep the standing check, rule-14 verification, rule-5 stops,
acceptance criteria, exact values, scope boundaries, full paths, the drift block and the ledger
update — all verbatim. Drop step-by-step implementation choreography. State goal, constraints and
acceptance criteria in one turn, then let it run; expect minutes per request.

**Codex slug — a deliberate divergence, flagged not hidden.** Every existing Wave-3 row reads
`gpt-5-codex`; these rows read `gpt-5.3-codex`. Rule 16's model table makes `gpt-5.3-codex` the
*"default for serious agentic coding"* and reserves `gpt-5-codex` for when the environment exposes
nothing newer — while also noting `gpt-5-codex` is *"this project's current pin"*. New rows take the
default; the older rows are **not** being retroactively renamed, because rule 16 says a change to an
already-authored pinned model goes through rule 8 rather than a find-and-replace. **If your
environment does not expose `gpt-5.3-codex`, drop these rows to `gpt-5-codex` at the same effort** —
that is the rule-16 fallback and needs no further approval.

**Codex tiers** follow rule 16's rubric — `medium` for a focused change across a few files,
`high` when it crosses module boundaries or can break production behavior, `xhigh` reserved for
data-model change. `3.FIX-SECURITY` is arguably `xhigh` on rule 16's *"auth/tenancy-sensitive"*
line; it is set to `high` because the fix itself is small and the breadth is in the audit. Raise it
if the handler sweep turns up many sites.

Steps 1–3 are small and unambiguous. Run 7 is the only substantial one.

---

## Step 1 — `3.FIX-DEPLOY`

> **Run:** 1 of 11 · **Step:** `3.FIX-DEPLOY` · **Fixes:** F-DEVX-7
> **Claude:** opus/medium · **Codex:** gpt-5.3-codex/medium
> (rule 15/16 — derived in this file's routing table. Rule 18 excludes Fable: synth census plus a human-decision raise.)
> **ONE SESSION, THIS PROMPT ONLY.** Set the model above *before* pasting the fenced
> block below. Do not chain this with another step in the same session.

```
You are running step 3.FIX-DEPLOY of Wave 3. Repo root:
/Users/yitzchak.meirovich/Documents/code5/careervp — anchor every shell block on
cd "$(git rev-parse --show-toplevel)".

STANDING CHECK: read runbooks/wave-3-status.md and
docs/evidence/wave3-32closeouta-devx-characterization-20260801T094608Z.md §5.7.

PROBLEM. src/backend/Makefile's deploy-devx target omits -c p26_rehome_features=true.
Scope-lock v2.6.0 requires devx to be built with it from first creation; it is absent
from infra/cdk.json, and cdk runs from src/backend, which has no cdk.json. Without the
flag, 76 P-26 resources synthesize into the PARENT stack with new logical ids and
CloudFormation aborts with 27 "LogGroup already exists" errors plus the CodeDeploy
application. Verified synth counts: without the flag 491 parent resources / 32 parent log
groups / 0 nested; with it 261 / 2 / 30. The DEPLOYED devx parent is 261 — it matches the
flagged synth. .github/workflows/db-redesign-checks.yml calls make deploy-devx, so CI
fails on every push touching src/backend/** or infra/**.

OWNERSHIP: infra/ is 3.4's lock. This is a one-line correction to a target that is
currently broken and blocking every other step. Record the cross-owner decision explicitly
in your ledger row (rule 5) rather than annexing infra/ silently. If you judge the lock
must not be crossed, STOP and say so — that is a legitimate outcome.

DO, IN THIS ORDER:
1. Reproduce the synth divergence yourself, both ways, and record the resource/log-group
   counts. Confirm against the deployed devx parent count.
2. Add --context "p26_rehome_features=true" to deploy-devx in src/backend/Makefile.
   Change nothing else in that file. Verify with make -n that deploy-devx now carries it
   and that `deploy` (used by seven workflows) is untouched.
3. Add a NON-DEPLOYING regression test asserting the devx synth's nested placement — the
   CrudFeatures nested stack holds the feature log groups and the parent does not. Assert
   on synthesized structure, not on a command string.
4. Run BOTH naming validators:
     python src/backend/scripts/validate_naming.py --path infra --verbose
     python src/backend/scripts/validate_naming.py --path infra --strict
   and the infra test suites.
5. RAISE, DO NOT RESOLVE, the governance conflict: db-redesign-checks.yml executes
   make deploy-devx (create+execute, --require-approval=never) while the Makefile's own
   P-28 comment forbids that from automation, and deploy.yml implements the compliant
   change-set + human-gated-execute shape. Ask whether devx is an intentional P-28
   exception. Do not silently settle it.

DO NOT: deploy in this step; reshape api_construct.py or anything else under infra/;
edit either project-scope-lock twin; touch application code or tests outside the new
topology guard.

OUTPUT REQUIRED: the synth comparison numbers; make -n output for both targets; the new
guard proven able to fail; both naming validators' exit codes; the governance question
stated for a human.

ALSO REQUIRED (runbooks/RUNBOOK-RULES.md): compare what you built against this prompt and
the matching scope-lock clause. If anything drifted, STOP, write one plain-English
sentence a non-engineer could follow, then the technical detail, and flag it for human
review. Update wave-3-status.md with a plain-English row, the commit, today's date, and
what the next step must resolve first (or "none").
```

---

## Step 2 — `3.FIX-HARNESS`

> **Run:** 2 of 11 · **Step:** `3.FIX-HARNESS` · **Fixes:** F-DEVX-2, F-DEVX-3, F-DEVX-4
> **Claude:** opus/medium · **Codex:** gpt-5.3-codex/medium
> (rule 15/16 — derived in this file's routing table. Rule 18 excludes Fable: test repair and recon, low blast radius.)
> **ONE SESSION, THIS PROMPT ONLY.** Set the model above *before* pasting the fenced
> block below. Do not chain this with another step in the same session.

```
You are running step 3.FIX-HARNESS of Wave 3. Repo root as above.

STANDING CHECK: read wave-3-status.md. If 3.FIX-DEPLOY left anything open, resolve it
first. Read docs/evidence/wave3-32closeouta-devx-characterization-20260801T094608Z.md
§§5.2-5.4 in full.

PROBLEM. The live-API suites have been incapable of testing anything for a long time, and
their failure is invisible because they skip when API_BASE is unset — pytest prints
"4 passed, 20 skipped" and reads as healthy. With API_BASE set they produce
"8 failed, 4 passed, 12 skipped", every failure a 401 at the first authenticated wire.
Three independent causes:
  (a) F-DEVX-2 — both helpers send the Cognito access_token; the authorizer accepts the id_token.
      integration_helpers.py:152, e2e_helpers.py:118. The FRONTEND IS CORRECT
      (src/frontend/lib/auth.ts:84-94 uses getIdToken), so this is a test defect only.
  (b) F-DEVX-3 — stale request shapes: /users/me/cv, /jobs, /company-research/fetch.
  (c) F-DEVX-4 — all four artifact polls target bare /{id}; only /{id}/status exists. A bare GET
      returns 403 DEFAULT_4XX, which looks like auth failure and is an unrouted method.

THIS STEP CHANGES TEST CODE ONLY. No file under src/backend/careervp/, src/frontend/ or
infra/ may change.

DO, IN THIS ORDER:
1. Use the id_token for product API requests in both helpers. Keep access_token only
   where a Cognito/OAuth endpoint specifically requires it; say which, if any.
2. Add a token-use regression test that decodes the claim and asserts token_use == 'id'
   for the API credential. NEVER log, assert on, or write a token value into evidence.
3. Correct the payload shapes to the CANONICAL ones the frontend uses — not the
   transitional aliases. Note that job_handler aliases `company`->`company_name` and
   cv_upload_handler accepts a legacy shape; using those would only prove the aliases
   still work. Check src/frontend/api/methods.ts for what the real client sends.
4. Poll /{id}/status for vpr, cv-tailoring, cover-letter and interview-prep.
5. Harden test_e2e_contract_gate_validation.py. It is not a gate while it accepts 401 for
   authenticated cases and tolerates stale routes. Replace broad expected-status sets like
   {200,401,404} with assertions that distinguish authenticated happy path, explicit
   validation failure, explicit not-found, a deliberate unauthorized negative, and an
   unrouted API Gateway response — the last must FAIL the gate.
6. Run the suites against devx and quote the real output.

EXPECTED OUTCOME — READ THIS BEFORE YOU PANIC. The suites will STILL FAIL, further along,
at cover-letter and interview-prep with HTTP 409 upstream_required. That is CORRECT. It is
F-DEVX-1, it is owned by step 3.CORR, and it is not yours to fix. Your success criterion
is that authentication and every wire up to and including VPR now pass, and that the
remaining failure is the legible 409 rather than an opaque 401. Do not chase the 409.

DO NOT: weaken or delete any assertion; touch product code; edit either scope-lock twin;
edit test_dh4_p01_canonical_artifact.py; fix F-DEVX-1, -5, -6 or -8.

OUTPUT REQUIRED: the suite output before and after, quoted, with an explicit statement of
what now passes, what still fails and why, and what skips. Proof no product file changed
(git status --porcelain over src/backend/careervp/ src/frontend/ infra/ empty). Ruff and
strict mypy clean.

ALSO REQUIRED: the standing drift comparison and the wave-3-status.md row, as in step 1.
```

---

## Step 3 — `3.FIX-SECURITY`

> **Run:** 3 of 11 · **Step:** `3.FIX-SECURITY` · **Fixes:** F-DEVX-8 (IDOR), bearer-token logging
> **Claude:** opus/high · **Codex:** gpt-5.3-codex/high
> (rule 15/16 — derived in this file's routing table. Rule 18 FORBIDS Fable outright — "anything security-focused… the P-04/P-05 IDOR work".)
> **ONE SESSION, THIS PROMPT ONLY.** Set the model above *before* pasting the fenced
> block below. Do not chain this with another step in the same session.

```
You are running step 3.FIX-SECURITY of Wave 3. Repo root as above.

STANDING CHECK: read wave-3-status.md and
docs/evidence/wave3-32closeouta-devx-characterization-20260801T094608Z.md §5.8.

PROD WILL LIVE IN THIS SAME AWS ACCOUNT. No prod stack exists yet, so this is not incident
response — but both items below are launch blockers and must land before prod exists.

PROBLEM 1 — cross-tenant write (IDOR) on POST /users/me/cv.
cv_upload_handler._normalize_request_payload injects the authorizer's user_id ONLY for the
{cv_content,file_name} shape. The legacy branch returns the body unchanged, so user_id is
whatever the caller sent, and it flows into the S3 key (cv_upload_handler.py:129) and the
stored record (:155) with nothing reconciling it against the token. Reproduced live on
devx: authenticated as 54683458-d001-7083-33b8-8d185d5d3a34, a body carrying
user_id 00000000-dead-beef-0000-000000000001 returned HTTP 201 and stored the CV under
that foreign identity.

PROBLEM 2 — bearer token written to CloudWatch.
interview_prep_submit_handler.py:100-105 logs api_gateway_event=event, which includes
headers.Authorization, the request body, identity/network metadata and authorizer claims.
A live bearer ID token was observed in the log. NEVER copy an observed token into an
issue, test, commit, or evidence file.

DO, IN THIS ORDER:
1. Reproduce both yourself before changing anything. For the IDOR use a UUID belonging to
   NO real account, so the test proves absent validation without touching a real user.
2. Fix the IDOR: derive user_id from the authorizer on EVERY path. CVParseRequest must not
   accept a client-supplied user_id on this route at all. Do not merely add a mismatch
   check on one branch — remove the ability to assert identity from the body.
3. Add a regression test: a body user_id differing from the token is ignored or rejected,
   never honoured. Assert on the STORED record's owner, not just the response.
4. AUDIT EVERY OTHER HANDLER for the same body-supplied-identity pattern and report what
   you find. Fix only what is the same defect; flag anything ambiguous.
5. Fix the logging: remove api_gateway_event=event. Log only allow-listed scalars such as
   endpoint and request id. If body observability is needed, log field names or a
   pre-redacted structure.
6. Add a unit test using a sentinel token and a sensitive body field, asserting neither
   appears in captured log calls or output.
7. AUDIT EVERY HANDLER for whole-event logging and report.
8. Deploy to devx and verify LIVE that the IDOR is closed — the same request must no
   longer store under a foreign identity.
9. CLEAN UP the probe record planted during characterization:
   careervp-cvs-table-devx, userId 00000000-dead-beef-0000-000000000001,
   cvId 4d877e8e-0db8-428f-a98f-09c70cb08e52. Confirm deletion.
10. Assess CloudWatch access and remaining validity of any token already logged. Retention
    is one day; retention is not redaction.

DO NOT: fix F-DEVX-1 or the 409; edit either scope-lock twin; edit
test_dh4_p01_canonical_artifact.py; put a real token anywhere.

OUTPUT REQUIRED: both reproductions before the fix and both re-tests after, live; the two
audits with their findings; confirmation the planted record is gone; full check battery.

ALSO REQUIRED: the standing drift comparison and the wave-3-status.md row.
```

---

## Step 4 — `3.CORR-SPEC` → `3.CORR-RED` → `3.CORR-GREEN`

See **`wave-3-corrective-slice-prompts.md`**. Fixes F-DEVX-1 and closes the D-H4 clause.
Its `STANDING CHECK` requires steps 1 and 2 to be done first.

---

## Step 4b — `3.FIX-LEGACY-PURGE` (run 8) — **human-gated, destructive**

This is **Codex's Step 7** and it had no execution step until now. It is not an agent task.

**Preconditions, all required:** `3.CORR-GREEN` has landed and a fresh journey writes a canonical
VPR; `DP-D` was answered **in writing** by a human; a successor evidence file exists.

**What exists.** Legacy `pk`/`sk` VPRs written by the old worker path, none of which any canonical
reader can see:

| Environment | Legacy VPRs in the users table | Canonical VPRs |
|---|---:|---:|
| devx | 4 | 0 |
| dev | **83** | 0 |
| staging | 2 | 0 |

**Why this is not automatic.** Scope-lock v2.7.0 says stored data is disposable and forbids
migration, backfill and dual-read — so the *code* must not learn to read these. That is not the
same as authorization to delete 83 records that may be somebody's working state. **Deletion is a
human action on a human decision.** An agent may prepare and verify; it may not delete.

**Sequence:** confirm the canonical path works in devx first → purge devx (4) → re-run a fresh
journey → only then consider dev and staging, each separately authorized. Do not purge all three in
one pass. Record counts before and after. If `DP-D` chose *leave orphaned*, record that instead and
close the step — orphaned records are inert once nothing reads `pk`/`sk`.

**Also purge here:** the IDOR probe record planted during characterization —
`careervp-cvs-table-devx`, `userId 00000000-dead-beef-0000-000000000001`,
`cvId 4d877e8e-0db8-428f-a98f-09c70cb08e52` — if `3.FIX-SECURITY` did not already remove it.

---

## Step 5 — `3.FIX-ISOLATION`

> **Run:** 9 of 11 · **Step:** `3.FIX-ISOLATION` · **Fixes:** Codex §11 cross-environment subscription lookup
> **Claude:** opus/high · **Codex:** gpt-5.3-codex/high
> (rule 15/16 — derived in this file's routing table. Rule 18 FORBIDS Fable — "any auth or secrets slice"; also an ownership decision.)
> **ONE SESSION, THIS PROMPT ONLY.** Set the model above *before* pasting the fenced
> block below. Do not chain this with another step in the same session.

```
You are running step 3.FIX-ISOLATION of Wave 3. Repo root as above.

STANDING CHECK: read wave-3-status.md and §11 of
docs/db-redesign/code/code-analysis/redesign/prompts/f-devx-codex-validation-implementation-handoff.md.

PROBLEM. SubscriptionRepository resolves its users table from TABLE_NAME and then a
NamingUtils fallback (subscription_repository.py:70-80). The devx gap Lambda supplies
USERS_TABLE_NAME but not TABLE_NAME, so the repository addresses careervp-users-table-DEV
from devx. Live devx log:
  AccessDeniedException ... not authorized to perform dynamodb:GetItem on
  arn:aws:dynamodb:us-east-1:788159322332:table/careervp-users-table-dev
QuotaService (quota_service.py:49-72) treats a failed lookup as sub=None and falls through
to trial enforcement, so a paid user can be treated as a trial user.

WHY THIS IS MORE SERIOUS THAN IT LOOKS: prod will live in THIS SAME ACCOUNT. Today the only
thing preventing a cross-environment read is an IAM denial — an accident, not a design.
Once prod is in the account, that same fallback has prod on the other side of it.

OWNERSHIP: this is Wave-6 auth/trial territory. Either pull it forward with an explicit
written ownership record, or report it to that owner as a launch blocker and STOP. Do not
pull it forward silently.

DO, IN THIS ORDER:
1. Reproduce the cross-environment addressing and quote the log.
2. Inject the environment's USERS_TABLE_NAME explicitly from the handler/composition root.
   Prefer explicit dependency injection over adding another broad fallback chain — another
   implicit chain is what caused F-DEVX-1.
3. Distinguish "no subscription row" from "subscription lookup failed". A DynamoDB failure
   must surface as an infrastructure/service-unavailable result and must never silently
   become trial mode.
4. Add tests proving no repository addresses another environment's table, for dev, devx and
   staging names.
5. Add a paid-user test proving a repository error can neither consume trial credit nor
   block an active subscriber as an expired trial.
6. SWEEP for the same pattern: any repository resolving a table through an implicit
   fallback rather than an injected name. Report what you find; fix only identical defects.

DO NOT: edit either scope-lock twin; change trial or billing business rules; widen scope
into Wave-6's other auth work.

OUTPUT REQUIRED: the reproduction; the ownership record or the STOP; the sweep results;
full check battery.

ALSO REQUIRED: the standing drift comparison and the wave-3-status.md row.
```

---

## Step 6b — `3.FIX-VERIFY` (run 10) — the closing gate

> **Run:** 10 of 11 · **Step:** `3.FIX-VERIFY` · **Fixes:** nothing — it is a gate
> **Claude:** opus/high · **Codex:** gpt-5.3-codex/high
> (rule 15/16 — derived in this file's routing table. Rule 18 excludes Fable — "GATE steps" are named.)
> **ONE SESSION, THIS PROMPT ONLY.** Set the model above *before* pasting the fenced
> block below. Do not chain this with another step in the same session.

```
You are running step 3.FIX-VERIFY of Wave 3. Repo root:
/Users/yitzchak.meirovich/Documents/code5/careervp — anchor every shell block on
cd "$(git rev-parse --show-toplevel)".

This is a GATE. You read evidence and check it against a contract. You fix NOTHING. If
something fails, you record it and stop; you do not repair it.

STANDING CHECK: read wave-3-status.md and confirm runs 1-9 are recorded as done.

DO: re-run the full live characterization against CareerVpCrudDevx, resolving the API base
live from the stack's RawApiInvokeUrl output, and check each line below. Quote real output
for every one. Mark each PASS / FAIL / DEFERRED.

  1.  A fresh journey writes a canonical VPR artifact and NO legacy users-table VPR.
  2.  The hub's vpr artifact id resolves to that exact canonical record.
  3.  Cover-letter submit returns 202 for the owned VPR, and its worker receives real
      VPR content -- not an id-only stub.
  4.  Interview-prep submit returns 202, same content check.
  5.  CV-tailoring resolves through the same canonical authority.
  6.  Wrong-owner access is still forbidden, with the pinned envelope.
  7.  A DynamoDB schema failure surfaces explicitly and never as 409/missing.
  8.  POST /users/me/cv ignores or rejects a body-supplied user_id; verify against the
      STORED record's owner, not just the response.
  9.  No handler logs an authorization token or a whole API Gateway event.
  10. No environment addresses another environment's tables.
  11. The live-API helpers use the id_token and current /{id}/status routes.
  12. The devx synth matches the deployed P-26 nested topology.
  13. The interview-prep contract still refuses missing identity with the exact
      AC-P01-1 envelope -- confirm 3.CORR did not regress 3.2-GREEN's work.
  14. Ruff, mypy --strict, the full backend suite, coverage with the core-branch ratchet
      held, oracle + route parity, infra suite, both naming validators, and
      check_scope_lock_integrity.py --base origin/main --head HEAD.

EXPECTED DEFERRALS -- these are NOT failures of this gate, and must be recorded as open
with their owners rather than silently passed:
  - F-DEVX-5 (gap-analysis on the 29s API Gateway ceiling) -- awaiting a contract decision.
  - F-DEVX-6 (extractor nulls -> HTTP 500) -- awaiting a policy decision.

DO: diff wire-by-wire against
docs/evidence/wave3-32closeouta-devx-characterization-20260801T094608Z.md and call out
every change, expected or not. Write a dated successor evidence file.

DO: state plainly whether D-H4's contract+integration and P-01's e2e+characterization can
NOW be claimed. If yes, say so explicitly so a human can close the clauses. If no, name
exactly what is missing.

DO NOT: fix anything; edit either scope-lock twin; edit
test_dh4_p01_canonical_artifact.py; mark a deferred item closed.

OUTPUT REQUIRED: the 14-line checklist with PASS/FAIL/DEFERRED and quoted evidence; the
baseline diff; the clause-closure statement; the evidence file path.

ALSO REQUIRED: the standing drift comparison and the wave-3-status.md row.
```

---

## Step 7 — decision-gated, non-blocking

Both need a **human product decision before a prompt can be written**. Neither blocks
anything else. Write the prompt once the decision is recorded in a spec or amendment.

### `3.FIX-GAPASYNC` — F-DEVX-5

`POST /gap-analysis/questions` sits on the 29 s API Gateway ceiling: observed 3 timeouts in
5 calls on devx, 3 of 3 on dev. CloudWatch shows a Lambda invocation completing at
`durationMs=29853` — **after** API Gateway already returned 504. So work completes and
persists while the client believes it failed, trial usage is charged before the LLM call,
and the user sees `gap_response_ids must not be empty` three wires later.

**Decision required:** authorize changing the public contract from synchronous `200` to
`202` + poll. Cannot be fixed by raising the Lambda timeout (29 s is the API Gateway hard
cap), and must not be fixed by backgrounding work after the response returns.

Once authorized, the prompt must require: durable state; idempotency per
user/application/request; exactly-once trial attribution under retry and worker
redelivery; failures surfacing on the question resource rather than on VPR; and a frontend
flow that does not advance until questions are retrieved.

### `3.FIX-NULLPOLICY` — F-DEVX-6

`company=exp.get('company', 'Unknown')` does not apply the default when the key exists with
an explicit `null`, so a null employer fails `WorkExperience` validation, `parse_cv` catches
it generically, and the handler returns HTTP 500. The same family affects role, institution
and degree.

**Decision required — pick one:**
1. Structured `422` requiring correction (recommended; launch-safe).
2. Make selected immutable fields optional — needs a full downstream audit of every model,
   prompt builder, validator, sorter, exporter and `.lower()` call.
3. An explicit employer-less work classification supported by model and UI.

**Do not** fix with `exp.get('company') or 'Unknown'`. Company and role are immutable facts
and inventing a placeholder violates the repository's fact-verification rules.

---

## Step 8 — resume Wave 3

Order: `3.2-CLOSEOUT-B` → `3.6-SPEC/RED/GREEN` → `3.4` → `3.5`.

**`3.6` needs amending before it runs.** `wave-3-prompts.md:2559` instructs `3.6-GREEN` to
re-run the characterization and diff it against the baseline from `3.2-CLOSEOUT-A`. That
baseline records a chain in which cover letter and interview prep never generate, so the
diff cannot measure what `3.6` intends. After step 4, `3.CORR-GREEN` writes a successor
evidence file; **repoint `3.6-GREEN` at that file** and re-check `3.6-SPEC`'s DP-1, which
asks whether every regenerable artifact type has a reachable inline edit path — a question
whose answer changes once the chain actually runs.

**Also add to `RUNBOOK-RULES.md`:** a step whose scope-lock verification mode is `e2e` or
`integration` may not be marked done on a skipped suite. `4 passed, 20 skipped` must be a
hard stop. That rule would have caught this three steps earlier.
