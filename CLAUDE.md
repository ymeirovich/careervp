# CareerVP Context Manifest & Decision Log

## Core Architecture
- [cite_start]**Infrastructure:** AWS Serverless (Lambda, DynamoDB, S3, API Gateway)[cite: 250].
- **Pattern:** Layered Monorepo (Handler -> Logic -> DAL).
- [cite_start]**Cost Target:** 91%+ profit margin via Hybrid AI Strategy[cite: 617].
- Environment: dev (AWS region: us-east-1)

## AI Model Strategy (Decision 1.2)
- [cite_start]**Strategic (Sonnet 4.5):** VPR Generation, Gap Analysis[cite: 259, 266].
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
- Infra: cd infra && uv sync && cdk synth.
- Naming Check: python src/backend/scripts/validate_naming.py --path infra --strict.

## Key Path Mappings
- **Task Source:** `docs/tasks/`
- **Infra Source:** `infra/careervp/` (CDK Stacks)
- **Logic Source:** `src/backend/careervp/logic/`
- **Models Source:** `src/backend/careervp/models/`
- **Verification Scripts:** `src/backend/scripts/`

## Git Workflow Rules
- **Don't switch branches with uncommitted changes** - use `git stash` first to avoid accidentally deleting files
- **Merge via gh CLI directly from the feature branch** - avoids needing to checkout main
- **Only clean up local branch after successful merge**
