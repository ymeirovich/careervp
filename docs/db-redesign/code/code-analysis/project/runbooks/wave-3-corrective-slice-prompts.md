# Wave 3 — corrective slice prompts (F-DEVX-1 canonical VPR persistence)

**Authored 2026-08-01.** Fold into `wave-3-prompts.md` when convenient — kept separate because that
file has uncommitted user edits.

**Step ids:** `3.CORR-SPEC` → `3.CORR-RED` → `3.CORR-GREEN`.

**Governance decision recorded here (see §0):** this is a **new step**, not a reopening of D-H4/3.2.
`3.2-GREEN` stays GREEN. The **clause** `D-H4` stays open until `3.CORR-GREEN` lands.

---

## §0 — Why a new step and not a reopened D-H4

`D-H4`'s verification mode is `contract+integration`. `3.2-GREEN` discharged the **contract** half
and said so, in its own ledger row, at the time:

> *"UNDEPLOYED DEBT (§0.5): nothing was deployed to `CareerVpCrudDevx` … D-H4 verifies
> `contract+integration` … so the unit/integration suite does NOT discharge either clause."*

That row was honest. The debt was recorded when it was incurred and has now come due.
`3.2-CLOSEOUT-A` proved the contract half works live (`HTTP 400 application_id/job_id is required`,
exactly as `AC-P01-1` pins) and proved the integration half does not.

Reopening `3.2` would therefore **contradict a row that was already correct**, and would re-litigate
a human-approved v3.0.0 contract amendment that is not in question. It would also not help: the
corrective work spans `D-H2` (key authority), `D-H4` (canonical artifact) and DAL internals owned by
`3.5` — a scope no single existing step can carry.

**Practical difference, in one line each:**
- *Reopen D-H4* = "3.2 was never done." Flips a GREEN row to open, muddies every downstream step
  that treated 3.2 as complete, and needs no new spec because the old one nominally covers it.
- *New step* = "3.2 did its half and logged the rest as debt; this step pays the debt." Keeps the
  audit trail, and can hold a scope that crosses three owners plus findings that belong to no
  existing clause at all.

**Chosen: new step.** `D-H4` may not be marked done until `3.CORR-GREEN` closes.

---

## §1 — `3.CORR-SPEC`

```
You are running step 3.CORR-SPEC of Wave 3 in the CareerVP redesign. Repo root:
/Users/yitzchak.meirovich/Documents/code5/careervp — anchor every shell block on
cd "$(git rev-parse --show-toplevel)".

STANDING CHECK — before anything else: read
docs/db-redesign/code/code-analysis/project/runbooks/wave-3-status.md, then
docs/evidence/wave3-32closeouta-devx-characterization-20260801T094608Z.md and
docs/db-redesign/code/code-analysis/redesign/prompts/f-devx-codex-validation-implementation-handoff.md
in full. Confirm with a real command that 3.CORR's prerequisites are met right now:
F-DEVX-7 is fixed (make deploy-devx carries -c p26_rehome_features=true) and the
live-API helpers use the id_token. If either is not true, STOP and say so plainly —
without them you cannot deploy or verify anything you build here.

YOU ARE WRITING NO TESTS AND NO IMPLEMENTATION IN THIS STEP. You are pinning a spec
so that 3.CORR-RED can be written against exact values (rule 14).

CONTEXT. A completed VPR is written to the legacy users table under pk/sk by the VPR
worker, and read from the canonical artifacts table under a pk/sk query by the
cover-letter and interview-prep submit handlers. The artifacts table is keyed
applicationId/artifactId, so the read raises
  ValidationException: Query condition missed key schema element: applicationId
which get_latest_vpr converts to a failed Result, which
DynamoArtifactDependencyRepos.get_artifact converts to None, which the resolver
reports as a missing upstream, which surfaces as HTTP 409 upstream_required. Two of
six V1 features cannot be produced. Live VPR counts: devx 4 legacy / 0 canonical,
dev 83 / 0, staging 2 / 0.

DO, IN THIS ORDER:

1. RE-VERIFY THE MECHANISM YOURSELF. Do not take the above on trust. Confirm live: the
   env split on the VPR worker vs the submit lambdas; the key schema of every table you
   touch; the CloudWatch ValidationException; and that a completed VPR lands in the
   users table and not the artifacts table. Record what you confirmed and anything that
   does not match.

2. SETTLE FIVE DECISION POINTS. Each needs a written answer with its reasoning. Where a
   decision is a human's, STOP and ask rather than choosing.
   - DP-A CANONICAL VPR REPRESENTATION. Bounded full payload in DynamoDB, or canonical
     metadata plus a stable S3 bucket/key that an owned repository read hydrates and
     validates? Resolve against the real payload sizes you measure, not an estimate.
     A presigned result_url is NEVER the durable locator.
   - DP-B CANONICAL ARTIFACT ID. Reuse the existing VPR job id, or mint a new opaque id?
     The hub already stores a vpr artifact id — check what it holds today before choosing.
     Whichever you pick, one id must be shared by the hub, the jobs status record and the
     canonical artifact.
   - DP-C ERROR CLASSIFICATION. A key-schema failure must not read as a missing
     dependency. D-H3 already established TABLE_SCHEMA_MISMATCH for exactly this shape —
     confirm it applies and pin the code, or pin a different explicit infrastructure code.
     Pin what the resolver does with it and what HTTP status the handler returns.
   - DP-D LEGACY RECORDS. 89 legacy-grammar VPRs exist across three environments (83 in
     dev). Scope-lock v2.7.0 calls stored data disposable, so no migration or backfill —
     but 83 records is somebody's working state. This is a HUMAN decision: delete and
     re-run, or leave orphaned. Do not infer authorization from the clause. STOP and ask.
   - DP-E OWNERSHIP OF THE DAL EDIT. save_vpr / get_vpr / get_latest_vpr are DAL
     internals that 3.5 owns as residue. This slice must change them. Record the
     cross-owner decision explicitly rather than annexing them silently (rule 5).

3. PIN THE CANONICAL INVARIANT with exact values, in
   docs/db-redesign/code/code-analysis/project/specs/ — either as a new spec file or an
   amendment to D-H4-P-01-canonical-artifact-spec.md; say which and why. It must state,
   at minimum: the exact key shape of the canonical VPR record; the exact artifact type
   value the table's type-index requires; the owner field CoreRepository reads; that
   ApplicationRepository stores the same opaque id in artifact_statuses.vpr_artifact_id;
   that CoreRepository.get_vpr_by_artifact_id returns the real payload and never an
   id-only stub; that a wrong owner returns FORBIDDEN and a genuinely absent artifact
   returns successful None; and that the worker does not mark the job or hub completed
   until the canonical write succeeds.

4. PIN THE JOBS-REPOSITORY TRAP AS A NAMED HAZARD. core_repository.py:173-200
   (_get_vpr_job) reads job.get('result'). Deployed jobs carry result_key and result_url
   and NO inline result, so it returns {artifact_id, application_id, user_id} — a
   non-empty dict that looks like success and contains no VPR. Routing submit handlers
   through CoreRepository without fixing this trades a visible 409 for silently empty AI
   context. The spec must require a test that fails if a worker receives a stub.

5. WRITE THE AFFECTED-EXISTING-TESTS INVENTORY (rule 14, and the defect behind two §0.3
   amendments). Enumerate every existing test that will change behaviour, by node id.
   Start from: test_vpr_dal.py, test_artifact_dependency_utils.py,
   test_artifact_dependency_resolver.py, test_cv_tailoring_vpr.py,
   test_l1_artifact_persistence.py, test_artifact_id_characterization.py,
   test_table_registry_characterization.py. Verify by running them, not by reading.

DO NOT: write tests or implementation; edit either project-scope-lock twin; edit
src/backend/tests/unit/test_dh4_p01_canonical_artifact.py; edit infra/; repoint
DYNAMODB_TABLE_NAME as a shortcut; introduce a dual-write, dual-read, migration,
backfill or compatibility reader (scope-lock v2.7.0 forbids all of them).

OUTPUT REQUIRED: what you re-verified and anything that contradicted the brief; the five
decision points with answers or an explicit STOP; the path of the spec you pinned; the
affected-existing-tests inventory with live evidence; any new defect found, flagged not
fixed.

ALSO REQUIRED (see runbooks/RUNBOOK-RULES.md): compare what you built against this
prompt and the matching scope-lock clauses; if anything drifted, STOP, write one
plain-English sentence a non-engineer could follow, then the technical detail, and flag
it for human review. Update wave-3-status.md with a plain-English row, the commit,
today's date, and what the next step must resolve first (or "none").
```

---

## §2 — `3.CORR-RED`

```
You are running step 3.CORR-RED of Wave 3. Repo root as above.

STANDING CHECK: read wave-3-status.md. If 3.CORR-SPEC left anything open — especially
DP-D (the 89 legacy records) — resolve it FIRST. Then confirm with a real command that
the spec 3.CORR-SPEC pinned exists, carries an "Affected existing tests (inventory)"
section, and states exact assertion values. If not, STOP (rule 14).

Write ONLY tests. No implementation file may change. Every test must fail for the reason
its acceptance criterion names, not on a collection error, an import error or a skip —
catch missing APIs inside the test and fail with an explicit AC-owned message.

WRITE THESE, each against the REAL table key schemas under moto (users pk/sk, artifacts
applicationId/artifactId, jobs job_id, applications userId/applicationId, plus S3 if
DP-A chose a key-based representation):

1. The VPR worker writes a canonical VPR item to the artifacts table at the exact key
   shape the spec pins.
2. The VPR worker writes NO VPR-shaped item to the users table.
3. Worker completion fails or retries if the canonical artifact write fails — the job and
   hub must not report completed over a missing artifact.
4. The hub's artifact_statuses.vpr_artifact_id and the canonical artifact carry the SAME
   opaque id.
5. Cover-letter submit returns 202 for an owned, completed canonical VPR.
6. Interview-prep submit returns 202 for the same.
7. A wrong-owner VPR returns the pinned public forbidden envelope.
8. A DynamoDB ValidationException surfaces as the code DP-C pinned and NEVER as
   409/upstream_required.
9. THE STUB TEST — given a completed VPR job carrying result_key and no inline result,
   plus a canonical artifact owned by the user, the cover-letter worker's prompt input
   contains real VPR sections/differentiators and not merely artifact_id/application_id/
   user_id. Repeat for interview-prep.
10. CV-tailoring resolves the same canonical VPR rather than the users-table copy.
11. The repository never treats result_url as the durable locator.

Mocking resolve_handler_dependencies to return ready is INSUFFICIENT for 5, 6 and 9 —
at least those must execute real repository calls against moto.

DO NOT: touch any implementation file; edit test_dh4_p01_canonical_artifact.py; edit
either scope-lock twin; edit infra/; weaken or delete an existing assertion. If an
existing test must change, that is a reconciliation needing human approval and a spec
inventory entry — raise it, do not perform it.

OUTPUT REQUIRED: each test's node id and its verbatim intended failure; proof no
implementation file changed (git status --porcelain over src/backend/careervp/,
src/frontend/, infra/ must be empty); ruff + strict mypy clean on new files; the
unchanged ratchets (dh2/dh3/dh4/p01, dh7) still passing.

ALSO REQUIRED: the standing drift comparison and the wave-3-status.md row, as in
3.CORR-SPEC.
```

---

## §3 — `3.CORR-GREEN`

```
You are running step 3.CORR-GREEN of Wave 3. Repo root as above.

STANDING CHECK: read wave-3-status.md and resolve anything 3.CORR-RED left open. Confirm
with a real command that the 3.CORR-RED tests exist and fail for their stated reasons.

Make them pass with IMPLEMENTATION ONLY. You may not edit a single test file. If you
believe a RED test is wrong, STOP and flag it — do not edit it.

THE WORK, per the pinned spec:
- Separate CV reads from artifact writes in the VPR worker. One generic DAL instance must
  stop representing two storage domains.
- Persist the canonical VPR artifact through TableRegistry/CoreRepository on the canonical
  applicationId/artifactId grammar, BEFORE the job or hub is marked completed.
- Remove the legacy users-table VPR write. Do NOT dual-write.
- Make the hub, the jobs status record and the canonical artifact share one opaque id.
- Fix _get_vpr_job so it materializes the real payload; never return an id-only stub.
- Route cover letter, interview prep and CV tailoring through the same repository
  authority, preserving ownership and staleness checks.
- Propagate schema/infrastructure errors with the code DP-C pinned; never collapse them
  to a missing dependency.

DEPLOY AND VERIFY LIVE — a green unit suite does NOT discharge D-H4, whose verification
mode is contract+integration. Deploy to CareerVpCrudDevx, resolve the API base live from
the stack's RawApiInvokeUrl output, and run a full journey. Then re-run the live-API
suites and quote the real output. A skipped suite is not a passing suite.

DIFF AGAINST THE BASELINE at
docs/evidence/wave3-32closeouta-devx-characterization-20260801T094608Z.md wire by wire,
and call out every change, expected or not. Write a dated successor evidence file.

DO NOT: edit any test file, either scope-lock twin, or test_dh4_p01_canonical_artifact.py;
repoint DYNAMODB_TABLE_NAME as a shortcut; add a dual-read, migration, backfill or
compatibility reader; delete legacy records unless DP-D authorized it in writing; fix
F-DEVX-5 (gap async) or F-DEVX-6 (null policy) here — both need human decisions and have
their own steps.

OUTPUT REQUIRED: the full verification battery (RED tests now passing, unchanged ratchets,
full backend suite, ruff, mypy --strict, coverage gate with the core-branch ratchet held,
oracle + route parity, scope-lock integrity OK); the live journey output quoted; the
baseline diff; a plain statement of whether D-H4's contract+integration and P-01's
e2e+characterization can NOW be claimed, and if not, exactly what is missing; any new
defect, flagged not fixed.

ALSO REQUIRED: the standing drift comparison and the wave-3-status.md row. If D-H4 can be
claimed, say so explicitly so a human can close the clause.
```
