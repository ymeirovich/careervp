"""
Thin proxy so `cdk.careervp` imports resolve to the actual CDK modules in `infra.careervp`.
"""

from __future__ import annotations

import importlib
import sys

_infra_pkg = importlib.import_module('infra.careervp')
sys.modules[__name__] = _infra_pkg
