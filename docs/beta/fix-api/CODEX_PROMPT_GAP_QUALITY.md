# Codex Prompt: Gap Analysis Question Quality Fix

## Context

The gap analysis questions generated are of low quality compared to the ground truth. The generated questions are generic fallbacks instead of contextually-rich, targeted questions.

## Current Problem

### Generated Output (Low Quality):
```json
{
  "question_id": "generated-q1",
  "question": "What concrete evidence demonstrates fit for uncovered requirement #1?",
  "impact": "LOW",
  "probability": "LOW",
  "gap_score": 0.0,
  "tags": ["[CV IMPACT]"]
}
```

### Expected Output (Ground Truth):
- Detailed strategic intent for each question
- Clear requirement from job posting
- Evidence gap analysis
- Priority level (CRITICAL | IMPORTANT | OPTIONAL)
- Proper quantification emphasis for CV IMPACT questions

## Architecture Reference

Per `docs/architecture/prompt-improvement/CareerVP_Agentic_Architecture.md` section 3.3:

The Gap Analysis Question Generator should:
1. Load User Memory (query knowledge base for recurring themes)
2. Cross-Reference Analysis (CV facts vs job requirements)
3. Categorize by Destination ([CV IMPACT] vs [INTERVIEW/MVP ONLY])
4. Generate Questions (Max 10) with quantification emphasis

## Enhanced Prompt Reference

Per `docs/architecture/jsa-skill-alignment/JSA-Skill-Alignment-Plan.md` section B:

The prompt should include:
- CV FACTS (user's established strengths)
- USER'S RECURRING THEMES (skip these topics)
- JOB REQUIREMENTS (critical requirements only)
- COMPANY CONTEXT
- PREVIOUS GAP RESPONSES (do not repeat)

### Question Format Should Include:
```markdown
### Question {N}

**Requirement:** [Exact quote from job posting]
**Question:** [Targeted question emphasizing quantification]
**Destination:** [CV IMPACT] or [INTERVIEW/MVP ONLY]
**Strategic Intent:** [Why being asked, how response will be used]
**Evidence Gap:** [What's missing from the CV]
**Priority:** CRITICAL | IMPORTANT | OPTIONAL
```

## Your Task

### 1. Analyze Current Implementation

Read these files:
- `src/backend/careervp/logic/gap_analysis.py` - gap analysis logic
- `src/backend/careervp/logic/prompts/gap_analysis_prompt.py` - current prompt

Identify:
- What's missing from the current prompt
- Why fallback questions are being used
- Why gap_score is 0.0 (it's hardcoded in _ensure_question_count)

### 2. Fix the Prompt

Replace the current simple prompt with the enhanced version that includes:
- CV facts context
- Job requirements context
- Recurring themes (skip topics)
- Company research context
- Previous gap responses

### 3. Fix the Fallback Logic

The `_ensure_question_count` function hardcodes `gap_score: 0.0` for fallback questions. Either:
- Remove fallbacks entirely (require LLM to generate all questions)
- Or calculate proper gap_score for fallbacks

### 4. Add Required Fields

Update the question schema to include:
- `requirement` - exact quote from job posting
- `strategic_intent` - why being asked
- `evidence_gap` - what's missing from CV
- `priority` - CRITICAL | IMPORTANT | OPTIONAL

### 5. Add Tests

**Unit Test:**
- Verify questions include all required fields
- Verify gap_score is calculated properly (not hardcoded 0.0)
- Verify fallback questions are not used when LLM generates enough

**Integration Test:**
- Compare generated questions against ground truth format
- Verify strategic_intent is meaningful (not generic)

## Expected Behavior

After the fix:
1. Each question should have a specific requirement from the job posting
2. Questions should be targeted, not generic fallbacks
3. gap_score should be calculated based on impact/probability (not hardcoded)
4. Questions should have strategic_intent, evidence_gap, and priority
5. [CV IMPACT] questions should emphasize quantification

## Test File Reference
- `careervp/live-test-results25.log` - contains current low-quality output
- `docs/features/Sample Gap Analysis Questions Answers.txt` - ground truth format
- `src/backend/careervp/logic/gap_analysis.py` - gap analysis logic
- `src/backend/careervp/logic/prompts/gap_analysis_prompt.py` - current prompt

## Hints
- The prompt is missing critical context (CV facts, job requirements, recurring themes)
- The _ensure_question_count function is creating generic fallback questions
- gap_score 0.0 is hardcoded, not calculated for fallback questions
- The LLM needs more context to generate targeted questions
