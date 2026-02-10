# JSA Skill Alignment - Junior Engineer Implementation Guide

**For:** Junior Backend Engineers
**Task:** Implement JSA Skill Alignment enhancements
**Created:** 2026-02-09
**Reference:** `docs/architecture/JSA_ALIGNMENT_DESIGN.md`

---

## Quick Start

### 1. Read These First (in order)

1. This guide (5 min)
2. `docs/specs/05-jsa-skill-alignment.md` (10 min)
3. `docs/architecture/JSA_ALIGNMENT_DESIGN.md` (15 min)
4. Existing code patterns in the codebase

### 2. Your First Task: Fix VPR Tests

Run this command to see what's broken:

```bash
cd src/backend
PYTHONPATH=$(pwd) uv run pytest ../../tests/jsa_skill_alignment/test_vpr_alignment.py -v
```

You'll see 7 failing tests. Your job is to fix `vpr_prompt.py` to make them pass.

---

## What You Need to Know

### The Problem

The VPR prompt currently jumps straight to generating output. The JSA Skill architecture uses a **6-stage methodology** with staged thinking and self-correction. We need to add this structure.

### The Solution

Add stage markers and internal output instructions to the VPR prompt. Don't worry - you're not rewriting everything, just adding structure.

### Your Files

| File | Action | What You Do |
|------|--------|-------------|
| `src/backend/careervp/logic/prompts/vpr_prompt.py` | Modify | Add 6-stage structure |

---

## Step-by-Step: Fixing VPR

### Step 1: Read the Current Prompt

```bash
# Open the file
code src/backend/careervp/logic/prompts/vpr_prompt.py
# Or use your preferred editor
```

Find the `VPR_GENERATION_PROMPT` constant. This is a large string (starts around line 15).

### Step 2: Understand the Structure

The current prompt has this structure:

```
1. System role and rules
2. Input data (CV, gap responses, job requirements, etc.)
3. VPR structure sections
4. Anti-AI detection rules
5. Fact verification checklist
6. Output format (JSON)
7. "Generate the JSON VPR now:"
```

You need to add stage markers BETWEEN these sections.

### Step 3: Add the Stages

Copy this template and insert it into the prompt at the appropriate places:

```markdown
---

STAGE 1: COMPANY & ROLE RESEARCH

Analyze the company research and identify:
- 3-5 strategic priorities or current challenges
- 5-7 role success criteria from job posting

OUTPUT (Internal): List strategic priorities and role criteria before proceeding.

---

STAGE 2: CANDIDATE ANALYSIS

Parse CV facts and gap responses:
- Identify achievements with quantified outcomes
- Extract 3-5 core differentiators (what sets candidate apart)
- Summarize career narrative in ONE sentence

OUTPUT (Internal): List differentiators and career narrative before proceeding.

---

STAGE 3: ALIGNMENT MAPPING

Create reasoning scaffold table with 5-7 minimum alignments:

| Company/Role Need | Candidate Evidence | Business Impact |
|-------------------|-------------------|------------------|
| [from Stage 1] | [from CV + gaps] | [value delivery] |

OUTPUT (Internal): Complete alignment matrix before proceeding.

---

STAGE 4: SELF-CORRECTION & META REVIEW

Before proceeding, perform internal critique:
- Are there any unsupported claims?
- Is logic consistent throughout?
- Would this persuade a senior hiring manager?
- Are arguments evidence-driven and sharp?

OUTPUT (Internal): Note any refinements made.

---

STAGE 5: GENERATE REPORT

[Current VPR structure sections - keep as-is]

---

STAGE 6: FINAL META EVALUATION

Ask yourself: "How could this report be 20% more persuasive, specific, or actionable?"

Apply those improvements and output the final refined version.
```

### Step 4: Where to Insert Each Stage

| Stage | Insert After | Context |
|-------|--------------|----------|
| STAGE 1 | "COMPANY RESEARCH:" input | Before processing the data |
| STAGE 2 | After Stage 1 output | Before analyzing the candidate |
| STAGE 3 | After Stage 2 output | Before creating the report |
| STAGE 4 | After Stage 3 output | Before final generation |
| STAGE 5 | After Stage 4 | Current VPR structure |
| STAGE 6 | After Stage 5 | Before JSON output |

### Step 5: Verify Your Changes

Run the tests:

```bash
cd src/backend
PYTHONPATH=$(pwd) uv run pytest ../../tests/jsa_skill_alignment/test_vpr_alignment.py -v
```

You should see:

```
tests/.../test_vpr_has_6_stages PASSED
tests/.../test_vpr_has_self_correction PASSED
tests/.../test_vpr_has_meta_evaluation PASSED
# ... and so on
```

---

## Common Mistakes to Avoid

### Mistake 1: Removing Existing Content

**Don't do this:**
```python
# BAD - Removed important rules!
VPR_GENERATION_PROMPT = """STAGE 1... [everything else deleted]"""
```

**Do this instead:**
```python
# GOOD - Added stages, kept existing content
VPR_GENERATION_PROMPT = """You are an expert career strategist...

[existing content]

---

STAGE 1: COMPANY & ROLE RESEARCH
...
"""
```

### Mistake 2: Wrong Stage Names

**Must match exactly:**
- `STAGE 1: COMPANY & ROLE RESEARCH` (all caps, colon, spaces)
- `STAGE 2: CANDIDATE ANALYSIS`
- `STAGE 3: ALIGNMENT MAPPING`
- `STAGE 4: SELF-CORRECTION & META REVIEW`
- `STAGE 5: GENERATE REPORT`
- `STAGE 6: FINAL META EVALUATION`

### Mistake 3: Missing Internal Output Markers

**Must include:**
- `OUTPUT (Internal):` before each transition

### Mistake 4: Forgetting to Test

Always run:
```bash
uv run pytest tests/jsa_skill_alignment/test_vpr_alignment.py -v
```

---

## Your Next Tasks (After VPR)

Once VPR is working, you'll implement these in order:

### Task 2: CV Tailoring 3-Step

**File:** `src/backend/careervp/logic/cv_tailoring_prompt.py`

**Tests:** `tests/jsa_skill_alignment/test_cv_tailoring_alignment.py`

**What to add:**
- STEP 1, STEP 2, STEP 3 markers
- ATS verification check (1-10 score)
- Hiring manager alignment check
- `{company_keywords}` and `{vpr_differentiators}` parameters

### Task 3: Cover Letter Handler

**Files:**
- `src/backend/careervp/handlers/cover_letter_handler.py` (create new)
- `src/backend/careervp/logic/prompts/cover_letter_prompt.py` (modify)

**Tests:** `tests/jsa_skill_alignment/test_cover_letter_alignment.py`

**What to do:**
1. Create new Lambda handler for POST /api/cover-letter
2. Add reference class priming step
3. Add paragraph word count constraints (80-100, 120-140, 60-80)
4. Add proof points structure (3 requirements × claim + proof)

### Task 4: Gap Analysis Handler

**Files:**
- `src/backend/careervp/handlers/gap_handler.py` (complete lambda_handler)
- `src/backend/careervp/logic/prompts/gap_analysis_prompt.py` (modify)

**Tests:** `tests/jsa_skill_alignment/test_gap_analysis_alignment.py`

**What to do:**
1. Complete the lambda_handler function (currently only has helpers)
2. Add [CV IMPACT] and [INTERVIEW/MVP ONLY] tags
3. Add MAX 10 questions constraint
4. Add recurring_themes parameter
5. Add strategic intent field

---

## How to Test Your Work

### Run Specific Tests

```bash
# VPR tests
cd src/backend
PYTHONPATH=$(pwd) uv run pytest ../../tests/jsa_skill_alignment/test_vpr_alignment.py -v

# CV Tailoring tests
PYTHONPATH=$(pwd) uv run pytest ../../tests/jsa_skill_alignment/test_cv_tailoring_alignment.py -v

# Cover Letter tests
PYTHONPATH=$(pwd) uv run pytest ../../tests/jsa_skill_alignment/test_cover_letter_alignment.py -v

# Gap Analysis tests
PYTHONPATH=$(pwd) uv run pytest ../../tests/jsa_skill_alignment/test_gap_analysis_alignment.py -v
```

### Run All JSA Tests

```bash
cd src/backend
PYTHONPATH=$(pwd) uv run pytest ../../tests/jsa_skill_alignment/ -v
```

### Code Quality

```bash
# Check linting
uv run ruff check src/backend/careervp/

# Check types
uv run mypy src/backend/careervp --strict
```

---

## Finding Help

### When You're Stuck

1. **Check the spec:** `docs/specs/05-jsa-skill-alignment.md`
2. **Check the design:** `docs/architecture/JSA_ALIGNMENT_DESIGN.md`
3. **Check existing patterns:** Look at similar files in `src/backend/careervp/`
4. **Ask questions:** Leave comments in your PR

### Code Patterns to Follow

Look at these files for patterns:

- `src/backend/careervp/handlers/cv_tailoring_handler.py` - Lambda handler pattern
- `src/backend/careervp/handlers/utils/validation.py` - Input validation
- `tests/gap_analysis/unit/test_gap_prompt.py` - Test patterns

### Key Imports to Use

```python
from aws_lambda_powertools.utilities.typing import LambdaContext
from careervp.handlers.utils.observability import logger, tracer, metrics
```

---

## Definition of Done

Your task is complete when:

- [ ] All VPR tests pass: `uv run pytest tests/jsa_skill_alignment/test_vpr_alignment.py -v`
- [ ] No linting errors: `uv run ruff check src/backend/careervp/`
- [ ] No type errors: `uv run mypy src/backend/careervp --strict`
- [ ] Code follows existing patterns in the codebase
- [ ] PR created and reviewed

---

## File Locations Quick Reference

```
src/backend/careervp/
├── logic/
│   ├── prompts/
│   │   ├── vpr_prompt.py           # <-- YOUR FIRST FILE
│   │   ├── cv_tailoring_prompt.py
│   │   ├── cover_letter_prompt.py
│   │   └── gap_analysis_prompt.py
│   └── cv_tailoring_logic.py
└── handlers/
    ├── cv_tailoring_handler.py     # Reference for patterns
    ├── gap_handler.py              # Needs completion
    └── cover_letter_handler.py     # Needs creation

tests/jsa_skill_alignment/
├── test_vpr_alignment.py           # Tests for your work
├── test_cv_tailoring_alignment.py
├── test_cover_letter_alignment.py
└── test_gap_analysis_alignment.py
```

---

## Questions?

Check these resources first:

1. `docs/specs/05-jsa-skill-alignment.md` - Technical requirements
2. `docs/architecture/JSA_ALIGNMENT_DESIGN.md` - Detailed design
3. `docs/tasks/05-jsa-skill-alignment.md` - Implementation tasks
4. `docs/architecture/jsa-skill-alignment/JSA-ALIGNMENT-CHECKLIST.md` - Checklist

If still stuck, leave a comment in your PR asking for clarification.

---

**Good luck! You've got this!**
