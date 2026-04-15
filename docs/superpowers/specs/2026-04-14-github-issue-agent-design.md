# Specification: GitHub Issue Agent & Sprite Integration

## 1. Overview
The **GitHub Issue Agent** is an automated workflow integrated into the Textractor Monolith. It enables the application to react to new GitHub issues by automatically attempting a fix, verifying it with tests, and spinning up a temporary sandbox environment (Sprite) for manual verification.

## 2. Architecture
The agent operates **In-Process** on the existing EC2 instance to minimize latency and infrastructure overhead.

### 2.1 Components
- **Webhook Endpoint**: A new FastAPI route (`/api/webhooks/github`) to receive `issues` events from GitHub.
- **Agent Orchestrator**: A background task that manages the lifecycle of an issue fix (clone -> modify -> test -> push -> deploy).
- **Gemini API Integration**: Direct calls to `gemini-1.5-pro` to analyze issue descriptions and generate code changes.
- **Verification Engine**: Executes `pytest` and project-specific tests on the modified code.
- **Sprite Sandbox Provider**: Uses the Sprite API to provision a sandbox for the generated branch.

## 3. Data Flow
1.  **Trigger**: GitHub sends a webhook when an issue is `opened` or `reopened`.
2.  **Ingestion**: The monolith verifies the HMAC signature and extracts the `issue_id`, `title`, and `body`.
3.  **Workspace Preparation**: The orchestrator clones the repository into a temporary directory (e.g., `/tmp/agent-<issue_id>`).
4.  **Inference**:
    - The agent sends the issue details and relevant project files (`main.py`, `static/index.html`) to the Gemini API.
    - Gemini returns the modified code or specific file diffs.
5.  **Implementation**: The agent creates a new branch `issue-fix-<issue_id>` and applies the changes.
6.  **Verification**:
    - The agent runs `PYTHONPATH=. pytest tests/backend`.
    - If tests fail, the agent sends the error logs back to Gemini for a "self-correction" attempt (max 2 retries).
7.  **Delivery**:
    - On success, the agent pushes the branch to GitHub.
    - The agent calls the Sprite API to create a sandbox instance for the new branch.
8.  **Reporting**: The agent posts a comment on the original GitHub issue with:
    - Status of the fix (Success/Failure).
    - Summary of changes made.
    - **Link to the Sprite Sandbox**.

## 4. Security & Configuration
- **`GITHUB_WEBHOOK_SECRET`**: Used to verify incoming requests from GitHub.
- **`GEMINI_API_KEY`**: Required for code generation.
- **`GITHUB_TOKEN`**: Already available; used for pushing branches and commenting on issues.
- **`SPRITES_TOKEN`**: Already available; used for provisioning sandboxes.

## 5. Error Handling
- **Test Failures**: Agent attempts to fix its own errors twice before giving up.
- **API Timeouts**: Background tasks use exponential backoff for external API calls (Gemini, Sprite).
- **Cleanup**: Temporary directories are deleted after the process completes, regardless of success.

## 6. Success Criteria
- A new GitHub issue results in a corresponding `issue-fix-<id>` branch.
- The branch passes existing tests.
- A Sprite sandbox URL is posted to the issue.
