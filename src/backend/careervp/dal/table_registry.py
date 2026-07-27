"""Single key-authority for the artifacts/core table (scope-lock D-H2).

This module and ``careervp.dal.core_repository`` are the only approved
builders of artifacts/core ``pk``/``sk``/``USER#``/artifact-SK values and the
only place the artifacts/core table name may be resolved from the
environment. Handlers and logic modules must import from here instead of
constructing key strings or env-precedence chains inline
(``tests/unit/test_dh2_dh3_key_authority.py`` enforces this statically).

The three env chains below are intentionally distinct roles, not one chain:
the ai-assist Lambda (``infra/careervp/ai_assist_nested_stack.py``) points
``ARTIFACTS_TABLE_NAME`` and ``COMPANY_RESEARCH_TABLE_NAME`` at different
physical tables, so collapsing the chains would silently retarget reads.
"""

from __future__ import annotations

import os
from typing import Any

import boto3
from boto3.dynamodb.conditions import ConditionBase, Key

# --- Artifact key grammar (sole authority) ---

CV_SORT_KEY_PREFIX = 'CV#'
VPR_SORT_KEY_PREFIX = 'ARTIFACT#VPR#v'
TAILORED_CV_SORT_KEY_PREFIX = 'ARTIFACT#CV_TAILORED#'
COVER_LETTER_SORT_KEY_PREFIX = 'ARTIFACT#COVER_LETTER#'
GAP_ANALYSIS_SORT_KEY_PREFIX = 'ARTIFACT#GAP_ANALYSIS#'
GAP_RESPONSES_SORT_KEY_PREFIX = 'ARTIFACT#GAP_RESPONSES#'
INTERVIEW_PREP_SORT_KEY_PREFIX = 'ARTIFACT#INTERVIEW_PREP#'
COMPANY_RESEARCH_ARTIFACT_PREFIX = 'ARTIFACT#COMPANY_RESEARCH#'
COMPANY_RESEARCH_KB_PREFIX = 'COMPANY_RESEARCH#'
USER_PARTITION_PREFIX = 'USER#'


def user_partition_key(user_id: str) -> str:
    return f'{USER_PARTITION_PREFIX}{user_id}'


def user_partition_candidates(user_id: str) -> tuple[str, str]:
    """Both accepted owner spellings of a legacy partition key."""
    return (user_id, user_partition_key(user_id))


def cv_sort_key(cv_id: str) -> str:
    return f'{CV_SORT_KEY_PREFIX}{cv_id}'


def cover_letter_artifact_id(job_id: str) -> str:
    return f'{COVER_LETTER_SORT_KEY_PREFIX}{job_id}'


def tailored_cv_artifact_id(request_id: str) -> str:
    return f'{TAILORED_CV_SORT_KEY_PREFIX}{request_id}'


def interview_prep_artifact_id(job_id: str) -> str:
    return f'{INTERVIEW_PREP_SORT_KEY_PREFIX}{job_id}'


def company_research_artifact_sk(job_id: str) -> str:
    return f'{COMPANY_RESEARCH_ARTIFACT_PREFIX}{job_id}'


def company_research_kb_sk(job_id: str) -> str:
    return f'{COMPANY_RESEARCH_KB_PREFIX}{job_id}'


def legacy_item_key(pk: str, sk: str) -> dict[str, str]:
    """Legacy pk/sk item key for the artifacts/core table."""
    return {'pk': pk, 'sk': sk}


def canonical_item_key(application_id: str, artifact_id: str) -> dict[str, str]:
    """Canonical applicationId/artifactId item key for the artifacts table."""
    return {'applicationId': application_id, 'artifactId': artifact_id}


def legacy_key_condition(pk: str, sk_prefix: str) -> ConditionBase:
    """Legacy-schema key condition: pk equals + sk begins_with prefix."""
    return Key('pk').eq(pk) & Key('sk').begins_with(sk_prefix)


def canonical_key_condition(application_id: str, artifact_id_prefix: str) -> ConditionBase:
    """Canonical-schema key condition: applicationId equals + artifactId prefix."""
    return Key('applicationId').eq(application_id) & Key('artifactId').begins_with(artifact_id_prefix)


def company_research_candidate_keys(user_id: str, job_id: str) -> list[dict[str, str]]:
    """Every legacy key convention a company-research item may live under."""
    return [
        legacy_item_key(user_id, company_research_artifact_sk(job_id)),
        legacy_item_key(user_id, company_research_kb_sk(job_id)),
        legacy_item_key(user_partition_key(user_id), company_research_kb_sk(job_id)),
    ]


def company_research_query_candidates(user_id: str) -> list[tuple[str, str]]:
    """(partition key, sk prefix) pairs covering legacy company-research layouts."""
    return [
        (user_id, COMPANY_RESEARCH_ARTIFACT_PREFIX),
        (user_id, COMPANY_RESEARCH_KB_PREFIX),
        (user_partition_key(user_id), COMPANY_RESEARCH_KB_PREFIX),
    ]


# --- Artifacts/core table-name resolution (sole authority) ---

_ARTIFACTS_ENV_CHAIN = ('ARTIFACTS_TABLE_NAME', 'DYNAMODB_TABLE_NAME', 'TABLE_NAME')
_LEGACY_ARTIFACTS_ENV_CHAIN = ('DYNAMODB_TABLE_NAME', 'TABLE_NAME')
_COMPANY_RESEARCH_ENV_CHAIN = ('COMPANY_RESEARCH_TABLE_NAME', *_ARTIFACTS_ENV_CHAIN)


def _resolve_chain(env_chain: tuple[str, ...]) -> tuple[str, str]:
    for env_key in env_chain:
        value = os.environ.get(env_key)
        if isinstance(value, str) and value.strip():
            return value.strip(), env_key
    return '', 'none'


def resolve_artifacts_table_name(*, required: bool = False) -> str:
    """Artifacts table via the full three-key precedence chain."""
    value, _ = _resolve_chain(_ARTIFACTS_ENV_CHAIN)
    if required and not value:
        raise RuntimeError('Artifacts table environment variable is not configured')
    return value


def resolve_artifacts_table_name_with_source() -> tuple[str, str]:
    """Artifacts table name plus the env key it resolved from ('none' if unset)."""
    return _resolve_chain(_ARTIFACTS_ENV_CHAIN)


def resolve_legacy_artifacts_table_name() -> str:
    """Artifacts table via the legacy two-key tail (no ARTIFACTS_TABLE_NAME)."""
    value, _ = _resolve_chain(_LEGACY_ARTIFACTS_ENV_CHAIN)
    return value


def legacy_artifacts_table_candidates() -> list[str]:
    """Deduped, in-precedence-order candidates from the legacy two-key tail."""
    candidates: list[str] = []
    for env_key in _LEGACY_ARTIFACTS_ENV_CHAIN:
        value = os.environ.get(env_key)
        if isinstance(value, str) and value.strip() and value.strip() not in candidates:
            candidates.append(value.strip())
    return candidates


def resolve_company_research_table_name() -> str:
    """Company-research table, preferring its dedicated env key."""
    value, _ = _resolve_chain(_COMPANY_RESEARCH_ENV_CHAIN)
    return value


class TableRegistry:
    """Resolves and hands out the artifacts/core table (scope-lock D-H2)."""

    def __init__(
        self,
        artifacts_table_name: str | None = None,
        dynamodb_resource: Any | None = None,
    ) -> None:
        self._artifacts_table_name = artifacts_table_name
        self._dynamodb_resource = dynamodb_resource

    @property
    def artifacts_table_name(self) -> str:
        if self._artifacts_table_name:
            return self._artifacts_table_name
        return resolve_artifacts_table_name()

    def artifacts_table(self) -> Any:
        resource = self._dynamodb_resource
        if resource is None:
            resource = boto3.session.Session().resource('dynamodb')
        return resource.Table(self.artifacts_table_name)
