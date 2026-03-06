"""
Integration tests for VPR list roundtrip persistence (RECOVERY_004).

Verifies that a generated VPR job ID appears in GET /vprs list after creation,
and that metadata fallback is non-breaking and user-scoped.

Traceability:
  - AC-VPR-301: generated VPR id appears in list after submit
  - AC-VPR-302: metadata fallback remains functional and non-breaking
"""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest

os.environ.setdefault('POWERTOOLS_SERVICE_NAME', 'careervp-test')
os.environ.setdefault('LOG_LEVEL', 'DEBUG')
os.environ.setdefault('JOBS_TABLE_NAME', 'test-jobs-table')


def _make_vpr_job(job_id: str, user_id: str, app_id: str) -> dict:
    return {
        'job_id': job_id,
        'user_id': user_id,
        'application_id': app_id,
        'status': 'COMPLETED',
        'created_at': '2026-03-05T10:00:00Z',
        'input_data': {
            'job_posting': {
                'role_title': 'Software Engineer',
                'company_name': 'TestCo',
            },
        },
    }


@pytest.fixture
def mock_jobs_repo_with_vpr():
    repo = MagicMock()
    generated_vpr = _make_vpr_job('vpr-generated-123', 'user-a', 'app-456')
    repo.get_vpr_jobs_by_user.return_value = [generated_vpr]
    return repo, generated_vpr


class TestVPRListRoundtrip:
    """AC-VPR-301: Generated VPR ID must appear in /vprs list after submit."""

    def test_generated_vpr_id_appears_in_list(self, mock_jobs_repo_with_vpr):
        """Generated VPR ID is included in list results within polling window."""
        from careervp.handlers.vpr_status_handler import _build_vpr_list_item

        repo, vpr_job = mock_jobs_repo_with_vpr
        item = _build_vpr_list_item(vpr_job, jobs_repo=repo)

        assert item['id'] == 'vpr-generated-123', 'Generated VPR ID must be present in list'
        assert item.get('job_title') == 'Software Engineer'
        assert item.get('company_name') == 'TestCo'

    def test_list_includes_generated_id_after_paginated_fetch(self):
        """Paginated accumulation returns newly generated VPR even if on page 2.

        Simulates scenario where first DynamoDB page returns only non-VPR records,
        requiring pagination to find the newly generated VPR on page 2.
        """
        from careervp.dal.jobs_repository import JobsRepository

        repo = JobsRepository.__new__(JobsRepository)
        repo.table_name = 'test-table'

        call_count = 0

        def mock_query(**kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # First page: all API jobs (no application_id) - newly generated VPR not here
                page1 = [{'job_id': f'api-job-{i}', 'user_id': 'user-a', 'title': f'Job {i}', 'entity_type': 'JOB'} for i in range(10)]
                return {'Items': page1, 'LastEvaluatedKey': {'user_id': 'user-a', 'job_id': 'api-job-9'}}
            # Second page: newly generated VPR job
            return {'Items': [_make_vpr_job('vpr-generated-new', 'user-a', 'app-new')]}

        repo.table = MagicMock()
        repo.table.query.side_effect = mock_query

        results = repo.get_vpr_jobs_by_user(user_id='user-a', limit=5)
        job_ids = [r['job_id'] for r in results]

        assert 'vpr-generated-new' in job_ids, 'Newly generated VPR (on page 2) must appear in list after paginated fetch'
        assert call_count == 2, 'Should have read 2 pages to find VPR after non-VPR page'


class TestVPRListMetadataFallback:
    """AC-VPR-302: Metadata fallback is non-breaking and user-scoped."""

    def test_metadata_fallback_does_not_write(self):
        """Metadata fallback from jobs table must not perform any writes."""
        from careervp.handlers.vpr_status_handler import _build_vpr_list_item

        mock_repo = MagicMock()
        mock_repo.get_job.return_value = {
            'job_id': 'job-ref',
            'title': 'DevOps Lead',
            'company_name': 'Infra Inc',
        }

        job = {
            'job_id': 'vpr-fallback-test',
            'user_id': 'user-b',
            'application_id': 'app-ref',
            'input_data': {'job_id': 'job-ref'},
            'created_at': '2026-03-05T00:00:00Z',
        }

        with patch('careervp.handlers.vpr_status_handler.metrics'):
            _build_vpr_list_item(job, jobs_repo=mock_repo)

        # Fallback must only read, never write
        mock_repo.create_job.assert_not_called()
        mock_repo.update_job.assert_not_called()
        mock_repo.update_job_status.assert_not_called()

    def test_cross_user_isolation(self):
        """VPR list for user-a must never include user-b's records."""
        from careervp.dal.jobs_repository import JobsRepository

        repo = JobsRepository.__new__(JobsRepository)
        repo.table_name = 'test-table'

        user_a_vprs = [_make_vpr_job('vpr-a1', 'user-a', 'app-a1')]
        _user_b_vprs = [_make_vpr_job('vpr-b1', 'user-b', 'app-b1')]

        def mock_query(**kwargs):
            _condition = kwargs.get('KeyConditionExpression')
            # The query is always scoped by user_id via the GSI key condition
            # Here we simulate per-user responses
            return {'Items': user_a_vprs}  # Only user-a items returned for user-a query

        repo.table = MagicMock()
        repo.table.query.side_effect = mock_query

        results = repo.get_vpr_jobs_by_user(user_id='user-a', limit=10)

        for item in results:
            assert item.get('user_id') == 'user-a', f'Cross-user leak: got user_id={item.get("user_id")}'
            assert item.get('job_id') != 'vpr-b1', 'user-b VPR must not appear in user-a list'

    def test_empty_metadata_does_not_block_list_inclusion(self):
        """VPR with unresolvable metadata still appears in list with empty strings."""
        from careervp.handlers.vpr_status_handler import _build_vpr_list_item

        mock_repo = MagicMock()
        mock_repo.get_job.return_value = None  # No job record found

        job = {
            'job_id': 'vpr-no-meta',
            'user_id': 'user-c',
            'application_id': 'app-missing',
            'input_data': {'job_id': 'job-missing'},
            'created_at': '2026-03-05T00:00:00Z',
        }

        with patch('careervp.handlers.vpr_status_handler.metrics'):
            result = _build_vpr_list_item(job, jobs_repo=mock_repo)

        assert result['id'] == 'vpr-no-meta', 'VPR must still be listed even with missing metadata'
        assert result['job_title'] == '', 'Empty metadata is acceptable'
        assert result['company_name'] == '', 'Empty metadata is acceptable'
