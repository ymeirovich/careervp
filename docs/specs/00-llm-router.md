# Global Spec: LLM Router Utility

## Overview
A centralized utility to handle model switching between Sonnet and Haiku to maintain 91% profit margins.

## Implementation Requirements
- **Location:** `src/backend/careervp/logic/utils/llm_client.py`
- **Logic:**
    - If `mode == "STRATEGIC"` (VPR, Gap Analysis) -> Use `sonnet-4.5`.
    - If `mode == "TEMPLATE"` (CV, Cover Letter) -> Use `haiku-4.5`.
- **Safety:** Wrap all calls in a retry decorator for transient 500 errors.
- **Tracing:** Use AWS Powertools to log token usage as custom metrics.
