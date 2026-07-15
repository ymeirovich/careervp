"""P-24 (Identity Surrogate) — TDD-first unit tests.

scope_lock_clause: P-24

RED tests for the conservative internal-``user_id`` surrogate + ``sub -> user_id``
resolver decided in O-4 (RESOLVED 2026-07-09):

    auto-link a social/second-method ``sub`` to an EXISTING internal ``user_id``
    ONLY when ``email_verified=true`` AND the email matches AND the asserting IdP
    is on the allow-list; else require step-up ("sign in with your original
    method to link"); email conflicts resolve to the earliest-created
    ``user_id``; all links are audit-logged.

These cover the three surfaces the P-24 IMPLEMENT step scopes:

  1. ``sub -> user_id`` resolution (JIT conditional-put create, loser re-reads).
  2. link-by-verified-email behavior (allow-list + verified-email safeguards,
     earliest-created conflict tiebreak).
  3. authorizer wiring (the shared resolution locus emits the internal surrogate
     as identity context; step-up is a deny; unconfigured => legacy passthrough).

The mapping lives in its OWN table (never the ``USER#`` core), exercised here
against a moto-backed ``sub``-keyed table.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import Mock

import boto3
import pytest
from moto import mock_aws

from careervp.dal.identity_map_repository import (
    IDENTITY_MAP_TABLE_ENV,
    ExistingUser,
    IdentityMapRepository,
    UsersDirectory,
)
from careervp.handlers import api_gateway_authorizer
from careervp.logic.identity_resolver import (
    TRUSTED_IDPS,
    IdentityResolver,
    LinkDecision,
    ResolvedIdentity,
)

IDENTITY_MAP_TABLE = 'test-identity-map-table'
USERS_TABLE = 'test-users-table'


# --------------------------------------------------------------------------- #
# Fixtures — moto-backed sub-keyed mapping table + users email-index directory.
# --------------------------------------------------------------------------- #
@pytest.fixture(autouse=True)
def _reset_authorizer_globals() -> Any:
    """Keep the authorizer's module singletons isolated between tests."""
    api_gateway_authorizer._auth_service = None
    api_gateway_authorizer._identity_resolver = None
    yield
    api_gateway_authorizer._auth_service = None
    api_gateway_authorizer._identity_resolver = None


@pytest.fixture
def moto_context() -> Any:
    with mock_aws():
        yield


@pytest.fixture
def dynamodb(moto_context: None) -> Any:
    _ = moto_context
    return boto3.resource('dynamodb', region_name='us-east-1')


@pytest.fixture
def identity_map_table(dynamodb: Any, monkeypatch: pytest.MonkeyPatch) -> Any:
    monkeypatch.setenv(IDENTITY_MAP_TABLE_ENV, IDENTITY_MAP_TABLE)
    table = dynamodb.create_table(
        TableName=IDENTITY_MAP_TABLE,
        KeySchema=[{'AttributeName': 'sub', 'KeyType': 'HASH'}],
        AttributeDefinitions=[{'AttributeName': 'sub', 'AttributeType': 'S'}],
        BillingMode='PAY_PER_REQUEST',
    )
    table.wait_until_exists()
    return table


@pytest.fixture
def users_table(dynamodb: Any, monkeypatch: pytest.MonkeyPatch) -> Any:
    monkeypatch.setenv('USERS_TABLE_NAME', USERS_TABLE)
    table = dynamodb.create_table(
        TableName=USERS_TABLE,
        KeySchema=[
            {'AttributeName': 'pk', 'KeyType': 'HASH'},
            {'AttributeName': 'sk', 'KeyType': 'RANGE'},
        ],
        AttributeDefinitions=[
            {'AttributeName': 'pk', 'AttributeType': 'S'},
            {'AttributeName': 'sk', 'AttributeType': 'S'},
            {'AttributeName': 'email', 'AttributeType': 'S'},
        ],
        GlobalSecondaryIndexes=[
            {
                'IndexName': 'email-index',
                'KeySchema': [{'AttributeName': 'email', 'KeyType': 'HASH'}],
                'Projection': {'ProjectionType': 'ALL'},
            }
        ],
        BillingMode='PAY_PER_REQUEST',
    )
    table.wait_until_exists()
    return table


def _seed_user(table: Any, *, user_id: str, email: str, created_at: str) -> None:
    table.put_item(
        Item={
            'pk': f'USER#{user_id}',
            'sk': 'PROFILE',
            'user_id': user_id,
            'email': email,
            'created_at': created_at,
        }
    )


def _resolver(
    identity_map: IdentityMapRepository,
    *,
    owners: dict[str, list[ExistingUser]] | None = None,
    user_id_factory: Any = None,
) -> IdentityResolver:
    lookup = owners or {}
    return IdentityResolver(
        identity_map=identity_map,
        email_lookup=lambda email: list(lookup.get(email, [])),
        user_id_factory=user_id_factory or (lambda: 'minted-user-id'),
    )


# --------------------------------------------------------------------------- #
# 1. sub -> user_id resolution.
# --------------------------------------------------------------------------- #
def test_p24_new_sub_mints_and_persists_surrogate_user_id(identity_map_table: Any, dynamodb: Any) -> None:
    """An unknown sub with no existing email owner mints a fresh internal user_id."""
    repo = IdentityMapRepository(table_name=IDENTITY_MAP_TABLE, dynamodb_resource=dynamodb)
    resolver = _resolver(repo, user_id_factory=lambda: 'fresh-uid-1')

    result = resolver.resolve({'sub': 'cognito-sub-new'})

    assert result == ResolvedIdentity(user_id='fresh-uid-1', decision=LinkDecision.CREATED_NEW)
    # Persisted: a second resolution returns the same surrogate (idempotent).
    assert repo.get_user_id('cognito-sub-new') == 'fresh-uid-1'


def test_p24_known_sub_returns_existing_mapping_idempotently(identity_map_table: Any, dynamodb: Any) -> None:
    """A sub already in the map resolves to its stored user_id every time."""
    repo = IdentityMapRepository(table_name=IDENTITY_MAP_TABLE, dynamodb_resource=dynamodb)
    repo.link('cognito-sub-known', 'existing-uid-9')
    resolver = _resolver(repo)

    first = resolver.resolve({'sub': 'cognito-sub-known'})
    second = resolver.resolve({'sub': 'cognito-sub-known'})

    assert first.user_id == 'existing-uid-9'
    assert first.decision is LinkDecision.EXISTING_MAPPING
    assert second == first


def test_p24_identity_surrogate_jit_conditional_put_loser_rereads(identity_map_table: Any, dynamodb: Any) -> None:
    """Concurrent first-writes for one sub yield exactly one user_id; loser re-reads.

    The conditional put ``attribute_not_exists(sub)`` lets the winner create the
    mapping; the loser's conditional fails, it re-reads, and returns the winner's
    user_id — never a second tenant for one human.
    """
    repo = IdentityMapRepository(table_name=IDENTITY_MAP_TABLE, dynamodb_resource=dynamodb)

    winner = repo.link('race-sub', 'uid-winner')
    loser = repo.link('race-sub', 'uid-loser')

    assert winner == 'uid-winner'
    assert loser == 'uid-winner'
    assert repo.get_user_id('race-sub') == 'uid-winner'


def test_p24_mapping_repo_does_not_overwrite_existing_sub(identity_map_table: Any, dynamodb: Any) -> None:
    """The conditional put never clobbers an existing sub->user_id row."""
    repo = IdentityMapRepository(table_name=IDENTITY_MAP_TABLE, dynamodb_resource=dynamodb)
    repo.link('sub-a', 'uid-first')
    repo.link('sub-a', 'uid-second')
    assert repo.get_user_id('sub-a') == 'uid-first'


# --------------------------------------------------------------------------- #
# 2. link-by-verified-email behavior (O-4).
# --------------------------------------------------------------------------- #
def test_p24_links_sub_to_existing_user_on_verified_trusted_email(identity_map_table: Any, dynamodb: Any) -> None:
    """Verified email + allow-listed IdP + single owner => auto-link to that user."""
    repo = IdentityMapRepository(table_name=IDENTITY_MAP_TABLE, dynamodb_resource=dynamodb)
    owner = ExistingUser(user_id='owner-uid', created_at='2025-01-01T00:00:00+00:00')
    resolver = _resolver(repo, owners={'user@example.com': [owner]})

    result = resolver.resolve({'sub': 'cognito-sub-x', 'email': 'user@example.com', 'email_verified': True})

    assert result == ResolvedIdentity(user_id='owner-uid', decision=LinkDecision.LINKED_VERIFIED_EMAIL)
    assert repo.get_user_id('cognito-sub-x') == 'owner-uid'


def test_p24_unverified_email_requires_step_up(identity_map_table: Any, dynamodb: Any) -> None:
    """An unverified email must not auto-link — step-up required, no mapping written."""
    repo = IdentityMapRepository(table_name=IDENTITY_MAP_TABLE, dynamodb_resource=dynamodb)
    owner = ExistingUser(user_id='owner-uid', created_at='2025-01-01T00:00:00+00:00')
    resolver = _resolver(repo, owners={'user@example.com': [owner]})

    result = resolver.resolve({'sub': 'attacker-sub', 'email': 'user@example.com', 'email_verified': False})

    assert result.decision is LinkDecision.STEP_UP_REQUIRED
    assert result.user_id is None
    assert repo.get_user_id('attacker-sub') is None


def test_p24_untrusted_idp_blocks_takeover_even_if_email_verified(identity_map_table: Any, dynamodb: Any) -> None:
    """A loosely-asserting IdP off the allow-list cannot auto-link (takeover guard).

    Adversarial vector: an IdP that asserts ``email_verified=true`` for an email
    it does not control. The allow-list is the defense — off-list => step-up.
    """
    repo = IdentityMapRepository(table_name=IDENTITY_MAP_TABLE, dynamodb_resource=dynamodb)
    owner = ExistingUser(user_id='victim-uid', created_at='2025-01-01T00:00:00+00:00')
    resolver = _resolver(repo, owners={'victim@example.com': [owner]})

    result = resolver.resolve(
        {
            'sub': 'attacker-sub',
            'email': 'victim@example.com',
            'email_verified': True,
            'identities': [{'providerName': 'LooseIdP'}],
        }
    )

    assert result.decision is LinkDecision.STEP_UP_REQUIRED
    assert result.user_id is None
    assert 'LooseIdP'.lower() not in TRUSTED_IDPS


def test_p24_earliest_created_preemption_requires_step_up(identity_map_table: Any, dynamodb: Any) -> None:
    """An email owned by >1 account (preemption/ambiguity) cannot be silently claimed."""
    repo = IdentityMapRepository(table_name=IDENTITY_MAP_TABLE, dynamodb_resource=dynamodb)
    attacker = ExistingUser(user_id='attacker-uid', created_at='2025-01-01T00:00:00+00:00')
    victim = ExistingUser(user_id='victim-uid', created_at='2025-06-01T00:00:00+00:00')
    resolver = _resolver(repo, owners={'shared@example.com': [victim, attacker]})

    result = resolver.resolve({'sub': 'new-sub', 'email': 'shared@example.com', 'email_verified': True})

    assert result.decision is LinkDecision.STEP_UP_REQUIRED
    assert result.user_id is None


def test_p24_conflict_resolution_prefers_earliest_created() -> None:
    """O-4 tiebreak: the canonical target under conflict is the earliest-created user."""
    attacker = ExistingUser(user_id='attacker-uid', created_at='2025-01-01T00:00:00+00:00')
    victim = ExistingUser(user_id='victim-uid', created_at='2025-06-01T00:00:00+00:00')
    assert IdentityResolver.earliest_owner([victim, attacker]).user_id == 'attacker-uid'


def test_p24_users_directory_finds_owners_by_email(users_table: Any, dynamodb: Any) -> None:
    """The real users-table directory resolves email owners via the email-index."""
    _seed_user(users_table, user_id='u-100', email='hit@example.com', created_at='2025-02-02T00:00:00+00:00')
    directory = UsersDirectory(table_name=USERS_TABLE, dynamodb_resource=dynamodb)

    owners = directory.find_owners('hit@example.com')

    assert [o.user_id for o in owners] == ['u-100']
    assert directory.find_owners('miss@example.com') == []


# --------------------------------------------------------------------------- #
# 3. authorizer wiring — the shared resolution locus.
# --------------------------------------------------------------------------- #
def _authz_event(method_arn: str = 'arn:aws:execute-api:us-east-1:123456789012:api/dev/GET/jobs') -> dict[str, Any]:
    return {'authorizationToken': 'Bearer test-token', 'methodArn': method_arn}


def test_p24_authorizer_resolves_sub_to_internal_surrogate_user_id(monkeypatch: pytest.MonkeyPatch) -> None:
    """A resolved surrogate becomes the identity context; raw sub is preserved."""
    auth_service = Mock()
    auth_service.validate_token.return_value = {'sub': 'cognito-sub-abc'}
    monkeypatch.setattr(api_gateway_authorizer, '_auth_service', auth_service)

    resolver = Mock()
    resolver.resolve.return_value = ResolvedIdentity(user_id='internal-uid-1', decision=LinkDecision.EXISTING_MAPPING)
    monkeypatch.setattr(api_gateway_authorizer, '_identity_resolver', resolver)

    result = api_gateway_authorizer.lambda_handler(_authz_event(), None)

    assert result['policyDocument']['Statement'][0]['Effect'] == 'Allow'
    assert result['principalId'] == 'internal-uid-1'
    assert result['context']['user_id'] == 'internal-uid-1'
    assert result['context']['principal_id'] == 'internal-uid-1'
    # Raw Cognito sub is preserved distinctly from the internal surrogate.
    assert result['context']['sub'] == 'cognito-sub-abc'


def test_p24_authorizer_denies_when_step_up_required(monkeypatch: pytest.MonkeyPatch) -> None:
    """A STEP_UP_REQUIRED resolution is a hard deny at the edge."""
    auth_service = Mock()
    auth_service.validate_token.return_value = {'sub': 'attacker-sub', 'email': 'victim@example.com'}
    monkeypatch.setattr(api_gateway_authorizer, '_auth_service', auth_service)

    resolver = Mock()
    resolver.resolve.return_value = ResolvedIdentity(user_id=None, decision=LinkDecision.STEP_UP_REQUIRED)
    monkeypatch.setattr(api_gateway_authorizer, '_identity_resolver', resolver)

    result = api_gateway_authorizer.lambda_handler(_authz_event(), None)

    assert result['policyDocument']['Statement'][0]['Effect'] == 'Deny'
    assert result['principalId'] == 'unauthorized'


def test_p24_authorizer_passthrough_when_surrogate_unconfigured(monkeypatch: pytest.MonkeyPatch) -> None:
    """With no mapping table wired, the authorizer keeps the legacy passthrough.

    This is the conservative additive default: surrogate resolution activates
    only once the mapping table env is present, so today's behavior is unchanged.
    """
    monkeypatch.delenv(IDENTITY_MAP_TABLE_ENV, raising=False)
    auth_service = Mock()
    auth_service.validate_token.return_value = {'user_id': 'legacy-user-1'}
    monkeypatch.setattr(api_gateway_authorizer, '_auth_service', auth_service)
    monkeypatch.setattr(api_gateway_authorizer, '_identity_resolver', None)

    result = api_gateway_authorizer.lambda_handler(_authz_event(), None)

    assert result['policyDocument']['Statement'][0]['Effect'] == 'Allow'
    assert result['principalId'] == 'legacy-user-1'
    assert result['context']['user_id'] == 'legacy-user-1'
