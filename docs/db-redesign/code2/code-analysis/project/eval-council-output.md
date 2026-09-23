# CareerVP Implementation-Plan Evaluation Council — Output

**Run:** 2026-07-11 (local council, 6 blind lenses, Fable 5 @ high effort)
**Subject:** scope-lock v1.3.0/v1.4.0 corpus + execution plan + test strategy + handoff + Q-gap exemplar
**Evidence baseline:** live-truth-2026-07-11 (415/500 deployed; register verified)

> **Local council** — these perspectives all come from Claude playing different
> roles, not from different AI vendors. Treat agreement as a shared starting
> point to pressure-test, not as independent confirmation.

---

## 🗳️ Lens 1: Architecture soundness (×2)

**Soundness verdict:** SOUND-WITH-CONDITIONS — the target design (surrogate `user_id`, seams-first staged collapse, S3-pointer + version-conditioned writes) is correct for <10k users, but the plan carries one technically false mitigation (P-26 "retained logical id"), leaves the failure mode of its own chain-reorder unspecced in the only authored exemplar, and keeps two load-bearing data-layer rules out of the contract.

### Hard questions

**Q(a) — surrogate `user_id` resolution on the hot auth path: hazard?** **Yes — latent, process-mitigated but not requirement-mitigated. Severity: Medium.**
The decision itself is sound (L-1, scope-lock §2; social IdP justifies not re-keying later). But the plan nowhere specs: (1) **where resolution lives** — Cognito authorizer is API-GW native, so `sub→user_id` must resolve in a shared layer across ~31 handlers or in a custom authorizer; neither is chosen (P-24 spec is TO-AUTHOR, execution-plan step 0.7); (2) **the brand-new-`sub` JIT-creation race** — two concurrent first requests for the same new `sub` (double-submit at signup, or social first-login) both create a `user_id` unless the mapping write is a conditional put; O-4's resolution (scope-lock §10, yaml P-24 `linking_policy`) covers *linking policy*, not *creation atomicity*; (3) **where the `sub→user_id` mapping itself lives** — it's per-user data but it is looked up *before* `user_id` is known, so it can't be keyed `USER#{user_id}` in `core`; the invariant list (§4, "shared data never in core") names CR-cache/LLM-cache/idempotency as the separate tables — the mapping table is unmentioned; (4) **caching** — a per-request DynamoDB lookup adds a hot-path dependency; authorizer result-cache TTL appears only in the register's Tier-3 tail (findings-register §Tier-3). Mitigation that does exist: P-24 is routed opus/xhigh with mandatory adversarial review (yaml P-24 note; §8.6 gate 4). Verdict: hazard is real but closable in the P-24 spec — condition, not a design flaw.

**Q(b) — does the `core` SK layout cover every live access pattern (61 resources + async)?** **Uncertain — mechanism exists, proof deferred, one pattern only obliquely covered. Severity: Medium.**
The layout (`db-upgrade-priorities.md:59`; findings-register Track D §2: `CV#{cvId}`, `APP#{appId}#ARTIFACT#{TYPE}#v{n}`, `APP#{appId}#GAPRESP#{qId}`) covers all user-scoped reads; billing-by-customer-id gets a GSI (D-H7/P-15); CR-cache stays out of `core` (§4 invariant). Two gaps: (1) **contract item #2** ("a hub `artifact_id` MUST be resolvable by the status endpoint," coverage-matrix §2.2) requires either an `artifact_id`-keyed GSI or an `artifact_id` that encodes `APP#…#TYPE#v{n}` — D-H4 stores the canonical id but no doc decides the lookup path; (2) the **hourly destructive `artifact_cleanup`** (coverage-matrix §1c) queries cross-user by status — needs the sparse in-flight index (see Q(c)). The plan's own answer is D-M6 (access-pattern inventory, Wave 3, before the Wave-6 collapse — sequencing is right), but D-M6's verification is just `doc` (yaml D-M6) with no acceptance criterion of the form "every live endpoint + async behavior maps to a documented Query, zero Scan" — so coverage is asserted-by-process, never proven. O-5 (jobs/applications fold) is correctly held OPEN.

**Q(c) — does the status/in-flight query respect the GSI-cardinality rule?** **Yes in the design docs, NO in the contract. Severity: Medium.**
The rule is explicit and correct — `db-upgrade-priorities.md:41`: "every GSI partition key must be user- or high-cardinality-scoped… or made sparse — no `STATUS#{status}` GSI PK"; echoed in findings-register Track D §2. But it appears **nowhere in the scope-lock**: §4's invariant list (yaml `invariants:`) has eleven entries and none is the GSI-cardinality rule; D-M3 covers projections only. Under the plan's own orchestration model, a fresh subagent gets "only that step's scope-lock clause + its spec + the few files it touches" (execution-plan "How to run this"; handoff §"WHAT THE AGENT DOES") — so the spec author for D-H8/Q-05/cleanup will never see a rule that lives in an authority-level-5 doc (scope-lock §0.2). A low-cardinality `STATUS#` GSI PK is exactly the natural implementation of the cleanup/in-flight query.

**Q(d) — CR blocking on submit: what happens when CR fails or times out?** **Yes, this is a real defect — the plan never answers it. Severity: High.**
L-5 (IMMUTABLE) says CR runs "on new-application submit, **to completion** — then gap." CR is a Tavily+LLM step (~15k tokens/gen, Q-09) with a known live reliability wart (CR queue visibility 120s < SFN heartbeat 180s — findings-register Tier-2). The **one authored spec — the exemplar for all ~20 others** — introduces the dependency (`Q-01`: "gap now declares CR as an upstream dependency," Q-gap spec §Q-01) and its three RED tests cover ordering, data-flow, and flag-reversibility — **but none covers CR failure/timeout** (spec `test_chain_runs_cr_before_gap` / `test_gap_receives_completed_cr` / `test_chain_reorder_is_reversible`). The prompt builder tolerates an absent CR block (Q-gap spec §Q-04: block "renders nothing — safe no-op"), so a degraded-proceed path is *cheap* — yet no clause, open question, or AC states the policy (proceed-degraded after N seconds vs. fail the chain). Trigger: Tavily outage or CR worker failure → every new-application submit stalls the entire artifact chain behind a dead dependency. This ships a bug the plan's own tests won't catch.

**Q(e) — does `UpdateItem`+`version` 409 hold for large-body-in-S3 artifacts?** **Yes, mechanically — with a hygiene residue. Severity: Low.**
`db-upgrade-priorities.md:31` specifies the correct order: write body to S3 first, then ONE conditional `UpdateItem` swapping pointer + bumping `version`; a losing concurrent editor gets the 409 (contract item #5) and readers never see a torn state because the pointer swap is atomic. Residue: (1) the loser's S3 blob is orphaned — and an orphan-pointer class already exists live (CV lifecycle 30d vs metadata TTL 90d, findings-register Tier-2), with no clause owning orphan hygiene; (2) the write-ordering discipline (S3-first, then conditional swap) lives only in the level-5 doc, not in the §4 invariant ("large bodies in S3 with a pointer" states *where*, not *how safely*). Echoing `result.*` on PATCH per contract #5 costs one S3 read-back — fine at <10k.

**Q(f) — is "seams now, physical collapse deferred" a safe resting state?** **Mostly yes — but the plan ignores that a DIFFERENT half-migration is already live and unclaused. Severity: Medium-High.**
The staged-committed structure (L-3, O-1 go/no-go, Wave 6 post-launch) is the right solo-dev shape: the seams (D-H2/H4/M2/M5) capture the correctness value at the code layer, and the multi-table layout with one key-authority is a coherent permanent state. The hole: coverage-matrix §3 records the **FE-UI-044 CR canonical-store migration as partial and in-flight** (dual-write + backfill of 239 items `users-table → artifacts-table`; "Current state = partial migration; **finish** and extend the pattern"). **No clause in the scope-lock owns finishing it** — Track D has D-H2/H3/H4/H7/M1-M6/Q/H6/H8, none is "complete FE-UI-044 backfill + retire the legacy dual-read." The `users-table` (908 items) still mixes `PROFILE + ARTIFACT# + CV` collections (live-truth §1). An unowned dual-read fallback is precisely the 3-schema-drift class that produced P-01 — so the plan's resting state is safe *except* for the half-migration it inherited and never scheduled.

### Findings

**F1 — P-26's "retained logical id" mitigation is technically false; the clause bakes in a site-break path** · type: architecture
- **Evidence:** scope-lock P-26 / yaml P-26 note ("RestApi recreate can change invoke URL → mitigate via retained logical id or custom domain+ACM"); Fable digest §8 (blue/green, "never move the RestApi"); findings-register §CFN-headroom #3; coverage-matrix §2 (FE → `NEXT_PUBLIC_API_URL`); findings-register Tier-2 ("Custom domain/ACM on the API (frontend has one; API doesn't)"); live-truth §2 (415/500).
- **Failure it causes:** breaks the site. Moving the `RestApi` into a nested stack is a cross-stack move — plain CloudFormation deletes the resource in the parent and creates a new one in the child regardless of logical ID; the `execute-api` URL changes, and the Amplify frontend (URL baked in `NEXT_PUBLIC_API_URL`) dies against 908 live dev users. A retained logical id only protects *within* one stack. Note also: Fable's alternative ("re-point the base-path mapping") silently assumes a custom domain that does **not exist yet** — so *both* written strategies are incomplete as stated.
- **Recommended fix:** amend P-26 to a mandatory two-phase strategy: (1) **custom domain + ACM first** (small, additive, reversible; frontend repointed once to the stable domain via one Amplify env change + smoke via P-30); (2) then stand up the **new RestApi born inside its own nested stack** (blue), verify via P-30's 4-wire harness against the raw invoke URL, flip the domain mapping, retire the old API from the parent in a later deploy (green). This also solves headroom arithmetic: a second 175-resource API cannot coexist in the 415/500 parent (live-truth §2), so blue must be a nested stack anyway. Drop "retained logical id" from the clause text.
- **Amendment?** **y** — P-26 (TARGET, `contract_impact: true`), **MINOR** (refines a TARGET's mitigation; no contract item changes — the URL flip is exactly the "version/stable-handle" discipline). Adversarial review required (contract-touching, §0.3). Flag: this *partially adopts* the Fable blue/green over the contract's nest-in-place, consistent with live truth (415 baseline confirmed; ordering conclusion unchanged).
- **Scores:** Importance **Critical** · LOE **M** · Difficulty **Med**.

**F2 — L-5's blocking CR-first chain has no failure/timeout policy, and the exemplar spec omits it** · type: architecture / correctness
- **Evidence:** scope-lock L-5 ("to completion — then gap"); Q-gap spec §Q-01 (three RED tests, none for CR failure); Q-gap spec §Q-04 (absent-CR renders nothing — proving degraded mode is cheap); findings-register Tier-2 (CR queue visibility 120s < SFN heartbeat 180s); Q-09 (~15k Tavily tokens/gen).
- **Failure it causes:** ships a bug — Tavily outage or CR worker death stalls every new-application submit behind a dead upstream; the interactive gap-questions UX (FE 3s polling, coverage-matrix §2.4) never progresses. The plan's own acceptance tests would pass while this bug ships.
- **Recommended fix:** add a failure-policy AC to the Q-01 slice of the exemplar spec now (before step 0.4 clones its shape 20 times): CR is a *soft-blocking* dependency — on CR `failed`/timeout > N seconds, gap proceeds degraded (empty CR block) and the application status surfaces CR's failure additively; add RED tests `test_chain_cr_failure_degrades_not_blocks` and `test_chain_cr_timeout_policy`. Record N as a new open question or decide it at step 0.0.
- **Amendment?** **y** — MINOR: add an acceptance rider to Q-01 (and a sentence to L-5's clause text clarifying "to completion **or documented degraded fallback**"). L-5 is IMMUTABLE, but this *refines* the decision's failure semantics rather than reversing CR-first — still route it through §0.3 with adversarial review since it touches a locked decision.
- **Scores:** Importance **High** · LOE **S** · Difficulty **Low**.

**F3 — The GSI-cardinality rule is not in the contract the subagents will actually read** · type: architecture
- **Evidence:** `db-upgrade-priorities.md:41` (the rule); scope-lock §4 / yaml `invariants:` (absent); execution-plan §"How to run this" (fresh subagent gets clause + spec + touched files only); coverage-matrix §1c (cleanup job queries by status).
- **Failure it causes:** ships a bug / blows margin at scale-up — a fresh subagent authoring the Q-05/D-H8/cleanup spec from its clause alone naturally builds a `STATUS#{status}` GSI PK, concentrating all completed items on one partition; per the brief's own framing this is the classic latent flaw that surfaces approaching 10k users.
- **Recommended fix:** add invariant to §4/yaml `invariants:`: `gsi_pk_user_or_high_cardinality_scoped_or_sparse_never_status`.
- **Amendment?** **y** — MINOR (adds a clause/invariant; changes no existing decision; it promotes an already-documented rule to contract level).
- **Scores:** Importance **High** · LOE **S** · Difficulty **Low**.

**F4 — The in-flight FE-UI-044 CR migration has no owning clause: the plan schedules the *next* migration while leaving the *current* one half-done** · type: architecture / delivery
- **Evidence:** coverage-matrix §3 ("finish and extend… rather than starting over"); scope-lock Track D (no completion clause); live-truth §1 (`users-table` 908 items, mixed collections, drift physically present).
- **Failure it causes:** ships a bug / stalls delivery — the legacy dual-read fallback in the DAL persists indefinitely; that fallback family is the root of the 3-schema drift that broke cover-letter/interview-prep (P-01). It also silently violates the plan's own read-switch discipline ("read path switched … before backfill+reconciliation complete" is a §9.3 PR-block item, yet the half-completed state is nobody's job).
- **Recommended fix:** add clause D-H9 "Complete FE-UI-044 CR canonical-store migration: verify backfill of 239 legacy items, dual-read parity, then retire the legacy `users-table` CR read path" — slot into Wave 3 (natural neighbor of D-M2/D-M5), reusing the migration-parity test type already in the taxonomy (test-strategy §2.7).
- **Amendment?** **y** — MINOR (adds a clause).
- **Scores:** Importance **High** · LOE **M** · Difficulty **Med**.

**F5 — P-24 resolution architecture unspecced: locus, JIT-creation atomicity, and the mapping table's home** · type: architecture / security
- **Evidence:** scope-lock L-1, P-24 (spec TO-AUTHOR); yaml P-24 `linking_policy` (policy only, no atomicity/locus); scope-lock §4 (mapping table absent from the "stays separate" list); findings-register Tier-3 (authorizer cache TTL relegated to hygiene).
- **Failure it causes:** breaches a tenant / ships a bug — a non-atomic JIT create under concurrent first-requests yields two `user_id`s for one human (split tenant data, permanent); an unconsidered per-request lookup makes the mapping table a single point of failure on every one of ~31 handlers.
- **Recommended fix:** constrain the P-24 spec (step 0.7) to answer four questions explicitly: (1) resolution in a shared auth layer with a memoized/authorizer-context cache; (2) JIT create via `attribute_not_exists` conditional put, loser re-reads; (3) mapping lives in its own small table (or a `sub`-keyed GSI) — name it in §4's separate-tables list; (4) cache-invalidation on link events (O-4 audit log is the hook). No contract change needed — this is spec-content discipline; add the four items to P-24's yaml `note` so the fresh subagent sees them.
- **Amendment?** **n** (PATCH-level note enrichment at most; no invariant or decision changes).
- **Scores:** Importance **High** · LOE **M** · Difficulty **Med**.

**F6 — D-M6 has no "Scan-free coverage proven" acceptance, so access-pattern completeness is asserted, never demonstrated** · type: architecture / spec-test
- **Evidence:** yaml D-M6 (`verification: doc`); coverage-matrix §1a (61 resources) + §1c (async/scheduled); contract item #2 (status-endpoint resolvability) with no decided lookup path.
- **Failure it causes:** ships a bug at Wave 6 — the collapse go/no-go (O-1) can pass while an access pattern (status-by-`artifact_id`, cleanup-by-in-flight) still needs a Scan or an unplanned GSI, discovered mid-migration.
- **Recommended fix:** strengthen D-M6 acceptance: "every endpoint in coverage-matrix §1a + every async/scheduled behavior in §1b/§1c maps to a named Query/GSI (zero Scan), including status-endpoint resolution of a hub `artifact_id` and the sparse in-flight index"; make it a hard dep of D-H8 in the yaml.
- **Amendment?** **y** — MINOR (refines a TARGET's acceptance).
- **Scores:** Importance **Med** · LOE **S** · Difficulty **Low**.

### Blind spots

1. **Frontend repoint is out-of-scope by C-6 but required by P-26.** Any URL-stabilization path ends in an Amplify env change + rebuild (`NEXT_PUBLIC_API_URL`) — a frontend deliverable the contract's C-6 nominally excludes. Nobody owns that step; it should be named in the amended P-26.
2. **Orphaned S3 bodies from losing conditional swaps** join the already-live orphan-pointer class (CV lifecycle 30d vs TTL 90d, findings-register Tier-2); no clause owns pointer/blob hygiene, which slowly erodes the "store rich, project lean" invariant.
3. **Interactive-latency budget of CR-first is never stated.** Even in the success path, gap questions now wait on Tavily; no NFR bounds submit→questions latency, so there is no number against which the L-5 reorder can be judged a UX regression.
4. **The `sub→user_id` mapping is a new pre-auth hot-path table** that appears in no capacity, alarm, or backup clause (P-29's snapshot list predates P-24's table existing).

### Dissent

- **vs. the contract (P-26):** the "retained logical id" mitigation is not a conservative option — it is a false one; leaving it as clause text invites the exact site-break the clause exists to prevent. I would not start Wave 0 step 0.65 until F1's amendment lands.
- **vs. the Fable evidence:** I adopt its "never move the RestApi in place" *direction* but reject its recipe as-written — "re-point the base-path mapping" presupposes a custom domain the live system does not have (findings-register Tier-2), and its 476/500 figure is wrong per live truth (415/500 deployed; live-truth §2 flagged and followed here). Its headroom urgency framing survives anyway: ~85 slots with P-09/P-14/P-17/P-21 all additive.
- **vs. the likely majority:** I expect other lenses to concentrate on "1 of 21 specs" as the plan's biggest risk. From the architecture chair, the sharper problem is that the **one spec that exists — the exemplar every other spec will imitate — omits the failure semantics of the very dependency it introduces (F2).** Scaling a flawed exemplar 20× is worse than having 20 unwritten specs; fix the exemplar before step 0.4 fans out.
- **Partial dissent from the plan's self-assessment of L-3:** "seams first" is sold as a production-ready resting state, and structurally it is — but only if the inherited FE-UI-044 half-migration is finished (F4). As written, the resting state quietly contains exactly the kind of dual-read limbo the staged strategy claims to avoid.

---

## 🗳️ Lens 2: Correctness & the site-break gap (×2)

**Soundness verdict:** SOUND-WITH-CONDITIONS — the deploy-safety architecture is genuinely encoded as clauses (P-27..P-30, P-12-first), but the contract's own P-26 text directs the single action most likely to take the site down (an in-place RestApi stack-move whose written mitigation, "retained logical id," is fictional under CFN semantics), and two enforcement holes (CI auto-deploy-on-push; all-10 oracle assertions deferred to Wave 4) mean "don't break the UI" is asserted, not yet provable, when the risky work runs.

### Hard questions

**Q(a): The single change most likely to break the live site on deploy — NAMED: executing P-26 as the contract writes it ("nest the whole RestApi ~175 resources → 1").** Call: **yes, this is the top site-breaker.** Evidence: scope-lock P-26 (`project-scope-lock.md:138`; YAML line 102: *"mitigate via retained logical id or custom domain+ACM"*); execution-plan step 0.65 (`redesign-execution-plan.md:118`). CFN resource identity is *(stack, logical id)* — moving a RestApi into a nested stack is **always delete+create in one update, and the old API is deleted in that same update's cleanup phase**, so "retained logical id" cannot preserve the invoke URL and "keep the old API live until verified" is unachievable in a single-stack update (`fable-infra-mitigation-plan.md:31,161,191` — a CFN-semantics claim, verifiable independent of live state; I accept it). **Blast radius: total.** Every FE call dies at once — all 10 contract items simultaneously, all 908 live dev users (`live-truth-2026-07-11.md` §1). Because `NEXT_PUBLIC_API_URL` is baked into the Next.js bundle at Amplify build time (`fable-infra-mitigation-plan.md:210`), recovery is a full Amplify rebuild (tens of minutes) unless a custom domain + base-path mapping fronts the API — a fact the plan never verifies before 0.65. Secondary risk: a failed update on a 415-resource stack can wedge in `UPDATE_ROLLBACK_FAILED` (`fable-infra-mitigation-plan.md:158`). Runners-up — the three-layer CORS change (P-10, breaks the site but revertible in minutes) and the P-01/D-H4 `artifact_id` fix (Wave 3, guarded by seams) — are an order of magnitude smaller. **Severity: Critical.**

**Q(b): Are the Fable deploy-safety gates encoded as actual clauses/steps?** Call: **yes for the core five, no for four load-bearing ones** — see tension 5 resolution below. Stack policy + termination protection = **P-27** (scope-lock:139, step 0.55), credential split + human-only `ExecuteChangeSet` + account/region pin = **P-28** (scope-lock:140, step 0.55), evidence pack + backups = **P-29** (scope-lock:141, step 0.61), 4-wire smoke harness = **P-30** (scope-lock:142, step 0.62), RETAIN-first = **P-12** at step 0.6. That is real encoding, not aspiration (v1.4.0 change-log row, scope-lock:315). **Missing:** (1) closure of `deploy.yml` auto-deploy-on-push with `cancel-in-progress:true` (digest §deploy-pipeline-risk; `fable-infra-mitigation-plan.md:163`) — no clause; (2) P-08-before-P-10 pilot ordering + pre-staged inverse change set + max-age→60s (digest §7; `fable-infra-mitigation-plan.md:128,130`) — step 1.3 (`redesign-execution-plan.md:126`) bundles P-07/P-08/P-10/P-11 into ONE "mechanical sonnet/med" step; (3) P-04 flip-then-remove + runtime-read lever (tension 3); (4) codified GatewayResponse ACAO `'*'` exception + fix of the poisoned `cors-no-wildcard.regression.test.ts` exemplar (`fable-infra-mitigation-plan.md:102`). **Severity: High.**

**Q(c): Is "don't break the UI" provable — does the F-01 oracle assert all 10 items?** Call: **no, not as sequenced (uncertain by Wave 4).** The design intends it — test-strategy §4 explicitly names all 10 incl. `vpr_id: null`-vs-absent and 409-on-stale (`test-strategy.md:70-77`) — but step 0.3 builds only an oracle *skeleton*, while **F-06 (encode all 10 as executable assertions) lands at step 4.8, Wave 4** (`redesign-execution-plan.md:110,160`; YAML wave_4 list line 173). Meanwhile the contract-touching steps 3.2 (D-H4 + P-01, both `contract_impact:true`) run in **Wave 3**. The wave-gate rule "oracle green on every touched contract item" (`test-strategy.md:92-95`) is vacuous for items with no assertion yet. Additionally, behavioral items — #1 (`application_id == job_id` value equality), #5 (409 on stale), #6 (`request_id` primacy) — are not provable by Zod/Pydantic schema comparison alone; they need the MSW/Playwright behavioral legs, which no step gates before Wave 3. **Severity: High; cheap fix (reorder).**

**Q(d): Which clauses are `contract_impact:true`, and does each have a versioning/back-compat plan?** Call: **five clauses; 3 adequate, 1 unsound, 1 underspecified.** From the YAML: **P-01** (line 77 — fixes *toward* contract item #2; §8.6 gate 2 forces its spec to carry the FE-contract slice — adequate once specced), **P-25** (line 101 — "preserves FE checkout/portal URL contract" — adequate), **P-26** (line 102 — back-compat plan half-fictional per Q(a) — **unsound as written**), **D-H4** (line 112 — no explicit statement that *previously-issued* `artifact_id`s held by open FE sessions/polling loops keep resolving through the key migration; contract item 2 requires it; dual-read guardrail §9.2 implies but never states it — **underspecified**), **D-H8** (line 121 — Wave 6, O-1-gated, migration-parity verified — adequate). The silent-shape-change risk is not in these five: it is step 1.3's CORS sweep breaking contract **item 10's 401→refresh→sign-out path** invisibly (401s become CORS-opaque, `error.response === undefined`) — a break no schema oracle sees. **Severity: High.**

### Tension resolutions (decisive)

- **Tension 1 (415 vs 476):** **415/500 is the truth**; live `list-stack-resources` on 2026-07-11 confirms it (`live-truth-2026-07-11.md` §2); Fable's 476 is rejected as a non-deployed (likely synth-with-additions) figure. Consequence: **P-26 keeps its "before P-09/P-14/P-17/P-21" gate but loses any emergency urgency** — ~85 slots of headroom means the Wave-0 sequencing (safety gates 0.55–0.62 *before* P-26 at 0.65) is correct and must not be compressed. **No register amendment needed** — the register already says 415 and was re-verified (`findings-register.md:39-47`); the scope-lock's `current_state: root_415_of_500` is accurate. No change.
- **Tension 2 (nest vs blue/green):** **Blue/green is decisively safer and is the only correct option**; the contract's "nest the RestApi + retained logical id" is not merely riskier — it is *impossible to execute safely* (delete+create in one update) and is even **self-contradicted by the plan itself**: P-27's stack policy denies `Update:Replace` on the RestApi (scope-lock:139), and §9.3 hard-rejects "big-bang cutover with no canary/flag/rollback" (scope-lock:291) — P-26-as-written violates both. **Yes, it is one amendment away:** P-26 is `TARGET`, so a **MINOR** amendment (refine a TARGET; adversarial review required since it's contract-touching) rewriting it as "decompose *around* the RestApi (feature Lambdas/alarms into nested stacks); if API-GW count must shrink, stand up a NEW RestApi in its **own stack** (never inside the 415-resource parent — +175 would breach 500), verify via raw `execute-api` URL, human-only base-path re-map, retire the old API in a later gated deploy; precondition: read the P-29 evidence pack to confirm what `NEXT_PUBLIC_API_URL` actually points at."
- **Tension 3 (dead `AUTHORIZER_DISABLED`):** The zero-readers claim is code-verified at the branch by Fable (`fable-infra-mitigation-plan.md:158,187`) but **still open against live** (`live-truth-2026-07-11.md` §3). Ruling: **P-04's safety does not rest on the dead lever — it rests on nothing.** The clause (scope-lock:116) is titled *remove* the switch and provides **no revert lever at all**; if the flag is dead, removing it is a no-op, but removing the `x-user-id` fallback (the real enforcement change on a live site) leaves revert = git-revert + 15–30 min redeploy of a 415-resource stack. That is a plan defect: an auth-enforcement flip on a live frontend with no instant rollback and no soak. Fix in the P-04 spec: (1) resolve both live-truth §3 open items first (`get-method` authorizationType + repo grep); (2) flip-then-remove sequencing behind a runtime-read kill switch; (3) 401-rate soak ≥24h (bump access-log retention first); (4) fire-drilled, measured revert RTO.
- **Tension 5 (missing gates):** **Resolved: the plan encodes the big five (P-27, P-28, P-29, P-30, RETAIN-first P-12) as real clauses with Wave-0 steps** — this tension is largely already closed by v1.4.0. The genuinely missing clauses are: **(i)** deploy-pipeline closure (branch-protect main, required-reviewer GitHub environment, `concurrency max=1` without cancel-in-progress — without it, `deploy.yml` auto-executes every merged infra change, making P-28's "human-only ExecuteChangeSet" a dead letter); **(ii)** P-08-before-P-10 split + pre-staged inverse change set; **(iii)** the P-04 runtime-lever rework; **(iv)** the GatewayResponse ACAO `'*'` keep-exception + poisoned-test fix; **(v)** a `detect-stack-drift` pre-deploy gate (so an emergency out-of-band revert isn't silently stomped by the next deploy).

### Findings

**F1 — P-26 as contracted is a same-deploy replacement of the live API** · *correctness/site-break*
- **Evidence:** scope-lock P-26 (`project-scope-lock.md:138`, YAML:102); step 0.65 (`redesign-execution-plan.md:118`); CFN semantics + refutation at `fable-infra-mitigation-plan.md:31,161,191`; self-contradiction with P-27 (scope-lock:139) and §9.3 (scope-lock:291).
- **Failure:** breaks the site — executing 0.65 as written deletes the RestApi the frontend calls in the same update; recovery = Amplify rebuild (URL baked at build) or emergency base-path re-map; wedged-stack risk on a 415-resource template. Trigger: the first `ExecuteChangeSet` of step 0.65.
- **Fix:** amend P-26 to decompose-*around* + blue/green-in-separate-stack + human base-path re-map + retire-later (text in tension 2); gate on evidence-pack read of `NEXT_PUBLIC_API_URL`.
- **Amendment?** **y** — P-26, **MINOR** (refines a TARGET; contract-touching → adversarial review per §0.3).
- **Scores:** Critical · M · Med.

**F2 — CI auto-deploy voids P-28's human-only execute gate** · *correctness/deploy-safety*
- **Evidence:** Fable digest §deploy-pipeline-risk (`fable-findings-digest.md:22-23`); `fable-infra-mitigation-plan.md:163`; P-28 (scope-lock:140); P-22 (scope-lock:134) covers OIDC only.
- **Failure:** breaks the site / wedges the stack — a merge to main batch-deploys accumulated infra changes with no human execute; a second merge **cancels a CFN update mid-flight**. Trigger: any two merges during a wave.
- **Fix:** extend P-28 (or add P-33): branch-protect main; GitHub `dev` environment with required human reviewer; `concurrency: group=deploy, max=1` and remove `cancel-in-progress`; home it in step 0.55.
- **Amendment?** **y** — P-28 note extension, **MINOR**.
- **Scores:** Critical · S · Low.

**F3 — F-06 (all-10 oracle assertions) lands a wave after the contract-touching work** · *correctness*
- **Evidence:** step 0.3 "skeleton" vs step 4.8 (`redesign-execution-plan.md:110,160`); Wave-3 step 3.2 ships `contract_impact:true` D-H4/P-01 (`redesign-execution-plan.md:146`; YAML:77,112); gate rule `test-strategy.md:92-95`.
- **Failure:** ships a bug that breaks the FE — a Wave-3 shape/id regression passes a "green oracle" that simply has no assertion for the touched item (esp. items 1, 3, 5). Trigger: step 3.2 merge.
- **Fix:** merge F-06 into step 0.3 (skeleton → full 10-item assertions incl. behavioral 409/null-vs-absent legs), or add "F-06 verified" as a Wave-3 entry dep.
- **Amendment?** **y** — wave re-assignment lives in scope-lock §7.2/YAML waves → **MINOR** (no clause scope change).
- **Scores:** High · S · Low.

**F4 — Step 1.3 bundles the CORS blast radius into one "mechanical" step; ACAO `'*'` exception uncodified** · *correctness/site-break*
- **Evidence:** `redesign-execution-plan.md:126`; P-10 (scope-lock:122); Fable P-08-first + inverse-change-set + max-age (`fable-infra-mitigation-plan.md:128,130`); ACAO-`'*'`/poisoned-test (`fable-infra-mitigation-plan.md:102`); contract item 10 (`coverage-matrix.md:112-113`).
- **Failure:** breaks the site invisibly — tightened GatewayResponse ACAO makes every 401 CORS-opaque, killing the FE's 401→refresh→sign-out path (users see hangs); a wrong allow-list downs all API calls with only a minutes-scale redeploy revert. Trigger: one sonnet/med subagent doing a "remove all wildcards" sweep in 1.3.
- **Fix:** split 1.3 → 1.3a P-08 (pilot, seconds-revert) → 1.3b P-10 (preconditions: runtime preflight probe green, pre-staged inverse change set, max-age→60s first) → 1.3c P-07/P-11; add to P-10's clause note: "GatewayResponse ACAO `'*'` is a codified exception — keep"; fix the poisoned regression test before spec fan-out.
- **Amendment?** **y** — P-10 note, **MINOR**; step split is a runbook edit.
- **Scores:** High · S · Low.

**F5 — P-04 has no rollback lever (the presumed one is likely dead wiring)** · *correctness/deploy-safety*
- **Evidence:** P-04 (scope-lock:116); zero-readers claim `fable-infra-mitigation-plan.md:158,187`; unverified live per `live-truth-2026-07-11.md` §3.
- **Failure:** breaks the site — auth enforcement flips on a live FE and the only revert is a 15–30 min full redeploy at incident time; or the removal is planned around a lever that never worked. Trigger: step 1.1 deploy with a token-flow edge (e.g., refresh at 1h expiry) unhandled.
- **Fix:** P-04 spec preconditions: resolve both live-truth §3 opens; flip-then-remove with a runtime-read kill switch; ≥24h 401-rate soak; fire-drilled measured RTO before the forward deploy.
- **Amendment?** **y** — P-04 note ("flip-then-remove; runtime lever precondition"), **MINOR**.
- **Scores:** High · M · Med.

**F6 — Evidence pack and smoke baseline sequenced AFTER the first change-set execution** · *correctness/deploy-safety*
- **Evidence:** step 0.6 (P-12 deploy) precedes 0.61 (P-29, deps: 0.6) and 0.62 (P-30, later row) (`redesign-execution-plan.md:114-116`); Fable requires snapshot + baseline-green before *any* change (`fable-findings-digest.md:41-43`).
- **Failure:** stalls delivery / masks a break — the first real deploy (RETAIN flip) runs with no golden snapshot and no smoke baseline; if it misbehaves there is no "before" to compare against. Trigger: step 0.6.
- **Fix:** re-dep 0.61 and 0.62 on 0.55 and run both before 0.6 (runbook-only edit; low-risk deploy, but the discipline must start at deploy #1).
- **Amendment?** n (execution-plan ordering only).
- **Scores:** Med · S · Low.

**F7 — D-H4 back-compat for already-issued `artifact_id`s is implied, never stated** · *correctness*
- **Evidence:** D-H4 (YAML:112, `contract_impact:true`); contract item 2 (`coverage-matrix.md:88-92`); §9.2 dual-read guardrail (scope-lock:284).
- **Failure:** ships a bug — an open FE session's 3s polling loop feeds a pre-migration `artifact_id` to the status endpoint and gets 404 after the canonical-key switch. Trigger: step 3.2 cutover with live sessions.
- **Fix:** D-H4 spec AC: "every `artifact_id` issued pre-migration resolves via the status endpoint post-migration (dual-read until contract phase)"; add a legacy-id probe to the oracle.
- **Amendment?** n (spec-level; clause already carries the intent).
- **Scores:** Med · S · Low.

### Blind spots

1. **Nobody has verified what `NEXT_PUBLIC_API_URL` points at** (custom domain vs raw `execute-api` URL) — the single fact that sets P-26's blast radius from "seconds re-map" to "full Amplify rebuild." P-29 captures Amplify env, but no step *gates P-26 on reading it*. Add as an explicit 0.65 precondition.
2. **The oracle is schema-shaped; the Wave-0/1 break classes are wiring-shaped** (CORS, auth, base-path mapping). F-01 cannot see them; P-30 is the only net and its 4 wires omit a full FE session including token refresh at the 1-hour expiry boundary — the exact edge Fable flags for P-04 revert verification.
3. **No measured redeploy RTO exists** (live-truth §3 open) — every rollback story in plan and evidence quotes estimates; a solo operator's incident math needs a measured number (fire-drill once in Wave 0).
4. **Cognito pool locality during decomposition** is never stated as an exclusion: step 0.7 touches `cognito_construct.py` right after 0.65; a pool move = unrecoverable loss of all 908 users (no password-hash export). P-27 pins it; the P-26/P-24 specs must also explicitly forbid moving it.

### Dissent

- **Against the Fable evidence:** its 476/500 figure is wrong for the deployed stack (live truth: 415) and its urgency framing is overblown; I also decline its "P-26 last, after P-04" sequencing as a hard rule — with 85 slots of headroom and blue/green in a separate stack, P-26's position in Wave 0 is acceptable so long as F4's CORS pilots and the smoke baseline precede it; the binding constraint is only "before P-09/P-14/P-17/P-21," exactly as the contract already says.
- **Against the plan:** its own §9.3 PR block-list already outlaws what P-26's clause text instructs — the contract disagrees with itself, and P-27's stack policy would (correctly) refuse the deploy. That is a defect to amend, not a reason to distrust the whole deploy-safety design.
- **Against the likely-majority view:** the headline risk here is *not* "missing deploy-safety gates" — v1.4.0 genuinely closed the big five as clauses with Wave-0 steps, and a lens that re-litigates tension 5 as open is fighting the previous version of this plan. The live risks are one wrong clause text (P-26), one enforcement hole that makes P-28 decorative (CI auto-deploy), and one timing hole (F-06 in Wave 4). All three are cheap, MINOR-semver amendments — this is a conditions list, not a NOT-SOUND.

---

## 🗳️ Lens 3: Security soundness

**Soundness verdict:** SOUND-WITH-CONDITIONS — the core known vulns (P-04/05/06/08/10/11, X-02, Q-05) each have an owning clause, but three named security risks have **no spec that provably closes them** (all-31-handler JWT-only is asserted not proven; the Cognito `COGNITO_ADMIN`-scope/implicit-grant sub-finding is orphaned inside P-07; the real-provider webhook-signature path is only ever tested against a self-signing mock), and the auth-enable wave ships before its rollback lever exists.

### Hard questions

**Q(a): Is identity provably JWT-only on all 31 handlers after P-04/P-05? — NO. High.**
The invariant "IDOR structurally impossible… DAL enforces the tenant partition key" (scope-lock §4; yaml `invariants.dal_enforces_tenant_partition_key_no_idor`) is the *goal*, but the structural mechanism — the single key-authority repository (D-H2) — lands in **Wave 3** (execution-plan step 3.1), while P-04/P-05 land in **Wave 1** (step 1.1). So between Wave 1 and Wave 3, IDOR is closed **per-handler imperatively**, not structurally. Worse, P-05's scope is written as `"get_job & peers"` (scope-lock P-05; yaml `P-05`) — "peers" is never enumerated. There is **no checklist mapping all 31 Lambdas to an owner-check assertion**, and the only cross-tenant test is described singularly ("cross-tenant isolation negative test", test-strategy §9/§2 row 10; coverage-matrix §4), not per-handler. "IDOR-by-construction" is therefore asserted, not provable, and a handler missed by "& peers" ships an IDOR. Severity High.

**Q(b): Does surrogate `user_id` + link-by-verified-email leave an account-takeover path? — UNCERTAIN (residual path). Med-High.**
The O-4 policy (scope-lock O-4; yaml `P-24.linking_policy`) — auto-link only when `email_verified=true AND email matches`, else step-up, `conflicts→earliest-created user_id`, audit-logged — closes the naive case and mandates an adversarial review (§8.6.4). Two residual vectors are un-analysed: (1) it **trusts the IdP's `email_verified` claim** with no IdP allow-list — a provider that asserts `email_verified` loosely (historically Facebook) becomes a takeover primitive; (2) the **`earliest-created user_id` conflict rule is itself a pre-emption weapon** — an attacker who pre-registers with a victim's email owns the merged identity when the victim later signs up via another method. No spec closes either; they must be named edge cases in the P-24 adversarial refuter. Severity Med-High.

**Q(c): Does the mock payment provider bake in a signature-verification bypass? — YES. High.**
P-25 (scope-lock P-25; yaml `P-25`, `note`) has the `MockProvider` "sign test webhooks + return realistic objects," and `StripeProvider` is **deferred with no clause and no wave**. Nothing requires the Mock's `verify_webhook` to implement a real HMAC check that *fails* on a bad signature, so the contract/idempotency tests (execution-plan 2.0/2.1) can pass against a Mock whose verify is effectively a no-op — the genuine signature-verification code path is never exercised. Then L-4 declares "billing live = launch-critical (paid launch)" (scope-lock L-4) and P-25 is in the freeze line — but the freeze line ships the **Mock**, and the real provider's signature verification would be new, **untested code on the money path** at go-live. This is both a security bypass risk and an internal inconsistency (paid launch with a mock provider). Severity High.

**Q(d): Is KB/PFACT cross-tenant recall enforced by key? — YES for the MVP; UNCERTAIN for Phase 2. Med.**
Q-05 MVP puts PFACT items in per-user `core` (`PK=USER#{user_id}`), so the recall Query is partition-scoped **by key** — structurally tenant-isolated, consistent with the invariant `shared_data_never_in_core` (yaml `invariants`) and verified with a mandatory data-spec adversarial refuter (Q-05 `verification: security`; §8.6.4). Sound. Phase 2 (Q-06, S3 Vectors top-K, OPEN O-6, post-launch) is the risk: a global vector index with a *post-retrieval* tenant filter leaks cross-tenant neighbours. The invariant says "tenant-filtered," but the Q-06 spec must enforce isolation **by namespace/partition, not a metadata post-filter** — currently unspecified. Severity Med (post-launch, gated).

**Q(e): Is prompt-injection / artifact XSS (NFR-SEC-9) owned by a spec or orphan? — OWNED. Low-Med.**
X-02 is a real clause (scope-lock X-02; yaml `X-02`), homed at execution-plan step 4.9 with a TO-AUTHOR spec, defense = delimit+XSS-encode+SSRF-guard, test = Q-08 OWASP-LLM red-team + a SAST negative (test-strategy §9b). Not an orphan. Caveat: the XSS **sink is in the frontend** (`dangerouslySetInnerHTML`-class rendering), which is out of scope (C-6) and unasserted by the oracle (F-01 checks shapes, not encoding) — so backend encoding is owned but end-to-end XSS closure is not provable from this plan. Severity Low-Med.

**Q(f): Is keeping `GatewayResponse` ACAO `'*'` exposure-free? — YES. Low (with a site-break caveat).**
GatewayResponses are emitted by API-GW for auth/4xx errors *before* the integration runs, so they carry no tenant data; the API is already publicly reachable, and the app uses Bearer headers (not cookies), so `'*'` without `Allow-Credentials` is not a readable-data exposure (Fable digest §three-layer-CORS is correct here). The real hazard is a **site-break, not exposure**: P-10 ("API GW CORS `ALL_ORIGINS` → allow-list", scope-lock P-10) does not explicitly say to **preserve** `GatewayResponse '*'` while tightening integration responses — tighten it and every 401 becomes CORS-opaque to the browser (breaks contract §10's "401 → one silent refresh-retry"). P-30's OPTIONS+GET exact-origin smoke wire (scope-lock P-30) is the runtime guard. Severity Low.

### Findings

**F-SEC-1 — "All 31 handlers JWT-only" is asserted, never enumerated or tested per-handler** · security
- **Evidence:** scope-lock P-05 (`"get_job & peers"`); yaml `P-05`; invariant lands only with D-H2 (execution-plan 3.1, Wave 3) two waves after P-04/P-05 (Wave 1, 1.1); only a single "cross-tenant isolation negative test" exists (test-strategy §2 row 10, §9; coverage-matrix §4).
- **Failure it causes:** ships an IDOR — a handler outside the undefined "& peers" set keeps a client-supplied-id path and leaks another tenant's data (breaches a tenant).
- **Recommended fix:** P-05 spec must carry the **explicit list of all 31 handlers** (from CDK `route_map` recon) with a per-handler owner-check assertion, and the security suite must run a **parametrized cross-tenant negative over every handler**, gated in CI. Add to the Wave-1 GATE.
- **Amendment?** n (spec/runbook fix — strengthens, does not change, the invariant).
- **Scores:** Importance High · LOE M · Difficulty Med.

**F-SEC-2 — Cognito `COGNITO_ADMIN` scope + implicit grant on a public SPA client is orphaned inside P-07** · security
- **Evidence:** finding #7 (findings-register §Security, `cognito_construct.py:27,44,47`) names `implicit_code_grant` + `COGNITO_ADMIN` scope on a public SPA client; P-07's title/scope is only "Cognito MFA + advanced security (ATP)" (scope-lock P-07; yaml `P-07`) — the grant-type and scope fix is not stated anywhere.
- **Failure it causes:** privilege escalation — a public-client user token with `COGNITO_ADMIN` scope can call Cognito admin APIs; implicit grant leaks tokens in URLs. The P-07 spec author reads "MFA+ATP" and drops the fix → the vuln ships. Per the brief's rule, a named risk with no owning spec = NOT-SOUND for that risk.
- **Recommended fix:** amend P-07 to explicitly own **migrate `implicit_code_grant` → authorization-code + PKCE** and **remove `COGNITO_ADMIN` from the SPA client's scopes**; carry both as `AC-###` in the P-07 spec with an IaC assertion.
- **Amendment?** y — P-07 (TARGET), **MINOR** (refine a TARGET's scope); why: expands a clause's stated scope to cover a named sub-finding, no invariant change.
- **Scores:** Importance High · LOE S · Difficulty Low.

**F-SEC-3 — Webhook signature verification only ever tested against a self-signing mock; no clause owns the real-provider path before paid launch** · security
- **Evidence:** P-25 `MockProvider` self-signs (scope-lock P-25 `note`; yaml `P-25`); `StripeProvider` "deferred… swap behind config later" with **no clause, no wave**; L-4 "billing live = launch-critical (paid launch)"; freeze line = "all Track-P T1" ships the Mock (scope-lock §7.3; yaml `freeze_line`).
- **Failure it causes:** ships a bug on the money path — the real provider's signature verification is untested code at go-live; a forged/replayed webhook that the Mock's lax verify accepted now hits production (double-grant / fraudulent subscription). Also an internal inconsistency: a "paid launch" whose freeze-line payment is a mock earns no money.
- **Recommended fix:** (1) P-25 spec must require the Mock's `verify_webhook` to implement a **real HMAC check that rejects a tampered signature** (so the negative test is meaningful); (2) add a clause **P-25b — StripeProvider + signature-verification + idempotency test, in the freeze line before paid launch**.
- **Amendment?** y — add **P-25b** (new TARGET clause), **MINOR** (add a clause); why: closes the launch-critical money-path security gap without touching an invariant.
- **Scores:** Importance High · LOE M · Difficulty Med.

**F-SEC-4 — Auth-enable (P-04/P-05) ships before its rollback lever; no safe revert for a mid-migration auth lockout** · security/delivery
- **Evidence:** P-04 removes `AUTHORIZER_DISABLED` (scope-lock P-04; Wave 1, execution-plan 1.1); P-23 alias+version+CodeDeploy canary/rollback is **Wave 2** (execution-plan 2.5); Fable digest §revised-sequence rebuilds P-04's flag as a real runtime lever + a ≥24h 401-rate watch — the execution plan encodes **neither**; live-truth §3 leaves "does `AUTHORIZER_DISABLED` have readers" unverified.
- **Failure it causes:** availability + security regression — if surrogate `sub→user_id` resolution (P-24) mis-resolves for some subs when strict auth turns on, the 908 dev users get 401 with **no fast revert** (Fable: "instant revert" is really a 15–30 min redeploy), and the only quick "fix" would be re-introducing a bypass (a security regression). Dev-only (C-7) bounds the blast radius.
- **Recommended fix:** move **P-23 (canary/alias rollback) into Wave 1 ahead of P-04/P-05**, so auth enforcement rolls out behind a canary with auto-rollback on a 401-rate alarm — do **not** rebuild `AUTHORIZER_DISABLED` as a lever (that re-creates the bypass). Add a 401-rate CloudWatch alarm to the P-04 spec's DoD.
- **Amendment?** n (runbook re-sequencing — wave order lives in the plan, not an invariant).
- **Scores:** Importance Med · LOE S · Difficulty Low.

**F-SEC-5 — KB Phase 2 (Q-06) vector tenant isolation unspecified (post-launch)** · security
- **Evidence:** Q-06 S3 Vectors top-K, OPEN O-6, Wave 6 (scope-lock Q-06; yaml `Q-06`); invariant says "tenant-filtered index" (yaml `invariants.vectors_derived…tenant_filtered`) but does not specify by-key vs post-filter.
- **Failure it causes:** cross-tenant recall leak — a global vector index with a post-retrieval tenant filter returns another user's nearest-neighbour PFACT content. Post-launch/gated, so lower urgency.
- **Recommended fix:** O-6 resolution + Q-06 spec must mandate **per-tenant namespace/partition isolation in the vector store (by key, not metadata post-filter)**, with an adversarial data-spec refuter (§8.6.4).
- **Amendment?** n (resolve OPEN O-6 + spec fix; MINOR only when O-6 is recorded).
- **Scores:** Importance Med · LOE M · Difficulty Med.

### Blind spots

- The plan counts "31 handlers" but never lists them anywhere in the corpus; the security guarantee's denominator is unenumerated, so "provably closed" is unfalsifiable as written.
- **Authorization vs authentication** is conflated: P-04/P-05 prove *who* the caller is and *ownership* of a row, but nothing checks **per-route scope/role** (e.g. a trial user hitting a paid-only generate route) — server-side quota (§9.2) is mentioned but no clause owns authz-by-plan negatives.
- The **XSS sink is out of scope (C-6, frontend)** — backend encoding (X-02) is owned but end-to-end XSS is unprovable from this backend-only plan; the oracle (F-01) validates shapes, not encoding.
- **Audit-log integrity** for the account-link events (O-4) is assumed but no clause specs where/how the audit log is stored tamper-evident.
- SSRF guard (X-02) is "preserve + test," but there is no spec asserting the Tavily/CR fetch path's allow-list — "preserve" assumes a guard that recon never confirmed exists.

### Dissent

- **Against Fable's "human executes every `ExecuteChangeSet`" as the security control (tension 4):** for a solo dev the human *is* the author, so the human gate is self-review — it is **not** the real net. The genuine net is the **agent adversarial-refuter** (§8.6.4) for auth/IAM/data specs, which is real independent analysis. I dissent from treating P-28's human-only execute as sufficient security assurance; it is fine for a **dev-only** proving ground (C-7) but must be re-examined before prod certification, because a fatigued solo approver of P-09 (one-role-per-fn) or P-24 (auth) is exactly where an over-broad role or a takeover edge case slips through. The plan should state this downgrade explicitly rather than inherit Fable's team-of-2-3 assumption.
- **Against the plan's implicit "P-04 kills the bypass, done" (tension 3):** removing `AUTHORIZER_DISABLED` is correct security, but the plan treats it as a clean cleanup while Fable treats it as a rollback lever. Both are half-right: it *should* be deleted (it's a bypass), but its deletion must be **paired with a real rollback mechanism (P-23 canary), sequenced first** — which the plan does not do. I side with neither wholesale: delete the lever, but do not enable strict auth until the canary/alarm rollback exists.
- **Against the register/Fable on urgency framing:** live-truth confirms 415/500 and dev-only, so I do **not** inflate these findings to launch-blockers-today; but F-SEC-2 (COGNITO_ADMIN) and F-SEC-3 (real-provider signature test) **are** freeze-line blockers for a *paid* launch and must not be deferred with the collapse work.

---

## 🗳️ Lens 4: Cost / margin soundness

**Soundness verdict:** SOUND-WITH-CONDITIONS — the plan is unusually honest that the ~88% margin is an unmeasured 2-sample estimate and sequences real metering (Q-10, Wave 2) ahead of the big cost decisions, but one cost-raising decision (L-6 Gap→Sonnet) is already locked and contract-exempted from that gate, the digest/cap numbers are asserted rather than sized, and ">70% margin" has no priced denominator anywhere in the contract — so the margin claim survives on structural headroom, not evidence.

### Hard questions

**Q(a) — which plan decisions are load-bearing on the ~88% / 2-Haiku-sample figure?** — **Yes, four are identifiable; call: yes (severity: High for L-6, Medium for the rest).**
- **L-6 / Q-03 (Gap→Sonnet)** — a *locked, IMMUTABLE* decision (scope-lock §2 L-6) approved before any real measurement exists; §6.3 explicitly exempts it ("Gap→Sonnet (Q-03) is separate and approved") from the very gate Q-10 imposes on Sonnet-5. Reversing it later is a MAJOR amendment (§0.3 semver).
- **L-5 / Q-01 (CR-first, unconditional per submit)** — makes a ~15k-token Tavily+LLM step (scope-lock Q-09) run to completion on *every* application submit, whether or not downstream artifacts are generated. Its economics rest on the same unmeasured base plus the unresolved O-2 cache-granularity question (§10), which directly sets the CR reuse rate.
- **Q-04/Q-05 (CR+KB into 4 consumers)** — justified as margin-safe only via "per-step digests" and a "1,200-token cap" that are themselves unmeasured.
- **The Sonnet-5 migration** — correctly load-bearing *and correctly gated*: §6.3 gates it on "real-token measurement," and the YAML Q-10 note (project-scope-lock.yaml:133) says "no cost decision may rest on that until real metering lands."
The one decision *not* really load-bearing is the DB-side deprioritization ("infra is a rounding error," context-pack.md:82-84): at live volumes of 221 artifacts / 908 users (live-truth §1), on-demand DynamoDB is cents regardless of whether the margin is 88% or 60% — that framing is robust even if the sample-of-2 is wrong.
Sensitivity check from the corpus's own numbers: VPR ≈ $0.43/app at 74% of AI spend → total AI ≈ $0.58/app; ~88% margin implies ≈ $4.80/app revenue; the 70% floor tolerates ≈ $1.45/app — roughly **2.5× headroom**. Sonnet-for-gap + unconditional CR + KB injection plausibly consumes a large slice of that, and the headroom figure itself is built on `len/4` (context-pack.md:394: "Real VPR economics unmeasured (2 cost samples, both Haiku); every Sonnet figure estimated").

**Q(b) — does Q-04 (CR+KB into gap/vpr/cover/interview) blow the token budget; is the digest + 1,200-cap sized from data?** — **Uncertain; the numbers are hand-waved, but the blow-out is bounded. Severity: Medium.**
- Not sized from data: the 1,200-token cap (scope-lock Q-05) has no provenance anywhere in the corpus, and Q-04's "per-step digests" carry **no number at all** — the exemplar spec says only "Project via a digest to protect margin (C-2)" (Q-gap-analysis-track-spec.md:76) and its RED test asserts merely "truncated/digested under the cap" (spec line 82) without defining the cap per consumer. Each of the 4 consumers' digest size will be decided ad hoc by a fresh implementing subagent.
- Bounded nonetheless: the cap test exists, Q-11 bounds output `max_tokens` and Tavily input, Q-09 truncates CR, and the Q-03 done-when requires "margin still >70% with the digest inputs from Q-04" (spec line 65). Since wave gates are hard barriers and Q-10 (Wave 2) precedes Wave 4, that check *can* run on measured tokens. So it's blow-out-resistant, not blow-out-proof — the risk is slow token creep across 4 consumers, not a single catastrophic step.

**Q(c) — real token metering (retire `len/4`) BEFORE the Sonnet routing + Sonnet-5 decisions?** — **Yes on sequencing, no on the routing *decision*; call: yes-with-caveat. Severity of caveat: Medium.**
- Sequencing holds: Q-10 is Wave 2 step 2.6 (execution-plan:139), explicitly "before any Sonnet-routing / Sonnet-5 cost decision (Wave 4)"; Sonnet-5 is gated on measurement (scope-lock §6.3); wave gates are hard barriers, so Wave-4's Q-03 implementation runs after metering exists.
- Caveat 1: the Gap→Sonnet *decision* was made and locked (L-6) pre-measurement, and the plan's own Haiku-vs-Sonnet value measurement is explicitly **"separate, non-blocking"** (Q-gap spec line 63). The gate protects Sonnet-5 but was waived for Sonnet-4.6 routing.
- Caveat 2: step 2.6's dependency is `2.0` (the payment port) — token metering has no technical dependency on a payment port; this spuriously delays the single most decision-critical instrument while 908 real dev users (live-truth §1) generate unmetered spend, with a *known* duplicate-AI-spend defect live (findings-register #18, visibility ≈ 1× timeout) and no budget alarm until P-32 in **Wave 5**.

**Q(d) — GSI-`ALL`→minimized and Scan-elimination: specced clauses or aspirational?** — **Yes, actual clauses; call: yes. Severity: Low (residual caveats only).**
- Scan-elimination: **P-15** (billing money-path Scan, T1, Wave 2 step 2.1, verification: integration) and **D-H7** (request-path Scans, T1, Wave 3 step 3.3) — both in the YAML backlog with `verification` fields and runbook steps; specs on the TO-AUTHOR list (execution-plan:181-184).
- GSI minimization: **D-M3** (yaml:116, `ALL`→minimized, verification: iac) homed at step 3.4. Caveats: (i) it is tier **T3** — below the freeze line only via the "low-effort/high-value picks" clause, so it could legitimately slip to post-launch (defensible: it's write/storage amplification on a tiny table — margin-irrelevant at this scale); (ii) it is double-homed (step 3.4 *and* Wave-5 step 5.3 "minimized GSI") — a small internal inconsistency; (iii) like all 20 unauthored specs, "specced" today means clause + step, not a written spec.

### Findings

**1. L-6 (Gap→Sonnet) is exempted from the metering gate its own contract created** — *cost*.
- **Evidence:** scope-lock §2 L-6 (IMMUTABLE) + §6.3 "Gap→Sonnet (Q-03) is separate and approved"; Q-gap spec line 63 marks the Haiku-vs-Sonnet value measurement "separate, non-blocking"; yaml Q-10 note (line 133): "no cost decision may rest on that until real metering lands."
- **Failure it causes:** blows margin — if measured Sonnet gap-generation cost erases the ~2.5× headroom, the plan discovers it *after* implementation, and undoing a locked decision costs a MAJOR amendment + adversarial review, which under solo time pressure invites the §9.3 anti-pattern (rubber-stamping what got built).
- **Recommended fix:** make the Q-03 eval blocking: done-when adds "measured (Q-10) cost-per-gap under Sonnet keeps cost-per-app ≤ X" with a named rollback trigger (router flips back to Haiku via `TaskMode` config — cheap, already flag-shaped).
- **Amendment?** y — §6.3 / L-6 note: "approved, subject to a post-Q-10 measured margin check with a defined revert lever"; **MINOR** (refines a locked decision's gate without changing the decision).
- **Scores:** High · S · Low.

**2. Per-step digest budgets are unspecified; the 1,200-token cap has no provenance** — *cost / spec-test*.
- **Evidence:** scope-lock Q-04 ("per-step digests to protect margin" — no number) and Q-05 ("1,200-token cap" — no derivation anywhere in the corpus); Q-gap spec lines 76-82 (digest mandated, size undefined; RED test asserts only "under the cap").
- **Failure it causes:** blows margin slowly / ships a quality bug — four fresh subagents each pick their own digest size (token creep ×4 consumers), or over-truncate and destroy the quality lift that justified L-5/L-6's cost in the first place. Trigger: step 0.4 mass spec authoring, where each spec inherits the hand-wave.
- **Recommended fix:** one solo-friendly measurement task after Q-10 lands (run ~10 real applications, take p95 CR/KB injected-token counts), then write a per-consumer token-budget table into the Q-04/Q-05 specs; RED tests assert the *numbers*, not "under the cap."
- **Amendment?** n for the budget table (spec-level); y-**MINOR** only if the 1,200 figure in clause Q-05 changes.
- **Scores:** Medium · S · Low.

**3. Budgets/Cost-Anomaly (P-32) sits in Wave 5 while a known duplicate-AI-spend defect runs unmonitored on 908 real users** — *cost*.
- **Evidence:** P-32 homed Wave 5 (scope-lock §7.2, execution-plan step 5.2); findings-register #18 ("visibility ≈ 1× function timeout → mid-flight redelivery → duplicate AI spend", fixed only in Wave 2 P-18); live-truth §1 (908 users, active dev traffic); SNS 0 subscribers until step 0.63.
- **Failure it causes:** blows margin (or the personal AWS bill, C-8) before the plan ever reaches its own cost wave — a retry storm or runaway chain burns unbounded LLM spend with zero alarm for the entire Waves 0–4 duration. This is the classic named-risk-without-an-early-owner: the *clause* exists but its wave placement doesn't cover the exposure window.
- **Recommended fix:** split the AWS Budgets + Cost-Anomaly slice out of P-32 into the Wave-0 "5-min-today" human-run block (alongside P-27) — it's a console task, perfectly solo-friendly; leave tagging/correlation-ID/validators in Wave 5.
- **Amendment?** y — rehome the P-32 budgets slice to Wave 0 in `path_to_production.waves`; **MINOR** (wave rehoming, precedent: v1.4.0 did exactly this for P-27..P-30).
- **Scores:** High · S · Low.

**4. Q-10 is needlessly gated behind the payment port, delaying the instrument every cost decision depends on** — *cost / delivery*.
- **Evidence:** execution-plan step 2.6 `Deps: 2.0`; nothing in Q-10 (metering, cost-per-app metric, anomaly alarm) requires the payment provider port; §7.1 ordered gate 5 ("token/cost measurement baseline") has no Wave-0 step, only this Wave-2 one.
- **Failure it causes:** stalls the margin evidence base — the baseline that Waves 3–4 changes should be measured *against* starts accumulating late; if Wave 1 slips, the Sonnet-5 intro-pricing window (2026-08-31, §6.3 — 7 weeks from today) can lapse before any measured data exists, silently killing an option the contract explicitly wants preserved.
- **Recommended fix:** drop the 2.0 dep and pull step 2.6 into Wave 0/1 (it is pure Python instrumentation, no CFN template contention); add the 2026-08-31 date as an explicit deadline note on the Sonnet-5 gate.
- **Amendment?** y — move Q-10 from `wave_2` to `wave_0/1` in the YAML waves; **MINOR**.
- **Scores:** Medium · S · Low.

**5. ">70% margin" is unfalsifiable: the contract has a cost numerator and no revenue denominator** — *cost*.
- **Evidence:** C-2 (scope-lock §1); Q-10 defines cost-per-app + anomaly alarm but no price input; gap-closure-checklist line 54 requires "measured margin ≥ 70% under representative load" with no source for the price; no clause anywhere records pricing/plan revenue (billing clauses P-25/P-02 are mechanics, not price).
- **Failure it causes:** ships an unverifiable gate — at certification time the solo dev cannot compute margin from anything in the contract, so the C-2 check either gets skipped or eyeballed, and the whole lens's guarantee reduces to vibes. Trigger: Wave-5/certification.
- **Recommended fix:** record price-per-app (or per-subscription ÷ expected apps) as a named constant in the Q-10 spec and derive the anomaly-alarm threshold from it (cost-per-app > 0.30 × price ⇒ alarm).
- **Amendment?** n (spec-level; add to Q-10's TO-AUTHOR spec).
- **Scores:** Medium · S · Low.

**6. Stale freeze-line enumeration excludes Q-10 (and all non-P T1 clauses) from the launch freeze as written** — *cost / traceability*.
- **Evidence:** scope-lock §7.3 "Freeze = all Track-P T1 (P-01..P-24) + all Tier-2..." — the parenthetical predates v1.4.0's P-25..P-30 and, read literally, excludes Track-Q/T/F T1 clauses; Q-10 is tier T1 (yaml:133) but is neither "Track-P T1" nor "Tier-2." yaml `freeze_line.include: [all_track_P_T1, all_T2, ...]` has the same hole.
- **Failure it causes:** blows margin at launch — a literal reading lets the freeze be declared with real token metering never landed, i.e., a paid launch certified against a margin figure still resting on `len/4`. (gap-closure-checklist line 54 partially backstops this, but the checklist is not the contract.)
- **Recommended fix:** amend §7.3 / `freeze_line.include` to "all T1 (any track) + all T2 + picks" and delete the stale "(P-01..P-24)".
- **Amendment?** y — **PATCH** (clarification/enumeration fix, no scope change; arguably MINOR if treated as widening the freeze set — propose PATCH with the rationale that T1 = launch-blocker by definition §0.4).
- **Scores:** Medium · S · Low.

**7. CR margin guard (Q-09) lands after the reorder that multiplies CR volume (Q-01)** — *cost*.
- **Evidence:** execution-plan Wave 4: step 4.4 (Q-01 CR-first) precedes step 4.5 (Q-07/Q-09 CR margin guard) in numeric order, and 4.4 does not depend on 4.5; Q-09 is T3 (yaml:132).
- **Failure it causes:** blows margin transiently — every submit triggers an untruncated ~15k-token CR ingest during the window between 4.4 and 4.5; small at dev scale, but it is exactly the pattern that goes to paid launch if 4.5 slips below the cherry-pick line.
- **Recommended fix:** swap the order (4.5 before 4.4) or add 4.5 to 4.4's deps — one runbook line.
- **Amendment?** n (runbook edit; wave membership unchanged).
- **Scores:** Low · S · Low.

### Blind spots

- **The cache-hit assumption is already falsified live.** context-pack.md:82-84 names "cache hit-rate" as half the margin lever, yet live truth shows `llm-cache` at **0 items with PITR disabled** (live-truth §1 — items TTL-expired from 11 to 0). Whatever cache offset is baked into the ~88% estimate is currently delivering nothing, and Q-11's prompt-cache breakpoints have no hit-rate measurement or eval anywhere in the plan. Prompt-cache writes are not free — un-hit breakpoints are a net cost increase, and no clause would ever detect that.
- **Dev-token spend vs product-token spend are conflated nowhere and separated nowhere.** Q-10's cost-per-app metric should tag traffic origin; otherwise the solo dev's own eval/test generation (Q-08 golden sets, promptfoo runs, mutmut-adjacent reruns) pollutes the margin baseline it is supposed to establish.
- **O-2 (CR cache-key granularity) is the largest single cost dial in Track Q** (company-only = max reuse vs company+role = min reuse) and the plan treats it purely as a correctness open question — no clause asks for the reuse-rate/cost delta to be part of the O-2 decision brief handed to the human.
- **No cost dimension in the §8.6 spec acceptance gate:** a spec can pass all five checks (structural, contract, self-sufficiency, refuter, test-validity) while being token-profligate; nothing forces a C-2 acceptance criterion into non-Q-track specs that add LLM calls.

### Dissent

- **Against the likely-majority "2 Haiku samples ⇒ margin claim unsound":** I disagree that this alone justifies NOT-SOUND. The plan self-diagnoses the weakness in the contract itself (Q-10 note, yaml:133), sequences metering ahead of the gated decisions, and the estimate carries ~2.5× headroom to the 70% floor by the corpus's own arithmetic. The genuine defect is narrower: *one* pre-approved exemption (L-6) and a late safety blanket (P-32) — both cheap to fix. Grading the whole cost domain NOT-SOUND would be hedging toward drama, not evidence.
- **Against the Fable evidence's relevance to this lens:** its effort scoring inflates *delivery* cost, and adopting its extra gates wholesale (evidence packs, fire drills, blue/green P-26) adds solo-dev time that is real but is **not** C-2 margin — C-2 is product COGS, and infra remains a rounding error at 221 artifacts. Any council member arguing the Fable gates threaten the >70% margin is conflating payroll with unit economics.
- **Against the plan's own emphasis:** the contract spends nine clauses (P-27..P-32, Q-10, Q-11, X-02) closing NFR orphans, yet the cheapest cost control of all — an AWS Budget with an alarm, a 15-minute human console task — was left in Wave 5 behind ~40 steps. For a solo dev on a shared personal account (C-8) with a live duplicate-spend defect, that is the wrong risk ordering, and I'd flag it even if every token estimate turns out generous.

---

## 🗳️ Lens 5: Spec & test quality

**Soundness verdict:** SOUND-WITH-CONDITIONS — the method (contract→spec→TDD + nets + characterization-first + real-key-schema testing) is genuinely aimed at the failure class that produced P-01, but the guarantee rests on one exemplar that violates the plan's own mandated format, a spec-acceptance gate whose test-validity check cannot run at acceptance time, and two named test types (migration-parity, load/perf) that no spec will produce.

### Hard questions

**Q(a): Is the Q-gap exemplar genuinely self-sufficient (§8.6 claim)? — NO** (severity: High).
Line-level audit of `project/specs/Q-gap-analysis-track-spec.md`:
- **It fails the mandated format it exemplifies.** Scope-lock §8.5 (project-scope-lock.md:263-268) mandates frontmatter `scope_lock_clause: Q-02` + top-level `claude_code:{model,effort}` + `codex:{...}`, and a spec body with "`AC-###` Given/When/Then". The exemplar has a **list-valued** `scope_lock_clause: [Q-01, Q-02, Q-03, Q-04]` (spec:7), a nested `tooling:` map instead of the mandated keys (spec:9-13), and **zero `AC-###` sections anywhere in the body** — it has "RED tests" + "Done-when" instead. §8.6 gate 2 ("the spec's `AC-###` do not contradict the clause") therefore has *nothing to check* against the exemplar, and `scope-diff.py` (specced to scan frontmatter for `scope_lock_clause`, execution-plan:188-190) has an unspecified behavior on list values.
- **Undefined load-bearing terms.** Q-04's fix is "set `job_posting['company_research'] = <digested CR>`. Project via a digest to protect margin" (spec:76) — no digest algorithm, no field projection, no token cap for CR (the 1,200 cap at spec:77 applies only to KB), and no metering method (Q-10 hasn't retired `len/4` yet). The RED test `test_gap_cr_kb_injection_respects_token_cap` (spec:82) asserts "truncated/digested under the cap" with the cap undefined — a fresh subagent picks its own cap and the test passes tautologically.
- **Ambiguous assertions.** `test_gap_missing_cv_errors_not_stub` accepts "a `cv not found` error response **(or logged fallback)**" (spec:44) — an OR in an assertion means two contradictory implementations both pass; it also contradicts fix step 3 ("do **not** silently ship the stub", spec:37). "Return a 404-style error" (spec:37) never states the envelope shape (contract item 10) or status code.
- **Q-01 is explicitly not copy-paste.** "Investigate before designing the GREEN change" + a list of things to go research (spec:91-94) directly contradicts the plan's claim that "Specs are copy-paste: a fresh subagent executes the Fix Plan + RED tests verbatim, no interpretation needed (this is also the §8.6 self-sufficiency acceptance check)" (execution-plan:59-60). The one hard clause *inside the exemplar* already broke the model.
- **Tribal pointers:** `format_note: "follows docs/upgrade/specs convention"` (spec:14) references a convention defined in the careervp repo, not in the corpus; `ProfileRecallService` (spec:77) is an invented interface named nowhere else. Q-03's "Option B is the fallback if the router migration is deferred" (spec:57) leaves a decision with no decider.
Q-02/Q-03 are *close* to self-sufficient (excellent file:line evidence, exact test names/assertions) — but the §8.6 claim as stated ("zero further questions") is false for the spec as a whole.

**Q(b): With 1 of 21 specs written, does the pattern scale? — NO (unproven)** (severity: High).
- The exemplar is called "proven" (scope-lock §8.5:261; test-strategy §7:99) but **nothing has ever been implemented from it** — zero red-green cycles have run. By the plan's own test-validity standard (§8.6 gate 5), it is unproven.
- The exemplar's quality derives from a completed multi-week analysis corpus (findings-register, dossier, coverage-matrix) that produced its rich `file:line` evidence. Step 0.4's fresh authoring subagents get "only that step's scope-lock clause + spec + the few files it touches" (execution-plan:19-21) — for thin clauses (D-H4: one line + `contract_impact: true`, yaml:112; P-09; Q-05) there is no comparable evidence base; clause-note richness varies by an order of magnitude across the 74-clause YAML.
- The 20 unwritten specs concentrate in exactly the class (P-26 CFN decomposition, P-24 identity surrogate, P-25 payment port, F-01 oracle, D-H8) where the exemplar's own hard clause (Q-01) already degraded into a research brief.
- The nets don't rescue quality: `scope-diff.py` is structural only (frontmatter present, no orphan/uncovered — §8.6 gate 1); it proves a spec *exists*, not that it is implementable. Gates 3 (self-sufficiency) and 4 (refuter) are LLM judgments with no required recorded artifact.
- A live inconsistency will fork the fan-out on day one: **handoff.md:60-61 still instructs authoring with "copy-paste `prompt:` blocks"** — residue of the v1.3.0-retired format — contradicting §8.5 and the exemplar. Handoff is the *first* doc pasted into the orchestrator.

**Q(c): Do coverage tiers + mutmut + characterization-first catch the P-01 class? — YES, with conditions** (severity of conditions: Med).
P-01 slipped because the autouse `mock_artifact_dependency_resolver` neutralized ~30 handler tests, branch coverage was 0, and the 78.45% line figure was vanity (coverage-matrix §1d:70-74). The plan attacks each root cause by name: T-02 retires the autouse mock and drives real key schemas via moto (yaml:137); T-01 enables branch coverage; characterization pins the routing/gate path at `4f7c294` "where the P-01 defect lives" (test-strategy §1:22-23); integration tests "assert ONE stored key, not three" (test-strategy §2 row 4); contract items 2/3 (hub `artifact_id` resolvable; `vpr_id` semantics) become executable assertions (F-06); mutmut catches non-asserting tests. That is a precisely aimed program. **Conditions:** (1) the F-01 oracle alone would NOT catch P-01 — MSW shape-validation cannot prove the backend *resolves* an id (MSW mocks the backend); resolvability needs the whole-chain-to-persisted-result integration test, which today lives only in a **debt list** (test-strategy §9:154-155) with fuzzy clause ownership (T-04, verification: "ci"), not in any named spec. (2) mutmut is deferred to Wave 5 (step 5.4) while §8.6 gate 5 cites it as part of spec/test acceptance from Wave 0 — a sequencing contradiction that means the check that "validates the tests themselves" arrives after Waves 1–4 are implemented.

**Q(d): Which named test types will NO spec produce?**
- **Migration-parity — NO producing spec before Wave 6 → NOT-SOUND for this risk** (severity: High). The taxonomy scopes it to "Track D seams, Wave 6 core collapse" (test-strategy §2 row 7), but the only clause carrying `verification: migration-parity` is D-H8 (yaml:121) — Wave 6, post-launch, OPEN. Wave-3 steps move live data *pre*-launch (D-M5 retire-userEmail-PK, D-M2 stop dual-key CV write, D-H4 canonical `artifact_id`; execution-plan 3.2-3.4), against a dev table holding 908 real users (live-truth §1). No spec, step, or clause owns building the "dual-read comparison harness."
- **Load/perf — NO producing spec → NOT-SOUND for this risk** (severity: Med). P-20's `verification: iac+load` (yaml:96) gestures at it, but P-20 is a sonnet/med mechanical throttle bump (step 2.4); no clause owns the locust/artillery harness, and the D-H8 go/no-go metric (O-1, "bootstrap-latency SLA", test-strategy §2 row 9) has no clause that ever measures it — O-1 is undecidable as planned.
- **Cross-tenant negative — UNCERTAIN** (severity: Med). A producing slot exists (P-04/05 auth spec, TO-AUTHOR, refuter mandatory), but P-05 reads "get_job **& peers**" with the peers never enumerated (yaml:81), and "cross-tenant isolation negative" also appears as unowned debt (test-strategy §9:155). Partial enumeration = IDOR ships with all gates green.
- **LLM-eval — YES**, produced: Q-08 (step 4.7, promptfoo + golden set + judge + red-team), with X-02 as the defense it tests (test-strategy §9b). Caveat: nothing owns *authoring* the versioned golden dataset (contents, PII provenance).

### Tension 6 resolved (decisively)

The guarantee is **UNPROVEN at scale — credible for structural drift only.** `scope-diff.py` + the ledger will reliably catch *missing/orphan* specs (deterministic, on-disk — that part of the design is sound). But the plan's claim that the safety net is "on-disk + deterministic, never attention-based" (execution-plan:38-42) is overclaimed: the only checks of spec *quality* — §8.6 gates 3 (self-sufficiency) and 4 (refuter) — are LLM judgments, i.e., exactly the attention-based safety the plan says it eliminated; and gate 5 (red-green + mutmut) physically cannot run at spec-acceptance time because pytest files only come into existence at IMPLEMENT (scope-lock §8.5:261). So across 20 unwritten specs the failure mode is concrete: an authoring subagent inherits the exemplar/§8.5 format fork (list-clause + `tooling:` + no `AC-###` vs. the mandated schema, plus handoff's stale `prompt:`-blocks instruction), writes a structurally-green spec with an underspecified fix ("& peers", "<digested CR>", "or logged fallback"), the refuter passes it (or isn't mandatory — refuter is required only for auth/IAM/data), and the implementer resolves every ambiguity unilaterally — with all nets green. The exemplar's own Q-01 already demonstrates the degradation on hard clauses. Verdict: the *nets* hold; the *§8.6 acceptance gate + fresh-subagent authoring* guarantee does not, without the fixes below.

### Findings

**1. The exemplar contradicts the mandated spec format (frontmatter schema + missing `AC-###`)** — type: spec-test.
- Evidence: spec:7-14 vs scope-lock §8.5 (:263-268) and test-strategy §7 (:111-116); §8.6 gate 2 references `AC-###` the exemplar doesn't contain.
- Failure it causes: stalls delivery / ships a bug — 20 authoring subagents fork between two conflicting templates; `scope-diff.py` mismatches list-valued clauses or passes inconsistent frontmatter; contract-consistency (gate 2) is unverifiable with no ACs. Trigger: step 0.4 fan-out.
- Recommended fix: before step 0.4, patch the exemplar to carry `AC-###` Given/When/Then per clause, and amend §8.5 to explicitly codify list-valued `scope_lock_clause` + the per-clause `tooling:` map (or forbid multi-clause specs); define `scope-diff.py`'s list handling in its spec.
- Amendment? **y** — §8.5, **MINOR** (refines a TARGET-format rule; the "matches the proven exemplar" claim as written is false).
- Scores: **High · S · Low**.

**2. §8.6 gate 5 (test-validity) cannot execute at spec-acceptance; mutmut arrives Wave 5** — type: spec-test.
- Evidence: scope-lock §8.5:261 (pytest written at IMPLEMENT) vs §8.6.5 (red-green + mutmut as *acceptance* criteria); mutmut scheduled step 5.4 (execution-plan:170) after Waves 1–4 implement.
- Failure: ships a bug — specs are "accepted" on prose RED descriptions containing ambiguous/untestable assertions (spec:44 "(or logged fallback)"; spec:82 undefined cap), and the test-validating check lands after most code is written.
- Recommended fix: split gate 5 into (a) spec-time lint — every RED description names exact assertion values, no "or" alternatives, no undefined constants — and (b) implement-time proof (red-run + green-run output recorded on the status board per step); move the mutmut spot-check to the Wave-3 gate (core tier is written by then).
- Amendment? **y** — §8.6, **MINOR** (restructures an acceptance gate).
- Scores: **High · M · Med**.

**3. Migration-parity harness has no owner before Wave-3 data migrations** — type: spec-test.
- Evidence: only D-H8 carries `verification: migration-parity` (yaml:121, Wave 6); Wave-3 steps 3.2/3.4 migrate D-H4/D-M2/D-M5 against live data (908 users, live-truth §1); test-strategy §2 row 7 scopes the harness to "Track D seams" but no clause/spec/step builds it.
- Failure: ships a bug / silent data corruption — the userEmail-PK retirement or canonical-`artifact_id` cutover diverges from legacy reads and nothing compares them; a P-01-class identifier defect is *reintroduced* by the very wave that fixes it.
- Recommended fix: make the dual-read parity harness an explicit deliverable of the D-H2 spec (it's the key-authority chokepoint — one harness, reused per entity), with `verification: migration-parity` added to D-H4/D-M2/D-M5.
- Amendment? **y** — new clause or D-H2 verification extension, **MINOR**.
- Scores: **High · M · Med**.

**4. Load/perf harness unowned; O-1's go/no-go metric is never measured** — type: spec-test.
- Evidence: yaml P-20 `verification: iac+load` (:96) with no harness clause; test-strategy §2 row 9 names "bootstrap-latency (D-H8 trigger)"; O-1 (scope-lock §10) blocks D-H8 on a metric no step produces.
- Failure: stalls delivery + ships a mis-sized throttle — P-20's "real target" is picked blind (the self-DoS recurs or capacity is guessed); Wave-6's gate is undecidable, converting "committed, gated" into "indefinitely stalled."
- Recommended fix: fold a minimal locust smoke (hub read + one generate flow, p99 assert) into the P-20 spec's RED tests; add bootstrap-latency emission to P-32's correlation-ID/metrics work so O-1 has data by Wave 5.
- Amendment? **y** — P-20/P-32 verification text, **PATCH-to-MINOR**.
- Scores: **Med · M · Low**.

**5. P-05 "& peers" unenumerated → cross-tenant negatives can be structurally green yet partial** — type: spec-test (security-adjacent).
- Evidence: yaml P-05 (:81) "get_job & peers"; test-strategy §9:155 lists the cross-tenant negative as unowned debt; ~31 handlers exist (handoff §1).
- Failure: breaches a tenant — the IDOR spec author picks a subset of peers; scope-diff, coverage gates, and even red-green all pass while unlisted handlers stay IDOR-able.
- Recommended fix: require the P-04/05 spec to contain an exhaustive route×handler table (from CDK `route_map`, the oracle source) with an owner-check status per row, and a *parameterized* cross-tenant negative over every authenticated route — the refuter's checklist is "is any route_map row missing."
- Amendment? **n** (spec/runbook fix; P-05 clause text gains the enumeration requirement as a PATCH if desired).
- Scores: **High · M · Med**.

**6. Q-04's digest/cap is undefined — the margin-protecting mechanism has no spec** — type: spec-test / cost.
- Evidence: spec:76-77 ("`<digested CR>`", cap only for KB), spec:82 (cap test with no cap), Q-10 metering lands Wave 2 but no interim counting method named.
- Failure: blows margin (C-2) quietly — implementer invents a projection and a cap, the "respects token cap" test passes against its own invented constant.
- Recommended fix: patch the exemplar's Q-04 with explicit numbers (CR digest field list + a stated cap, e.g. mirror the 1,200-token KB cap) and the counting method (Q-10's meter once landed; a named tokenizer until then).
- Amendment? **n** (spec fix — the cap value itself could be recorded on Q-04's clause as PATCH).
- Scores: **Med · S · Low**.

**7. handoff.md still instructs the retired `prompt:`-block format** — type: spec-test / delivery.
- Evidence: handoff.md:60-61 ("frontmatter + numbered Fix Plan + `AC-###` + copy-paste `prompt:` blocks") vs v1.3.0 retirement (scope-lock §12 v1.3.0 row; execution-plan:46-52).
- Failure: stalls delivery / format fork — the handoff is the first document pasted into every orchestration session; a fresh orchestrator follows it and mass-authors specs in a dead format, which `scope-diff.py` was never specced to reject.
- Recommended fix: one-line edit to handoff.md §0 to match v1.3.0 (inline RED-test descriptions, no prompt blocks).
- Amendment? **n** — handoff sits below the contract (authority §0.2); direct edit.
- Scores: **Med · S · Low**.

**8. Q-02 silently changes wire behavior while claiming "no frontend-contract change"** — type: spec-test / correctness.
- Evidence: spec:37 + :46 — replacing the always-succeeding stub with a "404-style" error is a new failure mode on a FE-called endpoint (coverage-matrix §1a, gap rows FE ✅); the error's envelope/status is unstated and contract item 10 isn't carried as an AC.
- Failure: ships a bug — FE gap flow hits an unhandled 404 (or a non-envelope error → `[object Object]`, the exact F-05 class) for any stale `cv_id`.
- Recommended fix: add an AC to Q-02 pinning the error to the §3 item-10 envelope + a specific status code, and a check (or characterization) of how `src/frontend` handles a gap-questions 4xx.
- Amendment? **n** (spec fix), unless FE turns out not to tolerate it — then Q-02 needs `contract_impact: true` (**PATCH** to YAML).
- Scores: **Med · S · Low**.

### Blind spots

- **The exemplar teaches mock-first testing.** Its RED tests patch `DynamoDalHandler.get_cv_by_id` (spec:43) while the plan's central lesson is that mocking the resolver produced vanity coverage and hid P-01 (test-strategy §1: "hand-mocked dicts are banned"). Twenty spec authors will copy the exemplar's style, not §1's rule — the plan re-seeds the failure mode it diagnoses. At least one exemplar RED test should be moto-real-key-schema.
- **No per-spec acceptance record.** §8.6 has five gates but no required artifact (who refuted, what the self-sufficiency probe asked, when accepted). For a solo dev the audit trail *is* the review; without it, "gate passed" is self-report — which §11 explicitly bans for implementation but forgot for spec acceptance.
- **Characterization is pinned to `4f7c294`, not to deployed behavior.** The Fable digest warns live/repo drift is likely; characterizing repo code at the anchor proves refactor-safety of the *code*, not of what users currently experience. Cheap fix: the P-30 smoke baseline doubles as live characterization — say so.
- **Golden-dataset provenance.** "Versioned golden dataset" is load-bearing for all LLM-eval, but no clause authors it, versions it, or addresses using real user CVs (PII) as fixtures.
- **The acceptance-gate cost at scale is unbudgeted:** 21 specs × (author + refuter + self-sufficiency probe + human review) is a substantial fan-out the runbook renders as a single row (0.4); no failure path is defined for "spec rejected twice."

### Dissent

- **Against the plan's self-description:** "safety net = on-disk + deterministic, never attention-based" (execution-plan:38-42) is overclaimed. The deterministic net checks *presence*; every *quality* check (§8.6 gates 3–4) is an LLM judgment — precisely the attention-based mechanism the sentence disavows. I expect other lenses to credit the nets as the plan's crown jewel; I say they are necessary but prove the wrong property.
- **Against the contract's word "proven":** §8.5 calls the exemplar "the proven `Q-gap` exemplar." It has never driven one red-green cycle; by the plan's own gate-5 standard it is *unproven*. The v1.3.0 amendment normalized the format to an untested artifact — the right call versus the never-built YAML format, but the label should be "the one authored exemplar," and the first IMPLEMENT pass through Q-02 should be treated as the pattern's validation experiment, gating step 0.4's mass fan-out if it fails. (Cheap sequencing win: run 4.1's TDD cycle against the exemplar *before* authoring 20 more specs in its image.)
- **Against likely-majority deference to the deploy-safety story:** for *this* lens the P-27..P-30 additions are irrelevant to whether specs produce correct code; a council that scores the plan up for closing the Fable gates should not let that halo cover the spec-quality holes above.
- **With the live truth, against Fable:** nothing in this lens's evidence contradicts live-truth-2026-07-11; the 415/500 correction doesn't move any spec-quality conclusion.

---

## 🗳️ Lens 6: Delivery soundness & red-team (solo)

**Soundness verdict:** SOUND-WITH-CONDITIONS — the orchestration mechanics (on-disk status board, fresh subagents, deterministic nets) are genuinely solo-executable, but the plan's load-bearing safety guarantee — amendment discipline plus human gates — is enforced by prompt text and self-approval exactly where the solo constraint (C-3) makes discipline weakest, and the Wave-0 dependency wiring lets the riskiest deploy (P-26) run before its own safety gates are verified.

### Hard questions

**Q(a) — THE single assumption: amendment discipline holds when the sole "human validator" is the same person driving the orchestrator.** Call: **yes, this is the invalidating assumption — and it is fragile (severity: Critical).** I reject the other candidates: anchor validity has a built-in check with a defined fallback (execution-plan step 0.1, "anchor confirmation… else re-anchor via amendment"); live-state match was just re-verified 2026-07-11 (live-truth §1–2, "every claim still holds," 415/500 confirmed); orchestration collapse is a *loud* failure (a stall you notice), not a silent one. Amendment-discipline failure is silent and self-amplifying: every net the plan relies on — `scope-diff.py`, the oracle, wave gates — audits *against the contract* (execution-plan "Why a dropped requirement is caught…", :36-42). If the solo dev rubber-stamps amendments under pressure, the contract starts tracking the code, and `scope-diff.py` then *enforces* drift instead of preventing it. The plan names the anti-patterns (scope-lock §9.3: "contract amended retroactively to rubber-stamp already-built code") and mandates "Human validates and confirms — no auto-apply" (scope-lock §0.3 step 3; yaml:215) — but there is **no mechanism anywhere in the corpus that prevents the orchestrator session from editing `project-scope-lock.{md,yaml}` itself**, and the mandatory "adversarial review" (§0.3, §9.2) is a same-model subagent spawned by the same operator. Fable's own verified principle applies to the plan's authors: "Discipline doesn't survive a subagent swarm; IAM and CloudFormation do" (fable-infra-mitigation-plan.md:60). The contract mechanizes deploy safety (P-27/P-28) but leaves its *own integrity* purely disciplinary.

**Q(b) — the nets are unbuilt Wave-0 deliverables: real hole?** Call: **yes — real, and larger than the brief states (severity: High).** The benign half: steps 0.1–0.4 before/while the nets exist are docs and spec authoring — zero blast radius, and nets-before-scaffolding (execution-plan Wave-0 note, :98-101) genuinely covers the mass-authoring step 0.4. The malignant half is what the brief's phrasing misses: **Wave 0 also contains the two riskiest deploys of the entire program (P-26 CFN decomposition at 0.65, opus/xhigh; P-24 identity surrogate at 0.7), and the wave gate only runs at end-of-wave** (execution-plan :30, "GATE (end of each wave)"). So P-26 — the change whose failure mode is "invoke URL changes, site down" — executes when: (i) the F-01 oracle is still an explicit **"skeleton"** (step 0.3, :110); the full 10-item contract assertions are F-06, scheduled **Wave 4 step 4.8** (:160); (ii) `scope-diff.py` itself has passed no acceptance gate (nothing in §8.6 is applied to the nets — who red-greens the net?); and (iii) the runbook's own dependency column does not force P-29 (evidence pack), P-30 (smoke harness), or P-21 (SNS) to be verified before 0.65. The hole is not "early Wave 0 is uncovered"; it is "Wave 0's *deploys* are covered only by ordering conventions, not by declared gates."

**Q(c) — Fable's team-of-2–3 / human-gates model vs a solo author-approver: does the safety model hold?** Call: **yes-with-conditions (severity: Med-High), and the tension is partly manufactured by the digest.** First, evidence check: the phrase "for a team of 2–3" **does not appear anywhere in the 62 KB Fable source** — I grepped `fable-infra-mitigation-plan.md` for `2–3`, `2-3`, `team`, `solo`: the human-gate mandate is real (:19, :130, :190 "human executes every change set"), but the team-sizing claim exists only in the digest (fable-findings-digest.md:49-50). It is a distillation artifact, not evidence. Second, the substance: the Fable gate's purpose is **agent↔human separation, not human↔human four-eyes** — "a swarm physically cannot execute… without a human keystroke" (fable plan :26). That property survives a solo operator fully: P-28's IAM split (agents `CreateChangeSet`-only, human-only `ExecuteChangeSet`, scope-lock P-28 / yaml:104) is operator-count-independent. What *breaks* solo is the review wire, and Fable itself names it: "Human-approval gates assume the human actually reads the change set; pair each approval with the machine-parsed replacement report… or the gate is theater" (fable plan :140, :200). The contract encodes `cdk diff zero-stateful-replacement` (§8.2, §9.2) — the *weaker* heuristic Fable explicitly downgrades ("the change set's per-resource `Replacement: True/False` is CFN's own computation — strictly stronger than `cdk diff` string-heuristics," :26) — and P-28 nowhere requires the parsed replacement report as the approval artifact. So: the mechanical layer holds solo; the review layer as specced is the theater Fable warned about. Condition, not collapse.

**Q(d) — where does the plan stall, and does the `core` collapse matter post-launch?** Call: **no — the designed stall (Wave 6 / D-H8) does not matter; the plan's actual stall point is Wave 0 (severity: Med).** D-H8 is `status: OPEN`, Wave 6, behind O-1/O-3/O-5 and explicitly post-launch (scope-lock §7.3 freeze line; yaml:121); L-3 declares the seams-only resting state production-ready, so an indefinite Wave-6 stall strands no launch requirement. The real stall risk is front-loaded: Wave 0 contains ~15 steps including two opus/xhigh deploys, the mass-authoring of ~20+ specs each requiring the five-gate §8.6 acceptance (with a **mandatory adversarial refuter for every auth/IAM/data spec** — which is most of Track P), plus every change-set execution, every amendment confirmation, and every wave-gate approval landing on one human. The plan carries per-clause LOE (Lo/Md/Hi) but **zero calendar or human-throughput budget anywhere in the corpus** — the solo dev's approval bandwidth is the unmodeled critical resource. A stall in the "guardrails" wave, unlike Wave 6, blocks everything.

### Findings

**1. Handoff contradicts the contract on the human's duties** — type: delivery/correctness.
Evidence: handoff.md:25-27 — "Your only jobs after 'begin': (1) answer… open questions; (2) approve each wave gate. **Nothing else**" — vs scope-lock P-28 (human-only `ExecuteChangeSet`), §0.3 step 3 (human confirms every amendment), P-27 ("human-applied"). Failure: the one document the human actually pastes tells them they have two jobs, omitting the most safety-critical ones; a compliant operator following handoff literally lets the orchestrator find another deploy path, or treats change-set approvals as rubber-stamp interrupts — the exact "gate is theater" failure (fable plan :140). Trigger: first Wave-0 deploy step. Fix: rewrite handoff's "HOW YOU RUN THIS" to enumerate all four human duties (O-# decisions, wave gates, every `ExecuteChangeSet`, every amendment confirmation). Amendment? **n** (handoff.md is authority-tier 2, not the contract; runbook fix). Scores: **High · S · Low**.

**2. Deploy-safety steps are not declared dependencies of the deploys they protect** — type: delivery/site-break.
Evidence: execution-plan :115-118 — step 0.65 (P-26) lists `Deps: 0.6` only; 0.61 (P-29 evidence pack), 0.62 (P-30 smoke harness), 0.63 (P-21 SNS) are not deps of 0.65 or 0.7, despite the contract homing P-27..P-30 in Wave 0 *as* deploy gates (scope-lock §7.2) and yaml P-29/P-30 carrying `gate: pre_deploy`. The plan's own semantics (":33 a numeric dep = another step that must be verified first") make numeric ordering advisory, and the plan encourages dep-driven parallelism. Failure: an orchestrator legally executes P-26 — the highest-blast-radius change — with no baseline smoke harness and no golden-state snapshot; a broken invoke URL is then discovered by users, not the harness, with no evidence pack to restore from. Trigger: any parallelization or step-skip in Wave 0. Fix: add `0.61, 0.62, 0.63` to step 0.65's Deps and `0.62` to 0.7's; one-line runbook edit. Amendment? **n** (runbook fix; clauses already exist). Scores: **Critical · S · Low**.

**3. Contract self-protection is disciplinary, not mechanical** — type: delivery (root guarantee).
Evidence: scope-lock §0.3 ("Human validates and confirms — no auto-apply"), §9.3 anti-patterns; no clause, step, or setting anywhere prevents an agent session from editing `project-scope-lock.{md,yaml}` directly — contrast P-28, which mechanizes the equivalent rule for AWS. Failure: under deadline pressure the solo author-approver (or a "helpful" subagent) edits the contract in-line; every downstream net then validates against a corrupted truth — silent total-loss of the "requirements can't rot" guarantee. Trigger: first hard deviation late in a wave. Fix (solo-friendly, ~30 min): write-deny the two contract files in agent permission settings + a CI check that any diff to them includes a §12 changelog row, a version bump, twin-sync, and a human-signed approval trailer; reject otherwise. Amendment? **y** — extend §0.3/§9.1 with "contract files are write-protected from agent sessions; amendments land only via human-executed commit" — **MINOR** (adds a guardrail; changes no invariant). Scores: **Critical · S · Low**.

**4. Approval artifact is the weaker lever: `cdk diff` instead of the machine-parsed change-set Replacement report** — type: delivery/site-break.
Evidence: scope-lock §8.2/§9.2 encode "`cdk diff` zero-stateful-replacement"; fable plan :26 (change-set `Replacement` flags "strictly stronger than `cdk diff` string-heuristics") and :140/:200 (approval without the parsed report = theater). P-28 defines who executes but not what artifact the human must read. Failure: a solo, fatigued approver green-lights a change set whose Replacement:True on a stateful resource `cdk diff` missed; stack policy (P-27) is then the last line — and Fable notes it must be relaxed for intended changes like P-26, i.e., exactly when it's most needed (:139). Fix: P-28 gains "approval input = machine-parsed `DescribeChangeSet` report; auto-fail on Replacement:True for RestApi/Table/Bucket/UserPool." Amendment? **y** — extend P-28, **MINOR**. Scores: **High · S · Low**.

**5. Wave-0 oracle is a skeleton while Wave 0 deploys the riskiest change** — type: delivery/site-break.
Evidence: execution-plan :110 (0.3 "executable oracle **skeleton**") vs :160 (F-06 full 10-item assertions at Wave-4 step 4.8) vs test-strategy §4 ("Encodes all 10 contract items" — aspirational at 0.3). Failure: "don't break the UI" during P-26 is defended only by the 4-wire smoke probe (if finding 2 is fixed), with contract items like `vpr_id: null`-vs-absent and 409-on-stale unasserted for the entire Waves 0–3. Fix: pull the 10-item assertion set (F-06 content) into step 0.3, or insert a mid-Wave-0 gate before 0.65 requiring oracle+harness green. Amendment? **n** if done as runbook scope of 0.3 (F-06 clause stays where it is); flag for the Correctness lens. Scores: **High · M · Med**.

**6. Digest fabricates the "team of 2–3" claim** — type: delivery (evidence integrity).
Evidence: fable-findings-digest.md:49-50 attributes 'Effort scored "for a team of 2–3"' to the Fable plan; grep of the full 62 KB source finds no such phrase or any team-sizing statement. Failure: the council (this brief's tension 4) and any future planning reason from an unsourced effort premise; more broadly, the digest — the *default* evidence read — contains at least one invented quote, so its other unverified claims (e.g. "zero readers" of `AUTHORIZER_DISABLED`, still open per live-truth §3) deserve lowered prior. Fix: correct the digest line to "effort/team-sizing: not stated in source"; re-verify remaining digest claims flagged unverified. Amendment? **n**. Scores: **Med · S · Low**.

**7. Human gate throughput is unbudgeted — the real solo-sustainability constraint** — type: delivery/stall.
Evidence: no time/throughput model anywhere in the corpus; §8.6 requires per-spec self-sufficiency check + adversarial refuter (mandatory for auth/IAM/data — the majority of the ~20+ TO-AUTHOR list, execution-plan :181-184); plus every `ExecuteChangeSet`, amendment, O-#, and wave gate on one person. Note also the plan disagrees with itself on the spec count (T-06 "~15–20"; the TO-AUTHOR list enumerates ~30 entries with duplicated lines "Track Q"/"Track X: X-01" — :182-184; the brief says ~21). Failure: Wave 0 becomes a months-long approval queue; the predictable human response is batching/skimming approvals — degrading exactly the gates findings 1/4 depend on. Fix: add a per-wave human-touch budget row to the runbook; batch refuter output for one review sitting; dedupe the TO-AUTHOR list and reconcile the count with T-06. Amendment? **n** (T-06 count fix is a PATCH if you touch the clause; the rest is runbook). Scores: **Med · S · Low**.

**8. §8.6 gate 3 (self-sufficiency) has no execution mechanism** — type: delivery/spec-test.
Evidence: scope-lock §8.6.3 / test-strategy §8.3: "a fresh subagent given ONLY the spec… can implement it with zero further questions. If it must ask… reject." Nothing defines who runs this trial, when, or what artifact proves it — unlike gates 1 (scope-diff, deterministic) and 5 (red-green, deterministic). Failure: the gate degrades to the orchestrator's opinion; underspecified specs pass and fail later at IMPLEMENT, mid-wave, where the cost is highest — this is the mechanism by which the 1-exemplar pattern fails to scale across 20 specs (tension 6). Fix: operationalize gate 3 as a cheap dry-run — a fresh subagent must return an implementation outline + an explicit "questions: []" block; any non-empty questions list auto-rejects. Amendment? **n** (test-strategy §8 edit). Scores: **High · S · Low**.

### Blind spots

- **Performative rigor #1 (the headline):** the amendment loop's "Human validates and confirms — no auto-apply" (scope-lock §0.3) and the §9.3 hard-rejects are gates with **no enforcement mechanism whatsoever** — no file protection, no CI check, no credential boundary. The plan mechanized deploy discipline (P-27/P-28) after Fable taught it that prompt-text guardrails don't bind agents, then left its own constitution guarded by prompt text. Every "IMMUTABLE" tag in the contract is exactly as strong as the orchestrator's inclination to obey it.
- **Performative rigor #2:** the §8.6 acceptance gate lists five checks but only two are deterministic; gates 3 and 4 (self-sufficiency, adversarial refuter) are same-model agents judged by the same operator — they will produce output, and output will be accepted. Nothing measures refuter efficacy (e.g., seeded-flaw detection rate).
- The plan never addresses **operator absence/continuity**: a solo program with human-only execute gates has a bus factor of 1 by design, and no clause covers pausing safely mid-wave (partially-executed change set + stack policy relaxed = the worst place to stop).
- Nothing audits the **status board itself** — the orchestrator both performs steps and writes their `status`, while §11 bans self-report for verification. `scope-diff.py` checks specs/tests exist, not that a step marked `verified` actually passed its gate.

### Dissent

- **Against the Fable evidence (as digested):** the solo condition does *not* invalidate the human-gate model. The gate's threat model is autonomous-agent mutation, and IAM-level separation survives one operator intact; the digest's "team of 2–3" premise is an invented quote absent from the source. The safety model's solo weakness is review fatigue — fixable with the parsed replacement report — not a structural contradiction requiring re-staffing or de-scoping.
- **Against the plan:** "Wave 0 — Guardrails & truth" is a mislabel that launders risk. P-26 and P-24 are the two most dangerous changes in the program, and placing them inside the guardrails wave — before any wave gate has ever fired, under a skeleton oracle, with safety steps un-wired as dependencies — is the opposite of the plan's own "smallest safe first slice" doctrine. They should be a gated Wave 0.5 with an explicit pre-gate.
- **Against the likely majority:** the consensus worry will be tension 6 — "1 of ~21 specs, unproven at scale." I dissent: spec authoring is the *best-defended* part of this plan (deterministic nets, acceptance gate, exemplar, fan-out isolation), and the orchestration is machine-sustainable across 20 cycles by construction (on-disk board, fresh contexts). The genuinely unproven resource is the **human**: unbudgeted approval throughput and unenforced amendment discipline. The plan will not fail because a subagent wrote a bad spec; it will fail — silently — because the one person gating everything got tired and started saying yes.

---
---

# SYNTHESIS — the council's combined deliverable

*(Same-model caveat: all six lenses share priors; convergence below is a shared prior to stress-test, not independent corroboration. Where lenses genuinely conflicted, §4 says so.)*

## 1. Overall soundness verdict

**SOUND-WITH-CONDITIONS** — unanimous across all six lenses, and with Architecture and Correctness (×2 each) both landing there, the weighted verdict is unambiguous. The plan's *method* (contract → spec → TDD, deterministic drift nets, staged seams-first migration, encoded deploy gates) is genuinely sound and unusually self-aware. What keeps it out of plain SOUND is a small set of specific, cheap-to-fix defects — one of which (P-26's clause text) would take the live site down if executed as written.

**Per-domain scorecard:**

| Domain | Verdict | The one-line reason |
|---|---|---|
| Architecture (×2) | **CONDITIONS** | Target design correct for <10k; P-26 mitigation technically false; CR-first failure semantics unspecced; 2 data-layer rules missing from contract |
| Correctness / site-break (×2) | **CONDITIONS** | Deploy gates genuinely encoded (v1.4.0), but P-26-as-written is the site-breaker, CI auto-deploy voids P-28, full oracle lands a wave late |
| Security | **CONDITIONS** | Every known vuln has an owning clause, but 31-handler JWT-only is unenumerated, COGNITO_ADMIN fix orphaned, mock-payment bypass risk |
| Cost / margin | **CONDITIONS** | Honest about unmeasured ~88% with ~2.5× headroom; L-6 exempt from its own gate; budgets alarm 5 waves too late; margin gate has no denominator |
| Spec & test | **CONDITIONS** | Method aims precisely at the P-01 class; exemplar violates its own mandated format; migration-parity & load/perf have no producing spec |
| Delivery (solo) | **CONDITIONS** | Orchestration solo-executable; contract integrity + approval quality enforced only by prompt text; Wave-0 deploys not gated by their own safety steps |

## 2. The blocking gaps (ranked)

**The single gap most likely to break the live site: P-26 executed as the contract writes it.** Both ×2 lenses converged independently: moving the RestApi into a nested stack is delete+create in one CloudFormation update — the invoke URL the Amplify frontend has baked in dies for all 908 dev users, with recovery a full Amplify rebuild. The clause's "retained logical id" mitigation is fictional under CFN semantics, and the clause contradicts the plan's own P-27 stack policy and §9.3 block-list. (Fable's blue/green direction is right but its recipe also incomplete: the base-path re-map assumes a custom domain that doesn't exist yet.)

Ranked blocking list:

1. **P-26 clause text** — *breaks the site* (Critical; Lenses 1+2). Amend before step 0.65.
2. **CI auto-deploy-on-push + cancel-in-progress** — *breaks the site / wedges the stack*; makes P-28's human-only gate decorative (Critical; Lens 2). Amend P-28 / close pipeline in step 0.55.
3. **Deploy-safety steps not wired as dependencies of 0.65/0.7** — *breaks the site*; P-26 can legally run before evidence pack + smoke harness exist (Critical; Lens 6). One-line runbook fix.
4. **Contract files writable by agent sessions** — *silent total-loss of the "requirements can't rot" guarantee* (Critical; Lens 6). Mechanize §0.3.
5. **P-04 auth flip with no rollback lever** — *breaks the site for authed users*; the presumed lever is likely dead wiring, revert is a 15–30 min redeploy at incident time (High; Lenses 2+3). Resequence P-23 canary first + soak + measured RTO.
6. **Exemplar spec defects before the 20× fan-out** — *ships bugs at scale*: violates §8.5 format (no `AC-###`), omits CR failure/timeout policy, teaches mock-first testing, undefined digest caps (High; Lenses 1+4+5). Fix the exemplar before step 0.4.
7. **Full 10-item oracle (F-06) in Wave 4, after Wave-3 contract-touching work** — *ships a FE-visible regression under a "green" oracle* (High; Lenses 2+6). Pull into step 0.3.
8. **P-05 "& peers" / 31-handler denominator unenumerated** — *breaches a tenant* via an unlisted handler (High; Lenses 3+5). Route×handler table + parametrized cross-tenant negative.
9. **Migration-parity harness unowned before Wave-3 live-data migrations** — *silent data corruption* on 908 users' rows (High; Lens 5). Home it in D-H2; add verification to D-H4/D-M2/D-M5.
10. **Mock-payment signature bypass + no StripeProvider clause before paid launch** — *money-path bug at go-live* (High; Lens 3). Real HMAC in Mock + new P-25b.
11. **Budgets/Cost-Anomaly in Wave 5 with a live duplicate-spend defect** — *blows the personal bill/margin* during Waves 0–4 (High; Lens 4). 15-minute console task → Wave 0.
12. **COGNITO_ADMIN scope + implicit grant orphaned in P-07** — *privilege escalation ships* (High; Lens 3). Amend P-07 scope.
13. **FE-UI-044 half-migration unowned** — *reintroduces the P-01 drift class* (High; Lens 1). New clause D-H9.
14. **GSI-cardinality rule absent from contract** — *latent hot-partition bug at ~10k* (High; Lens 1). Add invariant.
15. Medium tail: L-6 exempt from metering gate; Q-10 behind payment port + Sonnet-5 deadline 2026-08-31; margin denominator missing; freeze-line enumeration stale; handoff.md contradictions (duties + retired format); digest's fabricated "team of 2–3" quote; §8.6 gates 3/5 unexecutable as specced; CR-first latency budget unstated; P-24 JIT-creation atomicity.

## 3. Required plan changes

### (a) Spec/runbook fixes (mutable — no amendment)
1. Wire deps: step 0.65 ← {0.61, 0.62, 0.63}; step 0.7 ← 0.62; reorder 0.61/0.62 before 0.6 (evidence pack + smoke baseline before deploy #1).
2. Split step 1.3 → 1.3a P-08 pilot → 1.3b P-10 (preflight probe, pre-staged inverse change set, max-age→60s) → 1.3c P-07/P-11; fix the poisoned `cors-no-wildcard.regression.test.ts` before fan-out.
3. Patch the exemplar before step 0.4: add `AC-###` per clause; CR failure/timeout RED tests (`test_chain_cr_failure_degrades_not_blocks`, `test_chain_cr_timeout_policy`); pin Q-02's error to the item-10 envelope + status code; define the Q-04 CR digest (field list + cap + counting method); make ≥1 RED test moto-real-key-schema; remove "(or logged fallback)" ambiguity.
4. Run one full author→implement red-green cycle (Q-02) as the pattern-validation experiment BEFORE mass fan-out at 0.4.
5. handoff.md: enumerate all four human duties (O-# decisions, wave gates, every ExecuteChangeSet, every amendment); delete the retired `prompt:`-block instruction.
6. P-04 spec preconditions: resolve live-truth §3 opens; P-23 canary + 401-rate alarm sequenced first (do NOT rebuild the bypass flag); ≥24h soak; fire-drilled measured revert RTO.
7. P-05/P-04 spec: exhaustive route×handler table (31 handlers) + parametrized cross-tenant negative per authenticated route; Wave-1 gate.
8. P-24 spec constraints (4 items): shared-layer resolution + authorizer-context cache; `attribute_not_exists` conditional JIT create; mapping table named in §4's separate-tables list; cache invalidation on link events. Adversarial refuter must test the `email_verified`-trust and earliest-created pre-emption vectors.
9. D-M6 acceptance: "every §1a endpoint + §1b/§1c async behavior maps to a named Query/GSI, zero Scan, incl. status-by-`artifact_id` and sparse in-flight index."
10. Operationalize §8.6 gate 3 (fresh-subagent dry-run returning `questions: []`) and split gate 5 (spec-time lint / implement-time recorded red-green; mutmut spot-check at Wave-3 gate).
11. Q-10 spec: record price-per-app constant; tag traffic origin (dev vs product); measure prompt-cache hit-rate (live cache is at 0 items — the assumption is currently falsified).
12. Correct the Fable digest ("team of 2–3" is not in the source); note remaining unverified digest claims.
13. Add per-wave human-touch budget; dedupe the TO-AUTHOR spec list (~30 entries with duplicates) and reconcile with T-06's "~15–20".
14. O-2 decision brief must include the cache-reuse/cost delta; add CR-first submit→questions latency budget as an NFR line.

### (b) Contract amendments (for §0.3, each needs adversarial review + changelog + twin-sync)
| # | Clause | Semver | Proposed change |
|---|---|---|---|
| A1 | **P-26** | MINOR | Replace nest-in-place + "retained logical id" with: custom domain+ACM first (one Amplify env repoint, owned step); new RestApi born in its own stack (never inside the 415/500 parent); verify via P-30 4-wire against raw invoke URL; human-only base-path/domain flip; retire old API in a later gated deploy. Precondition: read P-29 evidence pack to confirm `NEXT_PUBLIC_API_URL`. Explicitly forbid moving the Cognito pool. |
| A2 | **P-28** | MINOR | Add: branch-protect main; GitHub environment with required human reviewer; `concurrency max=1`, no cancel-in-progress; approval artifact = machine-parsed `DescribeChangeSet` Replacement report, auto-fail on Replacement:True for RestApi/Table/Bucket/UserPool. |
| A3 | **§0.3/§9.1** | MINOR | Contract files write-protected from agent sessions; amendments land only via human-executed commit + CI check (changelog row, version bump, twin-sync, signed trailer). |
| A4 | **P-04** | MINOR | Note: flip-then-remove; rollback mechanism (P-23 canary + 401 alarm) verified before enforcement flip; soak + measured RTO. |
| A5 | **P-07** | MINOR | Scope explicitly owns implicit-grant→authorization-code+PKCE and removal of `COGNITO_ADMIN` from the SPA client. |
| A6 | **P-25b (new)** | MINOR | StripeProvider + real signature verification + idempotency negative, in the freeze line before paid launch; Mock's `verify_webhook` must implement real HMAC rejection. |
| A7 | **§8.5/§8.6** | MINOR | Codify list-valued `scope_lock_clause` + `tooling:` map (or forbid multi-clause specs); restructure gates 3/5 per fix (a)10; drop the word "proven" for the exemplar. |
| A8 | **L-5/Q-01 rider** | MINOR | "CR to completion **or documented degraded fallback** (timeout N, empty CR block, failure surfaced additively)." |
| A9 | **§4 invariant (new)** | MINOR | `gsi_pk_user_or_high_cardinality_scoped_or_sparse_never_status`. |
| A10 | **D-H9 (new)** | MINOR | Complete FE-UI-044 CR canonical-store migration (backfill parity, retire legacy dual-read); Wave 3. |
| A11 | **Waves** | MINOR | P-32 budgets slice → Wave 0 "5-min-today" block; Q-10 → Wave 0/1 (drop dep 2.0; note Sonnet-5 deadline 2026-08-31); F-06 → step 0.3 or Wave-3 entry dep; D-M6 verification strengthened + dep of D-H8. |
| A12 | **§7.3 freeze line** | PATCH | "all T1 (any track) + all T2 + picks" — delete stale "(P-01..P-24)". |
| A13 | **L-6/§6.3** | MINOR | Gap→Sonnet stays approved but gains a post-Q-10 measured margin check with a named revert lever (router → Haiku via TaskMode config). |
| A14 | **D-H4/D-M2/D-M5** | MINOR | Add `verification: migration-parity`; harness homed in D-H2. |

## 4. Consensus vs. disagreement

**Shared starting points (stress these — all six could be wrong the same way):** every lens returned SOUND-WITH-CONDITIONS; both ×2 lenses independently named P-26-as-written the top site-breaker; all accepted 415/500 from live truth; four lenses independently want the exemplar fixed before the 0.4 fan-out; nobody proposed violating a hard constraint (DynamoDB kept, solo, no GDPR gold-plating all respected). The shared blind-spot risk: all six graded from the same corpus — none could verify claims that require touching the live repo (e.g., whether `AUTHORIZER_DISABLED` truly has zero readers — still open in live-truth §3).

**Genuine conflicts:**
- **P-04 rollback shape:** Lens 2 wants a runtime-read kill switch during flip-then-remove; Lens 3 explicitly rejects rebuilding any bypass lever (it *is* the vuln) and wants P-23 canary+alarm instead. **Council resolution: side with Lens 3's shape** — canary/alias rollback + 401 alarm sequenced before the flip; no new bypass flag. Both agree on the substance: no enforcement flip without a real, fire-drilled revert.
- **What the plan's biggest risk is:** Lens 1 says the flawed exemplar (scaling a defect 20×); Lens 5 says the quality gates are attention-based theater; Lens 6 explicitly dissents from both — spec authoring is the *best-defended* part; the unproven resource is the human (approval throughput, amendment discipline). These are genuinely different failure theories; the fixes are complementary (A3 + A7 + fix-the-exemplar cover all three).
- **Tension 5 framing:** Lens 2 dissents from the brief itself — the "missing deploy gates" tension is mostly stale; v1.4.0 already encoded the big five. The residue is four specific holes, not a missing safety program.
- **Cost severity:** Lens 4 dissents from the anticipated majority — 2 Haiku samples do NOT make the margin claim unsound (2.5× structural headroom, honest self-diagnosis); the real cost defects are one gate exemption and one late alarm.
- **P-26 placement:** Lens 2 accepts P-26 in Wave 0 (with preconditions, given ~85 slots of headroom); Lens 6 wants it moved to a gated "Wave 0.5". **Resolution:** placement is secondary — the binding fix is A1 + the dependency wiring; once those land, Wave-0 placement is acceptable.
- **Evidence integrity:** Lens 6 grep-verified that the digest's "team of 2–3" quote does not exist in the Fable source — a distillation fabrication that partly manufactured the brief's tension 4. The council treated Fable critically as required: its 476/500 rejected (live truth 415), its blue/green direction adopted with a correction (custom domain must come first), its team-sizing claim exposed as a digest artifact, and its zero-readers claim held open pending live verification.

**All 6 known tensions — decisive answers:** (1) **415/500** — live-verified; no register amendment; P-26 loses emergency urgency but keeps its before-P-09/14/17/21 gate. (2) **Blue/green wins** — nest-in-place is unexecutable safely and self-contradicted by P-27/§9.3; one MINOR amendment (A1), with the correction that a custom domain must be created first. (3) **P-04 rests on nothing, not on a dead lever** — plan defect; fix = A4 + resequenced P-23. (4) **The human-gate model survives solo** — its threat model is agent↔human separation (IAM-enforced, operator-count-independent); what breaks is review quality → fix = machine-parsed Replacement report (A2) + refuters as the real review; the "team of 2–3" premise was a digest fabrication. (5) **Mostly already closed by v1.4.0** — the five big gates are real clauses; genuinely missing: CI pipeline closure, P-08-first split + inverse change set, P-04 rollback, ACAO-'*' codification, drift-detection gate. (6) **Unproven at scale** — the deterministic nets catch structural drift only; quality gates are LLM judgments and gate 5 can't run at acceptance; fix = A7 + fix-the-exemplar + one validation cycle before fan-out.

## 5. GO / NO-GO to implement

**GO — WITH CONDITIONS.** The architecture is right for the scale, the method is sound, and the deploy-safety program is mostly real. But three things are NO-GO as currently written:

- **NO-GO on step 0.65 (P-26)** until amendment A1 lands and steps 0.61/0.62/0.63 are wired as its dependencies. This is the site-breaker.
- **NO-GO on step 0.4 (mass spec fan-out)** until the exemplar is fixed (format + CR failure policy + digest cap + moto test) and §8.5/§8.6 are reconciled (A7) — ideally after one Q-02 validation cycle.
- **NO-GO on step 1.1 (P-04/P-05 auth flip)** until a real rollback (P-23 canary + 401 alarm) is sequenced ahead of it and the 31-handler enumeration exists.

**The blocking subset to clear before starting:** A1, A2, A3 (amendments — roughly a day of writing + adversarial review), the dependency-wiring and step-1.3-split runbook edits (an hour), the exemplar patch (a day), and the two 15-minute console tasks (AWS Budgets alarm from A11; branch protection from A2). Everything else on the conditions list can land wave-by-wave without blocking the start. Nothing found requires a MAJOR amendment, a re-architecture, a team, or abandoning any locked decision — the plan is one disciplined amendment session away from being executable.

---

# PRODUCTION-READINESS ANSWER (the user's ultimate question)

**Will the proposed changes, as planned, ready the system for production deployment? Not by themselves — the plan as written lands you at "dev-certified with conditions," and its own finish line is dev-only (C-7).** Three layers:

**Layer 1 — plan-internal gaps (would ship a defect even if you follow the runbook faithfully):** the blocking subset above (§5) plus the ranked list (§2). Until those land, faithful execution can break the live site (P-26, CORS, P-04), ship an IDOR (P-05 "& peers"), or corrupt live rows (unowned migration-parity).

**Layer 2 — plan-to-production gaps (things production requires that the plan never claims to cover):**
1. **Real payments** — the freeze line ships a mock provider; a paid launch needs P-25b (StripeProvider + real signature verification) or launch is unpaid by construction.
2. **A falsifiable margin gate** — C-2 has no revenue denominator anywhere; record price-per-app in Q-10 or the >70% certification check is uncomputable.
3. **Load/perf evidence** — no clause produces the harness; O-1's go/no-go metric is never measured; P-20's throttle target is picked blind.
4. **A measured rollback RTO** — every revert story in the corpus is an estimate; fire-drill one redeploy in Wave 0 and write the number down.
5. **Prod promotion mechanics** — the contract is dev-only; account separation, prod credential split, prod data backups, and the certification gate itself need their own (small) clause set before anything is promoted.
6. **End-to-end XSS closure** — backend encoding is owned (X-02) but the sink is in the out-of-scope frontend; one FE verification task is unavoidable before real users see LLM-generated artifacts.
7. **Operator continuity** — bus factor 1 by design; a "safe pause" procedure (never stop mid-change-set with a relaxed stack policy) is a one-page addition.

**Layer 3 — the verdict:** with the blocking subset landed (about 2–3 solo days of amendments, runbook edits, and console tasks — no re-architecture), the plan is sound to execute and its end state plus Layer-2's seven items is a defensible production launch for <10k users. The single most important thing to do first: **amend P-26 before anyone runs step 0.65.**

---
*Full lens outputs above are verbatim from the six blind council members. Saved by the council run of 2026-07-11.*
