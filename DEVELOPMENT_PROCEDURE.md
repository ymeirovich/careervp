# CareerVP Development Procedure

## Git/Workflow Problems Identified

| Problem | Root Cause |
|---------|------------|
| Direct main commits | No PR protection on main |
| Multiple fix commits | Tests not run before push |
| Rolled back commits | CI failures caught post-push |
| Repeated workflow fixes | Same errors fixed multiple times |
| Incorrect task completion | Assumptions not validated |
| CI false positives | Ruff format discrepancies |

---

## Standard Development Procedure (v2.0)

### Before Starting Any Feature

1. **Create feature branch**
   ```bash
   git checkout main
   git pull
   git checkout -b feature/<feature-name>
   ```

2. **Read design/specs** (ask Claude to read design docs)

3. **Run baseline tests** - verify current state passes
   ```bash
   cd src/backend && uv run pytest tests/ -q --tb=line
   cd infra && uv run pytest tests/infrastructure/ -q
   ```

---

### Implementation Loop (Repeat for each task)

1. **Implement the code change**

2. **Run LOCAL validation** - CRITICAL STEP
   ```bash
   cd src/backend
   uv run ruff format .      # Format
   uv run ruff check .       # Lint
   uv run mypy . --strict   # Type check
   uv run pytest tests/unit/test_<module>.py -v  # Relevant tests
   ```

3. **If all pass -> Commit with clear message**
   ```bash
   git add <files>
   git commit -m "feat: add gap_responses to generate_vpr"
   ```

4. **If any fail -> Fix before committing**
   - Repeat step 2 until clean

---

### After Completing Feature

1. **Run FULL local test suite**
   ```bash
   cd src/backend && uv run pytest tests/ -q
   cd infra && uv run pytest tests/infrastructure/ -q
   ```

2. **Push branch**
   ```bash
   git push -u origin feature/<feature-name>
   ```

3. **Create PR** via GitHub UI
   - Title: "feat: <feature-name>"
   - Description: Link to design doc

4. **Wait for CI to pass** - don't merge until green

5. **Merge PR** (Squash and merge recommended)

---

## Your Command Checklist

### Quick Local Validation (run BEFORE every commit)
```bash
cd src/backend && uv run ruff format . && uv run ruff check . && uv run mypy . --strict && uv run pytest tests/ -q --tb=line
```

### Full Backend Test Suite
```bash
cd src/backend && uv run pytest tests/ -v --tb=short
```

### Infrastructure Tests
```bash
cd infra && uv run pytest tests/infrastructure/ -v
```

### CDK Synth
```bash
cd infra && npx cdk synth
```

---

## Key Rules

| Rule | Why |
|------|-----|
| **No direct main commits** | Main branch protected |
| **Test before commit** | Catch failures locally |
| **Validate assumptions** | Check code, don't assume |
| **One feature = one PR** | Clean history |
| **Squash on merge** | Linear history |

---

## Feature Branch Template

When starting a new feature:

```
1. git checkout main && git pull
2. git checkout -b feature/<name>
3. Run baseline tests
4. Read design docs
5. Implement incrementally with local validation
6. Full test suite
7. Push + PR + CI + Merge
```

---

## Common Issues Quick Fix

| Issue | Fix |
|-------|-----|
| Ruff format diff | `uv run ruff format .` then commit |
| MyPy errors | Fix types, don't ignore |
| Test failures | Fix code, don't skip |
| CDK synth fails | Check resource names |
| CI false positive | Run locally first |
