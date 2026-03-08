"""Unit tests for paginated get_vpr_jobs_by_user in jobs_repository.

Covers RECOVERY_004 pagination fix:
- Single page returns valid VPR items
- Multi-page accumulation collects items from later pages
- Stops when limit satisfied without fetching extra pages
- Caps at safe_limit; ScanIndexForward=False for newest-first
"""

from __future__ import annotations

import os
from unittest.mock import MagicMock

import pytest

os.environ.setdefault('POWERTOOLS_SERVICE_NAME', 'careervp-test')
os.environ.setdefault('LOG_LEVEL', 'DEBUG')
os.environ.setdefault('JOBS_TABLE_NAME', 'test-jobs-table')


def _vpr(job_id: str, user_id: str = 'u1') -> dict:
    return {'job_id': job_id, 'user_id': user_id, 'application_id': f'app-{job_id}', 'status': 'COMPLETED'}


def _non_vpr(job_id: str, user_id: str = 'u1') -> dict:
    return {'job_id': job_id, 'user_id': user_id, 'status': 'COMPLETED'}


@pytest.fixture
def table():
    return MagicMock()


@pytest.fixture
def repo(table):
    from careervp.dal.jobs_repository import JobsRepository

    r = JobsRepository.__new__(JobsRepository)
    r.table = table
    return r


class TestVprPagination:
    def test_single_page_all_valid(self, repo, table):
        items = [_vpr(f'j{i}') for i in range(5)]
        table.query.return_value = {'Items': items}
        result = repo.get_vpr_jobs_by_user(user_id='u1', limit=20)
        assert len(result) == 5
        table.query.assert_called_once()

    def test_second_page_provides_valid_items(self, repo, table):
        page1 = [_non_vpr(f'np{i}') for i in range(10)]
        page2 = [_vpr(f'v{i}') for i in range(3)]
        table.query.side_effect = [
            {'Items': page1, 'LastEvaluatedKey': {'user_id': 'u1', 'job_id': 'np9'}},
            {'Items': page2},
        ]
        result = repo.get_vpr_jobs_by_user(user_id='u1', limit=20)
        assert len(result) == 3
        assert table.query.call_count == 2

    def test_stops_after_limit_satisfied(self, repo, table):
        page1 = [_vpr(f'j{i}') for i in range(5)]
        table.query.return_value = {'Items': page1, 'LastEvaluatedKey': {'job_id': 'j4'}}
        result = repo.get_vpr_jobs_by_user(user_id='u1', limit=5)
        assert len(result) == 5
        assert table.query.call_count == 1

    def test_caps_at_safe_limit(self, repo, table):
        items = [_vpr(f'j{i}') for i in range(30)]
        table.query.return_value = {'Items': items}
        result = repo.get_vpr_jobs_by_user(user_id='u1', limit=10)
        assert len(result) == 10

    def test_empty_when_no_valid_items(self, repo, table):
        table.query.return_value = {'Items': [_non_vpr('np0')]}
        assert repo.get_vpr_jobs_by_user(user_id='u1', limit=20) == []

    def test_exclusive_start_key_used(self, repo, table):
        last_key = {'user_id': 'u1', 'job_id': 'j-last'}
        table.query.side_effect = [
            {'Items': [_non_vpr('np0')], 'LastEvaluatedKey': last_key},
            {'Items': [_vpr('v1')]},
        ]
        repo.get_vpr_jobs_by_user(user_id='u1', limit=5)
        second_kwargs = table.query.call_args_list[1][1]
        assert second_kwargs.get('ExclusiveStartKey') == last_key

    def test_scan_index_forward_false(self, repo, table):
        table.query.return_value = {'Items': [_vpr('j0')]}
        repo.get_vpr_jobs_by_user(user_id='u1', limit=5)
        assert table.query.call_args[1].get('ScanIndexForward') is False
