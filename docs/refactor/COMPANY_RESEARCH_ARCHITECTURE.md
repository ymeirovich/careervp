# Company Research Transformation Layer - Architecture Design

**Version:** 1.0
**Date:** 2026-02-14
**Author:** Principal Software Architect
**Status:** Design Complete - Awaiting Implementation

---

## Executive Summary

### Problem Statement

CareerVP's company research feature faces a critical schema mismatch between LLM-generated outputs and DynamoDB storage requirements. The LLM generates structured JSON with 6 specific fields (`overview`, `values`, `mission`, `strategic_priorities`, `recent_news`, `financial_summary`), but the existing `knowledge_base_spec.yaml` expects a single `research_data` JSON blob with only metadata fields (`company_name`, `research_data`, `cached_at`). Without a transformation layer, we cannot:

1. Store company research in the knowledge table per Phase 8 requirements
2. Enable GSI queries by entity type and company name
3. Support TTL-based cache expiration (30 days)
4. Preserve all LLM-generated fields for future retrieval

### Proposed Solution

Implement a **bidirectional transformation layer** that bridges LLM output ↔ DynamoDB storage:

1. **Canonical Schema** - `CompanyResearchData` Pydantic model defining the complete data contract
2. **Transformer Class** - `CompanyResearchTransformer` handling serialization/deserialization
3. **Repository Updates** - Enhanced `KnowledgeRepository` with type-safe company research methods
4. **Validation Integration** - FVS quality checks before storage

This design enables:
- ✅ Preserves all 6 LLM fields in `research_data` JSON blob
- ✅ Supports GSI queries via `entity_type="company_research"` + `entity_id=<company_name>`
- ✅ 30-day TTL auto-expiration
- ✅ Type-safe transformations with Pydantic validation
- ✅ FVS compliance for generated content

### Key Architectural Decisions

| Decision | Rationale |
|----------|-----------|
| **Store as JSON blob** | DynamoDB best practice for semi-structured data; enables schema evolution |
| **Separate metadata from content** | PK/SK/GSI fields (user_email, entity_type, entity_id) enable queries; research_data holds full content |
| **Bidirectional transformer** | Enables round-trip serialization without data loss |
| **Pydantic for validation** | Consistent with codebase patterns; automatic JSON serialization |
| **TTL at item level** | Standard DynamoDB pattern for cache expiration |
| **FVS integration** | Ensures quality before storage; prevents AI-generated hallucinations |

---

## Data Flow Diagram

```
┌─────────────────┐
│  LLM Bedrock    │
│  (Sonnet 4.5)   │
└────────┬────────┘
         │ Returns JSON:
         │ {overview, values, mission, ...}
         ▼
┌─────────────────────────────────┐
│ CompanyResearchData (Pydantic)  │
│ - Validates field types         │
│ - Ensures required fields       │
│ - Normalizes optional fields    │
└────────┬────────────────────────┘
         │
         ▼
┌─────────────────────────────────┐
│ FVSValidator                    │
│ - Quality scoring (grammar,     │
│   tone, anti-AI patterns)       │
│ - Threshold enforcement         │
└────────┬────────────────────────┘
         │ Pass → Continue
         │ Fail → Reject
         ▼
┌─────────────────────────────────┐
│ CompanyResearchTransformer      │
│ to_dynamodb_item():             │
│ - Extract metadata fields       │
│ - Serialize research_data blob  │
│ - Calculate TTL (30 days)       │
│ - Add timestamps                │
└────────┬────────────────────────┘
         │
         ▼
┌─────────────────────────────────┐
│ KnowledgeRepository             │
│ save_company_research():        │
│ - Write to DynamoDB             │
│ - Handle errors → Result        │
└────────┬────────────────────────┘
         │
         ▼
┌─────────────────────────────────┐
│ DynamoDB: knowledge-table-dev   │
│ PK: user_email                  │
│ SK: entity_type#company_name    │
│ Attributes:                     │
│  - entity_id: company_name      │
│  - cached_at: ISO timestamp     │
│  - ttl: Unix timestamp          │
│  - research_data: JSON blob     │
│ GSI: entity-index               │
│  (entity_type → entity_id)      │
└─────────────────────────────────┘

┌─ RETRIEVAL PATH ─┐

get_company_research(company_name) →
  Query DynamoDB (PK + SK) →
    CompanyResearchTransformer.from_dynamodb_item() →
      Deserialize research_data blob →
        CompanyResearchData (Pydantic)
```

---

## Schema Mapping

### LLM Output → DB Storage

| LLM Field | DB Field | Transformation | Notes |
|-----------|----------|----------------|-------|
| `company_name` | `entity_id` | Direct copy (normalized) | Used as company identifier |
| `overview` | `research_data.overview` | Stored in JSON blob | Required field |
| `values` | `research_data.values` | Stored in JSON blob | List[str], defaults to [] |
| `mission` | `research_data.mission` | Stored in JSON blob | Optional string |
| `strategic_priorities` | `research_data.strategic_priorities` | Stored in JSON blob | List[str], defaults to [] |
| `recent_news` | `research_data.recent_news` | Stored in JSON blob | List[str], defaults to [] |
| `financial_summary` | `research_data.financial_summary` | Stored in JSON blob | Optional string |
| *(generated)* | `user_email` | From context (Lambda authorizer) | Partition key |
| *(generated)* | `entity_type` | Constant: `"company_research"` | Sort key component |
| *(generated)* | `cached_at` | `datetime.now(UTC).isoformat()` | ISO-8601 timestamp |
| *(generated)* | `ttl` | `int(time.time()) + (30 * 86400)` | Unix timestamp (30 days) |
| *(ALL fields)* | `research_data` | `json.dumps(model.model_dump())` | Complete JSON blob |

### DynamoDB Item Structure

```json
{
  "user_email": "user@example.com",
  "entity_type": "company_research#TechCorp",
  "entity_id": "TechCorp",
  "cached_at": "2026-02-14T10:30:00Z",
  "ttl": 1739615400,
  "research_data": "{\"company_name\":\"TechCorp\",\"overview\":\"Leading tech company...\",\"values\":[\"Innovation\",\"Integrity\"],\"mission\":\"Empower businesses...\",\"strategic_priorities\":[\"AI expansion\"],\"recent_news\":[\"Series B funding\"],\"financial_summary\":\"Revenue $50M\"}"
}
```

### GSI Query Pattern

```python
# Query all company research records
response = table.query(
    IndexName="entity-index",
    KeyConditionExpression="entity_type = :type",
    ExpressionAttributeValues={":type": "company_research"}
)

# Query specific company across all users
response = table.query(
    IndexName="entity-index",
    KeyConditionExpression="entity_type = :type AND entity_id = :id",
    ExpressionAttributeValues={
        ":type": "company_research",
        ":id": "TechCorp"
    }
)
```

---

## Deliverable 1: CompanyResearchData Pydantic Model

**File:** `src/backend/careervp/models/company_research.py`

### Class Design

```python
"""Company research data models.

This module defines the canonical schema for company research data,
supporting both LLM input format and DynamoDB storage format.

Patterns:
- Immutability: Model is frozen after validation
- Required vs Optional: overview required, all others optional
- List Defaults: Empty lists for missing data
- Validation: Field-level constraints on string lengths
"""

from datetime import datetime, timezone
from typing import Annotated

from pydantic import BaseModel, Field, field_validator


class CompanyResearchData(BaseModel):
    """Company research data from LLM or database.

    This model represents the complete company research schema,
    supporting both LLM output and DynamoDB storage retrieval.

    Fields match the output schema from company_research.py prompt.
    All 6 LLM fields are preserved in this model.

    Attributes:
        company_name: Normalized company name (max 200 chars)
        overview: Required 100-200 word company summary
        values: List of company values/principles
        mission: Optional mission statement
        strategic_priorities: List of current strategic focuses
        recent_news: List of recent company news items
        financial_summary: Optional financial overview
        researched_at: Timestamp when research was performed (UTC)
    """

    company_name: Annotated[
        str,
        Field(
            description="Company name (normalized, no special chars)",
            min_length=1,
            max_length=200,
        ),
    ]

    overview: Annotated[
        str,
        Field(
            description="100-200 word company summary (REQUIRED)",
            min_length=50,
            max_length=1000,
        ),
    ]

    values: Annotated[
        list[str],
        Field(
            default_factory=list,
            description="Company values and principles",
        ),
    ]

    mission: Annotated[
        str | None,
        Field(
            default=None,
            description="Mission statement",
            max_length=500,
        ),
    ]

    strategic_priorities: Annotated[
        list[str],
        Field(
            default_factory=list,
            description="Current strategic priorities",
        ),
    ]

    recent_news: Annotated[
        list[str],
        Field(
            default_factory=list,
            description="Recent company news items",
        ),
    ]

    financial_summary: Annotated[
        str | None,
        Field(
            default=None,
            description="Financial overview",
            max_length=500,
        ),
    ]

    researched_at: Annotated[
        datetime,
        Field(
            default_factory=lambda: datetime.now(timezone.utc),
            description="Research timestamp (UTC)",
        ),
    ]

    @field_validator("company_name")
    @classmethod
    def _normalize_company_name(cls, v: str) -> str:
        """Normalize company name for consistent storage.

        Strips whitespace and ensures non-empty after normalization.
        """
        normalized = v.strip()
        if not normalized:
            raise ValueError("Company name cannot be empty after normalization")
        return normalized

    @field_validator("values", "strategic_priorities", "recent_news")
    @classmethod
    def _filter_empty_strings(cls, v: list[str]) -> list[str]:
        """Remove empty/whitespace-only strings from lists."""
        return [item.strip() for item in v if item.strip()]

    model_config = {
        "frozen": False,  # Allow mutation for repository layer
        "str_strip_whitespace": True,  # Auto-strip all string fields
        "json_schema_extra": {
            "examples": [
                {
                    "company_name": "TechCorp Solutions",
                    "overview": "TechCorp is a leading provider of cloud-based enterprise solutions...",
                    "values": ["Innovation", "Integrity", "Customer Focus"],
                    "mission": "Empower businesses through technology",
                    "strategic_priorities": ["AI integration", "Global expansion"],
                    "recent_news": ["Series B funding $50M", "New VP of Engineering hired"],
                    "financial_summary": "Revenue grew 25% YoY to $50M ARR",
                    "researched_at": "2026-02-14T10:00:00Z"
                }
            ]
        }
    }


class CompanyResearchRequest(BaseModel):
    """Request to research a company.

    Used by API handlers to trigger company research workflow.
    """

    company_name: Annotated[
        str,
        Field(
            description="Company name to research",
            min_length=1,
            max_length=200,
        ),
    ]

    force_refresh: Annotated[
        bool,
        Field(
            default=False,
            description="Force refresh even if cached data exists",
        ),
    ]


class CompanyResearchResponse(BaseModel):
    """Response containing company research data.

    Returned by API handlers after successful research.
    """

    research: CompanyResearchData
    source: Annotated[
        str,
        Field(
            description="Data source: 'cache' or 'fresh'",
            pattern="^(cache|fresh)$",
        ),
    ]
    cached_at: Annotated[
        datetime,
        Field(
            description="When data was cached (UTC)",
        ),
    ]
    ttl_expires_at: Annotated[
        datetime,
        Field(
            description="When cache expires (UTC)",
        ),
    ]
```

### Validation Rules

| Field | Constraint | Error Message |
|-------|------------|---------------|
| `company_name` | min_length=1, max_length=200 | "Company name must be 1-200 characters" |
| `company_name` | Non-empty after strip | "Company name cannot be empty after normalization" |
| `overview` | min_length=50, max_length=1000 | "Overview must be 50-1000 characters" |
| `mission` | max_length=500 | "Mission statement cannot exceed 500 characters" |
| `financial_summary` | max_length=500 | "Financial summary cannot exceed 500 characters" |
| `values` | Empty strings filtered | N/A (silent filtering) |

---

## Deliverable 2: CompanyResearchTransformer Class

**File:** `src/backend/careervp/logic/company_research_transformer.py`

### Class Design

```python
"""Company research data transformation layer.

Handles bidirectional transformation between:
- LLM output (CompanyResearchData Pydantic model)
- DynamoDB storage (dict with PK/SK/attributes)

Responsibilities:
- Serialize CompanyResearchData → DynamoDB item
- Deserialize DynamoDB item → CompanyResearchData
- Calculate TTL (30 days from now)
- Generate composite sort key (entity_type#company_name)
- Preserve all LLM fields in research_data JSON blob
"""

import json
import time
from datetime import datetime, timezone
from typing import Any

from careervp.models.company_research import CompanyResearchData


class CompanyResearchTransformer:
    """Transforms company research data between Pydantic models and DynamoDB items.

    This class implements the bidirectional transformation layer that bridges
    LLM-generated output (Pydantic models) and DynamoDB storage (dicts).

    Key responsibilities:
    - Serialize Pydantic → DynamoDB item dict
    - Deserialize DynamoDB item dict → Pydantic
    - Calculate TTL timestamps (30 days)
    - Generate composite sort keys
    - Preserve all fields in research_data JSON blob

    Design patterns:
    - Static methods (no instance state needed)
    - Explicit field mapping (no magic)
    - Type-safe transformations
    - Error handling via exceptions (caller wraps in Result)
    """

    ENTITY_TYPE = "company_research"
    TTL_DAYS = 30

    @staticmethod
    def to_dynamodb_item(
        research: CompanyResearchData,
        user_email: str,
    ) -> dict[str, Any]:
        """Transform CompanyResearchData to DynamoDB item.

        Creates a DynamoDB item with:
        - PK: user_email
        - SK: entity_type#company_name
        - entity_id: company_name
        - cached_at: ISO-8601 timestamp
        - ttl: Unix timestamp (30 days from now)
        - research_data: JSON blob with all LLM fields

        Args:
            research: Validated CompanyResearchData from LLM
            user_email: User identifier (from Lambda authorizer)

        Returns:
            DynamoDB item dict ready for put_item()

        Raises:
            ValueError: If user_email is empty
            json.JSONEncodeError: If research data cannot serialize
        """
        if not user_email or not user_email.strip():
            raise ValueError("user_email cannot be empty")

        # Calculate TTL (30 days from now)
        ttl_timestamp = int(time.time()) + (CompanyResearchTransformer.TTL_DAYS * 86400)

        # Current timestamp (ISO-8601)
        cached_at = datetime.now(timezone.utc).isoformat()

        # Composite sort key: entity_type#company_name
        sort_key = f"{CompanyResearchTransformer.ENTITY_TYPE}#{research.company_name}"

        # Serialize entire research object to JSON blob
        research_json = json.dumps(
            research.model_dump(mode="json"),
            ensure_ascii=False,
            separators=(",", ":"),  # Compact JSON
        )

        return {
            "user_email": user_email,
            "entity_type": sort_key,
            "entity_id": research.company_name,
            "cached_at": cached_at,
            "ttl": ttl_timestamp,
            "research_data": research_json,
        }

    @staticmethod
    def from_dynamodb_item(item: dict[str, Any]) -> CompanyResearchData:
        """Transform DynamoDB item to CompanyResearchData.

        Deserializes the research_data JSON blob and reconstructs
        the Pydantic model with full validation.

        Args:
            item: DynamoDB item dict from query/get_item

        Returns:
            Validated CompanyResearchData instance

        Raises:
            KeyError: If required fields missing from item
            json.JSONDecodeError: If research_data is invalid JSON
            pydantic.ValidationError: If deserialized data fails validation
        """
        # Extract research_data JSON blob
        research_json = item["research_data"]

        # Deserialize to dict
        research_dict = json.loads(research_json)

        # Reconstruct Pydantic model (validates automatically)
        return CompanyResearchData.model_validate(research_dict)

    @staticmethod
    def get_sort_key(company_name: str) -> str:
        """Generate composite sort key for company research.

        Format: entity_type#company_name

        Args:
            company_name: Company name (will be normalized)

        Returns:
            Composite sort key string
        """
        normalized = company_name.strip()
        return f"{CompanyResearchTransformer.ENTITY_TYPE}#{normalized}"

    @staticmethod
    def calculate_ttl_expiration(ttl_timestamp: int) -> datetime:
        """Convert TTL Unix timestamp to datetime for display.

        Args:
            ttl_timestamp: Unix timestamp from DynamoDB TTL field

        Returns:
            UTC datetime when TTL expires
        """
        return datetime.fromtimestamp(ttl_timestamp, tz=timezone.utc)
```

### Example Usage

```python
# Serialization (LLM → DynamoDB)
research = CompanyResearchData(
    company_name="TechCorp",
    overview="Leading provider of...",
    values=["Innovation", "Integrity"],
)

item = CompanyResearchTransformer.to_dynamodb_item(
    research=research,
    user_email="user@example.com"
)
# item = {
#   "user_email": "user@example.com",
#   "entity_type": "company_research#TechCorp",
#   "entity_id": "TechCorp",
#   "cached_at": "2026-02-14T10:30:00Z",
#   "ttl": 1739615400,
#   "research_data": '{"company_name":"TechCorp","overview":"Leading provider...","values":["Innovation","Integrity"],...}'
# }

# Deserialization (DynamoDB → Pydantic)
research = CompanyResearchTransformer.from_dynamodb_item(item)
# research.company_name == "TechCorp"
# research.values == ["Innovation", "Integrity"]
```

---

## Deliverable 3: KnowledgeRepository Updates

**File:** `src/backend/careervp/dal/knowledge_repository.py`

### Method Signatures

```python
"""Knowledge repository for company research and gap responses.

Handles persistence of knowledge base entities to DynamoDB.
Supports caching, TTL expiration, and GSI queries.
"""

from datetime import datetime
from typing import Any

import boto3
from aws_lambda_powertools import Logger, Tracer
from botocore.exceptions import ClientError

from careervp.logic.company_research_transformer import CompanyResearchTransformer
from careervp.models.company_research import CompanyResearchData
from careervp.models.result import Result, ResultCode

logger = Logger()
tracer = Tracer()


class KnowledgeRepository:
    """Repository for knowledge base operations.

    Manages persistence for:
    - Company research (with 30-day TTL)
    - Gap responses (with 24-month TTL)
    - CV context (with 24-hour TTL)
    """

    def __init__(self, table_name: str | None = None) -> None:
        """Initialize repository.

        Args:
            table_name: DynamoDB table name (defaults to env var KNOWLEDGE_TABLE_NAME)
        """
        self.table_name = table_name or self._get_table_name()
        self.dynamodb = boto3.resource("dynamodb")
        self.table = self.dynamodb.Table(self.table_name)

    def _get_table_name(self) -> str:
        """Get table name from environment."""
        import os
        table_name = os.environ.get("KNOWLEDGE_TABLE_NAME")
        if not table_name:
            raise ValueError("KNOWLEDGE_TABLE_NAME environment variable not set")
        return table_name

    @tracer.capture_method(capture_response=False)
    def save_company_research(
        self,
        research: CompanyResearchData,
        user_email: str,
    ) -> Result[dict[str, Any]]:
        """Save company research to knowledge table.

        Transforms CompanyResearchData to DynamoDB item and persists.
        Automatically calculates 30-day TTL and composite sort key.

        Args:
            research: Validated company research data from LLM
            user_email: User identifier (from Lambda authorizer)

        Returns:
            Result with DynamoDB item on success, error on failure

        Example:
            >>> research = CompanyResearchData(company_name="TechCorp", overview="...")
            >>> result = repo.save_company_research(research, "user@example.com")
            >>> if result.success:
            ...     print(f"Cached until: {result.data['ttl']}")
        """
        try:
            # Transform Pydantic model → DynamoDB item
            item = CompanyResearchTransformer.to_dynamodb_item(
                research=research,
                user_email=user_email,
            )

            # Write to DynamoDB
            self.table.put_item(Item=item)

            logger.info(
                "Company research saved",
                company=research.company_name,
                user_email=user_email,
                ttl_expires_at=item["ttl"],
            )

            return Result(
                success=True,
                data=item,
                code=ResultCode.SUCCESS,
            )

        except ClientError as e:
            error_msg = f"DynamoDB error: {e.response['Error']['Message']}"
            logger.error(
                error_msg,
                company=research.company_name,
                user_email=user_email,
                error=str(e),
            )
            return Result(
                success=False,
                error=error_msg,
                code=ResultCode.DYNAMODB_ERROR,
            )

        except (ValueError, json.JSONEncodeError) as e:
            error_msg = f"Transformation error: {str(e)}"
            logger.error(
                error_msg,
                company=research.company_name,
                user_email=user_email,
            )
            return Result(
                success=False,
                error=error_msg,
                code=ResultCode.VALIDATION_ERROR,
            )

    @tracer.capture_method(capture_response=False)
    def get_company_research(
        self,
        company_name: str,
        user_email: str,
    ) -> CompanyResearchData | None:
        """Retrieve company research from knowledge table.

        Queries by PK (user_email) and SK (entity_type#company_name).
        Returns None if not found or TTL expired (handled by DynamoDB).

        Args:
            company_name: Company name to lookup
            user_email: User identifier (scopes query)

        Returns:
            CompanyResearchData if found and valid, None otherwise

        Example:
            >>> research = repo.get_company_research("TechCorp", "user@example.com")
            >>> if research:
            ...     print(f"Found: {research.overview}")
        """
        try:
            # Generate composite sort key
            sort_key = CompanyResearchTransformer.get_sort_key(company_name)

            # Query DynamoDB
            response = self.table.get_item(
                Key={
                    "user_email": user_email,
                    "entity_type": sort_key,
                }
            )

            # Check if item found
            item = response.get("Item")
            if not item:
                logger.info(
                    "Company research not found",
                    company=company_name,
                    user_email=user_email,
                )
                return None

            # Transform DynamoDB item → Pydantic model
            research = CompanyResearchTransformer.from_dynamodb_item(item)

            logger.info(
                "Company research retrieved",
                company=company_name,
                user_email=user_email,
                cached_at=item["cached_at"],
            )

            return research

        except ClientError as e:
            logger.error(
                f"DynamoDB error: {e.response['Error']['Message']}",
                company=company_name,
                user_email=user_email,
            )
            return None

        except (KeyError, json.JSONDecodeError, ValidationError) as e:
            logger.error(
                f"Deserialization error: {str(e)}",
                company=company_name,
                user_email=user_email,
            )
            return None
```

---

## Deliverable 4: Unit Tests

**File:** `tests/unit/test_company_research_transformer.py`

### Test Suite Design

```python
"""Unit tests for CompanyResearchTransformer.

Tests cover:
- to_dynamodb_item() serialization
- from_dynamodb_item() deserialization
- Round-trip transformations (data preservation)
- Edge cases (empty lists, None values, special characters)
- Error handling (invalid inputs, malformed JSON)
"""

import json
import time
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from careervp.logic.company_research_transformer import CompanyResearchTransformer
from careervp.models.company_research import CompanyResearchData


class TestToDynamoDBItem:
    """Tests for to_dynamodb_item() serialization."""

    def test_complete_research_serialization(self):
        """Test serialization with all fields populated."""
        research = CompanyResearchData(
            company_name="TechCorp Solutions",
            overview="Leading provider of cloud-based enterprise solutions with 500+ customers.",
            values=["Innovation", "Integrity", "Customer Focus"],
            mission="Empower businesses through technology",
            strategic_priorities=["AI integration", "Global expansion"],
            recent_news=["Series B funding", "New VP hired"],
            financial_summary="Revenue $50M ARR",
        )

        item = CompanyResearchTransformer.to_dynamodb_item(
            research=research,
            user_email="user@example.com",
        )

        # Verify keys
        assert item["user_email"] == "user@example.com"
        assert item["entity_type"] == "company_research#TechCorp Solutions"
        assert item["entity_id"] == "TechCorp Solutions"
        assert "cached_at" in item
        assert "ttl" in item
        assert "research_data" in item

        # Verify TTL calculation (30 days)
        expected_ttl = int(time.time()) + (30 * 86400)
        assert abs(item["ttl"] - expected_ttl) < 5  # Within 5 seconds

        # Verify cached_at is recent ISO timestamp
        cached_at = datetime.fromisoformat(item["cached_at"])
        assert abs((datetime.now(timezone.utc) - cached_at).total_seconds()) < 5

        # Verify research_data is valid JSON
        research_dict = json.loads(item["research_data"])
        assert research_dict["company_name"] == "TechCorp Solutions"
        assert research_dict["overview"] == research.overview
        assert research_dict["values"] == ["Innovation", "Integrity", "Customer Focus"]

    def test_minimal_research_serialization(self):
        """Test serialization with only required fields."""
        research = CompanyResearchData(
            company_name="MinimalCo",
            overview="A minimal company with just an overview field for testing purposes.",
        )

        item = CompanyResearchTransformer.to_dynamodb_item(
            research=research,
            user_email="test@example.com",
        )

        # Verify optional fields have defaults
        research_dict = json.loads(item["research_data"])
        assert research_dict["values"] == []
        assert research_dict["mission"] is None
        assert research_dict["strategic_priorities"] == []
        assert research_dict["recent_news"] == []
        assert research_dict["financial_summary"] is None

    def test_special_characters_in_company_name(self):
        """Test company names with special characters."""
        research = CompanyResearchData(
            company_name="AT&T Corp. (North America)",
            overview="Telecommunications company with special characters in name.",
        )

        item = CompanyResearchTransformer.to_dynamodb_item(
            research=research,
            user_email="user@example.com",
        )

        assert item["entity_type"] == "company_research#AT&T Corp. (North America)"
        assert item["entity_id"] == "AT&T Corp. (North America)"

    def test_empty_user_email_raises_error(self):
        """Test that empty user_email raises ValueError."""
        research = CompanyResearchData(
            company_name="TestCo",
            overview="Test company overview.",
        )

        with pytest.raises(ValueError, match="user_email cannot be empty"):
            CompanyResearchTransformer.to_dynamodb_item(research, "")

        with pytest.raises(ValueError, match="user_email cannot be empty"):
            CompanyResearchTransformer.to_dynamodb_item(research, "   ")


class TestFromDynamoDBItem:
    """Tests for from_dynamodb_item() deserialization."""

    def test_complete_item_deserialization(self):
        """Test deserialization with all fields."""
        item = {
            "user_email": "user@example.com",
            "entity_type": "company_research#TechCorp",
            "entity_id": "TechCorp",
            "cached_at": "2026-02-14T10:00:00Z",
            "ttl": 1739615400,
            "research_data": json.dumps({
                "company_name": "TechCorp",
                "overview": "Leading tech company with innovative solutions.",
                "values": ["Innovation", "Integrity"],
                "mission": "Empower businesses",
                "strategic_priorities": ["AI", "Cloud"],
                "recent_news": ["Funding round"],
                "financial_summary": "Revenue $50M",
                "researched_at": "2026-02-14T10:00:00Z",
            }),
        }

        research = CompanyResearchTransformer.from_dynamodb_item(item)

        assert research.company_name == "TechCorp"
        assert research.overview == "Leading tech company with innovative solutions."
        assert research.values == ["Innovation", "Integrity"]
        assert research.mission == "Empower businesses"
        assert research.strategic_priorities == ["AI", "Cloud"]
        assert research.recent_news == ["Funding round"]
        assert research.financial_summary == "Revenue $50M"

    def test_missing_research_data_raises_error(self):
        """Test that missing research_data field raises KeyError."""
        item = {
            "user_email": "user@example.com",
            "entity_type": "company_research#TestCo",
        }

        with pytest.raises(KeyError):
            CompanyResearchTransformer.from_dynamodb_item(item)

    def test_invalid_json_raises_error(self):
        """Test that invalid JSON raises JSONDecodeError."""
        item = {
            "research_data": "not valid json {{{",
        }

        with pytest.raises(json.JSONDecodeError):
            CompanyResearchTransformer.from_dynamodb_item(item)

    def test_invalid_data_raises_validation_error(self):
        """Test that invalid data fails Pydantic validation."""
        item = {
            "research_data": json.dumps({
                "company_name": "TestCo",
                # Missing required 'overview' field
                "values": [],
            }),
        }

        with pytest.raises(ValidationError):
            CompanyResearchTransformer.from_dynamodb_item(item)


class TestRoundTripTransformation:
    """Tests for bidirectional transformation (data preservation)."""

    def test_round_trip_preserves_all_fields(self):
        """Test that serialization + deserialization preserves all data."""
        original = CompanyResearchData(
            company_name="RoundTripCo",
            overview="Testing round-trip transformation with all fields populated.",
            values=["Value1", "Value2", "Value3"],
            mission="Mission statement here",
            strategic_priorities=["Priority1", "Priority2"],
            recent_news=["News1", "News2"],
            financial_summary="Financial details",
        )

        # Serialize
        item = CompanyResearchTransformer.to_dynamodb_item(
            research=original,
            user_email="test@example.com",
        )

        # Deserialize
        restored = CompanyResearchTransformer.from_dynamodb_item(item)

        # Verify all fields match
        assert restored.company_name == original.company_name
        assert restored.overview == original.overview
        assert restored.values == original.values
        assert restored.mission == original.mission
        assert restored.strategic_priorities == original.strategic_priorities
        assert restored.recent_news == original.recent_news
        assert restored.financial_summary == original.financial_summary

    def test_round_trip_with_empty_lists(self):
        """Test round-trip with empty lists preserved."""
        original = CompanyResearchData(
            company_name="EmptyListCo",
            overview="Testing empty list preservation.",
            values=[],
            strategic_priorities=[],
            recent_news=[],
        )

        item = CompanyResearchTransformer.to_dynamodb_item(
            research=original,
            user_email="test@example.com",
        )
        restored = CompanyResearchTransformer.from_dynamodb_item(item)

        assert restored.values == []
        assert restored.strategic_priorities == []
        assert restored.recent_news == []


class TestHelperMethods:
    """Tests for helper methods."""

    def test_get_sort_key(self):
        """Test sort key generation."""
        key = CompanyResearchTransformer.get_sort_key("TechCorp")
        assert key == "company_research#TechCorp"

    def test_get_sort_key_strips_whitespace(self):
        """Test sort key strips whitespace."""
        key = CompanyResearchTransformer.get_sort_key("  TechCorp  ")
        assert key == "company_research#TechCorp"

    def test_calculate_ttl_expiration(self):
        """Test TTL expiration calculation."""
        ttl_timestamp = int(time.time()) + (30 * 86400)
        expiration = CompanyResearchTransformer.calculate_ttl_expiration(ttl_timestamp)

        # Should be ~30 days from now
        assert isinstance(expiration, datetime)
        assert expiration.tzinfo == timezone.utc
        delta = (expiration - datetime.now(timezone.utc)).total_seconds()
        assert 29.5 * 86400 < delta < 30.5 * 86400  # Within 30 days ± 12 hours
```

---

## Deliverable 5: Integration Test

**File:** `tests/integration/test_company_research_flow.py`

### Test Design

```python
"""Integration tests for company research end-to-end flow.

Tests the complete workflow:
1. LLM generates company research (mocked)
2. FVS validation (mocked)
3. Transformation to DynamoDB item
4. Storage in knowledge repository
5. Retrieval from knowledge repository
6. Deserialization back to Pydantic model

Requires:
- DynamoDB Local or test table
- Mocked Bedrock LLM calls
- Mocked FVS validator
"""

import os
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
import boto3
from moto import mock_dynamodb

from careervp.dal.knowledge_repository import KnowledgeRepository
from careervp.models.company_research import CompanyResearchData
from careervp.models.result import ResultCode


@pytest.fixture
def dynamodb_table():
    """Create mock DynamoDB table for testing."""
    with mock_dynamodb():
        # Create mock table
        dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
        table = dynamodb.create_table(
            TableName="test-knowledge-table",
            KeySchema=[
                {"AttributeName": "user_email", "KeyType": "HASH"},
                {"AttributeName": "entity_type", "KeyType": "RANGE"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "user_email", "AttributeType": "S"},
                {"AttributeName": "entity_type", "AttributeType": "S"},
                {"AttributeName": "entity_id", "AttributeType": "S"},
            ],
            GlobalSecondaryIndexes=[
                {
                    "IndexName": "entity-index",
                    "KeySchema": [
                        {"AttributeName": "entity_type", "KeyType": "HASH"},
                        {"AttributeName": "entity_id", "KeyType": "RANGE"},
                    ],
                    "Projection": {"ProjectionType": "ALL"},
                }
            ],
            BillingMode="PAY_PER_REQUEST",
        )

        yield table


@pytest.fixture
def repository(dynamodb_table):
    """Create KnowledgeRepository with mock table."""
    with patch.dict(os.environ, {"KNOWLEDGE_TABLE_NAME": "test-knowledge-table"}):
        yield KnowledgeRepository()


class TestCompanyResearchFlow:
    """End-to-end integration tests."""

    def test_save_and_retrieve_company_research(self, repository):
        """Test complete save → retrieve workflow."""
        # Create research data
        research = CompanyResearchData(
            company_name="IntegrationCo",
            overview="Full integration test company with all fields populated for testing.",
            values=["Innovation", "Quality"],
            mission="Deliver excellence",
            strategic_priorities=["Growth", "Expansion"],
            recent_news=["Series A funding"],
            financial_summary="Revenue $10M",
        )

        # Save to repository
        result = repository.save_company_research(
            research=research,
            user_email="integration@example.com",
        )

        assert result.success is True
        assert result.code == ResultCode.SUCCESS
        assert "ttl" in result.data
        assert "cached_at" in result.data

        # Retrieve from repository
        retrieved = repository.get_company_research(
            company_name="IntegrationCo",
            user_email="integration@example.com",
        )

        assert retrieved is not None
        assert retrieved.company_name == "IntegrationCo"
        assert retrieved.overview == research.overview
        assert retrieved.values == ["Innovation", "Quality"]
        assert retrieved.mission == "Deliver excellence"

    def test_retrieve_nonexistent_company_returns_none(self, repository):
        """Test retrieving company that doesn't exist."""
        result = repository.get_company_research(
            company_name="NonExistent",
            user_email="test@example.com",
        )

        assert result is None

    def test_user_isolation(self, repository):
        """Test that users can only see their own data."""
        research = CompanyResearchData(
            company_name="IsolatedCo",
            overview="Testing user isolation in knowledge repository.",
        )

        # Save for user1
        repository.save_company_research(
            research=research,
            user_email="user1@example.com",
        )

        # Try to retrieve as user2
        result = repository.get_company_research(
            company_name="IsolatedCo",
            user_email="user2@example.com",
        )

        assert result is None  # Should not see user1's data

        # Retrieve as user1
        result = repository.get_company_research(
            company_name="IsolatedCo",
            user_email="user1@example.com",
        )

        assert result is not None
        assert result.company_name == "IsolatedCo"

    def test_overwrite_existing_research(self, repository):
        """Test that saving again overwrites previous data."""
        # Save initial version
        v1 = CompanyResearchData(
            company_name="UpdateCo",
            overview="Version 1 of the company overview.",
        )
        repository.save_company_research(v1, "user@example.com")

        # Save updated version
        v2 = CompanyResearchData(
            company_name="UpdateCo",
            overview="Version 2 with updated information.",
            values=["New Value"],
        )
        repository.save_company_research(v2, "user@example.com")

        # Retrieve
        result = repository.get_company_research("UpdateCo", "user@example.com")

        assert result.overview == "Version 2 with updated information."
        assert result.values == ["New Value"]
```

---

## Risk Assessment

### Potential Issues

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| **JSON blob size limit** | Medium | High | DynamoDB item max 400KB; monitor research_data size; add validation |
| **TTL cleanup delay** | Low | Low | DynamoDB TTL deletes within 48 hours; query filter on ttl for freshness |
| **GSI not implemented** | High | Medium | Must add GSI to CDK stack before deployment |
| **FVS validation failures** | Medium | Medium | Implement retry logic; log failures; manual review queue |
| **Schema evolution** | Medium | Low | JSON blob enables adding fields without migration |
| **Concurrent writes** | Low | Low | DynamoDB handles concurrency; last write wins |
| **Deserialization errors** | Low | High | Wrap in try/except; log errors; return None gracefully |

### Mitigation Strategies

1. **JSON Size Validation**
   ```python
   research_json = json.dumps(research.model_dump())
   if len(research_json) > 300_000:  # 300KB threshold
       raise ValueError(f"Research data too large: {len(research_json)} bytes")
   ```

2. **GSI Implementation** (CRITICAL - must add to CDK)
   ```python
   # In dynamodb_stack.py after table creation:
   self.knowledge_table.add_global_secondary_index(
       index_name="entity-index",
       partition_key=dynamodb.Attribute(
           name="entity_type",
           type=dynamodb.AttributeType.STRING,
       ),
       sort_key=dynamodb.Attribute(
           name="entity_id",
           type=dynamodb.AttributeType.STRING,
       ),
   )
   ```

3. **TTL Freshness Filter**
   ```python
   # In get_company_research(), add freshness check:
   current_time = int(time.time())
   if item.get("ttl", 0) < current_time:
       logger.info("Research expired, returning None")
       return None
   ```

---

## Dependencies

### New Python Packages

None required - all dependencies already in project.

### Existing Dependencies

| Package | Version | Usage |
|---------|---------|-------|
| pydantic | ^2.0 | Model validation |
| boto3 | ^1.28 | DynamoDB client |
| aws-lambda-powertools | ^2.0 | Logging, tracing |
| pytest | ^7.0 | Testing |
| moto | ^4.0 | DynamoDB mocking |

### Infrastructure Dependencies

| Resource | Status | Required Action |
|----------|--------|-----------------|
| careervp-knowledge-table-dev | ✓ Exists | None |
| entity-index GSI | ✗ Missing | Add to dynamodb_stack.py |
| KNOWLEDGE_TABLE_NAME constant | ✗ Missing | Add to constants.py |
| Lambda environment variable | ✗ Missing | Add KNOWLEDGE_TABLE_NAME to handlers |

---

## Validation Commands

```bash
# Navigate to backend directory
cd /Users/yitzchak/Documents/dev/careervp/src/backend

# 1. Ruff lint check
uv run ruff check \
  careervp/logic/company_research_transformer.py \
  careervp/models/company_research.py \
  careervp/dal/knowledge_repository.py

# 2. Mypy strict type checking
uv run mypy \
  careervp/logic/company_research_transformer.py \
  careervp/models/company_research.py \
  careervp/dal/knowledge_repository.py \
  --strict

# 3. Unit tests (transformer)
uv run pytest \
  tests/unit/test_company_research_transformer.py \
  -v --tb=short --cov=careervp.logic.company_research_transformer

# 4. Unit tests (models)
uv run pytest \
  tests/unit/test_company_research_models.py \
  -v --tb=short --cov=careervp.models.company_research

# 5. Integration tests
uv run pytest \
  tests/integration/test_company_research_flow.py \
  -v --tb=short

# 6. Full test suite
uv run pytest tests/ -v --tb=short --cov=careervp
```

---

## Implementation Checklist

- [ ] **Phase 1: Models** (Est: 1 hour)
  - [ ] Create `src/backend/careervp/models/company_research.py`
  - [ ] Add CompanyResearchData, CompanyResearchRequest, CompanyResearchResponse
  - [ ] Add field validators
  - [ ] Run mypy strict checks

- [ ] **Phase 2: Transformer** (Est: 1.5 hours)
  - [ ] Create `src/backend/careervp/logic/company_research_transformer.py`
  - [ ] Implement to_dynamodb_item()
  - [ ] Implement from_dynamodb_item()
  - [ ] Add helper methods (get_sort_key, calculate_ttl_expiration)
  - [ ] Run mypy strict checks

- [ ] **Phase 3: Repository** (Est: 2 hours)
  - [ ] Update `src/backend/careervp/dal/knowledge_repository.py`
  - [ ] Implement save_company_research()
  - [ ] Implement get_company_research()
  - [ ] Add error handling with Result wrapper
  - [ ] Add logging/tracing
  - [ ] Run mypy strict checks

- [ ] **Phase 4: Unit Tests** (Est: 3 hours)
  - [ ] Create `tests/unit/test_company_research_transformer.py`
  - [ ] Write 15+ test cases covering edge cases
  - [ ] Create `tests/unit/test_company_research_models.py`
  - [ ] Write validation tests
  - [ ] Achieve 95%+ code coverage

- [ ] **Phase 5: Integration Tests** (Est: 2 hours)
  - [ ] Create `tests/integration/test_company_research_flow.py`
  - [ ] Implement end-to-end workflow test
  - [ ] Test user isolation
  - [ ] Test data preservation

- [ ] **Phase 6: Infrastructure** (Est: 1 hour)
  - [ ] Add entity-index GSI to `infra/careervp/dynamodb_stack.py`
  - [ ] Add KNOWLEDGE_TABLE_NAME to `infra/careervp/constants.py`
  - [ ] Deploy CDK stack to dev
  - [ ] Verify GSI creation

- [ ] **Phase 7: Validation** (Est: 1 hour)
  - [ ] Run all validation commands
  - [ ] Fix any Ruff/Mypy issues
  - [ ] Ensure all tests pass
  - [ ] Review code coverage report

**Total Estimated Time:** 11.5 hours

---

## Next Steps

1. **Immediate Actions**
   - Implement CompanyResearchData model (Deliverable 1)
   - Implement CompanyResearchTransformer (Deliverable 2)
   - Write unit tests for both (Deliverable 5)

2. **Infrastructure Setup**
   - Add entity-index GSI to DynamoDB stack
   - Add KNOWLEDGE_TABLE_NAME constant
   - Deploy updated infrastructure

3. **Repository Integration**
   - Update KnowledgeRepository (Deliverables 3 & 4)
   - Write integration tests (Deliverable 6)
   - Validate end-to-end flow

4. **FVS Integration** (Future Work)
   - Add FVS validation before save_company_research()
   - Implement quality score thresholds
   - Add manual review queue for failures

---

## Appendix: Key Decisions Log

| Decision | Date | Rationale |
|----------|------|-----------|
| Store as JSON blob vs flattened attributes | 2026-02-14 | Enables schema evolution; DynamoDB best practice for semi-structured data |
| 30-day TTL for research | 2026-02-14 | Balances freshness vs API cost; matches spec requirements |
| Composite sort key (entity_type#company_name) | 2026-02-14 | Enables efficient queries; standard DynamoDB pattern |
| Bidirectional transformer | 2026-02-14 | Enables round-trip transformations; prevents data loss |
| Static transformer methods | 2026-02-14 | No instance state needed; simplifies testing |
| Result wrapper for mutations | 2026-02-14 | Consistent with existing codebase patterns |
| FVS validation before storage | 2026-02-14 | Prevents low-quality data in cache; enforces standards |

---

**End of Architecture Design Document**

Generated: 2026-02-14T15:30:00Z
Next Review: Implementation Phase Kickoff
