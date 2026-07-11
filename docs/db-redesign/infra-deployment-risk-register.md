# CareerVP Redesign — Infra Deployment Safety Risk Register

- **Version:** 1.0.0 · **Created:** 2026-07-11 · **Branch:** `db-redesign` (off `ui-upgrade`)
- **Code anchor:** `4f7c294` (HEAD `0709bbd` descends from it; backend logic byte-identical).
- **Question this answers:** *"What infra changes in this redesign will break the `ui-upgrade`
  installation on Amplify? What am I going to break?"*
- **Layer:** operational companion to
  [`code/code-analysis/project/project-scope-lock.md`](./code/code-analysis/project/project-scope-lock.md).
  It does **not** amend the contract — it classifies each infra-touching clause by its blast
  radius on the live `dev` stack + the Amplify-hosted frontend, with mitigation / rollback /
  verification. Every deploy of a 🔴/🟠 clause must clear its card here first.
- **Golden rule (scope-lock §9.2):** one reversible, flag-gated change at a time; `cdk diff`
  zero-stateful-replacement; RETAIN + backup before risky steps; never break the frontend contract.

---

## 1. The Amplify seam — the only 4 wires that can break the site

The `ui-upgrade` frontend is built by **AWS Amplify Hosting** (`amplify.yml` at repo root, artifacts
`.next`). **Backend/infra changes CANNOT break the Amplify _build_** — the build only runs `npm`
against the frontend tree, which this redesign does not touch. The site can only break at the
**runtime seam**: the browser calling the backend. That seam is four wires, all injected via Amplify
console env (from `src/frontend/.env.development.local`):

| # | Wire | Current value | Who serves it | Break vector |
|---|------|---------------|---------------|--------------|
| W1 | **API host** | `NEXT_PUBLIC_API_URL=https://api.dev.careervp.com` | ⚠️ **NOT in CDK** — configured outside IaC | P-26 recreates RestApi → mapping orphaned |
| W2 | **API CORS** | API GW = `Cors.ALL_ORIGINS` ([api_construct.py:326](../../infra/careervp/api_construct.py#L326)) | CDK | P-10 allow-list omits `*.amplifyapp.com` |
| W3 | **Auth** | Cognito pool `us-east-1_WiHMRqLpe`; **`AUTHORIZER_DISABLED="true"`** for non-prod ([api_construct.py:1720](../../infra/careervp/api_construct.py#L1720)) | CDK | P-04 turns authorizer ON; P-07 MFA; L-2 retires RS256 |
| W4 | **Presigned-S3 CORS** | upload bucket `allowed_origins=["*"]` ([api_db_construct.py:189](../../infra/careervp/api_db_construct.py#L189)) | CDK | P-08 allow-list omits `*.amplifyapp.com` |

**Confirmed live FE origin:** `*.amplifyapp.com` (Amplify default). Every CORS allow-list produced by
P-08/P-10 **MUST** contain the exact Amplify origin (and `https://dev.careervp.com` if/when the
custom domain is enabled). Today the scoped CV-download bucket lists
`["https://careervp.com","http://localhost:3000","https://*.amplifyapp.com"]`
([api_db_construct.py:566-570](../../infra/careervp/api_db_construct.py#L566)) — note it already
**omits `dev.careervp.com`**, a latent trap to copy forward.

---

## 2. Severity legend

| Sev | Meaning |
|-----|---------|
| 🔴 **Site-down** | Misstep takes the whole Amplify site offline (blank/`[object Object]`/CORS wall/401 wall). |
| 🟠 **Feature-break** | One flow breaks (CV upload, login challenge), rest of site works. |
| 🟡 **Backend-only** | FE unaffected unless a Lambda 500s; no contract/CORS/auth surface. |
| 🟢 **Safe / FE-positive** | Additive or improves the FE (e.g. throttle raise). |

---

## 3. ⚠️ The two out-of-IaC land-mines (NOT covered by the redesign's safety net)

The scope-lock's guardrails (`cdk diff` zero-stateful-replacement, the oracle, flag-gating) protect
everything **inside** CDK. These two are **outside CDK**, so those nets are blind to them:

### LM-1 — `api.dev.careervp.com` is not in the CDK
Grep of all `infra/careervp/*.py` finds **no API Gateway custom domain, no `BasePathMapping`, no
Route53 record** for the `api` subdomain. It is wired manually (clickops) in the live account.
**Consequence:** P-26 (and any RestApi replacement) changes the underlying `execute-api` id; the
manual base-path mapping keeps pointing at the dead RestApi → `api.dev.careervp.com` returns
**403/404 for every request → full site outage**, and CDK will not self-heal it.
**Required before P-26:** resolve how the subdomain is mapped (read-only AWS), then either
(a) import the custom domain into CDK so the mapping is managed, or (b) add an explicit manual
"re-point base-path mapping to new RestApi" runbook step gated in the P-26 deploy.

### LM-2 — CORS origin allow-lists are hand-authored
P-08/P-10 replace `*`/`ALL_ORIGINS` with explicit lists. There is **no test today** asserting the
Amplify origin is in them. A wrong or incomplete list is invisible to `cdk synth`/`cdk diff` (it's a
valid template) and only surfaces as a browser CORS wall in production.
**Required:** the F-01 executable oracle / an IaC assertion must include a CORS-origin check
(`*.amplifyapp.com` present) as a hard gate on P-08 and P-10.

> **Both LM-1 and LM-2 are pre-Wave-1 blockers.** Do not deploy P-04/P-08/P-10/P-26 until they are
> closed with live-account evidence.

---

## 4. Full infra clause risk table

| Clause | Change | Sev | Amplify/dev blast radius |
|--------|--------|-----|--------------------------|
| **P-26** | CFN nested-stack decomposition — recreate RestApi | 🔴 | **W1.** RestApi replace orphans `api.dev.careervp.com` (LM-1) → site-down. Also `contract_impact: true`. |
| **P-10** | API GW CORS `ALL_ORIGINS` → allow-list | 🔴 | **W2.** List missing `*.amplifyapp.com` → every XHR CORS-blocked → site-down. |
| **P-04** | Remove `x-user-id` bypass + `AUTHORIZER_DISABLED` | 🔴 | **W3.** dev runs with auth OFF today; turning it ON → any un-tokened call = 401 wall. FE does **not** use `x-user-id` (verified) so that half is safe. |
| **P-08** | CV bucket CORS `*` → locked origins | 🟠 | **W4.** List missing `*.amplifyapp.com` → presigned PUT/GET blocked → CV upload/download breaks. |
| **P-07** | Cognito MFA + advanced security | 🟠 | **W3.** If MFA **required**, Amplify login breaks unless FE handles the challenge. **Optional** = safe. |
| **L-2 / P-24** | Retire self-managed RS256; Cognito-only; `user_id` surrogate | 🟠 | **W3.** JWT_PRIVATE_KEY paths exist ([api_construct.py:894…](../../infra/careervp/api_construct.py#L894)). If any live FE/API path still verifies RS256 tokens, retiring breaks auth. P-24 itself is `contract_impact:false`. |
| **P-11** | WAF in all envs + rate rule | 🟠 | WAF is `if is_production_env` today ([api_construct.py:240](../../infra/careervp/api_construct.py#L240)) → **dev has none**. Adding a rate/managed rule can newly block legit FE bursts if thresholds too low. |
| **F-02..F-06** | Fix 4 live contract bugs; encode 10 contract items | 🟢→🟡 | **Corrective** (adds `download_url`, `cancelled/expired`, accepts `vpr_id:null`, flat error envelope). Must stay **additive** — guarded by the F-01 oracle. Risk only if oracle not built first. |
| **P-09** | One IAM role per function | 🟡 | Shared `self.lambda_role` today ([api_construct.py:70](../../infra/careervp/api_construct.py#L70)). A split role missing a grant → that Lambda 500s → FE sees errors on one route. |
| **P-06** | Secrets → SSM/Secrets Mgr | 🟡 | Partly done (JWT key already `value_for_string_parameter`). Moving to runtime fetch is backend-only; a missing SSM param → Lambda init fail. |
| **P-14/P-15/P-25** | Idempotency, kill money-path Scan, payment port | 🟡 | Billing flows; `P-25 contract_impact:true` (preserve FE checkout/portal URL contract). No hub-page surface. |
| **P-16/P-17/P-18/P-19** | Concurrency bounds, `ReportBatchItemFailures`, visibility ≥6×, SFN retry | 🟡 | Async worker reliability. FE only sees them as fewer stuck/lost generations. |
| **P-20** | Raise API throttle from 2 rps/burst 10 | 🟢 | **FE-positive** — current 2 rps can 429 the FE under normal use. Raising helps. |
| **P-12** | RETAIN + deletion_protection | 🟢 | Durability only. No runtime surface. First safe slice. |
| **P-13** | Remove dead RETAIN stacks | 🟢 | Never-instantiated code; verify with `cdk synth`. |
| **P-21** | SNS alarms → subscribed topic | 🟢 | Observability. No FE surface. |
| **P-22** | OIDC in `cdk-diff.yml` | 🟢 | CI only. |
| **P-23** | Alias+version + CodeDeploy canary | 🟢→🟡 | Improves rollout safety; a misconfigured canary hook could stall a deploy (not the live site). |
| **Track D (D-H2/H3/H4/H7, D-M*)** | Key-authority repo, stored `artifact_id`, kill Scans | 🟡 | **D-H4 `contract_impact:true`** (fixes P-01 cover-letter/interview-prep). Data-layer; guarded by characterization tests + oracle. No CORS/auth surface. |
| **CMK / field-PII (Wave 5)** | KMS on Dynamo/S3, PII encryption | 🟠 | A CMK swap on a live table/bucket can be a **stateful replacement** — must follow expand→migrate, never in-place. Backend-only but data-risk. |

---

## 5. Detail cards — the 🔴 items (deploy only after these pass)

### P-26 · CFN decomposition / RestApi recreate — 🔴 W1
- **Breaks because:** new RestApi id ≠ old; manual `api.dev.careervp.com` mapping orphaned (LM-1).
- **Mitigation:** (1) resolve the mapping in the live account; (2) bring the API custom domain into
  CDK OR script the base-path re-map into the deploy; (3) prefer a **retained logical id** so CFN
  updates in place rather than replacing; (4) run `cdk diff` and confirm **zero stateful/RestApi
  replacement** before applying.
- **Rollback:** keep the old RestApi live until the new one is verified; re-point the base-path
  mapping back on failure (seconds).
- **Verify:** after deploy, `curl https://api.dev.careervp.com/<health>` = 200 **and** an
  authenticated FE call from an `*.amplifyapp.com` origin succeeds.
- **Gate:** `pre_additive` — must precede P-09/P-14/P-17/P-21 (root at 415/500).

### P-10 · API GW CORS allow-list — 🔴 W2
- **Breaks because:** browser blocks any XHR whose origin isn't returned in `Access-Control-Allow-Origin`.
- **Mitigation:** allow-list = `["https://*.amplifyapp.com"]` (+ `https://dev.careervp.com`,
  `http://localhost:3000` for local). Add an IaC/oracle assertion that the Amplify origin is present
  (closes LM-2). Note the current header is "gated at Lambda layer" — keep the Lambda ACAO logic and
  the gateway list in sync.
- **Rollback:** revert to `ALL_ORIGINS` (flag or one-line) — instant.
- **Verify:** preflight `OPTIONS` from an `amplifyapp.com` origin returns that origin; real FE flow green.

### P-04 · Enforce the Cognito authorizer — 🔴 W3
- **Breaks because:** `AUTHORIZER_DISABLED="true"` means dev currently accepts un-validated requests;
  enforcing it 401s any path that doesn't attach/refresh a valid JWT.
- **Mitigation:** first run an **end-to-end token-flow audit** of the live FE (every fetch attaches
  `Authorization`; 401→silent-refresh→retry→sign-out works — contract item #10). Flip via the existing
  `AUTHORIZER_DISABLED` env as the reversible flag, in dev, watching CloudWatch 401 rate. Removing the
  `x-user-id` header path is independently safe (FE doesn't use it — verified).
- **Rollback:** set `AUTHORIZER_DISABLED="true"` again — instant, single env var.
- **Verify:** FE full session (login → generate artifact → hub read) green with authorizer ON.

---

## 6. Pre-Wave-1 blocker checklist (live-account, read-only)

Must be answered with evidence before deploying P-04/P-08/P-10/P-26:

- [ ] **LM-1:** How does `api.dev.careervp.com` resolve? (API GW custom domain? base-path mapping to
      which RestApi id? Route53 record?) → `aws apigateway get-domain-names`,
      `get-base-path-mappings`, `aws route53 list-resource-record-sets`.
- [ ] **LM-2:** Exact live Amplify origin(s) — the `*.amplifyapp.com` host + any custom domain →
      Amplify console / `aws amplify list-apps` + `list-branches`.
- [ ] Confirm whether any live path still verifies **RS256** tokens (before L-2 retire).
- [ ] Confirm the FE attaches a valid Cognito JWT on **every** call (before P-04 enforce).
- [ ] Confirm the P-07 MFA decision: **optional** (safe) vs **required** (needs FE challenge UI).

---

## 7. Recommended safe order (respecting the register)

1. **Zero-risk now:** Wave-0 nets (scope-diff.py, oracle, ledger), P-12, P-13, P-20, P-21 — no
   CORS/auth/domain surface. Build the **oracle first** (it's the net that guards F-fixes and LM-2).
2. **After LM-1/LM-2 closed with evidence:** P-08, P-10 (CORS, with the Amplify-origin assertion).
3. **After the token-flow audit:** P-04 (authorizer), behind the reversible `AUTHORIZER_DISABLED` flag.
4. **After the domain is in CDK or has a re-map runbook:** P-26.
5. P-07 as **optional** MFA unless/until the FE ships challenge UI.

> Nothing in Track D / Track Q generation quality touches the Amplify seam — those are backend/data
> and are guarded by characterization tests + the oracle. The site-down risk is concentrated in
> **P-26, P-10, P-04** (+ P-08 for CV files), and two of those depend on facts that live only in the
> AWS account, not the repo.
