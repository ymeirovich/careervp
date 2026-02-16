# CareerVP Execution Runbook 2.0 - Remaining Tasks (Corrected Order)

**Document Version:** 1.1
**Date:** 2026-02-16
**Purpose:** Detailed step-by-step instructions to complete all remaining tasks and achieve 100% implementation

---

## Implementation Order

The correct order of implementation is:

1. **Quality Gaps FIRST** (Phases 2-7) - These affect the core logic
2. **API Contract Gaps SECOND** (Phase 10) - These wrap the logic in HTTP endpoints

This order ensures:
- Core business logic is working before wrapping it in APIs
- API endpoints have complete functionality to expose
- Tests can validate the full stack correctly

---

## Current Status (Before This Runbook)

| Phase | Status | Gap |
|-------|--------|-----|
| Phase 0 | ✅ COMPLETE | 59 unit tests |
| Phase 1 | ✅ COMPLETE | Model consolidation |
| Phase 2 | ⚠️ PARTIAL (60%) | CV Summarizer, LLM Cache missing |
| Phase 3 | ⚠️ PARTIAL (65%) | 6-stage pipeline, anti-AI unwired |
| Phase 4 | ⚠️ PARTIAL (70%) | 3-step process missing |
| Phase 5 | ⚠️ PARTIAL (45%) | Question limit 5, tagging |
| Phase 6 | ✅ IMPLEMENTED | Cover Letter |
| Phase 7 | ⚠️ PARTIAL (25%) | FVS scoring missing |
| Phase 8 | ✅ IMPLEMENTED | Knowledge Base |
| Phase 9 | ✅ IMPLEMENTED | Interview Prep |
| Phase 10 | ⚠️ ASSESSED (56%) | 12/27 endpoints |

---

# PART 1: QUALITY GAPS (Implement First)

These tasks improve the core business logic before wrapping in APIs.

## Task 2.1: Implement CV Summarizer (Phase 2)

**Goal:** Reduce token costs by summarizing CV before LLM calls

### Step 2.1.1: Create CV Summarizer Logic
```bash
# File: src/backend/careervp/logic/cv_summarizer.py
cat > src/backend/careervp/logic/cv_summarizer.py << 'EOF'
"""CV Summarizer - Extracts key sections to reduce token costs."""
from typing import Optional

from careervp.models.cv import UserCV


class CVSummarizer:
    """Summarizes CV to reduce token usage in LLM calls."""

    KEY_SECTIONS = [
        'summary', 'experience', 'employment', 'work_history',
        'education', 'skills', 'certifications', 'projects'
    ]

    MAX_SECTION_LENGTH = 500

    def summarize(self, cv: UserCV) -> dict:
        """Create a summarized version of the CV."""
        result = {}

        if cv.summary:
            result['summary'] = self._truncate(cv.summary, 200)

        if cv.work_experience:
            result['experience'] = [
                self._summarize_job(job) for job in cv.work_experience[:3]
            ]

        if cv.skills:
            result['skills'] = cv.skills[:15] if isinstance(cv.skills, list) else cv.skills.split(',')[:15]

        if cv.education:
            result['education'] = [edu.model_dump() for edu in cv.education[:2]]

        return result

    def _summarize_job(self, job) -> dict:
        """Summarize a single job entry."""
        summary = {
            'title': job.title,
            'company': job.company,
        }
        if job.description:
            summary['highlights'] = self._truncate(job.description, 300)
        return summary

    def _truncate(self, text: str, max_length: int) -> str:
        """Truncate text to max length."""
        if len(text) <= max_length:
            return text
        return text[:max_length].rsplit(' ', 1)[0] + '...'

    def get_summary_prompt(self, cv: UserCV) -> str:
        """Generate a summary-focused prompt for LLM calls."""
        summary = self.summarize(cv)
        prompt_parts = []

        if 'summary' in summary:
            prompt_parts.append(f"Summary: {summary['summary']}")

        if 'experience' in summary:
            prompt_parts.append("\nRecent Experience:")
            for job in summary['experience']:
                prompt_parts.append(f"- {job['title']} at {job['company']}")

        if 'skills' in summary:
            prompt_parts.append(f"\nKey Skills: {', '.join(summary['skills'])}")

        return '\n'.join(prompt_parts)
EOF
```

### Step 2.1.2: Integrate with LLM Client
```python
# File: src/backend/careervp/logic/llm_client.py
from careervp.logic.cv_summarizer import CVSummarizer


class LLMClient:
    """LLM client with cost optimization."""

    def __init__(self):
        self.summarizer = CVSummarizer()
        self.cache = {}

    def generate(self, prompt: str, use_summary: bool = False, cv: UserCV = None) -> str:
        """Generate with optional CV summarization."""
        cache_key = hash(prompt)
        if cache_key in self.cache:
            return self.cache[cache_key]

        if use_summary and cv:
            prompt = self.summarizer.get_summary_prompt(cv) + "\n\n" + prompt

        response = self._call_bedrock(prompt)
        self.cache[cache_key] = response
        return response
```

---

## Task 2.2: Wire Circuit Breaker (Phase 2)

### Step 2.2.1: Update LLM Client
```python
# File: src/backend/careervp/logic/llm_client.py
from careervp.logic.circuit_breaker import CircuitBreaker


class LLMClient:
    """LLM client with circuit breaker protection."""

    def __init__(self):
        self.circuit_breaker = CircuitBreaker(
            name='bedrock-llm',
            failure_threshold=5,
            recovery_timeout_seconds=60.0
        )
        self.cache = {}

    def generate(self, prompt: str, **kwargs) -> str:
        """Generate with circuit breaker protection."""
        if not self.circuit_breaker.can_proceed():
            raise Exception("Circuit breaker OPEN - LLM temporarily unavailable")

        try:
            response = self._call_bedrock(prompt, **kwargs)
            self.circuit_breaker.record_success()
            return response
        except Exception as e:
            self.circuit_breaker.record_failure()
            raise
```

---

## Task 3.1: VPR 6-Stage Pipeline (Phase 3)

### Step 3.1.1: Refactor VPR Generator
```python
# File: src/backend/careervp/logic/vpr_generator.py
class VPRGenerator:
    """6-stage VPR generation pipeline."""

    STAGES = [
        'stage_1_research',    # Company & Role Research
        'stage_2_analyze',     # Candidate Analysis
        'stage_3_map',         # Alignment Mapping
        'stage_4_correct',    # Self-Correction
        'stage_5_generate',    # Generate Report
        'stage_6_evaluate'     # Final Meta Evaluation
    ]

    async def generate(self, cv: UserCV, job: dict, context: dict) -> VPR:
        """Run 6-stage pipeline."""
        research = await self.stage_1_research(job)
        analysis = await self.stage_2_analyze(cv, research)
        alignment = await self.stage_3_map(analysis, job)
        corrected = await self.stage_4_correct(alignment)
        vpr = await self.stage_5_generate(corrected)
        vpr = await self.stage_6_evaluate(vpr)

        # Wire anti-AI detection
        from careervp.logic.fvs_validator import check_anti_ai_patterns
        if not check_anti_ai_patterns(vpr.executive_summary):
            vpr = await self.stage_6_evaluate(vpr, force_regenerate=True)

        return vpr

    async def stage_6_evaluate(self, vpr: VPR, force_regenerate: bool = False) -> VPR:
        """Final meta evaluation - make 20% more persuasive."""
        return vpr
```

---

## Task 4.1: CV Tailoring 3-Step (Phase 4)

### Step 4.1.1: Implement 3-Step Process
```python
# File: src/backend/careervp/logic/cv_tailoring.py
class CVTailoringEngine:
    """3-step CV tailoring process."""

    async def tailor(self, cv: UserCV, job: dict) -> TailoredCV:
        """Run 3-step tailoring process."""

        # STEP 1: Analysis & Keyword Mapping (12-18 keywords)
        keywords = await self.step_1_analyze(cv, job)

        # STEP 2: Self-Correction (ATS score validation)
        tailored = await self.step_2_tailor(cv, keywords)
        ats_score = self._calculate_ats_score(tailed)

        # Self-correction loop: regenerate if ATS < 8.0
        max_iterations = 3
        iteration = 0
        while ats_score < 8.0 and iteration < max_iterations:
            tailored = await self.step_2_tailor(cv, keywords, feedback=f"ATS score too low: {ats_score}")
            ats_score = self._calculate_ats_score(tailored)
            iteration += 1

        # STEP 3: Finalize (ATS >= 8.0)
        final = await self.step_3_finalize(tailored, ats_score)

        return final

    def _calculate_ats_score(self, cv_text: str) -> float:
        """Calculate ATS compatibility score (1-10)."""
        return 7.0  # Implement ATS scoring logic
```

---

## Task 5.1: Gap Analysis Fixes (Phase 5)

### Step 5.1.1: Fix Question Limit
```python
# File: src/backend/careervp/logic/gap_analysis.py
# Change: questions[:5] -> questions[:10]
```

### Step 5.1.2: Add Question Tagging
```python
# Add to GapQuestion model:
class GapQuestion(BaseModel):
    question: str
    category: str  # technical, behavioral, situational
    priority: str  # CRITICAL, IMPORTANT, OPTIONAL
    tag: str      # [CV IMPACT], [INTERVIEW/MVP ONLY]
```

---

## Task 7.1: FVS Scoring (Phase 7)

### Step 7.1.1: Implement Full Validation
```python
# File: src/backend/careervp/logic/fvs_validator.py
class FVSValidator:
    """Full validation with all scoring dimensions."""

    async def validate(self, document: str, cv_data: dict = None) -> QualityScore:
        """Run full validation pipeline."""

        fact_score = await self._verify_facts(document, cv_data)
        ats_score = self._check_ats_compatibility(document)
        anti_ai_score = self._check_anti_ai(document)
        consistency_score = self._check_consistency(document, cv_data)
        completeness_score = self._check_completeness(document)
        language_score = self._check_language_quality(document)

        return QualityScore(
            fact_verification=fact_score,
            ats_score=ats_score,
            anti_ai_score=anti_ai_score,
            consistency_score=consistency_score,
            completeness_score=completeness_score,
            grammar_score=language_score.grammar,
            tone_score=language_score.tone,
            formatting_score=language_score.formatting
        )
```

---

# PART 2: API CONTRACT GAPS (Implement Second)

These tasks wrap the core logic in HTTP endpoints.

## Task 10.1: User Handler

### Files to Create:
- `models/user.py`
- `dal/user_repository.py`
- `handlers/user_handler.py`

### Endpoints:
- `GET /users/me`
- `PUT /users/me`
- `GET /users/me/cvs`

---

## Task 10.2: Job Handler

### Files to Create:
- `models/job.py`
- `dal/job_repository.py`
- `handlers/job_handler.py`

### Endpoints:
- `POST /jobs`
- `GET /jobs`
- `GET /jobs/{jobId}`

---

## Task 10.3: Status Endpoints

### Extend Existing Handlers:
- `cv_tailoring_handler.py` - Add `GET /cv-tailoring/{id}`, `GET /users/me/tailored-cvs`
- `cover_letter_handler.py` - Add `GET /cover-letter/{id}`, `GET /users/me/cover-letters`
- `interview_prep_handler.py` - Add `GET /interview-prep/{id}`

### New Handler:
- `handlers/health_handler.py` - `GET /health`

---

# PART 3: TEST CREATION (Missing Tests)

These tests are referenced in workflows but are NOT yet created.

## Task T1: VPR Async E2E Test

### File to Create:
- `src/backend/tests/e2e/test_vpr_async_polling.py`

### Test Coverage:
- Submit VPR job (POST /vpr/generate) → returns 202 with request_id
- Poll status (GET /vpr/status/{job_id}) → pending → processing → completed
- Error handling for invalid job_id
- Timeout handling

### Code:
```python
"""VPR Async Polling E2E Tests."""
import pytest
import requests
import time

API_BASE_URL = os.environ.get("API_BASE_URL", "https://api.careervp.com")

class TestVPRAsyncPolling:
    """Test VPR async job submission and status polling."""

    def test_submit_and_poll_success(self, auth_token):
        """Test complete VPR job lifecycle: submit → poll → completed."""
        # Submit VPR job
        response = requests.post(
            f"{API_BASE_URL}/v1/vpr/generate",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={"cv_id": "test-cv-123", "job_id": "test-job-456"}
        )
        assert response.status_code == 202
        data = response.json()
        assert "request_id" in data
        request_id = data["request_id"]

        # Poll for completion (max 60 seconds)
        for _ in range(60):
            status_response = requests.get(
                f"{API_BASE_URL}/v1/vpr/status/{request_id}",
                headers={"Authorization": f"Bearer {auth_token}"}
            )
            status_data = status_response.json()
            if status_data["status"] == "completed":
                break
            elif status_data["status"] == "failed":
                pytest.fail("VPR job failed")
            time.sleep(1)

        # Verify final status
        assert status_data["status"] == "completed"
        assert "result" in status_data
```

---

## Task T2: Cover Letter Tests

### Files to Create:

#### Unit Tests: `src/backend/tests/cover-letter/unit/`
- `test_cover_letter_logic.py` - Test cover_letter.py logic
- `test_cover_letter_prompt.py` - Test prompt building

#### Integration Tests: `src/backend/tests/cover-letter/integration/`
- `test_cover_letter_handler.py` - Test handler HTTP responses

#### E2E Tests: `src/backend/tests/cover-letter/e2e/`
- `test_cover_letter_flow.py` - Full cover letter generation flow

### Code (Unit):
```python
"""Cover Letter Unit Tests."""
import pytest
from careervp.logic.cover_letter import generate_cover_letter

class TestCoverLetterLogic:
    """Test cover letter generation logic."""

    @pytest.mark.asyncio
    async def test_generate_professional_tone(self):
        """Test professional tone cover letter generation."""
        # Test implementation
        pass

    @pytest.mark.asyncio
    async def test_word_count_limits(self):
        """Test word count stays within limits."""
        # short: 250, standard: 350, long: 400
        pass
```

---

# PART 4: VERIFICATION COMMANDS

```bash
# Run all tests
cd src/backend && uv run pytest tests/unit/ -v --tb=short

# Run lint
cd src/backend && uv run ruff check careervp/

# Run type check
cd src/backend && uv run mypy careervp --strict

# CDK synth
cd infra && npx cdk synth
```

---

# COMPLETION CHECKLIST

- [ ] Phase 2: CV Summarizer implemented
- [ ] Phase 2: LLM Cache implemented
- [ ] Phase 2: Circuit breaker wired
- [ ] Phase 3: 6-stage VPR pipeline
- [ ] Phase 3: Anti-AI wired
- [ ] Phase 4: 3-step CV tailoring
- [ ] Phase 4: Self-correction loop (ATS >= 8.0)
- [ ] Phase 5: 10 question limit
- [ ] Phase 5: Question tagging
- [ ] Phase 6: Cover Letter unit tests (tests/cover-letter/unit/)
- [ ] Phase 6: Cover Letter integration tests (tests/cover-letter/integration/)
- [ ] Phase 6: Cover Letter E2E tests (tests/cover-letter/e2e/)
- [ ] Phase 7: ATS scoring
- [ ] Phase 7: Anti-AI scoring
- [ ] Phase 7: Cross-doc consistency
- [ ] Phase 10: User handler (3 endpoints)
- [ ] Phase 10: Job handler (3 endpoints)
- [ ] Phase 10: Status endpoints (6 endpoints)
- [ ] Phase 10: Health endpoint
- [ ] VPR Async: E2E test (tests/e2e/test_vpr_async_polling.py)
- [ ] All tests passing
- [ ] Lint clean
- [ ] Type check clean
- [ ] CDK synth succeeds
