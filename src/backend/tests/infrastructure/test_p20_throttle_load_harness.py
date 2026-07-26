"""RED contract for P-20 API stage throttling and its supporting load harness."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

import pytest

os.environ.setdefault('JSII_RUNTIME_PACKAGE_CACHE', '/tmp/jsii-cache')
os.environ.setdefault('JSII_SILENCE_WARNING_UNTESTED_NODE_VERSION', '1')

from aws_cdk import App, Environment, NestedStack
from aws_cdk.assertions import Template

REPO_ROOT = Path(__file__).resolve().parents[4]
INFRA_SRC = str(REPO_ROOT / 'infra')
LOAD_HARNESS_CONFIG = REPO_ROOT / 'infra' / 'loadtest' / 'load_harness_config.json'

BASELINE_SELF_DOS_RATE = 2
BASELINE_SELF_DOS_BURST = 10


def _synth_resources(infra_src: str) -> dict[str, dict[str, Any]]:
    sys.path = [path for path in sys.path if path != infra_src]
    sys.path.insert(0, infra_src)
    for module_name, module in list(sys.modules.items()):
        if module_name == 'careervp' or module_name.startswith('careervp.'):
            module_file = str(getattr(module, '__file__', '') or '')
            if not module_file.startswith(infra_src):
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


def _all_resources() -> dict[str, dict[str, Any]]:
    return _synth_resources(INFRA_SRC)


def _synth_resources_at_revision(revision: str) -> dict[str, dict[str, Any]]:
    with tempfile.TemporaryDirectory() as tmp:
        archive_path = os.path.join(tmp, 'archive.tar')
        with open(archive_path, 'wb') as archive_file:
            subprocess.run(
                ['git', 'archive', revision, '--', 'infra'],
                cwd=REPO_ROOT,
                stdout=archive_file,
                check=True,
            )
        subprocess.run(['tar', '-xf', archive_path], cwd=tmp, check=True)
        real_build_dir = REPO_ROOT / 'src' / 'backend' / '.build'
        tmp_backend_dir = Path(tmp) / 'src' / 'backend'
        tmp_backend_dir.mkdir(parents=True, exist_ok=True)
        os.symlink(real_build_dir, tmp_backend_dir / '.build')
        return _synth_resources(os.path.join(tmp, 'infra'))


def _stage_method_settings() -> list[dict[str, Any]]:
    resources = _all_resources()
    stages = [resource for resource in resources.values() if resource.get('Type') == 'AWS::ApiGateway::Stage']
    assert len(stages) == 1, f'AC-P20-1 expected exactly one API Gateway stage, found {len(stages)}'
    settings = stages[0].get('Properties', {}).get('MethodSettings')
    assert isinstance(settings, list) and settings, 'AC-P20-1 stage must have MethodSettings'
    return settings


def test_p20_stage_throttle_not_self_dos() -> None:
    """AC-P20-1: stage throttle is raised above the self-DoS baseline of 2 rps / burst 10."""
    settings = _stage_method_settings()
    wildcard = [entry for entry in settings if entry.get('ResourcePath') == '/*' and entry.get('HttpMethod') == '*']
    assert len(wildcard) == 1, f'AC-P20-1 expected one wildcard MethodSettings entry, found {len(wildcard)}'
    rate = wildcard[0].get('ThrottlingRateLimit')
    burst = wildcard[0].get('ThrottlingBurstLimit')
    assert isinstance(rate, (int, float)) and rate > BASELINE_SELF_DOS_RATE, (
        f'AC-P20-1 ThrottlingRateLimit={rate!r} must exceed the self-DoS baseline of {BASELINE_SELF_DOS_RATE}'
    )
    assert isinstance(burst, (int, float)) and burst > BASELINE_SELF_DOS_BURST, (
        f'AC-P20-1 ThrottlingBurstLimit={burst!r} must exceed the self-DoS baseline of {BASELINE_SELF_DOS_BURST}'
    )


def _load_harness_config() -> dict[str, Any]:
    assert LOAD_HARNESS_CONFIG.exists(), f'AC-P20-2 expected load harness config at {LOAD_HARNESS_CONFIG}'
    return json.loads(LOAD_HARNESS_CONFIG.read_text())


def test_p20_load_harness_has_hub_read_and_generate_flow() -> None:
    """AC-P20-2: the load harness config covers a hub read and one generate flow."""
    config = _load_harness_config()
    endpoints = config.get('endpoints')
    assert isinstance(endpoints, dict), 'AC-P20-2 load harness config must have an endpoints object'

    hub_read = endpoints.get('hub_read')
    assert isinstance(hub_read, dict), 'AC-P20-2 load harness config must define endpoints.hub_read'
    assert hub_read.get('method') == 'GET', 'AC-P20-2 hub_read must be a GET'
    assert hub_read.get('path') == '/applications/{application_id}', (
        f'AC-P20-2 hub_read path must be /applications/{{application_id}}; got {hub_read.get("path")!r}'
    )

    generate = endpoints.get('generate')
    assert isinstance(generate, dict), 'AC-P20-2 load harness config must define endpoints.generate'
    assert generate.get('method') == 'POST', 'AC-P20-2 generate must be a POST'
    assert isinstance(generate.get('path'), str) and generate['path'].endswith('/generate'), (
        f'AC-P20-2 generate path must be a /generate endpoint; got {generate.get("path")!r}'
    )


def test_p20_load_harness_asserts_p99_threshold() -> None:
    """AC-P20-2: the load harness config pins a concrete, numeric p99 threshold."""
    config = _load_harness_config()
    thresholds = config.get('thresholds')
    assert isinstance(thresholds, dict), 'AC-P20-2 load harness config must have a thresholds object'
    p99_ms = thresholds.get('p99_ms')
    assert isinstance(p99_ms, (int, float)) and p99_ms > 0, f'AC-P20-2 thresholds.p99_ms must be a concrete positive number; got {p99_ms!r}'
    max_error_rate = thresholds.get('max_error_rate')
    assert isinstance(max_error_rate, (int, float)) and 0 <= max_error_rate < 1, (
        f'AC-P20-2 thresholds.max_error_rate must be a fraction in [0, 1); got {max_error_rate!r}'
    )


def _wildcard_throttle(resources: dict[str, dict[str, Any]]) -> tuple[Any, Any] | None:
    stages = [r for r in resources.values() if r.get('Type') == 'AWS::ApiGateway::Stage']
    if len(stages) != 1:
        return None
    for entry in stages[0].get('Properties', {}).get('MethodSettings', []):
        if entry.get('ResourcePath') == '/*' and entry.get('HttpMethod') == '*':
            return entry.get('ThrottlingRateLimit'), entry.get('ThrottlingBurstLimit')
    return None


def test_p20_throttle_change_has_zero_stateful_replacement() -> None:
    """AC-P20-1: raising the throttle vs. the last committed revision changes ONLY the wildcard
    ThrottlingRateLimit/ThrottlingBurstLimit values — no resource is added, removed, or otherwise
    modified, so a live cdk diff of this change carries zero stateful-replacement risk.

    This is a MIGRATION guard: it only has meaning while a throttle raise sits uncommitted in the
    working tree. Once P-20 landed (commit b624e96) HEAD already carries the raised values, so there
    is no pending delta to check and the guard goes dormant — it re-arms automatically the next time
    someone changes the throttle without committing. The steady-state invariants it used to also
    assert (throttle is above the self-DoS baseline; no stateful resource churns) are permanently
    covered by test_p20_stage_throttle_not_self_dos and the apigw-collapse stateful baseline."""
    before = _synth_resources_at_revision('HEAD')
    after = _all_resources()

    if _wildcard_throttle(before) == _wildcard_throttle(after):
        pytest.skip('no uncommitted throttle change vs HEAD; P-20 migration guard is dormant (landed in b624e96)')

    assert set(before.keys()) == set(after.keys()), (
        f'AC-P20-1 the throttle change must not add or remove any resource; added={set(after) - set(before)!r} removed={set(before) - set(after)!r}'
    )

    changed_logical_ids = {logical_id for logical_id in before if before[logical_id] != after[logical_id]}
    stages_before = {lid: r for lid, r in before.items() if r.get('Type') == 'AWS::ApiGateway::Stage'}
    assert len(stages_before) == 1, f'AC-P20-1 expected exactly one API Gateway stage at HEAD, found {len(stages_before)}'
    stage_logical_id = next(iter(stages_before))

    assert changed_logical_ids == {stage_logical_id}, (
        f'AC-P20-1 expected only the stage resource {stage_logical_id!r} to change; also changed: {changed_logical_ids - {stage_logical_id}!r}'
    )

    before_wildcard = next(
        entry
        for entry in before[stage_logical_id]['Properties']['MethodSettings']
        if entry.get('ResourcePath') == '/*' and entry.get('HttpMethod') == '*'
    )
    after_wildcard = next(
        entry
        for entry in after[stage_logical_id]['Properties']['MethodSettings']
        if entry.get('ResourcePath') == '/*' and entry.get('HttpMethod') == '*'
    )
    assert after_wildcard['ThrottlingRateLimit'] > before_wildcard['ThrottlingRateLimit'], (
        f'AC-P20-1 ThrottlingRateLimit must increase vs HEAD; before={before_wildcard["ThrottlingRateLimit"]!r} '
        f'after={after_wildcard["ThrottlingRateLimit"]!r}'
    )
    assert after_wildcard['ThrottlingBurstLimit'] > before_wildcard['ThrottlingBurstLimit'], (
        f'AC-P20-1 ThrottlingBurstLimit must increase vs HEAD; before={before_wildcard["ThrottlingBurstLimit"]!r} '
        f'after={after_wildcard["ThrottlingBurstLimit"]!r}'
    )
    non_throttle_diff = {
        key: (before_wildcard.get(key), after_wildcard.get(key))
        for key in set(before_wildcard) | set(after_wildcard)
        if key not in ('ThrottlingRateLimit', 'ThrottlingBurstLimit') and before_wildcard.get(key) != after_wildcard.get(key)
    }
    assert not non_throttle_diff, f'AC-P20-1 no non-throttle MethodSettings fields may change; diff={non_throttle_diff!r}'
