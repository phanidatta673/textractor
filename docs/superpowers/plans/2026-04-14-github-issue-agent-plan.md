# GitHub Issue Agent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Automate GitHub issue resolution by implementing fixes, verifying with tests, and deploying to Sprite sandboxes.

**Architecture:** In-process agent on EC2 FastAPI monolith triggered by GitHub webhooks.

**Tech Stack:** FastAPI, Gemini API, Pytest, Git, Sprite API.

---

### Task 1: GitHub Webhook Signature Verification

**Files:**
- Create: `backend/monolith/utils.py`
- Test: `tests/backend/test_webhook.py`

- [ ] **Step 1: Write the failing test for signature verification**
- [ ] **Step 2: Run test to verify it fails**
- [ ] **Step 3: Implement `verify_github_signature`**
- [ ] **Step 4: Run test to verify it passes**
- [ ] **Step 5: Commit**

---

### Task 2: Webhook Endpoint Implementation

**Files:**
- Modify: `backend/monolith/main.py`
- Test: `tests/backend/test_webhook.py`

- [ ] **Step 1: Write failing test for the `/api/webhooks/github` endpoint**
- [ ] **Step 2: Run test to verify it fails**
- [ ] **Step 3: Implement the webhook endpoint in `main.py`**
- [ ] **Step 4: Run test to verify it passes**
- [ ] **Step 5: Commit**

---

### Task 3: IssueAgent - Git Workspace & Branching

**Files:**
- Create: `backend/monolith/agent.py`
- Test: `tests/backend/test_agent.py`

- [ ] **Step 1: Write test for repo cloning and branch creation**
- [ ] **Step 2: Run test to verify it fails**
- [ ] **Step 3: Implement `IssueAgent.prepare_workspace`**
- [ ] **Step 4: Run test to verify it passes**
- [ ] **Step 5: Commit**

---

### Task 4: Gemini API Integration for Code Modification

**Files:**
- Modify: `backend/monolith/agent.py`
- Test: `tests/backend/test_agent.py`

- [ ] **Step 1: Write test for Gemini code generation**
- [ ] **Step 2: Run test to verify it fails**
- [ ] **Step 3: Implement `get_fix` using Gemini API**
- [ ] **Step 4: Run test to verify it passes**
- [ ] **Step 5: Commit**

---

### Task 5: Verification and Sprite Sandbox Deployment

**Files:**
- Modify: `backend/monolith/agent.py`
- Test: `tests/backend/test_agent.py`

- [ ] **Step 1: Write test for full orchestration flow**
- [ ] **Step 2: Run test to verify it fails**
- [ ] **Step 3: Implement `run`, `verify`, and `deploy_sprite`**
- [ ] **Step 4: Run test to verify it passes**
- [ ] **Step 5: Commit**

---

### Task 6: Final Integration in `main.py`

**Files:**
- Modify: `backend/monolith/main.py`

- [ ] **Step 1: Connect the agent to the webhook background task**
- [ ] **Step 2: Verify with a local mock webhook call**
- [ ] **Step 3: Commit**
