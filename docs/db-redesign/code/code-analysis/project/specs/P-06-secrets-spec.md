---
spec_id: P-06-SECRETS
title: "JWT keys and webhook secrets out of Lambda environment"
status: draft
owner: infra
tier: T1
scope_lock_clause: P-06
claude_code: {model: sonnet, effort: medium}
codex: {model: gpt-5-codex, reasoning: medium}
format_note: "AUTHOR ONLY. RED tests are inline descriptions; pytest files are written later at IMPLEMENT time."
---

# Spec - P-06: Secrets Out of Lambda Environment

## Problem Statement

JWT key material and webhook secrets must not be exposed as plaintext Lambda environment values. The implementation must use SSM SecureString or Secrets Manager references and fetch sensitive values at runtime, while non-sensitive parameter names may remain in environment variables.

## Evidence

- `infra/careervp/api_construct.py:925-928,1407-1410,1809-1812,1887-1890,1927-1930,1992-1995` injects JWT private/public values via `ssm.StringParameter.value_for_string_parameter`, which resolves into Lambda env at deploy rather than a runtime secret fetch.
- `infra/careervp/api_construct.py:2569-2573` sets payment webhook secret env vars to SSM parameter names, which is the desired non-secret pattern.
- `infra/careervp/constants.py:200-206` defines webhook SecureString parameter paths and env var names for primary and previous secrets.
- `src/backend/Makefile:164` uses `--type SecureString`, confirming SecureString is already an accepted operational primitive.

## Fix Plan

1. Inventory all Lambda env vars whose value is secret material, starting with JWT private/public keys and payment-provider webhook secrets.
2. Keep only parameter names or Secrets Manager ARNs in Lambda env. Fetch the secret at runtime through a shared cached secret provider.
3. Grant `ssm:GetParameter` with `WithDecryption` or `secretsmanager:GetSecretValue` to only the functions that need the secret, ARN-scoped and env-suffixed.
4. Preserve rotation support by supporting current and previous webhook secret values.
5. Keep request/response shapes unchanged; this is internal infra/runtime wiring only.

## RED Tests to Write First

- `test_p06_lambda_env_has_no_plaintext_jwt_key_material`: synth CDK and assert no Lambda environment value contains PEM markers or resolved JWT key text.
- `test_p06_secret_env_values_are_references_only`: assert JWT and webhook env vars match `/careervp/{env}/...` parameter paths or Secrets Manager ARNs, not secret payloads.
- `test_p06_runtime_secret_provider_fetches_with_decryption`: patch SSM/Secrets Manager client; assert runtime fetch uses `WithDecryption=True` for SSM SecureString and caches the value per execution environment.
- `test_p06_iam_secret_access_is_arn_scoped`: synth IAM policies and assert secret grants do not use `Resource: "*"`.

## Acceptance Criteria

**AC-P06-1** - Given synthesized Lambda env vars, when scanned, then no JWT private key, JWT public key, or webhook secret value is present as plaintext.

**AC-P06-2** - Given a function needs a secret, when it fetches at runtime, then the provider uses SecureString/Secrets Manager with decryption and caches without logging secret values.

**AC-P06-3** - Given CDK policies, when inspected, then secret access is scoped to env-specific parameter ARNs and no known ARN uses wildcard resource access.

## Done-when

All RED tests pass; Ruff/mypy pass for changed Python; `cdk diff` shows zero stateful replacements; naming validator passes after infra changes.

## Sequencing / Dependencies

Lands in Wave 1 after P-23 rollback safety. Does not depend on P-24 and must not change auth identity semantics.

