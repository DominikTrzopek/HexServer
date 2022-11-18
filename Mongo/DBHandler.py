import pymongo
from Mongo.DBConfig import Config
from pymongo import errors


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
        try:
            client = pymongo.MongoClient(Config.get_credentials())
            db = client[Config.get_db_name()]
        except (ConnectionRefusedError, errors.InvalidURI) as MongoError:
            exit("Fatal error: Connection to database refused" + MongoError._message)
        return db

    def get_db_collection(self, db, name):
        collection = db[name]
        return collection

    def save_to_collection(self, data, collection):
        coll = self.get_db_collection(self.database, collection)
        return coll.insert_one(data)

    def get_all_from_collection(self, collection):
        coll = self.get_db_collection(self.database, collection)
        servers = [info for info in coll.find({}, {'_id': False})]
        return servers

    def clear_collection(self, collection):
        coll = self.get_db_collection(self.database, collection)
        coll.drop()

    def modify_data(self, collection, filter, new_value):
        print(filter)
        coll = self.get_db_collection(self.database, collection)
        coll.update_one(filter, new_value)

    def get_X_last_documents(self, collection):
        coll = self.get_db_collection(self.database, collection)
        data = coll.find({}, {'_id': False}).sort({'_id':-1}).limit(Config.get_num_of_saved_TCP_documents)
        return [msg for msg in data]

