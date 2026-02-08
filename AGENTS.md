# CareerVP Coding & Workflow Rules (Codex)

Codex must follow the exact same rules defined in `.clauderules`. This document replicates those guardrails so both agents stay synchronized.

## Naming Convention Standard

### Kebab-Case Physical Resource Naming

All AWS physical resource names MUST follow the kebab-case convention:

**Format:** `careervp-{feature}-{resource_type}-{env}`

| Resource Type | Pattern | Example |
|---------------|---------|---------|
| **Stack IDs** | `CareerVp{Feature}{Env}` (PascalCase) | `CareerVpApiDev`, `CareerVpStorageProd` |
| **Logical IDs** | Must match Construct class name | `ApiConstruct`, `ApiDbConstruct` |
| **Lambda Functions** | `careervp-{feature}-lambda-{env}` | `careervp-cv-parser-lambda-dev` |
| **DynamoDB Tables** | `careervp-{feature}-table-{env}` | `careervp-users-table-dev` |
| **S3 Buckets** | `careervp-{env}-{purpose}-{region_shortcode}-{hash}` | `careervp-dev-cvs-use1-a1b2c3` |
| **IAM Roles** | `careervp-role-{service}-{feature}-{env}` | `careervp-role-lambda-cv-parser-dev` |
| **API Gateway** | `careervp-{feature}-api-{env}` | `careervp-core-api-dev` |

### Naming Rules

1. **No Auto-Generated Suffixes:** Logical IDs must NOT contain CDK tokens like `${Token[...]}` or random suffixes.
2. **Explicit Physical Names:** Always set `function_name`, `table_name`, `bucket_name` explicitly using the `NamingUtils` class.
3. **Constants Source of Truth:** All resource names must be derived from `infra/careervp/constants.py` (CDK) and `src/backend/careervp/logic/utils/constants.py` (backend logic).
4. **Environment Suffix:** All physical names must end with `-{env}` (e.g., `-dev`, `-staging`, `-prod`).

### Code Convention Summary

| Element | Convention | Example |
|---------|------------|---------|
| Python Classes | PascalCase | `VPRGenerator`, `ApiConstruct` |
| Python Functions/Variables | snake_case | `get_user_cv`, `table_name` |
| Constants | UPPER_SNAKE_CASE | `USERS_TABLE_NAME`, `CV_BUCKET_NAME` |
| AWS Physical Resources | kebab-case | `careervp-users-table-dev` |
| File Names | snake_case | `vpr_generator.py`, `cv_parser.py` |

### Gatekeeper Rule (MANDATORY)

**The Engineer (Codex) MUST run the naming validator after ANY CDK change and BEFORE any deployment.**

```bash
# After ANY change to infra/ directory
python src/backend/scripts/validate_naming.py --path infra --verbose

# For strict validation (full pattern enforcement)
python src/backend/scripts/validate_naming.py --path infra --strict
```

**If the validator fails:**
1. The fix is MANDATORY before proceeding
2. Do NOT run `cdk deploy` until all violations are resolved
3. Emit a "BLOCKING ISSUE" report if unable to fix

**Validation Checks:**
- All physical resource names start with `careervp-`
- Valid resource types: `lambda`, `table`, `bucket`, `api`, `role`, `queue`, `topic`, `bus`
- No CDK tokens (`${Token[...]}`) in Logical IDs
- Kebab-case enforced for all physical names

## Architecture & Style
- **Pattern:** Adhere strictly to the "Handler -> Logic -> DAL" separation.
- **Handlers:** Every Lambda handler MUST use AWS Lambda Powertools for logging, tracing, and metrics.
- **Types:** Python type hints are mandatory for all function signatures.
- **Errors:** Use a standard Result object pattern for cross-layer error communication.

## Testing & Linting

- Follow the **test-first** rule: no task is complete (and no checklist item updated) until its unit/integration tests pass.
- After modifying any Python file, immediately run `uv run mypy <filename> --strict`. Fix every reported issue before sharing code.
- After modifying any Python file, immediately run `uv run ruff check <filename> --fix`. Resolve every Ruff finding before sharing code.
- Run the project's pytest suites relevant to your change (`pytest` targets live under `src/backend/tests`). Never declare success without green tests.
- Respect the pre-commit toolchain (Ruff lint/format, mypy, etc.) defined in `.pre-commit-config.yaml` and the `pyproject.toml` settings (line length 150, single quotes, Python 3.14).

## Mandatory Ruff Test Before Task Completion

**CRITICAL:** ALL code edits MUST pass Ruff checks before completing any task.

Before marking ANY task as complete, you MUST:

1. Run `uv run ruff format <changed_files>` to auto-format code
2. Run `uv run ruff check <changed_files> --fix` to fix linting issues
3. Verify zero Ruff errors remain

If Ruff reports any errors that cannot be auto-fixed:
- You MUST manually fix the issues
- Re-run Ruff checks until they pass
- Do NOT mark the task complete until Ruff passes

```bash
# Example workflow for any code change
cd /Users/yitzchak/Documents/dev/careervp/src/backend
uv run ruff format careervp/logic/<file>.py
uv run ruff check careervp/logic/<file>.py --fix
# Verify output shows no errors before proceeding
```

### Mandatory Testing Commands

- **Unit tests:** `uv run pytest tests/unit/<test_file>.py -v`
- **Integration tests:** `uv run pytest tests/integration/ -v`
- **Full suite:** `uv run pytest tests/ -v --tb=short`

### Mocking Requirements

- Use `moto` for AWS service mocking (DynamoDB, S3).
- Mock external API calls (LLM, HTTP) - NEVER call real APIs in tests.
- Use `unittest.mock.patch` for LLM client mocking.

### Mandatory Cleanup (Before Task Completion)

- Run `uv run ruff format .` and `uv run ruff check --fix .`
- Zero linting errors required for task completion.

## Anti-Hallucination & Content Rules
- Enforce the Fact Verification tiers: IMMUTABLE facts (dates, roles, contact info) must never be altered; VERIFIABLE data must exist in the source CV; FLEXIBLE framing only where allowed.
- Apply the Anti-AI detection heuristics (varied sentence structure, minor imperfections, natural transitions) to all generated prose.

## Documentation & Planning
- Read the relevant spec in `docs/specs/` before implementing a feature.
- Update both `PROGRESS.md` and `plan.md` when (and only when) the associated code + tests land.

These rules are non‑negotiable. If any step fails (tests, lint, type checks), fix the issue and rerun before presenting results.

## Section: Agent Escalation Protocol
The Engineer (Codex) Rule: If any specified Path, Class Name, or Method Signature in a Task Guide does not exist in the current environment, the Engineer MUST NOT create a workaround. They must emit a "BLOCKING ISSUE" report and exit.

## The Architect (Claude) Rule
Upon a Blocking Issue, the Architect must analyze if the Spec is wrong or if the Environment needs refactoring. The Architect must provide a "Migration Path" in the next Task Guide.

## Implementation Guardrail
- Before starting any task, verify the state of the environment using verify_aws_state.py --mode deployed if infrastructure was recently changed.

## File Conventions
- Python Modules: `snake_case.py` (e.g., `company_research.py`)
- Infrastructure Scripts: `kebab-case.py` (e.g., `validate-naming.py`)
- Documentation/Tasks: `task-##-name.md`
- Tests: `test_*.py` located in `src/backend/tests/unit/`

## Git Workflow Rules
- **Don't switch branches with uncommitted changes** - use `git stash` first to avoid accidentally deleting files
- **Merge via gh CLI directly from the feature branch** - avoids needing to checkout main
- **Only clean up local branch after successful merge**
