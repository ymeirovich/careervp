# Wave 1 — Status Ledger

**Read this file FIRST before starting any Wave-1 prompt.** `wave-1-prompts.md` describes what
*should* happen; this file describes what *actually* happened, and is what every prompt checks
before starting its own work (see `RUNBOOK-RULES.md`, rules 2–3). Update your own row when you
finish a step or stop on a problem — do not leave this file stale for the next session to trip
over.

Rows are listed in dependency order. Before starting a step, read the row above it (or the rows
it depends on per `wave-1-prompts.md` §2) — if any of them show an open problem, resolve that
first.

| Step | Clause(s) | Status (plain English) | Open problem for the next step | Commit | Date |
|---|---|---|---|---|---|
| 1.0 | P-23 | Done: P-23 canary rollback code/tests are present in git, and the owner-tag replacement blocker was resolved by stable per-resource owner tags. | none | `3bb5446` | 2026-07-18 |
| 1.3c-gate | P-11 (enable WAF in all envs) | Done: removed the production-only WAF gate, so dev/non-production stacks now synthesize a WAF WebACL without changing WAF rule content. RED test failed first against the old gate, then passed after the gate removal. | None for the next spine step. Lane P2 Prompt 1.3c depends on this and can now land rate-rule content in `waf_construct.py`. | pending commit: `fix(infra): enable API WAF in all environments for P-11` | 2026-07-18 |
| 1.3c | P-07, P-11 (rate-rule content) | not started | — | — | — |
| 1.3a | P-08 | Done: CV and VPR-results ("generated") bucket S3 CORS wildcard origins replaced with explicit per-env origins (localhost only for dev). RED test written first, confirmed failing against the old wildcard code, then GREEN after the fix. `cdk diff` shows both buckets as in-place property updates only (`[~]`), zero replacement. | None for 1.3b itself, but see note: the prompt's cited evidence locations (`api_db_construct.py:184,561`, `s3_stack.py:40,63`, `frontend_stack.py:48`) were stale — `s3_stack.py` does not exist and `frontend_stack.py:48` already had an explicit (non-wildcard) origin, so it was correctly left untouched. The two real S3-CORS-with-wildcard sites were `api_db_construct.py:253` (CV bucket) and `api_db_construct.py:653-657` (VPR results bucket, which had a `https://*.amplifyapp.com` wildcard subdomain, not `"*"`). Scope/intent still matches the P-08 clause and spec; flagging the stale citations for whoever writes the next wave-prompt file. | pending (see commit message in session output) | 2026-07-18 |
| 1.3b | P-10 | not started | — | — | — |
| 1.2 | P-06 | not started | — | — | — |
| 1.3d | P-26 Job-1 | amendment landed; engineering not started | The v2.5.0 amendment recording Job-1's Wave-1 tracking is committed (`project-scope-lock.yaml`/`.md` both at v2.5.0). The precondition check in Prompt 1.3d is satisfied — normal step preconditions (1.3c-gate landed, spine free) still apply before starting. | `0a0cb81` | 2026-07-18 |
| 1.4 | P-09 | not started | — | — | — |
| 1.1 | P-04, P-05 | not started | — | — | — |
| 1.5 | P-22 | not started | — | — | — |
| GATE | — | not started | — | — | — |

## Standing notes carried into every step (do not lose these)

- The two IMMUTABLE laws (never move the live RestApi or the Cognito user pool) apply to every
  row above that touches `infra/`. See `wave-1-prompts.md` for the exact logical ids.
- `api_construct.py` is edited by most of these steps — never run two steps that touch it at the
  same time. See `wave-1-prompts.md` §2 for the current serialization order.
