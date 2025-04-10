import json
import hashlib
import base64
import os
import logging
import uuid
from datetime import datetime


import boto3
from botocore.exceptions import ClientError

logging.basicConfig()
logging.getLogger().setLevel(logging.INFO)

logger = logging.getLogger(__name__)

# Initialize DynamoDB client

request_tracker_table = os.environ['REQUEST_TRACKER_TABLE']
image_store = os.environ['IMAGE_STORAGE_BUCKET']    # S3 bucket name

s3 = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')

def lambda_handler(event: dict, context) -> dict:
    file_extensions = {
        "image/jpeg": "jpg",
        "image/png": "png"
            }
    try:
        logging.info(f"Received image upload request - {event}")
        # Extract file details from event

        body = json.loads(event.get('body', ''))
        file_data = body.get('file', None)
        file_type = body.get('fileType', None)
        request_label = body.get('label', 'cat')

        # Validate file type
        if file_type not in ['image/jpeg', 'image/png']:
            logging.error(f"{file_type} is not supported")
            return {
                'statusCode': 400,
                'headers': {
                    'Access-Control-Allow-Headers': 'Content-Type',
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Methods': 'OPTIONS,POST,GET'
                },
                'body': json.dumps('Invalid file type. Only JPEG and PNG are allowed.')
            }

        # calculate the SHA-256 of the image file to create a unique key
        # check if the hash exists in the dynamo table which means the same image has been uploaded and can give the results without 
        # calling the recognition service , hence saving cost

        image_content = base64.b64decode(file_data)

        image_hash = sha256_of_image(image_content)

        create_job_with_status(uuid.uuid4(),image_hash, 'pending', request_label)

        store_image_in_s3(s3_key=f"{image_hash}.{file_extensions[file_type]}")


        return {
                'statusCode': 200,
                'headers': {
                    'Access-Control-Allow-Headers': 'Content-Type',
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Methods': 'OPTIONS,POST,GET'
                },
                'body': json.dumps('Hang Tight. We will process your image as soon as we can.')
            }
    
    except Exception as e:
        logging.exception(f"Exception {e} during processing the event - {event}")
        return {
            'statusCode': 500,
                'headers': {
                    'Access-Control-Allow-Headers': 'Content-Type',
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Methods': 'OPTIONS,POST,GET'
                },
            'body': json.dumps(f'Error processing the Image: {str(e)}')
        }


def store_image_in_s3(s3_key: str, image_data: bytes, file_type: str) -> str:
    """Store the image in S3 and return the S3 key"""

    try:
        # Upload image to S3
        s3.put_object(
            Bucket=image_store,
            Key=s3_key,
            Body=image_data,
            ContentType=file_type  
        )
        return s3_key
    except ClientError as e:
        raise Exception(f"Error uploading to S3: {str(e)}")


def create_job_with_status(request_id: str, image_hash: str, status: str, request_label: str) -> str:
    """ Create a Job ID for the user request and tie with the Image hash"""
    try:
        item = {
                'request_id': request_id,
                'request_time': datetime.now().isoformat(),
                'request_status': status,
                'image_processing_status': 'pending',
                'image_hash': image_hash,
                'labels': request_label,
                'label_matched': False
            }
        logging.info(f"Creating Job with details - {item}")
        table = dynamodb.Table(request_tracker_table)
        table.put_item(
            Item=item
        )
    except ClientError as e:
        raise Exception(f"Error storing {item} in DynamoDB: {str(e)}")



def sha256_of_image(image_data: bytes) -> str:
    hasher = hashlib.sha256()
    hasher.update(image_data)
    return hasher.hexdigest()
