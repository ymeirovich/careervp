# CareerVP — Project Scope Lock (Contract)

- **Version:** 2.2.0
- **Frozen:** 2026-07-05 (v1.0.0) · last amended 2026-07-11 (v2.1.1 — dev ACM cert ISSUED; v2.1.0 human decisions on O-2/O-7/O-8 + recon refresh; v2.0.0 eval-council conditions)
- **Code anchor:** `github.com/ymeirovich/careervp` @ commit `4f7c294` (the analysis commit)
- **Live anchor:** AWS acct `788159322332`, `us-east-1`, `dev` stage (no `prod` exists yet — go-live is a first deploy)
- **Machine-checkable twin:** [`project-scope-lock.yaml`](./project-scope-lock.yaml) — same clause IDs; the periodic diff runs against the YAML.
- **Status:** IMMUTABLE. Change only via the amendment process in §0.3.

---

## 0. Control

### 0.1 Purpose
This document is the **single immutable contract** that keeps specs, tests, and implementation true across a long development series. Specs and tests are validated against it; drift from it is a defect in the spec/test, not in this document. It is **exhaustive** (every known feature and finding is listed and prioritized) and describes a **complete path to production**, robust to partially-implemented work.

### 0.2 Authority hierarchy (what wins on conflict)
1. **This document** (and its YAML twin) — wins over everything below on any conflict.
2. `handoff.md` — locked post-council decisions.
3. `careervp-architecture-v2.md` (arch truth) + `careervp-architecture-deepdive.md` (companion). **`careervparchitecture.md` (v1) is DEPRECATED — never cite.**
4. `findings-register.md` (scope), `coverage-matrix.md §2` (frontend contract), `redesign-runbook.md` (migration mechanics).
5. `requirements.md`, `features.md`, `db-upgrade-priorities.md`.
6. **Live truth** (`recon.py` output, code @ `4f7c294`) supersedes any static/aspirational claim — e.g. the best-practice guide's inline "✅ repo already does this" annotations are **aspirational and often false**; trust `recon.py` + code.
7. **Non-authoritative / do-not-build-from:** `docs/features/*`, `docs/swagger/careervp-api-v1.yaml` (drifted). The frontend contract oracle = `src/frontend/` code, not any spec doc.

### 0.3 Amendment process (immutability)
- No clause changes silently. Every change: bump `Version`, add a dated row to §12 Change Log, and update both MD and YAML in the same commit.
- Each clause is tagged `IMMUTABLE` (invariant — a violation is always a defect), `TARGET` (a state to reach), or `OPEN` (undecided — must be resolved before its dependent spec is written; never guessed).
- `current_state` vs `target` are recorded separately so partial implementation shows as partial, never as scope loss.

**Principle:** the contract is immutable to **drift** (silent, unversioned change), not to **learning**. Amendments are welcome; unrecorded changes are the defect. The contract changes at the *speed of decisions*, not the speed of code. Map = this contract; trail markers = specs; a washed-out trail → re-mark the trail (fix the spec), only re-draw the map when the destination or a hard constraint changed.

**Semver discipline:**
- **PATCH** (x.x.+1) — clarification / typo / `current_state` refresh. No scope change.
- **MINOR** (x.+1.0) — add a clause; refine a `TARGET`; resolve an `OPEN`.
- **MAJOR** (+1.0.0) — change an `IMMUTABLE` invariant or locked decision; drop a feature; break a frontend-contract item.

**Deviation → amendment loop (built into the spec/test/impl process — see execution-plan "Deviation & amendment handling"):** when a step's subagent cannot satisfy a clause as written, or live truth contradicts a `current_state`:
1. **Stop at the clause — never silently deviate.**
2. **Emit an Amendment Proposal:** `{clause_id, tag, what changed, why + evidence cite, semver level, affected specs/tests}`.
3. **Human validates and confirms** — no auto-apply.
4. **Update both twins in the same commit** + §12 change-log row + version bump.
5. **Propagate** to dependent specs/tests, then re-run `scope-diff.py`.
- **Adversarial review required** before committing any amendment to an `IMMUTABLE` invariant, locked decision, or frontend-contract item (§9.2).

**Contract self-protection (mechanical, not disciplinary — v2.0.0):** the two contract files (`project-scope-lock.md` + `.yaml`) are **write-protected from agent/orchestrator sessions** — an agent may *propose* an amendment but may not edit these files. **Amendments land only via a human-executed commit.** A CI check rejects any diff to either file that lacks: a §12 change-log row, a `Version` bump, twin-sync (both files changed together), and a human-signed approval trailer. *(Rationale: every downstream net — `scope-diff.py`, the oracle, wave gates — audits the code **against this contract**. If a session can silently edit the contract, `scope-diff.py` then enforces drift instead of preventing it — a silent total-loss of the "requirements can't rot" guarantee. The plan mechanized deploy discipline (P-27/P-28) after learning prompt-text guardrails don't bind agents; its own constitution gets the same treatment.)*

**Anti-patterns (hard-rejected — §9.3):** editing a *spec* to match the *code* instead of amending the contract when a decision changed · amending the contract *retroactively to rubber-stamp* what got built · weakening a test to pass. Amendments must cite evidence **and** a decision rationale, never "matches code."

### 0.4 Canonical ID space (kills the 3-namespace drift)
Every backlog item has ONE canonical ID (`P-##`, `D-##`, `Q-##`, `T-##`, `F-##`, `X-##`). The `crosswalk` field maps each to its legacy IDs (`finding #`, `NFR-*`, `DB-*`) so the three parallel namespaces collapse into one. LOE = `Lo/Md/Hi`. Priority tier = `T1/T2/T3/OUT`.

---

## 1. Fixed constraints (the physics — IMMUTABLE)
| ID | Constraint |
|---|---|
| C-1 | Scale ceiling **< 10k concurrent**. Design for it; do not over-engineer past it. |
| C-2 | **> 70% profit margin** maintained. LLM tokens are the lever, not infra. |
| C-3 | **Solo maintainer** — penalize big-bang / high-coordination work; favor incremental, reversible steps. |
| C-4 | **DynamoDB is kept** (decision closed — not re-litigated). |
| C-5 | Security-conscious, **no GDPR gold-plating**; lightweight DSAR (export/delete) only. |
| C-6 | **Backend + API contract only.** Frontend out of scope except where a change alters the API request/response contract. |
| C-7 | **No `prod` exists** — going live is a genuine first prod deploy. All work targets `dev` (the proving ground) until certified (§7.4). |
| C-8 | **Shared personal AWS account** (`788159322332`) — amplified IAM blast radius; `{env}`-scoped everything. |

## 2. Locked decisions (do-not-re-litigate — IMMUTABLE)
| ID | Decision |
|---|---|
| L-1 | **Identity/tenant key = internal immutable surrogate `user_id`** (own UUID). Resolve one-or-many Cognito `sub`s (Google/Facebook/password, linked by verified email) → `user_id` at the edge. *(Supersedes the earlier "key by Cognito sub"; chosen because social IdP is on the roadmap and this avoids re-keying the DB later.)* |
| L-2 | **Cognito-only auth** — retire the self-managed RS256 path; identity derives **only** from validated JWT claims (never a header/body field). Social IdP (Google/Facebook) planned; account-link by verified email. |
| L-3 | **Single-table `core` = STAGED-COMMITTED.** Do the decoupling seams first (one key-authority repository, kill the 3-schema drift, stop dual-key CV writes, retire the PII PK) → yields a production-ready best-practice data layer; **then** the full physical `core` collapse as a committed later wave with a go/no-go metric gate. |
| L-4 | **Billing live = launch-critical** (paid launch). |
| L-5 | **Company Research runs FIRST**, on new-application submit, **to completion — or a documented degraded fallback** — **then** gap analysis; CR is reused by all downstream artifacts. Requires reordering the artifact chain to `CR → gap → vpr → {cv, cover, interview}`. *(Failure semantics — refines the decision, does not reverse CR-first ordering/reuse: CR is a **soft-blocking** dependency. On CR `failed`/timeout > N seconds, gap proceeds degraded with an empty CR block — the prompt builder already renders nothing for an absent CR block (safe no-op) — and the application status surfaces CR's failure additively. Prevents a Tavily/CR-worker outage from stalling every submit behind a dead upstream.)* **Adversarial-review conditions (mandatory, close the C-2 + contract holes):** (a) **a degraded (empty-CR) gap MUST route to Haiku, never Sonnet** — L-6 pays Sonnet for the CR-fed quality lift, so running Strategic on empty inputs is the system's worst cost/quality trade and fires on CR's known reliability wart; gate Sonnet on a non-empty CR block. (b) `N` ships with a **concrete default** (proposed `N=180s`, matching the SFN heartbeat) — O-7 tunes it, it does not gate the constant's existence. (c) the "additive" status signal MUST name the exact enum value / degraded field and the F-01 oracle must confirm the frontend tolerates it (a fixed enum has no free room — "additive" is only proven for the prompt builder, not the status contract). **Semver: MAJOR (human-ruled 2026-07-11).** The adversarial refuter argued that relaxing "to completion" weakens a guarantee downstream code consumed; the human agreed and ruled this **MAJOR** — L-5's completion guarantee is **intentionally and explicitly relaxed** from "always to completion" to "to completion *or* documented degraded fallback (soft-blocking)". CR-first *ordering* and *reuse* remain locked; only the completion guarantee changed. This locked-decision change drove the v2.0.0 release. |
| L-6 | **Gap Analysis → Sonnet (Strategic)**, gated on fixing its inputs first (real CV + CR). *(Approval stands; the decision is not reversed. Refinement: it gains a **post-Q-10 measured-margin check** — once real metering lands, measured Sonnet cost-per-gap must keep cost-per-app within the C-2 headroom — with a **named revert lever**: the router flips gap back to Haiku via `TaskMode` config, cheap and flag-shaped. See §6.3.)* |
| L-7 | Priorities `T1/T2/T3`; effort `Lo/Md/Hi`. |

## 3. Frontend can't-break contract (IMMUTABLE) — `coverage-matrix.md §2`
The redesign is a data-layer + internal-identifier change that MUST keep API response shapes stable, **or version the route**. Internal PK is free to change; the wire contract is not.

1. `application_id == job_id` (one identifier, two names).
2. `artifact_id` is the round-tripped opaque key; a hub `artifact_id` MUST be resolvable by the status endpoint.
3. `vpr_id` = VPR's hub `artifact_id`; **CV-tailoring sends `vpr_id: null` (never omitted)** — null-vs-absent is load-bearing.
4. Status enum string-compared/unversioned (`pending|processing|completed|failed|cancelled|expired` + `not_generated`, `edited`); **changes must be additive.**
5. PATCH optimistic concurrency: echo `result.*` + `version` + `updated_at`; **HTTP 409 on stale `base_version`.**
6. `request_id` primacy (`request_id ?? job_id`).
7. Nested `result` shapes preserved (VPR/CV/IP/CL trees).
8. Presigned `download_url` + `status:'expired'` signal.
9. Existing shape polymorphism tolerated, must not worsen.
10. Error envelope (`error|message`, `classification`, `error_code`, `field`); 401 → one silent refresh-retry then sign-out.

**Oracle rule:** the authoritative contract = what `src/frontend/` actually calls + CDK `route_map` + handlers — NOT any OpenAPI/swagger doc (both are drifted).

**⚠️ Four live contract mismatches already exist** (real bugs — see F-02..F-05): VPR `download_url` missing from backend model; status enum lacks `cancelled/expired`; `vpr_id` required-non-null vs FE sends `null` (→422); error envelope nested vs FE expects flat (→`[object Object]`).

## 4. Architectural invariants (IMMUTABLE)
- Identity from validated JWT claims → `user_id` surrogate only; the DAL enforces the tenant partition key (IDOR structurally impossible); never re-fetch by a client-supplied `*_artifact_id`.
- A single **key-authority repository** is the sole key-builder; env-var table-precedence routing (`ARTIFACTS_TABLE_NAME → DYNAMODB_TABLE_NAME → TABLE_NAME`) is abolished; no new table alias.
- One typed home + one stored key per artifact type.
- Large bodies (VPR JSON, CV files) stay in **S3 with a pointer** (400KB / cost); "store rich, project lean" — storage shape ≠ prompt shape, both versioned.
- **Shared/cross-user data never lives in `core`** (partitioned by `USER#{user_id}`): Company Research cache (keyed by company), LLM cache, idempotency, **and the `sub→user_id` mapping (looked up *before* `user_id` is known, so it cannot be `USER#{user_id}`-keyed — its own small table or a `sub`-keyed GSI; see P-24)** stay separate tables.
- One IAM role per function, ARN-scoped, `{env}`-suffixed; no `Resource:"*"` where ARNs are known.
- Every SQS consumer reports `batchItemFailures`; visibility timeout **≥ 6× function timeout**; `max_concurrency` on rate-limited consumers; DLQ + depth alarm on every queue.
- All stateful resources `RETAIN` + `deletion_protection`; no PK/SK change on a live table; no template > ~400 CFN resources.
- Vectors (if built) are a derived, rebuildable, tenant-filtered index — never the system of record; a single retrieval service is the only query path.
- **Every GSI partition key is user-scoped, high-cardinality-scoped, or made sparse — never a low-cardinality `STATUS#{status}` PK** (that concentrates all completed/in-flight items on one partition; the natural-but-wrong implementation of the cleanup / in-flight query). Promoted to contract from `db-upgrade-priorities.md:41` so a fresh subagent authoring the D-H8/Q-05/`artifact_cleanup` spec sees it. *(invariant id: `gsi_pk_user_or_high_cardinality_scoped_or_sparse_never_status`)*

---

## 5. Canonical prioritized backlog (exhaustive)
> Full per-clause detail (deps, DoD, acceptance, current_state, verification) lives in the YAML twin. This is the readable index. `⟡` = belongs to both Track P and Track D.

### Track P — Production launch-blockers (T1 unless noted)
| ID | Item | LOE | Crosswalk |
|---|---|---|---|
| P-01 | Cover letter + interview prep FAIL — 3-schema / `vpr_id` routing defect ⟡ | Hi | #1, FR-F3/F4 |
| P-02 | Billing reconcile entrypoint mismatch (`Handler` ≠ `lambda_handler`) | Lo | #2, FR-I3 |
| P-03 | Map the `/api/*` surface before redesign (verify staging-only) | Lo | #3 |
| P-04 | Remove `x-user-id` header bypass + `AUTHORIZER_DISABLED` switch. **✅ Recon 2026-07-11 resolved the live-truth §3 opens and DE-RISKED this clause:** (1) **Cognito auth IS already enforced** in deployed dev — REST API `4xe2tdq8z6`, protected methods carry `COGNITO_USER_POOLS` (authorizer `j4yign` → pool `us-east-1_WiHMRqLpe`); unauthenticated `GET /jobs` returns 401. So the "flip" is **already done at the gateway** — this clause is NOT the risky enforcement flip it was feared to be. (2) **`AUTHORIZER_DISABLED` is confirmed DEAD config** — zero code readers (the only reader was removed in commit `05e6f74`, 2026-02-21); it lingers only as an env var at `api_construct.py:1720`. So the remaining work is **cleanup: delete the dead env var from CDK + remove the `x-user-id` handler fallback** (likely already unreachable behind the live authorizer — verify). The rollback story covers the fallback-removal handler change (revert = git-revert + a redeploy), NOT a nonexistent flag. **Rollback lever must match where the change lives:** an API-Gateway authorizer / method `authorizationType` change is a control-plane deploy that a Lambda-alias CodeDeploy canary does **not** roll back — the revert for it is a stage-level API-GW rollback (redeploy the prior stage/deployment). P-23's canary is the lever only for the fallback-removal *handler* change; it must be verified BEFORE the flip (P-23 resequenced into Wave 1 ahead of 1.1), and the P-04 spec must name the correct revert per artifact. **Do NOT rebuild `AUTHORIZER_DISABLED` as a lever** (re-creates the bypass). **Alarm on resolver-failure signals, not aggregate 401-rate:** a P-24 `sub→user_id` mis-resolution can present as a normal 401 (indistinguishable from token expiry) *or, worse, as a 200 serving the wrong tenant's data* — so emit a distinct authorizer-context resolution-failure metric at the P-24 resolver + a synthetic canary that asserts a known `sub` resolves to its expected `user_id`; the aggregate-401 alarm alone false-negatives a partial-population failure. Soak exit by **event coverage** (N distinct subs authenticated + all critical routes hit, with a traffic floor), not a bare ≥24h box (bump access-log retention first). **Measured RTO 2026-07-11: incremental backend redeploy ≈ 7 min (CFN update itself ~67–83s; rest is CI overhead) — the old "15–30 min" was a 2–4× overstatement.** *(The real P-26 recovery driver is the dead `api.dev.careervp.com` DNS, not stack time — see O-9.)* | Md | #4, NFR-SEC-1 |
| P-05 | IDOR — `get_job` (and peers) enforce owner/`user_id` | Md | #5, NFR-SEC-2 |
| P-06 | JWT key + webhook secret out of Lambda env → SSM SecureString/Secrets Mgr | Md | #6, NFR-SEC-3 |
| P-07 | Cognito MFA + advanced security (ATP) **+ SPA-client hardening: migrate `implicit_code_grant` → authorization-code + PKCE, and remove `COGNITO_ADMIN` from the public SPA client's OAuth scopes** (`cognito_construct.py:27,44,47` — implicit grant leaks tokens in URLs; `COGNITO_ADMIN` on a public client is a privilege-escalation primitive). Carry both as `AC-###` with an IaC assertion. **⚠️ Cross-C-6 boundary + live-lockout hazard on the 908-user pool — the spec MUST (not may):** (1) **verify before removing `COGNITO_ADMIN`** — grep `src/frontend` for `signin.user.admin` / browser-side `UpdateUserAttributes`/`ChangePassword`/`AssociateSoftwareToken` (TOTP self-enrollment uses this scope — collides with the MFA rollout); if any legit flow uses it, keep it or move the flow to a backend proxy first; (2) **dual-flow migration window** — keep both `code` and `implicit` enabled on the client, cut the frontend (`src/frontend` Amplify/OIDC `responseType`) over to code+PKCE FIRST, soak, then remove implicit; the frontend edit is a named cross-boundary deliverable with an owner (like P-26's Amplify repoint), not a silent scope expansion; (3) **MFA rolled OPTIONAL→enforced with an enrollment grace window** (forcing `ON` locks out device-less users); (4) sequence the whole flow cutover to **complete + soak before P-04** enforcement lands (stale implicit-flow tokens must not meet newly-strict auth mid-migration). | Lo | #7, NFR-SEC-6 |
| P-08 | CV bucket CORS `*` → locked origins | Lo | #8, NFR-SEC-7 |
| P-09 | One IAM role per function (retire the shared ~20-fn role; fix billing/export default roles) | Hi | #9, NFR-SEC-4 |
| P-10 | API GW CORS `ALL_ORIGINS` → allow-list | Lo | #10, NFR-SEC-7 |
| P-11 | WAF in all envs + rate-based rule | Md | #11, NFR-SEC-5 |
| P-12 | `RemovalPolicy.RETAIN` + `deletion_protection` on all tables/buckets; fix backups bucket auto-delete ⟡ | Md | #12, NFR-DATA-1, DB-H1 |
| P-13 | Remove dead `RETAIN` stacks never instantiated | Lo | #13, DB-L1 |
| P-14 | Idempotency wired on billing webhook + at-least-once workers (keyed on stable business id) | Md | #14, NFR-REL-1, DB-H5 |
| P-15 | Eliminate billing `Scan` on the money path ⟡ | Md | #15, NFR-SCALE-2, DB-H7 |
| P-16 | Reserved/`max_concurrency` bounds on rate-limited consumers | Lo | #16, NFR-REL-3 |
| P-17 | `ReportBatchItemFailures` on all SQS consumers; wire the 8 unreaped DLQs | Md | #17, NFR-REL-4 |
| P-18 | SQS visibility timeout ≥ 6× Lambda timeout | Lo | #18, NFR-REL-2 |
| P-19 | Step Functions retry/heartbeat: `MaxAttempts`/`BackoffRate`, `JitterStrategy: FULL`, `StartVPR` heartbeat | Md | #19, NFR-REL-5 |
| P-20 | Raise API throttle from 2 rps / burst 10 (self-DoS) to a real target | Lo | #20, NFR-SCALE-1 |
| P-21 | SNS alarms → subscribed on-call topic (currently 0 subscribers) | Lo | #21, NFR-OBS-1 |
| P-22 | CI/CD: replace long-lived keys in `cdk-diff.yml` with OIDC | Lo | #22, NFR-DEP-x |
| P-23 | Alias+version + CodeDeploy canary/rollback | Md | #23, NFR-DEP-x |
| P-24 | **Identity surrogate `user_id` layer** (resolve `sub`→`user_id`; social-IdP account-linking). **Spec MUST answer four architecture questions (v2.0.0 — else a latent split-tenant/SPOF bug):** (1) **resolution locus** — a shared auth layer (custom authorizer or shared handler middleware) with an authorizer-context/memoized cache, not a per-request DynamoDB lookup on each of ~31 handlers; (2) **JIT-creation atomicity** — create the `sub→user_id` mapping via an `attribute_not_exists` **conditional put**; the loser re-reads (prevents two `user_id`s for one human under concurrent first-requests — split tenant data, permanent); (3) **the mapping table has a home** — its own small table (or a `sub`-keyed GSI), named in §4's separate-tables list (it's looked up *before* `user_id` is known, so it cannot live in `core`); (4) **cache invalidation on link events** (O-4's audit log is the hook). **Adversarial refuter MUST test:** the `email_verified`-trust vector (an IdP that asserts `email_verified` loosely → takeover; consider an IdP allow-list) and the `earliest-created user_id` pre-emption vector (attacker pre-registers a victim's email). | Hi | L-1, NFR-SEC-1 |
| P-25 | **Payment-provider port + `MockProvider`** (plug-n-play; `StripeProvider` deferred). All billing (P-02/14/15, I1–I4) codes against the port; Mock signs test webhooks + returns realistic subscription/customer objects; preserves FE checkout/portal URL contract; swap to Stripe behind config later | Md | L-4, FR-I1/I2 |
| P-25b | **Real payment provider (`StripeProvider`) + signature verification — freeze-line, before any *paid* launch** — the freeze line currently ships the `MockProvider`, so a paid launch (L-4) would run untested signature-verification code on the money path. Two parts: (a) the `MockProvider`'s `verify_webhook` MUST implement a **real HMAC check that rejects a tampered/replayed signature** (so the negative test is meaningful, not tautological); (b) add `StripeProvider` with real signature verification + an idempotency negative test, landing **in the freeze line before paid launch** (not "deferred, swap later"). Codes against the P-25 port. | Md | L-4, FR-I1/I2, NFR-SEC-3 |
| P-26 | **CFN decomposition + safe API migration (blue/green, never in-place)** — decompose *around* the `RestApi`: move feature Lambdas/alarms into per-feature nested stacks; refs via constructor props, not `Fn::ImportValue`. **Do NOT move the existing `RestApi` in place** — a cross-stack move is delete+create in a single CFN update: the `execute-api` invoke URL changes and the Amplify frontend (which bakes `NEXT_PUBLIC_API_URL` at build time) dies for all 908 live dev users. **"Retained logical id" does NOT preserve the URL across a stack move — that mitigation is void; removed from this clause.** If the API-GW resource count must shrink, use two-phase blue/green: **(1) custom domain + ACM FIRST** (additive, reversible; one Amplify env repoint to the stable domain + a P-30 smoke); **(2) stand up a NEW `RestApi` born in its OWN stack** (never inside the 415/500 parent — a second ~175-resource API would breach the 500 ceiling), verify it via P-30's 4-wire harness against its raw invoke URL; **(3) human-only base-path/domain flip** (blue→green); **(4) retire the old API in a later gated deploy.** **Precondition (gates step 0.65):** read the P-29 evidence pack to confirm what `NEXT_PUBLIC_API_URL` actually resolves to (custom domain vs raw invoke URL) before touching the API. **Explicitly forbidden: moving the Cognito user pool** (no password-hash export → unrecoverable loss of 908 users). **Must precede P-09/P-14/P-17/P-21** (they add resources to a stack at 415/500). **Corrections from adversarial review (the spec MUST encode these, else the blue/green still fails):** (i) **the retire step (4) needs P-27's stack policy lifted** — P-27 denies `Update:Delete` on the RestApi, so retiring the old API in the parent requires a human-gated `SetStackPolicy` to temporarily allow that one delete, then reinstate; sequence it explicitly. (ii) **`refs via constructor props` still compile to `Fn::ImportValue`+Export in CDK** — the dichotomy is illusory; an exported value can't be removed while consumed (`Export … in use`), which bites the retire + decomposition, so break export locks first (co-stack tightly-coupled resources, or dummy-swap the export before the producer change). (iii) **the "one Amplify env repoint" is a full Next.js rebuild + redeploy** (URL baked at build) — a real, gated frontend deliverable with an owner, not a trivial env poke; this is the one deliberate cross-C-6 exception (name it, don't smuggle it). (iv) **custom domain has an ordered, wait-gated sequence** — request cert → DNS-validate (edge-optimized cert MUST be in `us-east-1`) → domain name → base-path-mapping to the *old* API+stage → Route53 alias → await propagation → *then* repoint; and it introduces a self-managed cert/Route53 **SPOF** (renewal-failure mode) — assign cert/hosted-zone ownership + a renewal alarm. (v) the spec states the RestApi-subtree size + a **parent-count target** so "if the count must shrink" is testable. **✅ Recon 2026-07-11 (land-mines for the precondition):** `api.dev.careervp.com` has **NO DNS record** — the intended custom domain is currently **dead**, so the live frontend must resolve `NEXT_PUBLIC_API_URL` to the raw `execute-api` URL; the "custom domain first" step must therefore **create the DNS record + base-path-mapping in CDK** (not manually — the current manual/absent mapping is exactly land-mine LM-1). And the **frontend-CI deploy pipeline is broken (O-9, failing since 2026-05-03)** — the Amplify rebuild+repoint P-26 depends on **cannot run until O-9 is fixed**; fix it before the domain cutover. Contract-touching. | Md | #8 |
| P-27 | **CFN stack policy + termination protection** — deny `Update:Replace`/`Delete` on RestApi, all DynamoDB, all S3, Cognito UserPool, nested stacks; termination protection on all stacks. Protects the 908 live dev users; human-applied "5-min-today" control | Lo | Fable, #12, C-7 |
| P-28 | **Deploy identity safety + pipeline closure** — automation gets read-only + `CreateChangeSet` only; **human-only `ExecuteChangeSet`**; hard-pin account/region in `app.py` (fail-fast). Solo model: orchestrator prepares change sets, *you* execute infra mutations. **Close the CI auto-deploy hole (else the human-only execute gate is decorative):** branch-protect `main`; a GitHub deployment environment with a **required human reviewer**; `concurrency: group=deploy, max=1` **without `cancel-in-progress`** (a second merge must never cancel a CFN update mid-flight). **The human's approval artifact = the machine-parsed `DescribeChangeSet` per-resource `Replacement` report (CFN's own computation, stronger than a `cdk diff` string-heuristic), auto-fail on `Replacement: True` for any `RestApi`/DynamoDB `Table`/S3 `Bucket`/Cognito `UserPool`.** | Md | Fable, C-8, NFR-SEC-4 |
| P-29 | **Pre-deploy evidence snapshot pack + on-demand backups** — golden-state capture (template, API-GW domain/base-path/deploymentId, Lambda envs, Cognito config, Amplify env, bucket CORS, Route53) + on-demand DynamoDB backups + external S3 sync of the unversioned upload bucket, before each risky deploy | Md | NFR-DATA-2, Fable |
| P-30 | **Deploy smoke harness (4-wire)** — health · OPTIONS+GET exact-origin assert · authed read · presigned upload; baseline green **before and after** each change. Deploy-time canary (complements the F-01 CI oracle) | Md | NFR-OBS-3, contract §3, Fable |
| P-31 | **EventBridge rule targets have a DLQ** (cleanup 1h, reconcile 02:00) | Lo | NFR-REL-6 |
| P-32 | **Cost/obs + edge hygiene** — Budgets + Cost-Anomaly + app-wide `Tags.of` (NFR-COST-3); correlation-ID propagation (NFR-OBS-3); log retention 30–90d + alarm coverage (NFR-OBS-2); API-edge request validators/models (NFR-SCALE-4) | Lo | NFR-COST-3, OBS-3, OBS-2, SCALE-4 |

### Track D — DB best-practice / single-table (seams = T1/T2; full collapse = committed later wave)
| ID | Item | LOE | Crosswalk |
|---|---|---|---|
| D-H2 | Single key-authority repository (`TableRegistry`/`CoreRepository`) — sole key-builder. **Also home of the reusable dual-read migration-parity harness** (the key-authority chokepoint — one harness, reused per entity by D-H4/D-M2/D-M5/D-H9, so a pre-launch live-data cutover is proven `legacy read == core read` per item, not asserted). | Md | DB-H2 |
| D-H3 | Surface swallowed `ValidationException` (no false "not found") | Lo | DB-Q1/H3 |
| D-H4 | Stored canonical `artifact_id` + pass resolved upstreams (contract-touching) | Md | DB-H4 |
| D-H7 | Eliminate request-path `Scan`s | Md | DB-H7, #15 |
| D-M1 | Split the 1,128-LOC DAL god-class | Md | DB-M1 |
| D-M2 | Stop dual-key CV write (recon: `cvs` has both `pk/sk` + `userId/cvId`) | Lo | DB-M2 |
| D-M3 | Minimized GSI projections | Lo | DB-M3 |
| D-M5 | Retire `userEmail` PII partition key (knowledge/gap tables) | Md | DB-M5 |
| D-H9 | **Complete the in-flight FE-UI-044 CR canonical-store migration** — verify the backfill of the 239 legacy items (`users-table → artifacts-table`), confirm dual-read parity, then **retire the legacy `users-table` CR read path**. The half-done migration leaves the dual-read-fallback family that is the root of the P-01 3-schema drift; finishing it (not restarting) closes it. Wave 3, uses the migration-parity harness (see D-H2/A14). | Md | coverage-matrix §3, FE-UI-044 |
| D-M6 | Access-pattern inventory doc (schema contract) | Lo | DB-M6 |
| D-Q* | Quick wins: connection reuse, pagination, schema-enforced TTL, PITR 7d→35d | Lo | DB-Q2..Q6 |
| D-H8 | **Full single-table `core` collapse** (committed later wave; contract-touching; re-justify gate) | Hi | DB-H8, #48 |
| D-H6 | `TransactWriteItems` for multi-item invariants | Md | DB-H6 |
| D-L* | LOW: delete dead resources, `_SingletonMeta` removal, `api_storage_adapter` collapse, `BatchGetItem` audit | Lo | DB-L1..L7 |

### Track Q — Generation quality / LLM
| ID | Item | LOE | Crosswalk |
|---|---|---|---|
| Q-01 | Reorder artifact chain: **CR first** (on submit) → gap → vpr → {cv, cover, interview} | Md | L-5 |
| Q-02 | Fix Gap **real-CV** injection (load via `get_cv_by_id`; stop the `'Candidate'` stub) — TDD, test-first | Lo | new (`gap_handler.py:528-533`) |
| Q-03 | Route Gap Analysis to **Sonnet** via `LLMRouter` `TaskMode.STRATEGIC` (currently Haiku) | Lo | new (`gap_analysis.py:283-286`) |
| Q-04 | Feed CR into **all consumers** (gap, VPR, cover, interview) via existing prompt slots; per-step **digests** to protect margin | Md | L-5, C-2 |
| Q-05 | **Cross-application knowledge base (MVP)** — distil prior gap answers + validated CV bullets + VPR differentiators into `PFACT` items in per-user `core`; recall = rolling digest + top-K under **1,200-token cap**; DynamoDB brute-force rank; tenant-filtered; non-PII key | Hi | FR-K1, new |
| Q-06 | KB **Phase 2** — S3 Vectors cosine top-K (swap ranker only), flag-gated | Hi | ragvector, FR-K1 |
| Q-07 | Recreate deployed `knowledge-table` on the `user_id`/`sub` key (currently declares `userEmail`, empty); retire mis-wired `/knowledge-base` route | Lo | #K, DB-M5 |
| Q-08 | LLM output-quality evals (promptfoo + golden dataset + LLM-judge @ temp 0 + FVS gate + OWASP-LLM red-team) | Md | T-05 |
| Q-09 | Company Research margin guard (~15k Tavily tokens/gen → truncate / `include_raw_content:false`) | Lo | cost-model |
| Q-10 | **Real token metering** (retire `len/4`) + cost-per-app metric + anomaly alarm — instrument **before** the Sonnet-routing / Sonnet-5 decisions that depend on it. Margin (C-2) is currently defended by a 2-Haiku-sample estimate. **Pricing model (2026-07-11): subscription, provisional $20–$30/mo (not finalized — deliberately set *after* measured COGS, since price depends on final LLM/infra cost + target margin; use $25 midpoint for provisional gate math); free trial = 3 applications over 14 days (unpaid).** Margin gate = measured monthly COGS/subscriber (`cost-per-app × apps-per-subscriber-per-month`) ≤ 30% of subscription revenue. **Still needed to make the gate fully computable: expected apps-per-subscriber-per-month for the PAID tier** (trial implies ~6/mo but paid usage is unmeasured) — flag, don't guess. Q-10-first breaks the price↔margin circularity: measure COGS, then set final price to clear >70%. | Md | NFR-COST-1, C-2 |
| Q-11 | Prompt-cache breakpoints + bound artifact output `max_tokens` + bound Tavily input | Md | NFR-COST-2 |

### Track T — Testing & spec coverage
| ID | Item | LOE | Crosswalk |
|---|---|---|---|
| T-01 | **Enable branch coverage** (currently 0) | Lo | NFR-DEP |
| T-02 | **Retire the autouse `mock_artifact_dependency_resolver`** (opt-in); drive resolver/routing tests against real key schemas (moto) | Md | coverage-matrix §3 |
| T-03 | Coverage gates: core 85%/80% (line/branch), supporting 75–80%/70%, glue ~60%/excluded; overall CI gate 80%/70% | Lo | §8.1 |
| T-04 | Full test taxonomy: unit, **contract, characterization, integration, IaC, idempotency, migration-parity, LLM-eval, load/perf, security/SAST, smoke/canary** | Md | §8.3 |
| T-05 | Mutation-testing spot-check (`mutmut`) on core tier | Lo | §8.1 |
| T-06 | **Spec-coverage ledger** + author **~20 grouped per-feature specs** (Tier-1 first; multi-clause files per §8.5 — the exemplar covers 4 clauses in one file; count reconciled with the execution-plan TO-AUTHOR list v2.0.0), derived from route_map + frontend calls (NOT drifted docs) | Hi | new, §8.4 |
| T-07 | 8 CI gates: ruff, mypy --strict, pytest, cdk synth, Checkov, Bandit, pip-audit, CodeQL | Lo | agentic-guide |
| T-08 | **Execution plan** — ordered runbook sequencing every clause into copy-paste steps w/ model+effort ([`redesign-execution-plan.md`](./redesign-execution-plan.md)) | Lo | new |
| T-09 | **`scope-diff.py` drift checker** — maps clause↔spec↔test↔impl_state from frontmatter `scope_lock_clause`; CI gate + periodic diff | Md | §11 |

### Track F — Frontend contract validation
| ID | Item | LOE | Crosswalk |
|---|---|---|---|
| F-01 | **Executable oracle:** Zod mirror of `src/frontend/lib/types.ts` + `safeParse` (frontend-truth) + Pydantic `model_json_schema()`→ajv (backend-truth), wired via MSW in CI; nightly Playwright vs dev | Md | coverage-matrix §2 |
| F-02 | Fix: VPR `download_url` missing from `VPRStatusResult` (`api_models.py:173`) | Lo | live bug |
| F-03 | Fix: status enum lacks `cancelled/expired` in backend `Literal` (`api_models.py:182`) | Lo | live bug, contract #4 |
| F-04 | Fix: `vpr_id` required-non-null vs FE sends `null` → 422 (`api_models.py:282`) | Lo | live bug, contract #3 |
| F-05 | Fix: error envelope nested vs FE-expected flat → `[object Object]` (`api_models.py:511`) | Lo | live bug, contract #10 |
| F-06 | Encode all 10 contract items as executable assertions | Md | contract §3 |
| F-07 | Regenerate OpenAPI from live/route_map; mark `careervp-api-v1.yaml` + `docs/features/*` non-authoritative | Lo | oracle rule |

### Track X — cross-cutting / compliance
| ID | Item | LOE | Crosswalk |
|---|---|---|---|
| X-01 | Account-close **delete-all-my-data** (export already exists; delete the full `USER#{user_id}` collection + S3 objects + Cognito user). T2 | Md | DSAR (C-5) |
| X-02 | **Prompt-injection hardening** — delimit/tag untrusted input (CV, JD, Tavily-scraped CR) in every artifact prompt; XSS-encode/sanitize generated artifact fields the FE renders; **preserve + test** the SSRF guard. The *defense* is the implementation; Q-08's OWASP-LLM red-team is the *test*. T2 | Md | NFR-SEC-9 |

## 6. Out of scope
### 6.1 Explicit deviations (documented, intentional — OUT)
- Global Tables (multi-region).
- **Data-residency partitioning** (deferred — revisit only for a contractual EU customer).
- Heavy formal-DSAR tooling (audit workflow, verified-request process) — lightweight export/delete stays IN.

### 6.2 In scope now (moved OUT→IN this round)
- **CMK** on DynamoDB/S3 (was Tier-4). Now T2.
- **Field-level PII encryption** (was Tier-4). Now T2.
- **Account-close "delete-all-my-data"** (clause `X-01`). Artifact **export already exists** — the only DSAR gap is a full data delete on account closure. T2.
- **Data residency: confirmed OUT** — stored in `us-east-1` only for now; revisit only for a contractual EU customer.

### 6.3 Deferred / bounded tracks
- **RAG/vectors** — only as KB Phase 2 (Q-06), derived index, flag-gated; OpenSearch Serverless rejected (idle cost).
- **Artifact compression** — measure-first; digest projections (already partly used) formalized under Q-04.
- **Sonnet-5 migration** — VPR-pilot-only, gated on the two blockers (`temperature=0.65` 400-error; the `SONNET_MODEL_ID` CI assertion) + real-token measurement + intro-pricing window (**deadline 2026-08-31** — Q-10 metering must land in time to make a measured call before the window lapses). Gap→Sonnet (Q-03) is separate and approved, **subject to a post-Q-10 measured-margin check with a defined revert lever** (router → Haiku via `TaskMode` config): approval is not a waiver of the margin gate, only a decoupling from the Sonnet-5 pilot. **Binding sequencing (adversarial-review fix — otherwise the gate is decorative): Gap→Sonnet MUST NOT enable in production until real Q-10 metering exists to measure cost-per-gap against; until then gap defaults to Haiku.** L-6 locks the **intent/direction** (Sonnet is the target model, subject to margin); the measured check + Haiku revert are an explicit, pre-authorized exception, not a silent reopening — so this stays MINOR, not a re-litigation of the lock.

## 7. Complete path to production
### 7.1 Non-negotiable ordered gates (before any migration)
1. RETAIN + deletion-protection (P-12) — the smallest safe first slice.
2. CFN headroom — nested-stack decomposition (root ~415/500) before adding resources.
3. Schema recon (`recon.py` — DONE 2026-07-05; re-run before dual-write).
4. SNS subscriber verification (P-21).
5. Token/cost measurement baseline (C-2 guard).
6. Rehearsed rollback + drift-visibility.

### 7.2 Waves
- **Wave 0 — Guardrails & truth (nets FIRST, then scaffold):** re-clone source + **anchor confirmation** (`HEAD==4f7c294` + re-run `recon.py`); **author `test-strategy.md`**; build the drift nets — `scope-diff.py` (T-09) + spec-coverage ledger (T-06) + **executable oracle carrying all 10 contract items as assertions (F-06 folded into the F-01 build, not deferred to Wave 4)** — **before** scaffolding specs; **the AWS Budgets + Cost-Anomaly slice of P-32 (a 15-min human console task, run alongside P-27) so a retry-storm/runaway-chain can't burn unbounded LLM spend unmonitored through Waves 0–4**; **real token metering (Q-10) — pure-Python instrumentation, no payment-port dependency; pulled here from Wave 2 so a measured margin baseline accrues before the Sonnet decisions (Sonnet-5 intro-pricing deadline 2026-08-31)**; then scaffold all specs (after one Q-02 validation cycle — see execution-plan); branch coverage + retire autouse mock (T-01/T-02); **deploy-safety gates — stack policy + termination protection (P-27), credential split + pipeline closure + account/region pin (P-28), evidence snapshot pack + backups (P-29), 4-wire smoke harness (P-30)**; **a Wave-0 rollback fire-drill that measures redeploy RTO and writes the number down**; RETAIN + deletion-protection (P-12); **CFN decomposition + blue/green API migration (P-26) before any additive resource work — its safety steps (P-29/P-30/P-21) are hard dependencies**; identity surrogate scaffolding (P-24). *(Nets precede scaffolding so a mis-authored spec is caught immediately; deploy-safety gates precede any change-set execution — see execution-plan Wave 0.)*
- **Wave 1 — Security/auth launch-blockers:** **P-23 FIRST (canary/alias + CodeDeploy rollback — pulled from Wave 2 so the P-04 auth flip has a real, fire-drilled revert + a 401-rate alarm before enforcement turns on)**, then P-04..P-11, P-22.
- **Wave 2 — Reliability/money:** P-14..P-20, P-02, P-25/P-25b. *(P-23 moved to Wave 1; Q-10 token metering moved to Wave 0/1 — see above.)*
- **Wave 3 — DB seams:** D-H2/H3/H4/H7, D-M1/M2/M3/M5/M6, D-Q*; fixes P-01 (the actual break).
- **Wave 4 — Generation quality:** Q-01 (chain reorder), Q-02/Q-03 (gap CV+Sonnet), Q-04 (CR everywhere), Q-05 (KB MVP), Q-07, Q-08/Q-09; frontend fixes F-02..F-06.
- **Wave 5 — Cost/observability + Tier-2 tail:** CMK, field-PII, DSAR export/delete, log retention, alarms, tagging, low-effort/high-value Tier-3 picks.
- **Wave 6 (committed, gated) — Full `core` collapse:** D-H8/H6 via expand→dual-write→backfill→dual-read→contract; KB Phase 2 (Q-06) optional.

### 7.3 Launch freeze line
**Freeze = all T1 (any track — P/D/Q/T/F/X) + all Tier-2 + cherry-picked low-effort/high-value** (criteria: cost↓, perf↑, security↑, durability/reliability↑ — e.g. ARM64, minimized GSI projections, dead-resource deletion). *(The stale "(P-01..P-24)" parenthetical was removed: T1 = launch-blocker by definition §0.4, so the freeze must include Track-Q/T/F/X T1 clauses too — notably Q-10 real token metering, without which a paid launch would be certified against a `len/4` margin estimate; and P-25b real payments before a paid launch.)* The full `core` collapse (Wave 6) and KB Phase 2 are **post-launch**. Everything below the line stays listed and prioritized.

### 7.4 Prod-promotion certification (DoD for standing up prod)
All freeze-line items closed **AND** NFRs met **AND** test suite green with real key-schema coverage (branch on, autouse mock retired) **AND** executable oracle green **AND** `cdk diff` shows zero stateful replacements.

## 8. Definition of Done / quality gates
### 8.1 Coverage (sourced: Google/AWS/BullseyeCoverage — 100% is an anti-pattern)
- **Two-phase (v2.2.0):** enforce a calibrated **baseline** now (CI green + honest), **ratchet** toward the target wave by wave. `check_coverage_gates.py` + the `test_t03` guard track `enforced_baseline`; gates never drop below it.
- **Ratchet target (the goal):** Core generation/orchestration **85% line / 80% branch**; Supporting 75–80% / 70%; overall **80% / 70%**. Glue ~60% or excluded. LLM output: **evals, not coverage.**
- **Enforced baseline (today, calibrated 2026-07-12 to measured coverage − ~2pts):** Core **71/53**, Supporting **70/48**, overall **70/51**. Gap to close in Waves 1–4: `cv_dal`/`cv_repository`/`cv_tailoring_dal` at 0%; the cover-letter/interview-prep/cv-tailoring handlers 63–73%.
- Branch coverage enabled; autouse mock retired; `mutmut` spot-check on core.
### 8.2 CI gates (all must pass — never "agent says done")
ruff · mypy --strict · pytest · `cdk synth` (+ resource-count <400) · Checkov · Bandit · pip-audit · CodeQL · executable-oracle · `cdk diff` zero-stateful-replacement.
### 8.3 Test types required
unit · contract · characterization · integration (real services, not mocks) · IaC/CDK · idempotency/replay · migration-parity · LLM-eval (promptfoo + golden set + judge @ temp 0 + red-team) · load/perf · security/SAST · smoke/canary.
### 8.4 Spec completeness
Every endpoint + async behavior has a spec row (request/response models, error codes, acceptance criteria, edge cases). Every FR maps to ≥1 spec row and vice-versa. Each artifact spec carries its slice of the §3 frontend contract as acceptance criteria. A feature is "spec-complete" only when its acceptance criteria are an executable test.

### 8.5 Spec/test authoring rules (IMMUTABLE — apply to EVERY spec and test file)
- **Format (v1.3.0 — matches the one authored `Q-gap-analysis-track-spec.md` exemplar, not a claimed-but-never-built convention):** a spec is one Markdown file, YAML frontmatter + Problem Statement + Evidence (`file:line`) + numbered Fix Plan + `AC-###` Given/When/Then. **RED-test descriptions (exact name + exact assertions) live inline in the spec body** under a "RED tests to write first" section — they are the brief, not the artifact. The **actual pytest files are written during the IMPLEMENT step**, under TDD (write it, watch it fail, then make it pass), **in the real `careervp` repo** — never as a standalone file in this docs project. *(Retired: the `TEST-###-test-prompts.yaml` copy-paste-prompt format — no working example of it ever existed; it contradicted the one real exemplar.)* *(v2.0.0: dropped the word "proven" — the exemplar has driven zero red-green cycles; it is the one **authored** exemplar, and its first IMPLEMENT pass through Q-02 is the pattern's validation experiment, gating the step-0.4 fan-out — see execution-plan step 0.4-gate.)*
- **Ordering:** every spec/test slots into [`redesign-execution-plan.md`](./redesign-execution-plan.md) (T-08) as a numbered step; do steps in order.
- **Mandatory frontmatter (the join key + tool routing).** Two forms are permitted:
  - **Single-clause spec** — one clause, one tool block:
    ```yaml
    scope_lock_clause: Q-02
    claude_code: {model: opus|sonnet, effort: low|medium|high|xhigh}
    codex: {model: gpt-5-codex, reasoning: low|medium|high}
    ```
  - **Multi-clause spec** (the `Q-gap` exemplar's shape — codified in v2.0.0, previously an undocumented deviation) — a **list-valued** `scope_lock_clause` plus a per-clause `tooling:` map:
    ```yaml
    scope_lock_clause: [Q-01, Q-02, Q-03, Q-04]
    tooling:
      Q-02: {claude_code: {model: sonnet, effort: medium}, codex: {model: gpt-5-codex, reasoning: medium}}
      Q-01: {claude_code: {model: opus,   effort: xhigh},  codex: {model: gpt-5-codex, reasoning: high}}
      # ...one entry per listed clause; every listed clause MUST have a tooling entry
    ```
  Model/effort per the task-class table in the execution plan. **`scope-diff.py` MUST handle both:** a list value covers every listed clause (each such clause is "covered" by this spec); a spec listing a clause with no matching `tooling:` entry is incomplete → reject. A spec/test without `scope_lock_clause` is out of contract; without the tool block (single) or `tooling:` map (multi) it is incomplete.

### 8.6 Spec/test acceptance gate (validating the specs & tests themselves — detail in [`test-strategy.md §8`](./test-strategy.md))
A spec/test is accepted only when ALL five pass:
1. **Structural** — `scope-diff.py`: required frontmatter present, `scope_lock_clause` exists here, no orphan spec (spec with no clause), no uncovered clause (clause with no spec).
2. **Contract-consistency** — the spec's `AC-###` do not contradict the clause's acceptance/verification; a `contract_impact` clause's spec MUST carry its §3 frontend-contract slice.
3. **Self-sufficiency (operationalized — v2.0.0)** — run a fresh subagent given ONLY the spec + clause + named files; it must return an implementation outline **and an explicit `questions: []` block**. A **non-empty `questions` list auto-rejects** the spec as underspecified. (No longer a matter of the orchestrator's opinion; it has a defined artifact and pass/fail.)
4. **Adversarial refuter** — a second agent tries to break the spec (ambiguity, missing edge cases, contradiction). Mandatory for auth/IAM/data specs.
5. **Test-validity — split into two phases (v2.0.0, because pytest files do not exist at spec-acceptance time):**
   - **(a) spec-time lint** (runs at acceptance): every inline RED-test description names **exact assertion values** — no "or"/alternative assertions, no undefined constants (e.g. no `<digested CR>`, no bare "under the cap"). Ambiguous or under-defined RED descriptions reject the spec.
   - **(b) implement-time proof** (runs at IMPLEMENT): red-green recorded on the status board per step (fails pre-impl, passes post) + characterization proven against `4f7c294`; traceability round-trip (FR → spec → test → clause, both directions). The **`mutmut` core spot-check moves to the Wave-3 gate** (core tier is written by then) rather than being a Wave-5 afterthought.

## 9. Guardrails
### 9.1 On this document
Immutable + amendment-only (§0.3); single authority hierarchy; one canonical ID per clause; every clause tagged IMMUTABLE/TARGET/OPEN; current-state ≠ target; commit-anchored; live truth supersedes static.
### 9.2 Imposed on all spec/test/impl work
- Frontend contract can't break — version a route instead of changing a response shape.
- `expand → dual-write → backfill → dual-read → contract`; no live PK/SK change in one deploy; RETAIN + backup before risky steps; one reversible, flag-gated change at a time.
- `cdk diff` zero-stateful-replacement is a first-class check; CI <400 resources/template; refs via constructor props, never `Fn::ImportValue`.
- Tests drive **real key schemas** (moto); **never weaken a test to pass**; branch coverage on; characterization test before each migration change.
- `{env}`-scoped IAM; one role per fn; no `Resource:"*"`; no secrets in env; server-side quota (14-day/3-app trial).
- Spawn an **adversarial review** for auth/IAM/data-layer diffs, and before committing any amendment to an IMMUTABLE/locked/frontend-contract clause (§0.3).
- **Serialize steps that touch the same CFN template file** (`api_construct.py`, `api_db_construct.py`, `cognito_construct.py`, `monitoring.py`, `waf_construct.py`) — never let parallel subagents edit one template concurrently. Pure-Python/handler/test/doc steps may parallelize.
### 9.3 PR block-list (hard reject — `redesign-runbook.md`)
A single deploy that renames/removes a live table/GSI/bucket or changes PK/SK · read path switched to `core` before backfill+reconciliation complete · big-bang cutover with no canary/flag/rollback · `removal_policy=DESTROY` reintroduced · unthrottled migration batch vs live capacity · new resources added to an already-near-full stack (>400) · IAM scoped across environments (no `{env}` suffix) · **parallel edits to one CFN template file** · **a spec edited to match code without a contract amendment** · **the contract amended retroactively to rubber-stamp already-built code** · **a test weakened to pass.**

## 10. Open-questions register (must resolve before the dependent spec — do NOT guess)
| ID | Question | Blocks |
|---|---|---|
| O-1 | Full `core` collapse (D-H8) go/no-go metric threshold — what evidence justifies Wave 6? | D-H8 |
| ~~O-2~~ | **RESOLVED 2026-07-11 — cache key = `company-only`.** CR is company-level research (culture, news, tech stack, financials), so company-only maximizes cross-user reuse (best for C-2); role-specificity is injected downstream at the consumer/digest layer (gap/VPR prompts already carry the JD's role/seniority), so no relevance is lost. | Q-01/Q-04 (unblocked) |
| O-3 | Cutover/downtime tolerance + retention window (from a fresh `recon.py` / product call). | Wave 3/6 |
| ~~O-4~~ | **RESOLVED 2026-07-09** — social-IdP account-linking: auto-link a new `sub` to an existing `user_id` **only when the IdP asserts `email_verified=true` AND email matches**; otherwise no auto-link (step-up "sign in with your original method to link"); conflicts → earliest-created `user_id`; all links audit-logged. Adversarial review required on the P-24 spec. | P-24 (unblocked) |
| O-5 | `jobs`/`applications` — fold into `core` or keep as focused tables? | D-H8 |
| O-6 | KB Phase-2 embedding model + dimension + min-cosine reuse threshold. | Q-06 |
| ~~O-7~~ | **RESOLVED 2026-07-11 — `N = 180s`; latency budget = async "come back later" UX (no tight interactive bound).** Users are explicitly told artifacts take time and to return later (an optional workflow-completion notification email may be added later), so there is **no tight submit→questions interactive latency NFR** — the CR-first reorder's added latency is acceptable by design. This also retires the council's "interactive-latency budget unstated" blind spot: the flow is intentionally asynchronous. | Q-01 (L-5 rider) (unblocked) |
| ~~O-8~~ | **RESOLVED 2026-07-11 — prod-promotion model decided.** Single AWS account `788159322332`; environment isolation by resource suffix `-dev` → `-stage` → `-prod` (consistent with C-8; no separate-account boundary). **(a)** Credential isolation = **`{env}`-scoped IAM: the P-28 deploy role for prod is scoped to `-prod` ARNs only and cannot touch `-dev`/`-stage`** (confirmed — this is the blast-radius control in lieu of a separate account). **(b)** **Prod backups enabled** (PITR on all prod tables + P-29 evidence pack applied to `-prod`). **(c)** **`-stage` is a FULL proving ground** — the app must be fully working at `-stage` running real logical use-case workflows before prod promotion (dev-cert → promote to stage → verify full workflows → promote to prod). **(d)** Prod-certification = the **§7.4 checklist re-run against the `-prod` stack** (all freeze-line closed, NFRs met, tests green on real key schemas, oracle green, `cdk diff` zero stateful replacements) — no new mechanics, the same gate applied to the promoted suffix. → A short **prod-promotion track** (env-scoped IAM + prod backups + the 3-env promotion path) is now scopeable; author it post-dev-certification. | prod stand-up (post-dev-certification) |
| O-9 | **Frontend-CI deploy pipeline is broken (surfaced by 2026-07-11 recon):** the `Deploy Frontend` workflow has failed every run since 2026-05-03 (~1-min failures); the last successful frontend stack update was done outside the pipeline. **This blocks P-26's frontend repoint step** (the blue/green plan needs a working `NEXT_PUBLIC_API_URL` rebuild+redeploy). Also: `api.dev.careervp.com` has **no DNS record** (land-mine LM-1) — the intended custom domain is currently dead, so the live frontend must be pointing at the raw `execute-api` URL. Fix the frontend deploy pipeline **before** the P-26 domain cutover; wire the custom domain's DNS+base-path-mapping **in CDK** (not manually). **DNS confirmed 2026-07-11: `careervp.com` is registered at NameCheap, DNS managed by Cloudflare (external to AWS) — so CDK CANNOT create the DNS records; they are MANUAL Cloudflare steps.** Closing O-9 (author as a P-26 spec slice, all `{env}`-scoped `api.{env}.careervp.com`; endpoint type = **REGIONAL** to avoid CloudFront/edge complexity): **CDK owns** — (1) ACM cert `api.{env}.careervp.com` (`us-east-1`, DNS-validated); (2) `AWS::ApiGateway::DomainName` (REGIONAL) bound to the cert; (3) `AWS::ApiGateway::BasePathMapping` → RestApi + stage. **Manual in Cloudflare (human, documented in runbook step 0.64b)** — (a) the ACM validation CNAME, (b) a CNAME `api.{env}` → the API-GW **regional target domain**, **both set to "DNS only" (grey cloud, NOT proxied)** — Cloudflare's orange-cloud proxy terminates TLS and breaks API-GW SNI/cert matching. Recommended flow: request+validate the ACM cert FIRST (add validation CNAME in Cloudflare, wait ISSUED), then reference the cert ARN in CDK so the main deploy doesn't block on manual DNS. Then fix the frontend CI and repoint `NEXT_PUBLIC_API_URL`. **✅ `dev` cert ISSUED 2026-07-11** — `arn:aws:acm:us-east-1:788159322332:certificate/d93bafb3-fe1a-4faa-9335-a9e868646bdb` (`api.dev.careervp.com`); DNS validation CNAME confirmed resolving. **Remaining for `dev`:** CDK `DomainName`(regional, referencing this ARN)+`BasePathMapping` → get the regional target domain from the deploy → manual Cloudflare alias CNAME `api.dev` → that target (grey cloud) → fix frontend CI → repoint `NEXT_PUBLIC_API_URL` → smoke. **`stage`/`prod` certs not yet requested** — identical procedure repeats per env when those environments are stood up (O-8). | P-26 (blocks the repoint) |

## 11. Traceability & drift-check protocol
- The **YAML twin** is the machine-checkable index: each clause = `{id, title, tier, track, status, loe, deps, crosswalk, contract_impact, acceptance, current_state, verification}`.
- **Periodic diff:** for each clause, map implemented specs/tests → clause ID → `{not_started | spec_written | test_written | implemented | verified}`. Partial completion shows as partial. A spec/test with no clause ID, or a clause a spec contradicts, is a drift defect.
- Verification sources: `recon.py` (live DB), `cdk synth`/`diff`, the executable oracle, the CI gate results — never self-report.

## 12. Change log
| Version | Date | Change |
|---|---|---|
| 1.0.0 | 2026-07-05 | Initial contract frozen at code `4f7c294`. |
| 1.1.0 | 2026-07-09 | **MINOR.** Added **P-25** (payment-provider port + `MockProvider`, plug-n-play, Stripe deferred) and **P-26** (CFN nested-stack decomposition — was a documented gate with no clause). Extended §0.3 with semver + the deviation→proposal→human-confirm amendment loop + anti-patterns. Added **§8.6** spec/test acceptance gate. Added guardrails: serialize CDK-template-touching steps (§9.2) + new §9.3 anti-pattern rejects. Wave-0 reordered so the drift nets (T-09, F-01) precede spec scaffolding; added anchor confirmation + `test-strategy.md` + P-26. Authored [`test-strategy.md`](./test-strategy.md). No IMMUTABLE clause changed; no launch-blocker re-tiered. |
| 1.2.0 | 2026-07-09 | **MINOR** (applied by protocol: structured proposal → human confirm). **(A)** Resolved **O-4** (social-IdP linking — verified-email-only auto-link + step-up + earliest-`user_id` conflict rule + audit log; recorded on P-24). **(B)** Homed 6 orphaned clauses surfaced by a reference audit: **P-03/P-13/P-21/T-07** given Wave-0 steps; **T-03/T-04** id-linked to steps 0.5/0.1.5. **(C)** Fixed `best-preactice`→`best-practice` typo in historical `redesign/` docs. Anchor confirmed (`4f7c294`, 541 py, HEAD==anchor). No IMMUTABLE clause changed; no launch-blocker re-tiered. |
| 1.3.0 | 2026-07-09 | **MINOR** (human-decided, option B). **Retired** the never-built `TEST-###-test-prompts.yaml` claim; **§8.5 now matches the proven `Q-gap` exemplar** — RED-test descriptions inline in the spec body, real pytest files written during IMPLEMENT in the real repo. Recorded: spec-authoring (execution-plan step 0.4) fan-out runs via the **Workflow tool** (human opt-in) for true per-clause `{model,effort}`, not model-only via a plain `Agent` fan-out. No IMMUTABLE clause changed; no launch-blocker re-tiered. |
| 1.4.0 | 2026-07-09 | **MINOR.** Closed orphan-requirement gaps found by a crosswalk audit (NFRs in `requirements.md` mapped to no clause). Added 9 clauses — **P-27** (stack policy + termination protection), **P-28** (deploy credential split + account/region pin), **P-29** (evidence snapshot pack + on-demand backups, NFR-DATA-2), **P-30** (4-wire deploy smoke harness), **P-31** (EventBridge DLQ, NFR-REL-6), **P-32** (Budgets + cost-anomaly + tagging + correlation-ID, NFR-COST-3/OBS-3), **Q-10** (real token metering, NFR-COST-1 → T1), **Q-11** (prompt-cache + `max_tokens`, NFR-COST-2), **X-02** (prompt-injection delimiting + XSS-encode + SSRF-guard test, NFR-SEC-9). Homed P-27–P-30 in Wave 0 (deploy-safety gates), P-31/Q-10 Wave 2, Q-11/X-02 Wave 4, P-32 Wave 5. Backlog 65→74. Authored [`gap-closure-checklist.md`](./gap-closure-checklist.md). No IMMUTABLE clause changed; no existing clause re-tiered. |
| 1.4.1 | 2026-07-09 | **PATCH** (traceability hygiene). Enriched YAML crosswalks so **every declared NFR maps to a clause** (`scope-diff.py` NFR-coverage now provable): SEC-8→X-01, REL-7→D-H6, SCALE-3→D-M6, COST-4→D-M3, DATA-3→D-Q, DEP-1→P-22, DEP-2→P-23, DEP-3→P-02, DEP-4→T-07, DEP-5→T-02. Finalized **P-32** to also home the two remaining homeless NFRs (OBS-2 log-retention/alarms, SCALE-4 API-edge validators). **Zero orphan NFRs.** No scope/tier change to any settled clause. *(Authoritative crosswalks live in the YAML twin; this MD table is representative per §0.4.)* |
| 2.0.0 | 2026-07-11 | **MAJOR** (applied by §0.3 protocol; source = the 2026-07-11 implementation-plan eval-council run, verdict SOUND-WITH-CONDITIONS; contract-touching/locked-decision amendments A1/A4/A5/A8/A13 had a fresh-subagent adversarial refutation recorded before finalizing). **MAJOR driver: A8 — the human ruled 2026-07-11 that relaxing L-5's "to completion" guarantee to soft-blocking is a substantive change to a locked decision (a downstream-consumed guarantee), which is MAJOR per §0.3; the remaining A1–A7, A9–A14 are individually MINOR/PATCH, but a release containing a MAJOR is a MAJOR release → v2.0.0.** Landed the council's 14 amendments as one coherent release. **A1** P-26: replaced the false "retained logical id" nest-in-place mitigation with blue/green (custom domain+ACM first; new RestApi in its own stack; human-only base-path flip; retire-old-later; P-29 `NEXT_PUBLIC_API_URL` precondition; forbid Cognito-pool move). **A2** P-28: CI pipeline closure (branch-protect main, required-reviewer env, `concurrency max=1` no cancel-in-progress) + machine-parsed `DescribeChangeSet` Replacement report as the approval artifact (auto-fail Replacement:True on RestApi/Table/Bucket/UserPool). **A3** §0.3/§9.1: contract files write-protected from agent sessions; amendments land only via human-executed commit + CI check. **A4** P-04: flip-then-remove; P-23 canary + 401-alarm verified before the flip (no rebuilt bypass); soak + measured RTO. **A5** P-07: owns implicit-grant→auth-code+PKCE + `COGNITO_ADMIN` removal from the SPA client. **A6** new **P-25b**: real `StripeProvider` + signature verification + Mock real-HMAC, freeze-line before paid launch. **A7** §8.5/§8.6: codified list-valued `scope_lock_clause` + `tooling:` map; operationalized gate 3 (`questions: []` dry-run); split gate 5 (spec-time lint / implement-time proof; mutmut → Wave-3); dropped "proven". **A8** L-5/Q-01 rider: "to completion **or documented degraded fallback**" (soft-blocking CR). **A9** new §4 invariant `gsi_pk_user_or_high_cardinality_scoped_or_sparse_never_status`. **A10** new **D-H9**: complete the FE-UI-044 CR migration (Wave 3). **A11** waves: P-32 budgets slice + Q-10 metering + F-06 assertions + RTO fire-drill → Wave 0; P-23 → Wave 1 ahead of P-04; D-M6 verification strengthened + dep of D-H8. **A12** §7.3 freeze line: "all T1 (any track) + all T2 + picks" (dropped stale "(P-01..P-24)"). **A13** L-6/§6.3: Gap→Sonnet keeps approval but gains a post-Q-10 measured-margin check + `TaskMode`→Haiku revert lever. **A14** D-H4/D-M2/D-M5: `verification: migration-parity`; harness homed in D-H2. Backlog 74→76 (P-25b, D-H9). Adversarial refutation materially strengthened A1 (P-27 stack-policy lift for retire; CDK export-lock reality; rebuild/C-6 honesty; cert/Route53 SPOF ownership), A4 (correct revert lever per artifact; resolver-failure metric not aggregate-401; event-coverage soak), A5 (verify-before-removing COGNITO_ADMIN; dual-flow migration window; MFA optional→enforced), A8 (degraded gap → Haiku not Sonnet; concrete `N`; named status field), A13 (binding "no Sonnet in prod before Q-10 metering" sequence). No IMMUTABLE invariant reversed, no locked decision reversed (L-5/L-6 refined, not reversed). **A8 ruled MAJOR by the human 2026-07-11** (L-5's completion guarantee intentionally relaxed to soft-blocking — the locked-decision change that makes this a v2.0.0 release). No frontend-contract item broken. |
| 2.1.0 | 2026-07-11 | **MINOR** (human decisions on open questions + a live-recon `current_state` refresh, by §0.3 protocol). **Resolved O-2** (CR cache-key = `company-only`; role context injected downstream), **O-7** (`N=180s`; latency budget = async "come back later" UX — no tight interactive NFR; retires the interactive-latency blind spot), **O-8** (prod-promotion: single account, `-dev/-stage/-prod` suffix; `{env}`-scoped IAM prod deploy role limited to `-prod` ARNs; prod backups enabled; `-stage` a full proving ground; prod-cert = §7.4 re-run against `-prod`). **Added O-9** (frontend-CI deploy pipeline broken since 2026-05-03 + dead `api.dev.careervp.com` DNS — blocks P-26's repoint). **Recon `current_state` refresh (2026-07-11):** P-04 de-risked — Cognito auth already enforced in dev, `AUTHORIZER_DISABLED` confirmed dead config (delete-only), measured redeploy RTO ≈7 min (not 15–30); P-26 land-mines recorded; Q-10 pricing model recorded (subscription ~$20–30/mo provisional, trial 3 apps/14d; still needs paid apps/subscriber/month). No IMMUTABLE/locked-decision change; no frontend-contract item broken. |
| 2.1.1 | 2026-07-11 | **PATCH** (`current_state` refresh — progress fact, no scope change). Recorded the `dev` ACM certificate for `api.dev.careervp.com` as **ISSUED** (`arn:aws:acm:us-east-1:788159322332:certificate/d93bafb3-fe1a-4faa-9335-a9e868646bdb`), DNS validation confirmed via the manual Cloudflare CNAME (grey-cloud). Next steps for closing O-9/step 0.64b recorded: CDK `DomainName`(regional)+`BasePathMapping` referencing this ARN, then the manual Cloudflare `api.dev` alias CNAME, then the frontend-CI fix + repoint. `stage`/`prod` certs not yet requested. |
| 2.2.0 | 2026-07-12 | **MINOR** (human-decided, by §0.3 — refine a TARGET + record calibrated `current_state`). Coverage gates go **two-phase**. Commit `80f60ca` found the §8.1 gates (core **85/80**) were aspirational vs measured **~73% line / ~55% branch** on a fully-passing 1450-test suite (12–25pt gap, too large for one session), and had lowered `check_coverage_gates.py` to a baseline **without amending here** — leaving `test_t03` RED and enforcer≠contract≠guard. Resolution: `quality_gates.coverage` split into **`enforced_baseline`** (core 71/53, supporting 70/48, overall 70/51 — what CI enforces today) and **`ratchet_target`** (the unchanged 85/80·78/70·80/70 goal) + a `ratchet_plan` naming the holes (`cv_dal`/`cv_repository`/`cv_tailoring_dal` at 0%; big handlers 63–73%). `test_t03` now asserts `enforced_baseline` (enforcer==contract==guard restored). **The 85/80 target is NOT weakened** — retained as the per-wave ratchet goal; gates never drop below `enforced_baseline`; the ~12–25pt of new tests are explicit Wave 1–4 work. This is LEARNING recorded, not built-code rubber-stamped (the low coverage predates and is unhidden by this amendment). Also fixed `check_scope_lock_integrity.py` to count the real `change_log:` key (it only matched `changelog:`, so it would have falsely rejected this and every future amendment). No IMMUTABLE invariant reversed; no locked decision reversed; no frontend-contract item broken; T-03 target refined, not dropped. |
