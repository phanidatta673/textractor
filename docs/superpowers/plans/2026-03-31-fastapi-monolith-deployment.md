# FastAPI Monolith Deployment Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace serverless architecture with a monolithic FastAPI app on EC2, secured by a secret code.

**Architecture:** 
- Monolithic FastAPI backend serving HTML and API.
- Background tasks for extraction logic.
- EC2 hosting with IAM Instance Profile for S3/DynamoDB access.
- Decommissioning of all Lambdas and API Gateways.

**Tech Stack:** FastAPI, Uvicorn, Boto3, Terraform, AWS (EC2, S3, DynamoDB).

---

### Task 1: Initialize FastAPI Monolith Structure

**Files:**
- Create: `backend/monolith/main.py`
- Create: `backend/monolith/requirements.txt`
- Create: `backend/monolith/static/index.html`

- [ ] **Step 1: Create `backend/monolith/requirements.txt`**
- [ ] **Step 2: Create `backend/monolith/main.py` with basic setup and /html route**
- [ ] **Step 3: Create a placeholder `backend/monolith/static/index.html`**

### Task 2: Implement FastAPI API Endpoints

**Files:**
- Modify: `backend/monolith/main.py`

- [ ] **Step 1: Implement `verify_secret` dependency**
- [ ] **Step 2: Port `GetPresignedUrl` logic to `/api/presigned-url`**
- [ ] **Step 3: Port `StartExtraction` logic to `/api/start`**
- [ ] **Step 4: Port `ExtractionProcessor` logic to a background task function**
- [ ] **Step 5: Port `GetStatus` logic to `/api/status/{file_id}`**

### Task 3: Develop the Monolithic UI

**Files:**
- Modify: `backend/monolith/static/index.html`

- [ ] **Step 1: Create the HTML/Tailwind/JS dashboard**
- [ ] **Step 2: Add Secret Code input and header injection logic**
- [ ] **Step 3: Verify local functionality (manual test)**

### Task 4: Infrastructure Transition (Terraform)

**Files:**
- Modify: `terraform/main.tf`
- Modify: `terraform/outputs.tf`

- [ ] **Step 1: Remove all Lambda, API Gateway, and Frontend S3 resources from `main.tf`**
- [ ] **Step 2: Add `aws_instance` (t2.micro) with Ubuntu 22.04**
- [ ] **Step 3: Add `aws_security_group` (allow ports 80, 22)**
- [ ] **Step 4: Add `aws_iam_instance_profile` and `aws_iam_role` for EC2**
- [ ] **Step 5: Update `outputs.tf` for `ec2_public_ip`**

### Task 5: Deployment and Final Verification

- [ ] **Step 1: Run `terraform apply -auto-approve`**
- [ ] **Step 2: SSH into EC2, install dependencies, and start the FastAPI app**
- [ ] **Step 3: Verify the app via the public IP**
