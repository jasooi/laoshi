"""
Mock MongoDB Database Module

This module provides an in-memory mock database that simulates MongoDB behavior.
When ready for production, replace this with actual PyMongo connections.
"""

from datetime import datetime
from typing import Dict, List, Optional, Any
import uuid


class MockCollection:
    """Simulates a MongoDB collection with basic CRUD operations."""

    def __init__(self, name: str):
        self.name = name
        self._data: Dict[str, Dict] = {}

    def _generate_id(self) -> str:
        """Generate a unique ID similar to MongoDB ObjectId."""
        return str(uuid.uuid4())

    def insert_one(self, document: Dict) -> Dict:
        """Insert a single document."""
        doc_id = self._generate_id()
        document['_id'] = doc_id
        document['createdAt'] = datetime.utcnow().isoformat()
        self._data[doc_id] = document.copy()
        return {'inserted_id': doc_id}

    def insert_many(self, documents: List[Dict]) -> Dict:
        """Insert multiple documents."""
        inserted_ids = []
        for doc in documents:
            result = self.insert_one(doc)
            inserted_ids.append(result['inserted_id'])
        return {'inserted_ids': inserted_ids}

    def find(self, filter_query: Optional[Dict] = None) -> List[Dict]:
        """Find documents matching the filter."""
        if filter_query is None:
            return list(self._data.values())

        results = []
        for doc in self._data.values():
            if self._matches_filter(doc, filter_query):
                results.append(doc.copy())
        return results

    def find_one(self, filter_query: Dict) -> Optional[Dict]:
        """Find a single document matching the filter."""
        for doc in self._data.values():
            if self._matches_filter(doc, filter_query):
                return doc.copy()
        return None

    def update_one(self, filter_query: Dict, update: Dict) -> Dict:
        """Update a single document."""
        for doc_id, doc in self._data.items():
            if self._matches_filter(doc, filter_query):
                if '$set' in update:
                    for key, value in update['$set'].items():
                        self._data[doc_id][key] = value
                self._data[doc_id]['updatedAt'] = datetime.utcnow().isoformat()
                return {'matched_count': 1, 'modified_count': 1}
        return {'matched_count': 0, 'modified_count': 0}

    def delete_one(self, filter_query: Dict) -> Dict:
        """Delete a single document."""
        for doc_id, doc in list(self._data.items()):
            if self._matches_filter(doc, filter_query):
                del self._data[doc_id]
                return {'deleted_count': 1}
        return {'deleted_count': 0}

    def delete_many(self, filter_query: Dict) -> Dict:
        """Delete multiple documents."""
        deleted_count = 0
        for doc_id, doc in list(self._data.items()):
            if self._matches_filter(doc, filter_query):
                del self._data[doc_id]
                deleted_count += 1
        return {'deleted_count': deleted_count}

    def count_documents(self, filter_query: Optional[Dict] = None) -> int:
        """Count documents matching the filter."""
        if filter_query is None:
            return len(self._data)
        return len(self.find(filter_query))

    def _matches_filter(self, doc: Dict, filter_query: Dict) -> bool:
        """Check if a document matches the filter query."""
        for key, value in filter_query.items():
            if key not in doc:
                return False
            if isinstance(value, dict):
                # Handle MongoDB operators like $in, $gt, etc.
                for op, op_value in value.items():
                    if op == '$in':
                        if doc[key] not in op_value:
                            return False
                    elif op == '$nin':
                        if doc[key] in op_value:
                            return False
                    elif op == '$gt':
                        if not doc[key] > op_value:
                            return False
                    elif op == '$gte':
                        if not doc[key] >= op_value:
                            return False
                    elif op == '$lt':
                        if not doc[key] < op_value:
                            return False
                    elif op == '$lte':
                        if not doc[key] <= op_value:
                            return False
            elif doc[key] != value:
                return False
        return True


class MockDatabase:
    """Simulates a MongoDB database with multiple collections."""

    def __init__(self, name: str):
        self.name = name
        self._collections: Dict[str, MockCollection] = {}

    def __getitem__(self, collection_name: str) -> MockCollection:
        """Get or create a collection."""
        if collection_name not in self._collections:
            self._collections[collection_name] = MockCollection(collection_name)
        return self._collections[collection_name]

    def get_collection(self, collection_name: str) -> MockCollection:
        """Get or create a collection."""
        return self[collection_name]

    def list_collection_names(self) -> List[str]:
        """List all collection names."""
        return list(self._collections.keys())


class MockMongoClient:
    """Simulates a MongoDB client connection."""

    def __init__(self, connection_string: str = "mock://localhost:27017"):
        self.connection_string = connection_string
        self._databases: Dict[str, MockDatabase] = {}

    def __getitem__(self, db_name: str) -> MockDatabase:
        """Get or create a database."""
        if db_name not in self._databases:
            self._databases[db_name] = MockDatabase(db_name)
        return self._databases[db_name]

    def get_database(self, db_name: str) -> MockDatabase:
        """Get or create a database."""
        return self[db_name]

    def close(self):
        """Close the connection (no-op for mock)."""
        pass


# Global mock client instance
_mock_client: Optional[MockMongoClient] = None


def get_db() -> MockDatabase:
    """Get the mock database instance."""
    global _mock_client
    if _mock_client is None:
        _mock_client = MockMongoClient()
    return _mock_client['laoshi']


def get_vocabulary_collection() -> MockCollection:
    """Get the vocabulary collection."""
    return get_db()['vocabulary']


def get_sources_collection() -> MockCollection:
    """Get the vocabulary sources collection."""
    return get_db()['sources']


def get_progress_collection() -> MockCollection:
    """Get the progress collection."""
    return get_db()['progress']


def get_settings_collection() -> MockCollection:
    """Get the settings collection."""
    return get_db()['settings']
