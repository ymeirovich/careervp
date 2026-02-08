"""Logic layer for CV Tailoring (Handler -> Logic -> DAL)."""

from __future__ import annotations

import hashlib
import time
from typing import Any

from careervp.dal.dynamo_dal_handler import DynamoDalHandler
from careervp.handlers.utils.observability import logger
from careervp.logic.cv_tailoring import create_fvs_baseline, tailor_cv
from careervp.logic.llm_client import LLMClient
from careervp.models.cv_tailoring_models import TailorCVRequest, TailoredCVResponse
from careervp.models.result import Result, ResultCode


class RetryingLLMClient:
    """Thin wrapper to add retry logic around LLMClient.generate."""

    def __init__(self, client: LLMClient, max_retries: int = 3, base_delay: float = 1.0) -> None:
        self._client = client
        self._max_retries = max_retries
        self._base_delay = base_delay

    def generate(self, prompt: str, timeout: int = 300) -> dict[str, Any]:
        last_exception: Exception | None = None
        for attempt in range(self._max_retries):
            try:
                return self._client.generate(prompt=prompt, timeout=timeout)
            except Exception as exc:  # noqa: BLE001 - retry on transient errors
                last_exception = exc
                delay = self._base_delay * (2**attempt)
                logger.warning('LLM call failed, retrying', attempt=attempt + 1, delay=delay, error=str(exc))
                time.sleep(delay)
        raise last_exception or RuntimeError('LLM retries exhausted')


class CVTailoringLogic:
    """Encapsulates CV tailoring business logic with dependency injection."""

    def __init__(self, dal: DynamoDalHandler, llm_client: LLMClient, fvs_validator: Any | None = None) -> None:
        self.dal = dal
        self.llm_client = llm_client
        self.fvs_validator = fvs_validator

    def tailor_cv(self, request: TailorCVRequest, user_id: str) -> Result[Any]:
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
            response = TailoredCVResponse(success=True, tailored_cv=existing.data)
            return Result(success=True, data=response, code=ResultCode.CV_TAILORED_SUCCESS)

        baseline = create_fvs_baseline(master_cv)
        retrying_llm = RetryingLLMClient(self.llm_client)
        return tailor_cv(
            master_cv=master_cv,
            job_description=request.job_description,
            preferences=request.preferences,
            fvs_baseline=baseline,
            dal=self.dal,
            llm_client=retrying_llm,
        )
