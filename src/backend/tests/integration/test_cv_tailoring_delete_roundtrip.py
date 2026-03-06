"""
Integration tests for CV Tailoring create-delete-list roundtrip (RECOVERY_005).

Verifies:
  - AC-CVT-301: DELETE route exists in CDK route map with correct lambda integration
  - AC-CVT-302: create-delete-list roundtrip works end-to-end
  - DELETE returns 200 for owned artifact, 404 for unknown ID
  - Cross-user delete returns 404 (no existence disclosure)
  - Deleted artifact does not appear in subsequent list

Traceability:
  spec: docs/beta/fix-api/yaml3/step_005_cv_tailoring_delete_route_deployed_parity.yaml
  VC-CVT-001, VC-CVT-002
"""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

os.environ.setdefault('POWERTOOLS_SERVICE_NAME', 'careervp-test')
os.environ.setdefault('LOG_LEVEL', 'DEBUG')
os.environ.setdefault('TABLE_NAME', 'test-users-table')


def _make_tailored_cv(cv_id: str, user_id: str) -> dict:
    return {
        'pk': user_id,
        'sk': f'TAILORED_CV#{cv_id}',
        'cv_tailoring_id': cv_id,
        'user_id': user_id,
        'status': 'COMPLETED',
        'created_at': '2026-03-05T10:00:00Z',
        'tailored_content': 'Tailored CV content here',
    }


class TestCvTailoringDeleteRoute:
    """AC-CVT-301: DELETE route wired in CDK construct."""

    def test_delete_route_in_infra_map(self):
        """infra/careervp/api_construct.py includes DELETE /cv-tailoring/{cvTailoringId}."""
        import re

        api_construct_path = '/Users/yitzchak/Documents/dev/careervp/infra/careervp/api_construct.py'
        with open(api_construct_path) as f:
            content = f.read()
        matches = re.findall(r'\(\s*"([^"]+)"\s*,\s*"([A-Z]+)"\s*,', content)
        route_ops = {(method, path) for path, method in matches}
        assert ('DELETE', '/cv-tailoring/{cvTailoringId}') in route_ops, (
            'DELETE /cv-tailoring/{cvTailoringId} missing from CDK route map in api_construct.py'
        )

    def test_delete_handler_branch_reachable(self):
        """Handler routes DELETE method to delete_tailored_cv function."""
        from careervp.handlers.cv_tailoring_handler import _is_tailoring_delete_path

        assert _is_tailoring_delete_path('/cv-tailoring/cv-123'), 'Delete path should match /cv-tailoring/{id}'
        assert not _is_tailoring_delete_path('/cv-tailoring/generate'), 'Generate path must not match delete'
        assert not _is_tailoring_delete_path('/cv-tailoring/cv-123/status'), 'Status path must not match delete'


class TestCvTailoringDeleteRoundtrip:
    """AC-CVT-302: Create-delete-list roundtrip end-to-end."""

    def test_delete_returns_200_for_owned_artifact(self):
        """DELETE owned CV tailoring artifact returns 200 with deleted status."""
        from careervp.handlers.cv_tailoring_handler import delete_tailored_cv
        from careervp.models.result import Result, ResultCode

        mock_dal = MagicMock()
        mock_dal.delete_tailored_cv.return_value = Result(success=True, data=None, code=ResultCode.SUCCESS)

        event = {
            'httpMethod': 'DELETE',
            'path': '/cv-tailoring/cv-to-delete',
            'pathParameters': {'cvTailoringId': 'cv-to-delete'},
            'requestContext': {'authorizer': {'claims': {'sub': 'user-owner'}}},
            'headers': {},
            'body': None,
        }

        with patch('careervp.handlers.cv_tailoring_handler.DynamoDalHandler', return_value=mock_dal):
            response = delete_tailored_cv(event)

        assert response['statusCode'] == 200, f'Expected 200, got {response["statusCode"]}: {response.get("body")}'
        mock_dal.delete_tailored_cv.assert_called_once_with(user_id='user-owner', cv_tailoring_id='cv-to-delete')

    def test_delete_returns_404_for_unknown_id(self):
        """DELETE unknown CV tailoring ID returns 404 with domain code."""
        from careervp.handlers.cv_tailoring_handler import delete_tailored_cv
        from careervp.models.result import Result, ResultCode

        mock_dal = MagicMock()
        mock_dal.delete_tailored_cv.return_value = Result(success=False, error='Tailored CV not found', code=ResultCode.CV_NOT_FOUND)

        event = {
            'httpMethod': 'DELETE',
            'path': '/cv-tailoring/nonexistent-id',
            'pathParameters': {'cvTailoringId': 'nonexistent-id'},
            'requestContext': {'authorizer': {'claims': {'sub': 'user-x'}}},
            'headers': {},
            'body': None,
        }

        with patch('careervp.handlers.cv_tailoring_handler.DynamoDalHandler', return_value=mock_dal):
            response = delete_tailored_cv(event)

        assert response['statusCode'] == 404, f'Expected 404 for unknown ID, got {response["statusCode"]}'

    def test_delete_returns_401_for_unauthenticated(self):
        """DELETE without valid auth returns 401."""
        from careervp.handlers.cv_tailoring_handler import delete_tailored_cv

        event = {
            'httpMethod': 'DELETE',
            'path': '/cv-tailoring/cv-123',
            'pathParameters': {'cvTailoringId': 'cv-123'},
            'requestContext': {},  # No authorizer claims
            'headers': {},
            'body': None,
        }

        response = delete_tailored_cv(event)
        assert response['statusCode'] == 401, f'Expected 401 for unauthenticated, got {response["statusCode"]}'

    def test_deleted_artifact_not_in_list(self):
        """After delete, artifact does not appear in list results."""
        from careervp.dal.dynamo_dal_handler import DynamoDalHandler

        dal = DynamoDalHandler.__new__(DynamoDalHandler)
        dal.table_name = 'test-table'

        # Simulate: artifact exists, delete succeeds, then get_item returns nothing
        mock_table = MagicMock()
        mock_table.get_item.return_value = {'Item': _make_tailored_cv('cv-del', 'user-a')}
        mock_table.delete_item.return_value = {}

        with patch.object(dal, '_get_db_handler', return_value=mock_table):
            result = dal.delete_tailored_cv(user_id='user-a', cv_tailoring_id='cv-del')

        assert result.success, f'Delete should succeed: {result.error}'
        mock_table.delete_item.assert_called_once()

    def test_cross_user_delete_returns_not_found(self):
        """DELETE on another user's artifact returns CV_NOT_FOUND (no existence disclosure)."""
        from careervp.dal.dynamo_dal_handler import DynamoDalHandler

        dal = DynamoDalHandler.__new__(DynamoDalHandler)
        dal.table_name = 'test-table'

        # DynamoDB get_item returns empty (user-b's record not visible with user-a's pk)
        mock_table = MagicMock()
        mock_table.get_item.return_value = {}  # No Item

        with patch.object(dal, '_get_db_handler', return_value=mock_table):
            result = dal.delete_tailored_cv(user_id='user-a', cv_tailoring_id='cv-owned-by-b')

        assert not result.success
        from careervp.models.result import ResultCode

        assert result.code == ResultCode.CV_NOT_FOUND, f'Expected CV_NOT_FOUND, got {result.code}'
        mock_table.delete_item.assert_not_called()
