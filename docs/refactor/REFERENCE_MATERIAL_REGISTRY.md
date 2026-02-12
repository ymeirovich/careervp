# CareerVP Refactoring - Reference Material Registry

**Document Version:** 1.0
**Date:** 2026-02-12
**Purpose:** Map all reference materials to phases for architectural consistency

---

## Part 1: Reference Material Catalog

### 1.1 Core Planning Documents (Required for All Phases)

| File | Purpose | Phases |
|------|---------|--------|
| `REFACTORING_PLAN.md` | Master implementation plan with 10 phases | ALL |
| `REFACTORING_ROADMAP.md` | High-level timeline and dependencies | ALL |
| `JSA_FEATURE_MAPPING.md` | Feature-to-phase mapping (100KB canonical) | ALL |
| `QUICK_REFERENCE.md` | Architectural decisions quick lookup | ALL |

### 1.2 Phase-Specific Documents

| File | Purpose | Phase |
|------|---------|-------|
| `PHASE_0_TASKS.md` | Security foundation tasks | Phase 0 |
| `PHASE_1_TASKS.md` | Model unification tasks | Phase 1 |

### 1.3 Architecture & Quality Documents

| File | Purpose | Relevant Phases |
|------|---------|-----------------|
| `ARCHITECTURAL_FINDINGS_REMEDIATION.md` | Layer violations and fixes | 0, 1, 2 |
| `CRITICAL_CORRECTIONS.md` | Error corrections and clarifications | ALL |
| `VPC_ARCHITECTURE_DECISION.md` | VPC and network architecture | 0 ( Infra) |

### 1.4 Cost & Optimization Documents

| File | Purpose | Relevant Phases |
|------|---------|-----------------|
| `COST_OPTIMIZATION_VALIDATION.md` | 4 cost strategies validation | 2, 3, 4, 5, 6 |
| `COST_CORRECTION.md` | Cost projection corrections | 2 |

### 1.5 Operations Documents

| File | Purpose | Relevant Phases |
|------|---------|-----------------|
| `DEPLOYMENT_OPERATIONS.md` | Lambda, DynamoDB, S3 deployment | 0, 8 |
| `CIRCUIT_BREAKER_FALLBACK.md` | Circuit breaker patterns | 2 |

### 1.6 Testing & Risk Documents

| File | Purpose | Relevant Phases |
|------|---------|-----------------|
| `TEST_STRATEGY.md` | TDD and testing patterns | ALL |
| `RISK_ANALYSIS.md` | Risk mitigation strategies | ALL |

---

## Part 2: Phase-to-Reference Mapping

### PHASE 0: Security Foundation (8 hours)

| Required Document | Source File | Sections |
|-------------------|-------------|----------|
| Security requirements | `REFACTORING_PLAN.md` | Section 3 |
| API Authorizer spec | `ARCHITECTURAL_FINDINGS_REMEDIATION.md` | Section 2.1 |
| VPC architecture | `VPC_ARCHITECTURE_DECISION.md` | ALL |
| Circuit breaker patterns | `CIRCUIT_BREAKER_FALLBACK.md` | Section 1 |
| Lambda deployment | `DEPLOYMENT_OPERATIONS.md` | Section 1 |
| Test strategy | `TEST_STRATEGY.md` | Section 2 |

**Canonical Source:** `docs/refactor/PHASE_0_TASKS.md`

---

### PHASE 1: Model Unification (22 hours)

| Required Document | Source File | Sections |
|-------------------|-------------|----------|
| CV models spec | `REFACTORING_PLAN.md` | Section 2 |
| VPR models spec | `REFACTORING_PLAN_UPDATE.md` | Section 4 |
| FVS models spec | `REFACTORING_PLAN.md` | Section 2.3 |
| Architectural findings | `ARCHITECTURAL_FINDINGS_REMEDIATION.md` | Section 3 |
| Critical corrections | `CRITICAL_CORRECTIONS.md` | Section 5 |

**Canonical Source:** `docs/refactor/PHASE_1_TASKS.md`

---

### PHASE 2: DAL Consolidation + Cost Optimization (20 hours)

| Required Document | Source File | Sections |
|-------------------|-------------|----------|
| CV Summarizer spec | `COST_OPTIMIZATION_VALIDATION.md` | Strategy 1 |
| LLM Content Cache spec | `COST_OPTIMIZATION_VALIDATION.md` | Strategy 2 |
| Circuit breaker | `CIRCUIT_BREAKER_FALLBACK.md` | ALL |
| DAL patterns | `ARCHITECTURAL_FINDINGS_REMEDIATION.md` | Section 4 |
| Cost corrections | `COST_CORRECTION.md` | ALL |
| DynamoDB patterns | `DEPLOYMENT_OPERATIONS.md` | Section 2 |

**Canonical Sources:**
- `docs/refactor/specs/cv_summarizer_spec.yaml`
- `docs/refactor/specs/llm_content_cache_spec.yaml`

---

### PHASE 3: VPR 6-Stage Generator (10 hours)

| Required Document | Source File | Sections |
|-------------------|-------------|----------|
| VPR 6-stage spec | `REFACTORING_PLAN.md` | Section 2.1 |
| VPR prompts | `JSA_FEATURE_MAPPING.md` | Section 5 |
| CV models | `REFACTORING_PLAN.md` | Section 2 |
| Cost optimization | `COST_OPTIMIZATION_VALIDATION.md` | Strategy 4 |
| Anti-AI patterns | `CRITICAL_CORRECTIONS.md` | Section 8 |

**Canonical Source:** `docs/refactor/specs/vpr_6stage_spec.yaml`

---

### PHASE 4: CV Tailoring 3-Step (11 hours)

| Required Document | Source File | Sections |
|-------------------|-------------|----------|
| CV tailoring spec | `JSA_FEATURE_MAPPING.md` | Section 7 |
| 10 gate tests | `TEST_STRATEGY.md` | Section 4 |
| CV models | `REFACTORING_PLAN.md` | Section 2 |
| DAL patterns | `ARCHITECTURAL_FINDINGS_REMEDIATION.md` | Section 4 |
| Cost targets | `COST_OPTIMIZATION_VALIDATION.md` | Strategy 4 |

**Canonical Source:** `docs/refactor/specs/cv_tailoring_spec.yaml`

---

### PHASE 5: Gap Analysis (13 hours)

| Required Document | Source File | Sections |
|-------------------|-------------|----------|
| Gap analysis spec | `JSA_FEATURE_MAPPING.md` | Section 8 |
| Gap questions spec | `JSA_FEATURE_MAPPING.md` | Section 8.1 |
| Gap responses spec | `JSA_FEATURE_MAPPING.md` | Section 8.2 |
| Cost targets | `COST_OPTIMIZATION_VALIDATION.md` | Strategy 3 |
| Integration patterns | `TEST_STRATEGY.md` | Section 3 |

**Canonical Source:** `docs/refactor/specs/gap_analysis_spec.yaml`

---

### PHASE 6: Cover Letter (13 hours)

| Required Document | Source File | Sections |
|-------------------|-------------|----------|
| Cover letter spec | `JSA_FEATURE_MAPPING.md` | Section 9 |
| Anti-AI patterns | `CRITICAL_CORRECTIONS.md` | Section 8 |
| Quality patterns | `TEST_STRATEGY.md` | Section 5 |
| CV models | `REFACTORING_PLAN.md` | Section 2 |
| Cost targets | `COST_OPTIMIZATION_VALIDATION.md` | Strategy 4 |

**Canonical Source:** `docs/refactor/specs/cover_letter_spec.yaml`

---

### PHASE 7: Quality Validator (FVS) (12 hours)

| Required Document | Source File | Sections |
|-------------------|-------------|----------|
| FVS spec | `REFACTORING_PLAN.md` | Section 4 |
| Quality patterns | `TEST_STRATEGY.md` | Section 5 |
| Anti-AI detection | `CRITICAL_CORRECTIONS.md` | Section 8 |
| Integration patterns | `ARCHITECTURAL_FINDINGS_REMEDIATION.md` | Section 5 |

**Canonical Source:** `docs/refactor/specs/fvs_spec.yaml`

---

### PHASE 8: Knowledge Base (12 hours)

| Required Document | Source File | Sections |
|-------------------|-------------|----------|
| Knowledge base spec | `JSA_FEATURE_MAPPING.md` | Section 10 |
| DAL patterns | `ARCHITECTURAL_FINDINGS_REMEDIATION.md` | Section 4 |
| DynamoDB patterns | `DEPLOYMENT_OPERATIONS.md` | Section 2 |
| S3 patterns | `DEPLOYMENT_OPERATIONS.md` | Section 3 |

**Canonical Source:** `docs/refactor/specs/knowledge_base_spec.yaml`

---

### PHASE 9: Interview Prep (16 hours)

| Required Document | Source File | Sections |
|-------------------|-------------|----------|
| Interview prep spec | `JSA_FEATURE_MAPPING.md` | Section 11 |
| Gap analysis integration | `JSA_FEATURE_MAPPING.md` | Section 8 |
| CV integration | `REFACTORING_PLAN.md` | Section 2 |
| Test strategy | `TEST_STRATEGY.md` | Section 6 |

**Canonical Source:** `docs/refactor/specs/interview_prep_spec.yaml`

---

## Part 3: Architectural Drift Prevention

### 3.1 Decision Audit Trail

For any architectural decision, record:

```yaml
decision_id: DEC-001
phase: 2
date: 2026-02-10
document: COST_OPTIMIZATION_VALIDATION.md
section: "Strategy 2: Caching"
decision: "Use LLMContentCache with TTL: CV(24h), Job(1h), Company(30d)"
rationale: "Optimize token costs for repeated CV/job lookups"
validated_by: COST_OPTIMIZATION_VALIDATION.md
```

### 3.2 Phase Validation Checklist

Before completing each phase, verify:

```yaml
phase: 2
validations:
  - reference: REFACTORING_PLAN.md
    check: "CV Summarizer matches Section 2.4 spec"
  - reference: COST_OPTIMIZATION_VALIDATION.md
    check: "Caching strategy matches Strategy 2"
  - reference: ARCHITECTURAL_FINDINGS_REMEDIATION.md
    check: "DAL patterns followed"
  - reference: CRITICAL_CORRECTIONS.md
    check: "No corrections violated"
```

### 3.3 Cross-Phase Dependencies

| Phase | Depends On | Provides To | Dependency Type |
|-------|------------|-------------|-----------------|
| 0 | - | 1, 2, 3 | Security foundation |
| 1 | 0 | 2, 3, 4 | Models |
| 2 | 1 | 3, 4, 5, 6 | Cost optimization |
| 3 | 1, 2 | 4, 5, 6 | VPR output |
| 4 | 1, 2, 3 | 6, 9 | Tailored CV |
| 5 | 3, 4 | 6, 9 | Gap analysis |
| 6 | 3, 4, 5 | 7, 9 | Cover letter |
| 7 | 6 | - | FVS validation |
| 8 | 4, 5 | - | Knowledge base |
| 9 | 4, 5, 6 | - | Interview prep |

---

## Part 4: Reference File Index

### Quick Lookup by Phase

| Phase | Primary Source | Secondary Sources |
|-------|----------------|-------------------|
| 0 | PHASE_0_TASKS.md | VPC_ARCHITECTURE_DECISION.md, CIRCUIT_BREAKER_FALLBACK.md |
| 1 | PHASE_1_TASKS.md | ARCHITECTURAL_FINDINGS_REMEDIATION.md, CRITICAL_CORRECTIONS.md |
| 2 | COST_OPTIMIZATION_VALIDATION.md | CIRCUIT_BREAKER_FALLBACK.md, DEPLOYMENT_OPERATIONS.md |
| 3 | JSA_FEATURE_MAPPING.md (Section 5) | REFACTORING_PLAN.md (Section 2.1) |
| 4 | JSA_FEATURE_MAPPING.md (Section 7) | TEST_STRATEGY.md (Section 4) |
| 5 | JSA_FEATURE_MAPPING.md (Section 8) | COST_OPTIMIZATION_VALIDATION.md |
| 6 | JSA_FEATURE_MAPPING.md (Section 9) | CRITICAL_CORRECTIONS.md (Section 8) |
| 7 | REFACTORING_PLAN.md (Section 4) | TEST_STRATEGY.md (Section 5) |
| 8 | JSA_FEATURE_MAPPING.md (Section 10) | DEPLOYMENT_OPERATIONS.md |
| 9 | JSA_FEATURE_MAPPING.md (Section 11) | TEST_STRATEGY.md (Section 6) |

### Mandatory Reads Before Each Phase

| Phase | Must Read Files |
|-------|-----------------|
| ALL | QUICK_REFERENCE.md (before starting) |
| 0 | REFACTORING_ROADMAP.md, VPC_ARCHITECTURE_DECISION.md |
| 1 | ARCHITECTURAL_FINDINGS_REMEDIATION.md, CRITICAL_CORRECTIONS.md |
| 2 | COST_CORRECTION.md, COST_OPTIMIZATION_VALIDATION.md |
| 3 | REFACTORING_PLAN.md Section 2.1, JSA_FEATURE_MAPPING.md Section 5 |
| 4 | JSA_FEATURE_MAPPING.md Section 7, TEST_STRATEGY.md Section 4 |
| 5 | JSA_FEATURE_MAPPING.md Section 8, RISK_ANALYSIS.md |
| 6 | JSA_FEATURE_MAPPING.md Section 9, CRITICAL_CORRECTIONS.md Section 8 |
| 7 | REFACTORING_PLAN.md Section 4, TEST_STRATEGY.md Section 5 |
| 8 | JSA_FEATURE_MAPPING.md Section 10, DEPLOYMENT_OPERATIONS.md |
| 9 | JSA_FEATURE_MAPPING.md Section 11, TEST_STRATEGY.md Section 6 |

---

**Document Version:** 1.0
**Created:** 2026-02-12
