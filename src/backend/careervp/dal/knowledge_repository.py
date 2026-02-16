"""Knowledge Base repository for gap responses and company research."""

from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any

import boto3
from boto3.dynamodb.conditions import Key

from careervp.models.result import Result, ResultCode

# TTL constants in seconds
GAP_RESPONSE_TTL = 63_072_000  # 24 months
COMPANY_RESEARCH_TTL = 2_592_000  # 30 days


class KnowledgeRepository:
    """CRUD operations for knowledge base entries."""

    def __init__(self, table_name: str, dynamodb_resource: Any | None = None) -> None:
        self._resource = dynamodb_resource or boto3.resource('dynamodb')
        self._table = self._resource.Table(table_name)

    def save_gap_response(
        self,
        user_id: str,
        job_id: str,
        cv_id: str,
        question_id: str,
        response_id: str,
        response_text: str,
    ) -> Result[dict[str, Any]]:
        """Save a gap analysis response."""
        now = datetime.now(timezone.utc)
        ttl_epoch = int(time.time()) + GAP_RESPONSE_TTL

        item = {
            'pk': f'USER#{user_id}',
            'sk': f'GAP_RESPONSE#{job_id}#{question_id}',
            'entity_type': 'GAP_RESPONSE',
            'user_id': user_id,
            'job_id': job_id,
            'cv_id': cv_id,
            'question_id': question_id,
            'response_id': response_id,
            'response_text': response_text,
            'created_at': now.isoformat(),
            'ttl': ttl_epoch,
        }

        try:
            self._table.put_item(Item=item)
            return Result(success=True, data=item, code=ResultCode.GAP_RESPONSES_SAVED)
        except Exception as exc:
            return Result(success=False, error=f'Failed to save gap response: {exc}', code=ResultCode.DYNAMODB_ERROR)

    def get_gap_responses(self, user_id: str, job_id: str | None = None) -> Result[list[dict[str, Any]]]:
        """Retrieve gap responses for a user, optionally filtered by job."""
        try:
            pk = f'USER#{user_id}'
            if job_id:
                sk_prefix = f'GAP_RESPONSE#{job_id}#'
                response = self._table.query(
                    KeyConditionExpression=Key('pk').eq(pk) & Key('sk').begins_with(sk_prefix),
                )
            else:
                response = self._table.query(
                    KeyConditionExpression=Key('pk').eq(pk) & Key('sk').begins_with('GAP_RESPONSE#'),
                )
            items = response.get('Items', [])
            return Result(success=True, data=items, code=ResultCode.SUCCESS)
        except Exception as exc:
            return Result(success=False, error=f'Failed to get gap responses: {exc}', code=ResultCode.DYNAMODB_ERROR)

    def save_company_research(
        self,
        user_id: str,
        job_id: str,
        company_research_id: str,
        company_name: str,
        research_data: dict[str, Any],
    ) -> Result[dict[str, Any]]:
        """Save company research with 30-day TTL."""
        now = datetime.now(timezone.utc)
        ttl_epoch = int(time.time()) + COMPANY_RESEARCH_TTL

        item = {
            'pk': f'USER#{user_id}',
            'sk': f'COMPANY_RESEARCH#{job_id}',
            'entity_type': 'COMPANY_RESEARCH',
            'user_id': user_id,
            'job_id': job_id,
            'company_research_id': company_research_id,
            'company_name': company_name,
            'research_data': research_data,
            'cached_at': now.isoformat(),
            'ttl': ttl_epoch,
        }

        try:
            self._table.put_item(Item=item)
            return Result(success=True, data=item, code=ResultCode.COMPANY_RESEARCHED)
        except Exception as exc:
            return Result(success=False, error=f'Failed to save company research: {exc}', code=ResultCode.DYNAMODB_ERROR)

    def get_company_research(self, user_id: str, job_id: str) -> Result[dict[str, Any] | None]:
        """Retrieve company research for a specific job."""
        try:
            pk = f'USER#{user_id}'
            sk = f'COMPANY_RESEARCH#{job_id}'
            response = self._table.get_item(Key={'pk': pk, 'sk': sk})
            item = response.get('Item')
            return Result(success=True, data=item, code=ResultCode.SUCCESS)
        except Exception as exc:
            return Result(success=False, error=f'Failed to get company research: {exc}', code=ResultCode.DYNAMODB_ERROR)
