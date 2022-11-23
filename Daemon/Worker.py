import os
import signal
import time
from Mongo.DBHandler import DBHandler
from Mongo.DBHandler import Config
from Daemon.Cleaner import Cleaner

sleep_time = 60


class Worker:
    def __init__(self):
        self.database = DBHandler()

    def check_ttl(self):
        servers_ttl = self.database.get_all_from_collection(
            Config.get_ttl_collection())
        for server_ttl in servers_ttl:
            pid = server_ttl["pid"]
            time_diff = time.time() - server_ttl["last_msg"]
            if self.check_if_idle(time_diff, {"pid": pid}):
                Cleaner(pid).do_cleanup()

    def get_num_of_connections(self, filter):
        try:
            return (
                self.database.get_one_from_collection(
                    Config.get_server_collection(), filter
                )
            ).get("connections")
        except AttributeError:
            return 0

    def kill_process(self, pid):
        try:
            os.kill(pid, signal.SIGINT)
        except ProcessLookupError:
            pass

    def check_if_idle(self, time_diff, filter):
        return time_diff > Config.get_max_idle_time() or (
            self.get_num_of_connections(filter) == 0
            and time_diff > Config.get_max_idle_no_connections()
        )


def run():
    worker = Worker()
    print("Daemon started")
    while True:
        worker.check_ttl()
        time.sleep(sleep_time)
