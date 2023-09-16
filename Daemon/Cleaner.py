import signal
from os import kill
from Mongo.DBHandler import DBHandler
from Mongo.DBHandler import Config


class Cleaner:
    def __init__(self, pid):
        self.pid = pid
        self.database = DBHandler()

    def do_cleanup(self):
        self.delete_data_from_db()
        self.kill_process()

    def kill_process(self):
        try:
            kill(self.pid, signal.SIGINT)
        except ProcessLookupError:
            pass

    def delete_data_from_db(self):
        filter = {"pid": self.pid}
        self.database.delete_from_collection(Config.get_ttl_collection(), filter)
        self.database.delete_from_collection(Config.get_server_collection(), filter)
