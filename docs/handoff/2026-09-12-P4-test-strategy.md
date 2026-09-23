# P4 — Provable specs & requirement-mapped coverage

**Model: Opus 5, xhigh effort. Runs in parallel with P2/P3.**
**Prerequisite: read `docs/handoff/2026-09-12-P0-COMMON.md` first — it is binding.**

---

You are designing the test and specification strategy for a pre-launch serverless
app whose owner does not trust its existing tests, with cause.

## The actual problem

This repo is heavy with tests and specs, and they did not prevent ~100 defects —
including a cross-tenant data leak on a live route, a CV upload path that 500s on
any CV with a GPA, and a gap-analysis state machine that has never once advanced.
Coverage numbers exist (last recorded: **72.97% core / 54.34% overall**, commit
`78c072f`) and they did not correlate with correctness.

The owner's own diagnosis, which you should take seriously as a hypothesis to
verify rather than a complaint to soothe:

> *"the specs did not validate the work against live deployed code when moving
> between specs and the tests did not provide 100% coverage — there is no
> guarantee that the tests were written correctly as some may have been
> self-closing and did not fail initially."*

One hard datum supporting it, from `docs/HARNESS.md`: the 25 older e2e specs in
`src/frontend/tests/e2e/` contain **282 test blocks and 113 live assertions** —
the rest are commented out. They pass while proving nothing.

## Part 1 — Measure the real state (do this before designing anything)

Produce numbers, not impressions. All are OBSERVATIONs with the command shown.

1. **Assertion density.** For backend (`src/backend/tests/`) and frontend
   (`src/frontend/tests/`): count test functions vs. actual assertions. Identify
   tests with zero assertions, tests whose only assertion is `assert True` /
   `expect(true)` / a mock being called, and tests that are skipped or xfail.
   Report the count and the worst offenders by file.

2. **Self-closing tests.** The critical class: a test that passes both with and
   without the code it claims to test. Design a cheap detection method and run it
   on a sample — mutation testing (`mutmut` is referenced in the scope-lock as
   deferred to Wave 3), or the poor-man's version: revert a known fix and see
   which tests go red. **Verify against a known case:** commit `7cdc5e5` ("make
   the cvs-table write fatal") changed a swallow into a 500. Did any pre-existing
   test fail because of it? If not, that is your proof the suite was blind to it.

3. **Requirement coverage, not line coverage.** Line coverage says which lines
   ran. It does not say which *requirements* are proven. Build the mapping:
   for every V1 feature in `CLAUDE.md` and every clause in
   `project-scope-lock.yaml` (v3.0.0), which test file asserts it? Expect large
   gaps — report them as the primary finding of this section.

4. **The inverse: code with no requirement.** Which modules have tests but trace
   to no spec clause? That is scope that arrived without a decision.

## Part 2 — What "provable" must mean here

Define the standard, then justify it against the failures above. At minimum
address:

- **RED-before-GREEN as an enforced gate, not a convention.** The wave-1/2/3
  runbooks already split RED and GREEN into separate sessions. Extend it: a test
  that has never been observed failing is unverified. Propose the mechanism that
  makes this checkable after the fact (a recorded RED output per test? a CI job
  that reverts and re-runs? your call — cheapest that actually works).
- **Assert on externally observable outcomes.** `journey.spec.ts:292-294`
  reloads the page before believing gap answers persisted, rather than trusting
  in-memory form state. Generalize that principle into a rule.
- **Never let "loading finished" stand for "it worked"** — `journey.spec.ts` puts
  it well: *"a failed generation also stops spinning."*
- **Round-trip tests per entity.** Write via the real write path, read via the
  real read path, assert equality. Most of the ~100 defects would have died
  instantly to this. **No such test exists for any entity today.** Specify one
  per entity: users, cvs, applications, jobs, artifacts (×4 types),
  gap_responses, company_research.
- **Contract tests between layers.** The frontend calls
  `POST /api/proxy/auth/logout`, which does not exist (404 on every sign-out,
  swallowed). A frontend↔backend contract test would have caught it. Note there
  is already a contract-oracle mechanism (`src/frontend/lib/contractOracle.ts`,
  `src/backend/scripts/emit_json_schemas.py`) — evaluate whether it is live and
  sufficient, or theatre.
- **Infra assertions.** The R1 root cause (a table env var resolving to the wrong
  physical table) is catchable by a CDK synth assertion. So is the WAF
  environment-parity bug. Specify these.

## Part 3 — Getting past 80%, meaningfully

The target is **>80% coverage that maps to requirements** — not 80% of lines.

- Propose the coverage metric you'd actually gate on, and defend it. Line
  coverage, branch coverage, mutation score, requirement coverage — argue the
  mix. A number that can be gamed by testing getters is worse than no number.
- Identify the highest-value untested surface. The six root causes (R1–R6 in the
  inventory) are a better guide than a coverage report: R3 alone is ~40 findings
  and is almost entirely untested error paths.
- Sequence it: which tests to write first so that the P2 and P3 remediation work
  has a net under it *before* it starts. This is the dependency that matters —
  those sessions will be changing the data layer and the error-handling idiom,
  and they need regression protection that exists beforehand.
- State the honest cost. Getting from 54% overall to >80% requirement-mapped
  coverage on a codebase this size is a real number of sessions; estimate it and
  say what can be cut if the estimate is unacceptable.

## Part 4 — Keeping it true

The failure mode to design against is not "we never wrote tests." It's "we wrote
tests that stopped meaning anything." Specify:

- The CI gate that blocks a merge (coverage floor, assertion-density floor, the
  `Limit`+`FilterExpression` lint, a no-`except Exception: pass` rule — propose
  the set).
- What `make journey` must report before a change is considered done, and what
  the rule is when the number goes **down** (`docs/HARNESS.md` says: revert
  first, investigate second).
- How a *new* requirement enters the traceability table so the mapping doesn't
  rot the way `PROGRESS.md` did.

## Output

Per `P0-COMMON.md` §4, ending with the traceability table — for this session the
**Tests** column is the payload, and `Status` should reflect whether each
requirement is *provably* satisfied, not whether code exists.

Plus:

1. Part 1's measurements, with commands and raw output.
2. The provability standard (Part 2), as rules someone can apply without you.
3. The sequenced plan to >80% requirement-mapped coverage, with a cost estimate
   and a cut list.
4. The CI gate specification.
5. **The list of tests that currently prove nothing and should be deleted.**
   Deleting a lying test is a net gain; leaving it is worse than having no test,
   because it reports safety that isn't there.

## Constraints

- **Design and measure. Do not write the test suite in this session.** Measuring
  Part 1 will require running commands — that is expected and encouraged.
- No test you propose may be satisfiable by a mock asserting it was called.
- If you conclude the existing suite is better than the owner believes, say so
  with evidence. That would be genuinely good news and it should not be softened
  into agreement with the premise.
