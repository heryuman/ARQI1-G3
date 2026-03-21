from pymongo import MongoClient
from config import MONGO_URI, MONGO_DB_NAME

class MongoService:
    def __init__(self):
        self.client = MongoClient(MONGO_URI)
        self.db = self.client[MONGO_DB_NAME]

    def insert(self, collection, payload):
        self.db[collection].insert_one(payload)
