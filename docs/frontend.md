# Frontend Documentation

## Overview
The frontend is a Next.js application (using TypeScript) that provides a user interface for uploading documents and viewing extracted text.

## Tech Stack
- **Framework**: Next.js 14+ (App Router)
- **Styling**: Tailwind CSS
- **API Communication**: Fetch API (connecting to AWS API Gateway)
- **Testing**: Playwright

## Core Features
1. **File Upload**: Users can drag and drop or select files (PDF, DOCX, TXT, ZIP).
2. **Presigned URL Flow**: The app requests a presigned URL from the backend before uploading directly to S3.
3. **Status Polling**: Once an extraction is started, the app polls the status endpoint until completion.
4. **Results View**: Displays the extracted text or an error message.

## Components
- `FileUpload`: Handles file selection and S3 upload.
- `ExtractionStatus`: Shows the current state of processing.
- `ResultsDisplay`: Renders the extracted content.

## Testing
Playwright tests are located in `frontend/tests/`. Run them using:
```bash
npx playwright test
```
