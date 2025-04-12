# ImageScanningService

The service could be tested through the simple FE app deployed on S3 at 

http://jothi-image-scanner-fe-app.s3-website-us-east-1.amazonaws.com


The backend service is deployed through API Gateway with lambda integration as shown below. currently , it is all deployed on my personal AWS account.

  POST -> /scanrequest
  
  GET -> /scanrequest/{request_id}

- Overview
  - User makes an image upload request
    - It is validated for valid file types.
    - An image hash is calculated on the image content and is uploaded to S3. 
    - Creates a request id to track the scanning request and is stored in a request tracker dynamo table with the image hash and some metadata
  - Imagescanning service is invoked through a trigger from S3 upload
    - The file name of S3 is image hash followed by file extension.
    - The image hash is checked in the image details table if it has been processed already.
      - If it is processed, then it is skipped for Image scanning and the status is updated to be completed.
      - If its not, then an item is created in the image details table and then its scanned using AWS Rekognition service to detect the labels . It is updated to be completed.
    - The request ids matching the image hash which are in pending state are updated to be completed. Notice this could be turned in to seperate service but did not do it for simplicity



  
![image](https://github.com/user-attachments/assets/4f2af534-78c4-4b36-af2a-fc4b4da7118d)


### Bootstrapping

If you would like to bootstrap this from a different AWS account , an IAM role should be setup for your github account to deploy the reosurces on your AWS account. Once that role is created, create a secret `ROLE_TO_ASSUME` in github with this newly created role and running the pipeline should create the necessary resources.