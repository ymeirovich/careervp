# Live-verified truth — 2026-07-11 (for the implementation-plan eval council)

Read-only recon against AWS account **788159322332**, `us-east-1`, caller
`arn:aws:iam::788159322332:user/presgen_user`. Non-destructive (ListTables, DescribeTable,
DescribeContinuousBackups, DescribeTimeToLive, limited 40-item Scan, CFN List/Describe). Raw
DynamoDB recon saved alongside at `recon-output-2026-07-11.txt`. **Live truth supersedes any
static claim in the plan or the Fable evidence.**

## 1. DynamoDB (recon.py --env dev) — confirms findings-register exactly
| Table | Items | PITR | Key conventions seen (schema drift) |
|---|---|---|---|
| applications-table | 9 | ENABLED | userId/applicationId, job_id |
| artifacts-table | 221 | ENABLED | applicationId/artifactId, job_id, userId/applicationId, pk/sk |
| company-research-cache-table | 2 | ENABLED | cacheKey |
| cvs-table | 6 | ENABLED | pk/sk, userId/cvId |
| gap-responses-table | 16 | ENABLED | userId/questionId, job_id |
| idempotency-table | 0 | ENABLED | (empty) |
| jobs-table | 144 | ENABLED | job_id |
| knowledge-table | 0 | ENABLED | (empty) |
| llm-cache | 0 | **DISABLED** | (empty) |
| users-table | 908 | ENABLED | pk/sk, job_id, userId/cvId |

- Volumes tiny (users 908 / artifacts 221 / jobs 144 / rest <20) → backfill is hours. **Confirmed.**
- Multi-schema drift is **physically present** (artifacts carries 4 key conventions incl. `pk/sk`;
  cvs dual-key `pk/sk`+`userId/cvId`; users mixed). **Confirmed.**
- PITR ENABLED on all except `llm-cache` (rebuildable). **Confirmed.**

## 2. CloudFormation resource count — resolves the 415-vs-476 conflict
Live `list-stack-resources` (paginated; summed across pages):

| Stack | Direct resources | Nested-stack children |
|---|---|---|
| **CareerVpCrudDev (root)** | **415 / 500** | 4 (AiAssist 7, CompanyResearch 4, ErrorReport 7, Monitoring 23) |
| CareerVpCrudStaging | 378 | 0 |
| CareerVpFrontend-Dev | 8 | 0 |

**Verdict on the tension:** the **findings-register / scope-lock figure of 415/500 is CORRECT for
the deployed dev stack.** The Fable evidence's "476/500, register is stale math" is **wrong for the
deployed state** — *unless* 476 was measured from a `cdk synth` of the `db-redesign` branch that
adds resources not yet deployed. **The council must treat the 415 as the live baseline** and, if it
wants the post-additions figure, derive it from `cdk synth`, not assert 476 as current. Either way
the plan's ordering conclusion (decompose before additive work) still holds — headroom is ~85 slots,
and P-09/P-14/P-17/P-21 each add resources.

## 3. Still-open (could NOT be resolved here — need repo code / API GW introspection)
These were flagged in the Fable evidence's "open questions"; resolve before or during the council:
- **Is Cognito auth actually enforced in the deployed dev stack?** — `aws apigateway get-method
  --rest-api-id <id> --resource-id <protected> --http-method GET` and inspect `authorizationType`.
  (Not run here — needs the live rest-api-id + resource-id.)
- **Does `AUTHORIZER_DISABLED` have any code readers?** — `grep -rn AUTHORIZER_DISABLED src/backend/`
  in the `careervp` repo. (Repo not checked out in this environment.)
- **Actual full-stack redeploy RTO** — measure empirically; the Fable plan's "15–30 min" is an estimate.

## 4. Provenance
- Anchor: analysis was against `github.com/ymeirovich/careervp @ 4f7c294` (2026-06-29). This live
  recon is 2026-07-11 — no DynamoDB drift vs the register's earlier passes.
- Fable evidence saved verbatim at `fable-infra-mitigation-plan.md` (62 KB, dated 2026-07-11).
