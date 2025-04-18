# terraform/main.tf

#provider 
terraform {
  backend "s3" {
    bucket = "jothi-terraform-state"
    key    = "image-scanning-service/terraform.tfstate"
    region = "us-east-1"
  }
}

# s3 buckets
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

resource "aws_s3_bucket" "front_end_deploy_bucket" {
  bucket = var.front_end_deploy_bucket_name

  tags = {
    Environment = "dev"
    Product = "image-scanner"
  }
}

resource "aws_s3_bucket_public_access_block" "public_access" {
  bucket = aws_s3_bucket.front_end_deploy_bucket.id

  block_public_acls       = false
  ignore_public_acls      = false
  block_public_policy     = false
  restrict_public_buckets = false
}

resource "aws_s3_bucket_ownership_controls" "front_end_deploy_bucket" {
  bucket = aws_s3_bucket.front_end_deploy_bucket.id
  rule {
    object_ownership = "BucketOwnerPreferred"
  }
}

resource "aws_s3_bucket_website_configuration" "front_end_deploy_bucket" {
  depends_on = [aws_s3_bucket_public_access_block.public_access]
  bucket = aws_s3_bucket.front_end_deploy_bucket.id

  index_document {
    suffix = "index.html"
  }

  error_document {
    key = "error.html"
  }
}

resource "aws_s3_bucket_policy" "allow_public_read" {
  depends_on = [
    aws_s3_bucket_public_access_block.public_access,
    aws_s3_bucket_ownership_controls.front_end_deploy_bucket
  ]
  
  bucket = aws_s3_bucket.front_end_deploy_bucket.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "PublicReadGetObject"
        Effect    = "Allow"
        Principal = "*"
        Action    = "s3:GetObject"
        Resource  = "${aws_s3_bucket.front_end_deploy_bucket.arn}/*"
      }
    ]
  })
}

resource "aws_s3_bucket_versioning" "front_end_deploy_bucket" {
  bucket = aws_s3_bucket.front_end_deploy_bucket.id
  versioning_configuration {
    status = "Enabled"
  }
}

# dyanmo tables
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
  hash_key       = "request_id"
  read_capacity  = 5
  write_capacity = 5
  billing_mode   = "PROVISIONED"

  attribute {
    name = "request_id"
    type = "S"
  }

  attribute {
    name = "image_hash"
    type = "S"
  }


  global_secondary_index {
    name               = var.requests_tracker_index
    hash_key           = "image_hash"
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
    Statement = [
      {
      Action = "sts:AssumeRole",
      Effect = "Allow",
      Principal = {
        Service = "lambda.amazonaws.com"
      }
    }
    ]
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

resource "aws_iam_role_policy_attachment" "lambda_rekognition" {
  role       = aws_iam_role.lambda_exec.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonRekognitionReadOnlyAccess"
}

resource "aws_iam_role_policy_attachment" "lambda_logs" {
  role       = aws_iam_role.lambda_exec.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

#Lambda for handling 
resource "aws_lambda_function" "image_requests" {
  function_name = "image_requests"
  s3_bucket     = aws_s3_bucket.lambda_deployment_bucket.id
  s3_key        = "image_requests.zip"
  runtime       = "python3.12"
  handler       = "image_requests.lambda_handler"
  role          = aws_iam_role.lambda_exec.arn
  s3_object_version = data.aws_s3_object.image_requests_zip.version_id
  timeout = 30

  environment {
    variables = {
      REQUEST_TRACKER_TABLE = var.requests_tracker_table
      IMAGE_STORAGE_BUCKET = var.image_bucket_name
      IMAGE_DETAIL_TABLE = var.image_results_table
      REQUEST_TRACKER_IMAGE_INDEX = var.requests_tracker_index
    }
  }
}

data "aws_s3_object" "image_requests_zip" {
  bucket = var.lambda_deployment_bucket_name
  key    = var.image_requests_s3_key
}

resource "aws_lambda_function" "image_scanner_handler" {
  function_name = "image_scanner"
  s3_bucket     = aws_s3_bucket.lambda_deployment_bucket.id
  s3_key        = "image_scanner.zip"
  runtime       = "python3.12"
  handler       = "image_scanner.lambda_handler"
  role          = aws_iam_role.lambda_exec.arn
  s3_object_version = data.aws_s3_object.image_scanner_zip.version_id
  timeout = 30

  environment {
    variables = {
      REQUEST_TRACKER_TABLE = var.requests_tracker_table
      IMAGE_STORAGE_BUCKET = var.image_bucket_name
      IMAGE_DETAIL_TABLE = var.image_results_table
      REQUEST_TRACKER_IMAGE_INDEX = var.requests_tracker_index
    }
  }
}

data "aws_s3_object" "image_scanner_zip" {
  bucket = var.lambda_deployment_bucket_name
  key    = var.image_scanner_s3_key
}


# api gateeway
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
  path_part   = "scanrequest"
}

resource "aws_api_gateway_resource" "images_idpath" {
  rest_api_id = aws_api_gateway_rest_api.image_scan_api.id
  parent_id   = aws_api_gateway_resource.images.id
  path_part   = "{request_id}"
}

# Create an OPTIONS method for CORS preflight
resource "aws_api_gateway_method" "images_options" {
  rest_api_id   = aws_api_gateway_rest_api.image_scan_api.id
  resource_id   = aws_api_gateway_resource.images.id
  http_method   = "OPTIONS"
  authorization = "NONE"
}

# Setup OPTIONS method response to allow CORS headers
resource "aws_api_gateway_method_response" "options_method_response" {
  rest_api_id = aws_api_gateway_rest_api.image_scan_api.id
  resource_id = aws_api_gateway_resource.images.id
  http_method = aws_api_gateway_method.images_options.http_method
  status_code = 200

  response_parameters = {
    "method.response.header.Access-Control-Allow-Origin"      = true
    "method.response.header.Access-Control-Allow-Headers"     = true
    "method.response.header.Access-Control-Allow-Methods"     = true
  }
}


# Setup the OPTIONS method integration (Mock Integration for CORS)
resource "aws_api_gateway_integration" "images_options_integration" {
  rest_api_id = aws_api_gateway_rest_api.image_scan_api.id
  resource_id = aws_api_gateway_resource.images.id
  http_method = aws_api_gateway_method.images_options.http_method
  type                    = "MOCK"
  depends_on = [ aws_api_gateway_method_response.options_method_response ]
  request_templates = {
    "application/json" = <<-EOF
      {
        "statusCode": 200
      }
    EOF
  }

}

# OPTIONS Integration Response
resource "aws_api_gateway_integration_response" "images_options_integration_response" {
  rest_api_id = aws_api_gateway_rest_api.image_scan_api.id
  resource_id = aws_api_gateway_resource.images.id
  http_method = aws_api_gateway_method.images_options.http_method
  status_code = aws_api_gateway_method_response.options_method_response.status_code
  depends_on = [aws_api_gateway_integration.images_options_integration]

  response_parameters = {
    "method.response.header.Access-Control-Allow-Origin"  = "'*'",
    "method.response.header.Access-Control-Allow-Methods" = "'OPTIONS'",
    "method.response.header.Access-Control-Allow-Headers" = "'Content-Type,X-Amz-Date,Authorization,X-Api-Key'"
  }
}

# POST method
resource "aws_api_gateway_method" "images_post" {
  rest_api_id   = aws_api_gateway_rest_api.image_scan_api.id
  resource_id   = aws_api_gateway_resource.images.id
  http_method   = "POST"
  authorization = "NONE"

}

# GET method
resource "aws_api_gateway_method" "images_idpath_get" {
  rest_api_id   = aws_api_gateway_rest_api.image_scan_api.id
  resource_id   = aws_api_gateway_resource.images_idpath.id
  http_method   = "GET"
  authorization = "NONE"

  # Declare the path parameter as required
  request_parameters = {
    "method.request.path.request_id" = true
  }

}

# POST method lambda integration
resource "aws_api_gateway_integration" "image_upload_lambda_integration" {
  rest_api_id             = aws_api_gateway_rest_api.image_scan_api.id
  resource_id             = aws_api_gateway_resource.images.id
  http_method             = aws_api_gateway_method.images_post.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.image_requests.invoke_arn

}

# GET method lambda integration
resource "aws_api_gateway_integration" "image_status_lambda_integration" {
  rest_api_id             = aws_api_gateway_rest_api.image_scan_api.id
  resource_id             = aws_api_gateway_resource.images_idpath.id
  http_method             = aws_api_gateway_method.images_idpath_get.http_method
  type                    = "AWS_PROXY"
  integration_http_method = "POST"
  uri                     = aws_lambda_function.image_requests.invoke_arn

  request_parameters = {
    "integration.request.path.request_id" = "method.request.path.request_id"
  }

}

# resource "aws_api_gateway_gateway_response" "images_cors_4xx" {
#   rest_api_id   = aws_api_gateway_rest_api.image_scan_api.id
#   response_type = "DEFAULT_4XX"
  
#   response_parameters = {
#     "gatewayresponse.header.Access-Control-Allow-Origin"  = "'*'",
#     "gatewayresponse.header.Access-Control-Allow-Headers" = "'Content-Type,X-Amz-Date,Authorization'"
#   }
# }

# resource "aws_api_gateway_gateway_response" "images_cors_5xx" {
#   rest_api_id   = aws_api_gateway_rest_api.image_scan_api.id
#   response_type = "DEFAULT_5XX"
  
#   response_parameters = {
#     "gatewayresponse.header.Access-Control-Allow-Origin"  = "'*'",
#     "gatewayresponse.header.Access-Control-Allow-Headers" = "'Content-Type,X-Amz-Date,Authorization'"
#   }
# }


resource "aws_api_gateway_deployment" "image_api_deployment" {
  depends_on = [
    aws_api_gateway_method.images_post
    ]

  triggers = {
    redeployment = sha1(jsonencode([
      aws_api_gateway_resource.images.id,
      aws_api_gateway_method.images_post.id,
      aws_api_gateway_method.images_idpath_get.id,
      aws_api_gateway_method.images_options.id,
      aws_api_gateway_integration.images_options_integration.id,
      aws_api_gateway_integration_response.images_options_integration_response.id,
      aws_api_gateway_integration.image_upload_lambda_integration.id,
      aws_api_gateway_integration.image_status_lambda_integration.id
    ]))
  }

  lifecycle {
    create_before_destroy = true  # Avoid downtime
  }

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

resource "aws_lambda_permission" "apigw" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.image_requests.function_name

  principal     = "apigateway.amazonaws.com"

  # Grant access to all methods/resources in the API
  source_arn = "${aws_api_gateway_rest_api.image_scan_api.execution_arn}/*/*/*"
}
