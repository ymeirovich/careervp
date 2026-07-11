# CareerVP — Post-Completion Validation Checklist

- **Version:** 1.0.0 (for scope-lock v1.4.0) · **Created:** 2026-07-09
- **Purpose:** run this **after implementation** to prove the project is *complete and sound* — the
  mirror of the pre-execution eval council. Every check names **how it's verified**; per scope-lock
  §11, **never self-report** — verification comes from `recon.py`, `cdk synth/diff`, the F-01 oracle,
  the P-30 smoke harness, CI gate results, or a named live probe.
- **A domain is DONE only when its check passes on evidence, not because "the clause is implemented."**

---

## Part A — v1.4.0 gap closures (the orphaned requirements this round added)

| ☐ | Clause | Validation check | Verified by |
|---|---|---|---|
| ☐ | **P-27** stack policy + termination protection | `aws cloudformation describe-stacks` shows `EnableTerminationProtection=true`; a dry-run `Update:Replace` on a table/RestApi/Cognito is **denied** by the stack policy | live CLI probe |
| ☐ | **P-28** deploy identity split | The automation profile **cannot** `ExecuteChangeSet`/`UpdateStack` (denied); `app.py` **fails fast** when account≠788159322332 or region≠us-east-1 | IAM sim + unit test |
| ☐ | **P-29** evidence pack + backups | A **restore drill** re-creates golden state from the snapshot (incl. Cognito pool config); on-demand DDB backups exist for all 10 tables; upload bucket synced externally | integration/restore drill |
| ☐ | **P-30** deploy smoke harness | 4-wire probe green (health · OPTIONS+GET exact-origin echo · authed read · presigned upload) both **before and after** a deploy | smoke run |
| ☐ | **P-31** EventBridge DLQ | cleanup(1h) + reconcile(02:00) rule targets each have a DLQ with a depth alarm | `cdk synth` assertion |
| ☐ | **P-32** cost/obs hygiene | AWS Budget + Cost-Anomaly Detector exist; `Tags.of` applied app-wide; correlation-ID present in logs across a traced request | live CLI + log probe |
| ☐ | **Q-10** real token metering | token usage is **measured** (not `len/4`); cost-per-app metric emits; an anomaly alarm is wired — **and no Sonnet/Sonnet-5 cost decision was made before this landed** | unit + CloudWatch |
| ☐ | **Q-11** cost bounds | prompt-cache breakpoints set; artifact `max_tokens` bounded; Tavily input bounded — margin still >70% under load | cost test + eval |
| ☐ | **X-02** prompt-injection hardening | untrusted input (CV/JD/Tavily CR) is delimited in prompts; generated artifact fields are XSS-encoded before FE render; SSRF guard preserved — **Q-08 OWASP-LLM red-team finds no escape** | security test + red-team eval |

**Also confirm the earlier-found orphans stayed closed:** NFR-SEC-9→X-02 ✓, NFR-COST-1→Q-10 ✓,
NFR-COST-2→Q-11 ✓, NFR-DATA-2→P-29 ✓, NFR-REL-6→P-31 ✓, NFR-COST-3/OBS-3→P-32 ✓.
Re-run the crosswalk audit (`scope-diff.py` + the NFR-vs-clause diff) — **zero orphan NFRs** remaining.

---

## Part B — Overall certification (scope-lock §7.4 — DoD to stand up prod)

| ☐ | Gate | Verified by |
|---|---|---|
| ☐ | All **freeze-line** items closed (all Track-P T1 + all T2 + low-effort/high-value picks) | `scope-diff.py` status board = all `verified` |
| ☐ | All applicable **NFRs met** (no orphan NFR; each maps to a `verified` clause) | crosswalk audit |
| ☐ | Test suite **green with real key-schema coverage** (moto real schemas; autouse mock retired; branch coverage on) | CI |
| ☐ | Coverage gates met (core 85/80 · supporting 78/70 · overall 80/70) + `mutmut` spot-check on core | CI |
| ☐ | **F-01 executable oracle green** on all 10 frontend-contract items (incl. `vpr_id: null`-vs-absent, 409-on-stale-version) | CI + nightly Playwright |
| ☐ | 8 CI gates pass (ruff · mypy --strict · pytest · `cdk synth` <400 · Checkov · Bandit · pip-audit · CodeQL) | CI |
| ☐ | **`cdk diff` = zero stateful replacements** | CI |
| ☐ | No PR-block-list violation (§9.3) in the merged history | review |

---

## Part C — Soundness re-confirmation (mirror of the eval-council domains)

| ☐ | Domain | "SOUND" means |
|---|---|---|
| ☐ | **Architecture** | surrogate `user_id` resolution has no hot-path/linking hazard; `core` serves every access pattern with no unspecced Scan; CR-first has a defined failure/timeout path |
| ☐ | **Correctness / site-break** | the single most-likely site-break change (RestApi recreate / CORS / `artifact_id`) shipped without breaking the live FE — smoke + oracle green through the deploy |
| ☐ | **Security** | identity provably JWT-only on all 31 handlers; no cross-tenant IDOR; mock→Stripe swap has no webhook-verify bypass; KB recall tenant-filtered by key; **X-02 defenses live** |
| ☐ | **Cost / margin** | measured (not estimated) margin ≥ 70% under representative load; no decision rested on the retired `len/4` estimate |
| ☐ | **Spec / test quality** | the P-01 class of bug (3-schema routing) cannot recur — characterization + real-schema tests catch it; every named test type has a producing spec |
| ☐ | **Delivery** | executed solo without the amendment discipline breaking; nets (`scope-diff.py`, oracle) were live before mass authoring |

---

## Part D — The final "don't break the site" gate (run at every deploy, not just at the end)
- ☐ P-30 smoke harness green **before** the change (baseline captured).
- ☐ Change deployed via a **human-executed** change set (P-28); automation never executed it.
- ☐ P-29 evidence snapshot taken immediately before.
- ☐ P-30 smoke harness green **after**; full FE session incl. token refresh at the 1-hour boundary.
- ☐ Rollback lever **tested** (fire-drill RTO measured) before the real deploy of any 🔴/🟠 clause.

> Passing Parts A–D = the project is **sound and complete** to certify prod (§7.4). Any ☐ that
> can't be checked on evidence is a **NOT-DONE**, not a "probably fine."
