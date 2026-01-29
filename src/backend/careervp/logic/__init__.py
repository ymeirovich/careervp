from importlib import import_module
from typing import Any

__all__ = [
    'parse_cv',
    'create_cv_parse_response',
    'validate_cv_against_baseline',
    'validate_immutable_facts',
    'validate_verifiable_skills',
    'FVSValidationResult',
    'FVSViolation',
]


def __getattr__(name: str) -> Any:
    """Lazily import logic modules when attributes are requested."""
    if name in {'parse_cv', 'create_cv_parse_response'}:
        module = import_module('careervp.logic.cv_parser')
        return getattr(module, name)

    if name in {
        'validate_cv_against_baseline',
        'validate_immutable_facts',
        'validate_verifiable_skills',
        'FVSValidationResult',
        'FVSViolation',
    }:
        module = import_module('careervp.logic.fvs_validator')
        return getattr(module, name)

    raise AttributeError(f'module {__name__!r} has no attribute {name!r}')
