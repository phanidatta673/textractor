# Textractor FastAPI Monolith Final Design

## Objective
Consolidate the serverless backend (multiple Lambdas) and the Next.js frontend into a single, monolithic FastAPI application hosted on an AWS Free Tier EC2 instance. This move simplifies the architecture, improves security via a static secret code, and provides a robust CLI for GitHub Action workflows.

## Architecture

### 1. Monolithic Backend (FastAPI)
- **Framework**: FastAPI with `uvicorn`.
- **Frontend Delivery**: A `/html` route serves a standalone `index.html` file using `HTMLResponse`.
- **Endpoints**:
    - `POST /api/process`: Receives `multipart/form-data` (file), validates `X-Secret-Code` header, uploads to S3, and starts a `BackgroundTask`.
    - `GET /api/status/{file_id}`: Fetches extraction status and content from DynamoDB.
    - `POST /github-webhook`: Handles GitHub issue events.
    - `GET /health`: Basic health check.
- **Extraction Engine**: Inherits logic from the `ExtractionProcessor` Lambda (supporting PDF, DOCX, TXT, ZIP).
- **CLI Mode**: If run with specific flags (e.g., `--process-issue`), the application processes a GitHub issue directly without starting the web server.

### 2. Frontend (Standalone Static UI)
- **Location**: `backend/monolith/static/index.html`.
- **Technology**: Single-file HTML/JS/CSS (Tailwind via CDN).
- **Workflow**:
    1.  User selects file(s) via drag-and-drop or file browser.
    2.  User enters the required Secret Code.
    3.  User clicks "Submit".
    4.  The frontend performs concurrent `POST /api/process` calls with the `X-Secret-Code` header.
    5.  The UI polls `/api/status/{file_id}` until extraction is complete.
- **Persistence**: `localStorage` stores the Secret Code and extraction history.

### 3. Infrastructure (Terraform)
- **Host**: AWS `t2.micro` or `t2.small` EC2 instance (Ubuntu 22.04).
- **Cleanup**: All existing Lambda and API Gateway resources are decommissioned.
- **Security**:
    - EC2 Instance Profile: For IAM-based access to S3 and DynamoDB.
    - Security Group: Port 80 (HTTP) and Port 22 (SSH).
- **Provisioning**: `user_data` script handles system updates, Python environment setup, repository cloning, and application launch.

### 4. GitHub Action Integration
- **Workflow**: `.github/workflows/issue-processor.yml` will be triggered by issue events or manually, invoking the monolith in CLI mode to process data and post results as comments.

## Data Flow
1. **User** -> Accesses `http://ec2-public-ip/html`.
2. **User** -> Selects files, enters Secret Code, clicks "Submit".
3. **Frontend** -> `POST /api/process` (with `X-Secret-Code` header).
4. **Backend** -> Validates code, uploads to S3, updates DynamoDB (PENDING), returns success.
5. **Backend (BackgroundTask)** -> Processes file, updates DynamoDB (PROCESSING -> COMPLETED/FAILED).
6. **Frontend** -> Polls `/api/status/{file_id}` until result is available.

## Success Criteria
- [ ] No more AWS Lambda or API Gateway resources in Terraform.
- [ ] FastAPI app serves UI on `/html`.
- [ ] File processing works (upload -> background extraction -> result).
- [ ] Unauthorized requests (missing/wrong Secret Code) return 403.
- [ ] CLI mode successfully processes a mock GitHub issue.
- [ ] All Next.js and frontend-specific build files are removed.
