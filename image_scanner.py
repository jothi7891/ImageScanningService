import json
import logging
import os
import sys
from datetime import datetime

import boto3
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Attr

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s [%(threadName)-12.12s] [%(levelname)-5.5s]  %(message)s",
                    handlers=[
                        logging.StreamHandler(sys.stdout)
                    ])

logger = logging.getLogger(__name__)

# Initialize DynamoDB client

image_table = os.environ['IMAGE_DETAIL_TABLE']  # Table name from environment variable
request_tracker_table = os.environ['REQUEST_TRACKER_TABLE']
image_hash_index = os.environ['REQUEST_TRACKER_IMAGE_INDEX']
bucket_name = os.environ['IMAGE_STORAGE_BUCKET']    # S3 bucket name

rekognition = boto3.client('rekognition')
dynamodb = boto3.resource('dynamodb')

def lambda_handler(event, context):
    # Process the dynamoDB stream and get the S3 URL and image

    try:
        for record in event['Records']:
            logging.info(f"Received New Image Upload Event - {record}")

            bucket_name = record['s3']['bucket']['name']
            file_key = record['s3']['object']['key']
            image_hash = file_key.split('.')[0]
            file_type = file_key.split('.')[1]
            image_size = record['s3']['object']['size']
            
            
            existing_item = get_item_from_dynamo(dynamodb.Table(image_table), {'image_hash': image_hash})

            if existing_item:
                logging.info(f"Image with hash {image_hash} already exists in DynamoDB. Skipping processing.")
                status = 'completed'
                image_labels = json.loads(existing_item['labels'])
            else:
                image_item = create_image_metadata(image_hash, file_type, image_size)
                logging.info(f"Image metadata - {image_item} created for {file_key}")
                logging.info(f"Extracting labels from image {file_key}")
                image_labels = image_labels_from_s3file(bucket_name, file_key)
                logging.info(f"Image labels - {image_labels}")
                status = 'completed'

                update_image_metadata_with_labels(image_hash, image_labels, status)

            update_request_table_based_on_image_hash(image_hash, status, image_labels)

            # Update the request tracker table based on the image hash
            
    except Exception as e:
        logging.exception(f"Error in processing the - {record}")
        
def update_image_metadata_with_labels(image_hash: str, labels: dict, status: str):
    """
        Update the status of image hash in image table
    """
    item = {
        'labels': json.dumps(labels),
        'image_status': status,
        'image_processing_completed': datetime.now().isoformat()
    }
    table = dynamodb.Table(image_table)

    # Update the image table with the labels and status
    update_item_in_dynamo(table, 'image_hash', image_hash, item)

def update_request_table_based_on_image_hash(image_hash: str, status: str, labels: str):
    """
        Update the status and labels of all the requests matching the image hash 
    """
    table = dynamodb.Table(request_tracker_table)

    # Perform the query on the global secondary index
    response = table.query(
        IndexName=image_hash_index,
        KeyConditionExpression=boto3.dynamodb.conditions.Key('image_hash').eq(image_hash),
        FilterExpression=Attr('request_status').eq('pending')
    )
    
    # Check if there are any items
    if 'Items' in response:
        items = response['Items']
        for item in items:

            update_request_status_with_matching_labels(item['request_id'], status, labels)



def update_request_status_with_matching_labels(request_id: str, status: str, labels: dict):
    """
    From the labels provided by the scanning service, match the label provided in the request and update the status
    """

    table = dynamodb.Table(request_tracker_table)
    item = get_item_from_dynamo(table, item_key={'request_id': request_id})

    label_match = is_label_matching(item['labels'], labels)

    updated_request_item = {
        'label_matched': label_match,
        'image_status': status,
        'request_status': status
    }
    update_item_in_dynamo(table, 'request_id', request_id, updated_request_item)
    

def is_label_matching(label: str , labels: dict) -> bool:
    """
    Match the label based on the labels provided and return True or False
    """
    
    matching_label = [x for x in labels if x['Name'].lower() == label.lower() and x['Confidence'] > 90]

    if matching_label:
        return True
    else:
        return False
    

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

def create_image_metadata(image_hash: str, file_type: str, image_size: int):
    """Store metadata in DynamoDB"""
    try:
        table = dynamodb.Table(image_table)
        item={
                'image_hash': image_hash,
                'image_status': 'processing',
                'file_type': file_type,
                'image_upload_time': datetime.now().isoformat()
                }
        

        logging.info(f"Creating a new image with reference - {item}")

        table.put_item(
            Item=item
        )
        return item
    except ClientError as e:
        raise Exception(f"Error storing {item} in DynamoDB: {str(e)}")
 

def update_item_in_dynamo(table: object, primary_key: str, item_key:str, new_data: dict)-> dict:
    try:
        # Define the update expression and values
        update_expression = "SET "
        expression_attribute_values = {}
        

        for key, value in new_data.items():
            update_expression += f"{key} = :{key}, "
            expression_attribute_values[f":{key}"] = value
        
        update_expression = update_expression.rstrip(', ')

        # Perform the update
        response = table.update_item(
            Key={
                primary_key: item_key  
            },
            UpdateExpression=update_expression,
            ExpressionAttributeValues=expression_attribute_values,
            ReturnValues="ALL_NEW"  
        )

        # Return the updated item
        return response['Attributes']

    except ClientError as e:
        logging.error(f"Error updating item: {e.response['Error']['Message']}")
        raise

def get_item_from_dynamo(table:object, item_key: dict)-> dict:
    try:

        item = None

        # Fetch an item by its primary key
        response = table.get_item(
            Key=item_key
        )

        # Check if the item exists and print the result
        if 'Item' in response:
            item = response['Item']
    except Exception as e:
        logging.exception(f"Error {e} retrieving the {item_key} from {table}")

    return item

if __name__ == '__main__':

    event = {
        'Records': [
            {'eventVersion': '2.1', 'eventSource': 'aws:s3', 'awsRegion': 'us-east-1', 'eventTime': '2025-04-10T14:08:43.632Z', 'eventName': 'ObjectCreated:Put', 'userIdentity': {'principalId': 'AWS:AROAUH4XHVINNITUNNNOL:image_uploader'}, 'requestParameters': {'sourceIPAddress': '107.21.199.50'}, 'responseElements': {'x-amz-request-id': 'XJMQFP803KWRNXYB', 'x-amz-id-2': 'P86M1/vyMpDZM3he1fPdA58zUlu+HL7Ef3R59+36kaJwuvkSlZYnHlt5mhjov2gaBhIYfq3lmOAvVOCerDm+7N66P8ZFRimO'}, 's3': {'s3SchemaVersion': '1.0', 'configurationId': 'a25b9005-4584-4f66-a51e-d05e4131b71f', 'bucket': {'name': 'jothi-image-test-bucket-2', 'ownerIdentity': {'principalId': 'A25NFHTB21CF2B'}, 'arn': 'arn:aws:s3:::jothi-image-test-bucket-2'}, 'object': {'key': '8a56ccfc341865af4ec1c2d836e52e71dcd959e41a8522f60bfcc3ff4e99d388.jpg', 'size': 107329, 'eTag': '26e16131d4778382634bbde8c0024b40', 'versionId': '6J0z62ba3zbf1Y9cOv8YVcf86uwRQ5x3', 'sequencer': '0067F7D0EB95F701A4'}}}
        ]
    }

    lambda_handler(event=event, context=None)