"""Deploy-environment resolution for runtime resource-name fallbacks."""

from __future__ import annotations

import os


def resource_env(default: str | None = None) -> str:
    """The deploy environment.

    With no default, never guesses: a missing ``ENVIRONMENT`` raises rather than
    silently resolving a resource name in another live environment. Callers that
    need a closed-by-default *behaviour* switch (not a resource name) may pass an
    explicit ``default`` — the safe direction only, e.g. ``'prod'`` so an unset
    ``ENVIRONMENT`` disables a dev-only code path instead of enabling one.
    """
    env = os.environ.get('ENVIRONMENT', '').strip()
    if env:
        return env
    if default is not None:
        return default
    raise RuntimeError('ENVIRONMENT unset; refusing to guess a resource name')
