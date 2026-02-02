"""
VPR Generator logic per docs/specs/03-vpr-generator.md (lines 91-104).
Handles prompt assembly, Sonnet 4.5 invocation, parsing, FVS validation,
and persistence using the Result pattern for safety.
"""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, cast

from careervp.logic.fvs_validator import validate_vpr_against_cv
from careervp.logic.prompts.vpr_prompt import build_vpr_prompt

if TYPE_CHECKING:
    TaskMode = Any

    def get_llm_router() -> Any: ...  # pragma: no cover
else:
    from careervp.logic.utils.llm_client import TaskMode, get_llm_router
from careervp.models.cv import UserCV
from careervp.models.result import Result, ResultCode
from careervp.models.vpr import (
    VPR,
    EvidenceItem,
    GapStrategy,
    TokenUsage,
    VPRRequest,
    VPRResponse,
)

if TYPE_CHECKING:
    from careervp.dal.dynamo_dal_handler import DynamoDalHandler

SYSTEM_PROMPT = 'You are CareerVP VPR Generator. Follow docs/specs/03-vpr-generator.md instructions exactly.'


class LLMClient:
    """Thin wrapper so Strict Alignment mode can patch LLM usage easily."""

    def __init__(self) -> None:
        self._router: Any = get_llm_router()

    def invoke(self, prompt: str, task_mode: TaskMode, max_tokens: int, temperature: float) -> Result[dict[str, Any]]:
        """Delegate to centralized router (spec line 96: Sonnet 4.5 via TaskMode.STRATEGIC)."""
        result = self._router.invoke(
            mode=task_mode,
            system_prompt=SYSTEM_PROMPT,
            user_prompt=prompt,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        return cast(Result[dict[str, Any]], result)


def generate_vpr(request: VPRRequest, user_cv: UserCV, dal: DynamoDalHandler) -> Result[VPRResponse]:
    """
    Generate a Value Proposition Report (spec lines 91-104).

    Flow:
      1. Build prompt with CV/job/gap data (line 95).
      2. Invoke Sonnet 4.5 via TaskMode.STRATEGIC (line 96).
      3. Parse response into VPR model (line 97).
      4. Validate IMMUTABLE facts via FVS (line 98).
      5. Persist + respond (lines 99-100).
    """
    start_time = time.perf_counter()

    prompt = build_vpr_prompt(user_cv, request)

    llm_client = LLMClient()
    llm_result = llm_client.invoke(
        prompt=prompt,
        task_mode=TaskMode.STRATEGIC,
        max_tokens=4000,
        temperature=0.7,
    )

    if not llm_result.success or not llm_result.data:
        return Result(
            success=False,
            error=llm_result.error or 'LLM invocation failed',
            code=llm_result.code if llm_result.code else ResultCode.LLM_API_ERROR,
        )

    raw_text = llm_result.data.get('text', '').strip()
    if not raw_text:
        return Result(
            success=False,
            error='LLM returned empty response',
            code=ResultCode.LLM_API_ERROR,
        )

    try:
        vpr = _parse_llm_response(raw_text, request)
    except ValueError as exc:
        return Result(
            success=False,
            error=f'Failed to parse LLM response: {exc}',
            code=ResultCode.INVALID_INPUT,
        )

    # FVS: IMMUTABLE - verify evidence dates/companies/titles against source CV.
    fvs_result = validate_vpr_against_cv(vpr, user_cv)
    if not fvs_result.success:
        return Result(
            success=False,
            error=fvs_result.error or 'FVS validation failed',
            code=fvs_result.code,
            data=VPRResponse(
                success=False,
                vpr=None,
                token_usage=None,
                generation_time_ms=0,
                error=fvs_result.error or 'FVS validation failed',
            ),
        )

    vpr.word_count = _calculate_word_count(vpr)
    generation_time_ms = int((time.perf_counter() - start_time) * 1000)

    token_usage = TokenUsage(
        input_tokens=llm_result.data.get('input_tokens', 0),
        output_tokens=llm_result.data.get('output_tokens', 0),
        cost_usd=llm_result.data.get('cost', 0.0),
        model=llm_result.data.get('model', 'claude-sonnet-4-5'),
    )

    save_result = dal.save_vpr(vpr)
    if not save_result.success:
        return Result(
            success=False,
            error=save_result.error or 'Failed to persist VPR',
            code=save_result.code,
        )

    response = VPRResponse(
        success=True,
        vpr=vpr,
        token_usage=token_usage,
        generation_time_ms=generation_time_ms,
    )

    return Result(success=True, data=response, code=ResultCode.VPR_GENERATED)


def _parse_llm_response(response_text: str, request: VPRRequest) -> VPR:
    """
    Parse structured JSON response produced by Sonnet (spec line 97).
    Handles LLM responses that may be wrapped in code blocks.
    """
    # Strip code block markers if present
    cleaned_text = response_text.strip()
    if cleaned_text.startswith('```'):
        # Remove opening code block
        first_newline = cleaned_text.find('\n')
        if first_newline != -1:
            cleaned_text = cleaned_text[first_newline + 1 :]
        # Remove closing code block
        if cleaned_text.endswith('```'):
            cleaned_text = cleaned_text[:-3]
        cleaned_text = cleaned_text.strip()

    try:
        payload = json.loads(cleaned_text)
    except json.JSONDecodeError as exc:
        raise ValueError(f'LLM response is not valid JSON: {exc}') from exc

    evidence_items = [
        EvidenceItem(
            requirement=item.get('requirement', ''),
            evidence=item.get('evidence', ''),
            alignment_score=item.get('alignment_score', 'MODERATE'),
            impact_potential=item.get('impact_potential', ''),
        )
        for item in payload.get('evidence_matrix', []) or []
    ]

    gap_entries_raw = payload.get('gap_strategies', [])
    if gap_entries_raw is None:
        gap_entries = []
    elif isinstance(gap_entries_raw, list):
        gap_entries = gap_entries_raw
    else:
        gap_entries = [gap_entries_raw]
    gap_strategies = [
        GapStrategy(
            gap=entry.get('gap', ''),
            mitigation_approach=entry.get('mitigation_approach', ''),
            transferable_skills=_ensure_str_list(entry.get('transferable_skills')),
        )
        for entry in gap_entries
    ]

    differentiators = _ensure_str_list(payload.get('differentiators'))
    talking_points = _ensure_str_list(payload.get('talking_points'))
    keywords = _ensure_str_list(payload.get('keywords'))

    vpr = VPR(
        application_id=request.application_id,
        user_id=request.user_id,
        executive_summary=payload.get('executive_summary', ''),
        evidence_matrix=evidence_items,
        differentiators=differentiators,
        gap_strategies=gap_strategies,
        cultural_fit=payload.get('cultural_fit'),
        talking_points=talking_points,
        keywords=keywords,
        language=payload.get('language', request.job_posting.language),
        version=int(payload.get('version', 1)),
        created_at=datetime.now(timezone.utc),
        word_count=int(payload.get('word_count', 0)),
    )

    return vpr


def _calculate_word_count(vpr: VPR) -> int:
    """Count words across all textual sections (success criteria line 157)."""
    sections: list[str] = [
        vpr.executive_summary or '',
        vpr.cultural_fit or '',
    ]
    sections.extend(vpr.differentiators)
    sections.extend(vpr.talking_points)
    sections.extend(vpr.keywords)

    for evidence in vpr.evidence_matrix:
        sections.extend([evidence.requirement, evidence.evidence, evidence.impact_potential])

    for strategy in vpr.gap_strategies:
        sections.extend(
            [
                strategy.gap,
                strategy.mitigation_approach,
                ' '.join(strategy.transferable_skills),
            ]
        )

    joined = ' '.join(sections)
    return len([word for word in joined.split() if word])


def _ensure_str_list(value: object) -> list[str]:
    """Utility to coerce payload entries into simple string lists."""
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value]
    return [str(value)]
