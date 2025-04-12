# ImageScanningService

The service could be tested through the simple FE app deployed on S3 at 

http://jothi-image-scanner-fe-app.s3-website-us-east-1.amazonaws.com


The backend service is deployed through API Gateway with lambda integration as shown below. currently , it is all deployed on my personal AWS account.

  POST -> /scanrequest
  
  GET -> /scanrequest/{request_id}

  
![image](https://github.com/user-attachments/assets/4f2af534-78c4-4b36-af2a-fc4b4da7118d)


### Bootstrapping

If you would like to bootstrap this from a different AWS account , an IAM role should be setup for your github account to deploy the reosurces on your AWS account. Once that role is created, create a secret `ROLE_TO_ASSUME` in github with this newly created role and running the pipeline should create the necessary resources.