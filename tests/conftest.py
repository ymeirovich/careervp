"""Root pytest configuration for contract-aligned test discovery."""

from __future__ import annotations

import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BACKEND_SRC = ROOT / "src" / "backend"
INFRA_ROOT = ROOT / "infra"
JSII_CACHE = Path("/tmp/jsii-runtime-package-cache")


for candidate in (BACKEND_SRC, INFRA_ROOT, ROOT):
    candidate_str = str(candidate)
    if candidate_str not in sys.path:
        sys.path.insert(0, candidate_str)


# Keep jsii cache writes inside sandbox-writable paths for CDK tests.
JSII_CACHE.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("JSII_RUNTIME_PACKAGE_CACHE", str(JSII_CACHE))
os.environ.setdefault(
    "CAREERVP_API_BASE_URL",
    "https://dev-api.careervp.com/prod",
)
