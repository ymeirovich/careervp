---
spec_id: P-26-BLUE-GREEN-API
title: "CFN decomposition + safe API migration (blue/green, NEVER in-place): decompose feature Lambdas/alarms AROUND the RestApi into per-feature nested stacks; if API-GW count must shrink, stand up a NEW RestApi in its OWN stack alongside the old and cut over via base-path mapping on the stable custom domain; human-only base-path/domain flip; retire old API last, gated"
status: draft
owner: infra
tier: T1
scope_lock_clause: P-26
tooling:
  P-26: {claude_code: {model: opus, effort: xhigh}, codex: {model: gpt-5-codex, reasoning: high}}  # hard: live-user blast radius, cross-stack export locks, human-gated cutover
format_note: "RED tests are TDD-first, not optional; RED-test descriptions inline (v1.3.0); pytest files written at IMPLEMENT in the real careervp repo. Clause carries AC-### Given/When/Then blocks (§8.5). This spec prepares change sets and IaC only — the domain/base-path FLIP and the old-API RETIRE are human-only ExecuteChangeSet steps (P-28), NOT implemented or executed here."
---

# Spec — Clause P-26: Blue/Green API Migration + CFN Decomposition (NEVER in-place)

- **Status:** SPEC ONLY — do **not** implement here. Apply under TDD in the redesign implementation wave (Wave 0, `P-*` deploy-safety slice), AFTER P-27 (stack policy), P-28 (deploy identity), P-29 (evidence pack), P-30 (smoke harness) are in place.
- **Governs clause:** `P-26` (CFN decomposition + blue/green API migration). Model/effort in frontmatter above.
- **Code anchor:** `github.com/ymeirovich/careervp @ 0709bbd`. All file:line refs are at that commit.
- **Env note for the implementer:** infra requires Python + `uv` + CDK (`infra/`). Run synth via `cd infra && uv sync && cdk synth`; run diff via `cdk diff`. The DomainName/BasePathMapping/ACM constructs live in `infra/careervp/api_construct.py`. The parent stack is `ServiceStack` (`infra/careervp/service_stack.py`), which owns `ApiConstruct` (which owns the `service-rest-api` RestApi) plus four `NestedStack`s (Monitoring, AiAssist, ErrorReport, CompanyResearch).
- **TDD contract:** each fix below lists the **RED test(s) to write and watch fail FIRST**, then the minimal GREEN change. No production edit without a failing test first.
- **Constraints (all sub-clauses):** never break the §3 frontend contract; `cdk diff` **zero stateful-resource replacement**; one reversible, flag-gated change at a time; RETAIN + P-29 evidence capture before any risky step; the DomainName/base-path FLIP and the RETIRE are **human-only ExecuteChangeSet** (P-28), never automation. This spec's IaC deliverables are additive and reversible up to (but not including) the flip.

---

## Why this clause is uniquely dangerous (the non-negotiable law)

**NEVER move the existing `AWS::ApiGateway::RestApi` in place, and NEVER move it across stacks.** A cross-stack move of a `RestApi` is, in CloudFormation terms, **delete + create in a single update** — the underlying `execute-api` id and invoke URL change. The `ui-upgrade` frontend is built by AWS Amplify Hosting and **bakes `NEXT_PUBLIC_API_URL` at build time**; a changed invoke URL means **908 live dev users lose their backend** until the frontend is rebuilt and redeployed. A "retained logical id" does **not** preserve the URL across a stack move — that idea is **VOID** and MUST NOT appear in the implementation.

**FORBIDDEN, absolutely:** moving the Cognito user pool (`AWS::Cognito::UserPool`). A replace/move is an **unrecoverable loss of 908 user accounts**. P-27's stack policy denies this; this spec never touches the pool.

Therefore P-26 has two independent jobs, and they must not be conflated:

- **Job 1 (decompose AROUND the RestApi):** move feature Lambdas / alarms / non-stateful resources OUT of the near-limit parent into per-feature nested stacks, **leaving the RestApi resource exactly where it is** (same stack, same logical id, same URL). This is the CFN-limit relief and is done first.
- **Job 2 (blue/green, only if API-GW resource count must still shrink):** stand up a **NEW** RestApi in its **OWN** stack **alongside** the old one, verify it against its raw invoke URL, then cut traffic over by re-pointing the **base-path mapping on the stable custom domain** `api.{env}.careervp.com` — **never** by replacing the existing RestApi resource. The old RestApi stays live until the new one is verified, and is retired last in a separately gated deploy.

The stable custom domain is the linchpin: because the frontend points `NEXT_PUBLIC_API_URL` at the custom domain (not at a raw `execute-api` URL), the base-path swap moves traffic to the new API **without re-touching the frontend build**. Standing up that domain is a **precondition** (Job 0 below), and it is exactly what O-9 resolves.

---

## Current state (confirmed, grounded in live evidence)

**Parent stack near the CFN hard limit.** `ServiceStack` (`service_stack.py:26`) instantiates `ApiConstruct` (`:56`) — which builds `service-rest-api` (the RestApi, `api_construct.py:343-404`), all feature Lambdas, log groups, DLQs/queues, IAM role, gateway responses, and monitoring — plus four nested stacks (`MonitoringNestedStack :65`, `AiAssistNestedStack :84`, `ErrorReportNestedStack :104`, `CompanyResearchNestedStack :116`). Recon records the **parent template at ~415/500 resources** (`current_state: root_415_of_500_4_nested`; earlier passes measured 476–498). Adding another full API-GW subtree (~+175 resources) inside the parent **breaches the 500-resources-per-template CFN hard limit** — so a NEW RestApi MUST be born in its own stack.

**The custom domain construct now exists in CDK, dev-only, guarded.** `_build_api_custom_domain` (`api_construct.py:254-279`) is invoked at `api_construct.py:241-242` when `not is_production_env`. It creates:
- an ACM cert **reference** (not a new cert) to the ISSUED dev cert `arn:aws:acm:us-east-1:788159322332:certificate/d93bafb3-fe1a-4faa-9335-a9e868646bdb` (`:255-259`);
- a **REGIONAL** `aws_apigateway.DomainName` for `api.dev.careervp.com` with `TLS_1_2` (`:260-267`);
- a `BasePathMapping` binding that domain to `self.rest_api` + `self.rest_api.deployment_stage` (`:268-274`);
- a `CfnOutput ApiDevRegionalDomainName` exposing `domain.domain_name_alias_domain_name` (the regional target for the Cloudflare CNAME) (`:275-279`).

**DNS is external to AWS (O-9).** `careervp.com` is registered at NameCheap with DNS managed by **Cloudflare** — **CDK cannot create DNS records**. The ACM-validation CNAME and the `api.dev` → regional-target CNAME are **manual Cloudflare steps**, and both MUST be **"DNS only" / grey-cloud (NOT orange-cloud proxied)** — orange-cloud proxy terminates TLS and breaks API-GW SNI/cert. The dev ACM cert is already ISSUED (validation CNAME added, confirmed). Evidence supplied 2026-07-11: `dig +short api.dev.careervp.com` resolves to `d-ufdp03t4f1.execute-api.us-east-1.amazonaws.com.` plus A records `54.157.91.177`, `98.90.192.136`, `98.89.7.162`.

**Frontend repoint is complete; GitHub CI proof remains.** Evidence supplied 2026-07-11: Amplify `NEXT_PUBLIC_API_URL` was set to `https://api.dev.careervp.com` and the Amplify redeploy was green. The historical blocker was the GitHub "Deploy Frontend" workflow, failing since **2026-05-03** because it still modeled a static S3/CloudFront export (`src/frontend/out/`) while the real deployment is Amplify SSR (`.next`). That workflow must now be green as an Amplify-build validation workflow before O-9 is considered closed.

**Cross-stack refs compile to Export/ImportValue.** CDK's "pass props, not `Fn::ImportValue`" is illusory: a construct reference across a stack boundary compiles to a CloudFormation `Export` + `Fn::ImportValue`, and **an export cannot be removed while it is consumed**. This locks the retire/decompose step unless the export locks are broken first (see Sub-clause C).

**Root causes:**
1. The RestApi lives inside a parent template that is ~415/500 — near the CFN hard limit; further additive waves (P-09/P-14/P-17/P-21) cannot land until the parent has headroom.
2. There is no NEW-API stack; a blue path does not yet exist.
3. `_build_api_custom_domain` exists and the manual Cloudflare CNAME + Amplify env repoint are now evidenced for dev; the remaining O-9 proof is a green GitHub Deploy Frontend validation run plus P-30 smoke through the custom domain.
4. The base-path FLIP and the old-API RETIRE have no prepared, machine-checked change set.

---

## Fix (GREEN — Job 0 → Job 1 → Job 2, in order)

> **Sequencing law:** Job 0 (stabilize the custom domain) and Job 1 (decompose around the RestApi) are additive/reversible and land first. Job 2 (blue/green) only runs **if** Job 1 does not free enough API-GW resources — and its FLIP + RETIRE are human-only P-28 executes.

### Job 0 — Stabilize the custom domain so the frontend seam is the domain, not the raw URL (O-9 closure, additive)

The domain is the precondition that makes every later base-path swap invisible to the frontend build.

1. **Keep the CDK constructs** already present (`_build_api_custom_domain`, `api_construct.py:254-279`): ACM cert reference → REGIONAL `DomainName` → `BasePathMapping` → RestApi+stage → `CfnOutput` of the regional target domain. Make the cert ARN, domain name, and env-scoping (`api.{env}.careervp.com`) driven off `constants.ENVIRONMENT` so stage/prod re-run the identical procedure per env (O-8).
2. **Order the deploy so it never blocks on manual DNS:** request+validate the ACM cert FIRST (human adds the validation CNAME in Cloudflare, waits `ISSUED`), then reference the cert ARN in CDK so the main `cdk deploy` does not stall.
3. **Manual Cloudflare steps (human, runbook 0.64b — NOT CDK):**
   (a) ACM validation CNAME (already done for dev);
   (b) CNAME `api.{env}` → the API-GW **regional target domain** from `CfnOutput ApiDevRegionalDomainName`;
   both **"DNS only" (grey cloud)**.
4. **Then, and only then (O-9):** fix the broken Deploy-Frontend CI, repoint `NEXT_PUBLIC_API_URL` to `https://api.{env}.careervp.com`, rebuild+redeploy the Amplify frontend, and P-30-smoke that the live frontend works through the custom domain. This is a **gated cross-C-6 frontend deliverable with a named owner** — it is NOT smuggled into a backend deploy.
- **Reversibility:** until step 4 lands, the frontend stays on the raw `execute-api` URL; the domain constructs are additive and can be removed with zero stateful replacement. The base-path mapping at this stage points at the **OLD** (current) RestApi + stage — no cutover has happened yet.

### Required human console tasks for Job 0 (explicit O-9 gates)

These are the two console tasks that block the custom-domain seam. Automation may produce values and validation commands, but a human performs the console changes and records evidence before any cutover.

1. **Cloudflare DNS console — create/verify `api.{env}`.**
   - Confirm the ACM validation CNAME for the environment certificate exists and the ACM certificate is `ISSUED`.
   - Create or update a CNAME named `api.{env}` pointing to the API Gateway regional target from `CfnOutput ApiDevRegionalDomainName` (or the environment-specific equivalent output).
   - Set proxy status to **DNS only** / grey-cloud. Do **not** use orange-cloud proxying for the API Gateway domain.
   - Evidence to capture: Cloudflare record name, target, proxy status, and `dig +short api.{env}.careervp.com` resolving to the regional target.

2. **Deploy-Frontend / Amplify console — repoint the baked frontend API URL.**
   - Set `NEXT_PUBLIC_API_URL=https://api.{env}.careervp.com` for the target Amplify frontend environment.
   - Trigger a rebuild/redeploy so the baked frontend config uses the custom domain instead of the raw `execute-api` URL.
   - Evidence supplied 2026-07-11 for dev: Amplify env var set and redeployed green.
   - Remaining evidence to capture: green GitHub Deploy Frontend validation workflow, Amplify deployment id, the resolved frontend environment variable value, and P-30 4-wire smoke results through `https://api.{env}.careervp.com`.

### Job 1 — Decompose AROUND the RestApi (CFN-limit relief, additive, no RestApi move)

Reduce the parent template's resource count by moving **non-stateful, non-RestApi** resources into per-feature nested stacks, **leaving `service-rest-api` and its `deployment_stage` in the parent, at the same logical id, with the same URL.**

1. Identify the largest movable subtrees in `ApiConstruct` that are NOT the RestApi and NOT stateful: feature Lambdas + their log groups, DLQs/queues, per-feature alarms/dashboards. (The existing four nested stacks are the template to follow; the `ErrorReportNestedStack` AwsIntegration-proxy pattern at `api_construct.py:294-308` shows how a nested-stack Lambda is wired to a parent Resource/method while keeping the invoke permission in the nested stack.)
2. Move each subtree into a new/existing `NestedStack`, passing the parent's RestApi/root-resource **as a construct prop** where a route must attach to it. Accept that this compiles to Export/ImportValue; that is fine while the parent RestApi is stable (it is not being retired here).
3. Do **not** move: the RestApi, the deployment stage, the custom `DomainName`/`BasePathMapping`, any DynamoDB table, any S3 bucket, the Cognito pool. Moving any of these is a stateful/URL-changing replacement — forbidden.
- **Target (warn, not a hard CI gate):** drive the **parent template toward `< 400` resources** as headroom for the additive waves. Treat `< 400` as a **target/warn** until decomposition lands — **do NOT** add a CI gate that fails the current ~415/498 parent (that would red-bar every build before the work is done). The hard, non-negotiable gate is the CFN limit itself: no single template may reach 500.
- **Verify:** `cdk synth` succeeds; `cdk diff` shows the moved resources as **create-in-nested / delete-from-parent for non-stateful resources only** and **zero replacement of any stateful resource or the RestApi**; the RestApi logical id and invoke URL are byte-identical before/after.

### Job 2 — Blue/green a NEW RestApi (ONLY if Job 1 leaves the API-GW count too high)

If, after Job 1, the API-GW subtree still cannot shrink enough within one template, stand up a NEW RestApi **alongside** the old.

1. **New RestApi in its OWN stack.** Create a new top-level stack (e.g. `ApiV2Stack`) that owns a **new** `RestApi` + stage. It is **never** born inside the ~415/500 parent (+~175 breaches 500). It has its own routes, integrations, and (temporarily) its own default `execute-api` URL.
2. **Verify green against the raw invoke URL** with the P-30 4-wire smoke (health; `OPTIONS`+`GET` exact-origin CORS assert; authed read; presigned upload) — the new API must pass ALL four wires on its raw URL **before** any traffic is moved.
3. **Prepare (do NOT execute) the base-path FLIP change set.** Author the CDK change so the `BasePathMapping` on `api.{env}.careervp.com` re-points from the OLD RestApi+stage to the NEW one. Run `cdk synth`/`cdk diff`, then `create-change-set` + the P-28 `DescribeChangeSet` Replacement report. The report **MUST auto-fail on `Replacement:True`** for `AWS::ApiGateway::RestApi`, `AWS::DynamoDB::Table`, `AWS::S3::Bucket`, or `AWS::Cognito::UserPool` (a correct flip touches only the `BasePathMapping`, which is not in that set). **The FLIP itself is a human-only `ExecuteChangeSet` (P-28).**
4. **Cut over.** Human executes the base-path flip change set. Because the frontend points at the custom domain, no frontend rebuild is needed for the flip. Smoke both the domain and the new raw URL green.
5. **Retire the old API LAST, separately gated (blocked-by-design by P-27).** The old RestApi delete is DENIED by the P-27 stack policy. The correct human-gated sequence (P-27 §Step 4 / AC-P27-3): human runs a **temporary** scoped `SetStackPolicy` allowing `Update:Delete` on the specific old-RestApi logical id → executes the retire change set → **immediately reinstates** the full P-27 deny policy. Additionally, break any Export/ImportValue **export locks** on the old RestApi first (an export cannot be removed while consumed), else the retire change set will not build. Automation NEVER executes the lift or the retire.
- **Rollback:** the old RestApi stays live and mapped until the flip; on failure the human re-points the base-path mapping back to the old RestApi+stage (a `BasePathMapping`-only change, seconds). Nothing is retired until the new path is proven.

---

## RED tests to write first (watch fail)

All tests live in `tests/infra/test_p26_blue_green_api.py` (authored at IMPLEMENT time, not now). They operate on synthesized templates / change-set JSON — never on the live account.

**`test_rest_api_logical_id_and_url_unchanged_after_decompose`**
- Synth the stack before and after the Job 1 decomposition (or assert against the committed logical id).
- Assert: the `service-rest-api` RestApi logical id is identical before/after, and the `CfnOutput` invoke URL (`constants.APIGATEWAY`, `api_construct.py:401-403`) is unchanged.
- MUST FAIL if any refactor moves the RestApi across a stack boundary (which would change its logical id / URL).

**`test_cdk_diff_zero_stateful_replacement`**
- Run `cdk diff` (or parse the diff artifact) for the Job 1 change.
- Assert: **no** `AWS::ApiGateway::RestApi`, `AWS::DynamoDB::Table`, `AWS::S3::Bucket`, or `AWS::Cognito::UserPool` appears with a replace/destroy action.
- Assert: the only deletes-from-parent are non-stateful (Lambda/log-group/queue/alarm) subtrees that reappear as creates in a nested stack.
- MUST FAIL if the decomposition replaces or moves any stateful resource.

**`test_no_single_template_reaches_cfn_limit`**
- Synth all templates; count resources per template.
- Assert: **no** single template has ≥ 500 resources (the CFN hard limit).
- Assert (warn-only, non-failing marker): record whether the parent is `< 400` (the headroom target) — emit a warning, do NOT fail, until decomposition lands.
- MUST FAIL only if any template hits the 500 limit (e.g. a NEW RestApi subtree was mistakenly added to the parent).

**`test_custom_domain_is_regional_and_maps_to_rest_api`**
- Synth; locate the `AWS::ApiGateway::DomainName` and `AWS::ApiGateway::BasePathMapping`.
- Assert: `DomainName` `EndpointConfiguration.Types == ["REGIONAL"]`, `DomainName == "api.{env}.careervp.com"` (env-scoped), and `SecurityPolicy == "TLS_1_2"`.
- Assert: the `BasePathMapping` binds that domain to the RestApi and its deployment stage; a `CfnOutput` exposes the regional target domain (for the Cloudflare CNAME).
- MUST FAIL if the domain is EDGE-typed, hard-codes `dev` in a non-dev env, or the mapping is absent.

**`test_new_api_born_in_own_stack_not_parent`** *(Job 2 only)*
- When a NEW RestApi is introduced, synth and assert the new `AWS::ApiGateway::RestApi` resides in a **separate** top-level stack template (e.g. `ApiV2Stack`), NOT in the `ServiceStack` parent template.
- MUST FAIL if the new RestApi subtree lands inside the ~415/500 parent.

**`test_flip_changeset_replacement_report_auto_fails_on_protected`** *(Job 2 only)*
- Feed the P-28 Replacement-report script a synthetic `describe-change-set` JSON in which an `AWS::ApiGateway::RestApi` (or `DynamoDB::Table`/`S3::Bucket`/`Cognito::UserPool`) carries `Replacement: "True"`.
- Assert: the script exits non-zero (auto-fail) and the `execute-change-set` gate never opens.
- Also assert the PASS path: a change set that touches ONLY the `AWS::ApiGateway::BasePathMapping` (the legitimate flip) reports `auto_fail: false`.
- MUST FAIL before the report wiring treats a RestApi replacement as a hard stop.

**`test_flip_and_retire_are_not_automation_executable`**
- Assert (workflow/IaC inspection) that no automation job calls `ExecuteChangeSet` for the base-path flip or the old-RestApi retire, and that the retire path documents the P-27 temporary-policy-lift + reinstate as a human runbook step.
- MUST FAIL if any CI job auto-executes the flip or the retire.

---

## Acceptance Criteria

**AC-P26-1** — *Given* the Job 1 decomposition ships, *When* the stack is synthesized, *Then* the `service-rest-api` RestApi remains in the same (parent) stack at the same logical id with an unchanged invoke URL, feature Lambdas/alarms/queues have moved into per-feature nested stacks, and `cdk diff` shows **zero replacement** of the RestApi or any DynamoDB table / S3 bucket / Cognito pool.

**AC-P26-2** — *Given* the parent template was near the CFN limit (~415/498 of 500), *When* decomposition and any Job-2 stand-up are complete, *Then* **no single template reaches 500 resources**, the parent trends toward the `< 400` headroom target (warn-only, not a build-failing gate at the current count), and the additive waves (P-09/P-14/P-17/P-21) can land.

**AC-P26-3** — *Given* the stable custom domain `api.{env}.careervp.com` (REGIONAL DomainName + BasePathMapping in CDK, ACM cert ISSUED, Cloudflare grey-cloud CNAME), *When* the frontend has `NEXT_PUBLIC_API_URL` pointed at that domain, *Then* a later base-path swap moves traffic between RestApis **without any frontend rebuild** — the domain is the stable seam.

**AC-P26-4 (O-9 blocking precondition)** — *Given* the Deploy-Frontend CI is broken (failing since 2026-05-03) and `api.{env}.careervp.com` DNS is external (Cloudflare, manual), *When* the P-26 domain cutover is contemplated, *Then* it is BLOCKED until (a) the frontend CI is fixed, (b) the manual grey-cloud Cloudflare CNAME exists, and (c) `NEXT_PUBLIC_API_URL` can be repointed + the Amplify frontend rebuilt+redeployed — all human actions, owned and gated, never smuggled into a backend deploy.

**AC-P26-5 (blue/green, Job 2)** — *Given* a NEW RestApi is required, *When* it is created, *Then* it is born in its **own** top-level stack (never the ~415/500 parent), passes the P-30 4-wire smoke on its raw invoke URL BEFORE any cutover, and the OLD RestApi stays live and mapped until the new path is proven.

**AC-P26-6 (human-only flip)** — *Given* the base-path FLIP change set, *When* it is prepared, *Then* automation only `create-change-set`s it and emits the P-28 `DescribeChangeSet` Replacement report; the report **auto-fails on `Replacement:True`** for RestApi/Table/Bucket/UserPool; the legitimate flip touches only the `BasePathMapping` and passes; and the actual `ExecuteChangeSet` is a **human-only** P-28 step.

**AC-P26-7 (retire blocked-by-design)** — *Given* the old RestApi must be retired, *When* the retire is attempted, *Then* the P-27 stack policy DENIES the delete; the human must (1) break the Export/ImportValue lock on the old RestApi, (2) apply a temporary scoped `SetStackPolicy` allowing `Update:Delete` on that one logical id, (3) execute the retire, (4) immediately reinstate the full P-27 deny policy — automation NEVER executes any of these steps.

**AC-P26-8 (Cognito untouched)** — *Given* any P-26 step, *When* `cdk diff` / the Replacement report is inspected, *Then* the `AWS::Cognito::UserPool` never appears with a replace/move/delete action; the 908 accounts are never at risk.

---

## Done-when

All RED tests pass (Job-1 tests unconditionally; Job-2 tests when a new RestApi is introduced); `ruff`/`mypy` clean (infra is CDK Python); AC-P26-1..8 hold; the RestApi is never moved in place or across stacks; `cdk diff` shows zero stateful-resource replacement for every prepared change; no single template reaches the 500-resource CFN limit; the custom-domain constructs are REGIONAL + env-scoped and the base-path mapping (still pointing at the OLD RestApi until cutover) is present; the base-path FLIP and old-API RETIRE exist only as **prepared change sets** with the P-28 Replacement report auto-fail wired — neither is executed by automation; the P-27 temporary-lift + reinstate procedure is cross-referenced in the retire runbook; the O-9 preconditions (frontend CI fixed, Cloudflare CNAME, `NEXT_PUBLIC_API_URL` repoint) are documented as owned, gated human actions that block the cutover.

---

## Sequencing within Wave 0

P-26 is the last of the deploy-safety guardrails and has hard dependencies on:
- **P-29** (evidence pack) — gates step 0.65: read the P-29 evidence pack to confirm exactly what `NEXT_PUBLIC_API_URL` resolves to today before any cutover.
- **P-30** (4-wire smoke) — baseline green BEFORE and AFTER every P-26 change; the sole proof the new API path is live.
- **P-27** (stack policy) — the retire step is blocked-by-design by P-27; must be applied first and lifted/reinstated only by a human.
- **P-28** (deploy identity) — the base-path flip and the retire are human-only `ExecuteChangeSet` gates with the machine-parsed Replacement report.
- **O-9** (frontend CI + external DNS) — the domain cutover cannot proceed until the Deploy-Frontend CI is fixed and `NEXT_PUBLIC_API_URL` can be repointed+redeployed.

**Order:** Job 0 (custom domain stabilize, additive) → Job 1 (decompose around the RestApi, additive, CFN-limit relief) → **[only if still over]** Job 2 (NEW RestApi in own stack → P-30-verify on raw URL → human flip base-path on the stable domain → human retire old API with P-27 lift/reinstate). P-26 MUST precede P-09/P-14/P-17/P-21 (they need the freed parent headroom). Nothing in P-26 touches the Cognito user pool.

## How the O-9 custom-domain resolution threads into the blue/green cutover

O-9 is not a side note — it is the mechanism that makes the whole blue/green approach safe. The resolution establishes `api.{env}.careervp.com` as a **stable seam owned partly by CDK and partly by manual Cloudflare**: CDK owns the ACM cert reference, the REGIONAL `DomainName`, and the `BasePathMapping`; Cloudflare (manual, grey-cloud) owns the validation CNAME and the `api.{env}` → regional-target CNAME. Once the frontend's `NEXT_PUBLIC_API_URL` points at that domain (which requires the broken Deploy-Frontend CI to be fixed first — the O-9 blocker), the base-path mapping becomes the single point of cutover: re-pointing it from the OLD RestApi+stage to a NEW one moves 908 users' traffic **without a frontend rebuild**. That is why Job 0 (domain) precedes Job 2 (blue/green), why the flip is a `BasePathMapping`-only change (auto-passing the P-28 Replacement report while a RestApi replacement would auto-fail it), and why the cutover is gated on O-9 rather than being a pure-IaC step.
