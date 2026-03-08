# CareerVP Documentation Analysis for Beta Launch

Generated: 2026-02-25

## Scope Context

### Beta Scope (from `docs/beta/BETA_PLAN_DESIGN.md`)

**In Scope for Beta:**
- Authentication: register, login, refresh, protected routes
- CV upload/list/select
- Job create/list/get
- Gap questions + responses
- VPR generate + status
- CV tailoring generate + status
- Cover letter generate + status
- Interview prep generate + status
- User profile basics (`/users/me`)
- Trial constraints (14-day, 3 applications)
- Staging subdomain usability

**Out of Scope (Post-Beta):**
- Full Step Functions replatform
- Full admin dashboard
- Advanced collaboration, analytics

---

## Validation Criteria Used

| # | Criterion | Question |
|---|-----------|----------|
| 1 | Scope Alignment | Is this relevant to features in Swagger + Beta Plan? |
| 2 | Guided Walkthrough Support | Is this needed for user onboarding? |
| 3 | Self-Serve Requirement | Do users need this without support? |
| 4 | Operational Blocker | Can you run beta WITHOUT this? |
| 5 | Quick Win | Can this be done in < 1 hour? |
| 6 | Prevents Support Tickets | Will missing this cause user confusion? |

## Decision Matrix

| Category | Criteria | Action |
|----------|----------|--------|
| **Beta (Now)** | Required for beta launch | Include |
| **Post-Beta** | Important but not blocking | Defer |
| **Future** | Nice to have | Archive |

---

## Analysis Results

### 📁 docs/staging/

| File | Category | Rationale |
|------|----------|------------|
| `execution_runbook.md` | **Beta** | Critical for deploying staging environment - needed for beta |
| `stage_migration_plan.md` | **Beta** | Required to set up staging for beta testing |
| `specs/` | **Beta** | API specs needed for testing |
| `payloads/` | **Beta** | Test payloads needed for validation |
| `scripts/` | **Beta** | Deployment scripts needed |
| `tests/` | **Beta** | Staging validation tests |

**Summary:** All `docs/staging/` content is **BETA** - essential for setting up and operating the staging environment for beta.

---

### 📁 docs/features/

| File | Category | Rationale |
|------|----------|------------|
| `CareerVP Features List - Final v2.md` | **Post-Beta** | Comprehensive feature spec - good reference but not needed for beta launch |
| `CareerVP Prompt Library.md` | **Beta** | Contains prompts needed for AI features in beta |
| `VP Report Sections.md` | **Future** | Internal reference |
| `Interview Prep Sections.md` | **Future** | Internal reference |
| `Job Post Examples/` | **Future** | Sample data, not needed |

**Summary:**
- **Beta:** Prompt Library (required for AI features)
- **Post-Beta:** Feature list (reference)
- **Future:** Other feature docs

---

### 📁 docs/architecture/

| File | Category | Rationale |
|------|----------|------------|
| `COVER_LETTER_DESIGN.md` | **Post-Beta** | Detailed design - good reference but implementation already done |
| `CV_TAILORING_DESIGN.md` | **Post-Beta** | Detailed design - reference |
| `GAP_ANALYSIS_DESIGN.md` | **Post-Beta** | Detailed design - reference |
| `VPR_ASYNC_DESIGN.md` | **Post-Beta** | Detailed design - reference |
| `JSA_ALIGNMENT_DESIGN.md` | **Post-Beta** | Design for job skill alignment |
| `async-vpr-design.md` | **Future** | Older design doc |
| `system_design.md` | **Future** | Older system design |
| `api_spec.openapi.yml` | **Beta** | API specification - needed for frontend integration |
| `architecture-review/` | **Future** | Historical review docs |
| `claude_sdk-tracking/` | **Future** | Tracking docs |
| `cloudflare/` | **Future** | Cloudflare integration |
| `jsa-skill-alignment/` | **Post-Beta** | JSA feature work |
| `prompt-improvement/` | **Post-Beta** | Prompt optimization work |

**Summary:**
- **Beta:** API spec (api_spec.openapi.yml)
- **Post-Beta:** Design docs (reference for future work)
- **Future:** Historical/archival

---

### 📁 docs/audit/

| File | Category | Rationale |
|------|----------|------------|
| `SECURITY_ACTION_PLAN.md` | **Beta** | Security requirements must be addressed before beta |
| `security_bug_audit.md` | **Beta** | Known security issues to fix |
| `security_bug_audit_2026-02-20.md` | **Beta** | Recent security audit |
| `security_validation_report_2026-02-20.md` | **Beta** | Validation of security fixes |
| `execution_runbook-prompt_audit.md` | **Post-Beta** | Prompt audit runbook - can defer |

**Summary:** All security audit docs are **BETA** priority - security issues must be resolved before launch.

---

### 📁 docs/refactor/

| File | Category | Rationale |
|------|----------|------------|
| `ARCHITECTURAL_FINDINGS_REMEDIATION.md` | **Post-Beta** | Historical findings - good reference |
| `CIRCUIT_BREAKER_FALLBACK.md` | **Post-Beta** | Resilience pattern - defer |
| `COMPANY_RESEARCH_ARCHITECTURE.md` | **Post-Beta** | Feature design - defer |
| `CRITICAL_CORRECTIONS.md` | **Beta** | Must address before beta |
| `CRITICAL_CORRECTIONS_RESOLUTION_PROMPT.md` | **Beta** | Resolution guidance |
| `DEPLOYMENT_OPERATIONS.md` | **Beta** | Deployment procedures needed |
| `EXECUTION_RUNBOOK.md` | **Beta** | Core runbook |
| `EXECUTION_RUNBOOK.md.backup` | **Future** | Backup - archive |
| `EXECUTION_RESULTS.md` | **Future** | Historical results |
| `REFACTORING_PLAN.md` | **Future** | Historical |
| `REFACTORING_PLAN_UPDATE.md` | **Future** | Historical |
| `PHASE_0_TASKS.md` | **Future** | Historical |
| `PHASE_1_TASKS.md` | **Future** | Historical |
| `TEST_MAPPING.md` | **Post-Beta** | Test strategy - defer |
| `TEST_STRATEGY.md` | **Post-Beta** | Test strategy - defer |
| `VALIDATION_REPORT.md` | **Future** | Historical validation |
| `route_mapping.md` | **Beta** | API route mapping needed |
| `async_cdk_remediation_plan.md` | **Post-Beta** | CDK improvements - defer |
| `execution_runbook_2.md` | **Beta** | Secondary runbook |
| `execution_runbook_2_results.md` | **Future** | Historical |
| `live_tests/` | **Beta** | Test results needed |
| `specs/` | **Beta** | Specs for refactor work |
| `payloads/` | **Future** | Historical payloads |
| `prompts/` | **Post-Beta** | Prompt work |

**Summary:**
- **Beta:** Critical corrections, deployment ops, runbooks, route mapping, live tests
- **Post-Beta:** Test strategies, company research architecture
- **Future:** Historical phases, backups

---

### 📁 docs/refactor2/

| File | Category | Rationale |
|------|----------|------------|
| `execution_runbook.md` | **Beta** | Phase 2 runbook |
| `REFACTOR2_PLAN.md` | **Future** | Historical plan |
| `API_TEST_GENERATION_PROMPT.md` | **Post-Beta** | Test generation |
| `ENDPOINT_2XX_REMEDIATION_PLAN.md` | **Beta** | Endpoint fixes needed |
| `payloads/`, `scripts/`, `tests/` | **Beta** | Supporting artifacts |
| `specs/` | **Beta** | Specifications |

**Summary:** Content overlaps with Phase 2 execution - critical for completing beta features.

---

### 📁 docs/refactor3/

| File | Category | Rationale |
|------|----------|------------|
| `execution_runbook3.md` | **Beta** | Phase 3 runbook |
| `RUNBOOK3_GENERATION_PROMPT.md` | **Future** | Historical prompt |
| `payloads/`, `scripts/`, `tests/` | **Beta** | Supporting artifacts |
| `validations/` | **Beta** | Validation results |

**Summary:** Phase 3 execution - needed for completing beta.

---

## Consolidated Summary

### ✅ BETA (Include - Next 2 Weeks)

| Source | Files | Purpose |
|--------|-------|---------|
| `docs/staging/` | All | Environment setup & deployment |
| `docs/features/` | Prompt Library | AI feature prompts |
| `docs/architecture/` | api_spec.openapi.yml | API contract |
| `docs/audit/` | All security docs | Must fix before launch |
| `docs/refactor/` | Critical corrections, runbooks, route_mapping | Operational |
| `docs/refactor2/` | execution_runbook, remediation plans | Feature completion |
| `docs/refactor3/` | execution_runbook3 | Feature completion |

### 📋 POST-BETA (After Launch)

| Source | Files | Purpose |
|--------|-------|---------|
| `docs/features/` | Features List v2 | Feature reference |
| `docs/architecture/` | Design docs | Future implementation |
| `docs/refactor/` | Test strategies, circuit breaker | Quality improvements |

### 📦 FUTURE (Archive/Deprecate)

| Source | Files | Purpose |
|--------|-------|---------|
| `docs/features/` | Sample job posts, sections | Sample data |
| `docs/architecture/` | Older designs, cloudflare | Historical |
| `docs/refactor/` | Phase 0/1 tasks, backups | Historical |

---

## Critical Path for Beta

### Must Complete Before Beta Launch

---

### 1. Security Fixes (from `docs/audit/`)

**Why critical:** Beta users will have real credentials. Security vulnerabilities could expose user data.

**Specific items:**
| Issue | Source Doc | Action |
|-------|------------|--------|
| Auth bypass in `gap_handler.py` | `security_bug_audit.md` | Fix user_id extraction from payload |
| Auth bypass in `cv_upload_handler.py` | `security_bug_audit.md` | Fix user_id extraction from payload |
| Auth bypass in `knowledge_base_handler.py` | `security_bug_audit.md` | Fix user_id extraction from payload |
| Missing idempotency (7 handlers) | `spec_compliance_analysis.md` | Add idempotency keys |
| No auth middleware on some routes | `SECURITY_ACTION_PLAN.md` | Ensure consistent `@require_auth` |

**Estimated effort:** 2-3 days

---

### 2. Staging Environment (from `docs/staging/`)

**Why critical:** You need a production-like environment to test beta features before launch.

**Specific items:**
| Item | Source Doc | Action |
|------|------------|--------|
| Deploy staging stack | `execution_runbook.md` | Run CDK deploy to staging |
| Set up SSM parameters | `stage_migration_plan.md` | Create `/careervp/staging/*` secrets |
| Validate API endpoints | `execution_runbook.md` | Test all Swagger endpoints |
| Configure custom domain | `BETA_PLAN_DESIGN.md` | Map `stage.careervp.com` |
| CI/CD for staging | `execution_runbook.md` | Auto-deploy on develop branch |

**Estimated effort:** 2-3 days

---

### 3. Feature Completion (from `docs/refactor*/`)

**Why critical:** Beta users need working features - incomplete features = bad UX.

**Features to validate:**
| Feature | Source Doc | Status |
|---------|------------|--------|
| VPR generation | `execution_runbook_2_results.md` | Needs validation |
| CV Tailoring | `execution_runbook_2_results.md` | Needs validation |
| Cover Letter | `execution_runbook_2_results.md` | Needs validation |
| Interview Prep | `execution_runbook_2_results.md` | Needs validation |
| Gap Analysis | `execution_runbook_3.md` | Needs validation |
| Company Research | `execution_runbook_3.md` | Needs validation |

**Specific issues to fix (from `spec_compliance_analysis.md`):**
- 11 handlers missing Powertools decorators
- 4 handlers missing @metrics.log_metrics
- 4 handlers missing capture_cold_start_metric
- Query vs Scan violations in jobs_repository.py

**Estimated effort:** 4-5 days

---

### 4. Operational Docs (from `docs/refactor/`)

**Why critical:** You need to run the system during beta without guessing.

**Specific items:**
| Doc | Purpose | Action Needed |
|-----|---------|---------------|
| `DEPLOYMENT_OPERATIONS.md` | How to deploy | Verify current |
| `route_mapping.md` | API routes | Verify accuracy |
| `CRITICAL_CORRECTIONS.md` | Known issues | Review for beta |

**Estimated effort:** 1 day

---

### Timeline Summary

| Week | Focus | Deliverable |
|------|-------|-------------|
| Week 1 | Security + Staging | Deployable staging env |
| Week 2 | Feature completion + Testing | Working beta |

---

## Recommendations

### Immediate Actions (Do Now)

#### 1. Consolidate Beta Docs
Create `docs/beta/README.md` that links to:

```
docs/beta/
├── README.md                    # This file
├── BETA_PLAN_DESIGN.md         # Beta goals
├── useful_features_analysis.md  # This analysis
├── docs_gaps/
│   ├── user_guide.md           # User-facing (created)
│   ├── api_error_codes.md      # User-facing (created)
│   └── trial_usage_enforcement.md  # Internal (created)
└── [other beta-critical docs]
```

#### 2. Archive Historical
Move to `docs/archive/`:
- `docs/refactor/PHASE_0_TASKS.md`
- `docs/refactor/PHASE_1_TASKS.md`
- `docs/refactor/EXECUTION_RUNBOOK.md.backup`
- `docs/refactor2/REFACTOR2_PLAN.md`
- `docs/refactor3/RUNBOOK3_GENERATION_PROMPT.md`

#### 3. Update Runbooks
Verify these are executable:
- `docs/staging/execution_runbook.md`
- `docs/refactor/execution_runbook_2.md`
- `docs/refactor3/execution_runbook3.md`

---

### Documentation Gaps (Create)

| Gap | Priority | Contents | Status |
|-----|----------|----------|--------|
| **User Guide** | HIGH | Step-by-step walkthrough | ✅ Created (docs_gaps/) |
| **Trial Enforcement** | HIGH | 14-day, 3-app logic | ✅ Created (docs_gaps/) |
| **API Errors** | MEDIUM | Error codes & resolutions | ✅ Created (docs_gaps/) |
| **Admin Runbook** | MEDIUM | How to manage beta | ❌ Not created |
| **On-Call Guide** | LOW | What to do when things break | ❌ Not created |

---

### Recommended Additional Docs

#### Admin Runbook (Medium Priority)
**For:** You during beta operations
- How to check system health
- How to view logs
- How to restart a Lambda
- How to check CloudWatch metrics
- How to rollback a deployment
- Emergency contacts

#### On-Call Guide (Low Priority)
**For:** You during off-hours
- Alert definitions
- Severity levels
- Escalation procedure
- Common issues & resolutions
- Runbooks for specific failures

---

## Appendix: Best Practices Specs

The following specs were created in `docs/best_practices/yaml/` and should be used to validate any new code:

| Spec | Purpose |
|------|---------|
| `lambda_handler_spec.yaml` | Lambda function standards |
| `dynamodb_modeling_spec.yaml` | DynamoDB data modeling |
| `testing_spec.yaml` | Testing patterns |
| `frontend_spec.yaml` | Frontend standards |
| `cicd_spec.yaml` | CI/CD pipeline standards |

See `docs/best_practices/README.md` for overview.
