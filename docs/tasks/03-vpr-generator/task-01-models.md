# Task: VPR & JobPosting Models Implementation

**Status:** Complete
**Spec Reference:** [[docs/specs/03-vpr-generator.md]]

## Overview

Create Pydantic models for VPR generation: JobPosting input model, VPR output model, and request/response models.

## Todo

### JobPosting Model (`models/job.py`)

- [x] Create `models/job.py` file.
- [x] Add `JobPosting` model with fields:
    - `company_name: str`
    - `role_title: str`
    - `description: str | None`
    - `responsibilities: list[str]`
    - `requirements: list[str]`
    - `nice_to_have: list[str]` (default empty)
    - `language: Literal['en', 'he']`
    - `source_url: HttpUrl | None`
- [x] Add `GapResponse` model (question/answer pair).
- [x] Add `CompanyContext` model (company research data).

### VPR Models (`models/vpr.py`)

- [x] Create `models/vpr.py` file.
- [x] Add `EvidenceItem` model (requirement, evidence, alignment_score, impact_potential).
- [x] Add `GapStrategy` model (gap, mitigation_approach, transferable_skills).
- [x] Add `TokenUsage` model (input_tokens, output_tokens, cost_usd, model).
- [x] Add `VPR` model with fields:
    - `application_id: str`
    - `user_id: str`
    - `executive_summary: str`
    - `evidence_matrix: list[EvidenceItem]`
    - `differentiators: list[str]` (3-5 items)
    - `gap_strategies: list[GapStrategy]`
    - `cultural_fit: str | None`
    - `talking_points: list[str]`
    - `keywords: list[str]`
    - `version: int`
    - `language: Literal['en', 'he']`
    - `created_at: datetime`
    - `word_count: int`
- [x] Add `VPRRequest` model.
- [x] Add `VPRResponse` model.

### Validation

- [x] Run `uv run ruff check src/backend/careervp/models/job.py`.
- [x] Run `uv run ruff check src/backend/careervp/models/vpr.py`.
- [x] Run `uv run mypy src/backend/careervp/models/job.py --strict`.
- [x] Run `uv run mypy src/backend/careervp/models/vpr.py --strict`.
- [x] Added regression test `tests/unit/test_vpr_handler.py::test_vpr_request_accepts_common_job_posting_aliases` to ensure alias fields like `title`/`company` continue to validate.

### Commit

- [ ] Commit with message: `feat(vpr): add JobPosting and VPR Pydantic models`.

---

## Codex Implementation Guide

### File Paths

| File | Purpose |
| ---- | ------- |
| `src/backend/careervp/models/job.py` | JobPosting, GapResponse, CompanyContext |
| `src/backend/careervp/models/vpr.py` | VPR, EvidenceItem, GapStrategy, TokenUsage, VPRRequest, VPRResponse |

### Commit Instructions

```bash
# Stage the model files
cd /Users/yitzchak/Documents/dev/careervp
git add src/backend/careervp/models/job.py
git add src/backend/careervp/models/vpr.py

# Commit with conventional commit message
git commit -m "feat(vpr): add JobPosting and VPR Pydantic models

- Add JobPosting model with company_name, role_title, requirements fields
- Add GapResponse model for gap analysis Q&A pairs
- Add CompanyContext model for company research data
- Add VPR model with executive_summary, evidence_matrix, differentiators
- Add EvidenceItem, GapStrategy, TokenUsage supporting models
- Add VPRRequest and VPRResponse for API contract

Co-Authored-By: Claude <noreply@anthropic.com>"
```

### Verification Commands

```bash
# Verify models pass linting
cd src/backend && uv run ruff format careervp/models/job.py careervp/models/vpr.py
cd src/backend && uv run ruff check careervp/models/job.py careervp/models/vpr.py

# Verify models pass type checking
cd src/backend && uv run mypy careervp/models/job.py --strict
cd src/backend && uv run mypy careervp/models/vpr.py --strict
```

### Zero-Hallucination Checklist

- [x] No FVS-relevant fields in models (models are data structures only).
- [x] `EvidenceItem.evidence` field description references CV facts as source.
- [x] `VPR.created_at` uses `datetime.utcnow` (no fabricated timestamps).

## Acceptance Criteria

- All models pass ruff and mypy --strict checks.
- Models follow existing patterns in `models/cv.py`.
- Type annotations are complete with `Annotated` and `Field` descriptions.
