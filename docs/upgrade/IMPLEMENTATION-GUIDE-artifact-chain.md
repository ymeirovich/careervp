# Implementation Guide — Artifact Auto-Chain, VPR↔CR Binding, CR Quality, Cancellation & UI

Step-by-step build order for spec set **FE-UI-038 → FE-UI-043** with per-step model/effort
recommendations and complete copy-paste prompts for **Claude Code** and **OpenAI Codex**.

- Specs: `docs/upgrade/specs/FE-UI-038..043*.yaml`
- Test-prompt files: `TEST-CHAIN-002`, `TEST-CANCEL-001`, `TEST-FE-042`
- Already implemented (siblings): FE-UI-029, FE-UI-030, FE-UI-031, FE-UI-034, FE-UI-035, WORKER-LEGS-001.

---

## 0. Two things to know before starting

### Test-first means per-step, not globally

For each step: write the unit tests (red) → implement → green → write integration tests → green → PR.
Do not write all three test files upfront; the integration tests for Step 6 can't run before Steps 1–3 exist.

| Step | Write these tests first | Then implement |
|------|------------------------|----------------|
| 1 | `TEST-CHAIN-002 §` `unit-cr-serve`, `unit-cr-quality`, `unit-cr-confidence`, `regression-no-company-for` | FE-UI-041 |
| 2 | `TEST-CHAIN-002 §` `unit-cr-load`, `unit-vpr-inject`, `unit-vpr-provenance` | FE-UI-040 |
| 3 | `TEST-CANCEL-001 §` `integration-stop-chain` test 1 only | FE-UI-043-A |
| 4 | `TEST-CHAIN-002 §` `unit-resolver`, `unit-resolver-ownership` | FE-UI-038 |
| 5 | `TEST-CHAIN-002 §` `infra-chain-legs`, `unit-cl-ip-tasktoken` | FE-UI-039 |
| 6 | `TEST-CANCEL-001 §` `unit-cancellation`, `unit-worker-guard`, `unit-cr-cancel`, `security-reaper`, `infra-cancel-resources` | FE-UI-043-B |
| 7 | `TEST-FE-042 §` `unit-processing-dots`, `unit-module-card-processing` | FE-UI-042 |

### FE-UI-043 is one spec file, implemented in two steps

`FE-UI-043-cancellation-and-orphan-cleanup.yaml` covers everything. The A/B split only exists
in this guide to break a dependency cycle (the resolver in Step 4 needs the ARN tracking from
Step 3; the full cancel machinery in Step 6 needs the resolver):

- **FE-UI-043-A (Step 3):** only the `chain_execution_tracking` section — persist `executionArn`/status in the DAL.
- **FE-UI-043-B (Step 6):** remaining sections — `shared_cancel_orchestration`, `cr_cancel_endpoint`, `worker_cancelled_guard`, `orphan_cleanup_reaper`.

---

## 1. Build order

| # | Spec | Title | Human gate | Depends on |
|---|------|-------|-----------|------------|
| 1 | **FE-UI-041** | CR quality gate | **Gate 3** (API shape) | 029, 030 |
| 2 | **FE-UI-040** | VPR↔CR binding + provenance | — | 030, 041 |
| 3 | **FE-UI-043-A** | Chain execution tracking | — | 031 |
| 4 | **FE-UI-038** | Artifact dependency resolver | **Gate 3** (resp. schema + sfn start) | 029, 031, 040, 043-A |
| 5 | **FE-UI-039** | CL + IP chain legs + `artifacts_partial` | **Gate 2** (SFN + IAM) | 031, 035, 038 |
| 6 | **FE-UI-043-B** | Cancellation lifecycle + orphan cleanup | **Gate 3** (StopExecution + deletes) | 038, 039, 040 |
| 7 | **FE-UI-042** | Hub Processing/Cancel UI | — | 027, 041, 043 |

---

## 2. Model / effort cheat sheet

| Work type | Claude model | Effort | OMC agent | Codex model | `model_reasoning_effort` |
|-----------|-------------|--------|-----------|-------------|--------------------------|
| Architecture / safety-critical (resolver, cancel race, IAM, SFN) | **Opus 4.8** | **Max** | `executor-high` + `architect` verify | `gpt-5-codex` or `o3` | **high** |
| Standard backend feature | **Opus 4.8** | **High** | `executor-high` | `gpt-5-codex` | **high** |
| DAL field / route add / FE method | **Sonnet 4.6** | Medium | `executor` | `gpt-5-codex` | **medium** |
| Frontend UI/UX | **Sonnet 4.6** | Medium | `designer` / `executor` | `gpt-5-codex` | **medium** |
| Test authoring (most) | **Sonnet 4.6** | Medium | `tdd-guide` / `qa-tester` | `gpt-5-codex` | **medium** |
| Test authoring (race / security / reaper) | **Opus 4.8** | **High** | `qa-tester-high` | `gpt-5-codex` | **high** |
| Security review of any gated PR | **Opus 4.8** | **High** | `security-reviewer` | `gpt-5-codex` | **high** |
| Trivial (rename, import) | **Haiku 4.5** | Low | `executor-low` | `gpt-5-codex` | **low** |

> `/fast` in Claude Code keeps Opus 4.8 with faster output — use it for Sonnet-tier steps when you want the quality uplift.

---

## 3. Codex setup notes

- Interactive session: `codex` (opens REPL).
- Non-interactive / CI: `codex exec`.
- **Gated steps** (Steps 1, 4, 5, 6): always use `--ask-for-approval on-request` so IAM / delete / schema changes pause for you.
- **Non-gated steps** (Steps 2, 3, 7): `--full-auto` is fine (workspace-write sandbox only).
- Codex has no sub-agents. Replace the `security-reviewer` agent with a separate `codex exec` security-review invocation (see the prompt templates for each gated step below).

---

## 4. Step-by-step prompts

---

### STEP 1 — FE-UI-041 · CR quality gate · **Gate 3**

**Goal:** delete `_build_fallback_company_research_payload` and every `"Company for {uuid}"` seed;
gate CR persistence on confidence; `GET` missing CR → `200 {status:'not_generated'}`; reuse
existing CR on page load.

**Key files:** `company_research_handler.py` · `company_research.py` · `gap_handler.py` · `src/frontend/adapters/mapApplicationDataToHubState.ts`

#### Claude Code

```
Read docs/upgrade/specs/FE-UI-041-company-research-quality-gate.yaml.

PHASE 1 — tests first (Sonnet tier):
Write these failing tests before touching implementation:
  - tests/unit/test_company_research_quality.py
    covering TEST-CHAIN-002 categories: unit-cr-serve, unit-cr-quality,
    unit-cr-confidence, regression-no-company-for
Run: cd src/backend && uv run pytest tests/unit/test_company_research_quality.py -v --tb=short
All tests must be RED (failing) before you proceed.

PHASE 2 — implement (Opus tier):
Implement FE-UI-041 per the spec. Key constraints:
  - DELETE _build_fallback_company_research_payload (company_research_handler.py:449-461) and its call site (line 167).
  - GET /company-research on missing item returns 200 {status:'not_generated', company_research:null} — never a fabricated company.
  - Remove all "Company for {job_id}" literals from gap_handler.py (lines 537, 545) and company_research_handler.py.
  - Sub-threshold CR (below CR_CONFIDENCE_THRESHOLD) must NOT be persisted as completed.
  - No-source research (scrape+search both empty) returns ALL_SOURCES_FAILED, not _fallback_overview generic text.
  - Frontend: map status 'not_generated' -> 'notStarted' in mapApplicationDataToHubState.ts.
  - On load, an existing confidence-gated CR is reused (card 'complete'), not refetched.
  - Do NOT implement any other spec from this series.

PHASE 3 — validate:
cd src/backend && uv run ruff format . && uv run ruff check --fix . && uv run mypy careervp --strict
cd src/backend && uv run pytest tests/unit/test_company_research_quality.py -v --tb=short
cd src/frontend && npm run typecheck && npm run test:unit

Report passing test output as evidence. Pause before merge — Gate 3 requires approval of the GET /company-research response shape change.
```

#### Codex

```bash
codex --model gpt-5-codex -c model_reasoning_effort=high \
  --ask-for-approval on-request \
  "Read docs/upgrade/specs/FE-UI-041-company-research-quality-gate.yaml.

Phase 1 — write failing tests first:
  src/backend/tests/unit/test_company_research_quality.py
  covering: missing CR returns {status:'not_generated'} (not fabricated); sub-threshold not served as completed; no-source returns ALL_SOURCES_FAILED; no 'Company for' literal anywhere.
Run them — they must be RED.

Phase 2 — implement:
  Delete _build_fallback_company_research_payload (company_research_handler.py:449-461, call at line 167).
  GET missing CR -> 200 {status:'not_generated', company_research:null}.
  Remove 'Company for {job_id}' from gap_handler.py lines 537, 545.
  Sub-threshold CR not persisted as completed.
  No-source -> ALL_SOURCES_FAILED (no _fallback_overview as result).
  Frontend: map not_generated -> notStarted in adapters/mapApplicationDataToHubState.ts.

Phase 3 — validate:
  cd src/backend && uv run ruff format . && uv run mypy careervp --strict && uv run pytest tests/unit/test_company_research_quality.py -v
  cd src/frontend && npm run typecheck && npm run test:unit
Show all passing output. PAUSE before merge — Gate 3 approval required on GET response shape."
```

**Security review (Codex):**
```bash
codex --model gpt-5-codex -c model_reasoning_effort=high \
  --ask-for-approval never \
  "Security review only — do not write code.
Review the changes to company_research_handler.py and company_research.py for:
1. Is the missing-CR 200 response safe (no data leak from another user's CR)?
2. Is the confidence gate enforced at persist time, not just serve time?
3. Is ownership checked before returning any existing CR?
Report findings only."
```

---

### STEP 2 — FE-UI-040 · VPR↔CR binding · no gate

**Goal:** inject confident CR into VPR on the manual/standalone path; worker defense-in-depth
load; add provenance fields (`company_context_included`, `company_research_id`, `company_research_at`).

**Key files:** `vpr_submit_handler.py` · `vpr_worker_handler.py` · `vpr_status_handler.py` · `company_research.py` (new loader) · `vpr_generator.py`

#### Claude Code

```
Read docs/upgrade/specs/FE-UI-040-vpr-company-research-binding.yaml.
FE-UI-041 is already merged. Do not re-implement it.

PHASE 1 — tests first (Sonnet tier):
Write failing tests:
  - tests/unit/test_vpr_company_research_binding.py
    covering TEST-CHAIN-002 categories: unit-cr-load, unit-vpr-inject, unit-vpr-provenance
Run: cd src/backend && uv run pytest tests/unit/test_vpr_company_research_binding.py -v --tb=short
All tests must be RED before you proceed.

PHASE 2 — implement (Opus tier):
  - Add load_confident_company_research(application_id, user_id) -> CompanyContext|None helper.
    Rules: ownership-checked (artifact.user_id == user_id, else None); only returns CR with confidence >= CR_CONFIDENCE_THRESHOLD; NEVER returns a fabricated payload.
  - vpr_submit_handler.py: call loader before SQS enqueue; inject company_context + company_research_id into input_data; when CR absent, defer to resolver (202 dependency_generating — stub this path for now; FE-UI-038 will implement fully in Step 4).
  - vpr_worker_handler.py: if input_data has no company_context, attempt load_confident_company_research as defense-in-depth; log warning company_context_missing=true if still None.
  - Add provenance fields to VPR result + jobs record: company_research_id, company_research_at, company_context_included.
  - vpr_status_handler.py: surface those three fields in GET /vpr/{job_id}/status response.
  - vpr_generator.py: post-generation check — if company_context provided but company_insights empty, set company_context_included=false and log warning.

PHASE 3 — validate:
cd src/backend && uv run mypy careervp --strict
cd src/backend && uv run pytest tests/unit/test_vpr_company_research_binding.py -v --tb=short
cd src/backend && uv run pytest tests/unit/ -k 'vpr' -v --tb=short

Report passing output as evidence.
```

#### Codex

```bash
codex --model gpt-5-codex -c model_reasoning_effort=high \
  --full-auto \
  "Read docs/upgrade/specs/FE-UI-040-vpr-company-research-binding.yaml.
FE-UI-041 already merged. Do not re-implement it.

Phase 1 — write failing tests in tests/unit/test_vpr_company_research_binding.py:
  test_load_confident_cr_returns_context_when_present
  test_load_confident_cr_returns_none_for_low_confidence
  test_load_confident_cr_ownership_enforced
  test_vpr_submit_injects_company_context
  test_worker_loads_cr_when_message_lacks_context
  test_status_endpoint_exposes_provenance
Run — must be RED.

Phase 2 — implement per spec architecture section. Key constraints:
  Loader: ownership-checked, confidence-gated, never returns fabricated payload.
  Submit handler: injects company_context into input_data before SQS send; stubs 202 when CR absent.
  Worker: defense-in-depth CR load when message has no company_context.
  Provenance: company_research_id, company_research_at, company_context_included in result + status endpoint.

Phase 3:
  cd src/backend && uv run mypy careervp --strict && uv run pytest tests/unit/test_vpr_company_research_binding.py -v
Show passing output."
```

---

### STEP 3 — FE-UI-043-A · Chain execution tracking · no gate

**Goal:** capture the `executionArn` returned by `start_execution` and persist it on the
application record so the resolver (Step 4) can detect a running chain without a ListExecutions call.

**Key files:** `gap_handler.py` · `dal/<application_repository>.py`

**Scope:** ONLY the `chain_execution_tracking` section of FE-UI-043. Do not touch cancellation, cancel endpoints, workers, or the reaper.

#### Claude Code

```
Read the chain_execution_tracking section of docs/upgrade/specs/FE-UI-043-cancellation-and-orphan-cleanup.yaml.
Do NOT implement any other section of that spec (cancel_artifact, cr_cancel_endpoint, worker_cancelled_guard, orphan_cleanup_reaper — those come in Step 6).

PHASE 1 — test first (Sonnet tier):
Write ONE failing test:
  tests/integration/test_stop_chain.py :: test_gap_submit_persists_execution_arn
  Setup: ARTIFACT_CHAIN_ENABLED=true, mocked sfn client returning executionArn.
  Assert: application.chain_execution_arn set; chain_execution_status='RUNNING'.
Run: cd src/backend && uv run pytest tests/integration/test_stop_chain.py::test_gap_submit_persists_execution_arn -v --tb=short
Must be RED.

PHASE 2 — implement (Sonnet tier):
  - gap_handler.py _maybe_start_artifact_chain: capture start_execution(...)['executionArn'] (currently discarded at line 442); call application_repo.set_chain_execution(application_id, user_id, execution_arn, status='RUNNING') immediately after.
  - dal/<application_repository>.py: add set_chain_execution(application_id, user_id, execution_arn, status) writing chain_execution_arn + chain_execution_status attributes.
  - Update existing failure-handler / success terminal paths to set chain_execution_status to 'STOPPED'/'SUCCEEDED'/'FAILED' when the chain ends.

PHASE 3 — validate:
cd src/backend && uv run mypy careervp --strict
cd src/backend && uv run pytest tests/integration/test_stop_chain.py::test_gap_submit_persists_execution_arn -v
cd src/backend && uv run pytest tests/unit/ -k 'application or chain' -v --tb=short

Report passing output.
```

#### Codex

```bash
codex --model gpt-5-codex -c model_reasoning_effort=medium \
  --full-auto \
  "Read ONLY the chain_execution_tracking section of docs/upgrade/specs/FE-UI-043-cancellation-and-orphan-cleanup.yaml.
Do NOT implement: cancel_artifact, cr_cancel_endpoint, worker_cancelled_guard, orphan_cleanup_reaper.

Phase 1 — write one failing integration test:
  tests/integration/test_stop_chain.py :: test_gap_submit_persists_execution_arn
  Mock sfn returning executionArn. Assert application.chain_execution_arn + chain_execution_status='RUNNING' are set.
Run — must be RED.

Phase 2 — implement:
  gap_handler.py: capture start_execution(...)['executionArn'] (currently discarded); call set_chain_execution.
  application_repository.py: add set_chain_execution DAL method; write chain_execution_arn + chain_execution_status.
  Failure/success terminal handlers: update chain_execution_status to STOPPED/SUCCEEDED/FAILED.

Phase 3:
  cd src/backend && uv run mypy careervp --strict && uv run pytest tests/integration/test_stop_chain.py::test_gap_submit_persists_execution_arn -v
Show passing output."
```

---

### STEP 4 — FE-UI-038 · Artifact dependency resolver · **Gate 3**

**Goal:** pure-logic resolver that enforces the artifact dependency graph for every generate
request; removes `_FallbackVPR` and all silent placeholders; missing upstream → `202 dependency_generating`;
running-chain guard reads the ARN persisted in Step 3.

**Key files:** new `logic/artifact_dependency_resolver.py` · `cover_letter_submit_handler.py` · `interview_prep_submit_handler.py` · `cv_tailoring_handler.py` · `vpr_submit_handler.py`

#### Claude Code

```
Read docs/upgrade/specs/FE-UI-038-artifact-dependency-resolver.yaml.
FE-UI-040 and FE-UI-043-A are already merged.

PHASE 1 — tests first (Opus tier — ownership is security-critical):
Write failing tests:
  - tests/unit/test_artifact_dependency_resolver.py
    covering TEST-CHAIN-002 categories: unit-resolver, unit-resolver-ownership
Run: cd src/backend && uv run pytest tests/unit/test_artifact_dependency_resolver.py -v --tb=short
All tests must be RED.

PHASE 2 — implement (Opus tier, plan mode first):
Before writing code, output a step-by-step plan covering:
  - The dependency graph edges (see spec dependency_graph section).
  - How resolve_dependencies(artifact_type, application_id, user_id, repos) returns DependencyResolution.
  - How the running-chain guard reads application.chain_execution_arn + chain_execution_status (set in 043-A).
  - How auto-generate starts a new chain (and persists the new ARN via 043-A's DAL method).
Wait for approval, then implement.

Key constraints:
  - Resolver is PURE logic; inject repos + sfn-trigger callable (no boto3 in resolver.py).
  - Ownership check on every upstream artifact load: artifact.user_id != user_id -> treat as MISSING.
  - Remove _FallbackVPR class (cover_letter_handler.py:61-76) and its _resolve_vpr_payload usage (lines 320-340).
  - Remove interview_prep {'vpr_id': vpr_id} placeholder (interview_prep_submit_handler.py ~233-254).
  - Replace cv_tailoring ValueError on missing vpr_id (line 62) with resolver call.
  - Missing upstream + ARTIFACT_CHAIN_ENABLED=true -> 202 dependency_generating (start chain, mark artifact pending).
  - Missing upstream + ARTIFACT_CHAIN_ENABLED=false -> 409 upstream_required (no placeholder, no chain).
  - Running chain (chain_execution_status=='RUNNING') -> 202 dependency_generating, chain_execution_arn=None, do NOT start duplicate.
  - Mark artifact_statuses[requested]='pending' on dependency_generating response.

PHASE 3 — validate:
cd src/backend && uv run mypy careervp --strict
cd src/backend && uv run pytest tests/unit/test_artifact_dependency_resolver.py tests/unit/test_resolver_ownership.py -v --tb=short
cd src/backend && uv run pytest tests/integration/test_downstream_dependency_202.py -v --tb=short
cd src/backend && uv run pytest tests/regression/test_no_placeholder_fallbacks.py -v --tb=short

Then run security review:
grep -rn '_FallbackVPR' src/backend/careervp/  # must return no matches
grep -rn "vpr_id': vpr_id" src/backend/careervp/  # must return no matches

Pause before merge — Gate 3 requires approval of the 202 dependency_generating response contract and any generate-handler sfn.start_execution call.
```

#### Codex

```bash
codex --model o3 -c model_reasoning_effort=high \
  --ask-for-approval on-request \
  "Read docs/upgrade/specs/FE-UI-038-artifact-dependency-resolver.yaml.
FE-UI-040 and FE-UI-043-A already merged.

Phase 1 — write failing tests:
  tests/unit/test_artifact_dependency_resolver.py (unit-resolver + unit-resolver-ownership categories from TEST-CHAIN-002)
Run — must be RED.

Phase 2 — implement. Key constraints:
  - artifact_dependency_resolver.py is PURE logic; inject repos + sfn-trigger.
  - Ownership check on every upstream artifact: other user's artifact = MISSING (security invariant).
  - Remove _FallbackVPR (cover_letter_handler.py:61-76, _resolve_vpr_payload:320-340).
  - Remove interview-prep vpr placeholder (~233-254).
  - Replace cv_tailoring ValueError on missing vpr_id with resolver 202.
  - Flag ON + missing upstream -> 202 dependency_generating + start chain (persist ARN via 043-A DAL).
  - Flag OFF + missing upstream -> 409 upstream_required.
  - Running chain (chain_execution_status==RUNNING) -> 202, no duplicate execution.
  - Mark artifact_statuses[requested]='pending' on 202.

Phase 3:
  cd src/backend && uv run mypy careervp --strict
  cd src/backend && uv run pytest tests/unit/test_artifact_dependency_resolver.py tests/unit/test_resolver_ownership.py tests/integration/test_downstream_dependency_202.py tests/regression/test_no_placeholder_fallbacks.py -v
  grep -rn '_FallbackVPR' src/backend/careervp/ # must be empty
Show all output. PAUSE — Gate 3 requires approval before merge."
```

**Security review (Codex):**
```bash
codex --model gpt-5-codex -c model_reasoning_effort=high \
  --ask-for-approval never \
  "Security review only — do not write code.
Review artifact_dependency_resolver.py and the modified generate handlers for:
1. Is ownership enforced on EVERY upstream artifact load? Can user A ever get user B's VPR or CR injected?
2. Can a missing-upstream condition be bypassed to produce a placeholder document?
3. Is the running-chain guard race-safe (concurrent generate calls for same application)?
4. Is 409 vs 202 routing correct when ARTIFACT_CHAIN_ENABLED=false?
Report findings only."
```

---

### STEP 5 — FE-UI-039 · CL + IP chain legs + `artifacts_partial` · **Gate 2**

**Goal:** add `GenerateFinalArtifacts` Parallel state (Cover Letter + Interview Prep) to the SFN
chain after CV Tailoring; task-token support in both workers; `artifacts_partial` terminal state.

**Key files:** `infra/careervp/artifact_chain_construct.py` · `cover_letter_submit_handler.py` · `interview_prep_submit_handler.py` · `infra/careervp/api_construct.py` · `src/backend/careervp/handlers/application_handler.py`

#### Claude Code

```
Read docs/upgrade/specs/FE-UI-039-chain-coverletter-interviewprep-legs.yaml.
FE-UI-038 is already merged. FE-UI-035 (dependency cycle fix) is already merged.

PHASE 1 — tests first (Opus tier — infra assertions):
Write failing tests:
  - infra/tests/test_artifact_chain_legs.py
    covering TEST-CHAIN-002 category: infra-chain-legs (5 tests including no-cycle regression)
  - tests/unit/test_cl_ip_task_token.py
    covering TEST-CHAIN-002 category: unit-cl-ip-tasktoken (4 tests)
Run:
  cd infra && uv run pytest tests/test_artifact_chain_legs.py -v --tb=short  # RED
  cd src/backend && uv run pytest tests/unit/test_cl_ip_task_token.py -v --tb=short  # RED

PHASE 2 — implement (Opus tier, plan mode first):
Output a plan before coding. Key constraints:
  - Add GenerateFinalArtifacts Parallel state AFTER StartCVTailoring in artifact_chain_construct.py per the spec's state_machine_extension section.
  - CL branch: sqs:sendMessage.waitForTaskToken to CoverLetterQueueUrl; passes vpr_id AND company_context in MessageBody.
  - IP branch: sqs:sendMessage.waitForTaskToken to InterviewPrepQueueUrl; passes vpr_id.
  - HandleCoverLetterFailure + HandleInterviewPrepFailure states call ArtifactFailureHandlerArn.
  - One branch failing must NOT silently discard the other branch's result — use Catch on Parallel.
  - Add artifacts_partial terminal state: add to VALID_TRANSITIONS in application_handler.py; add to _RELOAD_ROUTE_BY_STATE -> '/artifacts'; rule: VPR+CV completed AND >=1 of CL/IP completed but not all.
  - cover_letter_submit_handler.py + interview_prep_submit_handler.py: read task_token from SQS message; call sfn.send_task_success / send_task_failure. task_token is Optional — manual path must be unchanged.
  - IAM: states:SendTaskSuccess + states:SendTaskFailure on CL/IP workers, scoped to chain ARN only. sqs:SendMessage on CL/IP queues for Step Functions role. NO states:* wildcards.
Wait for approval, then implement.

PHASE 3 — validate:
cd infra && uv sync && npx cdk synth
cd infra && uv run pytest tests/infrastructure -v --tb=short  # zero dependency-cycle errors
cd infra && uv run pytest tests/test_artifact_chain_legs.py -v --tb=short
python src/backend/scripts/validate_naming.py --path infra --strict
uvx checkov -d infra/cdk.out --framework cloudformation --quiet
cd src/backend && uv run mypy careervp --strict
cd src/backend && uv run pytest tests/unit/test_cl_ip_task_token.py -v --tb=short

Pause before merge — Gate 2 requires approval of the SFN state-machine change + IAM grants.
```

#### Codex

```bash
codex --model gpt-5-codex -c model_reasoning_effort=high \
  --ask-for-approval on-request \
  "Read docs/upgrade/specs/FE-UI-039-chain-coverletter-interviewprep-legs.yaml.

Phase 1 — write failing tests:
  infra/tests/test_artifact_chain_legs.py (infra-chain-legs: 5 tests including no-cycle regression)
  src/backend/tests/unit/test_cl_ip_task_token.py (unit-cl-ip-tasktoken: 4 tests)
Run both — must be RED.

Phase 2 — implement. Constraints:
  Add GenerateFinalArtifacts Parallel state after StartCVTailoring per spec state_machine_extension.
  CL branch: waitForTaskToken, passes vpr_id + company_context. IP branch: passes vpr_id.
  Failure handlers: HandleCoverLetterFailure, HandleInterviewPrepFailure -> ArtifactFailureHandlerArn.
  Parallel catch: one branch failure must not discard the other's result.
  artifacts_partial state: add to VALID_TRANSITIONS + _RELOAD_ROUTE_BY_STATE in application_handler.py.
  Workers: read optional task_token; call send_task_success/failure; manual path unchanged.
  IAM: SendTaskSuccess/Failure on workers scoped to chain ARN; NO states:* wildcards.

Phase 3:
  cd infra && uv sync && npx cdk synth && uv run pytest tests/infrastructure tests/test_artifact_chain_legs.py -v
  python src/backend/scripts/validate_naming.py --path infra --strict
  uvx checkov -d infra/cdk.out --framework cloudformation --quiet
  cd src/backend && uv run mypy careervp --strict && uv run pytest tests/unit/test_cl_ip_task_token.py -v
Show all output. PAUSE — Gate 2 approval required before merge."
```

---

### STEP 6 — FE-UI-043-B · Cancellation lifecycle + orphan cleanup · **Gate 3**

**Goal:** `cancel_artifact` orchestration (chained → `stop_execution` + mark pending cancelled;
standalone → one job); CR cancel endpoint + infra route + FE method; worker CANCELLED-guard
(conditional `UpdateItem`); orphan-cleanup reaper Lambda + EventBridge schedule.

**Key files:** new `logic/cancellation.py` · new reaper handler · `company_research_handler.py` · `vpr_status_handler.py` · `cover_letter_handler.py` · `interview_prep_handler.py` · `cv_tailoring_handler.py` · all workers · `api_construct.py` · `api/methods.ts`

**Scope:** everything in FE-UI-043 EXCEPT `chain_execution_tracking` (already done in Step 3).

#### Claude Code

```
Read docs/upgrade/specs/FE-UI-043-cancellation-and-orphan-cleanup.yaml.
FE-UI-043-A (chain_execution_tracking section) is already implemented — do not re-implement it.
Implement only: shared_cancel_orchestration, cr_cancel_endpoint, worker_cancelled_guard, orphan_cleanup_reaper.
FE-UI-038 and FE-UI-039 are already merged.

PHASE 1 — tests first (Opus tier — race + security critical):
Write failing tests:
  - tests/unit/test_cancellation.py          (TEST-CANCEL-001 § unit-cancellation: 6 tests)
  - tests/unit/test_worker_cancelled_guard.py (TEST-CANCEL-001 § unit-worker-guard: 4 tests, parametrize across all 5 workers)
  - tests/unit/test_company_research_cancel.py (TEST-CANCEL-001 § unit-cr-cancel: 4 tests)
  - tests/security/test_cancel_cleanup_safety.py (TEST-CANCEL-001 § security-reaper: 3 tests)
  - infra/tests/test_cancellation_infra.py   (TEST-CANCEL-001 § infra-cancel-resources: 5 tests)
Run all — must be RED.

PHASE 2 — implement (Opus tier, plan mode first):
Output an implementation plan. Key constraints:
  - logic/cancellation.py cancel_artifact is injected with repos + sfn client (no direct boto3 import in the logic module).
  - Chained cancel (application.chain_execution_status=='RUNNING'): call sfn.stop_execution(chain_execution_arn); set chain_execution_status='STOPPED'; set artifact_statuses for every artifact in {pending, processing} to 'cancelled'.
  - Standalone cancel (no running chain): mark only that job CANCELLED.
  - Wire cancel_artifact into all 4 existing cancel handlers (replacing the status-only DynamoDB write) — external contract unchanged ({status:'cancelled'}, CONFLICT on terminal, FORBIDDEN on non-owner).
  - CR cancel: new _handle_company_research_cancel in company_research_handler.py; new route POST /company-research/{jobId}/cancel in api_construct.py; new api.cancelCompanyResearch in api/methods.ts.
  - Worker CANCELLED-guard: each of the 5 workers must use conditional UpdateItem (ConditionExpression: attribute_not_exists(#s) OR #s <> :cancelled) as the atomic guard on the COMPLETED write. If cancelled: skip S3 write (or delete if already written); call sfn.send_task_failure if task_token present; return cleanly (no DLQ).
  - Orphan reaper: new handler; EventBridge schedule; actions: delete S3 result_key if present; reset artifact_statuses[type]='cancelled'; roll back late COMPLETED (completed_at > cancel, chain_execution_status='STOPPED') to CANCELLED + delete S3. Support CLEANUP_DRY_RUN=true env var.
  - IAM: states:StopExecution + states:DescribeExecution scoped to chain ARN (no states:*); reaper: s3:DeleteObject prefix-scoped + dynamodb:UpdateItem/DeleteItem on specific tables.
  - Safety invariants: never delete another user's artifact; never delete COMPLETED for a live (non-stopped) chain.
Wait for approval, then implement.

PHASE 3 — validate:
cd src/backend && uv run mypy careervp --strict
cd src/backend && uv run pytest tests/unit/test_cancellation.py tests/unit/test_worker_cancelled_guard.py tests/unit/test_company_research_cancel.py -v --tb=short
cd src/backend && uv run pytest tests/security/test_cancel_cleanup_safety.py -v --tb=short
cd src/backend && uv run pytest tests/integration/test_stop_chain.py tests/integration/test_orphan_reaper.py -v --tb=short
cd infra && uv sync && npx cdk synth && uv run pytest tests/infrastructure tests/test_cancellation_infra.py -v --tb=short
python src/backend/scripts/validate_naming.py --path infra --strict
uvx checkov -d infra/cdk.out --framework cloudformation --quiet
cd src/frontend && npm run typecheck && npm run test:unit

Pause before merge — Gate 3 requires approval of states:StopExecution IAM, the new delete paths, and the reaper schedule.
```

#### Codex

```bash
codex --model o3 -c model_reasoning_effort=high \
  --ask-for-approval on-request \
  "Read docs/upgrade/specs/FE-UI-043-cancellation-and-orphan-cleanup.yaml.
FE-UI-043-A (chain_execution_tracking) already implemented. FE-UI-038 + FE-UI-039 already merged.
Implement only: shared_cancel_orchestration, cr_cancel_endpoint, worker_cancelled_guard, orphan_cleanup_reaper.

Phase 1 — write failing tests:
  tests/unit/test_cancellation.py (6 tests — chained/standalone/terminal/forbidden/idempotent/sfn-fail)
  tests/unit/test_worker_cancelled_guard.py (4 tests — parametrize across all 5 workers)
  tests/unit/test_company_research_cancel.py (4 tests)
  tests/security/test_cancel_cleanup_safety.py (3 tests)
  infra/tests/test_cancellation_infra.py (5 tests)
Run all — must be RED.

Phase 2 — implement. Constraints:
  cancel_artifact: injected repos + sfn (no boto3 in logic module).
  Chained cancel: stop_execution + mark all pending/processing artifacts 'cancelled' + set chain_execution_status='STOPPED'.
  Standalone: one job CANCELLED only.
  All 4 existing cancel handlers wired through cancel_artifact (external contract unchanged).
  CR cancel: new handler + route POST /company-research/{jobId}/cancel + api.cancelCompanyResearch.
  Workers: conditional UpdateItem guard on COMPLETED write; on cancel skip/delete S3; send_task_failure if token; no DLQ.
  Reaper: delete S3 + reset status for CANCELLED jobs; roll back late COMPLETED on stopped chain; CLEANUP_DRY_RUN mode.
  IAM: StopExecution + DescribeExecution scoped to chain ARN; NO states:*; reaper gets prefix-scoped S3:DeleteObject.
  Safety: never delete another user's artifact; never touch COMPLETED of live chain.

Phase 3:
  cd src/backend && uv run mypy careervp --strict
  cd src/backend && uv run pytest tests/unit/test_cancellation.py tests/unit/test_worker_cancelled_guard.py tests/unit/test_company_research_cancel.py tests/security/test_cancel_cleanup_safety.py tests/integration/test_stop_chain.py tests/integration/test_orphan_reaper.py -v
  cd infra && uv sync && npx cdk synth && uv run pytest tests/infrastructure tests/test_cancellation_infra.py -v
  python src/backend/scripts/validate_naming.py --path infra --strict
  uvx checkov -d infra/cdk.out --framework cloudformation --quiet
Show all output. PAUSE — Gate 3 approval required before merge."
```

**Security review (Codex):**
```bash
codex --model gpt-5-codex -c model_reasoning_effort=high \
  --ask-for-approval never \
  "Security review only — do not write code.
Review logic/cancellation.py, the modified cancel handlers, the worker CANCELLED-guard, and the reaper handler for:
1. Can a user cancel another user's artifact (ownership bypass)?
2. Can the reaper delete a COMPLETED artifact belonging to a live (non-stopped) chain?
3. Is the worker conditional-write guard race-safe — is it atomic, or can cancel arrive between the read and the write?
4. Does states:StopExecution grant have a wildcard resource ('*') or is it scoped to the specific chain ARN?
5. Does the reaper's S3:DeleteObject grant use a wildcard bucket or is it prefix-scoped?
Report findings only."
```

---

### STEP 7 — FE-UI-042 · Hub Processing/Cancel UI · no gate

**Goal:** `ProcessingDots` component (sequential 3-dot animation, reduced-motion); unified
Processing/Cancel across ALL cards including Company Research; failures surface error and always
restore buttons; AbortController for pre-taskId cancel.

**Key files:** new `components/ui/ProcessingDots.tsx` · `ModuleCard.tsx` · `app/applications/[id]/page.tsx` · `hooks/useGenerateModule.ts` · `api/methods.ts`

#### Claude Code

```
Read docs/upgrade/specs/FE-UI-042-hub-processing-cancel-state.yaml.
FE-UI-041 and FE-UI-043-B are already merged (CR not_generated status + CR cancel endpoint exist).

PHASE 1 — tests first (Sonnet tier):
Write failing tests:
  - tests/unit/processing-dots.test.tsx           (TEST-FE-042 § unit-processing-dots: 4 tests)
  - tests/unit/module-card-processing.test.tsx    (TEST-FE-042 § unit-module-card-processing: parametrize across all 7 modules)
Run: cd src/frontend && npx vitest run --config vitest.config.ts tests/unit/processing-dots.test.tsx tests/unit/module-card-processing.test.tsx
Must be RED.

PHASE 2 — implement (Sonnet tier):
  1. Create components/ui/ProcessingDots.tsx:
     - Renders "Processing" label + exactly 3 dot spans.
     - Dots animate sequentially via staggered animation-delay (0ms / 200ms / 400ms) on opacity.
     - Class must NOT be 'animate-pulse' (that fades the whole ellipsis — wrong).
     - Add @keyframes to tailwind.config or a scoped CSS module.
     - prefers-reduced-motion: render static 'Processing...' with no animation.
     - Dot spans: aria-hidden="true". Accessible label comes from the card's sr-only live region.
  2. ModuleCard.tsx: replace the animate-pulse span (line 214) with <ProcessingDots />.
  3. page.tsx — unify CR into the same processing model:
     - Add companyResearch to genMap using api.fetchCompanyResearch as generate and api.cancelCompanyResearch as cancel.
     - Remove the bespoke isRetryingCompanyResearch flag and its usage at lines ~188-196, ~236-243.
     - GENERATABLE_MODULES must include companyResearch.
  4. useGenerateModule.ts — fix failure handling:
     - generate() must propagate errors; wrap in try/catch; always reset isGenerating in finally.
     - handleGenerate in page.tsx must catch the error and call setGenerationErrors[moduleType] = message.
     - Polling: when useModuleStatus returns status='failed', set generationErrors[moduleType] and clear processing.
  5. useGenerateModule.ts — AbortController:
     - generate() creates an AbortController; passes signal to the API call.
     - cancel() before taskId is known: call controller.abort(), clear isGenerating.
     - Cancel always renders while isActivelyProcessing, even when taskId is null.

PHASE 3 — validate:
cd src/frontend && npm run typecheck
cd src/frontend && npm run test:unit
cd src/frontend && npm run test:integration
Verify cta-label-consistency.test.ts still passes (labels must not change).

Report passing output as evidence.
```

#### Codex

```bash
codex --model gpt-5-codex -c model_reasoning_effort=medium \
  --full-auto \
  "Read docs/upgrade/specs/FE-UI-042-hub-processing-cancel-state.yaml.
FE-UI-041 (CR not_generated) and FE-UI-043-B (CR cancel endpoint) already merged.

Phase 1 — write failing tests:
  src/frontend/tests/unit/processing-dots.test.tsx (4 tests: render, staggered-delay-not-pulse, reduced-motion, aria-hidden)
  src/frontend/tests/unit/module-card-processing.test.tsx (parametrize over all 7 modules: processing hides primary+secondary, shows ProcessingDots+Cancel, aria-busy)
Run: cd src/frontend && npx vitest run --config vitest.config.ts tests/unit/processing-dots.test.tsx tests/unit/module-card-processing.test.tsx
Must be RED.

Phase 2 — implement:
  ProcessingDots.tsx: 3 dot spans, staggered animation-delay NOT animate-pulse, reduced-motion static fallback, dots aria-hidden.
  ModuleCard.tsx line 214: replace animate-pulse span with <ProcessingDots />.
  page.tsx: add companyResearch to genMap; remove isRetryingCompanyResearch bespoke path; GENERATABLE_MODULES includes companyResearch.
  useGenerateModule.ts: generate() propagates errors (finally resets isGenerating); AbortController (abort on pre-taskId cancel); cancel renders unconditionally while isActivelyProcessing.
  handleGenerate in page.tsx: wrap in try/catch; set generationErrors on failure.
  Polling failed: set generationErrors + exit processing.

Phase 3:
  cd src/frontend && npm run typecheck && npm run test:unit && npm run test:integration
Show passing output. Verify cta-label-consistency.test.ts passes."
```

---

## 5. Human-approval gate checklist

Pause and get explicit sign-off before merging:
- [ ] **Step 1 / FE-UI-041** — `GET /company-research` response shape (`not_generated`).
- [ ] **Step 4 / FE-UI-038** — `202 dependency_generating` response variant + generate-handler `sfn.start_execution`.
- [ ] **Step 5 / FE-UI-039** — SFN state-machine extension + new IAM grants (Gate 2).
- [ ] **Step 6 / FE-UI-043-B** — `states:StopExecution` IAM, artifact-delete logic, reaper schedule.

For each gated step: run the security-review Codex prompt (or `security-reviewer` agent in Claude),
confirm `validate_naming.py --strict` + `checkov` green, merge via `scripts/git/safe_merge_to_main.sh`.

---

## 6. Final integration + rollout

Run these after all 7 steps are merged:

```bash
# Full regression sweep
cd src/backend && uv run ruff format . && uv run ruff check --fix . && uv run mypy careervp --strict && uv run pytest tests/unit -q
cd infra && uv sync && npx cdk synth && uv run pytest tests/infrastructure
python src/backend/scripts/validate_naming.py --path infra --strict
uvx checkov -d infra/cdk.out --framework cloudformation --quiet
cd src/frontend && npm run typecheck && npm run test:unit && npm run test:integration
```

Then rollout:
1. Enable `ARTIFACT_CHAIN_ENABLED=true` in dev only.
2. Start reaper with `CLEANUP_DRY_RUN=true`; verify it logs intended deletions correctly; then set `CLEANUP_DRY_RUN=false`.
3. End-to-end smoke test on dev: gap submit → all 5 artifacts produced on real CR; VPR `company_context_included=true`; cancel mid-chain → `stop_execution` called, no orphan S3 objects, hub shows cancelled state.
