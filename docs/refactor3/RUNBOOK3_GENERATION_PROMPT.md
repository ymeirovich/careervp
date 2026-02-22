# Prompt: Generate `docs/refactor3/execution_runbook3.md`

```md
You are a Principal Staff Engineer generating a production execution runbook.

## Objective
Create `docs/refactor3/execution_runbook3.md` from:
- `docs/refactor2/ENDPOINT_2XX_REMEDIATION_PLAN.md`

The runbook must be modeled on:
- `docs/refactor/execution_runbook_2.md`
- `docs/refactor2/execution_runbook.md`

It must align with:
- `docs/refactor2/REFACTOR2_PLAN.md`

## Hard Success Condition (non-negotiable)
Success is achieved only when **all 27 OpenAPI endpoints** return:
1. **2xx HTTP status** (exact expected code per payload contract), and
2. **valid JSON response payloads** (parseable and schema-conformant).

Any endpoint returning 4xx/5xx, non-JSON, or schema mismatch = overall failure.

## Scope and Alignment Rules
1. Do not invent a new architecture that conflicts with REFACTOR2.
2. Keep REFACTOR2 focus areas:
   - auth failures
   - missing/incorrect route wiring
   - validation mismatches
   - DAL consistency
   - async flow correctness
   - deploy/test gates
3. Treat REFACTOR2_PLAN as source of truth for priorities and sequencing.
4. Include only executable work (no vague “investigate later” steps).

## Required Output Artifacts in Runbook3
Your generated runbook must define and reference these artifact groups under `docs/refactor3/`:

1. `specs/`:
   - `api_contract_spec.yaml`
   - `auth_and_authorizer_spec.yaml`
   - `route_mapping_spec.yaml`
   - `async_flow_spec.yaml`
   - `dal_alignment_spec.yaml`
   - `validation_spec.yaml`
   - `release_gate_spec.yaml`

2. `payloads/`:
   - One payload contract file per endpoint (27 files), with expected 2xx code and expected JSON keys.
   - Include async generate + async status payload pairs where applicable.

3. `tests/`:
   - `unit_tests.md`
   - `integration_tests.md`
   - `e2e_tests.md`
   - `contract_gate_tests.md` (must enforce 27/27 2xx JSON)

4. `validations/`:
   - `phase_exit_gates.md`
   - `endpoint_2xx_scorecard.md` (27-row matrix)
   - `deployment_validation.md`

## Structure Requirements for `execution_runbook3.md`
Use the same style/pattern as runbook_2 and runbook (refactor2):

1. Title, version, date, purpose, prerequisite.
2. Implementation order (phased, priority-first).
3. Current status table.
4. Specs registry table.
5. Phase-by-phase execution:
   - phase objective
   - duration/effort
   - read-first docs
   - executable tasks
   - exact file targets
   - commands to run
   - validation criteria
   - exit gate
6. Dedicated “27 Endpoint Contract Gate” section with strict acceptance rules.
7. Rollback and risk controls.
8. Final definition of done.

## Mandatory Phase Content
Include at least these phases:

- Phase 0: Preconditions and environment consistency
  - single API_BASE source
  - preflight checks

- Phase 1: API Gateway route-to-handler correctness
  - explicit route mapping fixes
  - public vs protected route policy

- Phase 2: Auth and authorizer correctness
  - token issuance/validation parity
  - deny/allow behavior verification

- Phase 3: Endpoint contract conformance
  - request/response status and schema alignment
  - handler and DAL consistency

- Phase 4: Async and workflow reliability
  - polling completion behavior
  - ID chaining across workflow steps

- Phase 5: Test expansion and strict contract gate
  - live strict test suite
  - endpoint-by-endpoint scorecard

- Phase 6: Release gate and sign-off
  - must pass 27/27 2xx JSON

## 27 Endpoint Coverage (must appear explicitly)
List and gate all:
- `/health`
- `/auth/register`, `/auth/login`, `/auth/refresh`
- `/users/me` (GET, PUT), `/users/me/cv`, `/users/me/cvs`
- `/jobs` (POST, GET), `/jobs/{jobId}`
- `/company-research/fetch`, `/company-research/{jobId}`
- `/gap-analysis/questions`, `/gap-analysis/responses`, `/gap-analysis/{jobId}/questions`
- `/vpr/generate`, `/vpr/{vprId}`, `/users/me/vprs`
- `/cv-tailoring/generate`, `/cv-tailoring/{cvTailoringId}`, `/users/me/tailored-cvs`
- `/cover-letter/generate`, `/cover-letter/{coverLetterId}`, `/users/me/cover-letters`
- `/interview-prep/generate`, `/interview-prep/{interviewPrepId}`

## Validation and Reporting Requirements
In runbook3, require:
1. exact commands for unit/integration/e2e/contract execution,
2. a 27-row endpoint scorecard with:
   - expected code
   - actual code
   - JSON valid (Y/N)
   - schema pass (Y/N)
   - pass/fail
3. fail-fast rule for any endpoint non-compliance,
4. final sign-off blocked unless all 27 are pass.

## Output Quality Rules
1. No placeholders like “TBD”, “etc.”, “add more later”.
2. Use concrete filenames, commands, and exit criteria.
3. Keep language operational and auditable.
4. Preserve compatibility with existing repo layout and testing approach.

## Deliverable
Produce exactly one complete document:
- `docs/refactor3/execution_runbook3.md`

And ensure that document itself includes references to the new `specs/`, `payloads/`, `tests/`, and `validations/` artifacts listed above.
```

