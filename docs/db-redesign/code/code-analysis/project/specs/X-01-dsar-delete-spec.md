---
spec_id: X-01-DSAR-DELETE
title: "Account-close delete-all-my-data"
status: draft
owner: backend
tier: T2
scope_lock_clause: X-01
claude_code: {model: opus, effort: high}
codex: {model: gpt-5-codex, reasoning: high}
format_note: "AUTHOR ONLY. RED tests are inline descriptions; pytest files are written later at IMPLEMENT time."
---

# Spec - X-01: Delete All My Data

## Problem Statement

Lightweight DSAR requires account-close deletion in addition to export. Delete must remove the full `USER#{user_id}` collection, owned S3 objects, and Cognito user while avoiding shared caches and cross-user data.

## Evidence

- `project-scope-lock.md:210` defines X-01 as account-close delete-all-my-data, export already exists.
- `src/backend/careervp/handlers/auth_handler.py:104` writes user items with `pk: USER#{user_id}`.
- `src/backend/careervp/dal/subscription_repository.py:66,103,152,299` uses `USER#{user_id}` subscription/profile keys.
- `src/backend/careervp/handlers/export_handler.py:98,123,136,147,161` shows export/access to artifact buckets and tables.
- Scope-lock C-5 says no GDPR gold-plating; lightweight export/delete only.

## Fix Plan

1. Add an authenticated account-close flow that resolves internal `user_id` via P-24 identity.
2. Enumerate and delete the full `USER#{user_id}` collection with pagination.
3. Delete S3 objects owned by that user from upload/artifact buckets using scoped prefixes/indexes.
4. Delete or disable the Cognito user after data deletion succeeds.
5. Do not delete shared company research cache, LLM cache, idempotency records for other users, or sub->user mapping until account identity cleanup policy is explicit.

## RED Tests to Write First

- `test_x01_delete_user_collection_paginates_until_empty`: moto table with multiple pages; assert all `USER#{user_id}` items deleted.
- `test_x01_delete_user_s3_objects_only`: moto buckets with two users; assert only target user's objects are deleted.
- `test_x01_does_not_delete_shared_company_research_cache`: seed shared CR cache; assert it remains after account delete.
- `test_x01_cognito_delete_after_data_success`: patch Cognito; assert user delete called only after table/S3 deletion succeeds.
- `test_x01_partial_failure_returns_result_error`: force S3 failure; assert Cognito delete is not called and Result/error envelope reports failure.

## Acceptance Criteria

**AC-X01-1** - Given an authenticated account-close request, when deletion succeeds, then user-owned DynamoDB items, S3 objects, and Cognito user are removed.

**AC-X01-2** - Given shared/cross-user data, when account delete runs, then shared caches are not removed.

**AC-X01-3** - Given partial failure, when deletion cannot complete, then the flow fails closed and does not delete Cognito user prematurely.

## Done-when

All RED tests pass; deletion is idempotent/retryable; no GDPR-heavy workflow is added.

## Sequencing / Dependencies

Depends on P-24 for durable `user_id` identity. T2, not launch-critical unless product policy changes.

