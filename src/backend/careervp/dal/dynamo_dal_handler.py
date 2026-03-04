from datetime import datetime, timedelta, timezone
from typing import Any

import boto3  # type: ignore[import-untyped]
from boto3.dynamodb.conditions import Key  # type: ignore[import-untyped]
from botocore.exceptions import ClientError  # type: ignore[import-untyped]
from mypy_boto3_dynamodb import DynamoDBServiceResource
from pydantic import ValidationError

from careervp.dal.db_handler import DalHandler
from careervp.handlers.utils.observability import logger, tracer
from careervp.models.cv import UserCV
from careervp.models.cv_tailoring_models import TailoredCV
from careervp.models.exceptions import InternalServerException, InvalidVersionError
from careervp.models.job import GapResponse
from careervp.models.result import Result, ResultCode
from careervp.models.vpr import VPR

VPR_SORT_KEY_PREFIX = 'ARTIFACT#VPR#v'
USER_VPRS_INDEX = 'user_id-index'
# Storage per docs/specs/03-vpr-generator.md:14 uses PK=applicationId with ARTIFACT#VPR#v{version} SK.

TAILORED_CV_SORT_KEY_PREFIX = 'ARTIFACT#CV_TAILORED#'
COVER_LETTER_SORT_KEY_PREFIX = 'ARTIFACT#COVER_LETTER#'
GAP_ANALYSIS_SORT_KEY_PREFIX = 'ARTIFACT#GAP_ANALYSIS#'
GAP_RESPONSES_SORT_KEY_PREFIX = 'ARTIFACT#GAP_RESPONSES#'


class DynamoDalHandler(DalHandler):
    def __init__(self, table_name: str):
        self.table_name = table_name

    @staticmethod
    def _client_error_details(exc: Exception) -> tuple[str, str]:
        if isinstance(exc, ClientError):
            error = exc.response.get('Error', {})
            return str(error.get('Code', 'ClientError')), str(error.get('Message', str(exc)))
        return exc.__class__.__name__, str(exc)

    def _map_dal_error_code(self, exc: Exception, error_message: str) -> str:
        if isinstance(exc, ValidationError):
            return ResultCode.VALIDATION
        if isinstance(exc, ClientError):
            error_code, _ = self._client_error_details(exc)
            if error_code == 'ValidationException':
                if 'schema' in error_message.lower() or 'key element' in error_message.lower():
                    return ResultCode.TABLE_SCHEMA_MISMATCH
                return ResultCode.DYNAMODB_VALIDATION_EXCEPTION
        return ResultCode.DYNAMODB_ERROR

    def _dal_failure_result(
        self,
        *,
        operation: str,
        exc: Exception,
        key_names: list[str],
    ) -> Result[Any]:
        error_code, error_message = self._client_error_details(exc)
        mapped_code = self._map_dal_error_code(exc, error_message)
        logger.error(
            'DynamoDB DAL operation failed',
            table_name=self.table_name,
            operation=operation,
            key_names=key_names,
            error_code=error_code,
            error_message=error_message,
            exc_info=True,
        )
        return Result(
            success=False,
            error=(f'table_name={self.table_name} operation={operation} error_code={error_code} message={error_message}'),
            code=mapped_code,
        )

    def _get_db_handler(self, table_name: str) -> Any:
        logger.info('opening connection to dynamodb table', table_name=table_name)
        session = boto3.session.Session()
        dynamodb: DynamoDBServiceResource = session.resource('dynamodb')
        return dynamodb.Table(table_name)

    @tracer.capture_method(capture_response=False)
    def save_cv(self, user_cv: UserCV) -> None:
        logger.append_keys(user_id=user_cv.user_id)
        logger.info('saving CV to DynamoDB')
        try:
            table = self._get_db_handler(self.table_name)
            # Exclude nulls to avoid DynamoDB GSI key-type validation errors (e.g. email-index expects S, not NULL).
            item = user_cv.model_dump(exclude_none=True)
            item['pk'] = user_cv.user_id
            # Use CV#{cv_id} to support multiple CVs per user
            item['sk'] = f'CV#{user_cv.cv_id}'
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
            table = self._get_db_handler(self.table_name)
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

    @staticmethod
    def _ttl_timestamp(ttl_days: int = 90) -> int:
        now = datetime.now(timezone.utc)
        return int((now + timedelta(days=ttl_days)).timestamp())

    @staticmethod
    def _build_tailored_cv_sort_key(cv_id: str, job_id: str, version: int = 1) -> str:
        return f'{TAILORED_CV_SORT_KEY_PREFIX}{cv_id}#{job_id}#v{version}'

    @staticmethod
    def _build_cover_letter_sort_key(cv_id: str, job_id: str, version: int = 1) -> str:
        return f'{COVER_LETTER_SORT_KEY_PREFIX}{cv_id}#{job_id}#v{version}'

    @staticmethod
    def _build_gap_analysis_sort_key(cv_id: str, job_id: str) -> str:
        return f'{GAP_ANALYSIS_SORT_KEY_PREFIX}{cv_id}#{job_id}'

    @staticmethod
    def _build_gap_responses_sort_key(version: int = 1) -> str:
        return f'{GAP_RESPONSES_SORT_KEY_PREFIX}v{version}'

    @staticmethod
    def _parse_version_from_sk(sk: str) -> int:
        if '#v' not in sk:
            return 0
        try:
            return int(sk.split('#v')[-1])
        except ValueError:
            return 0

    @tracer.capture_method(capture_response=False)
    def save_vpr(self, vpr: VPR) -> Result[None]:
        """
        Persist VPR artifacts following docs/specs/03-vpr-generator.md:14 storage contract.
        """
        logger.append_keys(application_id=vpr.application_id, user_id=vpr.user_id)
        logger.info('saving VPR artifact to DynamoDB')
        try:
            table = self._get_db_handler(self.table_name)
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
            table = self._get_db_handler(self.table_name)
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
            table = self._get_db_handler(self.table_name)
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

            def _parse_record_version(record: dict[str, Any]) -> int:
                try:
                    version = int(record.get('version', 0))
                except (ValueError, TypeError) as e:
                    logger.warning('Invalid version: %s', record.get('version'))
                    raise InvalidVersionError(f'Invalid version: {e}') from e
                return version

            latest_item = max(items, key=_parse_record_version)
            vpr = VPR.model_validate(latest_item)
            return Result(success=True, data=vpr, code=ResultCode.SUCCESS)
        except (ClientError, ValidationError, InvalidVersionError):
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
            table = self._get_db_handler(self.table_name)
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

    @tracer.capture_method(capture_response=False)
    def save_tailored_cv(
        self,
        tailored_cv: TailoredCV,
        job_id: str | None = None,
        version: int = 1,
        ttl_days: int = 90,
    ) -> Result[None]:
        logger.append_keys(user_id=tailored_cv.user_id, cv_id=tailored_cv.cv_id)
        logger.info('saving tailored CV artifact to DynamoDB')
        resolved_job_id = job_id or tailored_cv.job_description_hash or 'unknown'
        resolved_cv_id = tailored_cv.cv_id or 'unknown'
        try:
            table = self._get_db_handler(self.table_name)
            item = {
                'pk': tailored_cv.user_id,
                'sk': self._build_tailored_cv_sort_key(resolved_cv_id, resolved_job_id, version),
                'artifact_type': 'cv_tailored',
                'user_id': tailored_cv.user_id,
                'cv_id': tailored_cv.cv_id,
                'job_id': resolved_job_id,
                'version': version,
                'tailored_cv': tailored_cv.model_dump(mode='json'),
                'created_at': datetime.now(timezone.utc).isoformat(),
                'updated_at': datetime.now(timezone.utc).isoformat(),
                'ttl': self._ttl_timestamp(ttl_days),
            }
            table.put_item(Item=item)
            return Result(success=True, data=None, code=ResultCode.SUCCESS)
        except (ClientError, ValidationError) as exc:
            error_msg = 'failed to save tailored CV'
            logger.exception(error_msg, user_id=tailored_cv.user_id)
            return Result(success=False, error=str(exc), code=ResultCode.DYNAMODB_ERROR)

    @tracer.capture_method(capture_response=False)
    def get_tailored_cv(
        self,
        user_id: str,
        cv_id: str,
        job_id: str,
        version: int | None = None,
    ) -> Result[TailoredCV | None]:
        logger.append_keys(user_id=user_id, cv_id=cv_id, job_id=job_id)
        logger.info('fetching tailored CV from DynamoDB')
        try:
            table = self._get_db_handler(self.table_name)
            if version is None:
                prefix = self._build_tailored_cv_sort_key(cv_id, job_id, version=0).replace('#v0', '#v')
                key_condition = Key('pk').eq(user_id) & Key('sk').begins_with(prefix)
                response = table.query(KeyConditionExpression=key_condition)
                items = response.get('Items', [])
                if not items:
                    return Result(success=True, data=None, code=ResultCode.SUCCESS)
                latest_item = max(items, key=lambda item: self._parse_version_from_sk(item.get('sk', '')))
                payload = latest_item.get('tailored_cv') or latest_item
            else:
                response = table.get_item(
                    Key={
                        'pk': user_id,
                        'sk': self._build_tailored_cv_sort_key(cv_id, job_id, version),
                    }
                )
                item = response.get('Item')
                if not item:
                    return Result(success=True, data=None, code=ResultCode.SUCCESS)
                payload = item.get('tailored_cv') or item
            return Result(success=True, data=TailoredCV.model_validate(payload), code=ResultCode.SUCCESS)
        except (ClientError, ValidationError) as exc:
            error_msg = 'failed to get tailored CV'
            logger.exception(error_msg, user_id=user_id)
            return Result(success=False, error=str(exc), code=ResultCode.DYNAMODB_ERROR)

    @tracer.capture_method(capture_response=False)
    def list_tailored_cvs(self, user_id: str) -> Result[list[dict[str, Any]]]:
        logger.append_keys(user_id=user_id)
        logger.info('listing tailored CVs for user from DynamoDB')
        try:
            table = self._get_db_handler(self.table_name)
            key_condition = Key('pk').eq(user_id) & Key('sk').begins_with(TAILORED_CV_SORT_KEY_PREFIX)
            items: list[dict[str, Any]] = []
            response = table.query(KeyConditionExpression=key_condition)
            items.extend(response.get('Items', []))
            while 'LastEvaluatedKey' in response:
                response = table.query(
                    KeyConditionExpression=key_condition,
                    ExclusiveStartKey=response['LastEvaluatedKey'],
                )
                items.extend(response.get('Items', []))
            # Return raw items as dicts for backward compatibility
            return Result(success=True, data=items, code=ResultCode.SUCCESS)
        except ClientError as exc:
            error_msg = 'failed to list tailored CVs'
            logger.exception(error_msg, user_id=user_id)
            return Result(success=False, error=str(exc), code=ResultCode.DYNAMODB_ERROR)

    @tracer.capture_method(capture_response=False)
    def save_cover_letter(
        self,
        cover_letter: dict[str, Any],
        user_id: str,
        cv_id: str,
        job_id: str,
        version: int = 1,
        ttl_days: int = 90,
    ) -> Result[None]:
        logger.append_keys(user_id=user_id, cv_id=cv_id, job_id=job_id)
        logger.info('saving cover letter artifact to DynamoDB')
        try:
            table = self._get_db_handler(self.table_name)
            item = {
                'pk': user_id,
                'sk': self._build_cover_letter_sort_key(cv_id, job_id, version),
                'artifact_type': 'cover_letter',
                'user_id': user_id,
                'cv_id': cv_id,
                'job_id': job_id,
                'version': version,
                'cover_letter': cover_letter,
                'created_at': datetime.now(timezone.utc).isoformat(),
                'updated_at': datetime.now(timezone.utc).isoformat(),
                'ttl': self._ttl_timestamp(ttl_days),
            }
            table.put_item(Item=item)
            return Result(success=True, data=None, code=ResultCode.SUCCESS)
        except (ClientError, ValidationError) as exc:
            error_msg = 'failed to save cover letter'
            logger.exception(error_msg, user_id=user_id)
            return Result(success=False, error=str(exc), code=ResultCode.DYNAMODB_ERROR)

    @tracer.capture_method(capture_response=False)
    def get_cover_letter(
        self,
        user_id: str,
        cv_id: str,
        job_id: str,
        version: int | None = None,
    ) -> Result[dict[str, Any] | None]:
        logger.append_keys(user_id=user_id, cv_id=cv_id, job_id=job_id)
        logger.info('fetching cover letter from DynamoDB')
        try:
            table = self._get_db_handler(self.table_name)
            if version is None:
                prefix = self._build_cover_letter_sort_key(cv_id, job_id, version=0).replace('#v0', '#v')
                key_condition = Key('pk').eq(user_id) & Key('sk').begins_with(prefix)
                response = table.query(KeyConditionExpression=key_condition)
                items = response.get('Items', [])
                if not items:
                    return Result(success=True, data=None, code=ResultCode.SUCCESS)
                latest_item = max(items, key=lambda item: self._parse_version_from_sk(item.get('sk', '')))
                payload = latest_item.get('cover_letter') or latest_item
            else:
                response = table.get_item(
                    Key={
                        'pk': user_id,
                        'sk': self._build_cover_letter_sort_key(cv_id, job_id, version),
                    }
                )
                item = response.get('Item')
                if not item:
                    return Result(success=True, data=None, code=ResultCode.SUCCESS)
                payload = item.get('cover_letter') or item
            return Result(success=True, data=payload, code=ResultCode.SUCCESS)
        except (ClientError, ValidationError) as exc:
            error_msg = 'failed to get cover letter'
            logger.exception(error_msg, user_id=user_id)
            return Result(success=False, error=str(exc), code=ResultCode.DYNAMODB_ERROR)

    @tracer.capture_method(capture_response=False)
    def list_cover_letters(self, user_id: str) -> Result[list[dict[str, Any]]]:
        logger.append_keys(user_id=user_id)
        logger.info('listing cover letters for user from DynamoDB')
        try:
            table = self._get_db_handler(self.table_name)
            key_condition = Key('pk').eq(user_id) & Key('sk').begins_with(COVER_LETTER_SORT_KEY_PREFIX)
            items: list[dict[str, Any]] = []
            response = table.query(KeyConditionExpression=key_condition)
            items.extend(response.get('Items', []))
            while 'LastEvaluatedKey' in response:
                response = table.query(
                    KeyConditionExpression=key_condition,
                    ExclusiveStartKey=response['LastEvaluatedKey'],
                )
                items.extend(response.get('Items', []))
            results = items
            return Result(success=True, data=results, code=ResultCode.SUCCESS)
        except (ClientError, ValidationError) as exc:
            error_msg = 'failed to list cover letters'
            logger.exception(error_msg, user_id=user_id)
            return Result(success=False, error=str(exc), code=ResultCode.DYNAMODB_ERROR)

    @tracer.capture_method(capture_response=False)
    def list_gap_questions_by_prefix(
        self,
        user_id: str,
        job_id: str | None = None,
    ) -> Result[list[dict[str, Any]] | None]:
        """List gap questions by querying with sort key prefix, optionally filtering by job_id."""
        logger.append_keys(user_id=user_id)
        logger.info('listing gap analysis questions from DynamoDB')
        try:
            table = self._get_db_handler(self.table_name)
            key_condition = Key('pk').eq(user_id) & Key('sk').begins_with(GAP_ANALYSIS_SORT_KEY_PREFIX)
            response = table.query(KeyConditionExpression=key_condition)
            items = list(response.get('Items', []))
            while 'LastEvaluatedKey' in response:
                response = table.query(
                    KeyConditionExpression=key_condition,
                    ExclusiveStartKey=response['LastEvaluatedKey'],
                )
                items.extend(response.get('Items', []))
            if job_id:
                normalized_job_id = str(job_id).strip().casefold()
                if normalized_job_id:
                    items = [
                        item
                        for item in items
                        if str(item.get('job_id', '')).strip().casefold() == normalized_job_id
                        or str(item.get('sk', '')).strip().casefold().endswith(f'#{normalized_job_id}')
                    ]
            return Result(success=True, data=items if items else None, code=ResultCode.SUCCESS)
        except (ClientError, ValidationError) as exc:
            error_msg = 'failed to list gap questions'
            logger.exception(error_msg, user_id=user_id)
            return Result(success=False, error=str(exc), code=ResultCode.DYNAMODB_ERROR)

    @tracer.capture_method(capture_response=False)
    def delete_tailored_cv(self, user_id: str, cv_tailoring_id: str) -> Result[None]:
        logger.append_keys(user_id=user_id, cv_tailoring_id=cv_tailoring_id)
        logger.info('deleting tailored CV artifact from DynamoDB')
        if not cv_tailoring_id:
            return Result(success=False, error='cv_tailoring_id is required', code=ResultCode.MISSING_REQUIRED_FIELD)

        normalized_id = str(cv_tailoring_id).strip()
        sort_keys = [normalized_id]
        prefixed = f'{TAILORED_CV_SORT_KEY_PREFIX}{normalized_id}'
        if normalized_id.startswith(TAILORED_CV_SORT_KEY_PREFIX):
            sort_keys.append(normalized_id.removeprefix(TAILORED_CV_SORT_KEY_PREFIX))
        else:
            sort_keys.append(prefixed)

        try:
            table = self._get_db_handler(self.table_name)
            for sk in dict.fromkeys(sort_keys):
                response = table.get_item(Key={'pk': user_id, 'sk': sk})
                if response.get('Item'):
                    table.delete_item(Key={'pk': user_id, 'sk': sk})
                    return Result(success=True, data=None, code=ResultCode.SUCCESS)
            return Result(success=False, error='Tailored CV not found', code=ResultCode.CV_NOT_FOUND)
        except (ClientError, ValidationError) as exc:
            error_msg = 'failed to delete tailored CV'
            logger.exception(error_msg, user_id=user_id, cv_tailoring_id=cv_tailoring_id)
            return Result(success=False, error=str(exc), code=ResultCode.DYNAMODB_ERROR)

    @tracer.capture_method(capture_response=False)
    def save_gap_questions(
        self,
        user_id: str,
        cv_id: str,
        job_id: str,
        questions: list[dict[str, Any]],
        ttl_days: int = 90,
    ) -> Result[None]:
        logger.append_keys(user_id=user_id, cv_id=cv_id, job_id=job_id)
        logger.info('saving gap analysis questions to DynamoDB')
        try:
            table = self._get_db_handler(self.table_name)
            item = {
                'pk': user_id,
                'sk': self._build_gap_analysis_sort_key(cv_id, job_id),
                'artifact_type': 'gap_analysis',
                'user_id': user_id,
                'cv_id': cv_id,
                'job_id': job_id,
                'questions': questions,
                'created_at': datetime.now(timezone.utc).isoformat(),
                'updated_at': datetime.now(timezone.utc).isoformat(),
                'ttl': self._ttl_timestamp(ttl_days),
            }
            table.put_item(Item=item)
            return Result(success=True, data=None, code=ResultCode.SUCCESS)
        except (ClientError, ValidationError) as exc:
            return self._dal_failure_result(
                operation='save_gap_questions',
                exc=exc,
                key_names=['pk', 'sk'],
            )

    @tracer.capture_method(capture_response=False)
    def get_gap_questions(
        self,
        user_id: str,
        cv_id: str,
        job_id: str,
    ) -> Result[list[dict[str, Any]] | None]:
        logger.append_keys(user_id=user_id, cv_id=cv_id, job_id=job_id)
        logger.info('fetching gap analysis questions from DynamoDB')
        try:
            table = self._get_db_handler(self.table_name)
            response = table.get_item(
                Key={
                    'pk': user_id,
                    'sk': self._build_gap_analysis_sort_key(cv_id, job_id),
                }
            )
            item = response.get('Item')
            if not item:
                return Result(success=True, data=None, code=ResultCode.SUCCESS)
            return Result(success=True, data=item.get('questions') or [], code=ResultCode.SUCCESS)
        except (ClientError, ValidationError) as exc:
            error_msg = 'failed to get gap questions'
            logger.exception(error_msg, user_id=user_id)
            return Result(success=False, error=str(exc), code=ResultCode.DYNAMODB_ERROR)

    @tracer.capture_method(capture_response=False)
    def save_gap_responses(
        self,
        user_id: str,
        responses: list[GapResponse],
        version: int = 1,
        ttl_days: int = 90,
    ) -> Result[None]:
        logger.append_keys(user_id=user_id)
        logger.info('saving gap responses to DynamoDB')
        try:
            table = self._get_db_handler(self.table_name)
            item = {
                'userId': user_id,
                'questionId': self._build_gap_responses_sort_key(version),
                'artifact_type': 'gap_responses',
                'user_id': user_id,
                'version': version,
                'responses': [response.model_dump(mode='json') for response in responses],
                'created_at': datetime.now(timezone.utc).isoformat(),
                'updated_at': datetime.now(timezone.utc).isoformat(),
                'ttl': self._ttl_timestamp(ttl_days),
            }
            table.put_item(Item=item)
            return Result(success=True, data=None, code=ResultCode.GAP_RESPONSES_SAVED)
        except (ClientError, ValidationError) as exc:
            return self._dal_failure_result(
                operation='save_gap_responses',
                exc=exc,
                key_names=['userId', 'questionId'],
            )

    @tracer.capture_method(capture_response=False)
    def save_gap_responses_raw(
        self,
        user_id: str,
        job_id: str,
        responses: list[dict[str, Any]],
        version: int = 1,
        ttl_days: int = 90,
    ) -> Result[None]:
        """Save gap responses from raw dict format (for handler compatibility)."""
        logger.append_keys(user_id=user_id)
        logger.info('saving gap responses (raw) to DynamoDB')
        try:
            table = self._get_db_handler(self.table_name)
            item = {
                'userId': user_id,
                'questionId': self._build_gap_responses_sort_key(version),
                'artifact_type': 'gap_responses',
                'user_id': user_id,
                'job_id': job_id,
                'version': version,
                'responses': responses,
                'created_at': datetime.now(timezone.utc).isoformat(),
                'updated_at': datetime.now(timezone.utc).isoformat(),
                'ttl': self._ttl_timestamp(ttl_days),
            }
            table.put_item(Item=item)
            return Result(success=True, data=None, code=ResultCode.GAP_RESPONSES_SAVED)
        except (ClientError, ValidationError) as exc:
            return self._dal_failure_result(
                operation='save_gap_responses_raw',
                exc=exc,
                key_names=['userId', 'questionId'],
            )

    @tracer.capture_method(capture_response=False)
    def get_gap_responses(
        self,
        user_id: str,
        version: int | None = None,
    ) -> Result[list[GapResponse]]:
        logger.append_keys(user_id=user_id)
        logger.info('fetching gap responses from DynamoDB')
        try:
            table = self._get_db_handler(self.table_name)
            if version is None:
                prefix = self._build_gap_responses_sort_key(version=0).replace('#v0', '#v')
                key_condition = Key('userId').eq(user_id) & Key('questionId').begins_with(prefix)
                response = table.query(KeyConditionExpression=key_condition)
                items = response.get('Items', [])
                if not items:
                    return Result(success=True, data=None, code=ResultCode.SUCCESS)
                latest_item = max(items, key=lambda item: self._parse_version_from_sk(item.get('questionId', '')))
                payload = latest_item.get('responses') or []
            else:
                response = table.get_item(Key={'userId': user_id, 'questionId': self._build_gap_responses_sort_key(version)})
                item = response.get('Item')
                payload = item.get('responses') if item else []
            parsed = [GapResponse.model_validate(item) for item in payload]
            return Result(success=True, data=parsed, code=ResultCode.SUCCESS)
        except (ClientError, ValidationError) as exc:
            return self._dal_failure_result(
                operation='get_gap_responses',
                exc=exc,
                key_names=['userId', 'questionId'],
            )
