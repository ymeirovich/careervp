"""resource_env() must never guess a resource name in another live environment.

Spec: docs/handoff/2026-09-21-HANDOFF-09-environment-coupling.md, Step 3.4.
"""

from __future__ import annotations

import pytest

from careervp.logic.utils.env import resource_env


@pytest.mark.parametrize('blank', ['', '   '])
def test_resource_env_raises_when_unset_or_blank(blank: str, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv('ENVIRONMENT', blank)

    with pytest.raises(RuntimeError, match='ENVIRONMENT unset'):
        resource_env()


def test_resource_env_returns_the_set_value(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv('ENVIRONMENT', 'devx')

    assert resource_env() == 'devx'


def test_resource_env_strips_whitespace(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv('ENVIRONMENT', '  devx  ')

    assert resource_env() == 'devx'


def test_resource_env_with_default_returns_default_when_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv('ENVIRONMENT', raising=False)

    assert resource_env(default='prod') == 'prod'


def test_resource_env_with_default_prefers_the_set_value(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv('ENVIRONMENT', 'devx')

    assert resource_env(default='prod') == 'devx'
