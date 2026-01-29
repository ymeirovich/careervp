"""
Compatibility package that exposes the CDK modules under the `cdk.*` namespace.

Tests import `cdk.careervp.*`, but the source of truth lives under `infra/careervp`.
This shim adds the repository root to `sys.path` so those modules resolve correctly.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.append(str(REPO_ROOT))
