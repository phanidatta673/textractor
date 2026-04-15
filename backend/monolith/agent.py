import os
import shutil
import subprocess

class IssueAgent:
    def __init__(self, issue_id):
        self.issue_id = issue_id
        self.repo_url = f"https://{os.environ.get('GITHUB_TOKEN')}@github.com/{os.environ.get('GITHUB_REPOSITORY')}.git"
        self.workspace = f"/tmp/agent-{issue_id}"
        self.branch_name = f"issue-fix-{issue_id}"

    def prepare_workspace(self):
        if os.path.exists(self.workspace):
            shutil.rmtree(self.workspace)
        
        # In a real environment, we'd clone. For this task, we'll implement the subprocess calls.
        subprocess.run(["git", "clone", self.repo_url, self.workspace], check=True)
        subprocess.run(["git", "checkout", "-b", self.branch_name], cwd=self.workspace, check=True)
        return self.workspace

    def cleanup(self):
        if os.path.exists(self.workspace):
            shutil.rmtree(self.workspace)
