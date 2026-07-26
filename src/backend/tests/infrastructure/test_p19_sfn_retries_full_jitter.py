"""RED contract for P-19 Step Functions retry jitter and StartVPR heartbeat."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any, cast

os.environ.setdefault('JSII_RUNTIME_PACKAGE_CACHE', '/tmp/jsii-cache')
os.environ.setdefault('JSII_SILENCE_WARNING_UNTESTED_NODE_VERSION', '1')

from aws_cdk import App, Environment, NestedStack
from aws_cdk.assertions import Template

REPO_ROOT = Path(__file__).resolve().parents[4]
INFRA_SRC = str(REPO_ROOT / 'infra')

EXPECTED_RETRY_POLICIES = {
    'StartCoverLetter': {'ErrorEquals': ['States.TaskFailed'], 'MaxAttempts': 2, 'BackoffRate': 2.0},
    'StartInterviewPrep': {'ErrorEquals': ['States.TaskFailed'], 'MaxAttempts': 2, 'BackoffRate': 2.0},
    'StartCVTailoring': {'ErrorEquals': ['States.TaskFailed'], 'MaxAttempts': 2, 'BackoffRate': 2.0},
    'StartVPR': {'ErrorEquals': ['States.TaskFailed'], 'MaxAttempts': 2, 'BackoffRate': 2.0},
    'StartCompanyResearch': {'ErrorEquals': ['CRRetryableError'], 'MaxAttempts': 3, 'BackoffRate': 2.0},
}
EXPECTED_JITTER_STRATEGY = 'FULL'
EXPECTED_START_VPR_HEARTBEAT_SECONDS = 180


def _all_resources() -> dict[str, dict[str, Any]]:
    sys.path = [path for path in sys.path if path != INFRA_SRC]
    sys.path.insert(0, INFRA_SRC)
    for module_name, module in list(sys.modules.items()):
        if module_name == 'careervp' or module_name.startswith('careervp.'):
            module_file = str(getattr(module, '__file__', '') or '')
            if not module_file.startswith(INFRA_SRC):
                sys.modules.pop(module_name, None)

    from careervp.naming_utils import NamingUtils  # type: ignore[import-untyped]
    from careervp.service_stack import ServiceStack  # type: ignore[import-untyped]

    app = App(context={'p26_rehome_features': 'true'})
    naming = NamingUtils(
        environment='devx',
        region='us-east-1',
        account_id='788159322332',
    )
    stack = ServiceStack(
        scope=app,
        id=naming.stack_id('crud'),
        env=Environment(account='788159322332', region='us-east-1'),
        is_production_env=False,
        naming=naming,
        stack_feature='crud',
    )
    templates = [Template.from_stack(stack)]
    templates.extend(Template.from_stack(construct) for construct in stack.node.find_all() if isinstance(construct, NestedStack))
    return {logical_id: resource for template in templates for logical_id, resource in template.to_json().get('Resources', {}).items()}


def _definition_string(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, dict) and isinstance(value.get('Fn::Join'), list):
        separator, parts = value['Fn::Join']
        assert isinstance(separator, str), f'AC-P19-1 expected Fn::Join separator string, got {separator!r}'
        assert isinstance(parts, list), f'AC-P19-1 expected Fn::Join parts list, got {parts!r}'
        return separator.join(part if isinstance(part, str) else 'TOKEN' for part in parts)
    raise AssertionError(f'AC-P19-1 expected DefinitionString or Fn::Join, got {value!r}')


def _state_machine_definition() -> dict[str, Any]:
    resources = _all_resources()
    matches = [
        resource
        for resource in resources.values()
        if resource.get('Type') == 'AWS::StepFunctions::StateMachine'
        and resource.get('Properties', {}).get('StateMachineName') == 'careervp-artifact-chain-statemachine-devx'
    ]
    assert len(matches) == 1, f'AC-P19-1 expected one artifact-chain state machine, found {len(matches)}'
    definition = matches[0].get('Properties', {}).get('DefinitionString')
    parsed = json.loads(_definition_string(definition))
    assert isinstance(parsed, dict), f'AC-P19-1 expected object definition, got {parsed!r}'
    return cast(dict[str, Any], parsed)


def _states_by_name(states: dict[str, Any]) -> dict[str, dict[str, Any]]:
    found: dict[str, dict[str, Any]] = {}
    for state_name, state in states.items():
        assert isinstance(state, dict), f'AC-P19-1 state {state_name} must synthesize as an object'
        found[state_name] = state
        if state.get('Type') == 'Parallel':
            branches = state.get('Branches', [])
            assert isinstance(branches, list), f'AC-P19-1 parallel state {state_name} must have Branches'
            for branch in branches:
                assert isinstance(branch, dict), f'AC-P19-1 parallel state {state_name} branch must be an object'
                branch_states = branch.get('States')
                assert isinstance(branch_states, dict), f'AC-P19-1 parallel state {state_name} branch must have States'
                found.update(_states_by_name(branch_states))
    return found


def test_p19_sfn_retries_use_full_jitter_and_start_vpr_heartbeat() -> None:
    """AC-P19-1: artifact-chain retries use full jitter and StartVPR has a 180s heartbeat."""
    definition = _state_machine_definition()
    states = definition.get('States')
    assert isinstance(states, dict), 'AC-P19-1 artifact-chain definition must have States'
    states_by_name = _states_by_name(states)

    for state_name, expected_policy in EXPECTED_RETRY_POLICIES.items():
        assert state_name in states_by_name, f'AC-P19-1 missing state {state_name}'
        retries = states_by_name[state_name].get('Retry')
        assert isinstance(retries, list) and retries, f'AC-P19-1 {state_name} must have Retry entries'
        matching_retries = [retry for retry in retries if isinstance(retry, dict) and retry.get('ErrorEquals') == expected_policy['ErrorEquals']]
        assert len(matching_retries) == 1, f'AC-P19-1 {state_name} expected one Retry for {expected_policy["ErrorEquals"]}; got {matching_retries!r}'
        retry = matching_retries[0]
        assert retry.get('JitterStrategy') == EXPECTED_JITTER_STRATEGY, (
            f'AC-P19-1 {state_name} Retry missing JitterStrategy={EXPECTED_JITTER_STRATEGY}; got {retry.get("JitterStrategy")!r}'
        )
        assert retry.get('MaxAttempts') == expected_policy['MaxAttempts'], (
            f'AC-P19-1 {state_name} Retry MaxAttempts changed; expected {expected_policy["MaxAttempts"]}, got {retry.get("MaxAttempts")!r}'
        )
        assert retry.get('BackoffRate') == expected_policy['BackoffRate'], (
            f'AC-P19-1 {state_name} Retry BackoffRate changed; expected {expected_policy["BackoffRate"]}, got {retry.get("BackoffRate")!r}'
        )

    start_vpr = states_by_name.get('StartVPR')
    assert start_vpr is not None, 'AC-P19-1 missing state StartVPR'
    assert start_vpr.get('HeartbeatSeconds') == EXPECTED_START_VPR_HEARTBEAT_SECONDS, (
        f'AC-P19-1 StartVPR missing HeartbeatSeconds={EXPECTED_START_VPR_HEARTBEAT_SECONDS}; got {start_vpr.get("HeartbeatSeconds")!r}'
    )
