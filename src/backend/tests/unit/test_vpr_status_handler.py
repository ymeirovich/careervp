"""
Unit tests for vpr_status_handler._build_vpr_list_item metadata resolution.

Covers:
- AC-VPR-LIST-001: job_title/company_name resolved from input_data.job_posting when present
- AC-VPR-LIST-001: fallback to jobs table when job_posting absent
- Negative edge case: missing both sources returns empty strings without exception
"""

import os
from unittest.mock import MagicMock, patch

import pytest

os.environ.setdefault('POWERTOOLS_SERVICE_NAME', 'careervp-test')
os.environ.setdefault('LOG_LEVEL', 'DEBUG')
os.environ.setdefault('JOBS_TABLE_NAME', 'test-jobs-table')

from careervp.handlers.vpr_status_handler import _build_vpr_list_item  # noqa: E402


@pytest.fixture(autouse=True)
def reset_environment(monkeypatch):
    monkeypatch.setenv('JOBS_TABLE_NAME', 'test-jobs-table')
    monkeypatch.setenv('POWERTOOLS_SERVICE_NAME', 'careervp-test')
    monkeypatch.setenv('LOG_LEVEL', 'DEBUG')


@pytest.fixture
def mock_jobs_repo():
    return MagicMock()


# ---------------------------------------------------------------------------
# test_vpr_list_item_uses_input_data_job_posting_when_present
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_vpr_list_item_uses_input_data_job_posting_when_present(mock_jobs_repo):
    """When input_data.job_posting has role_title and company_name, use them directly."""
    job = {
        'job_id': 'vpr-001',
        'created_at': '2026-03-04T00:00:00Z',
        'input_data': {
            'job_posting': {
                'role_title': 'Senior Engineer',
                'company_name': 'Acme Corp',
            }
        },
    }

    result = _build_vpr_list_item(job, jobs_repo=mock_jobs_repo)

    assert result['job_title'] == 'Senior Engineer', 'job_title should come from job_posting.role_title'
    assert result['company_name'] == 'Acme Corp', 'company_name should come from job_posting.company_name'
    assert result['id'] == 'vpr-001'
    mock_jobs_repo.get_job.assert_not_called()


@pytest.mark.unit
def test_vpr_list_item_uses_input_data_job_posting_title_alias(mock_jobs_repo):
    """Alias fields (title / company) are accepted when canonical fields absent."""
    job = {
        'job_id': 'vpr-002',
        'created_at': '2026-03-04T00:00:00Z',
        'input_data': {
            'job_posting': {
                'title': 'Product Manager',
                'company': 'Beta Inc',
            }
        },
    }

    result = _build_vpr_list_item(job, jobs_repo=mock_jobs_repo)

    assert result['job_title'] == 'Product Manager'
    assert result['company_name'] == 'Beta Inc'
    mock_jobs_repo.get_job.assert_not_called()


# ---------------------------------------------------------------------------
# test_vpr_list_item_falls_back_to_jobs_table_when_missing_job_posting
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_vpr_list_item_falls_back_to_jobs_table_when_missing_job_posting(mock_jobs_repo):
    """When input_data has no job_posting, resolve metadata from jobs table via input_data.job_id."""
    mock_jobs_repo.get_job.return_value = {
        'job_id': 'job-abc',
        'title': 'Data Scientist',
        'company_name': 'DataCo',
    }

    job = {
        'job_id': 'vpr-003',
        'created_at': '2026-03-04T00:00:00Z',
        'input_data': {
            'job_id': 'job-abc',
            'cv_id': 'cv-xyz',
        },
    }

    with patch('careervp.handlers.vpr_status_handler.metrics') as mock_metrics:
        result = _build_vpr_list_item(job, jobs_repo=mock_jobs_repo)

    assert result['job_title'] == 'Data Scientist', 'job_title should fall back to jobs table title'
    assert result['company_name'] == 'DataCo', 'company_name should fall back to jobs table company_name'
    mock_jobs_repo.get_job.assert_called_once_with('job-abc')
    mock_metrics.add_metric.assert_called_once_with(name='VPRMetadataFallbackUsed', unit='Count', value=1)


@pytest.mark.unit
def test_vpr_list_item_falls_back_via_application_id(mock_jobs_repo):
    """When input_data lacks job_id, fall back using top-level application_id."""
    mock_jobs_repo.get_job.return_value = {
        'job_id': 'app-999',
        'title': 'Backend Dev',
        'company': 'TechCorp',
    }

    job = {
        'job_id': 'vpr-004',
        'application_id': 'app-999',
        'created_at': '2026-03-04T00:00:00Z',
        'input_data': {'cv_id': 'cv-xyz'},
    }

    with patch('careervp.handlers.vpr_status_handler.metrics'):
        result = _build_vpr_list_item(job, jobs_repo=mock_jobs_repo)

    assert result['job_title'] == 'Backend Dev'
    assert result['company_name'] == 'TechCorp'
    mock_jobs_repo.get_job.assert_called_once_with('app-999')


# ---------------------------------------------------------------------------
# test_vpr_list_item_handles_missing_fallback_without_exception
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_vpr_list_item_handles_missing_fallback_without_exception(mock_jobs_repo):
    """When neither job_posting nor jobs table record exists, return empty strings without raising."""
    mock_jobs_repo.get_job.return_value = None

    job = {
        'job_id': 'vpr-005',
        'created_at': '2026-03-04T00:00:00Z',
        'input_data': {'job_id': 'job-missing'},
    }

    with patch('careervp.handlers.vpr_status_handler.metrics'):
        result = _build_vpr_list_item(job, jobs_repo=mock_jobs_repo)

    assert result['job_title'] == '', 'job_title should be empty when unresolvable'
    assert result['company_name'] == '', 'company_name should be empty when unresolvable'
    assert result['id'] == 'vpr-005'


@pytest.mark.unit
def test_vpr_list_item_handles_no_input_data_without_exception():
    """No jobs_repo, no input_data — returns empty strings without raising."""
    job = {
        'job_id': 'vpr-006',
        'created_at': '2026-03-04T00:00:00Z',
    }

    result = _build_vpr_list_item(job, jobs_repo=None)

    assert result['job_title'] == ''
    assert result['company_name'] == ''


@pytest.mark.unit
def test_vpr_list_item_jobs_repo_exception_does_not_propagate(mock_jobs_repo):
    """If jobs table lookup raises, the list item is still returned with empty metadata."""
    mock_jobs_repo.get_job.side_effect = Exception('DynamoDB timeout')

    job = {
        'job_id': 'vpr-007',
        'created_at': '2026-03-04T00:00:00Z',
        'input_data': {'job_id': 'job-boom'},
    }

    with patch('careervp.handlers.vpr_status_handler.metrics'):
        result = _build_vpr_list_item(job, jobs_repo=mock_jobs_repo)

    assert result['job_title'] == ''
    assert result['company_name'] == ''
    assert result['id'] == 'vpr-007'
