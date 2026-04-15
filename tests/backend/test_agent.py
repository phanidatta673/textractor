from unittest.mock import patch, MagicMock
import json
from backend.monolith.agent import IssueAgent

def test_agent_prepare_workspace(monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "test-token")
    monkeypatch.setenv("GITHUB_REPOSITORY", "test/repo")
    agent = IssueAgent(issue_id=1)
    try:
        # We need to mock subprocess.run for this test to avoid real git operations
        from unittest.mock import patch
        with patch("subprocess.run") as mock_run:
            workspace = agent.prepare_workspace()
            assert workspace == f"/tmp/agent-1"
            assert mock_run.call_count == 2 # clone and checkout
    finally:
        agent.cleanup()

@patch("backend.monolith.agent.IssueAgent._call_gemini")
def test_agent_get_fix(mock_gemini):
    mock_gemini.return_value = {"main.py": "new content"}
    agent = IssueAgent(issue_id=1)
    # Mock os.path.exists to always return False for simplicity in test
    with patch("os.path.exists", return_value=False):
        fix = agent.get_fix("Change button color", "The submit button should be blue.")
        assert fix == {"main.py": "new content"}

@patch("backend.monolith.agent.IssueAgent.get_fix")
@patch("backend.monolith.agent.IssueAgent.deploy_sprite")
@patch("backend.monolith.agent.IssueAgent.prepare_workspace")
@patch("backend.monolith.agent.IssueAgent.verify")
def test_agent_run_success(mock_verify, mock_prepare, mock_sprite, mock_fix):
    mock_fix.return_value = {"backend/monolith/main.py": "# modified"}
    mock_sprite.return_value = "http://sprite.sandbox/123"
    mock_verify.return_value = (True, "all passed")
    
    agent = IssueAgent(issue_id=1)
    # Mock subprocess.run to always succeed for tests
    from unittest.mock import patch
    with patch("subprocess.run") as mock_run:
        # Mocking open() to avoid actual file writing during test
        with patch("builtins.open", MagicMock()):
            url = agent.run("Fix bug", "Body")
            assert url == "http://sprite.sandbox/123"
