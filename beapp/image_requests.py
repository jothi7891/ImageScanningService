
import json
import hashlib
import base64
import os
import sys
import logging
import uuid
from datetime import datetime

import boto3
from botocore.exceptions import ClientError
from pynamodb.exceptions import DoesNotExist

from models.request_tracker import RequestTracker

image_store = os.environ['IMAGE_STORAGE_BUCKET']  # S3 bucket name
s3 = boto3.client('s3')

#Remove all handlers associated with the root logger object.

for handler in logging.root.handlers[:]:
    logging.root.removeHandler(handler)

logger = logging.getLogger(__name__)

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s [%(threadName)-12.12s] [%(levelname)-5.5s]  %(message)s",
                    handlers=[
                        logging.StreamHandler(sys.stdout)
                    ])

def lambda_handler(event: dict, context)-> dict:
    logging.info(f"Received event - {event}")

    resource = event.get('resource')
    http_method = event.get('httpMethod')

    if resource == '/scanrequest' and http_method == 'POST':

        return scan_requests_post_method_handler(event, context)
    elif resource == '/scanrequest/{request_id}' and http_method == 'GET':
        return scan_requests_id_get_method_handler(event, context)

def scan_requests_post_method_handler(event: dict, context) -> dict:
    file_extensions = {
        "image/jpeg": "jpg",
        "image/png": "png"
            }
    try:
        logging.info(f"Received image upload request")
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
                'body': json.dumps(
                    {
                        'request_id': 'Invalid',
                        'message': f'Invalid file type. Only JPEG and PNG are allowed.',
                        'status': "Validation Failed"
                    })
                }

        # Calculate the SHA-256 of the image file to create a unique key
        # Check if the hash exists in the DynamoDB table which means the same image has been uploaded and can give the results without calling the recognition service, hence saving cost
        image_content = base64.b64decode(file_data)
        image_hash = sha256_of_image(image_content)
        
        # Create a job in the request tracker table with pending status
        request_id = create_job_with_status(str(uuid.uuid4()), image_hash, 'pending', request_label)

        # Store the image in S3
        store_image_in_s3(f"{image_hash}.{file_extensions[file_type]}", image_content, file_type)

        return {
                'statusCode': 200,
                'headers': {
                    'Access-Control-Allow-Headers': 'Content-Type',
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Methods': 'OPTIONS,POST,GET'
                },
                'body': json.dumps({
                    'request_id': request_id,
                    'message': f'We will process your image as soon as we can',
                    'status': 'Processing'
                }
                    )
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
            'body': json.dumps(
                {
                'request_id': 'Not created',
                'message': f'Error processing the Image: {str(e)}',
                'status': 'Failed'
                }
        )
        }


def scan_requests_id_get_method_handler(event: dict, context) -> dict:

    file_extensions = {
        "image/jpeg": "jpg",
        "image/png": "png"
            }


    try:
        logging.info(f"Received image status request - {event}")
        # Extract file details from event

        request_id = event.get('pathParameters', None).get('request_id')

        # valid if its a valid request id 
        try:
    
            request_details = RequestTracker.get(request_id)

            debug_data = None

            query_string = event.get('queryStringParameters', {})
            
            if query_string:

                debug_data = query_string.get('debugData', None)

            if debug_data:
                return {
                'statusCode': 200,
                'headers': {
                    'Access-Control-Allow-Headers': 'Content-Type',
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Methods': 'OPTIONS,POST,GET'
                },
                'body': json.dumps(request_details.to_power_user())
                }
            else:
                return {
                    'statusCode': 200,
                    'headers': {
                        'Access-Control-Allow-Headers': 'Content-Type',
                        'Access-Control-Allow-Origin': '*',
                        'Access-Control-Allow-Methods': 'OPTIONS,POST,GET'
                    },
                    'body': json.dumps(request_details.to_normal_user())
                }
        
        except DoesNotExist:

            logging.error(f"Request {request_id} does not exist")

            return {
                    'statusCode': 404,
                    'headers': {
                        'Access-Control-Allow-Headers': 'Content-Type',
                        'Access-Control-Allow-Origin': '*',
                        'Access-Control-Allow-Methods': 'OPTIONS,POST,GET'
                    },
                    'body': json.dumps({
                        'request_id': request_id,
                        'message': f"{request_id} is invalid. Please check and try and again later"
                        })
                }

        except Exception as e:
            logging.exception(f" Exception {e} during processing of the request {request_id}")
            raise e

    except Exception as e:
        logging.exception(f"Exception {e} during processing the event - {event}")
        return {
            'statusCode': 500,
                'headers': {
                    'Access-Control-Allow-Headers': 'Content-Type',
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Methods': 'OPTIONS,POST,GET'
                },
                    'body': json.dumps({
                        'request_id': request_id,
                        'message': f'Error processing the Image: {str(e)})'
                    })
        }


def store_image_in_s3(s3_key: str, image_data: bytes, file_type: str) -> str:
    """Store the image in S3 and return the S3 key"""
    try:
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
        item = RequestTracker(
            request_id=request_id,
            request_start_time=datetime.now().isoformat(),
            request_status=status,
            image_status='pending',
            image_hash=image_hash,
            labels=request_label,
            label_matched=False
        )
        logging.info(f"Creating Job with details - {item}")
        item.save()
        return item.request_id
    
    except ClientError as e:
        raise Exception(f"Error storing {item} in DynamoDB: {str(e)}")


def sha256_of_image(image_data: bytes) -> str:
    hasher = hashlib.sha256()
    hasher.update(image_data)
    return hasher.hexdigest()