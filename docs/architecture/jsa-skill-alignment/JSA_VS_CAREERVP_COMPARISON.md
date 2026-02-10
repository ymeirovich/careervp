# JSA vs CareerVP Feature Comparison

**Date:** 2026-02-09
**Purpose:** Identify gaps and divergences between JSA Skill architecture and current CareerVP specifications

---

## Executive Summary

| Feature | CareerVP Status | JSA Adds | Verdict |
|---------|----------------|----------|---------|
| **VPR** | Implemented | 6-stage methodology + meta-review | **ENHANCE** |
| **CV Tailoring** | Implemented | 3-step verification + ATS scoring | **ENHANCE** |
| **Cover Letter** | Implemented | Reference class priming + scaffolded proof points | **ENHANCE** |
| **Gap Analysis** | Implemented | Contextual tagging + memory awareness | **ENHANCE** |
| **Interview Prep** | Specified | Same (STAR format, 4 categories) | **ALIGN** |
| **Quality Validator** | NOT in spec | New multi-check validation | **ADD** |
| **Knowledge Base** | NOT in spec | User memory for recurring themes | **ADD** |

---

## 1. Value Proposition Report (VPR)

### CareerVP Current Specification (F-JOB-005)

| Aspect | Current Specification |
|--------|----------------------|
| **Structure** | Executive Summary, Evidence Matrix, Differentiators, Gap Mitigation, Cultural Fit, Talking Points |
| **Quality** | Zero hallucinations, ATS-optimized, Anti-AI patterns |
| **Length** | 1,500-2,000 words (3-4 pages) |
| **Inputs** | CV facts, Job description, Company research, Gap responses |
| **Prompt** | Single-pass generation |

### JSA Requirements

| Aspect | JSA Adds |
|--------|----------|
| **Stages** | 6-stage methodology with internal outputs |
| **Stage 1** | Company & Role Research (3-5 priorities, 5-7 criteria) |
| **Stage 2** | Candidate Analysis (career narrative, 3-5 differentiators) |
| **Stage 3** | Alignment Mapping (explicit table creation) |
| **Stage 4** | Self-Correction & Meta Review (unsupported claims check) |
| **Stage 5** | Generate Report (existing structure) |
| **Stage 6** | Final Meta Evaluation ("20% more persuasive") |

### Comparison: VPR

| Element | CareerVP | JSA | Action |
|---------|----------|-----|--------|
| Executive Summary | Yes | Keep | PRESERVE |
| Evidence Matrix | Yes | Enhanced | KEEP, add internal output |
| Differentiators | Yes (3-5) | Same | PRESERVE |
| Gap Mitigation | Yes | Keep | PRESERVE |
| Cultural Fit | Yes | Keep | PRESERVE |
| Talking Points | Yes | Keep | PRESERVE |
| Anti-AI Detection | Yes | Same | PRESERVE |
| Fact Verification | Yes | Same | PRESERVE |
| **6-Stage Methodology** | No | **Required** | **ADD** |
| **Meta-Review** | No | Required | **ADD** |
| **Internal Outputs** | No | Required | **ADD** |

### Recommendation for VPR

**Keep existing structure** (all 6 sections), **add** 6-stage methodology as scaffolding that Claude follows before generating output. The final output remains the same.

---

## 2. CV Tailoring

### CareerVP Current Specification (F-JOB-006)

| Aspect | Current Specification |
|--------|----------------------|
| **Optimization** | Prioritize experience, Emphasize skills, ATS formatting |
| **Inputs** | CV facts, Job requirements, VPR differentiators, Company keywords |
| **Format** | Structured form editing, NOT WYSIWYG |
| **Length** | 1-2 pages (max 3) |
| **Quality** | Zero hallucinations, ATS-optimized |

### JSA Requirements

| Aspect | JSA Adds |
|--------|----------|
| **Step 1** | Analysis & Keyword Mapping (12-18 keywords, CAR/STAR format) |
| **Step 2** | Self-Correction & Verification (ATS score 1-10) |
| **Step 3** | Final Output (ATS score >= 8) |
| **Verification 1** | ATS keyword match scoring |
| **Verification 2** | Hiring Manager & Strategy alignment |
| **CAR/STAR** | Action verb + metric + keyword format |

### Comparison: CV Tailoring

| Element | CareerVP | JSA | Action |
|---------|----------|-----|--------|
| Prioritize experience | Yes | Enhanced | PRESERVE |
| ATS optimization | Yes | Same | PRESERVE |
| Keywords from job | Yes | Enhanced (12-18) | KEEP |
| VPR differentiators input | Yes | Same | PRESERVE |
| Structured editing | Yes | Same | PRESERVE |
| Length 1-2 pages | Yes | Same | PRESERVE |
| **3-Step Verification** | No | **Required** | **ADD** |
| **ATS Scoring (1-10)** | No | Required | **ADD** |
| **Hiring Manager Check** | No | Required | **ADD** |
| **CAR/STAR Format** | Implicit | Explicit | **CLARIFY** |

### Recommendation for CV Tailoring

**Keep existing inputs** (CV facts, job requirements, VPR differentiators, company keywords), **add** 3-step verification process with ATS scoring. The output remains the same JSON structure.

---

## 3. Cover Letter

### CareerVP Current Specification (F-JOB-007)

| Aspect | Current Specification |
|--------|----------------------|
| **Structure** | Opening hook, 2-3 body paragraphs, Closing CTA |
| **Inputs** | CV facts, Job requirements, VPR differentiators, Company culture |
| **Length** | Exactly 1 page (max 400 words) |
| **Quality** | Zero hallucinations, Anti-AI, ATS-optimized |
| **Tone** | Professional, matches company culture |

### JSA Requirements

| Aspect | JSA Adds |
|--------|----------|
| **Reference Class Priming** | Mental model for quality before drafting |
| **Paragraph 1 (Hook)** | 80-100 words, UVP + company reference |
| **Paragraph 2 (Proof Points)** | 120-140 words, 3 requirements × (Claim + Proof) |
| **Paragraph 3 (Close)** | 60-80 words, CTA + time-saver positioning |
| **Proof Points** | 3 requirements, each with Claim + Proof structure |

### Comparison: Cover Letter

| Element | CareerVP | JSA | Action |
|---------|----------|-----|--------|
| Opening hook | Yes | Specific (80-100 words) | CLARIFY |
| Body paragraphs | Yes (2-3) | Specific (Proof Points) | CLARIFY |
| Closing CTA | Yes | Same | PRESERVE |
| VPR differentiators | Yes | Same | PRESERVE |
| Company research | Yes | Same | PRESERVE |
| Length 400 words | Yes | Same | PRESERVE |
| Anti-AI detection | Yes | Same | PRESERVE |
| **Reference Class Priming** | No | **Required** | **ADD** |
| **Claim + Proof Structure** | Implicit | Explicit | **ADD** |
| **Word count per para** | No | Required | **ADD** |

### Recommendation for Cover Letter

**Keep existing output** (single cover letter, max 400 words), **add** Reference Class Priming and explicit Claim + Proof structure. The handler needs to be created (currently not implemented per JSA Plan).

---

## 4. Gap Analysis

### CareerVP Current Specification (F-JOB-003, F-JOB-004)

| Aspect | Current Specification |
|--------|----------------------|
| **Question Count** | Max 10 questions |
| **Priority Levels** | CRITICAL, IMPORTANT, OPTIONAL |
| **Categories** | QUANTIFY, EXAMPLE, CLARIFY, FILL_GAP |
| **Previous Questions** | Avoid repetition from previous applications |
| **Inputs** | CV facts, Job requirements, Company research |

### JSA Requirements

| Aspect | JSA Adds |
|--------|----------|
| **[CV IMPACT] Tag** | Quantifiable results, metrics, team sizes |
| **[INTERVIEW/MVP ONLY] Tag** | Philosophy, process, soft skills |
| **Strategic Intent** | Why each question is asked |
| **Destination Labeling** | Which artifact uses the response |
| **Evidence Gap** | What's missing from CV |
| **Memory Awareness** | Skip recurring themes from knowledge base |
| **Recurring Themes** | Topics to skip (from previous applications) |

### Comparison: Gap Analysis

| Element | CareerVP | JSA | Action |
|---------|----------|-----|--------|
| Max 10 questions | Yes | Same | PRESERVE |
| CRITICAL/IMPORTANT/OPTIONAL | Yes | Same | PRESERVE |
| QUANTIFY/EXAMPLE categories | Yes | Enhanced | PRESERVE |
| Previous questions check | Yes | Same | PRESERVE |
| **Contextual Tags** | No | **[CV IMPACT], [INTERVIEW/MVP ONLY]** | **ADD** |
| **Strategic Intent** | No | Required | **ADD** |
| **Evidence Gap** | No | Required | **ADD** |
| **Memory Awareness** | No | Required | **ADD** |
| **Recurring Themes** | No | Required | **ADD** |

### Recommendation for Gap Analysis

**Keep existing question generation** (max 10, priority levels), **add** contextual tagging and memory awareness. The handler needs completion (currently only has helper functions per JSA Plan).

---

## 5. Interview Prep

### CareerVP Current Specification (F-JOB-008)

| Aspect | Current Specification |
|--------|----------------------|
| **Question Count** | 10-15 predicted questions |
| **Categories** | Technical, Behavioral, Company-specific, Gap-related |
| **Format** | STAR method (Situation, Task, Action, Result) |
| **Additional** | Questions to ask interviewer, Salary guidance, Cultural fit |
| **Inputs** | CV facts, Job requirements, VPR differentiators, Gap responses |

### JSA Requirements

| Aspect | JSA Adds |
|--------|----------|
| **4 Categories** | Technical Competency, Behavioral/Cultural Fit, Experience & Background, Problem-Solving |
| **STAR Format** | Explicit Situation, Task, Action, Result sections |
| **Questions to Ask** | 5-7 questions |
| **Pre-interview Checklist** | Required section |
| **Salary Guidance** | Optional |

### Comparison: Interview Prep

| Element | CareerVP | JSA | Action |
|---------|----------|-----|--------|
| 10-15 questions | Yes | Same | PRESERVE |
| STAR format | Yes | Same | PRESERVE |
| Questions to ask | Yes (implied) | Explicit (5-7) | CLARIFY |
| Salary guidance | Yes | Same | PRESERVE |
| Technical questions | Yes | Same | PRESERVE |
| Behavioral questions | Yes | Same | PRESERVE |
| Company-specific | Yes | Same | PRESERVE |
| Gap-related | Yes | Same | PRESERVE |
| **Pre-interview Checklist** | No | Required | **ADD** |
| **4 Explicit Categories** | No | Required | **ADD** |

### Recommendation for Interview Prep

**Features align** - both specify 10-15 questions, STAR format, salary guidance. **Add** explicit 4 categories and pre-interview checklist. File needs to be created (not yet implemented).

---

## 6. Quality Validator (NEW)

### CareerVP Current Specification

**NOT IN SPEC** - This is a new component.

### JSA Requirements

| Check | Description |
|-------|-------------|
| Fact Verification | Cross-reference all claims against source |
| ATS Compatibility | Keyword score calculation |
| Anti-AI Detection | Banned words, patterns check |
| Cross-Document Consistency | CV, VPR, Cover Letter alignment |
| Completeness | Word counts, section counts |
| Language Quality | Spelling, grammar, tone |

### Recommendation for Quality Validator

**CREATE NEW** - This is a new component that validates all artifacts. Integrate as final step in VPR generation flow.

---

## 7. Knowledge Base (NEW)

### CareerVP Current Specification

**NOT IN SPEC** - Memory awareness for recurring themes is not specified.

### JSA Requirements

| Element | Description |
|---------|-------------|
| **Table** | `careervp-knowledge-base` |
| **Partition Key** | `userEmail` |
| **Sort Key** | `knowledgeType` |
| **TTL** | 365 days |
| **Types** | recurring_themes, gap_responses, differentiators |

### Recommendation for Knowledge Base

**CREATE NEW** - New DynamoDB table and repository for user memory. Enables memory-aware gap analysis (skip recurring themes).

---

## Summary: What to Keep vs. Add

### Features to PRESERVE (No Changes)

| Feature | Element | Location |
|---------|---------|----------|
| VPR | Executive Summary, Evidence Matrix, Differentiators, Cultural Fit, Talking Points | `vpr_prompt.py` |
| VPR | Anti-AI detection rules | `vpr_prompt.py` |
| VPR | Fact verification checklist | `vpr_prompt.py` |
| CV Tailoring | ATS optimization rules | `cv_tailoring_prompt.py` |
| CV Tailoring | VPR differentiators input | `cv_tailoring_logic.py` |
| CV Tailoring | Structured form editing | Frontend + models |
| Cover Letter | Max 400 words | `cover_letter_prompt.py` |
| Cover Letter | VPR differentiators input | `cover_letter_prompt.py` |
| Gap Analysis | Max 10 questions | `gap_analysis_prompt.py` |
| Gap Analysis | Priority levels | `gap_analysis_prompt.py` |
| Interview Prep | STAR format | `interview_prep_prompt.py` |
| Interview Prep | Salary guidance | `interview_prep_prompt.py` |

### Features to ADD/ENHANCE

| Feature | What to Add | Location |
|---------|-------------|----------|
| VPR | 6-stage methodology | `vpr_prompt.py` |
| VPR | Meta-review questions | `vpr_prompt.py` |
| VPR | Internal output markers | `vpr_prompt.py` |
| CV Tailoring | 3-step verification | `cv_tailoring_prompt.py` |
| CV Tailoring | ATS scoring (1-10) | `cv_tailoring_prompt.py` |
| CV Tailoring | Hiring manager check | `cv_tailoring_prompt.py` |
| Cover Letter | Reference class priming | `cover_letter_prompt.py` |
| Cover Letter | Claim + Proof structure | `cover_letter_prompt.py` |
| Cover Letter | Handler (NOT IMPLEMENTED) | `cover_letter_handler.py` |
| Gap Analysis | [CV IMPACT] tag | `gap_analysis_prompt.py` |
| Gap Analysis | [INTERVIEW/MVP ONLY] tag | `gap_analysis_prompt.py` |
| Gap Analysis | Strategic intent field | `gap_analysis_prompt.py` |
| Gap Analysis | Memory awareness | `gap_analysis_prompt.py` + new KB |
| Gap Analysis | Handler completion | `gap_handler.py` |
| Interview Prep | 4 explicit categories | `interview_prep_prompt.py` |
| Interview Prep | Pre-interview checklist | `interview_prep_prompt.py` |
| Quality Validator | 6 validation checks | `quality_validator.py` (NEW) |
| Knowledge Base | DynamoDB table + repo | NEW files |

### Files to CREATE

| File | Purpose |
|------|---------|
| `src/backend/careervp/handlers/cover_letter_handler.py` | Cover letter Lambda handler |
| `src/backend/careervp/handlers/interview_prep_handler.py` | Interview prep Lambda handler |
| `src/backend/careervp/logic/interview_prep.py` | Interview prep business logic |
| `src/backend/careervp/logic/quality_validator.py` | Quality validation agent |
| `src/backend/careervp/dal/knowledge_base_repository.py` | Knowledge base CRUD |
| `src/backend/careervp/logic/knowledge_base.py` | Knowledge base logic |

---

## Implementation Priority

### Phase 1: Core Enhancements (Keep + Add)

1. **VPR 6-stage** - Enhance existing prompt with stages
2. **CV Tailoring 3-step** - Add verification to existing prompt
3. **Cover Letter Handler** - Create handler, enhance prompt
4. **Gap Analysis Tags** - Add tagging, complete handler

### Phase 2: New Components

5. **Interview Prep** - Create prompt, logic, handler
6. **Quality Validator** - Create validation agent
7. **Knowledge Base** - Create table, repo, logic

---

**END OF COMPARISON**
