terraform {
  required_providers {
    github = {
      source  = "integrations/github"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.region
}

provider "github" {
  token = var.github_token
  owner = var.github_owner
}

# Variable for tokens (should be passed via terraform.tfvars or env vars)
variable "github_token" { type = string }
variable "github_owner" { type = string }
variable "github_repo"  { type = string }
variable "sprites_token" { type = string }
...
data "archive_file" "github_issue_handler" {
  type        = "zip"
  source_dir  = "../backend/lambdas/github-issue-handler"
  output_path = "github-issue-handler.zip"
  excludes    = ["node_modules", "package-lock.json", "index.ts"]
}

# GitHub Issue Handler Lambda
resource "aws_lambda_function" "github_issue_handler" {
  function_name    = "GitHubIssueHandler"
  role             = aws_iam_role.lambda_role.arn
  handler          = "index.handler"
  runtime          = "nodejs18.x"
  filename         = data.archive_file.github_issue_handler.output_path
  source_code_hash = data.archive_file.github_issue_handler.output_base64sha256

  environment {
    variables = {
      SPRITES_TOKEN = var.sprites_token
      GITHUB_TOKEN  = var.github_token
      REPO_URL      = "https://github.com/${var.github_owner}/${var.github_repo}.git"
    }
  }
}

# API Gateway Route for GitHub Webhook
resource "aws_apigatewayv2_integration" "github_issue_handler" {
  api_id           = aws_apigatewayv2_api.api.id
  integration_type = "AWS_PROXY"
  integration_uri  = aws_lambda_function.github_issue_handler.invoke_arn
}

resource "aws_apigatewayv2_route" "github_issue_handler" {
  api_id    = aws_apigatewayv2_api.api.id
  route_key = "POST /github-webhook"
  target    = "integrations/${aws_apigatewayv2_integration.github_issue_handler.id}"
}

resource "aws_lambda_permission" "api_gw_github_issue_handler" {
  statement_id  = "AllowExecutionFromAPIGateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.github_issue_handler.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.api.execution_arn}/*/*"
}

# GitHub Webhook
resource "aws_repository_webhook" "textractor" {
  repository = var.github_repo

  configuration {
    url          = "${aws_apigatewayv2_api.api.api_endpoint}/github-webhook"
    content_type = "json"
    insecure_ssl = false
  }

  active = true

  events = ["issues"]
}

# S3 Bucket for Uploads
resource "aws_s3_bucket" "uploads" {
  bucket_prefix = "text-extractor-uploads-"
  force_destroy = true
}

resource "aws_s3_bucket_lifecycle_configuration" "uploads_lifecycle" {
  bucket = aws_s3_bucket.uploads.id

  rule {
    id     = "delete-after-1-day"
    status = "Enabled"
    expiration {
      days = 1
    }
  }
}

resource "aws_s3_bucket_cors_configuration" "uploads_cors" {
  bucket = aws_s3_bucket.uploads.id

  cors_rule {
    allowed_headers = ["*"]
    allowed_methods = ["PUT", "POST", "GET"]
    allowed_origins = ["*"] # In production, restrict to your frontend domain
    max_age_seconds = 3000
  }
}

# DynamoDB Table for Status and Content
resource "aws_dynamodb_table" "extractions" {
  name         = "Extractions"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "fileId"

  attribute {
    name = "fileId"
    type = "S"
  }

  ttl {
    attribute_name = "ttl"
    enabled        = true
  }
}

# ECR Repository for Frontend/Backend Dockerization
resource "aws_ecr_repository" "app" {
  name                 = "textractor-app"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }
}

# IAM Role for Lambdas
resource "aws_iam_role" "lambda_role" {
  name = "text_extractor_lambda_role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "lambda.amazonaws.com"
      }
    }]
  })
}

resource "aws_iam_role_policy" "lambda_policy" {
  name = "text_extractor_lambda_policy"
  role = aws_iam_role.lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:ListBucket"
        ]
        Effect   = "Allow"
        Resource = [
          aws_s3_bucket.uploads.arn,
          "${aws_s3_bucket.uploads.arn}/*"
        ]
      },
      {
        Action = [
          "dynamodb:PutItem",
          "dynamodb:GetItem",
          "dynamodb:UpdateItem",
          "dynamodb:Query"
        ]
        Effect   = "Allow"
        Resource = aws_dynamodb_table.extractions.arn
      },
      {
        Action = "lambda:InvokeFunction"
        Effect = "Allow"
        Resource = aws_lambda_function.extraction_processor.arn
      },
      {
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Effect   = "Allow"
        Resource = "arn:aws:logs:*:*:*"
      }
    ]
  })
}

# Data sources for Lambda packaging
data "archive_file" "get_presigned_url" {
  type        = "zip"
  source_dir  = "../backend/lambdas/get-presigned-url"
  output_path = "get-presigned-url.zip"
  excludes    = ["node_modules", "package-lock.json", "index.ts"]
}

data "archive_file" "start_extraction" {
  type        = "zip"
  source_dir  = "../backend/lambdas/start-extraction"
  output_path = "start-extraction.zip"
  excludes    = ["node_modules", "package-lock.json", "index.ts"]
}

data "archive_file" "extraction_processor" {
  type        = "zip"
  source_dir  = "../backend/lambdas/extraction-processor"
  output_path = "extraction-processor.zip"
  excludes    = ["node_modules", "package-lock.json", "index.ts"]
}

data "archive_file" "get_status" {
  type        = "zip"
  source_dir  = "../backend/lambdas/get-status"
  output_path = "get-status.zip"
  excludes    = ["node_modules", "package-lock.json", "index.ts"]
}

# Lambdas
resource "aws_lambda_function" "get_presigned_url" {
  function_name    = "GetPresignedUrl"
  role             = aws_iam_role.lambda_role.arn
  handler          = "index.handler"
  runtime          = "nodejs18.x"
  filename         = data.archive_file.get_presigned_url.output_path
  source_code_hash = data.archive_file.get_presigned_url.output_base64sha256

  environment {
    variables = {
      BUCKET_NAME = aws_s3_bucket.uploads.id
    }
  }
}

resource "aws_lambda_function" "start_extraction" {
  function_name    = "StartExtraction"
  role             = aws_iam_role.lambda_role.arn
  handler          = "index.handler"
  runtime          = "nodejs18.x"
  filename         = data.archive_file.start_extraction.output_path
  source_code_hash = data.archive_file.start_extraction.output_base64sha256

  environment {
    variables = {
      TABLE_NAME       = aws_dynamodb_table.extractions.name
      PROCESSOR_LAMBDA = aws_lambda_function.extraction_processor.function_name
    }
  }
}

resource "aws_lambda_function" "extraction_processor" {
  function_name    = "ExtractionProcessor"
  role             = aws_iam_role.lambda_role.arn
  handler          = "index.handler"
  runtime          = "nodejs18.x"
  filename         = data.archive_file.extraction_processor.output_path
  source_code_hash = data.archive_file.extraction_processor.output_base64sha256
  timeout          = 60
  memory_size      = 256

  environment {
    variables = {
      TABLE_NAME = aws_dynamodb_table.extractions.name
    }
  }
}

resource "aws_lambda_function" "get_status" {
  function_name    = "GetStatus"
  role             = aws_iam_role.lambda_role.arn
  handler          = "index.handler"
  runtime          = "nodejs18.x"
  filename         = data.archive_file.get_status.output_path
  source_code_hash = data.archive_file.get_status.output_base64sha256

  environment {
    variables = {
      TABLE_NAME = aws_dynamodb_table.extractions.name
    }
  }
}

# API Gateway (HTTP API)
resource "aws_apigatewayv2_api" "api" {
  name          = "TextExtractorAPI"
  protocol_type = "HTTP"
  cors_configuration {
    allow_origins = ["*"]
    allow_methods = ["POST", "GET", "OPTIONS"]
    allow_headers = ["content-type"]
  }
}

resource "aws_apigatewayv2_stage" "default" {
  api_id      = aws_apigatewayv2_api.api.id
  name        = "$default"
  auto_deploy = true

  access_log_settings {
    destination_arn = aws_cloudwatch_log_group.api_gw.arn
    format          = "$context.identity.sourceIp - $context.identity.caller - $context.identity.user [$context.requestTime] \"$context.httpMethod $context.routeKey $context.protocol\" $context.status $context.responseLength $context.requestId"
  }
}

resource "aws_cloudwatch_log_group" "api_gw" {
  name              = "/aws/api_gw/${aws_apigatewayv2_api.api.name}"
  retention_in_days = 1
}

# Routes and Integrations
resource "aws_apigatewayv2_integration" "get_presigned_url" {
  api_id           = aws_apigatewayv2_api.api.id
  integration_type = "AWS_PROXY"
  integration_uri  = aws_lambda_function.get_presigned_url.invoke_arn
}

resource "aws_apigatewayv2_route" "get_presigned_url" {
  api_id    = aws_apigatewayv2_api.api.id
  route_key = "POST /presigned-url"
  target    = "integrations/${aws_apigatewayv2_integration.get_presigned_url.id}"
}

resource "aws_apigatewayv2_integration" "start_extraction" {
  api_id           = aws_apigatewayv2_api.api.id
  integration_type = "AWS_PROXY"
  integration_uri  = aws_lambda_function.start_extraction.invoke_arn
}

resource "aws_apigatewayv2_route" "start_extraction" {
  api_id    = aws_apigatewayv2_api.api.id
  route_key = "POST /start"
  target    = "integrations/${aws_apigatewayv2_integration.start_extraction.id}"
}

resource "aws_apigatewayv2_integration" "get_status" {
  api_id           = aws_apigatewayv2_api.api.id
  integration_type = "AWS_PROXY"
  integration_uri  = aws_lambda_function.get_status.invoke_arn
}

resource "aws_apigatewayv2_route" "get_status" {
  api_id    = aws_apigatewayv2_api.api.id
  route_key = "GET /status/{fileId}"
  target    = "integrations/${aws_apigatewayv2_integration.get_status.id}"
}

# Lambda Permissions for API Gateway
resource "aws_lambda_permission" "api_gw_get_presigned_url" {
  statement_id  = "AllowExecutionFromAPIGateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.get_presigned_url.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.api.execution_arn}/*/*"
}

resource "aws_lambda_permission" "api_gw_start_extraction" {
  statement_id  = "AllowExecutionFromAPIGateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.start_extraction.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.api.execution_arn}/*/*"
}

resource "aws_lambda_permission" "api_gw_get_status" {
  statement_id  = "AllowExecutionFromAPIGateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.get_status.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.api.execution_arn}/*/*"
}
