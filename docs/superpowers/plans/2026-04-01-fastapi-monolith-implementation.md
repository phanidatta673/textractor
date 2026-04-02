# Textractor FastAPI Monolith Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Consolidate the serverless backend and Next.js frontend into a single FastAPI monolith with backend-mediated uploads and CLI capabilities.

**Architecture:** A unified FastAPI server hosting a static single-page UI, handling multi-part file uploads with secret code verification, and processing extractions via background tasks. It also includes a CLI entry point for GitHub Action integration.

**Tech Stack:** Python 3.11, FastAPI, Uvicorn, Boto3, PyPDF, python-docx, Tailwind CSS (via CDN), Terraform.

---

### Task 1: Backend Refactor - Multipart Uploads & Secret Code

**Files:**
- Modify: `backend/monolith/main.py`
- Test: `tests/backend/test_monolith_v2.py`

- [ ] **Step 1: Create a new test file for the consolidated monolith**

```python
import pytest
from fastapi.testclient import TestClient
from backend.monolith.main import app

client = TestClient(app)

def test_upload_without_secret():
    response = client.post("/api/process", files={"file": ("test.txt", b"hello")})
    assert response.status_code == 403

def test_upload_with_invalid_secret():
    response = client.post("/api/process", 
                          files={"file": ("test.txt", b"hello")},
                          headers={"X-Secret-Code": "wrong"})
    assert response.status_code == 403
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/backend/test_monolith_v2.py`
Expected: FAIL (404 or connection error as `/api/process` doesn't exist)

- [ ] **Step 3: Refactor `main.py` to include `/api/process` with multipart support**

```python
from fastapi import FastAPI, Header, HTTPException, Depends, BackgroundTasks, UploadFile, File
# ... (imports)

@app.post("/api/process", dependencies=[Depends(verify_secret)])
async def process_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    x_secret_code: str = Header(...)
):
    file_id = str(uuid.uuid4())
    filename = file.filename
    extension = filename.split('.')[-1].lower() if '.' in filename else ''
    key = f"uploads/{file_id}.{extension}"

    # Read content
    content = await file.read()
    
    # Upload to S3
    try:
        s3_client.put_object(
            Bucket=BUCKET_NAME,
            Key=key,
            Body=content,
            ContentType=file.content_type
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"S3 Upload failed: {str(e)}")

    # Initial DynamoDB status
    update_status(file_id, 'PENDING')

    # Start extraction
    background_tasks.add_task(process_extraction, BUCKET_NAME, key, file_id)

    return {"fileId": file_id, "status": "PENDING"}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/backend/test_monolith_v2.py`
Expected: PASS (ensure `SECRET_CODE` env var is set for tests)

- [ ] **Step 5: Commit**

```bash
git add backend/monolith/main.py tests/backend/test_monolith_v2.py
git commit -m "feat: implement backend-mediated uploads with secret code"
```

---

### Task 2: Frontend Rewrite - Single-Page Static UI

**Files:**
- Modify: `backend/monolith/static/index.html`

- [ ] **Step 1: Update UI to include Secret Code field and Submit button**

Modify `index.html` to:
1.  Remove direct S3 upload logic (no more `PUT` to presigned URL).
2.  Add a `files` array to store selected files before submission.
3.  Implement `submitAll()` that loops through `files` and calls `POST /api/process`.

```javascript
async function handleSubmit() {
    const secret = secretCodeInput.value;
    if (!secret) return alert("Please enter Secret Code");
    
    for (const fileObj of selectedFiles) {
        const formData = new FormData();
        formData.append('file', fileObj.file);
        
        const res = await fetch('/api/process', {
            method: 'POST',
            headers: { 'X-Secret-Code': secret },
            body: formData
        });
        // ... poll status
    }
}
```

- [ ] **Step 2: Verify UI locally**

Run: `cd backend/monolith && python3 main.py`
Open: `http://localhost:8000/html`
Check: Select files -> Enter code -> Submit -> Verify status updates.

- [ ] **Step 3: Commit**

```bash
git add backend/monolith/static/index.html
git commit -m "feat: rewrite frontend for backend-mediated uploads"
```

---

### Task 3: CLI Mode for GitHub Issue Processing

**Files:**
- Modify: `backend/monolith/main.py`

- [ ] **Step 1: Add argument parsing for CLI mode**

```python
import sys
import argparse

def run_cli():
    parser = argparse.ArgumentParser()
    parser.add_argument("--process-issue", type=int, help="GitHub Issue ID to process")
    args = parser.parse_args()
    
    if args.process_issue:
        print(f"Processing issue {args.process_issue}...")
        # Implement logic to fetch issue, find attachments, extract, and post comment
        sys.exit(0)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        run_cli()
    else:
        import uvicorn
        uvicorn.run(app, host="0.0.0.0", port=8000)
```

- [ ] **Step 2: Verify CLI mode**

Run: `python3 backend/monolith/main.py --process-issue 1`
Expected: "Processing issue 1..." output.

- [ ] **Step 3: Commit**

```bash
git add backend/monolith/main.py
git commit -m "feat: add CLI mode to monolith"
```

---

### Task 4: Infrastructure Cleanup - Terraform Update

**Files:**
- Modify: `terraform/main.tf`

- [ ] **Step 1: Remove all Lambda and API Gateway resources**

Delete or comment out:
- `aws_lambda_function.*`
- `aws_apigatewayv2_api.*`
- `aws_lambda_permission.*`
- `aws_iam_role.lambda_exec`
- `aws_iam_role_policy.lambda_policy`

- [ ] **Step 2: Ensure EC2 instance has all required environment variables**

```hcl
user_data = <<-EOF
    # ...
    export SECRET_CODE=${var.secret_code}
    export BUCKET_NAME=${aws_s3_bucket.uploads.id}
    export TABLE_NAME=${aws_dynamodb_table.extractions.name}
    export SPRITES_TOKEN=${var.sprites_token}
    export GITHUB_TOKEN=${var.github_token}
    # ...
    EOF
```

- [ ] **Step 3: Commit**

```bash
git add terraform/main.tf
git commit -m "infra: remove serverless resources and update EC2 environment"
```

---

### Task 5: Decommission Old Components

- [ ] **Step 1: Delete `backend/lambdas/` and `frontend/` (Next.js)**

```bash
rm -rf backend/lambdas
rm -rf frontend
```

- [ ] **Step 2: Update `.github/workflows/deploy.yml` to simplify deployment**

Remove Next.js build and Lambda build steps. Focus on Terraform apply and maybe a health check on the EC2 instance.

- [ ] **Step 3: Commit**

```bash
git add .
git commit -m "cleanup: remove decommissioned serverless and Next.js code"
```
