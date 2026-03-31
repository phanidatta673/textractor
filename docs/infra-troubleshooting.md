# Infrastructure Troubleshooting & Fixes

This document outlines the challenges encountered during the deployment and testing of the Text Extractor infrastructure and the solutions implemented to resolve them.

## 1. Resource Drift (Manual Deletion vs. Terraform)
**Issue:** Resources were manually deleted in the AWS Console, but the Terraform state file (if it had existed) or the cloud environment still contained some persistent resources (like IAM Roles). Re-running `terraform apply` would have failed due to "Resource already exists" errors.

**Fix:** 
- Used `terraform import` to bring existing resources (specifically the `text_extractor_lambda_role`) back under Terraform management.
- Performed a `terraform refresh` to synchronize the state with the actual (mostly empty) environment.

## 2. GitHub Token Permissions
**Issue:** The provided GitHub Personal Access Token (PAT) did not have the `admin:repo_hook` scope. This prevented Terraform from creating the `github_repository_webhook` resource, which is required for automated issue handling.

**Fix:** 
- The webhook resource was temporarily bypassed to allow the core infrastructure (Lambda, S3, DynamoDB) to deploy. 
- *Recommendation:* Ensure the PAT has `repo`, `workflow`, and `admin:repo_hook` scopes for full automation.

## 3. Lambda Runtime: ImportModuleError (lxml/etree)
**Issue:** When building the `extraction-processor` Lambda on macOS, `pip install` downloaded macOS-compatible binaries for the `lxml` library. When uploaded to AWS Lambda (which runs Linux), the function failed with `Unable to import module 'index': cannot import name 'etree' from 'lxml'`.

**Fix:** 
- Modified `backend/build.sh` to use the `--platform manylinux2014_x86_64` and `--only-binary=:all:` flags during `pip install`. 
- This forces the download of the correct Linux-compatible wheel files even when running on macOS, ensuring the Lambda has the correct binary dependencies.

## 4. Extraction Stuck in PENDING
**Issue:** During initial testing, the status would remain `PENDING` indefinitely. This was a direct result of the `ImportModuleError` mentioned above; the Lambda was failing to initialize, so it never updated the status to `PROCESSING` or `COMPLETED`.

**Fix:** 
- Resolved by the dependency fix in Item 3. Verified by checking CloudWatch Logs for the `ExtractionProcessor` log group.

## 5. Multi-Format Support
**Issue:** Ensuring that `pypdf`, `python-docx`, and `zipfile` all worked correctly within the 250MB Lambda unzipped limit.

**Fix:** 
- Used a targeted `build.sh` script to only package necessary dependencies.
- Verified support for `.pdf`, `.docx`, `.txt`, and nested `.zip` files using a custom multi-format test suite (`tests/backend/test_multi_format_infra.py`).
