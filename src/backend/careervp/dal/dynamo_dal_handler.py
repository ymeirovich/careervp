from typing import Any

import boto3
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError
from mypy_boto3_dynamodb import DynamoDBServiceResource
from mypy_boto3_dynamodb.service_resource import Table
from pydantic import ValidationError

from careervp.dal.db_handler import DalHandler
from careervp.handlers.utils.observability import logger, tracer
from careervp.models.cv import UserCV
from careervp.models.exceptions import InternalServerException
from careervp.models.result import Result, ResultCode
from careervp.models.vpr import VPR

VPR_SORT_KEY_PREFIX = 'ARTIFACT#VPR#v'
USER_VPRS_INDEX = 'user_id-index'
# Storage per docs/specs/03-vpr-generator.md:14 uses PK=applicationId with ARTIFACT#VPR#v{version} SK.


class DynamoDalHandler(DalHandler):
    def __init__(self, table_name: str):
        self.table_name = table_name

    def _get_db_handler(self, table_name: str) -> Table:
        logger.info('opening connection to dynamodb table', table_name=table_name)
        session = boto3.session.Session()
        dynamodb: DynamoDBServiceResource = session.resource('dynamodb')
        return dynamodb.Table(table_name)

    @tracer.capture_method(capture_response=False)
    def save_cv(self, user_cv: UserCV) -> None:
        logger.append_keys(user_id=user_cv.user_id)
        logger.info('saving CV to DynamoDB')
        try:
            table: Table = self._get_db_handler(self.table_name)
            item = user_cv.model_dump()
            item['pk'] = user_cv.user_id
            item['sk'] = 'CV'
            table.put_item(Item=item)
        except (ClientError, ValidationError) as exc:  # pragma: no cover
            error_msg = 'failed to save CV'
            logger.exception(error_msg, user_id=user_cv.user_id)
            raise InternalServerException(error_msg) from exc

        logger.info('CV saved successfully', user_id=user_cv.user_id)

    @tracer.capture_method(capture_response=False)
    def get_cv(self, user_id: str) -> UserCV | None:
        logger.append_keys(user_id=user_id)
        logger.info('fetching CV from DynamoDB')
        try:
            table: Table = self._get_db_handler(self.table_name)
            response = table.get_item(Key={'pk': user_id, 'sk': 'CV'})
            item = response.get('Item')
            if not item:
                return None
            return UserCV.model_validate(item)
        except (ClientError, ValidationError) as exc:  # pragma: no cover
            error_msg = 'failed to get CV'
            logger.exception(error_msg, user_id=user_id)
            raise InternalServerException(error_msg) from exc

    @staticmethod
    def _build_vpr_sort_key(version: int) -> str:
        """Construct the sort key string for VPR artifacts."""
        return f'{VPR_SORT_KEY_PREFIX}{version}'

    @tracer.capture_method(capture_response=False)
    def save_vpr(self, vpr: VPR) -> Result[None]:
        """
        Persist VPR artifacts following docs/specs/03-vpr-generator.md:14 storage contract.
        """
        logger.append_keys(application_id=vpr.application_id, user_id=vpr.user_id)
        logger.info('saving VPR artifact to DynamoDB')
        try:
            table: Table = self._get_db_handler(self.table_name)
            item = vpr.model_dump(mode='json')
            item['pk'] = vpr.application_id
            item['sk'] = self._build_vpr_sort_key(vpr.version)
            item['user_id'] = vpr.user_id
            table.put_item(Item=item)
        except (ClientError, ValidationError):
            error_msg = 'failed to save VPR'
            logger.exception(error_msg, application_id=vpr.application_id)
            return Result(success=False, error=error_msg, code=ResultCode.DYNAMODB_ERROR)

        logger.info('VPR saved successfully', application_id=vpr.application_id)
        return Result(success=True, data=None, code=ResultCode.SUCCESS)

    @tracer.capture_method(capture_response=False)
    def get_vpr(self, application_id: str, version: int | None = None) -> Result[VPR | None]:
        """
        Fetch a VPR by application and version per docs/specs/03-vpr-generator.md:14 PK/SK scheme.
        """
        if version is None:
            return self.get_latest_vpr(application_id)

        logger.append_keys(application_id=application_id, version=version)
        logger.info('fetching VPR version from DynamoDB')
        try:
            table: Table = self._get_db_handler(self.table_name)
            response = table.get_item(
                Key={'pk': application_id, 'sk': self._build_vpr_sort_key(version)},
            )
            item = response.get('Item')
            if not item:
                return Result(success=True, data=None, code=ResultCode.SUCCESS)
            vpr = VPR.model_validate(item)
            return Result(success=True, data=vpr, code=ResultCode.SUCCESS)
        except (ClientError, ValidationError):
            error_msg = 'failed to get VPR'
            logger.exception(error_msg, application_id=application_id, version=version)
            return Result(success=False, error=error_msg, code=ResultCode.DYNAMODB_ERROR)

    @tracer.capture_method(capture_response=False)
    def get_latest_vpr(self, application_id: str) -> Result[VPR | None]:
        """
        Fetch the latest VPR for an application (docs/specs/03-vpr-generator.md:14).
        """
        logger.append_keys(application_id=application_id)
        logger.info('fetching latest VPR from DynamoDB')
        try:
            table: Table = self._get_db_handler(self.table_name)
            key_condition = Key('pk').eq(application_id) & Key('sk').begins_with(VPR_SORT_KEY_PREFIX)
            items: list[dict[str, Any]] = []
            response = table.query(KeyConditionExpression=key_condition)
            items.extend(response.get('Items', []))

            while 'LastEvaluatedKey' in response:
                response = table.query(
                    KeyConditionExpression=key_condition,
                    ExclusiveStartKey=response['LastEvaluatedKey'],
                )
                items.extend(response.get('Items', []))

            if not items:
                return Result(success=True, data=None, code=ResultCode.SUCCESS)

            latest_item = max(items, key=lambda record: int(record.get('version', 0)))
            vpr = VPR.model_validate(latest_item)
            return Result(success=True, data=vpr, code=ResultCode.SUCCESS)
        except (ClientError, ValidationError):
            error_msg = 'failed to get latest VPR'
            logger.exception(error_msg, application_id=application_id)
            return Result(success=False, error=error_msg, code=ResultCode.DYNAMODB_ERROR)

    @tracer.capture_method(capture_response=False)
    def list_vprs(self, user_id: str) -> Result[list[VPR]]:
        """
        List all VPR artifacts for a user via the user_id GSI (docs/specs/03-vpr-generator.md:14).
        """
        logger.append_keys(user_id=user_id)
        logger.info('listing VPRs for user from DynamoDB')
        try:
            table: Table = self._get_db_handler(self.table_name)
            key_condition = Key('user_id').eq(user_id) & Key('sk').begins_with(VPR_SORT_KEY_PREFIX)
            items: list[dict[str, Any]] = []
            response = table.query(IndexName=USER_VPRS_INDEX, KeyConditionExpression=key_condition)
            items.extend(response.get('Items', []))

            while 'LastEvaluatedKey' in response:
                response = table.query(
                    IndexName=USER_VPRS_INDEX,
                    KeyConditionExpression=key_condition,
                    ExclusiveStartKey=response['LastEvaluatedKey'],
                )
                items.extend(response.get('Items', []))

            vprs = [VPR.model_validate(item) for item in items]
            # Sort newest first for deterministic responses
            vprs.sort(key=lambda item: item.version, reverse=True)
            return Result(success=True, data=vprs, code=ResultCode.SUCCESS)
        except (ClientError, ValidationError):
            error_msg = 'failed to list VPRs'
            logger.exception(error_msg, user_id=user_id)
            return Result(success=False, error=error_msg, code=ResultCode.DYNAMODB_ERROR)
