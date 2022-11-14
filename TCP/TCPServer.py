import imp
import json
import socket
import os
import threading
import time
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
        self.listen = True
        self.connected_ports = self.connect_clients(self.sockets)

    def connect_clients(self, sockets):
        for it, socket in enumerate(sockets):
            thread = threading.Thread(target = self.listen_for_connections, args = (socket, self.conn_info[it],))
            thread.start()

    def listen_for_connections(self, socket, this_conn_info):
        socket.listen()
        conn, addr = socket.accept()
        with conn:
            data = conn.recv(bufferSize)
            print(data)
            check = self.authorise(data, addr)
            if check:
                self.update_num_of_connections(1)
                this_conn_info.fill_info(data, addr)
            for info in self.conn_info:
                conn.sendall(info.response_with_info())
            receiver_thread = threading.Thread(target = self.listen_for_status_change, args = (conn, this_conn_info, addr,))
            sender_thread = threading.Thread(target = self.send_data, args = (conn,))
            receiver_thread.start()
            sender_thread.start()
            sender_thread.join()

    def listen_for_status_change(self, conn, conn_info, addr):
        while(self.listen):
            data = conn.recv(bufferSize)
            print(data)
            conn_info.fill_info(data, addr)

    def send_data(self, conn):
        while(self.listen):
            time.sleep(1)
            for info in self.conn_info:
                conn.sendall(info.response_with_info())

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

    def prepare_sockets(self):
        sockets = []
        conn_info = []
        for port in self.ports:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.bind((self.ip, port))
            sockets.append(sock)
            conn_info.append(TCPConnection(port))
        return sockets, conn_info

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
