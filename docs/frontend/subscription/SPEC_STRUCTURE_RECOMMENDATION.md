# Subscription Implementation — Recommended Spec Structure

**Current Problem:** Single 1,367-line spec document creates context loss and implementation confusion.

**Solution:** Split into focused, self-contained prompts tied to test groups.

---

## Proposed Document Structure

### Tier 1: Architecture & Patterns (Single Document)

**File:** `SUBSCRIPTION_ARCHITECTURE.md` (NEW - 800 lines)

**Contents:**
- Request-response pipeline diagram
- Shared data models (User, Usage, Subscription, ApiError) with full code
- DynamoDB table schemas and GSI definitions
- API endpoints reference table
- Error handling strategy and codes
- Cognito JWT extraction pattern
- CORS security model
- Lambda environment variables and secrets
- CDK infrastructure overview

**Purpose:** Read ONCE, reference always. Architecture foundation for all implementation groups.

**Scope:** ~30 minutes to read + understand

---

### Tier 2: Implementation Group Prompts (Per Group)

**Structure:**

```
SUBSCRIPTION_IMPL_GROUP_1.md  (Trial & Quota)
SUBSCRIPTION_IMPL_GROUP_2.md  (Checkout Flow)
SUBSCRIPTION_IMPL_GROUP_3.md  (Subscription Lifecycle)
SUBSCRIPTION_IMPL_GROUP_4.md  (Webhooks & Billing)
SUBSCRIPTION_IMPL_GROUP_5.md  (Portal & Security)
```

**Each Group Prompt Contains:**
1. **Group Overview** — What tests must pass (5 min read)
2. **Spec Details** — Each sub-spec (S-XXX.Y) with:
   - Plain language description
   - Pseudo-code
   - Test file references (unit, integration, E2E, regression)
   - Payload examples
   - Error cases
3. **Verification Checklist** — Exactly how to validate each spec is 100% met
4. **Integration Points** — How this group connects to others
5. **File Locations** — Exact paths for code to be written

**Group 1 Size:** ~400 lines (digestible in one context)
**Total for All 5:** ~2,000 lines (split across agent/developer contexts)

---

### Tier 3: Verification & Validation (Single Document)

**File:** `IMPLEMENTATION_VERIFICATION.md` (NEW - 1,000 lines)

**Contents:**
- Checklist for each feature (F-SUB-001 through F-SUB-021)
- Code coverage metrics target (>80%)
- Integration test scenarios
- Manual validation procedures
- Pre-deployment checklist
- Rollback procedures

**Purpose:** After implementation, use to verify 100% completeness.

---

## Migration Plan

### Phase 1: Architecture (Read Once)
```
Read: SUBSCRIPTION_ARCHITECTURE.md
Time: 30 minutes
Output: Understanding of data models, patterns, security
Action: No code changes yet
```

### Phase 2: Group 1 Implementation (Trial & Quota)
```
Read: SUBSCRIPTION_IMPL_GROUP_1.md
Tests: npm run test:unit -- trial.test.ts
Time: 2-4 hours
Output: S-001.1, S-001.2, S-001.3 implemented
Verify: All unit tests F-SUB-001, 002, 003 pass
```

### Phase 3: Group 2 Implementation (Checkout)
```
Read: SUBSCRIPTION_IMPL_GROUP_2.md
Tests: npm run test:unit -- checkout.test.ts
        npm run test:integration -- checkout.integration.test.ts
Time: 3-5 hours
Output: S-002.1, S-002.2, S-002.3 implemented
Verify: Unit + Integration tests pass; no regression in Group 1
```

### Phases 4-5: Remaining Groups
```
Group 3: Subscription Lifecycle (S-003.1, 002, 003)
Group 4: Webhooks & Billing (S-004.1 through S-004.7)
Group 5: Portal & Security (S-005.1, 002, 003)

Each follows same pattern:
  1. Read group prompt
  2. Run tests
  3. Implement until tests pass
  4. Verify no regressions in prior groups
```

### Phase 6: Full System Validation
```
Read: IMPLEMENTATION_VERIFICATION.md
Tests: npm run test:coverage
        npm run test:e2e
        npm run test:regression
Time: 1-2 hours
Output: 129/129 tests pass, >80% coverage, E2E flows work
Verify: Production readiness checklist complete
```

---

## Document Content Map

| Document | Lines | Audience | When to Read | Frequency |
|----------|-------|----------|--------------|-----------|
| SUBSCRIPTION_ARCHITECTURE.md | 800 | Developers, Architects | Once at start | Refer as needed |
| SUBSCRIPTION_IMPL_GROUP_1.md | 400 | Developers (Group 1) | Before implementing Group 1 | Once |
| SUBSCRIPTION_IMPL_GROUP_2.md | 400 | Developers (Group 2) | After Group 1 complete | Once |
| SUBSCRIPTION_IMPL_GROUP_3.md | 400 | Developers (Group 3) | After Group 2 complete | Once |
| SUBSCRIPTION_IMPL_GROUP_4.md | 400 | Developers (Group 4) | After Group 3 complete | Once |
| SUBSCRIPTION_IMPL_GROUP_5.md | 400 | Developers (Group 5) | After Group 4 complete | Once |
| IMPLEMENTATION_VERIFICATION.md | 1000 | QA, DevOps, Architects | After implementation | Once per feature |
| SUBSCRIPTION_FEATURE_TEST_PROMPT.md | 1566 | Reference only | If clarifying test specs | As needed |

**Total Revised:** ~5,200 lines split into 8 focused documents
**Previous:** 1,367 + 1,566 + 104 = 3,037 lines in 3 documents

---

## Benefits of This Structure

### For Implementation (Developer)
✅ Read only relevant group prompt (400 lines vs 1,367 lines)
✅ Clear test files to run after each spec
✅ Specific verification steps for each feature
✅ No decision paralysis about scope
✅ Easy to spot missing pieces (checklist-driven)

### For Verification (QA/Architect)
✅ Dedicated verification document with criteria
✅ Can validate 100% completeness systematically
✅ Clear integration test scenarios
✅ Performance and load testing guidance
✅ Rollback procedures documented

### For Maintenance
✅ Update one group without affecting others
✅ Architecture doc is stable reference
✅ Easy to onboard new team members
✅ Clear separation of concerns

---

## Example: Group 1 Prompt Structure

```markdown
# Subscription Implementation — Group 1: Trial & Quota Foundation

## Overview
This group implements the core trial and quota validation logic that gates
all other features. Specs: S-001.1, S-001.2, S-001.3

Tests that MUST pass:
  ✓ npm run test:unit -- trial.test.ts (F-SUB-001, 002, 003)

Estimated time: 2-4 hours

---

## Architecture Prerequisite
Before starting, read SUBSCRIPTION_ARCHITECTURE.md sections:
  - "Request-Response Pipeline" (understand Lambda flow)
  - "Shared Data Models" (User, Usage models)
  - "DynamoDB Tables" (careervp-users, careervp-usage)

---

## S-001.1: Trial Activation on Sign-Up

### What It Does
When a new user registers, a 14-day trial is activated with 3 application credits.

### Test File
- Unit: src/frontend/tests/unit/trial.test.ts (case: F-SUB-001)
- Payload: src/frontend/tests/payloads/trial-active.json

### Implementation Spec
[Detailed pseudo-code, errors, preconditions]

### Verification Checklist
- [ ] Unit test F-SUB-001 passes
- [ ] DynamoDB User record has `created_at = now()`
- [ ] DynamoDB Usage record has `remaining = 3`
- [ ] Cognito sign-up hook calls activate_trial()
- [ ] Coverage: activate_trial() is 100% covered

### Where to Implement
- Function: `src/backend/careervp/logic/subscription_service.py::activate_trial()`
- Tests validate: `src/frontend/tests/unit/trial.test.ts::F-SUB-001`

---

## S-001.2: Check Trial and Quota

[Similar structure]

---

## Integration Points
- S-001 blocks all other features (must complete first)
- S-002 (Checkout) depends on check_trial_and_quota()
- All job creation endpoints call check_trial_and_quota()

---

## Pre-Implementation Checklist
- [ ] Read SUBSCRIPTION_ARCHITECTURE.md sections above
- [ ] Understand User and Usage data models
- [ ] Know DynamoDB table names and structure
- [ ] Understand trial expiry calculation (created_at + 14 days)
- [ ] Understand credit deduction logic (remaining - 1, never below 0)

---

## Post-Implementation Checklist (100% Validation)
- [ ] npm run test:unit -- trial.test.ts (all tests pass)
- [ ] npm run test:coverage (>80% for subscription_service.py)
- [ ] Manual: Create test user, verify DynamoDB records
- [ ] Manual: Attempt job creation as trial user, verify access granted
- [ ] Manual: Create 3 jobs, verify remaining goes 3→0
- [ ] Manual: Attempt 4th job, verify 403 trial_exhausted
- [ ] Regression: No changes to existing /jobs endpoint behavior
- [ ] Code review: activate_trial() and check_trial_and_quota() reviewed

---

## Time Box
- Reading: 20 minutes
- Implementation: 1.5-2 hours
- Testing & verification: 0.5-1 hour
- Total: 2-4 hours
```

---

## Implementation: Creating These Documents

To create this split:

1. **Extract architecture:**
   - Take core sections from SUBSCRIPTION_IMPLEMENTATION_SPECS.md
   - Create new SUBSCRIPTION_ARCHITECTURE.md
   - Make it a standalone reference

2. **Create 5 group prompts:**
   - S-001 (Trial) → SUBSCRIPTION_IMPL_GROUP_1.md
   - S-002 (Checkout) → SUBSCRIPTION_IMPL_GROUP_2.md
   - S-003 (Lifecycle) → SUBSCRIPTION_IMPL_GROUP_3.md
   - S-004 (Webhooks) → SUBSCRIPTION_IMPL_GROUP_4.md
   - S-005 (Portal) → SUBSCRIPTION_IMPL_GROUP_5.md

3. **Create verification doc:**
   - IMPLEMENTATION_VERIFICATION.md with detailed checklists
   - One section per feature
   - Test commands and expected outcomes

4. **Archive/deprecate:**
   - Mark SUBSCRIPTION_IMPLEMENTATION_SPECS.md as "Reference Archive"
   - Keep for historical context, but link to new structure

---

## Recommendation

**Implement this split structure BEFORE starting backend implementation.**

Why?
- Prevents context loss during multi-day implementation
- Clear stopping points between groups
- Easy to validate progress
- Easier to debug if a test fails (know which group/spec broke it)
- New team members can onboard to a single group

