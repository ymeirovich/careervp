import boto3
from botocore.exceptions import ClientError
from cachetools import TTLCache, cached
from mypy_boto3_dynamodb import DynamoDBServiceResource
from mypy_boto3_dynamodb.service_resource import Table
from pydantic import ValidationError

from careervp.dal.db_handler import DalHandler
from careervp.handlers.utils.observability import logger, tracer
from careervp.models.cv import UserCV
from careervp.models.exceptions import InternalServerException


class DynamoDalHandler(DalHandler):
    def __init__(self, table_name: str):
        self.table_name = table_name

    @cached(cache=TTLCache(maxsize=1, ttl=300))
    def _get_db_handler(self, table_name: str) -> Table:
        logger.info('opening connection to dynamodb table', table_name=table_name)
        dynamodb: DynamoDBServiceResource = boto3.resource('dynamodb')
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
