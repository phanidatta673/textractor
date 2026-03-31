#!/bin/bash
set -e

# Manual cleanup script using AWS CLI
# This script will attempt to find and delete resources created by the textractor project

# 1. Lambdas
LAMBDAS=("GetPresignedUrl" "StartExtraction" "ExtractionProcessor" "GetStatus" "GitHubIssueHandler")
for LAMBDA in "${LAMBDAS[@]}"
do
    echo "Deleting Lambda: $LAMBDA..."
    aws lambda delete-function --function-name "$LAMBDA" 2>/dev/null || echo "Lambda $LAMBDA already deleted."
done

# 2. DynamoDB
echo "Deleting DynamoDB table: Extractions..."
aws dynamodb delete-table --table-name "Extractions" 2>/dev/null || echo "DynamoDB table already deleted."

# 3. S3 Buckets
# We need to find the buckets as they have prefixes
BUCKETS=$(aws s3 ls | grep "text-extractor-uploads-\|textractor-frontend-" | awk '{print $3}')
for BUCKET in $BUCKETS
do
    echo "Emptying and deleting S3 bucket: $BUCKET..."
    aws s3 rb "s3://$BUCKET" --force 2>/dev/null || echo "S3 bucket $BUCKET already deleted."
done

# 4. API Gateway
API_ID=$(aws apigatewayv2 get-apis --query "Items[?Name=='TextExtractorAPI'].ApiId" --output text)
if [ -n "$API_ID" ] && [ "$API_ID" != "None" ]; then
    echo "Deleting API Gateway: $API_ID..."
    aws apigatewayv2 delete-api --api-id "$API_ID"
else
    echo "API Gateway already deleted."
fi

# 5. IAM Role and Policy
ROLE_NAME="text_extractor_lambda_role"
POLICY_NAME="text_extractor_lambda_policy"
echo "Deleting IAM Role and Policy..."
aws iam delete-role-policy --role-name "$ROLE_NAME" --policy-name "$POLICY_NAME" 2>/dev/null || true
aws iam delete-role --role-name "$ROLE_NAME" 2>/dev/null || echo "IAM Role already deleted."

# 6. ECR Repository
echo "Deleting ECR Repository: textractor-app..."
aws ecr delete-repository --repository-name "textractor-app" --force 2>/dev/null || echo "ECR Repository already deleted."

# 7. CloudWatch Logs
echo "Deleting CloudWatch Log Groups..."
aws logs delete-log-group --log-group-name "/aws/api_gw/TextExtractorAPI" 2>/dev/null || true

echo "Manual decommissioning complete."
