"""P-24 conservative ``sub -> user_id`` identity-surrogate resolver.

Decided in O-4 (RESOLVED 2026-07-09): auto-link a ``sub`` to an EXISTING
internal ``user_id`` ONLY when ``email_verified=true`` AND the email matches AND
the asserting IdP is on the allow-list; otherwise require step-up ("sign in with
your original method to link"); email conflicts resolve to the earliest-created
``user_id``; every link is audit-logged.

Resolution runs in the shared auth layer (the API-GW custom authorizer), not as
a per-handler lookup — the resolved internal ``user_id`` is handed to handlers
via the authorizer context.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from enum import Enum
from typing import Any

from careervp.dal.identity_map_repository import ExistingUser, IdentityMapRepository
from careervp.handlers.utils.observability import logger

# IdP allow-list for silent auto-link. A native Cognito user (no federated
# ``identities`` claim) resolves to ``cognito``. Social providers are added here
# ONLY after their email-verification assertions are trust-vetted — the default
# empty-of-social list is the takeover defense against loosely-asserting IdPs.
TRUSTED_IDPS: frozenset[str] = frozenset({'cognito'})

EmailLookup = Callable[[str], list[ExistingUser]]
UserIdFactory = Callable[[], str]


class LinkDecision(str, Enum):
    """Outcome of resolving a token's identity to an internal ``user_id``."""

    LEGACY_USER_ID = 'legacy_user_id'
    EXISTING_MAPPING = 'existing_mapping'
    CREATED_NEW = 'created_new'
    LINKED_VERIFIED_EMAIL = 'linked_verified_email'
    STEP_UP_REQUIRED = 'step_up_required'


@dataclass(frozen=True, slots=True)
class ResolvedIdentity:
    """Resolved internal identity. ``user_id`` is ``None`` iff step-up is needed."""

    user_id: str | None
    decision: LinkDecision


def _default_user_id_factory() -> str:
    return str(uuid.uuid4())


def _clean(value: Any) -> str:
    return value.strip() if isinstance(value, str) and value.strip() else ''


def _is_truthy_flag(value: Any) -> bool:
    return value is True or (isinstance(value, str) and value.strip().lower() == 'true')


class IdentityResolver:
    """Resolve validated JWT claims to a durable internal ``user_id``."""

    def __init__(
        self,
        identity_map: IdentityMapRepository,
        email_lookup: EmailLookup,
        *,
        trusted_idps: frozenset[str] = TRUSTED_IDPS,
        user_id_factory: UserIdFactory | None = None,
    ) -> None:
        self._identity_map = identity_map
        self._email_lookup = email_lookup
        self._trusted_idps = trusted_idps
        self._user_id_factory = user_id_factory or _default_user_id_factory

    def resolve(self, claims: dict[str, Any]) -> ResolvedIdentity:
        """Resolve ``claims`` to an internal ``user_id`` under the O-4 policy."""
        # 1. First-party tokens already carry the internal user_id — passthrough.
        legacy_user_id = _clean(claims.get('user_id'))
        if legacy_user_id:
            return ResolvedIdentity(legacy_user_id, LinkDecision.LEGACY_USER_ID)

        sub = _clean(claims.get('sub'))
        if not sub:
            # No usable identity claim — the authorizer denies.
            return ResolvedIdentity(None, LinkDecision.STEP_UP_REQUIRED)

        # 2. A sub already mapped resolves to its stable internal user_id.
        existing_user_id = self._identity_map.get_user_id(sub)
        if existing_user_id:
            return ResolvedIdentity(existing_user_id, LinkDecision.EXISTING_MAPPING)

        # 3. New sub: decide the target under link-by-verified-email (O-4).
        email = _normalize_email(claims.get('email'))
        owners = self._email_lookup(email) if email else []
        if owners:
            return self._resolve_with_existing_owner(sub, owners, claims)

        # 4. No existing owner — mint a fresh surrogate for this new human.
        minted = self._identity_map.link(sub, self._user_id_factory())
        logger.info('identity_surrogate created new user_id', sub=sub, user_id=minted)
        return ResolvedIdentity(minted, LinkDecision.CREATED_NEW)

    def _resolve_with_existing_owner(
        self,
        sub: str,
        owners: list[ExistingUser],
        claims: dict[str, Any],
    ) -> ResolvedIdentity:
        # A conflicting email (>1 owner) is the preemption/ambiguity vector — it
        # must never be claimed silently; require step-up.
        if len(owners) > 1:
            logger.warning(
                'identity_surrogate step-up: email conflict',
                sub=sub,
                owner_count=len(owners),
                earliest_user_id=self.earliest_owner(owners).user_id,
            )
            return ResolvedIdentity(None, LinkDecision.STEP_UP_REQUIRED)

        if not self._is_safe_to_autolink(claims):
            logger.warning('identity_surrogate step-up: unsafe auto-link', sub=sub)
            return ResolvedIdentity(None, LinkDecision.STEP_UP_REQUIRED)

        target = owners[0].user_id
        linked = self._identity_map.link(sub, target)
        logger.info('identity_surrogate linked sub to existing user_id', sub=sub, user_id=linked)
        return ResolvedIdentity(linked, LinkDecision.LINKED_VERIFIED_EMAIL)

    def _is_safe_to_autolink(self, claims: dict[str, Any]) -> bool:
        if not _is_truthy_flag(claims.get('email_verified')):
            return False
        return self._identity_provider(claims) in self._trusted_idps

    @staticmethod
    def _identity_provider(claims: dict[str, Any]) -> str:
        """Return the lowercased asserting IdP; native Cognito users are ``cognito``."""
        identities = claims.get('identities')
        if isinstance(identities, list) and identities:
            first = identities[0]
            if isinstance(first, dict):
                provider = first.get('providerName')
                if isinstance(provider, str) and provider.strip():
                    return provider.strip().lower()
            return 'unknown'
        # A federated ``identities`` claim is sometimes serialized as a JSON
        # string; anything non-empty and non-native is treated as untrusted.
        if isinstance(identities, str) and identities.strip():
            return 'unknown'
        return 'cognito'

    @staticmethod
    def earliest_owner(owners: Iterable[ExistingUser]) -> ExistingUser:
        """O-4 tiebreak: the canonical owner under conflict is earliest-created."""
        return min(owners, key=lambda owner: (owner.created_at, owner.user_id))


def _normalize_email(value: Any) -> str:
    return value.strip().lower() if isinstance(value, str) and value.strip() else ''
