"""Regression — interview prep must not be silently truncated by the output cap.

Journey step J8 failed against deployed devx code at 2ce05bcd with the module card
stuck on "Retry". The worker logs showed both parse attempts dying the same way:

    attempt 1/2, compact_output=False, question_count=10:
        Invalid JSON: Unterminated string starting at: line 76 column 22 (char 18910)
    attempt 2/2, compact_output=True, question_count=5:
        Invalid JSON: Unterminated string starting at: line 134 column 22 (char 16628)

An unterminated string at ~17-19k characters is a truncated completion, not a malformed
one: the model hit its output ceiling and stopped mid-token, so the JSON never closed.
LLMClient._invoke_model hardcoded `max_tokens=4096` with no parameter, so no caller could
raise it -- and interview prep asks for up to MAX_QUESTIONS answers of ANSWER_MAX_WORDS
words each, which does not fit. Halving the question count on retry did not help because
the cap, not the question count, was the binding constraint.

Two guards:
  1. generate() forwards a caller-supplied max_tokens to the provider call, and still
     defaults to the historical 4096 so no other caller's behaviour shifts.
  2. interview prep asks for a budget its own declared limits can actually fit in.
"""

from __future__ import annotations

import asyncio
import json
import os
from unittest.mock import MagicMock, patch

from careervp.logic.interview_prep import (
    ANSWER_MAX_WORDS,
    GENERATION_MAX_TOKENS,
    MAX_QUESTIONS,
    generate_interview_prep,
)
from careervp.logic.llm_client import DEFAULT_MAX_OUTPUT_TOKENS, LLMClient
from careervp.models.interview_prep import InterviewPrepRequest

os.environ.setdefault('AWS_ACCESS_KEY_ID', 'testing')
os.environ.setdefault('AWS_SECRET_ACCESS_KEY', 'testing')
os.environ.setdefault('AWS_DEFAULT_REGION', 'us-east-1')
os.environ.setdefault('ENVIRONMENT', 'test')
os.environ.setdefault('ANTHROPIC_API_KEY', 'test-key')


def _request() -> InterviewPrepRequest:
    return InterviewPrepRequest(
        user_id='user-token-budget',
        vpr_id='vpr-001',
        job_id='job-001',
        gap_response_ids=[],
        focus_areas=[],
        question_count=10,
    )


def _valid_payload() -> dict[str, object]:
    return {
        'text': json.dumps(
            {
                'questions': [
                    {
                        'question_id': 'q1',
                        'question': 'Tell me about a migration you led.',
                        'question_type': 'behavioral',
                        'difficulty': 'medium',
                        'suggested_answer': {
                            'situation': 'The platform was straining.',
                            'task': 'Plan a phased migration.',
                            'action': 'Split services behind a facade.',
                            'result': 'Incidents fell sharply.',
                            'full_text': 'Phased migration behind a facade reduced incidents.',
                        },
                    }
                ]
            }
        )
    }


class TestLLMClientHonoursCallerBudget:
    """generate() must forward max_tokens instead of pinning every caller to one ceiling."""

    @staticmethod
    def _client_with_spy() -> tuple[LLMClient, MagicMock]:
        provider = MagicMock()
        message = MagicMock()
        message.content = [MagicMock(text='{"ok": true}')]
        message.usage = MagicMock(
            input_tokens=10,
            output_tokens=10,
            cache_read_input_tokens=0,
            cache_creation_input_tokens=0,
        )
        provider.messages.create.return_value = message
        cache = MagicMock()
        cache.get.return_value = None
        return LLMClient(client=provider, cache=cache), provider

    def test_caller_supplied_budget_reaches_the_provider(self) -> None:
        client, provider = self._client_with_spy()

        client.generate(prompt='hello', max_tokens=16000)

        assert provider.messages.create.call_args.kwargs['max_tokens'] == 16000

    def test_default_budget_is_unchanged_for_every_other_caller(self) -> None:
        """The default must stay at the historical value: this fix widens one caller, not all."""
        client, provider = self._client_with_spy()

        client.generate(prompt='hello')

        assert provider.messages.create.call_args.kwargs['max_tokens'] == DEFAULT_MAX_OUTPUT_TOKENS
        assert DEFAULT_MAX_OUTPUT_TOKENS == 4096


class TestInterviewPrepBudgetFitsItsOwnPrompt:
    def test_budget_exceeds_the_worst_case_the_prompt_asks_for(self) -> None:
        """The ask must fit the budget, or generation truncates mid-answer as it did on devx.

        MAX_QUESTIONS answers x ANSWER_MAX_WORDS words, at a conservative ~1.3 tokens per
        English word, is the answer bodies alone -- question text, STAR fields and JSON
        scaffolding all land on top.
        """
        worst_case_answer_tokens = MAX_QUESTIONS * ANSWER_MAX_WORDS * 1.3

        assert GENERATION_MAX_TOKENS > worst_case_answer_tokens
        # The cap that actually broke J8 does not fit, which is why it had to be raised.
        assert DEFAULT_MAX_OUTPUT_TOKENS < worst_case_answer_tokens

    def test_generation_requests_the_widened_budget(self) -> None:
        with patch('careervp.logic.interview_prep.LLMClient') as mock_cls:
            mock_llm = MagicMock()
            mock_llm.generate.return_value = _valid_payload()
            mock_cls.return_value = mock_llm

            asyncio.run(
                generate_interview_prep(
                    request=_request(),
                    vpr_data={'summary': 'strong fit'},
                    job_title='Staff Engineer',
                    company_name='SysAid',
                )
            )

        assert mock_llm.generate.call_args.kwargs['max_tokens'] == GENERATION_MAX_TOKENS

    def test_parse_retry_also_gets_the_widened_budget(self) -> None:
        """The retry truncated too -- it must not fall back to the ceiling that broke it."""
        with patch('careervp.logic.interview_prep.LLMClient') as mock_cls:
            mock_llm = MagicMock()
            mock_llm.generate.side_effect = [
                {'text': '{"questions":[{"question_id":"q1","question":"truncated mid-str'},
                _valid_payload(),
            ]
            mock_cls.return_value = mock_llm

            asyncio.run(
                generate_interview_prep(
                    request=_request(),
                    vpr_data={'summary': 'strong fit'},
                    job_title='Staff Engineer',
                    company_name='SysAid',
                )
            )

        assert mock_llm.generate.call_count == 2
        for call in mock_llm.generate.call_args_list:
            assert call.kwargs['max_tokens'] == GENERATION_MAX_TOKENS
