# CareerVP Context Manifest & Decision Log

## Core Architecture
- [cite_start]**Infrastructure:** AWS Serverless (Lambda, DynamoDB, S3, API Gateway)[cite: 250].
- **Pattern:** Layered Monorepo (Handler -> Logic -> DAL).
- [cite_start]**Cost Target:** 91%+ profit margin via Hybrid AI Strategy[cite: 617].

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
