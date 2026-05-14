from pymongo import MongoClient
from pymongo.database import Database

_client: MongoClient | None = None


def get_db(uri: str = "mongodb://localhost:27017", db_name: str = "albion_bot") -> Database:
    global _client
    if _client is None:
        _client = MongoClient(uri)
    return _client[db_name]


def close():
    global _client
    if _client is not None:
        _client.close()
        _client = None
