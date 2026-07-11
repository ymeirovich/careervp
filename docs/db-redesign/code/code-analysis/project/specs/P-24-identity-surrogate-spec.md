---
spec_id: P-24-IDENTITY-SURROGATE
title: "Internal user_id surrogate and sub-to-user mapping"
status: draft
owner: auth
tier: T1
scope_lock_clause: P-24
claude_code: {model: opus, effort: xhigh}
codex: {model: gpt-5-codex, reasoning: high}
format_note: "AUTHOR ONLY. RED tests are inline descriptions; pytest files are written later at IMPLEMENT time."
---

# Spec - P-24: Identity Surrogate

## Problem Statement

The tenant key must become an internal immutable `user_id`; Cognito `sub` values are resolved at the edge and never used directly as the durable tenant partition key. The resolver must be shared, atomic, cache-aware, and social-IdP safe.

## Evidence

- `infra/careervp/api_construct.py:1987-2002` creates the API Gateway authorizer Lambda, the likely shared resolution locus.
- `src/backend/careervp/handlers/auth_handler.py:104` writes `pk: USER#{user_id}`, showing user-scoped items already exist.
- `infra/careervp/api_db_construct.py:337-361` creates a knowledge table keyed by `userEmail`, proving user identifiers are inconsistent today and need P-24/D-M5 follow-up.
- Scope-lock P-24 mandates shared auth-layer resolution, conditional put JIT creation, a separate mapping table or `sub`-keyed GSI, cache invalidation on link events, and adversarial checks for `email_verified` and earliest-created-user preemption.

## Fix Plan

1. Put resolution in a shared authorizer or middleware, not per-handler DynamoDB calls.
2. Create a separate `sub -> user_id` mapping table or sub-keyed GSI outside `core`.
3. JIT-create with conditional put `attribute_not_exists(sub)`; losing concurrent writers re-read.
4. Link social IdP subs only when IdP is allow-listed, `email_verified=true`, and email matches; otherwise require step-up with original method.
5. Emit resolver success/failure metrics and invalidate cache on account-link events.
6. Do not move Cognito user pool.

## RED Tests to Write First

- `test_p24_resolution_locus_shared_not_per_handler`: static scan asserts handlers consume authorizer context/middleware identity and do not each query mapping table.
- `test_p24_jit_create_uses_conditional_put_and_loser_rereads`: moto concurrent first-request simulation asserts one `user_id` is created for one `sub`.
- `test_p24_mapping_not_stored_in_user_partitioned_core`: synth/data-layer test asserts mapping lives in a separate table or sub-keyed GSI, not `USER#{user_id}` core.
- `test_p24_email_verified_idp_allowlist_blocks_takeover`: untrusted or unverified IdP email cannot auto-link.
- `test_p24_earliest_created_preemption_requires_step_up`: attacker pre-registering victim email cannot silently claim existing account without the decided step-up policy.
- `test_p24_cache_invalidates_on_link_event`: link event clears resolver cache and next request resolves updated mapping.

## Acceptance Criteria

**AC-P24-1** - Given a valid Cognito JWT, when the edge resolver runs, then handlers receive an internal `user_id` and never trust client-supplied tenant identity.

**AC-P24-2** - Given concurrent first requests for the same `sub`, when JIT creation races, then exactly one `user_id` is created and the loser re-reads it.

**AC-P24-3** - Given social IdP linking, when email trust or preemption vectors are attempted, then unsafe auto-link is denied and audit logged.

## Done-when

All RED tests pass; adversarial auth review returns no blocking questions; `cdk diff` zero stateful replacement; naming validator passes.

## Sequencing / Dependencies

Depends on P-26 and P-30. O-4 is resolved. P-23 should exist for rollback before handler identity cleanup consumes this resolver broadly.

