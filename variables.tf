variable "image_bucket_name" {
 type = string
 default = "jothi-image-test-bucket-2"
 description = "S3 storage bucket for Images"
}

variable "lambda_deployment_bucket_name" {
 type = string
 default = "jothi-lambda-deployments"
 description = "S3 storage bucket for lamnbda deployments"
}

variable "image_results_table" {
 type = string
 default = "IMAGE_RESULTS_TABLE"
 description = "Dynamo table containing information about images loaded"
}

variable "requests_tracker_table" {
 type = string
 default = "REQUESTS_TRACKER_TABLE"
 description = "User initiated requests table"
}
