# Refactoring Quick Reference

**Master Plan:** [REFACTORING_PLAN.md](./REFACTORING_PLAN.md)

---

## Immediate Next Steps (Week 1)

### Day 1: Security Foundation
| Task | Command | Files | Expected Duration |
|------|---------|-------|-------------------|
| Add API Authorizer | Manual edit | `infra/careervp/api_construct.py` | 4h |
| Fix exception leakage | Manual edit | `cv_tailoring_handler.py` | 2h |

### Day 2-3: Model Unification
| Task | Command | Files | Expected Duration |
|------|---------|-------|-------------------|
| Audit model usages | `grep -r "from.*models" src/` | All .py | 1h |
| Consolidate UserCV | Manual edit | `models/cv.py` | 4h |
| Consolidate FVS models | Manual edit | `models/fvs.py` | 3h |
| Update imports | `sed -i '' 's/cv_models/cv/g' src/` | All .py | 2h |

---

## Key Metrics to Track

| Metric | Current | Post-Phase 1 | Post-All |
|--------|---------|---------------|----------|
| Architecture Score | 2.7/5.0 | 3.2/5.0 | 4.0/5.0 |
| Duplicate Models | 4 | 1 | 0 |
| Handler→Logic→DAL Violations | 2 | 0 | 0 |
| JSA Alignment | 62.5% | 70% | 100% |

---

## Critical Success Factors

1. ✅ Phase 0 (Security) must complete before any user-facing deployment
2. ✅ Phase 1 (Models) must complete before Phase 2
3. ✅ All P0 issues must resolve before Cover Letter implementation
4. ✅ Maintain backward compatibility where possible

---

## Validation Commands

```bash
# Run JSA alignment tests
cd src/backend
PYTHONPATH=$(pwd) uv run pytest ../../tests/jsa_skill_alignment/ -v

# Check code quality
uv run ruff check src/backend/careervp/
uv run ruff format src/backend/careervp/
uv run mypy src/backend/careervp --strict
```

---

## Dependency Graph

```
Phase 0 (Security) ──► Phase 1 (Models) ──► Phase 2 (DAL)
                              │
                              ├──► Phase 3 (VPR 6-Stage)
                              │
                              ├──► Phase 4 (CV 3-Step)
                              │
                              ├──► Phase 5 (Gap)
                              │
                              └──► Phase 6 (Cover Letter)
                                          │
                                          ├──► Phase 7 (Quality)
                                          │
                                          ├──► Phase 8 (Knowledge)
                                          │
                                          └──► Phase 9 (Interview Prep)
```

---

## Quick Links

| Resource | Path |
|----------|------|
| Master Plan | `/docs/refactor/REFACTORING_PLAN.md` |
| JSA Alignment | `/docs/architecture/jsa-skill-alignment/JSA-Skill-Alignment-Plan.md` |
| Architecture Review | `/docs/architecture/architecture-review/DEEP_ANALYSIS_RESULTS.md` |
| Agentic Architecture | `/docs/architecture/prompt-improvement/CareerVP_Agentic_Architecture.md` |
| Test Suite | `/tests/jsa_skill_alignment/` |
