# Cover Letter Generation Design

**Date:** 2026-02-05
**Author:** Claude Sonnet 4.5 (Lead Architect)
**Phase:** 10 - Cover Letter Generation
**Status:** Architecture Complete - Ready for Implementation

---

## Table of Contents

1. [Overview](#overview)
2. [Architectural Decisions](#architectural-decisions)
3. [Cover Letter Generation Algorithm](#cover-letter-generation-algorithm)
4. [Quality Scoring Algorithm](#quality-scoring-algorithm)
5. [Cover Letter Generation Workflow](#cover-letter-generation-workflow)
6. [FVS Integration](#fvs-integration)
7. [Data Flow](#data-flow)
8. [LLM Prompt Strategy](#llm-prompt-strategy)
9. [Error Handling](#error-handling)
10. [Performance Considerations](#performance-considerations)
11. [Testing Strategy](#testing-strategy)

---

## Overview

### Purpose

The Cover Letter Generation feature creates personalized, compelling cover letters tailored to specific job positions. It synthesizes the user's Value Proposition Report (VPR), tailored CV, gap analysis responses, and company research into a natural, human-sounding cover letter that passes anti-AI detection filters.

### Key Objectives

1. **Personalization**: Create compelling narratives that showcase specific accomplishments aligned with job requirements
2. **Natural Voice**: Generate human-like text that avoids AI detection patterns (varied sentence structure, natural transitions, minimal buzzwords)
3. **Company Fit**: Demonstrate understanding of company culture and role-specific requirements
4. **Efficiency**: Generate cover letters in under 20 seconds
5. **Quality Assurance**: Score and validate output before delivery
6. **Cost Optimization**: Target $0.004-0.006 per letter using Claude Haiku 4.5

### Success Metrics

- **Quality Score**: Average quality score ≥ 0.75 across all generated cover letters
- **Personalization Score**: Minimum 0.70 (demonstrates specific accomplishments)
- **Relevance Score**: Minimum 0.70 (addresses job requirements)
- **Tone Appropriateness**: Minimum 0.70 (matches company culture)
- **Latency**: p95 response time < 20 seconds
- **Cost**: Average cost per letter < $0.006
- **FVS Compliance**: 100% of company names and job titles verified against input

---

## Architectural Decisions

### Decision 1: Synchronous Implementation ✅

**Decision:** Use synchronous Lambda pattern (like cv_upload_handler.py)

**Rationale:**
- Consistency with existing handlers (CV Upload, VPR Generator)
- Cover letter generation completes quickly (8-15 seconds Haiku response)
- Simpler error handling and immediate feedback
- Aligns with user expectations (request → response)
- Matches Phase 9 CV Tailoring pattern

**Trade-offs:**
- ❌ Cannot handle extremely long company research documents (> 20K chars)
- ✅ Simpler implementation (no SQS/polling infrastructure)
- ✅ Immediate feedback to user
- ✅ Better error handling (synchronous exceptions)

**Implementation Pattern:**
```python
# Synchronous handler that directly calls logic layer
@logger.inject_lambda_context(log_event=True)
@tracer.capture_lambda_handler(capture_response=False)
@metrics.log_metrics(capture_cold_start_metric=True)
def lambda_handler(event: dict, context: LambdaContext) -> dict:
    # Parse request
    # Call logic layer
    # Return response immediately
```

---

### Decision 2: LLM Model - Claude Haiku 4.5 ✅

**Decision:** Use Claude Haiku 4.5 (TaskMode.TEMPLATE)

**Rationale:**
- **Cost Optimized**: $0.25 per MTok input, $1.25 per MTok output
- **Fast**: 3-8 second response time (ideal for cover letters)
- **Sufficient Quality**: Template-based generation with explicit FVS rules
- **Pattern Proven**: Same model used successfully in CV Tailoring

**Estimated Costs per Cover Letter:**
```
Input tokens:  ~12,000 tokens  (CV + VPR + Job Description + Prompt)
Output tokens: ~600 tokens     (Cover letter text)

Cost = (12,000 * $0.25 / 1M) + (600 * $1.25 / 1M)
     = $0.003 + $0.00075
     = $0.00375 per letter

With overhead (error handling, retries):
Average: $0.004-0.006 per successful letter
```

**Fallback Strategy:** If Haiku produces quality score < 0.70, retry with Sonnet 4.5 (higher cost but better quality).

```python
# Fallback logic
haiku_result = await call_llm(model="haiku-4-5", ...)
quality_score = calculate_quality_score(haiku_result)

if quality_score < 0.70:
    logger.info("Haiku quality insufficient, falling back to Sonnet")
    sonnet_result = await call_llm(model="sonnet-4-5", ...)
    return sonnet_result
```

---

### Decision 3: Timeout - 300 Seconds ✅

**Decision:** 300 seconds (5 minutes) via asyncio.wait_for()

**Rationale:**
- Haiku typical response: 3-8 seconds
- Buffer for network latency: 30 seconds
- Buffer for retries: 3x attempts = 50 seconds max
- Safety margin: 200 seconds
- Total: ~60 seconds typical, 300 seconds max safety

**Implementation:**
```python
import asyncio

async def generate_cover_letter_with_timeout(llm_client: LLMClient, prompt: str) -> str:
    try:
        response = await asyncio.wait_for(
            llm_client.generate(
                messages=[...],
                model="claude-haiku-4-5",
                max_tokens=2048
            ),
            timeout=300.0  # 5 minutes
        )
        return response
    except asyncio.TimeoutError:
        raise TimeoutError("LLM call timed out after 300 seconds")
```

---

### Decision 4: Storage Strategy - DynamoDB Artifacts ✅

**Decision:** Store generated cover letters as DynamoDB artifacts with 90-day TTL

**Schema:**
```python
PK: user_id                                          # Partition key
SK: ARTIFACT#COVER_LETTER#{cv_id}#{job_id}#v{version}  # Sort key
TTL: current_timestamp + 7776000                     # 90 days in seconds
```

**Example:**
```json
{
  "pk": "user_123",
  "sk": "ARTIFACT#COVER_LETTER#cv_abc#job_xyz#v1",
  "artifact_type": "COVER_LETTER",
  "cv_id": "cv_abc",
  "job_id": "job_xyz",
  "version": 1,
  "user_id": "user_123",
  "company_name": "TechCorp Inc",
  "job_title": "Senior Python Engineer",
  "content": "Dear Hiring Manager,\n\nI am excited to apply for...",
  "word_count": 287,
  "personalization_score": 0.82,
  "relevance_score": 0.79,
  "tone_score": 0.85,
  "quality_score": 0.815,
  "preferences": {
    "tone": "professional",
    "word_count_target": 300,
    "emphasis_areas": ["leadership", "python", "aws"]
  },
  "fvs_validation": {
    "is_valid": true,
    "company_name_verified": true,
    "job_title_verified": true,
    "violations": []
  },
  "generated_at": "2026-02-05T12:00:00Z",
  "ttl": 1752076800
}
```

**Rationale:**
- Same pattern as other artifacts (VPR, Gap Analysis, Tailored CV)
- Easy retrieval by user_id + cv_id + job_id
- Automatic cleanup via TTL
- Version support for regeneration with different preferences
- Enables re-download and history tracking

---

## Cover Letter Generation Algorithm

### Overview

The cover letter generation algorithm synthesizes multiple data sources into a personalized, natural cover letter that demonstrates fit for a specific role while avoiding AI detection patterns.

### Input Synthesis

**Required Inputs:**
1. **Master CV** - User's complete CV (fetched from DAL)
2. **Tailored CV** - Optional, CV tailored to job description
3. **VPR Artifact** - Value Proposition Report with accomplishments and recommendations
4. **Job Description** - Target job posting (from request)
5. **Company Name** - Company hiring for role
6. **Job Title** - Target job title
7. **Preferences** - Optional tone, emphasis areas, word count target
8. **Gap Responses** - Optional responses to gap analysis questions

**Data Sources Priority:**
```
Personalization Level: High
├─ VPR accomplishments (most specific)
├─ Gap analysis responses (contextual)
├─ Tailored CV (relevant experience)
├─ Company research (culture/values)
└─ Master CV (background)
```

### Personalization Strategy

**Level 1: Specific Accomplishment Mapping**
```
Algorithm: Match VPR accomplishments to job requirements

For each job requirement (e.g., "5 years Python experience"):
  Find VPR accomplishment that demonstrates this
  Example: "Shipped 3 production systems in Python handling 100k+ users"

Extract specific metrics from accomplishment:
  - Quantifiable results (100k+ users)
  - Technical depth (production systems)
  - Relevant experience (Python)
```

**Level 2: Company Culture Alignment**
```
Algorithm: Reference company-specific details in cover letter

Gather company research:
  - Company mission/values
  - Recent products or announcements
  - Technical challenges mentioned in job description

Create connections:
  Example: "Your recent expansion into AI-powered features aligns
           with my experience shipping ML systems at previous companies"
```

**Level 3: Tone Calibration**
```
Available Tones:
- "professional": Formal, emphasize achievements and credentials
- "enthusiastic": Energetic, highlight passion and cultural fit
- "technical": Deep-dive on technical challenges and solutions

Strategy: Inject tone markers in prompt to guide LLM
  Professional: Use structured bullet points, formal transitions
  Enthusiastic: Use active voice, personal anecdotes, energy phrases
  Technical: Use technical terminology, architecture discussion
```

### Anti-AI Detection Patterns

**Pattern 1: Sentence Structure Variation**
```
❌ AVOID: All sentences start with subject-verb-object
  "I have experience with Python. I have built systems. I have led teams."

✅ IMPLEMENT: Mix sentence structures
  "My 8 years in backend engineering have prepared me for this role.
   What sets me apart is not just technical depth, but the ability to
   communicate complex systems. I've consistently..."
```

**Pattern 2: Natural Transitions**
```
❌ AVOID: Robotic connectors
  "Furthermore, the aforementioned experiences demonstrate synergy..."

✅ IMPLEMENT: Conversational flow
  "Beyond just writing code, I've always believed in mentoring junior
   developers. This philosophy shapes how I approach team projects."
```

**Pattern 3: No Buzzwords**
```
❌ AVOID: Clichés detected by AI detectors
  "In today's rapidly evolving landscape..."
  "Leveraging cutting-edge synergies..."
  "Passionate about driving impactful innovation..."

✅ IMPLEMENT: Specific, authentic language
  "When we shipped the real-time analytics dashboard, it reduced
   query latency from 5 seconds to 200ms..."
```

**Pattern 4: Varied Length and Complexity**
```
Sentence Length Distribution:
- 30% short sentences (5-10 words)
- 50% medium sentences (10-25 words)
- 20% long sentences (25+ words)

Word Complexity:
- 80% common words
- 15% domain-specific technical terms
- 5% sophisticated vocabulary
```

**Implementation in Prompt:**
```
# Anti-AI Detection Rules
Vary sentence structure - include short, medium, and long sentences
Use natural transitions - avoid "Furthermore" and "In conclusion"
Avoid AI buzzwords - no "landscape", "synergy", "innovative"
Include specific metrics - quantify achievements with real numbers
Use active voice - "I built" not "I was responsible for building"
Sound natural - as if human wrote it in 30 minutes
```

---

## Quality Scoring Algorithm

### Overview

Quality scoring quantifies the effectiveness of generated cover letters across three dimensions: personalization (how specific it is), relevance (how well it addresses job requirements), and tone appropriateness (how well it matches company culture).

### Scoring Formula

```python
quality_score = (
    0.40 × personalization_score +    # Specific accomplishments cited
    0.35 × relevance_score +          # Job requirements addressed
    0.25 × tone_appropriateness       # Matches company culture
)

# All component scores range [0.0, 1.0]
# Final quality_score ranges [0.0, 1.0]
```

### Component 1: Personalization Score (40% weight)

**Purpose:** Measure specificity of accomplishments and metrics

**Algorithm:**
```python
def calculate_personalization_score(
    cover_letter: str,
    vpr_accomplishments: list[str]
) -> float:
    """
    Calculate personalization by measuring:
    - Presence of specific metrics (numbers, percentages, timeframes)
    - References to unique accomplishments (not generic skills)
    - Company/role-specific details (not copy-paste generic)

    Returns: Score 0.0-1.0
    """
    score = 0.0

    # Check 1: Specific metrics (30% of personalization score)
    metric_patterns = [
        r'\d+\s*(?:%|years?|projects?|users?|systems?)',  # "5 years", "100 users"
        r'\$\d+[KMB]?',                                     # "$5M revenue"
        r'\d+x\s+(?:faster|improvement)',                   # "10x faster"
    ]

    metrics_found = sum(
        len(re.findall(pattern, cover_letter))
        for pattern in metric_patterns
    )
    metric_score = min(metrics_found / 3.0, 1.0)  # Need at least 3 metrics for full score
    score += 0.30 * metric_score

    # Check 2: VPR accomplishment references (40% of personalization score)
    referenced_accomplishments = 0
    for accomplishment in vpr_accomplishments:
        # Check if accomplishment is present or paraphrased
        if accomplishment_referenced_in_text(accomplishment, cover_letter):
            referenced_accomplishments += 1

    accomplishment_score = min(referenced_accomplishments / len(vpr_accomplishments), 1.0)
    score += 0.40 * accomplishment_score

    # Check 3: Unique details (30% of personalization score)
    # Check for role/company-specific details beyond generic statements
    unique_details = 0

    if uses_specific_company_name(cover_letter):
        unique_details += 1
    if references_specific_job_title(cover_letter):
        unique_details += 1
    if includes_unique_experience_detail(cover_letter):
        unique_details += 1

    uniqueness_score = unique_details / 3.0
    score += 0.30 * uniqueness_score

    return min(score, 1.0)
```

**Example:**
```
Cover Letter Text:
"During my time at FinTech Corp, I led development of a real-time
trading platform that processed 1 million transactions daily. This
5-person team shipped the system in 6 months, exceeding revenue targets
by 40%."

VPR Accomplishments:
1. "Led team of 5 engineers"
2. "Shipped production system handling high volume"
3. "Exceeded business targets"

Personalization Score Calculation:
- Metrics Found: 4 (1M transactions, 5-person, 6 months, 40%) → 0.30 score
- Accomplishments Referenced: 3/3 → 1.0 score
- Unique Details: 3/3 (FinTech Corp, trading platform, revenue targets) → 1.0 score

Final: 0.30*0.30 + 0.40*1.0 + 0.30*1.0 = 0.09 + 0.40 + 0.30 = 0.79 personalization_score
```

### Component 2: Relevance Score (35% weight)

**Purpose:** Measure how well cover letter addresses job requirements

**Algorithm:**
```python
def calculate_relevance_score(
    cover_letter: str,
    job_description: str
) -> float:
    """
    Calculate relevance by measuring:
    - Keyword match (technical skills mentioned in job)
    - Requirement addressing (required qualifications covered)
    - Experience alignment (similar roles mentioned)

    Returns: Score 0.0-1.0
    """
    job_keywords = extract_keywords(job_description)
    job_requirements = extract_requirements(job_description)

    score = 0.0

    # Check 1: Keyword match (40% of relevance score)
    keywords_in_letter = 0
    for keyword in job_keywords:
        if keyword_present_in_text(keyword, cover_letter):
            keywords_in_letter += 1

    keyword_score = keywords_in_letter / len(job_keywords) if job_keywords else 0.5
    score += 0.40 * min(keyword_score, 1.0)

    # Check 2: Requirement addressing (40% of relevance score)
    requirements_addressed = 0
    for requirement in job_requirements:
        # Check if requirement is addressed by cover letter
        if requirement_addressed_in_letter(requirement, cover_letter):
            requirements_addressed += 1

    requirement_score = (
        requirements_addressed / len(job_requirements)
        if job_requirements else 0.5
    )
    score += 0.40 * requirement_score

    # Check 3: Experience alignment (20% of relevance score)
    # Check if cover letter mentions relevant experience
    if mentions_relevant_role_experience(job_description, cover_letter):
        experience_score = 0.8
    elif mentions_related_experience(job_description, cover_letter):
        experience_score = 0.5
    else:
        experience_score = 0.2

    score += 0.20 * experience_score

    return min(score, 1.0)
```

**Example:**
```
Job Description Keywords: ["Python", "Django", "REST APIs", "PostgreSQL", "Docker"]
Relevance Score Calculation:
- Keywords in letter: 4/5 (missing "Docker") → 0.80
- Requirements addressed: 4/4 (skills, seniority, team size, company type) → 1.0
- Experience alignment: Mentions "5 years backend Python" → 0.8

Final: 0.40*0.80 + 0.40*1.0 + 0.20*0.8 = 0.32 + 0.40 + 0.16 = 0.88 relevance_score
```

### Component 3: Tone Appropriateness (25% weight)

**Purpose:** Measure how well tone matches company culture and preferences

**Algorithm:**
```python
def calculate_tone_appropriateness(
    cover_letter: str,
    requested_tone: str,  # "professional", "enthusiastic", "technical"
    company_description: str = "",
) -> float:
    """
    Calculate tone appropriateness by measuring:
    - Tone consistency (matches requested tone throughout)
    - Energy level (appropriate formality/enthusiasm)
    - Language register (technical depth if requested)

    Returns: Score 0.0-1.0
    """
    score = 0.0

    # Check 1: Tone consistency (50% of tone score)
    tone_indicators = analyze_tone_indicators(cover_letter)

    if requested_tone == "professional":
        consistency = measure_professional_consistency(tone_indicators)
    elif requested_tone == "enthusiastic":
        consistency = measure_enthusiastic_consistency(tone_indicators)
    elif requested_tone == "technical":
        consistency = measure_technical_consistency(tone_indicators)
    else:
        consistency = 0.5  # Unknown tone

    score += 0.50 * consistency

    # Check 2: Energy level (25% of tone score)
    if requested_tone == "professional":
        energy_score = 1.0 if is_formal_energy_level(cover_letter) else 0.6
    elif requested_tone == "enthusiastic":
        energy_score = 1.0 if is_energetic(cover_letter) else 0.6
    elif requested_tone == "technical":
        energy_score = 1.0 if is_technical_focused(cover_letter) else 0.6

    score += 0.25 * energy_score

    # Check 3: Language register (25% of tone score)
    if requested_tone == "professional":
        register_score = measure_professional_register(cover_letter)
    elif requested_tone == "enthusiastic":
        register_score = measure_energetic_register(cover_letter)
    elif requested_tone == "technical":
        register_score = measure_technical_register(cover_letter)
    else:
        register_score = 0.5

    score += 0.25 * register_score

    return min(score, 1.0)
```

**Example:**
```
Requested Tone: "enthusiastic"

Tone Indicators:
- Active voice sentences: 85% (target: 80+) → good
- Exclamation marks: 1/4 paragraphs (natural, not excessive) → good
- Energy phrases: 3 instances ("excited to", "passionate about", "thrilled") → good
- Sentence variety: 8 different sentence starts → good

Tone Appropriateness Score:
- Tone consistency: 0.90 (mostly consistent enthusiastic tone)
- Energy level: 0.85 (energetic but professional, not manic)
- Language register: 0.88 (good balance of enthusiasm and credibility)

Final: 0.50*0.90 + 0.25*0.85 + 0.25*0.88 = 0.45 + 0.2125 + 0.22 = 0.88 tone_score
```

### Quality Score Thresholds

| Score Range | Rating | Action | Fallback |
|-------------|--------|--------|----------|
| 0.80 - 1.00 | Excellent | Return immediately | None (no retry) |
| 0.70 - 0.79 | Good | Return to user | Optional retry with Sonnet |
| 0.60 - 0.69 | Acceptable | Return with warning | Recommend regeneration |
| 0.50 - 0.59 | Below Threshold | Auto-retry with Sonnet | Return if no improvement |
| < 0.50 | Insufficient | Return error | Manual regeneration only |

---

## Cover Letter Generation Workflow

### High-Level Flow

```
┌─────────────────┐
│ User Request    │  GenerateCoverLetterRequest(cv_id, job_id, company_name, job_title, preferences)
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────┐
│ Handler: cover_letter_handler.py                            │
│  - Validate request (Pydantic)                              │
│  - Authenticate user (JWT)                                  │
│  - Fetch master CV and VPR from DAL                         │
│  - Call generate_cover_letter() logic                       │
└────────┬────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────┐
│ Logic: cover_letter_generator.py                             │
│  1. Synthesize input data (CV, VPR, job description)        │
│  2. Build LLM prompt (system + user)                        │
│  3. Call LLM (Haiku 4.5) to generate cover letter           │
│  4. Parse LLM response into TailoredCoverLetter model       │
│  5. Calculate quality score (personalization + relevance)   │
│  6. Validate with FVS (company name, job title)             │
│  7. If quality < 0.70, retry with Sonnet 4.5               │
│  8. Return Result[TailoredCoverLetter]                      │
└────────┬────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────┐
│ Handler: cover_letter_handler.py                            │
│  - Check generation result                                  │
│  - If error: return appropriate HTTP status                 │
│  - Store cover letter artifact in DAL                       │
│  - Generate S3 presigned URL for download                   │
│  - Return TailoredCoverLetterResponse                       │
└─────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────┐
│ Response: HTTP 200 OK                                       │
│ {                                                           │
│   "success": true,                                          │
│   "cover_letter": { ... },                                  │
│   "quality_score": 0.82,                                    │
│   "download_url": "https://...",                            │
│   "code": "COVER_LETTER_GENERATED_SUCCESS"                 │
│ }                                                           │
└─────────────────────────────────────────────────────────────┘
```

### Detailed Steps

#### Step 1: Input Validation

**Input:** GenerateCoverLetterRequest (Pydantic model)

**Validations:**
```python
class GenerateCoverLetterRequest(BaseModel):
    cv_id: str = Field(..., min_length=1, max_length=255)
    job_id: str = Field(..., min_length=1, max_length=255)
    company_name: str = Field(..., min_length=1, max_length=255)
    job_title: str = Field(..., min_length=1, max_length=255)
    job_description: Optional[str] = Field(None, max_length=50000)
    preferences: Optional[CoverLetterPreferences] = None

class CoverLetterPreferences(BaseModel):
    tone: Literal["professional", "enthusiastic", "technical"] = "professional"
    word_count_target: int = Field(default=300, ge=200, le=500)
    emphasis_areas: Optional[List[str]] = None
    include_company_research: bool = True
```

**Validation Rules:**
- cv_id: Valid UUID format, must exist for user_id
- job_id: Valid UUID format, must exist for user_id
- company_name: 1-255 characters, no special characters
- job_title: 1-255 characters, no special characters
- job_description: 0-50,000 characters (optional)
- tone: Must be one of [professional, enthusiastic, technical]
- word_count_target: 200-500 words

#### Step 2: Data Retrieval

**Fetch from DAL:**
```python
# Retrieve master CV
cv_result = await dal.get_cv_by_id(request.cv_id, user_id)
if not cv_result.success:
    return Result.failure(code=ResultCode.CV_NOT_FOUND)

# Retrieve VPR artifact (required for personalization)
vpr_result = await dal.get_vpr_artifact(request.cv_id, request.job_id)
if not vpr_result.success:
    return Result.failure(code=ResultCode.VPR_NOT_FOUND)

# Optionally retrieve tailored CV (for additional context)
tailored_cv_result = await dal.get_artifact(
    user_id=user_id,
    artifact_type="CV_TAILORED",
    cv_id=request.cv_id,
    job_id=request.job_id
)

# Optionally retrieve gap responses (for personalization)
gap_responses_result = await dal.get_gap_analysis_responses(
    cv_id=request.cv_id,
    job_id=request.job_id
)
```

#### Step 3: LLM Prompt Construction

**Build System Prompt:**
```python
system_prompt = build_system_prompt(
    tone=request.preferences.tone,
    word_count_target=request.preferences.word_count_target
)
```

**Build User Prompt:**
```python
user_prompt = build_user_prompt(
    cv=cv_result.data,
    vpr=vpr_result.data,
    company_name=request.company_name,
    job_title=request.job_title,
    job_description=request.job_description,
    gap_responses=gap_responses_result.data if gap_responses_result.success else None,
    emphasis_areas=request.preferences.emphasis_areas,
)
```

See [LLM Prompt Strategy](#llm-prompt-strategy) section for detailed prompt structure.

#### Step 4: LLM Generation

**Call LLM with Timeout:**
```python
import asyncio

try:
    llm_response = await asyncio.wait_for(
        llm_client.generate(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            task_mode=TaskMode.TEMPLATE,
            model="claude-haiku-4-5",
            max_tokens=2048,
        ),
        timeout=300.0  # 5 minutes
    )
except asyncio.TimeoutError:
    return Result.failure(
        error=f"LLM request timed out after 300 seconds",
        code=ResultCode.CV_LETTER_GENERATION_TIMEOUT
    )
```

#### Step 5: Response Parsing

**Expected LLM Output:**
```json
{
  "cover_letter": "Dear Hiring Manager,\n\nI am thrilled...",
  "word_count": 287,
  "personalization_highlights": [
    "Led team of 5 engineers shipping production systems",
    "Passion for mentoring junior developers",
    "Experience with real-time analytics platforms"
  ]
}
```

**Parsing Strategy:**
```python
def parse_llm_response(llm_output: str) -> dict:
    """Parse LLM JSON output into structured format."""
    try:
        data = json.loads(llm_output)
        return {
            "cover_letter": data.get("cover_letter", ""),
            "word_count": count_words(data.get("cover_letter", "")),
            "personalization_highlights": data.get("personalization_highlights", [])
        }
    except (json.JSONDecodeError, ValueError) as e:
        raise ValueError(f"Failed to parse LLM response: {e}")
```

#### Step 6: Quality Scoring

**Calculate Quality Scores:**
```python
personalization_score = calculate_personalization_score(
    cover_letter_text=llm_response["cover_letter"],
    vpr_accomplishments=vpr_result.data.accomplishments
)

relevance_score = calculate_relevance_score(
    cover_letter=llm_response["cover_letter"],
    job_description=request.job_description
)

tone_score = calculate_tone_appropriateness(
    cover_letter=llm_response["cover_letter"],
    requested_tone=request.preferences.tone
)

# Combine into overall quality score
quality_score = (
    0.40 * personalization_score +
    0.35 * relevance_score +
    0.25 * tone_score
)
```

#### Step 7: FVS Validation

**Validate Company Name and Job Title:**
```python
fvs_result = validate_cover_letter(
    cover_letter_text=llm_response["cover_letter"],
    company_name=request.company_name,
    job_title=request.job_title
)

# VERIFIABLE tier: Company name and job title must match
if not fvs_result.is_valid:
    if fvs_result.has_critical_violations:
        return Result.failure(
            error=f"FVS validation failed: company/job title mismatch",
            code=ResultCode.FVS_HALLUCINATION_DETECTED,
            data=fvs_result
        )
```

**Example FVS Violations:**
```
CRITICAL Violations:
- Company name: Expected "Microsoft", got "Microsogt" → REJECT
- Job title: Expected "Senior Engineer", got "Junior Developer" → REJECT

WARNING Violations:
- Tone mismatch: Requested "technical", but letter is generic → WARN
- Word count: Target 300, got 250 → WARN (acceptable)
```

#### Step 8: Quality-Based Retry Logic

**Check Quality Score:**
```python
if quality_score >= 0.80:
    # Excellent quality, return immediately
    return Result.success(
        data=tailored_cover_letter,
        code=ResultCode.COVER_LETTER_GENERATED_SUCCESS
    )
elif quality_score >= 0.70:
    # Good quality, return but allow regeneration
    return Result.success(
        data=tailored_cover_letter,
        code=ResultCode.COVER_LETTER_GENERATED_SUCCESS,
        metadata={"quality_tier": "good"}
    )
elif quality_score >= 0.60:
    # Acceptable but suggest retry
    logger.info("Quality score below target, attempting retry with Sonnet")
    sonnet_result = await call_llm(model="sonnet-4-5", ...)
    sonnet_quality = calculate_quality_score(sonnet_result)

    if sonnet_quality > quality_score:
        return Result.success(
            data=tailored_cover_letter_from_sonnet,
            code=ResultCode.COVER_LETTER_GENERATED_SUCCESS
        )
    else:
        return Result.success(
            data=tailored_cover_letter,
            code=ResultCode.COVER_LETTER_GENERATED_SUCCESS,
            metadata={"quality_tier": "acceptable"}
        )
else:
    # Insufficient quality, return error
    return Result.failure(
        error="Generated cover letter quality insufficient",
        code=ResultCode.GENERATION_QUALITY_INSUFFICIENT
    )
```

#### Step 9: Artifact Storage

**Store in DynamoDB:**
```python
from careervp.dal.dynamo_dal_handler import DynamoDalHandler

dal = DynamoDalHandler(table_name=env_vars.TABLE_NAME)

artifact = {
    "pk": user_id,
    "sk": f"ARTIFACT#COVER_LETTER#{cv_id}#{job_id}#v{version}",
    "artifact_type": "COVER_LETTER",
    "cv_id": cv_id,
    "job_id": job_id,
    "version": version,
    "user_id": user_id,
    "company_name": request.company_name,
    "job_title": request.job_title,
    "content": tailored_cover_letter.content,
    "word_count": tailored_cover_letter.word_count,
    "personalization_score": personalization_score,
    "relevance_score": relevance_score,
    "tone_score": tone_score,
    "quality_score": quality_score,
    "preferences": request.preferences.model_dump() if request.preferences else {},
    "fvs_validation": fvs_result.model_dump(),
    "generated_at": datetime.now(UTC).isoformat(),
    "ttl": int(time.time()) + 7776000  # 90 days
}

await dal.save_artifact(artifact)
```

---

## FVS Integration

### FVS Tier Definitions (Per system_design.md)

1. **IMMUTABLE**: Facts that must NEVER be modified
   - None for cover letters (creative content)

2. **VERIFIABLE**: Facts that can be reframed but must have a source
   - Company name (must match job description or request)
   - Job title (must match job description or request)

3. **FLEXIBLE**: Content with full creative liberty
   - Cover letter narrative
   - Achievement descriptions
   - Tone and voice
   - Emphasis areas

### FVS Validation Strategy

**Pre-Generation (Baseline Capture):**
```python
def create_fvs_baseline(
    company_name: str,
    job_title: str
) -> dict:
    """
    Create FVS baseline for verification.
    Since cover letters are creative content, only verify company/role.
    """
    return {
        "verifiable_facts": {
            "company_name": company_name.lower(),
            "job_title": job_title.lower()
        }
    }
```

**Post-Generation (Validation):**
```python
def validate_cover_letter(
    cover_letter_text: str,
    company_name: str,
    job_title: str
) -> FVSValidationResult:
    """
    Validate cover letter against baseline facts.

    CRITICAL violations: Company name or job title completely wrong
    WARNING violations: Minor variations in capitalization/phrasing
    """
    violations = []

    # Check 1: Company name verification
    company_found = fuzzy_match_in_text(company_name, cover_letter_text, threshold=0.85)
    if not company_found:
        violations.append({
            "field": "company_name",
            "expected": company_name,
            "severity": "CRITICAL",
            "message": f"Company name '{company_name}' not found in cover letter"
        })

    # Check 2: Job title verification
    job_title_found = fuzzy_match_in_text(job_title, cover_letter_text, threshold=0.85)
    if not job_title_found:
        violations.append({
            "field": "job_title",
            "expected": job_title,
            "severity": "CRITICAL",
            "message": f"Job title '{job_title}' not found in cover letter"
        })

    return FVSValidationResult(
        is_valid=len(violations) == 0,
        has_critical_violations=any(v["severity"] == "CRITICAL" for v in violations),
        violations=violations
    )
```

### FVS Error Handling

**Scenario 1: CRITICAL Violation (Company Name Mismatch)**
```
Violation: Company name "Alphabet" in letter, but request says "Google"
Action: REJECT cover letter, return 400 Bad Request
Response:
{
  "success": false,
  "error": "FVS validation failed: company name mismatch",
  "code": "FVS_HALLUCINATION_DETECTED",
  "fvs_violations": [
    {
      "field": "company_name",
      "expected": "Google",
      "actual": "Alphabet",
      "severity": "CRITICAL"
    }
  ]
}
```

**Scenario 2: Acceptable Match (Fuzzy)**
```
Violation: Letter says "Senior Software Engineer", job title is "Senior Engineer"
Action: ACCEPT (fuzzy match, not critical)
Response:
{
  "success": true,
  "cover_letter": { ... },
  "fvs_validation": {
    "is_valid": true,
    "warnings": []
  }
}
```

---

## Data Flow

### End-to-End Data Flow Diagram

```
┌──────────────┐
│   Frontend   │
│  (React App) │
└──────┬───────┘
       │
       │ POST /api/cover-letter
       │ Body: { cv_id, job_id, company_name, job_title, preferences }
       │
       ▼
┌────────────────────────────────────────┐
│  API Gateway                           │
│  - Authentication (Cognito JWT)        │
│  - Rate limiting (5-15 req/min)        │
│  - Input validation (OpenAPI schema)   │
└──────┬─────────────────────────────────┘
       │
       │ Invoke Lambda
       │
       ▼
┌────────────────────────────────────────┐
│  Lambda: cover_letter_handler.py       │
│  - Parse TailoredCoverLetterRequest    │
│  - Validate input (Pydantic)           │
│  - Extract user_id from JWT            │
└──────┬─────────────────────────────────┘
       │
       │ Fetch data in parallel
       │
       ├──────────────┬──────────────┬──────────────┐
       │              │              │              │
       ▼              ▼              ▼              ▼
    ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐
    │Master CV │  │   VPR    │  │Tailored  │  │   Gap    │
    │          │  │ Artifact │  │   CV     │  │Responses │
    │ DynamoDB │  │ DynamoDB │  │DynamoDB  │  │DynamoDB  │
    └─────┬────┘  └─────┬────┘  └─────┬────┘  └─────┬────┘
       │              │              │              │
       └──────────────┴──────────────┴──────────────┘
                      │
                      ▼
┌────────────────────────────────────────┐
│  Logic: cover_letter_generator.py      │
│  1. Synthesize input data              │
│  2. Build LLM prompt                   │
│  3. Call quality scoring logic         │
└──────┬─────────────────────────────────┘
       │
       │ Call LLM
       │
       ▼
┌────────────────────────────────────────┐
│  Bedrock (Claude Haiku 4.5)            │
│  - Generate cover letter               │
│  - Timeout: 300 seconds                │
│  - Max tokens: 2048                    │
└──────┬─────────────────────────────────┘
       │
       │ Return generated letter
       │
       ▼
┌────────────────────────────────────────┐
│  Logic: cover_letter_generator.py      │
│  4. Parse LLM response                 │
│  5. Calculate quality score            │
│  6. Validate with FVS                  │
│  7. Check quality thresholds           │
│  8. If needed, retry with Sonnet       │
└──────┬─────────────────────────────────┘
       │
       │ If quality < 0.70
       │ (optional fallback)
       │
       ├─ Retry with Sonnet 4.5
       │
       ▼
┌────────────────────────────────────────┐
│  Bedrock (Claude Sonnet 4.5)           │
│  - Higher quality generation           │
│  - Same prompts as Haiku               │
│  - Timeout: 300 seconds                │
└──────┬─────────────────────────────────┘
       │
       │ Return improved letter (if applicable)
       │
       ▼
┌────────────────────────────────────────┐
│  Logic: cover_letter_generator.py      │
│  9. Store artifact in DynamoDB         │
└──────┬─────────────────────────────────┘
       │
       │ Save artifact
       │
       ▼
┌────────────────────────────────────────┐
│  DynamoDB                              │
│  Put: pk=user_id,                      │
│       sk=ARTIFACT#COVER_LETTER#...     │
│       ttl=current_time + 90_days       │
└──────┬─────────────────────────────────┘
       │
       │ Return success
       │
       ▼
┌────────────────────────────────────────┐
│  S3 Pre-signed URL Generator           │
│  - Generate download URL               │
│  - Expiration: 24 hours                │
└──────┬─────────────────────────────────┘
       │
       │ Return download URL
       │
       ▼
┌────────────────────────────────────────┐
│  Lambda: cover_letter_handler.py       │
│  - Build TailoredCoverLetterResponse   │
│  - Include quality scores              │
│  - Include download URL                │
│  - Return 200 OK                       │
└──────┬─────────────────────────────────┘
       │
       │ HTTP Response
       │
       ▼
┌──────────────────────────────────────┐
│  Frontend                            │
│  - Display cover letter content      │
│  - Show quality score breakdown      │
│  - Provide download link             │
│  - Allow regeneration with different │
│    tone/emphasis if desired           │
└──────────────────────────────────────┘
```

---

## LLM Prompt Strategy

### System Prompt

```
You are an expert cover letter writer helping job candidates stand out.

# Your Task
Generate a compelling, personalized cover letter for a specific job that:
1. Demonstrates specific accomplishments and metrics
2. Shows clear understanding of company culture and role requirements
3. Uses natural, conversational language (not generic buzzwords)
4. Maintains requested tone throughout
5. Includes concrete examples from the candidate's background

# Critical Guidelines

## Personalization
- Start with a specific accomplishment that relates to the role
- Include at least 2 quantifiable results (e.g., "shipped 3 systems", "reduced latency by 40%")
- Reference specific company details or role requirements
- Show genuine interest in THIS role, not a generic position

## Tone Guidelines
[IF "professional"]
- Use formal but warm language
- Focus on achievements and credentials
- Demonstrate respect for company and role
- Avoid excessive enthusiasm
[ENDIF]

[IF "enthusiastic"]
- Use active, energetic language
- Show genuine passion for the role and company
- Include personal touch about why you're excited
- Vary sentence structure for dynamic flow
[ENDIF]

[IF "technical"]
- Use technical terminology appropriately
- Discuss specific technologies and architectures
- Show depth of technical understanding
- Balance depth with accessibility for non-technical hiring managers
[ENDIF]

## Anti-AI Detection
- Vary sentence structure (short + medium + long sentences)
- Use natural transitions ("That experience taught me...", "What's been challenging...")
- Avoid clichés: "landscape", "synergy", "innovative", "passionate about"
- Include specific metrics and timelines
- Sound like someone wrote it naturally, not algorithmically

## FVS Rules (CRITICAL)
VERIFIABLE (must match exactly):
- Company name: Must use EXACTLY as provided
- Job title: Must reference provided job title
- Do NOT make up different company names or job titles

FLEXIBLE (full creative liberty):
- Narrative content
- Achievement descriptions
- Tone and voice
- Specific examples (as long as they align with provided accomplishments)

# Output Format
Return ONLY valid JSON (no markdown code blocks) in this exact format:
{
  "cover_letter": "Dear Hiring Manager,\n\n...",
  "word_count": <number>,
  "personalization_highlights": ["accomplishment 1", "accomplishment 2", ...]
}

Target word count: {{word_count_target}} words (acceptable: ±20%)
```

### User Prompt Template

```
# Job Position
Company: {{company_name}}
Position: {{job_title}}
Job Description:
{{job_description}}

# Candidate Background

## Master CV
Name: {{full_name}}
Email: {{email}}
Phone: {{phone}}

Professional Summary:
{{professional_summary}}

Experience:
{{#each experience}}
- **{{company}}** - {{role}} ({{dates}})
  {{description}}
{{/each}}

Skills:
{{#each skills}}
- {{skill}}
{{/each}}

Education:
{{#each education}}
- {{institution}}: {{degree}} ({{graduation_date}})
{{/each}}

## Value Proposition Report (Accomplishments)
{{#each vpr_accomplishments}}
- {{accomplishment}}
{{/each}}

## Recommended Focus Areas
{{vpr_recommendations}}

{{#if gap_responses}}
## Gap Analysis Responses
{{#each gap_responses}}
Q: {{question}}
A: {{response}}
{{/each}}
{{/if}}

{{#if emphasis_areas}}
## Areas to Emphasize
{{#each emphasis_areas}}
- {{area}}
{{/each}}
{{/if}}

# Requirements for This Cover Letter

Tone: {{tone}}
Word Count Target: {{word_count_target}} words
Personalization Level: HIGH (use specific accomplishments and metrics)
Company Research: {{company_research_snippet}}

# Write the Cover Letter
Generate a cover letter that demonstrates fit for this specific role by:
1. Opening with a specific accomplishment that matches job requirements
2. Including {{specific_metrics_count}} quantifiable results from the candidate's background
3. Referencing {{company_name}} specifically (not generic)
4. Addressing key requirements from the job description
5. Maintaining {{tone}} tone throughout
6. Ending with a clear call-to-action
7. Sounding natural and human-written, not AI-generated

Remember:
- MUST include company name "{{company_name}}" exactly as provided
- MUST reference the role of "{{job_title}}" or the job description requirements
- DO NOT make up accomplishments not in the provided background
- DO NOT use AI-detected phrases like "landscape", "synergy", "innovative"
- DO vary sentence structure for natural flow
```

### Prompt Engineering Best Practices

1. **Explicit FVS Rules**: Include company_name and job_title verification rules
2. **Tone Guidance**: Provide specific examples of tone markers for each style
3. **Anti-AI Patterns**: List phrases to avoid, provide alternatives
4. **Specific Metrics**: Request "at least 2 quantifiable results" to encourage specificity
5. **Company Details**: Include company name in prompt multiple times (reinforces FVS)
6. **Format Requirements**: Specify exact JSON output format with examples
7. **Length Targets**: Provide word count target with acceptable range (±20%)

---

## Error Handling

### Error Scenarios & Mitigation

| Scenario | Error Code | HTTP Status | Mitigation |
|----------|-----------|-------------|------------|
| Invalid request (missing cv_id) | `INVALID_INPUT` | 400 | Pydantic validation, return clear error message |
| CV not found in database | `CV_NOT_FOUND` | 404 | Check if cv_id exists for user_id |
| VPR not found (required for generation) | `VPR_NOT_FOUND` | 400 | Return error, suggest generating VPR first |
| Job not found in database | `JOB_NOT_FOUND` | 404 | Check if job_id exists for user_id |
| Job description too long (> 50K chars) | `INVALID_INPUT` | 400 | Enforce 50K character limit in validation |
| LLM timeout (> 300 seconds) | `CV_LETTER_GENERATION_TIMEOUT` | 504 | Log timeout, suggest user retry |
| LLM rate limited | `RATE_LIMIT_EXCEEDED` | 429 | Exponential backoff (3 retries) |
| LLM returns invalid JSON | `GENERATION_ERROR` | 500 | Log raw response, return generic error |
| FVS CRITICAL violations (company/role mismatch) | `FVS_HALLUCINATION_DETECTED` | 400 | Return violations list, reject generation |
| Quality score too low (< 0.50) | `GENERATION_QUALITY_INSUFFICIENT` | 500 | Return error, suggest regeneration |
| DynamoDB write failure | `STORAGE_ERROR` | 500 | Log error, suggest user retry |
| Authentication failure | `UNAUTHORIZED` | 401 | JWT validation failed, return 401 |
| User rate limit exceeded | `RATE_LIMIT_EXCEEDED` | 429 | Check per-user rate limits, return retry_after |

### Retry Logic

```python
import asyncio
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    reraise=True
)
async def call_llm_with_retry(
    llm_client: LLMClient,
    system_prompt: str,
    user_prompt: str,
    model: str = "claude-haiku-4-5"
) -> str:
    """Call LLM with exponential backoff retry."""
    try:
        response = await asyncio.wait_for(
            llm_client.generate(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                task_mode=TaskMode.TEMPLATE,
                model=model,
                max_tokens=2048,
            ),
            timeout=300.0
        )
        return response
    except asyncio.TimeoutError:
        logger.warning(f"LLM call timed out (attempt {attempt}), retrying...")
        raise
    except Exception as e:
        logger.error(f"LLM call failed (attempt {attempt})", error=str(e))
        raise
```

### Fallback Strategies

**Strategy 1: Sonnet Fallback (Quality Issues)**
```python
# Try Haiku first (cost-optimized)
haiku_result = await call_llm_with_retry(
    model="claude-haiku-4-5",
    system_prompt=system_prompt,
    user_prompt=user_prompt
)

quality_score = calculate_quality_score(haiku_result)

# If quality too low, retry with Sonnet (higher quality, higher cost)
if quality_score < 0.70:
    logger.info("Haiku quality insufficient, falling back to Sonnet (higher cost)")
    sonnet_result = await call_llm_with_retry(
        model="claude-sonnet-4-5",
        system_prompt=system_prompt,
        user_prompt=user_prompt
    )
    sonnet_quality = calculate_quality_score(sonnet_result)

    if sonnet_quality > quality_score:
        logger.info(f"Sonnet improved quality from {quality_score:.2f} to {sonnet_quality:.2f}")
        return sonnet_result
    else:
        logger.warning("Sonnet did not improve quality, returning Haiku result")
        return haiku_result
```

**Strategy 2: Simplified Fallback (LLM Timeout)**
```python
# If LLM times out, generate basic cover letter from template
if timeout_occurred:
    logger.warning("LLM timeout, generating basic cover letter from template")
    basic_letter = generate_basic_cover_letter(
        cv=cv_result.data,
        company_name=request.company_name,
        job_title=request.job_title
    )
    return Result(
        success=True,
        data=basic_letter,
        code=ResultCode.PARTIAL_SUCCESS,
        metadata={"quality_tier": "basic_fallback"}
    )
```

---

## Performance Considerations

### Latency Targets

| Metric | Target | P95 | P99 |
|--------|--------|-----|-----|
| **Total latency** | < 12s | < 20s | < 30s |
| Data retrieval (CV, VPR, etc) | < 2s | < 3s | < 5s |
| LLM call (Haiku) | < 8s | < 15s | < 25s |
| Quality scoring | < 1s | < 2s | < 3s |
| FVS validation | < 0.5s | < 1s | < 2s |
| DynamoDB write | < 0.5s | < 1s | < 2s |
| S3 presigned URL generation | < 0.1s | < 0.5s | < 1s |

### Cost Analysis

**Current Cost Model (Per Letter):**
```
Haiku (primary path, 90% of requests):
- Input:  ~12,000 tokens × $0.25/MTok = $0.003
- Output: ~600 tokens × $1.25/MTok = $0.00075
- Subtotal: $0.00375

Sonnet (fallback for 10% of requests):
- Input:  ~12,000 tokens × $3/MTok = $0.036
- Output: ~600 tokens × $15/MTok = $0.009
- Subtotal: $0.045

Blended Average (90% Haiku + 10% Sonnet):
- Average LLM cost: $0.00375 * 0.90 + $0.045 * 0.10 = $0.0074

Additional Costs:
- Lambda: ~10s × $0.0000166667/s = $0.00017
- DynamoDB: ~1 write + reads × $0.00000125 = $0.000003
- S3 presigned URL: negligible

Total Per Letter: ~$0.0076
```

### Optimization Strategies

1. **Parallel Data Retrieval**: Fetch CV, VPR, tailored CV, gap responses in parallel
2. **Prompt Caching**: Cache system prompt to reduce input token reuse (future enhancement)
3. **Response Truncation**: Request shorter output for very short cover letters
4. **Early Quality Check**: Stop generation early if quality thresholds reached

---

## Testing Strategy

### Unit Testing

**Test Coverage Targets:**
- Quality scoring algorithms: 100% coverage
- FVS integration: 100% coverage
- LLM prompt construction: 90% coverage
- Error handling: 95% coverage

**Key Test Categories:**

1. **Quality Scoring Tests** (27 tests)
   - Personalization score: specific metrics, VPR references, unique details
   - Relevance score: keyword matching, requirement addressing, experience alignment
   - Tone appropriateness: tone consistency, energy level, language register
   - Quality thresholds: excellent, good, acceptable, insufficient

2. **FVS Validation Tests** (24 tests)
   - Company name matching: exact match, fuzzy match, mismatch
   - Job title matching: exact match, fuzzy match, mismatch
   - Violation handling: critical violations, warnings, no violations
   - FVS result serialization

3. **LLM Integration Tests** (19 tests)
   - Successful generation with Haiku
   - Timeout handling and retries
   - Fallback to Sonnet
   - Invalid JSON parsing
   - Rate limit handling

4. **Prompt Construction Tests** (16 tests)
   - System prompt with tone variations
   - User prompt with different data combinations
   - FVS rules injection
   - Word count guidance

5. **Handler Tests** (19 tests)
   - Valid request → success response
   - Missing CV → CV_NOT_FOUND error
   - Missing VPR → VPR_NOT_FOUND error
   - Invalid preferences → INVALID_INPUT error
   - FVS violation → FVS_HALLUCINATION_DETECTED error
   - LLM timeout → CV_LETTER_GENERATION_TIMEOUT error
   - Authentication failures

6. **Model Tests** (27 tests)
   - GenerateCoverLetterRequest validation
   - CoverLetterPreferences validation
   - TailoredCoverLetter serialization/deserialization
   - Response model validation

7. **Integration Tests** (22 tests)
   - Full flow: handler → logic → DAL → LLM → FVS → storage
   - Quality-based fallback to Sonnet
   - Artifact storage and retrieval
   - Rate limiting enforcement

8. **Infrastructure Tests** (28 tests)
   - Lambda configuration (timeout, memory, env vars)
   - API Gateway route setup
   - DynamoDB table with TTL and GSI
   - IAM permissions
   - CORS configuration

9. **E2E Tests** (20 tests)
   - Complete HTTP flow
   - JWT authentication
   - Error scenarios
   - Download URL generation
   - Presigned URL validity

### Testing Fixtures (conftest.py)

```python
# Minimum 20 fixtures required
@pytest.fixture
def sample_master_cv() -> UserCV:
    """Complete UserCV with experience, skills, education."""

@pytest.fixture
def sample_vpr() -> VPRResponse:
    """Sample VPR with accomplishments and recommendations."""

@pytest.fixture
def sample_job_description() -> str:
    """500-word job posting text."""

@pytest.fixture
def sample_cover_letter_request() -> GenerateCoverLetterRequest:
    """Valid cover letter generation request."""

@pytest.fixture
def sample_cover_letter_preferences() -> CoverLetterPreferences:
    """Cover letter preferences with tone/length."""

@pytest.fixture
def mock_llm_client() -> Mock:
    """Mock LLMClient with generate() method."""

@pytest.fixture
def mock_dal_handler() -> Mock:
    """Mock DynamoDalHandler."""

@pytest.fixture
def sample_generated_cover_letter() -> str:
    """Expected cover letter text from LLM."""

@pytest.fixture
def sample_quality_scores() -> Dict[str, float]:
    """Quality scoring breakdown."""

# ... additional fixtures for different scenarios
```

---

## Appendices

### A. Quality Score Examples

**Example 1: High Quality (0.85+)**
```
Company: TechCorp Inc
Position: Senior Python Engineer
Quality Breakdown:
- Personalization: 0.89 (specific metrics, VPR accomplishments referenced)
- Relevance: 0.82 (keywords matched, requirements addressed)
- Tone: 0.85 (professional tone consistent throughout)

Final: 0.40*0.89 + 0.35*0.82 + 0.25*0.85 = 0.356 + 0.287 + 0.2125 = 0.8555
→ Rating: Excellent
```

**Example 2: Acceptable Quality (0.65)**
```
Quality Breakdown:
- Personalization: 0.68 (some metrics, partial VPR coverage)
- Relevance: 0.62 (some keywords missed, incomplete requirement coverage)
- Tone: 0.65 (mostly professional with some inconsistency)

Final: 0.40*0.68 + 0.35*0.62 + 0.25*0.65 = 0.272 + 0.217 + 0.1625 = 0.6515
→ Rating: Acceptable (triggers optional Sonnet retry)
```

### B. FVS Validation Examples

**Example 1: CRITICAL Violation**
```
Request: company_name="Google", job_title="Senior Engineer"
Generated Letter: "I'm excited to apply to Alphabet for the role of Junior Developer"

FVS Result:
- Company name: "Alphabet" vs "Google" → CRITICAL (different company!)
- Job title: "Junior Developer" vs "Senior Engineer" → CRITICAL (different level!)
→ Action: REJECT, return FVS_HALLUCINATION_DETECTED error
```

**Example 2: Acceptable Match**
```
Request: company_name="TechCorp Inc", job_title="Senior Python Engineer"
Generated Letter: "Your company, TechCorp, excites me... the Senior Engineer role aligns..."

FVS Result:
- Company name: "TechCorp" ≈ "TechCorp Inc" → Fuzzy match (0.92) → PASS
- Job title: "Senior Engineer" matches "Senior Python Engineer" → PASS
→ Action: ACCEPT
```

### C. Cost Optimization Opportunities

| Opportunity | Impact | Implementation |
|-------------|--------|-----------------|
| Prompt compression | Save $0.0005/letter (13%) | Reduce CV text to highlights only |
| Response truncation | Save $0.00075/letter (20%) | Request shorter output for short letters |
| System prompt caching | Save $0.0003/letter (8%) | Cache system prompt across requests |
| Batch requests | Save $0.001/letter (13%) | Process multiple requests together |
| Haiku-only strategy | Save $0.0037/letter (49%) | Only use Sonnet for <5% failures |

---

**Document Version:** 1.0
**Last Updated:** 2026-02-05
**Next Review:** After Phase 10 implementation complete
**References:** CV_TAILORING_DESIGN.md, COVER_LETTER_SPEC.md, ARCHITECT_PROMPT.md
