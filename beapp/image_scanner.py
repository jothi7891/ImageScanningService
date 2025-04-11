import json
import logging
import os
import sys
from datetime import datetime

import boto3
from pynamodb.exceptions import DoesNotExist

from models.request_tracker import RequestTracker
from models.image_details import ImageDetail


# Initialize Rekognition client
rekognition = boto3.client('rekognition')


image_hash_index = os.environ['REQUEST_TRACKER_IMAGE_INDEX']
bucket_name = os.environ['IMAGE_STORAGE_BUCKET']

#Remove all handlers associated with the root logger object.

for handler in logging.root.handlers[:]:
    logging.root.removeHandler(handler)

logger = logging.getLogger(__name__)

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s [%(threadName)-12.12s] [%(levelname)-5.5s]  %(message)s",
                    handlers=[
                        logging.StreamHandler(sys.stdout)
                    ])


def lambda_handler(event, context):
    try:
        for record in event['Records']:
            logging.info(f"Received New Image Upload Event - {record}")
            
            bucket_name = record['s3']['bucket']['name']
            file_key = record['s3']['object']['key']
            image_hash = file_key.split('.')[0]
            file_type = file_key.split('.')[1]
            image_size = record['s3']['object']['size']

            try:

                # Query using PynamoDB model (ImageDetail)
                existing_item = ImageDetail.get(image_hash)
                            
            except DoesNotExist:
                
                existing_item = None

            if existing_item:
                logging.info(f"Image with hash {image_hash} already exists in DynamoDB. Skipping processing.")
                status = 'completed'
                image_labels = existing_item.labels
            else:
                image_item = create_image_metadata(image_hash, file_type, image_size)
                logging.info(f"Image metadata - {image_item} created for {file_key}")
                logging.info(f"Extracting labels from image {file_key}")
                image_labels = image_labels_from_s3file(bucket_name, file_key)
                logging.info(f"Image labels - {image_labels}")
                status = 'completed'
                update_image_metadata_with_labels(image_hash, image_labels, status)

            # Update the request tracker table based on the image hash
            update_request_table_based_on_image_hash(image_hash, status, image_labels)

    except Exception as e:
        logging.exception(f"Error in processing the event: {e}")

def update_image_metadata_with_labels(image_hash: str, labels: dict, status: str):
    """
        Update the status of image hash in image table
    """
    try:

        image_detail = ImageDetail.get(image_hash)  # Retrieve the image detail
        image_detail.update(actions=[
            ImageDetail.labels.set(labels),
            ImageDetail.image_status.set(status),
            ImageDetail.image_processing_complete_time.set(datetime.now().isoformat())
        ])

        logging.info(f"Image metadata for {image_hash} updated.")
    except DoesNotExist:
        logging.error(f"Image with hash {image_hash} does not exist in DynamoDB.")
    except Exception as e:
        logging.error(f"Error updating image metadata: {e}")

def update_request_table_based_on_image_hash(image_hash: str, status: str, labels: str):
    """
        Update the status and labels of all the requests matching the image hash
    """
    try:
        # Use PynamoDB's query with filter
        items = RequestTracker.image_hash_index.query(image_hash, filter_condition=RequestTracker.request_status == 'pending')

        for item in items:
            update_request_status_with_matching_labels(item.request_id, status, labels)

    except Exception as e:
        logging.error(f"Error updating request table for image hash {image_hash}: {e}")

def update_request_status_with_matching_labels(request_id: str, status: str, labels: dict):
    """
    From the labels provided by the scanning service, match the label provided in the request and update the status
    """
    try:
        # Get the item from RequestTracker
        request_item = RequestTracker.get(request_id)
        label_match = is_label_matching(request_item.labels, labels)

        # Update the request item with new status and label match
        request_item.update(actions=[
            RequestTracker.label_matched.set(label_match),
            RequestTracker.image_status.set(status),
            RequestTracker.request_status.set(status),
            RequestTracker.request_complete_time.set(datetime.now().isoformat())
        ])

        logging.info(f"Request {request_id} status updated based on label match.")
    except DoesNotExist:
        logging.error(f"Request {request_id} does not exist.")
    except Exception as e:
        logging.error(f"Error updating request status for {request_id}: {e}")

def is_label_matching(label: str, labels: dict) -> bool:
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
            Image={'S3Object': {'Bucket': bucket_name, 'Name': file_name}}
        )

        logging.info(f"AWS Image recognition service response for {file_name} - {response}")
        return response["Labels"]

    except Exception as e:
        logging.exception(f"Error in processing the image {file_name}")
        return []

def create_image_metadata(image_hash: str, file_type: str, image_size: int):
    """Store metadata in DynamoDB using PynamoDB"""
    try:
        item = ImageDetail(
            image_hash=image_hash,
            image_status='processing',
            file_type=file_type,
            image_upload_time=datetime.now().isoformat()
        )

        logging.info(f"Creating a new image metadata: {item}")
        item.save()
        return item
    except Exception as e:
        logging.exception(f"Error storing {item} in DynamoDB: {e}")
        return None

if __name__ == '__main__':
    event = {'Records':[{'eventVersion': '2.1', 'eventSource': 'aws:s3', 'awsRegion': 'us-east-1', 'eventTime': '2025-04-10T14:06:07.978Z', 'eventName': 'ObjectCreated:Put', 'userIdentity': {'principalId': 'AWS:AROAUH4XHVINNITUNNNOL:image_uploader'}, 'requestParameters': {'sourceIPAddress': '107.21.199.50'}, 'responseElements': {'x-amz-request-id': 'D6M00Z8HY7TMY1D9', 'x-amz-id-2': 'Sw1Ax2LK2Q92kwYySiuRHnquS5+t37i84TvD/lrHhGPXtKisE50GuRvO9XxQlxkR/MtHZzpOX7dtM5mn04ImshUExVXzCylq'}, 's3': {'s3SchemaVersion': '1.0', 'configurationId': 'a25b9005-4584-4f66-a51e-d05e4131b71f', 'bucket': {'name': 'jothi-image-test-bucket-2', 'ownerIdentity': {'principalId': 'A25NFHTB21CF2B'}, 'arn': 'arn:aws:s3:::jothi-image-test-bucket-2'}, 'object': {'key': '8a56ccfc341865af4ec1c2d836e52e71dcd959e41a8522f60bfcc3ff4e99d388.jpg', 'size': 107329, 'eTag': '26e16131d4778382634bbde8c0024b40', 'versionId': 'PxXcRsrIQiAiooihhC4sQQCytbPbGATp', 'sequencer': '0067F7D04FEADC629A'}}}]}
    lambda_handler(event, None)