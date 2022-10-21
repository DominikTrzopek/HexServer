import json
import pymongo
from Mongo.DBConfig import Config

class SingletonMeta(type):

    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            instance = super().__call__(*args, **kwargs)
            cls._instances[cls] = instance
        return cls._instances[cls]


class DBHandler(metaclass=SingletonMeta):

    def __init__(self):
        self.database = self.connect_to_database()

    def connect_to_database(self):
        client = pymongo.MongoClient(Config.credentials())
        db = client[Config.db_name()]
        print("Connected to mongodb, db collections: ")
        print(db.list_collection_names())
        return db

    def get_db_collection(self, db, name):
        collection = db[name]
        return collection

    def save_to_collection(self, data, collection):
        coll = self.get_db_collection(self.database, collection)
        coll.insert_one(data)

    def get_all_from_collection(self, collection):
        coll = self.get_db_collection(self.database, collection)
        servers = [info for info in coll.find({}, {'_id': False})]
        return servers

    def clear_collection(self, collection):
        coll = self.get_db_collection(self.database, collection)
        coll.drop()
