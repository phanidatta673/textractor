# Technical Flow Documentation

## End-to-End Extraction Flow

1. **Upload Initiation**
   - Frontend calls `POST /presigned-url` with filename and content type.
   - `GetPresignedUrl` Lambda generates a UUID `fileId`, creates a key `uploads/{fileId}.ext`, and returns a presigned URL.

2. **File Upload**
   - Frontend performs a `PUT` request directly to the S3 bucket using the presigned URL.

3. **Extraction Start**
   - Frontend calls `POST /start` with `fileId`, `key`, and `bucket`.
   - `StartExtraction` Lambda creates a record in DynamoDB with `status: PENDING`.
   - `StartExtraction` asynchronously invokes `ExtractionProcessor` with the file details.

4. **Processing**
   - `ExtractionProcessor` updates DynamoDB to `status: PROCESSING`.
   - It downloads the file from S3 into memory.
   - Based on the extension, it uses `pypdf`, `python-docx`, or standard `zipfile` to extract text.
   - Upon success, it updates DynamoDB with `status: COMPLETED` and the extracted `content`.
   - Upon failure, it updates DynamoDB with `status: FAILED` and an `error` message.

5. **Result Retrieval**
   - Frontend polls `GET /status/{fileId}` every few seconds.
   - `GetStatus` Lambda returns the full DynamoDB record.
   - Frontend stops polling once the status is `COMPLETED` or `FAILED`.

## Sequence Diagram (Simplified)
```text
Frontend -> API GW (GetPresignedUrl) -> S3 (URL)
Frontend -> S3 (Upload)
Frontend -> API GW (StartExtraction) -> DynamoDB (PENDING)
StartExtraction -> ExtractionProcessor (Invoke Async)
ExtractionProcessor -> S3 (Download)
ExtractionProcessor -> ExtractionProcessor (Extract Text)
ExtractionProcessor -> DynamoDB (COMPLETED)
Frontend -> API GW (GetStatus) -> DynamoDB (Read)
```

## Error Handling
- Invalid file types are rejected by the processor.
- S3 upload failures are handled by the frontend.
- Lambda timeouts are configured to 60 seconds for the processor.
- DynamoDB TTL ensures that extraction records are cleaned up after 10 minutes.
