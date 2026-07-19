# P-28 — Human-Gated Deploy Runbook (HUMAN-APPLIED, not automated)

The IaC/CI portions of P-28 land in code (Wave 0 · step 0.55): account/region pin in
`infra/app.py`, `concurrency: group=deploy` without `cancel-in-progress`, the
create-change-set → human-gated execute-change-set split in `.github/workflows/deploy.yml`,
the `DescribeChangeSet` Replacement report (`scripts/ci/changeset_replacement_report.py`),
and the scope-lock guard (`scripts/ci/check_scope_lock_integrity.py` +
`.github/workflows/scope-lock-guard.yml`).

The following steps **cannot** be automated from an agent/CI session and MUST be applied by
a human in the GitHub UI / AWS console **before the first change-set-only deploy runs** —
otherwise `execute-change-set-dev` has no gate and the human-only-execute invariant is
decorative.

## 1. Branch-protect `main`
GitHub → Settings → Branches → add a rule for `main`:
- Require a pull request before merging (≥1 approval).
- Require status checks to pass: `scope-lock-integrity`, plus the existing db-redesign gates.
- Do not allow direct pushes / force-pushes to `main`.

## 2. Create the `deploy-dev` GitHub deployment environment with a required reviewer
GitHub → Settings → Environments → **New environment** → name it exactly `deploy-dev`
(matching `environment: deploy-dev` on the `execute-change-set-dev` job):
- **Required reviewers:** add yourself (the human operator). This is the gate — the workflow
  pauses at `execute-change-set-dev` until you approve.
- The reviewer reads the **Replacement report** (posted to the run's job summary by
  `create-change-set-dev`) BEFORE approving. If it shows AUTO-FAIL, the create job already
  failed and there is nothing to approve.
- Repeat for `staging` / `prod` environments (used by `execute-change-set-other`) if/when
  those environments exist.

## 3. Split the deploy IAM roles (least privilege)
- **`secrets.AWS_ROLE`** (automation, create job): grant ONLY
  `cloudformation:CreateChangeSet`, `DescribeChangeSet`, `DescribeStacks`,
  `ListChangeSets`, plus `s3:GetObject`/`PutObject` on the CDK assets bucket and
  `ssm:GetParameters` for CDK lookups. It MUST NOT have `cloudformation:ExecuteChangeSet`,
  `DeleteStack`, or data-plane `Update:*`.
- **`secrets.AWS_EXECUTE_ROLE`** (human-gated execute job): may have
  `cloudformation:ExecuteChangeSet` on the specific stacks, but NOT `CreateStack` /
  `DeleteStack`. If this secret is absent the workflow falls back to `AWS_ROLE` (so add the
  role and the secret as part of this step to realise the least-privilege split).

## 4. Apply the P-27 stack policy (separate, related human step)
Per `infra/cfn_stack_policy.README.md`, run `aws cloudformation set-stack-policy` once per
top-level stack. Automation never does this.

## 5. Dev-only devx parallel-stack cutover (P-26 v2.6.0 amendment)

`CareerVpCrudDevx`'s creation change set and its later base-path flip (`api.dev.careervp.com`
`BasePathMapping` re-pointed from `CareerVpCrudDev` to `CareerVpCrudDevx`) both go through this
same create-change-set → human-gated execute-change-set flow — no new environment/role is
needed. The flip change set MUST show `Replacement: false` for the `BasePathMapping` and MUST
NOT touch any `AWS::ApiGateway::RestApi`, `DynamoDB::Table`, `S3::Bucket`, or
`AWS::Cognito::UserPool`; the Replacement report auto-fails otherwise (see P-26 spec, AC-P26-6).
The eventual decommission of the old `CareerVpCrudDev` stack is a separate, later, explicitly
human-approved step — never bundled into the cutover change set.

## NOT part of P-28 / step 0.55
- AWS Budgets + Cost-Anomaly Detection = **step 0.56 / P-32**, now defined as CDK
  in `infra/careervp/monitoring.py` (moved console→IaC by explicit decision,
  2026-07-12 — see `runbooks/p32-budgets-cost-anomaly-runbook.md`). Deploys through
  this same change-set flow; only the post-deploy evidence capture is still
  human-only.
