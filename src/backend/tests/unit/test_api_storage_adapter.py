"""Unit tests for logical-to-physical storage adapter mappings."""

from careervp.dal.api_storage_adapter import ApiStorageAdapter


def test_cv_key_generation() -> None:
    adapter = ApiStorageAdapter()

    mapping = adapter.map_logical_to_physical_keys(
        resource_type='cv',
        logical_identifiers={'user_id': 'user-123', 'cv_id': 'cv-abc'},
    )

    assert mapping['s3']['key'] == 'cvs/user-123/cv-abc.pdf'
    assert mapping['users_table'] == {'pk': 'user-123', 'sk': 'CV'}


def test_job_pk_sk_construction() -> None:
    adapter = ApiStorageAdapter()

    pk, sk = adapter.build_pk_sk_for_users_table(
        resource_type='job',
        user_id='user-123',
        identifiers={'job_id': 'job-456'},
    )
    mapping = adapter.map_logical_to_physical_keys(
        resource_type='job',
        logical_identifiers={'job_id': 'job-456'},
    )

    assert (pk, sk) == ('user-123', 'JOB#job-456')
    assert mapping['jobs_table'] == {'job_id': 'job-456'}


def test_vpr_key_mapping() -> None:
    adapter = ApiStorageAdapter()

    physical = adapter.map_logical_to_physical_keys(
        resource_type='vpr',
        logical_identifiers={'vpr_id': 'vpr-789'},
    )
    logical = adapter.map_physical_to_logical_ids(
        resource_type='vpr',
        item={'job_id': 'vpr-789'},
    )

    assert physical['vpr_table'] == {'vpr_id': 'vpr-789'}
    assert physical['jobs_table'] == {'job_id': 'vpr-789'}
    assert logical == {'vpr_id': 'vpr-789', 'job_id': 'vpr-789'}
