# terraform/main.tf

terraform {
  backend "s3" {
    bucket = "jothi-terraform-state"
    key    = "image-scanning-service/terraform.tfstate"
    region = "us-east-1"
  }
}

resource "aws_s3_bucket" "jothi_test_bucket" {
  bucket = "jothi-image-test-bucket-2"

  tags = {
    Name        = "Terraform State Bucket"
    Environment = "dev"
  }
}