"""
Company research orchestration logic per docs/specs/02-company-research.md.
Coordinates managed web research and LLM structuring.
"""

from __future__ import annotations

import asyncio
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any
from urllib.parse import urlparse

from careervp.handlers.utils.observability import logger
from careervp.logic.company_intel_cache import (
    CachedNews,
    CachedProfile,
    acquire_lock,
    company_cache_keys,
    merge_cached_company_research,
    read_news,
    read_profile,
    release_lock,
    write_news,
    write_profile,
)
from careervp.logic.company_research_store import read_cr_artifact
from careervp.logic.llm_cache import DEFAULT_CACHE_TTL_SECONDS, LLMResponseCache
from careervp.logic.prompts.company_research_prompt import build_structure_system_prompt, build_structure_user_prompt
from careervp.logic.utils.llm_client import TaskMode, get_llm_router
from careervp.logic.utils.web_scraper import MIN_CONTENT_WORDS, count_words, scrape_company_about_page
from careervp.logic.utils.web_search import aggregate_search_content, search_company_info, search_company_news
from careervp.models.company import CompanyResearchRequest, CompanyResearchResult, ResearchSource
from careervp.models.job import CompanyContext
from careervp.models.result import Result, ResultCode

RESEARCH_TIMEOUT = 60.0
MAX_PROMPT_WORDS = 2500
DEFAULT_CONFIDENCE_THRESHOLD = 0.85

ContextHint = str


@dataclass(frozen=True)
class ConfidentCompanyResearch:
    """Confidence-gated Company Research artifact used by VPR generation."""

    company_context: CompanyContext
    company_research_id: str
    company_research_at: str | None


async def research_company(request: CompanyResearchRequest) -> Result[CompanyResearchResult]:
    """
    Research a company using Tavily retrieval and LLM structuring.
    """
    try:
        return await asyncio.wait_for(_research_company_inner(request), timeout=RESEARCH_TIMEOUT)
    except asyncio.TimeoutError:
        logger.error('Company research timed out', company_name=request.company_name)
        return Result(success=False, error='Company research timed out', code=ResultCode.TIMEOUT)


def load_confident_company_research(application_id: str, user_id: str) -> CompanyContext | None:
    """Return the VPR-ready CompanyContext for the latest confident CR artifact."""
    artifact = load_confident_company_research_artifact(application_id=application_id, user_id=user_id)
    return artifact.company_context if artifact is not None else None


def load_confident_company_research_artifact(application_id: str, user_id: str) -> ConfidentCompanyResearch | None:
    """Load the latest ownership-checked, confidence-gated Company Research artifact.

    This never synthesizes missing data. If the persisted record is absent, belongs to
    another user, is below threshold, or matches the deleted fabricated payload pattern,
    the function returns None.
    """
    clean_application_id = application_id.strip()
    clean_user_id = user_id.strip()
    if not clean_application_id or not clean_user_id:
        return None

    item = read_cr_artifact(application_id=clean_application_id, user_id=clean_user_id)
    if item is None:
        return None
    if str(item.get('user_id') or '').strip() != clean_user_id:
        logger.warning('Company Research ownership check failed', application_id=clean_application_id)
        return None

    payload = _company_research_payload(item)
    company_name = _coerce_text(item.get('company_name')) or _coerce_text(payload.get('company_name')) or ''
    if not company_name or company_name.startswith(_fabricated_company_prefix()):
        return None

    confidence = _coerce_float(item.get('confidence_score'))
    if confidence is None:
        confidence = _coerce_float(payload.get('confidence_score'))
    if confidence is None or confidence < _confidence_threshold():
        return None

    context = CompanyContext(
        company_name=company_name,
        overview=_coerce_text(item.get('overview')) or _coerce_text(payload.get('overview')),
        mission=_coerce_text(item.get('mission')) or _coerce_text(payload.get('mission')),
        values=_coerce_text_list(item.get('values')) or _coerce_text_list(payload.get('values')),
        strategic_priorities=_coerce_text_list(item.get('strategic_priorities')) or _coerce_text_list(payload.get('strategic_priorities')),
        recent_news=_coerce_recent_news(item.get('recent_news')) or _coerce_recent_news(payload.get('recent_news')),
        financial_summary=_coerce_text(item.get('financial_summary')) or _coerce_text(payload.get('financial_summary')),
        key_products=_coerce_text_list(item.get('key_products')) or _coerce_text_list(payload.get('key_products')),
        company_size=_coerce_text(item.get('company_size')) or _coerce_text(payload.get('company_size')),
        key_executives=_coerce_text_list(item.get('key_executives')) or _coerce_text_list(payload.get('key_executives')),
        competitive_positioning=_coerce_text(item.get('competitive_positioning')) or _coerce_text(payload.get('competitive_positioning')),
        growth_signals=_coerce_text_list(item.get('growth_signals')) or _coerce_text_list(payload.get('growth_signals')),
        industry=_coerce_text(item.get('industry')) or _coerce_text(payload.get('industry')),
    )
    research_id = (
        _coerce_text(item.get('company_research_id'))
        or _coerce_text(payload.get('company_research_id'))
        or _coerce_text(item.get('job_id'))
        or clean_application_id
    )
    research_at = _coerce_text(item.get('created_at')) or _coerce_text(item.get('updated_at')) or _coerce_text(payload.get('research_timestamp'))
    return ConfidentCompanyResearch(
        company_context=context,
        company_research_id=research_id,
        company_research_at=research_at,
    )


def _company_research_payload(item: dict[str, Any]) -> dict[str, Any]:
    research_data = item.get('research_data')
    if isinstance(research_data, dict):
        return research_data
    company_research = item.get('company_research')
    if isinstance(company_research, dict):
        return company_research
    return item


def _fabricated_company_prefix() -> str:
    return ' '.join(('Company', 'for')) + ' '


def _confidence_threshold() -> float:
    return _coerce_float(os.environ.get('CR_CONFIDENCE_THRESHOLD')) or DEFAULT_CONFIDENCE_THRESHOLD


def _coerce_float(value: Any) -> float | None:
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, int | float):
        return float(value)
    if isinstance(value, str) and value.strip():
        try:
            return float(value.strip())
        except ValueError:
            return None
    return None


def _coerce_text(value: Any) -> str | None:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    return None


def _coerce_text_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _coerce_recent_news(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    result: list[str] = []
    for item in value:
        if isinstance(item, dict):
            title = _coerce_text(item.get('title')) or _coerce_text(item.get('headline'))
            if title:
                result.append(title)
        elif str(item).strip():
            result.append(str(item).strip())
    return result


async def _research_company_inner(request: CompanyResearchRequest) -> Result[CompanyResearchResult]:
    logger.info('Starting company research', company_name=request.company_name)
    domain = _resolve_domain(request)
    keys = company_cache_keys(company_name=request.company_name, domain=domain)
    if keys is None:
        return await _run_full_company_research(request, domain=domain)

    profile_key, news_key, lock_key = keys
    cached_profile = read_profile(profile_key)
    cached_news = read_news(news_key)
    cached_result = _merge_cache_hit(cached_profile, cached_news, fallback_company_name=request.company_name)
    if cached_result is not None:
        logger.info('[RESEARCH_SUCCESS] Source: COMPANY_INTEL_CACHE', company_name=request.company_name)
        return Result(success=True, data=cached_result, code=ResultCode.RESEARCH_COMPLETE)

    if cached_profile is not None:
        news_refresh = await _refresh_cached_news(request, domain=domain, profile=cached_profile, news_key=news_key)
        if news_refresh.success:
            return news_refresh

    if acquire_lock(lock_key):
        try:
            direct_result = await _run_full_company_research(request, domain=domain)
            if direct_result.success and direct_result.data is not None:
                write_profile(profile_key, direct_result.data)
                write_news(news_key, direct_result.data)
            return direct_result
        finally:
            release_lock(lock_key)

    waited_result = await _wait_for_company_intel_cache(profile_key, news_key, fallback_company_name=request.company_name)
    if waited_result is not None:
        logger.info('[RESEARCH_SUCCESS] Source: COMPANY_INTEL_CACHE_AFTER_WAIT', company_name=request.company_name)
        return Result(success=True, data=waited_result, code=ResultCode.RESEARCH_COMPLETE)

    return await _run_full_company_research(request, domain=domain)


async def _run_full_company_research(request: CompanyResearchRequest, *, domain: str | None) -> Result[CompanyResearchResult]:
    """Run the pre-cache full Tavily profile/news research flow."""

    # Primary path: Tavily site-scoped search when a company/job domain is available.
    if domain:
        site_urls: list[str] = []
        site_result = await _try_web_search(request.company_name, domain=domain, source_urls=site_urls)
        if site_result.success and site_result.data:
            structured = await _structure_raw_content(
                company_name=request.company_name,
                raw_text=site_result.data,
                source=ResearchSource.WEB_API,
                source_urls=site_urls,
                word_count=count_words(site_result.data),
                context_hint='Tavily site-scoped company profile and news results',
                job_domain=domain,
            )
            if structured.success:
                logger.info('[RESEARCH_SUCCESS] Source: WEB_API_SITE_SCOPED', company_name=request.company_name)
            return structured
        logger.warning(
            '[WEB_API_FALLBACK] Site-scoped Tavily search failed, using general Tavily search',
            company_name=request.company_name,
            reason=site_result.error,
        )
    else:
        logger.warning(
            '[WEB_API_FALLBACK] Site-scoped Tavily search skipped, using general Tavily search',
            company_name=request.company_name,
            reason='domain_unavailable',
        )

    # Fallback: Tavily general web search.
    search_urls: list[str] = []
    search_result = await _try_web_search(request.company_name, source_urls=search_urls)
    if search_result.success and search_result.data:
        structured = await _structure_raw_content(
            company_name=request.company_name,
            raw_text=search_result.data,
            source=ResearchSource.WEB_API,
            source_urls=search_urls,
            word_count=count_words(search_result.data),
            context_hint='Tavily general company profile and recent news results',
            job_domain=domain,
        )
        if structured.success:
            logger.info('[RESEARCH_SUCCESS] Source: WEB_API_GENERAL', company_name=request.company_name)
        return structured

    # No real source content was obtained from scrape or search. Per FE-UI-041 we do NOT
    # synthesise company facts from the job posting alone — that produced fabricated,
    # low-confidence content indistinguishable from real research. Report an explicit
    # failure so the confidence gate / retry path owns the outcome.
    logger.warning(
        '[ALL_SOURCES_FAILED] Tavily returned no usable company research content',
        company_name=request.company_name,
        reason=search_result.error,
    )
    return Result(
        success=False,
        error='No company research sources returned usable content',
        code=ResultCode.ALL_SOURCES_FAILED,
    )


async def _refresh_cached_news(
    request: CompanyResearchRequest,
    *,
    domain: str | None,
    profile: CachedProfile,
    news_key: str,
) -> Result[CompanyResearchResult]:
    news_result = await _run_news_only_company_research(request, domain=domain)
    if not news_result.success or news_result.data is None:
        return news_result

    write_news(news_key, news_result.data)
    fresh_news = CachedNews(key=news_key, data=_news_cache_payload(news_result.data), expires_at=0)
    merged_result = merge_cached_company_research(profile, fresh_news, fallback_company_name=request.company_name)
    if merged_result is None:
        return await _run_full_company_research(request, domain=domain)
    logger.info('[RESEARCH_SUCCESS] Source: COMPANY_INTEL_CACHE_NEWS_REFRESH', company_name=request.company_name)
    return Result(success=True, data=merged_result, code=ResultCode.RESEARCH_COMPLETE)


async def _run_news_only_company_research(request: CompanyResearchRequest, *, domain: str | None) -> Result[CompanyResearchResult]:
    source_urls: list[str] = []
    search_result = await _try_news_search(request.company_name, source_urls=source_urls)
    if not search_result.success or not search_result.data:
        return Result(
            success=False,
            error=search_result.error or 'No company news sources returned usable content',
            code=search_result.code or ResultCode.SEARCH_FAILED,
        )
    return await _structure_raw_content(
        company_name=request.company_name,
        raw_text=search_result.data,
        source=ResearchSource.WEB_API,
        source_urls=source_urls,
        word_count=count_words(search_result.data),
        context_hint='Tavily recent company news and growth signal results',
        job_domain=domain,
    )


async def _wait_for_company_intel_cache(profile_key: str, news_key: str, *, fallback_company_name: str) -> CompanyResearchResult | None:
    for delay_seconds in (0.2, 0.4, 0.8):
        await asyncio.sleep(delay_seconds)
        cached_result = _merge_cache_hit(read_profile(profile_key), read_news(news_key), fallback_company_name=fallback_company_name)
        if cached_result is not None:
            return cached_result
    return None


def _merge_cache_hit(
    profile: CachedProfile | None,
    news: CachedNews | None,
    *,
    fallback_company_name: str,
) -> CompanyResearchResult | None:
    if profile is None or news is None:
        return None
    return merge_cached_company_research(profile, news, fallback_company_name=fallback_company_name)


def _news_cache_payload(result: CompanyResearchResult) -> dict[str, Any]:
    payload = result.model_dump(mode='json')
    return {
        'recent_news': payload.get('recent_news'),
        'growth_signals': payload.get('growth_signals'),
        'source': payload.get('source'),
        'source_urls': payload.get('source_urls'),
        'confidence_score': payload.get('confidence_score'),
        'research_timestamp': payload.get('research_timestamp'),
    }


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


async def _try_web_search(company_name: str, *, domain: str | None = None, source_urls: list[str] | None = None) -> Result[str]:
    search_result = await search_company_info(company_name, domain=domain)
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


async def _try_news_search(company_name: str, *, source_urls: list[str] | None = None) -> Result[str]:
    search_result = await search_company_news(company_name)
    if not search_result.success or not search_result.data:
        return Result(
            success=False,
            error=search_result.error or 'News search failed',
            code=search_result.code or ResultCode.SEARCH_FAILED,
        )

    results = search_result.data
    aggregated = aggregate_search_content(results)
    if source_urls is not None:
        source_urls.extend(str(item.url) for item in results)

    if count_words(aggregated) < MIN_CONTENT_WORDS:
        return Result(success=False, error='Insufficient news snippets', code=ResultCode.SEARCH_FAILED)

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
    job_domain: str | None = None,
) -> Result[CompanyResearchResult]:
    cache = LLMResponseCache()
    cache_key = _company_cache_key(company_name)
    cached_value = cache.get(cache_key)
    if cached_value:
        cached_result = _parse_cached_company_research(cached_value)
        if cached_result is not None:
            return Result(success=True, data=cached_result, code=ResultCode.RESEARCH_COMPLETE)

    trimmed_text = _truncate_text(raw_text, max_words=MAX_PROMPT_WORDS)
    user_prompt = build_structure_user_prompt(company_name, trimmed_text, context_hint)
    router = get_llm_router()

    loop = asyncio.get_running_loop()
    llm_result = await loop.run_in_executor(
        None,
        lambda: router.invoke(
            mode=TaskMode.TEMPLATE,
            system_prompt=build_structure_system_prompt(),
            user_prompt=user_prompt,
            max_tokens=1400,
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
        key_products=_ensure_list(payload.get('key_products')),
        company_size=_ensure_optional_text(payload.get('company_size')),
        key_executives=_ensure_list(payload.get('key_executives')),
        competitive_positioning=_ensure_optional_text(payload.get('competitive_positioning')),
        growth_signals=_ensure_list(payload.get('growth_signals')),
        source=source,
        source_urls=_deduplicate_urls(source_urls),
        confidence_score=_calculate_confidence(
            source,
            word_count,
            payload,
            company_name=company_name,
            content_text=raw_text,
            source_urls=source_urls,
            job_domain=job_domain,
        ),
        research_timestamp=datetime.now(timezone.utc),
    )

    cache.set(
        cache_key,
        result_model.model_dump_json(),
        ttl_seconds=DEFAULT_CACHE_TTL_SECONDS,
    )

    return Result(success=True, data=result_model, code=ResultCode.RESEARCH_COMPLETE)


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


def _company_cache_key(company_name: str) -> str:
    return company_name.strip().lower()


def _parse_cached_company_research(cached_value: str) -> CompanyResearchResult | None:
    try:
        payload = json.loads(cached_value)
    except json.JSONDecodeError:
        return None

    if not isinstance(payload, dict):
        return None

    try:
        return CompanyResearchResult.model_validate(payload)
    except Exception:  # noqa: BLE001
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


def _calculate_confidence(
    source: ResearchSource,
    word_count: int,
    payload: dict[str, Any],
    *,
    company_name: str = '',
    content_text: str = '',
    source_urls: list[str] | None = None,
    job_domain: str | None = None,
) -> float:
    if source == ResearchSource.WEBSITE_SCRAPE:
        score = 0.9
        if word_count < 300:
            score -= 0.1
    elif source == ResearchSource.WEB_API:
        score = 0.88
        if not _web_api_identity_verified(company_name=company_name, content_text=content_text, source_urls=source_urls or [], job_domain=job_domain):
            score = min(score, 0.7)
        penalty_fields = ['overview', 'mission', 'values', 'recent_news', 'strategic_priorities']
        missing = sum(1 for field in penalty_fields if not payload.get(field))
        score -= 0.1 * missing
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


def _web_api_identity_verified(*, company_name: str, content_text: str, source_urls: list[str], job_domain: str | None) -> bool:
    clean_company_name = company_name.strip().lower()
    if clean_company_name and clean_company_name in content_text.lower():
        return True

    normalized_job_domain = _normalize_domain(job_domain)
    if not normalized_job_domain:
        return False
    return any(_normalize_domain(url) == normalized_job_domain for url in source_urls)


def _normalize_domain(raw_value: str | None) -> str | None:
    if not raw_value:
        return None
    parsed = urlparse(raw_value if '://' in raw_value else f'https://{raw_value}')
    domain = (parsed.hostname or '').lower().removeprefix('www.')
    return domain or None


def _resolve_domain(request: CompanyResearchRequest) -> str | None:
    if request.domain:
        return request.domain
    if request.job_posting_url:
        parsed = urlparse(str(request.job_posting_url))
        if parsed.netloc:
            return parsed.netloc
    return None


__all__ = ['ConfidentCompanyResearch', 'load_confident_company_research', 'load_confident_company_research_artifact', 'research_company']
