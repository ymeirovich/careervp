"""P-11 WAF infrastructure contract tests.

scope_lock_clause: P-11
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

import pytest

os.environ.setdefault('JSII_RUNTIME_PACKAGE_CACHE', '/tmp/jsii-cache')

try:
    from aws_cdk import App, Environment, NestedStack
    from aws_cdk.assertions import Template

    CDK_AVAILABLE = True
except Exception:  # pragma: no cover - environment guard
    CDK_AVAILABLE = False

pytestmark = pytest.mark.skipif(not CDK_AVAILABLE, reason='aws-cdk not available')

REPO_ROOT = Path(__file__).resolve().parents[4]
INFRA_SRC = str(REPO_ROOT / 'infra')


def _dev_stack() -> Any:
    if INFRA_SRC not in sys.path:
        sys.path.insert(0, INFRA_SRC)

    from careervp.naming_utils import NamingUtils  # type: ignore[import-not-found]
    from careervp.service_stack import ServiceStack  # type: ignore[import-not-found]

    app = App()
    naming = NamingUtils(environment='dev', region='us-east-1', account_id='788159322332')
    return ServiceStack(
        scope=app,
        id=naming.stack_id('crud'),
        env=Environment(account='788159322332', region='us-east-1'),
        is_production_env=False,
        naming=naming,
        stack_feature='crud',
    )


def test_p11_waf_webacl_exists_in_non_production_envs() -> None:
    """AC-P11-1: non-production API stacks still synthesize a WAF WebACL."""
    stack = _dev_stack()
    templates = [Template.from_stack(stack)]
    templates.extend(Template.from_stack(construct) for construct in stack.node.find_all() if isinstance(construct, NestedStack))
    resources = {logical_id: resource for template in templates for logical_id, resource in template.to_json().get('Resources', {}).items()}

    web_acls = {logical_id: resource for logical_id, resource in resources.items() if resource.get('Type') == 'AWS::WAFv2::WebACL'}
    assert web_acls, 'P-11 requires a WAF WebACL in dev/non-production stacks'
