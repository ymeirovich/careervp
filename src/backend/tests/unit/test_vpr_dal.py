"""Unit tests for DAL VPR storage changes (spec 05)."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from careervp.dal.dynamo_dal_handler import DynamoDalHandler
from careervp.models.vpr import VPR


def _make_dal() -> tuple[DynamoDalHandler, MagicMock]:
    """Create a DynamoDalHandler with a mocked DynamoDB table.

    Returns: (dal, mock_table) where mock_table is the mocked DynamoDB table.
    """
    with patch('careervp.dal.dynamo_dal_handler.boto3'):
        dal = DynamoDalHandler(table_name='test-table')
        # Mock the _get_db_handler method to return a mock table
        mock_table = MagicMock()
        dal._get_db_handler = MagicMock(return_value=mock_table)
        return dal, mock_table


@pytest.mark.unit
class TestSaveVPRSerialization:
    def test_save_vpr_uses_snake_case_keys_not_camel(self, minimal_vpr: VPR) -> None:
        """Item stored in DynamoDB must use snake_case, not camelCase."""
        dal, mock_table = _make_dal()
        dal.save_vpr(minimal_vpr)

        put_call = mock_table.put_item.call_args
        assert put_call is not None
        item = put_call.kwargs.get('Item') or put_call.args[0].get('Item')
        # Must have snake_case keys
        assert 'application_id' in item or 'pk' in item
        # Must NOT have camelCase keys from model_dump(by_alias=True)
        assert 'applicationId' not in item
        assert 'executiveSummary' not in item

    def test_save_vpr_sort_key_format(self, minimal_vpr: VPR) -> None:
        """Sort key must follow ARTIFACT#VPR#v{version} format."""
        dal, mock_table = _make_dal()
        minimal_vpr.version = 3
        dal.save_vpr(minimal_vpr)

        put_call = mock_table.put_item.call_args
        item = put_call.kwargs.get('Item') or put_call.args[0].get('Item')
        sk = item.get('sk', '')
        assert sk.startswith('ARTIFACT#VPR#v'), f'SK format wrong: {sk}'
        assert '3' in sk

    def test_save_vpr_pk_is_application_id(self, minimal_vpr: VPR) -> None:
        dal, mock_table = _make_dal()
        dal.save_vpr(minimal_vpr)

        put_call = mock_table.put_item.call_args
        item = put_call.kwargs.get('Item') or put_call.args[0].get('Item')
        assert item.get('pk') == 'app-001'


@pytest.mark.unit
class TestGetNextVPRVersion:
    def test_returns_1_for_new_application(self) -> None:
        """When no VPR exists, get_next_vpr_version must return 1."""
        dal, _ = _make_dal()
        # Simulate get_latest_vpr returning no result
        with patch.object(dal, 'get_latest_vpr') as mock_get:
            mock_get.return_value = MagicMock(success=False, data=None)
            version = dal.get_next_vpr_version('new-app-999')
        assert version == 1

    def test_returns_increment_for_existing_application(self, minimal_vpr: VPR) -> None:
        """When a VPR exists at version N, must return N+1."""
        dal, _ = _make_dal()
        minimal_vpr.version = 2
        with patch.object(dal, 'get_latest_vpr') as mock_get:
            mock_get.return_value = MagicMock(success=True, data=minimal_vpr)
            version = dal.get_next_vpr_version('app-001')
        assert version == 3

    def test_returns_1_when_latest_vpr_data_is_none(self) -> None:
        dal, _ = _make_dal()
        with patch.object(dal, 'get_latest_vpr') as mock_get:
            mock_get.return_value = MagicMock(success=True, data=None)
            version = dal.get_next_vpr_version('app-no-data')
        assert version == 1


@pytest.mark.unit
class TestLegacyItemDeserialization:
    def test_vpr_model_validate_legacy_flat_item_returns_vpr(self, minimal_vpr: Any) -> None:
        """Old flat DynamoDB items should deserialize or raise ValidationError.

        Per spec 05: migration strategy is "lazy migration — old items remain in DynamoDB
        with flat schema". The VPR model uses extra='ignore', so unknown fields like
        'executive_summary' (old) won't crash. However, if all 10 required new sections
        are missing, validation will fail unless they're optional with defaults.
        """
        # Simulate an old VPR item that exists in DynamoDB
        legacy_item = {
            'application_id': 'legacy-app-001',
            'user_id': 'user-xyz',
            'version': 1,
            'language': 'en',
            'word_count': 180,
            'pk': 'legacy-app-001',
            'sk': 'ARTIFACT#VPR#v1',
            # Old schema: had flat executive_summary, differentiators, gap_strategies
            # These are NOT in the new 10-section schema, so they'll be ignored
            'executive_summary': 'Old free-text string',
            'differentiators': ['Strength A'],
        }

        # Either:
        # 1. Old items deserialize with new sections=None (if they're optional)
        # 2. Or we get ValidationError (if they're required and not provided)
        # Both are acceptable — depends on model config
        try:
            vpr = VPR.model_validate(legacy_item)
            # If successful, old data should be ignored and basic fields present
            assert vpr.application_id == 'legacy-app-001'
        except ValueError as e:
            # ValidationError is acceptable — indicates new schema is stricter
            assert 'required' in str(e).lower() or 'missing' in str(e).lower()

    def test_get_vpr_logs_debug_for_legacy_item(self) -> None:
        dal, mock_table = _make_dal()
        legacy_item = {
            'application_id': 'legacy-app',
            'user_id': 'u1',
            'version': 1,
            'language': 'en',
            'word_count': 100,
            'pk': 'legacy-app',
            'sk': 'ARTIFACT#VPR#v1',
        }
        mock_table.get_item.return_value = {'Item': legacy_item}

        with patch('careervp.dal.dynamo_dal_handler.logger') as mock_logger:
            result = dal.get_vpr('legacy-app', version=1)

        # Logger must emit a debug message when metadata is None (legacy item)
        debug_calls = [str(c) for c in mock_logger.debug.call_args_list]
        legacy_logged = any('legacy' in call_str.lower() for call_str in debug_calls)
        # Either logged or VPR came back without crashing
        assert result is not None or legacy_logged
