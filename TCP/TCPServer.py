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
        #stworzyć kolekcje dla wiadomości
        self.msg_queue = self.create_msg_queue()
        #self.num_of_read_msg = 0 -> dla każdego wątku
        self.num_of_all_msg = 0
        self.pid = os.getpid()

    def create_msg_queue(self):
        return [None for i in range(Config.get_max_msg_num())]

    def connect_clients(self, sockets):
        for it, socket in enumerate(sockets):
            thread = threading.Thread(target = self.listen_for_connections, args = (socket, self.conn_info[it],))
            thread.start()

    def listen_for_connections(self, socket, this_conn_info):
        socket.listen()
        conn, addr = socket.accept()
        with conn:
            data = conn.recv(bufferSize)
            check = self.authorise(data, addr)
            if check:
                self.update_num_of_connections(1)
                this_conn_info.fill_info(data, addr)
            for info in self.conn_info:
                conn.sendall(info.response_with_info())
            
            msg = TCPConnection.collect_message(data)
            self.msg_queue[self.num_of_all_msg % Config.get_max_msg_num()] = msg
            self.num_of_all_msg += 1

            receiver_thread = threading.Thread(target = self.listen_for_data, args = (conn, this_conn_info, addr,))
            sender_thread = threading.Thread(target = self.send_data, args = (conn,))
            receiver_thread.start()
            sender_thread.start()
            sender_thread.join()

    def listen_for_data(self, conn, conn_info, addr):
        while(self.listen):
            data = conn.recv(bufferSize)
            msg = TCPConnection.collect_message(data)
            self.msg_queue[self.num_of_all_msg % Config.get_max_msg_num()] = msg
            #save to database
            self.num_of_all_msg += 1
            #all += 1
            conn_info.fill_info(data, addr)

    def send_data(self, conn):
        num_of_read_msg = self.num_of_all_msg
        while(self.listen):
            time.sleep(1)
            current = self.num_of_all_msg % Config.get_max_msg_num()
            diff = self.num_of_all_msg - num_of_read_msg
            print(str(self.num_of_all_msg) + " | " + str(num_of_read_msg) + " | " + str(diff) + " ||| " + str(current) + " | " + str((current - diff) % Config.get_max_msg_num()))
            if diff > Config.get_max_msg_num():
                pass
                #close connection
            if diff > 0:
                index = index = (current - diff) % Config.get_max_msg_num()
                for i in range(0, diff):
                    print(TCPConnection.prepare_message(self.msg_queue[index]))
                    conn.sendall(TCPConnection.prepare_message(self.msg_queue[index]))
                    num_of_read_msg += 1
                    index += 1
                    index %= Config.get_max_msg_num()


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
