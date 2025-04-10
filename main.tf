# terraform/main.tf

terraform {
  backend "s3" {
    bucket = "jothi-terraform-state"
    key    = "image-scanning-service/terraform.tfstate"
    region = "us-east-1"
  }
}

resource "aws_s3_bucket" "image_store_bucket" {
  bucket = var.image_bucket_name

  tags = {
    Environment = "dev"
    Product = "image-scanner"
  }
}

resource "aws_s3_bucket_ownership_controls" "image_store_bucket" {
  bucket = aws_s3_bucket.image_store_bucket.id
  rule {
    object_ownership = "BucketOwnerPreferred"
  }
}

resource "aws_s3_bucket_acl" "image_store_bucket" {
  depends_on = [aws_s3_bucket_ownership_controls.image_store_bucket]
  bucket     = aws_s3_bucket.image_store_bucket.id
  acl        = "private"
}

resource "aws_s3_bucket" "lambda_deployment_bucket" {
  bucket = var.lambda_deployment_bucket_name

  tags = {
    Environment = "dev"
    Product = "image-scanner"
  }
}

resource "aws_s3_bucket_ownership_controls" "image_store_bucket" {
  bucket = aws_s3_bucket.image_store_bucket.id
  rule {
    object_ownership = "BucketOwnerPreferred"
  }
}

resource "aws_s3_bucket_acl" "jothi_test_bucket" {
  depends_on = [aws_s3_bucket_ownership_controls.image_store_bucket]
  bucket     = aws_s3_bucket.image_store_bucket.id
  acl        = "private"
}

resource "aws_s3_bucket" "jothi_test_bucket" {
  bucket = var.image_bucket_name

  tags = {
    Environment = "dev"
    Product = "image-scanner"
  }
}

resource "aws_s3_bucket_ownership_controls" "jothi_test_bucket" {
  bucket = aws_s3_bucket.jothi_test_bucket.id
  rule {
    object_ownership = "BucketOwnerPreferred"
  }
}

resource "aws_s3_bucket_acl" "jothi_test_bucket" {
  depends_on = [aws_s3_bucket_ownership_controls.jothi_test_bucket]
  bucket     = aws_s3_bucket.jothi_test_bucket.id
  acl        = "private"
}

resource "aws_dynamodb_table" "image_results" {
  name         = var.image_results_table
  hash_key     = "image_hash"
  read_capacity  = 5
  write_capacity = 5

  attribute {
    name = "image_hash"
    type = "S"
  }

  billing_mode = "PROVISIONED"

  tags = {
    Environment = "dev"
    Product = "image-scanner"
  }

}

resource "aws_dynamodb_table" "requests_tracker_table" {
  name           = var.requests_tracker_table
  hash_key       = "job_id"
  read_capacity  = 5
  write_capacity = 5
  billing_mode   = "PROVISIONED"

  attribute {
    name = "job_id"
    type = "S"
  }

  attribute {
    name = "image_hash"
    type = "S"
  }

  attribute {
    name = "is_complete"
    type = "S"
  }

  global_secondary_index {
    name               = "image_hash-index"
    hash_key           = "image_hash"
    range_key          = "is_complete"
    projection_type    = "ALL" 
    read_capacity  = 5
    write_capacity = 5
  }

  tags = {
    Environment = "dev"
    Product     = "image-scanner"
  }
}

#IAM role for lambda

resource "aws_iam_role" "lambda_exec" {
  name = "lambda-exec-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [{
      Action = "sts:AssumeRole",
      Effect = "Allow",
      Principal = {
        Service = "lambda.amazonaws.com"
      }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_s3" {
  role       = aws_iam_role.lambda_exec.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonS3FullAccess"
}

resource "aws_iam_role_policy_attachment" "lambda_dynamo" {
  role       = aws_iam_role.lambda_exec.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonDynamoDBFullAccess"
}

resource "aws_iam_role_policy_attachment" "lambda_logs" {
  role       = aws_iam_role.lambda_exec.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

#Lambda for handling 
resource "aws_lambda_function" "image_upload" {
  function_name = "my-function"
  s3_bucket     = aws_s3_bucket.lambda_deployment_bucket.id
  s3_key        = "lambda_deployments/image_upload.zip"
  runtime       = "python3.12"
  handler       = "image_upload.lambda_handler"
  role          = aws_iam_role.lambda_exec.arn
}

resource "aws_lambda_function" "image_scanner_handler" {
  function_name = "my-function"
  s3_bucket     = aws_s3_bucket.lambda_deployment_bucket.id
  s3_key        = "lambda_deployments/image_scanner.zip"
  runtime       = "python3.12"
  handler       = "image_scanner.lambda_handler"
  role          = aws_iam_role.lambda_exec.arn
}

resource "aws_api_gateway_rest_api" "image_scan_api" {
  name        = "ImageScan"
  description = "API for image scanning"
  binary_media_types = ["image/jpeg", "image/png", "multipart/form-data"]
  tags = {
    Environment = "dev"
    Product = "image-scanner"
  }
}

resource "aws_api_gateway_resource" "images" {
  rest_api_id = aws_api_gateway_rest_api.image_scan_api.id
  parent_id   = aws_api_gateway_rest_api.image_scan_api.root_resource_id
  path_part   = "images"
}

resource "aws_api_gateway_method" "images_post" {
  rest_api_id   = aws_api_gateway_rest_api.image_scan_api.id
  resource_id   = aws_api_gateway_resource.images.id
  http_method   = "POST"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "image_upload_lambda_integration" {
  rest_api_id             = aws_api_gateway_rest_api.image_scan_api.id
  resource_id             = aws_api_gateway_resource.images.id
  http_method             = aws_api_gateway_method.images_post.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.image_upload.invoke_arn
}

resource "aws_api_gateway_deployment" "image_api_deployment" {
  depends_on = [aws_api_gateway_integration.image_upload_lambda_integration]
  rest_api_id = aws_api_gateway_rest_api.image_scan_api.id
  stage_name  = "prod"
}