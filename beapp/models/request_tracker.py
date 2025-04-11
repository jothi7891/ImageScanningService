import os

from pynamodb.models import Model
from pynamodb.attributes import UnicodeAttribute, ListAttribute, BooleanAttribute
from pynamodb.indexes import GlobalSecondaryIndex, AllProjection

from models.image_details import ImageDetail

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
    request_start_time = UnicodeAttribute()
    request_complete_time = UnicodeAttribute(null=True)
    image_hash = UnicodeAttribute()
    request_status = UnicodeAttribute()
    label_matched = BooleanAttribute(null=True)
    image_status = UnicodeAttribute()
    labels = UnicodeAttribute()

    # Attach the global secondary index for querying by image_hash
    image_hash_index = ImageHashIndex()

    def to_normal_user(self):
        return {
            'request_id': self.request_id,
            f"contains{str(self.labels).title()}": self.label_matched
        }

    def to_power_user(self):

        debug_data = {
            'request_details': self.attribute_values
        }
        try:
            image_item = ImageDetail.get(self.image_hash)

            if image_item:
                debug_data['image_details'] = image_item.attribute_values
        except:
            pass
        return {
            'request_id': self.request_id,
            f"contains{str(self.labels).title()}": self.label_matched,
            'debug_data': debug_data
        }
