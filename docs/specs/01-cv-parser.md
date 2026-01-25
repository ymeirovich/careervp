# Feature Spec: CV Parsing Engine (F-CV-001)

## Objective
Extract structured JSON data from a user-uploaded PDF/DOCX and save it to the `careervp-users` table.

## Technical Details
- **Trigger:** S3 Upload Event or Direct API POST.
- **Model:** Claude Haiku 4.5 (Cost-optimized for extraction).
- **Memory:** 1024 MB (due to PDF parsing overhead).
- **Storage:** Metadata to `careervp-users`, document to `careervp-job-search-assistant-cvs`.

## Logic Flow
1. **Extract:** Use `PyPDF2` or `python-docx` to pull raw text.
2. **Clean:** Strip excessive whitespace and non-standard characters.
3. **Analyze:** Send text to Haiku 4.5 with the `cv_extraction_schema.json`.
4. **Validate:** Verify extraction against Pydantic `UserCV` model.
5. **Persist:** Update user record in DynamoDB with `is_parsed: true`.

## Success Criteria
- Validated JSON contains: Contact Info, Work History (with dates), Education, and Skills.
- Unit test passes for a 5-page complex PDF.

## Localization & Multi-Language (V1)
- [cite_start]**Primary Languages:** English and Hebrew (RTL)[cite: 90].
- [cite_start]**RTL Implementation:** - Use `python-docx` with `WD_ALIGN_PARAGRAPH.RIGHT` for Hebrew sections[cite: 90].
    - [cite_start]Font Support: Default to Arial or David for Hebrew readability.
    - [cite_start]Date Formats: Use DD/MM/YYYY for Israeli standards[cite: 91].
- [cite_start]**Closing Tag:** For Hebrew cover letters, use "בכבוד רב,"[cite: 133].

## Processing Constraints
- [cite_start]**Question Limits:** During Gap Analysis, limit output to a MAXIMUM of 10 targeted questions to prevent token bloat[cite: 136, 140].
- [cite_start]**Extraction Scope:** Focus on 10 core attributes: Contact Info, Work History, Education, Certifications, 5 Core Skills, and 3 Quantified Achievements[cite: 136].
- [cite_start]**Detection:** Use `langdetect` to automatically set the `{language}` variable for LLM prompts[cite: 90, 94].
