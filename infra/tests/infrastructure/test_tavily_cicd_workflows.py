from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]


def test_deploy_workflows_seed_tavily_ssm_parameter() -> None:
    for workflow_path in (
        ROOT / ".github/workflows/deploy.yml",
        ROOT / ".github/workflows/deploy-staging.yml",
    ):
        workflow = workflow_path.read_text()
        assert "TAVILY_API_KEY" in workflow
        assert "tavily-api-key" in workflow
        assert "--type SecureString" in workflow
        assert "--overwrite" in workflow


def test_tavily_handshake_workflow_triggers_and_seeds_secret() -> None:
    workflow = (ROOT / ".github/workflows/test-tavily-handshake.yml").read_text()

    assert "cron:" in workflow
    assert "src/backend/careervp/logic/utils/web_search.py" in workflow
    assert "src/backend/careervp/logic/utils/tavily_client.py" in workflow
    assert "TAVILY_API_KEY" in workflow
    assert "/careervp/dev/tavily-api-key" in workflow
