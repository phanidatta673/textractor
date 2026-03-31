# Backend Documentation

## Overview
The backend is a serverless architecture based on AWS Lambda, S3, and DynamoDB. It has been rewritten from TypeScript to Python for improved performance and simpler dependencies.

## Tech Stack
- **Runtime**: Python 3.11
- **Cloud Provider**: AWS
- **Infrastructure**: Terraform
- **Database**: DynamoDB (for status and content)
- **Storage**: S3 (for file uploads)

## Lambda Functions
1. **`GetPresignedUrl`**: Generates a UUID for the file and returns a presigned URL for S3 upload.
2. **`StartExtraction`**: Triggered by the frontend after upload. Updates DynamoDB and invokes the processor.
3. **`ExtractionProcessor`**: The core logic that parses PDF, DOCX, and ZIP files.
4. **`GetStatus`**: Provides the current state of an extraction task.
5. **`GitHubIssueHandler`**: Webhook handler for GitHub issues, integrating with Sprite.

## Data Schemas
### DynamoDB: `Extractions`
- `fileId` (Partition Key, String): Unique identifier for the file.
- `status` (String): PENDING, PROCESSING, COMPLETED, FAILED.
- `content` (String): The extracted text (if completed).
- `error` (String): Error message (if failed).
- `updatedAt` (String): ISO timestamp.
- `ttl` (Number): Expiration time for the record.

## Build and Deployment
The `backend/build.sh` script handles dependency installation and packaging. Terraform is used to deploy the infrastructure.
