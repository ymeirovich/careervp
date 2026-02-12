# Phase 1 Tasks: Model Unification

**Objective:** Consolidate duplicate models to single source of truth
**Duration:** 22 hours (3 days)
**Owner:** Backend

---

## Task 1.1: Audit Model Usages

**Effort:** 2 hours
**Priority:** P0
**Command:** None (manual analysis)

### Analysis Steps

1. **Find all model imports**
   ```bash
   cd /Users/yitzchak/Documents/dev/careervp/src/backend
   grep -r "from.*models" careervp/ --include="*.py" | grep -v "__pycache__"
   ```

2. **Identify duplicate model references**
   ```bash
   grep -r "cv_models\|fvs_models" careervp/ --include="*.py" | grep -v "__pycache__"
   ```

3. **Document current state**
   | Import Path | Used In | Model |
   |------------|---------|-------|
   | `models.cv.UserCV` | VPR, Gap Analysis | cv.py |
   | `models.cv_models.UserCV` | CV Tailoring | cv_models.py |
   | `models.fvs.FVSResult` | VPR | fvs.py |
   | `models.fvs_models.FVSConfig` | CV Tailoring | fvs_models.py |

---

## Task 1.2: Consolidate UserCV

**Effort:** 6 hours
**Priority:** P0
**Files Modified:** `models/cv.py`
**Files Impacted:** All files importing UserCV

### Current State

```python
# models/cv.py (VPR uses this)
class UserCV(BaseModel):
    personal_info: PersonalInfo
    work_experience: List[WorkExperience]
    # ...

# models/cv_models.py (CV Tailoring uses this)
class UserCV(BaseModel):
    name: str
    email: str
    experience: List[dict]
    # ... different structure!
```

### Target: Unified UserCV

```python
# models/cv.py (SINGLE SOURCE OF TRUTH)
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class PersonalInfo(BaseModel):
    name: str
    email: str
    phone: Optional[str] = None
    linkedin: Optional[str] = None
    location: Optional[str] = None

class Achievement(BaseModel):
    description: str
    metrics: Optional[Dict[str, Any]] = None

class WorkExperience(BaseModel):
    company: str
    title: str
    start_date: datetime
    end_date: Optional[datetime] = None
    location: Optional[str] = None
    responsibilities: List[str]
    achievements: List[Achievement] = []

class Education(BaseModel):
    institution: str
    degree: str
    graduation_date: datetime
    gpa: Optional[str] = None

class Skills(BaseModel):
    technical: List[str] = []
    tools: List[str] = []
    soft: List[str] = []

class UserCV(BaseModel):
    personal_info: PersonalInfo
    work_experience: List[WorkExperience]
    education: List[Education] = []
    skills: Optional[Skills] = None
    certifications: List[str] = []
    summary: Optional[str] = None
    cv_id: str
    user_email: str
    created_at: datetime
    updated_at: datetime
```

### Migration Steps

1. **Create unified model** in `models/cv.py`
2. **Update VPR imports** (minimal change - already uses cv.py)
3. **Update CV Tailoring imports**:
   ```python
   # FROM:
   from models.cv_models import UserCV
   # TO:
   from models.cv import UserCV
   ```
4. **Run tests** to verify functionality
5. **Remove duplicate file** `models/cv_models.py`

### Validation

- [ ] Single UserCV model exists
- [ ] All imports updated
- [ ] VPR tests pass
- [ ] CV Tailoring tests pass
- [ ] `models/cv_models.py` removed

---

## Task 1.3: Consolidate FVS Models

**Effort:** 4 hours
**Priority:** P0
**Files Modified:** `models/fvs.py`
**Files Impacted:** VPR, CV Tailoring

### Current State

```python
# models/fvs.py (VPR uses this)
class FVSResult(BaseModel):
    verified: bool
    claims: List[Claim]
    score: float

# models/fvs_models.py (CV Tailoring uses this)
class FVSConfig(BaseModel):
    strict_mode: bool
    allowed_deviation: float

class Claim(BaseModel):
    text: str
    verified: bool
    source: Optional[str]
```

### Target: Unified FVS Models

```python
# models/fvs.py (SINGLE SOURCE OF TRUTH)
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from enum import Enum

class ClaimVerificationStatus(str, Enum):
    VERIFIED = "verified"
    UNVERIFIED = "unverified"
    FLAGGED = "flagged"

class Claim(BaseModel):
    text: str
    status: ClaimVerificationStatus
    source: Optional[str] = None
    deviation: Optional[float] = None
    notes: Optional[str] = None

class FVSResult(BaseModel):
    verified: bool
    claims: List[Claim]
    score: float
    flagged_count: int = 0
    unverified_count: int = 0

class FVSConfig(BaseModel):
    strict_mode: bool = False
    allowed_deviation: float = 0.1
    require_metrics: bool = False
    min_confidence_score: float = 0.7
```

### Migration Steps

1. **Create unified models** in `models/fvs.py`
2. **Update VPR imports**
3. **Update CV Tailoring imports**
4. **Run tests**
5. **Remove duplicate file** `models/fvs_models.py`

### Validation

- [ ] Single FVS model set exists
- [ ] All imports updated
- [ ] FVS tests pass
- [ ] `models/fvs_models.py` removed

---

## Task 1.4: Define Clear Model Boundaries

**Effort:** 2 hours
**Priority:** P1
**Files Modified:** `models/__init__.py`

### Implementation

```python
# models/__init__.py
"""CareerVP Models - Single source of truth for all data models."""

# CV Models
from .cv import UserCV, PersonalInfo, WorkExperience, Achievement, Education, Skills

# Job Models
from .job import JobPosting, JobRequirement

# VPR Models
from .vpr import VPRResponse, StrategicDifferentiator, AlignmentMatrix

# Gap Analysis Models
from .gap_analysis import GapAnalysisQuestion, GapAnalysisResponse

# FVS Models
from .fvs import FVSResult, FVSConfig, Claim, ClaimVerificationStatus

# Result Pattern
from .result import Result, Ok, Err

__all__ = [
    # CV
    "UserCV", "PersonalInfo", "WorkExperience", "Achievement", "Education", "Skills",
    # Job
    "JobPosting", "JobRequirement",
    # VPR
    "VPRResponse", "StrategicDifferentiator", "AlignmentMatrix",
    # Gap Analysis
    "GapAnalysisQuestion", "GapAnalysisResponse",
    # FVS
    "FVSResult", "FVSConfig", "Claim", "ClaimVerificationStatus",
    # Result
    "Result", "Ok", "Err",
]
```

---

## Task 1.5: Update All Imports

**Effort:** 4 hours
**Priority:** P0
**Command:** `sed` and manual verification

### Update Commands

```bash
# Update cv_models imports
find careervp -name "*.py" -exec sed -i '' 's/from models\.cv_models import/from models.cv import/g' {} \;

# Update fvs_models imports
find careervp -name "*.py" -exec sed -i '' 's/from models\.fvs_models import/from models.fvs import/g' {} \;

# Verify no remaining references
grep -r "cv_models\|fvs_models" careervp/ --include="*.py"
```

### Manual Verification

For each file that imported from the removed modules:

```python
# BEFORE
from models.cv_models import UserCV, TailoredCV
from models.fvs_models import FVSConfig

# AFTER
from models.cv import UserCV, TailoredCV
from models.fvs import FVSConfig
```

---

## Phase 1 Exit Criteria

- [ ] Model audit complete
- [ ] Single UserCV model in `models/cv.py`
- [ ] Single FVS model set in `models/fvs.py`
- [ ] All imports updated
- [ ] All tests pass
- [ ] Duplicate files removed

---

## Rollback Plan

If issues arise:
1. Keep duplicate files as backups
2. Use git to quickly restore if needed
3. Feature flag for gradual migration:
   ```python
   try:
       from models.cv import UserCV as UnifiedUserCV
   except ImportError:
       from models.cv_models import UserCV as LegacyUserCV
   ```

---

## Testing

```bash
# Run model-related tests
PYTHONPATH=$(pwd) uv run pytest ../../tests/unit/models/ -v

# Run full test suite
PYTHONPATH=$(pwd) uv run pytest ../../tests/ -v

# Type checking
uv run mypy models/careervp/models/ --strict
```
