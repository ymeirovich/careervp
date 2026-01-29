# Feature Spec: Value Proposition Report Generator (F-JOB-005)

## Objective

Generate a strategic Value Proposition Report (VPR) that maps a candidate's CV facts to job requirements, identifying key strengths and gap mitigation strategies. VPR serves as the foundation for all downstream artifacts (CV Tailoring, Cover Letter, Interview Prep).

## Technical Details

- **Trigger:** API POST `/api/vpr` with CV facts, job posting, and optional gap analysis responses.
- **Model:** Claude Sonnet 4.5 (`TaskMode.STRATEGIC` via LLM Router).
- **Memory:** 1024 MB.
- **Timeout:** 120 seconds.
- **Cost Target:** < $0.04 per VPR (~8K input tokens, ~2.5K output tokens).
- **Storage:** DynamoDB with `PK=applicationId`, `SK=ARTIFACT#VPR#v{version}`.
- **Prompt Reference:** `docs/features/CareerVP Prompt Library.md` (lines 128-259).

## Input Schema

### Required

- `application_id`: Unique application identifier.
- `user_cv`: Parsed CV facts (from `UserCV` model).
- `job_posting`: Structured job posting data (from `JobPosting` model).

### Optional (MVP Approach)

- `gap_responses`: User answers to gap analysis questions (list of Q&A pairs).
- `company_context`: Company research data (mission, values, priorities).

## Output Schema: VPR Content Structure

1. **Executive Summary** (200-250 words)
   - Candidate's unique value proposition for this role.
   - Why they are a strong fit.

2. **Evidence & Alignment Matrix** (600-800 words)
   - Job requirement -> CV fact mapping.
   - Enhanced with gap analysis responses where available.
   - Format: Requirement | Evidence | Alignment Score | Impact Potential.

3. **Strategic Differentiators** (300-400 words)
   - 3-5 key strengths that set the candidate apart.
   - Quantified achievements from CV and gap responses.

4. **Gap Mitigation Strategies** (200-300 words)
   - For each missing/weak requirement.
   - Suggested talking points or reframing approaches.

5. **Cultural Fit Analysis** (150-200 words)
   - Based on company research.
   - Alignment with company values.

6. **Recommended Talking Points** (150-200 words)
   - 5-7 key messages for interviews.
   - ATS-optimized keywords for CV tailoring.

## FVS (Fact Verification System) Rules

Per CLAUDE.md, `.clauderules`, and `docs/features/CareerVP Prompt Library.md`:

| Tier | Fields | Rule |
| ---- | ------ | ---- |
| **IMMUTABLE** | Dates, company names, job titles, contact info | NEVER modify or fabricate |
| **VERIFIABLE** | Skills, achievements | Only include if present in source CV |
| **FLEXIBLE** | Executive summary, framing, strategic positioning | Creative liberty allowed |

**Critical:** The VPR synthesizes data from **multiple sources**:

- **CV Facts** (IMMUTABLE tier) - dates, titles, companies cannot be invented
- **Gap Analysis Responses** - user-provided evidence that can enhance CV facts
- **Job Requirements** - used for alignment mapping
- **Company Research** - used for cultural fit and strategic positioning

Any claim about the candidate's history must be traceable to CV facts or gap responses. Strategic framing and company alignment are FLEXIBLE.

## Anti-AI Detection Patterns

Per CLAUDE.md Decision 1.6 and Prompt Library, the generated VPR must:

1. **Avoid AI-flagged phrases:**
   - "leverage", "delve into", "landscape", "robust", "streamline"
   - "spearheading", "synergy", "cutting-edge", "game-changer"
   - "utilize", "paradigm shift", "best practices"

2. **Use natural language:**
   - Vary sentence length (8-25 words).
   - Include natural transitions.
   - Use approximations ("nearly 40%" not "39.7%").
   - Mix active and passive voice naturally.

## Logic Flow

1. **Validate Input:** Ensure CV and job posting are provided.
2. **Detect Language:** Auto-detect CV and job posting languages.
3. **Build Prompt:** Use `VPR_GENERATION_PROMPT` from Prompt Library.
4. **Invoke LLM:** Call Sonnet 4.5 via LLM Router with `TaskMode.STRATEGIC`.
5. **Parse Response:** Extract structured VPR sections from LLM output.
6. **FVS Validation:** Verify IMMUTABLE facts against input CV.
7. **Persist:** Save VPR to DynamoDB.
8. **Return:** Respond with VPR content and metadata.

## API Contract

### Request

```json
POST /api/vpr
{
  "application_id": "app-uuid-123",
  "user_id": "user-uuid-456",
  "job_posting": {
    "company_name": "Natural Intelligence",
    "role_title": "Learning & Development Manager",
    "responsibilities": ["Lead organizational development..."],
    "requirements": ["5+ years experience..."],
    "nice_to_have": ["HR Business Partner experience"],
    "language": "en"
  },
  "gap_responses": [
    {"question": "Describe your experience with...", "answer": "..."}
  ]
}
```

### Response

```json
{
  "success": true,
  "vpr": {
    "application_id": "app-uuid-123",
    "executive_summary": "...",
    "evidence_matrix": [...],
    "differentiators": [...],
    "gap_strategies": [...],
    "cultural_fit": "...",
    "talking_points": [...],
    "keywords": [...],
    "version": 1,
    "language": "en"
  },
  "token_usage": {
    "input_tokens": 7500,
    "output_tokens": 2200,
    "cost_usd": 0.035
  },
  "generation_time_ms": 45000
}
```

## Success Criteria

- [ ] VPR generated within 120 seconds.
- [ ] IMMUTABLE facts verified against CV (zero hallucinations on dates/titles/companies).
- [ ] Gap analysis responses integrated into evidence matrix.
- [ ] Passes anti-AI detection check.
- [ ] Length: 1,500-2,000 words.
- [ ] AI cost < $0.040 per VPR.
- [ ] Unit tests pass with mocked LLM.

## Task Breakdown

See `docs/tasks/03-vpr-generator/` for implementation tasks:

1. `task-01-models.md` - VPR and JobPosting Pydantic models
2. `task-02-dal-methods.md` - DynamoDB save/get VPR methods
3. `task-03-generator-logic.md` - Core VPR generation logic
4. `task-04-sonnet-prompt.md` - Integration with Prompt Library
5. `task-05-handler.md` - Lambda handler implementation
6. `task-06-tests.md` - Unit tests with moto/mocked LLM
