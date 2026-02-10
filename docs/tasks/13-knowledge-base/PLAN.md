# Knowledge Base Implementation Plan

**Parent Task:** JSA-KB-001 in `docs/tasks/05-jsa-skill-alignment.md`
**Spec:** `docs/specs/13-knowledge-base.md` (to be created)
**Priority:** P1 (Medium) - Foundation for memory-aware features
**Estimated Effort:** 8 hours total
**Status:** Pending

---

## Overview

The Knowledge Base provides persistent memory for user-specific data across job applications, enabling memory-aware questioning in Gap Analysis and consistent differentiators across artifacts.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      Knowledge Base System                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐    ┌──────────────────┐    ┌───────────────┐ │
│  │   Handlers   │───▶│  Logic Layer     │───▶│  Repository   │ │
│  │              │    │                  │    │               │ │
│  │ gap_handler  │    │ knowledge_base.py│    │ kb_repository │ │
│  │ vpr_handler  │    │                  │    │               │ │
│  │ cv_handler   │    └──────────────────┘    └───────┬───────┘ │
│  └──────────────┘                                     │         │
│                                                       ▼         │
│                                          ┌───────────────────┐  │
│                                          │    DynamoDB       │  │
│                                          │ careervp-knowledge│  │
│                                          │      -base        │  │
│                                          └───────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

## DynamoDB Schema

**Table Name:** `careervp-knowledge-base`

| Attribute | Type | Description |
|-----------|------|-------------|
| `pk` | String | `USER#{userEmail}` |
| `sk` | String | `KB#{knowledgeType}#{identifier}` |
| `data` | Map | The knowledge data |
| `applications_count` | Number | Times this knowledge was used |
| `created_at` | String | ISO timestamp |
| `updated_at` | String | ISO timestamp |
| `ttl` | Number | Optional TTL for cleanup |

### Knowledge Types

| Type | SK Pattern | Purpose |
|------|------------|---------|
| `recurring_themes` | `KB#THEME#{theme_id}` | Patterns identified across applications |
| `gap_responses` | `KB#GAP#{job_id}` | User answers to gap questions |
| `differentiators` | `KB#DIFF#{diff_id}` | Core differentiators extracted from VPR |
| `company_insights` | `KB#COMPANY#{company_id}` | Researched company data |

## Task Breakdown

### Task 1: DynamoDB Table CDK Definition
**File:** `infra/careervp/api_db_construct.py`
**Effort:** 1 hour

### Task 2: Repository Layer
**File:** `src/backend/careervp/dal/knowledge_base_repository.py`
**Effort:** 2 hours

### Task 3: Logic Layer
**File:** `src/backend/careervp/logic/knowledge_base.py`
**Effort:** 2 hours

### Task 4: Gap Analysis Integration
**File:** `src/backend/careervp/handlers/gap_handler.py`
**Effort:** 1.5 hours

### Task 5: Unit Tests
**File:** `tests/knowledge_base/unit/`
**Effort:** 1.5 hours

---

## Dependencies

**Blocks:**
- Gap Analysis memory-aware questioning
- Recurring themes extraction

**Blocked By:**
- None (can start immediately)

---

## Success Criteria

- [ ] DynamoDB table deployed
- [ ] Repository CRUD operations working
- [ ] Logic layer abstractions complete
- [ ] Gap Analysis retrieves recurring themes
- [ ] All 11 tests passing
