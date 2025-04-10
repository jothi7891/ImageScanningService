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

resource "aws_s3_bucket_versioning" "image_store_bucket" {
  bucket = aws_s3_bucket.image_store_bucket.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket" "lambda_deployment_bucket" {
  bucket = var.lambda_deployment_bucket_name

  tags = {
    Environment = "dev"
    Product = "image-scanner"
  }
}

resource "aws_s3_bucket_ownership_controls" "lambda_deployment_bucket" {
  bucket = aws_s3_bucket.lambda_deployment_bucket.id
  rule {
    object_ownership = "BucketOwnerPreferred"
  }
}

resource "aws_s3_bucket_acl" "lambda_deployment_bucket" {
  depends_on = [aws_s3_bucket_ownership_controls.lambda_deployment_bucket]
  bucket     = aws_s3_bucket.lambda_deployment_bucket.id
  acl        = "private"
}

resource "aws_s3_bucket_versioning" "lambda_deployment_bucket" {
  bucket = aws_s3_bucket.lambda_deployment_bucket.id
  versioning_configuration {
    status = "Enabled"
  }
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
  function_name = "image_uploader"
  s3_bucket     = aws_s3_bucket.lambda_deployment_bucket.id
  s3_key        = "image_upload.zip"
  runtime       = "python3.12"
  handler       = "image_upload.lambda_handler"
  role          = aws_iam_role.lambda_exec.arn
  s3_object_version = data.aws_s3_object.image_upload_zip.version_id

  environment {
    variables = {
      REQUEST_TRACKER_TABLE = var.requests_tracker_table
      IMAGE_STORAGE_BUCKET = var.image_bucket_name
    }
  }
}

data "aws_s3_object" "image_upload_zip" {
  bucket = var.image_bucket_name
  key    = var.image_uploader_s3_key
}

resource "aws_lambda_function" "image_scanner_handler" {
  function_name = "image_scanner"
  s3_bucket     = aws_s3_bucket.lambda_deployment_bucket.id
  s3_key        = "image_scanner.zip"
  runtime       = "python3.12"
  handler       = "image_scanner.lambda_handler"
  role          = aws_iam_role.lambda_exec.arn
  s3_object_version = data.aws_s3_object.image_scanner_zip.version_id

  environment {
    variables = {
      REQUEST_TRACKER_TABLE = var.requests_tracker_table
      IMAGE_STORAGE_BUCKET = var.image_bucket_name
      IMAGE_DETAIL_TABLE = var.image_results_table
    }
  }
}

data "aws_s3_object" "image_scanner_zip" {
  bucket = var.image_bucket_name
  key    = var.image_scanner_s3_key
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

resource "aws_api_gateway_stage" "prod_stage" {
  stage_name   = "prod"
  rest_api_id = aws_api_gateway_rest_api.image_scan_api.id
  deployment_id = aws_api_gateway_deployment.image_api_deployment.id
  
  access_log_settings {
    destination_arn = aws_cloudwatch_log_group.image_api.arn
    format          = "requestId: $context.requestId"
  }
}

resource "aws_api_gateway_method_settings" "prod_stage" {
  rest_api_id = aws_api_gateway_rest_api.image_scan_api.id
  stage_name  = aws_api_gateway_stage.prod_stage.stage_name
  method_path = "*/*"

  settings {
    metrics_enabled = true
    logging_level   = "INFO"
  }
}

resource "aws_cloudwatch_log_group" "image_api" {
  name              = "API-Gateway-Execution-Logs_${aws_api_gateway_rest_api.image_scan_api.id}"
  retention_in_days = 7
}

resource "aws_api_gateway_account" "api_global" {
  cloudwatch_role_arn = aws_iam_role.cloudwatch.arn
}

data "aws_iam_policy_document" "assume_role" {
  statement {
    effect = "Allow"

    principals {
      type        = "Service"
      identifiers = ["apigateway.amazonaws.com"]
    }

    actions = ["sts:AssumeRole"]
  }
}

resource "aws_iam_role" "cloudwatch" {
  name               = "api_gateway_cloudwatch_global"
  assume_role_policy = data.aws_iam_policy_document.assume_role.json
}

data "aws_iam_policy_document" "cloudwatch" {
  statement {
    effect = "Allow"

    actions = [
      "logs:CreateLogGroup",
      "logs:CreateLogStream",
      "logs:DescribeLogGroups",
      "logs:DescribeLogStreams",
      "logs:PutLogEvents",
      "logs:GetLogEvents",
      "logs:FilterLogEvents",
    ]

    resources = ["*"]
  }
}
resource "aws_iam_role_policy" "cloudwatch" {
  name   = "default"
  role   = aws_iam_role.cloudwatch.id
  policy = data.aws_iam_policy_document.cloudwatch.json
}