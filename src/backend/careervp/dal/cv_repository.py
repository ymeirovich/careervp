"""CV repository focused on logical-to-physical storage key translation."""

from __future__ import annotations

from typing import Any

from careervp.dal.api_storage_adapter import ApiStorageAdapter


class CVRepository:
    """Repository utilities for CV storage key generation."""

    def __init__(self, storage_adapter: ApiStorageAdapter | None = None) -> None:
        self.storage_adapter = storage_adapter or ApiStorageAdapter()

    def build_s3_object_key(
        self,
        user_id: str,
        cv_id: str,
        file_extension: str = 'pdf',
    ) -> str:
        """Build S3 key using logical identifiers through the storage adapter."""
        mapping = self.storage_adapter.map_logical_to_physical_keys(
            resource_type='cv',
            logical_identifiers={'user_id': user_id, 'cv_id': cv_id},
        )
        s3_mapping = mapping.get('s3')
        if not isinstance(s3_mapping, dict):
            raise ValueError('Adapter did not return s3 mapping for cv resource')
        key_value: Any = s3_mapping.get('key')
        if not isinstance(key_value, str) or not key_value:
            raise ValueError('Adapter returned invalid S3 key for cv resource')

        normalized_ext = file_extension.lstrip('.').lower() or 'pdf'
        if normalized_ext == 'pdf':
            return key_value
        base_key = key_value.rsplit('.', 1)[0]
        return f'{base_key}.{normalized_ext}'
