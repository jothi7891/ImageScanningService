import json
import logging
import os

import boto3
from botocore.exceptions import ClientError

# Initialize DynamoDB client

image_table = os.environ['IMAGE_DETAIL_TABLE']  # Table name from environment variable
job_table = os.environ['USER_REQUEST_TRACKER_TABLE']
bucket_name = os.environ['S3_BUCKET_NAME']    # S3 bucket name

rekognition = boto3.client('rekognition')
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('ScanResults')

def lambda_handler(event, context):
    bucket_name = event.get('bucketName')
    file_name = event.get('fileName')
    # Process the dynamoDB stream and get the S3 URL and image

    try:
        for record in event['Records']:
            logging.info(f"Received Image Record - {record}")

            if record['eventName'] == 'INSERT':
                image_file = record['dynamodb']['NewImage']['image_file']
    except Exception as e:
        logging.exception(f"Error in processing the - {record}")

    # Call Rekognition to analyze the image
    try:

        # Store scan results in DynamoDB
        result = json.dumps(response)
        table.put_item(
            Item={
                'imageId': file_name,
                'scanResult': result
            }
        )

        return {
            'statusCode': 200,
            'body': json.dumps('Image scanning complete and results stored.')
        }

    except ClientError as e:
        return {
            'statusCode': 500,
            'body': json.dumps(f'Error processing the image: {str(e)}')
        }


def image_labels_from_s3file(bucket_name, file_name):
    try:
        response = rekognition.detect_labels(
            Image={
                'S3Object': {
                    'Bucket': bucket_name,
                    'Name': file_name
                }
            }
        )

        logging.info(f"AWS Image recognigition service response for {file_name} - {response}")

        return response["Labels"]

    except Exception as e:
        logging.exception(f"Error in processing the image - {file_name}")
        return []

def store_image_metadata(image_hash: str, s3_key: str, file_type: str):
    """Store metadata in DynamoDB"""
    try:
        table = dynamodb.Table(image_table)
        item={
                'image_hash': image_hash,
                'status': 'initial',
                'metadata': {
                    's3_key': s3_key,
                    'file_type': file_type,
                    'image_upload_time': datetime.now().isoformat()
                }
        }

        logging.info(f"Creating a new image with reference - {item}")

        table.put_item(
            Item=item
        )

    except ClientError as e:
        raise Exception(f"Error storing {item} in DynamoDB: {str(e)}")

def update_jobs_with_status(job_id: str, image_hash: str, status: bool) -> str:
    """ Create a Job ID for the user request and tie with the Image hash"""
    try:
        item = {
                'job_id': job_id,
                'is_completed': status,
                'image_hash': image_hash
            }
        logging.info(f"Creating Job with details - {item}")
        table = dynamodb.Table(job_table)
        table.put_item(
            Item=item
        )
    except ClientError as e:
        raise Exception(f"Error storing {item} in DynamoDB: {str(e)}")
    
if __name__ == '__main__':
    labels = image_labels_from_s3file('jothi-test-image-scanner', 'leopard-kruger-rh-786x500.jpg')