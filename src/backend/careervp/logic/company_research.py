"""
Company research orchestration logic per docs/specs/02-company-research.md.
Coordinates website scraping, web search fallback, and LLM synthesis.
"""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

from careervp.handlers.utils.observability import logger
from careervp.logic.utils.llm_client import TaskMode, get_llm_router
from careervp.logic.utils.web_scraper import MIN_CONTENT_WORDS, count_words, scrape_company_about_page
from careervp.logic.utils.web_search import aggregate_search_content, search_company_info
from careervp.models.company import CompanyResearchRequest, CompanyResearchResult, ResearchSource
from careervp.models.result import Result, ResultCode

RESEARCH_TIMEOUT = 60.0
STRUCTURE_SYSTEM_PROMPT = 'You are CareerVP company research analyst. Extract structured insights faithfully.'
MAX_PROMPT_WORDS = 800

ContextHint = str


async def research_company(request: CompanyResearchRequest) -> Result[CompanyResearchResult]:
    """
    Research a company using scrape → search → LLM fallback strategy.
    """
    try:
        return await asyncio.wait_for(_research_company_inner(request), timeout=RESEARCH_TIMEOUT)
    except asyncio.TimeoutError:
        logger.error('Company research timed out', company_name=request.company_name)
        return Result(success=False, error='Company research timed out', code=ResultCode.TIMEOUT)


async def _research_company_inner(request: CompanyResearchRequest) -> Result[CompanyResearchResult]:
    logger.info('Starting company research', company_name=request.company_name)

    domain = _resolve_domain(request)

    # Primary path: Website scrape
    if domain:
        website_urls: list[str] = []
        scrape_result = await _try_website_scrape(request, domain=domain, source_urls=website_urls)
        if scrape_result.success and scrape_result.data:
            structured = await _structure_raw_content(
                company_name=request.company_name,
                raw_text=scrape_result.data,
                source=ResearchSource.WEBSITE_SCRAPE,
                source_urls=website_urls,
                word_count=count_words(scrape_result.data),
                context_hint='official website About page text',
            )
            if structured.success:
                logger.info('[RESEARCH_SUCCESS] Source: WEBSITE_SCRAPE', company_name=request.company_name)
            return structured
        logger.warning(
            '[WEB_SEARCH_FALLBACK] Scrape failed, using web search',
            company_name=request.company_name,
            reason=scrape_result.error,
        )
    else:
        logger.warning(
            '[WEB_SEARCH_FALLBACK] Scrape failed, using web search',
            company_name=request.company_name,
            reason='domain_unavailable',
        )

    # Fallback 1: Web search
    search_urls: list[str] = []
    search_result = await _try_web_search(request.company_name, source_urls=search_urls)
    if search_result.success and search_result.data:
        structured = await _structure_raw_content(
            company_name=request.company_name,
            raw_text=search_result.data,
            source=ResearchSource.WEB_SEARCH,
            source_urls=search_urls,
            word_count=count_words(search_result.data),
            context_hint='aggregated web search snippets',
        )
        if structured.success:
            logger.info('[RESEARCH_SUCCESS] Source: WEB_SEARCH', company_name=request.company_name)
        return structured

    # Fallback 2: LLM synthesis from job posting
    logger.warning(
        '[LLM_FALLBACK] All sources failed, using LLM synthesis',
        company_name=request.company_name,
        reason=search_result.error,
    )
    fallback_result = await _try_llm_fallback(request)
    if fallback_result.success:
        logger.info('[RESEARCH_SUCCESS] Source: LLM_FALLBACK', company_name=request.company_name)
        return fallback_result
    return fallback_result


async def _try_website_scrape(
    request: CompanyResearchRequest,
    *,
    domain: str,
    source_urls: list[str] | None = None,
) -> Result[str]:
    base_url = domain.strip()
    captured_url: str | None = None

    def _record_url(url: str) -> None:
        nonlocal captured_url
        captured_url = url

    scrape_result = await scrape_company_about_page(base_url, on_success=_record_url)
    if not scrape_result.success or not scrape_result.data:
        return Result(
            success=False,
            error=scrape_result.error or 'Website scrape failed',
            code=scrape_result.code or ResultCode.SCRAPE_FAILED,
        )

    text = scrape_result.data
    word_count = count_words(text)
    if word_count < MIN_CONTENT_WORDS:
        logger.warning(
            '[SCRAPE_INSUFFICIENT] Word count: <200, triggering web search',
            word_count=word_count,
            company_name=request.company_name,
        )
        return Result(success=False, error='Insufficient website content', code=ResultCode.SCRAPE_FAILED)

    if source_urls is not None:
        source_urls.append(captured_url or base_url)

    return Result(success=True, data=text, code=ResultCode.SUCCESS)


async def _try_web_search(company_name: str, source_urls: list[str] | None = None) -> Result[str]:
    search_result = await search_company_info(company_name)
    if not search_result.success or not search_result.data:
        return Result(
            success=False,
            error=search_result.error or 'Web search failed',
            code=search_result.code or ResultCode.SEARCH_FAILED,
        )

    results = search_result.data
    aggregated = aggregate_search_content(results)
    if source_urls is not None:
        source_urls.extend(str(item.url) for item in results)

    if count_words(aggregated) < MIN_CONTENT_WORDS:
        return Result(success=False, error='Insufficient search snippets', code=ResultCode.SEARCH_FAILED)

    return Result(success=True, data=aggregated, code=ResultCode.SUCCESS)


async def _try_llm_fallback(request: CompanyResearchRequest) -> Result[CompanyResearchResult]:
    if not request.job_posting_text:
        return Result(success=False, error='Job posting text unavailable for fallback', code=ResultCode.ALL_SOURCES_FAILED)

    fallback_urls: list[str] = []
    if request.job_posting_url:
        fallback_urls.append(str(request.job_posting_url))

    return await _structure_raw_content(
        company_name=request.company_name,
        raw_text=request.job_posting_text,
        source=ResearchSource.LLM_FALLBACK,
        source_urls=fallback_urls,
        word_count=count_words(request.job_posting_text),
        context_hint='job posting text (infer culture/mission carefully)',
    )


async def _structure_raw_content(
    *,
    company_name: str,
    raw_text: str,
    source: ResearchSource,
    source_urls: list[str],
    word_count: int,
    context_hint: ContextHint,
) -> Result[CompanyResearchResult]:
    trimmed_text = _truncate_text(raw_text, max_words=MAX_PROMPT_WORDS)
    user_prompt = _build_structure_prompt(company_name, trimmed_text, context_hint)
    router = get_llm_router()

    loop = asyncio.get_running_loop()
    llm_result = await loop.run_in_executor(
        None,
        lambda: router.invoke(
            mode=TaskMode.TEMPLATE,
            system_prompt=STRUCTURE_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            max_tokens=900,
            temperature=0.2,
        ),
    )

    if not llm_result.success or not llm_result.data:
        return Result(
            success=False,
            error=llm_result.error or 'LLM structuring failed',
            code=llm_result.code or ResultCode.LLM_API_ERROR,
        )

    payload = _parse_llm_payload(llm_result.data.get('text', ''))
    if payload is None:
        return Result(success=False, error='Unable to parse LLM response', code=ResultCode.LLM_API_ERROR)

    result_model = CompanyResearchResult(
        company_name=company_name,
        overview=_ensure_text(payload.get('overview')) or _fallback_overview(trimmed_text),
        values=_ensure_list(payload.get('values')),
        mission=_ensure_optional_text(payload.get('mission')),
        strategic_priorities=_ensure_list(payload.get('strategic_priorities')),
        recent_news=_ensure_list(payload.get('recent_news')),
        financial_summary=_ensure_optional_text(payload.get('financial_summary')),
        source=source,
        source_urls=_deduplicate_urls(source_urls),
        confidence_score=_calculate_confidence(source, word_count, payload),
        research_timestamp=datetime.now(timezone.utc),
    )

    return Result(success=True, data=result_model, code=ResultCode.RESEARCH_COMPLETE)


def _build_structure_prompt(company_name: str, raw_text: str, context_hint: ContextHint) -> str:
    return (
        f'Company Name: {company_name}\n'
        f'Source Context: {context_hint}\n\n'
        f'Extract structured company research from the following text. '
        f'Return JSON with keys overview (100-200 words), values (list), mission, strategic_priorities, recent_news, financial_summary.\n'
        f'Text:\n{raw_text}\n'
        'Return ONLY valid JSON.'
    )


def _parse_llm_payload(raw_output: str) -> dict[str, Any] | None:
    if not raw_output:
        return None
    start = raw_output.find('{')
    end = raw_output.rfind('}')
    candidate = raw_output[start : end + 1] if start != -1 and end != -1 and end > start else raw_output
    try:
        payload = json.loads(candidate)
    except json.JSONDecodeError:
        logger.warning('Failed to parse LLM JSON response')
        return None
    if isinstance(payload, dict):
        return payload
    logger.warning('LLM response was not a JSON object')
    return None


def _truncate_text(raw_text: str, max_words: int) -> str:
    words = raw_text.split()
    if len(words) <= max_words:
        return raw_text
    return ' '.join(words[:max_words])


def _fallback_overview(raw_text: str) -> str:
    preview = raw_text.split('\n', 1)[0]
    return preview[:500]


def _ensure_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def _ensure_text(value: Any) -> str:
    if isinstance(value, str):
        return value.strip()
    return ''


def _ensure_optional_text(value: Any) -> str | None:
    text = _ensure_text(value)
    return text or None


def _deduplicate_urls(urls: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for url in urls:
        if url and url not in seen:
            seen.add(url)
            ordered.append(url)
    return ordered


def _calculate_confidence(source: ResearchSource, word_count: int, payload: dict[str, Any]) -> float:
    if source == ResearchSource.WEBSITE_SCRAPE:
        score = 0.9
        if word_count < 300:
            score -= 0.1
    elif source == ResearchSource.WEB_SEARCH:
        score = 0.7
        penalty_fields = ['mission', 'values', 'recent_news', 'strategic_priorities']
        missing = sum(1 for field in penalty_fields if not payload.get(field))
        score -= 0.1 * missing
    else:  # LLM fallback
        score = 0.4
        if word_count > 400:
            score += 0.05
        score = min(score, 0.5)
    return max(0.1, min(score, 0.95))


def _resolve_domain(request: CompanyResearchRequest) -> str | None:
    if request.domain:
        return request.domain
    if request.job_posting_url:
        parsed = urlparse(str(request.job_posting_url))
        if parsed.netloc:
            return parsed.netloc
    return None


__all__ = ['research_company']
