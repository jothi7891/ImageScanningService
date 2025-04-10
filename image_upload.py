import json
import hashlib
import base64
import os
import logging

import boto3
from botocore.exceptions import ClientError


# Initialize DynamoDB client
dynamodb = boto3.resource('dynamodb')
table_name = os.environ['IMAGE_DETAIL_TABLE']  # Table name from environment variable
table = dynamodb.Table(table_name)
s3 = boto3.client('s3')


def lambda_handler(event: dict, context) -> dict:

    try:
        logging.info(f"Received image upload request - {event}")
        body = json.loads(event['body'])
        # Extract file details from event
        file_data = body.get('file', None)
        file_type = event.get('fileType', None)
        
        # Validate file type
        if file_type not in ['image/jpeg', 'image/png']:
            logging.error(f"{file_type} is not supported")
            return {
                'statusCode': 400,
                'body': json.dumps('Invalid file type. Only JPEG and PNG are allowed.')
            }

        # calculate the SHA-256 of the image file to create a unique key
        # check if the hash exists in the dynamo table which means the same image has been uploaded and can give the results without 
        # calling the recognition service , hence saving cost

        image_content = base64.b64decode(file_data)

        image_hash = sha256_of_image(image_content)

        response = check_and_write_item(image_hash=image_hash, image_content=image_content)

        return response
    
    except Exception as e:
        logging.exception(f"Exception {e} during processing the event - {event}")
        return {
            'statusCode': 500,
            'body': json.dumps(f'Error processing the file: {str(e)}')
        }


def check_and_write_item(image_hash: str, file_type: str, image_content: bytes) -> dict:
    try:
        # Check if the item with the image_sha already exists
        response = table.get_item(
            Key={'image_hash': image_hash}
        )
        
        # If the item exists, return a positive response and skip further processing
        if 'Item' in response:
            return {
                'statusCode': 200,
                'body': json.dumps({'message': 'Item already exists', 'item': response['Item']})
            }
        
        s3.upload_bytes(bucket_name=os.getenv('IMAGE_STORE_BUCKET'))

        item = {'image_hash': image_hash, 'status': 'initial', 'debug_data': '', '_version': os.getenv('IMAGE_RESULTS_TABLE_SCHEMA_VERSION', 1)}

        # If the item does not exist, write it to DynamoDB
        table.put_item(
            Item=item)
        
        return {
            'statusCode': 201,
            'body': json.dumps({'message': 'Item inserted successfully', 'image_sha': image_hash})
        }
    
    except ClientError as e:
        return {
            'statusCode': 500,
            'body': json.dumps({'error': f"Error interacting with DynamoDB: {str(e)}"})
        }

    
def sha256_of_image(image_data: bytes) -> str:
    hasher = hashlib.sha256()
    hasher.update(image_data)
    return hasher.hexdigest()
