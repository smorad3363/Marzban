from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]
WORKFLOW_PATH = ROOT / ".github" / "workflows" / "backend-tests.yml"


def test_backend_workflow_is_valid_and_non_publishing():
    workflow_text = WORKFLOW_PATH.read_text(encoding="utf-8")
    workflow = yaml.safe_load(workflow_text)

    assert workflow["permissions"] == {"contents": "read"}
    assert "python -m pytest -q" in workflow_text
    assert "packages:" not in workflow_text
    assert "docker/login-action" not in workflow_text
    assert "docker/build-push-action" not in workflow_text
    assert "push: true" not in workflow_text
