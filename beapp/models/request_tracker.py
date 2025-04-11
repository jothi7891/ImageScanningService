import os

from pynamodb.models import Model
from pynamodb.attributes import UnicodeAttribute, ListAttribute, BooleanAttribute
from pynamodb.indexes import GlobalSecondaryIndex, AllProjection


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
    request_time = UnicodeAttribute()
    image_hash = UnicodeAttribute()
    request_status = UnicodeAttribute()
    label_matched = BooleanAttribute(null=True)
    image_status = UnicodeAttribute()
    labels = UnicodeAttribute()

    # Attach the global secondary index for querying by image_hash
    image_hash_index = ImageHashIndex()

