# L0.4 — CV Tailoring Quality Scores Results

**Date:** 2026-02-27  
**Branch:** `beta/exec-runbk`  
**Test file:** `tests/unit/test_l0_cv_tailoring_scores.py`  
**Invariants:** I1 (partial), I2 (partial)

## Files Updated

- `src/backend/tests/unit/test_l0_cv_tailoring_scores.py`
- `src/backend/careervp/logic/cv_tailoring.py`

## RED Phase (tests first)

Command:

```bash
cd src/backend && uv run pytest tests/unit/test_l0_cv_tailoring_scores.py -v --tb=short
```

Initial failure state:

- `1 failed, 4 passed`
- Failing assertion: `save_tailored_cv` was never called from legacy tailoring path.

## GREEN Phase (after implementation)

Command:

```bash
cd src/backend && uv run pytest tests/unit/test_l0_cv_tailoring_scores.py -v --tb=short
```

Result:

- `5 passed, 0 failed`

## Before/After ATS (from deterministic weak-draft validation)

- Before: `3.2` (weak draft preliminary ATS)
- After: `8.73` (final ATS after self-correction)
- Iterations: `1` (self-correction triggered)

## Validation Commands

```bash
rg -n "cv_id.*null|cv_id.*None" src/backend/careervp/logic/cv_tailoring.py | wc -l
cd src/backend && uv run pytest tests/unit/test_l0_cv_tailoring_scores.py -v --tb=short
cd src/backend && uv run ruff check careervp/logic/cv_tailoring.py careervp/logic/cv_tailoring_logic.py tests/unit/test_l0_cv_tailoring_scores.py
cd src/backend && uv run mypy careervp/logic/cv_tailoring.py --strict
```

Results:

- grep result: `0`
- pytest: `5 passed`
- ruff: all checks passed
- mypy: success, no issues found

## Implementation Notes

- Replaced L0.4 placeholder assertions with real, behavior-based unit tests.
- Added DAL persistence path in `cv_tailoring.py` to call `save_tailored_cv(...)` when available.
- Added cv_id hardening in `_build_tailored_cv(...)` to ensure non-null artifact identifiers.
- Preserved ATS and anti-AI gates (`ATS >= 8.0`, `anti-AI >= 9.0`) with bounded self-correction (`max 3`).
