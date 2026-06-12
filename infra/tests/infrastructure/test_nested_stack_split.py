from __future__ import annotations

from aws_cdk import App
from aws_cdk.assertions import Template

from careervp.service_stack import ServiceStack


def test_parent_stack_under_resource_ceiling(synthesized_template: Template) -> None:
    count = len(synthesized_template.to_json()["Resources"])
    assert count < 480


def test_parent_has_nested_stack_resource(synthesized_template: Template) -> None:
    nested_stacks = synthesized_template.find_resources("AWS::CloudFormation::Stack")
    assert nested_stacks


def test_monitoring_moved_out_of_parent(synthesized_template: Template) -> None:
    assert not synthesized_template.find_resources("AWS::CloudWatch::Dashboard")


def test_monitoring_nested_stack_contains_dashboards_and_alarms(
    service_stack: ServiceStack,
) -> None:
    template = Template.from_stack(service_stack.api.monitoring)

    assert template.find_resources("AWS::CloudWatch::Dashboard")
    assert template.find_resources("AWS::CloudWatch::Alarm")


def test_artifact_chain_nested_stack_present_after_phase_2(
    service_stack: ServiceStack,
) -> None:
    parent_resources = Template.from_stack(service_stack).to_json()["Resources"]
    state_machines = Template.from_stack(
        service_stack.api.artifact_chain_stack
    ).find_resources("AWS::StepFunctions::StateMachine")

    assert state_machines
    assert not any(
        resource["Type"] == "AWS::StepFunctions::StateMachine"
        for resource in parent_resources.values()
    )
    assert any(
        resource["Type"] == "AWS::CloudFormation::Stack"
        and "ArtifactChain" in logical_id
        for logical_id, resource in parent_resources.items()
    )


def test_no_cross_stack_dependency_cycle(service_stack: ServiceStack) -> None:
    app = App.of(service_stack)
    assert app is not None
    app.synth()
