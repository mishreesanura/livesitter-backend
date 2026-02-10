"""
Database Configuration Module
Handles MongoDB connection setup and management
"""
import os
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure


class DatabaseConfig:
    """MongoDB Database Configuration Class"""
    
    def __init__(self):
        self.client = None
        self.db = None
    
    def init_db(self, app):
        """
        Initialize MongoDB connection with Flask app
        
        Args:
            app: Flask application instance
        """
        mongo_uri = app.config.get('MONGO_URI', 'mongodb://localhost:27017/')
        db_name = app.config.get('MONGO_DBNAME', 'livesitter_db')
        
        try:
            self.client = MongoClient(mongo_uri)
            # Verify connection
            self.client.admin.command('ping')
            self.db = self.client[db_name]
            print(f"✅ Successfully connected to MongoDB: {db_name}")
            return self.db
        except ConnectionFailure as e:
            print(f"❌ Failed to connect to MongoDB: {e}")
            raise e
    
    def get_db(self):
        """Get the database instance"""
        return self.db
    
    def get_collection(self, collection_name):
        """
        Get a specific collection from the database
        
        Args:
            collection_name: Name of the collection
            
        Returns:
            MongoDB collection instance
        """
        if self.db is not None:
            return self.db[collection_name]
        raise Exception("Database not initialized. Call init_db first.")
    
    def close_connection(self):
        """Close the MongoDB connection"""
        if self.client:
            self.client.close()
            print("MongoDB connection closed.")


# Create a singleton instance
db_config = DatabaseConfig()
