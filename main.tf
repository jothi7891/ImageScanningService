# terraform/main.tf

terraform {
  backend "s3" {
    bucket = "jothi-terraform-state"
    key    = "image-scanning-service/terraform.tfstate"
    region = "us-east-1"
  }
}

resource "aws_s3_bucket" "jothi_test_bucket" {
  bucket = var.image_bucket_name

  tags = {
    Environment = "dev"
    Product = "image-scanner"
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

resource "aws_dynamodb_table" "job_results" {
  name           = var.job_table
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


resource "aws_api_gateway_rest_api" "api" {
  name        = "ImageScan"
  description = "API for image scanning"
  tags = {
    Environment = "dev"
    Product = "image-scanner"
  }
}

resource "aws_api_gateway_resource" "upload" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  parent_id   = aws_api_gateway_rest_api.api.root_resource_id
  path_part   = "images"
}
