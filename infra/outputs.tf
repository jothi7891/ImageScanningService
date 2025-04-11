output "fe_deploy_bucket_name" {
  value = aws_s3_bucket.front_end_deploy_bucket.bucket
}

output "api_gateway_url" {
    value = aws_api_gateway_stage.prod_stage.invoke_url
}