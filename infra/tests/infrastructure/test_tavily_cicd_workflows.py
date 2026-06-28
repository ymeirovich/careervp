from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
HANDSHAKE_WORKFLOW = ROOT / ".github/workflows/test-tavily-handshake.yml"


def test_deploy_workflows_seed_tavily_ssm_parameter() -> None:
    expected_params = {
        ROOT / ".github/workflows/deploy.yml": "/careervp/dev/tavily-api-key",
        ROOT
        / ".github/workflows/deploy-staging.yml": "/careervp/staging/tavily-api-key",
    }
    for workflow_path, expected_param in expected_params.items():
        workflow = workflow_path.read_text()
        assert "aws ssm put-parameter" in workflow
        assert "TAVILY_KEY: ${{ secrets.TAVILY_API_KEY }}" in workflow
        assert expected_param in workflow
        assert "--type SecureString" in workflow
        assert "--overwrite" in workflow


def test_tavily_handshake_workflow_exists() -> None:
    assert HANDSHAKE_WORKFLOW.exists()


def test_tavily_handshake_workflow_triggers_on_change_and_schedule() -> None:
    workflow = HANDSHAKE_WORKFLOW.read_text()

    assert "schedule:" in workflow
    assert "cron:" in workflow
    assert "src/backend/careervp/logic/utils/tavily_client.py" in workflow
    assert "src/backend/careervp/logic/utils/web_search.py" in workflow


def test_tavily_handshake_ensures_ssm_then_runs_client_tests() -> None:
    workflow = HANDSHAKE_WORKFLOW.read_text()

    ensure_step = "name: Ensure Tavily SSM Parameter exists"
    test_step = "uv run pytest tests/unit/test_tavily_client.py -v --tb=short"
    assert ensure_step in workflow
    assert test_step in workflow
    assert workflow.index(ensure_step) < workflow.index(test_step)
    assert "TAVILY_KEY: ${{ secrets.TAVILY_API_KEY }}" in workflow
    assert "/careervp/dev/tavily-api-key" in workflow
