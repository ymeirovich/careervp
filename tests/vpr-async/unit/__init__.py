"""
VPR Async Unit Tests Package

Unit tests for VPR async architecture:
- Frontend client integration (polling, error handling)
- Async workflow orchestration (state machine, idempotency)
- Deployment validation (AWS resources, configurations)
"""

__version__ = "1.0.0"
__package_name__ = "vpr_async_tests"

from typing import Dict, Any

# Test categories
TEST_CATEGORIES = {
    "frontend": "Frontend client integration tests",
    "workflow": "Async workflow orchestration tests",
    "deployment": "Deployment validation tests",
}

# Default test configuration
DEFAULT_TEST_CONFIG: Dict[str, Any] = {
    "environment": "dev",
    "timeout": 30,
    "max_retries": 3,
    "poll_interval": 5,
    "max_polls": 60,
}

__all__ = ["TEST_CATEGORIES", "DEFAULT_TEST_CONFIG"]
