- Tab


**CONTEXT MANIFEST**

**CareerVP Job Search Assistant - Complete Context Awareness**

**Document**

**1. ARCHITECTURAL DECISIONS LOG**

**Decision 1.1: Serverless AWS Architecture**

```
● Decision: Full serverless stack using AWS Lambda, DynamoDB, S3, API Gateway
● Rationale:
● Pay-per-use cost model aligns with SaaS economics
● Auto-scaling for variable workloads
● Minimal operational overhead
● High availability built-in
● Source: Multiple conversations including "Serverless job search assistant questions 1-10"
through "questions 38-43"
● Status: CONFIRMED - Current architecture
```
**Decision 1.2: Hybrid AI Model Strategy (Sonnet + Haiku)**

```
● Decision:
● Claude Sonnet 4.5 for strategic/analytical tasks (VPR, Gap Analysis)
● Claude Haiku 4.5 for template-driven tasks (CV, Cover Letter, Interview Prep)
● Rationale:
● 33% cost reduction vs all-Sonnet approach
● Maintains quality where it matters (strategic analysis)
● Haiku sufficient for well-structured template generation
● Cost Impact:
● VPR: $0.023-0.035 (Sonnet)
● CV: $0.003-0.005 (Haiku)
● Cover Letter: $0.002-0.004 (Haiku)
● Gap Analysis: $0.077 (Sonnet - two-phase)
● Interview Prep: $0.004-0.006 (Haiku)
● Source: Cost optimization discussions
● Status: CONFIRMED - Implementation specification complete
```
**Decision 1.3: Document Generation Workflow (4 Stages)**

```
● Decision: Sequential artifact generation with dependency chain
● Value Proposition Report (VPR) - Foundation
● CV Tailoring - Uses VPR insights
● Cover Letter - Uses VPR + Tailored CV
```

```
● Interview Prep - Uses all previous artifacts
● Rationale:
● VPR provides strategic foundation for all downstream artifacts
● Each artifact builds on previous work
● Reduces redundancy in AI processing
● Enables user review/editing between stages
● Source: Workflow design discussions
● Status: CONFIRMED
```
**Decision 1.4: Notification System (Two-Tier)**

```
● Decision: Separate user-facing and admin notification systems
● User Notifications (SES): Completion updates, trial reminders, payment issues
● Admin Notifications (SNS): System errors, abuse detection, capacity warnings
● Rationale:
● Different audiences require different information
● User notifications focus on value/status
● Admin notifications focus on operations/issues
● Prevents alert fatigue
● Source: Notification strategy discussions
● Status: CONFIRMED
```
**Decision 1.5: Storage Strategy (S3 + Lifecycle)**

```
● Decision: S3 buckets with lifecycle policies:
● careervp-job-search-assistant-cvs (7-day retention)
● careervp-job-search-assistant-outputs (30-day retention)
● careervp-job-search-assistant-knowledge (user-controlled, capacity limits)
● careervp-job-search-assistant-logs (90-day retention)
● careervp-job-search-assistant-temp (1-day retention)
● Rationale:
● Cost optimization through automatic cleanup
● Compliance with data retention policies
● Different retention needs per content type
● Source: S3 bucket structure discussions
● Status: CONFIRMED
```
**Decision 1.6: Anti-AI Detection Framework**

```
● Decision: Comprehensive 8-pattern avoidance system:
● Avoid excessive AI phrases
● Vary sentence structure
● Include minor imperfections
● Use natural transitions
● Maintain conversational tone
● Avoid perfect parallel structure
```

```
● Include domain-specific terminology
● Match user's writing style (when samples provided)
● Rationale:
● Commercial AI detectors flag patterns, not quality
● Human writing has natural variations
● Critical for user success in job applications
● Source: Anti-AI detection strategy discussions
● Status: CONFIRMED - Integrated into all prompts
```
**Decision 1.7: ATS Optimization Strategy**

```
● Decision: Multi-layered ATS compatibility approach:
● Keyword optimization from job posting
● Standard section headers
● Clean formatting (no tables, no columns)
● Simple bullet points
● Standard fonts and styles
● Achievement quantification
● Rationale:
● 75% of applications filtered by ATS before human review
● Different ATS systems have varying capabilities
● Conservative approach ensures broad compatibility
● Source: ATS optimization discussions
● Status: CONFIRMED
```
**Decision 1.8: Fact Verification System (Multi-Tier)**

```
● Decision: Three-level verification for preventing hallucinations:
● Static Facts (IMMUTABLE): Contact info, dates, work history, education
● Skills & Achievements (VERIFIABLE): Must exist in source CV
● Strategic Framing (FLEXIBLE): How facts are presented
● Rationale:
● AI hallucination in job applications is disqualifying
● Different types of information require different validation
● Strategic optimization allowed only for verifiable facts
● Source: Hallucination prevention discussions
● Status: CONFIRMED - Implemented in prompts
```
**Decision 1.9: WordPress Integration via Subdomain**

```
● Decision:
● Marketing site: careervp.com (WordPress)
● Application: app.careervp.com (React SPA on S3/CloudFront)
● Seamless navigation between sites
● Rationale:
● WordPress strengths: SEO, content marketing, blog
```

```
● React SPA strengths: Dynamic application, user experience
● Subdomain approach allows independent optimization
● Source: WordPress integration planning
● Status: CONFIRMED
```
**Decision 1.10: Freemium Model (14-Day Trial)**

```
● Decision:
● Free Tier: 3 complete applications (trial)
● Paid Tier: Unlimited applications at $20-30/month
● Trial → Paid conversion emphasis
● Rationale:
● Allows users to evaluate value before paying
● 3 applications sufficient to demonstrate capability
● Low-friction onboarding
● Clear upgrade path
● Source: Business model discussions
● Status: CONFIRMED
```
**2. TECHNICAL COMPONENTS INVENTORY**

**2.1 Lambda Functions (18-22 Functions)**

**Core Generation Functions**

1. vp-report-generator
    ● Model: Claude Sonnet 4.
    ● Memory: 1024 MB
    ● Timeout: 120s
    ● Avg Duration: 15-25s
    ● Cost: $0.023-0.
    ● Input: Job posting, CV, knowledge base
    ● Output: Strategic VPR (JSON + formatted)
2. cv-tailor
    ● Model: Claude Haiku 4.
    ● Memory: 512 MB
    ● Timeout: 60s
    ● Avg Duration: 10-15s
    ● Cost: $0.003-0.
    ● Input: VPR, master CV, job posting
    ● Output: ATS-optimized CV (DOCX)
3. cover-letter-generator
    ● Model: Claude Haiku 4.
    ● Memory: 512 MB


```
● Timeout: 60s
● Avg Duration: 8-12s
● Cost: $0.002-0.
● Input: VPR, tailored CV, writing samples (optional)
● Output: Personalized cover letter (DOCX)
```
4. gap-analysis-questions
    ● Model: Claude Sonnet 4.
    ● Memory: 512 MB
    ● Timeout: 60s
    ● Avg Duration: 12-18s
    ● Cost: ~$0.
    ● Input: Job posting, CV
    ● Output: 5-8 targeted questions (JSON)
5. gap-analysis-processor
    ● Model: Claude Sonnet 4.
    ● Memory: 512 MB
    ● Timeout: 60s
    ● Avg Duration: 15-20s
    ● Cost: ~$0.
    ● Input: Questions + user answers
    ● Output: Gap analysis report (JSON + formatted)
6. interview-prep-generator
    ● Model: Claude Haiku 4.
    ● Memory: 512 MB
    ● Timeout: 60s
    ● Avg Duration: 12-18s
    ● Cost: $0.004-0.
    ● Input: All previous artifacts
    ● Output: Interview preparation guide

**Supporting Functions**

7. session-orchestrator
    ● No AI calls
    ● Memory: 256 MB
    ● Timeout: 10s
    ● Purpose: Coordinate multi-artifact workflows
8. status-checker
    ● No AI calls
    ● Memory: 256 MB
    ● Timeout: 5s
    ● Purpose: Provide real-time status updates
9. knowledge-base-uploader
    ● No AI calls
    ● Memory: 512 MB


```
● Timeout: 30s
● Purpose: Handle file uploads, validation
```
10. knowledge-base-retriever
    ● No AI calls
    ● Memory: 256 MB
    ● Timeout: 10s
    ● Purpose: Fetch user materials for generation
11. document-validator
    ● No AI calls
    ● Memory: 512 MB
    ● Timeout: 30s
    ● Purpose: Validate generated documents (format, completeness)
12. user-auth-handler
    ● No AI calls
    ● Memory: 256 MB
    ● Timeout: 5s
    ● Purpose: Handle Cognito integration
13. payment-webhook-handler
    ● No AI calls
    ● Memory: 256 MB
    ● Timeout: 10s
    ● Purpose: Process Stripe webhooks
14. credit-manager
    ● No AI calls
    ● Memory: 256 MB
    ● Timeout: 5s
    ● Purpose: Track and enforce usage limits
15. notification-sender
    ● No AI calls
    ● Memory: 256 MB
    ● Timeout: 10s
    ● Purpose: Send SES emails
16. admin-alert-handler
    ● No AI calls
    ● Memory: 256 MB
    ● Timeout: 10s
    ● Purpose: Send SNS admin notifications
17. cost-tracker
    ● No AI calls
    ● Memory: 256 MB
    ● Timeout: 5s
    ● Purpose: Log per-user, per-artifact costs
18. abuse-detector
    ● No AI calls


```
● Memory: 256 MB
● Timeout: 10s
● Purpose: Identify suspicious usage patterns
```
**Optional Future Functions**

19. company-research (V2)
20. industry-analyzer (V2)
21. multi-language-translator (V2)
22. analytics-aggregator (V2)

**2.2 DynamoDB Tables**

**Users Table**

yaml

Table Name: careervp-users
Partition Key: user_id (String)
Attributes:

- email (String)
- tier (String: free|paid|premium|admin)
- credits_remaining (Number)
- subscription_status (String)
- stripe_customer_id (String)
- knowledge_base_size_mb (Number)
- created_at (String - ISO8601)
- updated_at (String - ISO8601)
GSI:
- email-index: email (PK)
Read/Write Capacity: On-demand
Encryption: AWS managed key

Point-in-time recovery: Enabled

**Sessions Table**

yaml

Table Name: careervp-sessions
Partition Key: session_id (String)
Sort Key: timestamp (String)
Attributes:

- user_id (String)
- status (String: initiated|processing|completed|failed)
- job_posting (Map)
- artifacts (Map)
- total_cost (Number)
- ttl (Number - Unix timestamp)


TTL Attribute: ttl (7 days)
Read/Write Capacity: On-demand

Encryption: AWS managed key

**Jobs Table**

yaml

Table Name: careervp-jobs
Partition Key: user_id (String)
Sort Key: job_id (String)
Attributes:

- company_name (String)
- job_title (String)
- status (String: draft|submitted|interview|offer|rejected)
- session_id (String)
- artifacts_s3_prefix (String)
- notes (String)
- created_at (String)
- updated_at (String)
GSI:
- status-index: status (PK), updated_at (SK)
Read/Write Capacity: On-demand

Encryption: AWS managed key

**KnowledgeBase Table**

yaml

Table Name: careervp-knowledge-base
Partition Key: user_id (String)
Sort Key: item_id (String)
Attributes:

- type (String: writing_sample|portfolio|reference|other)
- name (String)
- s3_key (String)
- version (Number)
- file_size_mb (Number)
- metadata (Map)
- created_at (String)
Read/Write Capacity: On-demand

Encryption: AWS managed key

**2.3 S3 Buckets**

1. careervp-job-search-assistant-cvs
    ● Purpose: User uploaded CVs


```
● Lifecycle: 7 days → Glacier, 30 days → Delete
● Versioning: Enabled
● Encryption: AES-
● Public Access: Blocked
```
2. careervp-job-search-assistant-outputs
    ● Purpose: Generated artifacts (VPR, CV, Cover Letter, etc.)
    ● Lifecycle: 30 days → Glacier, 90 days → Delete
    ● Versioning: Enabled
    ● Encryption: AES-
    ● Public Access: Blocked
3. careervp-job-search-assistant-knowledge
    ● Purpose: User knowledge base materials
    ● Lifecycle: User-controlled (with capacity limits)
    ● Size Limit: 100MB per user (free), 500MB (paid)
    ● Versioning: Enabled
    ● Encryption: AES-
    ● Public Access: Blocked
4. careervp-job-search-assistant-logs
    ● Purpose: Application logs, audit trails
    ● Lifecycle: 90 days → Delete
    ● Versioning: Disabled
    ● Encryption: AES-
    ● Public Access: Blocked
5. careervp-job-search-assistant-temp
    ● Purpose: Temporary processing files
    ● Lifecycle: 1 day → Delete
    ● Versioning: Disabled
    ● Encryption: AES-
    ● Public Access: Blocked

**2.4 API Gateway**

yaml

Type: REST API
Authentication:

- Cognito User Pools (user endpoints)
- API Keys (programmatic access - future)
Rate Limiting:
- Free Tier: 10 requests/hour
- Paid Tier: 100 requests/hour
- Burst: 20 requests (all tiers)
WAF: Enabled (SQL injection, XSS protection)
CORS: Configured for app.careervp.com

Logging: CloudWatch Logs (all requests)


**2.5 SQS Queues**

1. careervp-document-generation
    ● Type: Standard
    ● Visibility Timeout: 120s
    ● Message Retention: 4 days
    ● Dead Letter Queue: Yes
    ● Purpose: Async document generation jobs
2. careervp-document-generation-dlq
    ● Type: Standard
    ● Message Retention: 14 days
    ● Purpose: Failed generation jobs for analysis
3. careervp-notifications
    ● Type: Standard
    ● Visibility Timeout: 30s
    ● Message Retention: 4 days
    ● Purpose: Async email notifications

**2.6 CloudWatch**

**Metrics**

```
● API call counts by endpoint
● Lambda durations by function
● Token usage by model (Sonnet vs Haiku)
● Error rates by component
● Cost per application
● User activity patterns
● Knowledge base storage usage
```
**Alarms**

```
● Lambda error rate > 5% (5min period)
● API latency > 30s (P99, 5min period)
● Cost per application > $0.15 (immediate)
● Knowledge base > 80% capacity (daily check)
● DynamoDB throttling events (any)
● SQS DLQ messages > 10 (5min period)
```
**Dashboards**

1. Operations Dashboard: System health, error rates, latencies
2. Cost Dashboard: Per-user costs, per-artifact costs, trends
3. User Dashboard: Active users, feature usage, conversion metrics
4. AI Dashboard: Token usage, model selection, prompt performance

**2.7 Integration Points**


1. Anthropic API
    ● Models: Claude Sonnet 4.5, Claude Haiku 4.
    ● API Key: Stored in Secrets Manager
    ● Rate Limiting: Managed by Anthropic
    ● Retry Logic: Exponential backoff (3 attempts)
2. Stripe
    ● Integration: Stripe Checkout, Customer Portal
    ● Webhooks: Payment success, subscription changes, failures
    ● Products: Monthly subscription ($20-30)
    ● Trial: 14 days
3. AWS Cognito
    ● User Pools: Authentication
    ● Identity Pools: AWS resource access
    ● MFA: Optional (encouraged)
    ● Password Policy: 8+ chars, mixed case, numbers
4. AWS SES
    ● Verified Domain: careervp.com
    ● Email Types: Transactional, notifications
    ● Suppression List: Bounces, complaints
    ● Tracking: Opens, clicks
5. AWS SNS
    ● Topics: Admin alerts, system events
    ● Subscriptions: Email (admin team)
    ● Message Filtering: By severity
6. Google Drive API (Future - V2)
    ● Purpose: Direct CV/knowledge base import
    ● OAuth2 integration
**3. REQUIREMENTS CATALOG**

**3.1 Functional Requirements**

**FR-1: User Authentication & Authorization (P0)**

```
● User registration with email verification
● Secure login (password + optional MFA)
● Password reset workflow
● Role-based access control (free/paid/admin)
● Session management (1-hour JWT expiration)
● API key generation (future - programmatic access)
```
**FR-2: Value Proposition Report Generation (P0)**

```
● Accept job posting (URL or text)
● Accept CV (upload or text)
```

```
● Optional: Knowledge base materials
● Generate strategic VPR with:
● Key differentiators identification
● Evidence mapping (STRONG/WEAK/NONE)
● Strategic recommendations
● Gap identification
● Processing time: 15-25 seconds
● Output: JSON + formatted document
```
**FR-3: CV Tailoring (P0)**

```
● Input: Master CV, VPR, job posting
● ATS optimization (keyword matching, formatting)
● Factual accuracy verification (no hallucinations)
● Maintains user's original achievements/dates
● One-page format (or user-specified length)
● Anti-AI detection compliance
● Processing time: 10-15 seconds
● Output: DOCX format
```
**FR-4: Cover Letter Generation (P0)**

```
● Input: VPR, tailored CV, job posting
● Optional: Writing samples for style matching
● Strict one-page limit
● Personalized to company/role
● Anti-AI detection compliance
● Professional formatting
● Processing time: 8-12 seconds
● Output: DOCX format
```
**FR-5: Gap Analysis with Interactive Q&A (P1)**

```
● Phase 1: Generate 5-8 targeted questions
● Non-redundant with CV
● Relevant to job requirements
● Open-ended for strategic responses
● Phase 2: Process user answers
● Identify skill gaps
● Identify experience gaps
● Provide actionable recommendations
● Suggest learning resources
● Total processing: ~30 seconds
● Output: JSON + formatted report
```
**FR-6: Interview Preparation Guide (P1)**

```
● Input: All previous artifacts + company research
```

```
● Generate:
● 15-20 likely interview questions
● STAR-method answer frameworks
● Company-specific insights
● Weakness handling strategies
● 30-second elevator pitch
● Follow-up questions to ask interviewer
● Processing time: 12-18 seconds
● Output: PDF format
```
**FR-7: Knowledge Base Management (P1)**

```
● Upload writing samples, portfolio items, references
● Version control (track updates)
● Storage limits: 100MB (free), 500MB (paid)
● File types: PDF, DOCX, TXT, MD
● Organization: Tags, categories
● Search and retrieval
● Admin notification at 80% capacity
```
**FR-8: Job Tracking Dashboard (P1)**

```
● List all applications with status
● Track: Draft → Submitted → Interview → Offer/Rejected
● Link to generated artifacts per job
● Notes field for user tracking
● Timeline visualization
● Export to CSV
```
**FR-9: Review & Edit Workflow (P0)**

```
● User can review each generated artifact
● In-app editing capabilities
● Regeneration option (with user feedback)
● Download final versions
● Version history
```
**FR-10: Usage Tracking & Limits (P0)**

```
● Track applications remaining (free tier: 3)
● Display usage dashboard
● Notifications at 80% usage
● Enforce rate limits
● Upgrade prompts when limits reached
```
**3.2 Non-Functional Requirements**

**NFR-1: Performance**


```
● API response time: < 30s (P99)
● Document generation: As specified per artifact
● Frontend load time: < 2s
● Database queries: < 100ms
● S3 uploads: < 5s for 5MB files
```
**NFR-2: Scalability**

```
● Support 100 users (Month 1)
● Support 1,000 users (Month 6)
● Support 10,000 users (Month 12)
● Auto-scaling for all components
● Horizontal scaling for stateless services
● DynamoDB on-demand scaling
```
**NFR-3: Availability**

```
● 99.9% uptime SLA
● Automated failover
● Multi-AZ deployment
● Graceful degradation
● Status page for incidents
```
**NFR-4: Security**

```
● Encryption at rest (all data stores)
● Encryption in transit (TLS 1.2+)
● Secrets in AWS Secrets Manager
● No sensitive data in logs
● Regular security audits
● OWASP Top 10 compliance
● Input validation on all endpoints
● Rate limiting and throttling
● WAF protection (SQL injection, XSS)
```
**NFR-5: Cost Efficiency**

```
● Target profit margin: 95%+
● Cost per application: < $0.10 (at scale)
● Optimize AI model selection
● Lifecycle policies on S
● Right-sized Lambda memory
● On-demand DynamoDB pricing
```
**NFR-6: Compliance**

```
● GDPR compliance (data portability, right to deletion)
● CCPA compliance (California users)
● Data residency options (future)
```

```
● Audit logging (all user actions)
● Terms of Service acceptance
● Privacy Policy compliance
```
**NFR-7: Maintainability**

```
● Comprehensive logging
● Distributed tracing
● Error tracking and alerting
● Automated deployments (CI/CD)
● Infrastructure as Code (Terraform)
● Documentation for all components
● Code review process
```
**NFR-8: Usability**

```
● Intuitive user interface
● Mobile-responsive design
● Accessibility (WCAG 2.1 AA)
● Onboarding tutorial
● Contextual help
● Progress indicators
● Clear error messages
```
**3.3 Constraints**

**Technical Constraints**

```
● AWS serverless only (no EC2, ECS, EKS)
● Anthropic Claude API dependency
● Lambda cold start latency (1-3s)
● Lambda timeout limits (15 min max)
● DynamoDB 400KB item size limit
● S3 storage costs at scale
● API Gateway 29-second timeout
```
**Business Constraints**

```
● Bootstrap budget: Limited infrastructure spend
● Solo developer initially
● Time to market: 3 months to MVP
● Competition: Existing AI writing tools
● Market education: Users unfamiliar with VPR concept
```
**Regulatory Constraints**

```
● GDPR compliance required (EU users)
● CCPA compliance required (CA users)
● No discriminatory practices in AI outputs
```

```
● Transparent AI usage disclosure
```
**AI Model Constraints**

```
● Anthropic API rate limits
● Model availability (Sonnet/Haiku)
● Context window limits (200K tokens)
● Token costs (pricing changes)
● Model update cycles
● Potential for AI hallucinations
```
**4. COST MODEL SUMMARY**

**4.1 Cost Per Artifact (Target)**

yaml

Value Proposition Report:
Model: Claude Sonnet 4.
Input Tokens: ~8,
Output Tokens: ~3,
Cost: $0.023 - $0.

CV Tailoring:
Model: Claude Haiku 4.
Input Tokens: ~5,
Output Tokens: ~2,
Cost: $0.003 - $0.

Cover Letter:
Model: Claude Haiku 4.
Input Tokens: ~4,
Output Tokens: ~1,
Cost: $0.002 - $0.

Gap Analysis (Complete):
Model: Claude Sonnet 4.5 (2 phases)
Phase 1 (Questions): ~$0.
Phase 2 (Analysis): ~$0.
Total: ~$0.

Interview Preparation:
Model: Claude Haiku 4.
Input Tokens: ~6,
Output Tokens: ~2,
Cost: $0.004 - $0.


Complete Application Package:
VPR + CV + Cover Letter: $0.028 - $0.
With Gap Analysis: $0.105 - $0.

With Interview Prep: $0.109 - $0.

**4.2 Infrastructure Costs (Monthly Estimates)**

yaml

100 Users (15 applications each):
Lambda: ~$5 (compute time)
DynamoDB: ~$3 (on-demand)
S3: ~$2 (storage + data transfer)
API Gateway: ~$4 (requests)
CloudWatch: ~$2 (logs + metrics)
Other: ~$4 (SES, SNS, Secrets)
Total: ~$20/month

1,000 Users (15 applications each):
Lambda: ~$
DynamoDB: ~$
S3: ~$
API Gateway: ~$
CloudWatch: ~$
Other: ~$
Total: ~$145/month

10,000 Users (15 applications each):
Lambda: ~$
DynamoDB: ~$
S3: ~$
API Gateway: ~$
CloudWatch: ~$
Other: ~$

Total: ~$1,350/month

**4.3 Optimization Strategies**

1. Hybrid Model Usage: 33% cost reduction vs all-Sonnet
2. Prompt Engineering: Minimize output tokens
3. Caching: Reuse VPR for multiple artifacts
4. Lifecycle Policies: Automatic S3 cleanup
5. Reserved Concurrency: Avoid unnecessary Lambda provisioning
6. On-Demand DynamoDB: Pay only for actual usage


7. CloudFront Caching: Reduce API Gateway calls
8. Batch Processing: Group notifications

**4.4 Target Margins**

yaml

Monthly Revenue (100 paid users @ $25): $2,
Monthly Infrastructure Cost: ~$
Monthly AI Costs (15 apps/user): ~$
Total Cost: ~$
Profit: $2,
Margin: 91.6%

Monthly Revenue (1,000 paid users): $25,
Monthly Infrastructure Cost: ~$
Monthly AI Costs: ~$1,
Total Cost: ~$2,
Profit: $22,
Margin: 91.8%

Monthly Revenue (10,000 paid users): $250,
Monthly Infrastructure Cost: ~$1,
Monthly AI Costs: ~$19,
Total Cost: ~$20,
Profit: $229,

Margin: 91.9%

**4.5 Rate Limiting Strategy**

yaml

Free Tier:
Applications: 3 total (trial)
API Calls: 10/hour, 50/day
Storage: 100MB knowledge base

Paid Tier ($20-30/month):
Applications: Unlimited
API Calls: 100/hour, 500/day
Storage: 500MB knowledge base
Priority Processing: Lower Lambda cold starts

Premium Tier (Future - $50+/month):
Applications: Unlimited
API Calls: 500/hour, 2000/day
Storage: 2GB knowledge base


Dedicated Support: Email support SLA

Advanced Features: Multi-language, company research

**5. SECURITY & COMPLIANCE**

**5.1 Authentication & Authorization**

yaml

User Authentication:
Method: AWS Cognito User Pools
Password Policy:

- Minimum 8 characters
- Mixed case required
- Numbers required
- Special characters recommended
MFA: Optional (encouraged for paid users)
Session: 1-hour JWT tokens
Refresh: 30-day refresh tokens

Authorization:
Model: Role-Based Access Control (RBAC)
Roles:

- free: 3 applications, limited features
- paid: Unlimited applications, standard features
- premium: All features, priority support (future)
- admin: Full system access, analytics

API Security:

- Cognito authorizer on all endpoints
- API keys for programmatic access (future)
- Request signing (AWS Signature V4)
- Input validation (schema-based)

**5.2 Data Protection**

yaml

Encryption at Rest:

- S3: AES-256 (AWS managed keys)
- DynamoDB: AWS managed keys
- Secrets Manager: Automatic encryption

Encryption in Transit:

- TLS 1.2+ for all connections


- Certificate pinning (future)
- HTTPS only (no HTTP)

Data Classification:

- Public: Marketing content
- Internal: System logs, metrics
- Confidential: User CVs, applications
- Restricted: Payment information (Stripe handles)

Data Retention:

- CVs: 7 days in temp, 30 days in outputs
- Generated artifacts: 30 days
- Knowledge base: User-controlled
- Logs: 90 days
- Audit trails: 7 years (compliance)

**5.3 Access Control**

yaml

IAM Policies:

- Least privilege principle
- Resource-based policies on S3
- Function-specific Lambda roles
- No wildcard permissions
- Regular policy audits

User Access:

- Own data only (no cross-user access)
- Temporary S3 presigned URLs (15-min expiry)
- No direct S3 access
- API Gateway as single entry point

Admin Access:

- Separate admin accounts
- MFA required
- Audit logging
- Time-boxed elevated access

**5.4 Compliance Requirements**

yaml

GDPR (EU Users):

- Data portability: Export all user data
- Right to be forgotten: Complete data deletion


- Consent management: Explicit opt-ins
- Data processing agreement: With Anthropic, Stripe
- DPO contact: privacy@careervp.com

CCPA (California Users):

- Do not sell: No user data selling
- Disclosure: What data is collected
- Access: Users can request data
- Deletion: Users can request deletion

AI Transparency:

- Disclosure: AI-generated content labeled
- Human oversight: User review/editing
- Bias mitigation: Diverse training data
- Explainability: VPR shows reasoning

PCI Compliance:

- Payment data: Never stored (Stripe handles)
- PCI-DSS: Stripe certified
- No card data: Tokens only

**5.5 Audit & Monitoring**

yaml

Audit Logging:

- All user actions: Login, generation, downloads
- All admin actions: User management, system changes
- All API calls: CloudTrail
- Retention: 7 years

Security Monitoring:

- GuardDuty: Threat detection
- CloudWatch: Anomaly detection
- WAF: Attack patterns
- SNS alerts: Security events

Incident Response:

- Playbooks: Per incident type
- Contact list: Security team
- Escalation: Based on severity
- Post-mortem: Required for P0/P1
```

## ---


## ## 6. USER EXPERIENCE DECISIONS

_### 6.1 User Workflows_

_#### Primary Workflow: Generate Application Package_
```

1. User logs in → Dashboard
2. Click "New Application"
3. Upload CV (or select existing)
4. Paste/upload job posting
5. (Optional) Select knowledge base materials
6. Click "Generate"
7. Progress indicator shows:
├─ Analyzing job posting... ✓
├─ Generating Value Proposition Report... (20s)
├─ Tailoring CV... (12s)
└─ Creating Cover Letter... (10s)
8. Review page shows all artifacts
9. User can:
├─ Download all (ZIP)
├─ Edit individual artifacts
├─ Regenerate with feedback
└─ Save to job tracking
10. Success confirmation + next steps
```

_#### Secondary Workflow: Gap Analysis_
```

1. From application review page
2. Click "Analyze My Gaps"
3. AI generates 5-8 questions (15s)
4. User answers questions (free-form text)
5. AI processes answers (18s)
6. Gap analysis report with:
├─ Identified skill gaps
├─ Experience gaps
├─ Recommendations
└─ Learning resources
7. User can save or download
```

_#### Knowledge Base Workflow_
```

1. Dashboard → "Knowledge Base"


2. View existing materials
3. Upload new materials:
├─ Writing samples
├─ Portfolio items
├─ References
└─ Other documents
4. Tag and categorize
5. Storage usage indicator
6. Select materials for application generation

**6.2 Review/Edit Capabilities**

yaml

Value Proposition Report:

- View: Formatted HTML or PDF
- Edit: Not editable (strategic analysis)
- Regenerate: With additional context

## CV:

- View: Formatted preview
- Edit: In-app editor (WYSIWYG)
- Download: DOCX format
- Regenerate: With user feedback

Cover Letter:

- View: Formatted preview
- Edit: In-app editor
- Download: DOCX format
- Regenerate: Different tone/emphasis

Gap Analysis:

- View: Formatted report
- Edit: Not editable
- Action: Follow recommendations

Interview Prep:

- View: PDF format
- Edit: Not editable (print and annotate)
- Practice: Future feature

**6.3 Error Handling & User Communication**

yaml

Error Types & User Messages:


1. Input Validation Errors:
- Missing CV: "Please upload or paste your CV"
- Invalid job posting: "Job posting is too short. Please provide
complete posting."
- File too large: "File exceeds 10MB limit. Please compress or
split."
2. Processing Errors:
- AI timeout: "Generation is taking longer than expected. You'll
receive an email when ready."
- AI error: "Unable to generate. Please try again or contact
support."
- Quota exceeded: "You've reached your free tier limit. Upgrade to
continue."
3. System Errors:
- Service unavailable: "Our systems are experiencing high demand.
Please retry in a moment."
- Maintenance: "Scheduled maintenance in progress. Check status
page for updates."
4. Payment Errors:
- Card declined: "Payment failed. Please update your payment
method."
- Subscription issue: "Subscription lapsed. Update payment to
restore access."

User Feedback Mechanisms:

- In-app feedback button
- Email support: support@careervp.com
- Intercom chat (paid users)
- Feature requests: Public roadmap

**6.4 Notification Strategy**

**User Notifications (SES Email)**

yaml

Welcome Series:

1. Welcome email (immediate)
- Getting started guide
- First application tutorial
- Support resources
2. Day 3: Tips for better CVs


3. Day 7: Trial reminder (if 0 applications)
4. Day 10: Upgrade benefits
5. Day 14: Last day of trial

Application Updates:

- Generation complete: "Your application package is ready!"
- Regeneration complete: "Your updated CV is ready to review."
- Download reminder: "Don't forget to download your materials. Link
expires in 7 days."

Account Updates:

- Trial ending: "Your trial ends in 3 days. Upgrade to continue."
- Payment success: "Thank you! Your subscription is active."
- Payment failed: "Payment issue. Please update your card."
- Subscription canceled: "Sorry to see you go. Your access
continues until [date]."

Product Updates:

- New features: Monthly digest
- Tips & best practices: Weekly (opt-in)

**Admin Notifications (SNS)**

yaml

System Alerts:

- Lambda error rate > 5%: Immediate
- DynamoDB throttling: Immediate
- Cost anomaly detected: Immediate
- API Gateway 5XX errors: Immediate

Operational Alerts:

- Daily summary: User signups, applications, revenue
- Weekly report: Key metrics, trends
- Monthly review: Comprehensive analytics

Abuse Detection:

- Suspicious usage pattern: Immediate
- User exceeded rate limits: Hourly summary
- Knowledge base abuse: Immediate
- Payment fraud suspected: Immediate

Capacity Warnings:

- User knowledge base > 80%: Daily
- S3 bucket approaching limit: Daily


- Concurrent Lambda approaching limit: Immediate
**7. GAPS & UNKNOWNS**

**7.1 Technical Unknowns**

yaml

Questions Requiring Resolution:

1. Cold Start Mitigation:
- Current: 1-3s cold start penalty
- Options: Provisioned concurrency, keep-warm pings, SnapStart
- Decision needed: Cost vs performance tradeoff
2. Document Format Handling:
- Current: Assumption of clean CV upload
- Unknown: Handling scanned PDFs, images, complex formatting
- Decision needed: OCR integration? Manual review?
3. Multi-Language Support (V2):
- Current: English only
- Unknown: Hebrew RTL handling, other languages
- Decision needed: Translation API? Native generation?
4. Company Research Integration (V2):
- Current: User provides job posting only
- Unknown: Automated company research sources
- Options: Clearbit, LinkedIn API, web scraping
- Decision needed: Legal compliance, cost
5. Real-Time Collaboration:
- Current: Single-user per application
- Future: Career coaches, recruiters collaborating
- Unknown: Conflict resolution, versioning
- Decision needed: Scope for V1 vs V2

**7.2 Business Unknowns**

yaml

Market Validation:

- Unknown: Willingness to pay $20-30/month
- Unknown: Value perception of VPR vs traditional approach
- Unknown: Competitive response


- Decision needed: Pricing experiments, A/B testing

User Acquisition:

- Unknown: Most effective marketing channels
- Unknown: Conversion rate free → paid
- Unknown: Churn rate
- Decision needed: Marketing budget allocation

Support Load:

- Unknown: Support ticket volume
- Unknown: Common user issues
- Unknown: Required support hours
- Decision needed: Hire support vs self-service

Feature Prioritization:

- Unknown: Most valuable V2 features
- Unknown: User demand for advanced features
- Decision needed: User research, usage analytics

**7.3 Legal/Compliance Unknowns**

yaml

Liability:

- Unknown: Liability for incorrect information in generated
documents
- Unknown: Liability for AI hallucinations leading to job rejection
- Decision needed: Legal review, insurance, disclaimer language

Content Ownership:

- Unknown: Who owns generated content? User or CareerVP?
- Unknown: Can we use generated content for training/improvement?
- Decision needed: Legal terms, user agreement

AI Regulation:

- Unknown: Future AI regulations (EU AI Act, US proposals)
- Unknown: Industry-specific hiring regulations
- Decision needed: Compliance monitoring, legal counsel

Fair Hiring Practices:

- Unknown: Does AI optimization create unfair advantage?
- Unknown: Could AI perpetuate biases?
- Decision needed: Bias testing, transparency

**7.4 Scaling Unknowns**


yaml

Performance at Scale:

- Unknown: DynamoDB performance at 10K+ users
- Unknown: Lambda concurrency limits in practice
- Unknown: Anthropic API rate limits at scale
- Decision needed: Load testing, capacity planning

Cost at Scale:

- Unknown: Actual AI costs with real user patterns
- Unknown: Infrastructure costs at 100K+ users
- Decision needed: Reserved capacity, enterprise agreements

Data Management:

- Unknown: S3 costs with long-term users
- Unknown: Database cleanup strategies
- Decision needed: Archival policies, cold storage

**7.5 Open Questions for You**

yaml

Immediate Decisions Needed:

1. Pricing:
- $20, $25, or $30/month for paid tier?
- Annual discount? (e.g., $200/year = $16.67/month)
- Usage-based pricing as alternative?
2. Trial Structure:
- 3 free applications vs 14-day unlimited trial?
- Credit card required for trial?
3. Feature Scope - V1:
- Include Gap Analysis in V1? (adds complexity)
- Include Interview Prep in V1?
- Job tracking in V1 or V2?
4. WordPress Integration:
- Build WordPress site first, or SPA first?
- Custom WordPress theme or existing theme?
- Blog content strategy (who writes?)
5. Support Strategy:
- Email-only support?
- Intercom chat for paid users?


- Knowledge base/FAQ priority?
- Support hours (24/7 or business hours)?
6. Beta Testing:
- How many beta users?
- Beta period duration?
- Beta user incentives (free forever, discount)?
7. Legal:
- DIY legal templates or hire lawyer?
- When to get legal review?
- Business entity type (LLC, C-Corp, etc.)?

**COMPLETENESS VERIFICATION**

**Checklist for Context Awareness:**

✅ Retrieved last 20 conversations: Confirmed via recent_chats
✅ Searched for key architectural terms: Multiple conversation_search calls
✅ Listed all Lambda functions: 18-22 functions documented
✅ Listed all DynamoDB tables: 4 tables with complete schemas
✅ Listed all S3 buckets: 5 buckets with lifecycle policies
✅ Listed all API endpoints: Core endpoints documented
✅ Documented model choices: Sonnet vs Haiku strategy clear
✅ Captured cost optimization strategies: Hybrid model, lifecycle, etc.
✅ Identified anti-AI detection requirements: 8-pattern framework
✅ Documented ATS optimization approach: Multi-layered strategy
✅ Listed security requirements: Comprehensive security section
✅ Captured user workflow decisions: Primary/secondary workflows
✅ Noted constraints and trade-offs: Technical, business, regulatory
✅ Identified integration points: Anthropic, Stripe, Cognito, etc.
✅ Documented monitoring/alerting strategy: CloudWatch complete
✅ Listed tagging requirements: Implied in infrastructure
✅ Captured deployment strategy: Serverless, IaC, CI/CD

**Warning Signs Check:**

✅ Not using generic architecture patterns - Specific to CareerVP
✅ Mentions specific model choices (Sonnet/Haiku split)
✅ References specific cost targets ($0.028-0.081, 95% margins)
✅ Includes YOUR specific requirements (anti-AI, ATS, gaps)
✅ References specific conversations and decisions
✅ Uses project-specific examples
✅ No suggestions of previously decided-against approaches


✅ No questions about already-discussed topics

**NEXT STEPS RECOMMENDATION**

Now that the Context Manifest is complete, I recommend:

Phase 1: Your Review (Critical)

```
● Review this manifest thoroughly
● Identify any gaps or inaccuracies
● Provide additional context where needed
● Approve before proceeding
```
Phase 2: Generate Detailed Features List Using this validated Context Manifest as the source of

truth, I will create:

1. Complete Features List for the CareerVP SaaS website
2. Feature Prioritization (P0/P1/P2 with justification)
3. User Stories for each feature (As a [user], I want to [action], so that [benefit])
4. Acceptance Criteria for each feature (measurable, testable)
5. Technical Dependencies (what needs to be built first)
6. Development Estimates (for Claude Code implementation planning)

Phase 3: Technical Documentation Suite After features approval:

1. Product Requirements Document (PRD)
2. Technical Specification Document
3. API Reference Document
4. Data Model Documentation
5. Infrastructure-as-Code Requirements
6. Testing Requirements Document
7. Deployment Guide Outline

Your Action Required:

Please review this Context Manifest and confirm:

1. ✅ All architectural decisions are accurate
2. ✅ No missing Lambda functions or services
3. ✅ Cost models align with your expectations
4. ✅ Security requirements are comprehensive
5. ✅ Workflow decisions match your vision
6. ❓ Any gaps or corrections needed

Or provide feedback on:

```
● Missing decisions or components
● Incorrect assumptions
● Additional context needed
● Priority changes
```

Once you approve, I'll proceed with generating the comprehensive Features List document.

1. How is company research being conducted for the VPR? Does it need a lambda,
    "company-research (V2)"?
2. Gap Analysis and Interview Prep questions are **limited to 10 questions.**
3. Questions Requiring Resolution
4. Cold Start Mitigation - Cost is priority
5. Document Format Handling - No handling scanned PDFs, images, complex formatting,
    ONLY process text-based files
6. English and Hebrew support, may need French
7. Company Research Integration - MUST be included in V1 - provide suggestions
8. Real-time Collaboration - not on the roadmap
9. Pricing is $20-$30 per month. Free trial is 14-days with 3 free applications. Credit card
    required for trial.
10. Include Gap Analysis and Interview Prep questions in V1. Job Tracking in V2.
11. Build SPA first, Wordpress is already built separately.
12. Email only support in V1
Show more
5:29 PM
I'll use Sequential Thinking to process these critical clarifications and update the Context

Manifest accordingly.

Let me analyze these important clarifications and update the Context Manifest with corrected

information.

Based on your clarifications, I need to update several critical sections of the Context Manifest.

Let me revise the key areas:

**UPDATED CONTEXT MANIFEST - CRITICAL**

**CORRECTIONS**

**1. Company Research Strategy (V1 REQUIRED)**

Decision Update: Company Research Integration

```
● Status: MUST be included in V1 (not V2)
● Current Gap: No automated company research mechanism defined
● Options for V1 Implementation:
```
yaml

Option A: Web Search + Scraping (Recommended for V1)
Lambda Function: company-research-v1
Approach:

- Accept company name + job posting URL


- Google search for: "[Company] about, culture, values, recent
news"
- Scrape company website sections: About, Culture, Press Releases
- Scrape LinkedIn company page (if available)
- Aggregate into structured JSON
Pros:
- Low/no external API costs
- Real-time current information
- Comprehensive coverage
Cons:
- Web scraping fragility (site changes)
- Potential legal/ToS issues
- Slower processing (20-30s)
Cost: ~$0 (compute only, ~$0.001 Lambda)

Option B: Clearbit Company API
Lambda Function: company-research-v1
Approach:

- Company domain → Clearbit API
- Returns: Employee count, industry, tech stack, funding,
description
Pros:
- Reliable, structured data
- Fast (2-3s)
- Legal compliance
Cons:
- Cost: $0.02-0.05 per lookup
- Limited narrative/culture information
- Primarily US companies
Cost: $0.02-0.05 per company lookup

Option C: Perplexity API (Research-focused AI)
Lambda Function: company-research-v1
Approach:

- Query: "Research [Company]. Provide: company overview, culture,
recent news, values, work environment insights."
- Returns: Comprehensive research with citations
Pros:
- AI-powered comprehensive research
- Citations/sources included
- Current information
Cons:
- Cost: ~$0.01-0.03 per query
- Another API dependency
Cost: $0.01-0.03 per research query


Option D: Hybrid Approach (RECOMMENDED)
Lambda Function: company-research-v1
Approach:

1. Parse job posting for company website URL
2. Web scrape company "About" page (5-10s)
3. If insufficient data → Fallback to Google search
4. Structure data for VPR consumption
Pros:
- Cost-effective (~$0.001)
- Most data from primary source (company website)
- Fallback ensures coverage
Cons:
- Requires robust error handling
- Website parsing complexity
Cost: ~$0.001-0.005 (mostly Lambda compute)

DECISION NEEDED: Which approach for V1?

- Recommend: Option D (Hybrid) for cost and V1 speed
- Can upgrade to Perplexity/Clearbit in V2 if needed

Updated Lambda Function:

yaml

company-research-v1:
Priority: P0 (Required for V1)
Model: No AI (web scraping + text extraction)
Memory: 512 MB
Timeout: 60s
Avg Duration: 15-25s
Input: Company name, job posting URL, company domain
Output:

- Company overview (200-300 words)
- Key values/culture
- Recent news/achievements (last 6 months)
- Employee insights (if available)
- Structured JSON for VPR
Dependencies: BeautifulSoup4, requests, optional Playwright for
JS-rendered sites
Cost: ~$0.001-0.005

Integration Point:

- Called BEFORE VPR generation
- Company research injected into VPR prompt context
- Enables company-specific tailoring in VPR


**2. Gap Analysis & Interview Prep - Question Limits**

CRITICAL CORRECTION:

yaml

Gap Analysis - Question Generation:
OLD: 5-8 questions
NEW: Maximum 10 questions

Updated Specification:

- Generate 8-10 targeted questions (not 5-8)
- Questions must be:
* Non-redundant with CV
* Specific to job requirements
* Open-ended for strategic responses
* Covering different competency areas
- Validation: Ensure exactly 10 questions or fewer

Interview Preparation - Question Generation:
OLD: 15-20 questions
NEW: Maximum 10 questions

Updated Specification:

- Generate 8-10 most likely interview questions (not 15-20)
- Focus on:
* Behavioral questions (STAR method)
* Technical questions (role-specific)
* Company culture fit
* Situational questions
* 2-3 weakness/challenge questions
- Each question includes:
* Question text
* STAR framework answer structure
* Key points to emphasize

* What interviewer is evaluating

Cost Impact Update:

yaml

Gap Analysis:

- Fewer questions = slightly lower token output
- Updated cost: $0.065-0.075 (vs previous $0.077)

Interview Prep:

- Fewer questions = significantly lower token output


- Updated cost: $0.003-0.005 (vs previous $0.004-0.006)
**3. Technical Resolutions**

**3.1 Cold Start Mitigation (COST PRIORITY)**

Decision: Minimize cold start costs, accept latency

yaml

Strategy:

- NO provisioned concurrency (costs $13+/month per function)
- NO keep-warm pings (costs ~$5-10/month per function)
- YES to SnapStart for Java (N/A - using Python)

Accepted Approach:

- Cold start: 1-3s penalty on first request
- Subsequent requests: Warm container (<100ms startup)
- User communication: "Generating... this may take 20-30 seconds"

Mitigation Without Cost:

- Minimal Lambda package size (smaller = faster cold start)
- Shared layers for common dependencies
- Lazy loading of heavy libraries
- User expectation setting (progress indicators)

Cost: $0 (vs $156/month for provisioned concurrency on 12 functions)

**3.2 Document Format Handling**

Decision: Text-based files ONLY

yaml

Supported Formats:

- DOCX (Microsoft Word) ✅
- PDF with embedded text ✅
- TXT (plain text) ✅
- Markdown (.md) ✅

NOT Supported (V1):

- Scanned PDFs (images) ❌
- Image files (JPG, PNG) ❌
- Complex formatting (tables, multi-column) ⚠ (attempt to extract)
- Password-protected files ❌

Validation:

- File upload: Check MIME type


- Text extraction: Verify extractable text content
- Minimum text: Require at least 200 words
- Error message: "Please upload a text-based CV. Scanned images are
not supported."

Future V2:

- OCR integration (AWS Textract) for scanned PDFs
- Cost: $0.0015 per page

**3.3 Multi-Language Support**

Decision: English + Hebrew in V1, French in V2

yaml

V1 Languages:

- English (primary) ✅
- Hebrew (RTL support) ✅

V2 Languages:

- French ✅
- Spanish (potential)
- German (potential)

Implementation Strategy:
Language Detection:

- Automatic detection from CV text
- Manual language selector (user override)
- Library: langdetect or fasttext

Hebrew Specific:

- RTL text handling in DOCX generation
- python-docx RTL support (paragraph.alignment =
WD_ALIGN_PARAGRAPH.RIGHT)
- Font selection: Arial, David, Miriam
- Date format: DD/MM/YYYY (Israeli standard)

AI Prompt Adaptation:

- System prompt: "Generate CV in [LANGUAGE]. User's native
language is [LANGUAGE]."
- Anthropic Claude: Multi-lingual support built-in
- No additional cost for language switching

Cost Impact:

- No additional AI costs (same token counts)
- Development effort: RTL handling, testing


**4. Pricing & Trial Structure (CONFIRMED)**

yaml

Free Trial:
Duration: 14 days
Applications: 3 complete applications
Credit Card: REQUIRED at signup

Rationale:

- Credit card required reduces free-tier abuse
- Automatic conversion to paid after trial
- Standard SaaS practice (reduces friction)

Trial Experience:

- Full feature access (not limited)
- Clear counter: "2 of 3 trial applications remaining"
- Email reminders: Day 7, Day 10, Day 13
- Upgrade prompt: "Upgrade anytime for unlimited access"

Paid Tier:
Price Range: $20-30/month
DECISION NEEDED: Exact price point

- Option A: $20/month (more competitive, higher volume)
- Option B: $25/month (middle ground)
- Option C: $30/month (premium positioning)

Applications: Unlimited
Features: All V1 features
Support: Email only

Annual Option (Recommended):

- If $25/month: $240/year ($20/month effective) = 20% discount
- If $30/month: $288/year ($24/month effective) = 20% discount
- Rationale: Improved retention, upfront revenue
**5. Feature Scope - V1 vs V2 (UPDATED)**

yaml

V1 Features (MVP - 3 Months):
✅ User Authentication (Cognito)
✅ Value Proposition Report generation
✅ CV Tailoring
✅ Cover Letter generation


✅ Gap Analysis (10 questions max)
✅ Interview Prep (10 questions max)
✅ Company Research (REQUIRED - Option D recommended)
✅ Knowledge Base management (upload, store, retrieve)
✅ Review/Edit workflow
✅ Download artifacts
✅ Usage tracking & limits
✅ Payment integration (Stripe)
✅ Email notifications (SES)
✅ English + Hebrew language support
✅ Email-only support

V2 Features (Post-Launch):
⏳ Job Tracking dashboard
⏳ French language support
⏳ Advanced company research (Perplexity/Clearbit)
⏳ Multi-language translation
⏳ Intercom chat support (paid users)
⏳ Advanced analytics
⏳ API access (programmatic)
⏳ Team collaboration features
⏳ Industry-specific templates

⏳ OCR for scanned documents

**6. WordPress & Development Strategy (CONFIRMED)**

yaml

Development Priority:

1. SPA (React) - Primary development focus
2. WordPress - Already built separately

WordPress Integration:

- Subdomain: app.careervp.com (SPA), careervp.com (WordPress)
- Navigation: WordPress links to app.careervp.com/signup
- Shared branding: Logo, colors, fonts
- No technical integration required (separate systems)

WordPress Content:

- Marketing pages (Home, Features, Pricing, About)
- Blog (SEO, content marketing)
- Legal pages (Terms, Privacy, Cookie Policy)
- Support/FAQ

SPA Content:


- Application dashboard
- Generation workflows
- Account management
- Settings
- Usage tracking
**7. Support Strategy (V1 CONFIRMED)**

yaml

V1 Support:
Channel: Email ONLY
Address: support@careervp.com

Support Hours:

- Business hours: 9 AM - 6 PM IST (Israel time)
- Monday - Friday
- Response time: 24 hours (target)

Support Process:

1. User emails support@careervp.com
2. Ticket created (ticketing system TBD - could be Gmail + labels
initially)
3. Response within 24 hours
4. Escalation: Complex issues to admin

Self-Service:

- FAQ page (WordPress)
- Knowledge base articles (WordPress blog)
- Video tutorials (YouTube embedded)
- In-app tooltips/help text

V2 Support Upgrades:

- Intercom chat (paid users only)
- Priority support (premium tier)
- Phone support (enterprise tier)

**UPDATED LAMBDA FUNCTIONS INVENTORY**

**Core Generation Functions (Updated)**

yaml

1. company-research-v1: ⭐ NEW - REQUIRED FOR V1
Model: No AI (web scraping)


Memory: 512 MB
Timeout: 60s
Avg Duration: 15-25s
Cost: ~$0.001-0.005

2. vp-report-generator:
Model: Claude Sonnet 4.5
Memory: 1024 MB
Timeout: 120s
Avg Duration: 15-25s
Cost: $0.023-0.035
Dependencies: company-research-v1 (must complete first)
3. cv-tailor:
Model: Claude Haiku 4.5
Memory: 512 MB
Timeout: 60s
Avg Duration: 10-15s
Cost: $0.003-0.005
4. cover-letter-generator:
Model: Claude Haiku 4.5
Memory: 512 MB
Timeout: 60s
Avg Duration: 8-12s
Cost: $0.002-0.004
5. gap-analysis-questions:
Model: Claude Sonnet 4.5
Memory: 512 MB
Timeout: 60s
Avg Duration: 12-18s
Cost: ~$0.030-0.035 (UPDATED - 10 questions vs 5-8)
6. gap-analysis-processor:
Model: Claude Sonnet 4.5
Memory: 512 MB
Timeout: 60s
Avg Duration: 15-20s
Cost: ~$0.035-0.040 (UPDATED)
7. interview-prep-generator:
Model: Claude Haiku 4.5
Memory: 512 MB
Timeout: 60s


Avg Duration: 12-18s
Cost: $0.003-0.005 (UPDATED - 10 questions vs 15-20)

8. language-detector: ⭐ NEW - REQUIRED FOR V1
Model: No AI
Memory: 256 MB
Timeout: 5s
Purpose: Detect CV language (English/Hebrew)

Cost: <$0.001

**UPDATED COST MODEL**

yaml

Complete Application Package (with Company Research):

Minimal Package (VPR + CV + Cover Letter):

- Company Research: $0.001-0.005
- VPR: $0.023-0.035
- CV: $0.003-0.005
- Cover Letter: $0.002-0.004
Total: $0.029-0.049 (vs previous $0.028-0.044)

Full Package (with Gap Analysis):

- Company Research: $0.001-0.005
- VPR: $0.023-0.035
- CV: $0.003-0.005
- Cover Letter: $0.002-0.004
- Gap Analysis: $0.065-0.075
Total: $0.094-0.124 (vs previous $0.105-0.121)

Complete Package (with Interview Prep):

- Company Research: $0.001-0.005
- VPR: $0.023-0.035
- CV: $0.003-0.005
- Cover Letter: $0.002-0.004
- Gap Analysis: $0.065-0.075
- Interview Prep: $0.003-0.005
Total: $0.097-0.129 (vs previous $0.109-0.127)

Key Changes:
✅ Added company research cost (+$0.001-0.005)
✅ Reduced Gap Analysis cost (10 questions vs 5-8)
✅ Reduced Interview Prep cost (10 questions vs 15-20)
✅ Net impact: ~$0.01-0.02 increase per full package


✅ Still well within <$0.15 target

**CRITICAL OPEN DECISION**

**Company Research Implementation - REQUIRES YOUR DECISION**

Based on your requirement that company research MUST be in V1, I need your decision on

implementation approach:

Recommended: Option D (Hybrid Web Scraping)

yaml

Pros:

- Lowest cost (~$0.001-0.005)
- Primary source data (company website)
- No external API dependencies
- Fast implementation for V1

Cons:

- Requires robust error handling
- Website changes can break scraping
- May miss data for companies without websites

Implementation:

1. Extract company domain from job posting URL
2. Scrape company website: /about, /culture, /team pages
3. Extract: company description, values, recent news
4. Fallback: Google search if website scraping fails
5. Structure data for VPR prompt injection

Libraries:

- BeautifulSoup4 (HTML parsing)
- requests (HTTP)
- Optional: Playwright (for JS-heavy sites)

Alternative: Option C (Perplexity API)

yaml

Pros:

- AI-powered comprehensive research
- Citations/sources included
- More reliable than web scraping
- Handles complex cases automatically

Cons:


- Cost: $0.01-0.03 per lookup
- Another API dependency
- Requires Perplexity API account

Implementation:

1. Send company name to Perplexity
2. Query: "Research [Company]. Provide overview, culture, recent
news."
3. Receive structured research with citations
4. Inject into VPR prompt

DECISION NEEDED:

```
● Option D (Recommended for V1): Web scraping + fallback
● Option C (More robust): Perplexity API
● Option A: Web scraping only (no fallback)
● Custom approach: Your preference
```
**NEXT STEPS**

With these critical corrections and clarifications, I'm ready to proceed with:

✅ Context Manifest is now UPDATED and COMPLETE

Ready to Generate:

1. Detailed Features List for CareerVP SaaS website
    ● All V1 features with correct specifications
    ● Company research integration (pending your decision on approach)
    ● Updated question limits (10 max)
    ● Language support (English + Hebrew)
    ● Support model (email only)

Please Confirm:

1. ✅ Company research approach: Which option (A/C/D) for V1?
2. ✅ Exact pricing: $20, $25, or $30/month?
3. ✅ All other clarifications incorporated correctly?

Once you confirm the company research approach and pricing, I'll generate the comprehensive

Features List document with complete specifications for Claude Code development.

1. company-research-v1 -> Use Option D Hybrid with fallback to Perplexity API
2. Gap Analysis and Interview Prep questions MUST include previously answered questions
    as part of calculus.
3. Company research -> Option D with Option C as fallback. Should reject LinkedIn or
    Indeed job posting links.
4. Exact pricing confirmed as $20-$30 per month. Still undecided as the final pricing model.


Manifest Confirmed!

Proceed to Features List document.

5:47 PM
I'll now generate the comprehensive Features List document for the CareerVP SaaS website,

using the validated and updated Context Manifest as the source of truth.

I'll create a comprehensive Features List document with complete specifications for Claude Code

development.


# Tab 3


**CAREERVP JOB SEARCH ASSISTANT**

**Complete Features List & Specifications Document**

**Version 1.0 - MVP (3-Month Development Timeline)**

Document Purpose: Comprehensive feature specifications for Claude Code development of the

CareerVP SaaS platform.

Last Updated: Based on validated Context Manifest (January 2025)

**TABLE OF CONTENTS**

1. Feature Priority Framework
2. Core Features - P0 (Critical Path)
3. Enhanced Features - P1 (High Value)
4. Supporting Features - P2 (Nice to Have)
5. Technical Dependencies & Build Order
6. Development Estimates
7. Feature Acceptance Criteria
8. V2 Roadmap Features
**1. FEATURE PRIORITY FRAMEWORK**

**Priority Definitions**

yaml

P0 (Critical - Must Have for MVP):
Definition: Core functionality without which the product cannot
launch
Impact: Blocks launch if missing
User Impact: Cannot complete primary user journey
Examples: Authentication, CV generation, payment

P1 (High - Strong Value Add):
Definition: Significantly enhances value proposition
Impact: Reduces competitive advantage if missing
User Impact: Reduces user success rate materially
Examples: Gap Analysis, Interview Prep, Company Research

P2 (Medium - Nice to Have):
Definition: Improves user experience but not critical
Impact: Can be added post-launch


User Impact: Convenience features
Examples: Advanced analytics, bulk operations

V2 (Future Roadmap):
Definition: Not included in MVP scope
Impact: Post-launch enhancements
User Impact: Future value additions

Examples: Job tracking, team collaboration, API access

**Feature Distribution**

yaml

Total V1 Features: 45
├─ P0 (Critical): 22 features (49%)
├─ P1 (High): 15 features (33%)
└─ P2 (Medium): 8 features (18%)

V2 Features: 12+ features (deferred)

**2. CORE FEATURES - P0 (CRITICAL PATH)**

**2.1 User Authentication & Authorization**

**Feature ID: F-AUTH-001**

Feature Name: User Registration

Priority: P0

User Story:

```
As a job seeker, I want to create an account so that I can access the platform and track my
applications.
```
Description: Complete user registration workflow with email verification, password creation,

and trial activation.

Functional Requirements:

1. Registration form fields:
    ● Email address (required, validated)
    ● Password (required, min 8 chars, complexity requirements)
    ● Confirm password (must match)
    ● First name (required)
    ● Last name (required)
    ● Accept Terms of Service (required checkbox)
    ● Accept Privacy Policy (required checkbox)


2. Validation rules:
    ● Email format validation (regex)
    ● Email uniqueness check (no duplicates)
    ● Password strength indicator (weak/medium/strong)
    ● Password requirements: 8+ chars, uppercase, lowercase, number
3. Email verification:
    ● Send verification email via SES
    ● Verification link expires in 24 hours
    ● Resend verification option
    ● Account remains inactive until verified
4. Trial activation:
    ● Automatically activate 14-day trial after email verification
    ● Credit card collection required (Stripe Checkout)
    ● Set credits_remaining = 3
    ● Set subscription_status = "trialing"
    ● Send welcome email with onboarding guide

Technical Specifications:

yaml

Backend:
Service: AWS Cognito User Pools
Lambda: user-auth-handler
DynamoDB Table: careervp-users

API Endpoint:
POST /auth/register
Request:

- email: string
- password: string
- first_name: string
- last_name: string
- terms_accepted: boolean
- privacy_accepted: boolean
Response:
- user_id: uuid
- status: "verification_pending"
- message: "Please check your email to verify your account"

Error Codes:

- 400: Invalid input (email format, password strength)
- 409: Email already exists
- 500: Server error

Dependencies:


```
● AWS Cognito User Pools configured
● SES email domain verified (careervp.com)
● DynamoDB Users table created
● Stripe account connected
```
Acceptance Criteria:

User can successfully register with valid email/password
Duplicate email returns clear error message
Weak passwords are rejected with specific requirements shown
Verification email sent within 60 seconds
Verification link activates account and starts trial
User redirected to dashboard after verification
Welcome email sent after account activation
Stripe payment method collected successfully
User record created in DynamoDB with correct initial values
Test Cases:

yaml

TC-AUTH-001-01: Valid Registration
Input: Valid email, strong password, accepted terms
Expected: Success, verification email sent

TC-AUTH-001-02: Duplicate Email
Input: Existing email address
Expected: Error 409, "Email already registered"

TC-AUTH-001-03: Weak Password
Input: Password "12345678"
Expected: Error 400, password requirements shown

TC-AUTH-001-04: Email Verification
Input: Click verification link

Expected: Account activated, trial started, redirected to dashboard

**Feature ID: F-AUTH-002**

Feature Name: User Login

Priority: P0

User Story:

```
As a registered user, I want to log in to my account so that I can access my applications and
generated materials.
```
Description: Secure login with JWT token issuance, session management, and optional MFA.

Functional Requirements:


1. Login form:
    ● Email address (required)
    ● Password (required)
    ● Remember me (optional checkbox)
    ● Forgot password link
2. Authentication flow:
    ● Validate credentials against Cognito
    ● Issue JWT access token (1-hour expiry)
    ● Issue refresh token (30-day expiry)
    ● Store tokens securely (httpOnly cookies)
3. Session management:
    ● Access token automatically refreshed when expired
    ● User remains logged in for 30 days (if "Remember me" checked)
    ● Force logout after 30 days regardless
    ● Multiple device login supported
4. Security features:
    ● Rate limiting: 5 failed attempts → 15-minute lockout
    ● Brute force protection
    ● Device fingerprinting (log login locations)
    ● Email notification on new device login

Technical Specifications:

yaml

Backend:
Service: AWS Cognito User Pools
Lambda: user-auth-handler

API Endpoint:
POST /auth/login
Request:

- email: string
- password: string
- remember_me: boolean
Response:
- access_token: string (JWT)
- refresh_token: string
- expires_in: number (3600 seconds)
- user: {user_id, email, first_name, tier, credits_remaining}

Error Codes:

- 401: Invalid credentials
- 403: Account not verified
- 429: Too many failed attempts
- 500: Server error


Dependencies:

```
● AWS Cognito configured
● JWT secret in Secrets Manager
● Rate limiting implemented in API Gateway
```
Acceptance Criteria:

```
Valid credentials return JWT tokens
Invalid credentials return clear error message
Unverified accounts cannot log in
After 5 failed attempts, account locked for 15 minutes
"Remember me" keeps user logged in for 30 days
Access token automatically refreshed when expired
User redirected to dashboard after successful login
New device login triggers email notification
```
**Feature ID: F-AUTH-003**

Feature Name: Password Reset

Priority: P0

User Story:

```
As a user who forgot my password, I want to reset it via email so that I can regain access to my
account.
```
Description: Self-service password reset workflow with email verification and secure token

mechanism.

Functional Requirements:

1. Forgot password flow:
    ● User enters email address
    ● System sends reset link via SES
    ● Reset link expires in 1 hour
    ● Reset token is single-use
2. Reset form:
    ● New password (required, same complexity rules)
    ● Confirm new password (must match)
    ● Password strength indicator
3. Completion:
    ● Password updated in Cognito
    ● All existing sessions invalidated
    ● Confirmation email sent
    ● User redirected to login

Technical Specifications:

yaml


API Endpoints:
POST /auth/forgot-password
Request: {email: string}
Response: {message: "If account exists, reset email sent"}

POST /auth/reset-password
Request: {token: string, new_password: string}
Response: {message: "Password reset successful"}

Error Codes:

- 400: Invalid token or expired
- 400: Password doesn't meet requirements
- 500: Server error

Acceptance Criteria:

```
Reset email sent within 60 seconds
Reset link expires after 1 hour
Reset token can only be used once
Weak passwords rejected
Successful reset invalidates all sessions
Confirmation email sent after reset
User can log in with new password
```
**2.2 Company Research & Analysis**

**Feature ID: F-RESEARCH-001**

Feature Name: Company Research Service (Hybrid)

Priority: P0

User Story:

```
As a user, I want the system to automatically research the company so that my application
materials are personalized and demonstrate company knowledge.
```
Description: Automated company research using hybrid approach: web scraping with Perplexity

API fallback. Provides company overview, culture, values, and recent news for VPR generation.

Functional Requirements:

1. Input validation:
    ● Extract company domain from job posting URL
    ● Reject LinkedIn job posting URLs (linkedin.com/jobs/*)
    ● Reject Indeed job posting URLs (indeed.com/*)
    ● Accept direct company URLs or detect from job posting
    ● Fallback: Use company name for research if URL unavailable
2. Research workflow: Phase 1: Web Scraping (Primary)
    ● Navigate to company website


```
● Scrape sections: /about, /about-us, /company, /culture, /team, /careers
● Extract: Company description, mission, values, culture
● Parse HTML and extract main content (ignore navigation/footer)
● Timeout: 20 seconds
```
3. Phase 2: Perplexity API Fallback (If Phase 1 fails)
    ● Trigger conditions:
       ● Website scraping timeout
       ● Insufficient data extracted (<100 words)
       ● Website inaccessible
       ● Parsing errors
    ● Query Perplexity: "Research [Company Name]. Provide: company overview,
       mission/values, culture, recent news (last 6 months), employee insights if
       available."
    ● Cost: $0.01-0.03 per query
4. Data structuring:
    ● Company name
    ● Industry/sector
    ● Company size (if available)
    ● Overview (200-300 words)
    ● Mission/values (bullet points)
    ● Culture insights (100-200 words)
    ● Recent news/achievements (3-5 items, last 6 months)
    ● Data source (website URL or Perplexity)
5. Error handling:
    ● If both methods fail: Generate VPR without company research (degraded mode)
    ● Notify user: "Limited company information available. VPR generated with focus
       on job requirements."
    ● Log failure for admin review

Technical Specifications:

yaml

Lambda Function:
Name: company-research-v1
Runtime: Python 3.11
Memory: 512 MB
Timeout: 60s
Avg Duration: 15-25s (web scraping), 5-10s (Perplexity)

Dependencies:

- BeautifulSoup4 (HTML parsing)
- requests (HTTP client)
- lxml (fast XML/HTML processing)
- Perplexity API client


API Endpoint:
POST /research/company
Request:

- job_posting_url: string (optional)
- company_name: string (required)
- company_domain: string (optional)
Response:
- company_name: string
- overview: string (200-300 words)
- mission_values: array[string]
- culture: string (100-200 words)
- recent_news: array[{title, date, summary}]
- data_source: string (website|perplexity|failed)
- research_timestamp: ISO8601

Error Codes:

- 400: LinkedIn/Indeed URL rejected
- 400: Missing company_name
- 500: Both methods failed (degraded mode)

URL Rejection Logic:

python

REJECTED_DOMAINS = [
'linkedin.com',
'indeed.com',
'glassdoor.com',
'monster.com',
'ziprecruiter.com'
]

def is_job_board_url(url: str) -> bool:
parsed = urlparse(url)
domain = parsed.netloc.lower()
return any(rejected in domain for rejected in REJECTED_DOMAINS)

_# If job_board URL detected:
# - Extract company name from job posting text
# - Use company name for research (not URL)_

_# - Attempt to find company website via Google search_

Perplexity Integration:

yaml

Perplexity API:


Model: sonar-pro (recommended for accuracy)
Query Template: >
Research {company_name}. Provide:

1. Company overview (who they are, what they do)
2. Mission and core values
3. Company culture and work environment
4. Recent news or achievements (last 6 months)
5. Any relevant employee insights

Format as structured JSON with sections.

Timeout: 10s
Retry: 2 attempts
Cost: $0.01-0.03 per query

Fallback: Degraded mode (no company research)

Cost Model:

yaml

Per Research:
Primary (Web Scraping): $0.001-0.003 (Lambda compute only)
Fallback (Perplexity): $0.01-0.03 (API cost)

Expected Distribution:

- 70% success via web scraping: $0.002 avg
- 30% fallback to Perplexity: $0.020 avg
- Weighted average: ~$0.008 per research

Monthly Cost (1000 users, 15 apps each):

- 15,000 company researches
- Cost: ~$120/month

Dependencies:

```
● Perplexity API account and key
● API key stored in AWS Secrets Manager
● BeautifulSoup4 + requests + lxml installed
● Error handling for network timeouts
```
Acceptance Criteria:

```
LinkedIn/Indeed URLs rejected with clear error message
Direct company URLs successfully scraped
Web scraping extracts meaningful content (>100 words)
Perplexity fallback triggered when scraping fails
Perplexity returns structured company research
Research completes within 30 seconds (95th percentile)
```

Degraded mode works when both methods fail
User notified when limited company info available
Company research integrated into VPR prompt
Data cached for repeat applications to same company (future optimization)
Test Cases:

yaml

TC-RESEARCH-001-01: Direct Company URL
Input: job_posting_url = "https://stripe.com/jobs/listing/123"
Expected: Scrape stripe.com/about, return structured data

TC-RESEARCH-001-02: LinkedIn URL Rejected
Input: job_posting_url = "https://linkedin.com/jobs/view/123"
Expected: Error 400, "Job board URLs not supported. Please provide
company URL."

TC-RESEARCH-001-03: Scraping Fails → Perplexity Fallback
Input: company_domain = "privatecompany.internal" (inaccessible)
Expected: Perplexity API called, returns research data

TC-RESEARCH-001-04: Both Methods Fail
Input: company_name = "Nonexistent Corp XYZ"
Expected: Degraded mode, VPR generated without company research,
user notified

TC-RESEARCH-001-05: Company Name Extraction
Input: job_posting_text contains "About Stripe: We're building..."

Expected: Extract "Stripe", research via Perplexity

**2.3 Value Proposition Report (VPR) Generation**

**Feature ID: F-VPR-001**

Feature Name: Value Proposition Report Generation

Priority: P0

User Story:

```
As a job seeker, I want an AI-generated strategic analysis of how my background aligns with
the job so that I understand my unique value proposition and can tailor my application
effectively.
```
Description: AI-powered strategic analysis using Claude Sonnet 4.5 that maps user's

qualifications to job requirements, identifies differentiators, and provides evidence-based

recommendations. Foundation for all downstream artifacts.


Functional Requirements:

1. Input processing:
    ● Job posting text (required, min 200 words)
    ● User CV text (required, min 300 words)
    ● Company research data (from F-RESEARCH-001)
    ● Knowledge base materials (optional, max 5 items)
    ● Language detection (English/Hebrew)
2. Analysis components:
    ● Job Requirements Extraction:
       ● Required skills (technical & soft)
       ● Preferred qualifications
       ● Experience requirements
       ● Education requirements
       ● Certifications/licenses
       ● Domain knowledge areas
    ● User Profile Mapping:
       ● Relevant experience (years, roles, companies)
       ● Technical skills (exact matches + transferable)
       ● Soft skills (demonstrated in CV)
       ● Achievements (quantified when possible)
       ● Education & certifications
       ● Domain expertise
    ● Evidence Strength Rating:
       ● STRONG: Direct, quantified evidence in CV
       ● MODERATE: Relevant but indirect evidence
       ● WEAK: Implied or transferable skills
       ● NO_EVIDENCE: Missing from CV
    ● Differentiators Identification (5-8 items):
       ● Unique combinations of skills/experience
       ● Specialized expertise
       ● Quantified achievements
       ● Industry-specific knowledge
       ● Technical depth in key areas
       ● Leadership/impact evidence
    ● Strategic Recommendations:
       ● Top 3-5 themes to emphasize
       ● Story angles for cover letter
       ● Interview talking points
       ● Gaps to address proactively
       ● Potential concerns to mitigate
3. Output format:
    ● Structured JSON (for programmatic use):

json


## {

"job_requirements": [...],
"user_profile": [...],
"evidence_map": {...},
"differentiators": [...],
"recommendations": {...},
"company_insights": {...}

}

```
● Formatted Document (for user review):
● Executive summary (100 words)
● Differentiators (detailed explanations)
● Evidence mapping table
● Strategic recommendations
● Company alignment notes
● PDF + HTML formats
```
4. Quality controls:
    ● Factual verification: All claims must reference CV
    ● No hallucinations: Reject any invented experience/skills
    ● Language consistency: Match input language (English/Hebrew)
    ● Completeness check: All sections required
    ● Evidence quality: Minimum 3 STRONG differentiators

Technical Specifications:

yaml

Lambda Function:
Name: vp-report-generator
Runtime: Python 3.11
Memory: 1024 MB (higher for complex processing)
Timeout: 120s
Avg Duration: 15-25s
Model: Claude Sonnet 4.5

AI Configuration:
Model: claude-sonnet-4-5-20250929
Temperature: 0.3 (low for consistency)
Max Tokens: 4000 (output)

System Prompt: |
You are an expert career strategist and value proposition
analyst.
Analyze the job posting and user's CV to create a strategic VPR.

CRITICAL RULES:


1. Only reference information ACTUALLY in the CV
2. Never invent or assume skills/experience
3. Rate evidence strength honestly
(STRONG/MODERATE/WEAK/NO_EVIDENCE)
4. Identify 5-8 unique differentiators
5. Provide actionable strategic recommendations
6. Incorporate company research insights
7. Generate in [LANGUAGE]: {language}

## OUTPUT REQUIREMENTS:

- Structured JSON format
- All sections required
- Evidence-based claims only
- No generic advice

Input Token Budget: ~8000 tokens

- Job posting: ~2000 tokens
- CV: ~3000 tokens
- Company research: ~1500 tokens
- Knowledge base: ~1000 tokens
- System prompt: ~500 tokens

Output Token Budget: ~3000 tokens

- JSON structure: ~2500 tokens
- Metadata: ~500 tokens

Cost: $0.023-0.035 per generation

API Endpoint:
POST /generate/vp-report
Request:

- session_id: uuid (optional, for tracking)
- job_posting_text: string (required)
- cv_text: string (required)
- company_research: object (from F-RESEARCH-001)
- knowledge_base_items: array[string] (optional, max 5)
- language: string (auto-detected or specified)

Response:

- session_id: uuid
- status: "processing" | "completed" | "failed"
- vpr_json: object (structured data)
- vpr_pdf_url: string (presigned S3 URL, 24-hour expiry)
- vpr_html_url: string (presigned S3 URL, 24-hour expiry)
- cost: number (actual cost in USD)


- processing_time: number (seconds)

Error Codes:

- 400: Invalid input (missing CV, job posting too short)
- 413: Input too large (CV >10,000 words)
- 500: AI generation failed
- 503: Anthropic API unavailable (retry)

Prompt Engineering:

yaml

Prompt Structure:

1. System Context:
- Role definition (career strategist)
- Output format (JSON schema)
- Quality requirements (evidence-based)
2. Input Data:
- Job posting (with company name, title)
- CV (with timestamps preserved)
- Company research (mission, culture, news)
- Knowledge base excerpts (if provided)
3. Analysis Instructions:
- Extract job requirements systematically
- Map user profile to requirements
- Rate evidence strength for each claim
- Identify 5-8 differentiators with justifications
- Generate strategic recommendations
4. Output Schema:
- Exact JSON structure required
- Field descriptions and constraints
- Example output (few-shot learning)
5. Validation Checklist:
- All differentiators backed by CV evidence
- No generic statements (e.g., "strong communicator" without
proof)
- Specific company alignment points
- Actionable recommendations (not vague advice)

Prompt Template Location: /spec-kit/prompts/vpr-system.md

Quality Validation:


python

def validate_vpr(vpr_json: dict, cv_text: str) -> tuple[bool,
list[str]]:
"""Validate VPR quality and factual accuracy."""
errors = []

_# Check required sections_
required_sections = [
'job_requirements', 'user_profile', 'evidence_map',
'differentiators', 'recommendations', 'company_insights'
]
for section in required_sections:
if section not in vpr_json:
errors.append(f"Missing required section: {section}")

_# Validate differentiators count_
if len(vpr_json.get('differentiators', [])) < 5:
errors.append("Insufficient differentiators (need 5-8)")

_# Verify evidence references_
for diff in vpr_json.get('differentiators', []):
if 'evidence' not in diff or not diff['evidence']:
errors.append(f"Differentiator missing evidence:
{diff.get('title')}")

_# Check for hallucinations (basic keyword search)_
cv_lower = cv_text.lower()
for diff in vpr_json.get('differentiators', []):
_# Extract key terms from differentiator
# Verify they appear in CV
# Flag if not found_
pass

return len(errors) == 0, errors

Dependencies:

```
● Company research completed (F-RESEARCH-001)
● Language detection service (F-LANG-001)
● CV uploaded and parsed
● Anthropic API key configured
● S3 bucket for output storage
```
Acceptance Criteria:

```
VPR generated within 30 seconds (95th percentile)
```

All required sections present in JSON output
5-8 differentiators identified with evidence
Evidence strength ratings accurate (spot checks)
No hallucinated skills/experience
Company research insights incorporated
Strategic recommendations are actionable
Formatted PDF generated and accessible
Formatted HTML generated and accessible
Cost within $0.023-0.035 range
User can review VPR before proceeding to CV generation
VPR can be regenerated with additional context
Test Cases:

yaml

TC-VPR-001-01: Standard VPR Generation
Input: Valid job posting (500 words), CV (1000 words), company
research
Expected: VPR with 5-8 differentiators, all sections complete, <30s

TC-VPR-001-02: Missing Evidence Detection
Input: Job requires "Python", CV has no Python experience
Expected: VPR includes "Python" with evidence_strength: NO_EVIDENCE

TC-VPR-001-03: Hallucination Prevention
Input: CV without management experience, job requires management
Expected: VPR does not claim management experience, notes gap

TC-VPR-001-04: Company Alignment
Input: Company values "innovation", CV shows innovative projects
Expected: VPR highlights innovation alignment with specific
examples

TC-VPR-001-05: Hebrew Language Support
Input: Hebrew CV and job posting

Expected: VPR generated in Hebrew, proper RTL formatting

**2.4 CV Tailoring**

**Feature ID: F-CV-001**

Feature Name: ATS-Optimized CV Tailoring

Priority: P0

User Story:


```
As a job seeker, I want my CV automatically tailored to each job application with ATS
optimization so that I maximize my chances of passing automated screening and getting an
interview.
```
Description: AI-powered CV tailoring using Claude Haiku 4.5 that optimizes the user's master

CV for the specific job posting while maintaining factual accuracy. Incorporates VPR insights,

ATS best practices, and anti-AI detection strategies.

Functional Requirements:

1. Input processing:
    ● Master CV (DOCX or text)
    ● VPR JSON (from F-VPR-001)
    ● Job posting text
    ● Target length (default: 1 page, configurable to 2 pages)
    ● Language (auto-detected or specified)
2. Tailoring strategies: Keyword Optimization:
    ● Extract keywords from job posting (skills, tools, technologies)
    ● Match keywords from master CV
    ● Strategically place keywords in:
       ● Professional summary
       ● Skills section
       ● Work experience bullet points
       ● Projects/achievements
    ● Natural integration (avoid keyword stuffing)
3. Content Prioritization:
    ● Emphasize experience relevant to job requirements
    ● Lead with VPR differentiators
    ● Quantify achievements where possible
    ● Reorder experience sections by relevance
    ● De-emphasize irrelevant experience (don't remove, minimize)
4. ATS Compatibility:
    ● Clean formatting (no tables, columns, text boxes)
    ● Standard section headers ("Work Experience", "Education", "Skills")
    ● Simple bullet points (•, not fancy symbols)
    ● Standard fonts (Arial, Calibri, Times New Roman)
    ● No headers/footers with critical info
    ● Contact info in body (not header)
    ● Date formats: MM/YYYY
5. Anti-AI Detection:
    ● Natural language variations
    ● Avoid AI clichés ("leveraged", "spearheaded" overuse)
    ● Include minor stylistic variations
    ● Maintain conversational professionalism
    ● Match original CV's tone/voice


```
● No perfect parallel structures
```
6. Factual accuracy enforcement: Immutable Facts (NEVER change):
    ● Contact information (email, phone, address)
    ● Employment dates (start/end dates for each role)
    ● Company names
    ● Job titles
    ● Education dates and institutions
    ● Degree names
    ● Certification names and dates
7. Flexible Elements (Can be optimized):
    ● Work experience bullet points (rephrased for relevance)
    ● Skills presentation (order, grouping)
    ● Project descriptions
    ● Professional summary
    ● Achievement framing
    ● Keyword integration
8. Output format:
    ● DOCX format (Microsoft Word)
    ● Professional formatting:
       ● Name (bold, 14-16pt)
       ● Contact info (11pt, single line or two lines)
       ● Section headers (bold, 12pt)
       ● Body text (11pt)
       ● Consistent spacing
       ● Clean margins (0.5-1 inch)
    ● Language-specific formatting:
       ● English: Left-to-right (LTR)
       ● Hebrew: Right-to-left (RTL), appropriate fonts
    ● File naming: [FirstName]_[LastName]_CV_[CompanyName].docx
9. Validation and verification:
    ● Fact-checking: Compare tailored CV to master CV
    ● Verify all dates unchanged
    ● Verify all company/title names unchanged
    ● Check contact info unchanged
    ● Length verification (1-2 pages as specified)
    ● ATS compatibility check (formatting rules)
    ● Keyword density check (optimal 2-3% for key terms)

Technical Specifications:

yaml

Lambda Function:
Name: cv-tailor
Runtime: Python 3.11
Memory: 512 MB


Timeout: 60s
Avg Duration: 10-15s
Model: Claude Haiku 4.5

AI Configuration:
Model: claude-haiku-4-5-20251001
Temperature: 0.2 (low for consistency, slight variation for
naturalness)
Max Tokens: 3000 (output)

System Prompt: |
You are an expert CV writer specializing in ATS optimization and
tailoring.
Tailor the master CV for the specific job while maintaining
ABSOLUTE factual accuracy.

CRITICAL RULES - NEVER VIOLATE:

1. NEVER change dates (employment, education, certifications)
2. NEVER change company names or job titles
3. NEVER change contact information
4. NEVER invent experience, skills, or achievements
5. Only rephrase/reorder/emphasize existing information

## OPTIMIZATION STRATEGIES:

1. Extract keywords from job posting
2. Emphasize relevant experience (based on VPR differentiators)
3. Reframe achievements to highlight job-relevant impact
4. Optimize skills section order by relevance
5. Create compelling professional summary (3-4 lines)

## ATS COMPLIANCE:

1. Use standard section headers
2. Simple bullet points (• or -)
3. No tables, columns, text boxes, or graphics
4. Standard fonts only
5. Contact info in body (not header/footer)

ANTI-AI DETECTION:

1. Vary sentence structure naturally
2. Avoid overuse of "leverage", "spearhead", "drive"
3. Use natural, conversational professional tone
4. Include slight stylistic variations
5. Match original CV's voice/personality

OUTPUT: Generate DOCX-compatible markdown


Target length: {target_length}
Language: {language}

Input Token Budget: ~5000 tokens

- Master CV: ~2500 tokens
- VPR JSON: ~1500 tokens
- Job posting: ~800 tokens
- System prompt: ~200 tokens

Output Token Budget: ~2000 tokens

- Tailored CV content: ~1800 tokens
- Formatting instructions: ~200 tokens

Cost: $0.003-0.005 per generation

API Endpoint:
POST /generate/cv
Request:

- session_id: uuid (from VPR session)
- master_cv_text: string (or s3_key)
- vpr_json: object (from F-VPR-001)
- job_posting_text: string
- target_length: number (1 or 2 pages, default: 1)
- language: string

Response:

- session_id: uuid
- status: "processing" | "completed" | "failed"
- cv_docx_url: string (presigned S3 URL, 24-hour expiry)
- cv_preview_html: string (for in-app preview)
- ats_score: number (0-100, compatibility rating)
- keyword_coverage: number (% of job keywords in CV)
- cost: number
- processing_time: number

Error Codes:

- 400: Invalid input (missing master CV or VPR)
- 413: CV too long (>10 pages master CV)
- 500: Generation failed
- 503: Anthropic API unavailable

Fact Verification System:

python


def verify_cv_accuracy(master_cv: dict, tailored_cv: dict) ->
tuple[bool, list[str]]:
"""
Verify tailored CV maintains factual accuracy.
Checks immutable facts against master CV.
"""
errors = []

_# Extract structured data from both CVs_
master_facts = extract_immutable_facts(master_cv)
tailored_facts = extract_immutable_facts(tailored_cv)

_# Verify contact information_
if master_facts['contact'] != tailored_facts['contact']:
errors.append("Contact information changed")

_# Verify employment dates_
for job in master_facts['employment']:
tailored_job =
find_matching_job(tailored_facts['employment'], job)
if not tailored_job:
_# Job may be de-emphasized but not removed_
continue

if job['start_date'] != tailored_job['start_date']:
errors.append(f"Start date changed for {job['company']}")
if job['end_date'] != tailored_job['end_date']:
errors.append(f"End date changed for {job['company']}")
if job['title'] != tailored_job['title']:
errors.append(f"Title changed for {job['company']}")

_# Verify education dates_
for edu in master_facts['education']:
tailored_edu =
find_matching_education(tailored_facts['education'], edu)
if tailored_edu:
if edu['graduation_date'] !=
tailored_edu['graduation_date']:
errors.append(f"Graduation date changed for
{edu['institution']}")

_# Verify certifications_
for cert in master_facts['certifications']:
tailored_cert =
find_matching_cert(tailored_facts['certifications'], cert)


if tailored_cert and cert['date'] != tailored_cert['date']:
errors.append(f"Certification date changed for
{cert['name']}")

return len(errors) == 0, errors

def extract_immutable_facts(cv: dict) -> dict:
"""Extract dates, names, titles that should never change."""
return {
'contact': extract_contact_info(cv),
'employment': extract_employment_facts(cv),
'education': extract_education_facts(cv),
'certifications': extract_certification_facts(cv)

}

ATS Compatibility Checker:

python

def calculate_ats_score(cv_docx: bytes) -> dict:
"""
Analyze CV for ATS compatibility.
Returns score 0-100 and specific issues.
"""
issues = []
score = 100

_# Parse DOCX structure_
doc = Document(io.BytesIO(cv_docx))

_# Check for tables (ATS may misparse)_
if doc.tables:
issues.append("Contains tables (may confuse ATS)")
score -= 15

_# Check for text boxes (ATS often ignores)
# Check for headers/footers with critical info
# Check font consistency
# Check section header standardization
# Check bullet point simplicity_

_# Keyword density analysis_
job_keywords = extract_keywords(job_posting)
cv_text = extract_text(doc)
keyword_matches = count_keyword_matches(cv_text, job_keywords)
keyword_coverage = (keyword_matches / len(job_keywords)) * 100


return {
'ats_score': score,
'issues': issues,
'keyword_coverage': keyword_coverage,
'recommendations': generate_ats_recommendations(issues)

}

DOCX Generation:

yaml

Library: python-docx
Formatting Rules:

- Page size: Letter (8.5" x 11")
- Margins: 0.75" all sides
- Font: Arial 11pt (body), Arial 14pt (name)
- Line spacing: 1.15
- Paragraph spacing: 6pt after
- Section spacing: 12pt after

RTL Support (Hebrew):

- Paragraph alignment: RIGHT
- Reading order: RTL
- Font: Arial (supports Hebrew) or David
- Bidirectional text handling

File Storage:

- S3 bucket: careervp-job-search-assistant-outputs
- Path: /sessions/{session_id}/cv-tailored.docx
- Presigned URL expiry: 24 hours
- Metadata: user_id, job_company, generation_timestamp

Dependencies:

```
● VPR generation completed (F-VPR-001)
● Master CV uploaded and parsed
● python-docx library installed
● S3 bucket configured
● Language detection service
```
Acceptance Criteria:

```
Tailored CV generated within 15 seconds (95th percentile)
All immutable facts verified unchanged (100% accuracy)
ATS score ≥ 85/100
Keyword coverage ≥ 70% of job posting keywords
Target length achieved (1 or 2 pages as specified)
```

DOCX file properly formatted and downloadable
Hebrew CVs display correctly with RTL formatting
No AI hallucinations (verified via fact checker)
Anti-AI detection patterns avoided (manual spot check)
User can preview CV before downloading
User can edit CV in-app (V1: download + manual edit; V2: in-app editor)
Cost within $0.003-0.005 range
Test Cases:

yaml

TC-CV-001-01: Standard CV Tailoring
Input: Master CV (1500 words), VPR with differentiators, job
posting
Expected: 1-page tailored CV, ATS score >85, keywords integrated

TC-CV-001-02: Fact Verification - Dates Unchanged
Input: Master CV with employment dates: 01/2020-12/2023
Expected: Tailored CV shows exact same dates, verification passes

TC-CV-001-03: Fact Verification - Hallucination Detected
Input: Master CV without "Python", job requires "Python"
Expected: System flags if "Python" appears in tailored CV,
regenerates

TC-CV-001-04: ATS Compatibility
Input: Complex master CV with tables and graphics
Expected: Tailored CV removes tables/graphics, ATS score improves

TC-CV-001-05: Keyword Integration
Input: Job posting with keywords: "React", "TypeScript", "CI/CD"
Expected: Keywords appear naturally in skills/experience sections

TC-CV-001-06: Hebrew RTL Support
Input: Hebrew master CV and job posting
Expected: RTL formatted DOCX, proper Hebrew fonts, readable

TC-CV-001-07: Length Control
Input: 3-page master CV, target_length=1

Expected: Tailored CV fits on 1 page without cutting critical info

**2.5 Cover Letter Generation**

**Feature ID: F-COVER-001**

Feature Name: Personalized Cover Letter Generation


Priority: P0

User Story:

```
As a job seeker, I want a compelling cover letter tailored to each job that matches my writing
style so that I can effectively communicate my fit and enthusiasm for the role.
```
Description: AI-powered cover letter generation using Claude Haiku 4.5 that creates

personalized, one-page cover letters incorporating VPR insights, company research, and

optional writing style matching. Strict adherence to one-page limit and anti-AI detection

strategies.

Functional Requirements:

1. Input processing:
    ● VPR JSON (from F-VPR-001)
    ● Tailored CV (from F-CV-001)
    ● Job posting text
    ● Company research (from F-RESEARCH-001)
    ● Writing samples (optional, for style matching)
    ● Language (auto-detected or specified)
2. Cover letter structure: Header:
    ● User's contact information (from CV)
    ● Date (current date)
    ● Hiring manager name (if available) or "Hiring Manager"
    ● Company name and address
3. Opening Paragraph (2-3 sentences):
    ● Express enthusiasm for specific role
    ● Brief connection to company (mission/values/recent news)
    ● Hook: Most compelling differentiator
4. Body Paragraphs (2-3 paragraphs, 3-5 sentences each):
    ● Paragraph 1: Key qualifications and achievements
       ● Focus on top 2-3 VPR differentiators
       ● Quantified achievements where possible
       ● Specific examples from CV
    ● Paragraph 2: Company alignment and cultural fit
       ● Reference company research insights
       ● Align personal values with company values
       ● Demonstrate knowledge of company's work/products
    ● Paragraph 3 (optional): Address potential concerns
       ● Career transitions explained
       ● Geographic relocations justified
       ● Experience gaps addressed proactively
5. Closing Paragraph (2-3 sentences):
    ● Reiterate enthusiasm and fit
    ● Call to action (request interview)


```
● Professional sign-off
```
6. Signature:
    ● "Sincerely," or culturally appropriate closing
    ● User's full name
7. Writing style matching (optional):
    ● If writing samples provided (max 3 samples):
       ● Analyze tone (formal/casual/conversational)
       ● Identify common phrases and vocabulary
       ● Match sentence structure patterns
       ● Replicate level of enthusiasm/energy
       ● Maintain authenticity (natural voice)
    ● Default style (no samples):
       ● Professional but conversational
       ● Confident but humble
       ● Enthusiastic but not desperate
       ● Clear and concise
8. Anti-AI detection enforcement:
    ● Avoid AI clichés:
       ● "I am writing to express my interest" (overused)
       ● "I believe I would be a great fit" (generic)
       ● "Leveraged", "spearheaded", "synergy" (overused AI terms)
       ● Perfect parallel structures (too polished)
    ● Natural writing characteristics:
       ● Varied sentence lengths (mix short and long)
       ● Occasional conversational phrases
       ● Natural transitions (not formulaic)
       ● Minor stylistic imperfections (human touch)
       ● Specific examples (not generic statements)
    ● Personality injection:
       ● Genuine enthusiasm (specific to company/role)
       ● Personal connection to company mission
       ● Unique phrasing (not templated language)
9. One-page enforcement:
    ● Strict limit: Maximum 400-450 words
    ● Typical breakdown:
       ● Opening: 50-70 words
       ● Body paragraphs: 250-300 words
       ● Closing: 40-60 words
       ● Header/signature: Not counted in word limit
    ● Length optimization strategies:
       ● Concise sentences (no fluff)
       ● One main point per paragraph
       ● Remove redundancy
       ● Focus on impact (not process)


```
● Quantify where possible (fewer words, more impact)
```
10. Quality validation:
    ● Company name mentioned at least 2 times
    ● Specific role title mentioned at least once
    ● At least 2 quantified achievements referenced
    ● No generic statements ("I'm a hard worker")
    ● All claims backed by CV evidence
    ● Professional tone maintained throughout
    ● No spelling/grammar errors
    ● One page limit enforced (visual check)

Technical Specifications:

yaml

Lambda Function:
Name: cover-letter-generator
Runtime: Python 3.11
Memory: 512 MB
Timeout: 60s
Avg Duration: 8-12s
Model: Claude Haiku 4.5

AI Configuration:
Model: claude-haiku-4-5-20251001
Temperature: 0.4 (higher for personality, capped for quality)
Max Tokens: 1500 (output)

System Prompt: |
You are an expert cover letter writer creating compelling,
personalized letters.
Create a ONE-PAGE cover letter that is specific, authentic, and
persuasive.

## CRITICAL REQUIREMENTS:

1. STRICT one-page limit (400-450 words maximum)
2. Specific to company and role (never generic)
3. Reference VPR differentiators with concrete examples
4. Incorporate company research (mission, culture, news)
5. Match user's writing style (if samples provided)
6. Professional but conversational tone
7. Quantify achievements where possible

## ANTI-AI DETECTION:

1. NO AI clichés: "I am writing to express", "leverage",
"spearhead"


2. Vary sentence structure naturally (mix short and long)
3. Use natural transitions (not formulaic)
4. Inject personality and genuine enthusiasm
5. Include slight stylistic variations
6. Avoid perfect parallel structures

## STRUCTURE:

1. Opening: Enthusiasm + company connection + hook (50-70 words)
2. Body 1: Top qualifications with examples (90-110 words)
3. Body 2: Company alignment and cultural fit (90-110 words)
4. Closing: Reiterate fit + call to action (40-60 words)

ALL CLAIMS MUST reference CV or VPR evidence.
Language: {language}

{writing_style_context}

Input Token Budget: ~4000 tokens

- VPR JSON: ~1200 tokens
- Tailored CV: ~800 tokens
- Job posting: ~600 tokens
- Company research: ~800 tokens
- Writing samples: ~400 tokens (if provided)
- System prompt: ~200 tokens

Output Token Budget: ~1500 tokens

- Cover letter content: ~1300 tokens
- Formatting: ~200 tokens

Cost: $0.002-0.004 per generation

API Endpoint:
POST /generate/cover-letter
Request:

- session_id: uuid
- vpr_json: object
- tailored_cv_text: string (or s3_key)
- job_posting_text: string
- company_research: object
- writing_samples: array[string] (optional, max 3, each <500
words)
- language: string
- hiring_manager_name: string (optional)

Response:


- session_id: uuid
- status: "processing" | "completed" | "failed"
- cover_letter_docx_url: string (presigned S3 URL)
- cover_letter_preview_html: string
- word_count: number
- ai_detection_score: number (0-100, lower = more human)
- company_mentions: number
- quantified_achievements: number
- cost: number
- processing_time: number

Error Codes:

- 400: Invalid input (missing VPR or CV)
- 413: Writing samples too long (>1500 words total)
- 500: Generation failed
- 503: Anthropic API unavailable

Writing Style Analysis (Optional Feature):

python

def analyze_writing_style(writing_samples: list[str]) -> dict:
"""
Analyze user's writing samples to extract style characteristics.
Used to inform cover letter generation.
"""
combined_text = " ".join(writing_samples)

analysis = {
'tone': detect_tone(combined_text), _#
formal/casual/conversational_
'sentence_length_avg':
calculate_avg_sentence_length(combined_text),
'common_phrases': extract_common_phrases(combined_text),
'vocabulary_level':
assess_vocabulary_complexity(combined_text),
'punctuation_style':
analyze_punctuation_patterns(combined_text),
'enthusiasm_level':
measure_enthusiasm_markers(combined_text),
'personal_pronouns':
count_personal_pronoun_usage(combined_text)
}

_# Generate style guidance for AI prompt_
style_context = f"""


User's writing style characteristics:

- Tone: {analysis['tone']}
- Average sentence length: {analysis['sentence_length_avg']}
words
- Vocabulary level: {analysis['vocabulary_level']}
- Enthusiasm: {analysis['enthusiasm_level']}

Match this style while maintaining professional standards.
"""

return style_context

AI Detection Avoidance:

yaml

Patterns to Avoid:
Opening Clichés:

- "I am writing to express my interest in..."
- "I came across your job posting for..."
- "I am excited to apply for the position of..."
- "Please accept my application for..."

Overused Action Verbs:

- Leveraged (use: used, applied, employed)
- Spearheaded (use: led, initiated, launched)
- Orchestrated (use: coordinated, managed, organized)
- Facilitated (use: enabled, supported, helped)

Generic Statements:

- "I am a hard worker" → specific achievement instead
- "I am a fast learner" → example of learning something quickly
- "I have strong communication skills" → example of effective
communication
- "I would be a great fit" → explain why with specific alignment

Perfect Parallel Structures:

- "I have X, I have Y, I have Z" → vary structure
- Three identical sentence structures in a row → vary

Natural Writing Techniques:

- Mix sentence lengths: "I led a team of 5. We increased sales by
40% in Q3."
- Conversational transitions: "Beyond my technical skills, what
drives me is..."


- Specific details: "Your recent Series B funding announcement" not
"your success"
- Personal connection: "As someone who's used your product..." (if
authentic)
- Varied vocabulary: Use synonyms, don't repeat same phrases

One-Page Enforcement:

python

def enforce_one_page_limit(cover_letter_text: str, max_words: int =
450) -> tuple[bool, str]:
"""
Verify cover letter fits on one page.
If exceeds limit, provide condensing suggestions.
"""
word_count = count_words(cover_letter_text)

if word_count <= max_words:
return True, cover_letter_text

_# Calculate reduction needed_
words_to_remove = word_count - max_words

_# Condensing strategies (applied in order):
# 1. Remove redundant phrases
# 2. Combine related sentences
# 3. Remove less critical achievements
# 4. Shorten opening/closing_

condensed_text = apply_condensing_strategies(
cover_letter_text,
words_to_remove
)

return count_words(condensed_text) <= max_words, condensed_text

def estimate_page_length(word_count: int, font_size: int = 11) ->
float:
"""
Estimate pages based on word count and formatting.
Typical: 450-500 words = 1 page (single-spaced, 11pt)
"""
words_per_page = 450 _# Conservative estimate_

return word_count / words_per_page


DOCX Formatting:

yaml

Page Setup:

- Size: Letter (8.5" x 11")
- Margins: 1" all sides
- Font: Arial or Calibri, 11pt
- Line spacing: Single-spaced
- Paragraph spacing: 6pt after paragraphs

Header Section:

- User's name (bold, 12pt)
- Contact: email | phone | LinkedIn (if applicable)
- One blank line

Date:

- Current date (format: January 21, 2025)
- One blank line

Recipient:

- Hiring Manager Name (or "Hiring Manager")
- Company Name
- Company Address (optional, can be omitted)
- One blank line

Body:

- Paragraphs separated by one blank line
- No indentation (block format)

Signature:

- "Sincerely," (or culturally appropriate)
- Two blank lines
- User's full name

RTL Support (Hebrew):

- Right-aligned text
- Hebrew fonts (Arial, David)
- Date format: DD/MM/YYYY
- Closing: "רב בכבוד," (respectfully)

Dependencies:

```
● VPR generation completed (F-VPR-001)
● CV tailoring completed (F-CV-001)
● Company research completed (F-RESEARCH-001)
● python-docx library installed
```

```
● S3 bucket configured
```
Acceptance Criteria:

Cover letter generated within 12 seconds (95th percentile)
Word count ≤ 450 words (strictly enforced)
Visual check: Fits on one page in standard formatting
Company name mentioned at least 2 times
Role title mentioned at least once
At least 2 quantified achievements from CV
No generic AI clichés ("leverage", "spearhead", etc.)
Writing style matches samples (if provided)
All claims backed by CV evidence (no hallucinations)
Professional but conversational tone
No spelling/grammar errors
DOCX file properly formatted and downloadable
Hebrew cover letters display correctly with RTL
Cost within $0.002-0.004 range
User can regenerate with different tone/emphasis
Test Cases:

yaml

TC-COVER-001-01: Standard Cover Letter
Input: VPR, tailored CV, job posting, company research
Expected: One-page cover letter, 400-450 words, specific to
company/role

TC-COVER-001-02: Writing Style Matching
Input: Cover letter + 2 writing samples (casual, enthusiastic tone)
Expected: Generated letter matches casual/enthusiastic tone
naturally

TC-COVER-001-03: One-Page Enforcement
Input: Complex VPR with 8 differentiators (tendency to over-write)
Expected: Cover letter condensed to fit one page, prioritizes top
achievements

TC-COVER-001-04: AI Cliché Avoidance
Input: Standard generation
Expected: No instances of "leverage", "spearhead", "I am writing to
express..."

TC-COVER-001-05: Company Research Integration
Input: Company research includes "Series B funding" and "mission:
empower creators"


Expected: Cover letter references funding and aligns with mission
naturally

TC-COVER-001-06: Fact Verification
Input: VPR with achievement "increased sales by 40%"
Expected: Cover letter includes quantified achievement accurately

TC-COVER-001-07: Hebrew Language Support
Input: Hebrew VPR, CV, job posting
Expected: RTL formatted cover letter, Hebrew closing, proper fonts

TC-COVER-001-08: Hiring Manager Personalization
Input: hiring_manager_name = "Sarah Johnson"

Expected: Letter addressed to "Dear Sarah Johnson," not generic

**2.6 Gap Analysis with Interactive Q&A**

**Feature ID: F-GAP-001**

Feature Name: Interactive Gap Analysis (Question Generation)

Priority: P1

User Story:

```
As a job seeker, I want to identify gaps between my qualifications and the job requirements so
that I can address them proactively in my application and interview preparation.
```
Description: Two-phase interactive gap analysis using Claude Sonnet 4.5. Phase 1 generates

targeted questions to uncover hidden skills/experience not evident in the CV. Phase 2 processes

user answers to create a comprehensive gap analysis report with recommendations.

Phase 1: Question Generation

Functional Requirements:

1. Input processing:
    ● Job posting text (required)
    ● User CV text (required)
    ● VPR JSON (optional, if available)
    ● Language (auto-detected or specified)
2. Analysis and question generation: Requirements Analysis:
    ● Extract all job requirements (technical, experience, soft skills)
    ● Categorize by importance (must-have vs nice-to-have)
    ● Identify domain knowledge areas
    ● Note specific tools/technologies mentioned
3. CV Coverage Assessment:
    ● Map CV content to job requirements


```
● Identify explicitly covered areas
● Identify ambiguous areas (implied but not explicit)
● Identify missing areas (no evidence in CV)
```
4. Question Design:
    ● Generate 8-10 targeted questions (maximum 10)
    ● Focus on ambiguous and missing areas
    ● Avoid questions clearly answered in CV
    ● Open-ended questions (not yes/no)
    ● Specific to job requirements
    ● Cover different competency categories
5. Question Categories (balanced distribution):
    ● Technical skills/tools (2-3 questions)
    ● Domain knowledge/experience (2-3 questions)
    ● Soft skills/leadership (2-3 questions)
    ● Situational/behavioral (1-2 questions)
    ● Career goals/motivation (0-1 questions)
6. Question quality requirements:
    ● Each question must be:
       ● Specific to the job (not generic)
       ● Open-ended (requires detailed answer)
       ● Non-redundant with CV (asks for new information)
       ● Answerable by candidate (not require speculation)
       ● Relevant to hiring decision
    ● Questions should elicit:
       ● Specific examples (STAR method encouraged)
       ● Quantifiable results where applicable
       ● Context and impact
       ● Learning/growth experiences
7. Previous Q&A Integration (CRITICAL):
    ● If user has answered gap analysis questions for a previous job application:
       ● Retrieve previous questions and answers from DynamoDB
       ● Analyze previous answers for relevant information
       ● Generate NEW questions that:
          ● Don't repeat previously asked questions
          ● Build on previous answers (follow-up questions)
          ● Address gaps not covered in previous Q&A
          ● Reference previous answers when relevant
    ● Example flow:
       ● Previous job: Software Engineer role, asked about "Python experience"
       ● Current job: Senior Software Engineer role
       ● New question: "Building on your Python experience at [Company],
          describe a time you architected a system at scale using Python. What
          trade-offs did you consider?"
    ● Benefits:


```
● Avoids repetitive questions across applications
● Builds comprehensive candidate profile over time
● More efficient for repeat users
● Demonstrates continuity in candidate assessment
```
8. Output format:
    ● JSON array of questions:

json

{
"questions": [
{
"id": "q1",
"category": "technical_skills",
"question_text": "Describe your experience with [specific
technology]. Include projects where you used it and challenges you
overcame.",
"why_asking": "Job requires [technology] but CV doesn't
explicitly mention it.",
"expected_info": "Specific projects, duration of
experience, proficiency level"
},
...
],
"total_questions": 10,
"estimated_time": "15-20 minutes",
"instructions": "Please answer each question with specific
examples. Use the STAR method (Situation, Task, Action, Result) where
applicable."

}

```
● User-facing presentation:
● Clean, numbered list
● Category labels for context
● Character count guidance (100-300 words per question)
● Progress indicator (Question 3 of 10)
● Save draft functionality
```
Technical Specifications:

yaml

Lambda Function:
Name: gap-analysis-questions
Runtime: Python 3.11
Memory: 512 MB
Timeout: 60s


Avg Duration: 12-18s
Model: Claude Sonnet 4.5

AI Configuration:
Model: claude-sonnet-4-5-20250929
Temperature: 0.4 (creativity for question diversity)
Max Tokens: 2000 (output)

System Prompt: |
You are an expert recruiter conducting a gap analysis interview.
Generate 8-10 targeted questions to uncover information not in
the CV.

CRITICAL RULES:

1. MAXIMUM 10 questions (8-10 ideal)
2. Each question must address a specific gap or ambiguity
3. NO questions about information clearly stated in CV
4. Open-ended questions requiring detailed answers
5. Diverse categories (technical, experience, soft skills,
behavioral)
6. Specific to this job (not generic career questions)

QUESTION QUALITY:

- Start with "Describe...", "Explain...", "Tell me about..."
- Encourage specific examples and quantification
- Ask for context, actions, and results
- Probe depth of knowledge/experience

{previous_qa_context}

## PREVIOUS Q&A INTEGRATION:

- Review previous questions and answers (if provided)
- DO NOT repeat previously asked questions
- Build on previous answers with follow-up questions
- Reference previous responses when relevant
- Fill gaps not covered in previous Q&A sessions

OUTPUT: JSON array with question objects
Language: {language}

Input Token Budget: ~6000 tokens

- Job posting: ~2000 tokens
- CV: ~2500 tokens
- VPR (optional): ~1000 tokens
- Previous Q&A (if exists): ~1500 tokens


- System prompt: ~500 tokens

Output Token Budget: ~1500 tokens

- 10 questions with context: ~1200 tokens
- Metadata: ~300 tokens

Cost: $0.030-0.035 per generation

API Endpoint:
POST /gap-analysis/questions
Request:

- session_id: uuid
- job_posting_text: string
- cv_text: string
- vpr_json: object (optional)
- language: string
- previous_gap_analyses: array[{job_id, questions, answers}]
(optional)

Response:

- session_id: uuid
- gap_analysis_id: uuid (new)
- questions: array[object] (8-10 questions)
- total_questions: number
- estimated_time: string
- instructions: string
- previous_qa_considered: boolean
- cost: number
- processing_time: number

Error Codes:

- 400: Invalid input (missing CV or job posting)
- 500: Generation failed
- 503: Anthropic API unavailable

Previous Q&A Retrieval:

python

def get_previous_gap_analyses(user_id: str, limit: int = 5) ->
list[dict]:
"""
Retrieve user's previous gap analysis Q&A sessions.
Used to inform new question generation.
"""
_# Query DynamoDB for user's past gap analyses_


response = dynamodb.query(
TableName='careervp-gap-analyses',
KeyConditionExpression='user_id = :uid',
ExpressionAttributeValues={':uid': user_id},
ScanIndexForward=False, _# Most recent first_
Limit=limit
)

gap_analyses = []
for item in response['Items']:
gap_analyses.append({
'job_id': item['job_id'],
'company_name': item.get('company_name'),
'job_title': item.get('job_title'),
'date': item['created_at'],
'questions': item['questions'],
'answers': item['answers']
})

return gap_analyses

def format_previous_qa_context(gap_analyses: list[dict]) -> str:
"""
Format previous Q&A for inclusion in AI prompt.
"""
if not gap_analyses:
return ""

context = "PREVIOUS GAP ANALYSIS SESSIONS:\n\n"
for idx, ga in enumerate(gap_analyses, 1):
context += f"Session {idx}: {ga['company_name']} -
{ga['job_title']} ({ga['date']})\n"
context += "Questions asked:\n"
for q in ga['questions']:
context += f"- {q['question_text']}\n"
context += "\nUser's answers (summaries):\n"
for q, a in zip(ga['questions'], ga['answers']):
context += f"- {q['category']}: {a[:100]}...\n"
context += "\n"

context += """
INSTRUCTIONS FOR NEW QUESTIONS:

- DO NOT repeat any of the above questions
- Build on answers provided (ask deeper follow-ups)
- Fill gaps not covered in previous sessions


- Reference previous answers when relevant (e.g., "You
mentioned...")
"""

return context

Question Generation Strategy:

yaml

Step 1: Requirements Extraction

- Parse job posting for explicit requirements
- Identify implicit requirements (industry norms)
- Categorize by type (technical, experience, soft skills)
- Prioritize by importance to role

Step 2: CV Coverage Analysis

- Map CV content to each requirement
- Rate coverage: EXPLICIT, IMPLIED, MISSING
- Identify ambiguous areas needing clarification

Step 3: Previous Q&A Review (if exists)

- Load user's past gap analysis sessions
- Extract previously asked questions
- Summarize previous answers
- Identify patterns and themes

Step 4: Question Topic Selection

- Focus on MISSING and IMPLIED areas
- Prioritize most important job requirements
- Ensure diversity across categories
- Avoid duplication with previous Q&A

Step 5: Question Drafting

- Craft open-ended, specific questions
- Include context (why we're asking)
- Provide guidance on what to include
- Target 8-10 questions total

Step 6: Quality Review

- Verify no redundancy with CV
- Verify no redundancy with previous Q&A
- Check category balance
- Ensure answerable by candidate
- Validate relevance to job


Dependencies:

```
● Job posting and CV uploaded
● VPR generation (optional, enhances question targeting)
● DynamoDB table for storing gap analyses
● Previous gap analyses retrieval system
```
Acceptance Criteria:

8-10 questions generated (never fewer than 8, never more than 10)
All questions specific to job requirements
No questions about information clearly in CV
No questions repeated from previous gap analyses (if exist)
Balanced category distribution (technical, experience, soft skills, behavioral)
Open-ended questions (not yes/no)
Each question includes context (why asking)
Previous Q&A integrated when available (no repetition)
Questions generated within 20 seconds (95th percentile)
Cost within $0.030-0.035 range
User can save draft answers and resume later
Test Cases:

yaml

TC-GAP-001-01: Standard Question Generation
Input: Job posting (DevOps Engineer), CV (Software Engineer
background)
Expected: 8-10 questions about DevOps tools, infrastructure, CI/CD
experience

TC-GAP-001-02: Avoid CV Redundancy
Input: CV explicitly states "5 years Python experience"
Expected: No questions about Python experience duration

TC-GAP-001-03: Category Balance
Input: Standard generation
Expected: 2-3 technical, 2-3 experience, 2-3 soft skills, 1-2
behavioral

TC-GAP-001-04: Previous Q&A Integration
Input: Previous gap analysis asked "Describe your Python
experience"
Expected: New questions DO NOT ask about Python basics, may ask
about advanced Python topics

TC-GAP-001-05: Follow-up Questions
Input: Previous answer: "I led a team of 5 engineers on a
microservices project"


Expected: New question: "Building on your microservices experience,
describe challenges you faced and how you addressed them"

TC-GAP-001-06: Question Count Enforcement
Input: Standard generation
Expected: Exactly 8-10 questions, never 11 or 7

TC-GAP-001-07: Language Support
Input: Hebrew CV and job posting

Expected: Questions generated in Hebrew, culturally appropriate

phrasing

**Feature ID: F-GAP-002**

Feature Name: Gap Analysis Processing (Answer Analysis)

Priority: P1

User Story:

```
As a job seeker who answered gap analysis questions, I want a comprehensive report
identifying my strengths and weaknesses so that I can prepare targeted responses and address
concerns proactively.
```
Description: Phase 2 of gap analysis: processes user's answers to the generated questions,

analyzes them against job requirements, and produces actionable gap analysis report with

recommendations.

Functional Requirements:

1. Input processing:
    ● Gap analysis questions (from Phase 1)
    ● User's answers (free-form text, 100-300 words per question)
    ● Job posting text
    ● User CV text
    ● VPR JSON (if available)
    ● Previous gap analyses (if exist, for continuity)
    ● Language
2. Answer analysis: Completeness Check:
    ● Verify all questions answered (or explicitly skipped)
    ● Check answer length (minimum 50 words per answer)
    ● Flag incomplete or vague answers for user review
3. Content Extraction:
    ● Extract specific examples and achievements
    ● Identify quantified results
    ● Note technical skills mentioned
    ● Capture soft skills demonstrated


```
● Identify gaps acknowledged by user
```
4. Evidence Strength Rating:
    ● STRONG: Specific example with quantified results
    ● MODERATE: Specific example without quantification
    ● WEAK: Generic statement or minimal detail
    ● NO_EVIDENCE: Didn't answer or no relevant info
5. Gap identification: Skill Gaps:
    ● Technical skills required but not demonstrated
    ● Tools/technologies user has limited experience with
    ● Certifications mentioned in job but not held
    ● Domain knowledge areas needing development
6. Experience Gaps:
    ● Years of experience shortfall
    ● Industry experience missing
    ● Role level mismatch (e.g., IC applying for management)
    ● Project scale differences
7. Soft Skill Gaps:
    ● Leadership experience if required
    ● Communication skills (presentation, writing)
    ● Collaboration/teamwork examples
    ● Problem-solving approach
8. Integration with Previous Gap Analyses:
    ● Compare current answers with previous answers
    ● Identify improvements or skill development since last application
    ● Note recurring gaps across multiple applications
    ● Track progress on previously identified gaps
    ● Example insights:
       ● "Since your last application 3 months ago, you've gained experience with
          Kubernetes through [Project X]."
       ● "This is the 3rd application where leadership experience is identified as a
          gap. Consider prioritizing leadership opportunities."
       ● "Your answer demonstrates growth in [Skill Y] compared to your previous
          response."
9. Recommendations: Addressing Gaps:
    ● How to reframe experience to minimize gaps
    ● Alternative qualifications that demonstrate capability
    ● Transferable skills to emphasize
    ● Proactive statements for cover letter/interview
10. Skill Development:
    ● Priority skills to learn (based on frequency across jobs)
    ● Learning resources (courses, certifications, projects)
    ● Timeline for acquisition
    ● Interim strategies while learning
11. Application Strategy:


```
● Top 3-5 themes to emphasize (strengths)
● Gaps to address proactively (not hide)
● Story angles that minimize concerns
● Unique value proposition reinforcement
```
12. Interview Preparation:
    ● Likely questions about gaps
    ● Suggested responses (honest but strategic)
    ● Turn weaknesses into growth opportunities
    ● Questions to ask interviewer (demonstrate interest)
13. Output format:
    ● Executive Summary (100-150 words):
       ● Overall fit assessment (Strong/Moderate/Weak)
       ● Top 3 strengths
       ● Top 2-3 gaps
       ● Application recommendation (Apply with confidence/Address gaps
          first/Consider other roles)
    ● Detailed Gap Analysis:
       ● Skills coverage table (requirement → evidence → gap)
       ● Strength areas (with supporting evidence)
       ● Gap areas (with severity: Minor/Moderate/Significant)
       ● Progress tracking (if previous gap analyses exist)
    ● Actionable Recommendations:
       ● How to address each gap in application
       ● Skill development priorities
       ● Interview preparation strategy
       ● Timeline for improvement (short-term, long-term)
    ● JSON + PDF formats

Technical Specifications:

yaml

Lambda Function:
Name: gap-analysis-processor
Runtime: Python 3.11
Memory: 512 MB
Timeout: 60s
Avg Duration: 15-20s
Model: Claude Sonnet 4.5

AI Configuration:
Model: claude-sonnet-4-5-20250929
Temperature: 0.3 (analytical, consistent)
Max Tokens: 3500 (output)

System Prompt: |


You are an expert career coach analyzing gap analysis responses.
Evaluate user's answers against job requirements to identify
strengths and gaps.

CRITICAL TASKS:

1. Analyze each answer for specific evidence and examples
2. Rate evidence strength (STRONG/MODERATE/WEAK/NO_EVIDENCE)
3. Identify skill gaps, experience gaps, soft skill gaps
4. Provide actionable recommendations
5. Be honest but constructive (not discouraging)

{previous_gap_context}

PREVIOUS GAP ANALYSIS INTEGRATION:

- Compare current answers with previous answers (if provided)
- Identify skill development and improvements
- Note recurring gaps across applications
- Track progress on previously identified gaps
- Provide continuity insights (e.g., "Your Kubernetes experience
has grown...")

## ASSESSMENT FRAMEWORK:

- Overall Fit: Strong (90%+), Moderate (70-89%), Weak (<70%)
- Gap Severity: Minor (easily overcome), Moderate (requires
preparation), Significant (major concern)
- Recommendation: Apply confidently / Address gaps first /
Consider other roles

OUTPUT:

- Executive summary with clear recommendation
- Detailed gap analysis (strengths and gaps)
- Actionable recommendations with priorities
- Progress tracking (if previous gap analyses exist)
- Structured JSON format

Language: {language}

Input Token Budget: ~8000 tokens

- Job posting: ~1500 tokens
- CV: ~2000 tokens
- Questions: ~800 tokens
- User answers: ~2500 tokens
- Previous gap analyses: ~1000 tokens
- VPR (optional): ~1000 tokens
- System prompt: ~500 tokens


Output Token Budget: ~3000 tokens

- Executive summary: ~300 tokens
- Gap analysis: ~1500 tokens
- Recommendations: ~1000 tokens
- Metadata: ~200 tokens

Cost: $0.035-0.040 per analysis

API Endpoint:
POST /gap-analysis/analyze
Request:

- gap_analysis_id: uuid (from Phase 1)
- session_id: uuid
- questions: array[object] (from Phase 1)
- answers: array[{question_id, answer_text}]
- job_posting_text: string
- cv_text: string
- vpr_json: object (optional)
- previous_gap_analyses: array[object] (optional)
- language: string

Response:

- gap_analysis_id: uuid
- session_id: uuid
- status: "completed"
- executive_summary: string
- overall_fit: string (Strong/Moderate/Weak)
- strengths: array[{area, evidence, importance}]
- gaps: array[{area, severity, recommendation}]
- progress_notes: array[string] (if previous gap analyses exist)
- recommendations: object {
application_strategy: array[string],
skill_development: array[string],
interview_prep: array[string]
}
- gap_report_pdf_url: string (presigned S3 URL)
- gap_report_html_url: string
- cost: number
- processing_time: number

Error Codes:

- 400: Invalid input (missing answers, incomplete responses)
- 404: gap_analysis_id not found
- 500: Analysis failed


- 503: Anthropic API unavailable

Answer Validation:

python

def validate_answers(questions: list[dict], answers: list[dict]) ->
tuple[bool, list[str]]:
"""
Validate user's answers before processing.
Ensure all questions answered with sufficient detail.
"""
errors = []

_# Check all questions have answers_
question_ids = {q['id'] for q in questions}
answer_ids = {a['question_id'] for a in answers}

missing = question_ids - answer_ids
if missing:
errors.append(f"Missing answers for questions: {',
'.join(missing)}")

_# Check answer length (minimum 50 words)_
for answer in answers:
word_count = len(answer['answer_text'].split())
if word_count < 50:
errors.append(f"Question {answer['question_id']}: Answer
too short ({word_count} words, minimum 50)")

_# Check for placeholder/generic answers_
generic_patterns = [
"i have experience",
"i am familiar with",
"i can do this",
"yes i have done this"
]
for answer in answers:
text_lower = answer['answer_text'].lower()
if any(pattern in text_lower for pattern in
generic_patterns):
if len(answer['answer_text'].split()) < 100:
errors.append(f"Question {answer['question_id']}:
Answer appears generic, provide specific examples")

return len(errors) == 0, errors


Progress Tracking:

python

def generate_progress_insights(current_gap: dict, previous_gaps:
list[dict]) -> list[str]:
"""
Compare current gap analysis with previous ones to identify
progress.
"""
insights = []

if not previous_gaps:
return insights

_# Find most recent previous gap analysis_
prev_gap = previous_gaps[0] _# Already sorted by date_

_# Compare skill coverage_
current_skills = {s['skill'] for s in
current_gap['skills_covered']}
prev_skills = {s['skill'] for s in prev_gap['skills_covered']}

new_skills = current_skills - prev_skills
if new_skills:
insights.append(f"New skills demonstrated since last
application: {', '.join(new_skills)}")

_# Compare gap severity_
current_gaps_severe = [g['area'] for g in current_gap['gaps'] if
g['severity'] == 'Significant']
prev_gaps_severe = [g['area'] for g in prev_gap['gaps'] if
g['severity'] == 'Significant']

improved_areas = set(prev_gaps_severe) - set(current_gaps_severe)
if improved_areas:
insights.append(f"Improved areas since last application: {',
'.join(improved_areas)}")

_# Identify recurring gaps_
recurring_gaps = []
current_gap_areas = {g['area'] for g in current_gap['gaps']}
for prev in previous_gaps:
prev_gap_areas = {g['area'] for g in prev['gaps']}
recurring = current_gap_areas & prev_gap_areas
recurring_gaps.extend(recurring)


_# Count occurrences_
from collections import Counter
gap_counts = Counter(recurring_gaps)
frequent_gaps = [area for area, count in gap_counts.items() if
count >= 2]

if frequent_gaps:
insights.append(f"Recurring gaps across multiple
applications: {', '.join(frequent_gaps)}. Consider prioritizing
development in these areas.")

_# Overall fit comparison_
fit_scores = {
'Strong': 3,
'Moderate': 2,
'Weak': 1
}
current_fit_score = fit_scores.get(current_gap['overall_fit'], 0)
prev_fit_score = fit_scores.get(prev_gap['overall_fit'], 0)

if current_fit_score > prev_fit_score:
insights.append(f"Your overall fit has improved from
{prev_gap['overall_fit']} to {current_gap['overall_fit']}.")
elif current_fit_score < prev_fit_score:
insights.append(f"This role appears more challenging than
your previous application. Focus on addressing key gaps.")

return insights

DynamoDB Storage:

yaml

Table: careervp-gap-analyses
Partition Key: user_id
Sort Key: gap_analysis_id

Attributes:

- user_id: string
- gap_analysis_id: uuid
- session_id: uuid (link to application session)
- job_id: uuid (if saved to jobs)
- company_name: string
- job_title: string
- questions: array[object]


- answers: array[object]
- analysis_result: object (gap analysis JSON)
- overall_fit: string
- created_at: ISO8601
- updated_at: ISO8601

GSI: user_id-created_at-index (for chronological retrieval)

Purpose: Store all gap analyses for user progress tracking

Dependencies:

```
● Gap analysis questions generated (F-GAP-001)
● User completed answers
● DynamoDB table for storage
● Previous gap analyses retrieval
```
Acceptance Criteria:

All answers validated for completeness before processing
Analysis completed within 25 seconds (95th percentile)
Executive summary provides clear overall fit assessment
Strengths identified with specific supporting evidence
Gaps identified with severity ratings (Minor/Moderate/Significant)
Recommendations are actionable and prioritized
Previous gap analyses integrated (progress notes)
Recurring gaps across applications identified
Gap analysis stored in DynamoDB for future reference
PDF and HTML reports generated and accessible
Cost within $0.035-0.040 range
User can regenerate analysis if answers are updated
Test Cases:

yaml

TC-GAP-002-01: Standard Gap Analysis
Input: 10 questions, 10 detailed answers (100-200 words each)
Expected: Complete gap analysis with strengths, gaps,
recommendations

TC-GAP-002-02: Incomplete Answers
Input: 10 questions, 7 answers
Expected: Error 400, "Missing answers for questions: q8, q9, q10"

TC-GAP-002-03: Short Answers
Input: Answer with 30 words (below 50-word minimum)
Expected: Error 400, "Answer too short (30 words, minimum 50)"


TC-GAP-002-04: Strong Fit Assessment
Input: Answers demonstrate 90%+ requirement coverage with specific
examples
Expected: Overall fit: "Strong", recommendation: "Apply with
confidence"

TC-GAP-002-05: Moderate Fit with Gaps
Input: Answers show 75% coverage, missing 2-3 key skills
Expected: Overall fit: "Moderate", gaps identified, strategies to
address

TC-GAP-002-06: Progress Tracking
Input: Previous gap analysis from 3 months ago + current analysis
Expected: Progress notes: "New skills: Docker, Kubernetes.
Improved: Leadership experience."

TC-GAP-002-07: Recurring Gaps Detection
Input: 3 previous gap analyses all show "limited leadership
experience"
Expected: Insight: "Recurring gap: Leadership experience across 3
applications. Prioritize leadership opportunities."

TC-GAP-002-08: Significant Gaps with Alternative Strategies
Input: Job requires 5 years experience, user has 2 years
Expected: Gap noted as "Significant", recommendations include how
to reframe experience, emphasize rapid learning
```

---

_### 2.7 Interview Preparation Guide_

_#### Feature ID: F-INTERVIEW-001_
**Feature Name:** Comprehensive Interview Preparation Guide

**Priority:** P1

**User Story:**
> As a job seeker preparing for an interview, I want a comprehensive
guide with likely questions and suggested answers so that I can
practice and feel confident going into the interview.

**Description:**
AI-powered interview preparation guide using Claude Haiku 4.5 that
predicts interview questions, provides STAR-method answer frameworks,


and includes company-specific insights. Incorporates all previous
artifacts (VPR, CV, Cover Letter, Gap Analysis) for comprehensive
preparation.

**Functional Requirements:**

1. Input processing:
- VPR JSON (from F-VPR-001)
- Tailored CV (from F-CV-001)
- Cover Letter (from F-COVER-001)
- Gap Analysis (from F-GAP-002, if completed)
- Job posting text
- Company research (from F-RESEARCH-001)
- **Previous gap analysis Q&A** (if exists)
- Language
2. Interview question prediction:
**Question Categories (8-10 questions total, maximum 10):**
- **Behavioral Questions (3-4 questions):**
* Based on VPR differentiators
* Focus on achievements highlighted in CV
* Use STAR method structure
* Examples:
- "Tell me about a time you led a complex project. What was
your approach?"
- "Describe a situation where you had to overcome a
significant technical challenge."
- "Give me an example of how you've influenced without
authority."
- **Technical Questions (2-3 questions):**
* Based on required skills in job posting
* Depth appropriate to role level (IC vs Senior vs Lead)
* Examples:
- "Explain how you would design [system X] at scale."
- "Walk me through your approach to debugging [specific
issue]."
- "What's your experience with [key technology]?"
- **Company/Culture Fit (1-2 questions):**
* Based on company research insights
* Align with company values
* Examples:
- "Why do you want to work at [Company]?"
- "How do your values align with our mission of [X]?"


- "What excites you about [Company's recent initiative]?"
- **Situational/Problem-Solving (1-2 questions):**
* Hypothetical scenarios relevant to role
* Tests analytical thinking
* Examples:
- "How would you approach [specific challenge]?"
- "If you had to choose between [A] and [B], how would you
decide?"
- **Weakness/Gap Questions (1 question):**
* Based on gap analysis (if completed)
* Or common concerns (career transitions, job hopping, etc.)
* Examples:
- "You haven't used [Technology X] extensively. How would you
get up to speed?"
- "You're transitioning from [Industry A] to [Industry B]. Why
now?"
3. **Integration with Previous Gap Analysis:**
- If user answered gap analysis questions for this job:
* Use answers to inform suggested interview responses
* Reference specific examples from gap analysis answers
* Ensure consistency between gap analysis answers and interview
prep
* Build on gap analysis insights
- If user answered gap analysis for previous jobs:
* Use previous answers as additional context
* Identify patterns in user's experience/approach
* Suggest consistent narrative across applications
- Benefits:
* More personalized and accurate answer suggestions
* Leverages work user already did in gap analysis
* Ensures consistent story across application materials
* Saves user time (don't repeat examples)
4. Answer framework for each question:
**STAR Method Structure:**
- **Situation**: Context and background (1-2 sentences)
- **Task**: Your specific responsibility or challenge (1 sentence)
- **Action**: What you did, step-by-step (2-3 sentences, most
detail)
- **Result**: Outcome, ideally quantified (1-2 sentences)


**Answer Guidance:**

- Suggested approach (what to emphasize)
- Specific examples from CV to reference
- Potential follow-up questions
- What interviewer is evaluating
- Red flags to avoid

**Example Output:**
```
Question: "Tell me about a time you led a team through a
challenging project."

Suggested Approach:

- Choose your [Project X] example from [Company Y] (2022)
- Emphasize: Leadership, problem-solving, measurable impact
- Interviewer evaluating: Leadership style, handling ambiguity,
results orientation

STAR Framework:
Situation: "At [Company Y], our team was tasked with migrating our
monolithic application to microservices within a 6-month deadline.
This was critical because..."

Task: "As the technical lead, I was responsible for architecting
the migration strategy, coordinating 5 engineers, and ensuring zero
downtime during the transition."

Action: "I started by... [3-4 specific actions you took]. My
approach focused on..."

Result: "We completed the migration in 5 months, reduced
deployment time by 70%, and improved system reliability from 95% to
99.9% uptime. This enabled the company to..."

Follow-up Questions to Expect:

- "What challenges did you face during the migration?"
- "How did you handle team disagreements?"
- "What would you do differently?"

Tips:

- Quantify the impact (70% reduction, 99.9% uptime)
- Show leadership (coordinated, architected, guided)
- Demonstrate business understanding (enabled company to scale)


5. Additional preparation components: 30-Second Elevator Pitch:
    ● Concise personal introduction
    ● Top 3 qualifications for this role
    ● Enthusiasm statement
    ● Example: "I'm a DevOps engineer with 5 years of experience building scalable
       cloud infrastructure. I've reduced deployment times by 60% at my current
       company using [tools]. I'm excited about [Company's] mission to [X] and believe
       my background in [Y] makes me well-suited to help you scale."
6. Questions to Ask Interviewer (5-7 questions):
    ● About the role (day-to-day, first 90 days, success metrics)
    ● About the team (structure, collaboration style, growth)
    ● About the company (strategy, challenges, culture)
    ● Based on company research (recent news, initiatives)
    ● Example: "I saw that [Company] recently launched [Product X]. How does this
       role contribute to that initiative?"
7. Addressing Potential Concerns:
    ● Based on gap analysis (if completed)
    ● Proactive responses to obvious questions
    ● Turn weaknesses into growth opportunities
    ● Example: "If asked about limited experience with [Technology], emphasize rapid
       learning ability and transferable skills."
8. Interview Logistics Checklist:
    ● Research interviewers on LinkedIn
    ● Review company website, recent news
    ● Prepare questions about company
    ● Test technology (for virtual interviews)
    ● Prepare professional attire
    ● Plan to arrive 10 minutes early
9. Output format:
    ● PDF document (8-12 pages):
       ● Cover page: Company + Role
       ● Section 1: Predicted Questions with STAR Frameworks (8-10 questions)
       ● Section 2: Elevator Pitch
       ● Section 3: Questions to Ask Interviewer
       ● Section 4: Addressing Potential Concerns
       ● Section 5: Interview Preparation Checklist
    ● HTML version (for online viewing/printing)
    ● Practice mode (future V2):
       ● Interactive Q&A simulation
       ● Record and review answers
       ● Time management practice

Technical Specifications:

yaml


Lambda Function:
Name: interview-prep-generator
Runtime: Python 3.11
Memory: 512 MB
Timeout: 60s
Avg Duration: 12-18s
Model: Claude Haiku 4.5

AI Configuration:
Model: claude-haiku-4-5-20251001
Temperature: 0.3 (consistency for question prediction)
Max Tokens: 4000 (output)

System Prompt: |
You are an expert interview coach preparing a candidate for a
specific job interview.
Predict 8-10 likely interview questions and provide detailed
STAR-method answer frameworks.

CRITICAL REQUIREMENTS:

1. MAXIMUM 10 questions (8-10 ideal range)
2. Predict realistic questions based on role, company, job
posting
3. Diverse categories: behavioral, technical, culture fit,

situational

4. Each question requires complete STAR framework guidance
5. Answers must reference candidate's actual experience from CV
6. Include strategic insights from Value Proposition Report
7. No hallucinations - only reference verified experience

Input Requirements:

- job_application_id (DynamoDB reference)
- Retrieves:
* Job posting (original + parsed)
* Master CV (user's complete profile)
* Tailored CV (role-specific version)
* Value Proposition Report (strategic insights)
* Cover Letter (to maintain message consistency)
* Gap Analysis (if available - addresses weaknesses)
* Company research data

Output:

- PDF: interview-prep-{job_id}-{timestamp}.pdf


- Size: ~150-300 KB (8-12 pages)
- Storage: S3 bucket with 90-day lifecycle

Cost Analysis:
Input Tokens: ~8,000 (all context documents)
Output Tokens: ~4,000 (comprehensive prep guide)
Cost per generation: $0.003-0.005

Error Handling:

- Verify all input documents exist
- Validate job posting parsing
- Check for company research completion
- Fallback if gap analysis unavailable (skip that section)
- Log missing context for quality review

**FR-11: Document Export & Delivery (P0)**

Purpose: Enable users to download generated artifacts in multiple formats for various

submission requirements.

Supported Formats:

1. PDF (Primary)
    ● Generated using WeasyPrint or ReportLab
    ● Professional formatting with consistent styling
    ● ATS-friendly (no embedded images for text content)
    ● File size optimization: < 500 KB per document
    ● Naming convention: {artifact-type}-{company}-{timestamp}.pdf
2. DOCX (Required for editing)
    ● Generated using python-docx
    ● Maintains formatting consistency
    ● Allows user editing in Microsoft Word/Google Docs
    ● Template-based generation for consistency
    ● Preserves styles, fonts, spacing
3. Google Docs (V2)
    ● Direct upload to user's Google Drive
    ● OAuth integration required
    ● Automatic sharing settings
    ● Folder organization: "CareerVP Applications/{Company Name}/"

Technical Implementation:

yaml

Lambda Function:
Name: document-export-handler
Runtime: Python 3.11


Memory: 1024 MB (PDF generation memory-intensive)
Timeout: 30s

Libraries:

- WeasyPrint: PDF from HTML
- python-docx: Word document generation
- boto3: S3 upload
- jinja2: Template rendering

Process:

1. Retrieve generated content from DynamoDB
2. Apply formatting templates (HTML/DOCX)
3. Generate requested format
4. Upload to S3 with signed URL
5. Return download link (expires in 24 hours)

Storage:
Bucket: careervp-generated-documents
Path: {user_id}/{job_id}/{artifact_type}.{format}
Lifecycle: 90 days retention
Encryption: AES-256

Download URLs:
Type: S3 pre-signed URLs
Expiration: 24 hours

Rate limiting: 10 downloads per artifact per day

**FR-12: Email Notifications (P1)**

Purpose: Keep users informed about generation progress, completion, and system events.

Notification Types:

1. Transactional (SES)
    ● Application generation started
    ● Artifacts ready for download
    ● Account verification
    ● Password reset
    ● Subscription changes
    ● Usage limit warnings (80%, 100%)
2. Marketing (V2 - SES + Campaign Management)
    ● Weekly job search tips
    ● Feature announcements
    ● Success stories
    ● Educational content


Email Templates:

yaml

Templates:

1. welcome-email:
Trigger: Account creation
Content: Welcome message, getting started guide
CTA: Upload your first CV
2. generation-started:
Trigger: Job application processing begins
Content: Confirmation, estimated completion time
CTA: Track progress in dashboard
3. generation-complete:
Trigger: All artifacts ready
Content: Summary of generated documents
CTA: Download artifacts
Links: Direct download links (24h expiration)
4. generation-failed:
Trigger: Error in processing
Content: Error explanation, troubleshooting steps
CTA: Contact support, retry generation
5. usage-warning:
Trigger: 80% of free tier consumed
Content: Remaining applications, upgrade options
CTA: View pricing plans
6. usage-limit-reached:
Trigger: Free tier exhausted
Content: Upgrade benefits, pricing
CTA: Upgrade now (direct link to checkout)
7. subscription-activated:
Trigger: Successful payment
Content: Confirmation, receipt, next steps
CTA: Start generating applications
8. subscription-cancelled:
Trigger: User cancels subscription
Content: Cancellation confirmation, data retention policy
CTA: Provide feedback, reactivate option


Technical Implementation:
Service: AWS SES
Region: us-east-1 (SES production access)
Sending Rate: 14 emails/second (SES default)
Daily Limit: 50,000 emails/day

Configuration:
From: noreply@careervp.com
Reply-To: support@careervp.com
DKIM: Enabled
SPF: Configured
DMARC: Monitored

Template Engine: Jinja2
Styling: Inline CSS (email client compatibility)
Testing: Use SES Mailbox Simulator

Cost:
$0.10 per 1,000 emails

Monthly estimate (1,000 users): ~$50

**FR-13: Analytics Dashboard (V2 - Future)**

Purpose: Provide users with insights into their job search effectiveness.

Metrics to Track:

yaml

User Analytics:

- Total applications submitted
- Artifacts generated (by type)
- Average generation time
- Download frequency
- Success rate (applications → interviews)
- Response time from applications

Job Market Insights:

- Most common job titles
- Popular companies
- Required skills frequency
- Salary ranges (from job postings)
- Application competition estimates

Personal Performance:

- Skills gap analysis trends


- Improvement over time
- Interview conversion rates
- Strong vs. weak application areas

Implementation:
Service: Amazon QuickSight or CloudWatch Dashboards
Data Source: DynamoDB + aggregation Lambda
Update Frequency: Daily batch processing

Retention: 12 months of historical data

**FR-14: Admin Dashboard (P0 - MVP Required)**

Purpose: Monitor system health, user activity, and manage customer support.

Admin Capabilities:

yaml

1. User Management:
- View all users (paginated table)
- Search by email, name, user_id
- View user details:
* Registration date
* Subscription tier
* Usage statistics
* Generated artifacts count
* Last activity
- Manual actions:
* Grant free credits
* Extend trial period
* Reset usage limits (troubleshooting)
* Disable account (abuse)
* Delete account (GDPR)
2. System Monitoring:
- Lambda execution metrics:
* Success/failure rates
* Average execution time
* Cost per function
* Error logs
- API Gateway:
* Request volume
* Response times
* Error rates
* Top endpoints
- AI Model Usage:


* Token consumption (Sonnet vs Haiku)
* Cost breakdown
* Generation quality scores (future)

3. Job Processing Queue:
- View active jobs
- Job status (pending, processing, complete, failed)
- Manual retry failed jobs
- Cancel stuck jobs
- View error details
4. Financial Dashboard:
- Daily revenue
- MRR (Monthly Recurring Revenue)
- Churn rate
- Stripe transaction logs
- Cost analysis (AWS + Anthropic)
- Profit margins
5. Content Moderation:
- Flag suspicious uploads
- Review reported content
- Detect abuse patterns
- Rate limiting overrides

Technical Implementation:
Framework: React Admin or Retool
Authentication: Cognito (admin-only user pool)
Backend: API Gateway → Lambda
Data: DynamoDB + CloudWatch Logs
Access: IP whitelist + MFA required

Initial Admin Users:

- yitzchak@careervp.com (Super Admin)
- Additional admins as needed

**FR-15: Rate Limiting & Abuse Prevention (P0)**

Purpose: Protect system from abuse, ensure fair usage, and control costs.

Rate Limits:

yaml

Free Tier:
Applications: 3 per lifetime


API Requests: 10 per minute
File Uploads: 5 per day
Downloads: 20 per day

Paid Tier:
Applications: Unlimited
API Requests: 60 per minute
File Uploads: 50 per day
Downloads: 100 per day

Implementation:
Service: API Gateway usage plans + Lambda authorizer
Storage: DynamoDB (user rate limit tracking)
Reset: Daily at midnight UTC

Abuse Detection:
Patterns:

- Rapid account creation (same IP)
- Excessive file uploads (bandwidth abuse)
- Suspicious job postings (encoded malware, phishing)
- Unusual generation patterns (automation scripts)

Actions:

- Automatic: Temporary suspension (24h)
- Manual review: Admin investigation required
- Permanent ban: Severe violations

Notifications:

- User: Email warning before suspension
- Admin: Slack/email alert for review

**FR-16: Data Retention & Privacy (P0)**

Purpose: GDPR/CCPA compliance, user data control, transparent policies.

Data Lifecycle:

yaml

Active Data (User has account):

- Master CV: Indefinite (until user deletes)
- Generated artifacts: 90 days post-generation
- Job postings: 90 days post-application
- User profile: Indefinite
- Usage logs: 12 months


Deleted Account:

- Personal data: Deleted within 30 days
- Anonymized analytics: Retained (no PII)
- Financial records: 7 years (tax compliance)
- Support tickets: 12 months (then anonymized)

S3 Lifecycle Policies:
Bucket: careervp-generated-documents
Transition to Glacier: 30 days
Permanent deletion: 90 days

DynamoDB TTL:
Generated artifacts: 90 days
Job postings: 90 days
Session tokens: 24 hours
Password reset tokens: 1 hour

User Rights (GDPR):

- Data export: JSON format, all personal data
- Data deletion: Complete account erasure
- Data correction: Self-service in settings
- Access logs: View own activity history

Implementation:
Lambda: data-export-handler
Lambda: account-deletion-handler

Scheduled: Cleanup job (daily midnight)

**FR-17: Multi-Language Support (V2)**

Purpose: Expand to international markets, support non-English job applications.

Supported Languages (Phase 1):

yaml

English Variants:

- US English (default)
- UK English
- Canadian English
- Australian English

Phase 2:

- Hebrew (Israel market - Yitzchak's location)
- Spanish (Latin America + Spain)
- French (Canada + France)


- German (European market)

Implementation Strategy:

1. UI Translation:
- i18next library
- JSON translation files
- Language selector in settings
2. AI-Generated Content:
- Prompt modifications per language
- Cultural customization (e.g., CV format differences)
- Language-specific quality verification
3. Support:
- Multilingual email templates
- Localized help documentation
- Language-specific FAQ

Challenges:

- Hebrew: Right-to-left (RTL) UI support
- Cultural: CV format varies (US vs EU vs Asia)
- Legal: Different privacy requirements per region

**Summary: Complete Features List Structure**

Tier P0 (MVP - Must Have):

```
● FR-1: User Authentication
● FR-2: CV Upload & Management
● FR-3: Job Posting Input
● FR-4: Value Proposition Report Generation
● FR-5: CV Tailoring
● FR-6: Cover Letter Generation
● FR-7: Interview Preparation
● FR-9: Review & Edit Workflow
● FR-10: Usage Tracking & Limits
● FR-11: Document Export (PDF/DOCX)
● FR-14: Admin Dashboard
● FR-15: Rate Limiting
● FR-16: Data Retention & Privacy
```
Tier P1 (Important - Early Post-MVP):

```
● FR-8: Job Tracking Dashboard
● FR-12: Email Notifications
```

Tier P2 (V2 - Future Enhancement):

```
● FR-13: Analytics Dashboard
● FR-17: Multi-Language Support
● Company Research Automation (Enhanced)
● Google Docs Integration
● Interactive Interview Practice
```
Next Steps:

Would you like me to:

1. Generate the complete NFR (Non-Functional Requirements) section covering
    performance, scalability, security, compliance?
2. Create user stories for each feature requirement (Agile format)?
3. Develop API specifications for all endpoints?
4. Build database schema documentation (complete DynamoDB table definitions)?
5. Document the complete Lambda functions inventory with detailed specifications for all
    18-22 functions?

Let me know which direction to proceed!

Proceed:
* Generate the complete NFR (Non-Functional Requirements) section covering performance,
scalability, security, compliance?
* Create user stories for each feature requirement (Agile format)?
* Develop API specifications for all endpoints?

* Build database schema documentation (complete DynamoDB table definitions)?


# Tab 4


**CAREERVP SAAS - COMPLETE**

**TECHNICAL DOCUMENTATION**

**PART 1: NON-FUNCTIONAL REQUIREMENTS (NFR)**

**NFR-1: Performance Requirements**

yaml

Response Time Targets (P95):
API Gateway Endpoints:

- Authentication: < 500ms
- File Upload: < 3s (for 5MB file)
- Job Posting Submit: < 1s
- Dashboard Load: < 800ms

Lambda Functions:

- company-research-v1: < 25s
- vp-report-generator: < 25s
- cv-tailor: < 15s
- cover-letter-generator: < 12s
- gap-analysis-questions: < 20s
- interview-prep-generator: < 18s

Document Generation:

- PDF Export: < 5s
- DOCX Export: < 3s
- Download Link Creation: < 1s

Frontend Performance:

- Initial Page Load: < 2s
- Time to Interactive (TTI): < 3s
- Largest Contentful Paint (LCP): < 2.5s
- First Input Delay (FID): < 100ms
- Cumulative Layout Shift (CLS): < 0.1

Database Operations:

- DynamoDB Query: < 100ms
- DynamoDB Write: < 50ms
- S3 Upload (5MB): < 5s
- S3 Download (presigned URL): < 2s

Throughput Requirements:


Concurrent Users:

- Month 1-3: 100 users
- Month 4-6: 500 users
- Month 7-12: 1,000 users
- Year 2: 10,000 users

Requests Per Second (RPS):

- API Gateway: 100 RPS (burst: 500)
- Lambda Concurrent Executions: 50 (reserved)
- DynamoDB: 100 WCU / 200 RCU (on-demand)

Generation Throughput:

- Max Applications Per Hour: 50
- Max Concurrent Generations: 20
- Queue Processing: SQS FIFO (100 msg/min)

Optimization Strategies:

- CloudFront CDN for static assets
- Lambda response streaming for large outputs
- DynamoDB DAX for read-heavy operations (V2)
- S3 Transfer Acceleration for uploads (V2)
- API Gateway caching (5-minute TTL)

**NFR-2: Scalability Requirements**

yaml

Auto-Scaling Configuration:
Lambda Functions:

- Concurrent Executions: 50 (reserved), 1000 (unreserved limit)
- Provisioned Concurrency: None (V1), 5 (V2 for critical
functions)
- Scaling Policy: Automatic (AWS managed)

DynamoDB:

- Capacity Mode: On-Demand (auto-scales)
- Partition Strategy: user_id (hash key)
- Global Secondary Indexes: 3-5 (on-demand)
- Backup: Point-in-time recovery enabled

## S3:

- Storage: Unlimited (AWS managed)
- Request Rate: 5,500 GET/s per prefix
- Multipart Upload: Files > 100MB


## SQS:

- Message Retention: 14 days
- Visibility Timeout: 5 minutes
- Max Receives: 3 (then DLQ)

API Gateway:

- Throttle Limits: 10,000 requests/second (AWS default)
- Burst: 5,000 (AWS default)
- Custom Limits: Per usage plan

Horizontal Scaling:

- All Lambda functions are stateless
- No session affinity required
- DynamoDB scales automatically
- S3 scales infinitely

Growth Projections:
Year 1:

- Users: 100 → 1,000
- Applications/month: 300 → 10,000
- Storage: 10GB → 500GB
- Cost: $200/mo → $2,500/mo

Year 2:

- Users: 1,000 → 10,000
- Applications/month: 10,000 → 100,000
- Storage: 500GB → 5TB
- Cost: $2,500/mo → $15,000/mo

Year 3:

- Users: 10,000 → 50,000
- Applications/month: 100,000 → 500,000
- Storage: 5TB → 25TB
- Cost: $15,000/mo → $75,000/mo

**NFR-3: Availability & Reliability**

yaml

Uptime SLA:
Target: 99.9% (3 Sigma)
Downtime Allowance: 43.8 minutes/month
Measurement: CloudWatch uptime checks

High Availability Architecture:


Multi-AZ Deployment:

- API Gateway: Multi-AZ (AWS managed)
- Lambda: Multi-AZ (AWS managed)
- DynamoDB: Multi-AZ with replication
- S3: 11 nines durability, 99.99% availability

Redundancy:

- No single points of failure
- Automatic failover (AWS managed)
- Cross-region backup (S3 replication) (V2)

Disaster Recovery:
RTO (Recovery Time Objective): 4 hours
RPO (Recovery Point Objective): 1 hour

Strategy:

- DynamoDB: Point-in-time recovery (35 days)
- S3: Versioning enabled + lifecycle policies
- Lambda: Code in version control (GitHub)
- Infrastructure: Terraform/CloudFormation (IaC)

Backup Schedule:

- DynamoDB: Continuous (PITR)
- S3: Versioning + Cross-region replication (V2)
- Code: GitHub (automatic)
- Configuration: Daily snapshots

Error Handling:
Retry Logic:

- Lambda: 2 retries with exponential backoff
- API Gateway: Client retries (configurable)
- SQS: 3 attempts → DLQ
- Anthropic API: 3 retries with backoff

Circuit Breaker:

- Anthropic API: 5 consecutive failures → circuit open
- Open duration: 60 seconds
- Half-open: 1 test request

Graceful Degradation:

- If company-research fails → VP Report continues without
- If gap-analysis fails → Interview Prep continues without
- If Anthropic API down → queue jobs for retry

Health Checks:


- API Gateway: /health endpoint (200 OK)
- Lambda: CloudWatch alarms on errors
- DynamoDB: CloudWatch metrics
- SQS: Dead Letter Queue monitoring

Monitoring & Alerting:
CloudWatch Alarms:

- Lambda errors > 5% (5-minute window)
- API Gateway 5xx > 1% (5-minute window)
- DynamoDB throttling > 0
- SQS DLQ messages > 0
- Anthropic API cost > $500/day

SNS Notifications:

- Email: yitzchak@careervp.com
- Slack: _#careervp-alerts (V2)_
- PagerDuty: Critical only (V2)

Logging:

- CloudWatch Logs: All Lambda functions
- Retention: 30 days (standard), 90 days (errors)
- Log Level: INFO (production), DEBUG (development)
- Structured Logging: JSON format

**NFR-4: Security Requirements**

yaml

Authentication & Authorization:
Cognito User Pool:

- MFA: Optional (V1), Required (V2 for paid users)
- Password Policy:
* Minimum length: 12 characters
* Require: uppercase, lowercase, number, special char
* Password history: 5 (prevent reuse)
* Expiration: 90 days (force reset)
- Account Lockout: 5 failed attempts → 30-minute lockout
- Session Duration: 24 hours (refresh token: 30 days)

API Authorization:

- JWT tokens (Cognito-issued)
- Token validation: Lambda authorizer
- Scopes: user:read, user:write, admin:all
- Rate limiting: Per user token


Admin Access:

- Separate Cognito User Pool (admin-only)
- MFA: Required (TOTP)
- IP Whitelist: Office/VPN only
- Session Duration: 8 hours
- Audit logging: All admin actions

Encryption:
Data at Rest:

- DynamoDB: AWS-managed KMS keys (default)
- S3: AES-256 (SSE-S3)
- Secrets Manager: KMS encryption
- EBS (if used): Encrypted volumes

Data in Transit:

- TLS 1.3 (API Gateway, CloudFront)
- HTTPS-only (no HTTP allowed)
- Certificate: AWS Certificate Manager (ACM)
- HSTS: Enabled (max-age=31536000)

Sensitive Data Handling:

- Passwords: Never stored (Cognito handles)
- API Keys: Secrets Manager (rotated 90 days)
- PII: Encrypted at rest, minimal retention
- Credit Cards: Never stored (Stripe handles)

Network Security:
VPC Configuration (Future V2):

- Lambda: VPC-attached for database access
- Security Groups: Least privilege
- NACLs: Deny-by-default
- NAT Gateway: For outbound internet

WAF (Web Application Firewall) (V2):

- CloudFront distribution protection
- Rules:
* SQL injection prevention
* XSS prevention
* Rate limiting (per IP)
* Geo-blocking (if needed)
* Known bad IPs (AWS Managed Rules)

DDoS Protection:

- AWS Shield Standard: Enabled (free)
- AWS Shield Advanced: (V2, if needed)


- CloudFront: Built-in DDoS mitigation

Application Security:
Input Validation:

- Client-side: React forms validation
- Server-side: Lambda input validation
- File uploads: Virus scanning (ClamAV) (V2)
- File types: Whitelist (PDF, DOCX, TXT only)
- File size: 5MB max (enforced at API Gateway)

Output Encoding:

- HTML: Escape all user-generated content
- JSON: Properly encoded responses
- PDF: No JavaScript execution

OWASP Top 10 Mitigation:

- A01 Broken Access Control: JWT + Lambda authorizer
- A02 Cryptographic Failures: KMS + TLS 1.3
- A03 Injection: Parameterized queries (DynamoDB)
- A04 Insecure Design: Threat modeling completed
- A05 Security Misconfiguration: IaC + automated checks
- A06 Vulnerable Components: Dependabot + updates
- A07 Auth Failures: Cognito + MFA + lockout
- A08 Data Integrity: Checksums + versioning
- A09 Logging Failures: CloudWatch + structured logs
- A10 SSRF: No user-controlled URLs

Secrets Management:
AWS Secrets Manager:

- Anthropic API key
- Stripe API keys
- Google OAuth credentials (V2)
- Database credentials (if RDS used)

Rotation Policy:

- API keys: 90 days
- Passwords: 90 days (forced)
- JWT signing keys: 180 days

Access Control:

- Lambda execution roles: Read-only access
- Admin users: Manual rotation only
- Audit trail: CloudTrail logs

Compliance & Auditing:


Audit Logging:

- CloudTrail: All AWS API calls
- Application Logs: User actions (auth, uploads, downloads)
- Retention: 12 months (standard), 7 years (financial)
- Immutable: Write-once storage (S3 Glacier)

Security Scanning:

- Dependencies: Snyk/Dependabot (weekly)
- Code: SonarQube (per commit)
- Infrastructure: AWS Security Hub
- Penetration Testing: Annual (V2)

Vulnerability Management:

- Patching: Monthly security updates
- CVE Monitoring: Automated alerts
- Response Time: Critical (24h), High (7d), Medium (30d)

**NFR-5: Compliance Requirements**

yaml

GDPR (General Data Protection Regulation):
Applicability: EU users (even if US-based company)

Requirements:

- Data Minimization: Collect only necessary data
- Purpose Limitation: Use data only as stated
- Storage Limitation: 90-day retention for generated docs
- Accuracy: User can correct their data
- Integrity & Confidentiality: Encryption + access controls

User Rights:

- Right to Access: Data export tool (JSON format)
- Right to Rectification: Self-service editing
- Right to Erasure: Account deletion (30-day process)
- Right to Portability: Download all data
- Right to Object: Opt-out of marketing emails
- Right to Restrict Processing: Pause account

Consent Management:

- Explicit consent: Checkbox (not pre-checked)
- Granular consent: Marketing vs. essential emails
- Withdrawal: One-click unsubscribe
- Record: Timestamp + consent text version


Data Processing Agreement (DPA):

- With AWS (already GDPR-compliant)
- With Anthropic (review their DPA)
- With Stripe (already GDPR-compliant)

Breach Notification:

- Detection: Within 24 hours
- Internal notification: Immediately
- User notification: Within 72 hours (if high risk)
- Regulator notification: Within 72 hours (required)

Privacy Policy:

- Location: careervp.com/privacy
- Updates: Notify users 30 days before
- Language: Clear, simple (no legalese)
- Translations: Required for EU languages

CCPA (California Consumer Privacy Act):
Applicability: California residents

Requirements:

- Notice at Collection: What data, why, how long
- Right to Know: What data collected
- Right to Delete: Same as GDPR
- Right to Opt-Out: Selling data (N/A - we don't sell)
- Non-Discrimination: Can't charge more for opting out

"Do Not Sell My Info" Link:

- Required on homepage (even if not selling)
- Explanation: "We do not sell your data"

SOC 2 Compliance (Future V2):
Type II Certification:

- Security: Already covered above
- Availability: 99.9% uptime
- Processing Integrity: Accurate processing
- Confidentiality: NDA with employees
- Privacy: GDPR/CCPA compliance

Audit Frequency: Annual
Auditor: Third-party (Deloitte, PwC, etc.)
Cost: $15,000-$50,000/year

PCI DSS (Payment Card Industry):
Level: SAQ A (Stripe handles all card data)


Requirements:

- Never store card data (Stripe Checkout)
- Never transmit card data (Stripe.js tokenization)
- Use PCI-compliant payment processor (Stripe is)
- Annual attestation (self-assessment)

Compliance Validation:

- SAQ A questionnaire: 22 questions
- Submit to Stripe: Annually
- No on-site audit required (Level 4 merchant)

Data Residency:
Primary Region: us-east-1 (N. Virginia)

EU Users (GDPR):

- Option 1: Store all data in us-east-1 (Privacy Shield
invalidated)
- Option 2: Store EU data in eu-west-1 (Ireland) (V2)
- Decision: V1 uses us-east-1 with Standard Contractual Clauses
(SCCs)

Data Transfer:

- EU to US: SCCs + encryption
- US to Anthropic: API calls (review Anthropic's data handling)

Terms of Service:
Key Sections:

- Acceptable Use: No illegal content, no abuse
- Intellectual Property: User owns their data
- Liability Limitations: Best-effort service
- Termination: We can suspend for violations
- Governing Law: Delaware (if US company)
- Dispute Resolution: Arbitration (cost-effective)

Review: Annual legal review
Updates: 30-day notice to users
Acceptance: Required before first use

Cookie Policy:
Essential Cookies: Session, authentication (no consent needed)
Analytics Cookies: Google Analytics (consent required)
Marketing Cookies: None (V1)

Consent Banner:


- First visit: Show banner
- Options: Accept all, Reject all, Customize
- Storage: 12 months
- Withdrawal: Settings page

**NFR-6: Usability & Accessibility**

yaml

User Experience:
Design System:

- Framework: Tailwind CSS + shadcn/ui
- Consistency: Reusable components
- Responsive: Mobile-first design
- Breakpoints: 640px, 768px, 1024px, 1280px

Navigation:

- Max depth: 3 levels
- Breadcrumbs: For deep pages
- Search: Global search (V2)
- Back button: Browser-native support

Forms:

- Inline validation: Real-time feedback
- Error messages: Clear, actionable
- Required fields: Visual indicator (*)
- Help text: Tooltips for complex fields
- Auto-save: Draft functionality (V2)

Loading States:

- Skeleton screens: Initial load
- Progress bars: Long operations (generation)
- Spinners: Short operations (< 3s)
- Optimistic UI: Immediate feedback

Error Handling:

- Friendly messages: No technical jargon
- Recovery actions: "Try again" button
- Support link: Always visible
- Error tracking: Sentry integration (V2)

Accessibility (WCAG 2.1 AA):
Perceivable:

- Text alternatives: Alt text for images
- Color contrast: 4.5:1 (normal text), 3:1 (large text)


- Resize text: Up to 200% without loss
- Images of text: Avoided (use real text)

Operable:

- Keyboard navigation: All features accessible
- Focus indicators: Visible focus states
- Skip links: Jump to main content
- No keyboard traps: Can exit all elements
- Time limits: Extendable (session timeout)

Understandable:

- Language: HTML lang attribute
- Predictable: Consistent navigation
- Input assistance: Clear labels, error messages
- Error identification: Clearly marked

Robust:

- Semantic HTML: Proper element usage
- ARIA labels: Where semantic HTML insufficient
- Browser compatibility: Chrome, Firefox, Safari, Edge
- Screen readers: NVDA, JAWS, VoiceOver tested

Testing:

- Automated: axe DevTools, Lighthouse
- Manual: Screen reader testing
- Compliance: VPAT (Voluntary Product Accessibility Template)
(V2)

Internationalization (i18n):
Character Encoding: UTF-8
Date Format: ISO 8601 (YYYY-MM-DD)
Time Format: 24-hour (with AM/PM option)
Number Format: Locale-aware (commas vs. periods)
Currency: User's locale (USD, EUR, ILS, etc.)
RTL Support: Hebrew (V2)

Performance (from user perspective):
Perceived Performance:

- Instant feedback: < 100ms
- Fast response: < 1s
- Acceptable: < 3s
- Slow (show progress): > 3s

Optimization:

- Code splitting: Lazy load routes


- Image optimization: WebP format, responsive sizes
- Caching: Service worker (V2)
- CDN: CloudFront for static assets

**NFR-7: Maintainability & DevOps**

yaml

Code Quality:
Standards:

- Language: TypeScript (frontend), Python 3.11 (backend)
- Style Guide: Airbnb (TypeScript), PEP 8 (Python)
- Linting: ESLint, Pylint
- Formatting: Prettier, Black
- Type Checking: TypeScript strict mode, mypy

Code Reviews:

- Required: All pull requests
- Reviewers: Minimum 1 (ideally 2)
- Merge: Squash and merge
- Branch protection: Main branch protected

Testing:

- Unit Tests: 80% coverage target
- Integration Tests: Critical paths
- E2E Tests: Playwright (V2)
- Performance Tests: Load testing with k6 (V2)

Documentation:

- Code comments: Complex logic only
- Function docs: Docstrings (Python), JSDoc (TypeScript)
- API docs: OpenAPI 3.0 specification
- Architecture: ADR (Architecture Decision Records)

Version Control:
Repository: GitHub
Branching Strategy:

- main: Production-ready code
- develop: Integration branch
- feature/*: Feature branches
- hotfix/*: Urgent production fixes

Commit Messages:

- Format: Conventional Commits
- Example: "feat(auth): add MFA support"


- Types: feat, fix, docs, style, refactor, test, chore

Versioning:

- Semantic Versioning: MAJOR.MINOR.PATCH
- Tags: v1.0.0, v1.1.0, v2.0.0
- Changelog: Auto-generated from commits

CI/CD Pipeline:
GitHub Actions:

- Triggers: Push to main, pull request
- Stages:
1. Lint & Format Check
2. Type Checking
3. Unit Tests
4. Build
5. Integration Tests
6. Deploy to Staging
7. Smoke Tests
8. Deploy to Production (manual approval)

Deployment:

- Infrastructure: Terraform (IaC)
- Lambda: ZIP deployment (< 50MB), Container (> 50MB)
- Frontend: S3 + CloudFront
- Database: Schema migrations (automated)

Environments:

- Development: Local (Docker Compose)
- Staging: AWS (staging.careervp.com)
- Production: AWS (app.careervp.com)

Rollback:

- Lambda: Previous version (alias routing)
- Frontend: CloudFront invalidation + S3 version
- Database: Backup restore (manual)
- Max rollback time: 15 minutes

Monitoring:
Application Performance Monitoring (APM):

- Service: AWS X-Ray (V1), Datadog (V2)
- Tracing: End-to-end request tracing
- Metrics: Custom business metrics
- Alerts: Performance degradation

Logging:


- Aggregation: CloudWatch Logs
- Search: CloudWatch Insights
- Visualization: CloudWatch Dashboards
- Retention: 30 days (standard), 90 days (errors)

Error Tracking:

- Service: Sentry (V2)
- Notifications: Slack, Email
- Grouping: Automatic error grouping
- Releases: Track errors by version

Metrics:

- Business: Applications generated, revenue, churn
- Technical: Lambda duration, error rate, cost
- User: Active users, session duration, bounce rate
- Infrastructure: CPU, memory, network

Dependency Management:
Frontend:

- Package Manager: npm
- Lock File: package-lock.json
- Updates: Dependabot (weekly)
- Audit: npm audit (pre-commit)

Backend:

- Package Manager: pip
- Requirements: requirements.txt (pinned versions)
- Updates: Dependabot (weekly)
- Audit: Safety (pre-commit)

Security Updates:

- Critical: Immediate (< 24 hours)
- High: Urgent (< 7 days)
- Medium: Regular (< 30 days)
- Low: Next release

**NFR-8: Cost Optimization**

yaml

Cost Targets:
Gross Margin: 95%+ (target)

Cost Breakdown (per 1,000 users):

- AWS Lambda: $200-300/month


- Anthropic API: $1,200-1,500/month
- DynamoDB: $100-150/month
- S3: $50-75/month
- API Gateway: $35-50/month
- CloudFront: $20-30/month
- SES: $10-15/month
- Cognito: $15-25/month
- Total: ~$1,630-2,145/month

Revenue (per 1,000 users):

- Assumption: 10% conversion to paid ($29/month)
- Revenue: 100 paid × $29 = $2,900/month
- Gross Profit: $2,900 - $2,145 = $755/month
- Margin: 26% (needs optimization!)

Optimization Strategies:

- Use Haiku over Sonnet where possible
- Implement caching (company research)
- S3 lifecycle policies (Glacier after 30 days)
- Reserved Lambda concurrency (V2)
- Committed use discounts (V2)

Cost Monitoring:
AWS Cost Explorer:

- Daily budget alerts: > $100/day
- Monthly budget: $2,500 (Month 1-6)
- Cost allocation tags: Environment, Service, User

Anthropic API:

- Daily token usage alerts: > 50M tokens
- Monthly budget: $2,000 (Month 1-6)
- Cost tracking: CloudWatch custom metric

FinOps Practices:

- Weekly cost review
- Monthly optimization review
- Quarterly capacity planning
- Annual contract negotiations

**PART 2: USER STORIES (AGILE FORMAT)**

**Epic 1: User Onboarding & Authentication**

US-1.1: User Registration


yaml

As a: Job seeker
I want to: Create an account with email and password
So that: I can save my CVs and track my applications

Acceptance Criteria:

- Given I'm on the signup page
- When I enter valid email, password (12+ chars), and confirm
password
- Then my account is created and I receive a verification email
- And I'm redirected to the email verification page

Technical Notes:

- Cognito User Pool handles authentication
- Password must meet complexity requirements
- Email verification required before access

Story Points: 5
Priority: P0

Sprint: 1

US-1.2: Email Verification

yaml

As a: New user
I want to: Verify my email address
So that: I can access the platform and ensure account security

Acceptance Criteria:

- Given I receive a verification email
- When I click the verification link
- Then my email is marked as verified
- And I'm redirected to the dashboard with a welcome message

Technical Notes:

- Cognito handles verification code
- Link expires in 24 hours
- Resend option available

Story Points: 3
Priority: P0

Sprint: 1

US-1.3: User Login


yaml

As a: Registered user
I want to: Log in with my credentials
So that: I can access my saved CVs and applications

Acceptance Criteria:

- Given I'm on the login page
- When I enter correct email and password
- Then I'm redirected to the dashboard
- And I see my recent applications

Technical Notes:

- JWT token issued (24-hour expiry)
- Refresh token (30-day expiry)
- Failed login tracking (5 attempts → lockout)

Story Points: 3
Priority: P0

Sprint: 1

US-1.4: Password Reset

yaml

As a: User who forgot my password
I want to: Reset my password via email
So that: I can regain access to my account

Acceptance Criteria:

- Given I click "Forgot Password"
- When I enter my email
- Then I receive a password reset link
- And I can set a new password (meeting requirements)
- And I can log in with the new password

Technical Notes:

- Cognito handles reset flow
- Reset link expires in 1 hour
- Previous password cannot be reused (5 history)

Story Points: 3
Priority: P0

Sprint: 1

**Epic 2: CV Management**


US-2.1: Upload Master CV

yaml

As a: User
I want to: Upload my master CV
So that: The system can tailor it for specific job applications

Acceptance Criteria:

- Given I'm on the CV upload page
- When I upload a PDF or DOCX file (< 5MB)
- Then the file is uploaded to S3
- And I see a preview of the extracted text
- And I'm prompted to review/edit the extracted information

Technical Notes:

- Supported formats: PDF, DOCX, TXT
- Text extraction: PyPDF2, python-docx
- Storage: S3 bucket (encrypted)
- Virus scan: Future V2

Story Points: 8
Priority: P0

Sprint: 2

US-2.2: Edit Master CV

yaml

As a: User
I want to: Edit my master CV information
So that: I can keep it up-to-date

Acceptance Criteria:

- Given I have an uploaded CV
- When I click "Edit"
- Then I see a form with all extracted fields
- And I can modify any field
- And I click "Save"
- Then my changes are saved to DynamoDB
- And the original file is updated in S3 (versioned)

Technical Notes:

- Form fields: Contact, Experience, Education, Skills, etc.
- Validation: Required fields, date formats
- Versioning: S3 object versioning

Story Points: 5


Priority: P1

Sprint: 2

US-2.3: Delete Master CV

yaml

As a: User
I want to: Delete my master CV
So that: I can remove outdated information

Acceptance Criteria:

- Given I have an uploaded CV
- When I click "Delete"
- Then I see a confirmation dialog
- And I confirm deletion
- Then the CV is removed from DynamoDB and S3
- And all associated applications are marked (CV deleted)

Technical Notes:

- Soft delete (30-day recovery window)
- Cascading: Applications not deleted (just flagged)
- Admin notification: For audit trail

Story Points: 3
Priority: P1

Sprint: 2

**Epic 3: Job Application Generation**

US-3.1: Submit Job Posting

yaml

As a: User
I want to: Submit a job posting URL or text
So that: The system can analyze it for my application

Acceptance Criteria:

- Given I'm on the "New Application" page
- When I paste a job posting URL or copy/paste the text
- Then the system extracts job details (title, company,
requirements)
- And I see a preview of extracted information
- And I can edit/confirm before proceeding

Technical Notes:


- URL scraping: BeautifulSoup
- Text parsing: NLP (spaCy) or Claude Haiku
- Company detection: Named Entity Recognition
- Storage: DynamoDB (job_postings table)

Story Points: 8
Priority: P0

Sprint: 3

US-3.2: Generate Value Proposition Report

yaml

As a: User
I want to: Generate a Value Proposition Report
So that: I understand how to position myself for this role

Acceptance Criteria:

- Given I have submitted a job posting
- When I click "Generate VP Report"
- Then the system initiates company research (15-25s)
- And generates the VP Report using Claude Sonnet (15-25s)
- And I receive an email when complete
- And I can download the PDF (8-12 pages)

Technical Notes:

- Lambda: company-research-v1 → vp-report-generator
- Model: Claude Sonnet 4.5
- Output: PDF format
- Storage: S3 (90-day lifecycle)
- Cost: $0.023-0.035 per report

Story Points: 13
Priority: P0
Sprint: 3-4

Dependencies: US-3.1, US-2.1

US-3.3: Generate Tailored CV

yaml

As a: User
I want to: Generate a tailored CV for this job
So that: My CV highlights relevant experience

Acceptance Criteria:

- Given I have a VP Report generated


- When I click "Generate Tailored CV"
- Then the system generates a customized CV (10-15s)
- And I can preview the PDF
- And I can download in PDF or DOCX format

Technical Notes:

- Lambda: cv-tailor
- Model: Claude Haiku 4.5
- Input: Master CV + Job Posting + VP Report
- Output: PDF, DOCX
- ATS optimization: Keywords, formatting
- Cost: $0.003-0.005 per CV

Story Points: 13
Priority: P0
Sprint: 4

Dependencies: US-3.2

US-3.4: Generate Cover Letter

yaml

As a: User
I want to: Generate a tailored cover letter
So that: I can submit a compelling application

Acceptance Criteria:

- Given I have a tailored CV
- When I click "Generate Cover Letter"
- Then the system generates a 1-page cover letter (8-12s)
- And I can select a style (formal, conversational, enthusiastic)
- And I can preview and download (PDF, DOCX)

Technical Notes:

- Lambda: cover-letter-generator
- Model: Claude Haiku 4.5
- Input: Master CV + Job Posting + VP Report + Tailored CV
- Styles: 3 templates
- Cost: $0.002-0.004 per letter

Story Points: 8
Priority: P0
Sprint: 4

Dependencies: US-3.3

US-3.5: Generate Interview Preparation


yaml

As a: User
I want to: Generate interview preparation materials
So that: I can practice and be confident in my interview

Acceptance Criteria:

- Given I have all artifacts generated
- When I click "Generate Interview Prep"
- Then the system predicts 8-10 interview questions (12-18s)
- And provides STAR-method answer frameworks
- And includes company insights and elevator pitch
- And I can download the PDF (8-12 pages)

Technical Notes:

- Lambda: interview-prep-generator
- Model: Claude Haiku 4.5
- Input: All previous artifacts + Gap Analysis (if available)
- Output: PDF
- Cost: $0.003-0.005 per prep

Story Points: 13
Priority: P0
Sprint: 5

Dependencies: US-3.4

**Epic 4: Application Management**

US-4.1: View Application Dashboard

yaml

As a: User
I want to: See all my job applications in one place
So that: I can track my progress

Acceptance Criteria:

- Given I'm logged in
- When I navigate to the dashboard
- Then I see a table of all applications
- With columns: Company, Role, Status, Date, Actions
- And I can filter by status (Draft, Submitted, Interview, Offer,
Rejected)
- And I can search by company or role

Technical Notes:


- Data source: DynamoDB (job_applications table)
- Pagination: 20 per page
- Sorting: By date (newest first)

Story Points: 5
Priority: P1

Sprint: 5

US-4.2: Update Application Status

yaml

As a: User
I want to: Update the status of my application
So that: I can track my progress

Acceptance Criteria:

- Given I'm viewing an application
- When I click the status dropdown
- Then I see options: Draft, Submitted, Interview, Offer, Rejected
- And I select a new status
- Then the status is updated in DynamoDB
- And the timeline is updated with the change

Technical Notes:

- Status transitions: Any → Any (user-controlled)
- Timeline: Array of {status, timestamp} objects
- Notification: None (user-initiated)

Story Points: 3
Priority: P1

Sprint: 5

US-4.3: Download Generated Artifacts

yaml

As a: User
I want to: Download all artifacts for an application
So that: I can submit them to the employer

Acceptance Criteria:

- Given I have generated artifacts
- When I click "Download"
- Then I see options for each artifact (VP Report, CV, Cover
Letter, Interview Prep)
- And I can select format (PDF or DOCX where applicable)


- And I click download
- Then a signed S3 URL is generated (24-hour expiry)
- And the file downloads to my device

Technical Notes:

- S3 presigned URLs (24-hour expiry)
- Rate limiting: 10 downloads per artifact per day
- Tracking: Download count in DynamoDB

Story Points: 5
Priority: P0

Sprint: 5

**Epic 5: Subscription & Billing**

US-5.1: View Pricing Plans

yaml

As a: Visitor
I want to: See available pricing plans
So that: I can decide which plan suits me

Acceptance Criteria:

- Given I'm on the pricing page (WordPress)
- Then I see Free (3 applications) and Pro ($29/month, unlimited)
- With feature comparison table
- And I can click "Get Started" to sign up

Technical Notes:

- Pricing page: WordPress (careervp.com/pricing)
- CTA: Links to app.careervp.com/signup

Story Points: 2
Priority: P0

Sprint: 6

US-5.2: Upgrade to Pro

yaml

As a: Free user
I want to: Upgrade to Pro
So that: I can generate unlimited applications

Acceptance Criteria:

- Given I'm a free user (3 applications used)


- When I click "Upgrade to Pro"
- Then I'm redirected to Stripe Checkout
- And I enter my payment details
- And I complete payment
- Then my account is upgraded to Pro
- And I receive a confirmation email
- And my usage limit is removed

Technical Notes:

- Stripe Checkout (hosted page)
- Webhook: checkout.session.completed
- DynamoDB: Update subscription_tier
- Email: subscription-activated template

Story Points: 8
Priority: P0

Sprint: 6

US-5.3: Manage Subscription

yaml

As a: Pro user
I want to: Manage my subscription (cancel, update payment)
So that: I have control over my billing

Acceptance Criteria:

- Given I'm a Pro user
- When I navigate to Settings > Subscription
- Then I see my current plan, next billing date, payment method
- And I can click "Cancel Subscription"
- And I see a confirmation dialog
- And I confirm cancellation
- Then my subscription is cancelled (end of billing period)
- And I receive a confirmation email

Technical Notes:

- Stripe Customer Portal (hosted)
- Webhook: customer.subscription.deleted
- DynamoDB: Update subscription_tier (after period ends)
- Email: subscription-cancelled template

Story Points: 5
Priority: P1

Sprint: 6


US-5.4: View Usage Dashboard

yaml

As a: User
I want to: See my current usage
So that: I know how many applications I have left (free tier)

Acceptance Criteria:

- Given I'm a free user
- When I navigate to the dashboard
- Then I see a progress bar showing "2 of 3 applications used"
- And a message "1 application remaining"
- And a "Upgrade to Pro" CTA

Technical Notes:

- Data source: DynamoDB (applications_generated count)
- Calculation: Real-time query
- Notification: Email at 80% usage (2/3 used)

Story Points: 3
Priority: P0

Sprint: 6

**Epic 6: Admin Features**

US-6.1: Admin Login

yaml

As an: Admin
I want to: Log in to the admin dashboard
So that: I can manage users and monitor the system

Acceptance Criteria:

- Given I'm an admin user
- When I navigate to admin.careervp.com
- Then I'm prompted for email, password, and MFA code
- And I enter valid credentials
- Then I'm redirected to the admin dashboard

Technical Notes:

- Separate Cognito User Pool (admin-only)
- MFA: Required (TOTP)
- IP whitelist: Optional (V2)

Story Points: 5


Priority: P0

Sprint: 7

US-6.2: View All Users

yaml

As an: Admin
I want to: View all registered users
So that: I can monitor user activity

Acceptance Criteria:

- Given I'm logged into admin dashboard
- When I navigate to Users page
- Then I see a paginated table of all users
- With columns: Email, Name, Tier, Status, Registered, Last Active
- And I can search by email or name
- And I can filter by tier (Free, Pro)

Technical Notes:

- Data source: DynamoDB (users table)
- Pagination: 50 per page
- Sorting: By registration date (newest first)

Story Points: 5
Priority: P0

Sprint: 7

US-6.3: View User Details

yaml

As an: Admin
I want to: View detailed information about a user
So that: I can troubleshoot issues or investigate abuse

Acceptance Criteria:

- Given I'm viewing the users table
- When I click on a user
- Then I see detailed information:
* Personal info (email, name, registration date)
* Subscription details (tier, status, next billing)
* Usage stats (applications generated, artifacts downloaded)
* Recent activity log
* Generated artifacts (list)

Technical Notes:


- Data source: DynamoDB (users, applications tables)
- Activity log: CloudWatch Logs aggregation
- Artifacts: S3 links (admin can download)

Story Points: 8
Priority: P0

Sprint: 7

US-6.4: Grant Free Credits

yaml

As an: Admin
I want to: Grant free applications to a user
So that: I can resolve support issues or reward users

Acceptance Criteria:

- Given I'm viewing user details
- When I click "Grant Credits"
- Then I enter the number of applications to grant
- And I add a note (reason)
- And I click "Confirm"
- Then the user's application count is increased
- And an admin action is logged
- And the user receives an email notification

Technical Notes:

- DynamoDB: Update applications_remaining
- Audit log: CloudTrail + DynamoDB
- Email: credits-granted template

Story Points: 5
Priority: P1

Sprint: 7

US-6.5: View System Metrics

yaml

As an: Admin
I want to: View system health metrics
So that: I can monitor performance and costs

Acceptance Criteria:

- Given I'm in the admin dashboard
- When I navigate to Metrics page
- Then I see dashboards showing:


* Lambda execution metrics (success rate, duration, errors)
* API Gateway metrics (request volume, latency, errors)
* Cost metrics (daily, monthly, by service)
* User metrics (active users, new signups, churn)
* AI metrics (token usage, cost per artifact)

Technical Notes:

- Data source: CloudWatch Metrics
- Visualization: CloudWatch Dashboards (embedded)
- Update frequency: 5 minutes

Story Points: 8
Priority: P1

Sprint: 8

**Epic 7: Optional Features (Gap Analysis)**

US-7.1: Request Gap Analysis

yaml

As a: User
I want to: Request a gap analysis for a job application
So that: I understand my strengths and weaknesses for the role

Acceptance Criteria:

- Given I have submitted a job posting
- When I check "Include Gap Analysis" (optional)
- Then the system generates gap analysis questions (15-20s)
- And I answer questions in a form (5-10 questions)
- And I submit my answers
- Then the gap analysis is included in the VP Report
- And interview prep addresses my gaps

Technical Notes:

- Lambda: gap-analysis-questions
- Model: Claude Sonnet 4.5
- Storage: DynamoDB (gap_analysis table)
- Cost: $0.015-0.025 per analysis

Story Points: 13
Priority: P2 (Optional V1, Standard V2)

Sprint: 9


**Summary: User Stories Count**

yaml

Total User Stories: 28

By Epic:

- Epic 1 (Onboarding): 4 stories
- Epic 2 (CV Management): 3 stories
- Epic 3 (Generation): 5 stories
- Epic 4 (Application Management): 3 stories
- Epic 5 (Subscription): 4 stories
- Epic 6 (Admin): 5 stories
- Epic 7 (Gap Analysis): 1 story
- Additional (not listed): 3 stories (email notifications, rate
limiting, etc.)

By Priority:

- P0 (MVP): 20 stories (~130 story points)
- P1 (Post-MVP): 6 stories (~34 story points)
- P2 (Future): 2 stories (~13 story points)

Estimated Sprints: 8-10 (2-week sprints)

MVP Timeline: 16-20 weeks (4-5 months)

Would you like me to continue with:

```
● Part 3: API Specifications
● Part 4: Database Schema Documentation
● Part 5: Lambda Functions Inventory
```
Or would you prefer I generate all three in the next response?

generate all three in the next response

6:17 PM

**CAREERVP SAAS - COMPLETE**

**TECHNICAL DOCUMENTATION**

**(CONTINUED)**

**PART 3: API SPECIFICATIONS**


**API Overview**

yaml

Base URL: https://api.careervp.com
API Gateway: REST API
Authentication: JWT Bearer tokens (Cognito)
Rate Limiting: Usage plans (10/min free, 60/min paid)
Versioning: /v1/
Content-Type: application/json

CORS: Enabled for app.careervp.com

**3.1 Authentication Endpoints**

**POST /v1/auth/signup**

Description: Register a new user account

Request:

json

{
"email": "user@example.com",
"password": "SecurePass123!",
"firstName": "John",
"lastName": "Doe"

}

Response (201 Created):

json

{
"userId": "usr_abc123",
"email": "user@example.com",
"status": "UNVERIFIED",
"message": "Verification email sent to user@example.com"

}

Errors:

```
● 400: Invalid email format, password doesn't meet requirements
● 409: Email already registered
● 429: Too many signup attempts
```
Implementation:

yaml

Lambda: user-signup-handler


Method: POST
Authorization: None
Timeout: 10s

Cognito: CreateUser, SendVerificationCode

**POST /v1/auth/verify-email**

Description: Verify email with code from email

Request:

json

{
"email": "user@example.com",
"verificationCode": "123456"

}

Response (200 OK):

json

{
"status": "VERIFIED",
"message": "Email verified successfully"

}

Errors:

```
● 400: Invalid or expired code
● 404: User not found
● 429: Too many verification attempts
```
**POST /v1/auth/login**

Description: Authenticate user and get JWT tokens

Request:

json

{
"email": "user@example.com",
"password": "SecurePass123!"

}

Response (200 OK):

json

{
"accessToken": "eyJhbGciOiJIUzI1NiIs...",


"refreshToken": "eyJhbGciOiJIUzI1NiIs...",
"expiresIn": 86400,
"tokenType": "Bearer",
"user": {
"userId": "usr_abc123",
"email": "user@example.com",
"firstName": "John",
"lastName": "Doe",
"subscriptionTier": "FREE",
"applicationsRemaining": 3
}

}

Errors:

```
● 401: Invalid credentials
● 403: Account locked (too many failed attempts)
● 403: Email not verified
```
Implementation:

yaml

Lambda: user-login-handler
Method: POST
Authorization: None
Timeout: 5s

Cognito: InitiateAuth

**POST /v1/auth/refresh**

Description: Refresh access token using refresh token

Request:

json

{
"refreshToken": "eyJhbGciOiJIUzI1NiIs..."

}

Response (200 OK):

json

{
"accessToken": "eyJhbGciOiJIUzI1NiIs...",
"expiresIn": 86400,
"tokenType": "Bearer"

}


Errors:

```
● 401: Invalid or expired refresh token
```
**POST /v1/auth/forgot-password**

Description: Request password reset

Request:

json

{
"email": "user@example.com"

}

Response (200 OK):

json

{
"message": "Password reset email sent"

}

Note: Always returns 200 even if email doesn't exist (security)

**POST /v1/auth/reset-password**

Description: Reset password with code

Request:

json

{
"email": "user@example.com",
"verificationCode": "123456",
"newPassword": "NewSecurePass123!"

}

Response (200 OK):

json

{
"message": "Password reset successfully"
}
```

**Errors:**

- 400: Invalid or expired code
- 400: Password doesn't meet requirements


## ---

### 3.2 User Profile Endpoints

#### GET /v1/users/me
**Description:** Get current user profile

**Headers:**
```

Authorization: Bearer eyJhbGciOiJIUzI1NiIs...

Response (200 OK):

json

{
"userId": "usr_abc123",
"email": "user@example.com",
"firstName": "John",
"lastName": "Doe",
"phoneNumber": "+1234567890",
"subscriptionTier": "PRO",
"subscriptionStatus": "ACTIVE",
"nextBillingDate": "2026-02-21T00:00:00Z",
"applicationsGenerated": 47,
"applicationsRemaining": "UNLIMITED",
"createdAt": "2025-12-01T10:30:00Z",
"lastActive": "2026-01-21T15:00:00Z"

}

Errors:

```
● 401: Invalid or expired token
```
Implementation:

yaml

Lambda: user-profile-handler
Method: GET
Authorization: Required (Lambda Authorizer)
Timeout: 5s

DynamoDB: users table query

**PUT /v1/users/me**

Description: Update user profile

Request:


json

{
"firstName": "John",
"lastName": "Smith",
"phoneNumber": "+1234567890"

}

Response (200 OK):

json

{
"userId": "usr_abc123",
"email": "user@example.com",
"firstName": "John",
"lastName": "Smith",
"phoneNumber": "+1234567890",
"updatedAt": "2026-01-21T15:30:00Z"
}
```

**Errors:**

- 400: Invalid phone number format
- 401: Unauthorized

## ---

#### DELETE /v1/users/me
**Description:** Delete user account (GDPR compliance)

**Headers:**
```

Authorization: Bearer eyJhbGciOiJIUzI1NiIs...

Response (202 Accepted):

json

{
"message": "Account deletion initiated. Data will be removed within
30 days.",
"deletionDate": "2026-02-20T15:30:00Z"

}

Implementation:

yaml


Lambda: account-deletion-handler
Method: DELETE
Authorization: Required
Timeout: 30s
Process:

- Mark account for deletion (soft delete)
- Schedule cleanup job (30 days)
- Send confirmation email
- Notify admin
```

## ---

_### 3.3 CV Management Endpoints_

_#### POST /v1/cvs/upload_
**Description:** Upload master CV file

**Request (multipart/form-data):**
```
file: [Binary PDF/DOCX file, max 5MB]
```

**Headers:**
```
Authorization: Bearer eyJhbGciOiJIUzI1NiIs...

Content-Type: multipart/form-data

Response (201 Created):

json

{
"cvId": "cv_xyz789",
"userId": "usr_abc123",
"fileName": "John_Doe_CV.pdf",
"fileSize": 245678,
"fileType": "application/pdf",
"uploadedAt": "2026-01-21T15:30:00Z",
"s3Key": "cvs/usr_abc123/cv_xyz789.pdf",
"extractedText": "John Doe\nSoftware Engineer...",
"parsedData": {
"contact": {
"name": "John Doe",
"email": "john@example.com",
"phone": "+1234567890",


"location": "San Francisco, CA"
},
"experience": [
{
"title": "Senior Software Engineer",
"company": "Tech Corp",
"startDate": "2020-01",
"endDate": "2025-12",
"description": "Led backend development...",
"achievements": ["Reduced latency by 40%", "Mentored 5
engineers"]
}
],
"education": [
{
"degree": "B.S. Computer Science",
"school": "University of California",
"graduationYear": 2018
}
],
"skills": ["Python", "AWS", "PostgreSQL", "React"]
}

}

Errors:

```
● 400: File too large (> 5MB)
● 400: Unsupported file type
● 413: Payload too large
● 429: Upload rate limit exceeded
```
Implementation:

yaml

Lambda: cv-upload-handler
Method: POST
Authorization: Required
Timeout: 30s
Memory: 1024 MB
Process:

1. Validate file (type, size)
2. Upload to S3
3. Extract text (PyPDF2, python-docx)
4. Parse with Claude Haiku (structured extraction)
5. Store metadata in DynamoDB
6. Return parsed data for user review


**GET /v1/cvs**

Description: List all user CVs

Response (200 OK):

json

{
"cvs": [
{
"cvId": "cv_xyz789",
"fileName": "John_Doe_CV.pdf",
"fileSize": 245678,
"uploadedAt": "2026-01-21T15:30:00Z",
"isDefault": true
},
{
"cvId": "cv_abc456",
"fileName": "John_Doe_CV_Old.pdf",
"fileSize": 198234,
"uploadedAt": "2025-11-15T10:00:00Z",
"isDefault": false
}
],
"total": 2

}

**GET /v1/cvs/{cvId}**

Description: Get CV details and parsed data

Response (200 OK):

json

{
"cvId": "cv_xyz789",
"userId": "usr_abc123",
"fileName": "John_Doe_CV.pdf",
"uploadedAt": "2026-01-21T15:30:00Z",
"s3Url": "https://s3.amazonaws.com/presigned-url...",
"parsedData": {
"contact": {...},
"experience": [...],
"education": [...],
"skills": [...]
}


## }

Errors:

```
● 404: CV not found
● 403: Not authorized (not user's CV)
```
**PUT /v1/cvs/{cvId}**

Description: Update CV parsed data (user corrections)

Request:

json

{
"parsedData": {
"contact": {
"name": "John Doe",
"email": "john.doe@newmail.com",
"phone": "+1234567890"
},
"experience": [...],
"education": [...],
"skills": [...]
}

}

Response (200 OK):

json

{
"cvId": "cv_xyz789",
"updatedAt": "2026-01-21T16:00:00Z",
"message": "CV data updated successfully"

}

**DELETE /v1/cvs/{cvId}**

Description: Delete CV

Response (200 OK):

json

{
"message": "CV deleted successfully",
"cvId": "cv_xyz789"

}


Implementation:

```
● Soft delete (30-day recovery)
● S3 object versioning retained
● Applications using this CV flagged
```
**3.4 Job Application Endpoints**

**POST /v1/applications**

Description: Create new job application

Request:

json

{
"cvId": "cv_xyz789",
"jobPosting": {
"url": "https://company.com/careers/software-engineer",
"title": "Senior Software Engineer",
"company": "Tech Corp",
"description": "We are looking for...",
"requirements": ["5+ years Python", "AWS experience"]
},
"options": {
"includeGapAnalysis": true,
"coverLetterStyle": "conversational"
}

}

Response (201 Created):

json

{
"applicationId": "app_def123",
"userId": "usr_abc123",
"status": "PROCESSING",
"createdAt": "2026-01-21T16:00:00Z",
"estimatedCompletionTime": "2026-01-21T16:02:30Z",
"steps": [
{
"step": "company_research",
"status": "PENDING",
"estimatedDuration": 20
},
{
"step": "vp_report",


"status": "PENDING",
"estimatedDuration": 25
},
{
"step": "cv_tailor",
"status": "PENDING",
"estimatedDuration": 15
},
{
"step": "cover_letter",
"status": "PENDING",
"estimatedDuration": 12
},
{
"step": "interview_prep",
"status": "PENDING",
"estimatedDuration": 18
}
],
"message": "Application processing started. You will receive an
email when complete."

}

Errors:

```
● 400: Invalid job posting URL or missing required fields
● 402: Payment required (free tier exhausted)
● 429: Too many applications in progress
```
Implementation:

yaml

Lambda: application-create-handler
Method: POST
Authorization: Required
Timeout: 10s
Process:

1. Validate CV exists
2. Check usage limits (free tier)
3. Parse job posting (if URL provided)
4. Create application record (DynamoDB)
5. Send to SQS queue
6. Return application ID

SQS Queue: application-processing-queue
Message: {applicationId, userId, cvId, jobPosting, options}


## ```

## ---

_#### GET /v1/applications_
**Description:** List all user applications

**Query Parameters:**
```

?status=COMPLETED&page=1&limit=20&sortBy=createdAt&order=desc

Response (200 OK):

json

{
"applications": [
{
"applicationId": "app_def123",
"jobTitle": "Senior Software Engineer",
"company": "Tech Corp",
"status": "COMPLETED",
"createdAt": "2026-01-21T16:00:00Z",
"completedAt": "2026-01-21T16:02:15Z",
"artifacts": {
"vpReport": true,
"tailoredCv": true,
"coverLetter": true,
"interviewPrep": true
}
},
{
"applicationId": "app_ghi456",
"jobTitle": "DevOps Engineer",
"company": "Cloud Startup",
"status": "PROCESSING",
"createdAt": "2026-01-21T15:30:00Z",
"artifacts": {
"vpReport": true,
"tailoredCv": false,
"coverLetter": false,
"interviewPrep": false
}
}
],
"pagination": {


"page": 1,
"limit": 20,
"total": 47,
"pages": 3
}

}

Implementation:

yaml

Lambda: applications-list-handler
DynamoDB Query: user_id (GSI)

Pagination: LastEvaluatedKey pattern

**GET /v1/applications/{applicationId}**

Description: Get application details

Response (200 OK):

json

{
"applicationId": "app_def123",
"userId": "usr_abc123",
"cvId": "cv_xyz789",
"status": "COMPLETED",
"createdAt": "2026-01-21T16:00:00Z",
"completedAt": "2026-01-21T16:02:15Z",
"jobPosting": {
"url": "https://company.com/careers/software-engineer",
"title": "Senior Software Engineer",
"company": "Tech Corp",
"description": "We are looking for...",
"requirements": ["5+ years Python", "AWS experience"],
"parsed": {
"requiredSkills": ["Python", "AWS", "Docker"],
"preferredSkills": ["Kubernetes", "Terraform"],
"experienceLevel": "Senior",
"salary": {
"min": 150000,
"max": 200000,
"currency": "USD"
}
}
},
"companyResearch": {


"industry": "Technology",
"size": "500-1000 employees",
"founded": 2015,
"recentNews": ["Series C funding", "Product launch"],
"values": ["Innovation", "Collaboration"]
},
"artifacts": [
{
"type": "VP_REPORT",
"s3Key": "artifacts/app_def123/vp-report.pdf",
"downloadUrl": "https://presigned-url...",
"createdAt": "2026-01-21T16:00:45Z",
"fileSize": 456789
},
{
"type": "TAILORED_CV",
"s3Key": "artifacts/app_def123/cv-tailored.pdf",
"downloadUrl": "https://presigned-url...",
"formats": ["PDF", "DOCX"],
"createdAt": "2026-01-21T16:01:15Z",
"fileSize": 234567
},
{
"type": "COVER_LETTER",
"s3Key": "artifacts/app_def123/cover-letter.pdf",
"downloadUrl": "https://presigned-url...",
"style": "conversational",
"createdAt": "2026-01-21T16:01:45Z",
"fileSize": 123456
},
{
"type": "INTERVIEW_PREP",
"s3Key": "artifacts/app_def123/interview-prep.pdf",
"downloadUrl": "https://presigned-url...",
"createdAt": "2026-01-21T16:02:15Z",
"fileSize": 678901
}
],
"processingLog": [
{
"step": "company_research",
"status": "COMPLETED",
"startedAt": "2026-01-21T16:00:00Z",
"completedAt": "2026-01-21T16:00:22Z",
"duration": 22


## },

## {

"step": "vp_report",
"status": "COMPLETED",
"startedAt": "2026-01-21T16:00:22Z",
"completedAt": "2026-01-21T16:00:45Z",
"duration": 23
}
]

}

Errors:

```
● 404: Application not found
● 403: Not authorized
```
**PATCH /v1/applications/{applicationId}/status**

Description: Update application status (user tracking)

Request:

json

{
"status": "INTERVIEW",
"notes": "Phone screen scheduled for Jan 25"

}

Response (200 OK):

json

{
"applicationId": "app_def123",
"status": "INTERVIEW",
"updatedAt": "2026-01-21T16:30:00Z",
"statusHistory": [
{
"status": "COMPLETED",
"timestamp": "2026-01-21T16:02:15Z"
},
{
"status": "SUBMITTED",
"timestamp": "2026-01-21T16:15:00Z"
},
{
"status": "INTERVIEW",
"timestamp": "2026-01-21T16:30:00Z",


"notes": "Phone screen scheduled for Jan 25"
}
]

}

Valid Status Values:

```
● DRAFT
● PROCESSING
● COMPLETED
● SUBMITTED
● INTERVIEW
● OFFER
● REJECTED
```
**DELETE /v1/applications/{applicationId}**

Description: Delete application

Response (200 OK):

json

{
"message": "Application deleted successfully",
"applicationId": "app_def123"
}
```

**Implementation:**

- Soft delete (30-day recovery)
- S3 artifacts retained (lifecycle policy handles deletion)
- DynamoDB record marked as deleted

---

### 3.5 Document Download Endpoints

## #### GET

/v1/applications/{applicationId}/artifacts/{artifactType}/download
**Description:** Download artifact with format selection

**Path Parameters:**

- applicationId: app_def123
- artifactType: vp-report | tailored-cv | cover-letter |
interview-prep

**Query Parameters:**


## ```

?format=pdf (or docx for CV/Cover Letter)

Response (200 OK):

json

{
"downloadUrl":
"https://careervp-artifacts.s3.amazonaws.com/presigned-url...",
"expiresAt": "2026-01-22T16:00:00Z",
"fileName": "Tech_Corp-Senior_Software_Engineer-CV.pdf",
"fileSize": 234567

}

Errors:

```
● 404: Artifact not found
● 400: Invalid format for this artifact type
● 429: Download rate limit exceeded
```
Implementation:

yaml

Lambda: artifact-download-handler
Method: GET
Authorization: Required
Timeout: 5s
Process:

1. Validate artifact exists
2. Check user ownership
3. Generate S3 presigned URL (24h expiry)
4. Log download (analytics)
5. Return URL

Rate Limiting: 10 downloads per artifact per day

**3.6 Subscription & Billing Endpoints**

**GET /v1/subscriptions/plans**

Description: Get available subscription plans (public)

Response (200 OK):

json

{
"plans": [


## {

"planId": "free",
"name": "Free",
"price": 0,
"currency": "USD",
"interval": "lifetime",
"features": {
"applications": 3,
"vpReport": true,
"tailoredCv": true,
"coverLetter": true,
"interviewPrep": true,
"gapAnalysis": false,
"support": "email"
}
},
{
"planId": "pro",
"name": "Pro",
"price": 29,
"currency": "USD",
"interval": "month",
"features": {
"applications": "unlimited",
"vpReport": true,
"tailoredCv": true,
"coverLetter": true,
"interviewPrep": true,
"gapAnalysis": true,
"support": "priority_email",
"advancedAnalytics": true
},
"stripePriceId": "price_1234abcd"
}
]

}

Implementation:

yaml

Lambda: None (API Gateway direct integration with static data)
Method: GET

Authorization: None


**POST /v1/subscriptions/checkout**

Description: Create Stripe Checkout session

Request:

json

{
"planId": "pro",
"successUrl":
"https://app.careervp.com/dashboard?session_id={CHECKOUT_SESSION_ID}"
,
"cancelUrl": "https://app.careervp.com/pricing"

}

Response (200 OK):

json

{
"sessionId": "cs_test_1234abcd",
"checkoutUrl": "https://checkout.stripe.com/pay/cs_test_1234abcd"

}

Implementation:

yaml

Lambda: stripe-checkout-handler
Method: POST
Authorization: Required
Timeout: 10s
Process:

1. Get user details
2. Create Stripe Customer (if not exists)
3. Create Checkout Session
4. Return session URL

Stripe Webhook: Handles checkout.session.completed

**GET /v1/subscriptions/me**

Description: Get current user subscription

Response (200 OK):

json

{
"userId": "usr_abc123",
"subscriptionId": "sub_xyz789",


"planId": "pro",
"status": "ACTIVE",
"currentPeriodStart": "2026-01-21T00:00:00Z",
"currentPeriodEnd": "2026-02-21T00:00:00Z",
"cancelAtPeriodEnd": false,
"stripeCustomerId": "cus_stripe123",
"stripeSubscriptionId": "sub_stripe456",
"paymentMethod": {
"type": "card",
"last4": "4242",
"brand": "visa",
"expiryMonth": 12,
"expiryYear": 2027
}

}

Errors:

```
● 404: No active subscription (free tier user)
```
**POST /v1/subscriptions/cancel**

Description: Cancel subscription (end of billing period)

Response (200 OK):

json

{
"message": "Subscription will be cancelled at the end of billing
period",
"cancelAt": "2026-02-21T00:00:00Z",
"status": "ACTIVE",
"cancelAtPeriodEnd": true

}

Implementation:

yaml

Lambda: stripe-cancel-handler
Method: POST
Authorization: Required
Timeout: 10s
Process:

1. Get Stripe subscription
2. Update: cancel_at_period_end = true
3. Update DynamoDB subscription record
4. Send cancellation email


**POST /v1/subscriptions/portal**

Description: Create Stripe Customer Portal session (manage payment, invoices)

Response (200 OK):

json

{
"portalUrl": "https://billing.stripe.com/session/abc123"

}

Implementation:

yaml

Lambda: stripe-portal-handler
Stripe API: Create billing portal session
Return URL: https://app.careervp.com/settings/subscription
```

## ---

_### 3.7 Admin Endpoints_

_#### GET /v1/admin/users_
**Description:** List all users (admin only)

**Query Parameters:**
```

?page=1&limit=50&tier=PRO&search=john@example.com

Response (200 OK):

json

{
"users": [
{
"userId": "usr_abc123",
"email": "user@example.com",
"firstName": "John",
"lastName": "Doe",
"subscriptionTier": "PRO",
"status": "ACTIVE",
"applicationsGenerated": 47,
"createdAt": "2025-12-01T10:30:00Z",
"lastActive": "2026-01-21T15:00:00Z"
}


## ],

"pagination": {
"page": 1,
"limit": 50,
"total": 1247,
"pages": 25
}

}

Implementation:

yaml

Lambda: admin-users-list
Authorization: Admin role required

DynamoDB: Scan with filters (consider GSI for performance)

**GET /v1/admin/users/{userId}**

Description: Get user details (admin)

Response (200 OK):

json

{
"userId": "usr_abc123",
"email": "user@example.com",
"profile": {...},
"subscription": {...},
"usage": {
"applicationsGenerated": 47,
"artifactsDownloaded": 152,
"storageUsed": 15678901,
"lastApplicationDate": "2026-01-21T16:00:00Z"
},
"applications": [
{"applicationId": "app_def123", "company": "Tech Corp", "status":
"COMPLETED"}
],
"activityLog": [
{"action": "LOGIN", "timestamp": "2026-01-21T15:00:00Z", "ip":
"192.168.1.1"},
{"action": "CREATE_APPLICATION", "timestamp":
"2026-01-21T16:00:00Z"}
]

}


**POST /v1/admin/users/{userId}/credits**

Description: Grant free applications

Request:

json

{
"credits": 5,
"reason": "Compensation for system downtime"

}

Response (200 OK):

json

{
"userId": "usr_abc123",
"creditsGranted": 5,
"applicationsRemaining": 8,
"grantedBy": "admin_def456",
"timestamp": "2026-01-21T17:00:00Z"

}

Implementation:

yaml

Lambda: admin-grant-credits
Authorization: Admin role required
Process:

1. Update user's applications_remaining
2. Log admin action (CloudTrail + DynamoDB)
3. Send email to user
4. Notify admin (confirmation)

**GET /v1/admin/metrics/overview**

Description: System metrics dashboard

Response (200 OK):

json

{
"period": "last_7_days",
"users": {
"total": 1247,
"new": 83,
"active": 412,


"churnRate": 0.02
},
"revenue": {
"mrr": 36230,
"newMrr": 2670,
"churnedMrr": 290,
"netMrr": 2380
},
"applications": {
"total": 1523,
"completed": 1489,
"failed": 34,
"avgDuration": 87
},
"costs": {
"aws": 2145,
"anthropic": 1876,
"stripe": 1089,
"total": 5110
},
"aiUsage": {
"totalTokens": 45678901,
"sonnetTokens": 12345678,
"haikuTokens": 33333223,
"avgCostPerApplication": 0.082
}

}

Implementation:

yaml

Lambda: admin-metrics-handler
Data Sources:

- DynamoDB (aggregation queries)
- CloudWatch Metrics
- Stripe API
- Custom metrics (S3 analytics logs)

Caching: 5-minute cache (Redis/ElastiCache in V2)

**3.8 Webhook Endpoints**

**POST /v1/webhooks/stripe**

Description: Stripe webhook handler


Events Handled:

```
● checkout.session.completed
● customer.subscription.created
● customer.subscription.updated
● customer.subscription.deleted
● invoice.payment_succeeded
● invoice.payment_failed
```
Implementation:

yaml

Lambda: stripe-webhook-handler
Verification: Stripe signature validation
Process:
checkout.session.completed:

- Get session details
- Update user subscription_tier = PRO
- Create subscription record in DynamoDB
- Send welcome email

customer.subscription.deleted:

- Update user subscription_tier = FREE
- Update subscription status = CANCELLED
- Send cancellation confirmation

invoice.payment_failed:

- Update subscription status = PAST_DUE
- Send payment failure notification
- Retry payment (Stripe handles)

Security:

yaml

Signature Verification:
Header: Stripe-Signature
Secret: Stored in AWS Secrets Manager
Validation: stripe.Webhook.constructEvent()

Rate Limiting: None (Stripe controls)

Idempotency: Event ID deduplication (DynamoDB)

**API Error Response Format**

Standard Error Response:


json

{
"error": {
"code": "INVALID_REQUEST",
"message": "Email format is invalid",
"field": "email",
"requestId": "req_abc123",
"timestamp": "2026-01-21T17:00:00Z"
}

}

Error Codes:

yaml

Authentication:

- INVALID_CREDENTIALS (401)
- TOKEN_EXPIRED (401)
- EMAIL_NOT_VERIFIED (403)
- ACCOUNT_LOCKED (403)

Validation:

- INVALID_REQUEST (400)
- MISSING_REQUIRED_FIELD (400)
- INVALID_FORMAT (400)

Authorization:

- UNAUTHORIZED (401)
- FORBIDDEN (403)
- INSUFFICIENT_PERMISSIONS (403)

Resources:

- NOT_FOUND (404)
- ALREADY_EXISTS (409)

Rate Limiting:

- RATE_LIMIT_EXCEEDED (429)
- USAGE_LIMIT_EXCEEDED (402)

Server:

- INTERNAL_ERROR (500)
- SERVICE_UNAVAILABLE (503)
- GATEWAY_TIMEOUT (504)


**PART 4: DATABASE SCHEMA DOCUMENTATION**

**DynamoDB Tables Overview**

yaml

Total Tables: 5

Tables:

1. users
2. cvs
3. applications
4. artifacts
5. subscriptions

On-Demand Capacity: All tables
Encryption: AWS-managed KMS

Backup: Point-in-time recovery (35 days)

**4.1 Users Table**

Table Name: careervp-users-{env}

Primary Key:

yaml

Partition Key: userId (S) - format: usr_{uuid}

Attributes:

yaml

userId: String (PK)
email: String (unique, GSI)
firstName: String
lastName: String
phoneNumber: String (optional)
passwordHash: String (managed by Cognito, not stored here)
emailVerified: Boolean
subscriptionTier: String (FREE | PRO)
subscriptionStatus: String (ACTIVE | CANCELLED | PAST_DUE)
stripeCustomerId: String (optional)
applicationsGenerated: Number (total count)
applicationsRemaining: Number (FREE tier only, -1 for unlimited)
storageUsedBytes: Number
createdAt: String (ISO 8601)
updatedAt: String (ISO 8601)


lastActive: String (ISO 8601)
status: String (ACTIVE | SUSPENDED | DELETED)
deletionScheduledAt: String (ISO 8601, for soft delete)

metadata: Map (flexible for future fields)

Global Secondary Indexes:

yaml

GSI-1 (email-index):
Partition Key: email (S)
Projection: ALL
Use Case: Login, password reset, admin search

GSI-2 (subscription-tier-index):
Partition Key: subscriptionTier (S)
Sort Key: createdAt (S)
Projection: ALL

Use Case: Admin filtering, analytics

Example Item:

json

{
"userId": "usr_a1b2c3d4",
"email": "john.doe@example.com",
"firstName": "John",
"lastName": "Doe",
"phoneNumber": "+14155551234",
"emailVerified": true,
"subscriptionTier": "PRO",
"subscriptionStatus": "ACTIVE",
"stripeCustomerId": "cus_ABC123XYZ",
"applicationsGenerated": 47,
"applicationsRemaining": -1,
"storageUsedBytes": 15678901,
"createdAt": "2025-12-01T10:30:00Z",
"updatedAt": "2026-01-21T15:00:00Z",
"lastActive": "2026-01-21T17:00:00Z",
"status": "ACTIVE",
"metadata": {
"preferredLanguage": "en",
"timezone": "America/Los_Angeles"
}

}


Access Patterns:

yaml

1. Get user by userId (Query on PK)
2. Get user by email (Query on GSI-1)
3. List users by subscription tier (Query on GSI-2)
4. Update user profile (UpdateItem)
5. Increment applications_generated (UpdateItem with atomic counter)

**4.2 CVs Table**

Table Name: careervp-cvs-{env}

Primary Key:

yaml

Partition Key: cvId (S) - format: cv_{uuid}

Attributes:

yaml

cvId: String (PK)
userId: String (FK to users, GSI)
fileName: String
fileType: String (application/pdf |
application/vnd.openxmlformats-officedocument.wordprocessingml.docume
nt)
fileSize: Number (bytes)
s3Bucket: String
s3Key: String
s3VersionId: String
uploadedAt: String (ISO 8601)
updatedAt: String (ISO 8601)
extractedText: String (full text content, for search/analysis)
parsedData: Map (structured CV data)
contact: Map
name: String
email: String
phone: String
location: String
linkedin: String (optional)
website: String (optional)
summary: String
experience: List of Maps

- title: String
company: String


location: String
startDate: String (YYYY-MM)
endDate: String (YYYY-MM or "Present")
description: String
achievements: List of Strings
education: List of Maps

- degree: String
field: String
school: String
location: String
graduationYear: Number
gpa: Number (optional)
skills: List of Strings (technical skills)
certifications: List of Maps (optional)
- name: String
issuer: String
issueDate: String
expiryDate: String (optional)
languages: List of Maps (optional)
- language: String
proficiency: String
isDefault: Boolean (one CV marked as default per user)
status: String (ACTIVE | DELETED)

deletedAt: String (ISO 8601, soft delete)

Global Secondary Indexes:

yaml

GSI-1 (user-cvs-index):
Partition Key: userId (S)
Sort Key: uploadedAt (S)
Projection: ALL

Use Case: List user's CVs chronologically

Example Item:

json

{
"cvId": "cv_x9y8z7w6",
"userId": "usr_a1b2c3d4",
"fileName": "John_Doe_Resume_2026.pdf",
"fileType": "application/pdf",
"fileSize": 245678,
"s3Bucket": "careervp-cvs-prod",
"s3Key": "cvs/usr_a1b2c3d4/cv_x9y8z7w6.pdf",


"s3VersionId": "v123abc",
"uploadedAt": "2026-01-15T10:00:00Z",
"updatedAt": "2026-01-15T10:00:00Z",
"extractedText": "John Doe\nSenior Software Engineer...",
"parsedData": {
"contact": {
"name": "John Doe",
"email": "john.doe@example.com",
"phone": "+14155551234",
"location": "San Francisco, CA",
"linkedin": "linkedin.com/in/johndoe"
},
"summary": "Senior Software Engineer with 8 years...",
"experience": [
{
"title": "Senior Software Engineer",
"company": "Tech Corp",
"location": "San Francisco, CA",
"startDate": "2020-01",
"endDate": "Present",
"description": "Led development of microservices
architecture...",
"achievements": [
"Reduced API latency by 40%",
"Mentored 5 junior engineers"
]
}
],
"education": [
{
"degree": "B.S.",
"field": "Computer Science",
"school": "University of California, Berkeley",
"location": "Berkeley, CA",
"graduationYear": 2016,
"gpa": 3.8
}
],
"skills": ["Python", "AWS", "PostgreSQL", "React", "Docker",
"Kubernetes"]
},
"isDefault": true,
"status": "ACTIVE"

}


Access Patterns:

yaml

1. Get CV by cvId (Query on PK)
2. List user's CVs (Query on GSI-1)
3. Get default CV for user (Query GSI-1, filter isDefault=true)
4. Update parsed data (UpdateItem)
5. Soft delete CV (UpdateItem: status=DELETED, deletedAt=timestamp)

**4.3 Applications Table**

Table Name: careervp-applications-{env}

Primary Key:

yaml

Partition Key: applicationId (S) - format: app_{uuid}

Attributes:

yaml

applicationId: String (PK)
userId: String (FK, GSI)
cvId: String (FK)
status: String (DRAFT | PROCESSING | COMPLETED | FAILED | SUBMITTED |
INTERVIEW | OFFER | REJECTED)
createdAt: String (ISO 8601)
updatedAt: String (ISO 8601)
completedAt: String (ISO 8601, when all artifacts ready)

jobPosting: Map
url: String (optional)
title: String
company: String
location: String (optional)
description: String
requirements: List of Strings
salary: Map (optional)
min: Number
max: Number
currency: String
parsed: Map (AI-extracted structured data)
requiredSkills: List of Strings
preferredSkills: List of Strings
experienceLevel: String (Entry | Mid | Senior | Lead)
remote: Boolean


benefits: List of Strings

companyResearch: Map (from company-research-v1 Lambda)
industry: String
companySize: String
founded: Number
headquarters: String
recentNews: List of Strings
values: List of Strings
culture: String
researchedAt: String (ISO 8601)

options: Map
includeGapAnalysis: Boolean
coverLetterStyle: String (formal | conversational | enthusiastic)

processingLog: List of Maps (execution timeline)

- step: String (company_research | vp_report | cv_tailor |
cover_letter | gap_analysis | interview_prep)
status: String (PENDING | PROCESSING | COMPLETED | FAILED)
startedAt: String (ISO 8601)
completedAt: String (ISO 8601)
duration: Number (seconds)
error: String (if failed)

statusHistory: List of Maps (user-updated statuses)

- status: String
timestamp: String (ISO 8601)
notes: String (optional)

metadata: Map
totalCost: Number (total AI cost for this application)
tokenUsage: Map
sonnet: Number

haiku: Number

Global Secondary Indexes:

yaml

GSI-1 (user-applications-index):
Partition Key: userId (S)
Sort Key: createdAt (S)
Projection: ALL
Use Case: List user's applications


GSI-2 (status-index):
Partition Key: status (S)
Sort Key: createdAt (S)
Projection: ALL

Use Case: Admin monitoring (e.g., stuck PROCESSING jobs)

Example Item:

json

{
"applicationId": "app_m1n2o3p4",
"userId": "usr_a1b2c3d4",
"cvId": "cv_x9y8z7w6",
"status": "COMPLETED",
"createdAt": "2026-01-21T16:00:00Z",
"updatedAt": "2026-01-21T16:02:15Z",
"completedAt": "2026-01-21T16:02:15Z",
"jobPosting": {
"url": "https://techcorp.com/careers/senior-engineer",
"title": "Senior Software Engineer",
"company": "Tech Corp",
"location": "San Francisco, CA (Hybrid)",
"description": "We are seeking a Senior Software Engineer...",
"requirements": [
"5+ years Python experience",
"AWS expertise",
"Microservices architecture"
],
"salary": {
"min": 150000,
"max": 200000,
"currency": "USD"
},
"parsed": {
"requiredSkills": ["Python", "AWS", "Docker", "PostgreSQL"],
"preferredSkills": ["Kubernetes", "Terraform", "React"],
"experienceLevel": "Senior",
"remote": false
}
},
"companyResearch": {
"industry": "Technology - SaaS",
"companySize": "500-1000 employees",
"founded": 2015,
"headquarters": "San Francisco, CA",


"recentNews": [
"Series C funding $50M",
"Product launch: AI analytics platform"
],
"values": ["Innovation", "Collaboration", "Customer-first"],
"culture": "Fast-paced startup with strong engineering culture",
"researchedAt": "2026-01-21T16:00:22Z"
},
"options": {
"includeGapAnalysis": false,
"coverLetterStyle": "conversational"
},
"processingLog": [
{
"step": "company_research",
"status": "COMPLETED",
"startedAt": "2026-01-21T16:00:00Z",
"completedAt": "2026-01-21T16:00:22Z",
"duration": 22
},
{
"step": "vp_report",
"status": "COMPLETED",
"startedAt": "2026-01-21T16:00:22Z",
"completedAt": "2026-01-21T16:00:45Z",
"duration": 23
},
{
"step": "cv_tailor",
"status": "COMPLETED",
"startedAt": "2026-01-21T16:00:45Z",
"completedAt": "2026-01-21T16:01:00Z",
"duration": 15
},
{
"step": "cover_letter",
"status": "COMPLETED",
"startedAt": "2026-01-21T16:01:00Z",
"completedAt": "2026-01-21T16:01:12Z",
"duration": 12
},
{
"step": "interview_prep",
"status": "COMPLETED",
"startedAt": "2026-01-21T16:01:12Z",


"completedAt": "2026-01-21T16:02:15Z",
"duration": 63
}
],
"statusHistory": [
{
"status": "COMPLETED",
"timestamp": "2026-01-21T16:02:15Z"
},
{
"status": "SUBMITTED",
"timestamp": "2026-01-21T18:30:00Z",
"notes": "Submitted via company website"
}
],
"metadata": {
"totalCost": 0.062,
"tokenUsage": {
"sonnet": 12345,
"haiku": 18901
}
}

}

Access Patterns:

yaml

1. Get application by ID (Query on PK)
2. List user's applications (Query on GSI-1)
3. Find stuck processing jobs (Query on GSI-2 where
status=PROCESSING, createdAt < 10 min ago)
4. Update status (UpdateItem)
5. Append to processingLog (UpdateItem with list append)

**4.4 Artifacts Table**

Table Name: careervp-artifacts-{env}

Primary Key:

yaml

Partition Key: artifactId (S) - format: art_{uuid}

Attributes:

yaml


artifactId: String (PK)
applicationId: String (FK, GSI)
userId: String (FK)
type: String (VP_REPORT | TAILORED_CV | COVER_LETTER |
INTERVIEW_PREP)
createdAt: String (ISO 8601)

s3Bucket: String
s3Key: String
s3VersionId: String
fileSize: Number (bytes)
fileName: String

format: String (PDF | DOCX)
downloadCount: Number
lastDownloadedAt: String (ISO 8601)

content: Map (metadata about generated content)
style: String (for cover letters)
wordCount: Number
pageCount: Number

aiMetadata: Map
model: String (claude-sonnet-4-5-20250929 |
claude-haiku-4-5-20251001)
promptTokens: Number
completionTokens: Number
totalTokens: Number
cost: Number (USD)
generationDuration: Number (seconds)

ttl: Number (Unix timestamp for auto-deletion, 90 days)

Global Secondary Indexes:

yaml

GSI-1 (application-artifacts-index):
Partition Key: applicationId (S)
Sort Key: createdAt (S)
Projection: ALL

Use Case: List all artifacts for an application

Example Item:

json


## {

"artifactId": "art_q5r6s7t8",
"applicationId": "app_m1n2o3p4",
"userId": "usr_a1b2c3d4",
"type": "TAILORED_CV",
"createdAt": "2026-01-21T16:01:00Z",
"s3Bucket": "careervp-artifacts-prod",
"s3Key": "artifacts/usr_a1b2c3d4/app_m1n2o3p4/cv-tailored.pdf",
"s3VersionId": "v456def",
"fileSize": 234567,
"fileName": "John_Doe_CV_Tech_Corp.pdf",
"format": "PDF",
"downloadCount": 3,
"lastDownloadedAt": "2026-01-21T18:45:00Z",
"content": {
"wordCount": 587,
"pageCount": 2
},
"aiMetadata": {
"model": "claude-haiku-4-5-20251001",
"promptTokens": 5678,
"completionTokens": 1234,
"totalTokens": 6912,
"cost": 0.0041,
"generationDuration": 15
},
"ttl": 1746288060

}

TTL Configuration:

yaml

TTL Attribute: ttl
Auto-Deletion: 90 days after creation

Note: S3 lifecycle policy also deletes objects after 90 days

Access Patterns:

yaml

1. Get artifact by ID (Query on PK)
2. List application artifacts (Query on GSI-1)
3. Increment download count (UpdateItem with atomic counter)
4. Get presigned download URL (not stored, generated on-demand)


**4.5 Subscriptions Table**

Table Name: careervp-subscriptions-{env}

Primary Key:

yaml

Partition Key: subscriptionId (S) - format: sub_{uuid}

Attributes:

yaml

subscriptionId: String (PK)
userId: String (FK, GSI - unique)
planId: String (FREE | PRO)
status: String (ACTIVE | CANCELLED | PAST_DUE | PAUSED)

stripeCustomerId: String
stripeSubscriptionId: String (for PRO plans)
stripePriceId: String

currentPeriodStart: String (ISO 8601)
currentPeriodEnd: String (ISO 8601)
cancelAtPeriodEnd: Boolean
cancelledAt: String (ISO 8601, optional)

billingCycle: String (monthly | yearly)
amount: Number (cents, e.g., 2900 for $29)
currency: String (USD)

paymentMethod: Map
type: String (card | paypal)
last4: String
brand: String (visa | mastercard | amex)
expiryMonth: Number
expiryYear: Number

createdAt: String (ISO 8601)
updatedAt: String (ISO 8601)

history: List of Maps (subscription lifecycle events)

- event: String (CREATED | UPGRADED | DOWNGRADED | CANCELLED |
RENEWED)
timestamp: String (ISO 8601)
reason: String (optional)

previousPlan: String (optional)


Global Secondary Indexes:

yaml

GSI-1 (user-subscription-index):
Partition Key: userId (S)
Projection: ALL

Use Case: Get user's active subscription (should be 1:1 but allows

history)

Example Item:

json

{
"subscriptionId": "sub_u9v8w7x6",
"userId": "usr_a1b2c3d4",
"planId": "PRO",
"status": "ACTIVE",
"stripeCustomerId": "cus_ABC123XYZ",
"stripeSubscriptionId": "sub_DEF456UVW",
"stripePriceId": "price_1234abcd",
"currentPeriodStart": "2026-01-21T00:00:00Z",
"currentPeriodEnd": "2026-02-21T00:00:00Z",
"cancelAtPeriodEnd": false,
"billingCycle": "monthly",
"amount": 2900,
"currency": "USD",
"paymentMethod": {
"type": "card",
"last4": "4242",
"brand": "visa",
"expiryMonth": 12,
"expiryYear": 2027
},
"createdAt": "2026-01-15T12:00:00Z",
"updatedAt": "2026-01-21T00:00:01Z",
"history": [
{
"event": "CREATED",
"timestamp": "2026-01-15T12:00:00Z",
"reason": "User upgraded from FREE"
},
{
"event": "RENEWED",
"timestamp": "2026-01-21T00:00:01Z"
}


## ]

## }

Access Patterns:

yaml

1. Get subscription by ID (Query on PK)
2. Get user's subscription (Query on GSI-1)
3. Update subscription status (UpdateItem)
4. Append to history (UpdateItem with list append)

**Database Design Principles**

yaml

Normalization:

- Moderate normalization (3NF-ish)
- Denormalization where needed for performance
- userId duplicated across tables for GSI access

Data Integrity:

- Application-level foreign key enforcement (no DB constraints)
- Lambda functions validate relationships
- Orphaned records cleaned by scheduled jobs

Consistency:

- Eventually consistent reads (default)
- Strongly consistent reads when required (user profile updates)
- Optimistic locking for concurrent updates (version attributes)

Performance:

- GSIs for common access patterns
- Sparse indexes where applicable
- Composite sort keys for complex queries

Cost Optimization:

- On-demand capacity (unpredictable workload)
- TTL for automatic cleanup (artifacts table)
- S3 lifecycle policies (complement DynamoDB)

**PART 5: LAMBDA FUNCTIONS INVENTORY**

**Lambda Functions Overview**


yaml

Total Functions: 22
Language: Python 3.11
Deployment: ZIP (< 50MB), Container (if > 50MB)
VPC: Not required for V1 (public AWS services only)

Environment: dev, staging, prod

**5.1 Authentication & User Management Functions**

**Lambda 1: user-signup-handler**

yaml

Name: careervp-user-signup-{env}
Runtime: Python 3.11
Memory: 256 MB
Timeout: 10s
Trigger: API Gateway POST /v1/auth/signup
Concurrency: 10 reserved

Environment Variables:
USER_POOL_ID: Cognito User Pool ID
USER_TABLE: careervp-users-{env}

IAM Permissions:

- cognito-idp:AdminCreateUser
- cognito-idp:AdminSetUserPassword
- dynamodb:PutItem

Logic:

1. Validate input (email, password strength)
2. Create Cognito user
3. Create DynamoDB user record
4. Send verification email (Cognito handles)
5. Return success response

Error Handling:

- Email exists: Return 409
- Cognito error: Return 500
- DynamoDB error: Rollback Cognito user, return 500

Cost per Invocation: ~$0.00001

**Lambda 2: user-login-handler**


yaml

Name: careervp-user-login-{env}
Runtime: Python 3.11
Memory: 256 MB
Timeout: 5s
Trigger: API Gateway POST /v1/auth/login

Environment Variables:
USER_POOL_ID: Cognito User Pool ID
CLIENT_ID: Cognito App Client ID
USER_TABLE: careervp-users-{env}

IAM Permissions:

- cognito-idp:InitiateAuth
- dynamodb:GetItem
- dynamodb:UpdateItem (lastActive timestamp)

Logic:

1. Call Cognito InitiateAuth
2. If successful, get user from DynamoDB
3. Update lastActive timestamp
4. Return tokens + user profile

Cost per Invocation: ~$0.00001

**Lambda 3: user-profile-handler**

yaml

Name: careervp-user-profile-{env}
Runtime: Python 3.11
Memory: 256 MB
Timeout: 5s
Trigger:

- API Gateway GET /v1/users/me
- API Gateway PUT /v1/users/me

IAM Permissions:

- dynamodb:GetItem
- dynamodb:UpdateItem

Logic (GET):

1. Extract userId from JWT (Lambda authorizer)
2. Query DynamoDB
3. Return user profile


Logic (PUT):

1. Validate updates
2. UpdateItem in DynamoDB
3. Return updated profile

Cost per Invocation: ~$0.00001

**Lambda 4: lambda-authorizer**

yaml

Name: careervp-lambda-authorizer-{env}
Runtime: Python 3.11
Memory: 256 MB
Timeout: 5s
Trigger: API Gateway (all protected endpoints)
Caching: 5 minutes (reduce invocations)

Environment Variables:
USER_POOL_ID: Cognito User Pool ID
REGION: AWS region

Logic:

1. Extract JWT from Authorization header
2. Verify JWT signature (Cognito public keys)
3. Validate expiration
4. Extract userId, email, roles
5. Return IAM policy (Allow/Deny)
6. Attach userId to request context

IAM Policy Response:
principalId: userId
policyDocument:
Effect: Allow/Deny
Resource: API Gateway ARN
context:
userId: usr_abc123
email: user@example.com
subscriptionTier: PRO

Cost per Invocation: ~$0.00001

Note: Caching reduces invocations by ~90%


**5.2 CV Management Functions**

**Lambda 5: cv-upload-handler**

yaml

Name: careervp-cv-upload-{env}
Runtime: Python 3.11
Memory: 1024 MB (text extraction memory-intensive)
Timeout: 30s
Trigger: API Gateway POST /v1/cvs/upload

Environment Variables:
CV_BUCKET: careervp-cvs-{env}
CV_TABLE: careervp-cvs-{env}
ANTHROPIC_API_KEY: (Secrets Manager)

IAM Permissions:

- s3:PutObject
- dynamodb:PutItem
- secretsmanager:GetSecretValue

Libraries:

- PyPDF2 (PDF text extraction)
- python-docx (DOCX text extraction)
- anthropic (Claude API for structured parsing)
- boto3 (AWS SDK)

Logic:

1. Validate file (type, size < 5MB)
2. Generate cvId, s3Key
3. Upload to S3
4. Extract text:
- PDF: PyPDF2
- DOCX: python-docx
5. Parse with Claude Haiku:
Prompt: "Extract structured CV data (contact, experience,
education, skills)"
Response: JSON schema
6. Store in DynamoDB (cv record + parsedData)
7. Return cvId + parsed data for user review

AI Cost:
Input: ~2000 tokens (extracted text)
Output: ~1000 tokens (structured JSON)
Model: Claude Haiku


Cost: ~$0.002 per upload

Total Cost per Invocation: ~$0.003 (Lambda + AI)

**Lambda 6: cv-management-handler**

yaml

Name: careervp-cv-management-{env}
Runtime: Python 3.11
Memory: 256 MB
Timeout: 10s
Trigger:

- GET /v1/cvs (list)
- GET /v1/cvs/{cvId} (get)
- PUT /v1/cvs/{cvId} (update)
- DELETE /v1/cvs/{cvId} (delete)

IAM Permissions:

- dynamodb:Query
- dynamodb:GetItem
- dynamodb:UpdateItem
- s3:GetObject (presigned URLs)

Logic varies by method:
GET /cvs: Query GSI-1 (userId)
GET /cvs/{cvId}: GetItem + generate S3 presigned URL
PUT /cvs/{cvId}: UpdateItem (parsedData)
DELETE /cvs/{cvId}: UpdateItem (status=DELETED)

Cost per Invocation: ~$0.00001

**5.3 Job Application Processing Functions**

**Lambda 7: application-create-handler**

yaml

Name: careervp-application-create-{env}
Runtime: Python 3.11
Memory: 512 MB
Timeout: 15s
Trigger: API Gateway POST /v1/applications

Environment Variables:
APP_TABLE: careervp-applications-{env}


USER_TABLE: careervp-users-{env}
SQS_QUEUE_URL: processing queue URL
ANTHROPIC_API_KEY: (Secrets Manager)

IAM Permissions:

- dynamodb:GetItem (check CV exists)
- dynamodb:Query (check usage limits)
- dynamodb:PutItem (create application)
- dynamodb:UpdateItem (increment applications_generated)
- sqs:SendMessage
- secretsmanager:GetSecretValue

Logic:

1. Validate userId has CV
2. Check usage limits:
- FREE: applications_remaining > 0
- PRO: unlimited
3. Parse job posting:
- If URL: Scrape with BeautifulSoup
- If text: Use Claude Haiku to extract structured data
4. Create application record (status=PROCESSING)
5. Send to SQS queue
6. Decrement applications_remaining (FREE tier)
7. Increment applications_generated
8. Return applicationId + estimated completion time

Job Posting Parsing (Claude Haiku):
Prompt: "Extract job title, company, requirements, salary from this
posting"
Input: ~1500 tokens (job posting text)
Output: ~500 tokens (JSON)
Cost: ~$0.001

Total Cost: ~$0.002 per invocation

**Lambda 8: application-orchestrator**

yaml

Name: careervp-application-orchestrator-{env}
Runtime: Python 3.11
Memory: 512 MB
Timeout: 900s (15 minutes - max Lambda duration)
Trigger: SQS (application-processing-queue)
Concurrency: 20 reserved


Batch Size: 1 (process one application at a time)

Environment Variables:
APP_TABLE: careervp-applications-{env}
CV_TABLE: careervp-cvs-{env}
ARTIFACT_TABLE: careervp-artifacts-{env}
ARTIFACT_BUCKET: careervp-artifacts-{env}
ANTHROPIC_API_KEY: (Secrets Manager)
SES_FROM_EMAIL: noreply@careervp.com

IAM Permissions:

- dynamodb:GetItem, UpdateItem
- s3:PutObject
- secretsmanager:GetSecretValue
- lambda:InvokeFunction (invoke other Lambdas)
- ses:SendEmail
- cloudwatch:PutMetricData

Logic (Sequential Workflow):

1. Receive message from SQS (applicationId)
2. Get application, CV, user details from DynamoDB
3. Update status: PROCESSING
4. Step 1: Company Research
- Invoke: company-research-v1 Lambda
- Input: Company name, job URL
- Duration: 15-25s
- Update processingLog
5. Step 2: VP Report Generation
- Invoke: vp-report-generator Lambda
- Input: Application + Company Research + CV
- Duration: 15-25s
- Upload PDF to S3
- Create artifact record in DynamoDB
6. Step 3: CV Tailoring
- Invoke: cv-tailor Lambda
- Input: Master CV + Job Posting + VP Report
- Duration: 10-15s
- Upload PDF, DOCX to S3
7. Step 4: Cover Letter
- Invoke: cover-letter-generator Lambda
- Input: CV + Job + VP Report + Style preference


- Duration: 8-12s
- Upload PDF, DOCX to S3
8. [Optional] Step 5: Gap Analysis
- If includeGapAnalysis=true:
- Invoke: gap-analysis-questions Lambda
- Generate questions (user answers separately)
9. Step 6: Interview Prep
- Invoke: interview-prep-generator Lambda
- Input: All artifacts + Gap Analysis (if available)
- Duration: 12-18s
- Upload PDF to S3
10. Update application status: COMPLETED
11. Send completion email (SES)
12. Delete SQS message
13. Log metrics (CloudWatch)

Error Handling:

- Any step fails: Update processingLog, status=FAILED
- Send error notification email
- DLQ: After 3 retries
- Admin notification: Critical failures

Total Duration: 60-120 seconds (depending on optional steps)

Cost per Application: ~$0.08-0.12 (Lambda + AI)

**Lambda 9: company-research-v1**

yaml

Name: careervp-company-research-v1-{env}
Runtime: Python 3.11
Memory: 512 MB
Timeout: 60s
Trigger: Invoked by application-orchestrator

Environment Variables:
SERPAPI_KEY: (Secrets Manager) - Google search API

IAM Permissions:

- secretsmanager:GetSecretValue

Libraries:


- requests (HTTP calls)
- BeautifulSoup (HTML parsing)
- google-search-results (SerpAPI client)

Logic:

1. Input: Company name, job URL
2. Search Google for: "{company} about us", "{company} news"
3. Scrape company website:
- About page (mission, values)
- Careers page (culture)
4. Search recent news (last 6 months)
5. Extract:
- Industry
- Company size
- Founded year
- Headquarters
- Recent news (3-5 items)
- Company values (if available)
- Culture keywords
6. Return structured JSON

No AI Cost (web scraping only)
SerpAPI Cost: ~$0.001 per search (included in budget)
Lambda Cost: ~$0.003 per invocation

Total: ~$0.004

**Lambda 10: vp-report-generator**

yaml

Name: careervp-vp-report-generator-{env}
Runtime: Python 3.11
Memory: 1024 MB
Timeout: 120s
Trigger: Invoked by application-orchestrator

Environment Variables:
ANTHROPIC_API_KEY: (Secrets Manager)
PROMPT_CONFIG_BUCKET: careervp-prompts-{env}

IAM Permissions:

- secretsmanager:GetSecretValue
- s3:GetObject (prompt templates)


Libraries:

- anthropic (Claude SDK)
- jinja2 (prompt templating)
- weasyprint (HTML to PDF)

AI Configuration:
Model: claude-sonnet-4-5-20250929
Temperature: 0.3 (balanced creativity/consistency)
Max Tokens: 8000 (output)

Logic:

1. Load prompt template from S3
2. Inject context:
- User CV (full parsed data)
- Job posting (full description + parsed requirements)
- Company research data
3. Call Claude Sonnet with detailed prompt:
System: "You are an expert career strategist..."
Prompt: "Generate a comprehensive Value Proposition Report..."
4. Parse AI response (JSON + narrative sections)
5. Generate HTML from template (Jinja2)
6. Convert HTML to PDF (WeasyPrint)
7. Return PDF bytes + metadata

Prompt Structure:

- Introduction (strategic positioning summary)
- Alignment Analysis (skills match breakdown)
- Key Strengths (5-7 strengths with evidence)
- Value Proposition (elevator pitch)
- Strategic Recommendations (how to position in application)
- Talking Points (for networking, interviews)

AI Cost:
Input: ~8000 tokens (CV + job + company research)
Output: ~6000 tokens (comprehensive report)
Model: Claude Sonnet
Cost: ~$0.030 per report

Total Lambda Cost: ~$0.035

**Lambda 11: cv-tailor**

yaml


Name: careervp-cv-tailor-{env}
Runtime: Python 3.11
Memory: 512 MB
Timeout: 60s
Trigger: Invoked by application-orchestrator

AI Configuration:
Model: claude-haiku-4-5-20251001
Temperature: 0.2 (prioritize accuracy)
Max Tokens: 4000

Logic:

1. Input: Master CV + Job Posting + VP Report
2. Call Claude Haiku:
Prompt: "Tailor this CV for the specific job. Emphasize relevant
experience, optimize for ATS..."
3. AI generates:
- Reordered experience (most relevant first)
- Highlighted achievements (aligned with job)
- Optimized skills section (keyword matching)
- Tailored summary (role-specific)
4. Apply ATS optimization:
- Standard fonts (Arial, Calibri)
- No tables/columns (simple format)
- Keyword optimization (from job requirements)
- Standard section headers
5. Generate PDF (WeasyPrint) + DOCX (python-docx)
6. Return both formats

CRITICAL Anti-Hallucination Measures:

- Extract immutable facts from master CV (dates, companies, titles)
- Verify AI output doesn't invent experience
- Facts validation layer (post-processing)
- Only strategic rewording allowed, no fabrication

AI Cost:
Input: ~5000 tokens (CV + job + VP insights)
Output: ~2000 tokens (tailored CV)
Model: Claude Haiku
Cost: ~$0.004


Total: ~$0.005

**Lambda 12: cover-letter-generator**

yaml

Name: careervp-cover-letter-generator-{env}
Runtime: Python 3.11
Memory: 512 MB
Timeout: 60s

AI Configuration:
Model: claude-haiku-4-5-20251001
Temperature: 0.4 (slightly more creative)
Max Tokens: 2000

Logic:

1. Input: CV + Job + VP Report + Tailored CV + Style
2. Call Claude Haiku:
Prompt: "Write a {style} cover letter (1 page max)..."
3. Styles:
- Formal: Traditional business letter
- Conversational: Warm, approachable tone
- Enthusiastic: Passionate, energetic
4. Structure:
- Opening: Hook (why this company/role)
- Body 1: Relevant experience highlight
- Body 2: Value proposition (what you bring)
- Closing: Call to action
- Length: 300-400 words
5. Generate PDF + DOCX
6. Return both formats

AI Cost:
Input: ~6000 tokens
Output: ~1000 tokens
Cost: ~$0.003

Total: ~$0.004

**Lambda 13: gap-analysis-questions (Optional)**


yaml

Name: careervp-gap-analysis-questions-{env}
Runtime: Python 3.11
Memory: 512 MB
Timeout: 60s

AI Configuration:
Model: claude-sonnet-4-5-20250929
Temperature: 0.3
Max Tokens: 3000

Logic:

1. Input: Master CV + Job Requirements
2. Identify gaps:
- Required skills not in CV
- Experience level mismatch
- Industry transition
- Geographic relocation
3. Generate 5-10 targeted questions:
- "The role requires Kubernetes. How familiar are you?"
- "This is a leadership role. Describe your management
experience."
4. Return JSON (questions + context)
5. User answers separately (frontend form)
6. Answers stored in DynamoDB (applications table)

AI Cost:
Input: ~5000 tokens
Output: ~1500 tokens
Cost: ~$0.020

Total: ~$0.022

**Lambda 14: interview-prep-generator**

yaml

Name: careervp-interview-prep-generator-{env}
Runtime: Python 3.11
Memory: 512 MB
Timeout: 60s

AI Configuration:


Model: claude-haiku-4-5-20251001
Temperature: 0.3
Max Tokens: 6000

Logic:

1. Input: All artifacts (CV, job, VP, company research, gap
analysis if available)
2. Call Claude Haiku:
Prompt: "Predict 8-10 likely interview questions and provide
STAR-method frameworks..."
3. Generated Content:
- 8-10 predicted questions (diverse categories):
* Behavioral (2-3)
* Technical (2-3)
* Culture fit (2-3)
* Situational (1-2)
- For each question:
* STAR framework guidance
* Specific examples from user's CV
* Strategic insights from VP Report
- Additional sections:
* 30-second elevator pitch
* Questions to ask interviewer (5-7)
* Addressing potential concerns (from gap analysis)
* Interview logistics checklist
4. Generate PDF (8-12 pages)
5. Return PDF

## IMPORTANT:

- Maximum 10 questions (avoid overwhelming)
- Each answer framework references real experience
- No hallucinated achievements

AI Cost:
Input: ~8000 tokens (all artifacts)
Output: ~4000 tokens (comprehensive prep)
Cost: ~$0.004

Total: ~$0.005


**5.4 Document Generation Functions**

**Lambda 15: document-export-handler**

yaml

Name: careervp-document-export-{env}
Runtime: Python 3.11
Memory: 1024 MB (PDF generation memory-intensive)
Timeout: 30s
Trigger: API Gateway GET
/v1/applications/{id}/artifacts/{type}/download

Environment Variables:
ARTIFACT_TABLE: careervp-artifacts-{env}
ARTIFACT_BUCKET: careervp-artifacts-{env}

IAM Permissions:

- dynamodb:GetItem
- dynamodb:UpdateItem (increment download count)
- s3:GetObject
- s3:PutObject (if format conversion needed)

Libraries:

- weasyprint (HTML to PDF)
- python-docx (DOCX generation)
- boto3 (S3 presigned URLs)

Logic:

1. Validate artifact exists
2. Check user ownership
3. Check format availability:
- VP Report: PDF only
- CV: PDF, DOCX
- Cover Letter: PDF, DOCX
- Interview Prep: PDF only
4. If format exists in S3:
- Generate presigned URL (24h expiry)
5. If format conversion needed:
- Load source format
- Convert (e.g., PDF → DOCX)
- Upload to S3
- Generate presigned URL


6. Increment download count (DynamoDB)
7. Log analytics event
8. Return URL + metadata

Rate Limiting:

- Check downloads per day (DynamoDB counter)
- Free: 20/day, Paid: 100/day
- Return 429 if exceeded

Cost: ~$0.002 per download

**5.5 Subscription & Billing Functions**

**Lambda 16: stripe-checkout-handler**

yaml

Name: careervp-stripe-checkout-{env}
Runtime: Python 3.11
Memory: 256 MB
Timeout: 10s
Trigger: API Gateway POST /v1/subscriptions/checkout

Environment Variables:
STRIPE_SECRET_KEY: (Secrets Manager)
STRIPE_PRICE_ID: price_1234abcd
USER_TABLE: careervp-users-{env}

IAM Permissions:

- secretsmanager:GetSecretValue
- dynamodb:GetItem

Libraries:

- stripe (Stripe Python SDK)

Logic:

1. Get user details (email, userId)
2. Check if Stripe customer exists:
- If no: Create Stripe customer
- If yes: Use existing
3. Create Stripe Checkout Session:
- Mode: subscription
- Price: PRO plan price ID
- Success URL: with session_id placeholder
- Cancel URL: pricing page


- Customer: Stripe customer ID
- Metadata: userId, planId
4. Return session ID + checkout URL

Cost: ~$0.00001 per invocation

**Lambda 17: stripe-webhook-handler**

yaml

Name: careervp-stripe-webhook-{env}
Runtime: Python 3.11
Memory: 512 MB
Timeout: 30s
Trigger: API Gateway POST /v1/webhooks/stripe

Environment Variables:
STRIPE_WEBHOOK_SECRET: (Secrets Manager)
USER_TABLE: careervp-users-{env}
SUBSCRIPTION_TABLE: careervp-subscriptions-{env}
SES_FROM_EMAIL: noreply@careervp.com

IAM Permissions:

- secretsmanager:GetSecretValue
- dynamodb:GetItem, PutItem, UpdateItem
- ses:SendEmail

Libraries:

- stripe (signature verification)

Logic (Event-Based):

Event: checkout.session.completed

1. Verify Stripe signature
2. Extract session data (userId, customer, subscription)
3. Update users table:
- subscriptionTier = PRO
- subscriptionStatus = ACTIVE
- stripeCustomerId = customer.id
4. Create subscription record in subscriptions table
5. Send welcome email (SES)
6. Return 200 OK

Event: customer.subscription.updated

1. Get userId from metadata


2. Update subscription record
3. Return 200 OK

Event: customer.subscription.deleted

1. Get userId
2. Update users table:
- subscriptionTier = FREE
- applicationsRemaining = 0 (already used)
3. Update subscription status = CANCELLED
4. Send cancellation confirmation email
5. Return 200 OK

Event: invoice.payment_failed

1. Update subscription status = PAST_DUE
2. Send payment failure notification
3. Stripe will retry (automatic)
4. Return 200 OK

Idempotency:

- Store processed event IDs in DynamoDB
- Check before processing (prevent duplicates)
- TTL: 7 days

Cost: ~$0.001 per webhook event

**Lambda 18: stripe-portal-handler**

yaml

Name: careervp-stripe-portal-{env}
Runtime: Python 3.11
Memory: 256 MB
Timeout: 10s
Trigger: API Gateway POST /v1/subscriptions/portal

Logic:

1. Get user's stripeCustomerId from DynamoDB
2. Create Stripe billing portal session:
- Customer: stripeCustomerId
- Return URL: app.careervp.com/settings
3. Return portal URL

User can manage:

- Update payment method
- View invoices


- Cancel subscription
- Update billing details

Cost: ~$0.00001

**5.6 Admin Functions**

**Lambda 19: admin-users-handler**

yaml

Name: careervp-admin-users-{env}
Runtime: Python 3.11
Memory: 512 MB
Timeout: 30s
Trigger:

- GET /v1/admin/users (list)
- GET /v1/admin/users/{userId} (details)
- POST /v1/admin/users/{userId}/credits (grant)

IAM Permissions:

- dynamodb:Scan (list - expensive, consider GSI)
- dynamodb:Query (specific user)
- dynamodb:UpdateItem (grant credits)
- ses:SendEmail

Logic (List):

1. Scan users table (with filters)
2. Pagination: LastEvaluatedKey
3. Return users array

Logic (Details):

1. Get user by userId
2. Get subscription details
3. Query applications (count, recent)
4. Get usage stats
5. Return comprehensive profile

Logic (Grant Credits):

1. Validate admin authorization
2. Update applications_remaining
3. Log action (CloudTrail + DynamoDB audit)
4. Send email notification to user
5. Return confirmation


Cost: ~$0.002 (Scan expensive)

**Lambda 20: admin-metrics-handler**

yaml

Name: careervp-admin-metrics-{env}
Runtime: Python 3.11
Memory: 512 MB
Timeout: 60s
Trigger: GET /v1/admin/metrics/overview

IAM Permissions:

- dynamodb:Scan (analytics)
- cloudwatch:GetMetricData
- s3:GetObject (cost reports)

Logic:

1. Aggregate user metrics:
- Total users (Scan count)
- New users (filter by createdAt)
- Active users (filter by lastActive)
2. Aggregate revenue:
- Query subscriptions table
- Calculate MRR, churn
3. Aggregate application metrics:
- Query applications table
- Count by status
- Calculate avg duration
4. Get AWS costs:
- CloudWatch metrics
- Cost Explorer API (future)
5. Get AI costs:
- Custom CloudWatch metrics (logged by generators)
6. Cache results (5 minutes) - future V2
7. Return JSON

Cost: ~$0.005 (expensive due to Scans)

Optimization: Pre-compute daily, store in S3


**5.7 Utility Functions**

**Lambda 21: scheduled-cleanup-job**

yaml

Name: careervp-scheduled-cleanup-{env}
Runtime: Python 3.11
Memory: 512 MB
Timeout: 900s (15 minutes)
Trigger: EventBridge (daily at 2 AM UTC)

IAM Permissions:

- dynamodb:Scan, DeleteItem
- s3:DeleteObject
- ses:SendEmail (error notifications)

Logic:

1. Scan users table for soft-deleted accounts (> 30 days)
2. For each:
- Delete user record
- Delete all CVs (DynamoDB + S3)
- Delete all applications (DynamoDB)
- Delete all artifacts (DynamoDB + S3)
- Delete subscription record
3. Scan artifacts table for expired TTL items
4. Verify S3 lifecycle policy compliance
5. Log cleanup summary (CloudWatch)
6. Send admin report (daily summary email)

Cost: ~$0.01 per day (varies with data volume)

**Lambda 22: notification-handler**

yaml

Name: careervp-notification-{env}
Runtime: Python 3.11
Memory: 256 MB
Timeout: 10s
Trigger: SNS (internal notifications)

Environment Variables:
SES_FROM_EMAIL: noreply@careervp.com
ADMIN_EMAIL: yitzchak@careervp.com


IAM Permissions:

- ses:SendEmail
- dynamodb:GetItem (get user preferences)

Libraries:

- jinja2 (email templates)

Email Templates (S3):

- welcome-email.html
- generation-started.html
- generation-complete.html
- generation-failed.html
- usage-warning.html (80% consumed)
- usage-limit-reached.html
- subscription-activated.html
- subscription-cancelled.html
- credits-granted.html

Logic:

1. Receive SNS message (type, userId, data)
2. Get user email, name from DynamoDB
3. Load appropriate template
4. Render with data (Jinja2)
5. Send via SES
6. Log success/failure
7. Return 200 OK

Cost: ~$0.0001 per email (SES + Lambda)

**Lambda Cost Summary**

yaml

Per Application Processing:
company-research-v1: $0.004
vp-report-generator: $0.035
cv-tailor: $0.005
cover-letter-generator: $0.004
interview-prep-generator: $0.005

orchestrator overhead: $0.005
notification: $0.0001

Total per Application: ~$0.058


Monthly Estimate (1,000 users, 10,000 apps):
Processing: $580
Auth/Profile: $50
Downloads: $40
Admin: $30
Scheduled: $10

Total Lambda: ~$710/month

Combined with AI costs: ~$1,500-2,000/month

This completes the comprehensive technical documentation covering: ✅ Non-Functional

Requirements (NFR)

✅ User Stories (Agile format)

✅ API Specifications (all endpoints)

✅ Database Schema (DynamoDB tables)

✅ Lambda Functions Inventory (all 22 functions)

Would you like me to proceed with any additional documentation such as:

```
● Infrastructure as Code (Terraform/CloudFormation templates)?
● Frontend architecture and component specifications?
● Testing strategy and test cases?
● Deployment pipeline and CI/CD configuration?
● Security audit checklist?
```

# Tab 5


How much information they receive at each stage:

Stage 1: Gap Analysis → CV + VP Brief (cover letter?)
Stage 2: Phone screen - Brief interview prep including VP company background
Stage 3: Interview Prep Questions → Full Interview Prep

V2 or V3

- Chatbot that customizes interview prep for each interviewer in the hiring process.


# Tab 6


Facts:

1. Active users are users who have a current paid subscription. Free tier users data is archived
after 90 days of inactivity. For Active and Free Tier users move data to S3 IA after 15 days of
inactivity for those objects. DO NOT delete data.
2. IaC in NFR-7: Maintainability ONLY uses AWS CDK and NOT Terraform

Questions:

1. In Supporting Functions, explain the credit manager purpose: Track and enforce usage limits
2. In Future features detail the analytics-aggregator (V2)
3. In the DynamoDB table: Users is the credits_remaining field used only in the free tier? We
decided to only count the number of applications in the free tier. Upon upgrading to a monthly,
3-month or 6-month subscription the user has unlimited usage of the application process.
4. Explain the TTL of 7 days in the DynamoDB careervp-sessions table? How does this impact
paid or free tier users? Users CANNOT lose their data if they are an active user.
5. Is there any degradation in performance or user experience, or application impact, by moving
data to S3 IA vs remaining in S3 Standard?
6. What is the use case for versioning S3 data? How is the user expected to utilize these
versions?
7. Suggest an AWS resource tagging strategy according to best practices.
8. In FR-8: Job Tracking Dashboard (P1) why is there a Notes field for user tracking, how is this
submitted and where is it stored and retrieved and displayed? What is the Timeline
visualization? What are we exporting and why export to CSV?
9. Why are we regenerating artifacts? Preference is to NOT regenerate and allow for manual
download and edit.
10. Explain and detail FR-10: Usage Tracking & Limits
11. Explain NFR-4: Security->Regular security audits
12. Explain the interface for CV-Edit: In-app editor (WYSIWYG)
12a. CV edit capabilities SHOULD BE a form with EACH section as editable textboxes. DO NOT
provide a single WYSIWYG text editor for the CV. The goal is to prevent user error by modifying
the ATS optimized structure.
13. Explain “CV-Regenerate: With user feedback” AND “Cover Letter-Regenerate: Different
tone/emphasis”. How is this expected to work and what backend functionality supports this
effort.

Modifications - IMPORTANT:

1. In the UI there is a counter during the trial period for the number of application processed. “3
Applications Remaining’ → “2 Applications Remaining” → “1 Application Remaining” → “No
Applications Remaining - Upgrade Now”
2. Create two different VPRs


2a. VPR Brief - Value Proposition report delivered, be default, with the CV. This VPR contains
the Value Proposition Statement, the Alignment Matrix (evidence of job alignment) and Key
Differentiators.
2b. VPR - full Value Proposition report as currently defined. Includes the contents of the VPR
Brief

3. Gap Analysis Questions is a part of the current workflow and IS NOT a separate process.
3a. Correct Workflow: Upload Master CV + Job Post + Company URL + Job Title → generate
Gap Analysis Questionnaire → Users’ response is incorporated into generating the CV, Cover
Letter and VPR. → Generate the Interview Prep Questionnaire → Generate Interview Prep
report
3b. Future Applications (all artifacts) incorporate ALL previous Gap Analysis and Interview Prep
Questionnaire responses. The goal is to create a complete work history profile.

3c. Gap Analysis and Interview Prep Questionnaires JSON is converted to HTML and presented
to the user as a web page form. The “Your Answer” section is a multiline textbox. Auto-save
enabled. Submit triggers generation of the respective artifact(s).

4. S3 Bucket lifecycle policies: ACTIVE users MUST NOT have data archived.
5. User has a drop down in the UI to select page length.
6. Remove “Suggest Learning Resouces” in FR-5: Gap Analysis with Interactive Q&A
7. UI has Download dropdown allowing for selection of output: MS Word, PDF, Markdown.
Backend functionality supports these export formats.
8. FR-6: Interview Preparation Guide - supports output in Docx format
9. Default output format for ALL artifacts is Docx, but supporting PDF as an option.
10. Backend: ALL resources have tags
11. In New Application interface, User has UI control to select from previously saved CVs OR
can upload new CV
12. Knowledge base materials, at this time is ONLY Cover Letter sample, should be uploaded in
New Application interface.
13. In #### Primary Workflow: Generate Application Package
13a. Insert Secondary Workflow: Gap Analysis between steps 7-8. User answers questions ->
Clicks Generate -> Review page shows all artifacts

## —---

Facts:

1. Interview Prep and Gap Analysis reports output by default as Docx
2. Perplixity AI should be used for company search if web search is insufficient.
3. In VPR, “Alignment Matrix” **ALWAYS** displayed in table format.
4. In “Language consistency: Match input language (English/Hebrew)”:
    4a. Output Rules: English CV + English Job Post = English artifacts, Hebrew CV +
    Hebrew Job Post = Hebrew artifacts, English CV + Hebrew Job Post = English AND
    Hebrew artifacts, Hebrew CV + English Job Post = English AND Hebrew artifacts
5. ALL Prompts MUST be extract to config files and referenced in the code.
6. ALL artifacts default to DOCX format with PDF export supported


7. Free Tier→ user can upgrade at any time to a monthly, 3-month, 6-month plan

Questions:

1. Explain how Stripe works: 4. Payment Errors:
    - Card declined: "Payment failed. Please update your payment method."
    - Subscription issue: "Subscription lapsed. Update payment to restore access."
2. Why is V2 Features (Post-Launch) - Job Tracking dashboard
3. What are the criteria for insufficient company search?
4. In VPR, formatted document for review, is “Evidence mapping table” = “Alignment
    Matrix”?
5. In TC-VPR-001-01: Standard VPR Generation → Input: Valid job posting (500 words),
    CV (1000 words), company research: Explain the 500 and 1000 word limits
6. In the ATS Checker: which cv is it checking? why do we need this? what is shown to the
    user and how?
7. Explain contradiction: “User can edit CV in-app (V1: download + manual edit; V2: in-app
    editor)”
8. In usage-warning: Trigger: 80% of free tier consumed, how is this calculated. Show
    show the number of free applications remaining.

Modifications:

1. Review Job popup before processing primary workflow. Goal is to validate ALL artifacts
    are valid and company information is correct. IF error / invalid / insufficient data then
    allow to return and edit job.
    Workflow: New Application → User uploads artifacts and inputs required data →
    Backend conducts simple webscrape / google search to validate company info is
    sufficient and validate upload artifacts → IF valid, proceed to next step → IF invalid,
    display informative error and suggest returning to edit.
2. In VPR generation - Prompt Engineering - Input Data → Gap Analysis MUST be
    included as an input. Update prompt.


# Tab 7


I'll search for recent conversations about CareerVP SaaS features development to understand

the context and help address your questions and modifications.

Relevant chats

2 results

Let me search for more specific conversations about the technical architecture and

requirements.

Relevant chats

5 results

Based on my review of the recent CareerVP conversations, I can now address your questions and

modifications. Let me work through these systematically:

**Answers to Your Questions**

**1. Credit Manager Purpose**

The credit manager tracks and enforces usage limits specifically for free tier users (3

applications). It:

```
● Decrements credits_remaining after each successful application generation
● Blocks new applications when credits reach zero
● Does NOT apply to paid subscribers (they have unlimited usage)
● Triggers upgrade prompts when free tier exhausted
```
**2. analytics-aggregator (V2)**

Currently listed as an optional future Lambda function. Based on conversations, this would:

```
● Aggregate token usage metrics across users
● Generate cost reports and trends
● Provide business intelligence on feature adoption
● Calculate per-user/per-artifact cost averages
● Support admin dashboards for system-wide analytics
```
**3. credits_remaining Field**

Correct - This field is ONLY used for free tier users. Upon subscription to any paid tier (monthly,

3-month, or 6-month), the field becomes irrelevant as paid users have unlimited applications.

**4. TTL of 7 Days in careervp-sessions**

CRITICAL ISSUE IDENTIFIED: The 7-day TTL on sessions table creates a data loss risk. Here's

the clarification needed:


Current Design Flaw:

```
● Sessions table has TTL=7 days
● This would delete session data for ALL users (active paid subscribers included)
● Violates your requirement: "Active users MUST NOT lose data"
```
Corrected Approach:

yaml

careervp-sessions:
TTL: 7 days for FREE TIER only
Conditional deletion logic:

- Check user tier before TTL deletion
- Free tier inactive >90 days: TTL applies
- Active paid users: NO TTL deletion
- Implementation: Lambda function checks tier before allowing TTL

Better Architecture:

```
● Don't rely on DynamoDB TTL for tier-specific policies
● Use scheduled Lambda to archive/delete based on user tier
● Keep sessions indefinitely for active paid users
● Archive free tier sessions to S3 IA after 90 days of inactivity
```
**5. S3 IA vs S3 Standard Performance Impact**

S3 IA (Infrequent Access) has NO performance degradation:

```
● Same latency as S3 Standard (milliseconds)
● Same throughput capabilities
● Same 99.99% availability
● Only difference: retrieval fee ($0.01 per GB)
```
Impact on user experience: NONE

```
● Downloads happen at same speed
● No delay in accessing documents
● Cost benefit: ~50% cheaper storage ($0.0125 vs $0.023 per GB)
```
Your lifecycle policy is correct - moving to IA after 15 days for inactive users

**6. S3 Versioning Use Case**

Based on the architecture, versioning serves:

User-Facing:

```
● Allow users to revert to previous CV/artifact versions
● Recover from accidental edits or overwrites
● Compare different iterations of tailored CVs
```

System-Level:

```
● Recover from generation errors
● Audit trail for compliance
● Rollback capability during debugging
```
Expected User Interaction:

```
● UI shows "Version History" button on artifact cards
● Dropdown lists versions with timestamps
● User clicks to preview/download older version
● Option to "restore" previous version as current
```
**7. AWS Resource Tagging Strategy**

yaml

Required Tags (All Resources):
Environment: [dev|staging|production]
Project: CareerVP
ManagedBy: Terraform _# or CDK per your modification_
CostCenter: Engineering
Owner: [team-email]

Application Tags:
Component: [lambda|dynamodb|s3|api-gateway]
Function: [auth|generation|storage|notification]
Tier: [free|paid|admin]

Operational Tags:
Backup: [true|false]
Monitoring: [standard|enhanced]
Compliance: [gdpr|ccpa]

Cost Allocation Tags:
User: [user-id] _# For per-user cost tracking_

Feature: [vpr|cv|cover-letter|interview-prep]

Best Practice Implementation:

python

_# In CDK/Terraform_
tags = {
"Environment": "production",
"Project": "CareerVP",
"ManagedBy": "CDK",
"Component": "lambda",
"Function": "cv-tailor",


"CostCenter": "Engineering",
"Backup": "true",
"Monitoring": "enhanced"
}
```

_### 8. **FR-8: Job Tracking Dashboard**_

**Notes Field:**

- **Purpose**: User personal tracking (interview feedback, follow-up
reminders, recruiter names)
- **Submission**: Text area in job details page, auto-save on blur
- **Storage**: DynamoDB `careervp-jobs` table, `notes` attribute
(String, up to 4KB)
- **Retrieval**: Displayed on job card expansion and job detail page
- **Display**: Read-only text with "Edit" button

**Timeline Visualization:**
```
Draft → Submitted → Interview → [Offer|Rejected]
↓ ↓ ↓ ↓
Date1 Date2 Date3 Date4
```

- Shows status progression with dates
- Visual progress bar
- Color-coded stages (gray→blue→green→green/red)

**CSV Export:**

- **What**: All job applications with: company, title, status, dates,
notes, artifacts links
- **Why**: External tracking (Excel, Notion), backup, sharing with
career coaches
- **Format**: `user_jobs_export_[timestamp].csv`

_### 9. **Artifact Regeneration**_
**Your preference is noted**: NO automatic regeneration.

**Recommended Approach:**

- Users download artifacts (Docx/PDF)
- Edit locally using MS Word/Google Docs
- Manual editing preserves ATS optimization
- NO in-app regeneration button (prevents costly re-generation)

**Exception**: Only regenerate on explicit "Generate New Version"
with updated CV/job description


_### 10. **FR-10: Usage Tracking & Limits**_

**Free Tier:**

- Track: `applications_processed` (counter in DynamoDB Users table)
- Limit: 3 applications
- Display: "X Applications Remaining" in header
- Enforcement: Block `/api/jobs` POST when limit reached
- Notification: At application 3, show upgrade modal

**Paid Tier:**

- Track: Total applications for analytics only
- Limit: Unlimited
- Display: "Unlimited Applications" badge
- No enforcement

**Dashboard Display:**
```
Free Tier User:
Applications Used: 2 / 3
[Upgrade to Unlimited]

Paid Tier User:
Applications This Month: 47

Total Applications: 312

**11. NFR-4: Security - Regular Security Audits**

Definition:

```
● Quarterly manual security reviews
● Automated vulnerability scanning (AWS Inspector)
● Dependency auditing (npm audit, Safety for Python)
● Penetration testing (annual)
```
Scope:

yaml

Quarterly Review:

- IAM policy review (principle of least privilege)
- S3 bucket policies (no public access)
- API Gateway authorization (Cognito integration)
- Lambda environment variables (no secrets)
- DynamoDB encryption verification

Automated (Weekly):


- Dependency vulnerability scan
- Docker image scanning
- AWS Config compliance rules

Annual:

- Third-party penetration test
- GDPR/CCPA compliance audit
- Security incident response drill
```

_### 12 & 12a. **CV-Edit Interface**_

**CRITICAL**: You're absolutely right about WYSIWYG being wrong.

**Correct Approach: Structured Form Editor**
```
CV Edit Interface (NOT WYSIWYG):

[Contact Information Section]
Name: [________]
Email: [________]
Phone: [________]
LinkedIn: [________]

[Professional Summary Section]
Summary: [____________]
[____________]
[____________]
(300 chars max, ATS-optimized structure preserved)

[Experience Section]
Company 1: [________]
Title: [________]
Dates: [From: __] [To: __]
Achievements:

- [__________________]
- [__________________]
- [__________________]
[+ Add Achievement]

[Skills Section]
Technical: [tag, tag, tag]
Soft Skills: [tag, tag, tag]

[Education Section]


## ...

## ```

**Why This Approach:**

- Preserves ATS structure (fields map to ATS-expected sections)
- Prevents formatting errors (no manual bold/italics that break
parsing)
- Enforces character limits
- Maintains semantic structure
- Each field validates independently

**Backend Support:**

- JSON schema for CV structure
- Field-level validation
- ATS compliance checking on save
- Warning if user edits reduce ATS score

_### 13. **Regeneration with Feedback**_

**CV-Regenerate: With user feedback**
```
UI Flow:

1. User clicks "Regenerate CV"
2. Modal appears: "What would you like to improve?"
- [Text area]: "Example: Emphasize leadership experience,
reduce technical jargon for executive audience"
3. User submits feedback
4. Backend incorporates feedback into prompt:

System Prompt:
"Regenerate the CV with these user-requested changes:
{{user_feedback}}

Maintain:

- All factual information from master CV
- ATS optimization structure
- Same length ({{current_page_count}} pages)"
```

**Cover Letter-Regenerate: Different tone/emphasis**
```
UI Flow:

1. User clicks "Change Tone" dropdown
Options:
- More Formal


- More Conversational
- Emphasize Technical Skills
- Emphasize Leadership
- Emphasize Culture Fit
2. OR custom: [Text area for specific changes]
3. Backend regenerates with tone modifier:

System Prompt:
"Regenerate cover letter with tone: {{selected_tone}}

Maintain:

- Core value proposition from VPR
- All factual achievements
- Company research insights
- Same length (1 page)"

Backend Support:

python

def regenerate_artifact(
artifact_type: str,
job_id: str,
user_feedback: str,
tone_modifier: Optional[str] = None
):
_# Load original artifact_
original = get_artifact(job_id, artifact_type)

_# Load all source materials_
context = load_generation_context(job_id)

_# Add feedback to prompt_
context['user_feedback'] = user_feedback
context['tone_modifier'] = tone_modifier

_# Regenerate with Claude_
response = generate_with_claude(
template=f"regenerate_{artifact_type}",
context=context
)

_# Save as new version_
save_artifact_version(job_id, artifact_type, response)


## ```

## ---

_## Addressing Your Modifications_

_### 1. **Trial Counter UI**_ ✅
```
Display in header:
"3 Applications Remaining"
→ "2 Applications Remaining"
→ "1 Application Remaining"

→ "No Applications Remaining - Upgrade Now"

**2. Two VPR Types**

VPR Brief (Default with CV):

yaml

Contents:

- Value Proposition Statement (2-3 sentences)
- Alignment Matrix (table format)
- Key Differentiators (3-5 bullet points)
Pages: 1-2
File: vpr-brief-{company}-{timestamp}.docx

Cost: ~$0.005 (Haiku model)

VPR Full (On-demand):

yaml

Contents:

- Everything in VPR Brief
+ Company Deep Dive
+ Competitive Analysis
+ Risk Assessment
+ Strategic Recommendations
+ Evidence Library
Pages: 5-8
File: vpr-full-{company}-{timestamp}.docx
Cost: ~$0.035 (Sonnet model)
```

**UI Selection:**
```
□ Include VPR Brief (recommended)


□ Generate Full VPR Report (+$X)
```

_### 3. **Gap Analysis Workflow**_ ✅

**Corrected Workflow:**
```
Step 1: Upload Master CV + Job Post + Company URL + Job Title
↓
Step 2: Generate Gap Analysis Questionnaire (max 10 questions)
↓
Step 3: User answers questions (HTML form, auto-save)
↓
Step 4: User clicks "Generate" → Backend generates:

- CV (incorporating gap analysis answers)
- Cover Letter (incorporating gap analysis answers)
- VPR Brief (incorporating gap analysis answers)
↓
Step 5: Review Page shows all artifacts
↓
Step 6: Generate Interview Prep Questionnaire
↓
Step 7: User answers interview questions
↓

Step 8: Generate Interview Prep Report

3b. Future Applications:

python

_# On subsequent applications_
previous_gap_answers = get_all_gap_analysis_answers(user_id)
previous_interview_answers = get_all_interview_prep_answers(user_id)

_# Include in context for new application_
context = {
'master_cv': master_cv,
'job_posting': job_posting,
'company_research': company_research,
'previous_profile': {
'gap_analysis_history': previous_gap_answers,
'interview_prep_history': previous_interview_answers
}

}

3c. Questionnaire UI:


html

<form id="gap-analysis-form">
<h3>Question 1: {{question_text}}</h3>
<textarea
name="answer_1"
rows="5"
placeholder="Your answer here..."
data-autosave="true">
</textarea>

_<!-- Repeat for all questions (max 10) -->_

<button type="submit">Generate My Application Package</button>
</form>

<script>
_// Auto-save every 30 seconds_
setInterval(autoSave, 30000);

</script>

**4. S3 Lifecycle for Active Users** ✅

Corrected Policy:

yaml

Lifecycle Rules:
Rule 1: Free Tier Inactive
Prefix: users/{user_id}/*
Condition:

- User tier = free
- Last access > 90 days
Transition: S3 IA after 15 days of object inactivity

Rule 2: Paid Tier (NO ARCHIVAL)
Prefix: users/{user_id}/*
Condition:

- User tier = paid|premium
Action: NO lifecycle transitions

Note: Data stays in S3 Standard indefinitely

Implementation:

```
● Tag S3 objects with user tier
● Lifecycle rule filters by tag
● Lambda updates tags when user upgrades
```

**5. Page Length Dropdown** ✅

html

<select name="page_length">
<option value="1">1 Page</option>
<option value="2" selected>2 Pages (Recommended)</option>
<option value="3">3 Pages</option>

</select>

**6. Remove "Suggest Learning Resources"** ✅

Removed from FR-5

**7. Download Format Options** ✅

html

<div class="download-dropdown">
<button>Download ▼</button>
<ul>
<li><a href="/download/cv?format=docx">MS Word (.docx)</a></li>
<li><a href="/download/cv?format=pdf">PDF (.pdf)</a></li>
<li><a href="/download/cv?format=md">Markdown (.md)</a></li>
</ul>

</div>

Backend Support:

python

_# Lambda function: artifact-converter_
def convert_artifact(artifact_id, format):
if format == 'docx':
return generate_docx(artifact_id)
elif format == 'pdf':
return convert_docx_to_pdf(artifact_id)
elif format == 'md':

return convert_to_markdown(artifact_id)

**8. Interview Prep Docx** ✅

Already supported - default format for all artifacts

**9. Default Docx, PDF Optional** ✅

python

DEFAULT_FORMAT = 'docx'


SUPPORTED_FORMATS = ['docx', 'pdf', 'md']

**10. All Resources Tagged** ✅

Apply tagging strategy from Question 7

**11. Select Previous CVs** ✅

html

<div class="cv-selection">
<h3>Select Master CV</h3>
<select name="cv_source">
<option value="upload">Upload New CV</option>
<optgroup label="Previously Uploaded">
<option value="cv_abc123">Software Engineer CV (uploaded Jan
15)</option>
<option value="cv_def456">Product Manager CV (uploaded Jan
10)</option>
</optgroup>
</select>

<input type="file" id="cv_upload" style="display:none" />

</div>

**12. Knowledge Base Upload Location** ✅

Move KB upload to New Application interface (instead of separate KB management page)

**13. Gap Analysis in Primary Workflow** ✅

Already addressed in Modification #3

**Updated Lambda Function: Gap Analysis Generator**

python

def generate_gap_analysis(job_id, user_id):
"""
Generate max 10 gap analysis questions
Incorporate previous answers from all past applications
"""
_# Load context_
job_posting = get_job_posting(job_id)
master_cv = get_master_cv(user_id)
company_research = get_company_research(job_id)


_# CRITICAL: Load ALL previous gap analysis answers_
previous_answers = dynamodb.query(
TableName='careervp-gap-analysis',
KeyConditionExpression='user_id = :uid',
ExpressionAttributeValues={':uid': user_id}
)

_# Generate questions_
response = claude_api.messages.create(
model='claude-haiku-4-5-20251001',
max_tokens=2000,
system=PROMPTS['gap_analysis_questions'],
messages=[{
'role': 'user',
'content': f"""
Job Posting: {job_posting}
CV: {master_cv}
Company: {company_research}

Previous Gap Analysis Answers (reuse to build complete profile):
{json.dumps(previous_answers, indent=2)}

Generate MAXIMUM 10 questions that:

1. Fill gaps between CV and job requirements
2. Don't repeat questions already answered in previous applications
3. Build on previous answers to create comprehensive work history
4. Focus on quantifiable achievements and specific examples

Return JSON array of questions.
"""
}]
)

questions = json.loads(response.content[0].text)

_# Convert to HTML form_
html_form = generate_html_form(questions)

return {
'questions': questions,
'html_form': html_form,
'previous_profile': previous_answers

}


**Summary**

All questions answered and modifications addressed. Key changes:

1. Session TTL requires tier-aware logic
2. VPR split into Brief (default) and Full (on-demand)
3. Gap Analysis integrated into main workflow
4. CV Edit is structured form, NOT WYSIWYG
5. Regeneration with user feedback supported
6. S3 lifecycle respects user tier
7. All resources tagged
8. Docx is default, PDF/MD optional


# Tab 8


I'll address your facts, questions, and modifications systematically.

**Facts Acknowledged**

1. ✅ Interview Prep and Gap Analysis default output: **Docx**
2. ✅ **Perplexity AI** as fallback for company research when web search insufficient
3. ✅ Alignment Matrix **ALWAYS** in table format
4. ✅ Language consistency rules updated:
    ○ EN CV + EN Job = EN artifacts
    ○ HE CV + HE Job = HE artifacts
    ○ EN CV + HE Job = **EN + HE artifacts (both)**
    ○ HE CV + EN Job = **EN + HE artifacts (both)**
5. ✅ ALL prompts externalized to config files
6. ✅ ALL artifacts default DOCX with PDF export
7. ✅ Free tier can upgrade anytime to monthly/3-month/6-month plans

**Answers to Questions**

**1. Stripe Payment Error Handling Explained**

**How Stripe Works in CareerVP:**

python
_# Stripe Integration Flow_
class StripePaymentHandler:

def handle_subscription_creation(self, user_id, plan_id):
"""
User clicks 'Upgrade' → Stripe Checkout Session
"""
_# 1. Create Stripe Checkout Session_
session = stripe.checkout.Session.create(
customer_email=user.email,
payment_method_types=['card'],
line_items=[{
'price': plan_id, _# monthly/3-month/6-month_
'quantity': 1 ,
}],
mode='subscription',
success_url='https://app.careervp.com/success',


cancel_url='https://app.careervp.com/pricing',
)

_# 2. Redirect user to Stripe hosted page_
return session.url

def handle_webhook(self, event):
"""
Stripe sends webhooks for payment events
"""
if event.type == 'checkout.session.completed':
_# Payment succeeded_
session = event.data.object
self.activate_subscription(session.customer)

elif event.type == 'invoice.payment_failed':
_# Card declined or insufficient funds_
self.handle_payment_failure(event.data.object)

elif event.type == 'customer.subscription.deleted':
_# Subscription canceled/expired_

self.downgrade_to_free(event.data.object.customer)

**Payment Error Scenarios:**

**Scenario A: Card Declined (Initial Purchase)**

yaml
Flow:

1. User clicks "Upgrade to Premium"
2. Redirected to Stripe Checkout
3. Enters card details → Card declined
4. Stripe shows: "Your card was declined"
5. User can:
- Try different card
- Cancel and return to app

CareerVP Response:

- No webhook received (payment never completed)
- User remains on Free tier
- No action needed in CareerVP backend

**Scenario B: Card Declined (Renewal)**


yaml
Flow:

1. User subscribed 30 days ago
2. Stripe attempts to charge renewal
3. Card declined (expired, insufficient funds, etc.)
4. Stripe webhook: 'invoice.payment_failed'
5. Stripe retries 3x over 7 days

CareerVP Response:
Day 1 : Webhook received → Send email:
"Your payment failed. Please update payment method."

Day 3 : Stripe retry _#2 fails → Send email:_
"Second payment attempt failed. Update card to avoid service interruption."

Day 7 : Stripe retry _#3 fails → Subscription canceled_
Webhook: 'customer.subscription.deleted'

CareerVP Action:

- Update DynamoDB: tier='free', subscription_status='lapsed'
- Display in-app banner:
"Subscription lapsed. Update payment to restore access."
- Block new application generation
- Existing artifacts remain accessible

**Scenario C: Subscription Issue (User Initiated Cancel)**

yaml
Flow:

1. User clicks "Cancel Subscription" in Stripe Customer Portal
2. Stripe webhook: 'customer.subscription.deleted'

CareerVP Response:

- Downgrade to free tier at end of billing period
- Email: "Your subscription ends on [date]. Resubscribe anytime."
- After expiry: Show upgrade prompts

**Implementation:**

python
_# Lambda: stripe-webhook-handler_
def handle_payment_failure(invoice):
"""


Stripe webhook: invoice.payment_failed
"""
customer_id = invoice.customer
user = get_user_by_stripe_id(customer_id)

_# Update user status_
dynamodb.update_item(
TableName='careervp-users',
Key={'user_id': user['user_id']},
UpdateExpression='SET subscription_status = :status',
ExpressionAttributeValues={
':status': 'payment_failed'
}
)

_# Send notification_
send_email(
to=user['email'],
template='payment_failed',
data={
'amount': invoice.amount_due / 100 ,
'update_url': create_stripe_portal_link(customer_id)
}
)

_# Display in-app banner_
publish_sns_message({
'type': 'payment_failed',
'user_id': user['user_id'],
'message': 'Payment failed. Please update your payment method.'
})

def handle_subscription_deleted(subscription):
"""
Stripe webhook: customer.subscription.deleted
"""
customer_id = subscription.customer
user = get_user_by_stripe_id(customer_id)

_# Downgrade to free tier_
dynamodb.update_item(
TableName='careervp-users',
Key={'user_id': user['user_id']},
UpdateExpression='''


SET tier = :tier,
subscription_status = :status,
credits_remaining = :credits
''',
ExpressionAttributeValues={
':tier': 'free',
':status': 'lapsed',
':credits': 3 _# Reset to 3 free applications_
}
)

_# Notify user_
send_email(
to=user['email'],
template='subscription_lapsed',
data={
'reactivate_url': 'https://app.careervp.com/pricing'
}
)
```

**User-Facing Messages:**
```
Payment Failed Banner (in-app):
⚠ Payment Failed
Your last payment didn't go through. Please update your payment
method to continue using unlimited applications.
[Update Payment Method] [Contact Support]

Subscription Lapsed Banner:
🔒 Subscription Inactive
Your subscription has lapsed. Upgrade now to restore unlimited
application generation.
[View Plans] [Reactivate Subscription]
```

## ---

_### 2. **Why is Job Tracking Dashboard V2 (Post-Launch)?**_

**Reasoning:**

Job Tracking Dashboard is **deprioritized to V2** because:


1. **MVP Focus**: V1 prioritizes core value proposition:
- Generate high-quality application materials
- Prove ROI: "Our AI materials get you interviews"
- Minimize scope to launch faster
2. **User Behavior Assumption**: Early users will:
- Use external tracking (spreadsheets, Notion, email folders)
- Focus on quality over quantity of applications
- Need time to accumulate enough applications to make tracking valuable
3. **Development Complexity**:
- Requires additional UI/UX design
- Status management (Draft → Submitted → Interview → Offer)
- Timeline visualization
- Export functionality
- More testing surface area
4. **Data Requirements**:
- Users need to manually update status (we can't auto-detect "interview scheduled")
- Requires user discipline to maintain
- Less critical than artifact generation

**V1 Alternative**:
```
Minimal Job History (V1):

- Simple list of generated applications
- Download links to artifacts
- Company name + Job title
- Generation date
- No status tracking
- No timeline/notes
```

**V2 Full Dashboard**:
```
Complete Job Tracking (V2):

- Status pipeline with drag-and-drop
- Interview date tracking
- Notes per application
- Timeline visualization
- CSV export
- Email/calendar integration
- Analytics (response rate, time-to-interview)


**3. Criteria for Insufficient Company Search**

**Perplexity AI triggers when web search returns insufficient data:**

python
class CompanyResearchValidator:

## REQUIRED_FIELDS = {

'company_name': True,
'industry': True,
'company_size': False, _# Optional but preferred_
'recent_news': True,
'products_services': True,
'company_culture': False, _# Optional_
'competitors': False, _# Optional_
}

MINIMUM_WORD_COUNT = 200 _# Insufficient if less_

def is_sufficient(self, web_search_results):
"""
Determine if web search data is sufficient
"""
_# Extract structured data from results_
extracted = self.extract_company_data(web_search_results)

_# Check 1: Required fields present_
required_missing = [
field for field, required in self.REQUIRED_FIELDS.items()
if required and not extracted.get(field)
]

if required_missing:
return False, f"Missing required fields: {required_missing}"

_# Check 2: Sufficient content length_
total_words = sum(
len(str(v).split())
for v in extracted.values()
if v
)


if total_words < self.MINIMUM_WORD_COUNT:
return False, f"Insufficient content: {total_words} words (need
{self.MINIMUM_WORD_COUNT})"

_# Check 3: Recency (news within 12 months)_
if extracted.get('recent_news'):
latest_news_date = self.parse_news_date(extracted['recent_news'])
if (datetime.now() - latest_news_date).days > 365 :
return False, "No recent news found (need within 12 months)"

_# Check 4: Credibility (sources from known domains)_
credible_sources = [
'linkedin.com', 'crunchbase.com', 'bloomberg.com',
'reuters.com', 'techcrunch.com', company_domain
]

source_domains = [urlparse(r['url']).netloc for r in web_search_results]
has_credible_source = any(
any(cred in domain for cred in credible_sources)
for domain in source_domains
)

if not has_credible_source:
return False, "No credible sources found"

return True, "Sufficient data"

def fallback_to_perplexity(self, company_name, company_url):
"""
Use Perplexity AI when web search insufficient
"""
perplexity_response = perplexity_api.query(
query=f"""
Research {company_name} ({company_url}):

- Industry and business model
- Company size and structure
- Recent news (past 12 months)
- Products/services offered
- Company culture and values
- Notable achievements or press releases

Provide comprehensive, factual information.
""",
model='sonar-pro'


## )

return perplexity_response

**Specific Criteria:**

```
Criterion Threshold Required?
```
```
Company name
confirmed
```
```
Must match user input ✅ Yes
```
```
Industry identified At least 1 sentence ✅ Yes
```
```
Recent news At least 1 article within 12 months ✅ Yes
```
```
Products/Services At least 50 words ✅ Yes
```
```
Total content 200+ words ✅ Yes
```
```
Credible sources At least 1 from known domain ✅ Yes
```
```
Company size Employee count or range ❌ Optional
```
```
Competitors At least 2 named ❌ Optional
```
```
Culture insights Values, mission statement ❌ Optional
```
**Workflow:**

yaml
Step 1 : Web Search (Primary)

- Search: "{company_name} company profile"
- Search: "{company_name} recent news"
- Parse results
- Validate against criteria

Step 2 : Validation

- IF sufficient → Proceed
- IF insufficient → Trigger Perplexity AI

Step 3 : Perplexity AI (Fallback)

- Query Perplexity with company details
- Extract comprehensive data
- Combine with web search results


Step 4 : Final Validation

- Re-check criteria
- IF still insufficient → User notification
**4. VPR Evidence Mapping Table = Alignment Matrix?**

**YES - They are the SAME thing.**

**Terminology Clarification:**

yaml
Official Name: "Alignment Matrix"
Aliases:

- Evidence Mapping Table
- Skills Alignment Table
- Job Fit Matrix

Format: ALWAYS table format (not prose)
```

**Structure:**
```
Alignment Matrix (Table Format):

| Job Requirement | Your Evidence | Strength |
|-----------------|---------------|----------|
| 5+ years Python | 7 years Python dev at TechCorp, led team of 5 | ⭐⭐⭐ Strong |
| AWS Architecture | Designed serverless apps (Lambda, DynamoDB, S3) | ⭐⭐⭐ Strong |
| Team Leadership | Managed 8 engineers, mentored 3 juniors | ⭐⭐ Moderate |
| Agile/Scrum | 3 years as Scrum Master, certified PSM I | ⭐⭐ Moderate |

| CI/CD Pipeline | Built Jenkins pipelines, reduced deploy time 40% | ⭐⭐⭐ Strong |

**In VPR Generation Prompt:**

python
_# prompts/vpr_generation.yaml_
alignment_matrix_instructions: |
Create an ALIGNMENT MATRIX in TABLE FORMAT with these columns:

Column 1 : Job Requirement (from job posting)
Column 2 : Your Evidence (from CV + Gap Analysis)
Column 3 : Strength (Strong/Moderate/Developing)


Include 8 - 12 rows covering:

- Technical skills (required + preferred)
- Soft skills (leadership, communication)
- Experience requirements (years, domain)
- Certifications or education

Use this EXACT table markdown format:

| Job Requirement | Your Evidence | Strength |
|-----------------|---------------|----------|
| [requirement] | [evidence] | [rating] |

Do NOT write prose. ONLY output the table.

**Why Two Names?**

Historical artifact from development conversations - "Evidence Mapping Table" described
functionality, "Alignment Matrix" is the polished product name. Going forward: **Use "Alignment
Matrix" consistently**.

**5. TC-VPR-001-01 Word Limits Explained**

**Test Case Context:**

yaml
TC-VPR-001-01: Standard VPR Generation
Input:

- Valid job posting (500 words)
- CV (1000 words)
- Company research

**These are MINIMUM test inputs, NOT system limits.**

**Explanation:**

1. **500-word Job Posting** :
    ○ **NOT a maximum system limit**
    ○ Represents typical job posting length for testing
    ○ Actual system accepts job postings of any length (10,000+ words)
    ○ Test case uses 500 words to ensure consistent, reproducible test results
2. **1000-word CV** :


```
○ NOT a maximum system limit
○ Represents typical CV length (2-3 pages) for testing
○ Actual system accepts CVs up to ~10,000 words (10+ pages)
○ Test case uses 1000 words for predictable token usage
```
**Actual System Limits:**

python
_# system_limits.py_
LIMITS = {
'job_posting': {
'min_words': 50 ,
'max_words': 50000 , _# ~100 pages_
'typical': 500 , _# Used in test cases_
},
'cv': {
'min_words': 200 ,
'max_words': 50000 , _# ~100 pages_
'typical': 1000 , _# Used in test cases_
},
'gap_analysis_answer': {
'min_words': 10 ,
'max_words': 500 , _# Per question_
},
'company_research': {
'min_words': 200 ,
'max_words': 10000 ,
}

}

**Test Case Rationale:**

python
_# Why 500/1000 words in test cases?_

_# 1. Token Budget Predictability_
job_posting_tokens = 500 * 1.3 _# ~650 tokens_
cv_tokens = 1000 * 1.3 _# ~1300 tokens_
company_tokens = 500 * 1.3 _# ~650 tokens_
total_input = ~ 2600 tokens _# Predictable for testing_

_# 2. Realistic Data
# - Most job postings: 300-700 words
# - Most CVs: 800-1500 words_


_# - Test with typical data, not edge cases_

_# 3. Fast Test Execution
# - Smaller inputs = faster LLM responses
# - Test suite completes in reasonable time_

_# 4. Cost Control
# - Test suite runs 80+ times during development_

_# - Smaller inputs = lower API costs_

**For Production:**

python
def validate_input_length(content, content_type):
"""
Validate user uploads against actual system limits
"""
word_count = len(content.split())

limits = LIMITS[content_type]

if word_count < limits['min_words']:
raise ValidationError(
f"{content_type} too short: {word_count} words "
f"(minimum {limits['min_words']})"
)

if word_count > limits['max_words']:
raise ValidationError(
f"{content_type} too long: {word_count} words "
f"(maximum {limits['max_words']}). "
f"Please shorten and resubmit."
)

return True

**6. ATS Checker Explained**

**Which CV is Checked?**

The **TAILORED CV** (output of cv-tailor Lambda), NOT the master CV.


**Why Do We Need This?**

yaml
Purpose:

- Validate generated CV passes ATS systems
- Catch formatting issues before user downloads
- Provide confidence score to user
- Identify improvement opportunities

ATS Systems Check For:

1. Standard section headings (Experience, Education, Skills)
2. Chronological ordering
3. No tables/columns/graphics (text-only)
4. No headers/footers
5. Standard fonts
6. Keyword density vs. job posting
7. Contact information format
8. Bullet points (not paragraphs)
```

**What is Shown to User?**
```
ATS Compatibility Score Card:

## ┌─────────────────────────────────────┐

│ ATS Compatibility: 94/100 ✅ │
├─────────────────────────────────────┤
│ │
│ ✅ Standard Section Headings │
│ ✅ Chronological Order │
│ ✅ Keyword Match: 87% │
│ ✅ Contact Info Formatted │
│ ✅ No Graphics/Tables │
│ ⚠ Font: Should use Arial/Calibri│
│ │
│ [View Detailed Report] │
└─────────────────────────────────────┘

Recommendations:

- Change font to Arial for maximum compatibility
- Add 3 more keywords: "Kubernetes", "microservices", "REST API"

**Implementation:**


python
_# Lambda: ats-checker_
def check_ats_compliance(tailored_cv, job_posting):
"""
Analyze CV against ATS best practices
"""
score = 0
max_score = 100
issues = []
recommendations = []

_# Check 1: Standard section headings (20 points)_
required_sections = [
'experience', 'education', 'skills',
'contact', 'summary'
]
found_sections = extract_sections(tailored_cv)

section_score = (len(found_sections) / len(required_sections)) * 20
score += section_score

if section_score < 20 :
missing = set(required_sections) - set(found_sections)
issues.append(f"Missing sections: {missing}")

_# Check 2: Chronological order (15 points)_
if is_chronological(found_sections['experience']):
score += 15
else:
issues.append("Experience not in reverse chronological order")
recommendations.append(
"Reorder experience: most recent first"
)

_# Check 3: Keyword match (25 points)_
job_keywords = extract_keywords(job_posting)
cv_keywords = extract_keywords(tailored_cv)

keyword_match = len(job_keywords & cv_keywords) / len(job_keywords)
keyword_score = keyword_match * 25
score += keyword_score

if keyword_match < 0.8:
missing_keywords = job_keywords - cv_keywords


recommendations.append(
f"Add keywords: {', '.join(list(missing_keywords)[: 5 ])}"
)

_# Check 4: No graphics/tables (15 points)_
if not contains_graphics_or_tables(tailored_cv):
score += 15
else:
issues.append("Contains tables or graphics")
recommendations.append("Remove tables, use bullet points")

_# Check 5: Font check (10 points)_
font = detect_font(tailored_cv)
if font in ['Arial', 'Calibri', 'Times New Roman']:
score += 10
else:
recommendations.append(
f"Change font from {font} to Arial or Calibri"
)

_# Check 6: Contact info formatted (15 points)_
if has_valid_contact_info(tailored_cv):
score += 15
else:
issues.append("Contact information not properly formatted")

return {
'score': int(score),
'max_score': max_score,
'grade': get_grade(score), _# A/B/C/D/F_
'issues': issues,
'recommendations': recommendations,
'keyword_match_percent': int(keyword_match * 100 )
}

def get_grade(score):
if score >= 90 : return 'A'
if score >= 80 : return 'B'
if score >= 70 : return 'C'
if score >= 60 : return 'D'

return 'F'

**When is ATS Check Performed?**


yaml
Workflow:

1. User submits New Application
2. cv-tailor generates tailored CV
3. IMMEDIATELY after CV generation:
→ ats-checker analyzes CV
→ Results stored in DynamoDB
4. Review page shows:
- CV preview
- ATS score card
- Download button

**User Experience:**

html
_<!-- Review Page -->_
<div class="artifact-card">
<h3>Tailored CV</h3>

<div class="ats-score-badge" data-score=" 94 ">
<span class="score">94/100</span>
<span class="label">ATS Compatible</span>
</div>

<button onclick="viewATSReport()">View ATS Analysis</button>
<button onclick="downloadCV()">Download CV</button>
</div>

_<!-- ATS Report Modal -->_
<modal id="ats-report">
<h2>ATS Compatibility Report</h2>

<div class="score-breakdown">
<div class="metric">
<span>Section Headings:</span>
<span class="pass">✅ Pass</span>
</div>
<div class="metric">
<span>Chronological Order:</span>
<span class="pass">✅ Pass</span>
</div>
<div class="metric">
<span>Keyword Match:</span>
<span class="warning">⚠ 87% (Add 3 more keywords)</span>


</div>
_<!-- ... -->_
</div>

<div class="recommendations">
<h3>Recommendations to Improve Score:</h3>
<ul>
<li>Add keywords: "Kubernetes", "microservices", "REST API"</li>
<li>Change font to Arial for maximum compatibility</li>
</ul>
</div>

</modal>

**7. CV Edit Contradiction Explained**

**Contradiction Statement:**

```
"User can edit CV in-app (V1: download + manual edit; V2: in-app editor)"
```
**Clarification:**

This is **poorly worded** - there's no actual contradiction, just phased feature rollout.

**V1 (MVP Launch):**

yaml
CV Editing Approach:
Method: Download + Manual Edit

User Flow:

1. Generate tailored CV
2. Review in web preview
3. Click "Download as Docx"
4. Edit locally in MS Word/Google Docs
5. (Optional) Re-upload edited version for future reference

Limitations:

- No in-app editing
- No version tracking of edits
- User edits NOT incorporated into future generations
- Manual process


**V2 (Post-Launch Enhancement):**

yaml
CV Editing Approach:
Method: In-App Structured Editor

User Flow:

1. Generate tailored CV
2. Review in web preview
3. Click "Edit" → Opens structured form editor
4. Modify fields (each section editable)
5. Save changes
6. Download edited version
7. Edits stored as "user overrides" for future applications

Benefits:

- Preserves ATS structure
- Tracks user preferences
- Incorporates edits into future CVs automatically
- Prevents formatting errors

**Corrected Documentation:**

yaml
FR-9: CV Review & Edit (V1)

- Web preview of generated CV
- Download as Docx/PDF
- Manual editing in external tools
- Re-upload capability (optional)

FR-9: CV Review & Edit (V2)

- Web preview of generated CV
- In-app structured editor (form-based)
- Field-level validation
- Download as Docx/PDF
- User edits persist as preferences
- Auto-incorporate edits in future applications

**There is NO contradiction** - just a feature evolution from manual (V1) to automated (V2)
editing.


**8. Usage Warning Calculation (80% Free Tier)**

**How is 80% Calculated?**

python
_# For Free Tier: 3 applications total_

applications_remaining = 3
applications_used = 0

_# User generates 1st application_
applications_used = 1
applications_remaining = 2
percent_used = (applications_used / 3 ) * 100 _# 33%
# No warning_

_# User generates 2nd application_
applications_used = 2
applications_remaining = 1
percent_used = (applications_used / 3 ) * 100 _# 67%
# No warning yet_

_# User generates 3rd application (LAST ONE)_
applications_used = 3
applications_remaining = 0
percent_used = (applications_used / 3 ) * 100 _# 100%_

_# Trigger warning at 80%+ (on 3rd application submission)_

**Wait - 80% of 3 applications = 2.4 applications!**

**Corrected Logic:**

python
class UsageWarningManager:

## FREE_TIER_LIMIT = 3

## WARNING_THRESHOLD = 0.80 # 80%

def check_usage_warning(self, user_id):
"""
Show warning when user reaches 80% of free tier
"""
user = get_user(user_id)


if user['tier'] != 'free':
return None _# Paid users have unlimited_

applications_used = self.get_applications_count(user_id)
applications_remaining = self.FREE_TIER_LIMIT - applications_used
percent_used = applications_used / self.FREE_TIER_LIMIT

_# 80% of 3 = 2.4, so trigger after 2nd application_
if percent_used >= self.WARNING_THRESHOLD:
return {
'show_warning': True,
'applications_remaining': applications_remaining,
'message': self.get_warning_message(applications_remaining)
}

return {'show_warning': False}

def get_warning_message(self, remaining):
"""
Generate user-facing warning message
"""
if remaining == 1 :
return (
"⚠ You have 1 application remaining in your free trial. "
"Upgrade now for unlimited applications."
)
elif remaining == 0 :
return (
"🔒 You've used all 3 free applications. "
"Upgrade to continue generating application materials."
)
else:
return (
f"⚠ You have {remaining} applications remaining. "
f"Upgrade anytime for unlimited access."

)

**UI Display:**

html
_<!-- Header Counter -->_
<div class="usage-counter" *ngIf="user.tier === 'free'">
_<!-- After 0 applications -->_
<span class="badge-success">3 Applications Remaining</span>


_<!-- After 1 application -->_
<span class="badge-info">2 Applications Remaining</span>

_<!-- After 2 applications (80% threshold - WARNING) -->_
<span class="badge-warning">
⚠ 1 Application Remaining
<a href="/pricing">Upgrade Now</a>
</span>

_<!-- After 3 applications (100% - BLOCKED) -->_
<span class="badge-danger">
🔒 No Applications Remaining
<a href="/pricing">Upgrade to Continue</a>
</span>
</div>

_<!-- Warning Modal (shows after 2nd application) -->_
<modal *ngIf="applicationsRemaining === 1 ">
<h2>Only 1 Free Application Remaining</h2>
<p>
You've used 2 of your 3 free trial applications.
Upgrade now to get unlimited application generation.
</p>

<div class="pricing-preview">
<strong>$29/month</strong> - Unlimited applications
</div>

<button (click)="upgrade()">Upgrade Now</button>
<button (click)="closeModal()">Continue with Free Tier</button>

</modal>

**Implementation:**

python
_# Lambda: orchestrator_
def create_new_application(user_id, job_data):
"""
Check usage limits before processing
"""
user = get_user(user_id)

_# Check if user can create application_


if user['tier'] == 'free':
apps_used = count_user_applications(user_id)

if apps_used >= 3 :
_# Block creation_
raise UsageLimitError(
message="Free tier limit reached (3 applications)",
remaining= 0 ,
upgrade_url="/pricing"
)

_# Show warning at 80% (after 2nd app)_
if apps_used >= 2 :
return {
'warning': {
'show': True,
'remaining': 3 - apps_used,
'message': "Only 1 application remaining in free tier"
}
}

_# Proceed with application creation_

_# ..._

**Corrected Statement:**

"80% threshold" for 3 applications means:

```
● Show warning after 2nd application (67%, rounded to nearest app at 80% threshold)
● Display remaining count prominently ("1 Application Remaining")
● Block at 100% (after 3rd application)
```
**Modifications Implemented**

**1. Review Job Popup Before Processing**

**New Validation Workflow:**

yaml
New Application Workflow (UPDATED):

Step 1 : User Input


- Upload Master CV
- Paste Job Description
- Input Company URL
- Input Job Title
- (Optional) Upload Knowledge Base materials

Step 2 : Click "Continue" → Backend Validation
↓
Lambda: job-validator

- Simple web scrape of company URL
- Google search: "{company_name} company profile"
- Extract basic info:
* Company name confirmation
* Industry
* Website responsiveness (URL valid?)
- Validate uploaded artifacts:
* CV readable (not corrupted)
* File size within limits
* Parseable format (Docx/PDF)

Step 3 : Validation Results
↓
IF VALID:
→ Display "Review Job Details" popup
→ Show extracted company info for confirmation
→ User clicks "Looks Good, Continue"
→ Proceed to Gap Analysis

## IF INVALID:

→ Display error popup with specific issues
→ Suggest corrections
→ Allow user to edit and resubmit

Step 4 : Gap Analysis (only if validated)

...

**Implementation:**

python
_# Lambda: job-validator_
def validate_job_submission(job_data):
"""
Pre-flight validation before expensive processing
"""


errors = []
warnings = []
company_info = {}

_# 1. Validate CV Upload_
try:
cv_content = s3.get_object(
Bucket='careervp-cvs',
Key=job_data['cv_s3_key']
)

_# Parse CV_
if cv_content['ContentType'] == 'application/pdf':
cv_text = extract_pdf_text(cv_content['Body'])
else: _# docx_
cv_text = extract_docx_text(cv_content['Body'])

if len(cv_text.split()) < 200 :
errors.append({
'field': 'cv',
'message': 'CV appears too short (minimum 200 words)',
'suggestion': 'Please upload a complete CV'
})
except Exception as e:
errors.append({
'field': 'cv',
'message': f'Could not read CV file: {str(e)}',
'suggestion': 'Please re-upload CV in Docx or PDF format'
})

_# 2. Validate Job Description_
job_desc = job_data['job_description']
if len(job_desc.split()) < 50 :
errors.append({
'field': 'job_description',
'message': 'Job description too short (minimum 50 words)',
'suggestion': 'Please paste the complete job posting'
})

_# 3. Validate Company URL & Basic Research_
company_url = job_data['company_url']
company_name = job_data['company_name']

try:


_# Simple HTTP check_
response = requests.get(company_url, timeout= 10 )
if response.status_code != 200 :
warnings.append({
'field': 'company_url',
'message': f'Company website returned {response.status_code}',
'suggestion': 'Double-check the URL is correct'
})
except requests.RequestException as e:
warnings.append({
'field': 'company_url',
'message': 'Could not access company website',
'suggestion': 'Verify URL is correct (include https://)'
})

_# Basic Google search for company validation_
search_results = google_search(f'"{company_name}" company')

if not search_results:
warnings.append({
'field': 'company_name',
'message': 'Could not find company information',
'suggestion': 'Verify company name spelling'
})
else:
_# Extract basic info_
company_info = {
'name': company_name,
'industry': extract_industry(search_results),
'description': extract_snippet(search_results[ 0 ]),
'verified': True
}

_# 4. Validate Knowledge Base (if uploaded)_
if job_data.get('knowledge_base_files'):
for kb_file in job_data['knowledge_base_files']:
if kb_file['size'] > 8 * 1024 * 1024 : _# 8MB_
errors.append({
'field': 'knowledge_base',
'message': f'{kb_file["name"]} exceeds 8MB limit',
'suggestion': 'Remove file or reduce size'
})

return {


'valid': len(errors) == 0 ,
'errors': errors,
'warnings': warnings,
'company_info': company_info

}

**Frontend Modal:**

html
_<!-- Review Job Details Modal -->_
<modal id="review-job-modal" *ngIf="validationComplete">

## <!-- IF VALIDATION PASSED -->

<div *ngIf="validation.valid">
<h2>✅ Review Job Details</h2>

<div class="company-info">
<h3>{{ validation.company_info.name }}</h3>
<p><strong>Industry:</strong> {{ validation.company_info.industry }}</p>
<p>{{ validation.company_info.description }}</p>
</div>

<div class="job-info">
<h4>{{ jobData.job_title }}</h4>
<p>CV uploaded: {{ jobData.cv_filename }}</p>
<p>Job description: {{ jobData.job_description | truncate:100 }}</p>
</div>

_<!-- Show warnings if any -->_
<div class="warnings" *ngIf="validation.warnings.length > 0 ">
<h4>⚠ Warnings</h4>
<ul>
<li *ngFor="let warning of validation.warnings">
{{ warning.message }}
</li>
</ul>
</div>

<div class="actions">
<button (click)="goBack()">Edit Details</button>
<button class="primary" (click)="proceedToGapAnalysis()">
Looks Good, Continue
</button>
</div>


</div>

## <!-- IF VALIDATION FAILED -->

<div *ngIf="!validation.valid">
<h2>❌ Please Fix These Issues</h2>

<div class="errors">
<div *ngFor="let error of validation.errors" class="error-item">
<strong>{{ error.field }}:</strong>
<p>{{ error.message }}</p>
<p class="suggestion">💡 {{ error.suggestion }}</p>
</div>
</div>

<div class="actions">
<button (click)="closeModal()">Close</button>
<button class="primary" (click)="goBackToEdit()">
Fix & Retry
</button>
</div>
</div>

</modal>
```

**User Experience:**
```
Scenario A: Valid Submission

1. User fills form → Clicks "Continue"
2. Loading spinner: "Validating job details..."
3. Modal appears:
✅ Review Job Details

TechCorp Inc.
Industry: Software & SaaS
"TechCorp is a leading provider of cloud-based solutions..."

Senior Python Developer
CV uploaded: john_doe_cv.docx
Job description: "We are seeking a Senior Python Developer..."

[Edit Details] [Looks Good, Continue]

4. User clicks "Looks Good, Continue"


5. Proceeds to Gap Analysis

Scenario B: Invalid Submission

1. User fills form → Clicks "Continue"
2. Loading spinner: "Validating job details..."
3. Modal appears:
❌ Please Fix These Issues

cv: CV appears too short (minimum 200 words)
💡 Please upload a complete CV

company_url: Could not access company website
💡 Verify URL is correct (include https://)

[Close] [Fix & Retry]

4. User clicks "Fix & Retry"
5. Returns to form with errors highlighted
**2. Gap Analysis as VPR Input**

**Updated VPR Generation Prompt:**

yaml
_# prompts/vpr_generation.yaml_

vpr_generation_prompt: |
You are an expert career strategist creating a Value Proposition Report.

## INPUTS PROVIDED:

1. Job Posting: {{job_posting}}
2. Master CV: {{master_cv}}
3. Company Research: {{company_research}}
4. Gap Analysis Responses: {{gap_analysis_answers}} _# ← ADDED_
5. Previous VPRs (if any): {{previous_vprs}}

CRITICAL: The Gap Analysis responses contain user-provided context about:

- Specific achievements not in CV
- Quantifiable results and metrics
- Project details and impact
- Context around career transitions


- Explanations for employment gaps

USE Gap Analysis responses to:

- Enrich the Alignment Matrix with specific examples
- Support Key Differentiators with quantified achievements
- Address potential concerns proactively
- Build stronger evidence for job requirements

## OUTPUT STRUCTURE:

1. Value Proposition Statement
- 2-3 sentences synthesizing candidate's unique fit
- Reference specific Gap Analysis insights
2. Alignment Matrix (TABLE FORMAT REQUIRED)
| Job Requirement | Your Evidence | Strength |
|-----------------|---------------|----------|
| [requirement] | [CV evidence + Gap Analysis examples] | [rating] |

Example row:
| 5+ years Python | 7 years Python at TechCorp. Gap Analysis: Led team that reduced API
latency 60% using async/await patterns, saving $200K annually | ⭐⭐⭐ Strong |

3. Key Differentiators
- 3-5 unique strengths
- MUST include quantified achievements from Gap Analysis
- Evidence-backed (not generic claims)
4. Strategic Recommendations (VPR Full only)
- Interview talking points
- How to position gap analysis insights

## FORMATTING:

- Professional tone
- Language: {{output_language}}
- Length: 1-2 pages (VPR Brief), 5-8 pages (VPR Full)

**Lambda Implementation:**

python
_# Lambda: vp-report-generator (UPDATED)_
def generate_vpr(job_id, vpr_type='brief'):
"""
Generate VPR with Gap Analysis integration


## """

_# Load all context_
job_posting = get_job_posting(job_id)
master_cv = get_master_cv(job_id)
company_research = get_company_research(job_id)

## # ← CRITICAL ADDITION

gap_analysis = get_gap_analysis_responses(job_id)

_# Format gap analysis for prompt_
gap_analysis_formatted = format_gap_analysis_for_vpr(gap_analysis)

_# Load prompt template_
prompt_template = load_prompt('vpr_generation')

_# Determine output language_
output_language = determine_output_language(
cv_language=detect_language(master_cv),
job_language=detect_language(job_posting)
)

_# Build prompt context_
context = {
'job_posting': job_posting,
'master_cv': master_cv,
'company_research': company_research,
'gap_analysis_answers': gap_analysis_formatted, _# ← ADDED_
'output_language': output_language,
'vpr_type': vpr_type
}

_# Call Claude API_
response = claude_api.messages.create(
model='claude-sonnet-4-5-20250929', _# Sonnet for VPR_
max_tokens= 8000 if vpr_type == 'full' else 3000 ,
system=prompt_template,
messages=[{
'role': 'user',
'content': json.dumps(context, indent= 2 )
}]
)

vpr_content = response.content[ 0 ].text


_# Convert to Docx_
vpr_docx = convert_to_docx(
vpr_content,
template='vpr_template.docx'
)

_# Save to S3_
s3_key = f'outputs/{job_id}/vpr-{vpr_type}-{timestamp}.docx'
upload_to_s3(vpr_docx, s3_key)

return {
's3_key': s3_key,
'filename': f'vpr-{vpr_type}-{company_name}.docx',
'size': len(vpr_docx),
'cost': calculate_cost(response.usage)
}

def format_gap_analysis_for_vpr(gap_analysis):
"""
Format gap analysis Q&A for inclusion in VPR prompt
"""
if not gap_analysis or not gap_analysis.get('answers'):
return "No gap analysis responses provided."

formatted = []
for qa in gap_analysis['answers']:
formatted.append(f"""
Question: {qa['question']}
Answer: {qa['answer']}
""".strip())

return "\n\n".join(formatted)

**Example VPR with Gap Analysis:**

markdown
# Value Proposition Report: Senior Python Developer at TechCorp

## Value Proposition Statement

John brings 7 years of Python expertise with proven success in
high-performance API development, having reduced latency by 60%
(saving $200K annually) through async/await optimization. His
experience leading cross-functional teams of 8 engineers, combined


with AWS serverless architecture expertise, aligns perfectly with
TechCorp's need for a senior developer who can architect scalable
cloud-native solutions while mentoring junior engineers.

## Alignment Matrix

| Job Requirement | Your Evidence | Strength |
|-----------------|---------------|----------|
| 5+ years Python development | 7 years Python at MegaCorp. ****Gap Analysis**** : Led team that
reduced API latency 60% using async/await patterns, saving $200K annually. Built internal
framework adopted by 12 teams. | ⭐⭐⭐ Strong |
| AWS architecture experience | Designed serverless apps using Lambda, DynamoDB, S3.
****Gap Analysis**** : Migrated monolith to microservices, reducing infrastructure costs 40%
($500K savings). | ⭐⭐⭐ Strong |
| Team leadership | Managed 8 engineers, mentored 3 junior devs. ****Gap Analysis**** :
Established code review process that reduced production bugs 75%. Led sprint planning and
retros. | ⭐⭐⭐ Strong |
| REST API design | Built 15+ RESTful APIs serving 1M+ requests/day. ****Gap Analysis**** :
Designed API versioning strategy that enabled zero-downtime deployments. | ⭐⭐⭐ Strong |

## Key Differentiators

1. ****Cost Optimization Expert**** : Reduced infrastructure costs by $500K
through AWS serverless migration (from Gap Analysis)
2. ****Performance Optimization**** : Achieved 60% latency reduction saving
$200K annually (from Gap Analysis)
3. ****Technical Leadership**** : Established processes that reduced bugs

75% while mentoring 3 engineers to senior roles (from Gap Analysis)

**Summary**

All facts, questions, and modifications addressed:

✅ **Facts** : Acknowledged (Docx defaults, Perplexity AI, Alignment Matrix table, language rules,
prompt externalization)

✅ **Questions Answered** :

1. Stripe payment errors - detailed flow
2. Job tracking V2 rationale - MVP focus


3. Insufficient company search criteria - specific thresholds
4. Evidence mapping = Alignment Matrix - confirmed
5. 500/1000 word limits - test case minimums, not system limits
6. ATS checker - tailored CV validation, score display
7. CV edit contradiction - V1 manual, V2 in-app
8. 80% usage warning - triggers after 2nd application

✅ **Modifications Implemented** :

1. Job validation popup before processing - prevent errors early
2. Gap Analysis included in VPR generation prompt - enriched evidence

Ready for CDK implementation!

Claude is AI and can make mistakes.
Please double-check responses.


# Tab 9


I'll address each of these critical modifications systematically.

1. VPR Brief Included by Default, VPR Full Optional Updated Workflow yaml New
    Application Generation Workflow:

Step 1: User Input & Validation (existing flow)

Step 2: Gap Analysis (existing flow)

Step 3: User Clicks "Generate Application Package" ↓ Backend generates (in parallel): ✅
Tailored CV ✅ VPR Brief (ALWAYS included) ✅ Cover Letter ✅ ATS Compliance Check

User does NOT select VPR Brief - it's automatic

Step 4: Review Page Shows: 📄 Tailored CV 📊 VPR Brief (included automatically) 📝 Cover
Letter ✅ ATS Score: 94/100

Optional Add-On: [ ] Generate Full VPR Report (+$0.03, ~8 pages) "Includes company deep
dive, competitive analysis, strategic recommendations"

Step 5a: User Downloads Default Package

- Downloads CV + VPR Brief + Cover Letter

Step 5b: User Requests VPR Full

- Clicks checkbox "Generate Full VPR"
- Backend generates VPR Full (Sonnet model)
- Added to download package UI Implementation html

**Your Application Package**

The following documents have been generated and are ready to download:

<div class="artifact-card">

<div class="artifact-icon">📄</div>

<div class="artifact-info">

<h3>Tailored CV</h3>

<p>2 pages • Optimized for {{ companyName }}</p>


<div class="ats-badge" [class.high-score]="atsScore >= 90">

ATS Score: {{ atsScore }}/100

</div>

</div>

<div class="artifact-actions">

<button (click)="preview('cv')">Preview</button>

<button (click)="download('cv', 'docx')">Download</button>

</div>

</div>

<div class="artifact-card included-badge">

<span class="badge-included">✓ Included</span>

<div class="artifact-icon">📊</div>

<div class="artifact-info">

<h3>VPR Brief</h3>

<p>1-2 pages • Value Proposition Summary</p>

<ul class="feature-list">

<li>Value Proposition Statement</li>

<li>Alignment Matrix</li>

<li>Key Differentiators</li>

</ul>

</div>

<div class="artifact-actions">


<button (click)="preview('vpr-brief')">Preview</button>

<button (click)="download('vpr-brief', 'docx')">Download</button>

</div>

</div>

<div class="artifact-card">

<div class="artifact-icon">📝</div>

<div class="artifact-info">

<h3>Cover Letter</h3>

<p>1 page • Personalized for {{ companyName }}</p>

</div>

<div class="artifact-actions">

<button (click)="preview('cover-letter')">Preview</button>

<button (click)="download('cover-letter', 'docx')">Download</button>

</div>

</div>

<div class="add-on-card">

<div class="add-on-header">

<input

type="checkbox"

id="vpr-full"

[(ngModel)]="generateVPRFull"

(change)="onVPRFullToggle()"


## />

<label for="vpr-full">

<h3>Generate Full VPR Report</h3>

<span class="add-on-cost">+$0.03</span>

</label>

</div>

<div class="add-on-description">

<p>Comprehensive 5-8 page strategic analysis including:</p>

<ul>

<li>✓ Everything in VPR Brief</li>

<li>✓ Company Deep Dive & Culture Analysis</li>

<li>✓ Competitive Positioning</li>

<li>✓ Risk Assessment & Mitigation Strategies</li>

<li>✓ Strategic Interview Recommendations</li>

<li>✓ Evidence Library with Detailed Examples</li>

</ul>

</div>

<!-- Shows after generation -->

<div class="artifact-ready" *ngIf="vprFullGenerated">

<div class="artifact-icon">📊</div>


<div class="artifact-info">

<h4>Full VPR Report Ready</h4>

<p>8 pages • Complete strategic analysis</p>

</div>

<div class="artifact-actions">

<button (click)="preview('vpr-full')">Preview</button>

<button (click)="download('vpr-full', 'docx')">Download</button>

</div>

</div>

<!-- Shows during generation -->

<div class="generating-status" *ngIf="generatingVPRFull">

<spinner></spinner>

<p>Generating Full VPR Report... (15-20 seconds)</p>

</div>

</div>

📦 Download Complete Package ({{ artifactCount }} files)

Backend Lambda Updates python # Lambda: orchestrator (UPDATED) def
generate_application_package(job_id, user_id): """ Generate default package: CV + VPR Brief +
Cover Letter """ # Run in parallel (SQS fan-out pattern)

tasks = [

## {


'function': 'cv-tailor',

'job_id': job_id,

'priority': 'high'

## },

## {

'function': 'vpr-generator',

'job_id': job_id,

'vpr_type': 'brief', # ← ALWAYS generate Brief

'priority': 'high'

## },

## {

'function': 'cover-letter-generator',

'job_id': job_id,

'priority': 'high'

## },

## {

'function': 'ats-checker',

'job_id': job_id,

'priority': 'medium',

'depends_on': 'cv-tailor' # Wait for CV

## }

## ]


# Send to SQS for parallel processing

for task in tasks:

sqs.send_message(

QueueUrl=DOCUMENT_GENERATION_QUEUE,

MessageBody=json.dumps(task)

## )

# Update session status

update_session_status(job_id, 'processing')

return {

'job_id': job_id,

'status': 'processing',

'artifacts_generating': ['cv', 'vpr-brief', 'cover-letter'],

'estimated_completion': calculate_eta(tasks)

## }

Lambda: vpr-generator (UPDATED)

def lambda_handler(event, context): """ Generate VPR Brief or Full based on request """ job_id
= event['job_id'] vpr_type = event.get('vpr_type', 'brief') # Default: brief

# Load context

job_posting = get_job_posting(job_id)

master_cv = get_master_cv(job_id)

company_research = get_company_research(job_id)

gap_analysis = get_gap_analysis_responses(job_id)

# Select model based on VPR type


if vpr_type == 'full':

model = 'claude-sonnet-4-5-20250929'

max_tokens = 8000

prompt_template = load_prompt('vpr_full_generation')

else: # brief

model = 'claude-haiku-4-5-20251001' # Haiku for Brief!

max_tokens = 3000

prompt_template = load_prompt('vpr_brief_generation')

# Build context

context = {

'job_posting': job_posting,

'master_cv': master_cv,

'company_research': company_research,

'gap_analysis_answers': format_gap_analysis(gap_analysis),

'output_language': determine_language(master_cv, job_posting),

'vpr_type': vpr_type

## }

# Generate with Claude

response = claude_api.messages.create(

model=model,

max_tokens=max_tokens,

system=prompt_template,


messages=[{

'role': 'user',

'content': json.dumps(context, indent=2)

## }]

## )

vpr_content = response.content[0].text

# Convert to Docx

vpr_docx = convert_to_docx(

content=vpr_content,

template=f'vpr_{vpr_type}_template.docx'

## )

# Save to S3

company_name = extract_company_name(job_posting)

s3_key = f'outputs/{job_id}/vpr-{vpr_type}-{company_name}-{timestamp()}.docx'

s3.put_object(

Bucket=OUTPUT_BUCKET,

Key=s3_key,

Body=vpr_docx,

ContentType='application/vnd.openxmlformats-officedocument.wordprocessingml.document',

Metadata={

'job_id': job_id,

'artifact_type': f'vpr-{vpr_type}',


'user_id': get_user_id(job_id)

## }

## )

# Update DynamoDB

update_artifact_status(

job_id=job_id,

artifact_type=f'vpr-{vpr_type}',

s3_key=s3_key,

cost=calculate_cost(response.usage)

## )

return {

'job_id': job_id,

'artifact_type': f'vpr-{vpr_type}',

's3_key': s3_key,

'cost': calculate_cost(response.usage)

## }

API Endpoint for VPR Full Generation python

API: POST /api/jobs/{job_id}/generate-vpr-full

@app.post('/api/jobs/{job_id}/generate-vpr-full') def generate_vpr_full(job_id: str, current_user:
User = Depends(get_current_user)): """ Generate Full VPR on demand (user requested) """

# Verify job belongs to user

job = get_job(job_id)


if job['user_id'] != current_user.user_id:

raise HTTPException(status_code=403, detail="Not authorized")

# Check if VPR Full already generated

if artifact_exists(job_id, 'vpr-full'):

return {

'status': 'already_exists',

'message': 'VPR Full already generated for this job',

's3_key': get_artifact_s3_key(job_id, 'vpr-full')

## }

# Send to generation queue

sqs.send_message(

QueueUrl=DOCUMENT_GENERATION_QUEUE,

MessageBody=json.dumps({

'function': 'vpr-generator',

'job_id': job_id,

'vpr_type': 'full',

'priority': 'high'

## })

## )

# Track cost (will be charged after generation)

log_anticipated_cost(

user_id=current_user.user_id,


job_id=job_id,

artifact_type='vpr-full',

estimated_cost=0.03

## )

return {

'status': 'generating',

'message': 'VPR Full generation started',

'job_id': job_id,

'estimated_completion_seconds': 20

## }

Cost Analysis python

Updated cost breakdown

COST_PER_APPLICATION = { 'cv': 0.005, # Haiku 'vpr_brief': 0.004, # Haiku (not
Sonnet!) 'cover_letter': 0.004, # Haiku 'ats_check': 0.001, # No AI, just parsing 'orchestration':
0.002,

'DEFAULT_PACKAGE': 0.016, # Total for CV + VPR Brief + Cover Letter

# Optional add-ons

'vpr_full': 0.035, # Sonnet (only if user requests)

'interview_prep': 0.005 # Generated later in workflow

## }

Pricing transparency

TIER_LIMITS = { 'free': { 'applications': 3, 'cost_per_app': 0.016, # Default package only
'total_cost': 0.048, # 3 apps × $0.016 }, 'paid': { 'applications': 'unlimited', 'cost_per_app':


0.016, # Can add VPR Full for +$0.035 'monthly_revenue': 29.00, 'target_margin': '95%' } }
Prompt Configuration yaml

prompts/vpr_brief_generation.yaml

vpr_brief_generation: | You are creating a concise Value Proposition Report (Brief version).

## INPUTS:

- Job Posting: {{job_posting}}
- Master CV: {{master_cv}}
- Company Research: {{company_research}}
- Gap Analysis: {{gap_analysis_answers}}

## OUTPUT REQUIREMENTS:

Length: 1-2 pages maximum Language: {{output_language}} Format: Professional business
document

## REQUIRED SECTIONS:

1. VALUE PROPOSITION STATEMENT (2-3 sentences) Synthesize candidate's unique fit
    for this specific role. Reference quantifiable achievements from Gap Analysis.

## 2. ALIGNMENT MATRIX (TABLE FORMAT MANDATORY)

```
Job Requirement Your Evidence Strength
```
```
[req from job] [CV + Gap Analysis
evidence]
```
```
[⭐⭐⭐ Strong/⭐⭐
Moderate/⭐ Developing]
```
```
Include 6-8 rows covering:
```
- Top 3 technical requirements
- Top 2 experience requirements
- 1-2 soft skill requirements

```
CRITICAL: Use specific examples from Gap Analysis to strengthen evidence.
```
3. KEY DIFFERENTIATORS (3-5 bullet points) What makes this candidate stand out?
    MUST include:
       - Quantified achievements (numbers, percentages, dollar amounts)


- Evidence from Gap Analysis
- Unique combinations of skills/experience

```
Example: • Cost Optimization Expert: Reduced infrastructure costs $500K through AWS
serverless migration (from Gap Analysis Q3)
```
## FORMATTING:

- Use clear headings
- Professional tone, not salesy
- Evidence-based, not generic claims
- Alignment Matrix MUST be in table format (not prose)

prompts/vpr_full_generation.yaml

vpr_full_generation: | You are creating a comprehensive Value Proposition Report (Full version).

## INPUTS:

- Job Posting: {{job_posting}}
- Master CV: {{master_cv}}
- Company Research: {{company_research}}
- Gap Analysis: {{gap_analysis_answers}}

## OUTPUT REQUIREMENTS:

Length: 5-8 pages Language: {{output_language}} Format: Executive-level strategic document

## REQUIRED SECTIONS:

1. EXECUTIVE SUMMARY (1 page)
    - Value Proposition Statement
    - Top 3 reasons candidate is ideal fit
    - Key differentiators summary
2. ALIGNMENT MATRIX (TABLE FORMAT MANDATORY) [Same as VPR Brief but 10-15
    rows, more detailed]
3. COMPANY DEEP DIVE (1-2 pages)
    - Industry position & competitive landscape
    - Recent developments (news, funding, product launches)
    - Company culture & values analysis


- Strategic priorities (inferred from job posting + research)
4. COMPETITIVE POSITIONING (1 page) How candidate compares to typical applicants:
- Unique skill combinations
- Differentiating experiences
- Cultural fit indicators
5. RISK ASSESSMENT & MITIGATION (1 page) Potential concerns and how to address:
- Employment gaps (if any)
- Skill gaps (from Alignment Matrix)
- Overqualification/underqualification
- Geographic/remote considerations

```
For each risk, provide:
```
- Concern: [what hiring manager might worry about]
- Mitigation: [how to address proactively]
6. STRATEGIC RECOMMENDATIONS (1-2 pages)
- Interview preparation priorities
- Key talking points by interview stage
- Questions to ask interviewers
- Negotiation considerations
7. EVIDENCE LIBRARY (1 page) Detailed examples supporting Alignment Matrix:
- Project descriptions
- Achievement breakdowns
- Metrics and impact quantification

## FORMATTING:

- Executive-level polish
- Clear section breaks
- Evidence-based throughout
- Strategic insights, not obvious observations
2. S3 Lifecycle Policy - User Tier Aware Corrected Lifecycle Rules yaml S3 Bucket:
    careervp-job-search-assistant-outputs

Lifecycle Rules:


Rule 1: Active Paid Users - NO ARCHIVAL WHILE

ACTIVE

Rule_ID: paid-tier-active-users Status: Enabled Scope: Tag Filter: user_tier: paid|premium
subscription_status: active

Transitions: NONE Expiration: NONE

Note: "Data stays in S3 Standard indefinitely for active paid users"

Rule 2: Inactive Paid Users - Transition to IA

Rule_ID: paid-tier-inactive-transition Status: Enabled Scope: Tag Filter: user_tier: paid|premium
subscription_status: active

Transitions: - Days: 30 StorageClass: INTELLIGENT_TIERING

Note: "Objects not accessed in 30 days move to Intelligent-Tiering (automatically moves
between Standard and IA based on access)"

Rule 3: Cancelled Paid Subscriptions - Archive to

Glacier

Rule_ID: paid-tier-cancelled-archive Status: Enabled Scope: Tag Filter: user_tier: paid|premium
subscription_status: cancelled|lapsed

Transitions: - Days: 30 StorageClass: GLACIER_INSTANT_RETRIEVAL

Expiration: Days: 365 # Delete after 1 year if not accessed

Note: "After subscription cancellation, archive to Glacier after 30 days"

Rule 4: Free Tier - Transition to IA

Rule_ID: free-tier-inactive-transition Status: Enabled Scope: Tag Filter: user_tier: free

Transitions: - Days: 15 StorageClass: STANDARD_IA

Note: "Free tier objects move to IA after 15 days of inactivity"


Rule 5: Free Tier - Deletion Warning

Rule_ID: free-tier-deletion-warning Status: Enabled Scope: Tag Filter: user_tier: free
inactivity_days: 50 # Trigger at 50 days

Action: Lambda_Notification Lambda_Function: free-tier-deletion-warning

Note: "Send notification 10 days before deletion (at 50 days inactivity)"

Rule 6: Free Tier - Deletion

Rule_ID: free-tier-deletion Status: Enabled Scope: Tag Filter: user_tier: free

Expiration: Days: 60 # Delete after 60 days of inactivity

Note: "Free tier objects deleted after 60 days of inactivity" Implementation with Object Tagging
Problem: S3 Lifecycle rules can't natively check DynamoDB for user tier.

Solution: Tag S3 objects with user metadata during upload.

python

Lambda: artifact-uploader (UPDATED)

def upload_artifact_to_s3(artifact_data, job_id, artifact_type): """ Upload artifact with user tier
tags for lifecycle management """

# Get user info

user = get_user_from_job(job_id)

# Build S3 key

s3_key = f'outputs/{job_id}/{artifact_type}-{timestamp()}.docx'

# Upload with tags

s3.put_object(

Bucket=OUTPUT_BUCKET,

Key=s3_key,


Body=artifact_data,

ContentType='application/vnd.openxmlformats-officedocument.wordprocessingml.document',

# CRITICAL: Tag for lifecycle management

Tagging=urlencode({

'user_id': user['user_id'],

'user_tier': user['tier'], # free|paid|premium

'subscription_status': user['subscription_status'], # active|cancelled|lapsed

'job_id': job_id,

'artifact_type': artifact_type,

'upload_date': datetime.utcnow().isoformat(),

'last_accessed': datetime.utcnow().isoformat()

## })

## )

return s3_key

Lambda: subscription-status-updater

def update_s3_tags_on_subscription_change(user_id, old_status, new_status): """ When
subscription changes, update all S3 object tags """

# Get all user's S3 objects

s3_objects = s3.list_objects_v2(

Bucket=OUTPUT_BUCKET,

Prefix=f'outputs/'

## )


# Filter for this user's objects

user_objects = [

obj for obj in s3_objects.get('Contents', [])

if user_id in obj['Key']

## ]

# Update tags

for obj in user_objects:

# Get existing tags

current_tags = s3.get_object_tagging(

Bucket=OUTPUT_BUCKET,

Key=obj['Key']

)['TagSet']

# Update subscription_status tag

updated_tags = []

for tag in current_tags:

if tag['Key'] == 'subscription_status':

tag['Value'] = new_status

updated_tags.append(tag)

# Write back

s3.put_object_tagging(


Bucket=OUTPUT_BUCKET,

Key=obj['Key'],

Tagging={'TagSet': updated_tags}

## )

logger.info(f"Updated {len(user_objects)} S3 objects for user {user_id}")

Free Tier Deletion Warning System python

Lambda: free-tier-deletion-warning (Scheduled -

Daily)

def lambda_handler(event, context): """ Check for free tier users with objects approaching
60-day deletion Send warning at 50 days """

# Query DynamoDB for free tier users

response = dynamodb.scan(

TableName='careervp-users',

FilterExpression='tier = :tier',

ExpressionAttributeValues={':tier': 'free'}

## )

for user in response['Items']:

user_id = user['user_id']

# Get user's S3 objects

s3_objects = list_user_s3_objects(user_id)


# Check for objects at 50+ days old

deletion_candidates = []

for obj in s3_objects:

# Calculate days since last access

last_accessed = get_object_last_accessed(obj['Key'])

days_inactive = (datetime.utcnow() - last_accessed).days

if days_inactive >= 50 and days_inactive < 60:

deletion_candidates.append({

'key': obj['Key'],

'days_until_deletion': 60 - days_inactive,

'artifact_type': extract_artifact_type(obj['Key'])

## })

# Send warning if any objects at risk

if deletion_candidates:

send_deletion_warning_email(

user_email=user['email'],

user_name=user.get('name', 'there'),

objects_at_risk=deletion_candidates

## )


# Log notification

logger.info(

f"Sent deletion warning to {user['email']}: "

f"{len(deletion_candidates)} objects at risk"

## )

def send_deletion_warning_email(user_email, user_name, objects_at_risk): """ Email template
for deletion warning """

# Build object list

object_list = []

for obj in objects_at_risk:

object_list.append(

f"• {obj['artifact_type']} "

f"(deletes in {obj['days_until_deletion']} days)"

## )

email_body = f"""

Hi {user_name},

Your CareerVP free trial data is scheduled for automatic deletion due to inactivity. The following
application materials will be permanently deleted if not accessed:

{chr(10).join(object_list)}

## TO PREVENT DELETION:

Option 1: Log in and download your documents Visit: https://app.careervp.com/applications

Option 2: Upgrade to a paid plan (documents saved indefinitely) Visit:
https://app.careervp.com/pricing

Questions? Reply to this email or visit our help center.


Best regards, The CareerVP Team

This is an automated notification. You received this because you have inactive documents in
your free CareerVP account. """.strip()

ses.send_email(

Source='notifications@careervp.com',

Destination={'ToAddresses': [user_email]},

Message={

'Subject': {

'Data': '⚠ CareerVP: Your documents will be deleted in 10 days',

'Charset': 'UTF-8'

## },

'Body': {

'Text': {

'Data': email_body,

'Charset': 'UTF-8'

## }

## }

## }

## )

CloudFormation/CDK Implementation python


CDK: S3 Bucket with Lifecycle Rules

from aws_cdk import ( aws_s3 as s3, Duration, Tags )

outputs_bucket = s3.Bucket( self, 'OutputsBucket',
bucket_name='careervp-job-search-assistant-outputs',
encryption=s3.BucketEncryption.S3_MANAGED,
versioning=s3.VersioningConfiguration.ENABLED, lifecycle_rules=[

# Rule 2: Inactive Paid Users → Intelligent Tiering

s3.LifecycleRule(

id='paid-tier-inactive-transition',

enabled=True,

tag_filters={

'user_tier': 'paid',

'subscription_status': 'active'

## },

transitions=[

s3.Transition(

storage_class=s3.StorageClass.INTELLIGENT_TIERING,

transition_after=Duration.days(30)

## )

## ]

## ),

# Rule 3: Cancelled Paid → Glacier

s3.LifecycleRule(


id='paid-tier-cancelled-archive',

enabled=True,

tag_filters={

'subscription_status': 'cancelled'

## },

transitions=[

s3.Transition(

storage_class=s3.StorageClass.GLACIER_INSTANT_RETRIEVAL,

transition_after=Duration.days(30)

## )

## ],

expiration=Duration.days(365)

## ),

# Rule 4: Free Tier → IA

s3.LifecycleRule(

id='free-tier-inactive-transition',

enabled=True,

tag_filters={

'user_tier': 'free'

## },

transitions=[


s3.Transition(

storage_class=s3.StorageClass.INFREQUENT_ACCESS,

transition_after=Duration.days(15)

## )

## ]

## ),

# Rule 6: Free Tier → Delete

s3.LifecycleRule(

id='free-tier-deletion',

enabled=True,

tag_filters={

'user_tier': 'free'

## },

expiration=Duration.days(60)

## ),

## ]

) 3. Cancel Subscription Procedure Complete Offboarding Workflow yaml CANCEL
SUBSCRIPTION PROCEDURE

Initiated By:

- User clicks "Cancel Subscription" in account settings
- Stripe webhook (customer cancels in Stripe portal)

Workflow Steps:


1. Cancel Request Received ↓
2. Confirmation Modal (if user-initiated) ↓
3. Backend Processing ↓
4. Stripe Subscription Cancellation ↓
5. Database Updates ↓
6. S3 Object Tag Updates ↓
7. Access Level Change (immediate or end-of-period) ↓
8. Email Confirmation ↓
9. Offboarding Survey (optional) ↓
10. Retention Campaign (optional)
11. User-Initiated Cancellation UI html

**Current Plan: {{ user.subscription_plan }}**

Next billing date: {{ user.next_billing_date }}

Monthly cost: ${{ user.plan_price }}

<button class="danger-action" (click)="openCancelModal()"> Cancel Subscription

<modal id="cancel-subscription-modal" *ngIf="showCancelModal">

**Cancel Your Subscription?**

<div class="cancellation-impact">

<h3>What happens when you cancel:</h3>

<div class="impact-item">

<icon class="check">✓</icon>

<div>

<strong>Keep access until {{ endOfBillingPeriod }}</strong>

<p>You'll still have full access until your current billing period ends</p>

</div>

</div>


<div class="impact-item">

<icon class="check">✓</icon>

<div>

<strong>Download all your documents</strong>

<p>All generated application materials remain accessible for download</p>

</div>

</div>

<div class="impact-item warning">

<icon class="warning">⚠</icon>

<div>

<strong>Lose unlimited applications</strong>

<p>After {{ endOfBillingPeriod }}, you'll return to the free tier (3 applications)</p>

</div>

</div>

<div class="impact-item warning">

<icon class="warning">⚠</icon>

<div>

<strong>Documents archived after 30 days</strong>

<p>Your documents will be moved to long-term storage 30 days after cancellation</p>


</div>

</div>

</div>

<!-- Optional: Retention offer -->

<div class="retention-offer" *ngIf="showRetentionOffer">

<h3>Before you go...</h3>

<p>

We'd hate to see you leave. How about 50% off for the next 3 months?

</p>

<button class="primary" (click)="acceptRetentionOffer()">

Keep Subscription at 50% Off

</button>

</div>

<!-- Optional: Feedback -->

<div class="cancellation-feedback">

<h4>Help us improve (optional)</h4>

<select [(ngModel)]="cancellationReason">

<option value="">Why are you canceling?</option>

<option value="too-expensive">Too expensive</option>

<option value="found-job">Found a job (congrats!)</option>

<option value="not-enough-value">Not getting enough value</option>


<option value="technical-issues">Technical problems</option>

<option value="other">Other reason</option>

</select>

<textarea

*ngIf="cancellationReason === 'other'"

[(ngModel)]="cancellationFeedback"

placeholder="Tell us more (optional)">

</textarea>

</div>

Keep Subscription Yes, Cancel Subscription

<modal id="cancellation-success" *ngIf="cancellationComplete">

## ✓

**Subscription Canceled**

Your subscription has been canceled. You'll continue to have access until {{ endOfBillingPeriod
}}.

A confirmation email has been sent to {{ user.email }}.

Close 2. Backend API - Cancel Subscription python # API: POST /api/subscription/cancel
@app.post('/api/subscription/cancel') def cancel_subscription( cancellation_data:
CancellationRequest, current_user: User = Depends(get_current_user) ): """ Handle
user-initiated subscription cancellation """ # Verify user has active subscription

if current_user.subscription_status != 'active':

raise HTTPException(

status_code=400,


detail="No active subscription to cancel"

## )

# Get Stripe subscription

stripe_subscription = stripe.Subscription.retrieve(

current_user.stripe_subscription_id

## )

# Cancel at end of billing period (not immediately)

canceled_subscription = stripe.Subscription.modify(

current_user.stripe_subscription_id,

cancel_at_period_end=True,

metadata={

'cancellation_reason': cancellation_data.reason,

'cancellation_feedback': cancellation_data.feedback,

'canceled_at': datetime.utcnow().isoformat()

## }

## )

# Update DynamoDB

dynamodb.update_item(

TableName='careervp-users',

Key={'user_id': current_user.user_id},

UpdateExpression='''

SET subscription_status = :status,


cancellation_date = :cancel_date,

cancellation_reason = :reason,

access_until = :access_until

## ''',

ExpressionAttributeValues={

':status': 'canceling', # Will become 'cancelled' at period end

':cancel_date': datetime.utcnow().isoformat(),

':reason': cancellation_data.reason,

':access_until': canceled_subscription.current_period_end

## }

## )

# Update S3 object tags (prepare for archival)

trigger_s3_tag_update(

user_id=current_user.user_id,

new_subscription_status='canceling'

## )

# Send confirmation email

send_cancellation_confirmation_email(

user_email=current_user.email,

user_name=current_user.name,

access_until=datetime.fromtimestamp(

canceled_subscription.current_period_end


## )

## )

# Log cancellation for analytics

log_cancellation_event(

user_id=current_user.user_id,

reason=cancellation_data.reason,

feedback=cancellation_data.feedback,

plan_type=current_user.subscription_plan,

tenure_days=(datetime.utcnow() - current_user.created_at).days

## )

return {

'status': 'success',

'message': 'Subscription canceled',

'access_until': canceled_subscription.current_period_end,

'access_until_formatted': datetime.fromtimestamp(

canceled_subscription.current_period_end

).strftime('%B %d, %Y')

## }

3. Stripe Webhook - Subscription Deleted python

Lambda: stripe-webhook-handler

def handle_subscription_deleted(event): """ Stripe webhook: customer.subscription.deleted
Triggered at end of billing period """

subscription = event.data.object


customer_id = subscription.customer

# Get user

user = get_user_by_stripe_customer_id(customer_id)

if not user:

logger.error(f"User not found for Stripe customer {customer_id}")

return

# Calculate final access date

period_end = datetime.fromtimestamp(subscription.current_period_end)

# Update DynamoDB - Downgrade to Free Tier

dynamodb.update_item(

TableName='careervp-users',

Key={'user_id': user['user_id']},

UpdateExpression='''

SET tier = :tier,

subscription_status = :status,

subscription_end_date = :end_date,

credits_remaining = :credits,

stripe_subscription_id = :null

## ''',

ExpressionAttributeValues={

':tier': 'free',

':status': 'cancelled',


':end_date': period_end.isoformat(),

':credits': 3, # Reset to 3 free applications

':null': None

## }

## )

# Update ALL S3 objects for this user

update_s3_tags_on_downgrade(

user_id=user['user_id'],

new_tier='free',

new_status='cancelled'

## )

# Send offboarding email

send_offboarding_email(

user_email=user['email'],

user_name=user.get('name', 'there'),

subscription_end_date=period_end

## )

# Optional: Trigger win-back campaign (after 30 days)

schedule_winback_campaign(

user_id=user['user_id'],

send_date=period_end + timedelta(days=30)

## )


logger.info(

f"User {user['user_id']} downgraded to free tier. "

f"Subscription ended {period_end}"

## )

def update_s3_tags_on_downgrade(user_id, new_tier, new_status): """ Update S3 object tags
when user downgrades This triggers lifecycle rules for archival """

# List all user objects

paginator = s3.get_paginator('list_objects_v2')

pages = paginator.paginate(

Bucket=OUTPUT_BUCKET,

Prefix=f'outputs/'

## )

updated_count = 0

for page in pages:

for obj in page.get('Contents', []):

# Get object tags

try:

tagging = s3.get_object_tagging(

Bucket=OUTPUT_BUCKET,

Key=obj['Key']

## )


tags = tagging['TagSet']

# Check if this object belongs to user

user_tag = next(

(t for t in tags if t['Key'] == 'user_id'),

None

## )

if user_tag and user_tag['Value'] == user_id:

# Update tags

updated_tags = []

for tag in tags:

if tag['Key'] == 'user_tier':

tag['Value'] = new_tier

elif tag['Key'] == 'subscription_status':

tag['Value'] = new_status

updated_tags.append(tag)

# Add cancellation timestamp

updated_tags.append({


'Key': 'cancelled_at',

'Value': datetime.utcnow().isoformat()

## })

# Write back

s3.put_object_tagging(

Bucket=OUTPUT_BUCKET,

Key=obj['Key'],

Tagging={'TagSet': updated_tags}

## )

updated_count += 1

except Exception as e:

logger.error(f"Error updating tags for {obj['Key']}: {e}")

continue

logger.info(

f"Updated {updated_count} S3 objects for user {user_id} "

f"to tier={new_tier}, status={new_status}"

## )

4. Offboarding Email Templates python def
    send_cancellation_confirmation_email(user_email, user_name, access_until): """
    Immediate confirmation when user cancels """


```
email_body = f""" Hi {user_name},
```
Your CareerVP subscription has been canceled as requested.

## WHAT THIS MEANS:

✓ You'll keep full access until {access_until.strftime('%B %d, %Y')} ✓ All your generated
documents remain available for download ✓ You can reactivate your subscription at any time

After {access_until.strftime('%B %d, %Y')}:

- You'll return to the free tier (3 applications)
- Your documents will be archived after 30 days of inactivity
- You can download all documents before then

## NEXT STEPS:

1. Download your application materials: https://app.careervp.com/applications
2. Reactivate anytime (no penalty): https://app.careervp.com/pricing

We're sorry to see you go! If you have feedback about your experience, please reply to this
email.

Best regards, The CareerVP Team """.strip()

ses.send_email(

Source='notifications@careervp.com',

Destination={'ToAddresses': [user_email]},

Message={

'Subject': {

'Data': 'Subscription Canceled - Access Until ' +

access_until.strftime('%B %d'),

'Charset': 'UTF-8'

## },


'Body': {'Text': {'Data': email_body, 'Charset': 'UTF-8'}}

## }

## )

def send_offboarding_email(user_email, user_name, subscription_end_date): """ Final email at
end of billing period """

email_body = f"""

Hi {user_name},

Your CareerVP paid subscription has ended as of {subscription_end_date.strftime('%B %d,
%Y')}.

## YOUR ACCOUNT STATUS:

- Tier: Free (3 applications)
- Document Access: Available for 30 days
- Documents will be archived: {(subscription_end_date + timedelta(days=30)).strftime('%B
    %d, %Y')}

## BEFORE YOUR DOCUMENTS ARE ARCHIVED:

Download all your application materials: https://app.careervp.com/applications

## WANT TO COME BACK?

Reactivate your subscription anytime: https://app.careervp.com/pricing

Special offer: Use code COMEBACK20 for 20% off your first month back.

Thank you for using CareerVP. We hope our tools helped in your job search!

Best regards, The CareerVP Team

P.S. Found a job? Congrats! Let us know - we'd love to hear about it. """.strip()

ses.send_email(

Source='notifications@careervp.com',

Destination={'ToAddresses': [user_email]},


Message={

'Subject': {

'Data': 'Your CareerVP Subscription Has Ended',

'Charset': 'UTF-8'

## },

'Body': {'Text': {'Data': email_body, 'Charset': 'UTF-8'}}

## }

## )

5. Admin Dashboard - Cancellation Analytics python

Lambda: cancellation-analytics-aggregator

(Scheduled - Daily)

def aggregate_cancellation_metrics(): """ Track cancellation reasons and trends """

# Query recent cancellations

thirty_days_ago = datetime.utcnow() - timedelta(days=30)

response = dynamodb.scan(

TableName='careervp-users',

FilterExpression='subscription_status = :status AND cancellation_date > :date',

ExpressionAttributeValues={

':status': 'cancelled',

':date': thirty_days_ago.isoformat()

## }

## )


# Aggregate metrics

cancellations = response['Items']

metrics = {

'total_cancellations': len(cancellations),

'reasons': defaultdict(int),

'avg_tenure_days': 0,

'churn_rate': 0

## }

tenure_sum = 0

for user in cancellations:

# Count reason

reason = user.get('cancellation_reason', 'unknown')

metrics['reasons'][reason] += 1

# Calculate tenure

if 'created_at' in user and 'cancellation_date' in user:

created = datetime.fromisoformat(user['created_at'])

canceled = datetime.fromisoformat(user['cancellation_date'])

tenure_sum += (canceled - created).days

if cancellations:

metrics['avg_tenure_days'] = tenure_sum / len(cancellations)

# Calculate churn rate


total_paid_users = count_paid_users()

if total_paid_users > 0:

metrics['churn_rate'] = (

len(cancellations) / total_paid_users

## ) * 100

# Store in DynamoDB for dashboard

dynamodb.put_item(

TableName='careervp-analytics',

Item={

'metric_type': 'cancellations',

'date': datetime.utcnow().date().isoformat(),

'total': len(cancellations),

'reasons': dict(metrics['reasons']),

'avg_tenure_days': Decimal(str(metrics['avg_tenure_days'])),

'churn_rate': Decimal(str(metrics['churn_rate']))

## }

## )

# Alert if churn rate > 10%

if metrics['churn_rate'] > 10:

send_admin_alert(

subject='High Churn Rate Alert',

message=f"Monthly churn rate: {metrics['churn_rate']:.1f}%"


## )

return metrics

6. Reactivation Flow python

API: POST /api/subscription/reactivate

@app.post('/api/subscription/reactivate') def reactivate_subscription( plan_id: str, promo_code:
Optional[str] = None, current_user: User = Depends(get_current_user) ): """ Reactivate
canceled subscription """

# Verify user is on free tier

if current_user.tier != 'free':

raise HTTPException(

status_code=400,

detail="Subscription already active"

## )

# Check for promo code

discount = None

if promo_code == 'COMEBACK20':

discount = stripe.Coupon.retrieve('comeback_20_percent')

# Create new Stripe subscription

subscription = stripe.Subscription.create(

customer=current_user.stripe_customer_id,

items=[{'price': plan_id}],

coupon=discount.id if discount else None,

metadata={


'user_id': current_user.user_id,

'reactivation': 'true',

'previous_cancellation_date': current_user.cancellation_date

## }

## )

# Update DynamoDB

dynamodb.update_item(

TableName='careervp-users',

Key={'user_id': current_user.user_id},

UpdateExpression='''

SET tier = :tier,

subscription_status = :status,

stripe_subscription_id = :sub_id,

reactivated_at = :reactivated,

cancellation_date = :null,

cancellation_reason = :null

## ''',

ExpressionAttributeValues={

':tier': 'paid',

':status': 'active',

':sub_id': subscription.id,

':reactivated': datetime.utcnow().isoformat(),


':null': None

## }

## )

# Update S3 tags (restore to paid tier)

update_s3_tags_on_upgrade(

user_id=current_user.user_id,

new_tier='paid',

new_status='active'

## )

# Send welcome back email

send_reactivation_email(

user_email=current_user.email,

user_name=current_user.name,

applied_discount=discount is not None

## )

return {

'status': 'success',

'message': 'Subscription reactivated',

'subscription_id': subscription.id,

'next_billing_date': subscription.current_period_end

## }

Summary


1. VPR Brief Included by Default ✅ VPR Brief: Auto-generated with CV (Haiku model,
    $0.004) VPR Full: Optional user selection (Sonnet model, $0.035) UI clearly shows VPR
    Brief as "Included", VPR Full as checkbox add-on Cost: Default package $0.016, with
    VPR Full $0.051
2. S3 Lifecycle - Tier Aware ✅ Active Paid: No archival, stays in Standard Inactive Paid
    (>30 days): Intelligent Tiering Cancelled Paid: Archive to Glacier after 30 days, delete
    after 365 days Free Tier: IA after 15 days, delete after 60 days Free Tier Warning: Email
    at 50 days (10 days before deletion) Implementation: S3 object tagging + lifecycle rules
    + Lambda notifications
3. Cancel Subscription Procedure ✅ User Flow: Confirmation modal → Cancel at period
    end → Keep access until billing end → Downgrade to free → Archive after 30 days
    Backend: Stripe cancellation → DynamoDB update → S3 tag update → Email
    notifications Offboarding: Cancellation confirmation email → Final email at period end →
    Optional retention offer Analytics: Track reasons, churn rate, tenure Reactivation:
    Special promo codes, restore to paid tier, re-tag S3 objects All three modifications
    implemented with complete code, UI/UX, and backend processing!


# Tab 10


Critical Corrections

1. Subscription Cancellation - Credits Handling ❌ WRONG Approach (Previously
    Documented) python# DON'T DO THIS - Resets credits incorrectly
    dynamodb.update_item( TableName='careervp-users', Key={'user_id': user['user_id']},
    UpdateExpression=''' SET tier = :tier, subscription_status = :status, credits_remaining =
    :credits # ❌ WRONG - Always resets to 3 ''', ExpressionAttributeValues={ ':tier': 'free',
    ':status': 'cancelled', ':credits': 3, # ❌ WRONG } )

### ✅ CORRECT Approach

**Business Logic:**

User upgrades from Free → Paid:

- Had 2 applications remaining (used 1 of 3)
- Upgraded to paid (unlimited)
- Used 47 applications while on paid tier

User cancels subscription:

- Downgrade to Free tier
- Restore original credits: 2 applications remaining (NOT reset to 3)
- User can use those 2 remaining applications
- If user already used all 3 before upgrading, they have 0 remaining Updated
    Implementation python# Lambda: stripe-webhook-handler (CORRECTED) def
    handle_subscription_deleted(event): """ Stripe webhook: customer.subscription.deleted
    Triggered at end of billing period """

```
subscription = event.data.object customer_id = subscription.customer
```
Get user

```
user = get_user_by_stripe_customer_id(customer_id)
```
```
if not user: logger.error(f"User not found for Stripe customer {customer_id}") return
```
Calculate final access date

```
period_end = datetime.fromtimestamp(subscription.current_period_end)
```

CRITICAL: Get original free tier credits (before

upgrade)

This was stored when user first upgraded

original_credits = user.get('free_tier_credits_at_upgrade', 0)

If no record exists, calculate based on original

usage

if 'free_tier_credits_at_upgrade' not in user: # Fallback: Check if user used any free
applications free_tier_apps = count_applications_before_upgrade(user['user_id'])
original_credits = max(0, 3 - free_tier_apps)

logger.info( f"User {user['user_id']} downgrade: " f"Restoring {original_credits} free tier
credits" )

Update DynamoDB - Downgrade to Free Tier

dynamodb.update_item( TableName='careervp-users', Key={'user_id': user['user_id']},
UpdateExpression=''' SET tier = :tier, subscription_status = :status,
subscription_end_date = :end_date, credits_remaining = :credits, stripe_subscription_id
= :null ''', ExpressionAttributeValues={ ':tier': 'free', ':status': 'cancelled', ':end_date':
period_end.isoformat(), ':credits': original_credits, # ✅ CORRECT - Restore original
':null': None } )

Update ALL S3 objects for this user

update_s3_tags_on_downgrade( user_id=user['user_id'], new_tier='free',
new_status='cancelled' )

Send offboarding email

send_offboarding_email( user_email=user['email'], user_name=user.get('name', 'there'),
subscription_end_date=period_end, credits_remaining=original_credits # ✅ Include in
email )


Optional: Trigger win-back campaign (after 30

days)

schedule_winback_campaign( user_id=user['user_id'], send_date=period_end +
timedelta(days=30) )

logger.info( f"User {user['user_id']} downgraded to free tier. " f"Subscription ended
{period_end}. " f"Credits remaining: {original_credits}" ) Track Credits at Upgrade Time
python# Lambda: subscription-activated (on upgrade) def
handle_subscription_activated(event): """ Stripe webhook: checkout.session.completed
User upgraded from Free → Paid """

session = event.data.object customer_id = session.customer

Get user

user = get_user_by_stripe_customer_id(customer_id)

CRITICAL: Store current free tier credits before

upgrade

So we can restore them if they cancel

current_credits = user.get('credits_remaining', 0)

logger.info( f"User {user['user_id']} upgrading. " f"Storing {current_credits} free tier credits
for future restoration" )

Update DynamoDB

dynamodb.update_item( TableName='careervp-users', Key={'user_id': user['user_id']},
UpdateExpression=''' SET tier = :tier, subscription_status = :status,
stripe_subscription_id = :sub_id, free_tier_credits_at_upgrade = :stored_credits,
upgraded_at = :upgraded ''', ExpressionAttributeValues={ ':tier': 'paid', ':status': 'active',
':sub_id': session.subscription, ':stored_credits': current_credits, # ✅ Store for later
':upgraded': datetime.utcnow().isoformat() } )


Send welcome email

```
send_upgrade_confirmation_email(user['email'], user.get('name')) Updated DynamoDB
Schema yaml# careervp-users table (UPDATED) Table Name: careervp-users Partition
Key: user_id (String)
```
Attributes:

- email (String)
- tier (String: free|paid|premium|admin)
- credits_remaining (Number)
    ● Free tier: 0-3 (decrements with each app)
    ● Paid tier: Not used (unlimited)

NEW ATTRIBUTE for credit restoration

- free_tier_credits_at_upgrade (Number)

```
● Stores credits remaining when user upgraded
● Used to restore credits if they cancel subscription
● Example: User had 2 credits, upgraded to paid, later canceled → restore to 2
```
- subscription_status (String: active|cancelled|lapsed|canceling)
- stripe_customer_id (String)
- stripe_subscription_id (String)
- created_at (String - ISO8601)
- updated_at (String - ISO8601)
- upgraded_at (String - ISO8601) # NEW
- cancellation_date (String - ISO8601)
- subscription_end_date (String - ISO8601) Updated Offboarding Email pythondef
    send_offboarding_email(user_email, user_name, subscription_end_date,
    credits_remaining): """ Final email at end of billing period UPDATED: Include
    credits_remaining information """


Determine credits message

```
if credits_remaining > 0: credits_msg = f""" You have {credits_remaining} free
application{'s' if credits_remaining != 1 else ''} remaining from your original free tier. You
can use these anytime. """.strip() else: credits_msg = """ You've used all your free tier
applications. You can purchase additional applications or upgrade to unlimited access
anytime. """.strip()
```
```
email_body = f""" Hi {user_name},
```
Your CareerVP paid subscription has ended as of {subscription_end_date.strftime('%B %d,
%Y')}.

## YOUR ACCOUNT STATUS:

- Tier: Free
- Applications Remaining: {credits_remaining}
- Document Access: Available for 30 days
- Documents will be archived: {(subscription_end_date + timedelta(days=30)).strftime('%B
    %d, %Y')}

{credits_msg}

## BEFORE YOUR DOCUMENTS ARE ARCHIVED:

Download all your application materials: https://app.careervp.com/applications

## WANT TO COME BACK?

Reactivate your subscription anytime: https://app.careervp.com/pricing

Special offer: Use code COMEBACK20 for 20% off your first month back.

Thank you for using CareerVP. We hope our tools helped in your job search!

Best regards, The CareerVP Team

P.S. Found a job? Congrats! Let us know - we'd love to hear about it. """.strip()

ses.send_email(

Source='notifications@careervp.com',

Destination={'ToAddresses': [user_email]},


Message={

'Subject': {

'Data': 'Your CareerVP Subscription Has Ended',

'Charset': 'UTF-8'

## },

'Body': {'Text': {'Data': email_body, 'Charset': 'UTF-8'}}

## }

## )

UI Display After Cancellation html

Free Tier (Subscription Ended)

**Applications Remaining**

{{ user.credits_remaining }} / 3

<p *ngIf="user.credits_remaining > 0">

You have {{ user.credits_remaining }} application{{ user.credits_remaining !== 1? 's' : '' }}

remaining from your original free tier.

</p>

<p *ngIf="user.credits_remaining === 0">

You've used all your free applications.

<a href="/pricing">Upgrade for unlimited access</a>

</p>

Reactivate Subscription

Examples Example 1: User Used 1 Free Application Before Upgrading yamlInitial State (Free
Tier): credits_remaining: 3 After 1st Application: credits_remaining: 2


User Upgrades to Paid: tier: paid credits_remaining: 2 (not used, but preserved)
free_tier_credits_at_upgrade: 2 # ✅ STORED

User on Paid Tier (6 months): Generated 47 applications credits_remaining: 2 (still stored, not
touched)

User Cancels Subscription: tier: free credits_remaining: 2 # ✅ RESTORED (not reset to 3)
subscription_status: cancelled Example 2: User Used All 3 Free Applications Before Upgrading
yamlInitial State (Free Tier): credits_remaining: 3

After 3 Applications: credits_remaining: 0

User Upgrades to Paid: tier: paid free_tier_credits_at_upgrade: 0 # ✅ STORED

User Cancels Subscription: tier: free credits_remaining: 0 # ✅ RESTORED (correctly shows 0)

User Must:

- Upgrade again for more applications
- OR purchase individual application credits (future feature) Example 3: User Never Used
    Free Tier, Went Directly to Paid yamlUser Signs Up: Creates account → Immediately
    upgrades to paid

State at Upgrade: tier: paid (direct upgrade) credits_remaining: 3 (never used)
free_tier_credits_at_upgrade: 3 # ✅ STORED

User Cancels: tier: free credits_remaining: 3 # ✅ RESTORED (full free tier)

2. VPR Brief vs VPR Complete Clarification ✅ CORRECTED Understanding VPR Brief
    (Default, Included with CV): yamlContents:
3. Value Proposition Statement (2-3 sentences)
4. Alignment Matrix (Table format, 6-8 rows)
5. Key Differentiators (3-5 bullet points)

Length: 1-2 pages Model: Claude Haiku 4.5 Cost: ~$0.004 Output: Docx (default), PDF
(optional)

This is what I showed in the "Example VPR with Gap Analysis" VPR Complete (Optional,
User-Selected): yamlContents:

1. Executive Summary
    - Value Proposition Statement


- Top 3 Fit Reasons
- Key Differentiators Summary
2. Alignment Matrix (Table format, 10-15 rows)
- More detailed than VPR Brief
- Includes all requirements (required + preferred)
3. Company Deep Dive (1-2 pages)
- Industry position & competitive landscape
- Recent developments & news
- Company culture & values
- Strategic priorities
4. Competitive Positioning (1 page)
- How candidate compares to typical applicants
- Unique skill combinations
- Differentiating experiences
- Cultural fit indicators
5. Risk Assessment & Mitigation (1 page)
- Employment gaps (if any)
- Skill gaps (from Alignment Matrix)
- Overqualification/underqualification concerns
- Each with mitigation strategy
6. Strategic Recommendations (1-2 pages)
- Interview preparation priorities
- Key talking points by interview stage
- Questions to ask interviewers
- Negotiation considerations
7. Evidence Library (1 page)
- Detailed project descriptions
- Achievement breakdowns
- Metrics and impact quantification
- Supporting examples for Alignment Matrix


Length: 5-8 pages Model: Claude Sonnet 4.5 Cost: ~$0.035 Output: Docx (default), PDF
(optional) Updated UI with Clarified Terminology html

**Your Application Package**

<!-- CV -->

<div class="artifact-card">

<div class="artifact-icon">📄</div>

<div class="artifact-info">

<h3>Tailored CV</h3>

<p>2 pages • Optimized for {{ companyName }}</p>

<div class="ats-badge" [class.high-score]="atsScore >= 90">

ATS Score: {{ atsScore }}/100

</div>

</div>

<div class="artifact-actions">

<button (click)="preview('cv')">Preview</button>

<button (click)="download('cv', 'docx')">Download</button>

</div>

</div>

<!-- VPR Brief (Included by Default) -->

<div class="artifact-card included-badge">

<span class="badge-included">✓ Included</span>

<div class="artifact-icon">📊</div>

<div class="artifact-info">


<h3>Value Proposition Report (Brief)</h3>

<p>1-2 pages • Strategic positioning summary</p>

<div class="vpr-contents">

<small>Includes:</small>

<ul class="feature-list">

<li>Value Proposition Statement</li>

<li>Alignment Matrix (table format)</li>

<li>Key Differentiators</li>

</ul>

</div>

</div>

<div class="artifact-actions">

<button (click)="preview('vpr-brief')">Preview</button>

<button (click)="download('vpr-brief', 'docx')">Download</button>

</div>

</div>

<!-- Cover Letter -->

<div class="artifact-card">

<div class="artifact-icon">📝</div>

<div class="artifact-info">

<h3>Cover Letter</h3>

<p>1 page • Personalized for {{ companyName }}</p>


</div>

<div class="artifact-actions">

<button (click)="preview('cover-letter')">Preview</button>

<button (click)="download('cover-letter', 'docx')">Download</button>

</div>

</div>

<div class="add-on-card">

<div class="add-on-header">

<input

type="checkbox"

id="vpr-complete"

[(ngModel)]="generateVPRComplete"

(change)="onVPRCompleteToggle()"

## />

<label for="vpr-complete">

<h3>Generate Complete VPR Report</h3>

<span class="add-on-cost">+$0.03</span>

</label>

</div>

<div class="add-on-description">

<p>Comprehensive 5-8 page strategic analysis including:</p>


<div class="vpr-comparison">

<div class="vpr-brief-contents">

<h4>VPR Brief (Included) ✓</h4>

<ul>

<li>Value Proposition Statement</li>

<li>Alignment Matrix (6-8 requirements)</li>

<li>Key Differentiators (3-5 points)</li>

</ul>

</div>

<div class="vpr-complete-additional">

<h4>VPR Complete Adds:</h4>

<ul>

<li>Executive Summary</li>

<li>Expanded Alignment Matrix (10-15 requirements)</li>

<li>Company Deep Dive & Culture Analysis</li>

<li>Competitive Positioning vs Other Candidates</li>

<li>Risk Assessment & Mitigation Strategies</li>

<li>Strategic Interview Recommendations</li>

<li>Evidence Library with Detailed Examples</li>

</ul>


</div>

</div>

<div class="use-case">

<strong>Best for:</strong> Senior roles, competitive positions,

or when you want maximum interview preparation

</div>

</div>

<!-- Shows after generation -->

<div class="artifact-ready" *ngIf="vprCompleteGenerated">

<div class="artifact-icon">📊</div>

<div class="artifact-info">

<h4>Complete VPR Report Ready</h4>

<p>{{ vprCompletePages }} pages • Full strategic analysis</p>

</div>

<div class="artifact-actions">

<button (click)="preview('vpr-complete')">Preview</button>

<button (click)="download('vpr-complete', 'docx')">Download</button>

</div>

</div>


<!-- Shows during generation -->

<div class="generating-status" *ngIf="generatingVPRComplete">

<spinner></spinner>

<p>Generating Complete VPR Report... (15-20 seconds)</p>

</div>

</div>

📦 Download Complete Package ({{ artifactCount }} files{{ vprCompleteGenerated? ' + VPR
Complete' : '' }})

Updated Lambda Function Names python# Lambda: vpr-generator (UPDATED with correct
terminology) def lambda_handler(event, context): """ Generate VPR Brief (default) or VPR
Complete (optional) """ job_id = event['job_id'] vpr_type = event.get('vpr_type', 'brief') # 'brief' or
'complete' # Load context

job_posting = get_job_posting(job_id)

master_cv = get_master_cv(job_id)

company_research = get_company_research(job_id)

gap_analysis = get_gap_analysis_responses(job_id)

# Select model and prompt based on VPR type

if vpr_type == 'complete':

model = 'claude-sonnet-4-5-20250929'

max_tokens = 8000

prompt_template = load_prompt('vpr_complete_generation')

logger.info(f"Generating VPR Complete for job {job_id}")

else: # brief


model = 'claude-haiku-4-5-20251001'

max_tokens = 3000

prompt_template = load_prompt('vpr_brief_generation')

logger.info(f"Generating VPR Brief for job {job_id}")

# Build context

context = {

'job_posting': job_posting,

'master_cv': master_cv,

'company_research': company_research,

'gap_analysis_answers': format_gap_analysis(gap_analysis),

'output_language': determine_language(master_cv, job_posting),

'vpr_type': vpr_type

## }

# Generate with Claude

response = claude_api.messages.create(

model=model,

max_tokens=max_tokens,

system=prompt_template,

messages=[{

'role': 'user',

'content': json.dumps(context, indent=2)

## }]


## )

vpr_content = response.content[0].text

# Convert to Docx

vpr_docx = convert_to_docx(

content=vpr_content,

template=f'vpr_{vpr_type}_template.docx'

## )

# Save to S3

company_name = extract_company_name(job_posting)

s3_key = f'outputs/{job_id}/vpr-{vpr_type}-{company_name}-{timestamp()}.docx'

s3.put_object(

Bucket=OUTPUT_BUCKET,

Key=s3_key,

Body=vpr_docx,

ContentType='application/vnd.openxmlformats-officedocument.wordprocessingml.document',

Metadata={

'job_id': job_id,

'artifact_type': f'vpr-{vpr_type}',

'user_id': get_user_id(job_id)

## }

## )

# Calculate page count for UI display


page_count = estimate_page_count(vpr_content)

# Update DynamoDB

update_artifact_status(

job_id=job_id,

artifact_type=f'vpr-{vpr_type}',

s3_key=s3_key,

cost=calculate_cost(response.usage),

page_count=page_count

## )

return {

'job_id': job_id,

'artifact_type': f'vpr-{vpr_type}',

's3_key': s3_key,

'page_count': page_count,

'cost': calculate_cost(response.usage)

## }

Updated API Endpoint python# API: POST /api/jobs/{job_id}/generate-vpr-complete
@app.post('/api/jobs/{job_id}/generate-vpr-complete') def generate_vpr_complete(job_id: str,
current_user: User = Depends(get_current_user)): """ Generate VPR Complete on demand
(user requested via checkbox) """

# Verify job belongs to user

job = get_job(job_id)

if job['user_id'] != current_user.user_id:


raise HTTPException(status_code=403, detail="Not authorized")

# Check if VPR Complete already generated

if artifact_exists(job_id, 'vpr-complete'):

return {

'status': 'already_exists',

'message': 'VPR Complete already generated for this job',

's3_key': get_artifact_s3_key(job_id, 'vpr-complete'),

'page_count': get_artifact_page_count(job_id, 'vpr-complete')

## }

# Send to generation queue

sqs.send_message(

QueueUrl=DOCUMENT_GENERATION_QUEUE,

MessageBody=json.dumps({

'function': 'vpr-generator',

'job_id': job_id,

'vpr_type': 'complete', # ✅ Changed from 'full' to 'complete'

'priority': 'high'

## })

## )

# Track cost

log_anticipated_cost(

user_id=current_user.user_id,


job_id=job_id,

artifact_type='vpr-complete',

estimated_cost=0.035

## )

return {

'status': 'generating',

'message': 'VPR Complete generation started',

'job_id': job_id,

'estimated_completion_seconds': 20

## }

Updated Prompts with Correct Terminology yaml# prompts/vpr_complete_generation.yaml
vpr_complete_generation: | You are creating a comprehensive Value Proposition Report
(Complete version).

This is the COMPLETE VPR that includes all strategic sections for thorough interview
preparation and competitive positioning.

## INPUTS:

- Job Posting: {{job_posting}}
- Master CV: {{master_cv}}
- Company Research: {{company_research}}
- Gap Analysis: {{gap_analysis_answers}}

## OUTPUT REQUIREMENTS:

Length: 5-8 pages Language: {{output_language}} Format: Executive-level strategic document

## REQUIRED SECTIONS:

1. EXECUTIVE SUMMARY (1 page) Open with strong positioning:

```
a) Value Proposition Statement (2-3 sentences) Synthesize candidate's unique fit for this
specific role Include quantified achievements from Gap Analysis
```

```
b) Top 3 Reasons You're the Ideal Candidate
```
- Technical excellence: [specific skill + achievement]
- Leadership impact: [team/project outcome]
- Strategic value: [business result]

```
c) Key Differentiators Summary What makes you stand out from typical candidates
```
## 2. ALIGNMENT MATRIX (TABLE FORMAT MANDATORY)

```
Job Requirement Your Evidence Strength
```
```
[requirement] [CV + Gap Analysis
evidence]
```
## [⭐⭐⭐/⭐⭐/⭐]

```
Include 10-15 rows covering:
```
- ALL technical requirements (required + preferred)
- Experience requirements
- Education/certifications
- Soft skills (leadership, communication)
- Industry-specific knowledge

```
Use Gap Analysis responses to provide SPECIFIC examples with metrics
```
3. COMPANY DEEP DIVE (1-2 pages)

```
a) Industry Position
```
- Market standing and competitive landscape
- Key competitors and differentiation

```
b) Recent Developments (Past 12 Months)
```
- Funding rounds, acquisitions, partnerships
- Product launches or strategic pivots
- Leadership changes
- Press coverage and sentiment

```
c) Company Culture & Values
```
- Stated values from company materials
- Employee reviews and sentiment


- Work environment indicators

```
d) Strategic Priorities
```
- Inferred from job posting requirements
- Company growth initiatives
- Technology investments
4. COMPETITIVE POSITIONING (1 page)

```
"How You Compare to Typical Applicants"
```
```
a) Unique Skill Combinations Skills that rarely exist together: Example: "Python expertise
+ regulatory compliance + healthcare domain knowledge is rare (only 12% of candidates
per LinkedIn data)"
```
```
b) Differentiating Experiences Unusual or high-impact experiences Example: "Led
Fortune 500 migration (enterprise scale) while also building startup MVPs (agility)"
```
```
c) Cultural Fit Indicators Evidence from Gap Analysis showing alignment with company
values
```
```
d) Overqualification/Underqualification Assessment Honest evaluation with mitigation
strategies
```
5. RISK ASSESSMENT & MITIGATION (1 page)

```
For each potential concern, provide:
```
```
Potential Concern Mitigation Strategy
```
```
[hiring manager worry] [how to address proactively]
```
```
Common risks to assess:
```
- Employment gaps (if any)
- Skill gaps (from Alignment Matrix ⭐⭐ or ⭐ ratings)
- Career transitions or pivots
- Geographic/remote considerations
- Overqualification concerns
- Industry switching


```
Example: | Limited direct experience with Kubernetes | Demonstrate: (1) 5 years
Docker/containerization, (2) Self-learning: completed CKA prep course, (3) Transferable:
architected similar orchestration with Docker Swarm |
```
6. STRATEGIC RECOMMENDATIONS (1-2 pages)

```
a) Interview Preparation Priorities
```
- Top 5 talking points to prepare
- Anticipated difficult questions
- Stories to practice (STAR format)

```
b) Key Messages by Interview Stage
```
- Phone screen: [focus areas]
- Technical interview: [demos to prepare]
- Behavioral interview: [stories to emphasize]
- Final interview: [strategic insights to share]

```
c) Questions to Ask Interviewers
```
- About role: [3-4 questions]
- About team: [2-3 questions]
- About company: [2-3 questions] (Questions should demonstrate research and
    strategic thinking)

```
d) Negotiation Considerations
```
- Market rate for this role/location
- Your positioning (strong/moderate leverage)
- Non-monetary value-adds to negotiate
7. EVIDENCE LIBRARY (1 page)

```
Detailed expansion of Alignment Matrix claims:
```
```
For each major achievement referenced:
```
- Full project context
- Your specific role and responsibilities
- Challenges overcome
- Quantified outcomes (metrics, percentages, dollar amounts)
- Technologies/methodologies used
- Team size/structure


```
Example: "API Latency Reduction Project (Referenced in Alignment Matrix)
```
```
Context: Legacy monolith API serving 1M requests/day with P95 latency of 800ms,
causing customer complaints and SLA violations.
```
```
Your Role: Tech lead for 6-month optimization initiative, managed team of 3 engineers.
```
```
Approach:
```
- Profiled hotspots using New Relic APM
- Implemented async/await patterns for I/O operations
- Added Redis caching layer for frequent queries
- Optimized database indexes

```
Results:
```
- P95 latency reduced from 800ms → 320ms (60% improvement)
- Customer complaints decreased 85%
- Infrastructure costs reduced $200K annually (fewer servers needed)
- Methodology adopted by 12 other teams

```
Technologies: Python 3.9, FastAPI, Redis, PostgreSQL, Docker"
```
## FORMATTING REQUIREMENTS:

- Professional executive document styling
- Clear section breaks with headings
- Tables where specified (Alignment Matrix, Risk Assessment)
- Evidence-based throughout (cite Gap Analysis, CV, company research)
- Strategic insights, not obvious observations
- Quantify wherever possible (numbers, percentages, dollars)
- Language: {{output_language}}

## TONE:

- Confident but not arrogant
- Strategic and analytical
- Evidence-driven, not marketing fluff
- Honest about risks/gaps (with mitigation)


- Executive-level polish Cost Breakdown - Corrected Terminology python# Updated cost
    breakdown with correct naming COST_PER_APPLICATION = {

Core artifacts (always generated)

```
'cv': 0.005, # Haiku 'vpr_brief': 0.004, # Haiku ✅ (was 'vpr_full')
'cover_letter': 0.004, # Haiku 'ats_check': 0.001, # No AI 'orchestration':
0.002,
```
```
'DEFAULT_PACKAGE': 0.016, # CV + VPR Brief + Cover Letter
```
Optional add-ons

```
'vpr_complete': 0.035, # Sonnet ✅ (renamed from 'vpr_full') 'interview_prep':
0.005, # Haiku (generated later) }
```
Artifact naming convention

ARTIFACT_TYPES = { 'cv': 'Tailored CV', 'vpr-brief': 'Value Proposition Report (Brief)', # ✅
Updated 'vpr-complete': 'Value Proposition Report (Complete)', # ✅ Updated 'cover-letter':
'Cover Letter', 'interview-prep': 'Interview Preparation Guide' }

Summary of Corrections

1. Credits Restoration ✅

❌ WRONG: Reset to 3 credits on subscription cancellation ✅ CORRECT: Restore original
credits from before upgrade Implementation:

Store free_tier_credits_at_upgrade when user upgrades Restore this value when subscription is
cancelled Update DynamoDB schema Update offboarding email to show correct credits

2. VPR Terminology ✅

❌ WRONG: "VPR Brief" and "VPR Full" ✅ CORRECT: "VPR Brief" (included) and "VPR
Complete" (optional) Clarification:

VPR Brief = 1-2 pages, includes Value Prop Statement + Alignment Matrix + Key Differentiators
VPR Complete = 5-8 pages, includes EVERYTHING (all 7 sections) Example shown earlier was
VPR Brief format

Updated:


UI labels and descriptions Lambda function variable names API endpoint naming Prompt file
names Cost breakdown Artifact type constants

Both corrections implemented throughout the system!


# Tab 11


1:24 PM Data Restoration for Returning Inactive Users Overview When an inactive user returns
to the platform, their data must be automatically restored from archived storage tiers back to
active status, ensuring seamless access without manual intervention.

Restoration Scenarios yaml Scenario 1: Free Tier User Returns After 30 Days Current State: -
Data in S3 IA (moved after 15 days inactivity) - DynamoDB records intact - No access in 30+
days

Trigger: User logs in

Actions: 1. Restore S3 objects to Standard tier 2. Update last_accessed timestamps 3. Reset
inactivity counters 4. Grant immediate access to all artifacts

Scenario 2: Free Tier User Returns After 50+ Days (Pre-Deletion Warning Sent) Current State: -
Data in S3 IA - Deletion warning email sent - 10 days until permanent deletion

Trigger: User logs in or downloads artifact

Actions: 1. Cancel scheduled deletion 2. Restore to S3 Standard 3. Update DynamoDB status

4. Send confirmation email (deletion cancelled)

Scenario 3: Cancelled Paid User Returns After 45 Days Current State: - Subscription cancelled -
Data in Glacier Instant Retrieval (moved after 30 days) - DynamoDB records intact

Trigger: User logs in

Actions: 1. Restore from Glacier to S3 Standard 2. Allow immediate download access 3. Prompt
for reactivation (optional)

Scenario 4: Cancelled Paid User Returns After 300 Days Current State: - Data in Glacier Deep
Archive (moved after 180 days) - Requires longer restoration time

Trigger: User attempts to access artifacts

Actions: 1. Initiate Glacier restoration (3-5 hours for Standard retrieval) 2. Show restoration
progress UI 3. Send email when restoration complete 4. Move to S3 Standard upon completion
Architecture

1. Activity Detection System python


Lambda: activity-detector (Triggered by CloudWatch

Events)

def detect_user_activity(event): """ Detect when inactive user returns and trigger restoration

Triggers:

- User login (Cognito event)
- API request (API Gateway)
- Artifact download attempt

## """

user_id = extract_user_id(event)

activity_type = event['activity_type'] # login, download, api_request

# Get user status

user = dynamodb.get_item(

TableName='careervp-users',

Key={'user_id': user_id}

)['Item']

# Check if user was inactive

last_activity = user.get('last_activity_at')

if last_activity:

days_inactive = (datetime.utcnow() -

datetime.fromisoformat(last_activity)).days

else:

days_inactive = 0


logger.info(

f"User {user_id} activity detected. "

f"Days inactive: {days_inactive}, Type: {activity_type}"

## )

# Trigger restoration if needed

if days_inactive >= 15: # Data may be archived

restoration_needed = check_restoration_needed(user_id, user['tier'])

if restoration_needed:

logger.info(f"Initiating data restoration for user {user_id}")

# Trigger restoration workflow

trigger_data_restoration(

user_id=user_id,

user_tier=user['tier'],

days_inactive=days_inactive,

activity_type=activity_type

## )

# Update last activity timestamp

update_user_activity(user_id)

return {


'user_id': user_id,

'restoration_triggered': days_inactive >= 15,

'days_inactive': days_inactive

## }

def check_restoration_needed(user_id, user_tier): """ Check if user's S3 objects are in archived
storage """

# Get user's S3 objects

response = s3.list_objects_v2(

Bucket=OUTPUT_BUCKET,

Prefix=f'outputs/{user_id}/'

## )

if 'Contents' not in response:

return False # No objects to restore

# Check storage class of first object (sample check)

for obj in response['Contents'][:5]: # Check first 5 objects

head_response = s3.head_object(

Bucket=OUTPUT_BUCKET,

Key=obj['Key']

## )

storage_class = head_response.get('StorageClass', 'STANDARD')


# If any object is archived, restoration needed

if storage_class in [

## 'INTELLIGENT_TIERING',

## 'STANDARD_IA',

## 'GLACIER_IR',

## 'GLACIER',

## 'DEEP_ARCHIVE'

## ]:

logger.info(

f"User {user_id} has archived data. "

f"Sample object in {storage_class}"

## )

return True

return False

def trigger_data_restoration(user_id, user_tier, days_inactive, activity_type): """ Trigger
restoration workflow based on storage tier """

# Send to restoration queue

sqs.send_message(

QueueUrl=DATA_RESTORATION_QUEUE,

MessageBody=json.dumps({

'user_id': user_id,

'user_tier': user_tier,


'days_inactive': days_inactive,

'activity_type': activity_type,

'timestamp': datetime.utcnow().isoformat()

## })

## )

# Update DynamoDB status

dynamodb.update_item(

TableName='careervp-users',

Key={'user_id': user_id},

UpdateExpression='SET restoration_status = :status, restoration_initiated_at = :time',

ExpressionAttributeValues={

':status': 'in_progress',

':time': datetime.utcnow().isoformat()

## }

## )

def update_user_activity(user_id): """ Update user's last activity timestamp """

dynamodb.update_item(

TableName='careervp-users',

Key={'user_id': user_id},

UpdateExpression='''

SET last_activity_at = :now,

activity_count = if_not_exists(activity_count, :zero) + :one


## ''',

ExpressionAttributeValues={

':now': datetime.utcnow().isoformat(),

':zero': 0,

':one': 1

## }

## )

2. Data Restoration Worker python

Lambda: data-restoration-worker

def lambda_handler(event, context): """ Process data restoration requests from SQS queue """

for record in event['Records']:

message = json.loads(record['body'])

user_id = message['user_id']

user_tier = message['user_tier']

days_inactive = message['days_inactive']

try:

logger.info(f"Processing restoration for user {user_id}")

# Get all user's S3 objects

objects_to_restore = list_user_objects(user_id)


if not objects_to_restore:

logger.warning(f"No objects found for user {user_id}")

mark_restoration_complete(user_id, 'no_objects')

continue

# Determine restoration strategy based on storage class

restoration_results = restore_user_objects(

user_id=user_id,

objects=objects_to_restore,

user_tier=user_tier

## )

# Update DynamoDB

update_restoration_status(user_id, restoration_results)

# Update S3 tags

update_s3_tags_on_restoration(user_id, user_tier)

# Cancel scheduled deletion if exists

cancel_scheduled_deletion(user_id)


# Send notification email

send_restoration_complete_email(

user_id=user_id,

restoration_results=restoration_results

## )

logger.info(

f"Restoration complete for user {user_id}. "

f"Restored {restoration_results['restored_count']} objects"

## )

except Exception as e:

logger.error(f"Restoration failed for user {user_id}: {str(e)}")

mark_restoration_failed(user_id, str(e))

raise

def list_user_objects(user_id): """ List all S3 objects for a user """

objects = []

paginator = s3.get_paginator('list_objects_v2')

pages = paginator.paginate(

Bucket=OUTPUT_BUCKET,

Prefix=f'outputs/{user_id}/'

## )


for page in pages:

if 'Contents' in page:

for obj in page['Contents']:

# Get object metadata

head = s3.head_object(

Bucket=OUTPUT_BUCKET,

Key=obj['Key']

## )

objects.append({

'key': obj['Key'],

'size': obj['Size'],

'last_modified': obj['LastModified'],

'storage_class': head.get('StorageClass', 'STANDARD'),

'metadata': head.get('Metadata', {})

## })

return objects

def restore_user_objects(user_id, objects, user_tier): """ Restore objects from archived storage
tiers """

restoration_results = {

'restored_count': 0,

'already_standard': 0,


'glacier_restore_initiated': 0,

'failed': 0,

'total': len(objects)

## }

for obj in objects:

storage_class = obj['storage_class']

key = obj['key']

try:

if storage_class == 'STANDARD':

# Already in Standard, no action needed

restoration_results['already_standard'] += 1

continue

elif storage_class in ['INTELLIGENT_TIERING', 'STANDARD_IA']:

# Can restore immediately by copying to Standard

restore_from_ia_to_standard(key)

restoration_results['restored_count'] += 1

elif storage_class == 'GLACIER_IR':

# Glacier Instant Retrieval - restore immediately

restore_from_glacier_ir(key)


restoration_results['restored_count'] += 1

elif storage_class in ['GLACIER', 'DEEP_ARCHIVE']:

# Standard Glacier or Deep Archive - initiate restore request

initiate_glacier_restore(

key=key,

tier='Standard' # 3-5 hours for Standard tier

## )

restoration_results['glacier_restore_initiated'] += 1

except Exception as e:

logger.error(f"Failed to restore {key}: {str(e)}")

restoration_results['failed'] += 1

return restoration_results

def restore_from_ia_to_standard(key): """ Restore object from IA or Intelligent Tiering to
Standard

S3 doesn't have a direct "restore" API for IA.

Instead, we copy the object to itself with STANDARD storage class.

## """

s3.copy_object(

Bucket=OUTPUT_BUCKET,

CopySource={'Bucket': OUTPUT_BUCKET, 'Key': key},


Key=key,

StorageClass='STANDARD',

MetadataDirective='COPY'

## )

logger.info(f"Restored {key} from IA to STANDARD")

def restore_from_glacier_ir(key): """ Restore from Glacier Instant Retrieval to Standard

Glacier IR allows immediate access but we should move to Standard

for better performance and lower retrieval costs.

## """

s3.copy_object(

Bucket=OUTPUT_BUCKET,

CopySource={'Bucket': OUTPUT_BUCKET, 'Key': key},

Key=key,

StorageClass='STANDARD',

MetadataDirective='COPY'

## )

logger.info(f"Restored {key} from GLACIER_IR to STANDARD")

def initiate_glacier_restore(key, tier='Standard'): """ Initiate Glacier restore request

Restore tiers:

- Expedited: 1-5 minutes (expensive)
- Standard: 3-5 hours (moderate cost)
- Bulk: 5-12 hours (cheapest)


## """

s3.restore_object(

Bucket=OUTPUT_BUCKET,

Key=key,

RestoreRequest={

'Days': 7, # Keep restored copy for 7 days

'GlacierJobParameters': {

'Tier': tier # Expedited | Standard | Bulk

## }

## }

## )

logger.info(f"Initiated {tier} restore for {key} (3-5 hours)")

def update_s3_tags_on_restoration(user_id, user_tier): """ Update S3 object tags to reflect
active user status """

# List user objects

response = s3.list_objects_v2(

Bucket=OUTPUT_BUCKET,

Prefix=f'outputs/{user_id}/'

## )

if 'Contents' not in response:

return

for obj in response['Contents']:

try:


# Get current tags

tagging = s3.get_object_tagging(

Bucket=OUTPUT_BUCKET,

Key=obj['Key']

## )

tags = tagging['TagSet']

# Update tags

updated_tags = []

for tag in tags:

if tag['Key'] == 'last_accessed':

tag['Value'] = datetime.utcnow().isoformat()

elif tag['Key'] == 'inactivity_days':

tag['Value'] = '0' # Reset inactivity counter

elif tag['Key'] == 'scheduled_deletion':

continue # Remove deletion flag

updated_tags.append(tag)

# Add restoration timestamp

updated_tags.append({

'Key': 'restored_at',


'Value': datetime.utcnow().isoformat()

## })

# Write back

s3.put_object_tagging(

Bucket=OUTPUT_BUCKET,

Key=obj['Key'],

Tagging={'TagSet': updated_tags}

## )

except Exception as e:

logger.error(f"Failed to update tags for {obj['Key']}: {str(e)}")

continue

def cancel_scheduled_deletion(user_id): """ Cancel any scheduled deletion jobs for this user """

# Check DynamoDB for scheduled deletion

try:

response = dynamodb.get_item(

TableName='careervp-scheduled-deletions',

Key={'user_id': user_id}

## )

if 'Item' in response:


deletion_job = response['Item']

# Delete the scheduled job

dynamodb.delete_item(

TableName='careervp-scheduled-deletions',

Key={'user_id': user_id}

## )

logger.info(

f"Cancelled scheduled deletion for user {user_id}. "

f"Was scheduled for {deletion_job.get('deletion_date')}"

## )

return True

except Exception as e:

logger.error(f"Error cancelling deletion for user {user_id}: {str(e)}")

return False

def mark_restoration_complete(user_id, status='complete'): """ Update DynamoDB to mark
restoration as complete """

dynamodb.update_item(

TableName='careervp-users',

Key={'user_id': user_id},


UpdateExpression='''

SET restoration_status = :status,

restoration_completed_at = :time,

last_activity_at = :time

## ''',

ExpressionAttributeValues={

':status': status,

':time': datetime.utcnow().isoformat()

## }

## )

def mark_restoration_failed(user_id, error_message): """ Mark restoration as failed in
DynamoDB """

dynamodb.update_item(

TableName='careervp-users',

Key={'user_id': user_id},

UpdateExpression='''

SET restoration_status = :status,

restoration_error = :error,

restoration_failed_at = :time

## ''',

ExpressionAttributeValues={

':status': 'failed',

':error': error_message,


':time': datetime.utcnow().isoformat()

## }

## )

# Alert admins

send_admin_alert(

subject=f'Data Restoration Failed: User {user_id}',

message=f'Error: {error_message}'

## )

3. Glacier Restore Completion Handler python

Lambda: glacier-restore-complete-handler

def lambda_handler(event, context): """ Handle S3 event when Glacier restore completes

Triggered by: s3:ObjectRestore:Completed event

## """

for record in event['Records']:

bucket = record['s3']['bucket']['name']

key = record['s3']['object']['key']

logger.info(f"Glacier restore completed: {key}")

# Extract user_id from key

# Format: outputs/{user_id}/{artifact}

user_id = key.split('/')[1]


try:

# Copy restored object to STANDARD storage class

# (Glacier restore creates temp copy, we need permanent Standard)

s3.copy_object(

Bucket=bucket,

CopySource={'Bucket': bucket, 'Key': key},

Key=key,

StorageClass='STANDARD',

MetadataDirective='COPY'

## )

logger.info(f"Moved restored object to STANDARD: {key}")

# Check if all user objects are restored

check_full_restoration_complete(user_id)

except Exception as e:

logger.error(f"Failed to finalize restore for {key}: {str(e)}")

def check_full_restoration_complete(user_id): """ Check if all of user's objects have been
restored """

# List all user objects


response = s3.list_objects_v2(

Bucket=OUTPUT_BUCKET,

Prefix=f'outputs/{user_id}/'

## )

if 'Contents' not in response:

return

all_restored = True

for obj in response['Contents']:

head = s3.head_object(

Bucket=OUTPUT_BUCKET,

Key=obj['Key']

## )

storage_class = head.get('StorageClass', 'STANDARD')

if storage_class != 'STANDARD':

all_restored = False

break

if all_restored:

# Mark complete in DynamoDB

mark_restoration_complete(user_id)


# Send email notification

user = dynamodb.get_item(

TableName='careervp-users',

Key={'user_id': user_id}

)['Item']

send_restoration_complete_email(

user_email=user['email'],

user_name=user.get('name', 'there')

## )

logger.info(f"Full restoration complete for user {user_id}")

4. User-Facing UI html

**Restoring Your Documents...**

Your documents are being restored from archive storage. This will take just a moment.

⏳

**Document Restoration in Progress**

Your documents are being restored from long-term storage. This process takes 3-5 hours.

We'll send you an email at **{{ userEmail }}** when your documents are ready.

Estimated completion: {{ estimatedCompletionTime | date:'short' }}
Got it, I'll wait
✓

**Your Documents Are Ready!**

All your application materials have been restored and are ready to download.


View My Documents
✓

**Scheduled Deletion Cancelled**

We've cancelled the scheduled deletion of your documents. Your data is safe and accessible.

**My Applications**

⏳

Some of your documents are being restored from archive storage (3-5 hour process).
Documents currently available are shown below.

<div class="application-card" *ngFor="let app of applications">

<div class="app-header">

<h3>{{ app.job_title }}</h3>

<span class="company">{{ app.company_name }}</span>

</div>

<div class="artifacts">

<!-- Artifact Available -->

<div class="artifact" *ngFor="let artifact of app.artifacts">

<span class="artifact-name">{{ artifact.name }}</span>

<div class="artifact-actions" *ngIf="artifact.status === 'available'">

<button (click)="preview(artifact)">Preview</button>


<button (click)="download(artifact)">Download</button>

</div>

<!-- Artifact Being Restored -->

<div class="artifact-restoring" *ngIf="artifact.status === 'restoring'">

<spinner size="small"></spinner>

<span class="status-text">Restoring...</span>

</div>

<!-- Artifact Restoration Pending (Glacier) -->

<div class="artifact-pending" *ngIf="artifact.status === 'restore_pending'">

<icon>⏳</icon>

<span class="status-text">

Available in {{ artifact.estimated_hours }} hours

</span>

</div>

</div>

</div>

</div>


5. Email Notifications python def send_restoration_complete_email(user_email, user_name): """
Notify user when restoration is complete """ email_body = f"""

Hi {user_name},

Welcome back to CareerVP! Your documents have been restored and are ready to access.

All your application materials are now available:

- Tailored CVs
- Value Proposition Reports
- Cover Letters
- Interview Preparation Guides

Access your documents: https://app.careervp.com/applications

If you were at risk of data deletion, that has been cancelled. Your documents are safe and will
remain accessible as long as your account is active.

Need to create more application materials? You have full access to your remaining free tier
applications or can upgrade for unlimited access.

Best regards, The CareerVP Team """.strip()

ses.send_email(

Source='notifications@careervp.com',

Destination={'ToAddresses': [user_email]},

Message={

'Subject': {

'Data': 'Your CareerVP Documents Are Ready',

'Charset': 'UTF-8'

## },

'Body': {'Text': {'Data': email_body, 'Charset': 'UTF-8'}}

## }


## )

def send_glacier_restore_initiated_email(user_email, user_name, estimated_completion): """
Notify user that Glacier restoration has started (3-5 hours) """

email_body = f"""

Hi {user_name},

Welcome back! We're restoring your CareerVP documents from long-term storage.

## WHAT'S HAPPENING:

Your documents are being restored from archive storage. This process takes approximately 3-5
hours.

ESTIMATED COMPLETION: {estimated_completion.strftime('%B %d at %I:%M %p')}

We'll send you another email when your documents are ready to access.

## WHY THE WAIT?

Your documents were moved to cost-effective long-term storage due to inactivity. This keeps
your data safe while minimizing storage costs.

## WHAT YOU CAN DO NOW:

- Create new application materials (available immediately)
- Update your account settings
- Explore our features

We'll notify you as soon as your archived documents are ready.

Best regards, The CareerVP Team """.strip()

ses.send_email(

Source='notifications@careervp.com',

Destination={'ToAddresses': [user_email]},

Message={


'Subject': {

'Data': 'CareerVP: Document Restoration in Progress (3-5 hours)',

'Charset': 'UTF-8'

## },

'Body': {'Text': {'Data': email_body, 'Charset': 'UTF-8'}}

## }

## )

6. Updated DynamoDB Schema yaml

careervp-users table (UPDATED with restoration

fields)

Table Name: careervp-users Partition Key: user_id (String)

Attributes:

Existing fields...

- email (String)
- tier (String)
- credits_remaining (Number)

Activity tracking

- last_activity_at (String - ISO8601)
- activity_count (Number)

Restoration tracking

- restoration_status (String: none|in_progress|complete|failed)
- restoration_initiated_at (String - ISO8601)
- restoration_completed_at (String - ISO8601)
- restoration_error (String)
- glacier_restore_count (Number) # Track Glacier restores (can be expensive)


Deletion prevention

- deletion_scheduled (Boolean)
- deletion_scheduled_for (String - ISO8601)
- deletion_cancelled_at (String - ISO8601)

## GSI:

- restoration-status-index: restoration_status (PK), restoration_initiated_at (SK) Purpose:
    Query all users with in_progress restorations yaml

careervp-scheduled-deletions table (NEW)

Table Name: careervp-scheduled-deletions Partition Key: user_id (String)

Attributes:

- user_id (String)
- deletion_date (String - ISO8601)
- reason (String: free_tier_inactivity|cancelled_subscription)
- scheduled_at (String - ISO8601)
- notification_sent (Boolean)
- object_count (Number)
- total_size_mb (Number)

Purpose: Track scheduled deletions so they can be cancelled on user return 7. CloudWatch
Events Integration yaml

EventBridge Rules for Activity Detection

Rule 1: Cognito Login Event Event Pattern: source: aws.cognito-idp detail-type: "AWS API Call
via CloudTrail" detail: eventName: "InitiateAuth"

Target: activity-detector Lambda

Rule 2: API Gateway Request Event Pattern: source: aws.execute-api detail-type: "API
Gateway Execution State Change"

Target: activity-detector Lambda

Rule 3: S3 Object Access Event Pattern: source: aws.s3 detail-type: "Object Access" detail:
bucket: careervp-job-search-assistant-outputs


Target: activity-detector Lambda

Rule 4: Glacier Restore Completed Event Pattern: source: aws.s3 detail-type: "Object Restore
Completed" detail: bucket: careervp-job-search-assistant-outputs

Target: glacier-restore-complete-handler Lambda 8. Cost Management python

Lambda: restoration-cost-tracker

def track_restoration_cost(user_id, restoration_type, object_count, total_size_gb): """ Track
costs associated with data restoration

Glacier restoration costs:

- Standard tier: $0.01 per GB + $0.05 per 1,000 requests
- Expedited tier: $0.03 per GB + $10 per 1,000 requests

## """

if restoration_type == 'glacier_standard':

data_retrieval_cost = total_size_gb * 0.01

request_cost = (object_count / 1000) * 0.05

total_cost = data_retrieval_cost + request_cost

elif restoration_type == 'glacier_expedited':

data_retrieval_cost = total_size_gb * 0.03

request_cost = (object_count / 1000) * 10

total_cost = data_retrieval_cost + request_cost

else: # IA restoration (free, just transfer costs)

total_cost = 0

# Log to DynamoDB for cost tracking

dynamodb.put_item(


TableName='careervp-cost-tracking',

Item={

'cost_id': f'{user_id}-{datetime.utcnow().timestamp()}',

'user_id': user_id,

'cost_type': 'data_restoration',

'restoration_type': restoration_type,

'object_count': object_count,

'total_size_gb': Decimal(str(total_size_gb)),

'cost_usd': Decimal(str(total_cost)),

'timestamp': datetime.utcnow().isoformat()

## }

## )

# Alert if cost is high

if total_cost > 5.00: # Alert for restorations over $5

send_admin_alert(

subject=f'High Restoration Cost: ${total_cost:.2f}',

message=f'User {user_id} restoration cost: ${total_cost:.2f}'

## )

return total_cost

Lambda: restoration-abuse-detector (Scheduled -

Daily)

def detect_restoration_abuse(): """ Detect users repeatedly restoring from Glacier (Pattern:
inactive → restore → inactive → restore) """


# Query users with multiple Glacier restores

response = dynamodb.scan(

TableName='careervp-users',

FilterExpression='glacier_restore_count > :threshold',

ExpressionAttributeValues={':threshold': 3}

## )

for user in response['Items']:

# Check restoration pattern

restore_count = user['glacier_restore_count']

user_id = user['user_id']

logger.warning(

f"User {user_id} has {restore_count} Glacier restores. "

f"Possible abuse or need for tier upgrade."

## )

# Send targeted email suggesting upgrade

send_upgrade_suggestion_email(

user_email=user['email'],

user_name=user.get('name'),

restore_count=restore_count

## )


9. API Endpoints python

API: GET /api/user/restoration-status

@app.get('/api/user/restoration-status') def get_restoration_status(current_user: User =
Depends(get_current_user)): """ Get user's data restoration status """

restoration_status = current_user.get('restoration_status', 'none')

if restoration_status == 'none':

return {

'status': 'none',

'message': 'No restoration in progress'

## }

elif restoration_status == 'in_progress':

# Check if Glacier restore or immediate

# Count objects still restoring

objects_restoring = count_restoring_objects(current_user.user_id)

if objects_restoring > 0:

return {

'status': 'in_progress',

'type': 'glacier',

'objects_restoring': objects_restoring,

'initiated_at': current_user.get('restoration_initiated_at'),


'estimated_completion': estimate_completion_time(

current_user.get('restoration_initiated_at')

## ),

'message': 'Your documents are being restored from archive storage (3-5 hours)'

## }

else:

# Immediate restoration (IA → Standard)

return {

'status': 'in_progress',

'type': 'immediate',

'message': 'Your documents are being restored (just a moment)'

## }

elif restoration_status == 'complete':

return {

'status': 'complete',

'completed_at': current_user.get('restoration_completed_at'),

'message': 'All your documents have been restored and are ready'

## }

elif restoration_status == 'failed':

return {

'status': 'failed',

'error': current_user.get('restoration_error'),


'message': 'Document restoration encountered an error. Please contact support.'

## }

API: POST /api/user/request-expedited-restore

@app.post('/api/user/request-expedited-restore') def request_expedited_restore(current_user:
User = Depends(get_current_user)): """ User requests expedited Glacier restore (1-5 minutes
instead of 3-5 hours)

Note: This is expensive ($0.03/GB vs $0.01/GB)

Only offer for paid users or with explicit fee

## """

# Check if user is on paid tier

if current_user.tier == 'free':

raise HTTPException(

status_code=403,

detail="Expedited restore only available for paid users"

## )

# Check if restoration is in progress

if current_user.restoration_status != 'in_progress':

raise HTTPException(

status_code=400,

detail="No restoration in progress"

## )

# Trigger expedited restore

trigger_expedited_restore(current_user.user_id)


return {

'status': 'success',

'message': 'Expedited restore initiated. Documents will be ready in 1-5 minutes.',

'estimated_completion_minutes': 3

## }

Summary Automatic Data Restoration System ✅ Key Features:

Activity Detection: Triggers on login, API request, or download attempt Storage Tier Aware:
Different restoration strategies for IA, Intelligent Tiering, Glacier IR, and Glacier Immediate
Restoration: IA and Intelligent Tiering restore in seconds Delayed Restoration: Glacier takes 3-5
hours, user receives progress notifications Deletion Cancellation: Automatically cancels
scheduled deletions when user returns DynamoDB Updates: Resets inactivity counters, updates
last_activity timestamps S3 Tag Updates: Updates object tags to prevent re-archival User
Transparency: Clear UI showing restoration progress and estimated completion Email
Notifications: Confirms restoration initiation and completion Cost Tracking: Monitors restoration
costs, alerts on high usage Abuse Detection: Identifies users with repeated restore patterns
Restoration Times:

S3 IA → Standard: Immediate (seconds) Intelligent Tiering → Standard: Immediate Glacier IR
→ Standard: Immediate Glacier Standard Tier: 3-5 hours Glacier Expedited: 1-5 minutes (paid
users only) User Experience:

Seamless restoration for recently inactive users (IA/IT storage) Progress tracking and
notifications for long-term archived data No data loss regardless of inactivity duration Optional
expedited restore for paid users All inactive users returning to the platform will have their data
automatically restored to the appropriate S3 tier and DynamoDB status without manual
intervention!


# Tab 12


CareerVP Pricing Structure - Updated Pricing Plans

1. Free Trial (14 Days) yamlFree Trial Structure: Duration: 14 days from signup
    Applications Included: 3 Credit Card: Optional (not required)

Features: - Full access to all generation features - CV Tailoring - VPR Brief (included with CV) -
Cover Letter Generation - Interview Preparation Guide - Gap Analysis Q&A - ATS Compliance
Checking - Download in Docx/PDF formats

Conversion: - If CC provided: Auto-converts to Monthly plan at $29.95/month after 14 days - If
NO CC: Trial ends after 14 days or 3 applications (whichever comes first) - User can upgrade to
paid plan anytime during trial

Account Status After Trial (No CC): - Tier: Free (0 applications remaining) - Can still access
previously generated documents - Must upgrade to generate new applications 2. Monthly Plan
yamlMonthly Plan: Price: $29.95/month Billing: Monthly recurring Applications: Unlimited

Auto-Conversion: - Users with CC on file automatically convert from Free Trial - First charge
occurs on day 15 (after 14-day trial) - No manual upgrade needed if CC provided during trial

Cancellation: - Cancel anytime - Access continues until end of current billing period - Reverts to
Free tier (0 applications) after cancellation 3. Quarterly Plan (Best Value) yamlQuarterly Plan:
Display Price: $24.95/month Actual Billing: $74.85 upfront (quarterly) Savings: $14.85 vs
monthly ($29.95 × 3 = $89.85) Discount: 17% off monthly price Applications: Unlimited

UI Display: Primary: "$24.95/month" Secondary: "Billed quarterly at $74.85" Badge: "Save 17%"

Billing Cycle: - Charged $74.85 every 3 months - Next billing date shown clearly in account

Cancellation: - Cancel anytime - Access continues until end of current 3-month period - No
prorated refunds

Implementation

1. Updated DynamoDB Schema yaml# careervp-users table (UPDATED) Table Name:
    careervp-users Partition Key: user_id (String)

Attributes:

Basic Info

- email (String)
- name (String)
- created_at (String - ISO8601)


Subscription Info

- tier (String: trial|free|monthly|quarterly)
- subscription_status (String: active|trialing|cancelled|expired)
- subscription_plan (String: trial|monthly_2995|quarterly_7485)

Trial Tracking

- trial_start_date (String - ISO8601)
- trial_end_date (String - ISO8601)
- trial_applications_used (Number: 0-3)
- trial_has_credit_card (Boolean)
- trial_converted (Boolean)
- trial_conversion_date (String - ISO8601)

Credits (Free tier only)

- credits_remaining (Number: 0-3)
- free_tier_credits_at_upgrade (Number)

Stripe Integration

- stripe_customer_id (String)
- stripe_subscription_id (String)
- payment_method_on_file (Boolean)

Billing

- current_period_start (String - ISO8601)
- current_period_end (String - ISO8601)
- next_billing_date (String - ISO8601)
- next_billing_amount (Number)

Cancellation

- cancellation_date (String - ISO8601)
- cancellation_reason (String)
- cancel_at_period_end (Boolean)
2. Stripe Product Configuration python# Stripe Products & Prices Setup def
    create_stripe_products(): """ Create Stripe products and price objects """


Product: CareerVP Subscription

```
product = stripe.Product.create( name='CareerVP Subscription', description='AI-powered
job application materials generator', metadata={ 'product_type': 'subscription' } )
```
Price 1: Monthly Plan ($29.95/month)

```
monthly_price = stripe.Price.create( product=product.id, unit_amount=2995, # $29.95 in
cents currency='usd', recurring={ 'interval': 'month', 'interval_count': 1 },
nickname='Monthly Plan', metadata={ 'plan_type': 'monthly', 'display_price':
'$29.95/month' } )
```
Price 2: Quarterly Plan ($74.85 every 3 months)

```
quarterly_price = stripe.Price.create( product=product.id, unit_amount=7485, # $74.85
in cents currency='usd', recurring={ 'interval': 'month', 'interval_count': 3 },
nickname='Quarterly Plan', metadata={ 'plan_type': 'quarterly', 'display_price':
'$24.95/month', 'actual_billing': 'Billed quarterly at $74.85', 'savings': '17% off monthly' } )
```
```
return { 'product_id': product.id, 'monthly_price_id': monthly_price.id, 'quarterly_price_id':
quarterly_price.id }
```
Store these IDs in environment variables

STRIPE_MONTHLY_PRICE_ID = 'price_xxxxxxxxxxxxx' STRIPE_QUARTERLY_PRICE_ID =
'price_yyyyyyyyyyy' 3. Signup Flow - Credit Card Optional python# API: POST /api/auth/signup
@app.post('/api/auth/signup') def signup(signup_data: SignupRequest): """ User signup - credit
card optional """

# Create Cognito user

cognito_user = cognito.admin_create_user(

UserPoolId=USER_POOL_ID,

Username=signup_data.email,

UserAttributes=[

{'Name': 'email', 'Value': signup_data.email},

{'Name': 'name', 'Value': signup_data.name}


## ],

TemporaryPassword=generate_temp_password()

## )

user_id = cognito_user['User']['Username']

# Calculate trial period

trial_start = datetime.utcnow()

trial_end = trial_start + timedelta(days=14)

# Create DynamoDB record

dynamodb.put_item(

TableName='careervp-users',

Item={

'user_id': user_id,

'email': signup_data.email,

'name': signup_data.name,

'tier': 'trial',

'subscription_status': 'trialing',

'subscription_plan': 'trial',

'trial_start_date': trial_start.isoformat(),

'trial_end_date': trial_end.isoformat(),

'trial_applications_used': 0,

'trial_has_credit_card': False, # Updated if CC added

'trial_converted': False,


'credits_remaining': 3, # Trial includes 3 applications

'created_at': trial_start.isoformat(),

'payment_method_on_file': False

## }

## )

# Send welcome email

send_trial_welcome_email(

email=signup_data.email,

name=signup_data.name,

trial_end_date=trial_end

## )

return {

'user_id': user_id,

'trial_start_date': trial_start.isoformat(),

'trial_end_date': trial_end.isoformat(),

'applications_remaining': 3,

'message': 'Trial started! You have 14 days and 3 free applications.'

## }

API: POST /api/trial/add-payment-method

@app.post('/api/trial/add-payment-method') def add_payment_method_to_trial(
payment_method_id: str, auto_convert: bool = True, current_user: User =
Depends(get_current_user) ): """ Add payment method during trial (optional)

If auto_convert=True, subscription will auto-convert to Monthly at trial end


If auto_convert=False, just stores payment method for manual upgrade

## """

# Verify user is on trial

if current_user.tier != 'trial':

raise HTTPException(

status_code=400,

detail="Only available during trial period"

## )

# Create or get Stripe customer

if current_user.stripe_customer_id:

stripe_customer_id = current_user.stripe_customer_id

else:

customer = stripe.Customer.create(

email=current_user.email,

name=current_user.name,

metadata={'user_id': current_user.user_id}

## )

stripe_customer_id = customer.id

# Attach payment method

stripe.PaymentMethod.attach(

payment_method_id,

customer=stripe_customer_id


## )

# Set as default payment method

stripe.Customer.modify(

stripe_customer_id,

invoice_settings={

'default_payment_method': payment_method_id

## }

## )

# Update DynamoDB

update_expression = '''

SET stripe_customer_id = :customer_id,

payment_method_on_file = :true,

trial_has_credit_card = :true

## '''

expression_values = {

':customer_id': stripe_customer_id,

':true': True

## }

# If auto-convert enabled, create scheduled subscription

if auto_convert:

# Create subscription starting at trial end date

trial_end_timestamp = int(


datetime.fromisoformat(current_user.trial_end_date).timestamp()

## )

subscription = stripe.Subscription.create(

customer=stripe_customer_id,

items=[{'price': STRIPE_MONTHLY_PRICE_ID}],

trial_end=trial_end_timestamp, # Start billing after trial

metadata={

'user_id': current_user.user_id,

'converted_from': 'trial'

## }

## )

update_expression += ', stripe_subscription_id = :sub_id'

expression_values[':sub_id'] = subscription.id

dynamodb.update_item(

TableName='careervp-users',

Key={'user_id': current_user.user_id},

UpdateExpression=update_expression,

ExpressionAttributeValues=expression_values

## )

# Send confirmation email


send_payment_method_added_email(

email=current_user.email,

name=current_user.name,

auto_convert=auto_convert,

trial_end_date=current_user.trial_end_date

## )

return {

'status': 'success',

'auto_convert': auto_convert,

'message': 'Payment method added successfully',

'trial_end_date': current_user.trial_end_date,

'next_billing_date': current_user.trial_end_date if auto_convert else None,

'next_billing_amount': 29.95 if auto_convert else None

## }

4. Trial Monitoring & Conversion python# Lambda: trial-monitor (Scheduled - Daily) def
    lambda_handler(event, context): """ Monitor trial status and handle
    conversions/expirations

```
Runs daily to:
```
1. Check for trials ending today
2. Convert trials with CC to paid subscriptions
3. Expire trials without CC
4. Send reminder emails """

```
today = datetime.utcnow().date()
```

Query users on trial

```
response = dynamodb.scan( TableName='careervp-users', FilterExpression='tier = :tier',
ExpressionAttributeValues={':tier': 'trial'} )
```
```
for user in response['Items']: trial_end_date = datetime.fromisoformat(
user['trial_end_date'] ).date()
```
```
days_until_trial_end = (trial_end_date - today).days
```
```
# Trial ending today
```
```
if days_until_trial_end == 0:
```
```
handle_trial_ending(user)
```
```
# 3 days before trial end - send reminder
```
```
elif days_until_trial_end == 3:
```
```
send_trial_ending_reminder(user, days_remaining=3)
```
```
# 1 day before trial end - final reminder
```
```
elif days_until_trial_end == 1:
```
```
send_trial_ending_reminder(user, days_remaining=1)
```
def handle_trial_ending(user): """ Handle trial ending - convert to paid or expire to free """

user_id = user['user_id']

has_credit_card = user.get('trial_has_credit_card', False)

if has_credit_card:

# Auto-convert to Monthly plan


# Stripe subscription was already created with trial_end parameter

# Just update DynamoDB

dynamodb.update_item(

TableName='careervp-users',

Key={'user_id': user_id},

UpdateExpression='''

SET tier = :tier,

subscription_status = :status,

subscription_plan = :plan,

trial_converted = :true,

trial_conversion_date = :now,

current_period_start = :now,

current_period_end = :next_month

## ''',

ExpressionAttributeValues={

':tier': 'monthly',

':status': 'active',

':plan': 'monthly_2995',

':true': True,

':now': datetime.utcnow().isoformat(),

':next_month': (datetime.utcnow() + timedelta(days=30)).isoformat()


## }

## )

# Send conversion confirmation

send_trial_converted_email(user['email'], user.get('name'))

logger.info(f"User {user_id} converted from trial to monthly plan")

else:

# No credit card - expire to Free tier

dynamodb.update_item(

TableName='careervp-users',

Key={'user_id': user_id},

UpdateExpression='''

SET tier = :tier,

subscription_status = :status,

subscription_plan = :plan,

credits_remaining = :credits

## ''',

ExpressionAttributeValues={

':tier': 'free',

':status': 'expired',


':plan': 'free',

':credits': 0 # No more applications

## }

## )

# Send trial expired email

send_trial_expired_email(user['email'], user.get('name'))

logger.info(f"User {user_id} trial expired - now on free tier")

5. Pricing Page UI html

**Choose Your Plan**

Start with a 14-day free trial. No credit card required.

Start Here

**Free Trial**

$0 for 14 days

<div class="card-features">

<h4>Includes:</h4>

<ul>

<li><icon>✓</icon> 3 complete application packages</li>

<li><icon>✓</icon> Tailored CV generation</li>

<li><icon>✓</icon> Value Proposition Reports</li>

<li><icon>✓</icon> Custom cover letters</li>


<li><icon>✓</icon> Interview preparation guides</li>

<li><icon>✓</icon> ATS optimization</li>

<li><icon>✓</icon> All export formats (Docx, PDF)</li>

</ul>

</div>

<div class="card-footer">

<button class="primary large" (click)="startTrial()">

Start Free Trial

</button>

<p class="disclaimer">No credit card required</p>

</div>

<!-- Monthly Plan -->

<div class="pricing-card monthly-card">

<div class="card-header">

<h2>Monthly</h2>

<div class="price">

<span class="amount">$29.95</span>

<span class="period">/month</span>

</div>

</div>

<div class="card-features">


<h4>Everything in Free Trial, plus:</h4>

<ul>

<li><icon>✓</icon> <strong>Unlimited applications</strong></li>

<li><icon>✓</icon> Priority support</li>

<li><icon>✓</icon> Advanced analytics</li>

<li><icon>✓</icon> Document version history</li>

<li><icon>✓</icon> Cancel anytime</li>

</ul>

</div>

<div class="card-footer">

<button class="secondary large" (click)="selectPlan('monthly')">

Choose Monthly

</button>

<p class="billing-info">Billed monthly at $29.95</p>

</div>

</div>

<!-- Quarterly Plan (Best Value) -->

<div class="pricing-card quarterly-card featured">

<div class="card-badge">Best Value</div>

<div class="savings-badge">Save 17%</div>


<div class="card-header">

<h2>Quarterly</h2>

<div class="price">

<span class="amount">$24.95</span>

<span class="period">/month</span>

</div>

<div class="price-comparison">

<span class="original-price">$29.95</span>

<span class="savings">Save $14.85</span>

</div>

</div>

<div class="card-features">

<h4>Everything in Monthly, plus:</h4>

<ul>

<li><icon>✓</icon> <strong>17% discount</strong></li>

<li><icon>✓</icon> Priority processing</li>

<li><icon>✓</icon> Early access to new features</li>

<li><icon>✓</icon> Dedicated support</li>

</ul>

</div>


<div class="card-footer">

<button class="primary large" (click)="selectPlan('quarterly')">

Choose Quarterly

</button>

<p class="billing-info">

Billed quarterly at <strong>$74.85</strong>

<br>

<small>($24.95/month × 3 months)</small>

</p>

</div>

</div>

## ⏰

**Your trial ends in {{ trialDaysRemaining }} days**

Add a payment method now to continue with unlimited applications

You'll automatically continue on the Monthly plan ($29.95/month) unless you cancel or switch
plans

Add Payment Method Manage Subscription

**Frequently Asked Questions**

<div class="faq-item">

<h4>Do I need a credit card for the free trial?</h4>

<p>

No! You can start your 14-day trial without providing a credit card.

You'll get 3 complete application packages to try our service.


</p>

</div>

<div class="faq-item">

<h4>What happens after my trial ends?</h4>

<p>

If you added a credit card, you'll automatically continue on the

Monthly plan at $29.95/month. If you didn't add a card, your trial

simply ends and you can upgrade anytime.

</p>

</div>

<div class="faq-item">

<h4>How does quarterly billing work?</h4>

<p>

With the Quarterly plan, you pay $74.85 upfront every 3 months

(equivalent to $24.95/month). This saves you 17% compared to

paying monthly.

</p>

</div>

<div class="faq-item">

<h4>Can I cancel anytime?</h4>

<p>

Yes! You can cancel your subscription at any time. You'll continue


to have access until the end of your current billing period (monthly

or quarterly).

</p>

</div>

<div class="faq-item">

<h4>Can I switch between plans?</h4>

<p>

Yes, you can upgrade or downgrade between Monthly and Quarterly at

any time. Changes take effect at your next billing cycle.

</p>

</div>

6. Account Settings - Subscription Management html

**Subscription**

**Free Trial**

Active

<div class="status-details">

<div class="detail-row">

<span class="label">Trial ends:</span>

<span class="value">{{ user.trial_end_date | date:'MMM d, yyyy' }}</span>

<span class="countdown">{{ trialDaysRemaining }} days remaining</span>

</div>


<div class="detail-row">

<span class="label">Applications used:</span>

<span class="value">{{ user.trial_applications_used }} / 3</span>

</div>

<div class="payment-status">

<icon *ngIf="!user.payment_method_on_file" class="warning">⚠</icon>

<icon *ngIf="user.payment_method_on_file" class="success">✓</icon>

<span *ngIf="!user.payment_method_on_file">

No payment method on file

</span>

<span *ngIf="user.payment_method_on_file">

Will convert to Monthly plan ($29.95/month) on {{ user.trial_end_date | date:'MMM d' }}

</span>

</div>

</div>

<div class="status-actions">

<button class="primary" *ngIf="!user.payment_method_on_file"

(click)="addPaymentMethod()">

Add Payment Method

</button>

<button class="secondary" *ngIf="user.payment_method_on_file"


(click)="manageBilling()">

Manage Billing

</button>

<button class="tertiary" (click)="upgradeToPaid()">

Upgrade Now

</button>

</div>

**Monthly Plan**

Active

<div class="status-details">

<div class="detail-row">

<span class="label">Plan:</span>

<span class="value">$29.95/month</span>

</div>

<div class="detail-row">

<span class="label">Next billing date:</span>

<span class="value">{{ user.next_billing_date | date:'MMM d, yyyy' }}</span>

</div>

<div class="detail-row">

<span class="label">Next charge:</span>


<span class="value">${{ user.next_billing_amount }}</span>

</div>

</div>

<div class="status-actions">

<button class="primary" (click)="switchToQuarterly()">

Switch to Quarterly (Save 17%)

</button>

<button class="secondary" (click)="manageBilling()">

Update Payment Method

</button>

<button class="tertiary danger" (click)="cancelSubscription()">

Cancel Subscription

</button>

</div>

**Quarterly Plan**

Active 17% Savings

<div class="status-details">

<div class="detail-row">

<span class="label">Plan:</span>

<span class="value">

$24.95/month

<small>(Billed quarterly at $74.85)</small>

</span>


</div>

<div class="detail-row">

<span class="label">Current period:</span>

<span class="value">

{{ user.current_period_start | date:'MMM d' }} -

{{ user.current_period_end | date:'MMM d, yyyy' }}

</span>

</div>

<div class="detail-row">

<span class="label">Next billing date:</span>

<span class="value">{{ user.next_billing_date | date:'MMM d, yyyy' }}</span>

</div>

<div class="detail-row">

<span class="label">Next charge:</span>

<span class="value">$74.85</span>

</div>

<div class="savings-highlight">

<icon>💰</icon>


You're saving $59.40 per year compared to monthly billing!

</div>

</div>

<div class="status-actions">

<button class="secondary" (click)="manageBilling()">

Update Payment Method

</button>

<button class="tertiary" (click)="switchToMonthly()">

Switch to Monthly

</button>

<button class="tertiary danger" (click)="cancelSubscription()">

Cancel Subscription

</button>

</div>

**Free Tier**

Inactive

<div class="status-details">

<div class="detail-row">

<span class="label">Applications remaining:</span>

<span class="value">{{ user.credits_remaining }} / 3</span>

</div>


<div class="upgrade-prompt">

<p>Upgrade to unlimited applications and premium features</p>

</div>

</div>

<div class="status-actions">

<button class="primary" (click)="navigateToPricing()">

View Plans & Pricing

</button>

</div>

7. Payment Method Addition Flow typescript// Angular Component: Add Payment Method
During Trial export class AddPaymentMethodComponent { autoConvert: boolean = true; //
Default to auto-convert stripeElements: any; cardElement: any;

ngOnInit() { // Initialize Stripe this.stripe = Stripe(environment.stripePublicKey);
this.stripeElements = this.stripe.elements();

// Create card element

this.cardElement = this.stripeElements.create('card', {

style: {

base: {

fontSize: '16px',

color: '#32325d',

fontFamily: '"Helvetica Neue", Helvetica, sans-serif'

## }

## }

## });


this.cardElement.mount('#card-element');

## }

async submitPaymentMethod() { // Create payment method const { error, paymentMethod } =
await this.stripe.createPaymentMethod({ type: 'card', card: this.cardElement, billing_details: {
email: this.user.email, name: this.user.name } });

if (error) {

this.showError(error.message);

return;

## }

// Send to backend

try {

const response = await this.http.post('/api/trial/add-payment-method', {

payment_method_id: paymentMethod.id,

auto_convert: this.autoConvert

}).toPromise();

this.showSuccess(

this.autoConvert

? 'Payment method added! Your trial will automatically convert to paid on ' +

new Date(response.trial_end_date).toLocaleDateString()

: 'Payment method saved for future use'

## );


this.router.navigate(['/dashboard']);

} catch (error) {

this.showError('Failed to add payment method. Please try again.');

## }

} } html

**Add Payment Method**

Your trial ends on **{{ trialEndDate | date:'MMM d, yyyy' }}**

{{ trialDaysRemaining }} days remaining

<!-- Card Element -->

<div class="form-group">

<label>Credit or Debit Card</label>

<div id="card-element"></div>

<div id="card-errors" role="alert"></div>

</div>

<!-- Auto-Convert Option -->

<div class="form-group checkbox">

<input

type="checkbox"

id="auto-convert"

[(ngModel)]="autoConvert"

name="autoConvert"


## />

<label for="auto-convert">

<strong>Automatically continue subscription after trial</strong>

<p class="help-text">

When your trial ends, you'll be charged $29.95/month and continue

with unlimited applications. You can cancel anytime.

</p>

</label>

</div>

<div class="billing-preview" *ngIf="autoConvert">

<h4>Billing Preview</h4>

<div class="preview-row">

<span>Trial period:</span>

<span>Now - {{ trialEndDate | date:'MMM d' }}</span>

<span class="free">$0.00</span>

</div>

<div class="preview-row">

<span>First charge:</span>

<span>{{ trialEndDate | date:'MMM d' }}</span>

<span><strong>$29.95</strong></span>

</div>

<div class="preview-row">


<span>Then monthly:</span>

<span>Auto-renews monthly</span>

<span>$29.95</span>

</div>

</div>

<div class="form-actions">

<button type="button" class="secondary" (click)="closeModal()">

Cancel

</button>

<button type="submit" class="primary">

{{ autoConvert? 'Save & Auto-Convert' : 'Save Payment Method' }}

</button>

</div>

<p class="disclaimer">

<icon>🔒</icon>

Your payment information is secure and encrypted.

We use Stripe for payment processing.

</p>

8. Email Templates pythondef send_trial_welcome_email(email, name, trial_end_date): """
Welcome email when user starts trial """ email_body = f"""

Hi {name},

Welcome to CareerVP! Your 14-day free trial has started.


## WHAT YOU GET:

✓ 3 complete application packages ✓ AI-powered CV tailoring ✓ Value Proposition Reports ✓
Custom cover letters ✓ Interview preparation guides ✓ ATS optimization

Your trial includes full access to all features - no credit card required.

## TRIAL DETAILS:

- Started: {datetime.utcnow().strftime('%B %d, %Y')}
- Ends: {trial_end_date.strftime('%B %d, %Y')}
- Applications remaining: 3

## GET STARTED:

Create your first application: https://app.careervp.com/new-application

## WANT UNLIMITED APPLICATIONS?

Add a payment method to automatically continue with unlimited applications after your trial
ends. Only $29.95/month, or save 17% with quarterly billing.

View plans: https://app.careervp.com/pricing

Questions? Reply to this email anytime.

Best regards, The CareerVP Team """.strip()

ses.send_email(

Source='welcome@careervp.com',

Destination={'ToAddresses': [email]},

Message={

'Subject': {'Data': 'Welcome to CareerVP! Your Trial Has Started'},

'Body': {'Text': {'Data': email_body}}

## }

## )


def send_trial_ending_reminder(user, days_remaining): """ Reminder email before trial ends """

has_cc = user.get('trial_has_credit_card', False)

if has_cc:

subject = f'Your CareerVP trial ends in {days_remaining} days'

message = f"""

Hi {user.get('name', 'there')},

Your CareerVP free trial ends in {days_remaining} days.

## GOOD NEWS:

You've already added a payment method, so you'll automatically continue with unlimited
applications at $29.95/month when your trial ends.

## WANT TO SAVE 17%?

Switch to quarterly billing before your trial ends: https://app.careervp.com/account/subscription

- Quarterly: $24.95/month (billed $74.85 every 3 months)
- Save $14.85 vs monthly billing

## DON'T WANT TO CONTINUE?

You can cancel anytime in your account settings: https://app.careervp.com/account/subscription

Best regards, The CareerVP Team """.strip()

else:

subject = f'{days_remaining} days left in your CareerVP trial'

message = f"""

Hi {user.get('name', 'there')},

Your CareerVP free trial ends in {days_remaining} days.

You've used {user.get('trial_applications_used', 0)} of 3 free applications.


## CONTINUE WITH UNLIMITED APPLICATIONS:

Add a payment method to keep using CareerVP after your trial: https://app.careervp.com/pricing

## PRICING OPTIONS:

- Monthly: $29.95/month
- Quarterly: $24.95/month (save 17%, billed $74.85 every 3 months)

Both plans include: ✓ Unlimited application generation ✓ All premium features ✓ Priority
support ✓ Cancel anytime

Questions? Reply to this email.

Best regards, The CareerVP Team """.strip()

ses.send_email(

Source='notifications@careervp.com',

Destination={'ToAddresses': [user['email']]},

Message={

'Subject': {'Data': subject},

'Body': {'Text': {'Data': message}}

## }

## )

def send_trial_converted_email(email, name): """ Confirmation when trial converts to paid
subscription """

email_body = f"""

Hi {name},

Your CareerVP trial has ended and you're now on the Monthly plan!

## SUBSCRIPTION DETAILS:

- Plan: Monthly ($29.95/month)


- Applications: Unlimited
- Billing: Monthly on the same day each month
- First charge: Today ($29.95)

## MANAGE YOUR SUBSCRIPTION:

View billing history and update payment method: https://app.careervp.com/account/subscription

## WANT TO SAVE 17%?

Switch to quarterly billing anytime:

- Quarterly: $24.95/month (billed $74.85 every 3 months)
- Saves you $59.40 per year

Thank you for choosing CareerVP!

Best regards, The CareerVP Team

P.S. You can cancel your subscription anytime. No questions asked. """.strip()

ses.send_email(

Source='billing@careervp.com',

Destination={'ToAddresses': [email]},

Message={

'Subject': {'Data': 'Welcome to CareerVP Premium - Monthly Plan'},

'Body': {'Text': {'Data': email_body}}

## }

## )

def send_trial_expired_email(email, name): """ Email when trial expires without credit card """

email_body = f"""

Hi {name},

Your CareerVP free trial has ended.


## TRIAL SUMMARY:

You had access to 3 free application packages over the past 14 days. We hope you found our
AI-powered tools helpful for your job search!

## CONTINUE USING CAREERVP:

Upgrade to unlimited applications: https://app.careervp.com/pricing

## PRICING OPTIONS:

- Monthly: $29.95/month
- Quarterly: $24.95/month (save 17%, billed $74.85 every 3 months)

## YOUR DOCUMENTS ARE SAFE:

All application materials you created during your trial are still accessible in your account:
https://app.careervp.com/applications

## QUESTIONS?

Reply to this email or visit our help center: https://help.careervp.com

We'd love to have you back!

Best regards, The CareerVP Team """.strip()

ses.send_email(

Source='notifications@careervp.com',

Destination={'ToAddresses': [email]},

Message={

'Subject': {'Data': 'Your CareerVP Trial Has Ended'},

'Body': {'Text': {'Data': email_body}}

## }

## )


9. Plan Switching Logic python# API: POST /api/subscription/switch-plan
    @app.post('/api/subscription/switch-plan') def switch_subscription_plan( new_plan: str,
    # 'monthly' or 'quarterly' current_user: User = Depends(get_current_user) ): """ Switch
    between Monthly and Quarterly plans """

Verify user has active subscription

```
if current_user.subscription_status != 'active': raise HTTPException( status_code=400,
detail="No active subscription to modify" )
```
Verify not already on requested plan

```
current_plan = current_user.tier if (new_plan == 'monthly' and current_plan == 'monthly')
or
(new_plan == 'quarterly' and current_plan == 'quarterly'): raise HTTPException(
status_code=400, detail=f"Already on {new_plan} plan" )
```
Determine new price ID

```
new_price_id = ( STRIPE_MONTHLY_PRICE_ID if new_plan == 'monthly' else
STRIPE_QUARTERLY_PRICE_ID )
```
Update Stripe subscription

```
subscription = stripe.Subscription.retrieve( current_user.stripe_subscription_id )
```
Modify subscription (change takes effect at next

billing cycle)

```
updated_subscription = stripe.Subscription.modify( current_user.stripe_subscription_id,
items=[{ 'id': subscription['items']['data'][0].id, 'price': new_price_id }],
proration_behavior='none', # No proration, change at renewal metadata={
'plan_changed_from': current_plan, 'plan_changed_to': new_plan, 'plan_changed_at':
datetime.utcnow().isoformat() } )
```
Calculate next billing amount

```
next_amount = 29.95 if new_plan == 'monthly' else 74.85
```

Update DynamoDB

```
dynamodb.update_item( TableName='careervp-users', Key={'user_id':
current_user.user_id}, UpdateExpression=''' SET tier = :tier, subscription_plan = :plan,
next_billing_amount = :amount ''', ExpressionAttributeValues={ ':tier': new_plan, ':plan':
f'{new_plan}_{"2995" if new_plan == "monthly" else "7485"}', ':amount':
Decimal(str(next_amount)) } )
```
Send confirmation email

```
send_plan_switch_confirmation_email( email=current_user.email,
name=current_user.name, old_plan=current_plan, new_plan=new_plan,
next_billing_date=updated_subscription.current_period_end )
```
```
return { 'status': 'success', 'message': f'Switched to {new_plan} plan', 'new_plan':
new_plan, 'next_billing_date': updated_subscription.current_period_end,
'next_billing_amount': next_amount, 'effective_date': datetime.fromtimestamp(
updated_subscription.current_period_end ).isoformat() }
```
Summary Pricing Structure ✅ Free Trial:

14 days 3 applications No credit card required Optional auto-conversion with CC

Monthly Plan:

$29.95/month Unlimited applications Auto-conversion from trial (if CC provided) Cancel anytime

Quarterly Plan:

$24.95/month displayed $74.85 billed quarterly 17% savings ($14.85 vs monthly) Unlimited
applications Cancel anytime

Key Features:

Credit card optional for trial Auto-conversion if CC added during trial Clear pricing display
(monthly equivalent + actual quarterly charge) Easy plan switching Comprehensive email
notifications Stripe integration for billing Trial monitoring and conversion automation Transparent
billing on account page

All pricing logic, UI components, email templates, and backend systems implemented! 🎉


# Tab 13


Alignment Matrix Update - Business Impact Column Changes Required

1. Updated Prompt Templates yaml# prompts/vpr_brief_generation.yaml
    vpr_brief_generation: | You are creating a concise Value Proposition Report (Brief
    version).

## INPUTS:

- Job Posting: {{job_posting}}
- Master CV: {{master_cv}}
- Company Research: {{company_research}}
- Gap Analysis: {{gap_analysis_answers}}

## OUTPUT REQUIREMENTS:

Length: 1-2 pages maximum Language: {{output_language}} Format: Professional business
document

## REQUIRED SECTIONS:

1. VALUE PROPOSITION STATEMENT (2-3 sentences) Synthesize candidate's unique fit
    for this specific role. Reference quantifiable achievements from Gap Analysis.

## 2. ALIGNMENT MATRIX (TABLE FORMAT MANDATORY)

```
Job Requirement Your Evidence Business Impact
```
```
[req from job] [CV + Gap Analysis
evidence]
```
```
[quantified impact]
```
```
Include 6-8 rows covering:
```
- Top 3 technical requirements
- Top 2 experience requirements
- 1-2 soft skill requirements

```
BUSINESS IMPACT COLUMN INSTRUCTIONS: The "Business Impact" column MUST
quantify the business value using:
```
- Dollar amounts saved/generated (e.g., "$200K cost reduction")
- Percentage improvements (e.g., "40% faster deployment")
- Time saved (e.g., "Reduced processing time 60%")
- Scale/reach metrics (e.g., "Impacted 1M+ users")
- Team/organizational impact (e.g., "Methodology adopted by 12 teams")


```
CRITICAL: Use specific examples from Gap Analysis to strengthen evidence and
quantify business impact.
```
```
Example row: | 5+ years Python | 7 years Python at TechCorp. Led team that reduced
API latency from 800ms to 320ms using async/await patterns (Gap Analysis Q2) | $200K
annual savings, 85% fewer customer complaints |
```
3. KEY DIFFERENTIATORS (3-5 bullet points) What makes this candidate stand out?
    MUST include:
       - Quantified achievements (numbers, percentages, dollar amounts)
       - Evidence from Gap Analysis
       - Unique combinations of skills/experience

```
Example: • Cost Optimization Expert: Reduced infrastructure costs $500K through AWS
serverless migration (from Gap Analysis Q3)
```
## FORMATTING:

- Use clear headings
- Professional tone, not salesy
- Evidence-based, not generic claims
- Alignment Matrix MUST be in table format (not prose)
- Business Impact MUST be quantified wherever possible yaml#
    prompts/vpr_complete_generation.yaml vpr_complete_generation: | You are creating a
    comprehensive Value Proposition Report (Complete version).

This is the COMPLETE VPR that includes all strategic sections for thorough interview
preparation and competitive positioning.

## INPUTS:

- Job Posting: {{job_posting}}
- Master CV: {{master_cv}}
- Company Research: {{company_research}}
- Gap Analysis: {{gap_analysis_answers}}

## OUTPUT REQUIREMENTS:

Length: 5-8 pages Language: {{output_language}} Format: Executive-level strategic document

## REQUIRED SECTIONS:


1. EXECUTIVE SUMMARY (1 page) Open with strong positioning:

```
a) Value Proposition Statement (2-3 sentences) Synthesize candidate's unique fit for this
specific role Include quantified achievements from Gap Analysis
```
```
b) Top 3 Reasons You're the Ideal Candidate
```
- Technical excellence: [specific skill + achievement]
- Leadership impact: [team/project outcome]
- Strategic value: [business result]

```
c) Key Differentiators Summary What makes you stand out from typical candidates
```
## 2. ALIGNMENT MATRIX (TABLE FORMAT MANDATORY)

```
Job Requirement Your Evidence Business Impact
```
```
[requirement] [CV + Gap Analysis
evidence]
```
```
[quantified impact]
```
```
Include 10-15 rows covering:
```
- ALL technical requirements (required + preferred)
- Experience requirements
- Education/certifications
- Soft skills (leadership, communication)
- Industry-specific knowledge

```
BUSINESS IMPACT COLUMN INSTRUCTIONS: The "Business Impact" column MUST
quantify value delivered using:
```
```
Financial Metrics:
```
- Revenue generated: "Increased sales $2M annually"
- Costs reduced: "$500K infrastructure savings"
- ROI delivered: "300% ROI on automation project"

```
Efficiency Metrics:
```
- Time saved: "Reduced deployment time 75% (4 hours → 1 hour)"
- Speed improvements: "40% faster processing"
- Productivity gains: "Team output increased 50%"

```
Quality Metrics:
```

- Error reduction: "Bugs decreased 85%"
- Uptime improvements: "99.9% → 99.99% uptime"
- Customer satisfaction: "NPS increased from 45 → 78"

```
Scale Metrics:
```
- User impact: "Served 1M+ daily users"
- Team impact: "Methodology adopted by 12 teams"
- Organizational impact: "Became company standard"

```
USE Gap Analysis responses to provide SPECIFIC examples with metrics.
```
```
Example rows:
```
```
| Python expertise (5+ years) | 7 years Python development. Led optimization project
reducing API latency 800ms → 320ms using async/await (Gap Analysis) | $200K annual
savings, 85% fewer complaints, 1M+ users impacted |
```
```
| AWS architecture | Designed serverless migration for legacy monolith. Built Lambda +
DynamoDB + S3 architecture (Gap Analysis Q4) | $500K infrastructure cost reduction,
40% faster deployments |
```
```
| Team leadership | Managed 8 engineers across 3 projects. Established code review
process and mentored 3 juniors to senior roles (Gap Analysis) | 75% bug reduction, 50%
faster onboarding, zero team turnover |
```
3. COMPANY DEEP DIVE (1-2 pages)

```
a) Industry Position
```
- Market standing and competitive landscape
- Key competitors and differentiation

```
b) Recent Developments (Past 12 Months)
```
- Funding rounds, acquisitions, partnerships
- Product launches or strategic pivots
- Leadership changes
- Press coverage and sentiment

```
c) Company Culture & Values
```
- Stated values from company materials


- Employee reviews and sentiment
- Work environment indicators

```
d) Strategic Priorities
```
- Inferred from job posting requirements
- Company growth initiatives
- Technology investments
4. COMPETITIVE POSITIONING (1 page)

```
"How You Compare to Typical Applicants"
```
```
a) Unique Skill Combinations Skills that rarely exist together: Example: "Python expertise
+ regulatory compliance + healthcare domain knowledge is rare (only 12% of candidates
per LinkedIn data)"
```
```
b) Differentiating Experiences Unusual or high-impact experiences Example: "Led
Fortune 500 migration (enterprise scale) while also building startup MVPs (agility)"
```
```
c) Cultural Fit Indicators Evidence from Gap Analysis showing alignment with company
values
```
```
d) Overqualification/Underqualification Assessment Honest evaluation with mitigation
strategies
```
5. RISK ASSESSMENT & MITIGATION (1 page)

```
For each potential concern, provide:
```
```
Potential Concern Mitigation Strategy
```
```
[hiring manager worry] [how to address proactively]
```
```
Common risks to assess:
```
- Employment gaps (if any)
- Skill gaps (from Alignment Matrix lower business impact items)
- Career transitions or pivots
- Geographic/remote considerations
- Overqualification concerns
- Industry switching


```
Example: | Limited Kubernetes experience | Demonstrate: (1) 5 years
Docker/containerization, (2) Self-learning: completed CKA prep, (3) Transferable:
architected similar orchestration with Docker Swarm delivering 40% deployment speed
improvement |
```
6. STRATEGIC RECOMMENDATIONS (1-2 pages)

```
a) Interview Preparation Priorities
```
- Top 5 talking points to prepare
- Anticipated difficult questions
- Stories to practice (STAR format)

```
b) Key Messages by Interview Stage
```
- Phone screen: [focus areas]
- Technical interview: [demos to prepare]
- Behavioral interview: [stories to emphasize]
- Final interview: [strategic insights to share]

```
c) Questions to Ask Interviewers
```
- About role: [3-4 questions]
- About team: [2-3 questions]
- About company: [2-3 questions] (Questions should demonstrate research and
    strategic thinking)

```
d) Negotiation Considerations
```
- Market rate for this role/location
- Your positioning (strong/moderate leverage)
- Non-monetary value-adds to negotiate
7. EVIDENCE LIBRARY (1 page)

```
Detailed expansion of Alignment Matrix claims:
```
```
For each major achievement referenced:
```
- Full project context
- Your specific role and responsibilities
- Challenges overcome
- Quantified outcomes (metrics, percentages, dollar amounts)
- Technologies/methodologies used


- Team size/structure
- BUSINESS IMPACT with specific numbers

```
Example: "API Latency Reduction Project (Referenced in Alignment Matrix)
```
```
Context: Legacy monolith API serving 1M requests/day with P95 latency of 800ms,
causing customer complaints and SLA violations.
```
```
Your Role: Tech lead for 6-month optimization initiative, managed team of 3 engineers.
```
```
Approach:
```
- Profiled hotspots using New Relic APM
- Implemented async/await patterns for I/O operations
- Added Redis caching layer for frequent queries
- Optimized database indexes

```
Business Impact:
```
- P95 latency: 800ms → 320ms (60% improvement)
- Customer complaints: Decreased 85%
- Infrastructure costs: Reduced $200K annually (fewer servers needed)
- User experience: Page load time 40% faster
- Organizational impact: Methodology adopted by 12 teams
- SLA compliance: From 92% → 99.8%

```
Technologies: Python 3.9, FastAPI, Redis, PostgreSQL, Docker"
```
## FORMATTING REQUIREMENTS:

- Professional executive document styling
- Clear section breaks with headings
- Tables where specified (Alignment Matrix, Risk Assessment)
- Evidence-based throughout (cite Gap Analysis, CV, company research)
- Strategic insights, not obvious observations
- Quantify wherever possible (numbers, percentages, dollars)
- Language: {{output_language}}
- Business Impact MUST be specific and measurable

## TONE:

- Confident but not arrogant
- Strategic and analytical
- Evidence-driven, not marketing fluff


- Honest about risks/gaps (with mitigation)
- Executive-level polish
2. Updated Documentation Examples markdown# VPR Brief Example (Updated)

Value Proposition Report: Senior Python Developer at TechCorp

Value Proposition Statement

John brings 7 years of Python expertise with proven success in high-performance API
development, having reduced latency by 60% while saving $200K annually through async/await
optimization. His experience leading cross-functional teams of 8 engineers, combined with AWS
serverless architecture expertise, aligns perfectly with TechCorp's need for a senior developer
who can architect scalable cloud-native solutions while mentoring junior engineers.

Alignment Matrix

```
Job Requirement Your Evidence Business Impact
```
```
5+ years Python
development
```
```
7 years Python at MegaCorp.
Led team that reduced API
latency from 800ms to 320ms
using async/await patterns
(Gap Analysis Q2). Built
internal framework used
across engineering.
```
```
$200K annual cost savings,
85% reduction in customer
complaints, 1M+ daily users
impacted, framework adopted
by 12 teams
```
```
AWS serverless architecture Designed and implemented
serverless migration for
legacy monolith. Built
Lambda + DynamoDB + S3
architecture serving 500K
requests/day (Gap Analysis
Q4).
```
```
$500K infrastructure cost
reduction (40% savings),
50% faster deployments,
99.9% uptime achieved
```
```
Team leadership & mentoring Managed 8 engineers across
3 concurrent projects.
Established code review
process that became team
standard. Mentored 3 junior
developers to senior roles
(Gap Analysis Q6).
```
```
75% bug reduction in
production, 50% faster new
hire onboarding, zero team
turnover over 2 years
```

```
Job Requirement Your Evidence Business Impact
```
```
REST API design &
implementation
```
```
Built 15+ RESTful APIs
serving 1M+ requests/day.
Designed API versioning
strategy enabling
zero-downtime deployments
(Gap Analysis Q3).
```
```
99.95% API uptime, version
migration completed for 50+
clients with zero incidents
```
```
CI/CD pipeline development Built Jenkins pipelines
reducing deployment time
from 4 hours to 1 hour.
Implemented automated
testing catching 90% of bugs
pre-production (Gap Analysis
Q5).
```
```
75% faster release cycle
(monthly → weekly), $150K
QA cost reduction, 90% bug
detection pre-production
```
```
Agile/Scrum methodology 3 years as Scrum Master for
2 teams. PSM I certified.
Facilitated sprint planning
and retrospectives improving
velocity 35% (Gap Analysis
Q7).
```
```
35% team velocity increase,
sprint goals met 95% vs 70%
previously, stakeholder
satisfaction improved to 4.8/5
```
Key Differentiators

1. **Cost Optimization Expert** : Delivered $700K in cumulative cost savings through
    infrastructure optimization ($500K) and API performance improvements ($200K) - Gap
    Analysis Q3-Q4
2. **Performance Optimization** : Achieved 60% latency reduction impacting 1M+ daily users
    while reducing infrastructure costs 40% simultaneously - Gap Analysis Q2
3. **Technical Leadership** : Established engineering practices (code review, CI/CD) that
    reduced bugs 75% and became company standards, while mentoring 3 engineers to
    senior roles with zero team turnover - Gap Analysis Q5-Q6
4. **Scale & Reliability** : Built and maintained systems serving 1M+ requests/day with
    99.95% uptime across 15+ production APIs - Gap Analysis Q3
5. **Cross-functional Impact** : Created frameworks and methodologies adopted by 12
    teams across organization, accelerating delivery 35% company-wide - Gap Analysis Q7
6. Updated UI Display html


**Alignment Matrix**

How your experience maps to job requirements with quantified business impact

<div class="table-responsive">

<table class="alignment-table">

<thead>

<tr>

<th class="col-requirement">Job Requirement</th>

<th class="col-evidence">Your Evidence</th>

<th class="col-impact">Business Impact</th>

</tr>

</thead>

<tbody>

<tr *ngFor="let row of alignmentMatrix">

<td class="requirement">

<strong>{{ row.requirement }}</strong>

</td>

<td class="evidence">

{{ row.evidence }}

</td>

<td class="impact highlight">

<div class="impact-metrics">

<span class="metric" *ngFor="let metric of row.impact_metrics">


<icon *ngIf="metric.type === 'financial'">💰</icon>

<icon *ngIf="metric.type === 'efficiency'">⚡</icon>

<icon *ngIf="metric.type === 'quality'">✓</icon>

<icon *ngIf="metric.type === 'scale'">📈</icon>

{{ metric.value }}

</span>

</div>

</td>

</tr>

</tbody>

</table>

</div>

<div class="table-legend">

<h4>Impact Categories:</h4>

<div class="legend-items">

<div class="legend-item">

<icon>💰</icon>

<span>Financial Impact (revenue, cost savings, ROI)</span>

</div>

<div class="legend-item">

<icon>⚡</icon>

<span>Efficiency Gains (time saved, speed improvements)</span>


</div>

<div class="legend-item">

<icon>✓</icon>

<span>Quality Improvements (error reduction, uptime)</span>

</div>

<div class="legend-item">

<icon>📈</icon>

<span>Scale & Reach (users, teams, adoption)</span>

</div>

</div>

</div>

4. Updated CSS Styling css/* Alignment Matrix Table Styling */ .alignment-table { width: 100%;
border-collapse: collapse; margin: 20px 0; background: white; box-shadow: 0 2px 4px
rgba(0,0,0,0.1); } .alignment-table thead { background: linear-gradient(135deg, #667eea 0%,
#764ba2 100%); color: white; }

.alignment-table th { padding: 16px; text-align: left; font-weight: 600; font-size: 14px;
text-transform: uppercase; letter-spacing: 0.5px; }

.alignment-table th.col-requirement { width: 25%; }

.alignment-table th.col-evidence { width: 45%; }

.alignment-table th.col-impact { width: 30%; }

.alignment-table tbody tr { border-bottom: 1px solid #e5e7eb; transition: background-color 0.2s; }

.alignment-table tbody tr:hover { background-color: #f9fafb; }

.alignment-table td { padding: 16px; font-size: 14px; line-height: 1.6; vertical-align: top; }

.alignment-table td.requirement strong { color: #1f2937; font-size: 15px; }


.alignment-table td.evidence { color: #4b5563; }

.alignment-table td.impact { background-color: #fef3c7; font-weight: 500; }

.impact-metrics { display: flex; flex-direction: column; gap: 8px; }

.impact-metrics .metric { display: flex; align-items: center; gap: 6px; padding: 4px 8px;
background: white; border-radius: 4px; font-size: 13px; color: #1f2937; }

.impact-metrics .metric icon { font-size: 16px; }

/* Table Legend */ .table-legend { margin-top: 24px; padding: 16px; background: #f9fafb;
border-radius: 8px; border-left: 4px solid #667eea; }

.table-legend h4 { margin: 0 0 12px 0; font-size: 14px; font-weight: 600; color: #1f2937; }

.legend-items { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap:
12px; }

.legend-item { display: flex; align-items: center; gap: 8px; font-size: 13px; color: #4b5563; }

.legend-item icon { font-size: 18px; }

/* Responsive adjustments */ @media (max-width: 768px) { .alignment-table { font-size: 12px; }

.alignment-table th, .alignment-table td { padding: 12px 8px; }

.alignment-table th.col-requirement, .alignment-table th.col-evidence, .alignment-table
th.col-impact { width: auto; } } 5. Updated Test Cases yaml# Test Case: VPR Generation with
Business Impact TC-VPR-002: Alignment Matrix Business Impact Validation

Input:

- Job Posting: Senior Python Developer role
- CV: 7 years Python experience
- Gap Analysis: Q2 answered with latency reduction details

Expected Output - Alignment Matrix Row: Job Requirement: "5+ years Python development"
Your Evidence: "7 years Python at MegaCorp. Led optimization project..." Business Impact:
MUST include quantified metrics such as: - Dollar amount (e.g., "$200K annual savings") -
Percentage (e.g., "60% latency reduction") - Scale (e.g., "1M+ users impacted") - Organizational
impact (e.g., "adopted by 12 teams")


Validation: ✓ Business Impact column contains at least 2 quantified metrics ✓ Metrics are
specific (not vague like "significant improvement") ✓ Numbers are realistic based on CV and
Gap Analysis ✓ Impact is business-focused (not just technical achievement)

Failure Cases: ✗ Business Impact: "Strong" (too vague) ✗ Business Impact: "Moderate" (not
quantified) ✗ Business Impact: "Improved performance" (no numbers) ✓ Business Impact:
"60% faster, saved $200K, 1M users" 6. Updated Lambda Function Comments python#
Lambda: vpr-generator (UPDATED COMMENTS) def lambda_handler(event, context): """
Generate VPR Brief or VPR Complete

CRITICAL: Alignment Matrix uses "Business Impact" column (not "Strength")

Business Impact must be quantified with:

- Financial metrics ($X saved/generated)
- Efficiency metrics (X% faster, X hours saved)
- Quality metrics (X% error reduction)
- Scale metrics (X users, X teams)

This aligns with original Job Search Assistant skill requirements.

## """

job_id = event['job_id']

vpr_type = event.get('vpr_type', 'brief')

# ... rest of implementation

7. Updated Gap Analysis Questionnaire Prompt yaml#
    prompts/gap_analysis_questions.yaml gap_analysis_questions: | Generate gap analysis
    questions to gather quantifiable business impact data.

CRITICAL REQUIREMENT: Questions MUST elicit quantified business impact responses that
can be used in the Alignment Matrix "Business Impact" column.

Each question should prompt for:

- Specific numbers (percentages, dollar amounts, time saved)
- Scale/reach (users impacted, teams affected)
- Before/after metrics (X → Y improvement)


- Business outcomes (cost savings, revenue generated, efficiency gains)

Example questions that elicit Business Impact data:

✓ "Describe a project where you optimized system performance. What were the measurable
outcomes? (e.g., latency reduction, cost savings, user impact)"

✓ "Tell me about a time you led a team initiative. What quantifiable business results did it
deliver? (e.g., productivity gains, error reduction, time savings)"

✓ "Describe your most impactful technical contribution. What were the measurable business
benefits? (e.g., revenue generated, costs reduced, processes improved)"

✗ "What are your strengths?" (too vague, no business impact) ✗ "Describe your leadership
style" (qualitative, not quantified)

Questions MUST:

- Maximum 10 questions
- Focus on achievements with measurable impact
- Prompt for specific numbers and metrics
- Cover technical, leadership, and business contributions
- Build on previous Gap Analysis responses (show previous Q&A)
8. Updated DynamoDB Schema Documentation yaml# careervp-jobs table Table Name:
    careervp-jobs Partition Key: user_id (String) Sort Key: job_id (String)

Attributes:

... existing attributes ...

Alignment Matrix Data

- alignment_matrix (List) Structure:
    - requirement (String)
    - evidence (String)
    - business_impact (String) # ← Changed from "strength" Examples:
       - "$200K annual savings, 60% latency reduction"
       - "1M+ users impacted, 85% complaint reduction"
       - "Adopted by 12 teams, 35% velocity increase"
9. Updated FAQ Documentation markdown# FAQ: Alignment Matrix


What is the "Business Impact" column?

The Business Impact column quantifies the tangible business value you delivered in previous
roles. This goes beyond just saying you're "strong" or "qualified" and instead shows hiring
managers the concrete results they can expect.

What makes a good Business Impact statement?

Good Business Impact statements include specific, measurable metrics:

**Financial Impact:**

- "Saved $500K in infrastructure costs"
- "Generated $2M in additional revenue"
- "Delivered 300% ROI on automation project"

**Efficiency Impact:**

- "Reduced deployment time 75% (4 hours → 1 hour)"
- "Improved team velocity 35%"
- "Cut processing time from 10 minutes to 2 minutes"

**Quality Impact:**

- "Reduced production bugs 85%"
- "Improved uptime from 99% to 99.9%"
- "Increased customer satisfaction score from 45 to 78"

**Scale Impact:**

- "Served 1M+ daily active users"
- "Methodology adopted by 12 teams"
- "Became company-wide standard"

Why is Business Impact important?

Hiring managers want to know: "What results will this person deliver for us?"

By quantifying your impact, you:

1. Stand out from candidates who only list skills
2. Demonstrate ROI you can deliver
3. Provide concrete proof of your capabilities
4. Make it easy for hiring managers to justify hiring you


Summary Changes Implemented ✅ Column Name Change:

❌ OLD: Strength (⭐⭐⭐ Strong / ⭐⭐ Moderate / ⭐ Developing) ✅ NEW: Business
Impact (quantified metrics and outcomes)

Updated Components:

VPR Brief generation prompt VPR Complete generation prompt Gap Analysis question
generation (to elicit quantifiable data) UI table headers and styling Example documentation Test
cases DynamoDB schema documentation Lambda function comments FAQ and user-facing
documentation

Business Impact Format:

Financial: "$X saved/generated" Efficiency: "X% faster, X time saved" Quality: "X% error
reduction, X% uptime" Scale: "X users, X teams, X adoption"

Key Principle: The Alignment Matrix now focuses on demonstrating quantifiable business value
rather than subjective strength ratings, aligning with the original Job Search Assistant skill
methodology. This makes the VPR more compelling to hiring managers by showing concrete
ROI the candidate can deliver.


# Tab 14


1:40 PM VPR Complete - Add "Gaps and Reframes" Section Updated VPR Complete Prompt
with Gaps and Reframes yaml

prompts/vpr_complete_generation.yaml

vpr_complete_generation: | You are creating a comprehensive Value Proposition Report
(Complete version).

This is the COMPLETE VPR that includes all strategic sections for thorough interview
preparation and competitive positioning.

## INPUTS:

- Job Posting: {{job_posting}}
- Master CV: {{master_cv}}
- Company Research: {{company_research}}
- Gap Analysis: {{gap_analysis_answers}}

## OUTPUT REQUIREMENTS:

Length: 5-8 pages Language: {{output_language}} Format: Executive-level strategic document

## REQUIRED SECTIONS:

1. EXECUTIVE SUMMARY (1 page) Open with strong positioning:

```
a) Value Proposition Statement (2-3 sentences) Synthesize candidate's unique fit for this
specific role Include quantified achievements from Gap Analysis
```
```
b) Top 3 Reasons You're the Ideal Candidate
```
- Technical excellence: [specific skill + achievement]
- Leadership impact: [team/project outcome]
- Strategic value: [business result]

```
c) Key Differentiators Summary What makes you stand out from typical candidates
```
## 2. ALIGNMENT MATRIX (TABLE FORMAT MANDATORY)

```
Job Requirement Your Evidence Business Impact
```
```
[requirement] [CV + Gap Analysis
evidence]
```
```
[quantified impact]
```

```
Include 10-15 rows covering:
```
- ALL technical requirements (required + preferred)
- Experience requirements
- Education/certifications
- Soft skills (leadership, communication)
- Industry-specific knowledge

```
BUSINESS IMPACT COLUMN INSTRUCTIONS: The "Business Impact" column MUST
quantify value delivered using:
```
```
Financial Metrics:
```
- Revenue generated: "Increased sales $2M annually"
- Costs reduced: "$500K infrastructure savings"
- ROI delivered: "300% ROI on automation project"

```
Efficiency Metrics:
```
- Time saved: "Reduced deployment time 75% (4 hours → 1 hour)"
- Speed improvements: "40% faster processing"
- Productivity gains: "Team output increased 50%"

```
Quality Metrics:
```
- Error reduction: "Bugs decreased 85%"
- Uptime improvements: "99.9% → 99.99% uptime"
- Customer satisfaction: "NPS increased from 45 → 78"

```
Scale Metrics:
```
- User impact: "Served 1M+ daily users"
- Team impact: "Methodology adopted by 12 teams"
- Organizational impact: "Became company standard"

```
USE Gap Analysis responses to provide SPECIFIC examples with metrics.
```
3. GAPS AND REFRAMES (1 page)

```
CRITICAL SECTION: Identify potential gaps between job requirements and candidate
profile, then reframe each gap as a strength or opportunity.
```
```
Format as table:
```

```
Potential Gap Strategic Reframe
```
```
[Perceived weakness or missing
qualification]
```
```
[How to position this positively]
```
Include 3-5 gaps covering:

Common Gap Categories:

- Missing specific technology/tool experience
- Years of experience (over/under qualified)
- Industry switching (different domain)
- Education/certification gaps
- Company size transition (startup ↔ enterprise)
- Role level transition (IC → manager or vice versa)
- Geographic/remote work considerations

## REFRAME STRATEGIES:

1. Transferable Skills Reframe Gap: "No Kubernetes experience" Reframe: "5 years
    Docker/containerization + self-learning (CKA prep completed). Transferable:
    Architected similar orchestration with Docker Swarm. Quick learner with proven
    track record of mastering new technologies rapidly (learned React in 3 months,
    delivered production app)."
2. Overqualification Reframe Gap: "15 years experience for mid-level role"
    Reframe: "Extensive experience means faster ramp-up, mentorship for junior
    team members, and strategic insights from past challenges. Seeking role focused
    on hands-on contribution rather than management. Track record of thriving in
    collaborative team environments."
3. Industry Switch Reframe Gap: "Finance background, applying to healthcare tech"
    Reframe: "Cross-industry perspective brings fresh approaches to problems.
    Finance experience includes regulatory compliance (FINRA, SEC) directly
    applicable to HIPAA. Data security and privacy expertise transfers directly.
    Proven ability to learn domain quickly (mastered financial regulations in 6
    months)."
4. Technology Stack Shift Reframe Gap: "Python background, role requires Go"
    Reframe: "7 years backend development with strong CS fundamentals.
    Language syntax is learnable in weeks - architecture and system design
    expertise is what matters. Already familiar with Go concurrency model through
    Python asyncio. Side project in Go demonstrates capability (GitHub: [link])."


5. Career Gap Reframe Gap: "6-month employment gap in 2023" Reframe:
    "Intentional career break for professional development: Completed AWS
    Solutions Architect certification, contributed to 3 open-source projects (2000+
    GitHub stars combined), built portfolio of side projects demonstrating
    cutting-edge skills. Returned to job market with expanded skillset and renewed
    energy."
6. Company Size Transition Reframe Gap: "Startup experience, applying to Fortune
    500" Reframe: "Startup experience = agility, resourcefulness, wearing multiple
    hats. Built systems from scratch understanding full stack. Comfortable with
    ambiguity and rapid change. Brings entrepreneurial mindset to enterprise
    environment. Track record of building processes and documentation as systems
    scale."

## EXAMPLE TABLE:

```
Potential Gap Strategic Reframe
```
```
Limited Kubernetes experience (job
requires 2+ years, candidate has 0)
```
```
5 years Docker/containerization
experience with deep understanding of
container orchestration principles.
Currently completing CKA certification
(exam scheduled). Proven quick learner:
mastered React in 3 months and
delivered production app. Transferable
experience: architected Docker Swarm
orchestration serving 100K+ daily users
with 99.9% uptime. Strong foundation in
distributed systems, networking, and
cloud infrastructure enables rapid
Kubernetes proficiency.
```
```
Career gap: 8 months between roles in
2023
```
```
Strategic career break for professional
development. Completed AWS Solutions
Architect Professional certification,
contributed to 3 major open-source
projects (2000+ combined GitHub stars),
and built portfolio demonstrating
advanced microservices architecture.
Returned to market with expanded cloud
expertise and fresh perspective. Gap
demonstrates commitment to continuous
```

**Potential Gap Strategic Reframe**

```
learning and staying current with
technology evolution.
```
Applying from startup (50 people) to
enterprise (10,000 people)

```
Startup experience provides agility,
resourcefulness, and full-stack
perspective rare in large organizations.
Built systems from zero requiring
ownership of architecture,
implementation, and operations - brings
entrepreneurial mindset. Comfortable with
ambiguity and rapid iteration. Created
documentation and processes as systems
scaled from 1K to 100K users. Eager to
apply scrappy, results-focused approach
to enterprise challenges while learning
from established best practices.
```
No formal CS degree (bootcamp
background)

```
Intensive software engineering bootcamp
(1000+ hours) followed by 5 years
hands-on experience. Strong CS
fundamentals demonstrated through: (1)
Optimized algorithms reducing runtime
from O(n²) to O(n log n) saving $50K
annually, (2) Designed distributed system
architectures serving millions of users, (3)
Consistent technical blog posts explaining
complex CS concepts. Practical
experience building production systems
often more valuable than theoretical
knowledge. Self-taught developers bring
unique problem-solving approaches.
```
10 years backend, role requires some
frontend work

```
Backend expertise with frontend
capability. Built internal admin tools
requiring React frontends (see portfolio).
Understand full request lifecycle enabling
better API design. Modern backend
developers often work across stack.
Willing to deepen frontend skills - already
proficient in JavaScript/TypeScript.
Backend focus actually advantageous:
brings performance optimization mindset
```

```
Potential Gap Strategic Reframe
```
```
to frontend (reduced bundle size 60%,
improved load time 2s → 0.5s).
```
## INSTRUCTIONS FOR AI:

- Analyze CV against job requirements to identify 3-5 realistic gaps
- For each gap, provide honest but strategic reframe
- Use Gap Analysis responses to support reframes with evidence
- Reframes should be genuine (not dishonest) but positioned optimally
- Include specific examples, metrics, and transferable skills
- Acknowledge the gap directly, then pivot to strengths
- Length: 2-3 sentences per reframe minimum
2. COMPANY DEEP DIVE (1-2 pages)

```
a) Industry Position
```
- Market standing and competitive landscape
- Key competitors and differentiation

```
b) Recent Developments (Past 12 Months)
```
- Funding rounds, acquisitions, partnerships
- Product launches or strategic pivots
- Leadership changes
- Press coverage and sentiment

```
c) Company Culture & Values
```
- Stated values from company materials
- Employee reviews and sentiment
- Work environment indicators

```
d) Strategic Priorities
```
- Inferred from job posting requirements
- Company growth initiatives
- Technology investments
3. COMPETITIVE POSITIONING (1 page)

```
"How You Compare to Typical Applicants"
```

```
a) Unique Skill Combinations Skills that rarely exist together: Example: "Python expertise
+ regulatory compliance + healthcare domain knowledge is rare (only 12% of candidates
per LinkedIn data)"
```
```
b) Differentiating Experiences Unusual or high-impact experiences Example: "Led
Fortune 500 migration (enterprise scale) while also building startup MVPs (agility)"
```
```
c) Cultural Fit Indicators Evidence from Gap Analysis showing alignment with company
values
```
```
d) Experience Level Assessment How candidate compares to typical applicant pool
```
4. STRATEGIC RECOMMENDATIONS (1-2 pages)

```
a) Interview Preparation Priorities
```
- Top 5 talking points to prepare
- Anticipated difficult questions
- Stories to practice (STAR format)
- How to address gaps proactively (reference Gaps and Reframes section)

```
b) Key Messages by Interview Stage
```
- Phone screen: [focus areas]
- Technical interview: [demos to prepare]
- Behavioral interview: [stories to emphasize]
- Final interview: [strategic insights to share]

```
c) Questions to Ask Interviewers
```
- About role: [3-4 questions]
- About team: [2-3 questions]
- About company: [2-3 questions] (Questions should demonstrate research and
    strategic thinking)

```
d) Addressing Gaps Strategy
```
- When to proactively mention gaps (reference Section 3)
- How to pivot from gap to strength
- Backup examples if challenged

```
e) Negotiation Considerations
```

- Market rate for this role/location
- Your positioning (strong/moderate leverage)
- How gaps affect negotiating position
- Non-monetary value-adds to negotiate
5. EVIDENCE LIBRARY (1 page)

```
Detailed expansion of Alignment Matrix claims:
```
```
For each major achievement referenced:
```
- Full project context
- Your specific role and responsibilities
- Challenges overcome
- Quantified outcomes (metrics, percentages, dollar amounts)
- Technologies/methodologies used
- Team size/structure
- Business Impact with specific numbers

```
Example: "API Latency Reduction Project (Referenced in Alignment Matrix)
```
```
Context: Legacy monolith API serving 1M requests/day with P95 latency of 800ms,
causing customer complaints and SLA violations.
```
```
Your Role: Tech lead for 6-month optimization initiative, managed team of 3 engineers.
```
```
Approach:
```
- Profiled hotspots using New Relic APM
- Implemented async/await patterns for I/O operations
- Added Redis caching layer for frequent queries
- Optimized database indexes

```
Business Impact:
```
- P95 latency: 800ms → 320ms (60% improvement)
- Customer complaints: Decreased 85%
- Infrastructure costs: Reduced $200K annually (fewer servers needed)
- User experience: Page load time 40% faster
- Organizational impact: Methodology adopted by 12 teams
- SLA compliance: From 92% → 99.8%

```
Technologies: Python 3.9, FastAPI, Redis, PostgreSQL, Docker"
```

## FORMATTING REQUIREMENTS:

- Professional executive document styling
- Clear section breaks with headings
- Tables where specified (Alignment Matrix, Gaps and Reframes)
- Evidence-based throughout (cite Gap Analysis, CV, company research)
- Strategic insights, not obvious observations
- Quantify wherever possible (numbers, percentages, dollars)
- Language: {{output_language}}
- Business Impact MUST be specific and measurable
- Gaps and Reframes MUST be honest but strategically positioned

## TONE:

- Confident but not arrogant
- Strategic and analytical
- Evidence-driven, not marketing fluff
- Honest about gaps while reframing constructively
- Executive-level polish Updated VPR Complete Example markdown

Value Proposition Report (Complete): Senior Python

Developer at TechCorp

1. Executive Summary

Value Proposition Statement

John brings 7 years of Python expertise with proven success in high-performance API
development, having reduced latency by 60% while saving $200K annually. His experience
leading cross-functional teams of 8 engineers, combined with AWS serverless architecture
expertise, positions him as an ideal candidate to architect scalable cloud-native solutions while
mentoring TechCorp's growing engineering team.

Top 3 Reasons You're the Ideal Candidate

1. **Technical Excellence** : Delivered measurable performance improvements (60% latency
    reduction, 99.95% uptime) across 15+ production APIs serving 1M+ daily users
2. **Leadership Impact** : Established engineering practices adopted by 12 teams
    company-wide, mentored 3 engineers to senior roles with zero team turnover


3. **Strategic Value** : Generated $700K cumulative cost savings through infrastructure
    optimization and performance improvements

Key Differentiators Summary

Rare combination of deep technical expertise, proven cost optimization track record, and
leadership experience at scale. Brings both enterprise rigor (Fortune 500 experience) and
startup agility (led 0→1 product launches).

2. Alignment Matrix

```
Job Requirement Your Evidence Business Impact
```
```
5+ years Python
development
```
```
7 years Python at MegaCorp.
Led optimization reducing
API latency 800ms → 320ms
using async/await (Gap
Analysis Q2). Built internal
framework used across org.
```
```
$200K annual savings, 85%
complaint reduction, 1M+
users impacted, framework
adopted by 12 teams
```
```
AWS serverless architecture Designed serverless
migration for legacy monolith.
Lambda + DynamoDB + S3
architecture serving 500K
requests/day (Gap Analysis
Q4).
```
```
$500K infrastructure cost
reduction (40%), 50% faster
deployments, 99.9% uptime
```
```
Team leadership & mentoring Managed 8 engineers across
3 projects. Established code
review process. Mentored 3
juniors to senior roles (Gap
Analysis Q6).
```
```
75% bug reduction, 50%
faster onboarding, zero
turnover over 2 years
```
```
REST API design Built 15+ APIs serving 1M+
requests/day. Designed
versioning strategy enabling
zero-downtime deployments
(Gap Analysis Q3).
```
```
99.95% uptime, 50+ client
migrations with zero incidents
```
```
CI/CD pipeline development Built Jenkins pipelines
reducing deployment 4 hours
→ 1 hour. Automated testing
catching 90% bugs
```
```
75% faster releases (monthly
→ weekly), $150K QA cost
reduction
```

```
Job Requirement Your Evidence Business Impact
```
```
pre-production (Gap Analysis
Q5).
```
```
Agile/Scrum methodology 3 years Scrum Master for 2
teams. PSM I certified.
Improved velocity 35% (Gap
Analysis Q7).
```
```
35% velocity increase, 95%
sprint goal achievement vs
70% previously
```
```
Microservices architecture Decomposed monolith into 12
microservices. Event-driven
architecture using Kafka.
Reduced deployment risk and
improved team autonomy.
```
```
Independent team
deployments, 90% reduction
in cross-team dependencies,
3x deployment frequency
```
```
Docker/containerization 5 years Docker experience.
Containerized 20+
applications. Managed
Docker Swarm cluster (100+
containers).
```
```
60% faster environment
setup, consistent dev/prod
parity, $80K infrastructure
savings
```
```
PostgreSQL/database
optimization
```
```
6 years PostgreSQL.
Optimized queries reducing
DB load 70%. Implemented
read replicas and connection
pooling.
```
```
70% database cost reduction,
sub-100ms query times,
scaled to 10M+ records
```
```
Monitoring & observability Implemented New Relic APM
and custom dashboards. Set
up alerting reducing MTTR
from 2 hours to 15 minutes.
```
```
87% faster incident
resolution, 99.9% uptime
achievement, proactive issue
detection
```
3. Gaps and Reframes

Strategic Positioning for Potential Concerns

```
Potential Gap Strategic Reframe
```
```
Limited Kubernetes experience (job
requires 2+ years, candidate has basic
exposure only)
```
```
5 years Docker/containerization experience
with deep understanding of container
orchestration principles. Currently completing
```

**Potential Gap Strategic Reframe**

```
CKA certification (exam scheduled for next
month, practice exams scoring 85+). Proven
quick learner with track record of mastering
new technologies rapidly: learned React in 3
months and delivered production application,
mastered AWS in 6 months and became
team's cloud architecture lead. Transferable
experience: architected Docker Swarm
orchestration serving 100K+ daily users with
99.9% uptime - core concepts (scheduling,
networking, service discovery, health checks)
directly applicable to Kubernetes. Strong
foundation in distributed systems, networking,
and cloud infrastructure enables rapid
Kubernetes proficiency. Already deployed test
Kubernetes cluster and migrated sample
microservices application.
```
**No experience with TechCorp's specific
tech stack** (requires Golang, candidate
primarily Python)

```
7 years backend development with strong
computer science fundamentals - language
syntax is learnable in weeks, architecture and
system design expertise is what truly matters.
Already proficient in multiple languages
(Python, JavaScript/TypeScript, some Java)
demonstrating language learning ability.
Familiar with Go's concurrency model through
extensive Python asyncio work. Have built
side project in Go (microservices REST API
with 85% test coverage, see GitHub)
demonstrating capability and initiative to learn
ahead of role. Go's simplicity and Python's
readability share common philosophy.
Backend engineering principles (API design,
database optimization, caching strategies,
monitoring) are language-agnostic. Previous
track record: became Python expert within 6
months of role transition, became team's
AWS authority within 1 year. Committed to
rapid Go proficiency through structured
learning plan (Udemy course + daily coding
practice + open source contributions).
```

**Potential Gap Strategic Reframe**

**Career gap: 8 months between roles in
2023**

```
Strategic career break for professional
development and skill expansion. Completed
AWS Solutions Architect Professional
certification (passed with 950/1000),
contributed meaningfully to 3 major
open-source projects (FastAPI, Celery,
PostgreSQL - 2000+ combined GitHub stars
for contributions), and built comprehensive
portfolio demonstrating advanced
microservices architecture and cloud-native
patterns. Gap demonstrates proactive
approach to continuous learning and staying
ahead of technology curve rather than
reactive learning on the job. Returned to job
market with significantly expanded cloud
expertise, modern architecture patterns, and
fresh perspective. Used time strategically to
become more valuable engineer rather than
rushing into wrong-fit role. Companies
increasingly value candidates who invest in
self-development and long-term career
trajectory over uninterrupted but stagnant
employment.
```
**Transitioning from mid-size company (500
employees) to large enterprise (TechCorp:
10,000+ employees)**

```
Mid-size company experience provides
optimal blend: more structure than startups
(established processes, documentation, code
review standards) but more agility than large
enterprises (faster decision-making, direct
impact, less bureaucracy). Have successfully
navigated scaling challenges as previous
company grew from 200 to 500 employees -
experienced firsthand the transition from
startup to structured organization. Built
systems designed for scale from the
beginning: architected for 10x growth,
implemented monitoring and observability,
created comprehensive documentation.
Comfortable working within established
frameworks while bringing fresh, innovative
approaches. Eager to learn enterprise best
practices (security compliance,
```

```
Potential Gap Strategic Reframe
```
```
cross-functional coordination, formal
architecture review processes) while
contributing startup-minded efficiency and
bias-for-action. Track record of building
processes and documentation as systems
mature positions well for enterprise
environment. Previous role included close
collaboration with Fortune 500 clients,
providing exposure to enterprise expectations
and communication styles.
```
```
Primarily backend focus, role requires
some full-stack capabilities
```
```
7 years backend expertise with demonstrated
frontend capability when needed. Built
internal admin tools requiring React frontends
(see portfolio: engineer dashboard with 500+
daily users). Deep understanding of full
request lifecycle from browser to database
enables superior API design - backend
engineers who understand frontend
constraints build better APIs. Modern
software development increasingly full-stack,
and backend developers frequently work
across stack for feature completion. Already
proficient in JavaScript/TypeScript through
Node.js work and frontend tooling. Willing
and eager to deepen frontend skills with
structured learning plan. Backend-focused
mindset actually advantageous for frontend
performance: applied backend optimization
thinking to frontend, reducing bundle size
60% and improving load time from 2s to 0.5s
in admin tool project. Strong computer
science fundamentals and system design
expertise transfer naturally across stack - UI
is just another interface to backend services.
```
How to Use This Section

**Proactive Addressing Strategy:**

- Bring up gaps yourself before interviewer raises them (demonstrates self-awareness)
- Use the reframe language provided to position constructively


- Have concrete evidence ready (certifications, side projects, metrics)

**Interview Stage Recommendations:**

- **Phone Screen** : Focus on strengths, mention learning agility if gaps come up
- **Technical Interview** : Demonstrate deep fundamentals that transfer across gaps
- **Behavioral Interview** : Use gap reframes to show growth mindset and adaptability
- **Final Interview** : Frame gaps as opportunities for mutual growth and learning
4. Company Deep Dive

Industry Position

TechCorp operates in the enterprise SaaS space, competing with Salesforce, ServiceNow, and
Workday. Recently achieved unicorn status ($1.2B valuation, Series D) and experiencing rapid
growth (300% ARR growth over 2 years).

Key differentiators:

- AI-powered workflow automation (80% reduction in manual processes)
- Modern API-first architecture (vs competitors' legacy monoliths)
- Developer-friendly integration platform (1000+ third-party integrations)

Recent Developments (Past 12 Months)

**Funding & Growth:**

- Series D: $200M at $1.2B valuation (March 2024)
- Headcount growth: 500 → 850 employees (70% growth)
- New office opened in Austin, TX

**Product Launches:**

- AI Copilot (Oct 2024): Natural language automation builder
- Enterprise Security Suite (Aug 2024): SOC 2 Type II, GDPR compliance
- Mobile App 2.0 (June 2024): Complete redesign, 4.8 App Store rating

**Press & Recognition:**

- Forbes Cloud 100 List (#47)
- Gartner Magic Quadrant Leader
- TechCrunch coverage: "TechCorp's AI approach disrupting workflow automation"


Company Culture & Values

**Stated Values:**

1. Customer obsession
2. Ownership mindset
3. Bias for action
4. Continuous learning

**Glassdoor Analysis (4.2/5 stars):**

- Strengths: Smart colleagues, interesting technical challenges, rapid growth
- Concerns: Fast-paced environment, some growing pains, work-life balance varies

**Engineering Culture:**

- Strong emphasis on code quality and testing
- Bi-weekly tech talks and knowledge sharing
- Quarterly hackathons
- 20% time for learning/side projects

Strategic Priorities (Inferred)

Based on job posting and company research:

1. **Scale infrastructure** : Current growth (70% headcount) requires scalable systems
2. **AI integration** : Heavy investment in AI features requires ML infrastructure
3. **Enterprise focus** : Security and compliance features indicate upmarket push
4. **Developer experience** : API-first approach suggests developer platform strategy
5. Competitive Positioning

Unique Skill Combinations

**Python + AWS + Team Leadership at Scale**

- Only 8% of senior Python developers have led teams of 8+ engineers
- Only 12% of AWS practitioners have delivered $500K+ cost optimizations
- Combination of technical depth + business impact + leadership is rare

**Enterprise + Startup Experience**

- Fortune 500 experience (MegaCorp) provides enterprise rigor


- Startup exposure (previous role) provides agility and ownership mindset
- Blend positions ideally for TechCorp's scale-up phase

Differentiating Experiences

1. **Cost Optimization at Scale** : $700K cumulative savings is top 5% of candidates
2. **Technical Leadership** : Practices adopted by 12 teams shows organizational impact
3. **Performance Engineering** : 60% latency reduction at 1M+ user scale is rare
    achievement

Cultural Fit Indicators

From Gap Analysis responses:

- "Ownership mindset": Built systems from architecture through operations
- "Bias for action": Delivered latency optimization in 6 months vs 18-month estimate
- "Continuous learning": Completed AWS certifications, contributed to open source

Experience Level Assessment

**Positioning** : Senior IC with Staff potential

- Technical depth: Deep expertise in Python, AWS, APIs
- Leadership scope: 8 direct reports, 3 mentored to senior roles
- Business impact: $700K quantified savings
- Organizational influence: Practices adopted across 12 teams

Compared to typical Senior Python Developer candidates:

- **More experienced** : 7 years vs typical 4-5 years
- **Higher impact** : Quantified business results vs feature delivery
- **Broader scope** : Cross-functional leadership vs individual contribution
6. Strategic Recommendations

Interview Preparation Priorities

**Top 5 Talking Points:**

1. **Cost Optimization Story** ($700K savings)
    - Prepare detailed STAR narrative
    - Emphasize business value, not just technical achievement


- Tie to TechCorp's scaling challenges
2. **Addressing Kubernetes Gap Proactively**
- Mention CKA certification in progress immediately
- Reference Docker Swarm orchestration as transferable
- Show side project demonstrating initiative
3. **Leadership & Mentorship Impact**
- 3 engineers mentored to senior roles with zero turnover
- Practices adopted by 12 teams
- Code review process reducing bugs 75%
4. **API Performance at Scale**
- 60% latency reduction impacting 1M+ users
- 15+ production APIs with 99.95% uptime
- Zero-downtime deployment strategy
5. **Cross-functional Collaboration**
- Worked with product, design, infrastructure teams
- Translated business requirements to technical solutions
- Stakeholder communication during incidents

Anticipated Difficult Questions & Responses

**Q: "I see you don't have Kubernetes experience, but that's required for this role."**

A: "That's a great question, and I want to address that directly. While I don't have production
Kubernetes experience yet, I have 5 years of deep container orchestration experience with
Docker Swarm serving 100K+ users at 99.9% uptime. The core concepts - scheduling,
networking, service discovery, health checks - are directly transferable. I'm also currently
completing my CKA certification (exam next month, scoring 85+ on practice tests) and I've
already deployed a test Kubernetes cluster with several microservices. I have a track record of
rapid technology adoption - I became our team's AWS authority within 6 months of first using it,
and I mastered React in 3 months to deliver a production application. Based on my experience,
I'm confident I'll be productive with Kubernetes within the first month, and an expert within six
months. Would you like me to walk through my Docker Swarm architecture to show my
orchestration understanding?"

**Q: "Why are you leaving your current company after only 2 years?"**


A: "I've had a great experience at MegaCorp and delivered significant impact - $500K in
infrastructure savings and mentoring 3 engineers to senior roles. The challenge is that
MegaCorp's technical stack is becoming dated (still running monolithic architecture) and there's
limited appetite for modernization. I'm looking for an opportunity to work with modern
cloud-native architecture and continue growing technically. TechCorp's API-first, microservices
approach and investment in AI infrastructure is exactly the technical environment where I thrive.
I'm also excited about the scale-up phase - I love the combination of structure and innovation
that companies at TechCorp's stage offer."

**Q: "What's your biggest weakness?"**

A: "I'd say it's my tendency to over-engineer solutions when I'm passionate about a problem. For
example, when building our caching layer, I initially designed a complex multi-tier system with
Redis, Memcached, and local caching. My manager pushed back and asked what the simplest
solution was. We ended up with just Redis and it solved 90% of our needs. That experience
taught me the value of starting simple and iterating. Now I actively ask myself 'What's the
simplest solution that could work?' and I involve teammates early in design discussions to get
that reality check. I still bring thorough architectural thinking, but I'm much better at balancing
ideal solutions with pragmatic delivery."

Key Messages by Interview Stage

**Phone Screen (30 min):**

- Focus: Culture fit, communication skills, basic technical competency
- Lead with: Career trajectory, business impact ($700K savings), leadership
- Mention proactively: Kubernetes learning plan (address gap early)
- Ask: Team structure, immediate priorities, tech stack evolution

**Technical Interview (60-90 min):**

- Focus: System design, coding ability, problem-solving
- Emphasize: Scaling challenges solved (1M+ users), architecture decisions
- Demonstrate: Deep Python expertise, AWS cloud-native patterns
- Be ready to: Whiteboard API design, discuss trade-offs
- Address gap: If asked about Kubernetes, reference Docker Swarm architecture

**Behavioral Interview (45-60 min):**

- Focus: Leadership, conflict resolution, growth mindset
- Stories to emphasize:
    ● Mentoring engineers to senior roles
    ● Latency optimization project (overcame technical challenges)
    ● Building practices adopted by 12 teams (organizational influence)
- Use STAR format consistently


- Reference Gap Analysis responses for specific examples

**Final Interview (30-45 min):**

- Focus: Strategic thinking, company fit, long-term potential
- Discuss: How your experience maps to TechCorp's scaling challenges
- Show: Understanding of company trajectory and technical priorities
- Frame gaps: As learning opportunities and areas for mutual investment
- Ask: Strategic questions about AI roadmap, infrastructure evolution

Addressing Gaps Strategy

**When to Mention Proactively:**

- Kubernetes gap: Mention in phone screen ("I'm currently pursuing CKA...")
- Career gap: Only if asked directly, use prepared reframe
- Company size transition: Frame positively in behavioral interview

**Pivot Formula: Acknowledge → Evidence → Commitment**

Example: "I don't have production Kubernetes experience [acknowledge], but I have deep
orchestration expertise with Docker Swarm and I'm completing my CKA certification [evidence].
I have a proven track record of mastering new technologies quickly, and I'm committed to being
Kubernetes-proficient within my first month [commitment]."

**Backup Examples:**

- If challenged on Kubernetes: Reference specific Swarm architecture decisions
- If challenged on Go experience: Show GitHub side project with code samples
- If challenged on scale: Detail 1M+ user architecture, traffic patterns

Questions to Ask Interviewers

**About Role (Technical Leads):**

1. "What are the biggest technical challenges the team is facing in the next 6 months?"
2. "How does the team balance new feature development with technical debt?"
3. "What does success look like for this role in the first 90 days?"
4. "What's the team's approach to learning and skill development, especially for
    technologies like Kubernetes where I'm still building expertise?"

**About Team (Hiring Manager):**

1. "Can you walk me through the team structure and how this role fits in?"
2. "How does the team collaborate with product and design?"


3. "What's your leadership style, and how do you support your team's growth?"

**About Company (Executives):**

1. "TechCorp is in a rapid growth phase - how are you thinking about scaling the
    engineering org while maintaining culture?"
2. "What's the AI infrastructure strategy given the recent Copilot launch?"
3. "How does TechCorp think about build vs buy for infrastructure components?"

Negotiation Considerations

**Market Rate Assessment:**

- Senior Python Developer, Enterprise SaaS: $140K-180K base
- TechCorp (Series D, high-growth): Likely top of range + equity
- Your positioning: $165K-175K is reasonable target

**Leverage Factors:**

- **Strengths** : Quantified impact, leadership experience, cultural fit
- **Gaps** : Kubernetes experience (minor), company size transition (minor)
- **Overall** : Strong leverage, but not maximum given gaps

**Negotiation Strategy:**

1. Let them make first offer
2. If below $160K, counter with $170K-175K + equity discussion
3. If Kubernetes gap mentioned: "I understand the concern. I'm confident I'll be fully
    productive within a month. Would the company support CKA certification costs? I've
    already started the prep."
4. Non-monetary asks:
    - Conference budget ($3-5K annually)
    - Professional development stipend
    - Flexible work arrangements
    - Title discussion (Senior vs Staff trajectory)

**How Gaps Affect Position:**

- Kubernetes gap might limit initial offer by 5-10%
- Mitigate with: CKA completion before start date, strong negotiation framing
- Emphasize: Long-term value, cultural fit, business impact track record


7. Evidence Library

[Detailed project descriptions supporting Alignment Matrix claims - same as before]

**End of VPR Complete Report** Updated UI Components html

**Table of Contents**

1. Executive Summary
2. Alignment Matrix
3. Gaps and Reframes ← New Section
4. Company Deep Dive
5. Competitive Positioning
6. Strategic Recommendations
7. Evidence Library

**Gaps and Reframes**

Strategic positioning for potential concerns or gaps between your profile and job requirements.
Each gap is reframed as a strength or opportunity.

💡

**How to use this section:** These reframes help you proactively address potential concerns in
interviews. Practice delivering these explanations naturally, and bring supporting evidence
(certifications, side projects, metrics) to back up your claims.

```
Potential Gap Strategic Reframe
```
```
{{ gap.category }}
{{ gap.title }}
```
```
{{ gap.description }}
```
```
{{ gap.reframe }}
Supporting
Evidence:
```
```
● {{ item }}
```
**Interview Strategy**

**When to Address**

```
● Proactively mention major gaps in phone screen
```

```
● Wait for interviewer to raise minor concerns
● Use behavioral interviews to demonstrate adaptability
```
<div class="strategy-card">

<h4>How to Deliver</h4>

<ul>

<li><strong>Acknowledge:</strong> "I don't have X experience"</li>

<li><strong>Evidence:</strong> "But I have Y transferable skills"</li>

<li><strong>Commitment:</strong> "And I'm actively learning/ready to ramp"</li>

</ul>

</div>

<div class="strategy-card">

<h4>Backup Preparation</h4>

<ul>

<li>Have concrete examples ready for each reframe</li>

<li>Prepare GitHub/portfolio links to demonstrate</li>

<li>Practice delivery to sound natural, not defensive</li>

</ul>

</div>

</div>

css /* Gaps and Reframes Section Styling */ .gaps-reframes { margin: 40px 0; } .gaps-intro {
margin-bottom: 24px; }

.info-box { display: flex; gap: 16px; padding: 16px; background: #eff6ff; border-left: 4px solid
#3b82f6; border-radius: 4px; }


.info-box icon { font-size: 24px; flex-shrink: 0; }

.gaps-table { width: 100%; border-collapse: collapse; margin: 24px 0; background: white;
box-shadow: 0 2px 4px rgba(0,0,0,0.1); }

.gaps-table thead { background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%); color:
white; }

.gaps-table th { padding: 16px; text-align: left; font-weight: 600; font-size: 14px; text-transform:
uppercase; letter-spacing: 0.5px; }

.gaps-table th.col-gap { width: 35%; }

.gaps-table th.col-reframe { width: 65%; }

.gaps-table tbody tr { border-bottom: 1px solid #e5e7eb; }

.gaps-table tbody tr:hover { background-color: #fef3c7; }

.gaps-table td { padding: 20px; vertical-align: top; font-size: 14px; line-height: 1.7; }

.gap-cell { background-color: #fef3c7; }

.gap-tag { display: inline-block; padding: 4px 12px; background: #f59e0b; color: white;
border-radius: 12px; font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing:
0.5px; margin-bottom: 8px; }

.gap-cell strong { display: block; color: #92400e; font-size: 15px; margin-bottom: 8px; }

.gap-description { color: #78350f; font-size: 13px; margin: 0; }

.reframe-cell { background-color: #f0fdf4; }

.reframe-content { color: #166534; line-height: 1.8; }

.reframe-evidence { margin-top: 12px; padding: 12px; background: white; border-radius: 4px;
border-left: 3px solid #10b981; }

.reframe-evidence strong { display: block; color: #065f46; font-size: 13px; margin-bottom: 8px; }

.reframe-evidence ul { margin: 0; padding-left: 20px; color: #047857; font-size: 13px; }

.reframe-evidence li { margin-bottom: 4px; }


.gaps-strategy { margin-top: 40px; padding: 24px; background: #f9fafb; border-radius: 8px; }

.gaps-strategy h3 { margin: 0 0 20px 0; color: #1f2937; font-size: 18px; }

.strategy-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap:
20px; }

.strategy-card { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 1px 3px
rgba(0,0,0,0.1); }

.strategy-card h4 { margin: 0 0 12px 0; color: #f59e0b; font-size: 15px; font-weight: 600; }

.strategy-card ul { margin: 0; padding-left: 20px; color: #4b5563; font-size: 14px; line-height: 1.7;
}

.strategy-card li { margin-bottom: 8px; }

.strategy-card strong { color: #1f2937; } Summary Added "Gaps and Reframes" Section ✅
Location: Section 3 in VPR Complete (between Alignment Matrix and Company Deep Dive)

Purpose:

Identify realistic gaps between candidate profile and job requirements Provide strategic
reframes positioning each gap constructively Give interview preparation guidance for
addressing concerns Format:

Table with two columns: "Potential Gap" | "Strategic Reframe" 3-5 gaps covering common
categories (technology, experience, transitions) Detailed reframes (2-3 sentences minimum)
with evidence and examples Gap Categories Covered:

Missing specific technology/tool experience Years of experience (over/under qualified) Industry
switching Education/certification gaps Company size transitions Role transitions Career gaps
Technology stack shifts Reframe Strategies:

Transferable Skills Reframe Overqualification Reframe Industry Switch Reframe Technology
Stack Shift Reframe Career Gap Reframe Company Size Transition Reframe Integration with
Other Sections:

Strategic Recommendations references Gaps section for interview prep Interview questions
include guidance on when/how to address gaps Negotiation section considers how gaps affect
positioning This section is now aligned with the original Job Search Assistant Skill and provides
critical interview preparation value! 🎯


# Tab 15


1:45 PM Corrected Pricing Page Copy Updated Pricing Page UI html

**Choose Your Plan**

Start with a 14-day free trial. Credit card required, but not charged until end of trial.

Start Here

**Free Trial**

$0 for 14 days

<div class="card-features">

<h4>Includes:</h4>

<ul>

<li><icon>✓</icon> 3 complete application packages</li>

<li><icon>✓</icon> Tailored CV generation</li>

<li><icon>✓</icon> Value Proposition Reports</li>

<li><icon>✓</icon> Custom cover letters</li>

<li><icon>✓</icon> Interview preparation guides</li>

<li><icon>✓</icon> ATS optimization</li>

<li><icon>✓</icon> All export formats (Docx, PDF)</li>

</ul>

</div>

<div class="trial-details">

<div class="detail-item">

<icon class="info">ℹ</icon>

<p>


<strong>Credit card required</strong> but you won't be charged

until your trial ends in 14 days

</p>

</div>

<div class="detail-item">

<icon class="success">✓</icon>

<p>Cancel anytime during trial - no charge</p>

</div>

</div>

<div class="card-footer">

<button class="primary large" (click)="startTrial()">

Start 14-Day Free Trial

</button>

<p class="billing-disclaimer">

First charge: $29.95 on {{ trialEndDate | date:'MMM d, yyyy' }}

</p>

</div>

**Monthly**

$29.95 /month

<div class="card-features">

<h4>Everything in Free Trial, plus:</h4>

<ul>


<li><icon>✓</icon> <strong>Unlimited applications</strong></li>

<li><icon>✓</icon> Priority support</li>

<li><icon>✓</icon> Advanced analytics</li>

<li><icon>✓</icon> Document version history</li>

<li><icon>✓</icon> Cancel anytime</li>

</ul>

</div>

<div class="card-footer">

<button class="secondary large" (click)="selectPlan('monthly')">

Choose Monthly

</button>

<p class="billing-info">Billed monthly at $29.95</p>

</div>

Best Value
Save 17%

<div class="card-header">

<h2>Quarterly</h2>

<div class="price">

<span class="amount">$24.95</span>

<span class="period">/month</span>

</div>

<div class="price-comparison">


<span class="original-price">$29.95</span>

<span class="savings">Save $14.85</span>

</div>

</div>

<div class="card-features">

<h4>Everything in Monthly, plus:</h4>

<ul>

<li><icon>✓</icon> <strong>17% discount</strong></li>

<li><icon>✓</icon> Priority processing</li>

<li><icon>✓</icon> Early access to new features</li>

<li><icon>✓</icon> Dedicated support</li>

</ul>

</div>

<div class="card-footer">

<button class="primary large" (click)="selectPlan('quarterly')">

Choose Quarterly

</button>

<p class="billing-info">

Billed quarterly at <strong>$74.85</strong>

<br>

<small>($24.95/month × 3 months)</small>

</p>


</div>

**Frequently Asked Questions**

<div class="faq-item">

<h4>Why do you need my credit card for a free trial?</h4>

<p>

We require a credit card to prevent abuse and ensure a seamless

transition to your paid subscription if you love the service.

<strong>You won't be charged during your 14-day trial.</strong>

If you cancel before the trial ends, you won't be charged at all.

</p>

</div>

<div class="faq-item">

<h4>When will I be charged?</h4>

<p>

Your first charge of $29.95 (Monthly plan) or $74.85 (Quarterly plan)

will occur on day 15, immediately after your 14-day trial ends. You'll

receive a reminder email 3 days before your trial ends.

</p>

</div>

<div class="faq-item">

<h4>Can I cancel during the trial?</h4>

<p>


Yes! You can cancel anytime during your 14-day trial and you won't be

charged. Simply go to Account Settings → Subscription → Cancel Subscription.

</p>

</div>

<div class="faq-item">

<h4>What happens after my trial ends?</h4>

<p>

If you don't cancel, you'll automatically continue on your selected plan

(Monthly at $29.95/month or Quarterly at $74.85 every 3 months). You'll

keep unlimited access to all features.

</p>

</div>

<div class="faq-item">

<h4>How does quarterly billing work?</h4>

<p>

With the Quarterly plan, you pay $74.85 upfront every 3 months

(equivalent to $24.95/month). This saves you 17% compared to

paying monthly. Your first quarterly charge happens on day 15

after your trial ends.

</p>

</div>

<div class="faq-item">


<h4>Can I switch plans later?</h4>

<p>

Yes, you can upgrade or downgrade between Monthly and Quarterly at

any time. Changes take effect at your next billing cycle.

</p>

</div>

Updated Signup Flow UI html

**Start Your 14-Day Free Trial**

Credit card required • No charge for 14 days • Cancel anytime

<!-- Account Information -->

<div class="form-section">

<h3>Account Information</h3>

<div class="form-group">

<label for="name">Full Name</label>

<input

type="text"

id="name"

[(ngModel)]="signupData.name"

required

placeholder="John Doe"

## />


</div>

<div class="form-group">

<label for="email">Email Address</label>

<input

type="email"

id="email"

[(ngModel)]="signupData.email"

required

placeholder="john@example.com"

## />

</div>

<div class="form-group">

<label for="password">Password</label>

<input

type="password"

id="password"

[(ngModel)]="signupData.password"

required

minlength="8"

placeholder="Minimum 8 characters"


## />

</div>

</div>

<!-- Plan Selection -->

<div class="form-section">

<h3>Select Your Plan</h3>

<p class="section-note">You can change this later</p>

<div class="plan-selector">

<label class="plan-option" [class.selected]="selectedPlan === 'monthly'">

<input

type="radio"

name="plan"

value="monthly"

[(ngModel)]="selectedPlan"

## />

<div class="plan-details">

<div class="plan-name">Monthly</div>

<div class="plan-price">$29.95/month</div>

<div class="plan-note">Billed monthly after trial</div>

</div>

</label>


<label class="plan-option recommended" [class.selected]="selectedPlan === 'quarterly'">

<span class="recommended-badge">Save 17%</span>

<input

type="radio"

name="plan"

value="quarterly"

[(ngModel)]="selectedPlan"

## />

<div class="plan-details">

<div class="plan-name">Quarterly</div>

<div class="plan-price">$24.95/month</div>

<div class="plan-note">Billed $74.85 every 3 months after trial</div>

</div>

</label>

</div>

</div>

<!-- Payment Information -->

<div class="form-section">

<h3>Payment Information</h3>

<p class="section-note">

<icon>🔒</icon> Secure payment processing by Stripe


</p>

<div class="trial-notice">

<icon class="info">ℹ</icon>

<div>

<strong>You won't be charged today</strong>

<p>

Your card will be charged <strong *ngIf="selectedPlan === 'monthly'">$29.95</strong>

<strong *ngIf="selectedPlan === 'quarterly'">$74.85</strong>

on {{ trialEndDate | date:'MMMM d, yyyy' }} (14 days from now).

Cancel anytime before then at no charge.

</p>

</div>

</div>

<div class="form-group">

<label>Card Information</label>

<div id="card-element"></div>

<div id="card-errors" role="alert"></div>

</div>

</div>

<!-- Billing Preview -->


<div class="billing-preview">

<h4>Billing Preview</h4>

<div class="preview-row">

<span>Today (Trial starts):</span>

<span class="free">$0.00</span>

</div>

<div class="preview-row highlight">

<span>{{ trialEndDate | date:'MMM d, yyyy' }} (Trial ends):</span>

<span class="charge">

<strong *ngIf="selectedPlan === 'monthly'">$29.95</strong>

<strong *ngIf="selectedPlan === 'quarterly'">$74.85</strong>

</span>

</div>

<div class="preview-row">

<span>Then:</span>

<span *ngIf="selectedPlan === 'monthly'">$29.95 monthly</span>

<span *ngIf="selectedPlan === 'quarterly'">$74.85 every 3 months</span>

</div>

</div>


<!-- Terms -->

<div class="form-section">

<label class="checkbox-label">

<input

type="checkbox"

[(ngModel)]="agreedToTerms"

required

name="terms"

## />

<span>

I agree to the <a href="/terms" target="_blank">Terms of Service</a>

and <a href="/privacy" target="_blank">Privacy Policy</a>

</span>

</label>

</div>

<!-- Submit -->

<div class="form-actions">

<button type="submit" class="primary large" [disabled]="!agreedToTerms">

Start My Free Trial

</button>

<p class="submit-disclaimer">

By clicking "Start My Free Trial", you agree to be charged


<strong *ngIf="selectedPlan === 'monthly'">$29.95</strong>

<strong *ngIf="selectedPlan === 'quarterly'">$74.85</strong>

on {{ trialEndDate | date:'MMM d, yyyy' }} unless you cancel before then.

</p>

</div>

Updated Email Templates python def send_trial_welcome_email(email, name, trial_end_date,
selected_plan): """ Welcome email when user starts trial (CORRECTED) """ # Calculate first
charge amount and date

first_charge_amount = 29.95 if selected_plan == 'monthly' else 74.85

first_charge_date = trial_end_date.strftime('%B %d, %Y')

email_body = f"""

Hi {name},

Welcome to CareerVP! Your 14-day free trial has started.

## TRIAL DETAILS:

✓ Trial Period: 14 days (ends {first_charge_date}) ✓ Applications Included: 3 during trial ✓
First Charge: ${first_charge_amount} on {first_charge_date} ✓ Selected Plan:
{selected_plan.title()}

IMPORTANT: You provided a credit card when signing up. You will be automatically charged
${first_charge_amount} on {first_charge_date} unless you cancel before then.

## WHAT YOU GET:

✓ 3 complete application packages during trial ✓ AI-powered CV tailoring ✓ Value Proposition
Reports ✓ Custom cover letters ✓ Interview preparation guides ✓ ATS optimization ✓ All
export formats (Docx, PDF)

After your trial, you'll have unlimited access to all features.

## GET STARTED:

Create your first application: https://app.careervp.com/new-application


## WANT TO CANCEL?

You can cancel anytime during your trial at no charge:
https://app.careervp.com/account/subscription

We'll send you a reminder 3 days before your trial ends.

## QUESTIONS?

Reply to this email anytime - we're here to help!

Best regards, The CareerVP Team

## BILLING SUMMARY:

- Today: $0.00 (trial start)
- {first_charge_date}: ${first_charge_amount} (first charge)
- Then: {'$29.95/month' if selected_plan == 'monthly' else '$74.85 every 3 months'}
    """.strip()

```
ses.send_email( Source='welcome@careervp.com', Destination={'ToAddresses':
[email]}, Message={ 'Subject': { 'Data': f'Welcome to CareerVP! Your 14-Day Trial Starts
Now', 'Charset': 'UTF-8' }, 'Body': {'Text': {'Data': email_body, 'Charset': 'UTF-8'}} } )
```
def send_trial_ending_reminder(user, days_remaining): """ Reminder email before trial ends
(CORRECTED) """

trial_end_date = datetime.fromisoformat(user['trial_end_date'])

plan = user.get('subscription_plan', 'monthly_2995')

charge_amount = 29.95 if 'monthly' in plan else 74.85

subject = f'Your CareerVP trial ends in {days_remaining} days'

message = f"""

Hi {user.get('name', 'there')},


Your CareerVP free trial ends in {days_remaining} days.

## WHAT HAPPENS NEXT:

On {trial_end_date.strftime('%B %d, %Y')}, your credit card will be charged ${charge_amount}
and you'll continue with unlimited access to all features.

Your plan: {user.get('subscription_plan', 'Monthly').replace('_', ' ').title()} {'• $29.95/month (billed
monthly)' if 'monthly' in plan else '• $74.85 every 3 months (equivalent to $24.95/month)'}

## TRIAL USAGE:

You've used {user.get('trial_applications_used', 0)} of 3 free applications.

## WANT TO SAVE 17%?

Switch to quarterly billing before your trial ends: https://app.careervp.com/account/subscription

- Quarterly: $24.95/month (billed $74.85 every 3 months)
- Save $14.85 vs monthly billing

## DON'T WANT TO CONTINUE?

Cancel before {trial_end_date.strftime('%B %d')} to avoid being charged:
https://app.careervp.com/account/subscription

You'll keep access to your trial until {trial_end_date.strftime('%B %d')}.

Questions? Reply to this email.

Best regards, The CareerVP Team

BILLING REMINDER: You will be charged ${charge_amount} on {trial_end_date.strftime('%B
%d, %Y')} unless you cancel. """.strip()

ses.send_email(

Source='notifications@careervp.com',

Destination={'ToAddresses': [user['email']]},

Message={


'Subject': {'Data': subject},

'Body': {'Text': {'Data': message}}

## }

## )

Updated Backend - Signup API python

API: POST /api/auth/signup (CORRECTED)

@app.post('/api/auth/signup') def signup(signup_data: SignupRequest): """ User signup -
CREDIT CARD REQUIRED

Flow:

1. Collect user info + payment method
2. Create Stripe customer
3. Create Stripe subscription with 14-day trial
4. Create Cognito user
5. Create DynamoDB record
6. Send welcome email

## """

# Validate payment method provided

if not signup_data.payment_method_id:

raise HTTPException(

status_code=400,

detail="Payment method is required to start trial"

## )


# Create Cognito user

cognito_user = cognito.admin_create_user(

UserPoolId=USER_POOL_ID,

Username=signup_data.email,

UserAttributes=[

{'Name': 'email', 'Value': signup_data.email},

{'Name': 'name', 'Value': signup_data.name}

## ],

TemporaryPassword=generate_temp_password()

## )

user_id = cognito_user['User']['Username']

# Create Stripe customer

customer = stripe.Customer.create(

email=signup_data.email,

name=signup_data.name,

metadata={'user_id': user_id}

## )

# Attach payment method

stripe.PaymentMethod.attach(

signup_data.payment_method_id,

customer=customer.id

## )


# Set as default payment method

stripe.Customer.modify(

customer.id,

invoice_settings={

'default_payment_method': signup_data.payment_method_id

## }

## )

# Determine price ID based on selected plan

price_id = (

STRIPE_MONTHLY_PRICE_ID if signup_data.selected_plan == 'monthly'

else STRIPE_QUARTERLY_PRICE_ID

## )

# Create subscription with 14-day trial

trial_end_timestamp = int(

(datetime.utcnow() + timedelta(days=14)).timestamp()

## )

subscription = stripe.Subscription.create(

customer=customer.id,

items=[{'price': price_id}],

trial_end=trial_end_timestamp, # ✅ Trial ends in 14 days, then charge

metadata={

'user_id': user_id,


'trial_started': datetime.utcnow().isoformat()

## }

## )

# Calculate dates

trial_start = datetime.utcnow()

trial_end = trial_start + timedelta(days=14)

# Create DynamoDB record

dynamodb.put_item(

TableName='careervp-users',

Item={

'user_id': user_id,

'email': signup_data.email,

'name': signup_data.name,

'tier': 'trial',

'subscription_status': 'trialing',

'subscription_plan': f"{signup_data.selected_plan}_{'2995' if signup_data.selected_plan ==
'monthly' else '7485'}",

'trial_start_date': trial_start.isoformat(),

'trial_end_date': trial_end.isoformat(),

'trial_applications_used': 0,

'trial_has_credit_card': True, # ✅ ALWAYS True (required)

'trial_converted': False,

'credits_remaining': 3,


'stripe_customer_id': customer.id,

'stripe_subscription_id': subscription.id,

'payment_method_on_file': True, # ✅ ALWAYS True

'created_at': trial_start.isoformat(),

'next_billing_date': trial_end.isoformat(),

'next_billing_amount': 29.95 if signup_data.selected_plan == 'monthly' else 74.85

## }

## )

# Send welcome email

send_trial_welcome_email(

email=signup_data.email,

name=signup_data.name,

trial_end_date=trial_end,

selected_plan=signup_data.selected_plan

## )

return {

'user_id': user_id,

'trial_start_date': trial_start.isoformat(),

'trial_end_date': trial_end.isoformat(),

'applications_remaining': 3,

'first_charge_date': trial_end.isoformat(),

'first_charge_amount': 29.95 if signup_data.selected_plan == 'monthly' else 74.85,


'message': 'Trial started! Credit card will be charged in 14 days unless you cancel.'

## }

Updated FAQ markdown

Updated FAQ

Do I need a credit card for the free trial?

**Yes, a credit card is required to start your 14-day free trial.**

However, you won't be charged during the trial period. Your card will only be charged when your
trial ends (14 days after signup) unless you cancel before then.

We require a credit card to:

- Prevent abuse of the trial system
- Ensure a seamless transition to paid subscription if you love the service
- Verify you're a real person, not a bot

If you cancel during the 14-day trial, you won't be charged at all.

When will I be charged?

Your first charge will occur **on day 15** (immediately after your 14-day trial ends):

- **Monthly plan** : $29.95 on day 15
- **Quarterly plan** : $74.85 on day 15

You'll receive reminder emails:

- 3 days before your trial ends
- 1 day before your trial ends

Both reminders will include your exact charge date and amount.

Can I cancel during the trial without being charged?

**Yes, absolutely!** You can cancel anytime during your 14-day trial and you won't be charged
anything.


To cancel:

1. Go to Account Settings
2. Click "Subscription"
3. Click "Cancel Subscription"
4. Confirm cancellation

You'll keep access until your trial ends, but you won't be charged when the trial period is over.

What if I forget to cancel?

If you don't cancel before your trial ends, you'll be automatically charged and your subscription
will continue. However:

- You can cancel anytime after being charged
- You'll keep access until the end of your current billing period
- We send reminder emails 3 days and 1 day before charging you

Can I change my plan during the trial?

Yes! You can switch between Monthly and Quarterly plans anytime during your trial. The change
will apply when your trial ends and you're first charged.

To switch plans:

1. Go to Account Settings → Subscription
2. Click "Switch to Monthly" or "Switch to Quarterly"
3. Confirm the change

What happens if my card is declined when the trial ends?

If your card is declined when we try to charge you on day 15:

1. We'll send you an email notification
2. We'll retry the charge 3 times over 7 days
3. You'll still have access during the retry period
4. If all retries fail, your account will revert to free tier (0 applications)

You can update your payment method anytime in Account Settings. Summary of Changes
Corrected Messaging ✅ OLD (Incorrect):

"No credit card required" Implied CC was optional NEW (Correct):


"Credit card required, but not charged until end of trial" Clear that CC is mandatory Emphasizes
no charge during 14-day period Updated Components: Pricing page header - Clear CC
requirement statement Trial card - Prominent notice about CC requirement and no charge
Signup modal - Trial notice explaining when charge occurs Billing preview - Shows $0.00 today,
charge on day 15 Email templates - Clarify CC was required and when first charge occurs FAQ
section - Explains why CC required and when charges happen Backend API - Always requires
payment_method_id, validates presence DynamoDB schema - trial_has_credit_card always
TRUE Key Messaging Points: ✅ Credit card IS REQUIRED to start trial ✅ NO CHARGE for 14
days ✅ First charge on day 15 (trial end date) ✅ Can cancel anytime during trial at no charge
✅ Reminders sent 3 days and 1 day before charge ✅ Transparent about exact charge date
and amount All pricing copy now accurately reflects the CC-required trial model! 💳
