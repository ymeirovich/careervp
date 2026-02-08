"""
CV Parser Logic - Extracts structured data from uploaded CVs.
Per docs/specs/01-cv-parser.md.

Uses Haiku 4.5 for cost-optimized extraction.
Supports English and Hebrew (RTL) documents.
"""

import json
import re
from typing import Any, Dict, Literal

from langdetect import LangDetectException, detect

from careervp.handlers.utils.observability import logger, tracer
from careervp.logic.utils.llm_client import TaskMode, get_llm_router
from careervp.models.cv import (
    Certification,
    ContactInfo,
    CVParseResponse,
    Education,
    UserCV,
    WorkExperience,
)
from careervp.models.result import Result, ResultCode

# CV Extraction System Prompt
CV_EXTRACTION_PROMPT = """You are an expert CV/Resume parser. Extract structured information from the provided CV text.

CRITICAL RULES:
1. Extract ONLY information that exists in the CV - NEVER invent or assume
2. Preserve exact dates as written (e.g., "2021 – Present", "Jan 2020 - Dec 2023")
3. Preserve exact company names and job titles as written
4. Preserve exact degree names and institution names as written
5. For Hebrew CVs, maintain RTL text order in your JSON output

OUTPUT FORMAT:
Return a valid JSON object with this exact structure:
{
  "full_name": "string",
  "contact_info": {
    "phone": "string or null",
    "email": "string or null",
    "location": "string or null",
    "linkedin": "string or null"
  },
  "experience": [
    {
      "company": "string",
      "role": "string",
      "dates": "string (preserve exact format)",
      "achievements": ["string", "string"]
    }
  ],
  "education": [
    {
      "institution": "string",
      "degree": "string",
      "field_of_study": "string or null",
      "graduation_date": "string or null"
    }
  ],
  "certifications": [
    {
      "name": "string",
      "issuer": "string or null",
      "date": "string or null"
    }
  ],
  "skills": ["string", "string"],
  "top_achievements": ["string (quantified if possible)", "string", "string"],
  "professional_summary": "string or null"
}

EXTRACTION GUIDELINES:
- Focus on the 10 core attributes: Contact Info, Work History, Education, Certifications, 5 Core Skills, 3 Quantified Achievements
- For achievements, prioritize quantified results (e.g., "Increased sales by 40%")
- Skills should be extracted from both explicit skills sections AND implied from experience
- Maximum 5 core skills, 3 top achievements
- If information is ambiguous or unclear, omit rather than guess

CV TEXT:
"""


def detect_language(text: str) -> Literal['en', 'he']:
    """
    Detect CV language using langdetect.
    Per 01-cv-parser.md: Use langdetect to set {language} variable.
    """
    try:
        detected = detect(text)
        if detected == 'he':
            return 'he'
        return 'en'
    except LangDetectException:
        logger.warning('Language detection failed, defaulting to English')
        return 'en'


def extract_text_from_pdf(pdf_content: bytes) -> str:
    """Extract text from PDF using PyPDF2."""
    try:
        from io import BytesIO

        from PyPDF2 import PdfReader

        reader = PdfReader(BytesIO(pdf_content))
        text_parts = []
        for page in reader.pages:
            text_parts.append(page.extract_text() or '')
        return '\n'.join(text_parts)
    except Exception as e:
        logger.error('PDF extraction failed', error=str(e))
        raise ValueError(f'Failed to extract text from PDF: {e}') from e


def extract_text_from_docx(docx_content: bytes) -> str:
    """Extract text from DOCX using python-docx."""
    try:
        from io import BytesIO

        from docx import Document

        doc = Document(BytesIO(docx_content))
        text_parts = []
        for paragraph in doc.paragraphs:
            text_parts.append(paragraph.text)
        return '\n'.join(text_parts)
    except Exception as e:
        logger.error('DOCX extraction failed', error=str(e))
        raise ValueError(f'Failed to extract text from DOCX: {e}') from e


def clean_text(text: str) -> str:
    """
    Clean extracted text by removing excessive whitespace.
    Per 01-cv-parser.md Step 2: Strip excessive whitespace and non-standard characters.
    """
    # Remove multiple consecutive newlines
    text = re.sub(r'\n{3,}', '\n\n', text)
    # Remove multiple consecutive spaces
    text = re.sub(r' {2,}', ' ', text)
    # Strip leading/trailing whitespace from each line
    lines = [line.strip() for line in text.split('\n')]
    return '\n'.join(lines)


def parse_llm_response(response_text: str) -> Dict[str, Any]:
    """Parse JSON from LLM response, handling potential markdown code blocks."""
    # Remove markdown code blocks if present
    text = response_text.strip()
    if text.startswith('```json'):
        text = text[7:]
    elif text.startswith('```'):
        text = text[3:]
    if text.endswith('```'):
        text = text[:-3]

    parsed: Dict[str, Any] = json.loads(text.strip())
    if not isinstance(parsed, dict):
        raise ValueError('Parsed response is not a dictionary')
    return parsed


@tracer.capture_method(capture_response=False)
def parse_cv(  # noqa: C901 - consolidates extraction, cleaning, LLM parsing, and validation
    user_id: str,
    cv_text: str | None = None,
    cv_content: bytes | None = None,
    file_type: Literal['pdf', 'docx', 'txt'] | None = None,
) -> Result[UserCV]:
    """
    Parse a CV and extract structured data.

    Per docs/specs/01-cv-parser.md:
    1. Extract: Use PyPDF2 or python-docx to pull raw text
    2. Clean: Strip excessive whitespace and non-standard characters
    3. Analyze: Send text to Haiku 4.5 with extraction schema
    4. Validate: Verify extraction against Pydantic UserCV model

    Args:
        user_id: User ID to associate with parsed CV
        cv_text: Plain text CV content (if already extracted)
        cv_content: Raw file bytes (PDF or DOCX)
        file_type: File type if cv_content provided

    Returns:
        Result[UserCV] with parsed CV data or error
    """
    logger.info('Starting CV parsing', user_id=user_id, has_text=bool(cv_text), file_type=file_type)

    # Step 1: Extract text from file if needed
    if cv_text is None:
        if cv_content is None:
            return Result(success=False, error='Either cv_text or cv_content must be provided', code=ResultCode.MISSING_REQUIRED_FIELD)

        if file_type == 'pdf':
            cv_text = extract_text_from_pdf(cv_content)
        elif file_type == 'docx':
            cv_text = extract_text_from_docx(cv_content)
        elif file_type == 'txt':
            cv_text = cv_content.decode('utf-8')
        else:
            return Result(success=False, error=f'Unsupported file type: {file_type}', code=ResultCode.UNSUPPORTED_FILE_FORMAT)

    # Step 2: Clean the text
    cv_text = clean_text(cv_text)

    if len(cv_text) < 100:
        return Result(success=False, error='CV text too short (minimum 100 characters)', code=ResultCode.INVALID_INPUT)

    # Detect language
    language = detect_language(cv_text)
    logger.info('Language detected', language=language)

    # Step 3: Send to Haiku 4.5 for extraction
    llm_router = get_llm_router()

    # Add language context to prompt
    language_instruction = ''
    if language == 'he':
        language_instruction = '\n\nNOTE: This CV is in Hebrew. Maintain RTL text integrity in your JSON output.'

    full_prompt = f'{CV_EXTRACTION_PROMPT}{language_instruction}\n\n{cv_text}'

    llm_result = llm_router.invoke(
        mode=TaskMode.TEMPLATE,  # Uses Haiku 4.5
        system_prompt='You are a CV parsing assistant. Return only valid JSON.',
        user_prompt=full_prompt,
        max_tokens=3000,
        temperature=0.1,  # Low temperature for consistent extraction
    )

    if not llm_result.success:
        logger.error('LLM extraction failed', error=llm_result.error)
        return Result(success=False, error=f'LLM extraction failed: {llm_result.error}', code=llm_result.code)

    # Step 4: Parse and validate response
    llm_data: Dict[str, Any] = llm_result.data or {}
    try:
        extracted_data = parse_llm_response(str(llm_data.get('text', '')))
    except json.JSONDecodeError as e:
        logger.error('Failed to parse LLM JSON response', error=str(e), response=str(llm_data.get('text', ''))[:500])
        return Result(success=False, error=f'Failed to parse extraction result: {e}', code=ResultCode.INTERNAL_ERROR)

    # Build UserCV model
    try:
        contact_info = ContactInfo(
            phone=extracted_data.get('contact_info', {}).get('phone'),
            email=extracted_data.get('contact_info', {}).get('email'),
            location=extracted_data.get('contact_info', {}).get('location'),
            linkedin=extracted_data.get('contact_info', {}).get('linkedin'),
        )

        experience = [
            WorkExperience(
                company=exp.get('company', 'Unknown'),
                role=exp.get('role', 'Unknown'),
                dates=exp.get('dates', 'Unknown'),
                achievements=exp.get('achievements', []),
            )
            for exp in extracted_data.get('experience', [])
        ]

        education = [
            Education(
                institution=edu.get('institution', 'Unknown'),
                degree=edu.get('degree', 'Unknown'),
                field_of_study=edu.get('field_of_study'),
                graduation_date=edu.get('graduation_date'),
            )
            for edu in extracted_data.get('education', [])
        ]

        certifications = [
            Certification(
                name=cert.get('name', 'Unknown'),
                issuer=cert.get('issuer'),
                date=cert.get('date'),
            )
            for cert in extracted_data.get('certifications', [])
        ]

        user_cv = UserCV(
            user_id=user_id,
            full_name=extracted_data.get('full_name', 'Unknown'),
            language=language,
            contact_info=contact_info,
            experience=experience,
            education=education,
            certifications=certifications,
            skills=extracted_data.get('skills', [])[:50],  # Max 50 skills
            top_achievements=extracted_data.get('top_achievements', [])[:3],  # Max 3
            professional_summary=extracted_data.get('professional_summary'),
            is_parsed=True,
        )

        logger.info(
            'CV parsed successfully',
            user_id=user_id,
            language=language,
            experience_count=len(experience),
            skills_count=len(user_cv.skills),
            input_tokens=llm_data.get('input_tokens'),
            output_tokens=llm_data.get('output_tokens'),
            cost=llm_data.get('cost'),
        )

        return Result(success=True, data=user_cv, code=ResultCode.CV_PARSED)

    except Exception as e:
        logger.exception('Failed to build UserCV model', error=str(e))
        return Result(success=False, error=f'Failed to validate extracted data: {e}', code=ResultCode.INTERNAL_ERROR)


def create_cv_parse_response(result: Result[UserCV]) -> CVParseResponse:
    """Convert Result[UserCV] to CVParseResponse for API response."""
    if result.success and result.data:
        return CVParseResponse(
            success=True,
            user_cv=result.data,
            language_detected=result.data.language,
            error=None,
        )
    return CVParseResponse(
        success=False,
        user_cv=None,
        language_detected='en',
        error=result.error,
    )
