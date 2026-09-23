# HANDOFF 16 — J9 closed, and the three defects it was hiding

**Model: Opus 5, high effort.** This continues HANDOFF-14, which owned J9, the
gap-response contract, and PRs #230/#232. HANDOFF-15 was written in parallel by
a read-and-assess session and covers W7–W10; it does not overlap with this.

Fresh session at the repo root on `tools/proof-harness`.

---

## The one-sentence version

**Five PRs landed and five deploys were validated; the gap-response contract is
fixed and proven in the live worker log; J9 now reaches the export Lambda for
the first time and exposed a real product defect — the artifacts bucket had no
CORS rule, so browser export has been broken for every user — and the `-dirty`
stamp turned out to be committed setuptools metadata, not anything to do with
requirements files.**

---

## Step 0 — verify before trusting this document

| # | Command | Expected |
|---|---|---|
| 0.1 | `aws cloudformation describe-stacks --stack-name CareerVpCrudDevx --region us-east-1 --query "Stacks[0].Outputs[?OutputKey=='DeployedGitSha'].OutputValue" --output text` | `469db656…` **with no `-dirty` suffix** |
| 0.2 | `git log -1 --oneline origin/db-redesign` | `469db65 Merge pull request #235 …` or later |
| 0.3 | `aws s3api get-bucket-cors --bucket careervp-devx-artifacts-use1-747cad --region us-east-1` | a `GET` rule listing the Amplify origins |
| 0.4 | `aws dynamodb get-item --region us-east-1 --table-name careervp-users-table-devx --key '{"pk":{"S":"USER#848834a8-4061-703d-419c-0294d4e88d66"},"sk":{"S":"TRIAL"}}' --query 'Item.application_count.N' --output text` | `3` — **0 runs left of 3** |
| 0.5 | `git ls-files infra/service_cdk.egg-info/` | empty — untracked now |

If 0.1 still shows `-dirty`, the egg-info fix regressed; see §3.

---

## What landed

| PR | What | Deploy | Validated |
|---|---|---|---|
| #232 | infra spec checks validate instead of crashing | none (workflow-only) | no deploy job fired — confirmed |
| #230 | 23 pip-audit CVEs across 4 packages | `00caf602` | 22 outputs, only `DeployedGitSha` moved |
| #233 | gap-response contract, INFO swallow, J9 selector | `67276657` | same |
| #234 | uv-independent requirements exports | `d6b1d1b` | same |
| #235 | egg-info untracked, artifacts-bucket CORS | `469db656` | same |

Every deploy diffed at exactly 22 stack outputs with only `DeployedGitSha`
changing. No resources lost.

---

## 1. The gap-response contract — fixed and *proven*

HANDOFF-14 called this the important item, and it was right that a green J8
concealed it.

**The defect.** `get_gap_responses` ran `GapResponse.model_validate` on items
written by `save_gap_responses_raw`. The writer persists
`{question_id, response}`; the model requires `{question_id, question, answer}`.
Every call raised `ValidationError`, was returned as a DAL failure, and the
handler logged it at INFO as "lookup empty". Interview prep was generated from
CV + VPR alone.

**Why option 1 as written was not viable.** HANDOFF-14 preferred sourcing
`question` inside `get_gap_responses`. That DAL is bound to
`careervp-gap-responses-table-devx`, which contains only
`ARTIFACT#GAP_RESPONSES#v1` items — no question records at all. Verified by
scanning the table.

**What was reused instead.** `vpr_worker_handler._fetch_gap_responses_from_application`
already solves this exact join, and its docstring states the contract outright.
It maps `response`→`answer` and falls back to the `question_id` when question
text is missing. `gap_questions` is absent from **every** live application
record, so that fallback is the path always taken. The DAL now uses the same
convention, leaving `GapResponse` untouched — so cover letter, VPR and
`VPRRequest` keep today's contract and HANDOFF-14 §4.2's risk never arises.

**Proof, from the live worker log (not a green tick):**

```
gap_responses_degraded: false
10 entries, keys ['answer','destination','question','question_id']
answer: "I don't have specific details in my CV about direct ownership of
         pricing tier design or per-user/per-cohort re…"
```

**Two things found along the way, both still open:**

- `save_gap_responses` — the *typed* writer, the one that produces the correct
  shape — has **zero callers**. Only `save_gap_responses_raw` is live. This is
  the underlying reason the contract drifted. Decide whether to wire it up or
  delete it; leaving dead code that documents the correct shape while the wrong
  shape ships is the worst of both.
- Every pre-existing interview-prep test **mocks the DAL**, which is exactly why
  this survived. The new tests in
  `tests/unit/test_gap_response_stored_contract.py` drive the real handler
  against the exact live item shape: 6 of 7 fail before the fix, 7 pass after.

---

## 2. J9 — now measured, and it found a real defect

**Before:** the selector matched the `Export` **toggle**
(`setOpen(o => !o)`); the real download buttons render inside the menu it
opens. J9 waited 240s for a download needing a second click. Zero invocations
of the export Lambda, ever.

**Two selector bugs, not one.** The second nearly cost a trial credit: the first
fix clicked "Download as PDF", and `export_handler._handle_export` returns
**501 for `format=pdf`** — only `docx` is implemented. That would have failed
J9 with the identical `TimeoutError` for a completely different reason. Caught
by reading the handler before running, not after.

This also corrects HANDOFF-14: it called `title="Export coming soon"` a stale
tooltip. It is stale on the docx item and **accurate on the PDF one**. It is now
rendered for PDF only.

**What the run proved:**

| | Before | 2026-09-23 run |
|---|---|---|
| `careervp-export-lambda-devx` invocations | 0 | **1** |
| errors | — | **0** |
| J1–J8 | 8 pass | **9 pass** |
| J9 | never reached backend | backend reached, returned 200 |

**The defect it exposed.** The UI showed `"Download failed. Please try again."`
— the generic catch, not the 501 branch. `handleExport` fetches the presigned
S3 URL **cross-origin**, and `aws s3api get-bucket-cors` on the artifacts bucket
returned `NoSuchCORSConfiguration`. The sibling CV bucket in the same file has
carried a GET `CorsRule` all along; `_build_artifacts_bucket` never got one.

**Export has been broken in the browser for every real user, not just the test.**

The rule alone would not have fixed it: `_s3_frontend_origins` returned
`["http://localhost:3000"]` for devx, on the stated assumption that no deployed
frontend depends on it. devx serves the Amplify branch `db-redesign`, so that
assumption was false. devx now reuses the same `allowed_origins` context the API
already trusts. This also widens CORS on the `cvs` and `vpr-results` buckets,
which had the same latent bug — an intentional, disclosed change. No wildcard
origin anywhere.

---

## 3. The `-dirty` stamp — I got this wrong twice

Worth reading in full, because the failure was one of **method**, not knowledge.

| Attempt | Hypothesis | Deploy | Result |
|---|---|---|---|
| #233 | stale committed `dev_requirements.txt` | `67276657` | still `-dirty` |
| #234 | uv 0.5.21 vs modern uv `# via` annotations | `d6b1d1b` | still `-dirty` |
| #235 | **committed `infra/service_cdk.egg-info/`** | `469db656` | clean |

Both early hypotheses were real drift, independently worth fixing, and both were
confidently predicted to work. Both were inferred from reading
`src/backend/Makefile` rather than from observing CI.

The fix was to make CI report the state after **each** deploy step:

```
after checkout             lines=0
after setup-uv             lines=0
after uv python install    lines=0
after setup-node           lines=0
after uv sync --group dev  lines=2   ← M infra/service_cdk.egg-info/SOURCES.txt
                                        M infra/service_cdk.egg-info/top_level.txt
after make build           lines=2
```

`src/backend/pyproject.toml` declares
`service-cdk = { path = "../../infra", editable = true }`, so `uv sync` performs
an editable install and setuptools regenerates the egg-info — **five files of
which were committed**. Every `uv sync` in CI modified tracked files before
`make deploy-devx` evaluated `GIT_STAMP`.

This is why correcting the requirements exports never helped: those files were
never the ones being rewritten.

After the fix, the same diagnostic reports `lines=0` at every step and
`GIT_STAMP=dc7de256…` with no suffix — verified **before** deploying.

**A defect I introduced and then fixed.** The `Requirements Drift` guard added
in #233 ran uv `"latest"` while the deploy runs `0.5.21`, so it validated
something the deploy never does. It passed on #233 and that deploy came out
dirty anyway — a false green. It is now pinned to the deploy's version.

### Do this next

**Remove the `Dirty Stamp Diagnostic` job** from `pr-validation.yml`. It has
served its purpose and runs a full docker `make build` on every PR. It was
committed as explicitly temporary.

---

## What's next, ordered by what unblocks the most

1. **`save_gap_responses` has no callers.** Wire it up or delete it (§1).
2. **Remove the temporary diagnostic job** (§3).
3. **`GENERATED_BUCKET_NAME` / `s3_spec.yaml`** — carried from HANDOFF-14 and
   still open: the spec declares 2 buckets while infra builds 6, so the repaired
   check validates one direction against an incomplete spec and would not notice
   four of the six disappearing.
4. **The five workflows pinning `UV_VERSION: '0.5.21'`** (Jan 2025) while 23
   other places use `latest`. Not currently breaking anything — `make deps`
   output is version-independent now — but it is a split-brain waiting to bite.
5. **HANDOFF-15's W7–W10** — Lambda config, performance, API contracts,
   security.

---

## Carried forward — operational hazards

- **The `devx` reviewer gate needs a human.** An agent session must not approve
  it; doing so would nullify the control added after the 2026-09-20 incident.
  Ask and wait. This session needed four separate approvals.
- **Amplify `db-redesign` auto-builds with no gate** on every push, regardless
  of path filter. The `devx` gate covers the backend job only.
- **`src/frontend/.env.e2e` is blocked from agent writes** by a permission deny
  rule on `.env.*`. Pass `E2E_TEST_EMAIL` / `E2E_TEST_PASSWORD` inline instead.
- **The trial budget is exhausted** — `application_count` is at 3 of 3. Resetting
  needs a fresh, time-boxed operator grant (HANDOFF-11 §0.1).
- **`preflight` should now pass 9/9**, not 8/9. If `deployed commit is known`
  still FAILs, the egg-info fix regressed — check `git ls-files` for any
  `*.egg-info/` reappearing.

## Ground rules

- `scripts/ops/blast-radius.sh <event> <branch>` before any merge, deploy,
  deletion or credential change; paste Action/Triggers/Undo **before** acting.
- Stop and ask on a `CREATE+EXECUTE` you did not expect, `NO ENVIRONMENT GATE`,
  or an environment with `0 rules`.
- Verify the environment; never infer it from a plan document — **including
  this one.**
- One concern per commit. Every fix gets a regression test that fails before and
  passes after — and run it the way CI runs it.
- **Diagnose by observation, not by reading.** Two confident, wrong `-dirty`
  fixes and two deploys were spent before making CI print what it actually saw.
  When a mechanism is not directly observable, the first move is to make it
  observable, not to infer it.
- A repo grep is not an inventory, a green deploy is not a working system, a
  green step is not a correct artifact, and a check that fails during setup has
  not scanned your change.
