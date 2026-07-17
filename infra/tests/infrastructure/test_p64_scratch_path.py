"""P-64 scratch-only service-stack synthesis assertions."""

from __future__ import annotations

from collections.abc import Mapping
from inspect import signature
from typing import cast

import pytest
from aws_cdk import App, Environment, NestedStack
from aws_cdk.assertions import Match, Template

from careervp.naming_utils import NamingUtils
from careervp.api_construct import ApiConstruct
from careervp.api_db_construct import ApiDbConstruct
from careervp.cognito_construct import CognitoConstruct
from careervp.configuration.configuration_construct import ConfigurationStore
from careervp.monitoring import MonitoringNestedStack
from careervp.scratch_deployment import ScratchDeploymentSettings
from careervp.service_stack import ServiceStack


SCRATCH_ACCOUNT = "123456789012"
SCRATCH_ENVIRONMENT = "rto-euw1-20260712-a1"
SCRATCH_ORIGIN = "https://scratch-rto.example.invalid"


def _scratch_settings() -> ScratchDeploymentSettings:
    return ScratchDeploymentSettings(
        account=SCRATCH_ACCOUNT,
        region="eu-west-1",
        environment=SCRATCH_ENVIRONMENT,
        configuration_source="test",
        allowed_origin=SCRATCH_ORIGIN,
    )


@pytest.fixture(scope="module")
def scratch_stack() -> ServiceStack:
    settings = _scratch_settings()
    app = App()
    naming = NamingUtils(
        environment=settings.environment,
        region=settings.region,
        account_id=settings.account,
    )
    return ServiceStack(
        scope=app,
        id=naming.stack_id("crud"),
        env=Environment(account=settings.account, region=settings.region),
        is_production_env=False,
        naming=naming,
        stack_feature="crud",
        scratch_settings=settings,
    )


@pytest.fixture(scope="module")
def scratch_templates(scratch_stack: ServiceStack) -> list[Template]:
    # Parent plus every nested stack. P-26 Job 1 adds CrudFeaturesNestedStack
    # (re-homed feature Lambdas/queues/state machine), so enumerate nested stacks
    # generically rather than by name to keep the scratch-isolation guards
    # covering the whole deployment.
    templates = [Template.from_stack(scratch_stack)]
    templates.extend(
        Template.from_stack(construct)
        for construct in scratch_stack.node.find_all()
        if isinstance(construct, NestedStack)
    )
    return templates


def _resource_names(template: Template) -> list[str]:
    names: list[str] = []
    rendered: Mapping[str, object] = template.to_json()
    resources = rendered.get("Resources", {})
    assert isinstance(resources, dict)
    for raw_resource in resources.values():
        assert isinstance(raw_resource, dict)
        properties = raw_resource.get("Properties", {})
        if not isinstance(properties, dict):
            continue
        for key in (
            "BucketName",
            "FunctionName",
            "Name",
            "QueueName",
            "RestApiName",
            "RoleName",
            "StateMachineName",
            "TableName",
            "TopicName",
            "UserPoolName",
        ):
            value = properties.get(key)
            if isinstance(value, str) and value.startswith("careervp-"):
                names.append(value)
    return names


def test_default_settings_remain_pinned_to_live_region() -> None:
    settings = ScratchDeploymentSettings.default()

    assert settings.scratch_mode is False
    assert settings.account == "788159322332"
    assert settings.region == "us-east-1"
    assert settings.environment == "dev"


def test_unflagged_live_environment_override_is_preserved(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("CAREERVP_SCRATCH_MODE", raising=False)
    monkeypatch.setenv("ENVIRONMENT", "staging")

    settings = ScratchDeploymentSettings.from_environment()

    assert settings.scratch_mode is False
    assert settings.account == "788159322332"
    assert settings.region == "us-east-1"
    assert settings.environment == "staging"
    assert settings.configuration_source == "staging"


def test_explicit_scratch_mode_synthesizes_service_only_in_eu_west_1(
    scratch_stack: ServiceStack,
) -> None:
    assembly = cast(App, scratch_stack.node.root).synth()

    assert scratch_stack.region == "eu-west-1"
    assert scratch_stack.termination_protection is False
    assert {artifact.stack_name for artifact in assembly.stacks} == {
        scratch_stack.stack_name
    }
    assert all("Frontend" not in artifact.stack_name for artifact in assembly.stacks)


def test_scratch_template_has_raw_url_and_no_custom_domain_resources(
    scratch_templates: list[Template],
) -> None:
    template = scratch_templates[0]

    template.has_output(
        "RawApiInvokeUrl",
        {"Value": Match.any_value()},
    )
    template.resource_count_is("AWS::ApiGateway::DomainName", 0)
    template.resource_count_is("AWS::ApiGateway::BasePathMapping", 0)
    template.resource_count_is("AWS::CertificateManager::Certificate", 0)
    assert "api.dev.careervp.com" not in str(template.to_json())


def test_scratch_physical_names_are_unique_and_never_dev(
    scratch_templates: list[Template],
) -> None:
    names = [
        name for template in scratch_templates for name in _resource_names(template)
    ]

    assert names
    assert len(names) == len(set(names))
    assert all(SCRATCH_ENVIRONMENT in name for name in names)
    assert all(not name.endswith("-dev") for name in names)


def test_scratch_stateful_resources_are_destroyable_and_unprotected(
    scratch_templates: list[Template],
) -> None:
    template = scratch_templates[0]

    for resource_type in ("AWS::DynamoDB::GlobalTable", "AWS::S3::Bucket"):
        resources = template.find_resources(resource_type)
        assert resources
        for resource in resources.values():
            assert resource["DeletionPolicy"] == "Delete"
            assert resource["UpdateReplacePolicy"] == "Delete"

    for table in template.find_resources("AWS::DynamoDB::GlobalTable").values():
        for replica in table["Properties"]["Replicas"]:
            assert replica.get("DeletionProtectionEnabled") is False

    assert template.find_resources("Custom::S3AutoDeleteObjects")


def test_recursive_scratch_templates_have_no_retains_or_account_level_resources(
    scratch_templates: list[Template],
) -> None:
    for template in scratch_templates:
        rendered = template.to_json()
        for resource in rendered.get("Resources", {}).values():
            assert resource.get("DeletionPolicy") not in {"Retain", "Snapshot"}
            assert resource.get("UpdateReplacePolicy") not in {"Retain", "Snapshot"}
        template.resource_count_is("AWS::Budgets::Budget", 0)
        template.resource_count_is("AWS::CE::AnomalyMonitor", 0)
        template.resource_count_is("AWS::CE::AnomalySubscription", 0)
        template.resource_count_is("AWS::ApiGateway::Account", 0)


def test_every_scratch_lambda_has_an_explicit_unique_physical_name(
    scratch_templates: list[Template],
) -> None:
    names: list[str] = []
    for template in scratch_templates:
        for logical_id, function in template.find_resources(
            "AWS::Lambda::Function"
        ).items():
            function_name = function["Properties"].get("FunctionName")
            assert isinstance(function_name, str), logical_id
            assert function_name.endswith(f"-{SCRATCH_ENVIRONMENT}")
            names.append(function_name)
    assert names
    assert len(names) == len(set(names))


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"environment": "dev"}, "reserved"),
        ({"environment": "stage"}, "reserved"),
        ({"environment": "staging"}, "reserved"),
        ({"environment": "prod"}, "reserved"),
        ({"environment": "production"}, "reserved"),
        # A live-tier token in the suffix would mint physical names ending -dev/-prod.
        ({"environment": "rto-euw1-20260712-dev"}, "live-tier token"),
        ({"environment": "rto-euw1-20260712-prod"}, "live-tier token"),
        ({"environment": "rto-euw1-20260712-staging-1"}, "live-tier token"),
        ({"region": "us-east-1"}, "eu-west-1"),
        ({"account": ""}, "account"),
        ({"configuration_source": "dev"}, "test"),
        ({"allowed_origin": "https://dev.careervp.com"}, "scratch"),
    ],
)
def test_invalid_scratch_combinations_fail_closed(
    overrides: dict[str, str], message: str
) -> None:
    values = {
        "account": SCRATCH_ACCOUNT,
        "region": "eu-west-1",
        "environment": SCRATCH_ENVIRONMENT,
        "configuration_source": "test",
        "allowed_origin": SCRATCH_ORIGIN,
    }
    values.update(overrides)

    with pytest.raises(ValueError, match=message):
        ScratchDeploymentSettings(
            account=values["account"],
            region=values["region"],
            environment=values["environment"],
            configuration_source=values["configuration_source"],
            allowed_origin=values["allowed_origin"],
        )


@pytest.mark.parametrize(
    "environment",
    ["rto-euw1-20260712", "rto-euw1-20260712-a1", "rto-euw1-20260712-b2-retry"],
)
def test_valid_scratch_environments_are_accepted(environment: str) -> None:
    """The live-tier token guard must not reject a legitimate scratch environment."""
    settings = ScratchDeploymentSettings(
        account=SCRATCH_ACCOUNT,
        region="eu-west-1",
        environment=environment,
        configuration_source="test",
        allowed_origin=SCRATCH_ORIGIN,
    )
    assert settings.environment == environment
    assert settings.scratch_mode is True


def test_scratch_overrides_require_explicit_scratch_settings() -> None:
    app = App()
    naming = NamingUtils(
        environment=SCRATCH_ENVIRONMENT,
        region="eu-west-1",
        account_id=SCRATCH_ACCOUNT,
    )

    with pytest.raises(ValueError, match="scratch_settings"):
        ServiceStack(
            scope=app,
            id=naming.stack_id("crud"),
            env=Environment(account=SCRATCH_ACCOUNT, region="eu-west-1"),
            is_production_env=False,
            naming=naming,
            stack_feature="crud",
            scratch_teardown_safe=True,
        )


def test_lower_level_scratch_boundaries_do_not_expose_destructive_booleans() -> None:
    constructors = (
        ApiConstruct.__init__,
        ApiDbConstruct.__init__,
        CognitoConstruct.__init__,
        ConfigurationStore.__init__,
        MonitoringNestedStack.__init__,
    )
    forbidden = {
        "scratch_mode",
        "scratch_teardown_safe",
        "include_account_cost_resources",
    }

    for constructor in constructors:
        assert forbidden.isdisjoint(signature(constructor).parameters)
        assert "scratch_settings" in signature(constructor).parameters


def test_scratch_configuration_and_ssm_names_are_explicit_and_isolated(
    scratch_templates: list[Template],
) -> None:
    rendered = "\n".join(str(template.to_json()) for template in scratch_templates)

    assert '"configuration_source": "test"' not in rendered
    assert "premium_features" in rendered
    assert f"/careervp/{SCRATCH_ENVIRONMENT}/anthropic-api-key" in rendered
    assert f"/careervp/{SCRATCH_ENVIRONMENT}/tavily-api-key" not in rendered
    assert "scratch-disabled-tavily-api-key" in rendered
    assert f"/careervp/{SCRATCH_ENVIRONMENT}/jwt-private-key" not in rendered
    assert f"/careervp/{SCRATCH_ENVIRONMENT}/jwt-public-key" not in rendered
    assert (
        f"/careervp/{SCRATCH_ENVIRONMENT}/payment-provider-webhook-secret"
        not in rendered
    )
    assert "scratch-disabled-jwt-private-key" in rendered
    assert "scratch-disabled-jwt-public-key" in rendered
    assert "scratch-disabled-payment-provider-webhook-secret" in rendered
    assert "/careervp/dev/" not in rendered
    assert "dev.careervp.com" not in rendered
    assert "stage.careervp.com" not in rendered
    assert "app.careervp.com" not in rendered
    assert SCRATCH_ORIGIN in rendered


def test_scratch_resources_include_environment_tag(
    scratch_templates: list[Template],
) -> None:
    rendered = scratch_templates[0].to_json()
    tagged_resources = [
        resource
        for resource in rendered["Resources"].values()
        if isinstance(resource.get("Properties", {}).get("Tags"), list)
    ]

    assert tagged_resources
    assert any(
        {"Key": "environment", "Value": SCRATCH_ENVIRONMENT}
        in resource["Properties"]["Tags"]
        for resource in tagged_resources
    )
