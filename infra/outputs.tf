output "fe_deploy_bucket_name" {
  value = var.front_end_deploy_bucket_name
}

output "api_gateway_url" {
    value = aws_api_gateway_stage.prod_stage.invoke_url
}

output "website_endpoint" {
  value = aws_s3_bucket_website_configuration.front_end_deploy_bucket.website_endpoint
}