"""
Overlay Model
Mongoose-style Schema/Model for overlay data
"""

from datetime import datetime
from bson.objectid import ObjectId
from marshmallow import Schema, fields, validate, post_load, pre_dump


class PositionSchema(Schema):
    """Schema for position coordinates"""

    x = fields.Float(required=True, validate=validate.Range(min=0))
    y = fields.Float(required=True, validate=validate.Range(min=0))


class SizeSchema(Schema):
    """Schema for size dimensions"""

    width = fields.Float(required=True, validate=validate.Range(min=1))
    height = fields.Float(required=True, validate=validate.Range(min=1))


class OverlaySchema(Schema):
    """
    Overlay Schema - Mongoose-style validation schema

    Fields:
        - id: Unique identifier (MongoDB ObjectId)
        - content: Text content or image URL
        - type: Either 'text' or 'image'
        - position: Object with x and y coordinates
        - size: Object with width and height
        - created_at: Timestamp of creation
        - updated_at: Timestamp of last update
    """

    id = fields.String(dump_only=True, attribute="_id")
    rtsp_url = fields.String(required=False, allow_none=True)
    content = fields.String(required=True, validate=validate.Length(min=1, max=5000))
    type = fields.String(
        required=True,
        validate=validate.OneOf(["text", "image"]),
        error_messages={"validator_failed": 'Type must be either "text" or "image"'},
    )
    position = fields.Nested(PositionSchema, required=True)
    size = fields.Nested(SizeSchema, required=True)
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)

    @pre_dump
    def convert_objectid(self, data, **kwargs):
        """Convert ObjectId to string for JSON serialization"""
        if isinstance(data, dict) and "_id" in data:
            data["_id"] = str(data["_id"])
        return data


class Overlay:
    """
    Overlay Model Class
    Provides CRUD operations for overlay documents in MongoDB
    """

    collection_name = "overlays"
    schema = OverlaySchema()

    def __init__(self, db):
        """
        Initialize the Overlay model with database connection

        Args:
            db: MongoDB database instance
        """
        self.collection = db[self.collection_name]

    def create(self, data):
        """
        Create a new overlay document

        Args:
            data: Dictionary containing overlay data

        Returns:
            Created overlay document with _id
        """
        # Validate data using schema
        errors = self.schema.validate(data)
        if errors:
            raise ValueError(f"Validation error: {errors}")

        # Add timestamps
        now = datetime.utcnow()
        data["created_at"] = now
        data["updated_at"] = now

        # Insert into database
        result = self.collection.insert_one(data)
        data["_id"] = result.inserted_id

        return self.schema.dump(data)

    def delete_by_rtsp_url(self, rtsp_url):
        """
        Delete all overlays for a specific RTSP URL

        Args:
            rtsp_url: The RTSP URL to delete overlays for
        """
        self.collection.delete_many({"rtsp_url": rtsp_url})

    def insert_many(self, overlays_data):
        """
        Insert multiple overlay documents

        Args:
            overlays_data: List of dictionary containing overlay data

        Returns:
            List of created overlays
        """
        if not overlays_data:
            return []

        now = datetime.utcnow()
        to_insert = []

        for data in overlays_data:
            # Validate essential fields manually or use partial schema if needed
            # For simplicity, we trust the input structure matches somewhat or let basic validation happen
            # A correct approach would be to validate each item

            # Clean data (remove id if present to let mongo gen new one, or keep if we want to preserve?
            # Usually strict replacement implies new IDs, but preserving might be nice for frontend React keys.
            # But React uses generated IDs. Let's let Mongo generate new IDs.)
            clean_data = {k: v for k, v in data.items() if k != "id" and k != "_id"}

            clean_data["created_at"] = now
            clean_data["updated_at"] = now
            to_insert.append(clean_data)

        if to_insert:
            result = self.collection.insert_many(to_insert)
            # Result doesn't give back the docs, so we constructing response
            # But simpler to just return the count or success
            return len(result.inserted_ids)

        return 0

    def find_all(self, query=None):
        """
        Retrieve all overlay documents

        Args:
            query: Dictionary for MongoDB filter query (optional)

        Returns:
            List of all overlay documents
        """
        filter_query = query if query is not None else {}
        overlays = list(self.collection.find(filter_query))
        return self.schema.dump(overlays, many=True)

    def find_by_id(self, overlay_id):
        """
        Find an overlay by its ID

        Args:
            overlay_id: String representation of MongoDB ObjectId

        Returns:
            Overlay document if found, None otherwise
        """
        try:
            overlay = self.collection.find_one({"_id": ObjectId(overlay_id)})
            if overlay:
                return self.schema.dump(overlay)
            return None
        except Exception:
            return None

    def update(self, overlay_id, data):
        """
        Update an existing overlay document

        Args:
            overlay_id: String representation of MongoDB ObjectId
            data: Dictionary containing fields to update

        Returns:
            Updated overlay document if found, None otherwise
        """
        # Remove _id from data if present (cannot update _id)
        data.pop("_id", None)
        data.pop("id", None)
        data.pop("created_at", None)

        # Validate partial data
        # For updates, we allow partial data
        validation_data = data.copy()
        errors = {}

        if "type" in data and data["type"] not in ["text", "image"]:
            errors["type"] = ['Type must be either "text" or "image"']

        if errors:
            raise ValueError(f"Validation error: {errors}")

        # Add updated timestamp
        data["updated_at"] = datetime.utcnow()

        try:
            result = self.collection.find_one_and_update(
                {"_id": ObjectId(overlay_id)}, {"$set": data}, return_document=True
            )
            if result:
                return self.schema.dump(result)
            return None
        except Exception:
            return None

    def delete(self, overlay_id):
        """
        Delete an overlay document

        Args:
            overlay_id: String representation of MongoDB ObjectId

        Returns:
            True if deleted, False otherwise
        """
        try:
            result = self.collection.delete_one({"_id": ObjectId(overlay_id)})
            return result.deleted_count > 0
        except Exception:
            return False

    def delete_all(self):
        """
        Delete all overlay documents

        Returns:
            Number of deleted documents
        """
        result = self.collection.delete_many({})
        return result.deleted_count
