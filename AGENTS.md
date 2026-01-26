# Codex Engineering Guardrails

Codex must follow the same engineering discipline defined in `.clauderules`. Treat this file as mandatory operating procedures.

## Architecture & Style
- Mirror the **Handler → Logic → DAL** separation in every change.
- Ensure every Lambda handler wires AWS Lambda Powertools logging, tracing, and metrics.
- Use full Python type hints on all functions and favor the shared `Result` object for cross-layer error propagation.

## Testing & Linting

- Follow the **test-first** rule: no task is complete (and no checklist item updated) until its unit/integration tests pass.
- After modifying any Python file, immediately run `uv run mypy <filename> --strict`. Fix every reported issue before sharing code.
- Run the project's pytest suites relevant to your change (`pytest` targets live under `src/backend/tests`). Never declare success without green tests.
- Respect the pre-commit toolchain (Ruff lint/format, mypy, etc.) defined in `.pre-commit-config.yaml` and the `pyproject.toml` settings (line length 150, single quotes, Python 3.14).

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

## The Architect (Claude) Rule:
Upon a Blocking Issue, the Architect must analyze if the Spec is wrong or if the Environment needs refactoring. The Architect must provide a "Migration Path" in the next Task Guide.
