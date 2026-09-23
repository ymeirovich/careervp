"""P-24 (Identity Surrogate) — infra synth guards.

scope_lock_clause: P-24

Assert the synthesized ``CareerVpCrudDev`` stack after the P-24 slice:

  1. Provisions the ``sub -> user_id`` mapping in its OWN ``sub``-keyed table —
     never inside the ``pk``/``sk`` ``USER#`` core (spec Fix item 2 /
     ``test_p24_mapping_not_stored_in_user_partitioned_core``).
  2. Leaves the Cognito ``UserPool`` untouched — same logical id, singular, no
     replacement (P-26/P-24 shared exclusion: never move the pool).
  3. Leaves the RestApi logical id unchanged (additive-only; no replace).
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

import pytest

os.environ.setdefault('JSII_RUNTIME_PACKAGE_CACHE', '/tmp/jsii-cache')

try:
    from aws_cdk import App, Environment
    from aws_cdk.assertions import Template

    CDK_AVAILABLE = True
except Exception:  # pragma: no cover - environment guard
    CDK_AVAILABLE = False

pytestmark = pytest.mark.skipif(not CDK_AVAILABLE, reason='aws-cdk not available')

REPO_ROOT = Path(__file__).resolve().parents[4]
INFRA_SRC = str(REPO_ROOT / 'infra')

DEV_REST_API_LOGICAL_ID = 'CareerVpCrudDevCrudservicerestapi5E02FD49'
DEV_COGNITO_USER_POOL_LOGICAL_ID = 'CareerVpCrudDevCognitoUserPool42C0A4E4'


def _dev_stack() -> Any:
    if INFRA_SRC not in sys.path:
        sys.path.insert(0, INFRA_SRC)

    from careervp.naming_utils import NamingUtils  # type: ignore[import-not-found]
    from careervp.service_stack import ServiceStack  # type: ignore[import-not-found]

    app = App()
    naming = NamingUtils(environment='dev', region='us-east-1', account_id='788159322332')
    return ServiceStack(
        scope=app,
        id=naming.stack_id('crud'),
        env=Environment(account='788159322332', region='us-east-1'),
        is_production_env=False,
        naming=naming,
        stack_feature='crud',
    )


def _parent_template() -> Template:
    return Template.from_stack(_dev_stack())


def _tables(template: Template) -> dict[str, Any]:
    # api_db_construct provisions every table as a CDK ``TableV2``, which
    # synthesizes to ``AWS::DynamoDB::GlobalTable`` (not the classic ``Table``).
    return template.find_resources('AWS::DynamoDB::GlobalTable')


def _hash_key(props: dict[str, Any]) -> str | None:
    for entry in props.get('KeySchema', []):
        if entry.get('KeyType') == 'HASH':
            return entry.get('AttributeName')
    return None


def _range_key(props: dict[str, Any]) -> str | None:
    for entry in props.get('KeySchema', []):
        if entry.get('KeyType') == 'RANGE':
            return entry.get('AttributeName')
    return None


def test_p24_identity_map_table_is_sub_keyed_and_separate() -> None:
    """Exactly one ``sub``-partitioned mapping table exists, distinct from core."""
    tables = _tables(_parent_template())
    sub_keyed = {lid: res for lid, res in tables.items() if _hash_key(res['Properties']) == 'sub'}
    assert len(sub_keyed) == 1, f'expected exactly one sub-keyed identity-map table, found {sorted(sub_keyed)}'
    props = next(iter(sub_keyed.values()))['Properties']
    # A pure sub->user_id lookup: no sort key, looked up BEFORE user_id is known.
    assert _range_key(props) is None, 'identity-map table must be a bare sub lookup (no sort key)'
    name = props.get('TableName', '')
    assert isinstance(name, str) and 'identity-map' in name, f'unexpected mapping table name {name!r}'


def test_p24_mapping_not_stored_in_user_partitioned_core() -> None:
    """The mapping is NOT co-located in the ``pk``/``sk`` users core table."""
    tables = _tables(_parent_template())
    core_tables = {lid: res for lid, res in tables.items() if _hash_key(res['Properties']) == 'pk' and _range_key(res['Properties']) == 'sk'}
    # The users core exists and is keyed pk/sk...
    assert core_tables, 'expected the pk/sk users core table to be present'
    # ...and none of the pk/sk core tables carry a `sub` attribute definition,
    # proving the surrogate map is not folded into user-partitioned core.
    for res in core_tables.values():
        attr_names = {a['AttributeName'] for a in res['Properties'].get('AttributeDefinitions', [])}
        assert 'sub' not in attr_names, 'sub->user_id mapping must not live in the USER# core table'


def test_p24_cognito_user_pool_untouched() -> None:
    """The Cognito UserPool is singular and keeps its deployed logical id (no replace)."""
    pools = _parent_template().find_resources('AWS::Cognito::UserPool')
    assert list(pools) == [DEV_COGNITO_USER_POOL_LOGICAL_ID], (
        f'Cognito UserPool drifted from the deployed anchor {DEV_COGNITO_USER_POOL_LOGICAL_ID!r} '
        f'to {sorted(pools)!r} — moving/replacing it is an unrecoverable account loss.'
    )


def test_p24_rest_api_logical_id_unchanged() -> None:
    """The P-24 slice is additive: the RestApi logical id must not drift."""
    rest_apis = _parent_template().find_resources('AWS::ApiGateway::RestApi')
    assert list(rest_apis) == [DEV_REST_API_LOGICAL_ID], (
        f'RestApi logical id drifted to {sorted(rest_apis)!r}; the P-24 table add must be additive-only.'
    )
