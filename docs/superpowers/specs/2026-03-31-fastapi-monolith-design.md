# Text Extractor FastAPI Monolith Design

## Objective
Consolidate the serverless backend (multiple Lambdas) and the Next.js frontend into a single, monolithic FastAPI application hosted on an AWS Free Tier EC2 instance. This move simplifies the architecture and improves security via a static secret code.

## Architecture

### 1. Monolithic Backend (FastAPI)
The entire application will reside in a single Python process.
- **Framework**: FastAPI with `uvicorn`.
- **Frontend Delivery**: A `/html` route will serve a standalone `index.html` file using `HTMLResponse`.
- **API Endpoints**:
    - `POST /api/presigned-url`: Wraps the `GetPresignedUrl` logic.
    - `POST /api/start`: Wraps the `StartExtraction` logic and triggers the extraction as a background task.
    - `GET /api/status/{file_id}`: Wraps the `GetStatus` logic (fetching from DynamoDB).
- **Background Processing**: Uses FastAPI's `BackgroundTasks` to execute the `ExtractionProcessor` logic without blocking the main thread.

### 2. Security (Secret Code)
To prevent unauthorized access and exploitation:
- **Backend**: A `SECRET_CODE` environment variable is required.
- **Validation**: All non-GET API routes require an `X-Secret-Code` header. A FastAPI dependency verifies this code against the environment variable.
- **Frontend**: The UI includes a persistent "Secret Code" input field. The value is sent with every API request.

### 3. Data Storage
The application retains the existing AWS managed services:
- **Storage**: AWS S3 (for file uploads).
- **Database**: AWS DynamoDB (for task status and extracted content).
- **IAM**: The EC2 instance will use an IAM Instance Profile with permissions for S3 and DynamoDB.

### 4. Deployment (EC2)
- **Host**: AWS `t2.micro` (Free Tier eligible).
- **OS**: Ubuntu 22.04 LTS.
- **Process Management**: `systemd` or `pm2` to ensure the FastAPI app restarts on failure.
- **Networking**: API Gateway will be replaced by direct access to the EC2 instance (Port 80/443).

## Data Flow
1. **User** -> Accesses `http://ec2-public-ip/html`.
2. **User** -> Enters Secret Code and selects file.
3. **Frontend** -> `POST /api/presigned-url` (with `X-Secret-Code` header).
4. **Backend** -> Returns S3 URL.
5. **Frontend** -> Uploads directly to S3.
6. **Frontend** -> `POST /api/start` (with `X-Secret-Code` header).
7. **Backend** -> Updates DynamoDB (PENDING) and starts `BackgroundTasks`.
8. **Backend (Background)** -> Downloads from S3, extracts text, updates DynamoDB (COMPLETED).
9. **Frontend** -> Polls `/api/status/{file_id}` until success.

## Error Handling
- Invalid Secret Code: Returns `401 Unauthorized`.
- AWS Service Failures: Returns `502 Bad Gateway`.
- Extraction Errors: Updates DynamoDB status to `FAILED`.

## 5. Infrastructure Transition (Terraform)
To minimize cost and complexity, the existing serverless resources will be decommissioned.
- **Remove**:
    - All `aws_lambda_function` resources.
    - `aws_apigatewayv2_api` and all associated routes/stages/integrations.
    - `aws_lambda_permission` resources.
- **Provision**:
    - `aws_instance`: A single `t2.micro` instance.
    - `aws_security_group`: Allowing inbound traffic on Port 80 (HTTP) and Port 22 (SSH).
    - `aws_iam_instance_profile`: Attached to the EC2 instance to provide the necessary IAM permissions for S3 and DynamoDB without needing static access keys.
- **Retain**:
    - `aws_s3_bucket` (uploads): Continued use for file storage.
    - `aws_dynamodb_table` (extractions): Continued use for task tracking.

## Verification Plan
- **Local Verification**: Run the FastAPI app locally and use the `/html` UI to perform a full extraction.
- **Security Check**: Verify that API calls fail if the `X-Secret-Code` header is missing or incorrect.
- **EC2 Deployment**: Verify the app is accessible via the EC2 public IP.
