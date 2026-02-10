# CareerVP ↔ Job Search Assistant Skill Alignment Plan

**Document Version:** 1.0
**Date:** 2026-02-09
**Purpose:** Comprehensive gap analysis and remediation plan to align CareerVP with the Job Search Assistant Skill architecture

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Gap Analysis Matrix](#2-gap-analysis-matrix)
3. [VPR Prompt Remediation](#3-vpr-prompt-remediation)
4. [CV Tailoring Remediation](#4-cv-tailoring-remediation)
5. [Cover Letter Remediation](#5-cover-letter-remediation)
6. [Gap Analysis Remediation](#6-gap-analysis-remediation)
7. [Missing Components](#7-missing-components)
8. [Implementation Priority](#8-implementation-priority)
9. [Validation Criteria](#9-validation-criteria)
10. [Questions & Clarifications](#10-questions--clarifications)

---

## 1. Executive Summary

### Current State vs. Target State

| Component | Current State | Target State (JSA Skill) | Gap Severity |
|-----------|---------------|--------------------------|--------------|
| **VPR Generation** | Direct output, no staged process | 6-stage methodology with self-correction | **CRITICAL** |
| **CV Tailoring** | Basic prompt, no verification | 3-step verification with company keywords | **HIGH** |
| **Cover Letter** | Basic prompt, NO HANDLER | Reference class priming + scaffolded proofs | **CRITICAL** |
| **Gap Analysis** | Basic 3-5 questions, incomplete handler | Contextual tagging + memory-aware + 10 max | **HIGH** |
| **Interview Prep** | NOT IMPLEMENTED | Tiered STAR responses + verification | **CRITICAL** |
| **Quality Validator** | NOT IMPLEMENTED | Multi-check validation agent | **MEDIUM** |
| **Company Research** | Implemented (3-tier fallback) | Needs keyword extraction for CV | **LOW** |

### Key Architectural Differences

1. **Methodology Gap**: Current prompts jump directly to output; Skill uses **staged thinking processes** with internal critique
2. **Self-Correction Gap**: No meta-review or refinement loops in current implementation
3. **Verification Gap**: No ATS scoring, strategic alignment checks, or fact verification in artifact generation
4. **Memory Gap**: No user knowledge base for recurring themes or previous responses

---

## 2. Gap Analysis Matrix

### 2.1 VPR Prompt Gaps

| Feature | Current (`vpr_prompt.py`) | JSA Skill | Status |
|---------|---------------------------|-----------|--------|
| STAGE 1: Company & Role Research | ❌ Missing | Extract 3-5 strategic priorities, 5-7 role criteria | **NOT IMPLEMENTED** |
| STAGE 2: Candidate Analysis | ❌ Missing | Career narrative in ONE sentence, 3-5 differentiators | **NOT IMPLEMENTED** |
| STAGE 3: Alignment Mapping | ⚠️ Partial (in output) | Explicit table creation step | **PARTIAL** |
| STAGE 4: Self-Correction | ❌ Missing | Meta-review, logical consistency check | **NOT IMPLEMENTED** |
| STAGE 5: Generate Report | ✅ Present | Structured sections | **IMPLEMENTED** |
| STAGE 6: Final Meta Evaluation | ❌ Missing | "20% more persuasive" improvement | **NOT IMPLEMENTED** |
| Anti-AI Detection | ✅ Present | Banned words, varied sentences | **IMPLEMENTED** |
| Fact Verification | ✅ Present | Checklist before output | **IMPLEMENTED** |
| JSON Output | ✅ Present | Structured response | **IMPLEMENTED** |

**Lines of Code Comparison:**
- Current: 239 lines
- Target: ~300 lines (with 6-stage methodology)

### 2.2 CV Tailoring Gaps

| Feature | Current (`cv_tailoring_prompt.py`) | JSA Skill | Status |
|---------|-----------------------------------|-----------|--------|
| Company Research Keywords | ❌ Missing | `{company_keywords}` parameter | **NOT IMPLEMENTED** |
| VPR Differentiators Input | ❌ Missing | Extract UVP and top 3 differentiators | **NOT IMPLEMENTED** |
| STEP 1: Analysis & Keyword Mapping | ❌ Missing | Extract 12-18 keywords, draft CV | **NOT IMPLEMENTED** |
| STEP 2: Self-Correction | ❌ Missing | ATS score (1-10), missing keywords | **NOT IMPLEMENTED** |
| STEP 3: Final Output | ❌ Missing | Apply revisions, ensure ATS ≥ 8 | **NOT IMPLEMENTED** |
| CAR/STAR Format | ❌ Missing | Action verb + metric + keyword | **NOT IMPLEMENTED** |
| ATS Formatting Rules | ⚠️ Implicit | Explicit rules (no tables, simple bullets) | **PARTIAL** |

**Lines of Code Comparison:**
- Current: 144 lines (utility functions only)
- Target: ~250 lines (with 3-step verification)

### 2.3 Cover Letter Gaps

| Feature | Current (`cover_letter_prompt.py`) | JSA Skill | Status |
|---------|-----------------------------------|-----------|--------|
| Lambda Handler | ❌ Missing | Endpoint at POST /api/cover-letter | **NOT IMPLEMENTED** |
| Reference Class Priming | ❌ Missing | Mental model for quality before drafting | **NOT IMPLEMENTED** |
| Paragraph 1 (Hook) | ⚠️ Generic | 80-100 words, UVP + company reference | **PARTIAL** |
| Paragraph 2 (Proof Points) | ❌ Missing | 3 requirements × (Claim + Proof) | **NOT IMPLEMENTED** |
| Paragraph 3 (Close) | ⚠️ Generic | 60-80 words, time-saver positioning | **PARTIAL** |
| Anti-AI Detection | ❌ Missing | Banned words, varied sentences | **NOT IMPLEMENTED** |
| Word Count Enforcement | ⚠️ Soft | Strict ≤400 words with counting | **PARTIAL** |

**Lines of Code Comparison:**
- Current: 58 lines (no handler)
- Target: ~200 lines (prompt + handler)

### 2.4 Gap Analysis Gaps

| Feature | Current (`gap_analysis_prompt.py`) | JSA Skill | Status |
|---------|-----------------------------------|-----------|--------|
| Lambda Handler | ❌ Incomplete | Only helper functions in handler | **NOT IMPLEMENTED** |
| Question Count | 3-5 questions | MAX 10 questions | **DIFFERENT** |
| Contextual Tagging | ❌ Missing | [CV IMPACT] vs [INTERVIEW/MVP ONLY] | **NOT IMPLEMENTED** |
| Strategic Intent | ❌ Missing | WHY each question is asked | **NOT IMPLEMENTED** |
| Memory Awareness | ❌ Missing | Skip recurring themes from history | **NOT IMPLEMENTED** |
| Destination Labeling | ❌ Missing | Which artifact uses the response | **NOT IMPLEMENTED** |
| Priority Levels | ❌ Missing | CRITICAL/IMPORTANT/OPTIONAL | **NOT IMPLEMENTED** |
| Previous Response Check | ❌ Missing | Avoid duplicate questions | **NOT IMPLEMENTED** |

**Lines of Code Comparison:**
- Current: 108 lines
- Target: ~300 lines (with enhanced tagging)

---

## 3. VPR Prompt Remediation

### 3.1 Required Changes

Replace current `VPR_GENERATION_PROMPT` with 6-stage methodology:

```python
VPR_GENERATION_PROMPT = """You are an expert career strategist creating a Value Proposition Report (VPR) for a job application.

Follow this 6-STAGE PROCESS exactly:

---

STAGE 1: COMPANY & ROLE RESEARCH

Analyze the company research and identify:
- 3-5 strategic priorities or current challenges
- 5-7 role success criteria from job posting

COMPANY RESEARCH:
{company_research_json}

JOB REQUIREMENTS:
{job_requirements_json}

OUTPUT (Internal): List strategic priorities and role criteria before proceeding.

---

STAGE 2: CANDIDATE ANALYSIS

Parse CV facts and gap responses:
- Identify achievements with quantified outcomes
- Extract 3-5 core differentiators (what sets candidate apart)
- Summarize career narrative in ONE sentence

CV FACTS:
{cv_facts_json}

GAP ANALYSIS RESPONSES (PRIMARY EVIDENCE):
{gap_responses_json}

OUTPUT (Internal): List differentiators and career narrative before proceeding.

---

STAGE 3: ALIGNMENT MAPPING

Create reasoning scaffold table with 5-7 minimum alignments:

| Company/Role Need | Candidate Evidence | Business Impact/Outcome |
|-------------------|-------------------|------------------------|
| [from Stage 1] | [from CV + gaps] | [value delivery] |

Use gap responses for quantified evidence.

OUTPUT (Internal): Complete alignment matrix before proceeding.

---

STAGE 4: SELF-CORRECTION & META REVIEW

Before proceeding, perform internal critique:
- Are there any unsupported claims?
- Is logic consistent throughout?
- Would this persuade a senior hiring manager?
- Are arguments evidence-driven and sharp?

Refine your analysis based on this critique.

OUTPUT (Internal): Note any refinements made.

---

STAGE 5: GENERATE REPORT

[Current VPR structure sections here - Executive Summary through Talking Points]

---

STAGE 6: FINAL META EVALUATION

Ask yourself: "How could this report be 20% more persuasive, specific, or actionable?"

Apply those improvements and output the final refined version.

---

[Anti-AI Detection Rules and Fact Verification Checklist - keep current]

OUTPUT FORMAT: Return ONLY valid JSON.

Generate VPR now:"""
```

### 3.2 Implementation Steps

1. **Add stage markers** to prompt template
2. **Add internal output instructions** for each stage
3. **Add meta-review questions** in Stage 4
4. **Add 20% improvement prompt** in Stage 6
5. **Test** that Claude actually follows staged process

### 3.3 Validation Test

```python
def test_vpr_follows_staged_process():
    """Verify VPR prompt includes all 6 stages."""
    from careervp.logic.prompts.vpr_prompt import VPR_GENERATION_PROMPT

    required_stages = [
        "STAGE 1: COMPANY & ROLE RESEARCH",
        "STAGE 2: CANDIDATE ANALYSIS",
        "STAGE 3: ALIGNMENT MAPPING",
        "STAGE 4: SELF-CORRECTION",
        "STAGE 5: GENERATE REPORT",
        "STAGE 6: FINAL META EVALUATION",
    ]

    for stage in required_stages:
        assert stage in VPR_GENERATION_PROMPT, f"Missing: {stage}"

    # Verify meta-review questions
    assert "unsupported claims" in VPR_GENERATION_PROMPT
    assert "20% more persuasive" in VPR_GENERATION_PROMPT
```

---

## 4. CV Tailoring Remediation

### 4.1 Required Changes

Replace current prompt utilities with 3-step verification methodology:

```python
CV_TAILORING_PROMPT = """You are an expert CV writer. Tailor this CV using a 3-STEP PROCESS.

---

INPUT DATA:

CV FACTS (SOURCE OF TRUTH):
{cv_facts_json}

JOB REQUIREMENTS:
{job_requirements_json}

VPR STRATEGIC DIFFERENTIATORS:
{vpr_differentiators}

COMPANY RESEARCH KEYWORDS:
{company_keywords}

LANGUAGE: {language}

---

STEP 1: ANALYSIS & KEYWORD MAPPING

- Extract core UVP and top 3 Key Differentiators from VPR
- Analyze job posting: extract 12-18 key skills/technologies/responsibilities
- Include company research keywords for ATS optimization
- Review CV facts: Include ONLY experience/skills directly relevant to keywords AND supporting the 3 Differentiators
- Draft CV with all bullets in CAR (Challenge-Action-Result) or STAR format:
  * Begin with strong action verb
  * Include quantifiable metric (number, percentage, scale)
  * If unquantifiable, highlight process improvement or technical expertise

OUTPUT (Internal): Draft tailored CV

---

STEP 2: SELF-CORRECTION & VERIFICATION

**Verification Check 1 (ATS):**
- Rate keyword match score (1-10) against job posting
- List 3 most critical missing/underrepresented keywords
- If score < 7, plan revisions to add keywords

**Verification Check 2 (Hiring Manager & Strategy):**
- Does Professional Summary directly align with UVP from VPR?
- Does it address Company's Core Problem implied by job posting?
- If not, plan summary rewrite for precise alignment

OUTPUT (Internal): Verification results + revision plan

---

STEP 3: FINAL OUTPUT

Apply revisions based on verification checks:
- Add missing keywords naturally
- Rewrite summary if needed
- Ensure ATS score >= 8
- Ensure strategic alignment with VPR

---

ATS FORMATTING RULES:
- Standard headers: "Professional Experience", "Education", "Skills"
- Simple bullets (•)
- No tables or columns
- Standard fonts only
- Length: 1-2 pages (max 3 pages)

CRITICAL: Use ONLY facts from CV. Zero hallucinations.

OUTPUT: JSON matching exact schema provided.

Generate tailored CV now:"""
```

### 4.2 Implementation Steps

1. **Add `company_keywords` parameter** to prompt builder
2. **Add `vpr_differentiators` parameter** from VPR response
3. **Implement 3-step structure** with internal verification
4. **Add ATS score self-rating** (1-10)
5. **Add verification results** to output schema
6. **Update `cv_tailoring_logic.py`** to pass new parameters

### 4.3 Code Changes Required

```python
# In cv_tailoring_logic.py - add these parameters

def tailor_cv(
    cv: UserCV,
    job_posting: JobPosting,
    vpr_response: VPRResponse,  # NEW: Extract differentiators
    company_research: CompanyResearch,  # NEW: Extract keywords
    language: str = "en"
) -> TailoredCV:
    # Extract company keywords from research
    company_keywords = extract_ats_keywords(company_research)

    # Extract differentiators from VPR
    vpr_differentiators = vpr_response.differentiators[:3]  # Top 3

    prompt = build_cv_tailoring_prompt(
        cv=cv,
        job_posting=job_posting,
        vpr_differentiators=vpr_differentiators,
        company_keywords=company_keywords,
        language=language
    )
    # ...
```

### 4.4 Validation Test

```python
def test_cv_tailoring_includes_verification():
    """Verify CV tailoring prompt has 3-step verification."""
    from careervp.logic.cv_tailoring_prompt import CV_TAILORING_PROMPT

    # Check steps
    assert "STEP 1: ANALYSIS & KEYWORD MAPPING" in CV_TAILORING_PROMPT
    assert "STEP 2: SELF-CORRECTION & VERIFICATION" in CV_TAILORING_PROMPT
    assert "STEP 3: FINAL OUTPUT" in CV_TAILORING_PROMPT

    # Check verification checks
    assert "Verification Check 1 (ATS)" in CV_TAILORING_PROMPT
    assert "Verification Check 2 (Hiring Manager" in CV_TAILORING_PROMPT

    # Check parameters
    assert "{company_keywords}" in CV_TAILORING_PROMPT
    assert "{vpr_differentiators}" in CV_TAILORING_PROMPT
```

---

## 5. Cover Letter Remediation

### 5.1 Required Changes

**A. Create Lambda Handler** (`cover_letter_handler.py`):

```python
@logger.inject_lambda_context
@tracer.capture_lambda_handler
def lambda_handler(event: dict, context: Any) -> dict:
    """POST /api/cover-letter endpoint."""
    # Validate request
    # Call cover letter logic
    # Return generated cover letter
```

**B. Replace prompt with scaffolded structure**:

```python
COVER_LETTER_PROMPT = """You are an expert cover letter writer. Create EXACTLY 1 page (max 400 words).

---

STEP 1: REFERENCE CLASS PRIMING

Before drafting, internally describe the structure and tone of an exemplary, modern, persuasive cover letter for a competitive job market that:
- Focuses on VALUE candidate provides to company (not what candidate wants)
- Leverages strategic claims from Value Proposition Report
- Uses concrete proof points, not generic interest statements

---

INPUT DATA:

CV FACTS:
{cv_facts_json}

JOB INFO:
- Title: {job_title}
- Company: {company_name}
- Top 3 Requirements: {key_requirements}

VPR DIFFERENTIATORS (EXTRACT UVP):
{vpr_differentiators}

COMPANY CULTURE/RESEARCH:
{company_culture}

LANGUAGE: {language}

---

STEP 2: DRAFT LETTER

**Paragraph 1 (The Hook) - 80-100 words:**
- State role and IMMEDIATELY reference UVP from VPR
- Show research: mention specific company goal, product, or recent announcement
- Link candidate's background to that goal

**Paragraph 2 (The Proof Points) - 120-140 words:**

Identify top 3 non-negotiable requirements from job posting.
For EACH requirement:
- Sentence 1: Assert candidate's skill using VPR language/claims
- Sentence 2: Detail specific quantified achievement from CV as proof

Format: Requirement 1 Claim + Proof. Requirement 2 Claim + Proof. Requirement 3 Claim + Proof.

**Paragraph 3 (The Close) - 60-80 words:**
- Express enthusiasm
- Clear, confident call to action
- Position candidate as time-saver (e.g., "I look forward to discussing how my experience in [Key Skill from UVP] can immediately reduce your team's ramp-up time.")

---

TONE REQUIREMENTS:
- Professional and highly confident
- Focused entirely on value candidate provides to company
- NOT what candidate hopes to gain

ANTI-AI DETECTION:
- Natural transitions (not formulaic)
- Vary sentence length (8-25 words)
- Brief personal touch
- Avoid: leverage, delve, robust, streamline
- Use approximations: "nearly 40%" not "39.7%"

WORD COUNT: MUST stay under 400 words. Count as you write.

CRITICAL: Use ONLY facts from CV. Zero hallucinations.

OUTPUT: Clean markdown, 3 paragraphs, no lists or bullets.

Generate cover letter now:"""
```

### 5.2 Implementation Steps

1. **Create `cover_letter_handler.py`** with POST endpoint
2. **Wire up API Gateway** route in CDK
3. **Replace prompt** with scaffolded structure
4. **Add reference class priming** step
5. **Implement proof points scaffolding** (3 requirements × claim + proof)
6. **Add anti-AI detection rules**
7. **Add word count enforcement**

### 5.3 Validation Test

```python
def test_cover_letter_has_scaffolded_structure():
    """Verify cover letter prompt has reference class priming and proof points."""
    from careervp.logic.prompts.cover_letter_prompt import COVER_LETTER_PROMPT

    # Reference class priming
    assert "REFERENCE CLASS PRIMING" in COVER_LETTER_PROMPT
    assert "exemplary, modern, persuasive" in COVER_LETTER_PROMPT

    # Proof points structure
    assert "Paragraph 2 (The Proof Points)" in COVER_LETTER_PROMPT
    assert "top 3 non-negotiable requirements" in COVER_LETTER_PROMPT
    assert "Claim + Proof" in COVER_LETTER_PROMPT

    # Word count per paragraph
    assert "80-100 words" in COVER_LETTER_PROMPT
    assert "120-140 words" in COVER_LETTER_PROMPT
    assert "60-80 words" in COVER_LETTER_PROMPT
```

---

## 6. Gap Analysis Remediation

### 6.1 Required Changes

**A. Complete Lambda Handler** (`gap_handler.py`):

```python
@logger.inject_lambda_context
@tracer.capture_lambda_handler
def lambda_handler(event: dict, context: Any) -> dict:
    """POST /api/gap-analysis endpoint."""
    # Parse request
    # Load user's recurring themes from knowledge base
    # Load previous gap responses
    # Generate questions with contextual tagging
    # Return tagged questions
```

**B. Replace prompt with enhanced tagging**:

```python
GAP_ANALYSIS_ENHANCED_PROMPT = """You are an expert career strategist generating targeted gap analysis questions with contextual tagging.

CRITICAL INSTRUCTIONS:
1. Generate MAXIMUM 10 questions
2. Tag each question: [CV IMPACT] or [INTERVIEW/MVP ONLY]
3. Include strategic intent for each question
4. Skip recurring themes from user history
5. Emphasize quantification for [CV IMPACT] questions
6. Focus on CRITICAL job requirements only

INPUT DATA:

CV FACTS (USER'S ESTABLISHED STRENGTHS):
{cv_facts_json}

USER'S RECURRING THEMES (SKIP THESE TOPICS):
{recurring_themes}

JOB REQUIREMENTS (CRITICAL REQUIREMENTS ONLY):
{job_requirements_json}

COMPANY CONTEXT:
{company_research_json}

PREVIOUS GAP RESPONSES (DO NOT REPEAT):
{previous_gap_responses_json}

---

QUESTION GENERATION STRATEGY:

STEP 1 - CROSS-REFERENCE & MEMORY CHECK:
- Analyze job requirements against CV facts
- Identify gaps where CV lacks specific metrics/evidence
- Explicitly skip topics from recurring_themes
- Focus ONLY on "Critical" or "Must-Have" job requirements

STEP 2 - CATEGORIZE BY DESTINATION:
- [CV IMPACT]: Questions that yield quantifiable results, metrics, team sizes
- [INTERVIEW/MVP ONLY]: Questions about philosophy, process, soft skills

STEP 3 - ENFORCE BREADTH OVER DEPTH:
- Avoid "in the weeds" technical questions
- Focus on business impact, not implementation details

---

QUESTION FORMAT (for each question):

### Question {N}

**Requirement:** [Exact quote from job posting]

**Question:** [Targeted question emphasizing quantification]

**Destination:** [CV IMPACT] or [INTERVIEW/MVP ONLY]

**Strategic Intent:** [Why this is being asked, how response will be used]

**Evidence Gap:** [What's missing from the CV]

**Priority:** CRITICAL | IMPORTANT | OPTIONAL

---

RULES:

[CV IMPACT] QUESTIONS (5-7 questions):
- MUST ask for specific numbers: "How many?", "What percentage?"
- Focus on: team sizes, metrics, results, time saved, cost reduced

[INTERVIEW/MVP ONLY] QUESTIONS (3-5 questions):
- Ask about: philosophy, approach, process, soft skills, judgment calls
- Don't force metrics if topic is inherently qualitative

OUTPUT FORMAT: JSON array with schema provided.

Generate gap analysis questions now:"""
```

### 6.2 Implementation Steps

1. **Complete `gap_handler.py`** with lambda_handler function
2. **Wire up API Gateway** route in CDK
3. **Create knowledge base table** for recurring themes
4. **Implement `load_recurring_themes()`** function
5. **Implement `load_previous_gap_responses()`** function
6. **Replace prompt** with enhanced tagging
7. **Update response schema** to include destination, strategic_intent, priority

### 6.3 Validation Test

```python
def test_gap_analysis_has_contextual_tagging():
    """Verify gap analysis prompt has contextual tagging system."""
    from careervp.logic.prompts.gap_analysis_prompt import GAP_ANALYSIS_ENHANCED_PROMPT

    # Contextual tagging
    assert "[CV IMPACT]" in GAP_ANALYSIS_ENHANCED_PROMPT
    assert "[INTERVIEW/MVP ONLY]" in GAP_ANALYSIS_ENHANCED_PROMPT

    # Memory awareness
    assert "recurring_themes" in GAP_ANALYSIS_ENHANCED_PROMPT
    assert "SKIP THESE TOPICS" in GAP_ANALYSIS_ENHANCED_PROMPT

    # Strategic intent
    assert "Strategic Intent" in GAP_ANALYSIS_ENHANCED_PROMPT

    # Max 10 questions
    assert "MAXIMUM 10 questions" in GAP_ANALYSIS_ENHANCED_PROMPT

    # Priority levels
    assert "CRITICAL | IMPORTANT | OPTIONAL" in GAP_ANALYSIS_ENHANCED_PROMPT
```

---

## 7. Missing Components

### 7.1 Interview Prep Generator

**Status:** NOT IMPLEMENTED

**Required Implementation:**

1. Create `interview_prep_prompt.py` with tiered responses
2. Create `interview_prep_logic.py` for orchestration
3. Create `interview_prep_handler.py` for API endpoint
4. Add to CDK infrastructure

**Key Features from Skill:**
- 10-15 predicted questions across 4 categories
- STAR-formatted responses
- Questions to ask interviewer (5-7)
- Salary negotiation guidance
- Pre-interview checklist
- Optional Tier 2 verification (premium feature)

### 7.2 Quality Validator Agent

**Status:** NOT IMPLEMENTED

**Required Implementation:**

1. Create `quality_validator.py` with 6 checks:
   - Fact verification (cross-reference all claims)
   - ATS compatibility (keyword score)
   - Anti-AI detection (banned words, patterns)
   - Cross-document consistency
   - Completeness (word counts, section counts)
   - Language quality (spelling, grammar, tone)

2. Integrate as final step in VPR generation flow

### 7.3 Knowledge Base for User Memory

**Status:** NOT IMPLEMENTED

**Required Implementation:**

1. Create DynamoDB table `careervp-knowledge-base`
2. Schema: `userEmail` (PK), `knowledgeType` (SK), `data`, `applications_count`
3. Types: `recurring_themes`, `gap_responses`, `differentiators`
4. Implement CRUD operations
5. Integrate with Gap Analysis for memory-aware questioning

---

## 8. Implementation Priority

### Phase 1: Critical Fixes (Week 1-2)
| Priority | Component | Effort | Impact |
|----------|-----------|--------|--------|
| P0 | VPR 6-stage methodology | 4 hours | HIGH |
| P0 | CV Tailoring 3-step verification | 6 hours | HIGH |
| P0 | Cover Letter handler + scaffolded prompt | 8 hours | HIGH |
| P0 | Gap Analysis handler + contextual tagging | 6 hours | HIGH |

### Phase 2: Missing Features (Week 3-4)
| Priority | Component | Effort | Impact |
|----------|-----------|--------|--------|
| P1 | Interview Prep full implementation | 16 hours | HIGH |
| P1 | Quality Validator agent | 8 hours | MEDIUM |
| P2 | Knowledge Base for user memory | 8 hours | MEDIUM |

### Phase 3: Enhancements (Week 5+)
| Priority | Component | Effort | Impact |
|----------|-----------|--------|--------|
| P2 | Company keyword extraction | 4 hours | LOW |
| P2 | Tiered verification (premium) | 12 hours | MEDIUM |
| P3 | Step Functions migration | 16 hours | LOW |

### Phase 4: Test-Driven Completion (Current)
| Priority | Component | Effort | Status |
|----------|-----------|--------|--------|
| P0 | VPR 6-stage implementation | TBD | **IN PROGRESS** |
| P0 | CV Tailoring 3-step implementation | TBD | Pending |
| P0 | Cover Letter implementation | TBD | Pending |
| P0 | Gap Analysis implementation | TBD | Pending |
| P1 | Interview Prep implementation | TBD | Pending |
| P1 | Quality Validator implementation | TBD | Pending |
| P1 | Knowledge Base implementation | TBD | Pending |

#### 8.1 Test Results Summary (2026-02-09)

| Component | Passing | Failing | Gap Identified |
|-----------|---------|---------|----------------|
| VPR | 5 | 7 | Missing 6-stage methodology |
| CV Tailoring | TBD | TBD | - |
| Cover Letter | TBD | TBD | - |
| Gap Analysis | TBD | TBD | - |
| Interview Prep | 0 | 11 | Files not yet created |
| Quality Validator | 0 | 10 | Files not yet created |
| Knowledge Base | 0 | 11 | Files not yet created |

#### 8.2 VPR Test Failures Detail

| Test ID | Failure Reason |
|---------|----------------|
| test_vpr_has_6_stages | Missing "STAGE 1: COMPANY & ROLE RESEARCH" |
| test_vpr_stage1_company_role_research | Missing "3-5 strategic priorities" |
| test_vpr_stage2_candidate_analysis | Missing "3-5 core differentiators" |
| test_vpr_stage3_alignment_mapping | Missing "ALIGNMENT MAPPING" |
| test_vpr_has_self_correction | Missing "unsupported claims" check |
| test_vpr_has_meta_evaluation | Missing "20% more persuasive" |
| test_vpr_internal_output_markers | Missing "OUTPUT (Internal)" |

#### 8.3 Validation Commands

```bash
# Run all JSA alignment tests
cd src/backend
PYTHONPATH=$(pwd) uv run pytest ../../tests/jsa_skill_alignment/ -v

# Run specific component tests
PYTHONPATH=$(pwd) uv run pytest ../../tests/jsa_skill_alignment/test_vpr_alignment.py -v
PYTHONPATH=$(pwd) uv run pytest ../../tests/jsa_skill_alignment/test_cv_tailoring_alignment.py -v
PYTHONPATH=$(pwd) uv run pytest ../../tests/jsa_skill_alignment/test_cover_letter_alignment.py -v
PYTHONPATH=$(pwd) uv run pytest ../../tests/jsa_skill_alignment/test_gap_analysis_alignment.py -v

# Validate test mapping
python ../../tests/jsa_skill_alignment/test_mapping.py

# Code quality checks
uv run ruff check src/backend/careervp/
uv run ruff format src/backend/careervp/
uv run mypy src/backend/careervp --strict
```

---

## 9. Validation Criteria

### 9.1 Automated Tests

```python
# tests/test_jsa_skill_alignment.py

class TestVPRAlignment:
    def test_vpr_has_6_stages(self): ...
    def test_vpr_has_self_correction(self): ...
    def test_vpr_has_meta_evaluation(self): ...

class TestCVTailoringAlignment:
    def test_cv_has_3_steps(self): ...
    def test_cv_has_company_keywords(self): ...
    def test_cv_has_vpr_differentiators(self): ...
    def test_cv_has_ats_verification(self): ...

class TestCoverLetterAlignment:
    def test_cover_letter_handler_exists(self): ...
    def test_cover_letter_has_reference_priming(self): ...
    def test_cover_letter_has_proof_points(self): ...
    def test_cover_letter_has_word_limits(self): ...

class TestGapAnalysisAlignment:
    def test_gap_handler_complete(self): ...
    def test_gap_has_contextual_tagging(self): ...
    def test_gap_has_memory_awareness(self): ...
    def test_gap_max_10_questions(self): ...

class TestInterviewPrepAlignment:
    def test_interview_prep_handler_exists(self): ...
    def test_interview_prep_has_star_format(self): ...
    def test_interview_prep_has_4_categories(self): ...
```

### 9.2 Manual Validation Checklist

- [ ] VPR output shows evidence of staged thinking
- [ ] CV tailoring includes ATS score self-rating
- [ ] Cover letter follows 3-paragraph structure with proof points
- [ ] Gap questions are tagged with [CV IMPACT] or [INTERVIEW/MVP ONLY]
- [ ] Interview prep includes STAR-formatted responses
- [ ] All artifacts pass anti-AI detection

---

## 10. Questions & Clarifications

### Questions for User

1. **I cannot access the Claude Desktop Skill directly.** Can you provide:
   - Exact prompt text from the Skill for Interview Prep?
   - Any additional methodology details not captured in exports?
   - Sample outputs from the Skill for comparison?

2. **Tiered Verification Cost:** The Prompt Library mentions Tier 2 verification adds significant cost (~$0.14/application vs $0.05 baseline). Should this be:
   - Implemented as default for all users?
   - Offered as a premium feature toggle?
   - Deferred to V2?

3. **Knowledge Base Priority:** Memory-aware questioning requires a new DynamoDB table and user knowledge accumulation. Should this be:
   - Part of Phase 1 (required for Skill parity)?
   - Deferred to Phase 2 (enhancement)?

4. **Step Functions vs. SQS:** Current architecture uses SQS for async VPR. The Skill documentation shows Step Functions. Should we:
   - Keep current SQS architecture (working, simpler)?
   - Migrate to Step Functions (more explicit orchestration)?

5. **Interview Prep Synchronous vs. Async:** Should Interview Prep be:
   - Synchronous (like CV Tailoring) for instant response?
   - Async (like VPR) given potential Tier 2 verification latency?

### What You May Not Be Considering

1. **Prompt Length Impact:** Adding 6-stage methodology significantly increases VPR prompt length. This may:
   - Increase input token costs
   - Require Sonnet's larger context window
   - Impact response latency

2. **Staged Process Reliability:** Claude may not reliably follow internal staged instructions. Consider:
   - Adding explicit JSON markers between stages
   - Using multi-turn conversations instead of single prompt
   - Adding validation that stages were followed

3. **Company Research Caching:** The architecture doc mentions 30-day caching, but current implementation may not have this. Verify cache TTL.

4. **User Experience for Gap Analysis:** With 10 questions (vs current 3-5), user burden increases. Consider:
   - Progressive disclosure (show high-priority first)
   - Skip button for recurring themes
   - Save-and-continue functionality

5. **Testing Strategy:** Current tests may not validate LLM output quality. Consider:
   - Adding LLM output parsing tests
   - Adding golden output comparison tests
   - Adding anti-AI detection validation

---

## Appendix: File Mapping

| Current File | Required Changes |
|--------------|------------------|
| `src/backend/careervp/logic/prompts/vpr_prompt.py` | Add 6-stage methodology |
| `src/backend/careervp/logic/cv_tailoring_prompt.py` | Replace with 3-step verification |
| `src/backend/careervp/logic/prompts/cover_letter_prompt.py` | Add scaffolded structure |
| `src/backend/careervp/logic/prompts/gap_analysis_prompt.py` | Add contextual tagging |
| `src/backend/careervp/handlers/cover_letter_handler.py` | **CREATE** - new handler |
| `src/backend/careervp/handlers/gap_handler.py` | Complete lambda_handler |
| `src/backend/careervp/handlers/interview_prep_handler.py` | **CREATE** - new handler |
| `src/backend/careervp/logic/interview_prep.py` | **CREATE** - new logic |
| `src/backend/careervp/logic/quality_validator.py` | **CREATE** - new logic |
| `infra/careervp/api_construct.py` | Add new endpoints |
| `infra/careervp/api_db_construct.py` | Add knowledge base table |

## Appendix: Test Files Created

| File | Tests | Purpose |
|------|-------|---------|
| `tests/jsa_skill_alignment/test_vpr_alignment.py` | 12 | VPR 6-stage methodology |
| `tests/jsa_skill_alignment/test_cv_tailoring_alignment.py` | 15 | CV Tailoring 3-step verification |
| `tests/jsa_skill_alignment/test_cover_letter_alignment.py` | 18 | Cover Letter scaffolded prompt |
| `tests/jsa_skill_alignment/test_gap_analysis_alignment.py` | 18 | Gap Analysis contextual tagging |
| `tests/jsa_skill_alignment/test_interview_prep_alignment.py` | 11 | Interview Prep Generator |
| `tests/jsa_skill_alignment/test_quality_validator_alignment.py` | 10 | Quality Validator Agent |
| `tests/jsa_skill_alignment/test_knowledge_base_alignment.py` | 11 | Knowledge Base |
| `tests/jsa_skill_alignment/test_mapping.py` | - | Test-to-requirement validation |

**Total: 95+ tests, all mapped to requirements in this plan**

---

**END OF ALIGNMENT PLAN**
