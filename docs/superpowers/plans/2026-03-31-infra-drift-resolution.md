# Infrastructure Drift Resolution and Deployment Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Address infrastructure drift by importing or recreating AWS and GitHub resources, then verify Lambda functionality.

**Architecture:** Use Terraform to synchronize state with the actual environment (which was manually deleted but some IAM roles might persist) and deploy the full stack.

**Tech Stack:** Terraform, AWS (Lambda, S3, DynamoDB, API Gateway, IAM), GitHub (Webhooks).

---

### Task 1: Prepare Terraform Configuration

**Files:**
- Create: `terraform/terraform.tfvars`

- [ ] **Step 1: Create `terraform/terraform.tfvars` with required variables**
    - Note: User provided AWS credentials in `~/.aws/credentials`. I will use those.
    - User needs to provide `github_token` and `sprites_token`.

```hcl
region        = "us-east-1"
github_token  = "USER_PROVIDED_GITHUB_TOKEN"
github_owner  = "phanidatta673"
github_repo   = "textractor"
sprites_token = "USER_PROVIDED_SPRITES_TOKEN"
```

- [ ] **Step 2: Initialize Terraform**
    - Run: `terraform init` in `terraform/` directory.

### Task 2: Address State Drift (Import/Refresh)

- [ ] **Step 1: Import existing IAM role if it exists**
    - Since `text_extractor_lambda_role` was found, it must be imported to avoid "already exists" errors.
    - Run: `terraform import aws_iam_role.lambda_role text_extractor_lambda_role`

- [ ] **Step 2: Refresh state to confirm others are gone**
    - Run: `terraform refresh`

### Task 3: Build Lambda Deployment Packages

- [ ] **Step 1: Execute `backend/build.sh`**
    - This prepares the `dist` directories for each Lambda.
    - Run: `./backend/build.sh`

### Task 4: Deploy Infrastructure

- [ ] **Step 2: Run `terraform apply`**
    - Run: `terraform apply -auto-approve`

### Task 5: Verify Deployed Lambdas

- [ ] **Step 1: Run integration tests against real AWS**
    - We will modify `tests/backend/test_extraction_flow.py` to optionally point to real endpoints or use a new test script.
    - For now, we will verify the functions exist and can be invoked.
    - Run: `aws lambda list-functions` to confirm existence.

### Task 6: Cleanup (Optional)
- [ ] **Step 1: Verify all resources are created and tagged correctly**
