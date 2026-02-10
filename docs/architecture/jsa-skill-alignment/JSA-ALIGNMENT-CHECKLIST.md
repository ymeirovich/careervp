# JSA Skill Alignment - Implementation Checklist

**Document Version:** 1.0.0
**Date:** 2026-02-09
**Related Documents:**
- `docs/architecture/jsa-skill-alignment/JSA-Skill-Alignment-Plan.md`
- `docs/specs/05-jsa-skill-alignment.md`
- `docs/tasks/05-jsa-skill-alignment.md`

---

## Validation Checklist

This checklist tracks implementation progress against requirements from JSA-Skill-Alignment-Plan.md.

### Phase 1: Critical Fixes (Week 1-2)

#### VPR Prompt Enhancement (VPR-001)

| Req ID | Requirement | Status | Test ID | Evidence |
|--------|-------------|--------|---------|----------|
| VPR-001 | 6-stage methodology | [ ] | TEST-VPR-001 | 6 stages in prompt |
| VPR-001 | Stage 1: Company & Role Research | [ ] | TEST-VPR-001a | 3-5 strategic priorities, 5-7 criteria |
| VPR-001 | Stage 2: Candidate Analysis | [ ] | TEST-VPR-001b | Career narrative, 3-5 differentiators |
| VPR-001 | Stage 3: Alignment Mapping | [ ] | TEST-VPR-001c | Explicit table creation |
| VPR-001 | Stage 4: Self-Correction | [ ] | TEST-VPR-002 | Meta-review questions |
| VPR-001 | Stage 6: Final Meta Evaluation | [ ] | TEST-VPR-003 | "20% more persuasive" |
| VPR-001 | Internal output markers | [ ] | TEST-VPR-004 | "OUTPUT (Internal)" |
| VPR-001 | Anti-AI detection preserved | [ ] | VPR-AN1 | Banned words present |
| VPR-001 | Fact verification preserved | [ ] | VPR-FV1 | Checklist present |

#### CV Tailoring Enhancement (CVT-001)

| Req ID | Requirement | Status | Test ID | Evidence |
|--------|-------------|--------|---------|----------|
| CVT-001 | 3-step verification | [ ] | TEST-CVT-001 | 3 steps in prompt |
| CVT-001 | STEP 1: Keyword Mapping | [ ] | TEST-CVT-001a | 12-18 keywords |
| CVT-001 | STEP 2: Self-Correction | [ ] | TEST-CVT-002 | ATS score 1-10 |
| CVT-001 | Verification Check 1 (ATS) | [ ] | TEST-CVT-004 | ATS keyword match |
| CVT-001 | Verification Check 2 (HM) | [ ] | TEST-CVT-005 | Hiring manager alignment |
| CVT-001 | STEP 3: Final Output | [ ] | TEST-CVT-003 | ATS >= 8 |
| CVT-001 | `company_keywords` param | [ ] | TEST-CVT-006 | Placeholder present |
| CVT-001 | `vpr_differentiators` param | [ ] | TEST-CVT-007 | Placeholder present |
| CVT-001 | CAR/STAR format | [ ] | TEST-CVT-009 | Action verb + metric |

#### Cover Letter Enhancement (CL-001)

| Req ID | Requirement | Status | Test ID | Evidence |
|--------|-------------|--------|---------|----------|
| CL-001 | Handler file exists | [ ] | TEST-CL-009 | cover_letter_handler.py |
| CL-001 | Reference Class Priming | [ ] | TEST-CL-001 | Priming step present |
| CL-001 | Paragraph 1 (Hook) | [ ] | TEST-CL-002 | 80-100 words |
| CL-001 | Paragraph 2 (Proof Points) | [ ] | TEST-CL-003 | 120-140 words |
| CL-001 | Paragraph 3 (Close) | [ ] | TEST-CL-006 | 60-80 words |
| CL-001 | 3 non-negotiable requirements | [ ] | TEST-CL-007 | Requirements specified |
| CL-001 | Claim + Proof structure | [ ] | TEST-CL-008 | Structure present |
| CL-001 | Anti-AI detection | [ ] | CL-AI1 | Banned words present |
| CL-001 | Word count enforcement | [ ] | CL-WC1 | < 400 words |

#### Gap Analysis Enhancement (GA-001)

| Req ID | Requirement | Status | Test ID | Evidence |
|--------|-------------|--------|---------|----------|
| GA-001 | lambda_handler exists | [ ] | TEST-GA-008 | Function present |
| GA-001 | [CV IMPACT] tag | [ ] | TEST-GA-001 | Tag present |
| GA-001 | [INTERVIEW/MVP ONLY] tag | [ ] | TEST-GA-002 | Tag present |
| GA-001 | Max 10 questions | [ ] | TEST-GA-003 | Constraint present |
| GA-001 | recurring_themes param | [ ] | TEST-GA-004 | Parameter present |
| GA-001 | SKIP THESE TOPICS | [ ] | TEST-GA-005 | Instruction present |
| GA-001 | Strategic Intent | [ ] | TEST-GA-006 | Field present |
| GA-001 | Priority levels | [ ] | TEST-GA-007 | CRITICAL/IMPORTANT/OPTIONAL |
| GA-001 | Powertools decorators | [ ] | TEST-GA-009 | @logger, @tracer |

### Phase 2: Missing Features (Week 3-4)

#### Interview Prep Generator (IP-001)

| Req ID | Requirement | Status | Test ID | Evidence |
|--------|-------------|--------|---------|----------|
| IP-001 | interview_prep_handler.py | [ ] | TEST-IP-001 | File exists |
| IP-001 | interview_prep.py | [ ] | TEST-IP-002 | Logic exists |
| IP-001 | STAR format | [ ] | TEST-IP-003 | Format required |
| IP-001 | 4 categories | [ ] | TEST-IP-004 | Categories present |
| IP-001 | 10-15 questions | [ ] | TEST-IP-005 | Target present |
| IP-001 | Questions to ask | [ ] | TEST-IP-006 | Section present |
| IP-001 | Salary guidance | [ ] | IP-SAL1 | Guidance present |
| IP-001 | Pre-interview checklist | [ ] | IP-CHK1 | Checklist present |

#### Quality Validator (QV-001)

| Req ID | Requirement | Status | Test ID | Evidence |
|--------|-------------|--------|---------|----------|
| QV-001 | quality_validator.py | [ ] | TEST-QV-001 | File exists |
| QV-001 | Fact verification | [ ] | TEST-QV-002 | Check present |
| QV-001 | ATS compatibility | [ ] | TEST-QV-003 | Check present |
| QV-001 | Anti-AI detection | [ ] | TEST-QV-004 | Check present |
| QV-001 | Cross-document consistency | [ ] | TEST-QV-005 | Check present |
| QV-001 | Completeness check | [ ] | QV-CMP1 | Word/section counts |
| QV-001 | Language quality | [ ] | QV-LANG1 | Grammar/tone check |

#### Knowledge Base (KB-001)

| Req ID | Requirement | Status | Test ID | Evidence |
|--------|-------------|--------|---------|----------|
| KB-001 | Table in CDK | [ ] | TEST-KB-001 | Table defined |
| KB-001 | Repository exists | [ ] | TEST-KB-002 | File exists |
| KB-001 | recurring_themes type | [ ] | TEST-KB-003 | Type supported |
| KB-001 | gap_responses type | [ ] | TEST-KB-004 | Type supported |
| KB-001 | differentiators type | [ ] | KB-DIF1 | Type supported |
| KB-001 | userEmail partition key | [ ] | KB-PK1 | PK defined |
| KB-001 | knowledgeType sort key | [ ] | KB-SK1 | SK defined |
| KB-001 | TTL configured | [ ] | KB-TTL1 | TTL present |

---

## Test Execution

### Run All JSA Alignment Tests

```bash
# From project root
cd src/backend
PYTHONPATH=$(pwd) uv run pytest ../../tests/jsa_skill_alignment/ -v

# Or run specific test files
PYTHONPATH=$(pwd) uv run pytest ../../tests/jsa_skill_alignment/test_vpr_alignment.py -v
PYTHONPATH=$(pwd) uv run pytest ../../tests/jsa_skill_alignment/test_cv_tailoring_alignment.py -v
PYTHONPATH=$(pwd) uv run pytest ../../tests/jsa_skill_alignment/test_cover_letter_alignment.py -v
PYTHONPATH=$(pwd) uv run pytest ../../tests/jsa_skill_alignment/test_gap_analysis_alignment.py -v
PYTHONPATH=$(pwd) uv run pytest ../../tests/jsa_skill_alignment/test_interview_prep_alignment.py -v
PYTHONPATH=$(pwd) uv run pytest ../../tests/jsa_skill_alignment/test_quality_validator_alignment.py -v
PYTHONPATH=$(pwd) uv run pytest ../../tests/jsa_skill_alignment/test_knowledge_base_alignment.py -v
```

### Validate Test Mapping

```bash
python tests/jsa_skill_alignment/test_mapping.py
```

### Current Test Status

Based on initial run (2026-02-09):

| Component | Tests Passing | Tests Failing | Gap Identified |
|-----------|---------------|---------------|----------------|
| VPR | 5 | 7 | Missing 6-stage methodology |
| CV Tailoring | TBD | TBD | - |
| Cover Letter | TBD | TBD | - |
| Gap Analysis | TBD | TBD | - |
| Interview Prep | TBD | TBD | Files not yet created |
| Quality Validator | TBD | TBD | Files not yet created |
| Knowledge Base | TBD | TBD | Files not yet created |

---

## Requirements Traceability

### Test-to-JSA Plan Mapping

| Test ID | JSA Plan Section | Requirement |
|---------|-----------------|-------------|
| TEST-VPR-001 | 3.3 | VPR-001 6-stage |
| TEST-VPR-002 | 3.1 | VPR-001 meta-review |
| TEST-VPR-003 | 3.1 | VPR-001 20% improvement |
| TEST-CVT-001 | 4.3 | CVT-001 3-step |
| TEST-CVT-004 | 4.1 | CVT-001 ATS check |
| TEST-CVT-005 | 4.1 | CVT-001 HM check |
| TEST-CVT-006 | 4.1 | CVT-001 company_keywords |
| TEST-CVT-007 | 4.1 | CVT-001 vpr_differentiators |
| TEST-CL-001 | 5.3 | CL-001 priming |
| TEST-CL-002 | 5.1 | CL-001 Hook |
| TEST-CL-003 | 5.1 | CL-001 Proof Points |
| TEST-CL-009 | 5.1 | CL-001 handler |
| TEST-GA-001 | 6.3 | GA-001 [CV IMPACT] |
| TEST-GA-002 | 6.3 | GA-001 [INTERVIEW/MVP] |
| TEST-GA-003 | 6.3 | GA-001 max 10 |
| TEST-GA-008 | 6.3 | GA-001 handler |
| TEST-IP-001 | 7.1 | IP-001 handler |
| TEST-IP-002 | 7.1 | IP-001 logic |
| TEST-IP-003 | 7.1 | IP-001 STAR |
| TEST-IP-004 | 7.1 | IP-001 4 categories |
| TEST-IP-005 | 7.1 | IP-001 10-15 questions |
| TEST-IP-006 | 7.1 | IP-001 questions to ask |
| TEST-QV-001 | 7.2 | QV-001 file exists |
| TEST-QV-002 | 7.2 | QV-001 fact check |
| TEST-QV-003 | 7.2 | QV-001 ATS check |
| TEST-QV-004 | 7.2 | QV-001 AI check |
| TEST-QV-005 | 7.2 | QV-001 cross-doc |
| TEST-KB-001 | 7.3 | KB-001 CDK table |
| TEST-KB-002 | 7.3 | KB-001 repository |
| TEST-KB-003 | 7.3 | KB-001 recurring_themes |
| TEST-KB-004 | 7.3 | KB-001 gap_responses |

---

## Definition of Done

A JSA alignment task is complete when:

1. [ ] All tests for the component pass
2. [ ] No linting errors (ruff check --fix)
3. [ ] Type checking passes (mypy careervp --strict)
4. [ ] Code follows existing patterns in codebase
5. [ ] Documentation updated (if applicable)
6. [ ] PR created and reviewed

---

## Files Created

| File | Purpose |
|------|---------|
| `docs/specs/05-jsa-skill-alignment.md` | Technical specification |
| `docs/tasks/05-jsa-skill-alignment.md` | Implementation tasks |
| `tests/jsa_skill_alignment/test_vpr_alignment.py` | VPR tests (12 tests) |
| `tests/jsa_skill_alignment/test_cv_tailoring_alignment.py` | CV Tailoring tests (15 tests) |
| `tests/jsa_skill_alignment/test_cover_letter_alignment.py` | Cover Letter tests (18 tests) |
| `tests/jsa_skill_alignment/test_gap_analysis_alignment.py` | Gap Analysis tests (18 tests) |
| `tests/jsa_skill_alignment/test_interview_prep_alignment.py` | Interview Prep tests (11 tests) |
| `tests/jsa_skill_alignment/test_quality_validator_alignment.py` | Quality Validator tests (10 tests) |
| `tests/jsa_skill_alignment/test_knowledge_base_alignment.py` | Knowledge Base tests (11 tests) |
| `tests/jsa_skill_alignment/test_mapping.py` | Test mapping validation |
| `tests/jsa_skill_alignment/__init__.py` | Package init |

**Total Tests Created:** 106+

---

**END OF CHECKLIST**
