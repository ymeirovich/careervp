# /goal FE-UI-054 Frontend — session-independent polling
# Model: sonnet | Effort: medium
# Spec: docs/upgrade/specs/FE-UI-054-cr-polling-session-independent.yaml
# Tests: docs/upgrade/specs/TEST-FE-054-test-prompts.yaml
# Prereq: FE-UI-053-backend-handoff.md gate confirmed (artifacts table contract set)

GOAL: Refactor company-research/page.tsx for session-independent polling + correct
terminal state map. Author and run all TEST-FE-054 categories.
No backend changes, no deploy, no commit without user approval.

## INLINED CONTRACTS (do not re-read specs unless resolving ambiguity)

Backend status values (from FE-UI-053 backend gate):
  processing   → {status:'processing', company_research:null}
  failed       → {status:'failed', company_research:null}
  completed    → {status:'completed', ...research fields}
  not_generated → {status:'not_generated', company_research:null}

API methods (src/frontend/api/methods.ts — verify symbols exist, no changes expected):
  getCompanyResearch(jobId)       → CompanyResearchResult|null  (completed-only; collapses all else to null)
  getCompanyResearchStatus(jobId) → {status:string, data:CompanyResearchResult|null}  (status-aware; use this)
  fetchCompanyResearch(data)      → AsyncTaskResponse  (fires POST /fetch; returns immediately)

## CURRENT PAGE STATE (src/frontend/app/applications/[id]/company-research/page.tsx)

Bugs to fix — symbols (verify; lines may have drifted):
  BUG-1 Mount useEffect (~L20) calls api.getCompanyResearch() — collapses processing
    to null, can't resume polling after reload/navigation.
  BUG-2 Poll loop lives inside handleTrigger closure (~L40) — lost on unmount.
  BUG-3 Terminal branch (~L61) treats 'not_generated' as failure → setError() called.

## STEP 1 — Refactor page.tsx (R1–R4)

R1 + R2: Extract status-keyed poll effect.
  - Add state: const [status, setStatus] = useState<string|null>(null)
  - Mount effect: call api.getCompanyResearchStatus(jobId) (NOT getCompanyResearch).
    Set status from response. If completed, set research from data. If failed, set
    error. If not_generated, leave status as 'not_generated'. If processing, set
    status='processing' (poll effect fires automatically).
  - Poll effect: useEffect keyed on [status, jobId]. When status==='processing':
    start interval (10s). Each tick: call getCompanyResearchStatus → update status.
    On completed: setResearch(data), setStatus('completed'). On failed: setError,
    setStatus('failed'). Cleanup: clearInterval on unmount or status change.
  - handleTrigger: POST only via fetchCompanyResearch → on success setStatus('processing').
    Do NOT own the poll loop. setTriggering wraps only the POST call.

R3: Terminal state map.
  completed  → render research card (existing JSX)
  failed     → render error div (existing JSX, already styled)
  processing → render spinner + pollMessage (existing JSX, already present)
  not_generated → render idle card with "Research this company" button. NO setError.
    FIX: remove not_generated from the error branch; it is the default idle state.

R4: Cap + message.
  Poll effect tracks attempt count (ref, not state — avoids re-render). At 30
  attempts (5 min): clearInterval, setStatus('timed_out'),
  setPollMessage('Still running — refresh later'). Do NOT cancel server job.
  Render timed_out same as processing idle (button re-enabled, poll message shown).

## STEP 2 — Author frontend tests then make them pass

### TEST CATEGORY A: mount_polling → SC1, SC5
File: src/frontend/tests/ui/unit/CompanyResearchPage.test.tsx
Mock: vi.mock('../../../../api/methods') + vitest fake timers (vi.useFakeTimers)

test_mount_processing_starts_polling
  - Mock getCompanyResearchStatus: first call → {status:'processing'}, second → {status:'completed', data:{...}}.
  - Render component. Assert: after first render, no research card.
  - Advance timers 10s. Assert: getCompanyResearchStatus called again.
  - Advance timers 10s. Assert: research card rendered (company name visible). → SC1, SC5

test_poll_cleanup_on_unmount
  - Mock: always returns {status:'processing'}.
  - Render → advance 5s → unmount.
  - Advance 15s more. Assert: getCompanyResearchStatus call count frozen after unmount. → SC5

Run: cd src/frontend && npx vitest run --config vitest.config.ts \
  tests/ui/unit/CompanyResearchPage.test.tsx -t "mount"
Pass: both green.

### TEST CATEGORY B: remount_resume → SC1, SC2
File: src/frontend/tests/ui/unit/CompanyResearchPage.test.tsx

test_remount_mid_run_resumes
  - Render (GET=processing) → unmount → remount.
  - Assert: getCompanyResearchStatus called again on remount (no POST fired).
  - Advance timers to completed. Assert: research card rendered. → SC1

test_navigate_away_and_return
  - Render (GET=processing) → unmount (navigate away) → remount (return).
  - Assert: polling resumes from server status; completes without fetchCompanyResearch
    being called. → SC2

Run: cd src/frontend && npx vitest run --config vitest.config.ts \
  tests/ui/unit/CompanyResearchPage.test.tsx -t "remount|navigate"
Pass: both green.

### TEST CATEGORY C: not_generated_cta → SC3
File: src/frontend/tests/ui/unit/CompanyResearchPage.test.tsx

test_not_generated_renders_cta
  - Mock getCompanyResearchStatus → {status:'not_generated'}.
  - Render. Assert: "Research this company" button visible (data-testid="research-company-btn").
  - Assert: NO element with role="alert" or error class rendered.
  - Assert: error state variable not set (no error div present). → SC3

Run: cd src/frontend && npx vitest run --config vitest.config.ts \
  tests/ui/unit/CompanyResearchPage.test.tsx -t "not_generated"
Pass: green.

### TEST CATEGORY D: terminal_states → SC4
File: src/frontend/tests/ui/unit/CompanyResearchPage.test.tsx

test_failed_renders_error
  - Mock → {status:'failed'}. Render.
  - Assert: error div rendered (contains error text). Assert: no research card. → SC4

test_completed_renders_card
  - Mock → {status:'completed', data:{company_name:'Acme',...}}.
  - Render. Assert: company name visible. Assert: no error. Assert: no poll timer
    advances needed (completed is terminal on mount). → SC4

Run: cd src/frontend && npx vitest run --config vitest.config.ts \
  tests/ui/unit/CompanyResearchPage.test.tsx -t "terminal|failed|completed"
Pass: both green.

## STEP 3 — Full suite
cd src/frontend && npm run typecheck && npm run test:unit && npm run test:integration && npm run test:e2e
All green (no regressions).

## DEFINITION OF DONE
- [ ] BUG-1,2,3 fixed; poll loop in status-keyed effect; mount uses getCompanyResearchStatus.
- [ ] FE-UI-054 SC1–SC6 all proven by passing tests.
- [ ] typecheck + unit + integration + e2e green.
- [ ] No commit, no deploy without explicit user approval.
