"""Regression tests — DynamoDB VPR key scheme must never change."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from careervp.models.vpr import VPR


@pytest.mark.regression
class TestDynamoKeyScheme:
    def test_vpr_sort_key_prefix_unchanged(self) -> None:
        """VPR_SORT_KEY_PREFIX must be exactly 'ARTIFACT#VPR#v'."""
        from careervp.dal.dynamo_dal_handler import VPR_SORT_KEY_PREFIX

        assert VPR_SORT_KEY_PREFIX == 'ARTIFACT#VPR#v', (
            f"VPR_SORT_KEY_PREFIX changed to '{VPR_SORT_KEY_PREFIX}'. Changing this breaks all existing DynamoDB VPR lookups."
        )

    def test_user_vprs_gsi_index_name_unchanged(self) -> None:
        """USER_VPRS_INDEX GSI name must remain 'user_id-index'."""
        from careervp.dal.dynamo_dal_handler import USER_VPRS_INDEX

        assert USER_VPRS_INDEX == 'user_id-index', (
            f"USER_VPRS_INDEX changed to '{USER_VPRS_INDEX}'. Changing the GSI name requires a DynamoDB schema migration."
        )

    def test_save_vpr_pk_is_application_id(self, minimal_vpr: VPR) -> None:
        """DynamoDB pk must be the application_id value — never changed."""
        with patch('careervp.dal.dynamo_dal_handler.boto3'):
            from careervp.dal.dynamo_dal_handler import DynamoDalHandler

            dal = DynamoDalHandler.__new__(DynamoDalHandler)
            dal._table = MagicMock()
            dal._logger = MagicMock()
            dal.table_name = 'test-artifacts'
            dal._get_db_handler = MagicMock(return_value=dal._table)

        minimal_vpr.application_id = 'regression-app-001'
        dal.save_vpr(minimal_vpr)

        put_call = dal._table.put_item.call_args
        item = put_call.kwargs.get('Item') or (put_call.args[0].get('Item') if put_call.args else {})
        assert item.get('pk') == 'regression-app-001', f"pk is '{item.get('pk')}', expected 'regression-app-001'. PK scheme must not change."

    def test_save_vpr_sk_starts_with_prefix(self, minimal_vpr: VPR) -> None:
        """Sort key must start with VPR_SORT_KEY_PREFIX = 'ARTIFACT#VPR#v'."""
        from careervp.dal.dynamo_dal_handler import VPR_SORT_KEY_PREFIX

        with patch('careervp.dal.dynamo_dal_handler.boto3'):
            from careervp.dal.dynamo_dal_handler import DynamoDalHandler

            dal = DynamoDalHandler.__new__(DynamoDalHandler)
            dal._table = MagicMock()
            dal._logger = MagicMock()
            dal.table_name = 'test-artifacts'
            dal._get_db_handler = MagicMock(return_value=dal._table)

        minimal_vpr.version = 1
        dal.save_vpr(minimal_vpr)

        put_call = dal._table.put_item.call_args
        item = put_call.kwargs.get('Item') or (put_call.args[0].get('Item') if put_call.args else {})
        sk = item.get('sk', '')
        assert sk.startswith(VPR_SORT_KEY_PREFIX), (
            f"SK '{sk}' does not start with '{VPR_SORT_KEY_PREFIX}'. SK format must not change — existing items won't be found."
        )

    def test_save_vpr_sk_contains_version(self, minimal_vpr: VPR) -> None:
        """Sort key must include the version number for ordered retrieval."""
        with patch('careervp.dal.dynamo_dal_handler.boto3'):
            from careervp.dal.dynamo_dal_handler import DynamoDalHandler

            dal = DynamoDalHandler.__new__(DynamoDalHandler)
            dal._table = MagicMock()
            dal._logger = MagicMock()
            dal.table_name = 'test-artifacts'
            dal._get_db_handler = MagicMock(return_value=dal._table)

        minimal_vpr.version = 7
        dal.save_vpr(minimal_vpr)

        put_call = dal._table.put_item.call_args
        item = put_call.kwargs.get('Item') or (put_call.args[0].get('Item') if put_call.args else {})
        sk = item.get('sk', '')
        assert '7' in sk, f"SK '{sk}' does not contain version '7'. Version must appear in the sort key."
