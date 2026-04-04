"""Logic layer for CV Tailoring (Handler -> Logic -> DAL)."""

from __future__ import annotations

import hashlib
import time
from typing import TYPE_CHECKING, Any

from careervp.dal.dynamo_dal_handler import DynamoDalHandler
from careervp.handlers.utils.observability import logger
from careervp.logic.cv_tailoring_pipeline import run_cv_tailoring_pipeline
from careervp.logic.llm_client import LLMClient
from careervp.models.cv_tailoring_models import (
    CompanyContext,
    GapAnalysisResponses,
    ParsedFacts,
    TailorCVRequest,
    TailoredCVResponse,
)
from careervp.models.result import Result, ResultCode

if TYPE_CHECKING:
    from careervp.models.cv import UserCV
    from careervp.models.vpr import VPR


class RetryingLLMClient:
    """Thin wrapper to add retry logic around LLMClient.generate."""

    def __init__(self, client: LLMClient, max_retries: int = 3, base_delay: float = 1.0) -> None:
        self._client = client
        self._max_retries = max_retries
        self._base_delay = base_delay

    def generate(self, prompt: str, timeout: int = 300, cv: Any | None = None) -> dict[str, Any]:
        last_exception: Exception | None = None
        for attempt in range(self._max_retries):
            try:
                return self._client.generate(prompt=prompt, timeout=timeout, cv=cv)
            except Exception as exc:  # noqa: BLE001 - retry on transient errors
                last_exception = exc
                delay = self._base_delay * (2**attempt)
                logger.warning('LLM call failed, retrying', attempt=attempt + 1, delay=delay, error=str(exc))
                time.sleep(delay)
        raise last_exception or RuntimeError('LLM retries exhausted')


class CVTailoringLogic:
    """Encapsulates CV tailoring business logic with dependency injection."""

    def __init__(
        self,
        dal: DynamoDalHandler,
        llm_client: LLMClient,
        fvs_validator: Any | None = None,
        artifact_dal: Any | None = None,
        company_research_dal: Any | None = None,
    ) -> None:
        self.dal = dal
        self.llm_client = llm_client
        self.fvs_validator = fvs_validator
        self.artifact_dal = artifact_dal
        self.company_research_dal = company_research_dal

    def _construct_parsed_facts_from_user_cv(self, cv: 'UserCV') -> ParsedFacts:
        """Construct ParsedFacts from UserCV fields (fallback when cv-parser hasn't run)."""
        logger.warning(f'parsed_facts absent for cv_id={cv.cv_id} — constructing from UserCV fields')

        # Convert work experience
        work_experience = []
        if cv.work_experience:
            for exp in cv.work_experience:
                work_experience.append(
                    {
                        'company': exp.company,
                        'title': exp.role,
                        'start_date': exp.start_date,
                        'end_date': exp.end_date,
                        'is_current': exp.is_current if hasattr(exp, 'is_current') else False,
                        'responsibilities': exp.responsibilities if hasattr(exp, 'responsibilities') else [],
                        'achievements': exp.achievements if hasattr(exp, 'achievements') else [],
                    }
                )

        # Convert skills
        skills: dict[str, list[str]] = {'technical': [], 'soft': []}
        if cv.skills:
            for skill in cv.skills:
                if hasattr(skill, 'name'):
                    skills['technical'].append(skill.name)
                else:
                    skills['technical'].append(str(skill))

        # Convert education
        education = []
        if cv.education:
            for edu in cv.education:
                education.append(
                    {
                        'institution': edu.institution,
                        'degree': edu.degree,
                        'field_of_study': edu.field_of_study,
                        'graduation_date': edu.graduation_date,
                    }
                )

        # Convert certifications
        certifications = []
        if cv.certifications:
            for cert in cv.certifications:
                certifications.append(
                    {
                        'name': cert.name if hasattr(cert, 'name') else str(cert),
                        'issuer': cert.issuer if hasattr(cert, 'issuer') else '',
                        'date': cert.date if hasattr(cert, 'date') else '',
                    }
                )

        return ParsedFacts(
            name=cv.full_name or '',
            email=cv.email or '',
            phone=cv.phone,
            location=cv.location,
            work_experience=work_experience,
            education=education,
            skills=skills,
            certifications=certifications,
            languages=cv.languages or [],
            summary_original=cv.professional_summary or '',
        )

    def _fetch_parsed_facts(self, cv: 'UserCV') -> ParsedFacts:
        """Fetch parsed_facts from cv_record or construct from UserCV.

        Priority 1: If cv_record has parsed_facts JSON → deserialize to ParsedFacts
        Priority 2: If parsed_facts is None → construct from UserCV fields (test data path)
        """
        # Check if cv has parsed_facts attribute (may not be on the model yet)
        # For now, use the fallback construction strategy
        return self._construct_parsed_facts_from_user_cv(cv)

    def _fetch_gap_responses(self, user_id: str, cv_id: str) -> GapAnalysisResponses:
        """Fetch GAP_ANALYSIS_RESPONSES artifact, return empty on failure."""
        if self.artifact_dal is None:
            logger.info('artifact_dal not configured, using empty GapAnalysisResponses')
            return GapAnalysisResponses(responses=[])

        try:
            # Try to fetch gap responses - implementation depends on artifact_dal interface
            # This is a placeholder - actual implementation would call the DAL
            logger.info('Fetching GAP_ANALYSIS_RESPONSES', user_id=user_id, cv_id=cv_id)
            # Placeholder: always return empty for now
            return GapAnalysisResponses(responses=[])
        except Exception as e:  # noqa: BLE001
            logger.warning(
                'gap_responses fetch failed, using empty GapAnalysisResponses',
                error=str(e),
            )
            return GapAnalysisResponses(responses=[])

    def _fetch_company_context(self, company_name: str | None) -> CompanyContext:
        """Fetch company research, return empty context on miss."""
        if not company_name:
            return CompanyContext(company_name='', company_culture='', products_services=[])

        if self.company_research_dal is None:
            logger.info('company_research_dal not configured, using empty CompanyContext')
            return CompanyContext(company_name=company_name, company_culture='', products_services=[])

        try:
            # Placeholder: always return empty for now
            logger.info('Fetching company research', company_name=company_name)
            return CompanyContext(company_name=company_name, company_culture='', products_services=[])
        except Exception as e:  # noqa: BLE001
            logger.warning(
                'company_research fetch failed, using empty CompanyContext',
                error=str(e),
            )
            return CompanyContext(company_name=company_name, company_culture='', products_services=[])

    async def tailor_cv(self, request: TailorCVRequest, user_id: str) -> Result[Any]:
        """Fetch master CV, perform tailoring, and persist artifacts."""
        logger.append_keys(user_id=user_id, cv_id=request.cv_id)

        master_cv = self.dal.get_cv(user_id)
        if master_cv is None:
            return Result(success=False, error='CV not found', code=ResultCode.CV_NOT_FOUND)
        if master_cv.user_id and master_cv.user_id != user_id:
            return Result(success=False, error='Forbidden', code=ResultCode.FORBIDDEN)

        if not master_cv.cv_id or (request.cv_id and master_cv.cv_id != request.cv_id):
            master_cv.cv_id = request.cv_id

        job_hash = hashlib.sha256(request.job_description.encode('utf-8')).hexdigest()
        job_id = request.idempotency_key or job_hash

        existing = self.dal.get_tailored_cv(
            user_id=user_id,
            cv_id=master_cv.cv_id or request.cv_id,
            job_id=job_id,
            version=None,
        )
        if not existing.success:
            return Result(success=False, error=existing.error, code=existing.code)
        if existing.data is not None:
            # P1: Return cv_sections instead of tailored_cv text blob
            response = TailoredCVResponse(success=True, cv_sections=None, metadata={'tailored_cv': existing.data})
            return Result(success=True, data=response, code=ResultCode.CV_TAILORED_SUCCESS)

        retrying_llm = RetryingLLMClient(self.llm_client)

        # Fetch VPR for strategic guidance (optional — graceful degradation)
        vpr: 'VPR | None' = None
        if request.vpr_id:
            vpr_result = self.dal.get_vpr(request.vpr_id)
            if vpr_result.success and vpr_result.data is not None:
                vpr = vpr_result.data
            else:
                logger.warning(
                    'CV tailoring: VPR not found or fetch failed — proceeding without strategic guide',
                    vpr_id=request.vpr_id,
                    error=vpr_result.error,
                )

        # P3: Fetch ground truth inputs
        parsed_facts = self._fetch_parsed_facts(master_cv)
        gap_responses = self._fetch_gap_responses(user_id, master_cv.cv_id or request.cv_id or '')
        company_context = self._fetch_company_context(None)  # TODO: extract from request if available

        # Call the new 3-stage pipeline
        # Note: parsed_facts parameter is named "parsed_facts" in pipeline but typed as UserCV
        # We pass master_cv as the cv and the extracted ParsedFacts for fact verification
        pipeline_result = run_cv_tailoring_pipeline(
            cv=master_cv,
            job_description=request.job_description,
            vpr=vpr,
            gap_responses=gap_responses.model_dump() if gap_responses else None,
            company_context=company_context.model_dump() if company_context else None,
            llm_client=retrying_llm,
            parsed_facts=parsed_facts,
        )

        if not pipeline_result.success:
            return Result(
                success=False,
                error=pipeline_result.error or 'Pipeline failed',
                code=ResultCode.LLM_API_ERROR,
            )

        # Convert Stage3Result to TailoredCVResponse
        stage3 = pipeline_result.data
        response = TailoredCVResponse(
            success=True,
            cv_sections=stage3.cv_sections if stage3 else None,
            fact_verification_passed=stage3.fact_verification_passed if stage3 else False,
        )
        return Result(success=True, data=response, code=ResultCode.CV_TAILORED_SUCCESS)
