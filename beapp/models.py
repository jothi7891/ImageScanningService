import logging
import os

from pynamodb.models import Model
from pynamodb.attributes import UnicodeAttribute, ListAttribute, BooleanAttribute
from pynamodb.indexes import GlobalSecondaryIndex, AllProjection

# Logging configuration
logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s [%(threadName)-12.12s] [%(levelname)-5.5s]  %(message)s",
                    handlers=[logging.StreamHandler()])
logger = logging.getLogger(__name__)

# Define the ImageDetail model for image metadata
class ImageDetail(Model):
    class Meta:
        table_name = os.environ['IMAGE_DETAIL_TABLE']
    
    image_hash = UnicodeAttribute(hash_key=True)
    image_status = UnicodeAttribute()
    file_type = UnicodeAttribute()
    image_upload_time = UnicodeAttribute()
    labels = ListAttribute(of=UnicodeAttribute, default=list)  # Storing labels as a list of strings
    image_processing_completed = UnicodeAttribute(null=True)

# Define the GSI for querying by image_hash
class ImageHashIndex(GlobalSecondaryIndex):
    class Meta:
        index_name = os.environ['REQUEST_TRACKER_IMAGE_INDEX']
        read_capacity = 5
        write_capacity = 5
        projection = AllProjection()

    image_hash = UnicodeAttribute(hash_key=True)

# Define the RequestTracker model for request metadata with the GSI
class RequestTracker(Model):
    class Meta:
        table_name = os.environ['REQUEST_TRACKER_TABLE']

    request_id = UnicodeAttribute(hash_key=True)
    image_hash = UnicodeAttribute()
    request_status = UnicodeAttribute()
    label_matched = BooleanAttribute(null=True)
    image_status = UnicodeAttribute()
    labels = ListAttribute(of=UnicodeAttribute, default=list)  # Storing labels as a list of strings

    # Attach the global secondary index for querying by image_hash
    image_hash_index = ImageHashIndex()

