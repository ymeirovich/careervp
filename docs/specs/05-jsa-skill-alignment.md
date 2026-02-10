# JSA Skill Alignment Specification

**Spec Version:** 1.0.0
**Date:** 2026-02-09
**Source:** `docs/architecture/jsa-skill-alignment/JSA-Skill-Alignment-Plan.md`
**Status:** Draft

## Table of Contents

1. [Overview](#1-overview)
2. [VPR Prompt Enhancement](#2-vpr-prompt-enhancement)
3. [CV Tailoring Enhancement](#3-cv-tailoring-enhancement)
4. [Cover Letter Enhancement](#4-cover-letter-enhancement)
5. [Gap Analysis Enhancement](#5-gap-analysis-enhancement)
6. [Interview Prep Implementation](#6-interview-prep-implementation)
7. [Quality Validator Implementation](#7-quality-validator-implementation)
8. [Knowledge Base Implementation](#8-knowledge-base-implementation)
9. [API Gateway Updates](#9-api-gateway-updates)
10. [Test Mapping](#10-test-mapping)

---

## 1. Overview

### 1.1 Purpose

This specification defines the technical requirements for aligning CareerVP with the Job Search Assistant (JSA) Skill architecture. The alignment addresses critical gaps in prompt methodology, verification processes, and missing components.

### 1.2 Scope

| Category | Components |
|----------|------------|
| **Prompt Enhancements** | VPR (6-stage), CV Tailoring (3-step), Cover Letter (scaffolded), Gap Analysis (tagged) |
| **New Components** | Interview Prep Generator, Quality Validator Agent, Knowledge Base |
| **Infrastructure** | API Gateway routes, DynamoDB tables |

### 1.3 Requirements Traceability

Each requirement in this spec maps to the JSA-Skill-Alignment-Plan.md sections:

| This Spec Section | JSA Plan Section |
|-------------------|------------------|
| Section 2 | Section 3 (VPR Remediation) |
| Section 3 | Section 4 (CV Tailoring Remediation) |
| Section 4 | Section 5 (Cover Letter Remediation) |
| Section 5 | Section 6 (Gap Analysis Remediation) |
| Section 6 | Section 7.1 (Interview Prep) |
| Section 7 | Section 7.2 (Quality Validator) |
| Section 8 | Section 7.3 (Knowledge Base) |

---

## 2. VPR Prompt Enhancement

### 2.1 Requirement: VPR-001 (6-Stage Methodology)

**Priority:** P0 (Critical)
**Source:** JSA-Skill-Alignment-Plan.md Section 3.1

#### Description

Replace the current direct-output VPR prompt with a 6-stage methodology that includes staged thinking and self-correction.

#### Technical Requirements

| Stage | Internal Output Required | Output to Next Stage |
|-------|-------------------------|---------------------|
| Stage 1 | 3-5 strategic priorities, 5-7 role criteria | Alignment mapping input |
| Stage 2 | Career narrative (1 sentence), 3-5 differentiators | Candidate analysis input |
| Stage 3 | Complete alignment matrix table | Self-correction input |
| Stage 4 | Meta-review notes, refinements made | Final evaluation input |
| Stage 5 | Full structured report | Meta evaluation input |
| Stage 6 | 20% improvement applied | Final JSON output |

#### Implementation Location

- **File:** `src/backend/careervp/logic/prompts/vpr_prompt.py`
- **Function:** `build_vpr_prompt()`
- **Model:** Sonnet 4.5 (per Decision 1.2)

#### Acceptance Criteria

| Criterion | Test ID | Verification |
|-----------|---------|--------------|
| Prompt contains all 6 stages | TEST-VPR-001 | String assertion |
| Meta-review questions present | TEST-VPR-002 | String assertion |
| "20% more persuasive" prompt present | TEST-VPR-003 | String assertion |
| Internal output markers present | TEST-VPR-004 | String assertion |

#### Anti-AI Detection

The existing anti-AI detection rules must be preserved and enhanced:

```python
BANNED_WORDS: list[str] = [
    'leverage', 'delve into', 'landscape', 'robust', 'streamline',
    'utilize', 'facilitate', 'implement', 'cutting-edge', 'best practices',
    'industry-leading', 'game-changer', 'paradigm shift', 'synergy',
]
```

#### Fact Verification

The existing fact verification checklist must be preserved:

```markdown
FACT VERIFICATION CHECKLIST:
- [ ] Is this explicitly stated in CV or gap responses?
- [ ] Are the numbers exact from source?
- [ ] Is the company name/title correct?
- [ ] Are dates accurate?
- [ ] Can I quote the source if questioned?
```

---

## 3. CV Tailoring Enhancement

### 3.1 Requirement: CVT-001 (3-Step Verification)

**Priority:** P0 (Critical)
**Source:** JSA-Skill-Alignment-Plan.md Section 4.1

#### Description

Replace the current utility-based CV tailoring with a 3-step verification methodology.

#### Technical Requirements

| Step | Purpose | Internal Output |
|------|---------|-----------------|
| Step 1 | Analysis & Keyword Mapping | Draft tailored CV, 12-18 keywords extracted |
| Step 2 | Self-Correction & Verification | ATS score (1-10), missing keywords list, hiring manager alignment check |
| Step 3 | Final Output | Revised CV with ATS score >= 8 |

#### Implementation Location

- **File:** `src/backend/careervp/logic/cv_tailoring_prompt.py`
- **New Parameters:**
  - `company_keywords: list[str]` - From company research
  - `vpr_differentiators: list[str]` - Top 3 from VPR response

#### Acceptance Criteria

| Criterion | Test ID | Verification |
|-----------|---------|--------------|
| STEP 1 marker present | TEST-CVT-001 | String assertion |
| STEP 2 marker present | TEST-CVT-002 | String assertion |
| STEP 3 marker present | TEST-CVT-003 | String assertion |
| Verification Check 1 (ATS) present | TEST-CVT-004 | String assertion |
| Verification Check 2 (Hiring Manager) present | TEST-CVT-005 | String assertion |
| `{company_keywords}` placeholder present | TEST-CVT-006 | String assertion |
| `{vpr_differentiators}` placeholder present | TEST-CVT-007 | String assertion |
| ATS score >= 8 requirement present | TEST-CVT-008 | String assertion |
| CAR/STAR format required | TEST-CVT-009 | String assertion |

#### ATS Formatting Rules

```markdown
ATS FORMATTING RULES:
- Standard headers: "Professional Experience", "Education", "Skills"
- Simple bullets (•)
- No tables or columns
- Standard fonts only
- Length: 1-2 pages (max 3 pages)
```

---

## 4. Cover Letter Enhancement

### 4.1 Requirement: CL-001 (Reference Class Priming)

**Priority:** P0 (Critical)
**Source:** JSA-Skill-Alignment-Plan.md Section 5.1

#### Description

Add reference class priming step before drafting to establish quality benchmark.

#### Technical Requirements

| Element | Requirement |
|---------|-------------|
| Reference Class Priming | Internal description of exemplary cover letter structure/tone |
| Paragraph 1 (Hook) | 80-100 words, UVP + company reference |
| Paragraph 2 (Proof Points) | 120-140 words, 3 requirements × (Claim + Proof) |
| Paragraph 3 (Close) | 60-80 words, CTA + time-saver positioning |

#### Implementation Location

- **New File:** `src/backend/careervp/handlers/cover_letter_handler.py`
- **File:** `src/backend/careervp/logic/prompts/cover_letter_prompt.py`

#### API Endpoint

| Property | Value |
|----------|-------|
| Method | POST |
| Path | /api/cover-letter |
| Handler | `cover_letter_handler.handler` |

#### Acceptance Criteria

| Criterion | Test ID | Verification |
|-----------|---------|--------------|
| REFERENCE CLASS PRIMING present | TEST-CL-001 | String assertion |
| Paragraph 1 (The Hook) present | TEST-CL-002 | String assertion |
| Paragraph 2 (The Proof Points) present | TEST-CL-003 | String assertion |
| 80-100 words constraint present | TEST-CL-004 | String assertion |
| 120-140 words constraint present | TEST-CL-005 | String assertion |
| 60-80 words constraint present | TEST-CL-006 | String assertion |
| "top 3 non-negotiable requirements" present | TEST-CL-007 | String assertion |
| "Claim + Proof" structure present | TEST-CL-008 | String assertion |
| Handler file exists | TEST-CL-009 | File existence check |

#### Anti-AI Detection for Cover Letter

```markdown
ANTI-AI DETECTION:
- Natural transitions (not formulaic)
- Vary sentence length (8-25 words)
- Brief personal touch
- Avoid: leverage, delve, robust, streamline
- Use approximations: "nearly 40%" not "39.7%"
```

---

## 5. Gap Analysis Enhancement

### 5.1 Requirement: GA-001 (Contextual Tagging)

**Priority:** P0 (Critical)
**Source:** JSA-Skill-Alignment-Plan.md Section 6.1

#### Description

Add contextual tagging system with [CV IMPACT] and [INTERVIEW/MVP ONLY] labels.

#### Technical Requirements

| Element | Requirement |
|---------|-------------|
| Max Questions | 10 (vs current 3-5) |
| Tag Types | [CV IMPACT], [INTERVIEW/MVP ONLY] |
| Priority Levels | CRITICAL, IMPORTANT, OPTIONAL |
| Memory Awareness | Skip recurring themes from history |
| Strategic Intent | Required for each question |

#### Implementation Location

- **File:** `src/backend/careervp/handlers/gap_handler.py` (complete lambda_handler)
- **File:** `src/backend/careervp/logic/prompts/gap_analysis_prompt.py`

#### API Endpoint

| Property | Value |
|----------|-------|
| Method | POST |
| Path | /api/gap-analysis |
| Handler | `gap_handler.lambda_handler` |

#### Question Format Schema

```markdown
### Question {N}

**Requirement:** [Exact quote from job posting]

**Question:** [Targeted question emphasizing quantification]

**Destination:** [CV IMPACT] or [INTERVIEW/MVP ONLY]

**Strategic Intent:** [Why this is being asked]

**Evidence Gap:** [What's missing from the CV]

**Priority:** CRITICAL | IMPORTANT | OPTIONAL
```

#### Acceptance Criteria

| Criterion | Test ID | Verification |
|-----------|---------|--------------|
| [CV IMPACT] tag present | TEST-GA-001 | String assertion |
| [INTERVIEW/MVP ONLY] tag present | TEST-GA-002 | String assertion |
| "MAXIMUM 10 questions" present | TEST-GA-003 | String assertion |
| "recurring_themes" parameter present | TEST-GA-004 | String assertion |
| "SKIP THESE TOPICS" instruction present | TEST-GA-005 | String assertion |
| "Strategic Intent" field present | TEST-GA-006 | String assertion |
| Priority levels present | TEST-GA-007 | String assertion |
| lambda_handler function exists | TEST-GA-008 | File content check |
| Handler decorated with Powertools | TEST-GA-009 | String assertion |

---

## 6. Interview Prep Implementation

### 6.1 Requirement: IP-001 (Complete Implementation)

**Priority:** P1 (High)
**Source:** JSA-Skill-Alignment-Plan.md Section 7.1

#### Description

Implement full Interview Prep Generator with STAR-formatted responses.

#### Technical Requirements

| Feature | Requirement |
|---------|-------------|
| Predicted Questions | 10-15 across 4 categories |
| Response Format | STAR (Situation, Task, Action, Result) |
| Questions to Ask | 5-7 for interviewer |
| Salary Guidance | Optional |
| Pre-interview Checklist | Required |

#### Categories

1. **Technical Competency** - Role-specific skills
2. **Behavioral/Cultural Fit** - Team dynamics, values
3. **Experience & Background** - Deep-dive on CV
4. **Problem-Solving** - Hypothetical scenarios

#### Implementation Location

| Component | Path |
|-----------|------|
| Prompt | `src/backend/careervp/logic/prompts/interview_prep_prompt.py` |
| Logic | `src/backend/careervp/logic/interview_prep.py` |
| Handler | `src/backend/careervp/handlers/interview_prep_handler.py` |
| CDK | `infra/careervp/api_construct.py` (new endpoint) |

#### API Endpoint

| Property | Value |
|----------|-------|
| Method | POST |
| Path | /api/interview-prep |
| Handler | `interview_prep_handler.handler` |

#### Acceptance Criteria

| Criterion | Test ID | Verification |
|-----------|---------|--------------|
| interview_prep_handler.py exists | TEST-IP-001 | File existence check |
| interview_prep.py exists | TEST-IP-002 | File existence check |
| STAR format required | TEST-IP-003 | String assertion |
| 4 categories present | TEST-IP-004 | String assertion |
| 10-15 questions target present | TEST-IP-005 | String assertion |
| Questions to ask section present | TEST-IP-006 | String assertion |

---

## 7. Quality Validator Implementation

### 7.1 Requirement: QV-001 (6-Check Validation)

**Priority:** P1 (Medium)
**Source:** JSA-Skill-Alignment-Plan.md Section 7.2

#### Description

Implement multi-check validation agent for artifact quality assurance.

#### Technical Requirements

| Check | Description |
|-------|-------------|
| Fact Verification | Cross-reference all claims against source |
| ATS Compatibility | Keyword score calculation |
| Anti-AI Detection | Banned words, patterns check |
| Cross-Document Consistency | CV, VPR, Cover Letter alignment |
| Completeness | Word counts, section counts |
| Language Quality | Spelling, grammar, tone |

#### Implementation Location

- **File:** `src/backend/careervp/logic/quality_validator.py`

#### Integration Point

The Quality Validator should be integrated as the final step in VPR generation flow (per Section 7.2 of JSA Plan).

#### Acceptance Criteria

| Criterion | Test ID | Verification |
|-----------|---------|--------------|
| quality_validator.py exists | TEST-QV-001 | File existence check |
| Fact verification method present | TEST-QV-002 | String assertion |
| ATS compatibility check present | TEST-QV-003 | String assertion |
| Anti-AI detection present | TEST-QV-004 | String assertion |
| Cross-document consistency present | TEST-QV-005 | String assertion |

---

## 8. Knowledge Base Implementation

### 8.1 Requirement: KB-001 (User Memory System)

**Priority:** P1 (Medium)
**Source:** JSA-Skill-Alignment-Plan.md Section 7.3

#### Description

Implement DynamoDB-backed knowledge base for user memory awareness.

#### Technical Requirements

| Element | Specification |
|---------|---------------|
| Table Name | `careervp-knowledge-base` |
| Partition Key | `userEmail` (string) |
| Sort Key | `knowledgeType` (string) |
| TTL | 365 days |

#### Knowledge Types

| Type | Description |
|------|-------------|
| `recurring_themes` | Topics to skip in gap analysis |
| `gap_responses` | Previous gap analysis answers |
| `differentiators` | VPR-identified differentiators |
| `applications_count` | Number of applications submitted |

#### Implementation Location

| Component | Path |
|-----------|------|
| CDK Table | `infra/careervp/api_db_construct.py` |
| DAL | `src/backend/careervp/dal/knowledge_base_repository.py` |
| Logic | `src/backend/careervp/logic/knowledge_base.py` |

#### Acceptance Criteria

| Criterion | Test ID | Verification |
|-----------|---------|--------------|
| Knowledge base table in CDK | TEST-KB-001 | File content check |
| Repository module exists | TEST-KB-002 | File existence check |
| recurring_themes type supported | TEST-KB-003 | String assertion |
| gap_responses type supported | TEST-KB-004 | String assertion |

---

## 9. API Gateway Updates

### 9.1 New Endpoints

| Method | Path | Handler | Phase |
|--------|------|---------|-------|
| POST | /api/cover-letter | cover_letter_handler.handler | Phase 1 |
| POST | /api/gap-analysis | gap_handler.lambda_handler | Phase 1 |
| POST | /api/interview-prep | interview_prep_handler.handler | Phase 2 |

### 9.2 Infrastructure Updates

#### CDK Updates Required

| File | Update |
|------|--------|
| `infra/careervp/api_construct.py` | Add new routes |
| `infra/careervp/api_db_construct.py` | Add knowledge base table |

---

## 10. Test Mapping

### 10.1 Test Directory Structure

```
tests/
  jsa_skill_alignment/
    test_vpr_alignment.py       # Tests for Section 2
    test_cv_tailoring_alignment.py  # Tests for Section 3
    test_cover_letter_alignment.py  # Tests for Section 4
    test_gap_analysis_alignment.py  # Tests for Section 5
    test_interview_prep_alignment.py # Tests for Section 6
    test_quality_validator_alignment.py  # Tests for Section 7
    test_knowledge_base_alignment.py  # Tests for Section 8
```

### 10.2 Test-to-Requirement Mapping

| Test ID | Req ID | Description |
|---------|--------|-------------|
| TEST-VPR-001 | VPR-001 | 6 stages present |
| TEST-VPR-002 | VPR-001 | Meta-review questions |
| TEST-VPR-003 | VPR-001 | 20% improvement prompt |
| TEST-CVT-001 | CVT-001 | STEP 1 present |
| TEST-CVT-002 | CVT-001 | STEP 2 present |
| TEST-CVT-003 | CVT-001 | STEP 3 present |
| TEST-CL-001 | CL-001 | Reference class priming |
| TEST-GA-001 | GA-001 | [CV IMPACT] tag |
| TEST-IP-001 | IP-001 | Handler exists |
| TEST-QV-001 | QV-001 | Validator exists |
| TEST-KB-001 | KB-001 | Table in CDK |

### 10.3 Validation Test Execution

All tests must be executed as part of CI/CD:

```bash
# Run JSA alignment tests
uv run pytest tests/jsa_skill_alignment/ -v

# Required to pass before merge
# All tests must map to requirements in JSA-Skill-Alignment-Plan.md
```

---

## Appendix A: File Changes Summary

| Current File | Change Type | New Content |
|--------------|-------------|-------------|
| `src/backend/careervp/logic/prompts/vpr_prompt.py` | Modify | Add 6-stage methodology |
| `src/backend/careervp/logic/cv_tailoring_prompt.py` | Modify | Add 3-step verification, new parameters |
| `src/backend/careervp/logic/prompts/cover_letter_prompt.py` | Modify | Add scaffolded structure |
| `src/backend/careervp/logic/prompts/gap_analysis_prompt.py` | Modify | Add contextual tagging |
| `src/backend/careervp/handlers/gap_handler.py` | Modify | Add lambda_handler |
| `src/backend/careervp/handlers/cover_letter_handler.py` | Create | New handler |
| `src/backend/careervp/handlers/interview_prep_handler.py` | Create | New handler |
| `src/backend/careervp/logic/interview_prep.py` | Create | New logic |
| `src/backend/careervp/logic/quality_validator.py` | Create | New validator |
| `infra/careervp/api_construct.py` | Modify | Add new endpoints |
| `infra/careervp/api_db_construct.py` | Modify | Add knowledge base table |

---

## Appendix B: Anti-AI Detection Rules (Global)

All prompts must include anti-AI detection rules from Decision 1.6:

1. **Avoid excessive AI phrases** - "In the ever-evolving landscape"
2. **Vary sentence structure** - Mix short and long sentences
3. **Include natural transitions** - Not formulaic connectors
4. **Avoid perfect parallel structure** - Slight variation acceptable

---

**END OF SPECIFICATION**
