import os
import shutil
import subprocess
import urllib.request
import json
import re
import time

class IssueAgent:
    def __init__(self, issue_id):
        self.issue_id = issue_id
        self.repo_url = f"https://{os.environ.get('GITHUB_TOKEN')}@github.com/{os.environ.get('GITHUB_REPOSITORY')}.git"
        self.workspace = f"/tmp/agent-{issue_id}"
        self.branch_name = f"issue-fix-{issue_id}"

    def prepare_workspace(self):
        print(f"Preparing workspace in {self.workspace}...")
        if os.path.exists(self.workspace):
            shutil.rmtree(self.workspace)
        
        print(f"Cloning {self.repo_url}...")
        subprocess.run(["git", "clone", self.repo_url, self.workspace], check=True, capture_output=True)
        print(f"Checking out branch {self.branch_name}...")
        subprocess.run(["git", "checkout", "-b", self.branch_name], cwd=self.workspace, check=True, capture_output=True)
        return self.workspace

    def cleanup(self):
        print(f"Cleaning up workspace {self.workspace}...")
        if os.path.exists(self.workspace):
            shutil.rmtree(self.workspace)

    def get_fix(self, title, body):
        print(f"Getting fix for issue: {title}...")
        # Read relevant files
        files_to_send = ["backend/monolith/main.py", "backend/monolith/static/index.html"]
        context = {}
        
        # Pre-flight check and context gathering
        print("Checking for required files in workspace...")
        for f in files_to_send:
            path = os.path.join(self.workspace, f)
            if os.path.exists(path):
                print(f"Found {f}, adding to context.")
                with open(path, "r") as file:
                    context[f] = file.read()
            else:
                print(f"WARNING: File {f} not found at {path}")
                # List current directory to help debug if files are missing
                subprocess.run(["ls", "-R", self.workspace], capture_output=False)

        prompt = f"""
Issue Title: {title}
Issue Body: {body}

---
CURRENT PROJECT FILES:
{json.dumps(context, indent=2)}
---

INSTRUCTIONS:
1. Analyze the issue and provide a fix by modifying the files above.
2. Return ONLY a valid JSON object where keys are file paths (relative to repo root) and values are the ENTIRE NEW CONTENT of the file.
3. Do not use snippets or placeholders; provide the full file content.
4. Ensure the JSON is properly escaped.
5. If no changes are needed for a file, do not include it in the JSON.

FORMAT:
{{
  "path/to/file.py": "full content here..."
}}
"""
        return self._call_gemini(prompt)

    def _call_gemini(self, prompt):
        print("Calling Gemini API...")
        api_key = os.environ.get("GEMINI_API_KEY")
        # Use v1beta endpoint for 2.5-flash
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
        
        payload = {
            "contents": [{"parts": [{"text": prompt}]}]
        }
        
        max_retries = 10
        base_delay = 30 # seconds
        
        for attempt in range(max_retries):
            req = urllib.request.Request(url, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"})
            try:
                with urllib.request.urlopen(req) as res:
                    response_data = json.loads(res.read().decode())
                    text = response_data['candidates'][0]['content']['parts'][0]['text']
                    print("Received response from Gemini API.")
                    
                    # Robust JSON extraction: Look for markdown blocks first
                    json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)
                    if json_match:
                        json_str = json_match.group(1)
                    else:
                        # Fallback to finding the first { and last }
                        json_match = re.search(r'(\{.*\})', text, re.DOTALL)
                        if json_match:
                            json_str = json_match.group(1)
                        else:
                            print(f"Raw response text: {text}")
                            raise ValueError("Could not find JSON object in Gemini response")
                    
                    return json.loads(json_str)
            except urllib.error.HTTPError as e:
                if e.code == 429:
                    delay = base_delay * (2 ** attempt)
                    print(f"Gemini API Rate Limit (429). Retrying in {delay}s... (Attempt {attempt+1}/{max_retries})")
                    time.sleep(delay)
                else:
                    print(f"Gemini API HTTP Error: {e.code} - {e.read().decode()}")
                    raise
        
        raise Exception("Failed to call Gemini API after multiple retries due to quota limits.")

    def verify(self):
        print("Verifying fix with pytest...")
        # Run tests in workspace
        # Note: We use absolute path for pytest to ensure it runs correctly
        result = subprocess.run(["python3", "-m", "pytest", "tests/backend"], cwd=self.workspace, capture_output=True, text=True)
        print(f"Pytest exit code: {result.returncode}")
        if result.returncode != 0:
            print(f"STDOUT: {result.stdout}")
            print(f"STDERR: {result.stderr}")
        return result.returncode == 0, result.stdout

    def deploy_sprite(self):
        print("Deploying to Sprite sandbox...")
        token = os.environ.get("SPRITES_TOKEN")
        repo = os.environ.get("GITHUB_REPOSITORY")
        url = "https://api.sprites.dev/v1/sandboxes"
        
        payload = {
            "repository": repo,
            "branch": self.branch_name,
            "config": {"port": 80}
        }
        
        req = urllib.request.Request(url, data=json.dumps(payload).encode(), headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        })
        with urllib.request.urlopen(req) as res:
            sandbox_url = json.loads(res.read().decode())['url']
            print(f"Deployed successfully: {sandbox_url}")
            return sandbox_url

    def run(self, title, body):
        print(f"Starting agent run for issue {self.issue_id}...")
        self.prepare_workspace()
        fix = self.get_fix(title, body)
        
        if not fix:
            raise Exception("Gemini returned an empty fix.")

        for path, content in fix.items():
            full_path = os.path.join(self.workspace, path)
            print(f"Applying fix to {path}...")
            # Ensure directory exists
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, "w") as f:
                f.write(content)
                
        passed, logs = self.verify()
        if not passed:
            print("Verification failed. Logs:")
            print(logs)
            raise Exception(f"Tests failed after applying fix.")
        
        print("Verification passed. Pushing changes to GitHub...")
        subprocess.run(["git", "add", "."], cwd=self.workspace, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", f"fix: {title}"], cwd=self.workspace, check=True, capture_output=True)
        subprocess.run(["git", "push", "origin", self.branch_name, "--force"], cwd=self.workspace, check=True, capture_output=True)
        
        # Create Pull Request
        print("Creating Pull Request...")
        repo = os.environ.get('GITHUB_REPOSITORY')
        token = os.environ.get('GITHUB_TOKEN')
        pr_url = f"https://api.github.com/repos/{repo}/pulls"
        pr_payload = {
            "title": f"fix: {title}",
            "body": f"Automatically generated fix for issue #{self.issue_id}.\n\n{body}",
            "head": self.branch_name,
            "base": "feature/text-extraction-improvements"
        }
        pr_req = urllib.request.Request(pr_url, data=json.dumps(pr_payload).encode(), headers={
            'Authorization': f'token {token}',
            'Accept': 'application/vnd.github.v3+json',
            'Content-Type': 'application/json'
        }, method='POST')
        try:
            with urllib.request.urlopen(pr_req) as pr_res:
                pr_data = json.loads(pr_res.read().decode())
                print(f"Created PR: {pr_data['html_url']}")
        except Exception as e:
            print(f"Failed to create PR (might already exist): {e}")

        return self.deploy_sprite()
