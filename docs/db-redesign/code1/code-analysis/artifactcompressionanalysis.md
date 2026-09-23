# Artifact Compression & Token Reduction — Analysis

**Goal:** Reduce data storage and LLM input tokens by compressing artifacts from their current
format to a more efficient one (e.g., what fields of each source artifact actually need to be
sent/stored for each downstream generation).

**Date:** 2026-06-30
**Status:** Discovery / scoping (no implementation)

---

## TL;DR

The core problem is **not** "invent a compression strategy from scratch." Your codebase already
contains the exact pattern (`build_vpr_digest`, `build_cv_digest`, `CVSummarizer`) — it was just
never **formalized, measured, or applied consistently**. The work is to formalize the digest
concept, measure where tokens actually go, and apply projections everywhere (not just two of five
generation steps).

There are **three independent levers** being conflated in the goal. Separate them:

| Lever | What it changes | Risk | Payoff | Priority |
|---|---|---|---|---|
| **A. Content projection** (which fields are sent) | LLM input tokens | Medium (quality) | High (~90% on full→digest) | **1st** |
| **B. Serialization encoding** (JSON → TOON/YAML) | LLM input tokens | Low (lossless) | Marginal (~30–40% on uniform arrays) | 2nd |
| **C. Storage encoding** (docx→JSON, gzip in S3) | Storage cost only | Low | Low (storage is cheap) | 3rd |

Token cost is the expensive, recurring one. Storage is rounding-error by comparison. **What you
store at rest and what you send to the LLM do not have to be the same representation — and
probably shouldn't be.**

---

## 1. Findings — Current State

### 1.1 The "digest" pattern already exists (but is applied unevenly)

- `build_vpr_digest()` — `logic/prompts/vpr_prompt.py:628-640` — extracts 5 fields from the
  ~10-section VPR: `positioning_statement`, `top_differentiators`, `ats_keywords_primary`,
  `overall_fit_score`, `recommended_approach`.
- `build_cv_digest()` — `logic/prompts/cover_letter_prompt.py:90-105` — name + top 3 roles +
  top 10 skills.
- `CVSummarizer` — `logic/cv_summarizer.py` — lossy truncation when CV > ~2000 tokens
  (drop older jobs → trim skills → shorten education → shorten summary).

### 1.2 What each generation step actually sends today

| Generation step | Source artifacts sent | Projected? |
|---|---|---|
| **Gap Analysis** | Full CV (`model_dump`) + full Job Posting (`model_dump`) | ❌ whole |
| **VPR synthesis** | Full CV facts + full Job + **full Gap responses** + Company research | ❌ whole |
| **Tailored CV** | VPR **digest** (5 fields) + CV + job description | ✅ VPR digested |
| **Cover Letter** | CV **digest** + VPR **digest** + gap responses + company research | ✅ both digested |
| **Interview Prep** | **Full VPR dict** + full CV facts + full job requirements | ❌ whole |

**Worst offenders (highest-value targets):** full VPR → Interview Prep; full CV + full job →
Gap Analysis; full Gap responses → VPR synthesis.

### 1.3 Dependency graph (`logic/artifact_dependency_resolver.py:50-58`)

```
gap_analysis → company_research → vpr → { cv_tailored, cover_letter, interview_prep }
```

These edges define *where* projections are needed; the open question is *what payload* rides each
edge.

### 1.4 Storage

- Mostly **JSON in DynamoDB already** (not docx). Sort-key prefixes per artifact in
  `dal/dynamo_dal_handler.py:23-32`.
- Base CV may arrive as docx and is parsed to `UserCV` JSON (`models/cv.py`).
- Tailored CVs carry a 90-day TTL (`dal/cv_dal.py:41`).
- Implication: the "docx → JSON" framing is largely **already done** for stored artifacts; the
  remaining storage lever is gzip/compaction, which is low value.

### 1.5 Token measurement is crude

- Token count is estimated as `len(text) / 4` (`logic/cv_summarizer.py:245`). No real tokenizer.
- No per-step, per-source-artifact token instrumentation exists.
- **You cannot optimize or prove savings without first fixing this.**

---

## 2. Recommended Approach

1. **Measure before cutting.** Add real token counting (Anthropic count_tokens / tokenizer).
   Instrument every generation to log input tokens **per source artifact, per step**. This is the
   baseline that justifies and de-risks everything else.
2. **Build the dependency × field matrix empirically.** For each downstream artifact, run an
   ablation over 10–20 representative cases: generate with full inputs (golden), then regenerate
   dropping field groups, and diff quality. Output = a table (rows: source fields; columns:
   consumers; cells: needed/ignored). **That table is the digest spec.**
3. **Formalize "digest" as a first-class concept.** Give each artifact a versioned
   `to_digest(consumer)` projection (or a small set of named projections) so storage-shape and
   prompt-shape are decoupled and independently testable.
4. **Apply projections to the offenders** in 1.2 (Interview Prep, Gap Analysis, VPR synthesis).
5. **Only then** consider encoding (TOON) at the serialization boundary, uniformly.

**Principle:** store rich, project lean. Keep the full artifact at rest (cheap, needed for the
user view and regeneration); send a purpose-built projection to the model.

---

## 3. Scope

### In scope (v1 of this effort)
- Token instrumentation + baseline measurement.
- The field-dependency (ablation) matrix — the research artifact that justifies the rest.
- Formalized, versioned digest projections for the 3 worst offenders.
- A quality-regression harness to prove "leaner ≠ worse."

### Defer
- TOON / alternative encoding (Lever B) — second pass, after projections.
- Storage-format / gzip changes (Lever C) — separate, low-priority track.
- **Anthropic prompt caching** — defer building, but evaluate the cost math **now** (see 5.3),
  because it may reprioritize the whole effort.

---

## 4. Questions to Answer

- **Cost breakdown:** which step × which source artifact dominates input tokens? Optimize the top
  2; ignore the long tail.
- **Quality bar & regression measurement:** what's the acceptance threshold, and is there an eval
  set? If not, that's a prerequisite, not optional.
- **Consumer = LLM or human?** What the model needs (lean digest) differs from what the user
  needs to view/download (full artifact). Don't conflate.
- **Regeneration / feedback loops:** VPR supports regeneration with feedback
  (`build_phase2_prompt`). If source detail is discarded, can it still regenerate well?
- **Lossy vs lossless per artifact:** digests (Lever A) are deliberately lossy; encoding
  (Lever B) must be lossless. Be explicit per artifact.

---

## 5. Concerns / Blind Spots

### 5.1 Fact-verification will fight aggressive CV compression
You have an FVS and immutable/verifiable tiers (`models/cv.py`,
`Stage3Result.fact_verification_passed`). Strip CV detail before tailoring and the model can
"hallucinate" facts that *were* in the source CV but not the digest — which your own verifier then
rejects. **Fact-bearing artifacts (CV) are riskier to digest than strategic ones (VPR).** The CV
may need to stay near-full where fact grounding matters.

### 5.2 Anti-AI-detection needs raw material
The 8-pattern avoidance framework (CLAUDE.md, Decision 1.6) and natural-voice output rely on the
model having varied, specific source detail. Over-compress → outputs get generic and *more*
detectable. **Compression and "human-sounding" pull in opposite directions** — tune, don't
maximize.

### 5.3 Prompt caching may dominate the entire analysis
Anthropic prompt caching gives a large discount (~90%) on cached input tokens. The same VPR/CV is
reused across Tailored CV + Cover Letter + Interview Prep in a session. Caching the shared prefix
could beat field-projection on cost **with zero quality risk** — and reorder the whole priority
list. **Verify current caching pricing/mechanics against live API docs before committing to
digests.**

### 5.4 Output tokens, not just input
Projection shrinks inputs, not the generated VPR/CV/letter. If output is a large share of cost,
input projection has a ceiling.

### 5.5 Bilingual (English + Hebrew)
Tokens-per-character differ; Hebrew may tokenize less efficiently. Validate savings in **both**
languages and ensure digests don't drop language-specific content.

### 5.6 Versioning / migration
Changing stored artifact shape means old + in-flight records must still deserialize. The
store-rich/project-lean split sidesteps most of this — another reason to keep storage and prompt
shapes separate, and to **version** the projections.

---

## 6. Suggested First Step

Highest leverage: **instrumentation + the ablation matrix**. That single deliverable tells you
whether to invest in digests, TOON, or prompt caching — instead of guessing. Concretely:

1. Token-logging wrapper around the LLM client (real tokenizer; log per source artifact, per step).
2. Ablation script over a sample set producing the dependency × field matrix.
3. A quick prompt-caching cost check (5.3) that may reprioritize everything.
