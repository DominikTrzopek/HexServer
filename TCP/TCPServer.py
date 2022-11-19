import json
import socket
import os
import threading
from Mongo.DBHandler import DBHandler
from Mongo.DBHandler import Config
from TCP.TCPConnection import TCPConnection


bufferSize = 1024


class TCPServer():
    def __init__(self, ip, id, password, ports):
        self.ip = ip
        self.creator_id = id
        self.password = password
        self.ports = ports
        self.database = DBHandler()

        self.sockets, self.conn_info = self.prepare_sockets()
        self.connections = 0
        self.listen = [True for i in range(0, len(ports))]
        self.locks = [threading.Lock() for i in range(0, len(ports))]
        
        self.num_of_all_msg = 0
        self.msg_queue = self.create_msg_queue()
        self.connected_ports = self.connect_clients(self.sockets)

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

    def connect_clients(self, sockets):
        for it, socket in enumerate(sockets):
            thread = threading.Thread(target=self.listen_for_connections, args=(
                socket, self.conn_info[it], it,))
            thread.start()

    def listen_for_connections(self, socket, this_conn_info, num_of_thread):
        while (True):
            self.listen[num_of_thread] = True
            socket.listen()
            port_number = socket.getsockname()[1]
            conn, addr = socket.accept()
            with conn:
                data = conn.recv(bufferSize)
                check = self.authorise(data, addr)
                if check:
                    self.update_num_of_connections(1)
                    self.update_port_pool(port_number, if_remove=True)
                    this_conn_info.fill_info(data, addr)
                for info in self.conn_info:
                    conn.sendall(str.encode(json.dumps(
                        info.response_with_info()) + "\n"))
                self.unlock_mutexes()
                msg = TCPConnection.collect_message(data)
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

    def listen_for_data(self, conn, conn_info, addr, num_of_thread):
        while (self.listen[num_of_thread]):
            data = conn.recv(bufferSize)
            if (len(data) == 0):
                self.listen[num_of_thread] = False
                conn_info.clear_info()
                self.add_to_msg_queue(conn_info.response_with_info())
                return
            self.add_to_msg_queue(TCPConnection.collect_message(data))
            conn_info.fill_info(data, addr)

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

    def add_to_msg_queue(self, msg):
        self.msg_queue[self.num_of_all_msg %
                           Config.get_max_msg_num()] = msg
        self.num_of_all_msg += 1
        self.unlock_mutexes()

    def disconnect_client(self, conn, addr, num, port):
        print(f"Disconnected {addr}")
        self.update_num_of_connections(-1)
        self.update_port_pool(port, if_remove=False)
        self.conn_info[num].clear_info()
        self.conn_info[num].clear_id()
        conn.close()

    def authorise(self, data, addr):
        message = json.loads(str(data, 'utf-8'))
        try:
            if message["password"] != self.password:
                print(f"Connected by {addr}: wrong password")
                return False
            if message["playerInfo"]["id"] == "" or message["playerInfo"]["name"] == "":
                print(f"Connected by {addr}: empty player info")
                return False
        except KeyError:
            print(f"Connected by {addr}: bad connect message")
            return False
        print(f"Connected by {addr}: success")
        return True

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
