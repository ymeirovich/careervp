from __future__ import annotations

from unittest.mock import MagicMock, patch

from careervp.logic.prompts.company_research_prompt import build_structure_system_prompt, build_structure_user_prompt


def test_system_prompt_golden_unchanged() -> None:
    assert build_structure_system_prompt() == 'You are CareerVP company research analyst. Extract structured insights faithfully.'


def test_user_prompt_golden_website_scrape() -> None:
    raw_text = 'Acme is a leader in cloud operations and platform engineering delivery.'
    prompt = build_structure_user_prompt('Acme Corp', raw_text, 'official website About page text')

    assert prompt == (
        'Company Name: Acme Corp\n'
        'Source Context: official website About page text\n\n'
        'Extract structured company research from the following text. '
        'Return JSON with keys overview (100-200 words), values (list), mission, strategic_priorities, recent_news, '
        'financial_summary, key_products, company_size, key_executives, competitive_positioning, growth_signals.\n'
        'Text:\n'
        'Acme is a leader in cloud operations and platform engineering delivery.\n'
        'Return ONLY valid JSON.'
    )


def test_company_research_py_still_works_after_extraction() -> None:
    from careervp.logic.company_research import _structure_raw_content
    from careervp.models.company import ResearchSource
    from careervp.models.result import Result, ResultCode

    router = MagicMock()
    router.invoke.return_value = Result(
        success=True,
        data={
            'text': '{"overview":"Acme overview","values":["innovation"],"mission":"Build","strategic_priorities":["grow"]}',
        },
        code=ResultCode.SUCCESS,
    )

    class CacheStub:
        def get(self, key: str) -> None:
            return None

        def set(self, key: str, value: str, ttl_seconds: int) -> None:
            return None

    with (
        patch('careervp.logic.company_research.build_structure_system_prompt', wraps=build_structure_system_prompt) as mock_system,
        patch('careervp.logic.company_research.build_structure_user_prompt', wraps=build_structure_user_prompt) as mock_user,
        patch('careervp.logic.company_research.LLMResponseCache', return_value=CacheStub()),
        patch('careervp.logic.company_research.get_llm_router', return_value=router),
    ):
        result = __import__('asyncio').run(
            _structure_raw_content(
                company_name='Acme Corp',
                raw_text='Acme is a leader in cloud operations.',
                source=ResearchSource.WEBSITE_SCRAPE,
                source_urls=['https://acme.example/about'],
                word_count=200,
                context_hint='official website About page text',
            )
        )

    assert result.success is True
    mock_system.assert_called_once_with()
    mock_user.assert_called_once()
