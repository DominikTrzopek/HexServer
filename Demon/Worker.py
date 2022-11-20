import os
import signal
import time
from Mongo.DBHandler import DBHandler
from Mongo.DBHandler import Config


class Worker():
    def __init__(self):
        self.database = DBHandler()

    def check_ttl(self):
        servers_ttl = self.database.get_all_from_collection(
            Config.get_ttl_collection())
        for server_ttl in servers_ttl:
            time_diff = time.time() - server_ttl["last_msg"]
            filter = {"pid": server_ttl["pid"]}
            try:
                connections = (self.database.get_one_from_collection(
                    Config.get_server_collection(), filter)).get("connections")
            except AttributeError:
                connections = 0
            if (time_diff > Config.get_max_idle_time() or (connections == 0 and time_diff > Config.get_max_idle_no_connections())):
                self.database.delete_from_collection(
                    Config.get_ttl_collection(), filter)
                self.database.delete_from_collection(
                    Config.get_server_collection(), filter)
                try:
                    os.kill(server_ttl["pid"], signal.SIGINT)
                except ProcessLookupError as err:
                    pass


def run():
    worker = Worker()
    while (True):
        worker.check_ttl()
        time.sleep(10)
