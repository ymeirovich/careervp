# CareerVP Comprehensive Refactoring Roadmap

**Generated:** 2026-02-09
**Research Method:** 6-stage parallel scientist analysis with cross-validation
**Status:** READY FOR IMPLEMENTATION

---

## Executive Summary

CareerVP requires a unified refactoring effort addressing **4 interconnected workstreams**:

| Workstream | Raw Hours | Deduplicated | MVP Scope |
|------------|-----------|--------------|-----------|
| JSA Skill Alignment | 60h | 40h | 24h |
| Architecture Review | 56h | 30h | 18h |
| Gap Analysis Remediation | 15h | 12h | 10h |
| Prompt Improvement | 17h | - (included in JSA) | - |
| **TOTAL** | **148h** | **106h** | **54h** |

**Key Finding:** 28% effort savings from deduplication - the 4 workstreams describe the SAME system from different angles.

---

## Critical Dependencies (Must Respect)

```
API_AUTHORIZER (4h) ─┬─→ All deployments blocked
                     │
VPR_6STAGE (8h) ─────┼─→ CV_3STEP (6h) ─→ QUALITY_VALIDATOR (6h)
                     │           │
                     │           └─→ GAP_CV_INTEGRATE (3h)
                     │
                     └─→ GAP_VPR_INTEGRATE (2h)

KB_IMPL (8h) ────────→ GAP_HANDLER (6h) ─→ GAP_INTEGRATIONS (8h)

LLM_CONSOLIDATE (8h) → Prevents fragmentation rework
```

**Critical Path Duration:** 40 hours (minimum sequential time)
**Highest Leverage Item:** VPR_6STAGE - blocks 5 items totaling 35h downstream

---

## Unified Implementation Phases

### Phase 0: Security Foundation (MUST BE FIRST)
**Duration:** 4 hours | **Priority:** P0-BLOCKING

| Task | Hours | Blocks |
|------|-------|--------|
| Add API Authorizer to infrastructure | 4h | All deployments |

**Gate:** Security review passed before any feature work

---

### Phase 1: Foundation (Parallel Track)
**Duration:** 18 hours (can parallelize) | **Priority:** P0

| Task | Hours | Dependencies | Workstream |
|------|-------|--------------|------------|
| LLM Client Consolidation | 8h | None | Architecture |
| Knowledge Base Implementation | 8h | None | JSA |
| Gap Analysis Lambda Handler | 6h | None | Gap Remediation |
| Create 13-knowledge-base task files | 2h | None | Infrastructure |

**Parallel Execution:** 3 developers can complete in ~8 hours elapsed

**Gate:** Foundation patterns established, KB operational

---

### Phase 2: Critical Path (Sequential)
**Duration:** 20 hours | **Priority:** P0

| Task | Hours | Dependencies | Workstream |
|------|-------|--------------|------------|
| VPR 6-Stage Methodology | 8h | Phase 1 | JSA + Prompts |
| CV Tailoring 3-Step Verification | 6h | VPR_6STAGE | JSA + Prompts |
| Gap Handler Completion | 6h | KB_IMPL | Gap Remediation |

**Gate:** Core methodology working, tests passing

---

### Phase 3: Extended Features (Parallel Track)
**Duration:** 22 hours | **Priority:** P1

| Task | Hours | Dependencies | Workstream |
|------|-------|--------------|------------|
| Cover Letter Handler + Prompt Fix | 8h | VPR_6STAGE | JSA |
| Gap-VPR Integration | 2h | GAP_HANDLER | Gap Remediation |
| Gap-CV Integration | 3h | CV_3STEP, GAP_HANDLER | Gap Remediation |
| Gap-Cover Letter Integration | 3h | COVER_LETTER | Gap Remediation |
| Quality Validator | 6h | VPR, CV, CL | JSA |

**Gate:** All features complete, integrations working

---

### Phase 4: Final Features (Parallel/Deferrable)
**Duration:** 22 hours | **Priority:** P1/P2

| Task | Hours | Priority | Status |
|------|-------|----------|--------|
| Interview Prep | 16h | P1 | DEFER TO V2 (per prompt analysis) |
| DynamoDB God Class Refactor | 10h | P2 | Can defer (tech debt) |
| Deep Analysis Prerequisite | 6h | P2 | Complete 10 dev runs |
| FVS Enable for VPR | 2h | P2 | Quick fix |

---

## MVP vs V2 Scope

### V1 MVP (54 hours / 4-5 weeks)

| Item | Hours | Justification |
|------|-------|---------------|
| API_AUTHORIZER | 4h | Security non-negotiable |
| VPR_6STAGE | 8h | Core methodology |
| CV_3STEP | 6h | User-facing quality |
| GAP_LAMBDA + GAP_HANDLER | 10h | Complete pipeline |
| KB_IMPL | 8h | Foundation for memory |
| LLM_CONSOLIDATE | 8h | Prevent tech debt |
| QUALITY_VALIDATOR | 6h | Output quality |
| Infrastructure (13-KB tasks) | 3h | Documentation |
| **TOTAL** | **54h** | |

### V2 Deferred (42 hours)

| Item | Hours | Reason for Deferral |
|------|-------|---------------------|
| INTERVIEW_PREP | 16h | Cost concern (+241% per prompt analysis) |
| COVER_LETTER_FULL | 8h | 60% aligned, lower priority |
| DYNAMO_REFACTOR | 10h | Tech debt, not blocking |
| DEEP_ANALYSIS_FIX | 6h | Prerequisite, not blocking |
| FVS_ENABLE | 2h | Nice-to-have |

---

## Risk Assessment

| Rank | Risk | Impact | Likelihood | Mitigation |
|------|------|--------|------------|------------|
| 1 | Missing API Authorizer | CRITICAL | CERTAIN | Do FIRST, block all deploys |
| 2 | VPR Critical Path | HIGH | HIGH | Senior dev, design doc first |
| 3 | DAL God Class | MEDIUM | HIGH | Add tests before refactor |
| 4 | LLM Fragmentation | MEDIUM | MEDIUM | Consolidate before new features |
| 5 | Prompt Token Growth | LOW | MEDIUM | Monitor costs, use filtering |

---

## Test Coverage Status

| Component | Tests | Passing | Failing | TBD |
|-----------|-------|---------|---------|-----|
| VPR | 12 | 5 | 7 | 0 |
| CV Tailoring | 15 | TBD | TBD | 15 |
| Cover Letter | 18 | TBD | TBD | 18 |
| Gap Analysis | 18 | TBD | TBD | 18 |
| Interview Prep | 11 | 0 | 11 | 0 |
| Quality Validator | 10 | 0 | 10 | 0 |
| Knowledge Base | 11 | 0 | 11 | 0 |
| **TOTAL** | **95** | **5** | **39** | **51** |

**Strategy:** Use failing tests as implementation guide (TDD approach)

---

## Architecture Scores

| Metric | Current | Target | Gap |
|--------|---------|--------|-----|
| Overall Score | 2.7/5.0 | 4.0/5.0 | -1.3 |
| JSA Alignment | 62.5% | 100% | -37.5% |
| Gap Analysis | 70% | 100% | -30% |
| Prompt Alignment | 40% avg | 100% | -60% |

---

## Recommended Team Allocation

| Role | Assignment | Duration |
|------|------------|----------|
| Senior Dev 1 | VPR + CV Critical Path | 3 weeks |
| Senior Dev 2 | Architecture + LLM Consolidation | 2 weeks |
| Dev 3 | Knowledge Base + Gap Integrations | 2 weeks |
| Dev 4 | Cover Letter + Quality Validator | 2 weeks |

**Elapsed Time:**
- With 1 developer: 12-14 weeks
- With 2 developers: 6-8 weeks (parallel tracks)
- With 3 developers: 4-5 weeks (optimal)
- With 4 developers: 3-4 weeks (diminishing returns)

---

## Immediate Next Steps

1. **TODAY:** Create API Authorizer (4h) - Security gate
2. **TODAY:** Create 13-knowledge-base task directory (2h)
3. **WEEK 1:** Start Phase 1 parallel tracks (KB, LLM, Gap Handler)
4. **WEEK 2:** Begin VPR 6-Stage (critical path start)
5. **WEEK 3-4:** Complete CV, Cover Letter, Integrations
6. **WEEK 5:** Quality Validator + Final testing

---

## Related Documents

- [JSA-Skill-Alignment-Plan.md](../architecture/jsa-skill-alignment/JSA-Skill-Alignment-Plan.md)
- [Architecture Review](../architecture/architecture-review/)
- [Gap Analysis Remediation](./00-gap-remediation/)
- [Prompt Improvement Report](../architecture/prompt-improvement/PROMPT_GAP_ANALYSIS_REPORT.md)
- [05-jsa-skill-alignment.md](./05-jsa-skill-alignment.md) - Detailed task breakdown

---

**[PROMISE:RESEARCH_COMPLETE]**

*This roadmap synthesizes 5 parallel research stages with cross-validation. Total analysis time: ~25 minutes across 6 scientist agents.*
