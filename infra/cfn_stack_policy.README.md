# CFN Stack Policy — HUMAN-APPLIED (P-27)

`cfn_stack_policy.json` is the authoritative CloudFormation **stack policy** for the
CareerVP stacks. It denies `Update:Replace` and `Update:Delete` on every stateful
resource type so a wrong-profile deploy or a careless `cdk deploy` cannot replace or
destroy them:

| Protected type | Why |
|---|---|
| `AWS::ApiGateway::RestApi` | invoke URL change ⇒ Amplify FE dead for the 908 live dev users |
| `AWS::DynamoDB::Table` (all) | data loss |
| `AWS::S3::Bucket` (all) | data loss (upload bucket is unversioned) |
| `AWS::Cognito::UserPool` | unrecoverable loss of 908 accounts |
| `AWS::CloudFormation::Stack` (nested) | replace/delete of a nested stack cascades to its stateful children |

A catch-all `Allow Update:*` keeps every non-stateful resource (Lambdas, IAM roles,
alarms, etc.) freely updatable. `Deny` always overrides `Allow` in a stack policy, so the
stateful types stay protected regardless of ordering.

> **Form note:** protect-by-type in a CFN stack policy is expressed with
> `"Resource": "*"` + `Condition.StringEquals.ResourceType`, per the
> [AWS docs](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/protect-stack-resources.html).
> The `LogicalResourceId/AWS::DynamoDB::Table/*` form floated in the draft spec is **not**
> valid CFN — `LogicalResourceId/` is followed by a logical id, never a resource type.
> Use `StringLike` (not `StringEquals`) if you ever switch to a wildcard such as
> `AWS::EC2::*`.

---

## HUMAN-APPLIED — DO NOT run `SetStackPolicy` from automation

CI/automation never calls `SetStackPolicy`. Apply the policy **once per top-level stack**
by hand (or from a human-triggered session) after the first successful change-set deploy:

```bash
aws cloudformation set-stack-policy \
  --stack-name CareerVpCrudDev \
  --region us-east-1 \
  --stack-policy-body file://infra/cfn_stack_policy.json

aws cloudformation set-stack-policy \
  --stack-name CareerVpFrontend-Dev \
  --region us-east-1 \
  --stack-policy-body file://infra/cfn_stack_policy.json
```

Verify with:

```bash
aws cloudformation get-stack-policy --stack-name CareerVpCrudDev --region us-east-1
```

This complements — it does not replace — CDK **termination protection**
(`self.termination_protection = True` on `ServiceStack` and `FrontendStack`), which blocks
whole-stack deletion. The stack policy blocks per-resource replace/delete during updates.

---

## P-26 interaction — temporary lift, then reinstate (NEVER weaken permanently)

The P-26 blue/green API migration's **retire step** (delete the old `RestApi`) is
*intentionally* blocked by this policy. Do **not** relax `cfn_stack_policy.json` to let it
through. The correct human-gated sequence is:

1. **Lift, scoped:** a human runs `set-stack-policy` with a *temporary* policy that adds a
   narrow `Allow Update:Delete` on the **specific** old-RestApi logical id (or removes it
   from the deny set) — nothing else.
2. **Execute** the change set that deletes only that old `RestApi`.
3. **Reinstate immediately:** re-apply this full `cfn_stack_policy.json`.

Automation NEVER executes step 1 or step 2. See
`docs/db-redesign/code/code-analysis/project/specs/P-26-blue-green-api-spec.md` and
`specs/P-27-cfn-stack-policy-spec.md` §Step 4 / AC-P27-3.
