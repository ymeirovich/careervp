# VPR Current Implementation — Architecture Reference

> **Purpose:** Documents the VPR system as it is actually implemented in code, for comparison against the ground truth schema (`vpr.json`) and ideal rendered output (`SysAid_Value_Proposition_Report_Yitzchak_Meirovich.docx`).
>
> **Do not modify** `prompt.md` or `vpr.json` — those are the target specification.
>
> Generated: 2026-03-28

---

## 1. Pipeline Architecture

The VPR generator uses a **6-stage pipeline** (`src/backend/careervp/logic/vpr_generator.py`). Stages 1, 2, and 5 are rule-based (no LLM call). Only stages 3 and 4 invoke Claude.

| Stage | Type | Model/Temp | What it does |
|-------|------|-----------|-------------|
| 1 — Analyze Input | **Rule-based** | — | Extract key skills (from CV), experience level (heuristic on titles), job requirements (requirements + responsibilities deduped) |
| 2 — Extract Evidence | **Rule-based** | — | Token-overlap matching: map each job requirement to the best CV achievement by shared word count |
| 3 — Synthesize | **LLM** | Sonnet 4.5, temp 0.65 | Generate draft VPR JSON from matched evidence |
| 4 — Self-Correct | **LLM** | Sonnet 4.5, temp 0.35 | Improve draft: remove anti-AI patterns, improve clarity; falls back to rule-based if LLM fails |
| 5 — Generate Output | **Rule-based** | — | Map Stage 4 JSON into typed Pydantic `VPR` model; calculate word count |
| 6 — Meta Evaluation | **Rule-based** | — | Run FVS anti-AI gate; if score < 9.0, regenerate from Stage 3 with feedback (max 3 attempts) |

**Model routing:** All LLM calls go through `TaskMode.STRATEGIC` → `claude-sonnet-4-5` (never Haiku for VPR).

**Regeneration loop:** On Stage 6 failure, feedback message (score + issue list) is injected into Stage 3 and 4 prompts and the pipeline reruns from Stage 3.

---

## 2. Input Schema

```python
class VPRRequest(BaseModel):
    application_id: str           # Unique application ID (idempotency key)
    user_id: str                  # User requesting VPR
    job_posting: JobPosting       # Company, role, requirements, responsibilities, language
    gap_responses: list[GapResponse]   # User responses to gap analysis questions (primary evidence)
    company_context: CompanyContext | None  # Optional: mission, values, strategic priorities
```

`company_context` feeds the `COMPANY RESEARCH` block in the main prompt and is the source of the DOCX's rich "Company Insights" section.

`gap_responses` are the PRIMARY EVIDENCE source — they elaborate on CV facts and are essential for strong alignment scores.

---

## 3. Current Prompts (verbatim from `vpr_prompt.py`)

### 3.1 Main Prompt (`VPR_GENERATION_PROMPT`)

> **Note:** This prompt exists in the codebase but is NOT used by the 6-stage pipeline. The pipeline uses the lighter Stage 3/4 prompts. This prompt is called by the legacy `build_vpr_prompt()` helper which is no longer invoked.

```
You are an expert career strategist creating a Value Proposition Report (VPR) for a job application.

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
...

## 2. EVIDENCE & ALIGNMENT MATRIX (600-800 words)
...

## 3. STRATEGIC DIFFERENTIATORS (300-400 words)
...

## 4. GAP MITIGATION STRATEGIES (200-300 words)
...

## 5. CULTURAL FIT ANALYSIS (150-200 words)
...

## 6. RECOMMENDED TALKING POINTS (150-200 words)
...

---

ANTI-AI DETECTION RULES:
BANNED WORDS (never use): leverage, delve into, landscape, robust, streamline, utilize,
facilitate, implement, cutting-edge, best practices, industry-leading, game-changer,
paradigm shift, synergy

WRITING STYLE: Vary sentence length (8-25 words), natural transitions, conversational phrases,
approximations not exact percentages, mix active and passive voice.

FACT VERIFICATION CHECKLIST: [before any fact, verify it's in CV or gap responses]

OUTPUT FORMAT: Return ONLY valid JSON matching this schema:
{
  "executive_summary": "...",
  "evidence_matrix": [{requirement, evidence, alignment_score, impact_potential}],
  "differentiators": ["..."],
  "gap_strategies": [{gap, mitigation_approach, transferable_skills[]}],
  "cultural_fit": "...",
  "talking_points": ["..."],
  "keywords": ["..."],
  "language": "en",
  "version": 1,
  "word_count": 1500
}
```

### 3.2 Stage 3 Prompts (actively used)

**System prompt:**
```
You are Stage 3 Synthesizer. Build a natural, evidence-grounded draft VPR in strict JSON.
```

**User prompt template:**
```
Create a draft value proposition JSON with fields:
executive_summary, evidence_matrix, differentiators, gap_strategies, cultural_fit, talking_points, keywords.
Stay factual and natural.

{few_shot_example}

EVIDENCE:
{evidence_json}
{feedback_block}
```

**Few-shot example injected:**
```json
Input evidence:
{ "matches": [{ "requirement": "Lead cross-functional teams", "evidence": "Managed a 9-person team to launch two products" }] }

Output draft:
{
  "executive_summary": "The candidate has repeatedly led cross-functional teams and shipped outcomes under deadlines.",
  "evidence_matrix": [{"requirement": "Lead cross-functional teams", "evidence": "Managed a 9-person team to launch two products", "alignment_score": "STRONG", "impact_potential": "Can coordinate roadmap execution with engineering, design, and operations."}],
  "differentiators": ["Execution leadership with measurable launches"],
  "gap_strategies": [],
  "cultural_fit": "Collaborative and delivery-focused operating style.",
  "talking_points": ["Share how cross-functional planning reduced launch risk."],
  "keywords": ["Cross-functional leadership", "Product delivery"]
}
```

**Evidence payload shape (input to Stage 3):**
```json
{
  "matches": [{"requirement": "...", "evidence": "...", "alignment_score": "STRONG|MODERATE|DEVELOPING", "impact_potential": "..."}],
  "uncovered_requirements": ["..."],
  "key_skills": ["..."],
  "experience_level": "senior|advanced|mid|early"
}
```

### 3.3 Stage 4 Prompts (actively used)

**System prompt:**
```
You are Stage 4 Self-Corrector. Improve clarity, factual grounding, and anti-AI style in strict JSON.
```

**User prompt template:**
```
Self-correct this draft JSON for clarity, factual grounding, and anti-AI writing.
Return same VPR fields plus corrections_applied: list[str].

{few_shot_example}

DRAFT:
{draft_json}
{feedback_block}
```

**Few-shot example injected:**
```json
Input draft:
{ "executive_summary": "I leverage robust strategies to streamline outcomes across the organization." }

Output corrected:
{
  "executive_summary": "I help teams focus on the few moves that improve outcomes and keep delivery steady.",
  "corrections_applied": ["Removed banned terms", "Reduced formulaic language"]
}
```

**Stage 4 fallback (no LLM):** If Stage 4 LLM call fails, rule-based banned-term replacement runs instead:
```
leverage → use
delve into → explore
landscape → space
robust → strong
streamline → simplify
utilize → use
facilitate → support
implement → build
cutting-edge → modern
best practices → proven methods
industry-leading → well-regarded
game-changer → high-impact improvement
paradigm shift → major change
synergy → collaboration
```

---

## 4. Current Output Schema

From `src/backend/careervp/models/vpr.py` — **Pydantic `VPR` model**:

```python
class VPR(BaseModel):
    # Identification
    application_id: str
    user_id: str

    # Content (9 fields, snake_case, flat)
    executive_summary: str              # 200-250 word narrative
    evidence_matrix: list[EvidenceItem] # Per requirement: requirement, evidence, alignment_score, impact_potential
    differentiators: list[str]          # 3-5 strategic differentiators (plain strings)
    gap_strategies: list[GapStrategy]   # Per gap: gap, mitigation_approach, transferable_skills[]
    cultural_fit: str | None            # Cultural fit analysis (nullable)
    talking_points: list[str]           # 5-7 interview talking points
    keywords: list[str]                 # ATS-optimized keywords

    # Metadata
    version: int                        # VPR iteration number
    language: Literal['en', 'he']       # Output language
    created_at: datetime
    word_count: int                     # Auto-calculated across all text sections

class EvidenceItem(BaseModel):
    requirement: str
    evidence: str
    alignment_score: Literal['STRONG', 'MODERATE', 'DEVELOPING']
    impact_potential: str

class GapStrategy(BaseModel):
    gap: str
    mitigation_approach: str
    transferable_skills: list[str]
```

---

## 5. Validation System (FVS)

All validation logic lives in `src/backend/careervp/logic/fvs_validator.py`.

### 5.1 Anti-AI Gate (used in Stage 6 of VPR pipeline)

Function: `check_anti_ai_patterns(content: str) -> AntiAIPatternResult`

8-pattern scoring framework. Score starts at 10.0, deductions apply:

| Pattern | Trigger | Deduction |
|---------|---------|-----------|
| 1 — Banned buzzwords | Any of 14 terms present | -0.6 per term (max -4.0) |
| 2 — Too-short shape | < 2 sentences | -0.4 |
| 3 — Heavy sentence length | Avg sentence > 26 words | -0.4 |
| 4 — Repeated openings | Same 2-word start ≥ 3 times | -0.4 |
| 5 — Uniform sentence lengths | Spread ≤ 4 words (when ≥ 4 sentences) | -0.5 |
| 6 — Low lexical diversity | Unique/total token ratio < 0.42 | -0.4 |
| 7 — Formulaic transitions/fillers | ≥ 3 hits from robotic phrases list | -0.6 |
| 8 — Heavy nominalization | Tokens ending -tion/-ment/-ness > 18% | -0.5 |

**Banned buzzwords (14):** leverage, delve into, landscape, robust, streamline, utilize, facilitate, implement, cutting-edge, best practices, industry-leading, game-changer, paradigm shift, synergy

**Robotic transitions checked:** furthermore, moreover, additionally, in conclusion, in summary

**Robotic filler phrases:** "in today's fast-paced", "across the organization", "in order to", "at the end of the day", "from a strategic perspective"

**Gate:** Score must be ≥ 9.0 to pass. On failure, regeneration feedback is built from score + issue list and injected into Stage 3/4 for the next attempt (max 3 attempts total).

### 5.2 Fact Verification (not currently wired into VPR pipeline gate, but function exists)

Function: `validate_vpr_against_cv(vpr: VPR, user_cv: UserCV)`

Checks VPR content for hallucinated facts:
- Company names extracted via regex → checked against CV `experience[].company`
- Years (4-digit) extracted → checked against CV employment/education dates
- Job titles extracted → fuzzy-matched (≥ 82% similarity) against CV `experience[].role`

Violations classified as CRITICAL; any CRITICAL violation = `FVS_HALLUCINATION_DETECTED`.

### 5.3 Extended Quality Dimensions (available, not used in VPR pipeline)

The FVS validator has full implementations for additional quality checks that are NOT currently invoked by `vpr_generator.py`:

| Check | Function | Min Score | What it checks |
|-------|----------|-----------|---------------|
| Grammar | `validate_grammar()` | ≥ 9.0 | Typos (8 common), noisy punctuation, spacing, sentence fragments |
| Tone | `validate_tone()` | ≥ 8.0 | Casual language, hedging, over-exclaiming, weak confidence markers |
| Formatting | (exists) | ≥ 8.0 | Not reached in this read |
| Structure | (exists) | ≥ 8.0 | Not reached in this read |
| ATS | (exists) | ≥ 8.0 | Action verbs, keyword density |
| Consistency | `CrossDocumentConsistencyResult` | ≥ 9.0 | Cross-document factual consistency |

---

## 6. Ground Truth DOCX — Section Map

The ideal rendered VPR (what users see in UI + PDF/DOCX export) has these sections:

| DOCX Section | Content Description |
|---|---|
| **Header** | Candidate name, target role, company, report date |
| **Executive Summary** | 2-3 paragraph narrative: unique value, key metrics, speed-to-impact |
| **Company Insights** | Mission & market position, recent strategic initiatives (2024-2025), current business challenges (3-4 numbered) |
| **Role Success Criteria** | Numbered list: what success requires (7 criteria for SysAid example) |
| **Alignment Matrix** | Per-need breakdown: Need title → Evidence (specific facts) → Business Impact |
| **Core Value Proposition Statement** | 2-paragraph summary of the "rare combination" narrative |
| **Key Differentiators** | 5 numbered differentiators, each with title + 2-3 sentence explanation |
| **Gaps & Strategic Reframes** | Per gap: Reality (honest) + Strategic Reframe (how to address) |
| **Messaging & Tone Guidance** | Recommended communication approach (4-5 paragraphs) + ATS keywords (primary/secondary) |
| **Verification Summary** | Confidence levels (HIGH/MEDIUM/GROWTH) + Key Evidence Sources |
| **Final Strategic Recommendation** | Narrative + explicit "PROCEED / DO NOT APPLY" signal |

---

## 7. Gap Analysis: Current vs. Ground Truth

### Schema gaps

| DOCX / vpr.json section | In current VPR model | Notes |
|---|---|---|
| `metadata` (reportDate, candidateName, targetRole, targetCompany) | ❌ Not present | Only application_id/user_id stored |
| `executiveSummary.overallFitScore` (0-100) | ❌ Not present | — |
| `executiveSummary.topThreeStrengths` (structured) | ❌ Not present | — |
| `executiveSummary.topThreeConcerns` (structured) | ❌ Not present | — |
| `executiveSummary.recommendedApproach` (enum) | ❌ Not present | DOCX has "PROCEED / DO NOT APPLY" narrative |
| `roleAlignment.coreResponsibilities[]` | ❌ Not present | Closest: `evidence_matrix[]` (flat, not structured by responsibility) |
| `roleAlignment.requirementBreakdown` (mustHave/niceToHave/prerequisites) | ❌ Not present | — |
| `experienceMapping.relevantExperiences[]` (chronological, with metrics) | ❌ Not present | — |
| `experienceMapping.experienceGaps[]` | ⚠️ Partial: `gap_strategies[]` has mitigation only | Missing: impactOnCandidacy enum, compensatingFactors[] |
| `skillsAnalysis.technicalSkills[]` (with proficiency levels) | ❌ Not present | `keywords[]` is flat list |
| `skillsAnalysis.softSkills[]` | ❌ Not present | — |
| `skillsAnalysis.toolProficiency[]` | ❌ Not present | — |
| `evidenceGaps.identifiedGaps[]` (severity, action items, timelines) | ❌ Not present | — |
| `evidenceGaps.priorityGapsToAddress[]` (ranked, with deadlines) | ❌ Not present | — |
| `differentiators.uniqueStrengths[]` (with rarity + proof) | ⚠️ Partial: `differentiators[]` is flat strings | No rarity, no proof citation |
| `differentiators.competitiveAdvantages[]` | ❌ Not present | — |
| `differentiators.positioningStatement` | ❌ Not present | — |
| `concernsAndMitigations.likelyObjections[]` | ❌ Not present | — |
| `concernsAndMitigations.preemptiveResponses[]` | ❌ Not present | — |
| `valueProposition.primaryValue` (statement + evidence + outcome) | ❌ Not present | Only implied in executive_summary |
| `valueProposition.secondaryValues[]` | ❌ Not present | — |
| `valueProposition.quantifiedImpact[]` | ❌ Not present | — |
| `valueProposition.elevatorPitch` | ❌ Not present | — |
| `applicationStrategy.cvCustomization` | ❌ Not present | — |
| `applicationStrategy.coverLetterStructure` | ❌ Not present | Separate document |
| `applicationStrategy.linkedInOutreach` | ❌ Not present | Separate document |
| `applicationStrategy.interviewPreparation` | ❌ Not present | Separate document |
| Company Insights (from DOCX) | ⚠️ Fed as input via `company_context` | Not persisted in VPR output schema |
| Verification Summary (from DOCX) | ❌ Not present | Unique to DOCX, not in vpr.json either |

### Naming convention

| Current | Ground truth |
|---|---|
| `snake_case` | `camelCase` |
| `executive_summary` (str) | `executiveSummary` (object) |
| `alignment_score: STRONG\|MODERATE\|DEVELOPING` | `alignmentScore: integer 0-100` + `evidenceQuality: direct\|analogous\|transferable\|weak` |

### Generation approach

| Current | Ground truth (prompt.md) |
|---|---|
| Stages 1-2 rule-based; 3-4 LLM; 5 rule-based | 3-phase LLM-driven (Phase 1: gap analysis, Phase 2: VPR generation, Phase 3: materials) |
| Stage 6: anti-AI gate only | 6 structural validation rules (evidence traceability, quantification consistency, alignment score justification, gap severity calibration, differentiator rarity, mitigation substance) |

---

## 8. Valuable Elements in Current Implementation (NOT in vpr.json spec)

These are implementation patterns that should be **preserved or elevated** in any upgrade:

| Element | Location | Value |
|---|---|---|
| **Rule-based pre-processing (Stages 1-2)** | `vpr_generator.py:_analyze_input`, `_extract_evidence` | Cheaper than full LLM; reduces hallucination by giving Stage 3 pre-matched evidence instead of raw CV |
| **8-pattern anti-AI scoring** | `fvs_validator.py:check_anti_ai_patterns` | Quantitative quality gate with specific deduction logic; deterministic and auditable |
| **Regeneration loop with feedback** | `vpr_generator.py:run()` | Up to 3 retries; Stage 6 failure message injected as feedback into Stage 3/4 prompts |
| **Rule-based Stage 4 fallback** | `vpr_generator.py:_self_correct` | Resilience: if LLM fails, banned-term replacement runs instead of crashing |
| **FVS fact validation** | `fvs_validator.py:validate_vpr_against_cv` | Detects hallucinated company names, years, and job titles in VPR output (CRITICAL severity) |
| **Extended quality checks** | `fvs_validator.py:validate_grammar/tone` | Grammar, tone, ATS, consistency scoring already implemented — not yet wired into VPR pipeline gate |
| **Token/cost tracking** | `vpr_generator.py:TokenUsage` | Per-generation cost visibility |
| **Language support (en/he)** | `VPR.language` | Hebrew as V1 feature |
| **Idempotency** | `VPR.application_id` + `VPR.user_id` | Retrieve existing VPR for same application |
| **Company context in prompt** | `VPRRequest.company_context` | Feeds rich Company Insights section (visible in DOCX); must survive schema upgrade |

---

## 9. Upgrade Spec (No Code Changes — Specification Only)

### 9.1 Pydantic model changes needed

Replace the flat `VPR` model with a 10-section model matching `vpr.json`. Key decisions:

- **Naming:** Use camelCase with Pydantic `model_config = ConfigDict(populate_by_name=True)` or `alias_generator` — avoids snake_case leaking into JSON
- **`alignment_score`:** Change from `STRONG|MODERATE|DEVELOPING` enum to integer 0-100 (per vpr.json) with separate `evidenceQuality: Literal["direct", "analogous", "transferable", "weak"]`
- **`executive_summary`:** Expand from free-text string to structured object: `overallFitScore`, `fitRationale`, `topThreeStrengths[]`, `topThreeConcerns[]`, `recommendedApproach`
- **`differentiators`:** Replace `list[str]` with structured object: `uniqueStrengths[]` (with rarity/proof), `competitiveAdvantages[]`, `positioningStatement`
- **Add new sections:** `metadata`, `roleAlignment`, `experienceMapping`, `skillsAnalysis`, `evidenceGaps`, `concernsAndMitigations`, `valueProposition`, `applicationStrategy`
- **Company Insights:** Add `companyInsights` section to schema (sourced from `company_context` input) — this appears in DOCX but is not in vpr.json; must decide whether to persist it in the model
- **Verification Summary:** Add `verificationSummary` section (HIGH/MEDIUM/GROWTH confidence levels per evidence type) — in DOCX but not in vpr.json

### 9.2 Prompt changes needed

Replace Stage 3/4 prompts with the 3-phase prompt architecture from `prompt.md` Part 2:

- **Phase 1 prompt (Prompt 1.1):** Initial gap analysis → clarifying questions
- **Phase 1 prompt (Prompt 1.2):** Process gap responses → updated candidate profile
- **Phase 2 prompt (Prompt 2.1):** Generate complete VPR JSON per 10-section schema
- **Phase 2 prompt (Prompt 2.2):** Validate and refine VPR (structural validation pass)

**Preserve:** Stages 1-2 rule-based pre-processing as input conditioning before Phase 2 LLM call.

**Preserve:** Regeneration loop with feedback (up to 3 retries on quality gate failure).

### 9.3 Validation changes needed

Replace the single anti-AI gate with 6 structural rules from `prompt.md` Part 3:

1. **Evidence traceability** — every claim must trace to CV or gap_responses
2. **Quantification consistency** — metrics must match exactly across all sections
3. **Alignment score justification** — 0-100 scores must use rubric (direct=80-100, analogous=60-79, transferable=40-59, weak=<40)
4. **Gap severity calibration** — critical/high/medium/low definitions applied consistently
5. **Differentiator rarity check** — very_rare/uncommon/somewhat_rare validated against claim
6. **Mitigation strategy substance** — must be specific and actionable (not generic)

**Preserve and extend:** 8-pattern anti-AI scoring (keep as one of the gate checks).

**Wire in existing but unused checks:** Grammar (≥9.0), Tone (≥8.0), ATS (≥8.0) from `fvs_validator.py`.

### 9.4 Frontend/export changes needed

The UI renderer and PDF/DOCX export template must be updated to consume the new 10-section schema. The DOCX ground truth is the authoritative reference for visual layout and section ordering:

| DOCX section | Maps to vpr.json property | Render priority |
|---|---|---|
| Header | `metadata` | Required |
| Executive Summary | `executiveSummary` (full object) | Required |
| Company Insights | `companyInsights` (to be added) | Required |
| Role Success Criteria | `roleAlignment.coreResponsibilities[]` | Required |
| Alignment Matrix | `roleAlignment` + `evidenceGaps` | Required |
| Core Value Proposition | `valueProposition.primaryValue` | Required |
| Key Differentiators | `differentiators.uniqueStrengths[]` | Required |
| Gaps & Reframes | `evidenceGaps` + `concernsAndMitigations` | Required |
| Messaging Guidance | `applicationStrategy.cvCustomization` | Required |
| ATS Keywords | `applicationStrategy.cvCustomization.keywordOptimization` | Required |
| Verification Summary | `verificationSummary` (to be added) | Required |
| Final Recommendation | `executiveSummary.recommendedApproach` (expanded) | Required |
