# Knowledge Base Technical Specification

**Document Version:** 1.0.0
**Date:** 2026-02-09
**Status:** Draft
**Related Documents:**
- `docs/architecture/jsa-skill-alignment/IMPLEMENTATION_ANALYSIS.md`
- `docs/architecture/jsa-skill-alignment/JSA-Skill-Alignment-Plan.md`

---

## 1. Executive Summary

The Knowledge Base is a **cross-application memory system** that enables CareerVP to remember user information across multiple job applications. This component was present in the original JSA (Job Search Assistant) Skill but was omitted from the CareerVP initial design.

### Problem Statement

Without a Knowledge Base, users must repeatedly answer the same questions across different job applications because the system has no memory of:
- Their recurring strengths and expertise areas
- Previous gap analysis responses
- Identified differentiators from past VPRs
- Interview notes and company research

### Solution

A dedicated DynamoDB table that stores user knowledge by type, enabling:
- Memory-aware gap analysis (skip known topics)
- Consistent differentiators across applications
- Cumulative learning about user's career narrative

---

## 2. Architecture

### 2.1 Data Model

```
Table: careervp-knowledge-base-{stage}

┌─────────────────┬─────────────────┬──────────────────────────────┐
│ PK (userEmail)  │ SK (knowledgeType) │ Attributes                │
├─────────────────┼─────────────────┼──────────────────────────────┤
│ user@example.com│ recurring_themes│ data, applications_count,   │
│                 │                 │ created_at, updated_at, ttl │
├─────────────────┼─────────────────┼──────────────────────────────┤
│ user@example.com│ gap_responses   │ data, applications_count,   │
│                 │                 │ created_at, updated_at, ttl │
├─────────────────┼─────────────────┼──────────────────────────────┤
│ user@example.com│ differentiators │ data, applications_count,   │
│                 │                 │ created_at, updated_at, ttl │
├─────────────────┼─────────────────┼──────────────────────────────┤
│ user@example.com│ interview_notes#│ data, company, created_at,  │
│                 │ {company_slug}  │ updated_at, ttl             │
├─────────────────┼─────────────────┼──────────────────────────────┤
│ user@example.com│ company_notes#  │ data, company, created_at,  │
│                 │ {company_slug}  │ updated_at, ttl             │
└─────────────────┴─────────────────┴──────────────────────────────┘
```

### 2.2 Why Separate Table?

| Aspect | Existing Tables | Knowledge Base |
|--------|-----------------|----------------|
| **PK** | `user_id` or `application_id` | `userEmail` |
| **Access Pattern** | Per-application | Cross-application |
| **TTL** | 90 days | 365 days |
| **Schema** | Artifact-specific | Knowledge-specific |
| **Purpose** | Store outputs | Store learning |

### 2.3 Knowledge Types

| Type | Purpose | Schema |
|------|---------|--------|
| `recurring_themes` | Topics to skip in gap analysis | `list[str]` |
| `gap_responses` | Previous answers to avoid repetition | `list[GapResponse]` |
| `differentiators` | VPR-identified strengths | `list[str]` |
| `interview_notes#{company}` | Post-interview reflections | `str` |
| `company_notes#{company}` | Research notes | `str` |

---

## 3. DynamoDB Table Specification

### 3.1 Table Configuration

```python
# CDK Definition
Table(
    self,
    "KnowledgeBaseTable",
    table_name=f"careervp-knowledge-base-{stage}",
    partition_key=Attribute(name="userEmail", type=AttributeType.STRING),
    sort_key=Attribute(name="knowledgeType", type=AttributeType.STRING),
    billing_mode=BillingMode.PAY_PER_REQUEST,
    removal_policy=RemovalPolicy.RETAIN,
    time_to_live_attribute="ttl",
    point_in_time_recovery=True,
)
```

### 3.2 Attribute Definitions

| Attribute | Type | Required | Description |
|-----------|------|----------|-------------|
| `userEmail` | String | Yes | Partition key - user's email |
| `knowledgeType` | String | Yes | Sort key - type of knowledge |
| `data` | Map/List | Yes | Type-specific payload |
| `applications_count` | Number | No | Number of applications using this |
| `created_at` | String | Yes | ISO 8601 timestamp |
| `updated_at` | String | Yes | ISO 8601 timestamp |
| `ttl` | Number | Yes | Unix timestamp for expiration |
| `company` | String | No | Company name (for notes) |
| `version` | Number | No | Schema version for migrations |

### 3.3 TTL Policy

- **Default TTL:** 365 days (31536000 seconds)
- **Rationale:** Knowledge should persist longer than draft artifacts (90 days)
- **Renewal:** TTL extends on each update

---

## 4. Data Schemas

### 4.1 Recurring Themes

```python
class RecurringThemesData(BaseModel):
    """Topics user has established expertise in."""
    themes: list[str]  # e.g., ["AWS", "Python", "Team Leadership"]
    sources: list[str]  # Which applications contributed
    confidence: dict[str, float]  # theme -> confidence score (0-1)

# Example
{
    "userEmail": "user@example.com",
    "knowledgeType": "recurring_themes",
    "data": {
        "themes": ["AWS", "Python", "Team Leadership", "Agile"],
        "sources": ["app_123", "app_456", "app_789"],
        "confidence": {
            "AWS": 0.95,
            "Python": 0.90,
            "Team Leadership": 0.85,
            "Agile": 0.70
        }
    },
    "applications_count": 3,
    "created_at": "2026-01-15T10:00:00Z",
    "updated_at": "2026-02-09T14:30:00Z",
    "ttl": 1770681000
}
```

### 4.2 Gap Responses

```python
class GapResponseData(BaseModel):
    """Previous gap analysis responses."""
    responses: list[GapResponse]

class GapResponse(BaseModel):
    question_hash: str  # Hash of question for deduplication
    question: str
    response: str
    category: str  # QUANTIFY, EXAMPLE, CLARIFY, FILL_GAP
    destination: str  # CV_IMPACT or INTERVIEW_MVP_ONLY
    application_id: str
    created_at: str

# Example
{
    "userEmail": "user@example.com",
    "knowledgeType": "gap_responses",
    "data": {
        "responses": [
            {
                "question_hash": "abc123",
                "question": "How many engineers did you lead?",
                "response": "I led a team of 8 engineers...",
                "category": "QUANTIFY",
                "destination": "CV_IMPACT",
                "application_id": "app_123",
                "created_at": "2026-01-15T10:00:00Z"
            }
        ]
    },
    "applications_count": 5,
    "created_at": "2026-01-15T10:00:00Z",
    "updated_at": "2026-02-09T14:30:00Z",
    "ttl": 1770681000
}
```

### 4.3 Differentiators

```python
class DifferentiatorsData(BaseModel):
    """VPR-identified unique strengths."""
    differentiators: list[Differentiator]

class Differentiator(BaseModel):
    text: str
    frequency: int  # How many VPRs identified this
    source_applications: list[str]

# Example
{
    "userEmail": "user@example.com",
    "knowledgeType": "differentiators",
    "data": {
        "differentiators": [
            {
                "text": "Cloud architecture expertise with AWS certifications",
                "frequency": 4,
                "source_applications": ["app_123", "app_456", "app_789", "app_012"]
            },
            {
                "text": "Track record of reducing cloud costs by 30%+",
                "frequency": 3,
                "source_applications": ["app_123", "app_456", "app_789"]
            }
        ]
    },
    "applications_count": 4,
    "created_at": "2026-01-15T10:00:00Z",
    "updated_at": "2026-02-09T14:30:00Z",
    "ttl": 1770681000
}
```

### 4.4 Interview Notes

```python
class InterviewNotesData(BaseModel):
    """Post-interview reflections for a company."""
    notes: str
    interview_date: str
    interview_type: str  # phone, technical, behavioral, onsite
    interviewers: list[str]
    questions_asked: list[str]
    what_went_well: list[str]
    areas_to_improve: list[str]

# Example
{
    "userEmail": "user@example.com",
    "knowledgeType": "interview_notes#acme-corp",
    "data": {
        "notes": "Good conversation about cloud architecture...",
        "interview_date": "2026-02-01",
        "interview_type": "technical",
        "interviewers": ["Jane Smith", "John Doe"],
        "questions_asked": ["Tell me about a time...", "How would you design..."],
        "what_went_well": ["System design explanation", "Team leadership examples"],
        "areas_to_improve": ["Could have quantified cost savings better"]
    },
    "company": "Acme Corp",
    "created_at": "2026-02-01T16:00:00Z",
    "updated_at": "2026-02-01T16:00:00Z",
    "ttl": 1770681000
}
```

### 4.5 Company Notes

```python
class CompanyNotesData(BaseModel):
    """Research notes about a company."""
    notes: str
    research_date: str
    sources: list[str]
    key_insights: list[str]
    culture_notes: str
    recent_news: list[str]

# Example
{
    "userEmail": "user@example.com",
    "knowledgeType": "company_notes#acme-corp",
    "data": {
        "notes": "Acme Corp is expanding into cloud services...",
        "research_date": "2026-01-20",
        "sources": ["LinkedIn", "Glassdoor", "Company Blog"],
        "key_insights": ["Focus on AI/ML", "Remote-first culture"],
        "culture_notes": "Values innovation and work-life balance",
        "recent_news": ["Series C funding", "New CTO hired"]
    },
    "company": "Acme Corp",
    "created_at": "2026-01-20T10:00:00Z",
    "updated_at": "2026-01-25T14:00:00Z",
    "ttl": 1770681000
}
```

---

## 5. Repository Interface

### 5.1 File Location

```
src/backend/careervp/dal/knowledge_base_repository.py
```

### 5.2 Class Definition

```python
from typing import Optional
from careervp.models.knowledge_base import (
    RecurringThemesData,
    GapResponseData,
    GapResponse,
    DifferentiatorsData,
    InterviewNotesData,
    CompanyNotesData,
)

class KnowledgeBaseRepository:
    """Repository for user knowledge persistence."""

    def __init__(self, table_name: str):
        self.table_name = table_name
        self.table = boto3.resource("dynamodb").Table(table_name)

    # ─────────────────────────────────────────────────────────────
    # Recurring Themes
    # ─────────────────────────────────────────────────────────────

    def load_recurring_themes(self, user_email: str) -> list[str]:
        """Load user's recurring expertise themes."""
        ...

    def save_recurring_themes(
        self,
        user_email: str,
        themes: list[str],
        source_application: str,
    ) -> None:
        """Save/update recurring themes (merge with existing)."""
        ...

    def add_recurring_theme(
        self,
        user_email: str,
        theme: str,
        confidence: float,
        source_application: str,
    ) -> None:
        """Add a single theme with confidence score."""
        ...

    # ─────────────────────────────────────────────────────────────
    # Gap Responses
    # ─────────────────────────────────────────────────────────────

    def load_gap_responses(
        self,
        user_email: str,
        limit: int = 50,
    ) -> list[GapResponse]:
        """Load previous gap responses for deduplication."""
        ...

    def save_gap_responses(
        self,
        user_email: str,
        responses: list[GapResponse],
        application_id: str,
    ) -> None:
        """Save new gap responses (append to existing)."""
        ...

    def find_similar_response(
        self,
        user_email: str,
        question_hash: str,
    ) -> Optional[GapResponse]:
        """Find if user already answered a similar question."""
        ...

    # ─────────────────────────────────────────────────────────────
    # Differentiators
    # ─────────────────────────────────────────────────────────────

    def load_differentiators(self, user_email: str) -> list[str]:
        """Load user's identified differentiators."""
        ...

    def save_differentiators(
        self,
        user_email: str,
        differentiators: list[str],
        application_id: str,
    ) -> None:
        """Save/update differentiators (merge with existing)."""
        ...

    # ─────────────────────────────────────────────────────────────
    # Interview Notes
    # ─────────────────────────────────────────────────────────────

    def load_interview_notes(
        self,
        user_email: str,
        company_slug: str,
    ) -> Optional[InterviewNotesData]:
        """Load interview notes for a company."""
        ...

    def save_interview_notes(
        self,
        user_email: str,
        company_slug: str,
        notes: InterviewNotesData,
    ) -> None:
        """Save interview notes for a company."""
        ...

    def list_interview_notes(
        self,
        user_email: str,
    ) -> list[tuple[str, str]]:
        """List all companies with interview notes (company_slug, company_name)."""
        ...

    # ─────────────────────────────────────────────────────────────
    # Company Notes
    # ─────────────────────────────────────────────────────────────

    def load_company_notes(
        self,
        user_email: str,
        company_slug: str,
    ) -> Optional[CompanyNotesData]:
        """Load research notes for a company."""
        ...

    def save_company_notes(
        self,
        user_email: str,
        company_slug: str,
        notes: CompanyNotesData,
    ) -> None:
        """Save research notes for a company."""
        ...

    # ─────────────────────────────────────────────────────────────
    # Utility Methods
    # ─────────────────────────────────────────────────────────────

    def delete_user_knowledge(self, user_email: str) -> int:
        """Delete all knowledge for a user (GDPR). Returns count deleted."""
        ...

    def get_knowledge_summary(self, user_email: str) -> dict:
        """Get summary of all knowledge types for a user."""
        ...
```

---

## 6. Integration Points

### 6.1 Gap Analysis Integration

**File:** `src/backend/careervp/handlers/gap_handler.py`

```python
async def lambda_handler(event: dict, context: Any) -> dict:
    # Extract user email from request/auth
    user_email = extract_user_email(event)

    # Load knowledge for memory-aware questioning
    kb_repo = KnowledgeBaseRepository(table_name=KB_TABLE_NAME)
    recurring_themes = kb_repo.load_recurring_themes(user_email)
    previous_responses = kb_repo.load_gap_responses(user_email)

    # Generate questions with knowledge context
    questions = await generate_gap_questions(
        cv_facts=cv_facts,
        job_requirements=job_requirements,
        recurring_themes=recurring_themes,  # NEW
        previous_responses=previous_responses,  # NEW
    )

    return {"questions": questions}
```

**Prompt Integration:**

```python
GAP_ANALYSIS_PROMPT = """...

USER'S RECURRING THEMES (SKIP THESE TOPICS):
{recurring_themes}

PREVIOUS GAP RESPONSES (DO NOT REPEAT):
{previous_gap_responses_json}

CRITICAL: Skip questions about topics in recurring_themes.
CRITICAL: Do not ask questions similar to previous_gap_responses.

..."""
```

### 6.2 VPR Integration

**File:** `src/backend/careervp/handlers/vpr_handler.py`

```python
async def lambda_handler(event: dict, context: Any) -> dict:
    # ... existing VPR generation ...

    vpr_response = await generate_vpr(...)

    # Save differentiators to Knowledge Base
    user_email = extract_user_email(event)
    kb_repo = KnowledgeBaseRepository(table_name=KB_TABLE_NAME)
    kb_repo.save_differentiators(
        user_email=user_email,
        differentiators=vpr_response.differentiators,
        application_id=application_id,
    )

    # Extract and save recurring themes from VPR content
    themes = extract_themes_from_vpr(vpr_response)
    kb_repo.save_recurring_themes(
        user_email=user_email,
        themes=themes,
        source_application=application_id,
    )

    return vpr_response
```

### 6.3 Integration Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                    User Starts New Application                  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  Gap Analysis Handler                                           │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ 1. Load recurring_themes from Knowledge Base            │   │
│  │ 2. Load previous_gap_responses from Knowledge Base      │   │
│  │ 3. Generate questions (skip known topics)               │   │
│  │ 4. Return fewer, more targeted questions                │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  User Answers Gap Questions                                     │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  Gap Response Handler (after user submits)                      │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ 1. Save gap_responses to Knowledge Base                 │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  VPR Handler                                                    │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ 1. Generate VPR with gap responses                      │   │
│  │ 2. Extract differentiators from VPR                     │   │
│  │ 3. Save differentiators to Knowledge Base               │   │
│  │ 4. Extract recurring_themes from VPR content            │   │
│  │ 5. Update recurring_themes in Knowledge Base            │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  Interview Prep Handler (future)                                │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ 1. Load interview_notes for company (if exists)         │   │
│  │ 2. Reference previous interview experiences             │   │
│  │ 3. Generate tailored prep materials                     │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

---

## 7. Implementation Tasks

### Phase 1: Infrastructure (2 hours)

| Task | Description | File |
|------|-------------|------|
| KB-CDK-001 | Create DynamoDB table construct | `infra/careervp/knowledge_base_construct.py` |
| KB-CDK-002 | Add table to main stack | `infra/careervp/careervp_stack.py` |
| KB-CDK-003 | Grant Lambda permissions | `infra/careervp/api_construct.py` |

### Phase 2: Repository (3 hours)

| Task | Description | File |
|------|-------------|------|
| KB-REPO-001 | Create Pydantic models | `src/backend/careervp/models/knowledge_base.py` |
| KB-REPO-002 | Implement repository class | `src/backend/careervp/dal/knowledge_base_repository.py` |
| KB-REPO-003 | Add unit tests | `tests/unit/dal/test_knowledge_base_repository.py` |

### Phase 3: Integration (3 hours)

| Task | Description | File |
|------|-------------|------|
| KB-INT-001 | Integrate with Gap Analysis | `src/backend/careervp/handlers/gap_handler.py` |
| KB-INT-002 | Update Gap Analysis prompt | `src/backend/careervp/logic/prompts/gap_analysis_prompt.py` |
| KB-INT-003 | Integrate with VPR handler | `src/backend/careervp/handlers/vpr_handler.py` |
| KB-INT-004 | Add integration tests | `tests/integration/test_knowledge_base_integration.py` |

---

## 8. Testing Strategy

### 8.1 Unit Tests

```python
# tests/unit/dal/test_knowledge_base_repository.py

class TestKnowledgeBaseRepository:
    def test_save_and_load_recurring_themes(self): ...
    def test_merge_recurring_themes(self): ...
    def test_save_and_load_gap_responses(self): ...
    def test_find_similar_response(self): ...
    def test_save_and_load_differentiators(self): ...
    def test_merge_differentiators(self): ...
    def test_save_and_load_interview_notes(self): ...
    def test_save_and_load_company_notes(self): ...
    def test_delete_user_knowledge(self): ...
    def test_get_knowledge_summary(self): ...
    def test_ttl_is_set_correctly(self): ...
```

### 8.2 Integration Tests

```python
# tests/integration/test_knowledge_base_integration.py

class TestKnowledgeBaseIntegration:
    def test_gap_analysis_uses_recurring_themes(self): ...
    def test_gap_analysis_skips_previous_responses(self): ...
    def test_vpr_saves_differentiators(self): ...
    def test_vpr_updates_recurring_themes(self): ...
    def test_cross_application_memory(self): ...
```

### 8.3 Validation Commands

```bash
# Run Knowledge Base tests
cd src/backend
PYTHONPATH=$(pwd) uv run pytest ../../tests/unit/dal/test_knowledge_base_repository.py -v
PYTHONPATH=$(pwd) uv run pytest ../../tests/integration/test_knowledge_base_integration.py -v

# Run JSA alignment tests for Knowledge Base
PYTHONPATH=$(pwd) uv run pytest ../../tests/jsa_skill_alignment/test_knowledge_base_alignment.py -v
```

---

## 9. Security Considerations

### 9.1 Data Privacy

- Knowledge Base contains **personal career data**
- Must comply with GDPR (right to deletion)
- `delete_user_knowledge()` method required for account deletion

### 9.2 Access Control

- Lambda functions access via IAM role
- No direct API endpoint for Knowledge Base (internal only)
- User can only access their own knowledge (enforced by userEmail key)

### 9.3 Data Encryption

- DynamoDB encryption at rest (AWS managed)
- HTTPS for all API calls (encryption in transit)

---

## 10. Cost Analysis

### 10.1 DynamoDB Costs (On-Demand)

| Operation | Price | Est. Monthly Usage | Monthly Cost |
|-----------|-------|-------------------|--------------|
| Write | $1.25/million | 10,000 writes | $0.0125 |
| Read | $0.25/million | 50,000 reads | $0.0125 |
| Storage | $0.25/GB | 1 GB | $0.25 |
| **Total** | | | **~$0.28/month** |

### 10.2 Scaling Estimate

| Users | Writes/month | Reads/month | Storage | Monthly Cost |
|-------|--------------|-------------|---------|--------------|
| 100 | 1,000 | 5,000 | 0.1 GB | ~$0.05 |
| 1,000 | 10,000 | 50,000 | 1 GB | ~$0.28 |
| 10,000 | 100,000 | 500,000 | 10 GB | ~$2.80 |

---

## 11. Future Enhancements

### 11.1 Phase 2 Features

- **Knowledge Export:** Allow users to export their knowledge
- **Knowledge Import:** Import from other career tools
- **Shared Knowledge:** Team/organization knowledge sharing
- **AI-Suggested Themes:** Auto-suggest themes based on CV

### 11.2 Analytics

- Track knowledge usage patterns
- Identify most valuable knowledge types
- Measure impact on user success rates

---

## Appendix A: File Structure

```
src/backend/careervp/
├── dal/
│   ├── knowledge_base_repository.py  # NEW
│   └── ...
├── logic/
│   ├── knowledge_base.py             # NEW (business logic)
│   └── ...
├── models/
│   ├── knowledge_base.py             # NEW (Pydantic models)
│   └── ...
└── handlers/
    ├── gap_handler.py                # MODIFY (integration)
    └── vpr_handler.py                # MODIFY (integration)

infra/careervp/
├── knowledge_base_construct.py       # NEW (CDK)
└── careervp_stack.py                 # MODIFY (add construct)

tests/
├── unit/dal/
│   └── test_knowledge_base_repository.py  # NEW
├── integration/
│   └── test_knowledge_base_integration.py # NEW
└── jsa_skill_alignment/
    └── test_knowledge_base_alignment.py   # EXISTS
```

---

## Appendix B: Environment Variables

```bash
# Lambda environment variables
KNOWLEDGE_BASE_TABLE_NAME=careervp-knowledge-base-{stage}
KNOWLEDGE_BASE_TTL_DAYS=365
```

---

**END OF SPECIFICATION**
