# CareerVP Context Manifest & Decision Log

## Core Architecture
- [cite_start]**Infrastructure:** AWS Serverless (Lambda, DynamoDB, S3, API Gateway)[cite: 250].
- **Pattern:** Layered Monorepo (Handler -> Logic -> DAL).
- [cite_start]**Cost Target:** 91%+ profit margin via Hybrid AI Strategy[cite: 617].
- Environment: dev (AWS region: us-east-1)

## AI Model Strategy (Decision 1.2)
- [cite_start]**Strategic (Sonnet 4.6):** VPR Generation, Gap Analysis[cite: 259, 266].
- [cite_start]**Template (Haiku 4.5):** CV Tailoring, Cover Letter, Interview Prep[cite: 260, 267].

## Anti-AI Detection Rules (Decision 1.6)
[cite_start]Must adhere to the 8-pattern avoidance framework in all text generation[cite: 308]:
1. [cite_start]Avoid excessive AI phrases (e.g., "In the ever-evolving landscape")[cite: 308].
2. [cite_start]Vary sentence structure[cite: 309].
3. [cite_start]Include minor natural transitions[cite: 309].
4. [cite_start]Avoid perfect parallel structure[cite: 309].

## Project Structure
- `/infra`: CDK Python stacks.
- `/src/backend/careervp/handlers`: Entry points (Powertools integration).
- [cite_start]`/src/backend/careervp/logic`: Business rules & FVS[cite: 331].
- `/src/backend/careervp/dal`: DynamoDB/S3 Repositories.

## Pricing (Decision 1.10)

- **Monthly:** $20/month unlimited applications.
- **Annual:** $192/year ($16/mo effective, 20% discount).
- **Trial:** 14 days, 3 free applications, credit card required.

## V1 Feature Scope (MVP)

**INCLUDED:** Auth, VPR, CV Tailoring, Cover Letter, Gap Analysis (10 Q max), Interview Prep (10 Q max), Company Research, Knowledge Base, English + Hebrew.

**DEFERRED TO V2:** Job Tracking, French, API access, Team collaboration, OCR.

**Active Commands:**
- Backend: cd src/backend && uv run ruff format . && uv run ruff check --fix . && uv run mypy careervp --strict.
- Testing: uv run pytest tests/unit/ -v --tb=short.
- Frontend: cd src/frontend && npm run typecheck && npm run test:unit && npm run test:integration.
- Frontend (conditional): cd src/frontend && npm run test:e2e && npm run test:regression && npx vitest run --config vitest.config.ts.
- Git Commit Helper: scripts/git/safe_commit.sh "<commit-message>".
- Git Merge Helper: scripts/git/safe_merge_to_main.sh <feature-branch>.
- Infra: cd infra && uv sync && cdk synth.
- Naming Check: python src/backend/scripts/validate_naming.py --path infra --strict.

## Key Path Mappings
- **Task Source:** `docs/tasks/`
- **Infra Source:** `infra/careervp/` (CDK Stacks)
- **Logic Source:** `src/backend/careervp/logic/`
- **Models Source:** `src/backend/careervp/models/`
- **Verification Scripts:** `src/backend/scripts/`

## Agent Model & Effort Policy (as of Aug 2026)

Applies to both OpenAI Codex and Claude Code sessions used on this repo. Model/effort tiers shift over time — treat this as the current calculation, not a permanent ranking; re-verify against provider docs if it's been a while.

**Codex (GPT-5.6 family — Sol/Terra/Luna tiers):**
- Routine implementation, tests, small refactors: **Terra**, medium reasoning.
- Large feature, unfamiliar codebase, debugging: **Sol**, high reasoning.
- Architecture, migrations, security-sensitive review, hard diagnosis: **Sol**, xhigh reasoning.
- Simple searches, repetitive edits, narrow reviews: **Luna** (or GPT-5.4 mini), low/medium reasoning.
- Maximum-quality final judgment call: **Sol**, max reasoning (or Pro mode).

**Claude Code:**
- Routine coding: **Sonnet 5**, high effort.
- Complex multi-service work: **Opus 5**, high or xhigh effort.
- Very difficult architecture or long-running autonomous work: **Opus 5**, xhigh/max effort.
- Hardest long-running research/coding where quality gain justifies cost: **Fable 5**, high effort.
- Use `opusplan` when a strong plan is needed but implementation should stay at normal cost (Opus plans, Sonnet executes).

**General rule:** default to the cheaper/faster tier (Sonnet 5 / GPT-5.6 Terra); escalate only when the task is genuinely architectural, ambiguous, long-running, or expensive to get wrong. Model switches must be confirmed via `/status` (Claude Code) or the equivalent Codex indicator — do not assume a stated policy alone changed the active model.

## MANDATORY — Blast radius before irreversible or outward-facing actions

**Before** merging a PR, pushing to a branch that auto-builds, deploying,
executing a change set, deleting or deactivating an AWS resource, rotating a
credential, or rewriting git history, you MUST run:

```bash
scripts/ops/blast-radius.sh <push|merge|pull_request> <branch>
```

and paste a three-line statement into the reply **before** taking the action:

```
Action:   <exactly what will run>
Triggers: <every workflow/deploy/stack/Amplify build it sets off>
Undo:     <the specific reversal, or "none — irreversible">
```

If the tool reports any job with `CREATE+EXECUTE`, `NO ENVIRONMENT GATE`, or an
environment with `0 rules`, **stop and ask** before proceeding. An
`environment:` label on a job is not a gate — GitHub auto-creates missing
environments unprotected, and `dev` currently has zero protection rules.

**Never classify an action as routine on your own judgment.** This rule exists
because on 2026-09-20 a one-file workflow PR was merged into `main` as
"paperwork"; the merge triggered an ungated `make deploy` that deleted ~70
resources in `CareerVpCrudDev`, including the `CrudFeatures` nested stack, the
WAFv2 WebACL and the API Gateway custom domain. The fact that `main`
auto-deploys had been documented hours earlier in this same repo and was not
connected to the action. No data was lost; that was luck, not design.

Corollary: verify the environment before reasoning about it. Which branch is
deployed, which stacks exist, and what fires on an event are all one command
away — never infer them from a plan document, a handoff, or a prior session's
prose.

## Deployment topology — the single source of truth

Measured 2026-09-21. Re-verify rather than trusting this table if it looks stale.

| | Value |
|---|---|
| Working branch | `tools/proof-harness` (a strict superset of `db-redesign`, which is a strict superset of `ui-upgrade`) |
| Backend target | `CareerVpCrudDevx`, deployed by `db-redesign-checks.yml` on push to `db-redesign` |
| Backend gate | `environment: devx` — 1 required reviewer (a real gate) |
| Backend deploy cmd | `make deploy-devx`, which passes `p26_rehome_features=true` (nested stacks) |
| Frontend | Amplify branch `db-redesign` → `https://db-redesign.d3j2wnm8g5clnw.amplifyapp.com` |
| `main` | **Not a deploy target for this project.** Vestigial; 12 commits of stale history. |

`CareerVpCrudDev` and `CareerVpCrudStaging` are **not** the working
environments. `production` and `gap-remediation` environments do not exist.

## Git Workflow Rules
- **Don't switch branches with uncommitted changes** - use `git stash` first to avoid accidentally deleting files
- **Merge via gh CLI directly from the feature branch** - avoids needing to checkout main
- **Only clean up local branch after successful merge**
- **Before every commit, run mandatory backend/frontend checks based on changed paths**
- **Use `scripts/git/safe_commit.sh` and `scripts/git/safe_merge_to_main.sh` for resilient commit/merge flows**
- **Do not use `gh pr merge --delete-branch` in this repo**
