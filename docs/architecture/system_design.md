# CareerVP System Design & Patterns

## 1. Repository Pattern (DAL)
To ensure high precision and testability, we decouple business logic from AWS SDKs.
- **Logic Layer:** Contains business rules, LLM orchestration, and fact verification.
- **DAL (Data Access Layer):** Purely handles DynamoDB/S3 operations.
- **Benefit:** Allows us to swap DynamoDB for a Mock during unit tests.

## 2. Result Object Pattern
Every logic function must return a `Result` object to prevent unhandled exceptions and "None" type errors.
- Schema: `{ "success": bool, "data": T, "error": Optional[str], "code": str }`

## 3. Fact Verification System (FVS)
Logic must categorize extracted data:
1. **Immutable:** Work history dates, degrees, company names.
2. **Verifiable:** Skills and accomplishments found in source documents.
3. **Flexible:** Professional summaries and "strategic framing" for specific job roles.
*Rule: AI is never allowed to change Immutable facts during tailoring.*

## 4. Hybrid AI Strategy
- **Task Type: STRATEGIC** -> Route to Claude Sonnet 4.5.
- **Task Type: TEMPLATE** -> Route to Claude Haiku 4.5.
