# Task: VPR & JobPosting Models Implementation

**Status:** In Progress
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

### Commit

- [ ] Commit with message: `feat(vpr): add JobPosting and VPR Pydantic models`.

## Acceptance Criteria

- All models pass ruff and mypy --strict checks.
- Models follow existing patterns in `models/cv.py`.
- Type annotations are complete with `Annotated` and `Field` descriptions.
