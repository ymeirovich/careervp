from __future__ import annotations

from datetime import datetime, timezone

from careervp.logic.cv_tailoring_prompt import build_user_prompt
from careervp.models.company import CompanyResearchResult, ResearchSource


def _company_research(values: list[str], strategic_priorities: list[str]) -> CompanyResearchResult:
    return CompanyResearchResult(
        company_name='Acme',
        overview='Acme overview',
        mission='Build',
        values=values,
        strategic_priorities=strategic_priorities,
        recent_news=[],
        financial_summary=None,
        source=ResearchSource.WEBSITE_SCRAPE,
        source_urls=['https://acme.example'],
        confidence_score=0.9,
        research_timestamp=datetime.now(timezone.utc),
    )


def test_cv_tailoring_no_cr_is_backward_compatible(minimal_user_cv, minimal_vpr) -> None:
    prompt_without_kwarg = build_user_prompt(
        cv=minimal_user_cv,
        job_description='Build systems.',
        vpr=minimal_vpr,
    )
    prompt_with_none = build_user_prompt(
        cv=minimal_user_cv,
        job_description='Build systems.',
        vpr=minimal_vpr,
        company_research=None,
    )

    assert prompt_without_kwarg == prompt_with_none
    assert '# Company Signals' not in prompt_without_kwarg


def test_cv_tailoring_with_cr_inserts_company_signals(minimal_user_cv, minimal_vpr) -> None:
    prompt = build_user_prompt(
        cv=minimal_user_cv,
        job_description='Build systems.',
        vpr=minimal_vpr,
        company_research=_company_research(values=['speed'], strategic_priorities=['AI first']),
    )

    assert '# Company Signals' in prompt
    assert 'Values: speed' in prompt
    assert 'Strategic Priorities: AI first' in prompt


def test_cv_tailoring_cr_signals_limit_to_5_values_3_priorities(minimal_user_cv, minimal_vpr) -> None:
    prompt = build_user_prompt(
        cv=minimal_user_cv,
        job_description='Build systems.',
        vpr=minimal_vpr,
        company_research=_company_research(
            values=['a', 'b', 'c', 'd', 'e', 'f'],
            strategic_priorities=['1', '2', '3', '4'],
        ),
    )

    assert 'Values: a, b, c, d, e' in prompt
    assert 'Values: a, b, c, d, e, f' not in prompt
    assert 'Strategic Priorities: 1, 2, 3' in prompt
    assert 'Strategic Priorities: 1, 2, 3, 4' not in prompt
