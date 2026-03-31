# Text Extractor App

Cost-efficient text extraction using Next.js, AWS Lambda, S3, and DynamoDB.

## Features
- Dashboard with concurrent uploads.
- Client-side zipping with JSZip.
- Text extraction from PDF, DOCX, TXT, and ZIP.
- GitHub Issue automation using Sprite Sandbox and Gemini CLI.
- Dockerized CI/CD for frontend and backend.

## Deployment
1. Set up GitHub Secrets:
   - `AWS_ACCESS_KEY_ID`
   - `AWS_SECRET_ACCESS_KEY`
   - `AWS_REGION`
2. Run Terraform:
   - `terraform init`
   - `terraform apply`
   - Provide `github_token`, `github_owner`, `github_repo`, and `sprites_token`.

## Infrastructure
- S3: Direct-to-S3 uploads with Presigned URLs. 1-day lifecycle.
- DynamoDB: On-Demand. 10-minute TTL.
- Lambda: Node.js 18.x with `esbuild` for minimal package size.
- API Gateway: HTTP API (Standard tier).

## Testing
- `npm test` runs Playwright with API mocking.
