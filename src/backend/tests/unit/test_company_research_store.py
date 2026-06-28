"""
Unit tests for careervp.logic.company_research_store.

TEST-FE-053 Category C: store idempotency (SC5)
TEST-FE-053 Category C2: worker failed row (SC5, SC8)
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture(autouse=True)
def _env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv('ARTIFACTS_TABLE_NAME', 'artifacts-table')
    monkeypatch.setenv('POWERTOOLS_SERVICE_NAME', 'test')
    monkeypatch.setenv('POWERTOOLS_METRICS_NAMESPACE', 'careervp')


# ---------------------------------------------------------------------------
# Category C: write_cr_processing idempotency — SC5
# ---------------------------------------------------------------------------


class TestWriteProcessingIdempotency:
    """TEST-FE-053 Category C: write_cr_processing is terminal-safe."""

    def test_write_processing_on_empty(self) -> None:
        """No existing item → put_item called."""
        from careervp.logic.company_research_store import write_cr_processing

        mock_table = MagicMock()
        mock_table.get_item.return_value = {'Item': None}

        with patch('careervp.logic.company_research_store.boto3') as mock_boto3:
            mock_boto3.resource.return_value.Table.return_value = mock_table
            write_cr_processing('app-1', 'user-1')

        mock_table.put_item.assert_called_once()
        item = mock_table.put_item.call_args[1]['Item']
        assert item['status'] == 'processing'
        assert item['artifactType'] == 'company_research'
        assert item['user_id'] == 'user-1'

    def test_write_processing_on_not_generated(self) -> None:
        """Existing {status:'not_generated'} → not terminal → put_item called."""
        from careervp.logic.company_research_store import write_cr_processing

        mock_table = MagicMock()
        mock_table.get_item.return_value = {
            'Item': {
                'applicationId': 'app-1',
                'artifactId': 'ARTIFACT#COMPANY_RESEARCH#app-1',
                'artifactType': 'company_research',
                'user_id': 'user-1',
                'status': 'not_generated',
            }
        }

        with patch('careervp.logic.company_research_store.boto3') as mock_boto3:
            mock_boto3.resource.return_value.Table.return_value = mock_table
            write_cr_processing('app-1', 'user-1')

        mock_table.put_item.assert_called_once()

    def test_no_overwrite_completed(self) -> None:
        """Existing item with research_data (worker-written) → terminal → put_item NOT called."""
        from careervp.logic.company_research_store import write_cr_processing

        mock_table = MagicMock()
        mock_table.get_item.return_value = {
            'Item': {
                'applicationId': 'app-1',
                'artifactId': 'ARTIFACT#COMPANY_RESEARCH#app-1',
                'artifactType': 'company_research',
                'user_id': 'user-1',
                'research_data': {'company_name': 'Acme'},
                'confidence_score': '0.95',
            }
        }

        with patch('careervp.logic.company_research_store.boto3') as mock_boto3:
            mock_boto3.resource.return_value.Table.return_value = mock_table
            write_cr_processing('app-1', 'user-1')

        mock_table.put_item.assert_not_called()

    def test_no_overwrite_failed(self) -> None:
        """Existing {status:'failed'} → terminal → put_item NOT called."""
        from careervp.logic.company_research_store import write_cr_processing

        mock_table = MagicMock()
        mock_table.get_item.return_value = {
            'Item': {
                'applicationId': 'app-1',
                'artifactId': 'ARTIFACT#COMPANY_RESEARCH#app-1',
                'artifactType': 'company_research',
                'user_id': 'user-1',
                'status': 'failed',
            }
        }

        with patch('careervp.logic.company_research_store.boto3') as mock_boto3:
            mock_boto3.resource.return_value.Table.return_value = mock_table
            write_cr_processing('app-1', 'user-1')

        mock_table.put_item.assert_not_called()


# ---------------------------------------------------------------------------
# Category C2: write_cr_failed — SC8
# ---------------------------------------------------------------------------


class TestWriteCrFailed:
    """TEST-FE-053 Category C2: write_cr_failed writes a terminal failed row."""

    def test_write_cr_failed_puts_failed_row(self) -> None:
        """write_cr_failed puts item with status='failed' and correct fields."""
        from careervp.logic.company_research_store import write_cr_failed

        mock_table = MagicMock()

        with patch('careervp.logic.company_research_store.boto3') as mock_boto3:
            mock_boto3.resource.return_value.Table.return_value = mock_table
            write_cr_failed('app-1', 'user-1')

        mock_table.put_item.assert_called_once()
        item = mock_table.put_item.call_args[1]['Item']
        assert item['status'] == 'failed'
        assert item['artifactType'] == 'company_research'
        assert item['user_id'] == 'user-1'
        assert item['applicationId'] == 'app-1'

    def test_write_cr_failed_overwrites_processing(self) -> None:
        """write_cr_failed always puts (no terminal guard), even over a processing row."""
        from careervp.logic.company_research_store import write_cr_failed

        mock_table = MagicMock()
        # Unlike write_cr_processing, write_cr_failed never calls get_item first.
        with patch('careervp.logic.company_research_store.boto3') as mock_boto3:
            mock_boto3.resource.return_value.Table.return_value = mock_table
            write_cr_failed('app-1', 'user-1')

        mock_table.get_item.assert_not_called()
        mock_table.put_item.assert_called_once()


# ---------------------------------------------------------------------------
# Integration-style: write_processing → write_failed → read confirms 'failed' — SC8
# ---------------------------------------------------------------------------


class TestFailedRowIntegration:
    """Simulate the full processing→failed lifecycle in-memory."""

    def test_get_failed_after_hard_fail(self) -> None:
        """write_cr_processing then write_cr_failed → read_cr_artifact returns failed status."""
        from careervp.logic.company_research_store import (
            read_cr_artifact,
            write_cr_failed,
            write_cr_processing,
        )

        store: dict[str, object] = {}

        def fake_put(Item: dict[str, object]) -> None:  # noqa: N803
            store.update(Item)

        def fake_get(Key: dict[str, object]) -> dict[str, object]:  # noqa: N803
            return {'Item': dict(store)} if store else {}

        mock_table = MagicMock()
        mock_table.put_item.side_effect = lambda **kwargs: fake_put(kwargs['Item'])
        mock_table.get_item.side_effect = lambda **kwargs: fake_get(kwargs['Key'])

        with patch('careervp.logic.company_research_store.boto3') as mock_boto3:
            mock_boto3.resource.return_value.Table.return_value = mock_table
            write_cr_processing('app-1', 'user-1')
            assert store.get('status') == 'processing'

            write_cr_failed('app-1', 'user-1')
            assert store.get('status') == 'failed'

            item = read_cr_artifact('app-1', 'user-1')

        assert item is not None
        assert item.get('status') == 'failed'
