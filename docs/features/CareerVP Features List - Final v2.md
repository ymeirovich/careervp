# CAREERVP JOB SEARCH ASSISTANT

## FINAL Technical Features List & Specifications

### Version 1.0 \- Production Ready Documentation

**Document Purpose:** Complete technical specifications for CareerVP SaaS platform development
**Last Updated:** January 22, 2026
**Status:** APPROVED \- Ready for Development

---

## EXECUTIVE SUMMARY

**Project:** CareerVP \- AI-Powered Job Application Assistant
**Architecture:** Serverless AWS (Lambda \+ DynamoDB \+ S3)
**AI Models:** Hybrid Anthropic Claude (Sonnet 4.5 \+ Haiku 4.5)
**Target Launch:** Q2 2026 (3-4 month development cycle)
**Total Features:** 48 features (V1: 36 features | V2: 12 features)
**Cost per Application:** $0.058
**Target Profit Margin:** 95%+

---

## TABLE OF CONTENTS

1. [Feature Priority Framework](#1-feature-priority-framework)
2. [Core Features \- P0 (Critical Path)](#2-core-features-p0-critical-path)
3. [Enhanced Features \- P1 (High Value)](#3-enhanced-features-p1-high-value)
4. [Supporting Features \- P2 (Nice to Have)](#4-supporting-features-p2-nice-to-have)
5. [V1.1 Features (Post-Launch Enhancements)](#5-v11-features-post-launch-enhancements)
6. [V2 Roadmap Features (Future)](#6-v2-roadmap-features-future)
7. [Technical Architecture Overview](#7-technical-architecture-overview)
8. [Development Sprints & Timeline](#8-development-sprints-timeline)
9. [Acceptance Criteria & Testing](#9-acceptance-criteria-testing)
10. [Cost Model & Performance Targets](#10-cost-model-performance-targets)

---

## 1\. FEATURE PRIORITY FRAMEWORK

### 1.1 Priority Definitions

P0 (Critical \- Must Have for MVP):

  Definition: Core functionality without which the product cannot launch

  Impact: Blocks launch if missing

  User Impact: Cannot complete primary user journey

  Development Priority: Sprint 0-6



P1 (High \- Strong Value Add):

  Definition: Significantly enhances value proposition

  Impact: Reduces competitive advantage if missing

  User Impact: Reduces user success rate materially

  Development Priority: Sprint 5-7



P2 (Medium \- Nice to Have):

  Definition: Improves user experience but not critical

  Impact: Can be added post-launch

  User Impact: Convenience features

  Development Priority: Sprint 7-8 or post-launch



V1.1 (Post-Launch Enhancements):

  Definition: Features planned for first major update

  Impact: Improves retention and engagement

  User Impact: Enhanced experience

  Development Priority: 1-2 months post-launch



V2 (Future Roadmap):

  Definition: Not included in V1 scope

  Impact: Post-launch enhancements

  User Impact: Future value additions

  Development Priority: 6-12 months post-launch

### 1.2 Feature Distribution

Total V1 Features: 36

├─ P0 (Critical): 18 features (50%)

├─ P1 (High): 12 features (33%)

└─ P2 (Medium): 6 features (17%)

V1.1 Features: 4 features

V2 Features: 12 features (deferred)

Total Documented: 52 features

---

## 2\. CORE FEATURES \- P0 (CRITICAL PATH)

### 2.1 User Authentication & Authorization

#### F-AUTH-001: User Registration

**Priority:** P0
**Sprint:** Sprint 1
**Dependencies:** AWS Cognito setup

**Description:** Complete user registration workflow with email verification, password creation, and trial activation.

**Functional Requirements:**

1. Registration form with validation:

   - Email address (required, valid format, unique)
   - Password (required, min 8 chars, 1 uppercase, 1 lowercase, 1 number, 1 special char)
   - Confirm password (must match)
   - First name (required, 2-50 chars)
   - Last name (required, 2-50 chars)
   - Accept Terms of Service (required checkbox)
   - Accept Privacy Policy (required checkbox)



2. Email verification:

   - Send verification email via AWS SES
   - Verification link expires in 24 hours
   - Resend verification option
   - Email verified flag in user profile



3. Trial activation:

   - Automatically activate 14-day trial on email verification
   - Set credits\_remaining \= 3 for free tier
   - Send welcome email with getting started guide

**Technical Implementation:**

Lambda Function: auth-handler

Runtime: Python 3.11

Memory: 256MB

Timeout: 10s

Trigger: API Gateway POST /api/auth/register

DynamoDB Table: careervp-users

Attributes:

  userId: String (PK)

  email: String (unique, GSI)

  passwordHash: String (bcrypt)

  firstName: String

  lastName: String

  tier: String (free\_trial, monthly, 3\_month, 6\_month)

  credits\_remaining: Number (only for free tier)

  trial\_start\_date: String (ISO 8601\)

  trial\_end\_date: String (ISO 8601\)

  email\_verified: Boolean

  created\_at: String (ISO 8601\)

  updated\_at: String (ISO 8601\)

**Acceptance Criteria:**

- ✅ User can register with valid email and password
- ✅ Duplicate email registration shows clear error message
- ✅ Weak passwords are rejected with specific requirements shown
- ✅ Verification email arrives within 60 seconds
- ✅ Clicking verification link activates account and redirects to login
- ✅ Expired verification links show error with resend option
- ✅ Trial period is exactly 14 days from email verification
- ✅ Free tier users see credits\_remaining \= 3 after registration

**Error Handling:**

- Email already exists: "This email is already registered. Please log in or use password reset."
- Invalid email format: "Please enter a valid email address."
- Weak password: "Password must be at least 8 characters with 1 uppercase, 1 lowercase, 1 number, and 1 special character."
- Terms not accepted: "You must accept the Terms of Service to continue."

**UI Components:**

- Registration form page
- Email verification sent confirmation page
- Email verification success page
- Toast notifications for errors

**Testing:**

- Unit: Password validation logic
- Integration: Cognito user creation and email sending
- E2E: Complete registration flow from form to verified account

---

#### F-AUTH-002: User Login

**Priority:** P0
**Sprint:** Sprint 1
**Dependencies:** F-AUTH-001 (User Registration)

**Description:** Secure user login with JWT token generation and refresh token management.

**Functional Requirements:**

1. Login form:

   - Email address (required)
   - Password (required)
   - Remember me checkbox (optional)
   - Forgot password link



2. Authentication flow:

   - Verify email and password with Cognito
   - Generate JWT access token (1 hour expiry)
   - Generate refresh token (30 days expiry)
   - Store tokens securely in httpOnly cookies
   - Redirect to dashboard on success



3. Session management:

   - Automatic token refresh when access token expires
   - Logout invalidates all tokens
   - Multiple device support
   - Track last login timestamp

**Technical Implementation:**

Lambda Function: auth-handler

Endpoint: POST /api/auth/login

Request Body:

  email: string

  password: string

  remember\_me: boolean

Response:

  access\_token: string (JWT, 1h expiry)

  refresh\_token: string (30d expiry)

  user:

    userId: string

    email: string

    firstName: string

    lastName: string

    tier: string

    credits\_remaining: number (if free tier)

**Acceptance Criteria:**

- ✅ Valid credentials grant access with correct tokens
- ✅ Invalid credentials show "Invalid email or password" error
- ✅ Unverified email shows "Please verify your email" with resend link
- ✅ Access token expires after 1 hour
- ✅ Refresh token auto-renews access token seamlessly
- ✅ "Remember me" extends session to 30 days
- ✅ Last login timestamp updates on successful login
- ✅ Rate limiting: max 5 failed attempts per 15 minutes per IP

**Security:**

- Password never sent in plain text (HTTPS only)
- Tokens stored in httpOnly, secure, sameSite cookies
- CSRF protection enabled
- Brute force protection with exponential backoff
- Failed login attempts logged to CloudWatch

---

#### F-AUTH-003: Password Reset

**Priority:** P0
**Sprint:** Sprint 1
**Dependencies:** F-AUTH-001 (User Registration)

**Description:** Self-service password reset flow with email verification.

**Functional Requirements:**

1. Request password reset:

   - User enters email address
   - System sends reset link via email
   - Reset link expires in 1 hour
   - Rate limit: 3 reset requests per hour per email



2. Reset password:

   - User clicks link in email
   - Enter new password (same validation as registration)
   - Confirm new password
   - Invalidate all existing sessions on success



3. Security:

   - Reset token is single-use only
   - Token invalidated after password change
   - Email sent even for non-existent accounts (security)
   - Log all password reset attempts

**Technical Implementation:**

Lambda Function: auth-handler

Endpoints:

  POST /api/auth/forgot-password

  POST /api/auth/reset-password

Reset Token Storage (DynamoDB):

  PK: RESET\_TOKEN\#{token}

  SK: EMAIL\#{email}

  TTL: 3600 (1 hour)

**Acceptance Criteria:**

- ✅ Reset email arrives within 60 seconds
- ✅ Reset link expires after exactly 1 hour
- ✅ Used reset tokens cannot be reused
- ✅ Invalid reset tokens show clear error message
- ✅ Password successfully changed with valid token
- ✅ All existing sessions invalidated after password change
- ✅ Confirmation email sent after successful password change

---

### 2.2 CV Management

#### F-CV-001: CV Upload

**Priority:** P0
**Sprint:** Sprint 2
**Dependencies:** F-AUTH-002 (User Login)

**Description:** Allow users to upload their CV in PDF or DOCX format with validation and text extraction.

**Functional Requirements:**

1. File upload:

   - Supported formats: PDF, DOCX
   - Max file size: 5MB
   - **Max pages: 3 pages** (show error if exceeded)
   - Drag-and-drop or file picker
   - Upload progress indicator



2. Validation:

   - Check file format and size
   - **Reject CVs longer than 3 pages with error: "CVs must be 3 pages or less for optimal ATS compatibility"**
   - Scan for malware (AWS S3 malware protection)
   - Extract text content using Lambda



3. Storage:

   - Store original file in S3 bucket: careervp-cv-uploads-{env}
   - Extract and store text in DynamoDB
   - Generate unique cvId
   - Set first uploaded CV as primary

**Technical Implementation:**

Lambda Function: cv-upload-handler

Runtime: Python 3.11

Memory: 512MB

Timeout: 30s

Trigger: API Gateway POST /api/cvs/upload

Process Flow:

  1\. Validate file format and size

  2\. Count pages (PDF: PyPDF2, DOCX: python-docx)

  3\. Reject if \> 3 pages

  4\. Upload to S3 with userId prefix

  5\. Trigger cv-parser Lambda (async)

  6\. Return cvId and upload confirmation

S3 Bucket: careervp-cv-uploads-prod

Structure: {userId}/cvs/{cvId}.{ext}

Encryption: SSE-S3

Lifecycle:

  \- 90 days: Move to Infrequent Access

  \- 365 days: Move to Glacier

**Acceptance Criteria:**

- ✅ PDF and DOCX files upload successfully
- ✅ Files over 5MB rejected with clear error
- ✅ **CVs over 3 pages rejected with error message**
- ✅ Unsupported formats (e.g., .txt, .png) rejected
- ✅ Upload progress shown during upload
- ✅ Success message shown after upload
- ✅ First uploaded CV automatically set as primary
- ✅ Original file accessible for download
- ✅ Text extraction completes within 30 seconds

**Error Handling:**

- File too large: "CV must be under 5MB. Please compress or reduce content."
- **Too many pages: "CVs must be 3 pages or less for optimal ATS compatibility. Please condense your CV."**
- Invalid format: "Please upload a PDF or DOCX file."
- Upload failed: "Upload failed. Please try again."

---

#### F-CV-002: CV Text Extraction & Parsing

**Priority:** P0
**Sprint:** Sprint 2
**Dependencies:** F-CV-001 (CV Upload)

**Description:** Extract text from uploaded CV and parse key information using Claude Haiku.

**Functional Requirements:**

1. Text extraction:

   - Extract plain text from PDF (pdfplumber)
   - Extract text from DOCX (python-docx)
   - Preserve basic formatting (bullets, sections)
   - Handle multi-column layouts



2. AI parsing (Claude Haiku):

   - Extract candidate name, email, phone
   - Extract work experience with dates
   - Extract education history
   - Extract skills list
   - Extract certifications
   - Store structured JSON in DynamoDB



3. Fact verification:

   - Verify extracted email matches user account email
   - Flag any date inconsistencies
   - Ensure all dates are in correct format (MM/YYYY)

**Technical Implementation:**

Lambda Function: cv-parser

Runtime: Python 3.11

Memory: 512MB

Timeout: 30s

Trigger: S3 event (cv-upload)

AI Model: Claude Haiku 4.5

Prompt Template:

  "Extract the following information from this CV:

   1\. Candidate name

   2\. Contact info (email, phone)

   3\. Work experience (company, title, dates, responsibilities)

   4\. Education (school, degree, dates)

   5\. Skills (technical, soft)

   6\. Certifications



   Return as JSON with date format: MM/YYYY"

DynamoDB Table: careervp-cvs

Attributes:

  userId: String (PK)

  cvId: String (SK)

  cv\_name: String

  s3\_key: String

  is\_primary: Boolean

  extracted\_text: String

  parsed\_facts: JSON

    \- name: String

    \- email: String

    \- phone: String

    \- work\_experience: Array

    \- education: Array

    \- skills: Array

    \- certifications: Array

  created\_at: String

  updated\_at: String

**Acceptance Criteria:**

- ✅ Text extracted from PDF within 15 seconds
- ✅ Text extracted from DOCX within 10 seconds
- ✅ Candidate name extracted correctly (95% accuracy)
- ✅ Contact info extracted correctly (90% accuracy)
- ✅ Work experience dates extracted in MM/YYYY format
- ✅ Education history extracted correctly (90% accuracy)
- ✅ Skills list extracted (80% accuracy)
- ✅ Parsing errors logged to CloudWatch
- ✅ User notified when parsing complete

**AI Cost:**

- Haiku input: \~2,000 tokens (CV text)
- Haiku output: \~500 tokens (JSON)
- Cost: \~$0.001 per CV parse

---

#### F-CV-003: CV Management (View, Edit, Delete)

**Priority:** P0
**Sprint:** Sprint 2
**Dependencies:** F-CV-002 (CV Parsing)

**Description:** Allow users to view, edit metadata, set primary CV, and delete CVs.

**Functional Requirements:**

1. View CV list:

   - Display all uploaded CVs
   - Show CV name, upload date, primary badge
   - Preview CV details (parsed facts)
   - Download original CV button



2. Edit CV metadata:

   - Rename CV
   - Set as primary CV
   - Edit parsed facts (structured form, not WYSIWYG)
   - Save changes



3. Delete CV:

   - Confirm deletion with modal
   - Cannot delete primary CV if it's the only CV
   - Delete from S3 and DynamoDB
   - Remove from all associated applications

**Technical Implementation:**

Lambda Function: user-profile-handler

Endpoints:

  GET /api/cvs \- List all CVs

  GET /api/cvs/{cvId} \- Get CV details

  PUT /api/cvs/{cvId} \- Update CV metadata

  DELETE /api/cvs/{cvId} \- Delete CV

Update Flow:

  1\. Validate cvId belongs to user

  2\. Update DynamoDB record

  3\. If is\_primary changed, update other CVs

  4\. Return updated CV object

**Acceptance Criteria:**

- ✅ User sees list of all uploaded CVs
- ✅ Primary CV clearly indicated with badge
- ✅ CV renamed successfully
- ✅ Primary CV can be changed
- ✅ CV deleted from both S3 and DynamoDB
- ✅ Cannot delete last remaining CV
- ✅ Confirmation required before deletion
- ✅ **CV facts edited via structured form (not WYSIWYG)**

---

### 2.3 Job Application Processing

#### F-JOB-001: Job Posting Input with Validation

**Priority:** P0
**Sprint:** Sprint 3
**Dependencies:** F-CV-003 (CV Management)

**Description:** Allow users to input job details with **validation popup before processing** to catch errors early.

**Functional Requirements:**

1. Job input form:

   - Job title (required, 5-100 chars)
   - Company name (required, 2-100 chars)
   - Company website URL (optional, valid URL)
   - Job description (required, paste or upload, max 10,000 chars)
   - Job posting URL (optional, valid URL)
   - Select CV to use (dropdown, defaults to primary)



2. **Validation popup before processing:**

   - Show summary of extracted information
   - Highlight any potential issues:
     * Missing company name
     * Unclear job requirements
     * Very short job description (\< 200 chars)
   - Allow user to correct before proceeding
   - "Looks good, proceed" button to continue



3. Processing initiation:

   - Create application record in DynamoDB
   - Set status \= "PENDING"
   - Queue orchestrator Lambda for processing
   - Redirect to application status page

**Technical Implementation:**

Lambda Function: job-posting-handler

Endpoint: POST /api/applications/create

Request Body:

  job\_title: string

  company\_name: string

  company\_website: string (optional)

  job\_description: string

  job\_posting\_url: string (optional)

  cv\_id: string

Validation Logic:

  1\. Check required fields present

  2\. Validate job\_description length (200-10,000 chars)

  3\. Extract key requirements using Claude Haiku

  4\. Return validation\_summary with warnings

  5\. User confirms or edits

  6\. Create application on confirmation

DynamoDB Table: careervp-applications

Attributes:

  userId: String (PK)

  applicationId: String (SK)

  job\_title: String

  company\_name: String

  company\_website: String

  job\_description: String

  job\_posting\_url: String

  cv\_id: String

  status: String (PENDING, PROCESSING, COMPLETED, FAILED)

  stage: String (CREATED, COMPANY\_RESEARCH, GAP\_ANALYSIS, GENERATING\_ARTIFACTS)

  created\_at: String

  updated\_at: String

**Acceptance Criteria:**

- ✅ Required fields validated before submission
- ✅ **Validation popup shows extracted job requirements**
- ✅ **User can correct information before processing**
- ✅ Job description length validated (200-10,000 chars)
- ✅ Invalid URLs rejected with clear error
- ✅ Application created with unique applicationId
- ✅ User redirected to status page after creation
- ✅ Free tier users see credits\_remaining decrement

**Error Handling:**

- Missing required field: "Please fill in all required fields."
- Job description too short: "Job description must be at least 200 characters. Please add more details."
- Job description too long: "Job description must be under 10,000 characters."
- Invalid URL: "Please enter a valid URL."

---

#### F-JOB-002: Company Research

**Priority:** P0
**Sprint:** Sprint 3
**Dependencies:** F-JOB-001 (Job Posting Input)

**Description:** Automated company research using hybrid web scraping with Perplexity API fallback.

**Functional Requirements:**

1. Research data collection:

   - Company overview and mission
   - Recent news (last 6 months)
   - Company size and industry
   - Key products/services
   - Company culture and values
   - Funding/growth information



2. Hybrid research approach:

   - Primary: Web scraping of company website
   - Fallback: Perplexity API if scraping insufficient
   - Cache results in DynamoDB (30 days TTL)
   - Reuse cached research for same company



3. Data quality:

   - Verify data freshness (\< 6 months old)
   - Flag outdated information
   - Include source URLs for verification

**Technical Implementation:**

Lambda Function: company-research-v1

Runtime: Python 3.11

Memory: 512MB

Timeout: 45s

Trigger: Orchestrator (async)

Research Flow:

  1\. Check cache for existing research (same company, \< 30 days)

  2\. If cached, return cached data

  3\. If not cached:

     a. Scrape company website (BeautifulSoup)

     b. If insufficient data, call Perplexity API

     c. Cache results in DynamoDB

  4\. Return research summary

Perplexity API:

  Model: sonar-small-online

  Query: "Provide an overview of {company\_name}, including mission, recent news, products, culture, and growth."

  Cost: \~$0.003 per query

DynamoDB Table: careervp-company-research-cache

Attributes:

  company\_name\_normalized: String (PK)

  research\_date: String (SK)

  company\_overview: String

  recent\_news: Array

  company\_size: String

  industry: String

  products\_services: Array

  culture\_values: String

  funding\_info: String

  source\_urls: Array

  TTL: Number (30 days)

**Acceptance Criteria:**

- ✅ Company research completes within 45 seconds
- ✅ Cached research retrieved in \< 1 second
- ✅ Web scraping successful for 80% of companies
- ✅ Perplexity fallback works when scraping fails
- ✅ Research includes at least 5 data points
- ✅ Source URLs included for verification
- ✅ Cache expires after 30 days
- ✅ Research cost \< $0.004 per company

**Error Handling:**

- Scraping failed: Automatically fallback to Perplexity
- Perplexity failed: Use minimal company info from job posting
- Network timeout: Retry once, then proceed with limited info

---

#### F-JOB-003: Gap Analysis Questions Generation

**Priority:** P0
**Sprint:** Sprint 4
**Dependencies:** F-JOB-002 (Company Research)

**Description:** Generate personalized gap analysis questions (max 10\) to gather evidence for value proposition.

**Functional Requirements:**

1. Question generation:

   - Analyze CV and job requirements
   - Identify gaps between CV and job
   - Generate targeted questions (max 10\)
   - Prioritize questions by importance
   - Integrate previously answered questions to avoid repetition



2. Question types:

   - Quantify achievements ("How many...", "What percentage...")
   - Provide specific examples ("Describe a time when...")
   - Clarify responsibilities ("What was your role in...")
   - Fill experience gaps ("Have you worked with...")



3. Question management:

   - Store questions in DynamoDB
   - Link to applicationId
   - Track response status
   - Allow skipping optional questions

**Technical Implementation:**

Lambda Function: gap-analysis-questions

Runtime: Python 3.11

Memory: 512MB

Timeout: 30s

AI Model: Claude Sonnet 4.5

Trigger: Orchestrator (after company research)

Prompt Template:

  "Analyze this CV and job description. Generate up to 10 targeted questions to:

   1\. Quantify achievements with specific numbers

   2\. Gather evidence for required skills

   3\. Fill gaps in experience

   4\. Clarify ambiguous responsibilities



   Prioritize questions by importance (CRITICAL, IMPORTANT, OPTIONAL).



   Previous questions answered: {previous\_gap\_responses}



   Do not repeat questions already answered."

DynamoDB Storage:

  PK: applicationId

  SK: GAP\_ANALYSIS\_QUESTIONS

  Attributes:

    questions: Array (max 10\)

      \- question\_id: String

      \- text: String

      \- priority: String (CRITICAL, IMPORTANT, OPTIONAL)

      \- category: String (QUANTIFY, EXAMPLE, CLARIFY, FILL\_GAP)

    created\_at: String

**Acceptance Criteria:**

- ✅ Generates exactly 10 questions or fewer
- ✅ Questions prioritized by importance
- ✅ Questions are specific and actionable
- ✅ No duplicate questions from previous applications
- ✅ Questions stored in DynamoDB
- ✅ User sees questions on application page
- ✅ Questions generated within 30 seconds
- ✅ AI cost \< $0.003 per generation

---

#### F-JOB-004: Gap Analysis Responses Collection

**Priority:** P0
**Sprint:** Sprint 4
**Dependencies:** F-JOB-003 (Gap Analysis Questions)

**Description:** Collect user responses to gap analysis questions with validation and auto-save.

**Functional Requirements:**

1. Response collection:

   - Display questions one at a time or all at once (user preference)
   - Text area for responses (min 50 chars, max 1,000 chars)
   - Mark questions as answered
   - Allow skipping optional questions
   - Show progress indicator (X of Y answered)



2. Auto-save:

   - Save responses every 30 seconds
   - Resume capability if user leaves page
   - Store draft responses in DynamoDB



3. Validation:

   - Require CRITICAL priority questions
   - Warn if IMPORTANT questions skipped
   - Allow proceeding with optional questions unanswered

**Technical Implementation:**

Lambda Function: artifact-review-handler

Endpoint: POST /api/applications/{applicationId}/gap-analysis/responses

Request Body:

  responses: Array

    \- question\_id: String

    \- response\_text: String

    \- skipped: Boolean

Validation:

  \- Check all CRITICAL questions answered

  \- Warn if IMPORTANT questions skipped

  \- Save responses to DynamoDB

DynamoDB Storage:

  PK: applicationId

  SK: GAP\_ANALYSIS\_RESPONSES

  Attributes:

    responses: Array

      \- question\_id: String

      \- response\_text: String

      \- word\_count: Number

      \- skipped: Boolean

    completed\_at: String

**Acceptance Criteria:**

- ✅ All 10 questions displayed clearly
- ✅ Responses auto-save every 30 seconds
- ✅ User can skip optional questions
- ✅ Warning shown if critical questions unanswered
- ✅ Progress indicator shows X of Y completed
- ✅ User can resume if they leave and return
- ✅ **Responses integrated into VPR generation as input**
- ✅ Responses stored for reuse in future applications

---

#### F-JOB-005: Value Proposition Report (VPR) Generation

**Priority:** P0
**Sprint:** Sprint 5
**Dependencies:** F-JOB-004 (Gap Analysis Responses)

**Description:** Generate comprehensive Value Proposition Report using Claude Sonnet with gap analysis responses.

**Functional Requirements:**

1. VPR content structure:

   - Executive summary (candidate's unique value)
   - Evidence and alignment matrix (job requirements vs. CV facts **enhanced with gap responses**)
   - Strategic differentiators (3-5 key strengths)
   - Gap mitigation strategies (for missing requirements)
   - Cultural fit analysis (based on company research)
   - Recommended talking points for interviews



2. Quality requirements:

   - All facts verified against CV (zero hallucinations)
   - **Incorporate gap analysis responses as evidence**
   - ATS-optimized language
   - Pass anti-AI detection (humanized writing)
   - Length: 3-4 pages (1,500-2,000 words)



3. Document formatting:

   - Professional layout
   - Clear section headers
   - Bullet points for readability
   - Export to DOCX format (default)

**Technical Implementation:**

Lambda Function: vp-report-generator

Runtime: Python 3.11

Memory: 1024MB

Timeout: 120s

AI Model: Claude Sonnet 4.5

Trigger: Orchestrator (after gap analysis)

Input Data:

  \- CV parsed facts

  \- Job description

  \- Company research

  \- \*\*Gap analysis responses\*\* (enriches evidence)

  \- Previous application artifacts (if any)

Prompt Template:

  "Generate a Value Proposition Report using:

   \- CV facts: {parsed\_facts}

   \- Job requirements: {job\_description}

   \- Company research: {company\_research}

   \- Gap analysis responses: {gap\_responses}



   The gap responses provide specific, quantified achievements

   that should be integrated into the evidence matrix.



   Follow anti-AI detection patterns.

   Verify all facts against CV (zero hallucinations).

   Length: 1,500-2,000 words."

AI Cost:

  Sonnet input: \~8,000 tokens

  Sonnet output: \~2,500 tokens

  Cost: \~$0.035 per VPR

DynamoDB Storage:

  PK: applicationId

  SK: ARTIFACT\#VPR\#v1

  Attributes:

    artifact\_type: "VPR"

    status: "DRAFT"

    content: String (markdown)

    s3\_key\_docx: String

    generated\_at: String

    model\_used: "sonnet-4.5"

    token\_cost: Number

**Acceptance Criteria:**

- ✅ VPR generated within 120 seconds
- ✅ All facts verified against CV (zero hallucinations)
- ✅ **Gap analysis responses integrated into evidence matrix**
- ✅ Passes ATS compatibility check
- ✅ Passes anti-AI detection check
- ✅ Length: 1,500-2,000 words
- ✅ Exported to DOCX format
- ✅ User can download immediately after generation
- ✅ AI cost \< $0.040 per VPR

**Anti-AI Detection Patterns:**

- Avoid "leverage", "delve into", "landscape", "robust", "streamline"
- Use natural transitions, not formulaic
- Vary sentence structure and length
- Include conversational language where appropriate
- Use approximations instead of exact percentages

---

#### F-JOB-006: CV Tailoring

**Priority:** P0
**Sprint:** Sprint 5
**Dependencies:** F-JOB-005 (VPR Generation)

**Description:** Generate tailored CV optimized for specific job posting using Claude Haiku with structured form editing.

**Functional Requirements:**

1. CV tailoring:

   - Prioritize relevant experience
   - Emphasize matching skills
   - Reorder sections for ATS optimization
   - Add job-specific keywords
   - Remove irrelevant information
   - Maintain factual accuracy (zero hallucinations)



2. ATS optimization:

   - Use exact keywords from job description
   - Standard section headers
   - Simple formatting (no tables, columns)
   - Bullet points for readability
   - Length: 1-2 pages (max 3 pages)



3. **Editing interface:**

   - **Structured form (NOT WYSIWYG)**
   - Edit sections individually (Experience, Education, Skills)
   - Reorder experience bullets
   - Add/remove sections
   - Preserve ATS compatibility

**Technical Implementation:**

Lambda Function: cv-tailor

Runtime: Python 3.11

Memory: 512MB

Timeout: 60s

AI Model: Claude Haiku 4.5

Trigger: Orchestrator (after VPR)

Input Data:

  \- CV parsed facts

  \- Job description

  \- VPR strategic differentiators

  \- Company research keywords

Prompt Template:

  "Tailor this CV for the specific job:

   \- CV facts: {parsed\_facts}

   \- Job requirements: {job\_requirements}

   \- Strategic differentiators: {vpr\_differentiators}



   Prioritize relevant experience and skills.

   Use ATS-optimized formatting.

   Zero hallucinations \- only use CV facts.

   Length: 1-2 pages."

AI Cost:

  Haiku input: \~5,000 tokens

  Haiku output: \~1,200 tokens

  Cost: \~$0.005 per CV

DynamoDB Storage:

  PK: applicationId

  SK: ARTIFACT\#CV\#v1

  Attributes:

    artifact\_type: "CV"

    status: "DRAFT"

    content: JSON (structured sections)

    s3\_key\_docx: String

    s3\_key\_pdf: String

    generated\_at: String

    model\_used: "haiku-4.5"

    token\_cost: Number

**Acceptance Criteria:**

- ✅ CV tailored to job requirements
- ✅ Relevant experience prioritized
- ✅ ATS-optimized formatting
- ✅ Zero hallucinations (facts verified)
- ✅ Length: 1-2 pages
- ✅ **Editing via structured form, not WYSIWYG**
- ✅ Exports to DOCX and PDF
- ✅ AI cost \< $0.006 per CV

---

#### F-JOB-007: Cover Letter Generation

**Priority:** P0
**Sprint:** Sprint 5
**Dependencies:** F-JOB-006 (CV Tailoring)

**Description:** Generate personalized cover letter using Claude Haiku with anti-AI detection.

**Functional Requirements:**

1. Cover letter content:

   - Opening paragraph (hook \+ job interest)
   - 2-3 body paragraphs (achievements \+ fit)
   - Closing paragraph (call to action)
   - Professional tone matching company culture
   - Use strategic differentiators from VPR



2. Quality requirements:

   - Length: **exactly 1 page (max 400 words)**
   - Zero hallucinations (facts verified)
   - Pass anti-AI detection
   - ATS-optimized language
   - Natural, human-like writing



3. Personalization:

   - Address specific job requirements
   - Reference company research insights
   - Highlight 2-3 key achievements
   - Match company culture tone

**Technical Implementation:**

Lambda Function: cover-letter-generator

Runtime: Python 3.11

Memory: 512MB

Timeout: 60s

AI Model: Claude Haiku 4.5

Trigger: Orchestrator (after CV tailoring)

Input Data:

  \- CV parsed facts

  \- Job description

  \- VPR strategic differentiators

  \- Company research

Prompt Template:

  "Generate a cover letter (exactly 1 page, max 400 words):

   \- CV facts: {parsed\_facts}

   \- Job requirements: {job\_requirements}

   \- Strategic differentiators: {vpr\_differentiators}

   \- Company culture: {company\_culture}



   Use anti-AI detection patterns.

   Zero hallucinations.

   Natural, conversational tone."

AI Cost:

  Haiku input: \~4,000 tokens

  Haiku output: \~800 tokens

  Cost: \~$0.004 per cover letter

DynamoDB Storage:

  PK: applicationId

  SK: ARTIFACT\#COVER\_LETTER\#v1

**Acceptance Criteria:**

- ✅ Cover letter length: **exactly 1 page (max 400 words)**
- ✅ Zero hallucinations (facts verified)
- ✅ Passes anti-AI detection check
- ✅ ATS-optimized language
- ✅ Natural, human-like writing
- ✅ Addresses specific job requirements
- ✅ References company insights
- ✅ Exports to DOCX and PDF
- ✅ AI cost \< $0.005 per cover letter

---

#### F-JOB-008: Interview Prep Generation

**Priority:** P0
**Sprint:** Sprint 6
**Dependencies:** F-JOB-007 (Cover Letter Generation)

**Description:** Generate interview preparation guide with predicted questions and STAR-formatted responses, defaults to Docx format.

**Functional Requirements:**

1. Interview prep content:

   - 10-15 predicted interview questions
   - STAR-formatted responses for each question
   - Company-specific talking points
   - Questions to ask the interviewer
   - Salary negotiation guidance
   - Cultural fit preparation



2. Question prediction:

   - Analyze job requirements for technical questions
   - Include behavioral questions
   - Company-specific questions based on research
   - Gap-related questions (based on gap analysis)



3. Response formatting:

   - STAR method (Situation, Task, Action, Result)
   - Include specific examples from CV
   - Quantified results where possible
   - Natural delivery (anti-AI detection)



4. **Default format: Docx** (user can also export to PDF)

**Technical Implementation:**

Lambda Function: interview-prep-generator

Runtime: Python 3.11

Memory: 512MB

Timeout: 60s

AI Model: Claude Haiku 4.5

Trigger: Orchestrator (after cover letter)

Input Data:

  \- CV parsed facts

  \- Job description

  \- VPR strategic differentiators

  \- Gap analysis responses

  \- Company research

Prompt Template:

  "Generate interview prep guide:

   \- Predict 10-15 interview questions

   \- Provide STAR responses using CV facts

   \- Include company-specific questions

   \- Suggest questions for interviewer



   Use natural, conversational language.

   Zero hallucinations."

AI Cost:

  Haiku input: \~5,000 tokens

  Haiku output: \~2,000 tokens

  Cost: \~$0.005 per interview prep

DynamoDB Storage:

  PK: applicationId

  SK: ARTIFACT\#INTERVIEW\_PREP\#v1

  Attributes:

    artifact\_type: "INTERVIEW\_PREP"

    default\_format: "DOCX"

**Acceptance Criteria:**

- ✅ 10-15 predicted questions generated
- ✅ STAR-formatted responses for each question
- ✅ Responses use specific CV facts
- ✅ Zero hallucinations
- ✅ Natural, conversational language
- ✅ Company-specific insights included
- ✅ **Defaults to DOCX format export**
- ✅ Also available as PDF export
- ✅ AI cost \< $0.006 per interview prep

---

### 2.4 Document Review & Editing

#### F-REVIEW-001: Artifact Review Interface

**Priority:** P0
**Sprint:** Sprint 6
**Dependencies:** F-JOB-008 (Interview Prep Generation)

**Description:** Allow users to review and edit all generated artifacts before finalizing.

**Functional Requirements:**

1. Review interface:

   - Side-by-side view: original CV vs. tailored CV
   - Highlight changes in tailored CV
   - View all artifacts (VPR, CV, Cover Letter, Interview Prep)
   - Download buttons for each artifact (DOCX, PDF)



2. **Editing capabilities (structured form, not WYSIWYG):**

   - Edit CV sections individually
   - Edit cover letter paragraphs
   - Edit interview prep responses
   - Cannot edit VPR (regenerate instead)
   - Track user edits as "ground truth"



3. Finalization:

   - Mark artifacts as "FINAL"
   - Store edited versions
   - Persist edits for future applications
   - Update knowledge base with verified facts

**Technical Implementation:**

Lambda Function: artifact-review-handler

Endpoints:

  GET /api/applications/{applicationId}/artifacts

  PUT /api/applications/{applicationId}/artifacts/{artifactId}

  POST /api/applications/{applicationId}/finalize

Edit Flow:

  1\. User edits artifact via structured form

  2\. Save edited version to DynamoDB

  3\. Mark status \= "EDITED"

  4\. Store edits in knowledge base for reuse

  5\. Update s3\_key\_docx with edited version

Knowledge Base Update:

  \- Extract edited facts as "ground truth"

  \- Store in careervp-knowledge-base table

  \- Reuse in future applications

  \- Reduces AI inference costs

**Acceptance Criteria:**

- ✅ User sees all generated artifacts
- ✅ Side-by-side comparison of original vs. tailored CV
- ✅ **Editing via structured form (not WYSIWYG)**
- ✅ Edits saved immediately
- ✅ User can finalize all artifacts
- ✅ Edited facts stored in knowledge base
- ✅ Download buttons work for all formats

---

#### F-REVIEW-002: Artifact Regeneration

**Priority:** P0
**Sprint:** Sprint 6
**Dependencies:** F-REVIEW-001 (Artifact Review)

**Description:** Allow users to regenerate individual artifacts or provide feedback for improvement.

**Functional Requirements:**

1. Regeneration options:

   - Regenerate single artifact (CV, Cover Letter, Interview Prep)
   - Regenerate all artifacts (batch)
   - Provide specific feedback for regeneration
   - Preserve user edits from previous versions



2. Feedback integration:

   - User provides instruction (e.g., "Make it more technical")
   - AI incorporates feedback into regeneration
   - Compare old vs. new version
   - User can revert to previous version



3. Version control:

   - Track artifact versions (v1, v2, v3...)
   - Allow downloading any version
   - Show version history
   - Mark latest as active

**Technical Implementation:**

Lambda Function: artifact-review-handler

Endpoint: POST /api/applications/{applicationId}/regenerate

Request Body:

  artifact\_type: String (CV, COVER\_LETTER, INTERVIEW\_PREP, ALL)

  feedback: String (optional, user instruction)

  version: Number (current version)

Regeneration Flow:

  1\. Load original inputs (CV, job, VPR)

  2\. Load user feedback

  3\. Incorporate user edits from knowledge base

  4\. Call appropriate generator Lambda

  5\. Increment version number

  6\. Save new version to DynamoDB

  7\. Return new artifact

Version Storage:

  PK: applicationId

  SK: ARTIFACT\#{type}\#v{N}

**Acceptance Criteria:**

- ✅ User can regenerate individual artifacts
- ✅ User can provide feedback for regeneration
- ✅ **Feedback incorporated into regeneration (not fully automated)**
- ✅ User edits preserved in new version
- ✅ Version history displayed
- ✅ User can revert to previous version
- ✅ AI cost \< $0.010 per regeneration

---

### 2.5 Document Export

#### F-EXPORT-001: DOCX Export

**Priority:** P0
**Sprint:** Sprint 7
**Dependencies:** F-REVIEW-002 (Artifact Regeneration)

**Description:** Export artifacts to professionally formatted DOCX files.

**Functional Requirements:**

1. DOCX formatting:

   - Professional template with branding
   - ATS-compatible formatting
   - Standard fonts (Calibri, Arial, Times New Roman)
   - Proper margins and spacing
   - Page breaks where appropriate



2. Export options:

   - Download single artifact
   - Download all artifacts as ZIP
   - Email artifacts to user
   - Send to Google Drive (future)



3. File naming:

   - Format: {FirstName}*{LastName}*{ArtifactType}\_{CompanyName}.docx
   - Example: John\_Doe\_CV\_Acme\_Corp.docx

**Technical Implementation:**

Lambda Function: docx-export

Runtime: Python 3.11

Memory: 512MB

Timeout: 30s

Library: python-docx

Trigger: API Gateway GET /api/artifacts/{artifactId}/download?format=docx

Export Flow:

  1\. Load artifact content from DynamoDB

  2\. Apply DOCX template

  3\. Generate file in /tmp

  4\. Upload to S3 bucket: careervp-artifacts-{env}

  5\. Generate presigned download URL (expires in 1 hour)

  6\. Return download URL

S3 Storage:

  Bucket: careervp-artifacts-prod

  Path: {userId}/applications/{applicationId}/{artifactType}.docx

  Encryption: SSE-S3

  Lifecycle: 90 days \-\> IA, 180 days \-\> Glacier

**Acceptance Criteria:**

- ✅ DOCX file generated within 10 seconds
- ✅ Professional formatting applied
- ✅ ATS-compatible layout
- ✅ Download link works immediately
- ✅ File naming follows standard format
- ✅ File size \< 500KB
- ✅ Compatible with Microsoft Word, Google Docs, LibreOffice

---

#### F-EXPORT-002: PDF Export

**Priority:** P0
**Sprint:** Sprint 7
**Dependencies:** F-EXPORT-001 (DOCX Export)

**Description:** Export artifacts to PDF format with professional formatting.

**Functional Requirements:**

1. PDF formatting:

   - Convert DOCX to PDF
   - Preserve formatting and layout
   - Embedded fonts for consistency
   - Searchable text (OCR not needed)



2. Export options:

   - Download single artifact as PDF
   - Download all artifacts as ZIP
   - Email artifacts to user



3. File naming:

   - Same as DOCX format
   - Example: John\_Doe\_CV\_Acme\_Corp.pdf

**Technical Implementation:**

Lambda Function: pdf-export

Runtime: Python 3.11

Memory: 512MB

Timeout: 30s

Library: reportlab or weasyprint

Trigger: API Gateway GET /api/artifacts/{artifactId}/download?format=pdf

Export Flow:

  1\. Load artifact content from DynamoDB

  2\. Generate PDF from markdown or DOCX

  3\. Upload to S3 bucket: careervp-artifacts-{env}

  4\. Generate presigned download URL

  5\. Return download URL

**Acceptance Criteria:**

- ✅ PDF generated within 15 seconds
- ✅ Professional formatting preserved
- ✅ Searchable text
- ✅ File size \< 1MB
- ✅ Compatible with all PDF readers
- ✅ Print-ready quality

---

### 2.6 Subscription & Billing

#### F-SUBSCRIPTION-001: Stripe Integration

**Priority:** P0
**Sprint:** Sprint 7
**Dependencies:** F-AUTH-002 (User Login)

**Description:** Integrate Stripe for subscription management and payment processing.

**Functional Requirements:**

1. Subscription plans:

   - Free Trial: 14 days, 3 applications, credit card required
   - Monthly: $25/month, unlimited applications
   - 3-Month: $65 (save 13%), unlimited applications
   - 6-Month: $120 (save 20%), unlimited applications



2. Checkout flow:

   - Redirect to Stripe Checkout for payment
   - Create subscription in Stripe
   - Webhook updates user tier in DynamoDB
   - Send confirmation email



3. Subscription management:

   - View current plan and renewal date
   - Upgrade/downgrade plans
   - Cancel subscription
   - Update payment method
   - View billing history

**Technical Implementation:**

Lambda Function: stripe-webhook-handler

Endpoints:

  POST /api/subscription/create-checkout

  POST /api/subscription/portal

  POST /api/webhooks/stripe

Stripe Products:

  \- Free Trial (trial\_period\_days: 14\)

  \- Monthly ($25/month)

  \- 3-Month ($65/3 months)

  \- 6-Month ($120/6 months)

Webhook Events:

  \- checkout.session.completed \-\> Update user tier

  \- customer.subscription.updated \-\> Update subscription

  \- customer.subscription.deleted \-\> Downgrade to free

  \- invoice.payment\_failed \-\> Send payment failed email

DynamoDB Table: careervp-subscriptions

Attributes:

  userId: String (PK)

  stripe\_customer\_id: String (GSI)

  stripe\_subscription\_id: String

  plan: String (monthly, 3\_month, 6\_month)

  status: String (active, canceled, past\_due)

  current\_period\_end: String (ISO 8601\)

  cancel\_at\_period\_end: Boolean

**Acceptance Criteria:**

- ✅ User can subscribe to paid plan
- ✅ Stripe checkout works correctly
- ✅ Webhook updates user tier immediately
- ✅ Confirmation email sent after payment
- ✅ User can view subscription details
- ✅ User can upgrade/downgrade plans
- ✅ User can cancel subscription
- ✅ Payment failures handled gracefully

**Error Handling:**

- Payment failed: Send email with retry instructions
- Card declined: Show error and retry option
- Webhook failure: Retry webhook 3 times, then alert admin

---

#### F-SUBSCRIPTION-002: Usage Tracking & Limits

**Priority:** P0
**Sprint:** Sprint 7
**Dependencies:** F-SUBSCRIPTION-001 (Stripe Integration)

**Description:** Track usage and enforce limits for free tier users (3 applications).

**Functional Requirements:**

1. **Free tier tracking (3 applications limit):**

   - Decrement credits\_remaining after each application
   - Block new applications when credits \= 0
   - Show remaining credits on dashboard
   - Prompt upgrade when credits low



2. **Paid tier tracking (unlimited):**

   - No credit tracking
   - Unlimited applications
   - Usage displayed for transparency (no limits)



3. Upgrade prompts:

   - Show upgrade modal when credits \= 1
   - Show upgrade banner when credits \= 0
   - Include pricing comparison
   - One-click upgrade to paid plan

**Technical Implementation:**

Lambda Function: credit-manager

Trigger: Called by orchestrator before processing

Credit Check Flow:

  1\. Load user from DynamoDB

  2\. Check tier (free vs. paid)

  3\. If free tier:

     a. Check credits\_remaining \> 0

     b. If yes, proceed and decrement

     c. If no, return error: "No credits remaining"

  4\. If paid tier:

     a. Always proceed (unlimited)

     b. Increment usage\_count for analytics

DynamoDB Update:

  \- Free tier: Decrement credits\_remaining

  \- Paid tier: Increment usage\_count

**Acceptance Criteria:**

- ✅ Free tier users limited to 3 applications
- ✅ Paid tier users have unlimited applications
- ✅ Credits\_remaining displayed on dashboard (free tier only)
- ✅ Upgrade prompt shown when credits \= 1
- ✅ Clear error when credits \= 0
- ✅ Upgrade button redirects to Stripe checkout
- ✅ Credits reset on free trial expiry (not on renewal)

---

### 2.7 Admin Dashboard

#### F-ADMIN-001: Admin Dashboard

**Priority:** P0
**Sprint:** Sprint 8
**Dependencies:** All core features

**Description:** Admin dashboard for monitoring system health, user activity, and costs.

**Functional Requirements:**

1. Dashboard metrics:

   - Total users (by tier)
   - Active users (last 7 days)
   - Total applications generated
   - AI costs (daily, weekly, monthly)
   - Average cost per application
   - System health (Lambda errors, API latency)



2. User management:

   - Search users by email
   - View user details
   - Reset user limits (free tier)
   - Suspend/unsuspend accounts
   - View user activity log



3. Cost monitoring:

   - Token usage by model
   - S3 storage costs
   - DynamoDB costs
   - CloudWatch alerts for high costs

**Technical Implementation:**

Lambda Function: admin-dashboard-api

Endpoints:

  GET /api/admin/metrics

  GET /api/admin/users

  GET /api/admin/users/{userId}

  POST /api/admin/users/{userId}/reset-limits

  POST /api/admin/users/{userId}/suspend

Authorization:

  \- Require admin role (JWT claim)

  \- Admin users defined in DynamoDB

Metrics Aggregation:

  \- Query DynamoDB for user counts

  \- Query CloudWatch for Lambda metrics

  \- Query DynamoDB for application counts

  \- Calculate costs from token\_metrics table

DynamoDB Table: careervp-admin-audit

Attributes:

  adminId: String (PK)

  action: String (SK)

  userId: String

  details: JSON

  timestamp: String

**Acceptance Criteria:**

- ✅ Admin can view dashboard metrics
- ✅ Metrics update in real-time
- ✅ Admin can search users
- ✅ Admin can reset user limits
- ✅ Admin can suspend accounts
- ✅ All admin actions logged to audit table
- ✅ Cost alerts sent to admin email

---

### 2.8 Notifications

#### F-NOTIFY-001: Email Notifications (User-Facing)

**Priority:** P0
**Sprint:** Sprint 8
**Dependencies:** All core features

**Description:** Send email notifications to users for key events.

**Functional Requirements:**

1. **User-facing notifications (via email):**

   - Welcome email on registration
   - Email verification link
   - Application processing started
   - Application completed (with download links)
   - Trial expiring (7 days, 3 days, 1 day)
   - Subscription upgraded/downgraded
   - Payment successful
   - Payment failed (with retry instructions)



2. Email templates:

   - Branded HTML templates
   - Responsive design (mobile-friendly)
   - Unsubscribe link (except critical emails)
   - Personalized with user name



3. Email delivery:

   - AWS SES for sending
   - Track delivery status
   - Retry failed deliveries (3 attempts)

**Technical Implementation:**

Lambda Function: notification-handler

Runtime: Python 3.11

Memory: 256MB

Timeout: 10s

Trigger: SNS topic: careervp-notifications

Email Service: AWS SES

Templates: Jinja2 HTML templates

SNS Message Format:

  notification\_type: String (WELCOME, APPLICATION\_COMPLETE, etc.)

  userId: String

  data: JSON (context for template)

Email Flow:

  1\. Receive SNS message

  2\. Load user details from DynamoDB

  3\. Load email template

  4\. Render template with data

  5\. Send via AWS SES

  6\. Log delivery status to CloudWatch

**Acceptance Criteria:**

- ✅ Welcome email sent within 60 seconds of registration
- ✅ Application complete email sent immediately after processing
- ✅ Trial expiry emails sent at correct intervals (7, 3, 1 day)
- ✅ Payment emails sent within 5 minutes of Stripe event
- ✅ All emails use branded templates
- ✅ Unsubscribe link included (except critical emails)
- ✅ Failed deliveries retried 3 times

---

#### F-NOTIFY-002: Admin Alerts (CloudWatch Alarms)

**Priority:** P0
**Sprint:** Sprint 8
**Dependencies:** All core features

**Description:** Send CloudWatch alarms to admin email for system issues (NOT to users).

**Functional Requirements:**

1. **Admin-only alerts (via CloudWatch alarms):**

   - Lambda function errors
   - API Gateway 5xx errors
   - **Knowledge base limit reached (NO user notification)**
   - High AI costs (\> $100/day)
   - High API latency (\> 3 seconds)
   - DynamoDB throttling
   - S3 storage exceeds threshold



2. Alert delivery:

   - Email to admin email address
   - Include error details and logs
   - Link to CloudWatch dashboard
   - Priority level (WARNING, CRITICAL)



3. Alert suppression:

   - Don't spam admin with duplicate alerts
   - Suppress repeated errors (same error within 1 hour)

**Technical Implementation:**

CloudWatch Alarms:

  LambdaErrorRate:

    Metric: Errors

    Threshold: \> 5 errors in 5 minutes

    Action: Send SNS to admin-alerts topic



  APIGateway5xxErrors:

    Metric: 5XXError

    Threshold: \> 10 errors in 5 minutes

    Action: Send SNS to admin-alerts topic



  KnowledgeBaseLimitReached:

    Metric: Custom metric (kb\_entries\_count)

    Threshold: \> 90% of limit

    Action: Send SNS to admin-alerts topic

    Note: NO USER NOTIFICATION



  HighAICosts:

    Metric: Custom metric (daily\_ai\_cost)

    Threshold: \> $100

    Action: Send SNS to admin-alerts topic

SNS Topic: careervp-admin-alerts

Subscribers: admin@careervp.com

**Acceptance Criteria:**

- ✅ Admin receives alert within 5 minutes of error
- ✅ **Knowledge base limit alerts sent ONLY to admin, NEVER to users**
- ✅ Alert includes error details and CloudWatch link
- ✅ Duplicate alerts suppressed (1 hour window)
- ✅ Critical alerts have "CRITICAL" in subject line
- ✅ Admin can acknowledge alerts

---

## 3\. ENHANCED FEATURES \- P1 (HIGH VALUE)

### 3.1 Language Support

#### F-LANG-001: Multi-Language Document Generation

**Priority:** P1
**Sprint:** Sprint 6
**Dependencies:** All artifact generation features

**Description:** Support English and Hebrew languages for V1 with language consistency rules.

**Functional Requirements:**

1. **Language consistency rules:**

   - If CV language \= Job posting language → Generate artifacts in that language
   - **If CV language ≠ Job posting language → Generate artifacts in BOTH languages**
   - Example: English CV \+ Hebrew job posting → Generate English \+ Hebrew artifacts



2. Supported languages (V1):

   - English (US, UK, Canadian, Australian variants)
   - Hebrew (Israel)



3. Language detection:

   - Auto-detect CV language from text
   - Auto-detect job posting language
   - Allow manual language override



4. Translation quality:

   - Native-level language generation (not translation)
   - Cultural appropriateness
   - Professional tone in both languages

**Technical Implementation:**

Lambda Function: language-detector

Library: langdetect

Trigger: Called during CV upload and job posting input

Language Detection Flow:

  1\. Detect CV language (auto)

  2\. Detect job posting language (auto)

  3\. If languages differ:

     a. Generate artifacts in both languages

     b. Create 2x artifacts (e.g., CV\_EN, CV\_HE)

  4\. Store language preference in user profile

AI Prompts:

  \- Include language instruction in all prompts

  \- "Generate in {language} with native-level fluency"

  \- Hebrew prompts use right-to-left formatting

**Acceptance Criteria:**

- ✅ Language auto-detected correctly (95% accuracy)
- ✅ **Artifacts generated in both languages when CV/job languages differ**
- ✅ Hebrew artifacts use right-to-left formatting
- ✅ Native-level language quality (not machine translation)
- ✅ User can manually override language detection
- ✅ Language preference saved in user profile

**AI Cost Impact:**

- 2x AI costs when generating both languages
- Example: CV in both languages \= $0.010 (vs. $0.005 single)

---

### 3.2 Advanced Editing

#### F-EDIT-001: Collaborative Editing (V1.1)

**Priority:** P1
**Sprint:** Post-launch
**Dependencies:** F-REVIEW-001 (Artifact Review)

**Description:** Allow users to share artifacts for collaborative editing (career coaches, mentors).

**Functional Requirements:**

1. Sharing:

   - Generate shareable link with expiry (7 days)
   - Share with specific email addresses
   - View-only or edit permissions
   - Revoke access anytime



2. Collaboration:

   - Multiple users can view artifact
   - Comments on specific sections
   - Suggested edits (track changes)
   - Owner approves/rejects changes



3. Version control:

   - Track all changes with author
   - Revert to any version
   - Compare versions side-by-side

**Technical Implementation:**

Lambda Function: sharing-handler

Endpoints:

  POST /api/applications/{applicationId}/share

  GET /api/shared/{shareToken}

  POST /api/shared/{shareToken}/comment

  DELETE /api/applications/{applicationId}/share/{shareToken}

DynamoDB Table: careervp-shares

Attributes:

  shareToken: String (PK)

  applicationId: String

  sharedBy: String (userId)

  sharedWith: String (email)

  permission: String (view, edit)

  expiresAt: String (ISO 8601\)

  created\_at: String

**Acceptance Criteria:**

- ✅ User can generate shareable link
- ✅ Link expires after 7 days
- ✅ Collaborators can view artifact
- ✅ Edit permissions allow suggested changes
- ✅ Owner receives notification of changes
- ✅ Owner can approve/reject changes
- ✅ Version history tracked

---

### 3.3 ATS Compatibility

#### F-ATS-001: ATS Compatibility Checker

**Priority:** P1
**Sprint:** Sprint 6
**Dependencies:** F-JOB-006 (CV Tailoring)

**Description:** Check tailored CVs for ATS compatibility and provide optimization suggestions.

**Functional Requirements:**

1. ATS checks:

   - Keyword match percentage (CV vs. job description)
   - Formatting issues (tables, columns, headers/footers)
   - Section headers (standard vs. non-standard)
   - Font compatibility
   - File format compatibility (DOCX, PDF)



2. Scoring:

   - ATS compatibility score (0-100)
   - Green (90-100), Yellow (70-89), Red (\< 70\)
   - Specific issues with fix suggestions



3. Optimization:

   - Suggest missing keywords
   - Flag formatting issues
   - Recommend section reordering
   - Provide ATS-friendly alternatives

**Technical Implementation:**

Lambda Function: ats-checker

Library: Custom ATS rules engine

Trigger: Called after CV tailoring

ATS Rules:

  \- Check keyword density

  \- Validate section headers

  \- Check font compatibility

  \- Validate formatting (no tables, columns)

  \- Check file size (\< 1MB)

Scoring Algorithm:

  \- Keyword match: 40 points

  \- Formatting: 30 points

  \- Section headers: 20 points

  \- Font compatibility: 10 points



  Total: 100 points

**Acceptance Criteria:**

- ✅ ATS score calculated within 5 seconds
- ✅ Score displayed with color coding
- ✅ Specific issues listed with fix suggestions
- ✅ User can fix issues and recheck
- ✅ Score improves after fixes applied
- ✅ Educational content about ATS optimization

---

### 3.4 Analytics

#### F-ANALYTICS-001: User Analytics Dashboard

**Priority:** P1
**Sprint:** Post-launch
**Dependencies:** All core features

**Description:** Provide users with insights on their application performance.

**Functional Requirements:**

1. Application metrics:

   - Total applications submitted
   - Success rate (interviews / applications)
   - Average time per application
   - Most successful companies/roles



2. Document quality:

   - ATS compatibility scores over time
   - AI detection scores
   - Word count trends
   - Keyword usage



3. Insights:

   - Personalized recommendations
   - Best performing application strategies
   - Comparison to anonymized peers

**Technical Implementation:**

Lambda Function: analytics-aggregator

Endpoints:

  GET /api/analytics/user

  GET /api/analytics/applications

  GET /api/analytics/insights

DynamoDB Table: careervp-analytics

Attributes:

  userId: String (PK)

  metric\_type: String (SK)

  value: Number

  timestamp: String

**Acceptance Criteria:**

- ✅ Dashboard shows key metrics
- ✅ Insights personalized to user
- ✅ Trends displayed visually (charts)
- ✅ Comparison to peers (anonymized)
- ✅ Recommendations actionable

---

## 4\. SUPPORTING FEATURES \- P2 (NICE TO HAVE)

### 4.1 Integrations

#### F-INTEGRATION-001: Google Drive Integration

**Priority:** P2
**Sprint:** Post-launch
**Dependencies:** F-EXPORT-001 (DOCX Export)

**Description:** Allow users to save artifacts directly to Google Drive.

**Functional Requirements:**

1. Google Drive connection:

   - OAuth authentication
   - Grant CareerVP access to Google Drive
   - Select destination folder



2. Export to Drive:

   - Save artifacts to Google Drive
   - Create folder structure: CareerVP/{Company Name}
   - Include all formats (DOCX, PDF)



3. Auto-sync:

   - Automatically save new artifacts to Drive
   - Update existing artifacts when edited

**Technical Implementation:**

Lambda Function: google-drive-export

Library: google-api-python-client

Trigger: User clicks "Save to Google Drive"

OAuth Flow:

  1\. User clicks "Connect Google Drive"

  2\. Redirect to Google OAuth consent screen

  3\. Store access token and refresh token in DynamoDB

  4\. Export artifacts to Drive

Google Drive API:

  \- Create folder: "CareerVP"

  \- Upload files: DOCX, PDF

  \- Set permissions: Private

**Acceptance Criteria:**

- ✅ User can connect Google Drive
- ✅ Artifacts saved to Drive successfully
- ✅ Folder structure created automatically
- ✅ User can disconnect Google Drive
- ✅ Auto-sync works when enabled

---

## 5\. V1.1 FEATURES (POST-LAUNCH ENHANCEMENTS)

### 5.1 Real-Time Updates

#### F-REALTIME-001: WebSocket Real-Time Status Updates

**Priority:** V1.1
**Sprint:** 1-2 months post-launch
**Dependencies:** All core features

**Description:** Implement WebSocket for real-time application processing status updates.

**Functional Requirements:**

1. Real-time status:

   - Show processing stage in real-time
   - Progress bar for each artifact
   - Estimated time remaining
   - Live notifications when artifacts ready



2. WebSocket connection:

   - Establish connection on application creation
   - Receive updates from orchestrator
   - Automatic reconnection on disconnect
   - Close connection on completion



3. User experience:

   - User doesn't need to refresh page
   - Toast notifications for milestones
   - Smooth progress animations
   - Download buttons appear when ready

**Technical Implementation:**

API Gateway: WebSocket API

Endpoints:

  $connect \-\> websocket-connect Lambda

  $disconnect \-\> websocket-disconnect Lambda

  $default \-\> websocket-message Lambda

Lambda Function: websocket-connect

Action:

  \- Store connectionId in DynamoDB

  \- Associate connectionId with userId



Lambda Function: orchestrator (modified)

Action:

  \- Publish updates to WebSocket connection

  \- Send progress updates after each stage



Message Format:

  {

    "type": "progress",

    "stage": "COMPANY\_RESEARCH",

    "progress": 20,

    "message": "Researching company...",

    "estimatedTimeRemaining": 120

  }

DynamoDB Table: careervp-websocket-connections

Attributes:

  connectionId: String (PK)

  userId: String (GSI)

  connected\_at: String

  TTL: Number (2 hours)

**Acceptance Criteria:**

- ✅ WebSocket connection established successfully
- ✅ Real-time updates displayed in UI
- ✅ Progress bar updates smoothly
- ✅ Estimated time remaining accurate
- ✅ Download buttons appear immediately when artifacts ready
- ✅ Automatic reconnection on network issues
- ✅ Connection closed after processing complete

**Implementation Notes:**

- Use API Gateway WebSocket API (cheaper than maintaining persistent connections via ALB)
- Lambda functions invoked for connect/disconnect/message
- Orchestrator publishes updates to WebSocket connections
- Frontend uses native WebSocket API or library like Socket.IO-client

---

## 6\. V2 ROADMAP FEATURES (FUTURE)

### 6.1 Job Tracking

#### F-TRACKING-001: Job Application Tracking Dashboard

**Priority:** V2
**Timeline:** Q3 2026

**Description:** Track job applications through the entire hiring process.

**Functional Requirements:**

1. Application stages:

   - Applied
   - Phone screen
   - Interview (multiple rounds)
   - Offer
   - Rejected
   - Withdrawn



2. Dashboard:

   - Kanban board view
   - Calendar view (interview dates)
   - List view with filters
   - Statistics (success rate, time in stage)



3. Reminders:

   - Follow-up reminders
   - Interview preparation reminders
   - Thank you note reminders

---

### 6.2 Video Interview Prep

#### F-VIDEO-001: Video Interview Practice

**Priority:** V2
**Timeline:** Q4 2026

**Description:** Practice answering interview questions on video with AI feedback.

**Functional Requirements:**

1. Video recording:

   - Record answers to predicted questions
   - Webcam and microphone access
   - Record multiple takes



2. AI feedback:

   - Transcribe video using speech-to-text
   - Analyze content quality
   - Evaluate delivery (pace, filler words)
   - Suggest improvements



3. Playback:

   - Watch recordings
   - Side-by-side comparison
   - Share with career coaches

---

### 6.3 Advanced Features (V2)

- **F-COLLABORATION-001:** Team Collaboration (Enterprise)
- **F-API-001:** API Access for HR Systems
- **F-MOBILE-001:** Mobile App (iOS \+ Android)
- **F-CAREER-COACH-001:** Career Coach Marketplace
- **F-AI-MATCHING-001:** AI Job Matching
- **F-SALARY-001:** Salary Negotiation Assistant
- **F-PORTFOLIO-001:** Portfolio Website Generator
- **F-LINKEDIN-001:** LinkedIn Profile Optimization

---

## 7\. TECHNICAL ARCHITECTURE OVERVIEW

### 7.1 AWS Services

Compute:

  \- AWS Lambda (22 functions)

  \- Python 3.11 runtime



Storage:

  \- DynamoDB (5 tables)

  \- S3 (5 buckets)



API:

  \- API Gateway (REST API)

  \- API Gateway (WebSocket API) \- V1.1



Authentication:

  \- AWS Cognito User Pools

  \- JWT tokens



Payments:

  \- Stripe API



Email:

  \- AWS SES



AI:

  \- Anthropic Claude API (Sonnet 4.5 \+ Haiku 4.5)

  \- Perplexity API (company research fallback)



Monitoring:

  \- CloudWatch Logs

  \- CloudWatch Alarms

  \- CloudWatch Dashboards



CI/CD:

  \- GitHub Actions

  \- CloudFormation/SAM

### 7.2 Lambda Functions Inventory (22 Total)

| Function Name | Purpose | Model | Memory | Timeout | Cost/Call |
| :---- | :---- | :---- | :---- | :---- | :---- |
| `auth-handler` | Authentication (register, login, reset) | N/A | 256MB | 10s | $0.0001 |
| `user-profile-handler` | User profile CRUD | N/A | 256MB | 5s | $0.00005 |
| `cv-upload-handler` | Process CV uploads | N/A | 512MB | 30s | $0.0003 |
| `cv-parser` | Extract facts from CV | Haiku 4.5 | 512MB | 30s | $0.001 |
| `job-posting-handler` | Process job posting input | N/A | 256MB | 10s | $0.0001 |
| `orchestrator` | Coordinate generation workflow | N/A | 512MB | 60s | $0.005 |
| `company-research-v1` | Hybrid web scraping \+ Perplexity | Varies | 512MB | 45s | $0.004 |
| `gap-analysis-questions` | Generate gap analysis questions | Sonnet 4.5 | 512MB | 30s | $0.003 |
| `vp-report-generator` | Generate VPR | Sonnet 4.5 | 1024MB | 120s | $0.035 |
| `cv-tailor` | Generate tailored CV | Haiku 4.5 | 512MB | 60s | $0.005 |
| `cover-letter-generator` | Generate cover letter | Haiku 4.5 | 512MB | 60s | $0.004 |
| `interview-prep-generator` | Generate interview prep | Haiku 4.5 | 512MB | 60s | $0.005 |
| `artifact-review-handler` | Handle user edits and regeneration | N/A | 512MB | 10s | $0.0001 |
| `docx-export` | Export to DOCX | N/A | 512MB | 30s | $0.0002 |
| `pdf-export` | Export to PDF | N/A | 512MB | 30s | $0.0002 |
| `stripe-webhook-handler` | Process Stripe events | N/A | 256MB | 10s | $0.0001 |
| `subscription-manager` | Manage subscriptions | N/A | 256MB | 10s | $0.0001 |
| `credit-manager` | Track free tier usage | N/A | 256MB | 5s | $0.00005 |
| `notification-handler` | Send email notifications | N/A | 256MB | 10s | $0.0001 |
| `admin-dashboard-api` | Admin data aggregation | N/A | 512MB | 10s | $0.0002 |
| `scheduled-cleanup` | Daily cleanup of expired data | N/A | 256MB | 60s | $0.0001 |
| `websocket-connect` | WebSocket connection handler (V1.1) | N/A | 256MB | 5s | $0.00005 |

**Total Lambda Cost per Application:** \~$0.002

---

### 7.3 DynamoDB Tables (5 Total)

| Table Name | Partition Key | Sort Key | GSIs | Purpose |
| :---- | :---- | :---- | :---- | :---- |
| `careervp-users` | userId | \- | email-index | User profiles, tiers, preferences |
| `careervp-cvs` | userId | cvId | \- | CV metadata and parsed facts |
| `careervp-applications` | userId | applicationId | status-index | Job applications and workflow state |
| `careervp-artifacts` | applicationId | artifactId | type-index | Generated documents (VPR, CV, Cover Letter, Interview Prep) |
| `careervp-subscriptions` | userId | \- | stripe\_id-index | Stripe subscription details |

**Additional Tables (Supporting):**

- `careervp-sessions` \- Draft state persistence (with tier-aware TTL fix)
- `careervp-company-research-cache` \- Cached company research (30-day TTL)
- `careervp-knowledge-base` \- Reusable user facts and responses
- `careervp-websocket-connections` \- WebSocket connectionIds (V1.1)

---

### 7.4 S3 Buckets (5 Total)

| Bucket Name | Purpose | Lifecycle Policy |
| :---- | :---- | :---- |
| `careervp-cv-uploads-{env}` | Original CV files | 90 days → IA, 365 days → Glacier |
| `careervp-artifacts-{env}` | Generated documents | 90 days → IA, 180 days → Glacier |
| `careervp-static-{env}` | Frontend assets (SPA) | No lifecycle |
| `careervp-backups-{env}` | Database backups | 30 days → IA, 90 days → Glacier |
| `careervp-logs-{env}` | CloudWatch log archive | 180 days → IA, 365 days → Glacier |

---

## 8\. DEVELOPMENT SPRINTS & TIMELINE

### 8.1 Sprint Breakdown (8 Sprints x 2 Weeks \= 16 Weeks \= 4 Months)

Sprint 0 (2 weeks): Infrastructure Setup

  \- AWS account setup

  \- CloudFormation templates

  \- CI/CD pipeline (GitHub Actions)

  \- Dev/Staging/Prod environments

  \- Monitoring and alerting setup



Sprint 1 (2 weeks): Authentication & User Management

  \- F-AUTH-001: User Registration

  \- F-AUTH-002: User Login

  \- F-AUTH-003: Password Reset

  \- Frontend: Auth pages



Sprint 2 (2 weeks): CV Management

  \- F-CV-001: CV Upload (with 3-page limit)

  \- F-CV-002: CV Parsing

  \- F-CV-003: CV Management

  \- Frontend: CV upload and management pages



Sprint 3 (2 weeks): Job Input & Company Research

  \- F-JOB-001: Job Posting Input (with validation popup)

  \- F-JOB-002: Company Research

  \- Frontend: Job input page with validation



Sprint 4 (2 weeks): Gap Analysis

  \- F-JOB-003: Gap Analysis Questions

  \- F-JOB-004: Gap Analysis Responses

  \- Frontend: Gap analysis page



Sprint 5 (2 weeks): Artifact Generation (Part 1\)

  \- F-JOB-005: VPR Generation (with gap responses)

  \- F-JOB-006: CV Tailoring

  \- F-LANG-001: Multi-Language Support (English \+ Hebrew)

  \- Frontend: Application status page



Sprint 6 (2 weeks): Artifact Generation (Part 2\) & Review

  \- F-JOB-007: Cover Letter Generation

  \- F-JOB-008: Interview Prep Generation (Docx default)

  \- F-REVIEW-001: Artifact Review (structured form)

  \- F-REVIEW-002: Artifact Regeneration

  \- F-ATS-001: ATS Compatibility Checker

  \- Frontend: Review and edit pages



Sprint 7 (2 weeks): Export & Subscriptions

  \- F-EXPORT-001: DOCX Export

  \- F-EXPORT-002: PDF Export

  \- F-SUBSCRIPTION-001: Stripe Integration

  \- F-SUBSCRIPTION-002: Usage Tracking

  \- Frontend: Subscription pages



Sprint 8 (2 weeks): Admin & Notifications

  \- F-ADMIN-001: Admin Dashboard

  \- F-NOTIFY-001: Email Notifications

  \- F-NOTIFY-002: Admin Alerts

  \- Testing & bug fixes

  \- Launch preparation

### 8.2 Timeline

Month 1 (Weeks 1-4):

  \- Sprint 0: Infrastructure

  \- Sprint 1: Authentication



Month 2 (Weeks 5-8):

  \- Sprint 2: CV Management

  \- Sprint 3: Job Input & Research



Month 3 (Weeks 9-12):

  \- Sprint 4: Gap Analysis

  \- Sprint 5: Artifact Generation (Part 1\)



Month 4 (Weeks 13-16):

  \- Sprint 6: Artifact Generation (Part 2\)

  \- Sprint 7: Export & Subscriptions

  \- Sprint 8: Admin & Launch Prep



Post-Launch (Months 5-6):

  \- V1.1: WebSocket Real-Time Updates

  \- V1.1: Collaborative Editing

  \- V1.1: User Analytics Dashboard

---

## 9\. ACCEPTANCE CRITERIA & TESTING

### 9.1 Testing Strategy

Unit Testing:

  \- Test individual Lambda functions

  \- Mock AWS services (DynamoDB, S3, SES)

  \- Test AI prompt parsing logic

  \- Coverage: 80%+



Integration Testing:

  \- Test end-to-end workflows

  \- Test Lambda → DynamoDB → S3 flows

  \- Test Stripe webhook handling

  \- Test email delivery



End-to-End (E2E) Testing:

  \- Automated browser tests (Playwright)

  \- Test complete user journeys

  \- Test all happy paths

  \- Test error scenarios



Performance Testing:

  \- Load test API endpoints

  \- Test Lambda cold starts

  \- Test concurrent user scenarios

  \- Target: 100 concurrent users



Security Testing:

  \- Penetration testing

  \- OWASP Top 10 checks

  \- Authentication/authorization tests

  \- Data encryption verification

### 9.2 Quality Gates

Code Quality:

  \- Linting: flake8 (Python), ESLint (JavaScript)

  \- Code review: Required for all PRs

  \- Test coverage: 80%+ required



Security:

  \- Secrets scanning (GitHub)

  \- Dependency vulnerability checks

  \- HTTPS only

  \- Input validation on all endpoints



Performance:

  \- API response time: \< 500ms (P95)

  \- Lambda execution time: Within timeout limits

  \- Cold start: \< 3 seconds

  \- Document generation: \< 3 minutes total



Compliance:

  \- GDPR checklist completed

  \- CCPA checklist completed

  \- Privacy policy published

  \- Terms of service published

---

## 10\. COST MODEL & PERFORMANCE TARGETS

### 10.1 Cost per Application

AI Model Costs:

  company-research-v1: $0.004 (Perplexity fallback)

  gap-analysis-questions: $0.003 (Sonnet 4.5)

  vp-report-generator: $0.035 (Sonnet 4.5)

  cv-tailor: $0.005 (Haiku 4.5)

  cover-letter-generator: $0.004 (Haiku 4.5)

  interview-prep-generator: $0.005 (Haiku 4.5)



  Total AI Costs: $0.056 per application

Lambda Costs:

  orchestrator: $0.001

  supporting functions: $0.001



  Total Lambda: $0.002 per application

Grand Total: $0.058 per application

### 10.2 Monthly Operational Costs

Scenario: 1,000 users, 10,000 applications/month

AI & Lambda:

  Processing: $580 (10,000 apps × $0.058)



Infrastructure:

  DynamoDB: $50 (on-demand, light usage)

  S3 storage: $30 (uploads \+ artifacts)

  API Gateway: $10 (REST \+ WebSocket)

  CloudWatch: $20 (logs \+ metrics)

  AWS Cognito: $10 (1,000 MAUs)

  AWS SES: $5 (email sending)

  Stripe: $150 (2.9% \+ $0.30 per transaction)



Total Monthly Cost: \~$855

Revenue (1,000 users @ $25/month): $25,000

Profit Margin: 96.6% ✅

### 10.3 Performance Targets

API Endpoints:

  Authentication: \< 200ms (P95)

  CV Upload: \< 1s (P95)

  Job Input: \< 300ms (P95)

  Artifact Generation: \< 3 minutes total (P95)

  Download Links: \< 100ms (P95)



Lambda Functions:

  Cold Start: \< 3s

  Warm Start: \< 500ms



Document Generation:

  Company Research: \< 45s

  Gap Analysis Questions: \< 30s

  VPR Generation: \< 120s

  CV Tailoring: \< 60s

  Cover Letter: \< 60s

  Interview Prep: \< 60s



  Total Processing Time: \< 5 minutes (all artifacts)



User Experience:

  Page Load Time: \< 2s

  Time to Interactive: \< 3s

  First Contentful Paint: \< 1s



Availability:

  Uptime: 99.9% (8.76 hours downtime/year)

  Error Rate: \< 0.1%

---

## 11\. CRITICAL ISSUES & RESOLUTIONS

### 11.1 Identified Issues

| Issue | Priority | Status | Resolution |
| :---- | :---- | :---- | :---- |
| **TTL Data Retention Bug** | 🔴 CRITICAL | ✅ FIXED | Implement tier-aware deletion: Free tier 90 days inactivity, paid users indefinite retention |
| **CV Page Limit** | 🟡 MEDIUM | ✅ IMPLEMENTED | Enforce 3-page maximum with error message during upload |
| **Language Consistency** | 🟡 MEDIUM | ✅ IMPLEMENTED | Generate artifacts in both languages when CV/job languages differ |
| **Gap Responses Integration** | 🟢 LOW | ✅ IMPLEMENTED | Gap analysis responses integrated into VPR generation as input data |

---

## 12\. NEXT STEPS

### 12.1 Development Process

1. **Review & Approval:**

   - ✅ Context Manifest approved
   - ✅ Technical Features List approved
   - ⏳ Begin Sprint 0: Infrastructure setup



2. **Implementation:**

   - Use Claude Code for complex business logic
   - Use OpenAI Codex for boilerplate code
   - Follow sprint plan (8 sprints × 2 weeks)
   - Daily standups and weekly demos



3. **Testing:**

   - Write tests as you build (TDD encouraged)
   - Automated testing in CI/CD pipeline
   - Manual QA for UI/UX
   - Beta testing before launch



4. **Launch:**

   - Soft launch to beta users (100 users)
   - Gather feedback and iterate
   - Public launch (marketing campaign)
   - Monitor metrics and costs

### 12.2 Documentation Deliverables

✅ **COMPLETE:**

1. CareerVP\_Technical\_Features\_FINAL.md (this document)

⏳ **TODO:** 2\. CareerVP\_PRD.md (Product Requirements Document) 3\. CareerVP\_Spec\_Kit/ (Component specifications)

- API\_Specification.md
- Database\_Schema.md
- Lambda\_Functions\_Spec.md
- Frontend\_Components.md
- Integration\_Spec.md
4. CareerVP\_Sprint\_Plan.md (Detailed sprint tasks)
5. CareerVP\_Testing\_Plan.md (Comprehensive testing strategy)

---

## APPENDIX

### A. Glossary

- **ATS:** Applicant Tracking System
- **VPR:** Value Proposition Report
- **GSI:** Global Secondary Index (DynamoDB)
- **TTL:** Time To Live (DynamoDB auto-deletion)
- **JWT:** JSON Web Token
- **SES:** Simple Email Service (AWS)
- **SNS:** Simple Notification Service (AWS)
- **SQS:** Simple Queue Service (AWS)
- **IAM:** Identity and Access Management (AWS)
- **CORS:** Cross-Origin Resource Sharing
- **HTTPS:** Hypertext Transfer Protocol Secure
- **SSE:** Server-Side Encryption
- **KMS:** Key Management Service (AWS)

---

**Document Status:** ✅ APPROVED \- Ready for Development
**Last Updated:** January 22, 2026
**Version:** 1.0 FINAL
**Total Features:** 52 (V1: 36 | V1.1: 4 | V2: 12\)
**Estimated Development Time:** 4 months (Sprint 0-8)
**Target Launch:** Q2 2026

---

**END OF DOCUMENT**
