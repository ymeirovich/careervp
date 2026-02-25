# CAREERVP AGENTIC ARCHITECTURE
## Job Search Assistant Skill → Production Platform Design

**Document Purpose:** Complete agentic architecture specification for replicating the Job Search Assistant Skill into CareerVP's AWS serverless platform  
**Target Platform:** AWS Lambda + DynamoDB + S3 + Step Functions  
**AI Provider:** Anthropic Claude (Sonnet 4.5 + Haiku 4.5)  
**Version:** 1.0  
**Date:** January 2026  

---

## TABLE OF CONTENTS

1. [Executive Summary](#1-executive-summary)
2. [Architecture Overview](#2-architecture-overview)
3. [Agent Specifications](#3-agent-specifications)
4. [Data Schemas](#4-data-schemas)
5. [Orchestration Logic](#5-orchestration-logic)
6. [Quality Assurance Framework](#6-quality-assurance-framework)
7. [Implementation Guide](#7-implementation-guide)
8. [Cost Model](#8-cost-model)

---

## 1. EXECUTIVE SUMMARY

### 1.1 Architecture Philosophy

The Job Search Assistant Skill operates as a **multi-agent system** where each agent:
- Has a **single, well-defined responsibility**
- Implements **self-correction and meta-review** mechanisms
- Follows **staged thinking processes** (not direct output)
- Maintains **transparent reasoning chains**
- Validates outputs against **explicit quality criteria**

### 1.2 Agent Topology

```
┌─────────────────────────────────────────────────────────────────┐
│                    ORCHESTRATOR LAMBDA                          │
│              (Coordinates all agents via Step Functions)        │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
        ┌─────────────────────────────────────────────┐
        │          CV PARSER AGENT                     │
        │          (Extract facts from CV)             │
        └─────────────────────────────────────────────┘
                              │
                              ▼
        ┌─────────────────────────────────────────────┐
        │     COMPANY RESEARCH AGENT                   │
        │     (Web scraping + Perplexity fallback)     │
        └─────────────────────────────────────────────┘
                              │
                              ▼
        ┌─────────────────────────────────────────────┐
        │     GAP ANALYSIS QUESTION AGENT              │
        │     (Generate targeted questions)            │
        └─────────────────────────────────────────────┘
                              │
                    ┌─────────┴─────────┐
                    │  USER RESPONDS    │
                    └─────────┬─────────┘
                              │
                              ▼
        ┌─────────────────────────────────────────────┐
        │     VALUE PROPOSITION AGENT (VPR)            │
        │     (6-stage strategic analysis)             │
        └─────────────────────────────────────────────┘
                              │
                    ┌─────────┴─────────┐
                    │                   │
                    ▼                   ▼
        ┌──────────────────┐  ┌──────────────────┐
        │  CV TAILOR AGENT │  │ COVER LETTER     │
        │  (3-step verify) │  │ AGENT (Scaffold) │
        └──────────────────┘  └──────────────────┘
                    │                   │
                    └─────────┬─────────┘
                              ▼
                  ┌───────────────────────┐
                  │ INTERVIEW PREP AGENT  │
                  │ (STAR responses)      │
                  └───────────────────────┘
                              │
                              ▼
                  ┌───────────────────────┐
                  │   QUALITY VALIDATOR   │
                  │   (Final checks)      │
                  └───────────────────────┘
```

### 1.3 Key Design Principles

1. **Iterative Thinking:** Agents use staged processes with internal critique
2. **Self-Correction:** Built-in meta-review before output
3. **Fact Grounding:** Zero hallucinations through evidence verification
4. **Strategic Alignment:** All outputs derive from VPR analysis
5. **Cost Optimization:** Haiku for template tasks, Sonnet for strategic work

---

## 2. ARCHITECTURE OVERVIEW

### 2.1 System Components

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Orchestrator** | AWS Step Functions + Lambda | Coordinate agent execution, manage state |
| **Agents** | AWS Lambda (Python 3.11) | Individual processing units |
| **AI Models** | Anthropic Claude API | Natural language processing |
| **State Store** | DynamoDB | Persist agent outputs, application state |
| **File Storage** | S3 | Store CVs, generated documents |
| **Cache Layer** | DynamoDB with TTL | Cache company research (30 days) |
| **Message Queue** | SQS (optional) | Async agent communication |
| **Monitoring** | CloudWatch | Logging, metrics, alerts |

### 2.2 Execution Flow

```yaml
Application Creation (User):
  ↓
Orchestrator Initiates:
  ↓
┌─ STAGE 1: CV Parsing ──────────────────────┐
│ Agent: cv-parser                            │
│ Model: Haiku 4.5                            │
│ Output: Structured CV facts JSON            │
└─────────────────────────────────────────────┘
  ↓
┌─ STAGE 2: Company Research ────────────────┐
│ Agent: company-research-v1                  │
│ Method: Web scraping → Perplexity fallback  │
│ Output: Company intelligence JSON           │
│ Cache: 30 days TTL                          │
└─────────────────────────────────────────────┘
  ↓
┌─ STAGE 3: Gap Analysis Questions ──────────┐
│ Agent: gap-analysis-question-generator      │
│ Model: Sonnet 4.5                           │
│ Process: Memory-aware, tagged questioning   │
│ Output: 10 questions max (CV_IMPACT tagged) │
└─────────────────────────────────────────────┘
  ↓
[WAIT FOR USER GAP RESPONSES]
  ↓
┌─ STAGE 4: Value Proposition Report ────────┐
│ Agent: vpr-strategist                       │
│ Model: Sonnet 4.5                           │
│ Process: 6-stage analysis with self-review  │
│ Output: Strategic VPR document              │
└─────────────────────────────────────────────┘
  ↓
┌─ STAGE 5: Parallel Artifact Generation ────┐
│ ┌─ CV Tailoring ────────────────────────┐  │
│ │ Agent: cv-tailor                      │  │
│ │ Model: Haiku 4.5                      │  │
│ │ Process: 3-step with verification     │  │
│ └───────────────────────────────────────┘  │
│                                             │
│ ┌─ Cover Letter ────────────────────────┐  │
│ │ Agent: cover-letter-writer            │  │
│ │ Model: Haiku 4.5                      │  │
│ │ Process: Reference class + scaffold   │  │
│ └───────────────────────────────────────┘  │
│                                             │
│ ┌─ Interview Prep ──────────────────────┐  │
│ │ Agent: interview-prep-generator       │  │
│ │ Model: Haiku 4.5                      │  │
│ │ Process: Tiered STAR responses        │  │
│ └───────────────────────────────────────┘  │
└─────────────────────────────────────────────┘
  ↓
┌─ STAGE 6: Quality Validation ──────────────┐
│ Agent: quality-validator                    │
│ Checks: ATS score, anti-AI detection, facts │
│ Output: Quality report + approval           │
└─────────────────────────────────────────────┘
  ↓
Application Complete (Notify User)
```

---

## 3. AGENT SPECIFICATIONS

### 3.1 AGENT: CV Parser

**Lambda Function:** `cv-parser`  
**Model:** Claude Haiku 4.5  
**Timeout:** 30s  
**Memory:** 512MB  

#### Responsibility
Extract structured facts from uploaded CV with zero hallucinations.

#### Input Schema
```json
{
  "cv_id": "string",
  "cv_text": "string",
  "user_email": "string"
}
```

#### Internal Process
```yaml
Step 1: Extract Raw Text
  - Parse PDF/DOCX to plain text
  - Preserve basic formatting (bullets, sections)

Step 2: AI Fact Extraction (Haiku)
  - Extract: name, contact, work experience, education, skills, certifications
  - Format dates as MM/YYYY
  - Quantify achievements where mentioned
  
Step 3: Verification
  - Verify email matches user account
  - Check date consistency
  - Flag ambiguous information

Step 4: Output
  - Store structured JSON in DynamoDB
  - Return parsed facts
```

#### Output Schema
```json
{
  "cv_id": "string",
  "personal_info": {
    "name": "string",
    "email": "string",
    "phone": "string",
    "linkedin": "string",
    "location": "string"
  },
  "work_experience": [
    {
      "company": "string",
      "title": "string",
      "start_date": "MM/YYYY",
      "end_date": "MM/YYYY",
      "location": "string",
      "responsibilities": ["string"],
      "achievements": [
        {
          "description": "string",
          "metrics": {
            "type": "percentage|dollar|time|scale",
            "value": "number"
          }
        }
      ]
    }
  ],
  "education": [...],
  "skills": {
    "technical": ["string"],
    "tools": ["string"],
    "soft": ["string"]
  },
  "certifications": [...],
  "parsing_confidence": "high|medium|low",
  "warnings": ["string"]
}
```

#### Prompt Template
```python
CV_PARSING_PROMPT = """Extract structured information from this CV.

CRITICAL RULES:
- Extract ONLY information explicitly stated
- Do NOT invent or infer details
- Format all dates as MM/YYYY
- Quantify achievements when numbers are mentioned
- Mark confidence level (high/medium/low)

CV TEXT:
{cv_text}

USER EMAIL (verify match):
{user_email}

OUTPUT: Return JSON matching the exact schema provided.
"""
```

---

### 3.2 AGENT: Company Research

**Lambda Function:** `company-research-v1`  
**Method:** Hybrid (Web Scraping → Perplexity API)  
**Timeout:** 45s  
**Memory:** 512MB  

#### Responsibility
Gather comprehensive company intelligence with caching.

#### Input Schema
```json
{
  "company_name": "string",
  "company_website": "string (optional)",
  "cache_check": "boolean (default: true)"
}
```

#### Internal Process
```yaml
Step 1: Cache Check
  - Query DynamoDB for existing research (< 30 days old)
  - If cached and fresh, return cached data
  - If stale, proceed to Step 2

Step 2: Web Scraping (Primary)
  - Scrape company website for:
    * About/Mission page
    * Products/Services
    * News/Blog (last 6 months)
    * Careers page (culture insights)
  - Use BeautifulSoup + Requests
  - Timeout: 20 seconds

Step 3: Data Sufficiency Check
  - Minimum 5 data points required
  - Must have: mission, products, industry
  - If insufficient, proceed to Step 4

Step 4: Perplexity Fallback
  - Query: "Provide overview of {company_name}: mission, products, 
    recent news (last 6 months), culture, company size, funding"
  - Model: sonar-small-online
  - Cost: ~$0.003

Step 5: Data Enrichment
  - Extract keywords for ATS optimization
  - Identify 3-5 strategic priorities
  - Tag company size/stage (startup, growth, enterprise)

Step 6: Cache Storage
  - Store in DynamoDB with 30-day TTL
  - Tag with company_name_normalized as PK
```

#### Output Schema
```json
{
  "company_name": "string",
  "research_date": "ISO 8601",
  "data_source": "web_scraping|perplexity|cached",
  "company_overview": "string (200-300 words)",
  "mission_vision": "string",
  "products_services": [
    {
      "name": "string",
      "description": "string"
    }
  ],
  "recent_news": [
    {
      "headline": "string",
      "date": "YYYY-MM",
      "source": "string",
      "summary": "string"
    }
  ],
  "culture_values": "string",
  "company_size": "startup|growth|enterprise",
  "industry": "string",
  "funding_stage": "string (if available)",
  "strategic_priorities": ["string"],
  "ats_keywords": ["string"],
  "source_urls": ["string"],
  "confidence_score": "number (0-1)"
}
```

#### Perplexity Prompt Template
```python
PERPLEXITY_RESEARCH_PROMPT = """Provide a comprehensive overview of {company_name}.

Include:
1. Mission and vision statement
2. Top 3-5 products or services
3. Recent news or announcements (last 6 months)
4. Company culture and values
5. Company size and industry
6. Funding stage or growth indicators
7. 3-5 current strategic priorities or challenges

Focus on factual, verifiable information. Cite sources where possible.
"""
```

---

### 3.3 AGENT: Gap Analysis Question Generator

**Lambda Function:** `gap-analysis-question-generator`  
**Model:** Claude Sonnet 4.5  
**Timeout:** 30s  
**Memory:** 512MB  

#### Responsibility
Generate contextually-tagged, memory-aware questions to gather evidence.

#### Input Schema
```json
{
  "application_id": "string",
  "cv_facts": "object",
  "job_requirements": "object",
  "company_research": "object",
  "user_email": "string",
  "previous_gap_responses": "array (from knowledge base)"
}
```

#### Internal Process
```yaml
Step 1: Load User Memory
  - Query knowledge base for recurring themes
  - Load previous gap responses to avoid duplication
  - Identify established strengths

Step 2: Cross-Reference Analysis
  - CV facts vs. job requirements
  - Identify critical gaps (missing metrics/evidence)
  - Focus on "Must-Have" requirements only

Step 3: Categorize by Destination
  - [CV IMPACT]: Quantifiable results, metrics, team sizes
  - [INTERVIEW/MVP ONLY]: Philosophy, process, soft skills

Step 4: Generate Questions (Max 10)
  - Enforce quantification for [CV IMPACT] questions
  - Skip topics from recurring themes
  - Include strategic intent for each question
  - Link to specific job requirements

Step 5: Self-Review
  - Check: Are questions too technical/in-the-weeds?
  - Ensure: Business impact focus, not implementation details
  - Validate: Each question has clear strategic purpose
```

#### Output Schema
```json
{
  "application_id": "string",
  "questions": [
    {
      "question_id": "gap_001",
      "requirement": "Exact quote from job posting",
      "question_text": "Detailed question emphasizing quantification",
      "destination": "CV_IMPACT|INTERVIEW_MVP_ONLY",
      "strategic_intent": "Why this matters and how it will be used",
      "evidence_gap": "What's missing from CV",
      "priority": "CRITICAL|IMPORTANT|OPTIONAL",
      "recurring_theme_check": "boolean"
    }
  ],
  "summary": {
    "total_questions": "number (max 10)",
    "cv_impact_questions": "number",
    "interview_only_questions": "number",
    "skipped_recurring_themes": ["string"],
    "critical_gaps_addressed": ["string"]
  }
}
```

#### Prompt Template
```python
GAP_ANALYSIS_PROMPT = """You are an expert career strategist generating targeted gap analysis questions.

CRITICAL INSTRUCTIONS:
1. Generate MAXIMUM 10 questions
2. Tag each: [CV IMPACT] or [INTERVIEW/MVP ONLY]
3. Include strategic intent for each
4. Skip recurring themes from user history
5. Emphasize quantification for [CV IMPACT]
6. Focus on CRITICAL job requirements only

INPUT DATA:

CV FACTS (USER'S ESTABLISHED STRENGTHS):
{cv_facts_json}

RECURRING THEMES (SKIP THESE):
{recurring_themes}

JOB REQUIREMENTS (CRITICAL ONLY):
{job_requirements_json}

COMPANY CONTEXT:
{company_research_json}

PREVIOUS GAP RESPONSES (DO NOT REPEAT):
{previous_gap_responses_json}

---

PROCESS:

STEP 1: CROSS-REFERENCE & MEMORY CHECK
- Identify gaps where CV lacks metrics/evidence
- Skip topics from recurring_themes
- Focus on "Must-Have" requirements

STEP 2: CATEGORIZE BY DESTINATION
- [CV IMPACT]: Quantifiable results
- [INTERVIEW/MVP ONLY]: Philosophy, soft skills

STEP 3: ENFORCE BREADTH OVER DEPTH
- Avoid technical weeds
- Focus on business impact

STEP 4: STRUCTURE QUESTIONS

### Question {N}

**Requirement:** [Exact quote from job]

**Question:** [Targeted question with quantification emphasis]

**Destination:** [CV IMPACT] or [INTERVIEW/MVP ONLY]

**Strategic Intent:** [Why asking, how used]

**Evidence Gap:** [What's missing from CV]

---

RULES:

[CV IMPACT] QUESTIONS (5-7):
- MUST ask for numbers: "How many?", "What percentage?"
- Focus on: team sizes, metrics, time saved, cost reduced

[INTERVIEW/MVP ONLY] QUESTIONS (3-5):
- Ask about: philosophy, approach, process, judgment
- Don't force metrics if inherently qualitative

OUTPUT: JSON array matching schema exactly.
"""
```

---

### 3.4 AGENT: Value Proposition Strategist (VPR)

**Lambda Function:** `vpr-strategist`  
**Model:** Claude Sonnet 4.5  
**Timeout:** 120s  
**Memory:** 1024MB  

#### Responsibility
Generate strategic value proposition report through 6-stage analytical process.

#### Input Schema
```json
{
  "application_id": "string",
  "cv_facts": "object",
  "gap_responses": "array",
  "job_requirements": "object",
  "company_research": "object",
  "previous_insights": "object (optional)"
}
```

#### Internal Process (6-STAGE METHODOLOGY)

```yaml
STAGE 1: COMPANY & ROLE RESEARCH
  - Analyze company research
  - Identify 3-5 strategic priorities/challenges
  - Extract 5-7 role success criteria from job posting
  - Output: Strategic priorities list + role criteria

STAGE 2: CANDIDATE ANALYSIS
  - Parse CV facts for achievements with metrics
  - Integrate gap responses as primary evidence
  - Identify 3-5 core differentiators
  - Summarize career narrative in ONE sentence
  - Output: Differentiators list + narrative

STAGE 3: ALIGNMENT MAPPING
  - Create reasoning scaffold table:
    | Company/Role Need | Candidate Evidence | Business Impact |
  - Map 5-7 alignments minimum
  - Use gap responses for quantified evidence
  - Output: Alignment matrix

STAGE 4: SELF-CORRECTION & META REVIEW
  - Check logical consistency
  - Identify unsupported claims
  - Ask: "Would this persuade senior hiring manager?"
  - Refine arguments for evidence strength
  - Output: Critique notes + refinements

STAGE 5: GENERATE REPORT
  - Executive Summary (200-250 words)
  - Evidence & Alignment Matrix (600-800 words)
  - Strategic Differentiators (300-400 words)
  - Gap Mitigation Strategies (200-300 words)
  - Cultural Fit Analysis (150-200 words)
  - Recommended Talking Points (150-200 words)
  - Apply anti-AI detection patterns
  - Output: Draft report

STAGE 6: FINAL META EVALUATION
  - Ask: "How could this be 20% more persuasive, specific, actionable?"
  - Apply improvements
  - Final verification against CV facts
  - Output: Final VPR document
```

#### Output Schema
```json
{
  "application_id": "string",
  "vpr_content": "string (markdown)",
  "extracted_metadata": {
    "uvp_statement": "string (core value proposition)",
    "strategic_differentiators": [
      {
        "differentiator": "string",
        "evidence": "string",
        "impact": "string"
      }
    ],
    "alignment_matrix": [
      {
        "company_need": "string",
        "candidate_evidence": "string",
        "business_impact": "string",
        "alignment_score": "STRONG|MODERATE|DEVELOPING"
      }
    ],
    "ats_keywords": ["string"],
    "talking_points": ["string"]
  },
  "quality_metrics": {
    "word_count": "number (1500-2000 target)",
    "fact_verification_passed": "boolean",
    "anti_ai_score": "number (0-100)",
    "alignment_count": "number (5-7 target)"
  },
  "stage_outputs": {
    "stage_1_priorities": ["string"],
    "stage_2_differentiators": ["string"],
    "stage_3_alignments": "array",
    "stage_4_critique": "string",
    "stage_6_improvements": "string"
  }
}
```

#### Prompt Template
```python
VPR_GENERATION_PROMPT = """You are an expert career strategist creating a Value Proposition Report.

Follow this 6-STAGE PROCESS exactly:

---

STAGE 1: COMPANY & ROLE RESEARCH

Analyze the company research and identify:
- 3-5 strategic priorities or current challenges
- 5-7 role success criteria from job posting

COMPANY RESEARCH:
{company_research_json}

JOB REQUIREMENTS:
{job_requirements_json}

OUTPUT (Internal): Strategic priorities list + role criteria

---

STAGE 2: CANDIDATE ANALYSIS

Parse CV facts and gap responses:
- Identify achievements with quantified outcomes
- Extract 3-5 core differentiators (what sets candidate apart)
- Summarize career narrative in ONE sentence

CV FACTS:
{cv_facts_json}

GAP ANALYSIS RESPONSES (PRIMARY EVIDENCE):
{gap_responses_json}

OUTPUT (Internal): Differentiators list + career narrative

---

STAGE 3: ALIGNMENT MAPPING

Create reasoning scaffold table with 5-7 minimum alignments:

| Company/Role Need | Candidate Evidence | Business Impact/Outcome |
|-------------------|-------------------|------------------------|
| [from Stage 1] | [from CV + gaps] | [value delivery] |

Use gap responses for quantified evidence.

OUTPUT (Internal): Complete alignment matrix

---

STAGE 4: SELF-CORRECTION & META REVIEW

Before proceeding, perform internal critique:
- Are there any unsupported claims?
- Is logic consistent throughout?
- Would this persuade a senior hiring manager?
- Are arguments evidence-driven and sharp?

Refine your analysis based on this critique.

OUTPUT (Internal): Critique notes + refinements applied

---

STAGE 5: GENERATE REPORT

Create structured report with these sections:

## 1. EXECUTIVE SUMMARY (200-250 words)
- Why candidate is exceptional fit
- 3-5 key differentiators with quantified evidence
- Strategic fit with company needs
- Forward-looking impact statement

## 2. EVIDENCE & ALIGNMENT MATRIX (600-800 words)

For each major job requirement:

### [Requirement Name]
**Evidence:** [Specific facts from CV + gap responses with quantification]
**Alignment:** STRONG|MODERATE|DEVELOPING
**Impact Potential:** [How experience translates to role success]

## 3. STRATEGIC DIFFERENTIATORS (300-400 words)
3-5 unique strengths with quantified examples from gap responses

## 4. GAP MITIGATION STRATEGIES (200-300 words)
- Acknowledge gaps honestly
- Highlight transferable skills
- Demonstrate learning agility

## 5. CULTURAL FIT ANALYSIS (150-200 words)
Based on company research

## 6. RECOMMENDED TALKING POINTS (150-200 words)
5-7 key messages for interviews

---

ANTI-AI DETECTION RULES:

BANNED WORDS: leverage, delve into, landscape, robust, streamline
WRITING STYLE:
- Vary sentence length (8-25 words)
- Natural transitions, not formulaic
- Conversational phrases
- Approximations not exact percentages
- Mix active/passive voice naturally

---

FACT VERIFICATION CHECKLIST:
Before including ANY fact:
- [ ] Explicitly stated in CV or gap responses?
- [ ] Numbers exact from source?
- [ ] Company name/title correct?
- [ ] Dates accurate?

If cannot verify, DO NOT INCLUDE.

---

STAGE 6: FINAL META EVALUATION

Ask yourself: "How could this report be 20% more persuasive, specific, or actionable?"

Apply those improvements and output the final refined version.

---

OUTPUT FORMAT: Professional markdown, 1,500-2,000 words.

Generate VPR now:
"""
```

---

### 3.5 AGENT: CV Tailor

**Lambda Function:** `cv-tailor`  
**Model:** Claude Haiku 4.5  
**Timeout:** 60s  
**Memory:** 512MB  

#### Responsibility
Generate tailored CV with 3-step verification process.

#### Input Schema
```json
{
  "application_id": "string",
  "cv_facts": "object",
  "job_requirements": "object",
  "vpr_differentiators": "array",
  "company_keywords": "array",
  "language": "string (en|he)"
}
```

#### Internal Process (3-STEP METHODOLOGY)

```yaml
STEP 1: ANALYSIS & KEYWORD MAPPING
  - Extract core UVP from VPR differentiators
  - Extract top 3 Key Differentiators from VPR
  - Analyze job posting: extract 12-18 key skills/technologies
  - Include company research keywords for ATS optimization
  - Draft CV with all bullets in CAR/STAR format
  - Output: Draft tailored CV

STEP 2: SELF-CORRECTION & VERIFICATION

  Verification Check 1 (ATS):
    - Rate keyword match score (1-10) against job posting
    - List 3 most critical missing/underrepresented keywords
    - If score < 7, revise to add missing keywords
  
  Verification Check 2 (Hiring Manager & Strategy):
    - Does Professional Summary align with UVP from VPR?
    - Does it address Company's Core Problem from job posting?
    - If not, rewrite summary for precise alignment

  Output: Verification results + revision plan

STEP 3: FINAL OUTPUT
  - Apply revisions based on verification checks
  - Ensure ATS score ≥ 8
  - Ensure strategic alignment with VPR
  - Output: Final tailored CV as structured JSON
```

#### Output Schema
```json
{
  "application_id": "string",
  "cv_content": {
    "contact_info": {...},
    "professional_summary": "string (2-3 sentences)",
    "work_experience": [
      {
        "company": "string",
        "title": "string",
        "dates": "MM/YYYY - MM/YYYY",
        "location": "string",
        "bullets": [
          "Action verb + quantified achievement + keywords"
        ]
      }
    ],
    "education": [...],
    "skills": {
      "technical": ["string"],
      "tools": ["string"]
    },
    "certifications": [...]
  },
  "verification_results": {
    "ats_score": "number (1-10)",
    "missing_keywords": ["string"],
    "strategic_alignment": "boolean",
    "revisions_applied": ["string"]
  },
  "metadata": {
    "language": "string",
    "length_pages": "number",
    "keyword_density": "number"
  }
}
```

#### Prompt Template
```python
CV_TAILORING_PROMPT = """You are an expert CV writer. Tailor this CV using a 3-STEP PROCESS.

---

INPUT DATA:

CV FACTS (SOURCE OF TRUTH):
{cv_facts_json}

JOB REQUIREMENTS:
{job_requirements_json}

VPR STRATEGIC DIFFERENTIATORS:
{vpr_differentiators}

COMPANY RESEARCH KEYWORDS:
{company_keywords}

LANGUAGE: {language}

---

STEP 1: ANALYSIS & KEYWORD MAPPING

- Extract core UVP and top 3 Key Differentiators from VPR
- Analyze job posting: extract 12-18 key skills/technologies/responsibilities
- Include company research keywords for ATS optimization
- Review CV facts: Include ONLY experience/skills directly relevant to keywords AND supporting the 3 Differentiators
- Draft CV with all bullets in CAR (Challenge-Action-Result) or STAR format:
  * Begin with strong action verb
  * Include quantifiable metric (number, percentage, scale)
  * If unquantifiable, highlight process improvement or technical expertise

OUTPUT (Internal): Draft tailored CV

---

STEP 2: SELF-CORRECTION & VERIFICATION

**Verification Check 1 (ATS):**
- Rate keyword match score (1-10) against job posting
- List 3 most critical missing/underrepresented keywords
- If score < 7, plan revisions to add keywords

**Verification Check 2 (Hiring Manager & Strategy):**
- Does Professional Summary directly align with UVP from VPR?
- Does it address Company's Core Problem implied by job posting?
- If not, plan summary rewrite for precise alignment

OUTPUT (Internal): Verification results + revision plan

---

STEP 3: FINAL OUTPUT

Apply revisions based on verification checks:
- Add missing keywords naturally
- Rewrite summary if needed
- Ensure ATS score ≥ 8
- Ensure strategic alignment with VPR

---

ATS FORMATTING RULES:
- Standard headers: "Professional Experience", "Education", "Skills"
- Simple bullets (•)
- No tables or columns
- Standard fonts only
- Length: 1-2 pages (max 3 pages)

CRITICAL: Use ONLY facts from CV. Zero hallucinations.

OUTPUT: JSON matching exact schema provided.

Generate tailored CV now:
"""
```

---

### 3.6 AGENT: Cover Letter Writer

**Lambda Function:** `cover-letter-writer`  
**Model:** Claude Haiku 4.5  
**Timeout:** 60s  
**Memory:** 512MB  

#### Responsibility
Generate persuasive cover letter with reference class priming and scaffolded proof points.

#### Input Schema
```json
{
  "application_id": "string",
  "cv_facts": "object",
  "job_title": "string",
  "company_name": "string",
  "key_requirements": "array",
  "vpr_differentiators": "array",
  "company_culture": "string",
  "language": "string (en|he)"
}
```

#### Internal Process

```yaml
STEP 1: REFERENCE CLASS PRIMING
  - Internally describe structure and tone of exemplary cover letter
  - Focus on: value over interest, strategic claims, persuasive
  - Set mental model for quality output

STEP 2: EXTRACT UVP AND PROOF POINTS
  - Extract core UVP from VPR differentiators
  - Identify top 3 non-negotiable job requirements
  - Map each requirement to CV fact + VPR claim

STEP 3: DRAFT LETTER

  Paragraph 1 (Hook - 80-100 words):
    - State role + company name
    - IMMEDIATELY reference UVP from VPR
    - Show research: specific company goal/product/announcement
    - Link candidate's background to that goal
  
  Paragraph 2 (Proof Points - 120-140 words):
    For EACH of top 3 requirements:
      - Sentence 1: Assert skill using VPR language/claims
      - Sentence 2: Detail quantified achievement from CV as proof
    Format: Req 1 Claim + Proof. Req 2 Claim + Proof. Req 3 Claim + Proof.
  
  Paragraph 3 (Close - 60-80 words):
    - Express enthusiasm
    - Clear, confident call to action
    - Position as time-saver (reference UVP)

STEP 4: ANTI-AI DETECTION CHECK
  - Verify natural transitions
  - Check sentence length variety
  - Remove banned words
  - Ensure conversational tone
```

#### Output Schema
```json
{
  "application_id": "string",
  "cover_letter_content": "string (markdown, max 400 words)",
  "metadata": {
    "word_count": "number (≤ 400)",
    "language": "string",
    "anti_ai_score": "number (0-100)",
    "proof_points_count": "number (3 expected)"
  },
  "extraction": {
    "uvp_used": "string",
    "requirements_addressed": ["string"],
    "company_research_reference": "string"
  }
}
```

#### Prompt Template
```python
COVER_LETTER_PROMPT = """You are an expert cover letter writer. Create EXACTLY 1 page (max 400 words).

---

STEP 1: REFERENCE CLASS PRIMING

Before drafting, internally describe the structure and tone of an exemplary, modern, persuasive cover letter for a competitive job market that:
- Focuses on VALUE candidate provides to company (not what candidate wants)
- Leverages strategic claims from Value Proposition Report
- Uses concrete proof points, not generic interest statements

---

INPUT DATA:

CV FACTS:
{cv_facts_json}

JOB INFO:
- Title: {job_title}
- Company: {company_name}
- Top 3 Requirements: {key_requirements}

VPR DIFFERENTIATORS (EXTRACT UVP):
{vpr_differentiators}

COMPANY CULTURE/RESEARCH:
{company_culture}

LANGUAGE: {language}

---

STEP 2: DRAFT LETTER

**Paragraph 1 (The Hook) - 80-100 words:**
- State role and IMMEDIATELY reference UVP from VPR
- Show research: mention specific company goal, product, or recent announcement
- Link candidate's background to that goal

**Paragraph 2 (The Proof Points) - 120-140 words:**

Identify top 3 non-negotiable requirements from job posting.
For EACH requirement:
- Sentence 1: Assert candidate's skill using VPR language/claims
- Sentence 2: Detail specific quantified achievement from CV as proof

Format: Requirement 1 Claim + Proof. Requirement 2 Claim + Proof. Requirement 3 Claim + Proof.

**Paragraph 3 (The Close) - 60-80 words:**
- Express enthusiasm
- Clear, confident call to action
- Position candidate as time-saver (e.g., "I look forward to discussing how my experience in [Key Skill from UVP] can immediately reduce your team's ramp-up time.")

---

TONE REQUIREMENTS:
- Professional and highly confident
- Focused entirely on value candidate provides to company
- NOT what candidate hopes to gain

ANTI-AI DETECTION:
- Natural transitions (not formulaic)
- Vary sentence length (8-25 words)
- Brief personal touch
- Avoid: leverage, delve, robust, streamline
- Use approximations: "nearly 40%" not "39.7%"

WORD COUNT: MUST stay under 400 words. Count as you write.

CRITICAL: Use ONLY facts from CV. Zero hallucinations.

OUTPUT: Clean markdown, 3 paragraphs, no lists or bullets.

Generate cover letter now:
"""
```

---

### 3.7 AGENT: Interview Prep Generator

**Lambda Function:** `interview-prep-generator`  
**Model:** Claude Haiku 4.5  
**Timeout:** 60s  
**Memory:** 512MB  

#### Responsibility
Generate comprehensive interview guide with predicted questions and STAR-formatted responses.

#### Input Schema
```json
{
  "application_id": "string",
  "cv_facts": "object",
  "job_requirements": "object",
  "vpr_differentiators": "array",
  "gap_responses": "object",
  "company_research": "object",
  "language": "string (en|he)"
}
```

#### Internal Process

```yaml
Step 1: Question Prediction
  - Analyze job requirements for technical questions
  - Generate behavioral questions (STAR format)
  - Create company-specific questions from research
  - Identify gap-related questions
  - Total: 10-15 questions across categories

Step 2: Categorize Questions
  - Technical (4-5 questions)
  - Behavioral (4-5 questions)
  - Company-Specific (2-3 questions)
  - Gap Questions (2-3 questions)

Step 3: Generate STAR Responses
  For each question:
    - Situation: Brief context (2-3 sentences)
    - Task: Responsibility (1-2 sentences)
    - Action: Specific steps (3-4 bullets)
    - Result: Quantified outcome (2-3 sentences with metrics)
  Use CV facts + gap responses for evidence

Step 4: Additional Sections
  - Questions to ask interviewer (5-7)
  - Salary negotiation guidance
  - Pre-interview checklist
```

#### Output Schema
```json
{
  "application_id": "string",
  "interview_prep_content": "string (markdown)",
  "predicted_questions": [
    {
      "question_id": "string",
      "question": "string",
      "category": "TECHNICAL|BEHAVIORAL|COMPANY|GAP",
      "star_response": {
        "situation": "string",
        "task": "string",
        "action": ["string"],
        "result": "string"
      },
      "key_points": ["string"]
    }
  ],
  "questions_for_interviewer": ["string"],
  "metadata": {
    "total_questions": "number (10-15)",
    "language": "string",
    "default_format": "DOCX"
  }
}
```

#### Prompt Template
```python
INTERVIEW_PREP_PROMPT = """You are an interview preparation expert. Generate comprehensive guide with predicted questions and STAR responses.

INPUT:

CV FACTS:
{cv_facts_json}

JOB REQUIREMENTS:
{job_requirements_json}

VPR STRATEGIC DIFFERENTIATORS:
{vpr_differentiators}

GAP ANALYSIS RESPONSES:
{gap_responses_json}

COMPANY RESEARCH:
{company_research_json}

LANGUAGE: {language}

---

OUTPUT STRUCTURE:

## PREDICTED INTERVIEW QUESTIONS (10-15 total)

### Technical Questions (4-5)
Based on job requirements

### Behavioral Questions (4-5)
STAR method required

### Company-Specific Questions (2-3)
Based on company research

### Gap Questions (2-3)
Address potential weaknesses

---

FOR EACH QUESTION:

**Q: [Question]**

**STAR Response:**
- **Situation:** Brief context (2-3 sentences)
- **Task:** Your responsibility (1-2 sentences)
- **Action:** Specific steps (3-4 bullet points)
- **Result:** Quantified outcome (2-3 sentences with metrics)

**Key Points to Emphasize:**
- Specific metric or achievement
- Relevant skill demonstrated
- Transferable learning

---

## QUESTIONS TO ASK INTERVIEWER (5-7)

Categories:
- Role-specific questions
- Team dynamics
- Company growth/direction
- Technical environment
- Success metrics

## SALARY NEGOTIATION GUIDANCE

Based on role and experience

## PRE-INTERVIEW CHECKLIST

- Research recap
- Key achievements to mention
- Questions prepared
- Technical setup (if virtual)

CRITICAL: Use ONLY facts from CV and gap responses. Zero hallucinations.

Generate interview prep now:
"""
```

---

### 3.8 AGENT: Quality Validator

**Lambda Function:** `quality-validator`  
**Model:** N/A (Rule-based + Light AI)  
**Timeout:** 30s  
**Memory:** 256MB  

#### Responsibility
Final quality assurance across all artifacts before delivery.

#### Input Schema
```json
{
  "application_id": "string",
  "vpr_content": "string",
  "cv_content": "object",
  "cover_letter_content": "string",
  "interview_prep_content": "string",
  "cv_facts": "object"
}
```

#### Validation Checks

```yaml
Check 1: Fact Verification
  - Scan all artifacts for numeric claims
  - Cross-reference against cv_facts and gap_responses
  - Flag: Any number not in source data
  - Result: PASS/FAIL with flagged items

Check 2: ATS Compatibility
  - Run CV through ATS checker
  - Keyword match score against job requirements
  - Formatting compliance
  - Result: Score (0-100), issues list

Check 3: Anti-AI Detection
  - Scan for banned words
  - Check sentence length variety
  - Detect formulaic patterns
  - Result: Score (0-100), issues list

Check 4: Cross-Document Consistency
  - Verify UVP consistent across all artifacts
  - Check differentiators align
  - Ensure no contradictions
  - Result: PASS/FAIL with inconsistencies

Check 5: Completeness
  - VPR: 1,500-2,000 words
  - CV: 1-2 pages
  - Cover Letter: ≤ 400 words
  - Interview Prep: 10-15 questions
  - Result: PASS/FAIL with gaps

Check 6: Language Quality
  - Spelling/grammar check
  - Professional tone verification
  - Natural language flow
  - Result: Score (0-100), issues list
```

#### Output Schema
```json
{
  "application_id": "string",
  "overall_quality": "EXCELLENT|GOOD|NEEDS_IMPROVEMENT|FAILED",
  "quality_score": "number (0-100)",
  "checks": [
    {
      "check_name": "string",
      "status": "PASS|FAIL|WARNING",
      "score": "number (0-100)",
      "issues": ["string"],
      "recommendations": ["string"]
    }
  ],
  "approval": "boolean",
  "regeneration_required": "boolean",
  "flagged_artifacts": ["string"]
}
```

---

## 4. DATA SCHEMAS

### 4.1 DynamoDB Table Schemas

#### Table: `careervp-applications`

```python
{
  "userId": "string",  # PK
  "applicationId": "string",  # SK
  "job_title": "string",
  "company_name": "string",
  "company_website": "string",
  "job_description": "string",
  "job_posting_url": "string",
  "cv_id": "string",
  "status": "string",  # PENDING|PROCESSING|PENDING_GAP_RESPONSES|COMPLETED|FAILED
  "stage": "string",  # Current processing stage
  "language": "string",
  "created_at": "string",
  "updated_at": "string",
  
  # Agent outputs
  "cv_facts": "object",
  "company_research": "object",
  "gap_questions": "array",
  "gap_responses": "array",
  "vpr_metadata": "object",
  "artifacts": {
    "vpr": {
      "s3_key": "string",
      "version": "number",
      "status": "DRAFT|FINAL"
    },
    "cv": {...},
    "cover_letter": {...},
    "interview_prep": {...}
  },
  
  # Cost tracking
  "cost_breakdown": "object",
  "total_cost": "number"
}
```

#### Table: `careervp-knowledge-base`

```python
{
  "userEmail": "string",  # PK
  "knowledgeType": "string",  # SK (recurring_themes|gap_responses|differentiators)
  "data": "object",
  "created_at": "string",
  "updated_at": "string",
  "applications_count": "number"  # How many times this knowledge was used
}
```

### 4.2 S3 Storage Structure

```
careervp-artifacts-prod/
├── {userId}/
│   ├── applications/
│   │   ├── {applicationId}/
│   │   │   ├── vpr_v1.md
│   │   │   ├── vpr_v1.docx
│   │   │   ├── cv_en_v1.json
│   │   │   ├── cv_en_v1.docx
│   │   │   ├── cv_en_v1.pdf
│   │   │   ├── cv_he_v1.docx (if multi-language)
│   │   │   ├── cover_letter_en_v1.md
│   │   │   ├── cover_letter_en_v1.docx
│   │   │   ├── interview_prep_v1.md
│   │   │   └── interview_prep_v1.docx
```

---

## 5. ORCHESTRATION LOGIC

### 5.1 AWS Step Functions State Machine

```json
{
  "Comment": "CareerVP Application Processing Workflow",
  "StartAt": "ParseCV",
  "States": {
    "ParseCV": {
      "Type": "Task",
      "Resource": "arn:aws:lambda:region:account:function:cv-parser",
      "Next": "CompanyResearch",
      "Catch": [
        {
          "ErrorEquals": ["States.ALL"],
          "Next": "HandleError"
        }
      ]
    },
    "CompanyResearch": {
      "Type": "Task",
      "Resource": "arn:aws:lambda:region:account:function:company-research-v1",
      "Next": "GenerateGapQuestions"
    },
    "GenerateGapQuestions": {
      "Type": "Task",
      "Resource": "arn:aws:lambda:region:account:function:gap-analysis-question-generator",
      "Next": "WaitForGapResponses"
    },
    "WaitForGapResponses": {
      "Type": "Task",
      "Resource": "arn:aws:states:::lambda:invoke.waitForTaskToken",
      "Parameters": {
        "FunctionName": "notify-user-gap-questions",
        "Payload": {
          "applicationId.$": "$.applicationId",
          "taskToken.$": "$$.Task.Token"
        }
      },
      "Next": "GenerateVPR"
    },
    "GenerateVPR": {
      "Type": "Task",
      "Resource": "arn:aws:lambda:region:account:function:vpr-strategist",
      "Next": "ParallelArtifactGeneration"
    },
    "ParallelArtifactGeneration": {
      "Type": "Parallel",
      "Branches": [
        {
          "StartAt": "TailorCV",
          "States": {
            "TailorCV": {
              "Type": "Task",
              "Resource": "arn:aws:lambda:region:account:function:cv-tailor",
              "End": true
            }
          }
        },
        {
          "StartAt": "GenerateCoverLetter",
          "States": {
            "GenerateCoverLetter": {
              "Type": "Task",
              "Resource": "arn:aws:lambda:region:account:function:cover-letter-writer",
              "End": true
            }
          }
        },
        {
          "StartAt": "GenerateInterviewPrep",
          "States": {
            "GenerateInterviewPrep": {
              "Type": "Task",
              "Resource": "arn:aws:lambda:region:account:function:interview-prep-generator",
              "End": true
            }
          }
        }
      ],
      "Next": "ValidateQuality"
    },
    "ValidateQuality": {
      "Type": "Task",
      "Resource": "arn:aws:lambda:region:account:function:quality-validator",
      "Next": "CheckQualityScore"
    },
    "CheckQualityScore": {
      "Type": "Choice",
      "Choices": [
        {
          "Variable": "$.quality_score",
          "NumericGreaterThanEquals": 80,
          "Next": "ExportArtifacts"
        },
        {
          "Variable": "$.quality_score",
          "NumericLessThan": 80,
          "Next": "FlagForReview"
        }
      ],
      "Default": "ExportArtifacts"
    },
    "ExportArtifacts": {
      "Type": "Task",
      "Resource": "arn:aws:lambda:region:account:function:artifact-exporter",
      "Next": "NotifyCompletion"
    },
    "FlagForReview": {
      "Type": "Task",
      "Resource": "arn:aws:lambda:region:account:function:flag-for-review",
      "Next": "NotifyCompletion"
    },
    "NotifyCompletion": {
      "Type": "Task",
      "Resource": "arn:aws:lambda:region:account:function:send-completion-email",
      "End": true
    },
    "HandleError": {
      "Type": "Task",
      "Resource": "arn:aws:lambda:region:account:function:handle-error",
      "End": true
    }
  }
}
```

### 5.2 Orchestrator Lambda (Simplified Alternative)

If not using Step Functions, use orchestrator Lambda:

```python
def orchestrate_application(application_id: str):
    """
    Main orchestrator coordinating all agents.
    """
    try:
        # Stage 1: Parse CV
        cv_facts = invoke_agent('cv-parser', {
            'cv_id': app['cv_id'],
            'cv_text': app['cv_text'],
            'user_email': app['user_email']
        })
        update_application(application_id, cv_facts=cv_facts)
        
        # Stage 2: Company Research
        company_research = invoke_agent('company-research-v1', {
            'company_name': app['company_name'],
            'company_website': app['company_website']
        })
        update_application(application_id, company_research=company_research)
        
        # Stage 3: Gap Questions
        gap_questions = invoke_agent('gap-analysis-question-generator', {
            'application_id': application_id,
            'cv_facts': cv_facts,
            'job_requirements': app['job_requirements'],
            'company_research': company_research,
            'user_email': app['user_email']
        })
        update_application(application_id, 
                          gap_questions=gap_questions,
                          status='PENDING_GAP_RESPONSES')
        
        # WAIT FOR USER GAP RESPONSES (async)
        # User fills gap responses via UI
        # Continuation triggered by webhook/event
        
        return {'status': 'PENDING_GAP_RESPONSES'}
        
    except Exception as e:
        handle_error(application_id, e)
        raise

def continue_after_gap_responses(application_id: str):
    """
    Continue orchestration after user provides gap responses.
    """
    app = load_application(application_id)
    gap_responses = app['gap_responses']
    
    try:
        # Stage 4: Generate VPR
        vpr = invoke_agent('vpr-strategist', {
            'application_id': application_id,
            'cv_facts': app['cv_facts'],
            'gap_responses': gap_responses,
            'job_requirements': app['job_requirements'],
            'company_research': app['company_research']
        })
        update_application(application_id, vpr_metadata=vpr['extracted_metadata'])
        
        # Extract company keywords for CV tailoring
        company_keywords = extract_keywords(app['company_research'])
        
        # Stage 5: Parallel Artifact Generation
        # Use Lambda async invocation for parallel execution
        
        cv_future = invoke_agent_async('cv-tailor', {
            'application_id': application_id,
            'cv_facts': app['cv_facts'],
            'job_requirements': app['job_requirements'],
            'vpr_differentiators': vpr['extracted_metadata']['strategic_differentiators'],
            'company_keywords': company_keywords,
            'language': app['language']
        })
        
        cover_letter_future = invoke_agent_async('cover-letter-writer', {
            'application_id': application_id,
            'cv_facts': app['cv_facts'],
            'job_title': app['job_title'],
            'company_name': app['company_name'],
            'key_requirements': extract_top_requirements(app['job_requirements']),
            'vpr_differentiators': vpr['extracted_metadata']['strategic_differentiators'],
            'company_culture': app['company_research']['culture_values'],
            'language': app['language']
        })
        
        interview_prep_future = invoke_agent_async('interview-prep-generator', {
            'application_id': application_id,
            'cv_facts': app['cv_facts'],
            'job_requirements': app['job_requirements'],
            'vpr_differentiators': vpr['extracted_metadata']['strategic_differentiators'],
            'gap_responses': gap_responses,
            'company_research': app['company_research'],
            'language': app['language']
        })
        
        # Wait for all to complete
        cv_result = await_result(cv_future)
        cover_letter_result = await_result(cover_letter_future)
        interview_prep_result = await_result(interview_prep_future)
        
        # Stage 6: Quality Validation
        quality_report = invoke_agent('quality-validator', {
            'application_id': application_id,
            'vpr_content': vpr['vpr_content'],
            'cv_content': cv_result['cv_content'],
            'cover_letter_content': cover_letter_result['cover_letter_content'],
            'interview_prep_content': interview_prep_result['interview_prep_content'],
            'cv_facts': app['cv_facts']
        })
        
        if quality_report['approval']:
            # Export artifacts
            invoke_agent('artifact-exporter', {
                'application_id': application_id
            })
            
            # Send completion email
            send_completion_email(app['user_email'], application_id)
            
            update_application(application_id, status='COMPLETED')
        else:
            # Flag for manual review
            flag_for_review(application_id, quality_report)
            update_application(application_id, status='NEEDS_REVIEW')
        
    except Exception as e:
        handle_error(application_id, e)
        raise
```

---

## 6. QUALITY ASSURANCE FRAMEWORK

### 6.1 Self-Correction Mechanisms

Each agent implements internal self-correction:

```python
def agent_with_self_correction(prompt_template: str, inputs: dict, 
                               verification_fn: callable) -> dict:
    """
    Generic pattern for agents with self-correction.
    """
    # Stage 1: Initial generation
    initial_output = call_claude(prompt_template.format(**inputs))
    
    # Stage 2: Self-verification
    verification_result = verification_fn(initial_output, inputs)
    
    # Stage 3: Conditional regeneration
    if not verification_result['passed']:
        refinement_prompt = f"""
        Your initial output had these issues:
        {verification_result['issues']}
        
        Please refine your output to address these issues.
        
        Initial output:
        {initial_output}
        """
        
        refined_output = call_claude(refinement_prompt)
        final_output = refined_output
    else:
        final_output = initial_output
    
    return {
        'output': final_output,
        'verification': verification_result,
        'refinement_applied': not verification_result['passed']
    }
```

### 6.2 Multi-Agent Verification (Optional Premium Feature)

For critical artifacts (VPR, Interview Prep), implement 3-agent verification:

```python
def three_agent_verification(content: str, evidence: dict) -> dict:
    """
    Three-agent verification for zero hallucinations.
    
    Agent 1: Fact Checker
    Agent 2: Logic Validator
    Agent 3: Strategic Reviewer
    """
    # Agent 1: Extract all factual claims
    claims = extract_claims_agent(content)
    
    # Agent 2: Verify each claim against evidence
    verification_results = []
    for claim in claims:
        result = verify_claim_agent(claim, evidence)
        verification_results.append(result)
    
    # Agent 3: Strategic quality review
    strategic_review = strategic_review_agent(content, verification_results)
    
    # Aggregate results
    all_verified = all(r['verified'] for r in verification_results)
    quality_score = strategic_review['quality_score']
    
    if all_verified and quality_score >= 8:
        return {
            'approved': True,
            'quality_score': quality_score,
            'verification_results': verification_results
        }
    else:
        return {
            'approved': False,
            'quality_score': quality_score,
            'failed_claims': [r for r in verification_results if not r['verified']],
            'recommendations': strategic_review['recommendations']
        }
```

### 6.3 Quality Metrics Dashboard

Track quality metrics across all applications:

```python
quality_metrics = {
    'vpr': {
        'avg_word_count': 1750,
        'avg_alignment_count': 6,
        'avg_anti_ai_score': 92,
        'fact_verification_pass_rate': 98.5
    },
    'cv': {
        'avg_ats_score': 8.3,
        'avg_keyword_density': 12,
        'avg_length_pages': 1.5
    },
    'cover_letter': {
        'avg_word_count': 375,
        'avg_anti_ai_score': 94,
        'avg_proof_points': 3
    },
    'interview_prep': {
        'avg_questions_count': 12,
        'avg_star_completeness': 95
    }
}
```

---

## 7. IMPLEMENTATION GUIDE

### 7.1 Development Phases

#### Phase 1: Core Agents (Weeks 1-2)
- [ ] CV Parser Agent
- [ ] Company Research Agent
- [ ] Basic orchestrator
- [ ] Test with 10 sample applications

#### Phase 2: Strategic Analysis (Weeks 3-4)
- [ ] Gap Analysis Question Generator
- [ ] Value Proposition Strategist (6-stage)
- [ ] Knowledge base integration
- [ ] Test VPR quality metrics

#### Phase 3: Artifact Generation (Weeks 5-6)
- [ ] CV Tailor Agent (3-step verification)
- [ ] Cover Letter Writer (scaffolded)
- [ ] Interview Prep Generator
- [ ] Parallel execution optimization

#### Phase 4: Quality & Polish (Week 7)
- [ ] Quality Validator Agent
- [ ] ATS compatibility checker
- [ ] Anti-AI detection validator
- [ ] Export functionality

#### Phase 5: Production Ready (Week 8)
- [ ] Step Functions state machine
- [ ] Error handling & retries
- [ ] Cost monitoring
- [ ] Performance optimization
- [ ] Load testing

### 7.2 Lambda Function Template

```python
# template_agent.py

import json
import os
from typing import Dict, Any
import anthropic
from aws_lambda_powertools import Logger, Tracer, Metrics
from aws_lambda_powertools.metrics import MetricUnit

logger = Logger()
tracer = Tracer()
metrics = Metrics()

client = anthropic.Anthropic(api_key=os.environ['ANTHROPIC_API_KEY'])

@logger.inject_lambda_context
@tracer.capture_lambda_handler
@metrics.log_metrics(capture_cold_start_metric=True)
def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Agent Lambda function template.
    """
    try:
        # Extract input from event
        application_id = event['application_id']
        inputs = event['inputs']
        
        logger.info(f"Processing application {application_id}")
        
        # Stage 1: Prepare prompt
        prompt = AGENT_PROMPT_TEMPLATE.format(**inputs)
        
        # Stage 2: Call Claude
        with tracer.capture_method("claude_api_call"):
            response = client.messages.create(
                model=os.environ['MODEL_NAME'],  # sonnet-4.5 or haiku-4.5
                max_tokens=int(os.environ['MAX_TOKENS']),
                temperature=float(os.environ.get('TEMPERATURE', '0.7')),
                messages=[{"role": "user", "content": prompt}]
            )
        
        output = response.content[0].text
        
        # Stage 3: Parse output
        parsed_output = parse_output(output)
        
        # Stage 4: Verify quality
        verification = verify_output(parsed_output, inputs)
        
        # Stage 5: Self-correction if needed
        if not verification['passed']:
            logger.warning("Verification failed, applying refinement")
            output = apply_refinement(output, verification, inputs)
            parsed_output = parse_output(output)
        
        # Track metrics
        metrics.add_metric(
            name="AgentExecutionSuccess",
            unit=MetricUnit.Count,
            value=1
        )
        metrics.add_metric(
            name="TokensUsed",
            unit=MetricUnit.Count,
            value=response.usage.total_tokens
        )
        
        # Track cost
        cost = calculate_cost(response.usage.input_tokens, 
                            response.usage.output_tokens,
                            os.environ['MODEL_NAME'])
        
        logger.info(f"Agent completed. Cost: ${cost:.4f}")
        
        return {
            'statusCode': 200,
            'body': {
                'application_id': application_id,
                'output': parsed_output,
                'verification': verification,
                'cost': cost,
                'tokens_used': response.usage.total_tokens
            }
        }
        
    except Exception as e:
        logger.exception("Agent execution failed")
        metrics.add_metric(
            name="AgentExecutionFailure",
            unit=MetricUnit.Count,
            value=1
        )
        raise


def parse_output(output: str) -> Dict[str, Any]:
    """Parse agent output to structured format."""
    # Implementation specific to each agent
    pass


def verify_output(parsed_output: Dict[str, Any], 
                 inputs: Dict[str, Any]) -> Dict[str, Any]:
    """Verify output quality."""
    # Implementation specific to each agent
    pass


def apply_refinement(output: str, verification: Dict[str, Any],
                    inputs: Dict[str, Any]) -> str:
    """Apply self-correction refinement."""
    # Implementation specific to each agent
    pass


def calculate_cost(input_tokens: int, output_tokens: int, 
                  model: str) -> float:
    """Calculate API cost."""
    pricing = {
        'claude-sonnet-4-5': {'input': 0.003, 'output': 0.015},
        'claude-haiku-4-5': {'input': 0.0008, 'output': 0.004}
    }
    
    rate = pricing.get(model, pricing['claude-haiku-4-5'])
    cost = (input_tokens / 1000 * rate['input'] + 
            output_tokens / 1000 * rate['output'])
    return cost


# Agent-specific prompt template
AGENT_PROMPT_TEMPLATE = """
[Agent-specific prompt goes here]
"""
```

### 7.3 Infrastructure as Code (CloudFormation)

```yaml
# agents-stack.yaml

AWSTemplateFormatVersion: '2010-09-09'
Transform: AWS::Serverless-2016-10-31
Description: CareerVP Agentic System

Globals:
  Function:
    Runtime: python3.11
    Timeout: 60
    MemorySize: 512
    Environment:
      Variables:
        ANTHROPIC_API_KEY: !Ref AnthropicApiKey
        DYNAMODB_TABLE: !Ref ApplicationsTable

Resources:
  # DynamoDB Tables
  ApplicationsTable:
    Type: AWS::DynamoDB::Table
    Properties:
      TableName: careervp-applications
      BillingMode: PAY_PER_REQUEST
      AttributeDefinitions:
        - AttributeName: userId
          AttributeType: S
        - AttributeName: applicationId
          AttributeType: S
      KeySchema:
        - AttributeName: userId
          KeyType: HASH
        - AttributeName: applicationId
          KeyType: RANGE

  # Lambda Functions (Agents)
  CVParserAgent:
    Type: AWS::Serverless::Function
    Properties:
      FunctionName: cv-parser
      CodeUri: agents/cv_parser/
      Handler: lambda_function.lambda_handler
      MemorySize: 512
      Timeout: 30
      Environment:
        Variables:
          MODEL_NAME: claude-haiku-4-5-20251001
          MAX_TOKENS: 2000

  CompanyResearchAgent:
    Type: AWS::Serverless::Function
    Properties:
      FunctionName: company-research-v1
      CodeUri: agents/company_research/
      Handler: lambda_function.lambda_handler
      MemorySize: 512
      Timeout: 45
      Environment:
        Variables:
          PERPLEXITY_API_KEY: !Ref PerplexityApiKey

  GapAnalysisAgent:
    Type: AWS::Serverless::Function
    Properties:
      FunctionName: gap-analysis-question-generator
      CodeUri: agents/gap_analysis/
      Handler: lambda_function.lambda_handler
      MemorySize: 512
      Timeout: 30
      Environment:
        Variables:
          MODEL_NAME: claude-sonnet-4-5-20250929
          MAX_TOKENS: 3000

  VPRStrategistAgent:
    Type: AWS::Serverless::Function
    Properties:
      FunctionName: vpr-strategist
      CodeUri: agents/vpr_strategist/
      Handler: lambda_function.lambda_handler
      MemorySize: 1024
      Timeout: 120
      Environment:
        Variables:
          MODEL_NAME: claude-sonnet-4-5-20250929
          MAX_TOKENS: 4000

  CVTailorAgent:
    Type: AWS::Serverless::Function
    Properties:
      FunctionName: cv-tailor
      CodeUri: agents/cv_tailor/
      Handler: lambda_function.lambda_handler
      MemorySize: 512
      Timeout: 60
      Environment:
        Variables:
          MODEL_NAME: claude-haiku-4-5-20251001
          MAX_TOKENS: 2000

  CoverLetterAgent:
    Type: AWS::Serverless::Function
    Properties:
      FunctionName: cover-letter-writer
      CodeUri: agents/cover_letter/
      Handler: lambda_function.lambda_handler
      MemorySize: 512
      Timeout: 60
      Environment:
        Variables:
          MODEL_NAME: claude-haiku-4-5-20251001
          MAX_TOKENS: 1000

  InterviewPrepAgent:
    Type: AWS::Serverless::Function
    Properties:
      FunctionName: interview-prep-generator
      CodeUri: agents/interview_prep/
      Handler: lambda_function.lambda_handler
      MemorySize: 512
      Timeout: 60
      Environment:
        Variables:
          MODEL_NAME: claude-haiku-4-5-20251001
          MAX_TOKENS: 3000

  QualityValidatorAgent:
    Type: AWS::Serverless::Function
    Properties:
      FunctionName: quality-validator
      CodeUri: agents/quality_validator/
      Handler: lambda_function.lambda_handler
      MemorySize: 256
      Timeout: 30

  # Step Functions State Machine
  ApplicationWorkflow:
    Type: AWS::Serverless::StateMachine
    Properties:
      Name: careervp-application-workflow
      DefinitionUri: state-machine.json
      Role: !GetAtt StepFunctionsRole.Arn

  # IAM Roles
  StepFunctionsRole:
    Type: AWS::IAM::Role
    Properties:
      AssumeRolePolicyDocument:
        Version: '2012-10-17'
        Statement:
          - Effect: Allow
            Principal:
              Service: states.amazonaws.com
            Action: sts:AssumeRole
      ManagedPolicyArns:
        - arn:aws:iam::aws:policy/service-role/AWSLambdaRole

Outputs:
  StateMachineArn:
    Description: ARN of the Step Functions state machine
    Value: !Ref ApplicationWorkflow
```

---

## 8. COST MODEL

### 8.1 Per-Application Cost Breakdown

```yaml
Agent Costs (Anthropic Claude API):
  cv-parser:
    model: Haiku 4.5
    input_tokens: 2000
    output_tokens: 500
    cost: $0.0026
    
  company-research-v1:
    method: Perplexity fallback
    cost: $0.004
    
  gap-analysis-question-generator:
    model: Sonnet 4.5
    input_tokens: 8000
    output_tokens: 1000
    cost: $0.039
    
  vpr-strategist:
    model: Sonnet 4.5
    input_tokens: 10000
    output_tokens: 2500
    cost: $0.0675
    
  cv-tailor:
    model: Haiku 4.5
    input_tokens: 5000
    output_tokens: 1200
    cost: $0.0088
    
  cover-letter-writer:
    model: Haiku 4.5
    input_tokens: 4000
    output_tokens: 800
    cost: $0.0064
    
  interview-prep-generator:
    model: Haiku 4.5
    input_tokens: 5000
    output_tokens: 2000
    cost: $0.012

Total AI Cost: $0.1403 per application

Lambda Costs:
  orchestrator: $0.001
  agent executions: $0.002
  
Total Lambda: $0.003 per application

Total Per Application: $0.1433

Target: $0.058 (EXCEEDED)

Optimization Needed: Reduce Sonnet usage or optimize prompts
```

### 8.2 Cost Optimization Strategies

```yaml
Strategy 1: Prompt Compression
  - Reduce VPR input tokens from 10K to 7K
  - Savings: ~$0.009 per application

Strategy 2: Cached Company Research
  - Cache hit rate: 40% (same company applications)
  - Savings: $0.0016 per application (40% of $0.004)

Strategy 3: Reduce Gap Analysis Questions
  - Current: 10 questions max
  - Optimized: 7 questions max
  - Reduce Sonnet tokens by 30%
  - Savings: ~$0.012 per application

Strategy 4: Haiku for Simple VPR Sections
  - Use Haiku for Cultural Fit, Talking Points
  - Use Sonnet only for Alignment Matrix, Differentiators
  - Savings: ~$0.025 per application

Optimized Total: $0.087 per application
Still above target of $0.058

Strategy 5: Tiered Service
  - Basic: Skip VPR or use compressed version
  - Premium: Full VPR with all features
  - Allows hitting $0.058 target for basic tier
```

---

## APPENDIX A: PROMPT TEMPLATES REFERENCE

All complete prompt templates are provided in each agent specification section above.

---

## APPENDIX B: ERROR HANDLING PATTERNS

```python
class AgentError(Exception):
    """Base exception for agent errors."""
    pass

class VerificationFailedError(AgentError):
    """Output failed quality verification."""
    pass

class APIRateLimitError(AgentError):
    """Anthropic API rate limit exceeded."""
    pass

def handle_agent_error(application_id: str, error: Exception):
    """
    Centralized error handling for agents.
    """
    if isinstance(error, APIRateLimitError):
        # Retry with exponential backoff
        retry_with_backoff(application_id)
    
    elif isinstance(error, VerificationFailedError):
        # Flag for manual review
        flag_for_review(application_id, str(error))
    
    else:
        # Log and notify admin
        logger.error(f"Unhandled error: {error}")
        notify_admin(application_id, error)
    
    # Update application status
    update_application(application_id, 
                      status='FAILED',
                      error_message=str(error))
```

---

## APPENDIX C: TESTING STRATEGY

```yaml
Unit Tests:
  - Each agent's prompt formatting
  - Output parsing logic
  - Verification functions
  - Cost calculation
  
Integration Tests:
  - Agent to DynamoDB storage
  - Agent to S3 storage
  - Orchestrator coordination
  - Quality validator integration
  
End-to-End Tests:
  - Complete application workflow
  - Multi-language generation
  - Error recovery
  - Cost tracking accuracy
  
Load Tests:
  - 100 concurrent applications
  - API rate limit handling
  - Database throughput
  - Lambda cold start optimization
```

---

**DOCUMENT STATUS:** ✅ PRODUCTION READY  
**LAST UPDATED:** January 2026  
**VERSION:** 1.0  
**NEXT REVIEW:** March 2026  

---

**END OF AGENTIC ARCHITECTURE SPECIFICATION**
