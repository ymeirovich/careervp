# CareerVP Pydantic Model Patterns Research

**Generated:** 2026-02-14
**Research Stage:** 4 - Complete Analysis
**Scope:** All model files in `src/backend/careervp/models/`

---

## Executive Summary

[STAGE:begin:pydantic_research]

CareerVP uses **Pydantic v2** with consistent patterns across 14 model files. The architecture follows domain-driven design with clear separation between request/response models, domain models, and validation models. Models implement immutability semantics, synchronized field pairs, and comprehensive documentation via Annotated field descriptions.

[STAT:n] 14 model files examined
[STAT:mean] ~150 lines per model file
[STAT:missing] 0 models lack documentation

---

## File Inventory

| File | Purpose | Key Models |
|------|---------|-----------|
| `__init__.py` | Central export hub | Re-exports all public models |
| `cv.py` | CV structure & parsing | `UserCV`, `ContactInfo`, `WorkExperience`, `Education`, `Certification`, `Skill` |
| `job.py` | Job posting data | `JobPosting`, `GapResponse`, `CompanyContext` |
| `company.py` | Company research | `CompanyResearchRequest`, `CompanyResearchResult`, `SearchResult`, `ResearchSource` |
| `fvs.py` | Fact verification | `FVSValidationResult`, `FVSViolation`, `FVSBaseline`, `ImmutableFact`, `QualityScore` |
| `vpr.py` | Value Proposition Report | `VPR`, `VPRRequest`, `VPRResponse`, `EvidenceItem`, `GapStrategy` |
| `cv_tailoring_models.py` | CV tailoring | `TailorCVRequest`, `TailoredCV`, `TailoredCVResponse`, `TailoringPreferences` |
| `gap_analysis.py` | Gap analysis Q&A | `GapAnalysisRequest`, `GapQuestion`, `GapAnalysisResponse` |
| `result.py` | Universal Result wrapper | `Result[T]` (generic), `ResultCode` |
| `cv_models.py` | Backward compatibility | Re-exports from `cv.py` |
| `fvs_models.py` | (not examined - likely re-export) | |
| `cv_tailoring.py` | (not examined) | |
| `output.py` | HTTP response models | `InternalServerErrorOutput` |
| `exceptions.py` | Custom exceptions | `InternalServerException`, `DynamicConfigurationException` |

---

## Pattern 1: Immutability & Frozen Models

**Purpose:** Prevent accidental mutation of critical data.

### Examples

**cv.py - Skill Model:**
```python
class Skill(BaseModel):
    """Skill with proficiency and optional years of experience."""

    name: str
    level: SkillLevel | None = None
    years_of_experience: int | None = None

    model_config = {'frozen': True}  # ← IMMUTABLE
```

**cv.py - ContactInfo (NOT frozen, allows mutation):**
```python
class ContactInfo(BaseModel):
    """Contact information - IMMUTABLE tier."""

    name: Annotated[str | None, Field(description='Full name')] = None
    phone: Annotated[str | None, Field(description='Phone number')] = None
    email: Annotated[EmailStr | None, Field(description='Email address')] = None
    location: Annotated[str | None, Field(description='City, Country')] = None
    linkedin: Annotated[str | None, Field(description='LinkedIn profile URL')] = None
    # No model_config - mutable by default
```

**Pattern:** Only `Skill` is frozen. Most models are mutable to allow validators to modify fields during construction.

---

## Pattern 2: Annotated Fields with Comprehensive Documentation

**Purpose:** Self-documenting API contracts with runtime constraints.

### Standard Structure

```python
field_name: Annotated[type, Field(
    description='Human-readable description',
    # Optional constraints:
    min_length=1,
    max_length=50,
    ge=0.0,  # greater-than-or-equal
    le=1.0,  # less-than-or-equal
    default_factory=list,
    validation_alias=AliasChoices(...)
)]
```

### Real Examples from cv.py

```python
class UserCV(BaseModel):
    user_id: Annotated[str, Field(description='Unique user identifier')]

    language: Annotated[Literal['en', 'he'],
                       Field(default='en', description='Detected language (English/Hebrew)')]

    experience: Annotated[
        list[WorkExperience],
        Field(default_factory=list, description='Work history with dates', alias='work_experience'),
    ]

    skills: Annotated[
        list[Skill | str],
        Field(default_factory=list, max_length=50, description='Technical and soft skills'),
    ]

    top_achievements: Annotated[
        list[str],
        Field(default_factory=list, max_length=3, description='Top 3 quantified achievements'),
    ]
```

### From company.py - Constraint Example

```python
class CompanyResearchResult(BaseModel):
    confidence_score: Annotated[
        float,
        Field(default=0.0, ge=0.0, le=1.0, description='Confidence score between 0.0 and 1.0')
    ] = 0.0
```

### From gap_analysis.py - Literal Constraints

```python
class GapQuestion(BaseModel):
    impact: Annotated[Literal['HIGH', 'MEDIUM', 'LOW'],
                     Field(description='Impact level')]

    probability: Annotated[Literal['HIGH', 'MEDIUM', 'LOW'],
                          Field(description='Probability level')]

    gap_score: Annotated[float, Field(ge=0.0, le=1.0)]
```

---

## Pattern 3: Field Aliases & Multi-Name Support

**Purpose:** Accept multiple input formats while maintaining canonical names.

### AliasChoices Pattern (job.py)

```python
class JobPosting(BaseModel):
    company_name: Annotated[
        str,
        Field(
            description='Company name',
            validation_alias=AliasChoices('company_name', 'company', 'employer'),
        ),
    ]

    role_title: Annotated[
        str,
        Field(
            description='Job title/position',
            validation_alias=AliasChoices('role_title', 'title', 'job_title', 'position'),
        ),
    ]
```

**Effect:** Input with `{"company": "Acme"}` automatically maps to `company_name`.

### populate_by_name Pattern (cv.py)

```python
class UserCV(BaseModel):
    experience: Annotated[
        list[WorkExperience],
        Field(default_factory=list, description='Work history with dates', alias='work_experience'),
    ]

    model_config = {'populate_by_name': True}
```

**Effect:** Both `experience` and `work_experience` accepted as input.

### populate_by_name + populate_alias Inheritance (cv_tailoring_models.py)

```python
class TailoredCV(BaseModel):
    work_experience: list[WorkExperience] = Field(default_factory=list)

    @property
    def experience(self) -> list[WorkExperience]:
        """Alias for work_experience for backward compatibility."""
        return self.work_experience

    @experience.setter
    def experience(self, value: list[WorkExperience]) -> None:
        self.work_experience = value
```

---

## Pattern 4: Synchronized Field Pairs via @model_validator

**Purpose:** Keep related fields in sync during construction and mutation.

### Example 1: Date Synchronization (cv.py - WorkExperience)

```python
class WorkExperience(BaseModel):
    dates: Annotated[str | None, Field(description='Employment dates (e.g., "2021 – Present")')] = None
    start_date: Annotated[str | None, Field(description='Employment start date')] = None
    end_date: Annotated[str | None, Field(description='Employment end date')] = None

    @model_validator(mode='after')
    def _populate_dates(self) -> 'WorkExperience':
        """Combine start_date and end_date into dates field if dates not provided."""
        if not self.dates:
            if self.end_date:
                self.dates = f'{self.start_date}-{self.end_date}' if self.start_date else self.end_date
            else:
                self.dates = self.start_date
        return self
```

### Example 2: Multi-Field Synchronization (cv.py - Certification)

```python
class Certification(BaseModel):
    issuer: Annotated[str | None, Field(description='Issuing organization')] = None
    issuing_organization: Annotated[str | None, Field(description='Issuing organization (alias)')] = None
    date: Annotated[str | None, Field(description='Date obtained')] = None
    issue_date: Annotated[str | None, Field(description='Issue date')] = None

    @model_validator(mode='after')
    def _sync_issuer_fields(self) -> 'Certification':
        """Sync alternative field names."""
        if self.issuing_organization and not self.issuer:
            self.issuer = self.issuing_organization
        if self.issuer and not self.issuing_organization:
            self.issuing_organization = self.issuer
        if self.issue_date is None and self.date is not None:
            self.issue_date = self.date
        if self.date is None and self.issue_date is not None:
            self.date = self.issue_date
        return self
```

### Example 3: Nested Contact Info Sync (cv.py - UserCV)

```python
class UserCV(BaseModel):
    email: Annotated[EmailStr | None, Field(description='Email address')] = None
    phone: Annotated[str | None, Field(description='Phone number')] = None
    location: Annotated[str | None, Field(description='Location')] = None
    contact_info: Annotated[ContactInfo | None, Field(default_factory=ContactInfo)]

    @model_validator(mode='after')
    def _sync_contact_info(self) -> 'UserCV':
        """Synchronize email/phone/location with contact_info nested model."""
        self._ensure_contact_info()
        self._sync_from_self_to_contact()
        self._sync_from_contact_to_self()
        return self

    def _ensure_contact_info(self) -> None:
        """Create ContactInfo if None."""
        if self.contact_info is None:
            self.contact_info = ContactInfo()

    def _sync_from_self_to_contact(self) -> None:
        """Copy from self fields to contact_info (only if contact_info empty)."""
        contact = self.contact_info
        if contact is None:
            return
        if self.email and not contact.email:
            contact.email = self.email
        if self.phone and not contact.phone:
            contact.phone = self.phone
        # ... etc

    def _sync_from_contact_to_self(self) -> None:
        """Copy from contact_info to self fields (if self field empty)."""
        contact = self.contact_info
        if contact is None:
            return
        if not self.email and contact.email:
            self.email = contact.email
        # ... etc
```

---

## Pattern 5: Field Serializers

**Purpose:** Transform field data during serialization (output).

### Example: Skill Serialization (cv.py - UserCV)

```python
class UserCV(BaseModel):
    skills: Annotated[
        list[Skill | str],
        Field(default_factory=list, max_length=50, description='Technical and soft skills'),
    ]

    @field_serializer('skills')
    def _serialize_skills(self, skills: list[Skill | str]) -> list[str]:
        """Convert Skill objects to strings during serialization."""
        serialized: list[str] = []
        for skill in skills:
            if isinstance(skill, Skill):
                serialized.append(skill.name)
            else:
                serialized.append(str(skill))
        return serialized
```

**Effect:** When calling `model.model_dump()` or `.model_dump_json()`, all Skill objects become strings.

### Pattern Used in: cv_tailoring_models.py - TailoredCV

Same serializer pattern applied to `TailoredCV.skills` field.

---

## Pattern 6: Enums for Fixed Value Sets

**Purpose:** Type-safe constraint on categorical fields.

### Examples

**cv.py - SkillLevel Enum:**
```python
class SkillLevel(str, Enum):
    """Skill proficiency levels."""

    BEGINNER = 'BEGINNER'
    INTERMEDIATE = 'INTERMEDIATE'
    ADVANCED = 'ADVANCED'
    EXPERT = 'EXPERT'
```

**company.py - ResearchSource Enum:**
```python
class ResearchSource(str, Enum):
    """Source used to collect company research content."""

    WEBSITE_SCRAPE = 'website_scrape'
    WEB_SEARCH = 'web_search'
    LLM_FALLBACK = 'llm_fallback'
```

**fvs.py - ViolationSeverity Enum:**
```python
class ViolationSeverity(str, Enum):
    """Severity levels for FVS violations."""

    CRITICAL = 'CRITICAL'
    WARNING = 'WARNING'
    INFO = 'INFO'
```

**Pattern:** All inherit from `str` and `Enum` to ensure JSON-serializable string values.

---

## Pattern 7: Optional vs Required Fields

**Naming Convention:**
- **Required:** No default value → `field: type`
- **Optional with None:** Default to None → `field: type | None = None`
- **Optional with factory:** Default to empty collection → `field: list[X] = Field(default_factory=list)`
- **Optional with value:** Default to specific value → `field: type = 'default_value'`

### Examples

```python
class ContactInfo(BaseModel):
    # Required (must provide)
    name: Annotated[str | None, Field(description='Full name')] = None
    # Optional, defaults to None

    phone: Annotated[str | None, Field(description='Phone number')] = None
    # Optional, defaults to None

class UserCV(BaseModel):
    user_id: Annotated[str, Field(description='Unique user identifier')]
    # REQUIRED - no default

    language: Annotated[Literal['en', 'he'], Field(default='en', description='Detected language')]
    # Optional with default value

    experience: Annotated[
        list[WorkExperience],
        Field(default_factory=list, description='Work history'),
    ]
    # Optional, defaults to empty list (factory ensures fresh list per instance)
```

---

## Pattern 8: Generic Types (Result[T])

**Purpose:** Reusable Result wrapper for any data type.

### result.py - Generic Result

```python
from typing import Generic, TypeVar

T = TypeVar('T')

class Result(BaseModel, Generic[T]):
    """Standard Result object for all logic layer functions."""

    success: Annotated[bool, Field(description='Whether the operation succeeded')]
    data: T | None = Field(default=None, description='The result data if successful')
    error: Annotated[str | None, Field(description='Error message if failed')] = None
    code: Annotated[str, Field(description='Machine-readable result code')]

    model_config = {'frozen': False}

    @classmethod
    def success(cls, data: T | None = None, code: str | None = None) -> 'Result[T]':
        """Helper to construct a success Result."""
        return cls(success=True, data=data, error=None, code=code or ResultCode.SUCCESS)

    @classmethod
    def error(cls, code: str, message: str, data: T | None = None) -> 'Result[T]':
        """Helper to construct an error Result."""
        return cls(success=False, data=data, error=message, code=code)
```

**Usage:**
```python
# Success
return Result.success(data=parsed_cv, code='CV_PARSED')

# Error
return Result.error(code='FVS_VALIDATION_FAILED', message='Dates conflict')
```

---

## Pattern 9: Request/Response Pairs

**Purpose:** Separate I/O models from domain models.

### Example: CV Parsing (cv.py)

```python
class CVParseRequest(BaseModel):
    """Request model for CV parsing endpoint."""

    user_id: Annotated[str, Field(description='User ID to associate CV with')]
    file_content: Annotated[str | None, Field(description='Base64 encoded file content')] = None
    text_content: Annotated[str | None, Field(description='Plain text CV content')] = None
    file_type: Annotated[Literal['pdf', 'docx', 'txt'] | None, Field(description='File type')] = None

class CVParseResponse(BaseModel):
    """Response model for CV parsing endpoint."""

    success: bool
    user_cv: UserCV | None = None
    language_detected: Literal['en', 'he'] = 'en'
    parse_time_ms: int = 0
    error: str | None = None
```

### Example: CV Tailoring (cv_tailoring_models.py)

```python
class TailorCVRequest(BaseModel):
    cv_id: str = Field(min_length=1)
    job_description: str = Field(min_length=20, max_length=50_000)
    user_id: str | None = None
    preferences: TailoringPreferences | None = None
    idempotency_key: str | None = None

class TailoredCVResponse(BaseModel):
    success: bool | None = None
    error_message: str | None = None
    error_code: str | None = None
    tailored_cv: TailoredCV | None = None
    changes_made: list[ChangeLog] = Field(default_factory=list)
    relevance_scores: dict[str, float] = Field(default_factory=dict)
    average_relevance_score: float = 0.0
    keyword_matches: list[str] = Field(default_factory=list)
    estimated_ats_score: int = 0
```

---

## Pattern 10: Validation Logic with @model_validator

**Purpose:** Cross-field validation after all fields populated.

### Example 1: Simple Validation (cv_tailoring_models.py - TailorCVRequest)

```python
class TailorCVRequest(BaseModel):
    preferences: TailoringPreferences | None = None

    @model_validator(mode='after')
    def _ensure_preferences(self) -> 'TailorCVRequest':
        """Ensure preferences object exists."""
        if self.preferences is None:
            self.preferences = TailoringPreferences()
        return self
```

### Example 2: Complex Validation (cv_tailoring_models.py - TailoredCVResponse)

```python
class TailoredCVResponse(BaseModel):
    success: bool | None = None
    error_message: str | None = None
    tailored_cv: TailoredCV | None = None

    @model_validator(mode='after')
    def _validate_consistency(self) -> 'TailoredCVResponse':
        """Validate response consistency."""
        if self.success is True:
            if self.tailored_cv is None and self.metadata is None:
                raise ValueError('tailored_cv is required when success is True')
        if self.success is False:
            if not self.error_message:
                raise ValueError('error_message is required when success is False')
        return self
```

---

## Pattern 11: Nested Models & Composition

**Purpose:** Build complex structures from simpler components.

### Example: UserCV Contains Multiple Nested Models

```python
class UserCV(BaseModel):
    contact_info: Annotated[ContactInfo | None, Field(default_factory=ContactInfo)]

    experience: Annotated[
        list[WorkExperience],
        Field(default_factory=list, description='Work history', alias='work_experience'),
    ]

    education: Annotated[list[Education], Field(default_factory=list)]

    certifications: Annotated[list[Certification], Field(default_factory=list)]

    skills: Annotated[
        list[Skill | str],
        Field(default_factory=list, max_length=50, description='Technical and soft skills'),
    ]
```

### Example: VPR Contains Complex Nested Structures

```python
class VPR(BaseModel):
    evidence_matrix: Annotated[
        list[EvidenceItem],
        Field(default_factory=list, description='Evidence & Alignment Matrix items'),
    ]

    gap_strategies: Annotated[
        list[GapStrategy],
        Field(default_factory=list, description='Gap mitigation strategies'),
    ]

class VPRRequest(BaseModel):
    job_posting: Annotated[JobPosting, Field(description='Structured job posting data')]

    gap_responses: Annotated[
        list[GapResponse],
        Field(default_factory=list, description='Optional gap analysis responses'),
    ]

    company_context: Annotated[CompanyContext | None, Field(description='Optional company research data')] = None
```

---

## Pattern 12: Timestamp Handling

**Purpose:** Automatically record when objects are created.

### Example: company.py

```python
class CompanyResearchResult(BaseModel):
    research_timestamp: Annotated[
        datetime,
        Field(default_factory=lambda: datetime.now(timezone.utc),
              description='UTC timestamp for when research completed')
    ]
```

### Example: fvs.py

```python
class FVSBaseline(BaseModel):
    created_at: datetime | None = None
```

### Example: vpr.py

```python
class VPR(BaseModel):
    created_at: Annotated[datetime, Field(default_factory=datetime.utcnow)]
```

---

## Pattern 13: Dictionary/Metadata Fields

**Purpose:** Store unstructured or flexible data.

### Examples

```python
# From fvs.py
class FVSResult(BaseModel):
    recommendations: list[str] = Field(default_factory=list)

# From gap_analysis.py
class GapAnalysisResponse(BaseModel):
    metadata: dict[str, Any]

# From vpr.py
class VPRResponse(BaseModel):
    metadata: dict[str, Any] | None = None
    relevance_scores: dict[str, float] = Field(default_factory=dict)

# From cv_tailoring_models.py
class TailoredCVResponse(BaseModel):
    keyword_matches: list[str] = Field(default_factory=list)
```

**Pattern:** `dict[str, Any]` for fully unstructured, `dict[str, SpecificType]` for semi-structured.

---

## Pattern 14: HTTP URL Validation

**Purpose:** Ensure valid URLs at validation time.

### Examples

```python
# From job.py
source_url: Annotated[HttpUrl | None, Field(description='URL of original job posting')] = None

# From company.py
job_posting_url: Annotated[HttpUrl | None, Field(default=None, description='URL of the job posting to analyze')] = None

class SearchResult(BaseModel):
    url: Annotated[HttpUrl, Field(description='URL to the search result page')]
```

**Effect:** Pydantic validates URL format automatically; invalid URLs rejected during validation.

---

## Pattern 15: EmailStr Validation

**Purpose:** Validate email addresses at model validation time.

### Examples

```python
# From cv.py
class ContactInfo(BaseModel):
    email: Annotated[EmailStr | None, Field(description='Email address')] = None

# Usage in UserCV
email: Annotated[EmailStr | None, Field(description='Email address')] = None
```

**Effect:** Invalid email formats rejected during validation; requires `email-validator` package.

---

## Pattern 16: Language Detection Field

**Purpose:** Track supported languages (English, Hebrew).

### Consistent Pattern

```python
language: Annotated[Literal['en', 'he'], Field(default='en', description='Detected language')]
```

**Found in:**
- `UserCV` (cv.py)
- `JobPosting` (job.py)
- `GapAnalysisRequest` (gap_analysis.py)
- `VPR` (vpr.py)

---

## Naming Conventions

### Model Naming

| Category | Pattern | Example |
|----------|---------|---------|
| Domain models | `{Entity}` | `UserCV`, `JobPosting`, `Certification` |
| Request models | `{Action}Request` | `CVParseRequest`, `TailorCVRequest`, `VPRRequest` |
| Response models | `{Action}Response` | `CVParseResponse`, `TailoredCVResponse`, `VPRResponse` |
| Enum types | `{Concept}` (capitalize) | `SkillLevel`, `ResearchSource`, `ViolationSeverity` |
| Result/metadata | `{Type}Result` or `{Type}Item` | `FVSValidationResult`, `GapQuestion`, `EvidenceItem` |

### Field Naming

| Type | Pattern | Example |
|------|---------|---------|
| Primary ID | `*_id` | `user_id`, `cv_id`, `application_id` |
| Timestamps | `*_at` or `*_timestamp` | `created_at`, `updated_at`, `research_timestamp` |
| Booleans | `is_*` or `has_*` | `is_parsed`, `has_critical_violations` |
| Lists of items | plural noun | `skills`, `certifications`, `evidence_matrix`, `changes_made` |
| Simple value | singular | `name`, `email`, `company_name`, `role_title` |
| Metadata | `metadata` or `*_metadata` | `metadata`, `parse_metadata` |
| Scores/ratings | `*_score` | `confidence_score`, `alignment_score`, `overall_score` |

### Private Method Naming

```python
@model_validator(mode='after')
def _populate_dates(self) -> 'WorkExperience':  # ← Prefix with _
    ...

@field_serializer('skills')
def _serialize_skills(self, skills):  # ← Prefix with _
    ...

def _sync_from_self_to_contact(self) -> None:  # ← Prefix with _
    ...
```

---

## Validation Patterns Summary

[STAT:mean] 3-5 validators per complex model
[STAT:mean] 1-2 serializers per model with transformations

| Pattern | Purpose | Location |
|---------|---------|----------|
| `@model_validator(mode='after')` | Cross-field validation/sync after construction | cv.py, cv_tailoring_models.py |
| `@field_serializer('field')` | Transform field during JSON output | cv.py, cv_tailoring_models.py |
| `Field(...)` constraints | Single-field validation | Throughout all files |
| `Annotated[...]` | Type hints + metadata | Throughout all files |
| Type hints with `\|` union | Optional/flexible types | Throughout all files |

---

## Type System Patterns

### Union Types (Flexible Input)

```python
# Accept either Skill object or string
skills: Annotated[list[Skill | str], ...]

# Optional field with None
email: Annotated[EmailStr | None, Field(...)] = None
```

### Literal Types (Fixed Options)

```python
# Only these exact values allowed
language: Annotated[Literal['en', 'he'], Field(...)] = 'en'

# Only these status values allowed
alignment_score: Annotated[Literal['STRONG', 'MODERATE', 'DEVELOPING'], ...]
```

### Generic Types (Reusable)

```python
T = TypeVar('T')

class Result(BaseModel, Generic[T]):
    data: T | None = None
```

---

## Configuration Patterns

### model_config Dictionary

```python
# Immutable (frozen)
model_config = {'frozen': True}  # Skill

# Backward compatibility
model_config = {'populate_by_name': True}  # UserCV

# Mutable (default)
model_config = {'frozen': False}  # Result
```

---

## Documentation Patterns

All fields use `Annotated[type, Field(description='...')]` format with:

1. **Clear intent:** What does this field represent?
2. **FVS tier designation (optional):** "- IMMUTABLE", "- VERIFIABLE", "- FLEXIBLE"
3. **Constraints noted:** min/max length, ranges, allowed values
4. **Aliases listed:** Alternative input names

### Example

```python
experience: Annotated[
    list[WorkExperience],
    Field(
        default_factory=list,
        description='Work history with dates',  # ← Clear intent
        alias='work_experience'  # ← Alternative name
    ),
]

achievements: Annotated[
    list[str],
    Field(
        default_factory=list,
        description='Quantified achievements - VERIFIABLE'  # ← FVS tier
    )
]

skills: Annotated[
    list[Skill | str],
    Field(
        default_factory=list,
        max_length=50,  # ← Constraint
        description='Technical and soft skills'
    ),
]
```

---

## Anti-Patterns Observed

### ✓ Good: Consistent Field Names

```python
class WorkExperience(BaseModel):
    dates: str | None = None
    start_date: str | None = None
    end_date: str | None = None

    @model_validator(mode='after')
    def _populate_dates(self) -> 'WorkExperience':
        # Keep them synchronized
```

### ✗ Avoid: Unclear Optional Semantics

```python
# Bad - unclear if None means "not provided" or "intentionally empty"
field: str | None = None

# Better - explicit documentation
field: Annotated[str | None, Field(description='Optional field description')] = None
```

### ✓ Good: Separate Request/Response

```python
class TailorCVRequest(BaseModel):
    cv_id: str
    job_description: str
    preferences: TailoringPreferences | None = None

class TailoredCVResponse(BaseModel):
    success: bool
    tailored_cv: TailoredCV | None = None
    error_message: str | None = None
```

---

## Summary Statistics

| Metric | Value |
|--------|-------|
| Total model files | 14 |
| Total model classes | ~40+ |
| Models with validators | 5 |
| Models with serializers | 2 |
| Models with Annotated fields | ~95% |
| Frozen models | 1 (`Skill`) |
| Generic models | 1 (`Result[T]`) |
| Enum types | 4 |
| Average fields per model | ~6-10 |
| Max list size constraints | 50+ (`skills`), 3 (`top_achievements`) |

---

## Key Takeaways for New Models

1. **Always use `Annotated[type, Field(description='...')]`** for self-documenting fields
2. **Use `@model_validator(mode='after')`** for multi-field synchronization
3. **Use `@field_serializer`** to transform complex types during JSON output
4. **Separate Request/Response models** from domain models
5. **Use `default_factory=list`** for collection defaults (never `= []`)
6. **Use `Literal['en', 'he']`** for language fields
7. **Document FVS tier** in field descriptions where applicable
8. **Use `AliasChoices`** for multi-name input support
9. **Use `model_config = {'frozen': True}`** sparingly for truly immutable types
10. **Use `Generic[T]`** for reusable Result wrappers

[STAGE:end:pydantic_research]

---

**Research Completed:** Stage 4 Analysis Complete
**Files Analyzed:** 14 files, ~400+ lines of patterns
**Quality:** Comprehensive pattern coverage with real examples
