# CareerVP — Feature Catalog (definition + significance)

**Purpose:** the authoritative, categorized inventory of what the platform *does*, so
requirements, specs, and tests map to a stable feature list. Derived from the live API
surface (dev, 61 resources), the async/SFN surface, the frontend touchpoints, and code.
Status flags: 🟢 works · 🔴 broken today · 🟡 partial/at-risk · ⚫ dead/unwired.

Legend for resources: L=Lambda · DDB=DynamoDB table · S3 · SQS · SFN=Step Functions ·
EB=EventBridge · Cog=Cognito · ext=external API.

---

## A. Identity & Access
| Feature | Definition | Significance | Endpoints / resources | Status |
|---|---|---|---|---|
| A1 Registration/Login/Refresh/Logout | Cognito-backed account creation + JWT issuance/refresh/revoke | Front door; every other feature depends on a trusted identity | `POST /auth/*` (proxy, public at edge) · `auth-api` L · Cog pool | 🟢 |
| A2 Edge authorization | Cognito User Pools authorizer validates JWT on every non-public route | The security perimeter; without it every data feature is exposed | API GW authorizer · `api_gateway_authorizer` L | 🟡 (dual-auth: self-managed RS256 path also exists → root of #4/#6) |
| A3 Tenant isolation | Every data access scoped to the authenticated subject | Prevents cross-user data exposure (IDOR); legal/trust foundation | all handlers · all DDB | 🔴 (`x-user-id` fallback #4, IDOR `get_job` #5) |
| A4 Profile management | Read/update the user PROFILE record | User account surface | `GET/PUT /users/me` · `user-api` L · users DDB (`PROFILE` SK) | 🟢 |

## B. CV Management
| B1 CV upload & parse | Upload PDF/DOCX/TXT → S3 → LLM parse → structured CV | The seed input for the whole artifact chain | `POST /users/me/cv` · `cv-upload` L (S3-triggered) · `cv-parser` L · cvs bucket · cvs DDB · ext:Anthropic(Haiku) | 🟢 |
| B2 CV list / fetch / delete | Manage stored CVs; default CV = first in list | Users maintain multiple CVs; generators consume the default | `GET/DELETE /users/me/cv[/{id}]` · users/cvs DDB · cvs bucket | 🟡 (dual-key `pk/sk`+`userId/cvId` write, E2) |
| B3 CV summarization | Compress CVs >5k tokens for prompt use | Bounds LLM input cost (margin) | `cv_summarizer` logic · ext:Anthropic | 🟢 |

## C. Job & Application Lifecycle
| C1 Job create/list/fetch | Create a target job (title/company/URL/description), with URL validation + trial gate | Defines the target every artifact is tailored to | `POST/GET /jobs`, `GET /jobs/{id}` · `job-api` L · jobs DDB (144 items) | 🟢 |
| C2 Application state | Per-application state machine + `artifact_statuses` map + chain-execution lock | The hub the frontend renders; tracks the artifact graph | `GET /applications/{id}` · `application-handler` L · applications DDB (9) | 🟡 (stale `RUNNING` lock, dormant `_is_stale`) |
| C3 Identifier model | `application_id == job_id`; artifacts carry a stored `artifact_id` | **Load-bearing frontend contract** (round-trips artifact_id) | (cross-cutting) | 🔴 (3-schema/3-id defect #1) |

## D. Gap Analysis
| D1 Gap question generation | LLM-generate + score gap questions from CV×job | Elicits the evidence that powers VPR quality | `POST/GET /jobs/{id}/gap-questions` · `gap` L · gap-responses DDB · ext:Anthropic | 🟢 |
| D2 Gap responses → impact statements | Collect answers; on submit, trigger the artifact chain | The chain trigger; converts answers to reusable evidence | `POST /jobs/{id}/gap-responses` · `gap` L · SFN start | 🟢 |

## E. Company Research
| E1 Company research generation | Tavily web search → scrape (SSRF-guarded) → LLM structuring; confidence gate 0.85 | Grounds VPR/cover-letter in real company intel | `POST /company-research/fetch`, `GET /company-research/{jobId}` · `company-research-worker` L · SQS · artifacts DDB · ext:Tavily+Anthropic(Sonnet) | 🟢 |
| E2 Cross-user intel cache | Split-TTL cache (183d profile / 120d news) reused across users | Cost lever: skips redundant Tavily+LLM runs | company-research-cache DDB (2) | 🟢 |
| E3 CR canonical store (migration) | Dual-write/backfill of CR from users→artifacts table | The proven migration pattern for Track D | artifacts DDB · FE-UI-044 | 🟡 (partial migration in progress) |

## F. AI Artifact Generation
| F1 VPR (Value Proposition Report) | 6-stage Sonnet pipeline (analyze→extract→synthesize→self-correct→generate→meta-eval), FVS-gated | The hub artifact (74% of AI spend); all downstream depend on it | `POST /vpr/generate`, `GET /vpr/{id}/status`, `/vprs`, `/cancel` · `vpr-submit`/`vpr-worker` L · SQS · users DDB(`ARTIFACT#VPR#`) · vpr-results S3 · ext:Anthropic(Sonnet) | 🟢 |
| F2 Tailored CV | Multi-pass ATS keyword optimization + self-correct (≤3), Haiku, FVS; editable | Core deliverable; ATS score + editable sections | `POST /cv-tailoring/generate`, status/list/cancel/PATCH/DELETE · `cv-tailor-worker` L (DDB-stream) · artifacts DDB · ext:Anthropic(Haiku) | 🟢 |
| F3 Cover Letter | 220–350w paragraphs, Haiku, FVS; editable w/ autosave | Core deliverable | `POST /cover-letter/generate`, status/list/cancel/PATCH · `cover-letter-worker` L · SQS · artifacts DDB | 🔴 (fails today via #1) |
| F4 Interview Prep | ≤15 Q&A (STAR), questions-to-ask, checklist, salary guidance; per-question autosave | Core deliverable | `POST /interview-prep/generate`, status/list/cancel/PATCH · `interview-prep-worker` L · SQS · artifacts DDB | 🔴 (fails today via #1) |
| F5 FVS validation | Fact-verification + anti-AI-pattern scoring, min 90/100, gates F1–F3 | Quality/trust gate; prevents hallucinated output | `fvs_validator` logic (cross-cutting) | 🟢 |

## G. AI Assist
| G1 Field rewrite | Field-scoped AI rewrite with server-resolved cross-artifact context; no credit; 25s cap | In-editor polish across all artifact types | `POST /ai/assist` · `ai-assist` L (nested stack) · ext:Anthropic | 🟢 |

## H. Orchestration & Async
| H1 Dependency resolver | Pure resolver: `ready`/`upstream_required`(409)/`dependency_generating`(202) over the artifact graph | Prevents generating an artifact before its inputs exist | `artifact_dependency_resolver` logic | 🟡 (gate reads wrong table #1) |
| H2 Step Functions chain | CR→VPR→(choice)→CVTailoring→{CoverLetter∥InterviewPrep}, task-token + heartbeats | Orchestrates the full multi-artifact generation | SFN `careervp-artifact-chain-*` · SQS · failure L's | 🟡 (StartVPR/StartCVTailoring **no heartbeat** → can hang 2h) |
| H3 Submit→SQS→worker | Per-artifact async pattern (standalone path) | Keeps expensive AI off the API path; absorbs spikes | `*-submit`/`*-worker` L · SQS(+DLQ) | 🟡 (no partial-batch, no reapers) |
| H4 Cancellation | Cancel in-flight generation; `StopExecution`; worker CANCELLED guards | User control; stops wasted AI spend | `*/cancel` · `cancellation` logic · SFN | 🟢 |
| H5 Orphan cleanup reaper | Hourly EB sweep; deletes orphaned/cancelled artifacts (S3) | Cost/hygiene; prevents storage growth | EB rate(1h) · `artifact-cleanup` L (destructive S3 delete) | 🟢 |
| H6 DLQ reaper | Marks orphaned VPR jobs FAILED | Failure recovery | `vpr-dlq-handler` L | 🟡 (only VPR; 8 other DLQs unreaped) |

## I. Billing & Subscription
| I1 Checkout / portal | Create checkout + customer-portal sessions | Revenue entry; paid-launch critical | `POST /billing/checkout`,`/billing/portal` (proxy) · `billing` L · ext:payment | 🟡 (placeholder provider only) |
| I2 Webhook | Provider webhook, self-verifies signature, dual-secret rotation | Applies subscription state changes | `POST /billing/webhook` (public) · `billing` L | 🔴 (no `@idempotent` → double-apply risk #14) |
| I3 Reconcile | Nightly reconcile subscriptions vs provider | Corrects drift between provider and DB | EB cron(02:00) · `billing-reconcile` L | 🔴 (deployed Handler `.handler`≠source `lambda_handler` → fails at invoke #2) |
| I4 Trial & quota | 14-day / 3-application trial; atomic credit consume; access = sub OR trial | Monetization gate; server-side enforcement | `trial_service`/`quota_service` · users DDB · `GET /users/me/usage`,`/subscription` | 🟡 (verify conditional-write atomicity #15) |

## J. Export
| J1 Artifact export | DOCX (python-docx) to S3 + presigned URL; PDF stubbed 501 | Users take deliverables offline | `GET /jobs/{id}/artifacts/{type}/export` · `export` L · S3 | 🟢 (PDF pending) |

## K. Knowledge Base
| K1 KB entries | Store/query gap-response + company-research knowledge | Reuse of prior evidence | `GET /knowledge-base` (served by `company-research` L) | ⚫ (`knowledge` table empty; `knowledge_base_handler` unwired) — **Council 2026-07-08: DROP now** (`userEmail` PII PK); re-add later on a non-PII key if committed |

## L. LLM Infrastructure
| L1 Model router | STRATEGIC→Sonnet, TEMPLATE→Haiku | Margin lever: right model per task | `llm_client` logic · ext:Anthropic | 🟡 (routing measured only via `len/4` estimate) |
| L2 Response cache | DynamoDB `llm-cache` (7d TTL) | Cost lever: avoids repaying tokens | llm-cache DDB (0; was 11, TTL-expired; PITR off in dev) | 🟢 |
| L3 Circuit breaker | 5 fails/60s → open | Resilience against provider outage | `circuit_breaker` logic | 🟢 (32% test coverage) |
| L4 Cost metering | CloudWatch cost metric ($0.25/run alert) | Margin visibility | CloudWatch | 🟡 (token count estimated, not real) |

## M. Platform & Ops
| M1 Health | Static + dependency health | Uptime signal / canary target | `GET /health` (public) · `health` L | 🟢 |
| M2 Client error telemetry | Ingest FE error reports | Frontend observability | `POST /errors` (public) · `error-report` L | 🟢 |
| M3 Observability | Logs/metrics/traces/alarms | "Is it healthy? why failed? what cost?" | CloudWatch · SNS · X-Ray | 🔴 (SNS 0 subscribers; 1-day logs; alarm gaps) |
| M4 Edge protection | WAF managed rules on API GW | Abuse/attack mitigation | WAF | 🔴 (prod-only, no rate rule, not attached in dev; no real prod env) |
| M5 Legacy `/api/*` surface | Older path namespace | Must decide: carry or drop at prod | staging API only (7 paths) | ⚫ (staging-only) |
