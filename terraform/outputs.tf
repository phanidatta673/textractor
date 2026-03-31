output "api_url" {
  value = aws_apigatewayv2_api.api.api_endpoint
}

output "s3_bucket_name" {
  value = aws_s3_bucket.uploads.id
}

output "frontend_url" {
  value = aws_s3_bucket_website_configuration.frontend.website_endpoint
}

output "frontend_bucket_name" {
  value = aws_s3_bucket.frontend.id
}
