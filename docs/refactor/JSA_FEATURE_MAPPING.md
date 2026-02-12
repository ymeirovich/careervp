# CareerVP JSA Feature Mapping & Integration Plan

**Document Version:** 1.0
**Date:** 2026-02-10
**Purpose:** 1-1 mapping of JSA features to CareerVP components with integration flows

---

## Table of Contents

1. [JSA Feature Overview](#1-jsa-feature-overview)
2. [Feature-to-Component Mapping](#2-feature-to-component-mapping)
3. [VPR Feature Detail](#3-vpr-feature-detail)
4. [CV Tailoring Feature Detail](#4-cv-tailoring-feature-detail)
5. [Cover Letter Feature Detail](#5-cover-letter-feature-detail)
6. [Gap Analysis Feature Detail](#6-gap-analysis-feature-detail)
7. [Interview Prep Feature Detail](#7-interview-prep-feature-detail)
8. [Feature Integration Flows](#8-feature-integration-flows)
9. [Data Sharing Architecture](#9-data-sharing-architecture)
10. [Gap Analysis: What's Missing](#10-gap-analysis-whats-missing)
11. [Implementation Priority Matrix](#11-implementation-priority-matrix)

---

## 1. JSA Feature Overview

### JSA Core Features (Must Have 1-1 Mapping)

| JSA Feature | CareerVP Component | Status | Gap |
|-------------|------------------|--------|-----|
| **1. CV Upload & Parsing** | `cv_upload_handler.py` | ✅ Implemented | None |
| **2. Job Search/Research** | `company_research_handler.py` | ✅ Implemented | None |
| **3. VPR Generation** | `vpr_handler.py` / `vpr_generator.py` | ⚠️ Partial | Missing 6-stage |
| **4. CV Tailoring** | `cv_tailoring_handler.py` | ⚠️ Partial | Missing 3-step |
| **5. Cover Letter** | ❌ Missing | ❌ Not Implemented | CRITICAL |
| **6. Gap Analysis** | `gap_handler.py` | ⚠️ Incomplete | Missing integration |
| **7. Interview Prep** | ❌ Missing | ❌ Not Implemented | CRITICAL |
| **8. Quality Validation** | ❌ Missing | ❌ Not Implemented | Missing |
| **9. Knowledge Base** | ❌ Missing | ❌ Not Implemented | Missing |

---

## 2. Feature-to-Component Mapping

### 2.1 Complete Mapping Table

```
┌────────────────────────────────────────────────────────────────────────────────┐
│                         JSA FEATURE → CAREERVP COMPONENT MAPPING                  │
├────────────────────────────────────────────────────────────────────────────────┤
│                                                                                │
│  JSA FEATURE              CAREERVP COMPONENT              STATUS              │
│  ──────────────────────────────────────────────────────────────────────────── │
│                                                                                │
│  1. CV UPLOAD                                                            │
│     ├── Upload Endpoint     cv_upload_handler.py          ✅ DONE               │
│     ├── Parser            cv_parser.py                 ✅ DONE               │
│     ├── DAL               cv_dal.py                    ✅ DONE               │
│     └── Model             models/cv.py                  ⚠️  PARTIAL           │
│                                                                                │
│  2. COMPANY RESEARCH                                                      │
│     ├── Search            company_research_handler.py   ✅ DONE               │
│     ├── Logic             company_research.py           ✅ DONE               │
│     ├── Web Scraper       web_scraper.py               ✅ DONE               │
│     └── DAL               dynamo_dal_handler.py         ✅ DONE               │
│                                                                                │
│  3. VPR GENERATION                                                       │
│     ├── Submit            vpr_submit_handler.py        ✅ DONE               │
│     ├── Status            vpr_status_handler.py        ✅ DONE               │
│     ├── Worker            vpr_worker_handler.py        ✅ DONE               │
│     ├── Generator Logic    vpr_generator.py             ⚠️  PARTIAL (6-stage)│
│     ├── Prompt            prompts/vpr_prompt.py        ⚠️  PARTIAL          │
│     └── Model             models/vpr.py                ✅ DONE               │
│                                                                                │
│  4. CV TAILORING                                                          │
│     ├── Handler           cv_tailoring_handler.py      ⚠️  PARTIAL          │
│     ├── Logic             cv_tailoring_logic.py       ⚠️  PARTIAL (3-step) │
│     ├── Prompt            cv_tailoring_prompt.py      ⚠️  PARTIAL          │
│     ├── FVS Integration   fvs_validator.py            ✅ DONE               │
│     └── Model             models/cv.py                 ⚠️  PARTIAL          │
│                                                                                │
│  5. COVER LETTER                                                          │
│     ├── Handler           ❌ MISSING                   ❌  CRITICAL          │
│     ├── Logic             ❌ MISSING                   ❌  CRITICAL          │
│     ├── Prompt            ❌ MISSING                   ❌  CRITICAL          │
│     ├── FVS Integration   ❌ MISSING                   ❌  CRITICAL          │
│     └── Model             ❌ MISSING                   ❌  CRITICAL          │
│                                                                                │
│  6. GAP ANALYSIS                                                           │
│     ├── Handler           gap_handler.py                ⚠️  INCOMPLETE        │
│     ├── Logic             gap_analysis.py              ✅ DONE               │
│     ├── Prompt            gap_analysis_prompt.py        ⚠️  PARTIAL          │
│     ├── DAL               dynamo_dal_handler.py        ✅ DONE               │
│     └── Model             models/gap_analysis.py      ⚠️  PARTIAL          │
│                                                                                │
│  7. INTERVIEW PREP                                                        │
│     ├── Handler           ❌ MISSING                   ❌  CRITICAL          │
│     ├── Logic             ❌ MISSING                   ❌  CRITICAL          │
│     ├── Prompt            ❌ MISSING                   ❌  CRITICAL          │
│     └── Model             ❌ MISSING                   ❌  CRITICAL          │
│                                                                                │
│  8. QUALITY VALIDATOR                                                     │
│     ├── Logic             ❌ MISSING                   ❌  MISSING           │
│     ├── FVS Check         ❌ MISSING                   ❌  MISSING           │
│     ├── Anti-AI Check     ❌ MISSING                   ❌  MISSING           │
│     └── Model             ❌ MISSING                   ❌  MISSING           │
│                                                                                │
│  9. KNOWLEDGE BASE                                                         │
│     ├── Repository       ❌ MISSING                   ❌  MISSING           │
│     ├── Memory Storage    ❌ MISSING                   ❌  MISSING           │
│     ├── DAL               ❌ MISSING                   ❌  MISSING           │
│     └── Model             ❌ MISSING                   ❌  MISSING           │
│                                                                                │
└────────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 File-by-File Mapping

| JSA Requirement | File Path | Line Numbers | Status |
|-----------------|-----------|--------------|--------|
| **CV Upload** |
| Upload API | `handlers/cv_upload_handler.py` | 1-150 | ✅ DONE |
| Parse CV | `logic/cv_parser.py` | 1-200 | ✅ DONE |
| Store CV | `dal/cv_dal.py` | 1-100 | ✅ DONE |
| CV Model | `models/cv.py` | 1-200 | ⚠️ PARTIAL |
| **Job Research** |
| Research API | `handlers/company_research_handler.py` | 1-120 | ✅ DONE |
| Search Logic | `logic/company_research.py` | 1-300 | ✅ DONE |
| Web Scraper | `logic/web_scraper.py` | 1-150 | ✅ DONE |
| **VPR** |
| Submit API | `handlers/vpr_submit_handler.py` | 1-180 | ✅ DONE |
| Status API | `handlers/vpr_status_handler.py` | 1-100 | ✅ DONE |
| Worker | `handlers/vpr_worker_handler.py` | 1-200 | ✅ DONE |
| Generator | `logic/vpr_generator.py` | 1-250 | ⚠️ PARTIAL |
| VPR Prompt | `logic/prompts/vpr_prompt.py` | 1-300 | ⚠️ PARTIAL |
| VPR Model | `` | 1models/vpr.py-150 | ✅ DONE |
| **CV Tailoring** |
| Tailoring API | `handlers/cv_tailoring_handler.py` | 1-200 | ⚠️ PARTIAL |
| Tailoring Logic | `logic/cv_tailoring_logic.py` | 1-150 | ⚠️ PARTIAL |
| Prompt | `logic/prompts/cv_tailoring_prompt.py` | 1-250 | ⚠️ PARTIAL |
| FVS | `logic/fvs_validator.py` | 1-300 | ✅ DONE |
| **Cover Letter** |
| API Handler | `handlers/cover_letter_handler.py` | ❌ MISSING | ❌ CRITICAL |
| Logic | `logic/cover_letter_logic.py` | ❌ MISSING | ❌ CRITICAL |
| Prompt | `logic/prompts/cover_letter_prompt.py` | ❌ MISSING | ❌ CRITICAL |
| **Gap Analysis** |
| Gap API | `handlers/gap_handler.py` | 1-50 | ⚠️ INCOMPLETE |
| Gap Logic | `logic/gap_analysis.py` | 1-200 | ✅ DONE |
| Gap Prompt | `logic/prompts/gap_prompt.py` | 1-150 | ⚠️ PARTIAL |
| Gap Model | `models/gap_analysis.py` | 1-100 | ⚠️ PARTIAL |
| **Interview Prep** |
| Interview API | `handlers/interview_prep_handler.py` | ❌ MISSING | ❌ CRITICAL |
| Interview Logic | `logic/interview_prep.py` | ❌ MISSING | ❌ CRITICAL |
| Interview Prompt | `logic/prompts/interview_prompt.py` | ❌ MISSING | ❌ CRITICAL |
| **Quality Validator** |
| Validator Logic | `logic/quality_validator.py` | ❌ MISSING | ❌ MISSING |
| FVS Check | `logic/fvs_quality.py` | ❌ MISSING | ❌ MISSING |
| **Knowledge Base** |
| KB Repository | `dal/knowledge_repository.py` | ❌ MISSING | ❌ MISSING |
| KB Logic | `logic/knowledge_base.py` | ❌ MISSING | ❌ MISSING |

---

## 3. VPR Feature Detail

### 3.1 JSA VPR Requirements → CareerVP Implementation

```
┌─────────────────────────────────────────────────────────────────┐
│                    VPR FEATURE MAPPING                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  JSA REQUIREMENT                    CAREERVP IMPLEMENTATION      │
│  ─────────────────────────────────────────────────────────────  │
│                                                                 │
│  1. INPUT ANALYSIS                                                   │
│     ├── Parse Job Description    ✅ cv_parser.py (existing)      │
│     ├── Parse CV Facts          ✅ cv_parser.py (existing)       │
│     └── Extract Requirements    ✅ vpr_generator.py (existing) │
│                                                                  │
│  2. COMPANY RESEARCH                                                 │
│     ├── Extract Keywords        ✅ company_research.py (exist)   │
│     ├── Identify Priorities     ⚠️ PARTIAL (needs work)         │
│     └── Research Culture        ✅ company_research.py (exist)   │
│                                                                  │
│  3. CANDIDATE ANALYSIS                                               │
│     ├── Map Skills              ✅ vpr_generator.py (existing)   │
│     ├── Identify Experience     ✅ vpr_generator.py (existing)  │
│     └── Find Achievements       ⚠️ PARTIAL (needs FVS)           │
│                                                                  │
│  4. ALIGNMENT MAPPING (NEW - Missing 6-Stage)                     │
│     ├── Create Match Matrix     ❌ NOT IN VPR GENERATOR           │
│     ├── Identify Gaps           ⚠️ PARTIAL (uses Gap Analysis)  │
│     └── Score Alignment         ❌ NOT IN VPR GENERATOR          │
│                                                                  │
│  5. DIFFERENTIATORS (NEW - Missing 6-Stage)                        │
│     ├── Unique Skills           ❌ NOT IN VPR GENERATOR           │
│     ├── Quantifiable Impact     ⚠️ PARTIAL (no gap integration) │
│     └── USP Definition          ⚠️ PARTIAL (no gap integration)  │
│                                                                  │
│  6. STRATEGIC NARRATIVE (NEW - Missing 6-Stage)                   │
│     ├── Career Story            ❌ NOT IN VPR GENERATOR           │
│     ├── Value Proposition       ⚠️ PARTIAL (basic)              │
│     └── Future Alignment        ❌ NOT IN VPR GENERATOR           │
│                                                                  │
│  7. META REVIEW (NEW - Missing 6-Stage)                           │
│     ├── Quality Check           ❌ NOT IN VPR GENERATOR           │
│     ├── Completeness Check      ❌ NOT IN VPR GENERATOR           │
│     └── Self-Correction         ❌ NOT IN VPR GENERATOR           │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 3.2 VPR 6-Stage Implementation Gap

```python
# REQUIRED: vpr_generator.py additions

class VPRGenerator:
    """
    VPR Generator with JSA 6-Stage methodology.

    Current Status: Missing Stages 1, 4, 5, 6
    """

    def execute(self, request: VPRRequest) -> Result[VPRResponse]:
        """
        Execute VPR following JSA 6-Stage methodology.

        STAGE 1: INPUT ANALYSIS (EXISTING - needs enhancement)
        STAGE 2: EVIDENCE EXTRACTION (EXISTING - needs gap integration)
        STAGE 3: ALIGNMENT MAPPING (MISSING - CRITICAL)
        STAGE 4: DIFFERENTIATORS (MISSING - CRITICAL)
        STAGE 5: STRATEGIC NARRATIVE (MISSING - CRITICAL)
        STAGE 6: META REVIEW (MISSING - CRITICAL)
        """
        # TODO: Implement missing stages
        pass

    # ========================================================================
    # STAGE 3: ALIGNMENT MAPPING (MISSING)
    # ========================================================================
    def _create_alignment_matrix(
        self,
        cv_facts: UserCV,
        job_requirements: JobRequirements,
        company_research: CompanyResearch,
    ) -> AlignmentMatrix:
        """
        Create matrix mapping candidate qualifications to job requirements.

        Returns:
            AlignmentMatrix with match scores, gaps, and recommendations
        """
        # MISSING - Need to implement
        raise NotImplementedError("Stage 3: Alignment Mapping not implemented")

    # ========================================================================
    # STAGE 4: DIFFERENTIATORS (MISSING)
    # ========================================================================
    def _identify_differentiators(
        self,
        cv_facts: UserCV,
        gap_responses: List[GapResponse],
        alignment: AlignmentMatrix,
    ) -> List[Differentiator]:
        """
        Identify unique selling points that differentiate from other candidates.

        Returns:
            List of differentiators with evidence
        """
        # MISSING - Need to implement
        raise NotImplementedError("Stage 4: Differentiators not implemented")

    # ========================================================================
    # STAGE 5: STRATEGIC NARRATIVE (MISSING)
    # ========================================================================
    def _build_strategic_narrative(
        self,
        cv_facts: UserCV,
        differentiators: List[Differentiator],
        alignment: AlignmentMatrix,
    ) -> StrategicNarrative:
        """
        Build cohesive narrative connecting candidate journey to role.

        Returns:
            StrategicNarrative with UVP and career story
        """
        # MISSING - Need to implement
        raise NotImplementedError("Stage 5: Strategic Narrative not implemented")

    # ========================================================================
    # STAGE 6: META REVIEW (MISSING)
    # ========================================================================
    def _meta_review(
       : StrategicNarrative,
        self,
        narrative differentiators: List[Differentiator],
        alignment: AlignmentMatrix,
    ) -> QualityCheck:
        """
        Review and score generated VPR for quality.

        Returns:
            QualityCheck with score and improvement suggestions
        """
        # MISSING - Need to implement
        raise NotImplementedError("Stage 6: Meta Review not implemented")
```

### 3.3 VPR Test Coverage

| Test | Status | File | Line |
|------|--------|------|------|
| Input parsing | ✅ PASS | `tests/unit/test_vpr_generator.py` | 1-50 |
| Evidence extraction | ✅ PASS | `tests/unit/test_vpr_generator.py` | 50-100 |
| Alignment matrix | ❌ MISSING | - | - |
| Differentiators | ❌ MISSING | - | - |
| Strategic narrative | ❌ MISSING | - | - |
| Meta review | ❌ MISSING | - | - |
| Gap integration | ⚠️ PARTIAL | `tests/unit/test_vpr_generator.py` | 100-150 |
| Full flow E2E | ⚠️ PARTIAL | `tests/e2e/test_vpr.py` | 1-50 |

---

## 4. CV Tailoring Feature Detail

### 4.1 JSA CV Tailoring Requirements → CareerVP Implementation

```
┌─────────────────────────────────────────────────────────────────┐
│                    CV TAILORING FEATURE MAPPING                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  JSA REQUIREMENT                    CAREERVP IMPLEMENTATION      │
│  ─────────────────────────────────────────────────────────────  │
│                                                                 │
│  1. ANALYSIS PHASE                                                   │
│     ├── Parse Target JD       ✅ cv_tailoring_logic.py (exist)   │
│     ├── Extract Keywords      ✅ cv_tailoring_logic.py (exist)   │
│     └── Identify Requirements ✅ cv_tailoring_logic.py (exist)   │
│                                                                  │
│  2. EXTRACTION PHASE                                                 │
│     ├── Match Skills          ✅ cv_tailoring_logic.py (exist)   │
│     ├── Find Achievements     ✅ cv_tailoring_logic.py (exist)   │
│     └── Identify Gaps         ⚠️ PARTIAL (no gap integration)   │
│                                                                  │
│  3. TAILORING PHASE (MISSING 3-Step)                               │
│     ├── Draft Tailored CV    ⚠️ PARTIAL (no FVS)                 │
│     ├── FVS Verification     ⚠️ PARTIAL (separate)                │
│     ├── ATS Score Check      ❌ NOT IMPLEMENTED                   │
│     └── Self-Correction       ❌ NOT IMPLEMENTED                   │
│                                                                  │
│  4. VERIFICATION PHASE (MISSING)                                    │
│     ├── Fact Verification    ⚠️ PARTIAL (FVS separate)            │
│     ├── Keyword Density      ❌ NOT IMPLEMENTED                   │
│     ├── Format Compliance     ❌ NOT IMPLEMENTED                   │
│     └── Quality Score         ❌ NOT IMPLEMENTED                   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 4.2 CV Tailoring 3-Step Implementation Gap

```python
# REQUIRED: cv_tailoring_logic.py additions

class CVTailoringLogic:
    """
    CV Tailoring with JSA 3-Step Verification.

    Current Status: Missing Steps 2 & 3
    """

    def execute(self, request: CVTailoringRequest) -> Result[TailoredCV]:
        """
        Execute CV tailoring following JSA 3-Step methodology.

        STEP 1: ANALYSIS & EXTRACTION (EXISTING)
        STEP 2: DRAFT & VERIFY (MISSING - CRITICAL)
        STEP 3: FINALIZE & OPTIMIZE (MISSING - CRITICAL)
        """
        pass

    # ========================================================================
    # STEP 2: DRAFT & VERIFY (MISSING)
    # ========================================================================
    def _draft_and_verify(
        self,
        draft: TailoredCV,
        requirements: List[Requirement],
        gap_responses: List[GapResponse],
    ) -> VerificationResult:
        """
        Draft tailored CV and verify against requirements.

        This is the core 3-step verification:
        1. Draft CV based on analysis
        2. Run FVS verification
        3. Self-correct based on gaps
        """
        # MISSING - Need to implement
        raise NotImplementedError("Step 2: Draft & Verify not implemented")

    def _run_fvs_verification(
        self,
        cv: TailoredCV,
        original: UserCV,
    ) -> FVSResult:
        """
        Run Fact Verification System on tailored CV.

        Checks:
        - IMMUTABLE facts unchanged (dates, titles, companies)
        - VERIFIABLE facts have supporting evidence
        - FLEXIBLE framing only where allowed
        """
        # EXISTS - fvs_validator.py
        return fvs_validator.verify(cv, original)

    def _calculate_ats_score(
        self,
        cv: TailoredCV,
        job_description: str,
    ) -> ATSScore:
        """
        Calculate ATS compatibility score.

        Returns:
            ATSScore with breakdown by section
        """
        # MISSING - Need to implement
        raise NotImplementedError("ATS Score calculation not implemented")

    def _self_correct(
        self,
        cv: TailoredCV,
        verification: VerificationResult,
    ) -> TailoredCV:
        """
        Apply corrections based on verification results.
        """
        # MISSING - Need to implement
        raise NotImplementedError("Self-correction not implemented")

    # ========================================================================
    # STEP 3: FINALIZE & OPTIMIZE (MISSING)
    # ========================================================================
    def _finalize_and_optimize(
        self,
        verified: TailoredCV,
        ats_score: ATSScore,
        differentiators: List[str],
    ) -> TailoredCV:
        """
        Finalize CV with optimizations for impact.

        Actions:
        1. Reorder bullets by impact
        2. Add quantified metrics where missing
        3. Optimize for ATS keywords
        4. Ensure consistency in formatting
        """
        # MISSING - Need to implement
        raise NotImplementedError("Finalize & Optimize not implemented")
```

### 4.3 CV Tailoring Gap Integration (CRITICAL)

```python
# REQUIRED: Integration with Gap Analysis

class CVTailoringWithGapIntegration:
    """
    CV Tailoring that consumes Gap Analysis responses.

    JSA Requirement: CV should use gap responses to enhance content.
    """

    def _inject_gap_evidence(
        self,
        draft_cv: TailoredCV,
        gap_responses: List[GapResponse],
        job_requirements: JobRequirements,
    ) -> TailoredCV:
        """
        Enhance CV bullets with quantified gap response evidence.

        Example:
        - Original bullet: "Improved team productivity"
        - Gap response: "Led team of 8, improved productivity by 40%"
        - Enhanced bullet: "Led team of 8, improving productivity by 40%"
        """
        enhanced = copy.deepcopy(draft_cv)

        # Filter to CV_IMPACT responses only
        cv_impact_responses = [
            r for r in gap_responses
            if r.evidence_type == GapQuestionType.CV_IMPACT
        ]

        for exp in enhanced.work_experience:
            enhanced_bullets = []
            for bullet in exp.bullets:
                # Find matching gap response
                matching_gap = self._find_matching_gap(
                    bullet, cv_impact_responses
                )
                if matching_gap:
                    # Enhance with quantified evidence
                    enhanced_bullet = self._enhance_bullet(
                        bullet, matching_gap
                    )
                    enhanced_bullets.append(enhanced_bullet)
                else:
                    enhanced_bullets.append(bullet)

            exp.bullets = enhanced_bullets

        return enhanced

    def _find_matching_gap(
        self,
        bullet: str,
        gap_responses: List[GapResponse],
    ) -> Optional[GapResponse]:
        """Find gap response that matches bullet content."""
        # MISSING - Need to implement semantic matching
        raise NotImplementedError("Gap matching not implemented")
```

---

## 5. Cover Letter Feature Detail

### 5.1 JSA Cover Letter Requirements (CRITICAL - NOT IMPLEMENTED)

```
┌─────────────────────────────────────────────────────────────────┐
│                    COVER LETTER FEATURE MAPPING                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  JSA REQUIREMENT                    STATUS                      │
│  ─────────────────────────────────────────────────────────────  │
│                                                                 │
│  1. REFERENCE CLASS PRIMING                                            │
│     ├── Load UserCV            ❌ HANDLER MISSING                 │
│     ├── Load VPR              ❌ HANDLER MISSING                 │
│     └── Load Company Research  ❌ HANDLER MISSING                 │
│                                                                      │
│  2. SCAFFOLDED PROMPT STRUCTURE                                     │
│     ├── Reference User        ❌ HANDLER MISSING                 │
│     ├── Reference Company     ❌ HANDLER MISSING                 │
│     ├── Position Context      ❌ HANDLER MISSING                 │
│     └── Value Proposition     ❌ HANDLER MISSING                 │
│                                                                      │
│  3. PARAGRAPH 1: HOOK                                               │
│     ├── Unique Value Prop    ❌ NOT IMPLEMENTED                   │
│     ├── Company Reference    ❌ NOT IMPLEMENTED                   │
│     └── 80-100 words         ❌ NOT IMPLEMENTED                   │
│                                                                      │
│  4. PARAGRAPH 2: PROOF POINTS                                       │
│     ├── 3 Requirements       ❌ NOT IMPLEMENTED                   │
│     ├── Claim + Proof Format ❌ NOT IMPLEMENTED                   │
│     └── Quantified Evidence  ❌ NOT IMPLEMENTED                   │
│                                                                      │
│  5. PARAGRAPH 3: CLOSE                                               │
│     ├── Time-Saver Angle     ❌ NOT IMPLEMENTED                   │
│     ├── 60-80 words          ❌ NOT IMPLEMENTED                   │
│     └── Call to Action       ❌ NOT IMPLEMENTED                   │
│                                                                      │
│  6. FACT VERIFICATION                                                │
│     ├── Match Claims to CV   ❌ NOT IMPLEMENTED                   │
│     └── Verify Numbers       ❌ NOT IMPLEMENTED                   │
│                                                                      │
│  7. ANTI-AI DETECTION                                               │
│     ├── Avoid AI Phrases     ❌ NOT IMPLEMENTED                   │
│     ├── Varied Sentence Str  ❌ NOT IMPLEMENTED                   │
│     └── Natural Transitions  ❌ NOT IMPLEMENTED                   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 5.2 Cover Letter Implementation Requirements

```python
# REQUIRED: handlers/cover_letter_handler.py

class CoverLetterHandler:
    """
    Cover Letter Generation Handler.

    JSA Requirement: Generate 3-paragraph cover letter with scaffolded prompt.
    CONSUMES: UserCV, VPRResponse, GapResponses, CompanyResearch
    """

    def __init__(
        self,
        llm: LLMClient,
        kb_repo: KnowledgeBaseRepository,
        cv_repo: CVRepository,
        vpr_repo: VPRRepository,
        company_repo: CompanyResearchRepository,
        fvs: FVSValidator,
    ):
        self.llm = llm
        self.kb_repo = kb_repo
        self.cv_repo = cv_repo
        self.vpr_repo = vpr_repo
        self.company_repo = company_repo  # NEW: Company Research input
        self.fvs = fvs

    @logger.inject_lambda_context
    @tracer.capture_lambda_handler
    def lambda_handler(self, event: dict, context: Any) -> dict:
        """Generate cover letter."""
        # 1. Parse request
        request = CoverLetterRequest(**json.loads(event["body"]))

        # 2. Load context from Knowledge Base
        cv = self.cv_repo.get(request.cv_id)
        vpr = self.vpr_repo.get_latest(request.job_id)
        gap_responses = self.kb_repo.get_gap_responses(request.user_email)
        company_research = self.company_repo.get_by_job(request.job_id)  # NEW

        # 3. Build scaffolded prompt
        prompt = self._build_scaffolded_prompt(
            cv=cv,
            vpr=vpr,
            company_research=company_research,  # UPDATED: pass company research
            gap_responses=gap_responses,
            job_description=request.job_description,
        )

        # 4. Generate cover letter
        draft = self.llm.generate(prompt)

        # 5. FVS verification
        fvs_result = self.fvs.verify(draft, cv)

        # 6. Anti-AI detection
        anti_ai_result = self._apply_anti_ai_patterns(draft)

        # 7. Return final
        return CoverLetterResponse(
            cover_letter=anti_ai_result.final_text,
            fvs_verified=fvs_result.verified,
            anti_ai_score=anti_ai_result.score,
            metadata={
                "paragraph_1_word_count": anti_ai_result.paragraph_1_words,
                "paragraph_2_word_count": anti_ai_result.paragraph_2_words,
                "paragraph_3_word_count": anti_ai_result.paragraph_3_words,
            }
        )

    def _build_scaffolded_prompt(
        self,
        cv: UserCV,
        vpr: VPRResponse,
        company_research: CompanyResearch,
        gap_responses: List[GapResponse],
        job_description: str,
    ) -> str:
        """
        Build scaffolded prompt following JSA structure.

        INPUTS (from Knowledge Base):
        - UserCV: Candidate's profile and experience
        - VPRResponse: Value proposition and differentiators
        - CompanyResearch: Company culture, values, recent news ← KEY INPUT
        - GapResponses: Impact statements and interview prep answers
        - Job Requirements: Target position requirements

        Prompt Structure:
        1. Reference Class Priming (User + Company context)
        2. Paragraph 1: Hook (80-100 words) ← Uses Company Research
        3. Paragraph 2: Proof Points (3 requirements) ← Uses VPR + Gap Responses
        4. Paragraph 3: Close (60-80 words) ← Uses UVP + Company fit

        Company Research Usage:
        - Paragraph 1: Reference company mission/values/news
        - Paragraph 2: Align proof points with company culture
        - Paragraph 3: Emphasize cultural alignment fit
        """
        # MISSING - Need to implement full prompt
        raise NotImplementedError("Cover letter prompt not implemented")
```

### 5.3 Cover Letter Integration Flow

```
┌─────────────────────────────────────────────────────────────────┐
│              COVER LETTER INTEGRATION FLOW                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  UserCV ──────────┐                                              │
│                   │                                              │
│  Job Description ─┼──► GAP ANALYSIS ───► GapResponses           │
│       │           │     (3-5 questions)     │                   │
│       │           │                         │                   │
│       └───────────┼─────────────────────────┼───────────────────┘
│                   │                         │
│                   ▼                         ▼
│          ┌────────────────┐      ┌────────────────┐
│          │ VPR GENERATOR  │      │ COMPANY RESEARCH │
│          │                │      │  (MISSING)       │
│          │ • UVP          │      │                  │
│          │ • Differentiators     │ • Mission/Values │
│          │ • Strategic Narrative  │ • Recent News   │
│          └────────┬───────┘      │ • Culture       │
│                   │              └────────┬───────┘
│                   │                       │
│                   ▼                       │
│          ┌────────────────┐               │
│          │ VPRResponse    │◄──────────────┘
│          │                │
│          └────────┬───────┘
│                   │
│                   ▼
│          ┌────────────────────────────────────────┐
│          │       COVER LETTER GENERATOR           │
│          │                                        │
│          │ INPUTS:                               │
│          │ • UserCV                              │
│          │ • VPRResponse (UVP + Differentiators) │
│          │ • GapResponses (Impact statements)     │
│          │ • CompanyResearch ⬅ CRITICAL          │
│          │                                        │
│          │ OUTPUT:                               │
│          │ • 3-paragraph cover letter            │
│          │ • FVS verified for facts              │
│          │ • Anti-AI detection compliant         │
│          └────────────────────────────────────────┘
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 5.4 Cover Letter Files Required

| File | Status | Description |
|------|--------|-------------|
| `handlers/cover_letter_handler.py` | ❌ MISSING | Main handler |
| `logic/cover_letter_logic.py` | ❌ MISSING | Business logic |
| `logic/prompts/cover_letter_prompt.py` | ❌ MISSING | Scaffolded prompt |
| `models/cover_letter.py` | ❌ MISSING | Request/Response models |
| `tests/unit/test_cover_letter.py` | ❌ MISSING | Unit tests |
| `tests/integration/test_cover_letter.py` | ❌ MISSING | Integration tests |
| `tests/e2e/test_cover_letter.py` | ❌ MISSING | E2E tests |

---

## 6. Gap Analysis Feature Detail

### 6.1 JSA Gap Analysis Requirements → CareerVP Implementation

```
┌─────────────────────────────────────────────────────────────────┐
│                    GAP ANALYSIS FEATURE MAPPING                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  JSA REQUIREMENT                    CAREERVP IMPLEMENTATION      │
│  ─────────────────────────────────────────────────────────────  │
│                                                                 │
│  1. CONTEXTUAL QUESTION GENERATION                                  │
│     ├── Based on Job Posting    ✅ gap_analysis.py (exist)       │
│     ├── Based on CV             ✅ gap_analysis.py (exist)       │
│     └── 3-5 Questions Max        ✅ gap_analysis.py (exist)       │
│                                                                      │
│  2. QUESTION TAGGING SYSTEM                                         │
│     ├── [CV IMPACT] Tag          ⚠️ PARTIAL (needs enforcement) │
│     ├── [INTERVIEW/MVP ONLY] Tag ⚠️ PARTIAL (needs enforcement) │
│     └── Strategic Intent         ❌ NOT IMPLEMENTED               │
│                                                                      │
│  3. MEMORY/AWARENESS                                               │
│     ├── Skip Recurring Themes   ❌ NOT IMPLEMENTED                 │
│     ├── Prioritize by Job       ❌ NOT IMPLEMENTED                 │
│     └── Track Question History   ❌ NOT IMPLEMENTED                 │
│                                                                      │
│  4. RESPONSE HANDLING                                               │
│     ├── Store Response          ⚠️ PARTIAL (no Knowledge Base)    │
│     ├── Quantify Responses      ⚠️ PARTIAL (needs enhancement)    │
│     └── Tag Response Type       ⚠️ PARTIAL (no enforcement)     │
│                                                                      │
│  5. INTEGRATION OUTPUT                                               │
│     ├── For VPR                 ⚠️ PARTIAL (no integration)      │
│     ├── For CV Tailoring        ⚠️ PARTIAL (no integration)      │
│     └── For Cover Letter        ❌ NOT IMPLEMENTED                 │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 6.2 Gap Analysis Lambda Handler (MISSING)

```python
# REQUIRED: handlers/gap_handler.py

class GapAnalysisHandler:
    """
    Gap Analysis Lambda Handler.

    JSA Requirement: Generate contextual questions and handle responses.
    """

    def __init__(
        self,
        gap_logic: GapAnalysisLogic,
        kb_repo: KnowledgeBaseRepository,
        cv_repo: CVRepository,
    ):
        self.gap_logic = gap_logic
        self.kb_repo = kb_repo
        self.cv_repo = cv_repo

    @logger.inject_lambda_context
    @tracer.capture_lambda_handler
    def generate_questions(self, event: dict, context: Any) -> dict:
        """
        Generate gap analysis questions for a job application.

        Steps:
        1. Load CV and Job Description
        2. Analyze missing qualifications
        3. Generate contextual questions
        4. Apply [CV IMPACT] and [INTERVIEW/MVP ONLY] tags
        5. Return questions with metadata
        """
        request = GapQuestionRequest(**json.loads(event["body"]))

        # Load context
        cv = self.cv_repo.get(request.cv_id)
        job = self._parse_job_description(request.job_description)

        # Get existing questions to skip recurring themes
        existing_questions = self.kb_repo.get_gap_questions(
            user_email=request.user_email,
        )

        # Generate questions
        questions = self.gap_logic.generate_questions(
            cv=cv,
            job_requirements=job.requirements,
            existing_questions=existing_questions,
            max_questions=10,
        )

        # Apply contextual tags
        tagged_questions = [
            GapQuestionWithTags(
                question=q,
                tags=self._determine_tags(q, cv, job),
                strategic_intent=self._get_strategic_intent(q, job),
                evidence_gap=self._identify_gap(q, cv),
            )
            for q in questions
        ]

        # Store questions
        self.kb_repo.store_questions(
            user_email=request.user_email,
            application_id=request.application_id,
            questions=tagged_questions,
        )

        return {
            "statusCode": 200,
            "body": json.dumps({
                "questions": [q.dict() for q in tagged_questions],
                "count": len(tagged_questions),
            }),
        }

    @tracer.capture_lambda_handler
    def submit_responses(self, event: dict, context: Any) -> dict:
        """
        Handle gap analysis response submission.

        Steps:
        1. Validate responses
        2. Quantify where possible
        3. Store with tagging
        4. Notify downstream features
        """
        request = GapResponseRequest(**json.loads(event["body"]))

        # Validate and quantify
        quantified_responses = [
            self.gap_logic.quantify_response(
                question=q,
                response=r,
            )
            for q, r in zip(request.questions, request.responses)
        ]

        # Store responses
        self.kb_repo.store_responses(
            user_email=request.user_email,
            application_id=request.application_id,
            responses=quantified_responses,
        )

        # Trigger downstream updates
        self._notify_features(request.application_id)

        return {
            "statusCode": 200,
            "body": json.dumps({
                "status": "saved",
                "responses_stored": len(quantified_responses),
            }),
        }

    def _determine_tags(
        self,
        question: GapQuestion,
        cv: UserCV,
        job: JobDescription,
    ) -> List[str]:
        """
        Determine appropriate tags for question.

        Tags:
        - [CV IMPACT]: Quantifiable evidence for CV
        - [INTERVIEW/MVP ONLY]: Qualitative for interview
        """
        # MISSING - Need to implement tagging logic
        raise NotImplementedError("Question tagging not implemented")

    def _get_strategic_intent(
        self,
        question: GapQuestion,
        job: JobDescription,
    ) -> str:
        """
        Explain WHY this question matters for the application.
        """
        # MISSING - Need to implement strategic intent
        raise NotImplementedError("Strategic intent not implemented")
```

### 6.3 Gap Analysis Knowledge Base Integration (MISSING)

```python
# REQUIRED: dal/knowledge_repository.py additions

class KnowledgeBaseRepository:
    """
    Repository for persistent user knowledge.

    Stores:
    - Gap Questions
    - Gap Responses
    - Recurring Themes
    - Differentiators
    """

    def get_gap_questions(
        self,
        user_email: str,
        application_id: str = None,
    ) -> List[GapQuestion]:
        """
        Retrieve gap questions for user/application.
        """
        # MISSING - Need to implement
        raise NotImplementedError("Knowledge Base not implemented")

    def store_gap_questions(
        self,
        user_email: str,
        application_id: str,
        questions: List[GapQuestion],
    ) -> None:
        """
        Store generated gap questions.
        """
        # MISSING - Need to implement
        raise NotImplementedError("Knowledge Base not implemented")

    def get_gap_responses(
        self,
        application_id: str,
        evidence_type: GapQuestionType = None,
    ) -> List[GapResponse]:
        """
        Retrieve gap responses for an application.

        Can filter by evidence type:
        - CV_IMPACT: For VPR and CV Tailoring
        - INTERVIEW_MVP_ONLY: For Interview Prep
        """
        # MISSING - Need to implement
        raise NotImplementedError("Knowledge Base not implemented")

    def store_gap_responses(
        self,
        user_email: str,
        application_id: str,
        responses: List[GapResponse],
    ) -> None:
        """
        Store gap responses with quantification.
        """
        # MISSING - Need to implement
        raise NotImplementedError("Knowledge Base not implemented")

    def get_recurring_themes(
        self,
        user_email: str,
    ) -> List[RecurringTheme]:
        """
        Get recurring themes across applications.
        """
        # MISSING - Need to implement
        raise NotImplementedError("Knowledge Base not implemented")

    def update_recurring_themes(
        self,
        user_email: str,
        responses: List[GapResponse],
    ) -> None:
        """
        Update recurring themes based on new responses.
        """
        # MISSING - Need to implement
        raise NotImplementedError("Knowledge Base not implemented")
```

---

## 7. Interview Prep Feature Detail

### 7.1 JSA Interview Prep Requirements (CRITICAL - NOT IMPLEMENTED)

```
┌─────────────────────────────────────────────────────────────────┐
│                    INTERVIEW PREP FEATURE MAPPING               │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  JSA REQUIREMENT                    STATUS                      │
│  ─────────────────────────────────────────────────────────────  │
│                                                                 │
│  1. QUESTION PREDICTION                                             │
│     ├── Technical Questions      ❌ NOT IMPLEMENTED             │
│     ├── Behavioral Questions     ❌ NOT IMPLEMENTED             │
│     ├── Company-Specific         ❌ NOT IMPLEMENTED             │
│     └── Gap-Based Questions      ❌ NOT IMPLEMENTED             │
│                                                                      │
│  2. STAR FORMATTING                                                 │
│     ├── Situation Context        ❌ NOT IMPLEMENTED             │
│     ├── Task Definition         ❌ NOT IMPLEMENTED             │
│     ├── Action Taken            ❌ NOT IMPLEMENTED             │
│     └── Result Metrics          ❌ NOT IMPLEMENTED             │
│                                                                      │
│  3. RESPONSE GENERATION                                             │
│     ├── Tailor to Role          ❌ NOT IMPLEMENTED             │
│     ├── Use Gap Responses        ❌ NOT IMPLEMENTED             │
│     └── Add Quantified Evidence  ❌ NOT IMPLEMENTED             │
│                                                                      │
│  4. CATEGORY ORGANIZATION                                            │
│     ├── Technical Competency    ❌ NOT IMPLEMENTED             │
│     ├── Leadership/Management   ❌ NOT IMPLEMENTED             │
│     ├── Problem Solving         ❌ NOT IMPLEMENTED             │
│     ├── Cultural Fit            ❌ NOT IMPLEMENTED             │
│     └── Company-Specific        ❌ NOT IMPLEMENTED             │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 7.2 Interview Prep Files Required

| File | Status | Description |
|------|--------|-------------|
| `handlers/interview_prep_handler.py` | ❌ MISSING | Main handler |
| `logic/interview_prep.py` | ❌ MISSING | Question prediction & response generation |
| `logic/prompts/interview_prep_prompt.py` | ❌ MISSING | STAR-formatted prompts |
| `models/interview_prep.py` | ❌ MISSING | Request/Response models |
| `tests/unit/test_interview_prep.py` | ❌ MISSING | Unit tests |
| `tests/integration/test_interview_prep.py` | ❌ MISSING | Integration tests |
| `tests/e2e/test_interview_prep.py` | ❌ MISSING | E2E tests |

---

## 8. Feature Integration Flows

### 8.1 Complete User Journey

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         COMPLETE USER JOURNEY FLOW                               │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  PHASE 1: PREPARATION                                                           │
│  ───────────────────────────────────────────────────────────────────────────    │
│                                                                                 │
│  ┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐              │
│  │   CV    │────▶│  VPR     │────▶│   GAP    │────▶│INTERVIEW │              │
│  │  UPLOAD │     │GENERATOR │     │ ANALYSIS │     │   PREP   │              │
│  └──────────┘     └──────────┘     └──────────┘     └──────────┘              │
│       │                │                │                │                       │
│       │                │                │                │                       │
│       └────────────────┴────────────────┴────────────────┘                       │
│                                │                                                  │
│                                ▼                                                  │
│                       ┌──────────────┐                                          │
│                       │  KNOWLEDGE   │                                          │
│                       │     BASE     │                                          │
│                       │  (Memory)    │                                          │
│                       └──────────────┘                                          │
│                                                                                 │
│  PHASE 2: APPLICATION                                                            │
│  ───────────────────────────────────────────────────────────────────────────    │
│                                                                                 │
│  ┌──────────┐     ┌──────────┐     ┌──────────┐                              │
│  │   CV    │────▶│   CV     │────▶│  COVER   │                              │
│  │  UPLOAD │     │ TAILORING │     │  LETTER  │                              │
│  └──────────┘     └──────────┘     └──────────┘                              │
│       │                │                │                                       │
│       │                │                │                                       │
│       └────────────────┴────────────────┘                                       │
│                                │                                                  │
│                                ▼                                                  │
│                       ┌──────────────┐                                          │
│                       │  KNOWLEDGE   │                                          │
│                       │     BASE     │                                          │
│                       │  (Updated)  │                                          │
│                       └──────────────┘                                          │
│                                                                                 │
│  PHASE 3: INTERVIEW (Optional)                                                   │
│  ───────────────────────────────────────────────────────────────────────────    │
│                                                                                 │
│       ┌──────────────────────────────────────────┐                             │
│       │     Enhanced by Previous Phase Data      │                             │
│       │                                          │                             │
│       │  • VPR differentiators                  │                             │
│       │  • Gap response evidence                  │                             │
│       │  • Tailored CV content                   │                             │
│       │  • Company research insights              │                             │
│       └──────────────────────────────────────────┘                             │
│                                │                                                  │
│                                ▼                                                  │
│                       ┌──────────────┐                                          │
│                       │    STAR      │                                          │
│                       │  FORMATTED   │                                          │
│                       │  RESPONSES   │                                          │
│                       └──────────────┘                                          │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### 8.2 Data Flow Between Features

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         DATA FLOW DIAGRAM                                       │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  USER CV (Source of Truth)                                                      │
│       │                                                                           │
│       ├─────────────────────┬─────────────────────┬─────────────────────┐        │
│       │                     │                     │                     │        │
│       ▼                     ▼                     ▼                     ▼        │
│  ┌─────────┐          ┌─────────┐          ┌─────────┐          ┌─────────┐   │
│  │   VPR   │◀─────────│   GAP   │◀────────│   CV    │─────────▶│INTERVIEW│   │
│  │GENERATOR│  Evidence│ANALYSIS │ Evidence│ TAILORING│          │  PREP   │   │
│  └─────────┘          └─────────┘          └─────────┘          └─────────┘   │
│       │                     │                     │                     │        │
│       │                     │                     │                     │        │
│       └─────────────────────┴─────────────────────┴──────────────────┘        │
│                                         │                                       │
│                                         ▼                                       │
│                              ┌─────────────────┐                               │
│                              │   KNOWLEDGE BASE │                               │
│                              │   (Persistent)   │                               │
│                              └─────────────────┘                               │
│                                         │                                       │
│                                         ▼                                       │
│                              ┌─────────────────┐                               │
│                              │  QUALITY        │                               │
│                              │  VALIDATOR      │                               │
│                              └─────────────────┘                               │
│                                                                                 │
│  DATA SHARED:                                                                    │
│  ─────────────                                                                   │
│  • Gap Responses (VPR, CV Tailoring, Interview Prep)                           │
│  • Differentiators (All features)                                               │
│  • Recurring Themes (Gap Analysis → All features)                               │
│  • UVP (VPR → Cover Letter → Interview Prep)                                    │
│  • Company Research (All features)                                              │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### 8.3 Knowledge Base Schema

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         KNOWLEDGE BASE SCHEMA                                    │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  DynamoDB Table: careervp-knowledge-base-{env}                                 │
│                                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │  PARTITION KEY (pk): USER#{user_email}                                 │   │
│  │  SORT KEY (sk): Multiple patterns                                        │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                                 │
│  ITEM TYPES:                                                                   │
│  ─────────────                                                                   │
│                                                                                 │
│  1. COMPANY_RESEARCH#{application_id}                                           │
│     {                                                                           │
│       "pk": "USER#user@example.com",                                           │
│       "sk": "COMPANY_RESEARCH#app-123",                                        │
│       "company_name": "Acme Inc",                                              │
│       "company_url": "https://acme.com",                                        │
│       "mission": "Connecting the world...",                                     │
│       "values": ["Innovation", "Customer Focus", "Integrity"],                 │
│       "recent_news": [                                                          │
│         {"title": "Q4 Revenue Growth", "date": "2026-01-15"},                  │
│         {"title": "New Product Launch", "date": "2025-12-01"}                   │
│       ],                                                                        │
│       "culture": "Fast-paced, collaborative, remote-first",                     │
│       "products_services": ["Cloud Platform", "Analytics Suite"],              │
│       "competitors": ["Competitor A", "Competitor B"],                          │
│       "funding_status": "Public company",                                      │
│       "size_range": "1000-5000 employees",                                       │
│       "industry": "Technology",                                                 │
│       "used_in": ["cover_letter", "vpr"],  ⬅ KEY: Cover Letter uses this      │
│       "created_at": "2026-02-10T08:00:00Z",                                   │
│       "ttl": 18144000  # 210 days from now                                    │
│     }                                                                           │
│                                                                                 │
│  2. GAP_QUESTION#{application_id}#{question_id}                                │
│     {                                                                           │
│       "pk": "USER#user@example.com",                                           │
│       "sk": "GAP_QUESTION#app-123#q-001",                                     │
│       "question_text": "...",                                                  │
│       "tags": ["CV_IMPACT", "INTERVIEW/MVP ONLY"],                             │
│       "strategic_intent": "...",                                               │
│       "evidence_gap": "...",                                                   │
│       "created_at": "2026-02-10T10:00:00Z"                                    │
│     }                                                                           │
│                                                                                 │
│  3. GAP_RESPONSE#{application_id}#{question_id}                                │
│     {                                                                           │
│       "pk": "USER#user@example.com",                                           │
│       "sk": "GAP_RESPONSE#app-123#q-001",                                       │
│       "response_text": "...",                                                  │
│       "quantifiable_data": {"percentage": 40, "team_size": 8},                │
│       "evidence_type": "CV_IMPACT",                                             │
│       "used_in": ["vpr", "cv_tailoring"],                                      │
│       "created_at": "2026-02-10T10:30:00Z"                                    │
│     }                                                                           │
│                                                                                 │
│  4. THEME#{theme_id}                                                           │
│     {                                                                           │
│       "pk": "USER#user@example.com",                                           │
│       "sk": "THEME#leadership",                                                │
│       "pattern": "Led team*",                                                  │
│       "occurrences": 5,                                                        │
│       "applications": ["app-123", "app-456"],                                   │
│       "created_at": "2026-02-01T00:00:00Z"                                    │
│     }                                                                           │
│                                                                                 │
│  5. DIFFERENTIATOR#{application_id}                                             │
│     {                                                                           │
│       "pk": "USER#user@example.com",                                           │
│       "sk": "DIFFERENTIATOR#app-123",                                         │
│       "differentiators": [                                                      │
│         {"text": "40% productivity increase", "source": "gap_response"},       │
│         {"text": "Led 8-person team", "source": "cv"}                           │
│       ],                                                                        │
│       "created_at": "2026-02-10T10:00:00Z"                                    │
│     }                                                                           │
│                                                                                 │
│  6. APPLICATION#{application_id}                                                │
│     {                                                                           │
│       "pk": "USER#user@example.com",                                           │
│       "sk": "APPLICATION#app-123",                                             │
│       "cv_id": "cv-123",                                                       │
│       "job_description_hash": "...",                                             │
│       "company_name": "Acme Inc",                                               │
│       "status": "in_progress",                                                 │
│       "created_at": "2026-02-10T09:00:00Z",                                   │
│       "updated_at": "2026-02-10T11:00:00Z"                                    │
│     }                                                                           │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## 9. Data Sharing Architecture

### 9.1 What Each Feature Provides and Consumes

| Feature | PROVIDES | CONSUMES |
|---------|----------|----------|
| **CV Upload** | UserCV | - |
| **Company Research** | CompanyResearch | Job URL |
| **VPR Generator** | VPRResponse, Differentiators | UserCV, CompanyResearch, GapResponses |
| **CV Tailoring** | TailoredCV | UserCV, VPRResponse, GapResponses |
| **Cover Letter** | CoverLetter | UserCV, VPRResponse, GapResponses, CompanyResearch |
| **Gap Analysis** | GapQuestions, GapResponses | UserCV, JobRequirements |
| **Interview Prep** | STARResponses | VPRResponse, GapResponses |
| **Knowledge Base** | Persistent Storage | All features |

### 9.2 Integration Points

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         INTEGRATION POINTS                                      │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  VPR → GAP ANALYSIS                                                             │
│  ─────────────────────                                                          │
│  VPR provides:                                                                  │
│    - Alignment matrix (identifies gaps)                                         │
│    - Missing qualifications                                                     │
│    - Role-specific requirements                                                 │
│                                                                                 │
│  Gap Analysis consumes:                                                         │
│    - List of missing qualifications                                             │
│    - Priority排序 for questions                                                 │
│                                                                                 │
│  ────────────────────────────────────────────────────────────────────────────  │
│                                                                                 │
│  GAP ANALYSIS → VPR                                                              │
│  ────────────────────                                                           │
│  Gap Analysis provides:                                                         │
│    - Quantified evidence for achievements                                       │
│    - Additional differentiators                                                │
│    - Missing experience framing                                                  │
│                                                                                 │
│  VPR consumes:                                                                  │
│    - GapResponse.quantifiable_data (enhanced bullets)                           │
│    - GapResponse.used_in_vpr = true                                             │
│                                                                                 │
│  ────────────────────────────────────────────────────────────────────────────  │
│                                                                                 │
│  GAP ANALYSIS → CV TAILORING                                                    │
│  ─────────────────────────                                                       │
│  Gap Analysis provides:                                                         │
│    - [CV IMPACT] tagged responses                                               │
│    - Quantified achievements                                                    │
│                                                                                 │
│  CV Tailoring consumes:                                                         │
│    - GapResponse for enhanced bullets                                           │
│    - Strategic framing for experience descriptions                              │
│                                                                                 │
│  ────────────────────────────────────────────────────────────────────────────  │
│                                                                                 │
│  COMPANY RESEARCH → COVER LETTER                                                │
│  ────────────────────────────                                                  │
│  Company Research provides:                                                     │
│    - Mission statement and company values                                       │
│    - Recent news and achievements                                               │
│    - Company culture description                                                 │
│    - Products and services                                                      │
│    - Industry and market position                                               │
│                                                                                 │
│  Cover Letter consumes:                                                          │
│    - Mission/values for Hook paragraph (Paragraph 1)                            │
│    - Recent news for company-specific references                                │
│    - Culture for alignment statements                                            │
│    - Products/services to demonstrate familiarity                               │
│                                                                                 │
│  Usage in Prompt:                                                               │
│    "The company [MISSION], known for [VALUES]. Recently, they                  │
│     [NEWS HIGHLIGHT]. Their culture emphasizes [CULTURE]."                     │
│                                                                                 │
│  ────────────────────────────────────────────────────────────────────────────  │
│                                                                                 │
│  VPR → COVER LETTER                                                             │
│  ───────────────────                                                             │
│  VPR provides:                                                                  │
│    - Unique Value Proposition (UVP)                                             │
│    - Differentiators list                                                       │
│    - Company-job fit score                                                      │
│                                                                                 │
│  Cover Letter consumes:                                                          │
│    - UVP for opening paragraph                                                  │
│    - Differentiators for proof points                                           │
│    - Company context for personalization                                         │
│                                                                                 │
│  ────────────────────────────────────────────────────────────────────────────  │
│                                                                                 │
│  GAP ANALYSIS → COVER LETTER                                                    │
│  ─────────────────────────                                                      │
│  Gap Analysis provides:                                                         │
│    - Quantified impact statements                                               │
│    - [CV IMPACT] tagged responses                                               │
│    - Missing qualification framing                                              │
│                                                                                 │
│  Cover Letter consumes:                                                          │
│    - GapResponse.quantifiable_data for proof points                             │
│    - GapResponse.response_text for impact statements                            │
│    - Missing qualification framing for honest gap acknowledgment               │
│                                                                                 │
│  Usage in Prompt:                                                               │
│    "In my role at [Company], I achieved [QUANTIFIED RESULT]..."               │
│                                                                                 │
│  ────────────────────────────────────────────────────────────────────────────  │
│                                                                                 │
│  GAP ANALYSIS → INTERVIEW PREP                                                  │
│  ──────────────────────────                                                     │
│  Gap Analysis provides:                                                         │
│    - [INTERVIEW/MVP ONLY] tagged responses                                      │
│    - Qualitative stories                                                        │
│    - Situational examples                                                       │
│                                                                                 │
│  Interview Prep consumes:                                                        │
│    - GapResponse for STAR-formatted answers                                     │
│    - Question-specific evidence                                                 │
│                                                                                 │
│  ────────────────────────────────────────────────────────────────────────────  │
│                                                                                 │
│  VPR + GAP ANALYSIS → QUALITY VALIDATOR                                        │
│  ────────────────────────────────────                                           │
│  VPR and Gap provide:                                                            │
│    - All generated content                                                      │
│    - Source evidence                                                            │
│    - Confidence scores                                                          │
│                                                                                 │
│  Quality Validator checks:                                                      │
│    - FVS verification (facts match source)                                      │
│    - Anti-AI detection                                                          │
│    - Cross-document consistency                                                 │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## 10. Gap Analysis: What's Missing

### 10.1 Critical Gaps (Must Fix)

| Gap | JSA Requirement | CareerVP Status | Fix Required |
|-----|-----------------|-----------------|--------------|
| **VPR 6-Stage** | JSA specifies 6 stages | 2 stages only | Implement Stages 3-6 |
| **CV 3-Step** | JSA specifies 3 steps | 1 step only | Implement Steps 2-3 |
| **Cover Letter Handler** | JSA requires cover letter | NOT IMPLEMENTED | Create full handler |
| **Gap Handler** | JSA requires lambda handler | INCOMPLETE | Complete handler + KB |
| **Interview Prep** | JSA requires interview prep | NOT IMPLEMENTED | Create full feature |
| **Knowledge Base** | JSA requires persistent memory | NOT IMPLEMENTED | Create repository + storage |

### 10.2 Integration Gaps (Must Fix)

| Integration | Status | Fix Required |
|-------------|---------|--------------|
| VPR → Gap Analysis | ❌ MISSING | Pass gap IDs to VPR |
| Gap Responses → VPR | ❌ MISSING | Load responses in VPR |
| Gap Responses → CV Tailoring | ❌ MISSING | Inject in bullets |
| VPR → Cover Letter | ❌ MISSING | Pass UVP + differentiators |
| Gap Responses → Interview Prep | ❌ MISSING | Load for STAR formatting |
| All → Knowledge Base | ❌ MISSING | Create repository |

### 10.3 Test Gaps

| Feature | Unit Tests | Integration Tests | E2E Tests |
|---------|------------|-------------------|-----------|
| VPR 6-Stage | ❌ MISSING | ❌ MISSING | ⚠️ PARTIAL |
| CV 3-Step | ❌ MISSING | ❌ MISSING | ⚠️ PARTIAL |
| Cover Letter | ❌ MISSING | ❌ MISSING | ❌ MISSING |
| Gap Handler | ⚠️ PARTIAL | ❌ MISSING | ❌ MISSING |
| Interview Prep | ❌ MISSING | ❌ MISSING | ❌ MISSING |
| Quality Validator | ❌ MISSING | ❌ MISSING | ❌ MISSING |
| Knowledge Base | ❌ MISSING | ❌ MISSING | ❌ MISSING |

---

## 11. Implementation Priority Matrix

### 11.1 Priority by Feature (Critical Path)

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                    IMPLEMENTATION PRIORITY MATRIX                                │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  PRIORITY 1: FOUNDATION (Must Do First)                                       │
│  ────────────────────────────────────────                                        │
│                                                                                 │
│  1. Knowledge Base (dal/knowledge_repository.py)                                │
│     Why: All other features depend on persistent storage                        │
│     Effort: 12h                                                                 │
│     Blocks: Gap Handler, All Integrations                                       │
│                                                                                 │
│  2. Gap Handler Complete (handlers/gap_handler.py)                              │
│     Why: Generates questions and stores responses                              │
│     Effort: 8h                                                                  │
│     Blocks: VPR Gap Integration, CV Gap Integration                             │
│                                                                                 │
│  ────────────────────────────────────────────────────────────────────────────  │
│                                                                                 │
│  PRIORITY 2: CORE FEATURES (Must Have)                                          │
│  ──────────────────────────────────────                                          │
│                                                                                 │
│  3. VPR 6-Stage Implementation                                                  │
│     Why: Core JSA differentiator - sets strategic direction                     │
│     Effort: 10h                                                                 │
│     Blocks: Cover Letter, Quality Validator                                      │
│                                                                                 │
│  4. CV Tailoring 3-Step Implementation                                          │
│     Why: Core user-facing feature - CV enhancement                              │
│     Effort: 10h                                                                 │
│     Blocks: Cover Letter (uses enhanced CV)                                      │
│                                                                                 │
│  5. Cover Letter Handler (NEW - CRITICAL)                                       │
│     Why: Required JSA feature - completes application package                   │
│     Effort: 12h                                                                 │
│     Blocks: Quality Validator                                                    │
│                                                                                 │
│  ────────────────────────────────────────────────────────────────────────────  │
│                                                                                 │
│  PRIORITY 3: INTEGRATION (Connects Features)                                     │
│  ──────────────────────────────────────────                                       │
│                                                                                 │
│  6. VPR → Gap Analysis Integration                                               │
│     Why: VPR informs Gap Analysis of missing qualifications                     │
│     Effort: 4h                                                                  │
│     Blocks: All downstream integrations                                          │
│                                                                                 │
│  7. Gap Responses → VPR Integration                                              │
│     Why: VPR uses quantified evidence from gap responses                         │
│     Effort: 4h                                                                  │
│     Blocks: VPR quality improvement                                              │
│                                                                                 │
│  8. Gap Responses → CV Tailoring Integration                                     │
│     Why: CV uses quantified evidence from gap responses                          │
│     Effort: 4h                                                                  │
│     Blocks: CV quality improvement                                               │
│                                                                                 │
│  ────────────────────────────────────────────────────────────────────────────  │
│                                                                                 │
│  PRIORITY 4: COMPLETION FEATURES                                                 │
│  ────────────────────────────────                                                │
│                                                                                 │
│  9. Interview Prep (NEW - CRITICAL)                                             │
│     Why: Required JSA feature - interview preparation                            │
│     Effort: 16h                                                                 │
│     Blocks: None (uses existing data)                                           │
│                                                                                 │
│  10. Quality Validator (NEW - MISSING)                                           │
│      Why: Validates all outputs for quality and consistency                      │
│      Effort: 12h                                                                 │
│      Blocks: Production readiness                                                 │
│                                                                                 │
│  ────────────────────────────────────────────────────────────────────────────  │
│                                                                                 │
│  PRIORITY 5: TESTING & VALIDATION                                               │
│  ───────────────────────────────────                                             │
│                                                                                 │
│  11. All Unit Tests                                                             │
│      Why: Required for production quality                                        │
│      Effort: 40h (distributed)                                                  │
│                                                                                 │
│  12. All Integration Tests                                                       │
│      Why: Required for feature integration                                        │
│      Effort: 20h (distributed)                                                  │
│                                                                                 │
│  13. All E2E Tests                                                              │
│      Why: Required for user journey validation                                   │
│      Effort: 16h (distributed)                                                   │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### 11.2 Timeline

| Week | Focus | Deliverables |
|------|-------|--------------|
| **Week 1** | Foundation | Knowledge Base + Gap Handler |
| **Week 2** | Core Features | VPR 6-Stage + CV 3-Step + Cover Letter |
| **Week 3** | Integration | All feature integrations |
| **Week 4** | Completion | Interview Prep + Quality Validator |
| **Week 5-6** | Testing | All tests + E2E validation |

---

## Summary: 1-1 Mapping Verification

| JSA Feature | CareerVP Component | 1-1 Mapping | Status |
|-------------|-------------------|-------------|--------|
| CV Upload | `cv_upload_handler.py` | ✅ | DONE |
| CV Parser | `cv_parser.py` | ✅ | DONE |
| Job Research | `company_research_handler.py` | ✅ | DONE |
| VPR Submit | `vpr_submit_handler.py` | ✅ | DONE |
| VPR Status | `vpr_status_handler.py` | ✅ | DONE |
| VPR Worker | `vpr_worker_handler.py` | ✅ | DONE |
| VPR Generator | `vpr_generator.py` | ⚠️ | PARTIAL (6-stage missing) |
| CV Tailoring | `cv_tailoring_handler.py` | ⚠️ | PARTIAL (3-step missing) |
| **Cover Letter** | `handlers/cover_letter_handler.py` | ❌ | **MISSING** |
| Gap Analysis | `gap_handler.py` | ⚠️ | INCOMPLETE |
| **Interview Prep** | `handlers/interview_prep_handler.py` | ❌ | **MISSING** |
| **Quality Validator** | `logic/quality_validator.py` | ❌ | **MISSING** |
| **Knowledge Base** | `dal/knowledge_repository.py` | ❌ | **MISSING** |

**CRITICAL ACTION ITEMS:**
1. Implement Cover Letter (12h)
2. Implement Interview Prep (16h)
3. Implement Knowledge Base (12h)
4. Complete VPR 6-Stage (10h)
5. Complete CV 3-Step (10h)
6. Complete Gap Handler (8h)

---

**Document Version:** 1.0
**Last Updated:** 2026-02-10

---

**END OF MAPPING DOCUMENT**
