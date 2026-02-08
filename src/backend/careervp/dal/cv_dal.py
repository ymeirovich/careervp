"""Compatibility DAL for CV retrieval used by integration tests."""

from __future__ import annotations

from typing import Any, cast

import boto3


class CVTable:
    """Lightweight CV table wrapper."""

    def __init__(self, table_name: str | None = None) -> None:
        resource = boto3.resource('dynamodb')
        self.table = resource.Table(table_name) if table_name else resource.Table('cv-table')

    def get_item(self, key: dict[str, Any]) -> dict[str, Any]:
        """Proxy get_item to underlying table."""
        return cast(dict[str, Any], self.table.get_item(Key=key))

    def put_item(self, Item: dict[str, Any]) -> dict[str, Any]:  # noqa: N803
        """Proxy put_item to underlying table."""
        return cast(dict[str, Any], self.table.put_item(Item=Item))
