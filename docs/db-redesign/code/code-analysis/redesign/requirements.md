# CareerVP — Requirements (mapped to features + all backend resources)

**Purpose:** the requirements that specs and tests will satisfy. Functional requirements
(FR) map to features in `features.md`; non-functional requirements (NFR) map to the
best-practice guide (§) and `findings-register.md` (#). A resource-coverage matrix at the
end proves every backend resource is governed. Verified against live dev (2026-07-04; re-verified 2026-07-08).

Priority: **H/M/L** (no S). Effort: **Lo/Md/Hi**.

---

## 1. Functional requirements (FR) — by feature domain

Each FR is a behavior the system MUST preserve or provide. "Contract" = frontend-visible
(see coverage-matrix §2); breaking it breaks the UI.

### Identity & Access (A)
- **FR-A1** Register/login/refresh/logout via Cognito; issue JWT (access 1h / refresh 30d). *Res: auth-api L, Cog pool.*
- **FR-A2** Every non-public route authorized at the edge by validated JWT claims only. **No client-supplied identity fallback.** *Res: API GW authorizer, authorizer L.* (Contract: 401 semantics.)
- **FR-A3** Every data read/write scoped to the authenticated principal; a foreign id MUST NOT return another user's data. *Res: all handlers + all DDB.* (Council 2026-07-08 HS1: the internal principal is a **surrogate `user_id`** — resolve one-or-many Cognito `sub`→`user_id` at the edge — to survive the planned social IdP; this becomes the `core` PK.)
- **FR-A4** Get/update PROFILE. *Res: user-api L, users DDB.* (Contract: `id,user_id,email,name`.)

### CV (B)
- **FR-B1** Upload PDF/DOCX/TXT → parse → persist CV (S3 object + metadata). *Res: cv-upload/cv-parser L, cvs bucket, cvs DDB, Anthropic.* (Contract: `cv_id,status,parsed_data`.)
- **FR-B2** List/fetch/delete CVs; default CV = first of list. *Res: user-api L, cvs/users DDB.* (Contract: `cvs[].{cv_id,full_name}`.)

### Job & Application (C)
- **FR-C1** Create/list/fetch jobs with URL validation + trial gate. *Res: job-api L, jobs DDB.* (Contract: `/jobs/{id}` renames `role_title→title`, `company→company_name`.)
- **FR-C2** Serve the application hub: `application.{state,is_finalized,…}`, `artifacts.{type}.{status,artifact_id}`, `gap_analysis`. *Res: application L, applications DDB.* (Contract: **linchpin** — status enum, `artifact_id`.)
- **FR-C3** `application_id == job_id` externally; each artifact exposes a **stored, resolvable** `artifact_id` that the status/patch/cancel endpoints accept. *Res: cross-cutting.* (Contract: hard.)

### Gap (D)
- **FR-D1** Generate + score gap questions from CV×job. *Res: gap L, gap-responses DDB, Anthropic.*
- **FR-D2** Accept gap responses; on submit trigger the artifact chain when enabled. *Res: gap L, SFN.*

### Company Research (E)
- **FR-E1** Fetch/generate/cancel company research; Tavily→scrape(SSRF-guarded)→LLM; confidence gate 0.85. *Res: company-research(-worker) L, SQS, artifacts DDB, Tavily, Anthropic.* (Contract: status-envelope `completed|not_generated|failed`.)
- **FR-E2** Cross-user intel cache with split TTL. *Res: company-research-cache DDB.*

### Artifact generation (F)
- **FR-F1** Generate VPR (async, FVS≥90); status/list/cancel. *Res: vpr-submit/worker L, SQS, users DDB, vpr-results S3, Anthropic(Sonnet).* (Contract: `request_id`; `result.*` + `download_url`; `status:expired`.)
- **FR-F2/F3/F4** Generate tailored-CV / cover-letter / interview-prep (async, FVS); status/list/cancel/**PATCH with optimistic 409**. *Res: respective workers, SQS/DDB-stream, artifacts DDB, Anthropic(Haiku).* (Contract: `version`/`updated_at`/409; nested `result` shapes; `vpr_id` incl. `null`-vs-absent.)
- **FR-F5** FVS gate blocks sub-threshold artifacts. *Res: fvs_validator.*

### AI assist / Export / KB (G/J/K)
- **FR-G1** Field rewrite with server-resolved context; no credit. *Res: ai-assist L, Anthropic.* (Contract: `generated_markdown`.)
- **FR-J1** Export artifact to DOCX + presigned URL (PDF→501). *Res: export L, S3.* (Contract: `download_url`.)
- **FR-K1** KB store/query. *Res: (currently unwired).* **Council 2026-07-08 HS3: DROP the dead table + plumbing now** (empty, `userEmail` PII PK); re-introduce later on a non-PII key (`sub`/`user_id`) only if the cross-application-memory feature is committed.

### Orchestration (H)
- **FR-H1** Resolver returns `ready`/`upstream_required`/`dependency_generating` correctly against the **real** artifact home. *Res: resolver, all artifact DDB.*
- **FR-H2** Chain executes CR→VPR→CVTailoring→{CL∥IP} with per-state retry/catch and **task-token timeouts on every task**. *Res: SFN, SQS, failure L's.*
- **FR-H3** Async submit→SQS→worker; workers report partial-batch failures; poison→DLQ. *Res: workers, SQS+DLQ.*
- **FR-H4** Cancel in-flight generation; clear chain lock deterministically. *Res: cancellation, SFN.*
- **FR-H5** Hourly cleanup deletes only orphaned/cancelled artifacts, never a live or foreign one. *Res: cleanup L, EB, S3.*

### Billing (I)
- **FR-I1** Checkout/portal sessions. *Res: billing L, payment provider.*
- **FR-I2** Webhook applies subscription changes **idempotently** (replay-safe on provider event id). *Res: billing L, users DDB, idempotency DDB.*
- **FR-I3** Nightly reconcile runs (fix the entrypoint) and corrects drift. *Res: billing-reconcile L, EB, users DDB, payment provider.*
- **FR-I4** Enforce trial/quota server-side with **conditional/transactional** credit consume. *Res: trial/quota services, users DDB.*

### LLM infra (L) / Ops (M)
- **FR-L1** Route STRATEGIC→Sonnet / TEMPLATE→Haiku; cache responses; circuit-break on provider failure; **meter real token usage**. *Res: llm_client, llm-cache DDB, Anthropic, CloudWatch.*
- **FR-M1** Health + client error telemetry. *Res: health/error-report L.*

---

## 2. Non-functional requirements (NFR) — cross-cutting, by pillar

Each NFR governs ALL applicable resources; cites guide § and finding #.

### Security (§7,§8,§9)
- **NFR-SEC-1 (H)** JWT-only identity; retire self-managed RS256; remove `x-user-id` + `AUTHORIZER_DISABLED`. §8 · #4. *All handlers, authorizer.*
- **NFR-SEC-2 (H)** No IDOR: owner-vs-`sub` check on every id-addressed read. §8 · #5. *All handlers/DDB.*
- **NFR-SEC-3 (H)** No secrets in Lambda env — JWT keys via SSM path fetched at runtime (as Anthropic/Tavily already are). §9 · #6 (confirmed: 6 fns). *auth/user/job/cv fns, SSM.*
- **NFR-SEC-4 (H)** One execution role per function; ARN- + env-suffix-scoped; no shared mega-role (critical in this **shared account**). §7,§18.1 · #9. *All L, IAM.*
- **NFR-SEC-5 (H)** WAF in every env, with a **rate-based rule**, attached to API GW (and CloudFront). §4,§9 · #11. *WAF, API GW, CloudFront.*
- **NFR-SEC-6 (H)** Cognito MFA available + advanced-security/ATP on; password ≥12 + symbols. §8 · #7 (confirmed MFA OFF). *Cog.*
- **NFR-SEC-7 (M)** CORS locked to known origins (API GW + CV bucket, currently `*`). §4,§6 · #8,#10. *API GW, cvs bucket.*
- **NFR-SEC-8 (M)** Personal-data export/delete fans across all tables + S3. §9. *All DDB/S3.*
- **NFR-SEC-9 (M)** Prompt-injection delimiting + XSS-encode generated artifacts; preserve SSRF guard. §9. *artifact L's.*

### Data safety (§2,§5.4)
- **NFR-DATA-1 (H)** `RETAIN` + `deletion_protection` on every table + bucket (incl. backups). §2 · #12,#13 (confirmed FALSE on all 10 tables). *All DDB/S3.*
- **NFR-DATA-2 (M)** Scheduled on-demand DynamoDB backups before risky migrations; backups bucket RETAIN. §5.4 · register T2. *DDB, backups bucket.*
- **NFR-DATA-3 (M)** PITR remains ENABLED — keep; extend **7d→35d on PII tables** (`idempotency` already 35d; `llm-cache` PITR off in dev — rebuildable, fine). §5.4. *All DDB.* (re-verified 2026-07-08.)

### Reliability (§3.3,§10,§15)
- **NFR-REL-1 (H)** `@idempotent` on billing + every at-least-once worker, keyed on stable business id. §3.3 · #14 (idempotency table empty). *billing/worker L, idempotency DDB.*
- **NFR-REL-2 (H)** SQS `ReportBatchItemFailures` on all workers; visibility ≥6× fn timeout; every DLQ has depth alarm + reaper/replay. §10 · #17,#18. *SQS, workers.*
- **NFR-REL-3 (H)** `max_concurrency` on AI/payment workers; reserved concurrency on money-path + auth fns. §3.3 · #16 (confirmed 0/31). *All L.*
- **NFR-REL-4 (H)** `retry_attempts>0` on async invoke only after idempotency lands. §3.3 · #19. *Async L.*
- **NFR-REL-5 (M)** Task-token **HeartbeatSeconds** on every SFN task (VPR/CVTailoring lack it — confirmed) + timeouts. §10. *SFN.*
- **NFR-REL-6 (M)** EventBridge rule targets have a DLQ. §10. *EB.*
- **NFR-REL-7 (H)** Transactions (`TransactWriteItems`) for multi-item invariants (create-app + consume-quota); atomicity fix for E7. §5.3 · #15. *DDB.*

### Scalability / performance (§4,§5)
- **NFR-SCALE-1 (H)** API throttle sized to target (raise from 2 rps); per-route limits. §4 · #20 (confirmed live). *API GW.*
- **NFR-SCALE-2 (H)** No Scan on any request path (billing customer-id lookup, CR, cover-letter). §5.1 · #15. *DDB.*
- **NFR-SCALE-3 (M)** Access-pattern doc as the schema contract; item-collection modeling; minimized GSI projections. §5.1,§5.2. *DDB.*
- **NFR-SCALE-4 (M)** Request validators/models at the API edge. §4. *API GW.*

### Cost / margin (§13)
- **NFR-COST-1 (H)** Real token metering (retire `len/4`); cost-per-app metric + anomaly alarm. §12,§13 · #L4. *CloudWatch, Anthropic.*
- **NFR-COST-2 (M)** Prompt-cache breakpoints; bound artifact output `max_tokens`; bound Tavily input. §13. *artifact L's.*
- **NFR-COST-3 (M)** App-wide tagging (`Tags.of(app)`: Environment/CostCenter) + Budgets/Cost-Anomaly. §2,§13. *all.*
- **NFR-COST-4 (L)** ARM64; GSI `ALL`→minimized; remove dead resources (knowledge table, `/api/*` if dropped). §13. *L, DDB, API GW.*

### Observability (§12)
- **NFR-OBS-1 (H)** Alarms route to a **subscribed** SNS topic/on-call. §12 · #21 (confirmed 0 subs). *SNS, CloudWatch.*
- **NFR-OBS-2 (M)** Log retention 30–90d (from 1d); alarm coverage: Lambda errors/throttles/p99, DLQ depth ×all, API 4xx, DynamoDB throttles ×all tables, SFN failures, concurrency-near-limit; fix dashboard flag. §12. *CloudWatch.*
- **NFR-OBS-3 (L)** Synthetic canary on `/health`; correlation-ID propagation. §12. *CloudWatch.*

### Deployability / correctness (§14,§18)
- **NFR-DEP-1 (H)** OIDC everywhere in CI (remove long-lived keys in `cdk-diff`). §14 · #22. *CI/CD.*
- **NFR-DEP-2 (H)** Lambda alias/version + CodeDeploy canary + auto-rollback for prod deploys. §14,§18.3 · #23. *All L, CI/CD.*
- **NFR-DEP-3 (H)** Fix broken deployed entrypoints (billing-reconcile Handler) + dead-stack/entrypoint mismatches. §2 · #2. *billing-reconcile L, IaC.*
- **NFR-DEP-4 (M)** CI gates enforced unmasked: ruff, mypy, tests, cdk synth/diff, Checkov, **secret scan**; `cdk diff` = zero stateful replacements. §14. *CI/CD.*
- **NFR-DEP-5 (M)** Fix the autouse resolver test stub; enable branch coverage; real-key-schema moto; whole-chain + replay-same-event + cross-tenant tests. §14 · coverage-matrix §4. *tests.*

---

## 3. Resource coverage matrix (every backend resource → governing requirements)

| Resource (live dev) | Governing requirements |
|---|---|
| **API Gateway** `careervp-core-api-dev` | FR-A2 · NFR-SEC-5,7 · SCALE-1,4 · OBS-2 |
| **Cognito** pool `careervp-users-dev` | FR-A1 · NFR-SEC-1,6 |
| **Lambda** (31 fns) | all FR · NFR-SEC-3,4 · REL-1,3,4 · DEP-2 · COST-4 |
| **DDB users** (908) | FR-A4,B2,C2,F1,I2,I4 · NFR-DATA-1 · SCALE-2,3 · REL-7 |
| **DDB artifacts** (221) | FR-E1,F2,F3,F4,H1 · DATA-1 · SCALE-2,3 |
| **DDB jobs** (144) | FR-C1,H2 · DATA-1 · SEC-2 |
| **DDB applications** (9) | FR-C2,H1,H4 · DATA-1 |
| **DDB cvs** (6) | FR-B1,B2 · DATA-1 |
| **DDB gap-responses** (16) | FR-D1,D2 · DATA-1 |
| **DDB idempotency** (0) | FR-I2,H3 · REL-1 |
| **DDB llm-cache** (0; was 11, TTL-expired; PITR off in dev) | FR-L1 · COST-1,2 |
| **DDB company-research-cache** (2) | FR-E2 · COST-2 |
| **DDB knowledge** (0, dead) | FR-K1 (decide keep/drop) · COST-4 |
| **S3 cvs / vpr-results / artifacts** | FR-B1,F1,J1 · NFR-DATA-1,2 · SEC-7 |
| **S3 backups / logs / static** | NFR-DATA-1,2 · OBS-2 |
| **SQS** (vpr, cover-letter, interview-prep, company-research, cv-upload, gap +DLQs) | FR-H3 · NFR-REL-2,3 |
| **Step Functions** artifact-chain | FR-H2,H4 · NFR-REL-5 |
| **EventBridge** (cleanup 1h, reconcile 02:00) | FR-H5,I3 · NFR-REL-6 · DEP-3 |
| **SNS** monitoring-topic | NFR-OBS-1 |
| **WAF** | NFR-SEC-5 |
| **KMS** (logs, SNS, SQS CMKs) | NFR-SEC-4 (wildcard grants) |
| **SSM Parameter Store** | NFR-SEC-3 |
| **CloudWatch** (logs/metrics/alarms/dashboards) | NFR-OBS-1,2,3 · COST-1 |
| **X-Ray** | NFR-OBS-3 · COST-4 |
| **CI/CD** (.github, pre-commit) | NFR-DEP-1,2,4,5 |
| **External:** Anthropic / Tavily / payment | FR-B1,E1,F1-4,G1,I1-3 · COST-1,2 · REL-1,3 |
