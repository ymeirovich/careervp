"""Logical API ID to physical storage key adapter.

This adapter preserves the currently deployed storage model while exposing
OpenAPI logical identifiers to handlers/services.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class StorageKey:
    """Physical DynamoDB key pair for the users table."""

    pk: str
    sk: str


class ApiStorageAdapter:
    """Translate between logical API identifiers and physical storage keys."""

    def map_logical_to_physical_keys(
        self,
        resource_type: str,
        logical_identifiers: dict[str, Any],
    ) -> dict[str, Any]:
        """Return table/bucket key mapping for a logical resource."""
        normalized = dict(logical_identifiers)

        # Backward-compatible alias: legacy payloads still send application_id.
        if 'job_id' not in normalized and normalized.get('application_id'):
            normalized['job_id'] = normalized['application_id']

        if resource_type == 'jobs':
            return {'jobs_table': {'pk': normalized.get('job_id')}}

        if resource_type == 'cv_upload':
            user_id = self._require(normalized, 'user_id')
            return {
                'users_table': self.build_users_table_pk_sk(
                    resource_type='cv_upload',
                    user_id=user_id,
                    identifiers=normalized,
                )
            }

        user_id = self._require(normalized, 'user_id')
        return {
            'users_table': self.build_users_table_pk_sk(
                resource_type=resource_type,
                user_id=user_id,
                identifiers=normalized,
            )
        }

    def map_physical_to_logical_ids(
        self,
        resource_type: str,
        item: dict[str, Any],
    ) -> dict[str, Any]:
        """Extract logical IDs from a physical table item."""
        if resource_type == 'jobs':
            job_id = item.get('job_id')
            return {
                'job_id': job_id,
                'application_id': job_id,  # compatibility alias
            }

        pk = str(item.get('pk', ''))
        sk = str(item.get('sk', ''))

        logical: dict[str, Any] = {'user_id': pk}

        if sk == 'CV':
            logical['cv_id'] = item.get('cv_id')
            return logical

        if sk.startswith('ARTIFACT#VPR#'):
            logical['vpr_id'] = item.get('vpr_id')
            logical['job_id'] = item.get('job_id')
            logical['application_id'] = item.get('job_id')
            return logical

        if sk.startswith('ARTIFACT#CV_TAILORED#'):
            _, _, _, cv_id, job_id, *_ = sk.split('#')
            logical['cvTailoringId'] = item.get('cvTailoringId')
            logical['cv_id'] = cv_id
            logical['job_id'] = job_id
            return logical

        if sk.startswith('ARTIFACT#COVER_LETTER#'):
            _, _, _, cv_id, job_id, *_ = sk.split('#')
            logical['coverLetterId'] = item.get('coverLetterId')
            logical['cv_id'] = cv_id
            logical['job_id'] = job_id
            return logical

        if sk.startswith('ARTIFACT#INTERVIEW_PREP#'):
            logical['interviewPrepId'] = sk.split('#')[-1]
            logical['job_id'] = item.get('job_id')
            return logical

        if sk.startswith('ARTIFACT#COMPANY_RESEARCH#'):
            logical['company_research_id'] = sk.split('#')[-1]
            logical['job_id'] = item.get('job_id')
            return logical

        if sk.startswith('ARTIFACT#GAP_ANALYSIS#'):
            _, _, _, cv_id, job_id = sk.split('#')
            logical['cv_id'] = cv_id
            logical['job_id'] = job_id
            return logical

        return logical

    def build_users_table_pk_sk(
        self,
        resource_type: str,
        user_id: str,
        identifiers: dict[str, Any],
    ) -> dict[str, str]:
        """Build users-table PK/SK for a resource type."""
        keys = self._build_users_storage_key(resource_type, user_id, identifiers)
        return {'pk': keys.pk, 'sk': keys.sk}

    # Alias for the method name used in runbook step text.
    def build_pk_sk_for_users_table(
        self,
        resource_type: str,
        user_id: str,
        identifiers: dict[str, Any],
    ) -> dict[str, str]:
        return self.build_users_table_pk_sk(resource_type, user_id, identifiers)

    def _build_users_storage_key(
        self,
        resource_type: str,
        user_id: str,
        identifiers: dict[str, Any],
    ) -> StorageKey:
        if resource_type == 'cv_upload':
            return StorageKey(pk=user_id, sk='CV')

        job_id = identifiers.get('job_id') or identifiers.get('application_id')
        cv_id = identifiers.get('cv_id')

        if resource_type == 'vpr_async':
            vpr_id = identifiers.get('vpr_id') or identifiers.get('request_id')
            return StorageKey(pk=user_id, sk=f'ARTIFACT#VPR#{vpr_id}')

        if resource_type == 'cv_tailoring_async':
            return StorageKey(pk=user_id, sk=f'ARTIFACT#CV_TAILORED#{cv_id}#{job_id}#v1')

        if resource_type == 'cover_letter_async':
            return StorageKey(pk=user_id, sk=f'ARTIFACT#COVER_LETTER#{cv_id}#{job_id}#v1')

        if resource_type == 'interview_prep_async':
            prep_id = identifiers.get('interviewPrepId') or identifiers.get('request_id')
            return StorageKey(pk=user_id, sk=f'ARTIFACT#INTERVIEW_PREP#{prep_id}')

        if resource_type == 'company_research_async':
            company_research_id = identifiers.get('company_research_id') or identifiers.get('job_id')
            return StorageKey(pk=user_id, sk=f'ARTIFACT#COMPANY_RESEARCH#{company_research_id}')

        if resource_type == 'gap_analysis':
            return StorageKey(pk=user_id, sk=f'ARTIFACT#GAP_ANALYSIS#{cv_id}#{job_id}')

        return StorageKey(pk=user_id, sk=f'ARTIFACT#{resource_type}')

    @staticmethod
    def _require(values: dict[str, Any], key: str) -> Any:
        value = values.get(key)
        if value is None or value == '':
            raise ValueError(f'{key} is required')
        return value
