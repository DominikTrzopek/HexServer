import imp
import json
import socket
import os
import threading
from Mongo.DBHandler import DBHandler
from Mongo.DBHandler import Config

bufferSize = 1024

class TCPServer():
    def __init__(self, ip, id, password, ports):
        self.ip = ip
        self.creator_id = id
        self.password = password
        self.ports = ports
        self.database = DBHandler()
        self.sockets = self.prepare_sockets()
        self.connections = 0
        #self.authorisefffff(self.sockets[0])
        self.connected_ports = self.connect_clients(self.sockets)

    def connect_clients(self, sockets):
        for socket in sockets:
            thread = threading.Thread(target = self.listen_for_connections, args = (socket,))
            thread.start()

    def listen_for_connections(self, socket):
        socket.listen()
        conn, addr = socket.accept()
        with conn:
            print(f"Connected by {addr}")
            data = conn.recv(bufferSize)
            print(data)
            check = self.authorise(data)
            if check:
                self.update_num_of_connections(1)
            conn.sendall(data)

    def authorise(self, data):
        message = json.loads(str(data, 'utf-8'))
        if message["password"] == self.password:
            print("Correct password")
            return True
        return False

    def update_num_of_connections(self, val):
        self.connections += val
        self.database.modify_data(
            Config.get_server_collection(),
            {'pid': os.getpid()},
            {"$set": {'connections': self.connections}} #TODO set value
        )

    def prepare_sockets(self):
        sockets = []
        for port in self.ports:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.bind((self.ip, port))
            sockets.append(sock)
        return sockets

    def authorisefffff(self, socket):
        socket.listen()
        conn, addr = socket.accept()
        self.database.modify_data(
            Config.get_server_collection(),
            {'pid': os.getpid()},
            {"$set": {'connections': self.connections}} #TODO set value
        )
        with conn:
            self.connections += 1
            print(f"Connected by {addr}")
            while True:
               # data = conn.recv(bufferSize)
               # print(data)
                conn.sendall(str.encode("Server says hi"))
