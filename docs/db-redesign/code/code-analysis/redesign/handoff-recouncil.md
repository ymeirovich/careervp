# Handoff — CareerVP: re-validate + re-run council against updated docs

Paste into a fresh **interactive** Claude Code session (claude-council needs an interactive
terminal). Model: Opus; effort **xhigh** for the council run, **high** otherwise. AWS CLI +
read-only creds are available — validate live, don't infer.

---

## Mission
Two source docs were updated after the last council run, so the council outputs and the
derived artifacts are **stale**. Your job:
1. **Review ALL source material** (list below).
2. **Re-assess and validate every assumption against the two updated docs + live AWS** — find
   where the updates contradict the derived artifacts and reconcile.
3. **Refresh the council inputs, then re-run claude-council** (both queries) and save updated
   outputs.
4. **Reconcile the derived register/requirements/features** with the refreshed evidence.

Do NOT re-derive from scratch — the analysis is mature. Diff, validate, update.

## What changed (treat as AUTHORITATIVE — reconcile everything else to these)
- **`redesign/db-upgrade-priorities.md`** (updated) — now carries the `core` table design
  (SK layout, AI-Assist write pattern, DRY-at-code-layer, hot-partition GSI-cardinality rule).
- **`redesign/aws-infrastructure-configuration-reference.md`** (updated, 53 KB — refined; note
  this is a NEWER copy than the older `code-analysis/aws-infrastructure-configuration-reference.md.md`).
First action: **read both in full, then diff them against the artifacts in "Derived" below** and
list every contradiction or new constraint before doing anything else.

## Source material (read in this order)
**Updated (authoritative):**
- `redesign/db-upgrade-priorities.md`
- `redesign/aws-infrastructure-configuration-reference.md`

**Best-practice rubric:** `~/Documents/code/best-practice/AWS_Serverless_Best_Practices.md` ·
`agentic-development-guide.{md,yaml}`

**Ground-truth evidence (verified live 2026-07-04):**
- `redesign/findings-register.md` — full scope (~70–90 findings) + **Live verification** section + CFN #8 fix design.
- `redesign/coverage-matrix.md` — functionality surface + **frontend can't-break contract**.
- `redesign/recon.py` — re-run to re-validate DB state: `AWS_PROFILE=… python3 recon.py --env dev`.

**Derived (reconcile these against the updates — may be stale):**
- `redesign/features.md`, `redesign/requirements.md`
- `redesign/context-pack.md`, `redesign/context-pack-rebuild-addendum.md` (council evidence — **regenerate/refresh before re-running council**)
- `redesign/council-prompt.md`, `redesign/council-prompt-rebuild.md`
- `redesign/.claude/council-cache/local-council-1783166912.md` (in-place, STALE) · `…1783171127.md` (rebuild, STALE)

**In-repo:** `docs/db-redesign/01-*.md` (routing/identifier dossier) · `docs/upgrade/specs/*`
(FE-UI-044 CR migration, TEST-DEBT-001, TEST-CHAIN-001) · the CDK under `infra/careervp/`.

**Prior analysis (context):** the 8 docs in `code-analysis/` (architecture-v2, deepdive,
redesign-runbook, rag, sonnet-migration, compression, v1). Older than the updates — do not
override the updated docs with these.

## Locked decisions (do NOT re-litigate — validate they still hold)
Keep DynamoDB → single-table `core` done once (in-place incremental, NOT parallel rebuild) ·
Cognito-only auth · paid launch (billing live) · frontend out-of-scope except API contract ·
**dev-only until prod certified** (no prod exists; prod is a future promote) · priorities H/M/L,
effort Lo/Md/Hi.

## Verified live ground truth (re-confirm with recon.py + CLI; flag any drift)
Acct 788159322332, us-east-1, dev+staging only. Deletion protection FALSE on all 10 tables;
PITR ON; tiny volume (users 908 / artifacts 221 / jobs 144 / rest <20; idempotency+knowledge
empty). Multi-schema drift physically present. API throttle 2 rps; WAF unattached; SNS 0 subs;
Cognito MFA OFF; 0/31 fns reserved concurrency; JWT keys in env on 6 fns; billing-reconcile
Handler `.handler`≠`lambda_handler`; StartVPR/StartCVTailoring no SFN heartbeat; root CFN
stack **415/500** resources, 4 nested. Frontend contract: external `application_id==job_id`;
hub `artifact_id` must resolve at status/patch/cancel; status enum additive-only; PATCH→409;
`request_id` primacy; internal PK free.

## Steps
1. **Read the two updated docs; diff against Derived artifacts; produce a "what changed / what
   contradicts" list.** This drives everything.
2. **Re-validate live** (recon.py + targeted read-only CLI). Confirm the ground truth above
   still holds; note drift. Never destructive.
3. **Refresh `context-pack.md`** (+ rebuild addendum) so council evidence reflects the updated
   docs + live state. Update `council-prompt.md` / `-rebuild.md` only if the framing changed.
4. **Re-run claude-council — but SCOPE it, don't blind-re-derive.** The prior councils are
   **local (same-model)** — their priors are shared, so a full blind re-run has low marginal
   value and just re-states the last outputs. Instead, refresh the council prompt to focus on:
   (a) **the deltas** — every place the two updated docs changed a constraint, severity, or the
   `core` design; and (b) **the unresolved high-stakes assumptions** the last councils flagged:
   is single-table `core` a COMMITTED deliverable or a hypothesis to re-justify after the cheaper
   decoupled seams (both councils demoted it to Med)? · identity keying (`cognito_sub` vs a stable
   internal `user_id`) · knowledge-base keep/drop · cutover/downtime tolerance + retention.
   If external providers are now configured, prefer a **cross-vendor** `--agents` run on those
   assumptions (higher signal than another local panel); else `--local --agents`, effort xhigh:
   - In-place: `/claude-council:ask "$(cat .../council-prompt.md)" --local --agents`
   - Rebuild:  `/claude-council:ask "$(cat .../council-prompt-rebuild.md)" --local --agents`
   Save outputs to `redesign/council-output.md` and `redesign/council-output-rebuild.md`
   (the `.claude/council-cache/*` files are the old runs — supersede them).
   **Acceptance gate:** accept a run ONLY if it meets the "Success criteria" block in the
   council prompt — especially (i) genuine dissent surfaced (zero disagreement on a same-model
   panel = re-run with sharper adversarial framing), (ii) no recommendation contradicts the
   live-verified ground truth unflagged, and (iii) a decisive answer on each high-stakes
   assumption. If a run fails the gate, re-run; don't accept a consensus-theater result.
5. **Reconcile** `findings-register.md`, `requirements.md`, `features.md` with the refreshed
   council + updated docs; flag any finding whose severity/priority/effort moved.
6. **Report** a concise change-log: what the doc updates changed, what live re-validation
   confirmed/contradicted, and the net delta to the register.

## Guardrails
Read-only AWS; never destructive; RETAIN + backup before any dev mutation. Don't break the
frontend contract. Local council = same-model panel → treat agreement as a prior to
pressure-test, disagreement as the signal. Cite `file:line`; validate, don't assert.
Goal after this: finalize understanding to begin writing tests + specs (see `handoff.md`).
