"""Logical API ID to physical storage key adapter.

This adapter keeps existing storage infrastructure while exposing OpenAPI
logical identifiers (`cv_id`, `job_id`, `vpr_id`, etc.) to handlers/repositories.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Literal

ResourceType = Literal['cv', 'job', 'vpr', 'gap_response', 'company_research']

_RESOURCE_ALIASES: dict[str, ResourceType] = {
    'cv': 'cv',
    'cv_upload': 'cv',
    'job': 'job',
    'jobs': 'job',
    'vpr': 'vpr',
    'vpr_async': 'vpr',
    'gap_response': 'gap_response',
    'gap_analysis': 'gap_response',
    'company_research': 'company_research',
    'company_research_async': 'company_research',
}


class ApiStorageAdapter:
    """Translate between logical API identifiers and active physical storage keys."""

    def map_logical_to_physical_keys(
        self,
        resource_type: str,
        logical_identifiers: dict[str, Any],
    ) -> dict[str, Any]:
        """Map logical IDs to physical key schema used by active infrastructure."""
        normalized_type = self._normalize_resource_type(resource_type)
        ids = dict(logical_identifiers)

        if normalized_type == 'cv':
            user_id = self._require_string(ids, ('user_id',))
            cv_id = self._require_string(ids, ('cv_id',))
            pk, sk = self.build_pk_sk_for_users_table('cv', user_id, ids)
            return {
                's3': {
                    'bucket': 'cvs',
                    'key': self.build_cv_s3_key(user_id, cv_id, extension='pdf'),
                },
                'users_table': {'pk': pk, 'sk': sk},
            }

        if normalized_type == 'job':
            job_id = self._require_string(ids, ('job_id', 'application_id'))
            return {'jobs_table': {'job_id': job_id}}

        if normalized_type == 'vpr':
            vpr_id = self._require_string(ids, ('vpr_id', 'job_id', 'application_id'))
            return {
                'vpr_table': {'vpr_id': vpr_id},
                # Active infra stores VPR async status in jobs table keyed by job_id.
                'jobs_table': {'job_id': vpr_id},
            }

        if normalized_type == 'gap_response':
            user_id = self._require_string(ids, ('user_id',))
            job_id = self._require_string(ids, ('job_id', 'application_id'))
            pk, sk = self.build_pk_sk_for_users_table('gap_response', user_id, ids)
            return {
                'gap_responses_table': {'user_id': user_id, 'job_id': job_id},
                'users_table': {'pk': pk, 'sk': sk},
            }

        # company_research
        user_id = self._require_string(ids, ('user_id',))
        job_id = self._require_string(ids, ('job_id', 'company_research_id'))
        pk, sk = self.build_pk_sk_for_users_table('company_research', user_id, ids)
        return {
            'company_research_table': {'job_id': job_id},
            'users_table': {'pk': pk, 'sk': sk},
        }

    def map_physical_to_logical_ids(
        self,
        resource_type: str,
        item: dict[str, Any],
    ) -> dict[str, Any]:
        """Map physical record fields back to OpenAPI logical identifiers."""
        normalized_type = self._normalize_resource_type(resource_type)

        if normalized_type == 'job':
            return self._map_job_from_physical(item)

        if normalized_type == 'vpr':
            return self._map_vpr_from_physical(item)

        if normalized_type == 'cv':
            return self._map_cv_from_physical(item)

        if normalized_type == 'gap_response':
            return self._map_gap_response_from_physical(item)

        return self._map_company_research_from_physical(item)

    def _map_job_from_physical(self, item: Mapping[str, Any]) -> dict[str, Any]:
        job_id = self._optional_string(item, ('job_id',))
        return {'job_id': job_id} if job_id else {}

    def _map_vpr_from_physical(self, item: Mapping[str, Any]) -> dict[str, Any]:
        vpr_id = self._optional_string(item, ('vpr_id', 'job_id', 'application_id', 'pk'))
        if not vpr_id:
            return {}
        return {'vpr_id': vpr_id, 'job_id': vpr_id}

    def _map_cv_from_physical(self, item: Mapping[str, Any]) -> dict[str, Any]:
        user_id = self._optional_string(item, ('user_id', 'pk'))
        cv_id = self._optional_string(item, ('cv_id',))
        if not cv_id:
            source_file_key = self._optional_string(item, ('source_file_key',))
            if source_file_key:
                cv_id = self._extract_cv_id_from_s3_key(source_file_key)
        logical: dict[str, Any] = {}
        if user_id:
            logical['user_id'] = user_id
        if cv_id:
            logical['cv_id'] = cv_id
        return logical

    def _map_gap_response_from_physical(self, item: Mapping[str, Any]) -> dict[str, Any]:
        user_id = self._optional_string(item, ('user_id', 'pk'))
        job_id = self._optional_string(item, ('job_id', 'application_id'))
        if not job_id:
            sk = self._optional_string(item, ('sk',))
            if sk and sk.startswith('ARTIFACT#GAP_RESPONSES#'):
                job_id = sk.split('ARTIFACT#GAP_RESPONSES#', 1)[1]
        logical: dict[str, Any] = {}
        if user_id:
            logical['user_id'] = user_id
        if job_id:
            logical['job_id'] = job_id
        return logical

    def _map_company_research_from_physical(self, item: Mapping[str, Any]) -> dict[str, Any]:
        user_id = self._optional_string(item, ('user_id', 'pk'))
        job_id = self._optional_string(item, ('job_id', 'application_id'))
        company_research_id = self._optional_string(item, ('company_research_id',))
        logical = {}
        if user_id:
            logical['user_id'] = user_id
        if job_id:
            logical['job_id'] = job_id
        if company_research_id:
            logical['company_research_id'] = company_research_id
        elif job_id:
            logical['company_research_id'] = job_id
        return logical

    def build_pk_sk_for_users_table(
        self,
        resource_type: str,
        user_id: str,
        identifiers: dict[str, Any],
    ) -> tuple[str, str]:
        """Build users table PK/SK tuple for a resource type."""
        normalized_type = self._normalize_resource_type(resource_type)
        if normalized_type == 'cv':
            return user_id, 'CV'
        if normalized_type == 'job':
            job_id = self._require_string(identifiers, ('job_id', 'application_id'))
            return user_id, f'JOB#{job_id}'
        if normalized_type == 'vpr':
            vpr_id = self._require_string(identifiers, ('vpr_id', 'job_id', 'application_id'))
            return user_id, f'ARTIFACT#VPR#{vpr_id}'
        if normalized_type == 'gap_response':
            job_id = self._require_string(identifiers, ('job_id', 'application_id'))
            return user_id, f'ARTIFACT#GAP_RESPONSES#{job_id}'
        company_research_id = self._require_string(
            identifiers,
            ('company_research_id', 'job_id'),
        )
        return user_id, f'ARTIFACT#COMPANY_RESEARCH#{company_research_id}'

    def build_users_table_pk_sk(
        self,
        resource_type: str,
        user_id: str,
        identifiers: dict[str, Any],
    ) -> dict[str, str]:
        """Compatibility helper returning users-table key as dict."""
        pk, sk = self.build_pk_sk_for_users_table(resource_type, user_id, identifiers)
        return {'pk': pk, 'sk': sk}

    def build_cv_s3_key(self, user_id: str, cv_id: str, extension: str = 'pdf') -> str:
        """Build canonical CV S3 object key."""
        cleaned_ext = extension.lstrip('.').lower() or 'pdf'
        return f'cvs/{user_id}/{cv_id}.{cleaned_ext}'

    @staticmethod
    def _normalize_resource_type(resource_type: str) -> ResourceType:
        normalized = _RESOURCE_ALIASES.get(resource_type)
        if normalized is None:
            raise ValueError(f'Unsupported resource_type: {resource_type}')
        return normalized

    @staticmethod
    def _require_string(values: Mapping[str, Any], keys: tuple[str, ...]) -> str:
        value = ApiStorageAdapter._optional_string(values, keys)
        if value is None:
            joined = ', '.join(keys)
            raise ValueError(f'One of [{joined}] is required')
        return value

    @staticmethod
    def _optional_string(values: Mapping[str, Any], keys: tuple[str, ...]) -> str | None:
        for key in keys:
            raw = values.get(key)
            if isinstance(raw, str) and raw.strip():
                return raw.strip()
        return None

    @staticmethod
    def _extract_cv_id_from_s3_key(source_file_key: str) -> str | None:
        # Expected canonical pattern: cvs/{user_id}/{cv_id}.{ext}
        parts = source_file_key.split('/')
        if len(parts) < 3:
            return None
        filename = parts[-1]
        if '.' not in filename:
            return filename
        return filename.rsplit('.', 1)[0]
