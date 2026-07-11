"""RED-first CDK tests for clause P-27 — termination protection on top-level stacks.

Spec: docs/db-redesign/code/code-analysis/project/specs/P-27-cfn-stack-policy-spec.md

The stack-policy JSON document assertions live in the backend suite
(src/backend/tests/infra/test_p27_stack_policy.py) because they only read a file and
need PyYAML/json; these two tests need the CDK toolkit, so they run in the infra venv.
"""

from __future__ import annotations

from aws_cdk import App, Environment
from careervp.frontend_stack import FrontendStack
from careervp.naming_utils import NamingUtils
from careervp.service_stack import ServiceStack


def _pinned_env() -> Environment:
    return Environment(account="123456789012", region="us-east-1")


def test_service_stack_has_termination_protection() -> None:
    app = App()
    naming = NamingUtils(
        environment="dev", region="us-east-1", account_id="123456789012"
    )
    stack = ServiceStack(
        scope=app,
        id=naming.stack_id("crud"),
        env=_pinned_env(),
        is_production_env=False,
        naming=naming,
        stack_feature="crud",
    )
    assert stack.termination_protection is True, (
        "P-27: ServiceStack.termination_protection must be True"
    )


def test_frontend_stack_has_termination_protection() -> None:
    app = App()
    stack = FrontendStack(
        scope=app,
        construct_id="CareerVpFrontendDevTP",
        environment="dev",
        domain="dev.careervp.com",
        is_production=False,
        env=_pinned_env(),
    )
    assert stack.termination_protection is True, (
        "P-27: FrontendStack.termination_protection must be True"
    )
