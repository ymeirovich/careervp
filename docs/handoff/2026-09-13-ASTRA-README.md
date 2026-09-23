# Astra second-order review — operator guide

Validates `docs/handoff/2026-09-12-P1-VERDICTS.md` (the P1 adversarial-validation
session, repo @ `cea0799`).

## Run order — three separate sessions, never one

| Pass | Prompt | Sees | Must NOT see |
|---|---|---|---|
| **A** blind derivation | `2026-09-13-ASTRA-PASS-A-blind-derivation.md` | findings manifest, RECON-FINDINGS, repo, live AWS (read-only) | P1-VERDICTS, evidence register, `docs/evidence/p1-repro/` |
| **B** evidence audit | `2026-09-13-ASTRA-PASS-B-evidence-audit.md` | evidence register, repro tests, repo, live AWS, **then** P1-VERDICTS last | Pass A's output |
| **C** reconciliation | `2026-09-13-ASTRA-PASS-C-reconciliation.md` | A's output, B's output, manifest, register, repro tests, repo, live AWS | P1-VERDICTS prose |

Do not let one conversation perform two roles. The independence is the method.

## Supporting artifacts

- `2026-09-13-ASTRA-findings-manifest.yaml` — 20 stable ids, original claim text,
  **no verdicts**. The Pass-A input and the reconciliation key for all three passes.
- `2026-09-13-ASTRA-evidence-register.yaml` — 22 records (`E-001`…`E-022`), each
  separating `material_output` from `interpretation_by_p1`. The Pass-B input.
- `docs/evidence/p1-repro/` — four runnable tests reproducing P1's core claims,
  with exact invocations and a caveats section. Read its README before running:
  **the tests assert the defect, so a green run demonstrates the bug.**

## Settings

- Model **GPT-6 Astra**, `reasoning.effort: high` for all three passes.
  Escalate to `xhigh` only for individually disputed, high-impact ids.
- A cheaper/lower-effort model is appropriate for mechanical steps only —
  id extraction, schema validation, table diffing — never for adjudication.
- **Read-only** AWS credentials, account `788159322332`, `us-east-1`,
  stack `CareerVpCrudDevx`. Nothing in this review requires a mutating call.
- Record model, effort, prompt version, repo commit, environment and timestamps
  in every pass's run-metadata block. Pin the model snapshot if you intend to
  reproduce the review later.
- Checkpoint each pass's structured output to a file before starting the next.

## Verify before you start

1. That the model selector actually reads GPT-6 Astra — do not assume from the
   plan tier or the API docs.
2. That the sandbox can run `uv run pytest` in `src/backend`.
3. That AWS credentials resolve and are read-only.
4. Whether the Codex UI exposes the reasoning-effort control at all; if not,
   record what it does expose.

## The one thing to watch for

P1's document is fluent, specifically cited, internally consistent, and ships
execution transcripts. That is the exact profile most likely to be ratified
rather than examined. Every prompt here is built to resist that — through blind
derivation in Pass A, a mandated disconfirming effort even on agreement in Pass C,
and an explicit calibration self-check in Pass B that counts unsupported
reversals so overcorrection is visible too.

A known weak point, flagged for the auditor in all three prompts: P1 proves
system-level security properties with in-process `moto` tests that never traverse
API Gateway, the Cognito authorizer, WAF, or IAM — and per `E-022`,
`DEPLOYED_GIT_SHA` is `null` on the live Lambdas, so no live observation is
provably tied to `cea0799`. Pass C must rule on both globally.

---

## Data flow — what feeds what

```
Pass A (blind)  ──┐
                  ├──→  Pass C (reconcile)  ──→  final verdict set
Pass B (audit)  ──┘
```

**A and B are independent of each other.** Neither receives the other's output.
Run them in parallel in two windows if you like — it halves the wall clock and
costs nothing in rigor, because their independence is exactly what Pass C is
measuring. Feeding B into A (or A into B) destroys the method: you would get one
opinion twice.

**Only Pass C receives both.**

## Where to put each pass's output

```bash
mkdir -p docs/evidence/astra
```

> **Actual locations — A and B have landed.** They did not use the paths
> originally suggested below. What exists now is authoritative:
>
> | Pass | Verdicts (authoritative) | Narrative | Raw receipts |
> |---|---|---|---|
> | A | `docs/handoff/2026-09-13-ASTRA-PASS-A-results.yaml` | `...-PASS-A-results.md` | `docs/evidence/astra-pass-a/` |
> | B | `docs/handoff/2026-09-13-ASTRA-PASS-B-results.yaml` | `...-PASS-B-results.md` | `docs/evidence/astra-pass-b/` |
> | C | `docs/handoff/2026-09-13-ASTRA-PASS-C-results.yaml` (to be produced) | `...-PASS-C-results.md` | `docs/evidence/astra-pass-c/` |
>
> Where a `.md` and its `.yaml` disagree, the YAML governs.
> The Pass-C prompt has been updated with these exact paths; no further edit is
> needed before running it.

Save the YAML records *and* the prose sections (reconciliation block, calibration
self-check, run metadata). If a pass emits them in one stream, keep the stream —
the run metadata is what lets you reproduce or discount the pass later.

Attach the two saved files to Pass C as files, not pasted text.

## Gate each pass before you use it

A pass that quietly dropped findings or fabricated a run will contaminate
everything downstream. Check these **before** moving on, and re-run the pass if
any fail. Do not hand-patch the output.

```bash
# 1. Does it parse, and did it cover all 20 ids?
python3 - <<'PY'
import yaml
man = yaml.safe_load(open('docs/handoff/2026-09-13-ASTRA-findings-manifest.yaml'))
ids = {c['id'] for k in ('defect_claims','good_claims','premise_claims') for c in man[k]}
got = yaml.safe_load(open('docs/evidence/astra/pass-a-verdicts.yaml'))  # or pass-b
seen = {r['finding_id'] for r in (got if isinstance(got, list) else got['records'])}
print('missing:', sorted(ids - seen))
print('unexpected:', sorted(seen - ids))
PY
```

2. **Every execution claim carries a transcript.** Spot-check three records: is
   there a command, a cwd, an exit code, and material output? "I ran the test and
   it passed" with no transcript is a fabricated-execution signal — re-run the pass.
3. **It named its governing instruction files.** If the pass never mentions
   auditing `CLAUDE.md`, its other compliance claims are unverified too.
4. **Verdicts use only the three allowed labels.** Any `PASS`, `OK`, `LIKELY`,
   or `NOT REPRODUCED` is silent-PASS decay — re-run.
5. **Pass B only: the calibration self-check is present and its counts are zero
   or explained.** A high overturn rate with unsupported reversals means it
   overshot into contrarianism and the pass is not usable as-is.
6. **Run metadata block present** — model, effort, prompt version, commit,
   account/region, timestamps, files inspected.

## What to do with the final output

Pass C produces six things. Here is what each is for.

| Pass C section | What you do with it |
|---|---|
| Master comparison table | The authoritative verdict set. This supersedes P1's table. |
| Manifest reconciliation | Proof nothing was dropped across three passes. File it. |
| Base rate (with denominator + sampling frame) | Decides how much to trust the **~85 findings nobody adjudicated**. This is the number that scopes future work. |
| Corrections to P1 | Ranked list of where P1 was wrong. Drives the two actions below. |
| `UNPROVABLE-WITHOUT-DEPLOY` set | Becomes the task list for the next proving run — each entry already carries the exact command or access it needs. |
| Run metadata | Reproducibility. Keep with the verdicts. |

**Then, in order:**

1. **Do not delete or rewrite `2026-09-12-P1-VERDICTS.md`.** It is the audit
   trail — the record of what was believed before the audit. Add a header
   pointing at `pass-c-final.yaml` as the superseding authority. Keeping the
   superseded document is what lets anyone later check whether the *audit* was
   sound, which is the same discipline that caught the P1 errors.
2. **Act on the CONFIRMED set**, ranked by the corrections table. Anything with a
   `refuted_subclaims` entry gets fixed against the *corrected* mechanism, not
   the original claim — that is where the multi-day wrong-fix risk lives.
3. **Drop the REFUTED set** from the work queue, and note in each dropped item
   why, so it does not get rediscovered and re-filed in three weeks.
4. **Re-scope P2 through P5** using the four `PREMISE-*` verdicts. Each carries an
   explicit "should grow / shrink / stand" instruction. If Pass C overturns any
   of P1's premise verdicts, those session prompts need rewriting before they run
   — that is four sessions of work pointed by a single verdict each.
5. **Schedule the proving run** from the `UNPROVABLE` set. Until it runs, every
   one of those stays `UNPROVABLE`. It does not decay to "fine" with age.

**Bring `pass-c-final.yaml` back to the assistant** to regenerate the P2–P5
prompts against the corrected premises and scope.

## Reading the outcome

- **Pass C overturns little and the base rate roughly holds** — P1's verdicts
  stand, and the corrected set is safe to execute against.
- **Pass C overturns a few, mostly on `refuted_subclaims`** — the expected
  result. Mechanisms were right, some triggers and severities were wrong. Fix
  against corrected mechanisms.
- **Pass C overturns a SEV-0, or rules that `moto`-level proof does not establish
  a system-level leak** — stop and re-plan. Two of P1's headline findings and its
  recommended fix order depend on that ruling.
- **Pass A and Pass B disagree broadly** — the corpus is thinner than either
  believed. Trust Pass C's evidence-decided verdicts only, and treat every
  `AGREE-SUPERFICIAL` bucket entry as unresolved.

## Cost note

Passes A and B are the expensive ones — each reads the repository and runs tools
across 20 ids. Pass C is comparatively cheap: its inputs are two structured YAML
files plus targeted re-runs, not a fresh repository sweep. Budget accordingly,
and do not economize by merging passes — a merged pass is not a cheaper review,
it is a different and much weaker one.
