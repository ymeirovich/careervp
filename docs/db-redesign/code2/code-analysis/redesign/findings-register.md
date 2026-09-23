# CareerVP — Full Findings Register (un-compressed scope)

**This replaces the earlier "prioritized ladder" as the source of truth for SCOPE.**
The ladder showed *what to do first*; this shows *the true size of the gap*. Consolidated
and deduplicated from: the DB dossier, Council Query A (50 items), the coverage-matrix
pass, the per-service infra audit (17 services), and the AWS best-practices guide (§2–§15).

**Honest scope count:** ~**23 launch-blocking (HIGH/CRITICAL)** findings · ~**30 strongly-
recommended (MEDIUM)** · a long **LOW/hygiene** tail · **plus** the DB best-practice
program (single-table migration) as its own multi-week track. **Not a handful — ~70–90
discrete findings.** Earlier compression came from (a) collapsing to representative tiers,
(b) showing only launch-blockers, (c) root-cause grouping. Corrected here.

Two tracks run in parallel:
- **Track P — Production launch-blockers** (get to a safe *paid* launch).
- **Track D — DB best-practice program** (the "do it once" single-table migration; some
  of its pieces are also launch-blockers, marked ⟡).

---

## Live verification (AWS acct 788159322332, us-east-1, dev — 2026-07-04)

Read-only sweep. **No `prod` env exists — only `dev` + `staging`** (going to production
is a genuine first prod deploy). **Shared personal account** (unrelated `bank-data-records`,
`personal-password-manager`, `casper-*` buckets present) → amplifies the single-account
IAM blast-radius concern (§18.1, #9).

> **Re-verified 2026-07-08 (recon.py + read-only CLI): every claim below still holds — no drift
> that moves any finding.** Refinements only: (a) PITR window is 7d on the 8 PII tables, **35d on
> `idempotency`**, **DISABLED on `llm-cache`** (prod-only in code — a rebuildable cache, no
> data-loss concern); (b) `llm-cache` item count **11→0** (TTL expiry, expected); (c) WAF is not
> merely detached — **zero REGIONAL web ACLs exist** in the account; (d) 3 `careervp` Cognito
> pools live (1 dev, 2 staging — one staging pool may be orphaned). Deletion protection FALSE ×10,
> throttle 2rps/10, SNS 0 subs, MFA OFF, 0/31 reserved concurrency, CFN 415/500 + 4 nested — all
> re-confirmed. Also resolved: the **active `api_db_construct` schema is the deployed one** (live
> keys `userId/cvId`, `userId/applicationId`, `job_id`, `pk/sk`); the legacy `RETAIN` `user_email`
> `DynamoDBStack` is dead code → delete (DB-L1).
>
> **Re-verified 2026-07-11 (recon.py + CFN List/Describe → `redesign/evidence/live-truth-2026-07-11.md`):**
> every claim still holds. DynamoDB volumes/PITR/drift unchanged (users 908 / artifacts 221 / jobs 144;
> PITR on except `llm-cache`; multi-schema drift physically present). **CFN count re-confirmed: root
> `CareerVpCrudDev` = 415/500 direct + 4 nested (AiAssist/CompanyResearch/ErrorReport/Monitoring);
> staging = 378, 0 nested.** Reconciliation: the Fable infra-mitigation plan's "476/500, register is
> stale" is **not the deployed figure** — 476 is most plausibly a post-`cdk synth`-with-additions count;
> treat **415 as the live baseline** (the eval council must not adopt 476 as current). Still open (need
> repo/API-GW introspection): is Cognito auth enforced in the deployed stack, and does
> `AUTHORIZER_DISABLED` have any code readers.

**CONFIRMED LIVE (inferred → verified):**
- Deletion protection **FALSE on all 10 dev tables** → #12/#13 data-loss risk is real.
- API stage throttle **2 rps / burst 10** live (account limit 10k; the stage override is the cap) → #20.
- **WAF not attached** to the dev API stage (no `webAclArn`) → #11.
- **SNS monitoring topic: 0 subscribers** on BOTH dev and staging → #21 (alarms notify nobody).
- **Cognito MFA OFF**, min-length 8, `RequireSymbols=false` (dev + staging) → #7.
- **CV bucket CORS `["*"]`** live (Block-Public-Access fully ON, so not publicly exposed) → #8.
- **Reserved concurrency: 0 of 31 dev functions**; account unreserved 1000 → #16.
- **CFN 500-resource ceiling is imminent:** root `CareerVpCrudDev` = **415/500 direct resources** (83%) with only 4 nested children (AiAssist, CompanyResearch, ErrorReport, Monitoring); staging = 378, **0 nested**. Biggest sinks: 115 ApiGateway::Method + 60 ::Resource (CORS-OPTIONS-per-route doubling), ~139 Lambda-satellite (31 fn × ~5). → #8 is a live near-blocker; nested-stack decomposition must precede adding redesign resources (per-fn roles, idempotency, DLQ reapers, alarms all ADD count).
- **`idempotency` table empty (0 items)** → #14 / F3 (idempotency wired to nothing, in use).
- **Multi-schema drift is physically present:** `artifacts` rows carry `applicationId/artifactId`
  + `pk/sk`(`ARTIFACT#`) + `job_id` at once; `cvs` carry both `userId/cvId` + `pk/sk`;
  `users` (908 items) mixes `PROFILE` + `ARTIFACT#` + `CV` + tailored-CV → #1 / Track D.

**CFN headroom fix — #8 resolution design:**
1. **Nest the whole `RestApi`** (not individual methods) into its own nested stack — a `RestApi`'s Resources/Methods/Deployment must share one API, so the API construct itself becomes the nesting boundary. Collapses the live **175 API-GW resources (115 Method + 60 Resource) to 1** `AWS::CloudFormation::Stack` in the parent. Feature Lambdas get their own per-feature nested stacks (extending the existing AiAssist/CompanyResearch/ErrorReport/Monitoring pattern); refs pass as constructor props, never `Fn::ImportValue`.
2. **Shrink the count too:** consolidate per-route CORS `OPTIONS` (roughly half of the 115 Methods) and extend the `{proxy+}` Lambda-proxy pattern (already used for `/auth`,`/users`,`/gap-analysis`,`/billing`) to remaining features — fewer real resources, not just fewer nested.
3. **Caveat:** recreating the `RestApi` can change the `execute-api` invoke URL the frontend calls (`NEXT_PUBLIC_API_URL`). Mitigate via retained logical ID, or (better, already NFR-SCALE/DEP-listed) a custom domain + ACM in front so the URL is stable. Low-risk to do now since we're dev-only — verify the frontend still resolves after.
4. **Ordering:** decompose the API stack *before* adding resources that grow the parent further (per-function IAM roles NFR-SEC-4, idempotency table wiring, DLQ reapers, new alarms) — otherwise those land on an already-near-full stack.

**CORRECTED (assumption → live truth):**
- **PITR is ENABLED on all dev tables except `llm-cache`** (disabled — prod-only in code;
  rebuildable cache so fine); `idempotency` window is 35d, the rest 7d. Residual risk is
  `DESTROY` + no deletion protection, NOT PITR.
- **`/api/*` legacy surface is STAGING-ONLY** (7 paths incl. `/api/vpr/status/{job_id}`); the
  dev API's 61 resources are clean. Finding #3 resolved — decide whether prod carries the
  legacy `/api/*` or drops it. Also: the dev REST API's stage is literally named `prod` (a
  naming artifact, not a real prod environment).

**VOLUME (production-shaped, tiny → backfill is cheap, Track D LOE → low end):**
users 908 · artifacts 221 · jobs 144 · gap-responses 16 · applications 9 · cvs 6 ·
llm-cache 0 (was 11; TTL-expired) · CR-cache 2 · idempotency 0 · knowledge 0. *(re-verified 2026-07-08)*

---

## TIER 1 — Launch-blockers (🚫 cannot safely go to paid production without these)

### Correctness (broken features today)
| # | Finding | Source | Cite |
|---|---|---|---|
| 1 ⟡ | Cover letter + interview prep FAIL (3-schema routing + `vpr_id`-is-not-a-key identifier defect) | dossier | `docs/db-redesign/01` |
| 2 | Billing reconcile fails at invoke — infra entrypoint `.handler` vs source `lambda_handler` | async pass | `api_construct.py:2640` |
| 3 | Entire `/api/*` API surface (`/api/vpr`, `/api/vpr/status/{job_id}`, `/api/cv`, `/api/cv-tailoring`, `/api/company-research`) uninventoried — must be mapped before any redesign | this session | `...2026-05-16.json` |

### Security / Auth
| # | Finding | Cite |
|---|---|---|
| 4 | `x-user-id` header auth bypass + `AUTHORIZER_DISABLED=true` (non-prod) | `auth_utils.py:44` |
| 5 | IDOR: `get_job` (+ sibling handlers) return data without owner-vs-JWT check | council #6 |
| 6 | JWT private key + payment webhook secret baked into Lambda **env** (plaintext at rest) | `api_construct.py:894,2538` |
| 7 | Cognito: **no MFA, no advanced security / account-takeover protection**; `implicit_code_grant` + `COGNITO_ADMIN` scope on a public SPA client | `cognito_construct.py:27,44,47` |
| 8 | CV bucket CORS `allowed_origins=["*"]` (user PII documents) | `api_db_construct.py:190` |
| 9 | Single shared IAM role across ~20 functions (billing Lambda can read CV buckets, etc.) | `api_construct.py:501` |
| 10 | API Gateway CORS `ALL_ORIGINS` + GatewayResponse `Access-Control-Allow-Origin: '*'` | `api_construct.py:326,393` |
| 11 | WAF: **no rate-based rule**, prod-only (dev/staging unprotected), never attached to CloudFront | `waf_construct.py`, `api_construct.py:240` |

### Data safety
| # | Finding | Cite |
|---|---|---|
| 12 ⟡ | `RemovalPolicy.DESTROY` + `auto_delete_objects` on **every** table + bucket **including `backups`** — a stack replacement / `cdk destroy` wipes user data and backups | `api_db_construct.py:101,164,190` |
| 13 | Dead `DynamoDBStack`/`S3Stack` (the only `RETAIN`+versioned code) never instantiated; deployed resources use `DESTROY` | `app.py:39,58` |

### Money path (paid launch)
| # | Finding | Cite |
|---|---|---|
| 14 | No idempotency on billing (Stripe-style retries double-charge) or on async workers | council #5, F3 |
| 15 ⟡ | Billing-path **Scan** (`get_subscription_by_customer_id`) — §5.1 no-Scan violation on a request path | `subscription_repository.py:127` |

### Reliability under load
| # | Finding | Cite |
|---|---|---|
| 16 | **No concurrency bounds** anywhere (no reserved/max) → Anthropic/Tavily/payment stampede, no API headroom | grep: none |
| 17 | SQS: no `ReportBatchItemFailures`; 8 DLQs with no reaper/replay → silent 14-day data loss | audit §5, async pass |
| 18 | SQS visibility timeout ≈ 1× function timeout → mid-flight redelivery → duplicate AI spend | council #3 |
| 19 | `retry_attempts=0` on async-invoked functions → dropped events | `api_construct.py` ×2 |

### Scale
| # | Finding | Cite |
|---|---|---|
| 20 | API stage throttle **2 rps / burst 10** account-wide — self-DoS, unusable | `api_construct.py:338` |

### Observability
| # | Finding | Cite |
|---|---|---|
| 21 | SNS monitoring topic has **zero subscribers** — every alarm notifies nobody | `monitoring.py:71` |

### CI/CD deploy safety
| # | Finding | Cite |
|---|---|---|
| 22 | `cdk-diff.yml` uses long-lived AWS access keys (every other workflow uses OIDC) | `cdk-diff.yml` |
| 23 | No Lambda alias/version + CodeDeploy canary/linear + auto-rollback anywhere → no safe rollout | grep: none |

---

## TIER 2 — Strongly recommended pre-launch (⚠️ MEDIUM)

**Observability:** log retention **1-day** on every group → 30–90d · missing alarms (Lambda
errors/throttles, **p99**, DLQ depth ×all, API 4xx, DynamoDB throttles on all tables not
just 2, SFN failures, concurrency-near-limit) · broken/inverted dashboard flag
(`monitoring.py:215/250`) · `monitoring.py` still has copy-pasted "Order" metrics · no
synthetic canary on `/health`.
**Reliability:** EventBridge rule targets have no DLQ · VPR SFN state has no
`heartbeat_timeout` (hangs to 2h) · CR queue visibility 120s < SFN heartbeat 180s mismatch.
**Security:** API Gateway request validators/models (validate at edge) · KMS `Decrypt`/
`GenerateDataKey` on `Resource:"*"` · WAF log-group `AnyPrincipal()` · `artifacts_table`
grant includes `Scan` · retire self-managed JWT path in favor of Cognito-only (decided).
**Data rights:** personal-data account-delete/export (holds real CVs).
**Testing:** fix the autouse `mock_artifact_dependency_resolver` (make opt-in) · turn on
branch coverage (currently 0) · whole-chain-to-persisted-result + replay-same-event +
`batchItemFailures` + cross-tenant negative tests.
**CI:** mypy disabled in pre-commit · no secret scanning (gitleaks/trufflehog).
**S3:** CV bucket unversioned · no server access logging · CV lifecycle 30d vs metadata
TTL 90d (orphan pointers).
**Backups:** no scheduled on-demand DynamoDB backup; `backups` bucket is `DESTROY`; PITR
only 7d on most tables.
**Cost/margin:** `Tags.of(app)` app-wide (`Environment`/`CostCenter`) · AWS Budgets +
Cost Anomaly Detection · AI-spend metric (Sonnet vs Haiku) · prompt-cache breakpoints +
bound artifact output `max_tokens` · retire `len/4` token estimator.
**Custom domain/ACM** on the API (frontend has one; API doesn't).

---

## TIER 3 — Post-launch / hygiene (▫️ LOW)

ARM64/Graviton migration · GSI `ALL`→minimized projections · remove dead `knowledge_table`
+ dead `vpr_handler.py`/`knowledge_base_handler.py` + unwired `gap-analysis-queue`/`jobs`
stream · S3 object lock + cross-region replication · X-Ray cost tuning at scale · response
caching for read GETs · authorizer result-cache TTL.

---

## TIER 4 — Deliberate deviations (skip; document as intentional)

- **CMK on DynamoDB/S3** — AWS-managed keys adequate (no regulated PII / GDPR duty). Skip.
- **Global Tables** — no multi-region requirement. Skip.
- **Field-level PII encryption / DSAR tooling / residency partitioning** — not owed. Skip.

---

## TRACK D — DB best-practice program (the "do it once" single-table work)

Separate multi-week track (LOE gated on the read-only recon). Sequence:
1. **Seams (on-ramp):** TableRegistry single key-authority (ends env-var precedence) ·
   `ValidationException` surfacing · god-class split by entity · error taxonomy.
2. **Single-table `core`** (full design now in `db-upgrade-priorities.md`): `PK=USER#{sub}`;
   CV at USER level (`CV#{cvId}`, referenced by `cv_id`, never copied); per-app artifacts
   `APP#{appId}#ARTIFACT#{TYPE}#v{n}` (version in SK); gap `APP#{appId}#GAPRESP#{qId}`;
   app hub `APP#{appId}`. `CoreRepository` = **sole key-builder** (DRY at the code layer, not
   storage) · edits persist via conditional `UpdateItem` on `version` (= the 409 contract) ·
   `TransactWriteItems` for multi-item invariants · **GSI-cardinality rule: every GSI PK must be
   user-/high-cardinality-scoped or sparse — no `STATUS#{status}` GSI PK** · schema-enforced TTL ·
   connection reuse. **Stays OUT of `core`:** `idempotency`, `llm-cache`, `company-research-cache`.
3. **Migration** (§18.4 expand→dual-write→backfill→dual-read→contract), reusing the
   **already-proven CR canonical-store pattern** (FE-UI-044), per entity, CV-first.
4. **Hard constraint (frontend contract):** external `application_id==job_id` and hub
   `artifact_id` round-trip **must be preserved**; internal PK is free. Status enum
   additive-only; PATCH→409; `request_id` primacy; `download_url`; `vpr_id: null`-vs-absent.

**Blocking questions — now answered (recon.py + re-council 2026-07-08):** live key-schema set +
drift counts confirmed (active schema deployed; 3-schema drift physically present) · data volume
tiny (backfill = hours) · cutover = **zero-downtime** (online expand→contract).

**Re-council verdict (2026-07-08 — `council-output.md`, same-model panel, acceptance-gate passed):**
- **HS2 — is `core` committed?** → **STAGED-COMMITTED / GATED.** The seams (step 1: single
  key-authority, `ValidationException`, god-class split, error taxonomy) + retire-PII-key + stop
  dual-key CV write are **committed** and capture the correctness/DRY/isolation value at the code
  layer. The **physical single-table collapse (DB-H8 / #48) is a DEFERRED wave behind a go/no-go
  gate** (trigger = a measured need, e.g. bootstrap-latency SLA or post-seams drift) — **NOT a
  launch blocker.** 5 of 6 lenses (incl. the double-weight Data-architect conceding) agree; Cost &
  Delivery-risk dissent hardest that the collapse is not cost-justified at this scale.
- **HS1 — identity keying** → key `core` on an **internal immutable surrogate `user_id`** (resolve
  one-or-many `cognito_sub`→`user_id` at the edge), driven by the planned social IdP; flip to raw
  `sub` only if social IdP is definitively dropped. Decide before backfill (re-keying a populated
  table is the risk to avoid).
- **HS3 — knowledge base** → **DROP** the dead table + plumbing now (empty, `userEmail` PII PK,
  two conflicting designs); re-introduce later on a non-PII key only if the feature is committed.
- **HS4 — cutover/retention** → no downtime; **gate on RETAIN + deletion-protection + a fresh
  on-demand backup + PITR 7d→35d on PII tables** before any contract step.

**Net register delta (2026-07-08): no launch-blocker severity/priority/effort moved.** The doc
updates enrich the `core` design (SK layout, GSI rule, edit-write pattern, DRY-at-code-layer) and
resolve open questions (deployed schema, jobs/apps subsumed by `core`, SNS unsubscribed); the only
new scoping change is the explicit **gating** of the physical collapse behind a go/no-go.
