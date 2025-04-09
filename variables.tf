variable "image_bucket_name" {
 type = string
 default = "jothi-image-test-bucket-2"
 description = "S3 storage bucket for Images"
}

variable "image_results_table" {
 type = string
 default = "IMAGE_RESULTS_TABLE"
 description = "Dynamo table containing information about images loaded"
}

variable "job_table" {
 type = string
 default = "JOB_RESULTS_TABLE"
 description = "User initiated job table"
}
