"""Declared per-environment capability table.

A capability lives here, not as a check against an environment's literal name.
A new environment that isn't listed is a synth-time ``ValueError``, not a
silent ``false`` — see docs/handoff/2026-09-21-HANDOFF-09-environment-coupling.md.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EnvProfile:
    artifact_chain: bool
    api_custom_domain: bool


ENVIRONMENTS: dict[str, EnvProfile] = {
    "dev": EnvProfile(artifact_chain=True, api_custom_domain=True),
    "devx": EnvProfile(artifact_chain=True, api_custom_domain=False),
    "prod": EnvProfile(artifact_chain=True, api_custom_domain=True),
}


def profile(env: str) -> EnvProfile:
    if env not in ENVIRONMENTS:
        raise ValueError(f"No profile for {env!r}; add a row to environments.py")
    return ENVIRONMENTS[env]
