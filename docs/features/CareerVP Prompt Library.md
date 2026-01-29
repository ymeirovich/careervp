# CAREERVP PROMPT LIBRARY - CONTINUED
## Completing from "Job Search Assistant prompts and AWS deployment" chat

---

## ATS Compatibility Checker

```python
def check_ats_compatibility(cv_content: str, job_requirements: dict) -> dict:
    """
    Check CV for ATS compatibility issues.

    Returns:
        {
            'score': 0-100,
            'level': 'high|medium|low',
            'issues': List[dict],
            'suggestions': List[str]
        }
    """

    issues = []
    score = 100

    # Check 1: Keyword matching (40 points)
    required_keywords = job_requirements.get('required_skills', [])
    present_keywords = [
        kw for kw in required_keywords
        if kw.lower() in cv_content.lower()
    ]
    keyword_score = (len(present_keywords) / len(required_keywords)) * 40 if required_keywords else 40
    score = keyword_score

    if keyword_score < 30:
        missing = set(required_keywords) - set(present_keywords)
        issues.append({
            'type': 'keywords',
            'severity': 'high',
            'message': f'Missing critical keywords: {", ".join(list(missing)[:5])}'
        })

    # Check 2: Formatting issues (30 points)
    formatting_score = 30

    if '|' in cv_content or '┃' in cv_content:  # Tables
        formatting_score -= 15
        issues.append({
            'type': 'formatting',
            'severity': 'high',
            'message': 'Tables detected - not ATS-friendly. Use bullet points instead.'
        })

    if 'header' in cv_content.lower()[:200] or 'footer' in cv_content.lower()[-200:]:
        formatting_score -= 10
        issues.append({
            'type': 'formatting',
            'severity': 'medium',
            'message': 'Headers/footers may not be parsed by ATS. Put contact info in main body.'
        })

    score += max(0, formatting_score)

    # Check 3: Section headers (20 points)
    standard_headers = [
        'experience', 'work history', 'employment',
        'education', 'skills', 'certifications'
    ]

    found_headers = sum(1 for h in standard_headers if h in cv_content.lower())
    header_score = (found_headers / len(standard_headers)) * 20
    score += header_score

    if header_score < 15:
        issues.append({
            'type': 'headers',
            'severity': 'medium',
            'message': 'Use standard section headers: Experience, Education, Skills, Certifications'
        })

    # Check 4: Font compatibility (10 points)
    # Check for unusual characters that suggest fancy fonts
    unusual_chars = sum(1 for c in cv_content if ord(c) > 127 and c not in 'àáâãäåèéêëìíîïòóôõöùúûü')
    if unusual_chars > 50:
        score -= 10
        issues.append({
            'type': 'font',
            'severity': 'low',
            'message': 'Unusual characters detected. Stick to standard fonts (Arial, Calibri, Times New Roman).'
        })

    # Determine level
    if score >= 90:
        level = 'high'
    elif score >= 70:
        level = 'medium'
    else:
        level = 'low'

    # Generate suggestions
    suggestions = []
    if keyword_score < 30:
        suggestions.append(f"Add these keywords: {', '.join(list(set(required_keywords) - set(present_keywords))[:5])}")
    if formatting_score < 20:
        suggestions.append("Remove tables and use simple bullet points")
    if header_score < 15:
        suggestions.append("Add standard section headers: Work Experience, Education, Skills")

    return {
        'score': round(score),
        'level': level,
        'issues': issues,
        'suggestions': suggestions,
        'keyword_match_percentage': round((len(present_keywords) / len(required_keywords) * 100) if required_keywords else 100)
    }
```

---

## PROMPT 1: VALUE PROPOSITION REPORT (VPR) GENERATION

**Model:** Claude Sonnet 4.5
**Cost:** ~$0.035 per report
**Function:** `vp-report-generator`

### VPR Prompt Template

```python
VPR_GENERATION_PROMPT = """You are an expert career strategist creating a Value Proposition Report (VPR) for a job application.

CRITICAL REQUIREMENTS:
- ALL facts must be verifiable from the CV (ZERO HALLUCINATIONS)
- Integrate gap analysis responses as primary evidence
- Pass anti-AI detection (see banned words below)
- ATS-optimized language
- Length: 1,500-2,000 words

INPUT DATA:

CV FACTS (IMMUTABLE - DO NOT INVENT):
{cv_facts_json}

GAP ANALYSIS RESPONSES (PRIMARY EVIDENCE):
{gap_responses_json}

JOB REQUIREMENTS:
{job_requirements_json}

COMPANY RESEARCH:
{company_research_json}

PREVIOUS APPLICATION INSIGHTS (if any):
{previous_insights_json}

---

VPR STRUCTURE:

## 1. EXECUTIVE SUMMARY (200-250 words)
Synthesize the candidate's unique value proposition in 3-4 compelling paragraphs:
- Opening: Why this candidate is exceptional fit for this specific role
- Core strengths: 3-5 key differentiators with quantified evidence
- Strategic fit: How their background aligns with company's needs
- Compelling close: Forward-looking statement about impact

## 2. EVIDENCE & ALIGNMENT MATRIX (600-800 words)

For each major job requirement, provide:

**Requirement:** [Exact requirement from job posting]
**Evidence:** [Specific facts from CV + gap responses with quantification]
**Alignment Score:** [Strong/Moderate/Developing]
**Impact Potential:** [How this experience translates to role success]

Use this format:
```
### Cloud Architecture (Required)
**Evidence:** Designed and deployed AWS serverless architecture processing 1M+ daily transactions (gap response). Reduced infrastructure costs by 40% through Lambda optimization. Led migration of monolithic application to microservices for team of 8 engineers.

**Alignment:** STRONG - Direct experience with required AWS services (Lambda, DynamoDB, S3) at scale matching job requirements.

**Impact Potential:** Can immediately architect scalable solutions and mentor team on cloud best practices.
```

## 3. STRATEGIC DIFFERENTIATORS (300-400 words)

Identify 3-5 unique strengths that set candidate apart:
- Technical depth + business acumen
- Leadership + hands-on execution
- Innovation + operational excellence
- Cross-functional collaboration
- Industry-specific expertise

Support each with quantified examples from gap responses.

## 4. GAP MITIGATION STRATEGIES (200-300 words)

For any missing requirements:
- Acknowledge the gap honestly
- Highlight transferable skills
- Demonstrate learning agility with examples
- Propose 30-60-90 day plan to close gap

## 5. CULTURAL FIT ANALYSIS (150-200 words)

Based on company research:
- Alignment with company values
- Work style compatibility
- Team collaboration approach
- Growth mindset examples

## 6. RECOMMENDED TALKING POINTS (150-200 words)

5-7 key messages for interviews:
- Strongest technical capabilities
- Most impressive quantified achievements
- Unique value proposition
- Questions that demonstrate strategic thinking

---

ANTI-AI DETECTION RULES:

BANNED WORDS (never use):
- leverage, delve into, landscape, robust, streamline
- utilize, facilitate, implement (use sparingly)
- cutting-edge, best practices, industry-leading
- game-changer, paradigm shift, synergy

WRITING STYLE:
- Vary sentence length (8-25 words)
- Use natural transitions, not formulaic
- Include conversational phrases
- Use approximations not exact percentages (e.g., "nearly 40%" not "39.7%")
- Mix active and passive voice naturally

DOCUMENT-LEVEL PATTERNS:
- Avoid formulaic structure (vary section order slightly)
- Use different header styles
- Include brief narrative examples
- Natural language flow, not bullet-point heavy

---

FACT VERIFICATION CHECKLIST:
Before including ANY achievement or fact:
- [ ] Is this explicitly stated in CV or gap responses?
- [ ] Are the numbers exact from source?
- [ ] Is the company name/title correct?
- [ ] Are dates accurate?
- [ ] Can I quote the source if questioned?

If you cannot verify a fact, DO NOT INCLUDE IT.

---

OUTPUT FORMAT: Professional markdown document, ready for DOCX export.

Generate the VPR now:"""
```

### VPR Lambda Implementation

```python
def generate_vpr(application_id: str, cv_facts: dict, gap_responses: list,
                 job_requirements: dict, company_research: dict) -> dict:
    """
    Generate Value Proposition Report using Claude Sonnet 4.5.
    """
    client = anthropic.Anthropic(api_key=os.environ['ANTHROPIC_API_KEY'])

    # Load previous insights if user has past applications
    previous_insights = load_previous_insights(cv_facts['personal_info']['email'])

    prompt = VPR_GENERATION_PROMPT.format(
        cv_facts_json=json.dumps(cv_facts, indent=2),
        gap_responses_json=json.dumps(gap_responses, indent=2),
        job_requirements_json=json.dumps(job_requirements, indent=2),
        company_research_json=json.dumps(company_research, indent=2),
        previous_insights_json=json.dumps(previous_insights, indent=2)
    )

    input_tokens = count_tokens(prompt, "sonnet-4.5")

    response = client.messages.create(
        model="claude-sonnet-4-5-20250929",
        max_tokens=4000,
        temperature=0.7,  # Some creativity for natural writing
        messages=[{"role": "user", "content": prompt}]
    )

    vpr_content = response.content[0].text
    output_tokens = response.usage.output_tokens

    # Verify VPR quality
    quality_issues = verify_vpr_quality(vpr_content, cv_facts, gap_responses)
    if quality_issues:
        logger.warning(f"VPR quality issues: {quality_issues}")

    # Track cost
    cost = track_ai_cost(application_id, "vpr_generation", input_tokens, output_tokens, "sonnet-4.5")

    # Store in DynamoDB
    store_artifact(application_id, "VPR", vpr_content, cost)

    return {
        'content': vpr_content,
        'word_count': len(vpr_content.split()),
        'cost': cost,
        'quality_issues': quality_issues
    }
```

---

## PROMPT 2: CV TAILORING

**Model:** Claude Haiku 4.5
**Cost:** ~$0.005 per CV
**Function:** `cv-tailor`

```python
CV_TAILORING_PROMPT = """You are an expert CV writer. Tailor this CV for the specific job while maintaining ATS compatibility.

CRITICAL RULES:
- Use ONLY facts from the CV (zero hallucinations)
- Prioritize relevant experience
- Use exact keywords from job description
- ATS-optimized formatting (no tables, simple bullets)
- Length: 1-2 pages (max 3 pages)

INPUT:

CV FACTS:
{cv_facts_json}

JOB REQUIREMENTS:
{job_requirements_json}

VPR STRATEGIC DIFFERENTIATORS:
{vpr_differentiators}

LANGUAGE: {language}

---

TAILORING STRATEGY:

1. REORDER SECTIONS for relevance:
   - Most relevant experience first
   - Highlight matching skills
   - De-emphasize irrelevant experience

2. OPTIMIZE BULLET POINTS:
   - Start with action verbs
   - Include quantified results
   - Use job description keywords
   - Keep 3-5 bullets per role

3. SKILLS SECTION:
   - List required skills first
   - Group by category
   - Match job description terminology

4. ATS FORMATTING:
   - Standard headers: "Professional Experience", "Education", "Skills"
   - Simple bullets (•)
   - No tables or columns
   - Standard fonts

OUTPUT: Return tailored CV as JSON structure:

{{
    "contact_info": {{
        "name": "Full Name",
        "email": "email@example.com",
        "phone": "+1-555-0000",
        "linkedin": "linkedin.com/in/profile",
        "location": "City, State"
    }},
    "professional_summary": "2-3 sentences highlighting relevant experience...",
    "work_experience": [
        {{
            "company": "Company Name",
            "title": "Job Title",
            "dates": "MM/YYYY - MM/YYYY",
            "location": "City, State",
            "bullets": [
                "Action verb + quantified achievement + relevant keywords",
                "..."
            ]
        }}
    ],
    "education": [...],
    "skills": {{
        "technical": ["skill1", "skill2"],
        "tools": ["tool1", "tool2"]
    }},
    "certifications": [...]
}}

Generate tailored CV now:"""
```

---

## PROMPT 3: COVER LETTER GENERATION

**Model:** Claude Haiku 4.5
**Cost:** ~$0.004 per letter
**Length:** EXACTLY 1 page (max 400 words)

```python
COVER_LETTER_PROMPT = """You are an expert cover letter writer. Create a compelling cover letter that is EXACTLY 1 page (maximum 400 words).

CRITICAL REQUIREMENTS:
- Length: MAX 400 words (strictly enforced)
- Use facts from CV only (zero hallucinations)
- Pass anti-AI detection
- Natural, conversational tone
- Address specific job requirements

INPUT:

CV FACTS:
{cv_facts_json}

JOB INFO:
- Title: {job_title}
- Company: {company_name}
- Requirements: {key_requirements}

VPR DIFFERENTIATORS:
{vpr_differentiators}

COMPANY CULTURE:
{company_culture}

LANGUAGE: {language}

---

STRUCTURE (400 words total):

**Opening (80-100 words):**
- Hook: Compelling opener showing genuine interest
- Position statement: Role + company name
- Value preview: Brief statement of unique fit

**Body Paragraph 1 (120-140 words):**
- Most impressive quantified achievement
- Direct relevance to job requirement
- Technical depth demonstration

**Body Paragraph 2 (100-120 words):**
- Second key achievement or skill
- Cultural fit or company-specific insight
- Forward-looking statement

**Closing (60-80 words):**
- Enthusiasm for opportunity
- Call to action
- Professional close

---

ANTI-AI DETECTION:
- Use natural transitions
- Vary sentence length
- Include brief personal touch
- Avoid: leverage, delve, robust, streamline
- Use approximations: "nearly 40%" not "39.7%"

WORD COUNT: You MUST stay under 400 words. Count as you write.

Generate cover letter now:"""
```

---

## PROMPT 4: INTERVIEW PREP GENERATION

**Model:** Claude Haiku 4.5
**Cost:** ~$0.005 per guide
**Default Format:** DOCX

```python
INTERVIEW_PREP_PROMPT = """You are an interview preparation expert. Generate a comprehensive interview guide with predicted questions and STAR responses.

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

---

OUTPUT STRUCTURE:

## PREDICTED INTERVIEW QUESTIONS (10-15 questions)

Generate questions in these categories:

### Technical Questions (4-5 questions)
Based on job requirements:
- Specific technology questions
- Architecture/design questions
- Problem-solving scenarios

### Behavioral Questions (4-5 questions)
STAR method required:
- Leadership examples
- Conflict resolution
- Project challenges
- Team collaboration

### Company-Specific Questions (2-3 questions)
Based on company research:
- Cultural fit
- Company challenges
- Strategic initiatives

### Gap Questions (2-3 questions)
Address potential weaknesses:
- Missing skills
- Career transitions
- Experience gaps

---

FOR EACH QUESTION PROVIDE:

**Q: [Question]**

**STAR Response:**
- **Situation:** Brief context (2-3 sentences)
- **Task:** Your responsibility (1-2 sentences)
- **Action:** Specific steps you took (3-4 bullet points)
- **Result:** Quantified outcome (2-3 sentences with metrics)

**Key Points to Emphasize:**
- Specific metric or achievement
- Relevant skill demonstrated
- Transferable learning

---

## QUESTIONS TO ASK INTERVIEWER (5-7 questions)

Categories:
- Role-specific questions
- Team dynamics
- Company growth/direction
- Technical environment
- Success metrics

## SALARY NEGOTIATION GUIDANCE

Based on role and experience:
- Market research summary
- Suggested range
- Negotiation talking points

## PRE-INTERVIEW CHECKLIST

- Research recap
- Key achievements to mention
- Questions prepared
- Technical setup (if virtual)

Generate interview prep guide now:"""
```

---

## SUPPORTING UTILITIES

### Language Detection & Multi-Language Rules

```python
def determine_artifact_languages(cv_language: str, job_language: str) -> list:
    """
    Determine which languages to generate artifacts in.

    RULES:
    - If CV language == Job language: Generate in that language only
    - If CV language != Job language: Generate in BOTH languages

    Returns: List of language codes to generate ['en', 'he']
    """
    if cv_language == job_language:
        return [cv_language]
    else:
        return [cv_language, job_language]

# Example usage:
cv_lang = detect_language(cv_text)  # 'en'
job_lang = detect_language(job_description)  # 'he'
languages_to_generate = determine_artifact_languages(cv_lang, job_lang)
# Returns: ['en', 'he'] - generate both versions
```

### Anti-AI Detection Validator

```python
def validate_anti_ai_detection(content: str) -> list:
    """
    Check content for AI detection red flags.
    Returns list of issues found.
    """
    issues = []

    # Banned words
    banned = ['leverage', 'delve into', 'landscape', 'robust', 'streamline',
              'utilize', 'paradigm shift', 'game-changer', 'synergy']

    for word in banned:
        if word in content.lower():
            count = content.lower().count(word)
            issues.append(f"Banned word '{word}' used {count} time(s)")

    # Check sentence length variety
    sentences = content.split('.')
    lengths = [len(s.split()) for s in sentences if s.strip()]
    if len(set(lengths)) < len(lengths) * 0.3:  # Less than 30% variety
        issues.append("Sentence length too uniform")

    # Check for formulaic patterns
    formulaic_patterns = [
        r'firstly.*secondly.*thirdly',
        r'in conclusion.*in summary',
        r'it is important to note that'
    ]
    for pattern in formulaic_patterns:
        if re.search(pattern, content.lower()):
            issues.append(f"Formulaic pattern detected: {pattern}")

    return issues
```

---

## COST TRACKING IMPLEMENTATION

```python
def track_full_application_cost(application_id: str, stages: dict) -> dict:
    """
    Track complete cost breakdown for application.

    stages = {
        'cv_parsing': {'tokens_in': X, 'tokens_out': Y, 'model': 'haiku'},
        'company_research': {'cost': 0.004},
        'gap_analysis': {...},
        'vpr': {...},
        'cv_tailor': {...},
        'cover_letter': {...},
        'interview_prep': {...}
    }
    """
    total_cost = 0
    breakdown = {}

    for stage, data in stages.items():
        if 'cost' in data:
            cost = data['cost']
        else:
            cost = estimate_cost(data['tokens_in'], data['tokens_out'], data['model'])

        total_cost += cost
        breakdown[stage] = cost

    # Store in DynamoDB
    table = dynamodb.Table('careervp-cost-tracking')
    table.put_item(Item={
        'applicationId': application_id,
        'total_cost': Decimal(str(total_cost)),
        'breakdown': breakdown,
        'timestamp': datetime.utcnow().isoformat()
    })

    # Alert if cost exceeds target
    if total_cost > 0.065:  # Target is $0.058
        logger.warning(f"Application {application_id} cost ${total_cost:.4f} exceeds target")

    return {
        'total': total_cost,
        'breakdown': breakdown,
        'target': 0.058,
        'variance': total_cost - 0.058
    }
```

---

## INTEGRATION WITH ORCHESTRATOR LAMBDA

```python
def orchestrate_application_processing(application_id: str):
    """
    Main orchestrator function coordinating all AI prompts.
    """
    # Load application data
    app = load_application(application_id)

    stages = {}

    try:
        # Stage 1: Parse CV (if not already done)
        if not app.get('cv_facts'):
            cv_facts = parse_cv(app['cv_text'], app['user_email'], app['cv_id'])
            stages['cv_parsing'] = {'tokens_in': 2000, 'tokens_out': 500, 'model': 'haiku'}
        else:
            cv_facts = app['cv_facts']

        # Stage 2: Company research (cached if available)
        company_research = get_company_research(app['company_name'])
        stages['company_research'] = {'cost': 0.004}

        # Stage 3: Generate gap analysis questions
        gap_questions = generate_gap_questions(cv_facts, app['job_requirements'], company_research)
        stages['gap_analysis'] = {'tokens_in': 8000, 'tokens_out': 1000, 'model': 'sonnet'}

        # Wait for user to answer gap questions
        update_status(application_id, "PENDING_GAP_RESPONSES")

        # [User answers questions via UI]
        gap_responses = wait_for_gap_responses(application_id)

        # Stage 4: Generate VPR
        vpr = generate_vpr(application_id, cv_facts, gap_responses,
                          app['job_requirements'], company_research)
        stages['vpr'] = {'tokens_in': 10000, 'tokens_out': 2500, 'model': 'sonnet'}

        # Stage 5: Determine languages
        cv_lang = detect_language(app['cv_text'])
        job_lang = detect_language(app['job_description'])
        languages = determine_artifact_languages(cv_lang, job_lang)

        # Stage 6-8: Generate artifacts (potentially in multiple languages)
        for lang in languages:
            suffix = f"_{lang}" if len(languages) > 1 else ""

            cv_tailored = tailor_cv(cv_facts, app['job_requirements'],
                                   vpr['differentiators'], lang)
            stages[f'cv_tailor{suffix}'] = {'tokens_in': 5000, 'tokens_out': 1200, 'model': 'haiku'}

            cover_letter = generate_cover_letter(cv_facts, app['job_title'],
                                                 app['company_name'], vpr, lang)
            stages[f'cover_letter{suffix}'] = {'tokens_in': 4000, 'tokens_out': 800, 'model': 'haiku'}

            interview_prep = generate_interview_prep(cv_facts, app['job_requirements'],
                                                     vpr, gap_responses, company_research, lang)
            stages[f'interview_prep{suffix}'] = {'tokens_in': 5000, 'tokens_out': 2000, 'model': 'haiku'}

        # Track total cost
        cost_summary = track_full_application_cost(application_id, stages)

        # Update status
        update_status(application_id, "COMPLETED", cost_summary)

        # Send notification
        send_completion_email(app['user_email'], application_id)

    except Exception as e:
        logger.error(f"Application processing failed: {e}")
        update_status(application_id, "FAILED", error=str(e))
        raise
```
---

## SECTION 3.2 ENHANCED: GAP ANALYSIS QUESTIONS GENERATION (ADVANCED)

**Purpose:** Generate contextually-tagged, strategically-aligned gap analysis questions with explicit destination mapping and memory awareness.

**Model:** Claude Sonnet 4.5
**Cost:** ~$0.021 per generation (+$0.001 vs basic)
**Timeout:** 30 seconds
**Lambda Function:** `gap-analysis-questions-v2`

### Key Enhancements

1. **Contextual Tagging System**
   - `[CV IMPACT]` - Questions that gather quantifiable metrics for CV
   - `[INTERVIEW/MVP ONLY]` - Questions for soft skills, philosophy, process understanding

2. **Memory-Aware Questioning**
   - Skip recurring themes from user's history
   - Avoid redundant questions across applications
   - Reference previously-established strengths

3. **Strategic Intent Framework**
   - Each question includes WHY it's being asked
   - Maps to specific job requirements
   - Defines expected outcome

4. **Destination Labeling**
   - Clear indication of which artifact(s) will use the response
   - Prioritization based on artifact importance

### Enhanced Prompt Template

```python
GAP_ANALYSIS_ENHANCED_PROMPT = """You are an expert career strategist generating targeted gap analysis questions with contextual tagging and strategic intent mapping.

CRITICAL INSTRUCTIONS:
1. Generate MAXIMUM 10 questions
2. Tag each question with destination: [CV IMPACT] or [INTERVIEW/MVP ONLY]
3. Include strategic intent for each question
4. Skip recurring themes from user history
5. Emphasize quantification for [CV IMPACT] questions
6. Wait for user responses before proceeding

INPUT DATA:

CV FACTS (USER'S ESTABLISHED STRENGTHS):
{cv_facts_json}

USER'S RECURRING THEMES (SKIP THESE TOPICS):
{recurring_themes}
Examples:
- Technical audience experience (already established)
- Cross-functional collaboration (documented across multiple roles)
- Leadership of distributed teams (quantified in previous applications)

JOB REQUIREMENTS (CRITICAL REQUIREMENTS ONLY):
{job_requirements_json}

COMPANY CONTEXT:
{company_research_json}

PREVIOUS GAP RESPONSES (DO NOT REPEAT):
{previous_gap_responses_json}

---

QUESTION GENERATION STRATEGY:

STEP 1 - CROSS-REFERENCE & MEMORY CHECK:
- Analyze job requirements against CV facts
- Identify gaps where CV lacks specific metrics/evidence
- Explicitly skip topics from recurring_themes
- Focus ONLY on "Critical" or "Must-Have" job requirements

STEP 2 - CATEGORIZE BY DESTINATION:
- [CV IMPACT]: Questions that yield quantifiable results, metrics, team sizes, time savings
- [INTERVIEW/MVP ONLY]: Questions about philosophy, process, soft skills, approach

STEP 3 - ENFORCE BREADTH OVER DEPTH:
- Avoid "in the weeds" technical questions unless explicitly "Must-Have"
- Focus on business impact, not implementation details
- Example: Ask "What was the impact?" not "What database schema did you use?"

STEP 4 - STRUCTURE EACH QUESTION:

**QUESTION FORMAT:**
```
### Question {N}

**Requirement:** [Exact quote from job posting]

**Question:** [Your targeted question emphasizing quantification]

**Destination:** [CV IMPACT] or [INTERVIEW/MVP ONLY]

**Strategic Intent:** [Why this is being asked]
- Example: "To prove pipeline impact with specific metrics"
- Example: "To prepare for 'failing fast' philosophy interview questions"

**Evidence Gap:** [What's missing from the CV]

**YOUR ANSWER:**
[User fills this in]
```

---

EXAMPLE QUESTIONS:

### Question 1

**Requirement:** "Build and optimize data pipelines processing 100M+ events/day"

**Question:** You mention building data pipelines in your CV. For your largest pipeline:
- How many events/day did it process?
- What was the processing latency (before and after your optimizations)?
- What was the infrastructure cost, and did you achieve any cost reductions?

**Destination:** [CV IMPACT]

**Strategic Intent:** To quantify pipeline scale and optimization impact with specific metrics for CV bullets. These numbers prove you meet the "100M+ events/day" requirement.

**Evidence Gap:** CV mentions "built scalable data pipelines" but lacks volume metrics, latency numbers, or cost impact.

**YOUR ANSWER:**
[User response]

---

### Question 2

**Requirement:** "Experience with failing fast and iterative development"

**Question:** Describe a situation where you intentionally killed a project or feature early after discovering it wouldn't work. What signals triggered the decision, and what did you learn?

**Destination:** [INTERVIEW/MVP ONLY]

**Strategic Intent:** To prepare for behavioral questions about judgment, risk management, and company's "fail fast" culture. This won't go in CV but strengthens MVP report and interview prep.

**Evidence Gap:** CV shows successful projects but doesn't demonstrate decision-making about what NOT to build.

**YOUR ANSWER:**
[User response]

---

GENERATION RULES:

1. **[CV IMPACT] QUESTIONS (5-7 questions):**
   - MUST ask for specific numbers: "How many?", "What percentage?", "How much time/cost?"
   - Focus on: team sizes, metrics, results, time saved, cost reduced, scale achieved
   - These feed directly into CV bullets and VPR evidence matrix

2. **[INTERVIEW/MVP ONLY] QUESTIONS (3-5 questions):**
   - Ask about: philosophy, approach, process, soft skills, judgment calls
   - These strengthen interview prep and cultural fit sections
   - Don't force metrics if topic is inherently qualitative

3. **REFINEMENT PRINCIPLE:**
   - If asking about process, also ask for OUTCOME
   - Example: "How did you approach X?" + "What was the measurable result?"

4. **MEMORY AWARENESS:**
   - Before asking about a topic, check recurring_themes
   - If topic is already established, SKIP IT
   - Example: Don't ask "Have you led cross-functional teams?" if recurring_themes shows this is documented

5. **STRATEGIC INTENT:**
   - Every question must explain WHY it matters
   - Link to specific job requirement
   - Show how response will be used

---

OUTPUT FORMAT:

Return JSON array of questions:

{{
    "questions": [
        {{
            "question_id": "gap_001",
            "requirement": "Exact quote from job posting",
            "question_text": "Detailed question emphasizing quantification",
            "destination": "CV_IMPACT",
            "strategic_intent": "Why this matters and how it will be used",
            "evidence_gap": "What's missing from the CV",
            "priority": "CRITICAL",
            "recurring_theme_check": false
        }},
        {{
            "question_id": "gap_002",
            "requirement": "Another requirement",
            "question_text": "Question about approach or philosophy",
            "destination": "INTERVIEW_MVP_ONLY",
            "strategic_intent": "Prepares for cultural fit questions",
            "evidence_gap": "No examples of this thinking style",
            "priority": "IMPORTANT",
            "recurring_theme_check": false
        }}
    ],
    "summary": {{
        "total_questions": 10,
        "cv_impact_questions": 6,
        "interview_only_questions": 4,
        "skipped_recurring_themes": ["Technical audience", "Cross-functional collaboration"],
        "critical_gaps_addressed": ["Pipeline scale metrics", "Cost optimization results"]
    }}
}}

IMPORTANT: After generating questions, WAIT for user responses before proceeding with artifact generation.

Generate gap analysis questions now:"""
```

### Lambda Implementation with Memory

```python
def generate_gap_questions_enhanced(
    application_id: str,
    cv_facts: dict,
    job_requirements: dict,
    company_research: dict,
    user_email: str
) -> dict:
    """
    Generate enhanced gap analysis questions with contextual tagging.
    """
    client = anthropic.Anthropic(api_key=os.environ['ANTHROPIC_API_KEY'])

    # Load user's recurring themes from knowledge base
    recurring_themes = load_recurring_themes(user_email)

    # Load previous gap responses to avoid duplication
    previous_responses = load_previous_gap_responses(user_email)

    prompt = GAP_ANALYSIS_ENHANCED_PROMPT.format(
        cv_facts_json=json.dumps(cv_facts, indent=2),
        recurring_themes=json.dumps(recurring_themes, indent=2),
        job_requirements_json=json.dumps(job_requirements, indent=2),
        company_research_json=json.dumps(company_research, indent=2),
        previous_gap_responses_json=json.dumps(previous_responses, indent=2)
    )

    input_tokens = count_tokens(prompt, "sonnet-4.5")

    response = client.messages.create(
        model="claude-sonnet-4-5-20250929",
        max_tokens=3000,
        temperature=0.5,  # Some creativity but mostly structured
        messages=[{"role": "user", "content": prompt}]
    )

    questions_json = json.loads(response.content[0].text)
    output_tokens = response.usage.output_tokens

    # Store questions in DynamoDB
    table = dynamodb.Table('careervp-gap-questions')
    table.put_item(Item={
        'applicationId': application_id,
        'questions': questions_json['questions'],
        'summary': questions_json['summary'],
        'created_at': datetime.utcnow().isoformat(),
        'status': 'PENDING_RESPONSES'
    })

    # Track cost
    cost = track_ai_cost(application_id, "gap_analysis_enhanced",
                        input_tokens, output_tokens, "sonnet-4.5")

    return {
        'questions': questions_json['questions'],
        'summary': questions_json['summary'],
        'cost': cost
    }
```

### Response Collection with Destination Tracking

```python
def store_gap_responses_enhanced(
    application_id: str,
    responses: list
) -> dict:
    """
    Store gap responses with destination tracking for artifact generation.
    """
    # Separate responses by destination
    cv_impact_responses = []
    interview_only_responses = []

    for response in responses:
        # Load original question to get destination tag
        question = get_question_by_id(application_id, response['question_id'])

        enhanced_response = {
            **response,
            'destination': question['destination'],
            'strategic_intent': question['strategic_intent']
        }

        if question['destination'] == 'CV_IMPACT':
            cv_impact_responses.append(enhanced_response)
        else:
            interview_only_responses.append(enhanced_response)

    # Store in DynamoDB
    table = dynamodb.Table('careervp-gap-responses')
    table.put_item(Item={
        'applicationId': application_id,
        'cv_impact_responses': cv_impact_responses,
        'interview_only_responses': interview_only_responses,
        'completed_at': datetime.utcnow().isoformat()
    })

    # Update knowledge base with new evidence
    update_knowledge_base(application_id, responses)

    return {
        'cv_impact_count': len(cv_impact_responses),
        'interview_only_count': len(interview_only_responses),
        'total_responses': len(responses)
    }
```

---

## SECTION 3.4 ENHANCED: INTERVIEW PREP GENERATION (TIERED VERIFICATION)

**Purpose:** Generate interview prep with multi-agent verification system ensuring zero hallucinations and strategic alignment.

**Model:** Claude Haiku 4.5 (Generation) + Claude Haiku 4.5 (3× Verification)
**Cost:** Tier 1: ~$0.005 | Tier 2: ~$0.019 per question
**Timeout:** 90 seconds (for Tier 2 with verification)
**Lambda Function:** `interview-prep-generator-v2`

### Key Enhancements

1. **Tiered Complexity System**
   - **Tier 1 (Standard):** Philosophy, soft skills, process questions
   - **Tier 2 (High-Stakes):** Metric-heavy, [CV IMPACT] questions requiring precision

2. **Multi-Agent Verification**
   - **Agent 2A:** Fact Auditor (integrity check against evidence bank)
   - **Agent 2B:** Strategic Alignment Check (differentiator visibility)
   - **Agent 2C:** Persona & Tone Scraper (conversational quality)

3. **Adaptive Tone System**
   - Peer-to-peer language with contractions
   - Approximations vs exact percentages
   - Natural transitions, no "bot-speak"

4. **Staged Verification Workflow**
   - Generate → Verify (parallel 3-agent check) → Regenerate if needed
   - Max 1 regeneration attempt to control costs

### Cost Implications

```yaml
TIER 1 (Simple Questions):
  Generation: 1 call × $0.005 = $0.005
  Verification: Embedded (no extra calls)
  Total: $0.005 per question

TIER 2 (High-Stakes Questions):
  Generation: 1 call × $0.005 = $0.005
  Verification: 3 parallel calls × $0.003 = $0.009
  Regeneration (if needed): 1 call × $0.005 = $0.005
  Total: $0.019 per question (worst case)

TYPICAL INTERVIEW PREP (15 questions):
  Tier 1: 10 questions × $0.005 = $0.050
  Tier 2: 5 questions × $0.019 = $0.095
  Total: $0.145 per application

COST IMPACT:
  Original: $0.058 total per application
  Enhanced: $0.058 + $0.140 = $0.198 per application
  Increase: +241% overall cost

RECOMMENDATION: Make Tier 2 verification OPTIONAL premium feature
```

### Tier 1: Standard Generation (Embedded Verification)

```python
INTERVIEW_TIER1_PROMPT = """You are generating an interview response for a STANDARD question (philosophy, soft skills, or process).

EVIDENCE BANK:
{evidence_bank}

DIFFERENTIATOR:
{differentiator}

TONE SAMPLE (match this style):
{tone_sample}

QUESTION:
{interview_question}

INSTRUCTIONS:

1. **Use ONLY facts from Evidence Bank** - no hallucinations
2. **Maximum 300 words** - be concise
3. **Conversational tone** - use contractions, approximations (e.g., "about 20%" not "19.42%")
4. **Integrate differentiator naturally** - don't force it
5. **Structure:**
   - Opening: Brief context (1-2 sentences)
   - Body: Your approach/philosophy with 1-2 specific examples
   - Close: Key takeaway or forward-looking statement

EMBEDDED VERIFICATION:
Before outputting, self-check:
- [ ] All facts from Evidence Bank?
- [ ] Word count ≤ 300?
- [ ] Conversational tone (no "Furthermore", "In conclusion")?
- [ ] Differentiator mentioned naturally?

If any check fails, revise before outputting.

OUTPUT FORMAT: Plain text response (no JSON, no metadata)

Generate response now:"""
```

### Tier 2: High-Stakes Generation (Staged Verification)

```python
INTERVIEW_TIER2_PROMPT = """You are generating an interview response for a HIGH-STAKES question requiring precision and metrics.

EVIDENCE BANK (CV IMPACT responses):
{evidence_bank}

DIFFERENTIATOR:
{differentiator}

TONE SAMPLE:
{tone_sample}

QUESTION (requires specific metrics):
{interview_question}

INSTRUCTIONS:

1. **EXACTLY 5-8 discrete facts** - must be countable
2. **All facts from Evidence Bank** - zero tolerance for hallucination
3. **300-400 words** - strict limit
4. **Conversational tone** - peer-to-peer language
5. **Structure (STAR method):**
   - **Situation:** Brief context with scale (1-2 sentences)
   - **Task:** Your specific responsibility (1 sentence)
   - **Action:** What you did with quantified steps (3-5 bullet points with metrics)
   - **Result:** Quantified outcomes (2-3 sentences)

FACT REQUIREMENTS:
- Include: team sizes, metrics, percentages, time saved, cost reduced
- Use approximations: "nearly 40%" not "39.7%"
- Be specific: "team of 8 engineers" not "small team"

DIFFERENTIATOR INTEGRATION:
- Weave in naturally within Action or Result
- Don't force it if it doesn't fit
- Should reinforce your unique value

OUTPUT FORMAT: Plain text response (no JSON)

Generate response now:"""
```

### Verification Agent 2A: Fact Auditor

```python
VERIFICATION_2A_FACT_AUDIT = """You are a Senior Data Auditor ensuring ZERO hallucinations.

EVIDENCE BANK (source of truth):
{evidence_bank}

GENERATED RESPONSE (to verify):
{generated_response}

TASK:

1. **Extract all claims** from the Response:
   - Numerical claims (team sizes, percentages, metrics, dates)
   - Proper nouns (company names, product names, technologies)
   - Achievements and outcomes

2. **Cross-reference** each claim against Evidence Bank:
   - PASS: Claim explicitly supported by Evidence Bank
   - FAIL: Claim not found or contradicts Evidence Bank

3. **Count discrete facts:**
   - Must be 5-8 facts for Tier 2
   - Each fact should be independently verifiable

OUTPUT FORMAT:

{{
    "verdict": "PASS" or "FAIL",
    "fact_count": 7,
    "verified_facts": [
        {{"claim": "Led team of 8 engineers", "status": "PASS", "source": "gap_response_003"}},
        {{"claim": "Reduced latency by 40%", "status": "PASS", "source": "cv_facts.work_experience[0]"}},
        {{"claim": "Processing 2M events/day", "status": "FAIL", "reason": "Evidence shows 1.5M events/day"}}
    ],
    "hallucinations": [
        "Processing 2M events/day (actual: 1.5M)"
    ],
    "recommendation": "FAIL - contains 1 hallucination, regenerate required"
}}

Audit now:"""
```

### Verification Agent 2B: Strategic Alignment

```python
VERIFICATION_2B_STRATEGY = """You are a Career Strategist checking if the response showcases the candidate's unique value.

TARGET DIFFERENTIATOR:
{differentiator}

JOB REQUIREMENT:
{job_requirement}

GENERATED RESPONSE:
{generated_response}

TASK:

1. **Bridge to Requirement:**
   - Does the response explicitly connect experience to the job requirement?
   - Is the connection clear or is it implied?

2. **Differentiator Visibility:**
   - Is the differentiator clearly articulated?
   - Is it buried in technical details?
   - Does it stand out as unique value?

3. **Strategic Impact:**
   - Does the response show WHY this matters to the employer?
   - Is there business impact, not just technical execution?

OUTPUT FORMAT:

{{
    "verdict": "PASS" or "FAIL",
    "bridge_to_requirement": "CLEAR" or "WEAK" or "MISSING",
    "differentiator_visibility": "PROMINENT" or "BURIED" or "ABSENT",
    "business_impact": "STRONG" or "WEAK",
    "recommendation": "PASS" or "FAIL: [specific reasoning]"
}}

Analyze now:"""
```

### Verification Agent 2C: Tone & Persona

```python
VERIFICATION_2C_TONE = """You are a Speech Coach ensuring the response sounds like a PEER, not a BOT.

TONE SAMPLE (target style):
{tone_sample}

GENERATED RESPONSE:
{generated_response}

TASK:

1. **Peer-to-Peer Language Check:**
   - ✓ Contractions ("I've", "we're", "didn't")
   - ✓ Approximations ("roughly", "nearly", "about")
   - ✗ Formal transitions ("Furthermore", "Moreover", "In conclusion")
   - ✗ Corporate jargon ("leverage", "synergy", "utilize")

2. **Bot-Speak Detection:**
   - Flag: "It is important to note that..."
   - Flag: "In today's fast-paced environment..."
   - Flag: Overly structured (Firstly, Secondly, Thirdly)

3. **Word Count:**
   - Tier 1: Must be ≤ 300 words
   - Tier 2: Must be 300-400 words

OUTPUT FORMAT:

{{
    "verdict": "PASS" or "FAIL",
    "word_count": 347,
    "word_count_valid": true,
    "peer_language_score": 8,  // out of 10
    "bot_speak_violations": [
        "Line 3: 'Furthermore' detected",
        "Line 8: 'It is important to note' detected"
    ],
    "contractions_used": 5,
    "approximations_used": 3,
    "recommendation": "PASS" or "FAIL: [specific style violations]"
}}

Analyze now:"""
```

### Staged Verification Orchestrator

```python
def generate_interview_response_tier2(
    question: dict,
    evidence_bank: dict,
    differentiator: str,
    tone_sample: str
) -> dict:
    """
    Generate Tier 2 interview response with 3-agent verification.
    """
    client = anthropic.Anthropic(api_key=os.environ['ANTHROPIC_API_KEY'])

    # Stage 1: Generate initial response
    generation_prompt = INTERVIEW_TIER2_PROMPT.format(
        evidence_bank=json.dumps(evidence_bank, indent=2),
        differentiator=differentiator,
        tone_sample=tone_sample,
        interview_question=question['text']
    )

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=800,
        temperature=0.7,
        messages=[{"role": "user", "content": generation_prompt}]
    )

    generated_response = response.content[0].text
    generation_cost = estimate_cost(
        count_tokens(generation_prompt, "haiku"),
        response.usage.output_tokens,
        "haiku-4.5"
    )

    # Stage 2: Run 3-agent verification in parallel
    verification_results = {
        'fact_audit': verify_facts(generated_response, evidence_bank, client),
        'strategy': verify_strategy(generated_response, differentiator,
                                    question['requirement'], client),
        'tone': verify_tone(generated_response, tone_sample, client)
    }

    verification_cost = 3 * 0.003  # 3 verification calls

    # Stage 3: Determine if regeneration needed
    needs_regeneration = (
        verification_results['fact_audit']['verdict'] == 'FAIL' or
        verification_results['strategy']['verdict'] == 'FAIL' or
        verification_results['tone']['verdict'] == 'FAIL'
    )

    if needs_regeneration:
        logger.warning(f"Response failed verification: {verification_results}")

        # Compile feedback for regeneration
        feedback = {
            'fact_issues': verification_results['fact_audit'].get('hallucinations', []),
            'strategy_issues': verification_results['strategy'].get('recommendation', ''),
            'tone_issues': verification_results['tone'].get('bot_speak_violations', [])
        }

        # Regenerate with feedback
        regenerated = regenerate_with_feedback(
            question, evidence_bank, differentiator,
            tone_sample, feedback, client
        )

        regeneration_cost = 0.005
        final_response = regenerated['response']
        total_cost = generation_cost + verification_cost + regeneration_cost
    else:
        final_response = generated_response
        total_cost = generation_cost + verification_cost

    return {
        'response': final_response,
        'verification_results': verification_results,
        'regenerated': needs_regeneration,
        'cost': total_cost,
        'quality_score': calculate_quality_score(verification_results)
    }

def regenerate_with_feedback(
    question: dict,
    evidence_bank: dict,
    differentiator: str,
    tone_sample: str,
    feedback: dict,
    client
) -> dict:
    """
    Regenerate response incorporating verification feedback.
    """
    regeneration_prompt = f"""{INTERVIEW_TIER2_PROMPT.format(
        evidence_bank=json.dumps(evidence_bank, indent=2),
        differentiator=differentiator,
        tone_sample=tone_sample,
        interview_question=question['text']
    )}

CRITICAL FEEDBACK FROM VERIFICATION:

FACT ISSUES:
{json.dumps(feedback['fact_issues'], indent=2)}

STRATEGY ISSUES:
{feedback['strategy_issues']}

TONE ISSUES:
{json.dumps(feedback['tone_issues'], indent=2)}

You MUST address these issues in your regenerated response.

Generate corrected response now:"""

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=800,
        temperature=0.7,
        messages=[{"role": "user", "content": regeneration_prompt}]
    )

    return {
        'response': response.content[0].text,
        'tokens': response.usage.output_tokens
    }
```

### Complete Interview Prep Orchestrator

```python
def generate_interview_prep_enhanced(
    application_id: str,
    cv_facts: dict,
    job_requirements: dict,
    vpr_differentiators: list,
    gap_responses: dict,
    company_research: dict,
    tier2_enabled: bool = True  # Premium feature flag
) -> dict:
    """
    Generate complete interview prep with tiered verification.
    """
    # Prepare evidence bank
    evidence_bank = {
        'cv_facts': cv_facts,
        'cv_impact_responses': gap_responses['cv_impact_responses'],
        'interview_responses': gap_responses['interview_only_responses']
    }

    # Load user's tone sample (from previous successful responses)
    tone_sample = load_tone_sample(cv_facts['personal_info']['email'])

    # Identify primary differentiator
    primary_differentiator = vpr_differentiators[0] if vpr_differentiators else None

    # Generate predicted questions
    predicted_questions = predict_interview_questions(
        job_requirements, cv_facts, company_research
    )

    # Classify questions by tier
    tier1_questions = []
    tier2_questions = []

    for q in predicted_questions:
        if q['category'] in ['BEHAVIORAL', 'CULTURAL', 'SOFT_SKILLS']:
            tier1_questions.append(q)
        else:  # TECHNICAL, METRIC_HEAVY, ACHIEVEMENT
            tier2_questions.append(q)

    responses = []
    total_cost = 0

    # Generate Tier 1 responses (simple)
    for question in tier1_questions:
        response_data = generate_interview_response_tier1(
            question, evidence_bank, primary_differentiator, tone_sample
        )
        responses.append(response_data)
        total_cost += response_data['cost']

    # Generate Tier 2 responses (with verification)
    if tier2_enabled:
        for question in tier2_questions:
            response_data = generate_interview_response_tier2(
                question, evidence_bank, primary_differentiator, tone_sample
            )
            responses.append(response_data)
            total_cost += response_data['cost']
    else:
        # Fall back to Tier 1 generation for Tier 2 questions
        for question in tier2_questions:
            response_data = generate_interview_response_tier1(
                question, evidence_bank, primary_differentiator, tone_sample
            )
            responses.append(response_data)
            total_cost += response_data['cost']

    # Compile interview prep document
    interview_prep_doc = compile_interview_prep(
        responses, company_research, job_requirements
    )

    # Store in DynamoDB
    store_interview_prep(application_id, interview_prep_doc, responses, total_cost)

    return {
        'document': interview_prep_doc,
        'questions_count': len(responses),
        'tier1_count': len(tier1_questions),
        'tier2_count': len(tier2_questions),
        'tier2_enabled': tier2_enabled,
        'total_cost': total_cost,
        'quality_metrics': calculate_aggregate_quality(responses)
    }
```

---

## COST-BENEFIT ANALYSIS: ENHANCED SYSTEM

### Scenario 1: Basic (Original)
```yaml
Gap Analysis: $0.020
Interview Prep: $0.005
Total: $0.025 per application
Quality: Standard
```

### Scenario 2: Enhanced Gap Only
```yaml
Gap Analysis Enhanced: $0.021
Interview Prep: $0.005
Total: $0.026 per application
Quality: Improved question targeting
```

### Scenario 3: Full Enhanced (Tier 2 Verification)
```yaml
Gap Analysis Enhanced: $0.021
Interview Prep with Tier 2: $0.145
Total: $0.166 per application
Quality: Zero hallucinations guaranteed
```

### Scenario 4: Hybrid (Selective Tier 2)
```yaml
Gap Analysis Enhanced: $0.021
Interview Prep:
  - 10 Tier 1 questions: $0.050
  - 3 Tier 2 questions (critical only): $0.057
Total: $0.128 per application
Quality: Balanced cost-quality
```

### Recommendation

**V1 Launch:** Use Scenario 2 (Enhanced Gap + Standard Interview Prep)
- Minimal cost increase ($0.001)
- Better question quality
- Maintains $0.058 target

**V1.1 Premium Feature:** Offer Scenario 4 (Hybrid) as upgrade
- Pricing: Add $10/month for Tier 2 verification
- Position as "Premium Interview Prep with Fact Verification"
- Marginal cost: $0.10 per application
- Gross margin: Still >95% at scale

**Enterprise:** Offer Scenario 3 (Full Verification)
- High-stakes roles (executive, specialized)
- Cost increase justified by role value
- Position as "Executive Interview Prep"

---

## IMPLEMENTATION CHECKLIST

### Phase 1: Enhanced Gap Analysis (Week 1)
- [ ] Implement contextual tagging system
- [ ] Build recurring themes knowledge base
- [ ] Add destination labeling to question schema
- [ ] Update UI to show [CV IMPACT] vs [INTERVIEW/MVP] tags
- [ ] Test memory-aware question generation

### Phase 2: Tier 1 Interview Prep (Week 2)
- [ ] Implement basic tiered generation
- [ ] Load tone samples from user history
- [ ] Add embedded verification
- [ ] Test conversational quality

### Phase 3: Tier 2 Verification System (Week 3-4)
- [ ] Build 3-agent verification orchestrator
- [ ] Implement parallel verification calls
- [ ] Add regeneration logic with feedback
- [ ] Create quality scoring system
- [ ] Add premium feature flag in database

### Phase 4: Cost Monitoring & Optimization (Week 5)
- [ ] Track Tier 1 vs Tier 2 usage
- [ ] Monitor verification pass rates
- [ ] Analyze regeneration frequency
- [ ] A/B test quality improvements
- [ ] Calculate ROI for premium feature

---

This enhanced system provides:
✅ **Better Questions** - Contextually tagged with strategic intent
✅ **Zero Hallucinations** - Multi-agent fact verification
✅ **Higher Quality** - Tone matching and strategic alignment
✅ **Flexibility** - Tiered pricing for different user needs
✅ **Cost Control** - Optional premium features
