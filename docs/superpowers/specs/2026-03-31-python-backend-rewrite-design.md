# Python Backend Rewrite Design

## Objective
Rewrite the backend Lambdas from TypeScript to Python (minimalist approach) and provide comprehensive documentation.

## Architecture & Components

### 1. Lambdas (Python 3.11)
Each Lambda function will be rewritten in Python using `boto3` and minimalist dependencies.

- **`get-presigned-url`**: Generates a UUID for `fileId` and returns a presigned S3 URL for uploads.
- **`start-extraction`**: Initializes a DynamoDB record with "PENDING" status and triggers the processor.
- **`get-status`**: Fetches the current extraction status and content from DynamoDB.
- **`extraction-processor`**: Main processing engine. Downloads from S3, extracts text based on extension (PDF, DOCX, TXT, ZIP), and updates DynamoDB.
- **`github-issue-handler`**: Responds to GitHub issues by launching Sprite sandboxes.

### 2. Infrastructure (Terraform)
- Update `aws_lambda_function` resources to use `python3.11` runtime.
- Update `handler` to `index.handler` (pointing to `index.py`).
- Update `data.archive_file` to include the Python files and excludes the old TypeScript/JS/Node files.

### 3. Build & Packaging
- A new `backend/build.sh` (Python-based) will:
    1.  Create a `dist` or `build` folder for each Lambda.
    2.  Install dependencies from `requirements.txt` into that folder.
    3.  Copy the `index.py` (and any other modules) into it.
    4.  The Terraform `archive_file` will then zip this folder.

### 4. Documentation
A root `/docs` folder containing:
- `frontend.md`: UI architecture and component overview.
- `backend.md`: Lambda architecture, database schemas, and infrastructure.
- `technical-flow.md`: End-to-end sequence flow and error handling.

## Data Flow
1.  **Client** -> `GET /presigned-url` (via API GW).
2.  **GetPresignedUrl** -> returns URL + `fileId` + `key`.
3.  **Client** -> `PUT` file to S3.
4.  **Client** -> `POST /start` with `fileId`, `key`, `bucket`.
5.  **StartExtraction** -> Updates DynamoDB `Extractions` table (Status: PENDING).
6.  **StartExtraction** -> Invokes `ExtractionProcessor` (Async).
7.  **ExtractionProcessor** -> `GET` from S3 -> `Extract Text` -> `Update` DynamoDB (Status: COMPLETED/FAILED, Content: ...).
8.  **Client** -> `GET /status/{fileId}` (Polling).
9.  **GetStatus** -> Returns DynamoDB record.

## Dependencies (Minimalist)
- `boto3` (AWS SDK for Python) - Included in Lambda runtime.
- `pypdf` - For PDF text extraction.
- `python-docx` - For DOCX text extraction.
- `urllib.request` - Standard library for HTTP requests.
- `zipfile` - Standard library for ZIP handling.
- `json`, `uuid`, `os`, `time`, `datetime` - Standard library.

## Error Handling
- Use `try/except` blocks in all Lambdas.
- Return consistent error messages with appropriate HTTP status codes (400 for bad input, 500 for server errors).
- Log errors to CloudWatch.
- Update DynamoDB status to "FAILED" with an error message in the `extraction-processor`.

## Verification & Testing
- Manual testing of each Lambda using API Gateway endpoints.
- Verification of text extraction for each supported format (PDF, DOCX, TXT, ZIP).
- Check DynamoDB records for status and content updates.
- Check S3 for correct file uploads.
