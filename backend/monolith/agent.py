import os
import shutil
import subprocess
import urllib.request
import json
import re

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

    def get_fix(self, title, body):
        # Read relevant files
        files_to_send = ["backend/monolith/main.py", "backend/monolith/static/index.html"]
        context = {}
        for f in files_to_send:
            path = os.path.join(self.workspace, f)
            if os.path.exists(path):
                with open(path, "r") as file:
                    context[f] = file.read()

        prompt = f"Issue Title: {title}\nIssue Body: {body}\n\nFiles:\n{json.dumps(context)}\n\n"
        prompt += "Provide the full updated content for any files that need changes in a JSON format: {\"path\": \"content\"}. Only return the JSON."

        return self._call_gemini(prompt)

    def _call_gemini(self, prompt):
        api_key = os.environ.get("GEMINI_API_KEY")
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-pro:generateContent?key={api_key}"
        
        payload = {
            "contents": [{"parts": [{"text": prompt}]}]
        }
        
        req = urllib.request.Request(url, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req) as res:
            response_data = json.loads(res.read().decode())
            text = response_data['candidates'][0]['content']['parts'][0]['text']
            # Extract JSON from text (in case model adds markdown)
            json_str = re.search(r'\{.*\}', text, re.DOTALL).group()
            return json.loads(json_str)

    def cleanup(self):
        if os.path.exists(self.workspace):
            shutil.rmtree(self.workspace)
