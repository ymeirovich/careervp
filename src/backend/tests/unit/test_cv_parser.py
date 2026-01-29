"""Unit tests for cv_parser helpers per docs/specs/01-cv-parser.md."""

import json

import pytest
from langdetect import LangDetectException

from careervp.logic.cv_parser import clean_text, detect_language, parse_llm_response


def test_clean_text_normalizes_whitespace():
    raw_text = 'Experience    Summary\n\n\n  Built systems   at scale.  \n  Led teams.    '
    expected = 'Experience Summary\n\nBuilt systems at scale.\nLed teams.'

    assert clean_text(raw_text) == expected


def test_detect_language_returns_hebrew(monkeypatch):
    monkeypatch.setattr('careervp.logic.cv_parser.detect', lambda _: 'he')

    assert detect_language('כל הכבוד') == 'he'


def test_detect_language_defaults_to_english_on_error(monkeypatch):
    def _raise(_text: str) -> str:
        raise LangDetectException('failed', 0)

    monkeypatch.setattr('careervp.logic.cv_parser.detect', _raise)

    assert detect_language('unknown text') == 'en'


def test_parse_llm_response_handles_json_code_block():
    response = """```json\n{\n  \"full_name\": \"Ada\",\n  \"skills\": [\"Python\"]\n}\n```"""

    parsed = parse_llm_response(response)

    assert parsed['full_name'] == 'Ada'
    assert parsed['skills'] == ['Python']


def test_parse_llm_response_invalid_json():
    with pytest.raises(json.JSONDecodeError):
        parse_llm_response('```json { invalid } ```')
