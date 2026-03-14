# CareerVP Pre-Coding Documentation Guide

**For:** Non-technical partner / Product owner
**Purpose:** Explains what each pre-coding document is, why it exists, what it should contain, and what questions you need to answer to generate it.
**Last Updated:** 2026-03-08

---

## What Is "Pre-Coding Documentation"?

Before writing a single line of code for a new feature, we create a set of documents that describe exactly what needs to be built, how it should behave, and how the pieces connect. Think of it like architectural blueprints before construction — the contractor (the AI or developer) needs to know the floor plan before laying bricks.

These documents fall into five categories. Each one serves a different audience and answers different questions.

---

## Document 1: Feature Specification ("Spec")

### What it is
A detailed description of what one feature does from the user's perspective AND the system's perspective. It is the single source of truth for a feature.

### Why it exists
Without a spec, different people (or AI tools) will build different versions of the "same" feature. A spec eliminates ambiguity.

### What to include

**Section 1 — Overview**
- What is this feature? (1–2 sentences)
- What problem does it solve for the user?
- What type of user uses it? (e.g., "a job seeker in their trial period")

**Section 2 — User Stories**
Write in this format:
> As a [user type], I want to [do something], so that [I get this benefit].

Example:
> As a user whose free trial has ended, I want to upgrade to a paid plan, so that I can continue generating application packages.

**Section 3 — Acceptance Criteria**
A checklist of exactly what "done" means. Use this format:
> ✅ Given [situation], when [action], then [result].

Example:
> ✅ Given a user clicks "Upgrade," when the checkout flow completes, then their subscription status changes to "active" within 30 seconds.

**Section 4 — What it is NOT (out of scope)**
List things that might seem related but are explicitly not included in this feature. This prevents scope creep.

**Section 5 — Edge Cases**
What should happen in unusual situations?
- What if the payment fails?
- What if the user closes the browser mid-checkout?
- What if they already have an active subscription?

### Questions to answer before generating this doc
1. What is the exact name of this feature?
2. Who are the 1–3 types of users who will use it?
3. What is the happy path (the ideal journey a user takes through this feature)?
4. What are 3–5 things that could go wrong, and what should happen in each case?
5. What explicitly should NOT be part of this feature right now?

### Example prompts to give an AI
> "Generate a feature spec for Stripe subscription checkout. The user clicks an upgrade button, gets redirected to Stripe's hosted checkout page, and returns to the app with an active subscription. Include user stories, acceptance criteria, and edge cases for payment failure and browser closure mid-checkout."

---

## Document 2: API Endpoint Specification

### What it is
A technical document describing every API endpoint (URL) that the backend needs to expose for a feature. It documents what data goes in, what data comes out, and what the backend does in between.

### Why it exists
The frontend (what users see) and backend (server logic) are built by different people or at different times. This document is the contract between them — both sides agree on the interface before either builds anything.

### What to include

**For each endpoint:**

| Field | Description | Example |
|---|---|---|
| **Method** | HTTP verb | POST, GET, DELETE |
| **Path** | URL path | `/billing/checkout` |
| **Auth required?** | Does the user need to be logged in? | Yes — requires valid JWT token |
| **Request body** | What data does the caller send? | `{ plan: "monthly", success_url: "...", cancel_url: "..." }` |
| **Response (success)** | What data comes back when it works? | `{ checkout_url: "https://stripe.com/..." }` |
| **Response (errors)** | What error codes and messages? | 400: invalid plan, 401: not logged in, 500: Stripe error |
| **What the backend does** | Step-by-step description | 1. Validate token. 2. Look up Stripe customer. 3. Create checkout session. 4. Return URL. |

### Questions to answer before generating this doc
1. What actions does the user need to perform? (Each action usually maps to one API call)
2. For each action, what information does the frontend need to send?
3. What does the frontend need back to show the user?
4. What can go wrong at each step, and what error should be returned?
5. Which endpoints require the user to be logged in?
6. Are any endpoints admin-only?

### Example prompts to give an AI
> "Write a full API specification for the billing feature. Include these endpoints: POST /billing/checkout (creates a Stripe checkout session), POST /billing/portal (opens Stripe customer portal), GET /users/me/subscription (returns current subscription status), and POST /billing/webhook (handles Stripe events). For each: document the request body, success response, error responses, and step-by-step backend logic."

---

## Document 3: Database Schema

### What it is
A description of how data is stored and organized in the database. For CareerVP, this means defining DynamoDB tables — their structure, access patterns, and relationships to other data.

### Why it exists
The database design determines how fast the app runs, how easy it is to query data, and how data is organized long-term. Changing a database schema after data exists is painful and risky.

### What to include

**For each table:**

| Field | Description |
|---|---|
| **Table name** | e.g., `careervp-subscriptions` |
| **Purpose** | What does this table store? |
| **Primary key** | How is each row uniquely identified? (partition key + optional sort key) |
| **Key attributes** | Every field stored, with its type and description |
| **Access patterns** | What queries does the app need to run against this table? |
| **Global Secondary Indexes (GSI)** | Extra indexes for queries that don't use the primary key |
| **TTL (Time-to-Live)** | Does data expire automatically? When? |

**Access pattern examples (write these in plain English first):**
- "Look up a subscription by user ID"
- "Find all users whose subscription is past_due"
- "Get the most recent subscription for a given Stripe customer ID"

### Questions to answer before generating this doc
1. What are the main "things" this feature needs to remember? (These become tables or attributes)
2. How will the app look up this data? (By user ID? By date? By status?)
3. Does any data expire? (e.g., session tokens, temporary codes)
4. What is the relationship between this data and existing tables?
5. Will you need to list/filter data? (e.g., "show all past_due subscriptions" — needs a GSI)

### Example prompts to give an AI
> "Design a DynamoDB table schema for CareerVP subscriptions. Users can have one subscription at a time. The app needs to: look up a user's subscription by user_id, find a subscription by Stripe customer_id, and query all users with status=past_due for a billing alert job. Include the table structure, primary key, all attributes with types, and recommended GSIs."

---

## Document 4: Backend Architecture / Flow Diagram

### What it is
A written description (or diagram) of how a request travels through the entire system — from the user clicking a button, through the API, through the business logic, to the database, and back.

### Why it exists
Code is complex. When many pieces connect together, it's easy to lose track of what talks to what. This document makes the "big picture" explicit so every developer (or AI tool) builds each piece consistently.

### What to include

**The standard CareerVP flow looks like this:**
```
User Action → Frontend → API Gateway → Lambda Function → DAL (Data Access Layer) → DynamoDB
                                                       ↘ External Service (e.g., Stripe, SQS)
```

For each feature, describe:

1. **Trigger:** What user action starts the flow?
2. **Frontend step:** What does the browser send? (which URL, which data)
3. **API Gateway:** Which route handles it?
4. **Lambda function:** Which function runs? What does it do step by step?
5. **DAL (Data Access Layer):** What database reads/writes happen?
6. **External calls:** Does it call Stripe, send an email, push to a queue (SQS)?
7. **Response:** What does the Lambda return to the frontend?
8. **Frontend reaction:** What does the UI do with the response?

### Questions to answer before generating this doc
1. What is the user action that triggers this flow?
2. What external services does this feature touch? (Stripe, SQS, S3, email service?)
3. Are there any background/async steps? (e.g., a webhook that fires later)
4. What error conditions should stop the flow and return an error to the user?
5. What gets written to the database at each step?

### Example prompts to give an AI
> "Document the complete backend flow for the Stripe subscription checkout feature. Start from the user clicking 'Upgrade', trace through: POST /billing/checkout → API Gateway → checkout_handler Lambda → Stripe API call → DynamoDB write → return checkout_url to frontend. Then document the separate webhook flow: Stripe sends checkout.session.completed → POST /billing/webhook → webhook_handler Lambda → update subscriptions table → update user's application quota."

---

## Document 5: Admin Portal Specification

### What it is
A spec for the internal management interface that you (the product owner / admin) use to view and manage users, subscriptions, and system health. It is NOT something regular users see.

### Why it exists
After launch, you need visibility into what's happening: who signed up, who upgraded, who is having problems. The admin portal is your control panel.

### What to include

**Section 1 — Who uses this?**
Describe the admin user. What do they need to see every day?

**Section 2 — Pages / Views**
For each page in the admin portal:
- What is shown on this page?
- What can the admin do here? (read-only vs. take actions)
- What data does it pull from?

**Section 3 — Admin Actions**
List every action an admin can take (e.g., extend a user's trial, cancel a subscription, view a user's application history).

**Section 4 — Access Control**
Who can access the admin portal? How is this enforced?

**Section 5 — Metrics / KPIs**
What numbers does the admin need to see on the dashboard?

### Questions to answer before generating this doc
1. What questions do you need answered every morning when you log in?
2. What actions do you need to take on user accounts? (e.g., extend trials, issue refunds?)
3. Who else (if anyone) needs admin access?
4. What would indicate a problem that needs immediate attention?
5. Do you need to export any data? (e.g., user list to CSV)

### Example prompts to give an AI
> "Write a full admin portal specification for CareerVP. The admin needs to: view all users with their subscription status, trial days remaining, and applications used; search users by email; extend a user's trial by N days; view subscription revenue metrics (MRR, conversion rate); and see a list of users with payment failures. The portal is accessed only by users in the Cognito 'Admins' group."

---

## Summary: Which Document to Generate First?

Use this order for any new feature:

| Order | Document | Generates | Used By |
|---|---|---|---|
| 1 | Feature Spec | The "what" | Product + Dev + AI |
| 2 | API Endpoint Spec | The request/response contract | Backend dev + Frontend dev |
| 3 | Database Schema | The data model | Backend dev + DBA |
| 4 | Backend Architecture Flow | The step-by-step logic | Backend dev + AI code generation |
| 5 | Admin Portal Spec (if needed) | The management interface | Product owner + Frontend dev |

**Rule of thumb:** If a document downstream contradicts a document upstream, fix the upstream one first.

---

## Template: Quick Prompt for Any Feature

Copy and fill in the blanks to generate any of the above documents:

```
I am building [feature name] for CareerVP, a job application AI tool.

The user wants to [do X]. The system should [do Y]. The result should be [Z].

The tech stack is:
- Frontend: Next.js 15 (App Router), TanStack Query, Zustand, shadcn/ui
- Backend: Python Lambda functions, DynamoDB, API Gateway
- Auth: AWS Cognito (JWT tokens in Authorization header)
- External: [list any: Stripe, SQS, S3, etc.]

Please generate [Document Type] for this feature. Include:
[list what you need based on the relevant section above]
```
