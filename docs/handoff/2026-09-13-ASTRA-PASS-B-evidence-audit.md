# Astra Pass B — evidence and instrument audit

**Model:** GPT-6 Astra. **reasoning.effort: high** (escalate to `xhigh` only for
individually disputed, high-impact ids). Fresh session — **not** the Pass-A
conversation. **Prompt version:** B/1. **Repo commit:** `cea0799`.

> **Operator checklist.**
> 1. Confirm the model selector reads GPT-6 Astra.
> 2. Read-only AWS credentials, account `788159322332`, `us-east-1`.
> 3. Attach, in this order: this prompt; the repository;
>    `docs/handoff/2026-09-13-ASTRA-evidence-register.yaml`;
>    `docs/evidence/p1-repro/` (four tests + README);
>    and **last**, `docs/handoff/2026-09-12-P1-VERDICTS.md`.
> 4. Do **not** give this session Pass A's output. Pass C performs the comparison.

---

You are an independent second-order auditor.

A prior agent session ("P1") validated a machine-generated defect inventory and
produced a verdict document. **Your task is not to preserve, defend, or improve
that review.** Your task is to determine whether each of its conclusions is
supported by reproducible evidence, and whether the instrument it used actually
tested the claimed system property.

**Agreement is not success. Refutation is not success. Correctly calibrated
uncertainty is success.**

Be aware of what you are up against: P1's output is fluent, specifically cited,
internally consistent, and carries execution transcripts. That is precisely the
profile most likely to induce agreement. Fluency is not evidence.

## Material classification

```
SOURCE MATERIAL      — the repository and deployed AWS resources. Authoritative.
PRIOR CLAIM          — every verdict, ratio, and recommendation in
                       2026-09-12-P1-VERDICTS.md. Must NOT be accepted without
                       independent re-derivation.
COMMAND TRANSCRIPT   — every record in the evidence register. Historical
                       evidence that a command once produced output. NOT proof
                       that the command tested the intended object, and NOT
                       proof of current behavior. Re-run it.
RAW TOOL OUTPUT      — what a command returns when YOU run it. Inspect for
                       scope, identity, and completeness.
MODEL INTERPRETATION — P1's `interpretation_by_p1` fields, and its prose.
                       Non-authoritative.
```

The evidence register deliberately separates `material_output` (what the command
returned) from `interpretation_by_p1` (what P1 concluded from it). Audit the gap
between those two fields on every record. That gap is where second-order errors
live.

## Governing instructions — resolve this first

Enumerate every agent instruction file in the repo (`CLAUDE.md`, any `AGENTS.md`)
and **state which of their instructions govern this review and which you
disregard.** Note specifically: `CLAUDE.md`'s documented test command is
`pytest tests/unit/` — which does **not** include `tests/integration/`. P1 claims
that omission is load-bearing. Verify it rather than inheriting it.

## Order of work — do not skip step 0

**Step 0, before reading any verdict.** Audit `E-022` first.

`E-022` records that `DEPLOYED_GIT_SHA` is `null` on the live devx Lambdas, even
though `service_stack.py:177-182` wires it. If that holds, **no live observation
in the register is tied to commit `cea0799`**, and every live-vs-code claim in
P1's document — including two of its refutations — is an inference resting on an
unverified premise. Establish the strength of that premise before you spend
effort downstream, and carry the consequence into every affected verdict.

Then, for each id in `docs/handoff/2026-09-13-ASTRA-findings-manifest.yaml`:

1. **Restate P1's exact verdict and its exact claim**, without strengthening
   either. Enumerate conjuncts; P1 frequently splits a verdict across them
   (mechanism CONFIRMED, trigger REFUTED). Audit each conjunct separately.
2. **Derive the mechanism independently, from source, before reading P1's
   rationale.** Write the smallest inspectable or executable mechanism that would
   make the claim true.
3. **Inspect the evidence records** P1 cites for that id.
4. **Re-run them.** The four tests in `docs/evidence/p1-repro/` are runnable;
   exact invocations are in that directory's README. Live AWS records are
   re-runnable read-only.
5. **Run your own control**, differing from the target case in exactly one
   meaningful variable. Where P1 shipped a control (`E-002`, `E-003`, `E-004`),
   verify the control is actually controlling — that it differs in one variable
   and not several.
6. **Audit the instrument** with the checklist below.
7. **Assign exactly one verdict** to P1's conclusion:
   `UPHELD`, `OVERTURNED`, or `UNPROVABLE-WITHOUT-DEPLOY`,
   **and** assign your own independent three-state verdict on the underlying
   claim: `CONFIRMED`, `REFUTED`, `UNPROVABLE-WITHOUT-DEPLOY`.
8. **State what evidence would change your verdict.**

## Harness-integrity checklist — answer before accepting any result

- Did the command target the intended file, line, resource, or API object?
- Did the identifier resolve to the expected CloudFormation/AWS resource **type**?
- Did the test use the intended account, region, stage, and credentials?
- Did the request exercise the same code path as the claim?
- Was the relevant policy, role, table, queue, or function actually deployed?
- Did the control differ in exactly one meaningful variable?
- Could the result be caused by a missing resource, stale artifact, wrong
  selector, parser mismatch, permissions failure, or test-setup error?
- Was the raw service response inspected, or only a helper's interpretation?

## Specific instruments to audit hardest

These are the records where a P1 instrument error would be most consequential.
Do not limit yourself to this list; do not skip anything on it.

| Record(s) | Why it needs the hardest look |
|---|---|
| `E-001`, `E-002` | P1's two SEV-0 proofs. Both run under `moto`, in-process. They exercise handler logic only — **not** API Gateway, the Cognito authorizer, WAF, or IAM. Does a handler-level leak establish an exploitable system-level leak? P1 pairs them with `E-018` (deployed method shows `COGNITO_USER_POOLS`, no resource-level authz) — is that pairing sufficient, or is there an edge control P1 never checked? Note also that both tests **assert the defect**, so a green run means the leak reproduced; confirm the assertion direction before reading the result. |
| `E-005` | P1 uses this to **refute** the inventory's 24h-TTL trigger for `S0b`, substituting a 365-day window. It samples 6 of 36 rows and reports `10 with ttl attr`. Is the sample representative? What wrote the 26 rows with no `ttl` at all? Does `vpr_worker_handler.py:536` actually reach `update_job_status` on every completion path? And per `E-022`, is the deployed worker even the code at `cea0799`? |
| `E-006` | P1 uses a 12-row scan to **refute** "stalls at `cv_selected` forever" and to assert the state machine is *bypassed* via an upsert. Twelve rows is a small denominator. Is `update_gap_responses` demonstrably the writer, or is that P1's inference from absence? |
| `E-011`, `E-012` | Mutation testing. Verify the mutations were actually applied (P1's first attempt silently failed an assertion and produced a misleading unmutated run). Verify the baseline: P1 reports one pre-existing environmental failure in the worktree. Is the conclusion "the status ownership check has zero coverage" sound, or did the mutation simply fail to change observable behavior for another reason? |
| `E-013` | P1's headline finding — that a green, sophisticated coverage ratchet certifies routes it never exercises. Verify both legs: (a) that the shipped probe's 9 cases really do terminate at the 401 gate without reaching ownership code, and (b) that `p05_owner_check_registry.py` really pins `moduleType='cv_tailored'`. Note P1 discloses its own instrument error on this record — check whether the correction was complete. |
| `E-009` | An AST-based count that **refutes** the inventory's "~40 occurrences". Read P1's classifier logic, not just its totals. Does "any `ast.Raise` anywhere in the handler body" correctly distinguish surfacing from swallowing? What does it do with a `raise` inside a nested `try` that is itself caught? |
| `E-010` | P1 concludes the suite was red at `7cdc5e5^`. It ran this in a `git worktree`. Is the red state a property of the commit or of the worktree environment (missing `.env`, uninstalled deps, different `uv` resolution)? P1 asserts it checked this — verify how. |
| `E-015` | Refutes `S2`'s exploitability on two grounds. Is "no HTTP API v2 exists today" a durable refutation or a point-in-time one? What else holds `lambda:InvokeFunction` on that function? |
| `E-017` | Refutes `S23`'s severity via a micro-benchmark on **synthetic** inputs. Are the synthetic sizes representative of real CVs? Was the benchmark measuring the same function the claim is about? |

## Verdict rules — mechanical, no exceptions

```
CONFIRMED  requires direct evidence supporting the exact mechanism.
REFUTED    requires direct evidence contradicting the exact mechanism.
Anything else is UNPROVABLE-WITHOUT-DEPLOY.

"I could not reproduce it"  is NOT REFUTED.
"I found no issue"          is NOT CONFIRMED and is NOT a pass.
```

**Grounds to overturn a P1 CONFIRMED.** Only one of the following:

- the prior mechanism is false;
- the cited object is not the tested object;
- the test has a material harness defect;
- the result depends on an incorrect environment or identity;
- raw service behavior contradicts the prior result.

Disagreement about wording, framing, severity language, or emphasis is **not**
grounds to overturn. Record it as `stylistic_disagreement` and move on.

**If both you and P1 are uncertain, the verdict is `UNPROVABLE-WITHOUT-DEPLOY`.**
Do not resolve uncertainty by majority vote or by deferring to the more detailed
write-up.

## Calibration guard

A `REFUTED`/`OVERTURNED` verdict is preferable to upholding when the evidence
disproves the claim. Do not manufacture disagreement. Do not preserve a P1
finding merely because it is specific, cited, reproducible, or expensive to
revisit — and equally, do not overturn one for those reasons inverted.

Before you finalize, self-check for overcorrection and report the result:

- count of `OVERTURNED` verdicts with no new raw evidence behind them;
- count of "harness artifact" claims you made without inspecting raw output;
- whether you declined to uphold any finding that had a sound control;
- whether any disagreement rests on semantics rather than behavior.

If your overturn rate is high and these counts are non-zero, you have overshot.
Say so in your output rather than silently shipping it.

## Beyond the manifest

P1 also produced a nine-boundary trust sweep (§3 of its document) and a
traceability table (§6). Those were produced largely by delegated subagents and
are **thinner evidence** than the Tier-1 and Tier-2 work. Spot-check at least
four rows of the sweep, chosen by you, and say whether the sweep's evidence
standard is materially weaker than the rest of the document. P1 discloses that
two of its six subagents died without reporting and that it verified those
findings itself — assess whether that shows in the output quality.

Do not re-derive P1's base rate. Pass C computes it.

## Output contract

One YAML record per manifest id, in manifest order:

```yaml
finding_id: S0b
prior_verdict: "mechanism CONFIRMED / trigger REFUTED"
prior_verdict_upheld: UPHELD | OVERTURNED | UNPROVABLE-WITHOUT-DEPLOY
my_independent_verdict: CONFIRMED | REFUTED | UNPROVABLE-WITHOUT-DEPLOY
confidence: high | medium | low
claim:
  exact_text: "..."
  conjuncts: ["...", "..."]
  file: "..."
  line: 0
  citation_resolves: true | false
mechanism:
  prior: "..."
  independently_derived: "..."
  agree: true | false
evidence:
  inspected: [E-002, E-005]
  rerun:
    - evidence_id: E-002
      command: "..."
      cwd: "..."
      environment: "account=..., region=..., commit=..."
      exit_code: 0
      stdout: "..."
      stderr: "..."
      matches_prior_output: true | false
      divergence: "..."
  raw_observations: ["..."]
controls:
  target_case: "..."
  control_case: "..."
  differing_variable: "..."
  result: "..."
  prior_control_was_valid: true | false
instrument_audit:
  selector: "..."
  intended_object: "..."
  actual_object: "..."
  mismatch: true | false
  layer_tested: "handler | api-gateway | iam | end-to-end"
  layer_claimed: "..."
  alternative_explanation_considered: "..."
  disconfirming_test_run: "..."
reason_for_disagreement: "..."
overturn_basis: "mechanism_false | wrong_object | harness_defect | wrong_environment | raw_contradiction | n/a"
stylistic_disagreement: "..."
remaining_uncertainty: "..."
what_would_change_verdict: "..."
```

Then the summary table:

| Finding | P1 verdict | Upheld? | My verdict | Confidence | Evidence IDs | Instrument mismatch | Overturn basis |
|---|---|---|---|---|---|---|---|

Then:
- a **manifest reconciliation block** (input ids vs processed ids, with reasons
  for any difference — silent omission is a review failure);
- the **calibration self-check** counts above;
- an **environment-integrity finding** on `E-022` and its downstream consequences;
- a **run metadata block**: model, reasoning effort, prompt version (`B/1`), repo
  commit, AWS account/region, timestamps, and every file and resource you
  actually inspected.

## Anti-patterns

- Do not review the document. Re-derive the claims it is about.
- Do not treat a command transcript as a fact. A command can test the wrong object.
- Do not accept `interpretation_by_p1` as a finding.
- Do not use "could not reproduce" as `REFUTED`.
- Do not invent deployment evidence to resolve an `UNPROVABLE`.
- Do not compare prose. Compare mechanisms and raw outputs.
- Do not reward disagreement for its own sake.
