# Dead code / dead API / table map — inventory

**HANDOFF 10** (`docs/handoff/2026-09-21-HANDOFF-10-dead-code-sweep.md`), W2/W3/W4.3
of `PRODUCTION-PROGRAM.md`. Measured 2026-09-21 against `tools/proof-harness`.

**This is an inventory. Nothing listed here has been deleted.** Per the
handoff's ordering rule, deletion is a separate, later, reviewable pass — see
"Ordering for removal" at the end. Every row states a confidence level and the
command that proves it, so it can be re-checked rather than believed.

This document runs independently of **HANDOFF 09**
(`docs/handoff/2026-09-21-HANDOFF-09-environment-coupling.md`), which owns
environment-coupling fixes in `infra/careervp/` and `src/backend/careervp/dal/`
and was editing those trees concurrently with this sweep. Nothing here
duplicates that work; two items below explicitly connect to it instead.

## Reproduce this inventory

```bash
cd src/backend
uv run python scripts/dead_code.py    # orphaned modules
uv run python scripts/dead_api.py     # CDK routes vs. handlers vs. frontend callers
uv run python scripts/table_map.py    # table env vars vs. physical tables
```

Each writes a timestamped JSON proof to `docs/evidence/`; the three proofs this
inventory is drawn from are `dead_code-20260921T190614-0c04fc9.json`,
`dead_api-20260921T190615-0c04fc9.json`, `table_map-20260921T190615-0c04fc9.json`.

---

## 1. Confirmed finding — an orphaned CDK stack shipped inside every Lambda

`src/backend/careervp/infrastructure/stacks/cv_tailoring_stack.py` — **HIGH
confidence, safe-to-delete category.**

| Check | Result |
|---|---|
| Anything imports it? | `grep -rn 'CVTailoringStack' src/backend infra --include='*.py' \| grep -vE '\.build/\|cdk\.out/' \| grep -v 'stacks/cv_tailoring_stack.py:'` → **empty** |
| Predates the rehome to `infra/careervp/api_construct.py`? | `git log --oneline --follow -- src/backend/careervp/infrastructure/stacks/cv_tailoring_stack.py \| tail -2` → `5919449`/`e179ba4`, "Complete CV Tailoring feature" |
| Is it packaged into the Lambda build? | **Yes, confirmed.** `src/backend/Makefile`'s `build` target does `rsync -a careervp .build/lambdas --exclude 'cdk.out' --exclude '.mypy_cache' --exclude '.venv' --exclude '*.log'` — no exclude for `infrastructure/`, and every `_lambda.Function(...)` in `api_construct.py` sources `code=_lambda.Code.from_asset(constants.BUILD_FOLDER)`, i.e. `.build/lambdas`. Dead infrastructure code ships inside every one of the ~31 Lambda deployment artifacts. |
| Is there a deployed CloudFormation stack it corresponds to? | **No.** `aws cloudformation list-stacks --stack-status-filter CREATE_COMPLETE UPDATE_COMPLETE --query "StackSummaries[?contains(StackName,'Tailor')||contains(StackName,'CvTailoring')].StackName"` → `[]`. Orphaned in source only; deleting it is a source-tree change, not an infrastructure change. |

`dead_code.py` independently reaches the same conclusion (see §2) — this file,
and both of its now-empty containing packages (`infrastructure/__init__.py`,
`infrastructure/stacks/__init__.py`), have zero incoming import edges from
anywhere, including tests.

---

## 2. Orphaned backend modules (`dead_code.py`)

138 modules under `src/backend/careervp/`, seeded from all 27 Lambda
`handler=` strings in `infra/careervp/*.py` plus every import in
`src/backend/tests/`. **16 orphaned** (zero incoming edges from anywhere), **4
test-only** (reached only from `tests/`, never from a deployed handler).

| Module | Confidence | Evidence |
|---|---|---|
| `infrastructure/stacks/cv_tailoring_stack.py` (+ `infrastructure/__init__.py`, `infrastructure/stacks/__init__.py`) | HIGH | §1 above |
| `dal/cv_dal.py`, `dal/cv_repository.py` | HIGH | `CVTable` (defined in `cv_dal.py`) is deliberately migrated away from — `tests/unit/test_l1_dal_unification.py` asserts by name "CVTable must not be imported anywhere in handlers or DAL (except cv_dal.py itself)" and greps for zero matches. This is a locked-in migration, not an oversight. |
| `dal/cv_tailoring_dal.py` | MEDIUM | Zero import edges found; not cross-checked against a lock-in test the way `cv_dal.py` is. |
| `dal/knowledge_repository.py`, `handlers/knowledge_base_handler.py`, `models/knowledge_base.py` | HIGH | The whole "Knowledge Base backend" trio. See §4 — the live `GET /knowledge-base` route is served by a *different*, already-live handler (`company_research_handler.get_knowledge_base`), making this trio a superseded duplicate, not a missing feature. `grep -rn "knowledge_base_handler" --include='*.py' .` outside its own file → empty; `grep -rln "knowledge_repository\|KnowledgeRepository"` → only the two files that define it. |
| `dal/models/__init__.py` | HIGH | Empty file, no sibling modules (`ls src/backend/careervp/dal/models/` → `__init__.py` only). A package stub containing nothing. |
| `handlers/auth_middleware.py` | MEDIUM | Zero import edges found. |
| `handlers/models/dynamic_configuration.py` | MEDIUM | Zero import edges found. |
| `handlers/utils/validation.py` | MEDIUM | Zero import edges found. |
| `logic/utils/idempotency.py` | MEDIUM | Zero import edges found. |
| `models/cv_tailoring.py` | MEDIUM | Precisely re-checked (`grep -rn "models\.cv_tailoring\b\|from \.cv_tailoring import"` — the naive substring `cv_tailoring` also matches the unrelated, very much alive `logic/cv_tailoring.py`; the precise check returns empty). |
| `models/gap_analysis.py` | MEDIUM | Precisely re-checked the same way; empty. |

### Test-only (imported only by `tests/`, no production handler reaches them)

| Module | Note |
|---|---|
| `handlers/utils/dynamic_configuration.py` | Not cross-checked further. |
| `handlers/validators.py` | Not cross-checked further. |
| `logic/cv_tailoring_logic.py` | Not cross-checked further. |
| `models/fvs_models.py` | **Correction to the handoff's own framing, not a new bug.** The handoff's "read this first" section states "`models/fvs_models.py` ... are all live" as part of "FVS is not dead" — true of the *FVS system* (`check_anti_ai_patterns` in `logic/fvs_validator.py` is imported by `cover_letter.py`, `cv_tailoring.py`, `cv_tailoring_logic.py`, `vpr_generator.py` — very much alive), but `models/fvs_models.py` the *file* is specifically a legacy compat re-export shim over `models/fvs.py` (`fvs_models.py` itself does `from .fvs import ...`), and its own test's name says so: `test_legacy_fvs_models_module_reexports_canonical_models`. Production code imports `models/fvs.py` directly; nothing outside that one test imports `fvs_models.py`. Not dead code to remove — a live compatibility guarantee, just not a production dependency. |

`infra/careervp` (22 modules, seeded from `infra/app.py`): **zero orphaned.**
The infra tree is small and everything in it is reached.

---

## 3. A dead Lambda construction method, found by hand (not by `dead_code.py`)

`_add_vpr_lambda_integration` in `infra/careervp/api_construct.py:1357` is
**defined but never called** — `grep -n "_add_vpr_lambda_integration" infra/careervp/api_construct.py`
shows only its own `def` line; contrast with the structurally identical
`_add_company_research_lambda_integration`, which *is* called
(`self.company_research_func = self._add_company_research_lambda_integration(...)`
at line 220) and is a live Lambda.

This means the CDK app never constructs the `VPR_GENERATOR_LAMBDA` Lambda
resource, so `handlers/vpr_handler.py` (`handler="careervp.handlers.vpr_handler.lambda_handler"`,
the only place that handler string occurs) **ships to no deployed Lambda** —
production VPR generation runs entirely through the async
`vpr_submit_handler.py` / `vpr_worker_handler.py` / `vpr_status_handler.py`
trio instead.

**Why `dead_code.py` does not flag this:** the tool seeds reachability from
every handler string it finds in `infra/careervp/*.py`, regardless of whether
the method containing that string is itself called — by design, to avoid the
opposite trap (a naive import walk marking all 27 real handlers dead). A
handler string inside dead CDK code is a blind spot this category of tool
cannot close without also walking the CDK class's own call graph, which is a
different, harder check. This one instance was traced by hand.

`vpr_handler.py` is imported directly by four test files
(`tests/unit/test_vpr_handler.py`, `tests/unit/test_vpr_handler_serialization.py`,
`tests/integration/test_vpr_dal_handler_contract.py`,
`tests/integration/test_vpr_e2e.py`, `tests/integration/test_company_research_vpr.py`)
— thoroughly tested, never deployed.

**Confidence: HIGH.** Not touched here — belongs to the same "orphaned CDK
method" family as §1, but is entangled with HANDOFF-09's in-flight edits to
adjacent VPR handler files; coordinate before removing.

---

## 4. Dead / uncalled API routes (`dead_api.py`)

43 explicit routes + 4 proxy-prefix routes parsed from
`_add_openapi_contract_routes`, `register_ai_assist_routes` and
`register_error_report_route`. **0 missing handlers** (every route resolves to
a handler file and function that exist). **0 frontend calls with no matching
CDK route** (i.e. nothing in the frontend is calling into a 404).

**8 routes with no known frontend caller:**

| Route | Confidence | Note |
|---|---|---|
| `GET /health` | LOW severity | Called only from `src/frontend/tests/ops/rollback-procedure.ops.test.ts`, not from app code — expected; health checks are usually probed by infra, not the UI. |
| `POST /users/me/trial/reset` | MEDIUM | No frontend caller found anywhere (`grep -rn "trial/reset" src/frontend` → empty). Possibly an admin/support-only endpoint; verify with the operator before treating as dead. |
| `POST /jobs/{jobId}/gap-questions` | MEDIUM | Distinct from `saveGapResponses`'s `POST /jobs/{jobId}/gap-responses`, which *is* called. This is the *questions* endpoint (as opposed to *responses*) and has no caller. |
| `GET /vprs` | MEDIUM | No "list all VPRs" caller in the frontend. |
| `DELETE /cv-tailoring/{cvTailoringId}` | MEDIUM | `methods.ts` has `patchCVTailored` (PATCH) but nothing exposes delete. |
| `GET /interview-preps` | MEDIUM | No "list all interview preps" caller, mirroring `/vprs`. |
| `GET /knowledge-base` | HIGH, see below | Route is wired and really is served (see §3-adjacent finding below) — the gap is purely on the frontend side. |
| `POST /errors` | **FALSE POSITIVE — verified alive** | Not called via `apiClient` (which is all this tool scans), but is called: `src/frontend/app/api/errors/route.ts` is a Next.js route handler that itself does `fetch(\`${apiBase}/errors\`, ...)` server-to-server, and `components/ErrorBoundary/ErrorBoundary.tsx` calls `fetch('/api/errors/', ...)` client-side, which that route handler forwards. Recorded here as a documented limitation of the tool (see its docstring), not a dead route. |

### `/knowledge-base` — a route that works, served by the wrong-sounding handler, next to a fully dead duplicate

`("/knowledge-base", "GET", self.company_research_func)` in
`api_construct.py:3522` routes to the **Company Research** Lambda, not to
`handlers/knowledge_base_handler.py`. This is real, not a misconfiguration —
`company_research_handler.py:55` dispatches
`if method == 'GET' and path == '/knowledge-base': return get_knowledge_base(event)`,
and `get_knowledge_base` is implemented at line 304. So the route works.

What's dead is the entire *separate* `handlers/knowledge_base_handler.py` +
`dal/knowledge_repository.py` + `models/knowledge_base.py` trio (§2) — an
earlier, unwired implementation of the same concept, superseded when Knowledge
Base was folded into Company Research. Frontend never calls
`/knowledge-base` under any spelling (`grep -rli "knowledge" src/frontend/app src/frontend/components src/frontend/api src/frontend/lib` → empty), so the live route itself currently has no caller either — CLAUDE.md lists "Knowledge Base" as an included V1 feature; worth confirming with the operator whether this is a UI gap or an intentionally deferred surface, rather than assuming either.

---

## 5. Table map (`table_map.py`)

13 physical-table attributes resolved to 11 distinct DynamoDB tables (10 from
`ApiDbConstruct` + `llm_cache_table` built directly in `api_construct.py`).
Zero unresolved env-var assignments — every `"X_TABLE_NAME": expr` dict entry
across `infra/careervp/*.py` (including nested stacks) resolved to a known
physical table.

### Dead env vars — CDK sets them, nothing in the backend reads them, not even as a string

| Env var | Confidence | Evidence |
|---|---|---|
| `TOKEN_BLACKLIST_TABLE_NAME` | HIGH | Set once (`api_construct.py:2290`, pointing at the idempotency table). `grep -rn "TOKEN_BLACKLIST_TABLE_NAME" src/backend/careervp` → empty. Not even mentioned as a string. |
| `VPR_TABLE_NAME` | HIGH | Set once (`ai_assist_nested_stack.py:112`, pointing at the users table). `grep -rn "VPR_TABLE_NAME" src/backend/careervp` → empty. |

### Weak signal, manually verified ALIVE — not dead, just indirected past this tool's reach

`table_map.py` also reports two names as "mentioned as a quoted string
somewhere but no direct `os.environ` read found" rather than flatly dead,
specifically so they'd get checked by hand instead of miscounted:

| Env var | Verdict | Evidence |
|---|---|---|
| `COMPANY_RESEARCH_TABLE_NAME` | **ALIVE**, read via a `*args` fallback-chain helper | `dal/table_registry.py:136`: `_COMPANY_RESEARCH_ENV_CHAIN = ('COMPANY_RESEARCH_TABLE_NAME', *_ARTIFACTS_ENV_CHAIN)`, consumed by a shared `os.getenv(name)` loop the tool doesn't trace through. |
| `GAP_QUESTIONS_TABLE_NAME` | **ALIVE**, read the same way | `handlers/gap_handler.py:57-60`: `_resolve_table_name('GAP_QUESTIONS_TABLE_NAME', 'USERS_TABLE_NAME', 'DYNAMODB_TABLE_NAME')`, a private fallback-chain helper that does `os.getenv(env_key)` per candidate. |

Two other names the tool initially reported as "produced, not consumed" were
resolved by extending it rather than left as false alarms: `IDEMPOTENCY_TABLE_NAME`'s
`idempotency_table` parameter alias (one place in this codebase where a
Lambda-builder parameter name differs from the `ApiDbConstruct` attribute it
was seeded from — `idempotency_table=self.api_db.idempotency_db`), and
`IDENTITY_MAP_TABLE_NAME` / `COMPANY_RESEARCH_CACHE_TABLE_NAME`, both read via
an imported constant (`os.environ.get(IDENTITY_MAP_TABLE_ENV)`,
`api_gateway_authorizer.py:29`) rather than a literal string. All three are
now resolved correctly and do not appear in either "not consumed" list.

### Read but never set — backend has a fallback CDK never produces

| Env var | Confidence | Where read | Note |
|---|---|---|---|
| `JOBS_TABLE` | HIGH | `handlers/cover_letter_handler.py:204` | One of four candidate names tried in sequence (`JOBS_TABLE_NAME`, `VPR_JOBS_TABLE_NAME`, `JOBS_TABLE`, `JOB_TABLE_NAME`); CDK only ever sets the first two. This candidate can never fire — dead fallback branch, same shape as an `environment == "dev"` literal that no longer occurs. |
| `JOB_TABLE_NAME` | HIGH | `handlers/cover_letter_handler.py:205` | Same as above — singular "JOB", never set by CDK. |
| `SESSIONS_TABLE_NAME` | MEDIUM | `logic/utils/constants.py` | No corresponding `SESSIONS_TABLE_NAME` env assignment anywhere in `infra/careervp/`. There is a `SESSIONS_TABLE_NAME` constant in `infra/careervp/constants.py` (line 24, `"sessions"`) but no CDK code ever builds a sessions table from it — appears to be a planned-but-never-built table. |

### Same env var name, different physical table depending on which Lambda sets it

`ARTIFACTS_TABLE_NAME`, `TABLE_NAME`, and `DYNAMODB_TABLE_NAME` each resolve to
more than one physical table across different Lambdas. This is the exact
pattern `PRODUCTION-PROGRAM.md` already documents as a known code smell
("Four table env vars, three aliasing one physical table") — **not a new
finding**, reported here only because it's now backed by a mechanical,
re-runnable check instead of one hand-read example. `TABLE_NAME` and
`DYNAMODB_TABLE_NAME` are generic catch-all names reused per-Lambda by design;
treat a *new* occurrence of this pattern on a name that is not already known
to be generic as the real bug shape to watch for, not these three.

---

## 6. Unreachable branches (§2.3)

| Finding | Confidence | Evidence |
|---|---|---|
| `application_repository.py`'s `cr_pending`/`cr_failed` state-machine branch is currently unreachable in devx | HIGH, ties to HANDOFF-09 | `dal/application_repository.py:32-45`'s own comment: "cr_pending / cr_failed are intermediate states reached only when the auto-chain feature flag is ON." The write path (`handlers/gap_handler.py:424`) opens with `if os.environ.get('ARTIFACT_CHAIN_ENABLED', 'false').lower() != 'true': return` — and HANDOFF-09 (§0.1, §1 Class B) already measured `ARTIFACT_CHAIN_ENABLED` as `false` in the deployed devx Lambda. Same root cause as HANDOFF-09's finding, different symptom (a whole DAL state-machine branch, not just a config default). Not fixed here — it resolves automatically once HANDOFF-09's fix lands and the flag is deployed on. |
| `cover_letter_handler.py`'s dead `JOBS_TABLE`/`JOB_TABLE_NAME` fallback candidates | HIGH | See §5. |
| `knowledge_base_handler.py:26` hardcodes `os.environ.get('KNOWLEDGE_TABLE_NAME', 'careervp-knowledge-table-dev')` | LOW severity (moot) | Same *shape* as HANDOFF-09's Class A ("guess another environment's name"), but in a handler that §2/§3 establish is entirely orphaned — nothing invokes this code, so the hardcoded `-dev` default never actually executes. Flagged for completeness since it's the same bug pattern, in a file HANDOFF-09's own inventory doesn't cover (it wasn't in HANDOFF-09's six Class-A sites). |
| `logic/auth_service.py:229`, `except Exception: pass` | Checked — **not a defect** | Guards a single `cognito_idp.admin_confirm_sign_up` call with an inline comment "`# User may already be confirmed`" — an intentional, narrow, idempotency swallow around one known outcome, not a branch silently swallowed into non-existence. Investigated because the handoff named this file/line region explicitly; no action needed. |

---

## 7. Fixed while in there (already committed, separately from this inventory)

Per HANDOFF-10 §2.5's explicit instruction ("that is a live defect, not dead
code, and it is why the 2026-09-20 Dev incident was not caught. Fix it while
you are in there"):

- `scripts/ci/changeset_replacement_report.py`'s `PROTECTED_TYPES` listed
  `AWS::DynamoDB::Table` but not `AWS::DynamoDB::GlobalTable` — every table in
  this stack has been a `GlobalTable` since the P-26 migration, so the P-28
  data-loss AUTO-FAIL gate could never fire for a DynamoDB replacement. Fixed;
  regression test added (`test_replacement_report_covers_all_protected_types`
  now parametrizes `GlobalTable` too — it fails before the fix, passes after).
- `src/backend/scripts/preflight.py:366`'s `premise_tables` had the same
  type-string gap in the other direction: its "managed" set only matched
  `Table`, so every real `GlobalTable` was reported unmanaged regardless of
  stack ownership (consistent with `PRODUCTION-PROGRAM.md`'s "10 of 10 tables
  unmanaged" reading). Fixed to match either type.
- Commit `0c04fc9`. Both fixes verified: `uv run pytest tests/infra/test_p28_deploy_identity.py tests/infrastructure/test_p26_blue_green_api.py -k "report or replacement or Replacement"` — 22 passed.

---

## 8. Frontend (§2.6)

Findings from a dedicated frontend sweep (Explore agent), re-verified counts
against `docs/handoff/2026-09-21-HANDOFF-08-j3-client-side-submit.md`'s prior
claim.

| Finding | Confidence | Evidence |
|---|---|---|
| Dead route: `/dashboard/jobs/[jobId]` | HIGH | `src/frontend/app/dashboard/jobs/[jobId]/page.tsx` — duplicates `app/applications/[id]/page.tsx`'s logic. Zero references anywhere in `src/frontend` (`grep -rn "dashboard/jobs" src/frontend --include='*.tsx' --include='*.ts'` → empty), including zero test coverage. |
| Dead component: `components/layout/PageContainer.tsx` | HIGH | `grep -rn "PageContainer" src/frontend` → only its own definition. |
| Dead component: `components/UsageGate/UsageGate.tsx` | HIGH | `grep -rn "UsageGate" src/frontend` → only its own definition and three unrelated *test description strings* in `tests/unit/module-card-actions.test.tsx` (title text, not an import). |
| `*.figma.tsx` files (`ModuleCard.figma.tsx`, `Badge.figma.tsx`, `Button.figma.tsx`) | N/A — not dead | Zero in-repo imports, but these are Figma Code Connect definitions consumed by Figma's own tooling, not application code. Different category from the above; do not delete. |
| e2e test-block count, corrected | — | HANDOFF-08 claimed "308 e2e test blocks... ~1187 TODO-bodied... 0 test.fixme()". Re-verified 2026-09-21: **298** `test(` blocks (not 308), **1187** `TODO` occurrences (confirmed), **0** `test.fixme(` (confirmed). |
| 5 specs with exactly one real assertion, and it's a screenshot diff | MEDIUM | `badge.spec.ts:42`, `dashboard.spec.ts:58`, `error-boundary.spec.ts:54`, `progressbar.spec.ts:43`, `spinner.spec.ts:57` each have exactly one `expect(page).toHaveScreenshot(...)` and no functional assertion — the same "reports green, asserts nothing" failure mode `journey.spec.ts`'s header calls out, just not literally zero assertions. |

The frontend sweep was a **sample**, not exhaustive, over ~39 non-test
component files — treat the two dead-component findings as high-confidence
spot checks, not a complete count of dead frontend code.

---

## Ordering for removal (per the handoff's rule — safest first)

Nothing below has been actioned. This is the order the handoff specifies for
whenever a deletion pass is approved, with this inventory's findings slotted
in:

1. **Unread environment variables** (no behavior change): `TOKEN_BLACKLIST_TABLE_NAME`, `VPR_TABLE_NAME`.
2. **Orphaned source files with no deployed counterpart**: `infrastructure/stacks/cv_tailoring_stack.py` (§1, confirmed no deployed CFN stack), `dal/cv_dal.py`/`dal/cv_repository.py` (locked by their own migration test), the Knowledge Base trio (§2/§4, confirmed superseded), `handlers/vpr_handler.py` and its uncalled `_add_vpr_lambda_integration` (§3) — **coordinate with HANDOFF-09 first**, it is actively editing adjacent VPR handler files.
3. **Unreferenced routes**: none found with zero handler (§4's 0 missing-handler count) — the candidates in §4's table are "no known frontend caller", a softer signal requiring product confirmation (especially `/knowledge-base` and `POST /users/me/trial/reset`), not "safe to delete".
4. **Unreachable branches**: the `cover_letter_handler.py` dead fallback names (§6) — trivial, zero behavior change. The `cr_pending`/`cr_failed` branch (§6) needs no action; it resolves itself once HANDOFF-09's flag fix deploys.
5. **Data** — out of scope for this pass entirely; none of the above touches a table schema, and the handoff is explicit that data changes are last and never without the operator.

## What this inventory does not claim

- **Not exhaustive.** The frontend component sweep was a sample (§8). The
  per-artifact-type "does this reader's table match this writer's table"
  semantic check that `table_map.py`'s own docstring disclaims is not
  attempted here beyond the one instance already documented in
  `PRODUCTION-PROGRAM.md` (§5).
- **Not a second flags tool.** `FVS_ENABLED` and `ARTIFACT_CHAIN_ENABLED` are
  HANDOFF-09's Step 3.2 producer/consumer contract test's job; this document
  only cross-references its findings (§6) where they explain something found
  here, per the coordination note at the top.
- **A repo grep is not an inventory** — the rule this document was built to
  honor. Every row above states the command that proves it so the claim can
  be re-run, not just believed; several rows above exist specifically because
  an earlier, narrower grep would have gotten them wrong (§4's `/errors`
  false positive, §5's `COMPANY_RESEARCH_TABLE_NAME`/`GAP_QUESTIONS_TABLE_NAME`
  weak-signal correction).
