import os

from pynamodb.models import Model
from pynamodb.attributes import UnicodeAttribute, ListAttribute, BooleanAttribute, MapAttribute


# Define the ImageDetail model for image metadata
class ImageDetail(Model):
    class Meta:
        table_name = os.environ['IMAGE_DETAIL_TABLE']
    
    image_hash = UnicodeAttribute(hash_key=True)
    image_status = UnicodeAttribute()
    file_type = UnicodeAttribute()
    image_upload_time = UnicodeAttribute()
    labels = ListAttribute(of=MapAttribute, default=list)  # Storing labels as a list of dicts
    image_processing_complete_time= UnicodeAttribute(null=True)

