---
spec_id: P-27-CFN-STACK-POLICY
title: "CFN stack policy (deny Update:Replace/Delete on RestApi, all DynamoDB, all S3, Cognito UserPool, nested stacks) + termination protection on all stacks"
status: draft
owner: infra
tier: T1
scope_lock_clause: P-27
tooling:
  P-27: {claude_code: {model: sonnet, effort: low}, codex: {model: gpt-5-codex, reasoning: low}}
format_note: "RED tests are TDD-first, not optional; RED-test descriptions inline (v1.3.0); pytest files written at IMPLEMENT in the real careervp repo. Clause carries an AC-### Given/When/Then block (§8.5)."
---

# Spec — Clause P-27: CFN Stack Policy + Termination Protection

- **Status:** SPEC ONLY — do **not** implement here. Apply under TDD in the redesign implementation wave (Wave 0).
- **Governs clause:** `P-27` (CFN stack policy + termination protection). Model/effort in frontmatter above.
- **Code anchor:** `github.com/ymeirovich/careervp @ 0709bbd`. All file:line refs are at that commit.
- **Env note for the implementer:** infra requires Python + `uv` + CDK (`infra/`). Run CDK synth via `cd infra && uv sync && cdk synth`. Stack policy documents are pure JSON; validation is done against the synthesized template.
- **TDD contract:** each fix below lists the **RED test(s) to write and watch fail FIRST**, then the minimal GREEN change. No production edit without a failing test first.
- **Constraints:** the stack policy MUST block any in-place replace or delete of stateful resources; termination protection covers ALL stacks; the policy document is IaC-authored but `SetStackPolicy` is human-applied (never executed by automation). Do not weaken scope-lock §3 frontend contract; do not alter any application handler.

---

## P-27 — Stack Policy Document + Termination Protection

### Current state (confirmed)

`infra/` has no stack policy document and no call to `stack.termination_protection = True` anywhere. The stacks are fully unprotected: a wrong-profile deploy or a careless `cdk deploy` could replace or delete the `AWS::ApiGateway::RestApi` (changing invoke URL → Amplify FE dead for 908 live dev users), any `AWS::DynamoDB::Table` (data loss), any `AWS::S3::Bucket` (data loss), or the `AWS::Cognito::UserPool` (unrecoverable loss of 908 user accounts).

**Root cause:** P-27 was never implemented — no stack policy document exists, no CDK termination protection flag is set.

### Fix (GREEN, minimal)

**Step 1 — Termination protection on all stacks:**

In every CDK stack constructor that inherits from `aws_cdk.Stack` (at minimum `ServiceStack` and `FrontendStack`), set:
```python
self.termination_protection = True
```
This compiles to `TerminationProtection: true` in the CloudFormation template and causes `cdk deploy` to pass `--termination-protection enabled` to the stack. Verify with `cdk synth` — every top-level stack must carry the property.

**Step 2 — Author the stack policy JSON document:**

Create `infra/cfn_stack_policy.json` with the following deny rules, in this exact structure. Allowed (`Allow *`) is the catch-all; Deny statements take precedence:

```json
{
  "Statement": [
    {
      "Effect": "Deny",
      "Action": ["Update:Replace", "Update:Delete"],
      "Principal": "*",
      "Resource": "LogicalResourceId/AWS::ApiGateway::RestApi"
    },
    {
      "Effect": "Deny",
      "Action": ["Update:Replace", "Update:Delete"],
      "Principal": "*",
      "Resource": "LogicalResourceId/AWS::DynamoDB::Table/*"
    },
    {
      "Effect": "Deny",
      "Action": ["Update:Replace", "Update:Delete"],
      "Principal": "*",
      "Resource": "LogicalResourceId/AWS::S3::Bucket/*"
    },
    {
      "Effect": "Deny",
      "Action": ["Update:Replace", "Update:Delete"],
      "Principal": "*",
      "Resource": "LogicalResourceId/AWS::Cognito::UserPool/*"
    },
    {
      "Effect": "Deny",
      "Action": ["Update:Replace", "Update:Delete"],
      "Principal": "*",
      "Resource": "LogicalResourceId/AWS::CloudFormation::Stack/*"
    },
    {
      "Effect": "Allow",
      "Action": "Update:*",
      "Principal": "*",
      "Resource": "*"
    }
  ]
}
```

> **Note:** CFN stack policy `Resource` uses a logical-resource-id wildcard pattern. The wildcard `AWS::DynamoDB::Table/*` covers every `Table` logical id in the stack. For the `RestApi`, the logical id is a specific resource — use `*` to cover any RestApi logical id in the stack, or enumerate by resource type prefix. The canonical form above uses `AWS::ResourceType/*` shorthand that CFN evaluates against the `ResourceType` field of each resource, not the logical id — verify against AWS CFN stack policy docs before implementation. The test suite below drives the correct final form.

**Step 3 — Document the human-apply procedure (runbook stub in `infra/`):**

Add a comment block at the top of `infra/cfn_stack_policy.json`:
```json
// HUMAN-APPLIED — DO NOT execute SetStackPolicy from automation.
// Apply once per stack after initial deploy:
//   aws cloudformation set-stack-policy --stack-name <StackName> --region us-east-1 \
//     --stack-policy-body file://infra/cfn_stack_policy.json
// Reinstate after any permitted exception (see P-26 retire step below).
```

**Step 4 — P-26 retire step interaction (by design):**

The P-27 policy BLOCKS Step 4 of the P-26 blue/green API migration (retire the old RestApi). This is intentional: the old RestApi cannot be deleted without first lifting the policy. The correct human-gated sequence is:
1. Human runs `aws cloudformation set-stack-policy` with a **temporary** policy that allows `Update:Delete` on the specific RestApi logical id.
2. Human executes the change set that deletes the old RestApi.
3. Human immediately reinstates the full P-27 deny policy.

The spec for P-26 MUST cross-reference this procedure. The P-27 policy MUST NOT be weakened permanently to accommodate the retire step.

---

### RED tests to write first (watch fail)

All tests live in `tests/infra/test_p27_stack_policy.py` (authored at IMPLEMENT time, not now).

**`test_stack_policy_denies_replace_on_rest_api`**
- Synthesize the stack policy JSON from `infra/cfn_stack_policy.json` (or from CDK assets).
- Parse the JSON as a Python dict.
- Assert: there exists a `Statement` entry with `Effect == "Deny"`, `"Update:Replace"` in `Action` (or `Action == "Update:Replace"` as a string), and `Resource` targeting `AWS::ApiGateway::RestApi` (by type pattern or logical id wildcard).
- This test MUST FAIL before the policy document exists.

**`test_stack_policy_denies_delete_on_dynamo`**
- Same structure as above.
- Assert: at least one Deny statement covers `"Update:Delete"` AND targets `AWS::DynamoDB::Table` by resource type pattern (not only a named logical id — must cover any table in the stack).
- Also assert the statement covers both `Update:Replace` AND `Update:Delete` (not just one action) — a replace-only deny leaves tables deletable.

**`test_all_stacks_have_termination_protection`**
- Run `cd infra && cdk synth --quiet` and capture the synthesized CloudFormation template(s) for `ServiceStack` and `FrontendStack`.
- Parse each template JSON/YAML.
- Assert: every top-level stack resource (the root template itself) has `TerminationProtection: true` — equivalently, the `EnableTerminationProtection` property is `true` in the CloudFormation stack resource or the `cdk synth` output carries the `--termination-protection` flag annotation.
- Acceptable implementation: assert `stack.termination_protection is True` on every instantiated CDK `Stack` object before `app.synth()`.
- This test MUST FAIL before the property is set.

**`test_stack_policy_blocks_cognito_pool_delete`**
- Assert: at least one Deny statement in the policy covers `"Update:Delete"` AND targets `AWS::Cognito::UserPool` by type pattern.
- Rationale: the UserPool holds 908 live accounts; deletion is unrecoverable. This is a separate assertion from the DynamoDB test because the resource types are distinct.

---

### Acceptance Criteria

**AC-P27-1** — *Given* the stack policy JSON is applied to the stack via `SetStackPolicy`, *When* a change set attempts `Update:Replace` or `Update:Delete` on `AWS::ApiGateway::RestApi`, any `AWS::DynamoDB::Table`, any `AWS::S3::Bucket`, `AWS::Cognito::UserPool`, or any nested `AWS::CloudFormation::Stack`, *Then* CloudFormation rejects the change set update with a policy-violation error and the resource is unchanged.

**AC-P27-2** — *Given* `cdk synth` runs on the current infra, *When* the output templates are inspected, *Then* every top-level stack (ServiceStack, FrontendStack) has termination protection enabled — a human or automation cannot delete the stack without explicitly disabling protection first.

**AC-P27-3** — *Given* the P-26 blue/green retire step must delete the old RestApi, *When* the P-27 policy is active, *Then* the delete FAILS (policy denial) and the human must temporarily lift the policy (human-gated `SetStackPolicy` with a scoped allow, then reinstate) — automation NEVER executes this lift.

**AC-P27-4** — *Given* the stack policy document is `infra/cfn_stack_policy.json`, *When* a non-stateful resource (e.g., a Lambda function, IAM role, CloudWatch alarm) is replaced or deleted, *Then* the policy permits the update (the catch-all `Allow Update:*` applies).

---

### Done-when

All four RED tests pass; `ruff`/`mypy` clean (infra is CDK Python); AC-P27-1..4 hold; `infra/cfn_stack_policy.json` exists and is the authoritative policy document; runbook stub is present; the P-26 spec cross-references the temporary-lift procedure; no application handler code changed.

---

## Sequencing within Wave 0

P-27 is a Wave 0 guardrail and MUST be applied (human `SetStackPolicy` step) before any additive wave deploys. The IaC change (termination protection property) ships with Wave 0; the `SetStackPolicy` human step is gated on the first working CDK deploy that the P-28 changeset workflow produces.

P-27 is a hard dependency of P-26 (retire step cannot proceed without understanding the policy lift); P-27 MUST precede the P-26 blue/green cutover.
