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
from CommunicationCodes import ClientStatusType
from copy import deepcopy

bufferSize = 8196
timeout = 2


class TCPServer:
    def __init__(self, ip, id, password, ports, game_lenght):
        self.ip = ip
        self.creator_id = id
        self.password = password
        self.ports = ports
        self.game_lenght = game_lenght
        self.database = DBHandler()
        self.threads = []
        self.connections = 0
        self.game_state = None

        self.game_started = False
        self.current_move = 0
        self.num_of_players = len(ports)

        self.sockets, self.conn_info = self.prepare_sockets()
        self.msg_read = [0 for i in range(0, len(ports) + 1)]
        self.listen = [True for i in range(0, len(ports) + 1)]
        self.locks = [threading.Lock() for i in range(0, len(ports))]
        self.connect_locks = [threading.Lock() for i in range(0, len(ports))]

        self.insert_to_server_ttl()
        self.num_of_all_msg = 0
        self.num_of_msg_last_turn = 0
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
        sys.exit(0)

    def prepare_sockets(self):
        sockets = []
        conn_info = []
        for port in self.ports:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, bufferSize)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, bufferSize)
            sock.bind((self.ip, port))
            sockets.append(sock)
            conn_info.append(TCPConnection(port))
        return sockets, conn_info

    def create_msg_queue(self):
        return [None for i in range(Config.get_max_msg_num())]

    def add_to_msg_queue(self, msg):
        self.msg_queue[self.num_of_all_msg % Config.get_max_msg_num()] = msg
        self.num_of_all_msg += 1
        self.unlock_mutexes()

    def start_conn_threads(self, sockets):
        for it, socket in enumerate(sockets):
            thread = threading.Thread(
                target=self.listen_for_connections,
                args=(
                    socket,
                    it,
                ),
            )
            self.threads.append(thread)
            thread.start()
        for thread in self.threads:
            thread.join()

    def listen_for_connections(self, sock, num_of_thread):
        while self.listen[-1]:
            port_number = self.prepare_for_connection(sock, num_of_thread)
            try:
                conn, addr = sock.accept()
            except OSError:
                return
            with conn:
                check, error_response, data = self.connect_player(
                    conn, addr, num_of_thread
                )
                if check:
                    msg = json.loads(str(data, "utf-8"))
                    if not self.game_started:
                        self.conn_info[num_of_thread].fill_info(
                            msg, addr, num_of_thread
                        )
                        self.send_all_player_info(conn)
                    self.update_num_of_connections(1)
                    self.update_port_pool(port_number, if_remove=True)
                    self.unlock_mutexes()
                    if data != None:
                        self.send_new_player_info(num_of_thread)
                    self.handle_threads(conn, addr, num_of_thread)
                    self.disconnect_client(conn, addr, num_of_thread, port_number)
                elif error_response != None:
                    conn.sendall(TCPConnection.prepare_error_response(error_response))
                self.connect_locks[num_of_thread].release()

    def prepare_for_connection(self, sock, num_of_thread):
        self.listen[num_of_thread] = True
        self.connect_locks[num_of_thread].acquire()
        sock.listen()
        return sock.getsockname()[1]

    def connect_player(self, conn, addr, num_of_thread):
        if not self.game_started:
            conn.sendall(str.encode("Server says hi"))
            data = conn.recv(bufferSize)
            check, error_response = self.authorise(data, addr)
            return check, error_response, data
        data = conn.recv(bufferSize)
        check, error_response = self.check_reconnect(data, addr, num_of_thread)
        return check, error_response, data

    def handle_threads(self, conn, addr, num_of_thread):
        receiver_thread = threading.Thread(
            target=self.listen_for_data,
            args=(
                conn,
                self.conn_info[num_of_thread],
                addr,
                num_of_thread,
            ),
        )
        sender_thread = threading.Thread(
            target=self.send_data,
            args=(
                conn,
                num_of_thread,
            ),
        )
        receiver_thread.start()
        sender_thread.start()
        receiver_thread.join()
        sender_thread.join()

    def send_new_player_info(self, num_of_thread):
        self.msg_queue[self.num_of_all_msg % Config.get_max_msg_num()] = self.conn_info[
            num_of_thread
        ].response_with_info()
        self.num_of_all_msg += 1

    def send_all_player_info(self, conn):
        for info in self.conn_info:
            conn.sendall(str.encode(json.dumps(info.response_with_info()) + "\n"))

    def listen_for_data(self, conn, cnn_info, addr, num_of_thread):
        while self.listen[num_of_thread]:
            do_read = False
            try:
                r, _, _ = select.select([conn], [], [], timeout)
                do_read = bool(r)
                if do_read:
                    data = self.recive_large(conn, b"")
                    self.update_server_ttl()
                    msg = TCPConnection.collect_message(data)
                    if msg != "":
                        if self.game_started:
                            self.handle_ingame_commands(num_of_thread, msg)
                        else:
                            self.handle_lobby_messages(num_of_thread, msg, addr)
            except socket.error:
                self.handle_sock_error(num_of_thread)
                return

    def handle_ingame_commands(self, num_of_thread, msg):
        if msg.get("command") == 1:
            self.current_move += 1
            self.num_of_msg_last_turn = self.num_of_all_msg
            if self.current_move >= self.game_lenght * self.num_of_players:
                msg = self.modify_ext_turn_msg(num_of_thread, msg, 2)
            else:
                msg = self.modify_ext_turn_msg(num_of_thread, msg, 1)
                self.game_state = deepcopy(msg)
                msg["gameState"] = ""
        self.add_to_msg_queue(msg)

    def handle_lobby_messages(self, num_of_thread, msg, addr):
        print(msg)
        self.add_to_msg_queue(msg)
        self.conn_info[num_of_thread].fill_info(msg, addr, num_of_thread)
        if self.conn_info[num_of_thread].client_status == ClientStatusType.INGAGME:
            self.game_started = True
            self.add_to_msg_queue(
                self.build_ext_turn_msg(self.conn_info[num_of_thread].client_id)
            )

    def handle_sock_error(self, num_of_thread):
        self.listen[num_of_thread] = False
        if not self.game_started:
            self.conn_info[num_of_thread].clear_info()
        self.add_to_msg_queue(self.conn_info[num_of_thread].response_with_info())

    def send_data(self, conn, num_of_thread):
        self.prepare_for_sending_data(conn, num_of_thread)
        while self.listen[num_of_thread]:
            self.locks[num_of_thread].acquire()
            current = self.num_of_all_msg % Config.get_max_msg_num()
            diff = self.num_of_all_msg - self.msg_read[num_of_thread]
            if diff > Config.get_max_msg_num():
                self.listen[num_of_thread] = False
                return
            if diff > 0 and self.listen[num_of_thread]:
                self.send_all_msgs(current, diff, conn, num_of_thread)

    def prepare_for_sending_data(self, conn, num_of_thread):
        if not self.game_started:
            self.msg_read[num_of_thread] = self.num_of_all_msg
        else:
            conn.sendall(TCPConnection.prepare_message(self.game_state))
            self.msg_read[num_of_thread] = self.num_of_msg_last_turn + 1

    def send_all_msgs(self, current, diff, conn, num_of_thread):
        index = (current - diff) % Config.get_max_msg_num()
        for i in range(0, diff):
            conn.sendall(TCPConnection.prepare_message(self.msg_queue[index]))
            self.msg_read[num_of_thread] += 1
            index += 1
            index %= Config.get_max_msg_num()

    def recive_large(self, conn, data):
        new_data = conn.recv(bufferSize)
        data_str = str(new_data, "utf-8")
        if len(new_data) == 0:
            raise socket.error
        while "\n" not in data_str:
            data += new_data
            new_data = conn.recv(bufferSize)
            data_str = str(new_data, "utf-8")
            if len(new_data) == 0:
                raise socket.error
        return data + new_data

    def check_reconnect(self, data, addr, thread_num):
        try:
            message = json.loads(str(data, "utf-8"))
            if (
                message["playerInfo"]["secretId"]
                != self.conn_info[thread_num].secret_id
            ):
                return False, ResponseType.BADPLAYERDATA
        except KeyError:
            return False, ResponseType.BADCONNECTION
        except json.decoder.JSONDecodeError:
            return False, ResponseType.BADCONNECTION
        print(f"{os.getpid()}: connected by {addr}")
        self.conn_info[thread_num].client_status = ClientStatusType.INGAGME
        return True, None

    def disconnect_client(self, conn, addr, num, port):
        print(f"Disconnected {addr}")
        self.update_num_of_connections(-1)
        self.update_port_pool(port, if_remove=False)
        self.conn_info[num].client_status = ClientStatusType.NOTCONNECTED
        if not self.game_started:
            self.conn_info[num].clear_info()
            self.conn_info[num].clear_id()
        conn.close()

    def build_ext_turn_msg(self, id):
        msg = {}
        msg["networkId"] = id
        msg["command"] = 1
        msg["args"] = ["0"]
        msg["gameState"] = ""
        return msg

    def modify_ext_turn_msg(self, num_of_thread, msg, command):
        new_msg = {}
        conn_number = (num_of_thread + 1) % (self.num_of_players)
        print()
        if self.conn_info[conn_number].client_status != ClientStatusType.NOTCONNECTED:
            new_msg["networkId"] = self.conn_info[conn_number].client_id
        else:
            new_msg = self.modify_ext_turn_msg(num_of_thread + 1, msg, 1)
        new_msg["command"] = command
        new_msg["args"] = msg["args"]
        new_msg["gameState"] = msg["gameState"]
        return new_msg

    def authorise(self, data, addr):
        try:
            message = json.loads(str(data, "utf-8"))
            if message["password"] != self.password:
                return False, ResponseType.WRONGPASSWORD
            if (
                message["playerInfo"]["id"].strip() == ""
                or message["playerInfo"]["name"].strip() == ""
            ):
                return False, ResponseType.BADPLAYERDATA
        except KeyError:
            return False, ResponseType.BADCONNECTION
        except json.decoder.JSONDecodeError:
            return False, ResponseType.BADCONNECTION
        print(f"{os.getpid()}: connected by {addr}")
        return True, None

    def insert_to_server_ttl(self):
        data = {}
        data["pid"] = os.getpid()
        data["last_msg"] = time.time()
        self.database.save_to_collection(data, Config.get_ttl_collection())

    def update_num_of_connections(self, val):
        self.connections += val
        self.database.modify_data(
            Config.get_server_collection(),
            {"pid": os.getpid()},
            {"$set": {"connections": self.connections}},
        )

    def update_port_pool(self, val, if_remove):
        if if_remove:
            self.ports.remove(val)
        else:
            self.ports.append(val)
        self.database.modify_data(
            Config.get_server_collection(),
            {"pid": os.getpid()},
            {"$set": {"ports": self.ports}},
        )

    def update_server_ttl(self):
        self.database.modify_data(
            Config.get_ttl_collection(),
            {"pid": os.getpid()},
            {"$set": {"last_msg": time.time()}},
        )

    def unlock_mutexes(self):
        for lock in self.locks:
            if lock.locked():
                lock.release()
