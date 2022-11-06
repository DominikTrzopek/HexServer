import imp
import json
import socket
import os
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
        self.connections = 1
        self.listen(self.sockets[0])

    def prepare_sockets(self):
        sockets = []
        for port in self.ports:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.bind((self.ip, port))
            sockets.append(sock)
        return sockets

    def listen(self, socket):
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
                data = conn.recv(bufferSize)
                print(data)
                if not data:
                    break
                conn.sendall(data)
