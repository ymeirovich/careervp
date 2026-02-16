"""Backward-compatible FVS model imports.

Canonical FVS models live in ``careervp.models.fvs``.
This module remains for compatibility and re-exports those types.
"""

from careervp.models.fvs import FVSBaseline, ImmutableFact

__all__ = [
    'ImmutableFact',
    'FVSBaseline',
]
