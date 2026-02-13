"""
VPR Prompt builder per docs/features/CareerVP Prompt Library.md lines 128-259.
Provides the canonical template and helpers for VPR generation.
"""

from __future__ import annotations

import json
from typing import Any

from careervp.models.cv import UserCV
from careervp.models.vpr import VPRRequest

# Grounding: docs/specs/03-vpr-generator.md:95 requires this prompt template.
VPR_GENERATION_PROMPT = """You are an expert career strategist creating a Value Proposition Report (VPR) for a job application.

STRICT RULES (VIOLATIONS WILL CAUSE FAILURE):
- NEVER mention the target company name (SysAid, etc.) as if the candidate worked there
- NEVER invent companies, roles, or achievements not explicitly in the CV
- NEVER use the gap responses to fabricate new facts - only use them to ELABORATE on CV facts
- ALL facts must be DIRECTLY VERIFIABLE from the provided CV text
- If you cannot find a fact in the CV, do NOT include it
- Use exact company names and roles from the CV (e.g., "AllCloud", "Director of AWS Training")

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
### LMS Implementation Experience (Example from CV)
**Evidence:** Led LMS setup and deployment of Cloud Academy serving 200+ internal employees and external customers; created 30+ learning plans including comprehensive 8-week DevOps Bootcamp (CV fact).

**Alignment:** STRONG - Direct LMS implementation experience matching requirement for LMS selection and management.

**Impact Potential:** Can immediately set up and scale SysAid Customer Academy infrastructure.
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

OUTPUT FORMAT: Return ONLY valid JSON (no markdown formatting, no code blocks). The JSON will be parsed programmatically.

```json
{{
  "executive_summary": "...",
  "evidence_matrix": [
    {{
      "requirement": "Exact requirement from job posting",
      "evidence": "Specific facts from CV + gap responses",
      "alignment_score": "STRONG|MODERATE|DEVELOPING",
      "impact_potential": "How this translates to role success"
    }}
  ],
  "differentiators": ["different strength 1", "different strength 2"],
  "gap_strategies": [
    {{
      "gap": "Missing requirement",
      "mitigation_approach": "How to address this",
      "transferable_skills": ["skill 1", "skill 2"]
    }}
  ],
  "cultural_fit": "Analysis based on company research",
  "talking_points": ["point 1", "point 2"],
  "keywords": ["keyword 1", "keyword 2"],
  "language": "en",
  "version": 1,
  "word_count": 1500
}}
```

Generate the JSON VPR now:"""

# Anti-AI detection list from docs/specs/03-vpr-generator.md lines 80-84.
BANNED_WORDS: list[str] = [
    'leverage',
    'delve into',
    'landscape',
    'robust',
    'streamline',
    'utilize',
    'facilitate',
    'implement',
    'cutting-edge',
    'best practices',
    'industry-leading',
    'game-changer',
    'paradigm shift',
    'synergy',
]


def build_vpr_prompt(user_cv: UserCV, request: VPRRequest) -> str:
    """
    Build the formatted prompt for Sonnet 4.5 (spec line 95).
    """
    cv_facts = _serialize_cv_for_prompt(user_cv)
    job_requirements = request.job_posting.model_dump(mode='json')
    gap_responses = [gr.model_dump(mode='json') for gr in request.gap_responses]
    company_research = request.company_context.model_dump(mode='json') if request.company_context else {}
    previous_insights: dict[str, Any] = {}

    return VPR_GENERATION_PROMPT.format(
        cv_facts_json=json.dumps(cv_facts, indent=2),
        job_requirements_json=json.dumps(job_requirements, indent=2),
        gap_responses_json=json.dumps(gap_responses, indent=2),
        company_research_json=json.dumps(company_research, indent=2),
        previous_insights_json=json.dumps(previous_insights, indent=2),
    )


def check_anti_ai_patterns(content: str) -> list[str]:
    """
    Return banned words detected in generated content.
    """
    content_lower = content.lower()
    return [word for word in BANNED_WORDS if word in content_lower]


def _serialize_cv_for_prompt(user_cv: UserCV) -> dict[str, Any]:
    """
    Serialize UserCV while preserving IMMUTABLE facts (FVS requirement).
    """
    data = user_cv.model_dump(mode='json')
    # Remove unused bulk fields.
    data.pop('raw_text', None)
    data.pop('file_content', None)
    data.pop('source_file_key', None)
    for field in ['email', 'phone', 'location', 'linkedin']:
        data.pop(field, None)
    contact_info = data.get('contact_info')
    if isinstance(contact_info, dict):
        # Strip contact identifiers before sharing with the LLM.
        for field in ['email', 'phone']:
            contact_info.pop(field, None)
        if not any(value for value in contact_info.values()):
            data.pop('contact_info', None)
    return data
