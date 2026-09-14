# Astra Pass C — reconciliation

**Model:** GPT-6 Astra. **reasoning.effort: high**; escalate to `xhigh` for the
individually disputed ids only. Fresh session — **not** Pass A's or Pass B's.
**Prompt version:** C/1. **Repo commit:** `cea0799`.

> **Operator checklist.**
> 1. Attach exactly these, by path:
>
>    | What | Path |
>    |---|---|
>    | Pass A verdicts (authoritative) | `docs/handoff/2026-09-13-ASTRA-PASS-A-results.yaml` |
>    | Pass A narrative | `docs/handoff/2026-09-13-ASTRA-PASS-A-results.md` |
>    | Pass A raw receipts | `docs/evidence/astra-pass-a/` (`commands.json`, `validation.json`) |
>    | Pass B verdicts (authoritative) | `docs/handoff/2026-09-13-ASTRA-PASS-B-results.yaml` |
>    | Pass B narrative | `docs/handoff/2026-09-13-ASTRA-PASS-B-results.md` |
>    | Pass B raw receipts | `docs/evidence/astra-pass-b/` (~100 files: mutation diffs/logs, live AWS JSON, bundle comparison, IAM policies, schemas) |
>    | Findings manifest | `docs/handoff/2026-09-13-ASTRA-findings-manifest.yaml` |
>    | Evidence register | `docs/handoff/2026-09-13-ASTRA-evidence-register.yaml` |
>    | P1 reproduction tests | `docs/evidence/p1-repro/` |
>    | Repository | commit `cea0799`, branch `tools/proof-harness` |
>
>    The two `.yaml` files are the authoritative records; the `.md` files are
>    summaries and may compress or round. **Where a `.md` and its `.yaml`
>    disagree, the YAML governs** — and that disagreement is itself worth
>    reporting.
>
>    The two raw-receipt directories are the point. You are authorised to
>    adjudicate against them directly and you are expected to: several of the
>    decisive artifacts (`E010-fatal-write-only.diff`, `E011-*-controlled.log`,
>    `E012-both-header-cases.diff`, `deployed-bundle-comparison.json`,
>    `independent-controls.json`) settle questions that neither narrative fully
>    resolves.
>
> 2. AWS: account `788159322332`, `us-east-1`. **Correction to the earlier
>    checklist — Pass B established that the credentials in use are
>    administrative (`AdminAccess`), not read-only.** Provision genuinely
>    read-only credentials if you can. If you cannot, this session must still
>    issue **only** read-only calls, and must record that the restriction was
>    self-imposed rather than enforced by IAM. Do not perform any write,
>    deploy, mutation, or delete against live AWS under any circumstance.
>
> 3. Do **not** attach `2026-09-12-P1-VERDICTS.md` prose. Pass B already
>    adjudicated it and its structured verdicts reach you through Pass B's
>    output. You are reconciling structured records against raw evidence, not
>    re-reading an essay.

---

You are resolving disagreement between two independent audits.

Pass A derived verdicts blind, from the original inventory and the source, with
no sight of any prior conclusion. Pass B audited a prior reviewer's verdicts and
its evidence. You now hold both, plus the raw evidence both drew on.

**Your authority is the raw evidence, not either audit.** Where A and B agree,
that agreement is a *hypothesis*, not a proof — two passes can share a blind
spot, particularly on the layer-of-test question that runs through this corpus.
Where they disagree, the disagreement is a pointer to where the evidence is
genuinely thin.

**Agreement is not success. Refutation is not success. Correctly calibrated
uncertainty is success.**

## Material classification

```
SOURCE MATERIAL      — repository and deployed AWS resources. Authoritative.
RAW TOOL OUTPUT      — what a command returns when YOU run it.
MODEL INTERPRETATION — Pass A's records, Pass B's records, and P1's verdicts
                       reaching you through Pass B. All non-authoritative,
                       including where two of them agree.
```

## Procedure — for every id in the manifest

1. **Place the id in one of four buckets:**
   - `AGREE-SUBSTANTIVE` — A and B reached the same verdict on the same mechanism.
   - `AGREE-SUPERFICIAL` — same verdict label, different mechanism or different
     reason. Treat as a disagreement; the label is coincidence.
   - `DISAGREE` — different verdicts.
   - `BOTH-UNCERTAIN` — one or both `UNPROVABLE-WITHOUT-DEPLOY`.
2. For `DISAGREE` and `AGREE-SUPERFICIAL`: **go to the raw evidence and decide on
   the evidence**, re-running what is re-runnable. Do not adjudicate by comparing
   the two write-ups, by preferring the more detailed one, or by majority.

   **Bucketing hazard — read before you classify anything.** Both passes split
   verdicts across conjuncts, and both sometimes report a *scalar* label for a
   *composite* claim. Pass B states this explicitly: "a scalar REFUTED identifies
   a contradicted conjunct; it does not erase confirmed mechanisms listed in that
   record." So two passes can print opposite labels while agreeing on every
   mechanism, or print the same label while disagreeing about which conjunct they
   adjudicated. **Classify on the conjunct-level mechanism, never on the top-line
   label.** Where the two passes did not adjudicate the same conjunct, that is
   `AGREE-SUPERFICIAL` at best — decide it yourself on the evidence, and say
   plainly which conjunct each pass actually ruled on.
3. For `AGREE-SUBSTANTIVE`: **spend one deliberate disconfirming effort anyway.**
   State the strongest case against the agreed verdict and whether it survives.
   Agreement between two passes that share a method is weak evidence.
4. For `BOTH-UNCERTAIN`: the verdict stays `UNPROVABLE-WITHOUT-DEPLOY`. Produce
   the **exact command, credential, or environment** that would settle it. Do not
   resolve it by reasoning.
5. Assign the **final verdict** and record which evidence decided it.

## The systematic question you must answer once, globally

Both prior passes rely heavily on in-process `moto` tests to establish
**system-level** security properties. Adjudicate this directly and state the
answer as a finding, because it conditions several verdicts at once:

> Does a handler-level leak demonstrated under `moto` establish an exploitable
> leak in the deployed system, given that the test traverses neither API Gateway,
> nor the Cognito authorizer, nor WAF, nor IAM?

Then state, per affected id, whether its verdict survives your answer. If the
answer is "only in combination with `E-018`" (the deployed method's authorizer
configuration), say what would make that combination airtight and whether anyone
has actually established it.

Related and equally global, **but substantially changed since this prompt was
first written** — read this before you re-litigate it:

`E-022` originally said `DEPLOYED_GIT_SHA` is `null` on the live devx Lambdas, so
no live observation was provably tied to `cea0799`. Pass B went further and
largely closed it: it downloaded the Lambda deployment ZIP, verified its SHA-256
against the AWS `CodeSha256`, and compared all **137 `careervp/*.py` members**
against the commit, reporting **zero mismatches**, with the export, status,
CV-parser and CV-tailor `live-devx` aliases resolving to version 16 on that
bundle. Pass B also found that the `service_stack.py` stamp P1 cited is an
uncommitted **CloudFormation output**, not a Lambda environment variable.

Your job here is **not** to repeat that work. It is to decide whether Pass B's
bundle comparison actually establishes what it claims, and what it leaves open.
Verify the method from `docs/evidence/astra-pass-b/deployed-bundle-comparison.json`,
then rule on the residual: Pass B itself disclaims dependency equivalence, full
deployment configuration, and any executed end-to-end attack. State which
verdicts still carry a live-correspondence caveat after that ruling, and which
are now clean.

## Verdict rules

```
CONFIRMED  requires direct evidence supporting the exact mechanism.
REFUTED    requires direct evidence contradicting the exact mechanism.
Anything else is UNPROVABLE-WITHOUT-DEPLOY.

"I could not reproduce it"  is NOT REFUTED.
"I found no issue"          is NOT CONFIRMED and is NOT a pass.
Majority vote is NOT a resolution method.
```

Where a mechanism is real but a stated trigger, severity, scope, or blast radius
is false, record `CONFIRMED` on the mechanism and enumerate the false conjuncts
in `refuted_subclaims`. Several ids in this corpus are of exactly that shape and
collapsing them to a single label destroys the most decision-relevant
information in the review.

## The base rate — compute it here, and define it properly

You are the only pass authorized to compute a base rate. State, explicitly:

- the **sampling frame** — which population the sampled ids were drawn from, and
  how they were drawn (the P1 session drew with `sort -R` over SEV-1/2/3 ids
  before reading any of them, plus 2 from a "confirmed-good" list; Tier-1 ids
  were **not** random, they were pre-selected as high-impact);
- the **denominator** for each rate you report, and why the Tier-1 ids must not
  be pooled with the random sample without comment;
- **exclusions** and why;
- an **uncertainty interval**, and an honest statement of what a sample of this
  size can and cannot support about the ~85 un-adjudicated findings.

P1 reported: 14/14 claims had a real defect at the core, 0 fully refuted, and
6/14 carried a materially wrong sub-claim. Re-derive those numbers from the final
verdicts rather than inheriting them, and state whether the inference P1 drew
from them — *"treat each entry as a reliable pointer to a location and an
unreliable description of the problem"* — is supported by the corrected data.

## Claims neither pass was asked to adjudicate

Passes A and B each surfaced findings that are **not** in the 20-id manifest.
These must not be lost between rounds, and they must not be smuggled into a
manifest verdict either. Collect them in a separate register with the evidence
each pass offered and a one-line assessment of whether it looks worth a proving
run. Do **not** fully adjudicate them — you do not have a blind pass on them, so
a verdict here would carry none of this review's independence guarantees.

Known examples to capture, non-exhaustive — sweep both outputs for more:

- **`G4` page-two failure.** Both passes confirm pagination is correct, and both
  note that an error on the second page still yields an empty list to the caller.
  That is a different defect from the one `G4` denies.
- **`S0b` write ordering.** Pass B observes the worker uploads to S3 *before*
  canonical persistence and TTL extension, so a failed completion can strand an
  object against an older job TTL.
- **The 26 untracked jobs rows.** Pass B's scan found 36 jobs: 10 completed with
  ~1-year TTLs, 26 `active` with no TTL at all. Neither pass established what
  writes them.
- **The VPR results bucket 365-day lifecycle**, which contradicts the
  "persists indefinitely" premise independently of the TTL question.

## Process findings to record

Two defects in how this review was conducted, not in the system under review.
Record both; neither changes a verdict.

1. **Credential scope.** Pass B established the AWS credentials in use are
   administrative (`AdminAccess`), not read-only as every operator checklist
   claimed. All three passes report having issued only read-only calls, but the
   restriction was self-imposed, not enforced. State the residual risk.
2. **A reproduction artifact ships with wrong assertions.** P1 corrected its
   prose about the two "empty 200" cases but left the failing assertions in
   `docs/evidence/p1-repro/` — Pass B re-ran them and got 3 failed / 13 passed,
   which is expected for that file and must not be read as three production
   defects. Recommend the fix; do not apply it.

Also assess, in one short paragraph: Pass B reports that P1's `E-010` worktree
counts and its claimed single-failure mutation baseline **did not reproduce**,
because the isolated runs hit unmocked AWS transport (real isolated baseline: 46
failed, not 1). Rule on whether P1's mutation-derived conclusions survive being
re-based on the correct baseline — specifically the claim that the VPR *status*
ownership check has zero test coverage, which Pass B appears to sustain via a
separate poisoned-input control even though the naive mutation added no failures.

## Output contract

One YAML record per manifest id:

```yaml
finding_id: S0b
bucket: AGREE-SUBSTANTIVE | AGREE-SUPERFICIAL | DISAGREE | BOTH-UNCERTAIN
pass_a_verdict: "..."
pass_b_verdict: "..."
p1_verdict: "..."
final_verdict: CONFIRMED | REFUTED | UNPROVABLE-WITHOUT-DEPLOY
confidence: high | medium | low
decided_by:
  evidence_ids: [E-002, E-005]
  reran: true | false
  command: "..."
  exit_code: 0
  material_output: "..."
mechanism_final: "..."
refuted_subclaims: ["..."]
disconfirming_effort: "..."          # required even when A and B agree
depends_on_live_aws: true | false     # if true, note the E-022 caveat
layer_caveat: "..."                   # moto vs deployed, where relevant
residual_disagreement: "..."
what_would_change_verdict: "..."
```

Then:

1. **Master comparison table**

| Finding | P1 | Pass A | Pass B | Final | Confidence | Bucket | Decided by | Refuted subclaims |
|---|---|---|---|---|---|---|---|---|

2. **Manifest reconciliation** — every id from the manifest, every id processed
   by A, by B, and by you; any gap, with a reason. Silent omission is a review
   failure at every level, including this one.

3. **Base rate section**, per the definition requirements above.

4. **Corrections to P1** — every place the final verdict differs from P1's, with
   the overturn basis, ranked by how much the correction changes what a developer
   would do next.

5. **What the next proving run must cover** — the consolidated
   `UNPROVABLE-WITHOUT-DEPLOY` set, each with the exact command, credential, or
   environment that would settle it. This is a deliverable, not an apology.

6. **Unadjudicated-claims register** — the out-of-manifest findings above,
   captured but explicitly not verdicted.

7. **Process findings** — credential scope, the mis-asserting reproduction
   artifact, and your ruling on the re-based mutation baseline.

8. **Run metadata** — model, reasoning effort, prompt version (`C/1`), repo
   commit, AWS account/region, timestamps, files and resources inspected.

## Anti-patterns

- Do not adjudicate by comparing write-ups. Go to the evidence.
- Do not treat A+B agreement as proof. Run the disconfirming effort.
- Do not resolve `BOTH-UNCERTAIN` by reasoning. Produce the command instead.
- Do not pool a purposive sample with a random one when computing a rate.
- Do not report a base rate without a denominator and a sampling frame.
- Do not collapse "mechanism real, trigger false" into a single verdict label.
