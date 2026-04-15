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
