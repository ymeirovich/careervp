# Prompt: Generate Beta Execution Runbook with Executable Prompts

**READ FIRST:**
- `@spec docs/best_practices/yaml/prompt_optimization_spec.yaml`
- `@spec docs/best_practices/yaml/lambda_handler_spec.yaml`
- `@spec docs/best_practices/yaml/dynamodb_modeling_spec.yaml`
- `@spec docs/best_practices/yaml/testing_spec.yaml`
- `@spec docs/best_practices/yaml/cicd_spec.yaml`
- `@ref docs/beta/BETA_STRUCTURED_OUTLINE_2026-03-11.md`
- `@pattern docs/refactor/execution_runbook_2.md`

**ROLE:** Senior DevOps Engineer and Technical Writer specializing in AWS Serverless, CI/CD, and executable documentation

**PROBLEM:** CareerVP needs an executable runbook where EACH STEP IS A PROMPT that Claude Code can execute to produce deterministic outputs.

**SOLUTION:** Create runbook where every Step contains a complete, executable prompt following the `execution_runbook_2.md` pattern.

---

## Critical Pattern: Steps MUST Create Prompts

Each Step MUST follow this EXACT format:

```markdown
### Step N.X: [Task Name]

**READ FIRST:**
- `@spec path/to/spec.yaml`
- `@ref path/to/reference.md`

**PROMPT:**
```bash
# VSCode + Anthropic [Sonnet|Haiku]
"""
ROLE: [Specific role title]

CONTEXT: [What needs to be built and why]

TASK: [What to implement]

1. [File to create]: [path/to/file.py]
   - Class/Function: [name]
   - Method: [signature]
   - [Detailed implementation steps with bullet points]

2. [File to modify]: [path/to/file.py]
   - [What to add/change]

3. [Test file to create]: tests/unit/test_[feature].py
   - test_[scenario_1]
   - test_[scenario_2]

VALIDATION CRITERIA (must all pass):
- [ ] [Specific measurable criterion]
- [ ] [Command to run]: [exact command]

OUTPUT FORMAT: [What to output and where]
"""
```

---

## Required Structure (8 Phases)

### Phase 1: Generator Reality (Layer 0)

**Purpose:** Fix broken AI generators that return templates instead of Claude calls

| Step | Prompt Output |
|------|---------------|
| L0.1 | Fix Cover Letter handler to call Claude API |
| L0.2 | Fix Interview Prep handler to call Claude API |
| L0.3 | Fix Gap Analysis handler to call Claude API |
| L0.4 | Validate/fix CV Tailoring quality scores |
| L0.5 | Reduce Company Research latency |

**Phase Integration Test:** Run all 5 generators, scan output for template strings (regex), verify 0 matches

---

### Phase 2: Persistence and Data Integrity (Layer 1)

**Purpose:** Ensure all artifacts are stored and retrievable

| Step | Prompt Output |
|------|---------------|
| L1.1 | Fix artifact persistence to DynamoDB |
| L1.2 | Replace CVTable with DynamoDalHandler |
| L1.3 | Fix health check to report real infrastructure |
| L1.4 | Validate list endpoints return generated artifacts |

**Phase Integration Test:** Generate artifact → poll complete → list → assert artifact in response

---

### Phase 3: Auth Migration (Layer 2)

**Purpose:** Migrate to Cognito JWT authorizer

| Step | Prompt Output |
|------|---------------|
| L2.1 | Create CDK Cognito User Pool |
| L2.2 | Configure API Gateway Cognito authorizer |
| L2.3 | Remove X-User-Id header and payload identity extraction |
| L2.4 | Update frontend with Cognito SDK |
| L2.5 | Integration test auth scenarios |

**Phase Integration Test:** Test all 4 auth scenarios (no token, expired, wrong user, valid)

---

### Phase 4: Application State Model (Layer 3)

**Purpose:** Canonical lifecycle model for state recovery

| Step | Prompt Output |
|------|---------------|
| L3.1 | Design Application DynamoDB schema |
| L3.2 | Implement GET /applications/{id} recovery endpoint |
| L3.3 | Wire trial credit charging at gap question generation |
| L3.4 | Test state recovery on page reload |

**Phase Integration Test:** Simulate workflow interruption, reload page, verify state restored

---

### Phase 5: Trial Enforcement (Layer 4)

**Purpose:** 14-day / 3-application limit

| Step | Prompt Output |
|------|---------------|
| L5.1 | Implement trial expiry check middleware |
| L5.2 | Implement 3-application counter |
| L5.3 | Create GET /users/me/usage endpoint |
| L5.4 | Integration test trial enforcement |

**Phase Integration Test:**
- Exhaust 3 applications → attempt 4th → assert 403
- Simulate day-15 → assert blocked

---

### Phase 6: Route Surface Cleanup (Layer 5)

**Purpose:** Single canonical route set

| Step | Prompt Output |
|------|---------------|
| L6.1 | Document canonical route decisions |
| L6.2 | Remove duplicate API Gateway routes |
| L6.3 | Update Swagger contract |
| L6.4 | Verify route surface matches spec |

**Phase Integration Test:** Compare deployed routes to frozen spec, assert exact match

---

### Phase 7: Frontend Integration (Layer 6)

**Purpose:** Complete user workflow

| Step | Prompt Output |
|------|---------------|
| L7.1 | Implement Cognito auth flow |
| L7.2 | Implement CV upload workflow |
| L7.3 | Implement job application workflow |
| L7.4 | Implement artifact polling |
| L7.5 | Implement state recovery on reload |

**Phase Integration Test:** Full E2E workflow with page reloads at each step

---

### Phase 8: Operational Readiness (Layer 7)

**Purpose:** Deploy and validate

| Step | Prompt Output |
|------|---------------|
| L8.1 | Deploy CDK to staging |
| L8.2 | Run smoke tests |
| L8.3 | Generate evidence bundle (E1-E8) |
| L8.4 | Run final sign-off checklist |

**Live Test Suite:** Execute against deployed staging, measure SLAs, generate evidence JSON

---

## Per-Step Template (COPY THIS PATTERN FOR EACH STEP)

```markdown
### Step [N.X]: [Descriptive Title]

**Duration:** [X hours]
**Invariant(s) Satisfied:** [I1, I2, etc.]
**Precondition(s) Resolved:** [PC1, PC2, etc.]

**READ FIRST:**
- `@spec [spec file]`
- `@ref [reference doc]`
- `@pattern [example pattern]`

**PROMPT:**
```bash
# VSCode + Anthropic [Sonnet|Haiku]
"""
ROLE: [Specific role - e.g., "Senior Backend Engineer specializing in AWS Lambda and Python"]

CONTEXT: [Why this task matters - business/technical justification]
- Current state: [what's broken/wrong]
- Target state: [what should happen]
- Impact: [why this matters for beta launch]

TASK: [One sentence - what to implement]

IMPLEMENTATION DETAILS:

1. [New File to Create]: [full path]
   - [Class/Function name]: [signature]
   - [Key attributes/methods]
   - [Implementation logic - numbered sub-steps]

2. [Existing File to Modify]: [full path]
   - [What to add/change]
   - [Import statements]
   - [Integration point]

3. [Test File]: tests/unit/test_[feature].py
   - test_[scenario_1]: [description]
   - test_[scenario_2]: [description]

4. [CDK/Infra if needed]: [stack file]
   - [Resource to add]
   - [Configuration]

VALIDATION CRITERIA (ALL MUST PASS):
- [ ] [Specific measurable criterion #1]
- [ ] [Specific measurable criterion #2]
- [ ] Run: `cd src/backend && uv run pytest tests/unit/test_[feature].py -v --tb=short`
- [ ] Run: `cd src/backend && uv run ruff check careervp/[module]/`
- [ ] Run: `cd src/backend && uv run mypy careervp/[module]/[file].py --strict`

OUTPUT FORMAT:
- Write results to: docs/beta/execution_results/[step_id]_results.md
- Include: [what to document]
"""
```

---

## Compliance Requirements

All prompts MUST comply with specs:

| Spec | Requirement |
|------|-------------|
| `lambda_handler_spec.yaml` | Powertools Logger/Tracer/Metrics, Pydantic, Response builders, Auth from requestContext |
| `dynamodb_modeling_spec.yaml` | Single table, PK/SK prefixes, GSI/LSI, Query not Scan |
| `testing_spec.yaml` | RED phase TDD, mocking, pytest config |
| `cicd_spec.yaml` | Pipeline stages, security scanning |

---

## Evidence Generation (Live Tests)

For Phase 8, include prompts that generate evidence files:

```bash
# Generate E1: generator-output-audit.json
"""
TASK: Run 50 iterations of each generator, scan for template strings

OUTPUT: docs/beta/evidence/I1_generators/generator-output-audit.json
"""
```

---

## Output

Write complete runbook to: `docs/beta/beta_execution_runbook.md`

Include at end:
- Phase completion checklist
- Evidence bundle commands
- Sign-off criteria from BETA_STRUCTURED_OUTLINE_2026-03-11.md Section 5
