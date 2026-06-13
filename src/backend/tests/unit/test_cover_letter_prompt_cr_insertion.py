from __future__ import annotations

from datetime import datetime, timezone

from careervp.logic.prompts.cover_letter_prompt import build_user_prompt
from careervp.models.company import CompanyResearchResult, ResearchSource


def _company_research(
    *,
    overview: str = 'Acme is expanding its platform business.',
    mission: str | None = 'Build',
    values: list[str] | None = None,
    strategic_priorities: list[str] | None = None,
) -> CompanyResearchResult:
    return CompanyResearchResult(
        company_name='Acme',
        overview=overview,
        mission=mission,
        values=values or ['innovation'],
        strategic_priorities=strategic_priorities or ['grow'],
        recent_news=[],
        financial_summary=None,
        source=ResearchSource.WEBSITE_SCRAPE,
        source_urls=['https://acme.example'],
        confidence_score=0.9,
        research_timestamp=datetime.now(timezone.utc),
    )


def test_cover_letter_no_cr_is_backward_compatible(minimal_user_cv, minimal_vpr) -> None:
    prompt_without_kwarg = build_user_prompt(
        cv=minimal_user_cv,
        vpr=minimal_vpr,
        company_name='Acme',
        job_title='Eng',
        job_description='Build systems.',
    )
    prompt_with_none = build_user_prompt(
        cv=minimal_user_cv,
        vpr=minimal_vpr,
        company_name='Acme',
        job_title='Eng',
        job_description='Build systems.',
        company_research=None,
    )

    assert prompt_without_kwarg == prompt_with_none
    assert '# Company Research' not in prompt_without_kwarg


def test_cover_letter_with_cr_inserts_company_research_section(minimal_user_cv, minimal_vpr) -> None:
    prompt = build_user_prompt(
        cv=minimal_user_cv,
        vpr=minimal_vpr,
        company_name='Acme',
        job_title='Eng',
        job_description='Build systems.',
        company_research=_company_research(),
    )

    assert '# Company Research' in prompt
    assert 'Overview:' in prompt
    assert 'Mission: Build' in prompt
    assert 'Values: innovation' in prompt
    assert prompt.index('# Company Research') > prompt.index('# Company')
    assert prompt.index('# Company Research') < prompt.index('# Role')


def test_cover_letter_cr_with_none_fields_does_not_crash(minimal_user_cv, minimal_vpr) -> None:
    prompt = build_user_prompt(
        cv=minimal_user_cv,
        vpr=minimal_vpr,
        company_name='Acme',
        job_title='Eng',
        job_description='Build systems.',
        company_research=_company_research(mission=None, values=[], strategic_priorities=[]),
    )

    assert '# Company Research' in prompt
