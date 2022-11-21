import json
import socket
import os
import threading
import time
import signal
import sys
import select
from Mongo.DBHandler import DBHandler
from Mongo.DBHandler import Config
from TCP.TCPConnection import TCPConnection
from socket import SHUT_RDWR
from CommunicationCodes import ResponseType


bufferSize = 1024
timeout = 10


class TCPServer():
    def __init__(self, ip, id, password, ports):
        self.ip = ip
        self.creator_id = id
        self.password = password
        self.ports = ports
        self.database = DBHandler()
        self.threads = []
        self.connections = 0

        self.sockets, self.conn_info = self.prepare_sockets()
        self.listen = [True for i in range(0, len(ports) + 1)]
        self.locks = [threading.Lock() for i in range(0, len(ports))]

        self.insert_to_server_ttl()
        self.num_of_all_msg = 0
        self.msg_queue = self.create_msg_queue()

        signal.signal(signal.SIGINT, self.signal_handler)
        self.connected_ports = self.start_conn_threads(self.sockets)

    def signal_handler(self, _signo, _stack_frame):
        self.listen = [False for i in range(0, len(self.sockets) + 1)]
        self.unlock_mutexes()
        for sock in self.sockets:
            try:
                sock.shutdown(SHUT_RDWR)
                sock.close()
            except OSError:
                pass
        for thread in self.threads:
            thread.join()
            print("thread gone")
        sys.exit(0)

    def prepare_sockets(self):
        sockets = []
        conn_info = []
        for port in self.ports:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.bind((self.ip, port))
            sockets.append(sock)
            conn_info.append(TCPConnection(port))
        return sockets, conn_info

    def create_msg_queue(self):
        return [None for i in range(Config.get_max_msg_num())]

    def add_to_msg_queue(self, msg):
        self.msg_queue[self.num_of_all_msg %
                       Config.get_max_msg_num()] = msg
        self.num_of_all_msg += 1
        self.unlock_mutexes()

    def start_conn_threads(self, sockets):
        for it, socket in enumerate(sockets):
            thread = threading.Thread(target=self.listen_for_connections, args=(
                socket, self.conn_info[it], it,))
            self.threads.append(thread)
            thread.start()
        for thread in self.threads:
            thread.join()

    def listen_for_connections(self, socket, this_conn_info, num_of_thread):
        while (self.listen[-1]):
            self.listen[num_of_thread] = True
            socket.listen()
            port_number = socket.getsockname()[1]
            try:
                conn, addr = socket.accept()
            except OSError:
                return
            with conn:
                data = conn.recv(bufferSize)
                check, error_response = self.authorise(data, addr)
                if check:
                    self.update_num_of_connections(1)
                    self.update_port_pool(port_number, if_remove=True)
                    this_conn_info.fill_info(data, addr)
                    for info in self.conn_info:
                        conn.sendall(str.encode(json.dumps(
                            info.response_with_info()) + "\n"))
                        print("sent data")
                    self.unlock_mutexes()
                    msg = TCPConnection.collect_message(data)
                    if msg != "":
                        self.msg_queue[self.num_of_all_msg %
                                       Config.get_max_msg_num()] = msg
                        self.num_of_all_msg += 1

                    receiver_thread = threading.Thread(target=self.listen_for_data, args=(
                        conn, this_conn_info, addr, num_of_thread,))
                    sender_thread = threading.Thread(
                        target=self.send_data, args=(conn, num_of_thread,))

                    receiver_thread.start()
                    sender_thread.start()

                    receiver_thread.join()
                    sender_thread.join()

                    self.disconnect_client(
                        conn, addr, num_of_thread, port_number)
                elif (error_response != None):
                    conn.sendall(self.prepare_error_response(error_response))

    def prepare_error_response(self, response_code, message=""):
        response = {}
        response["code"] = response_code
        response["errorMessage"] = message
        return str.encode(json.dumps(response))

    def listen_for_data(self, conn, conn_info, addr, num_of_thread):
        while (self.listen[num_of_thread]):
            do_read = False
            print(do_read)
            try:
                r, _, _ = select.select([conn], [], [], timeout)
                do_read = bool(r)

                if do_read:
                    data = conn.recv(bufferSize)
                    if (len(data) == 0):
                        raise socket.error
                    self.add_to_msg_queue(TCPConnection.collect_message(data))
                    self.update_server_ttl()
                    conn_info.fill_info(data, addr)
            except socket.error:
                self.listen[num_of_thread] = False
                conn_info.clear_info()
                self.add_to_msg_queue(conn_info.response_with_info())
                return

    def send_data(self, conn, num_of_thread):
        num_of_read_msg = self.num_of_all_msg
        while (self.listen[num_of_thread]):
            self.locks[num_of_thread].acquire()
            current = self.num_of_all_msg % Config.get_max_msg_num()
            diff = self.num_of_all_msg - num_of_read_msg
            if diff > Config.get_max_msg_num():
                self.listen[num_of_thread] = False
                return
            if diff > 0:
                index = (current - diff) % Config.get_max_msg_num()
                for i in range(0, diff):
                    conn.sendall(TCPConnection.prepare_message(
                        self.msg_queue[index]))
                    num_of_read_msg += 1
                    index += 1
                    index %= Config.get_max_msg_num()

    def disconnect_client(self, conn, addr, num, port):
        print(f"Disconnected {addr}")
        self.update_num_of_connections(-1)
        self.update_port_pool(port, if_remove=False)
        self.conn_info[num].clear_info()
        self.conn_info[num].clear_id()
        conn.close()

    def authorise(self, data, addr):
        try:
            message = json.loads(str(data, 'utf-8'))
            if message["password"] != self.password:
                return False, ResponseType.WRONGPASSWORD
            if message["playerInfo"]["id"].strip() == "" or message["playerInfo"]["name"].strip() == "":
                return False, ResponseType.BADARGUMENTS
        except KeyError:
            return False, ResponseType.BADREQUEST
        except json.decoder.JSONDecodeError:
            return False, ResponseType.BADREQUEST
        print(f"{os.getpid()}: connected by {addr}")
        return True, None

    #######################################################

    def insert_to_server_ttl(self):
        data = {}
        data["pid"] = os.getpid()
        data["last_msg"] = time.time()
        self.database.save_to_collection(data, Config.get_ttl_collection())

    def update_num_of_connections(self, val):
        self.connections += val
        self.database.modify_data(
            Config.get_server_collection(),
            {'pid': os.getpid()},
            {"$set": {'connections': self.connections}}
        )

    def update_port_pool(self, val, if_remove):
        if if_remove:
            self.ports.remove(val)
        else:
            self.ports.append(val)
        self.database.modify_data(
            Config.get_server_collection(),
            {'pid': os.getpid()},
            {"$set": {'ports': self.ports}}
        )

    def update_server_ttl(self):
        self.database.modify_data(
            Config.get_ttl_collection(),
            {'pid': os.getpid()},
            {"$set": {'last_msg': time.time()}}
        )

    ################################################################

    def unlock_mutexes(self):
        for lock in self.locks:
            if (lock.locked()):
                lock.release()

    def server_hello(self, socket):
        socket.listen()
        conn, addr = socket.accept()
        with conn:
            self.connections += 1
            print(f"Connected by {addr}")
            while True:
                data = conn.recv(bufferSize)
                print(data)
                conn.sendall(str.encode("Server says hi"))
