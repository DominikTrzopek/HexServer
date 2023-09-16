import json
import socket
import os
import threading
import time
import signal
import sys
import select
import logging
from Mongo.DBHandler import DBHandler
from Mongo.DBHandler import Config
from TCP.TCPConnection import TCPConnection
from socket import SHUT_RDWR 
from CommunicationCodes import ResponseType
from CommunicationCodes import ClientStatusType
from copy import deepcopy

bufferSize = 8196
timeout = 2


class ColoredFormatter(logging.Formatter):
    COLORS = {
        "DEBUG": "\033[94m",  # Blue
        "INFO": "\033[92m",  # Green
        "WARNING": "\033[93m",  # Yellow
        "ERROR": "\033[91m",  # Red
        "CRITICAL": "\033[95m",  # Purple
        "RESET": "\033[0m",  # Reset color
    }

    def format(self, record):
        log_message = super(ColoredFormatter, self).format(record)
        log_message = (
            self.COLORS.get(record.levelname, "") + log_message + self.COLORS["RESET"]
        )
        return log_message


# Logic flow
# 1. Init server variables
# 2. Create TCP socket
# 3. Listen for connections:
#    - listen
#    - notify connection attempt
#    - accept
# 4. Attempt to connect player:
#    - send hello msg
#    - receive rsp with password
#    - check password
#    - connect or decline
# 4. Save and send player info to other users
# 5.


class TCPServer:
    def __init__(self, ip, id, password, ports, game_length):
        # TODO make logger properly
        self.logger = logging.getLogger("my_logger")
        self.logger.setLevel(logging.DEBUG)

        handler = logging.StreamHandler()
        formatter = ColoredFormatter(fmt="%(levelname)s: %(message)s")
        handler.setFormatter(formatter)

        self.logger.addHandler(handler)
        # TODO this is temporary
        port = ports[0]
        self.num_of_players = len(ports)
        # end TODO
        self.creator_id = id
        self.password = password
        # TODO uncomment
        # self.num_of_players = num_of_players
        self.game_length = game_length

        self.database = DBHandler()
        self.threads = []
        self.num_of_connections = 0
        self.game_state = None

        self.game_started = False
        self.current_move = 0

        self.socket = self.prepare_socket(ip, port)
        self.conn_info = [TCPConnection(port) for i in range(0, self.num_of_players)]

        self.msg_read = [0 for i in range(0, self.num_of_players + 1)]
        self.connections_ids = [False for i in range(0, self.num_of_players + 1)]
        self.locks = [threading.Lock() for i in range(0, self.num_of_players)]
        #   self.connect_locks = [threading.Lock() for i in range(0, num_of_players)]

        self.insert_to_server_ttl()
        self.num_of_all_msg = 0
        self.num_of_msg_last_turn = 0
        self.msg_queue = self.create_msg_queue()

        signal.signal(signal.SIGINT, self.signal_handler)
        self.connected_ports = self.listen_for_connections(self.num_of_players)

    def signal_handler(self, _signo, _stack_frame):
        self.connections_ids = [False for i in self.connections_ids]
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

    def prepare_socket(self, ip, port):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, bufferSize)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, bufferSize)
        sock.bind((ip, port))
        return sock

    def create_msg_queue(self):
        return [None for i in range(Config.get_max_msg_num())]

    def add_to_msg_queue(self, msg):
        self.msg_queue[self.num_of_all_msg % Config.get_max_msg_num()] = msg
        self.num_of_all_msg += 1
        self.unlock_mutexes()

    def listen_for_connections(self, max_players):
        self.socket.listen(max_players)
        while self.num_of_connections < max_players:
            try:
                self.logger.debug(
                    "TCP " + str(os.getpid()) + ": socket listening for connections"
                )
                connection_idx = self.prepare_for_connection()
                conn, addr = self.socket.accept()
            except (OSError, ConnectionRefusedError):
                self.logger.warning(
                    str(
                        "TCP "
                        + str(os.getpid())
                        + ": connection refused -> all slots taken"
                    )
                )
                continue
            check, error_response, data = self.connect_player(
                conn, addr, connection_idx
            )
            if check:
                self.logger.debug(
                    "TCP "
                    + str(os.getpid())
                    + ": client accepted -> "
                    + str(addr)
                    + " on slot "
                    + str(connection_idx)
                )
                msg = json.loads(str(data, "utf-8"))
                if not self.game_started:
                    self.conn_info[connection_idx].fill_info(msg, addr, connection_idx)
                    self.send_all_player_info(conn)
                self.update_num_of_connections(1)
                self.unlock_mutexes()
                if data != None:
                    self.send_new_player_info(connection_idx)
                self.handle_threads(conn, addr, connection_idx)
            else:
                conn.sendall(TCPConnection.prepare_error_response(error_response))
                self.disconnect_client(conn, addr, connection_idx)

    def prepare_for_connection(self):
        connection_idx = self.find_free_connection_idx()
        self.connections_ids[connection_idx] = True
        return connection_idx

    def find_free_connection_idx(self):
        for idx, val in enumerate(self.connections_ids):
            if val == False:
                self.connections_ids[idx] = True
                return idx
        raise ConnectionRefusedError

    def connect_player(self, conn, addr, connection_idx):
        if not self.game_started:
            conn.sendall(str.encode("Server says hi"))
            data = conn.recv(bufferSize)
            check, error_response = self.authorize(data, addr)
            return check, error_response, data
        data = conn.recv(bufferSize)
        check, error_response = self.check_reconnect(data, addr, connection_idx)
        return check, error_response, data

    def handle_threads(self, conn, addr, connection_idx):
        self.logger.debug(str(conn))
        receiver_thread = threading.Thread(
            target=self.listen_for_data,
            args=(
                conn,
                self.conn_info[connection_idx],
                addr,
                connection_idx,
            ),
        )
        sender_thread = threading.Thread(
            target=self.send_data,
            args=(
                conn,
                connection_idx,
            ),
        )
        receiver_thread.start()
        self.threads.append(receiver_thread)
        sender_thread.start()
        self.threads.append(sender_thread)
        # TODO threads needs to be joined

    # receiver_thread.join()
    # sender_thread.join()

    def send_new_player_info(self, connection_idx):
        self.msg_queue[self.num_of_all_msg % Config.get_max_msg_num()] = self.conn_info[
            connection_idx
        ].response_with_info()
        self.num_of_all_msg += 1

    def send_all_player_info(self, conn):
        for info in self.conn_info:
            conn.sendall(str.encode(json.dumps(info.response_with_info()) + "\n"))

    def listen_for_data(self, conn, cnn_info, addr, connection_idx):
        self.logger.debug(
            "TCP "
            + str(os.getpid())
            + ": listener thread started for slot "
            + str(connection_idx)
        )
        while self.connections_ids[connection_idx]:
            self.logger.warning(
                "TCP " + str(os.getpid()) + ": listening " + str(connection_idx)
            )
            do_read = False
            try:
                r, _, _ = select.select([conn], [], [], timeout)
                do_read = bool(r)
                if do_read:
                    data = self.receive_large(conn, b"")
                    self.update_server_ttl()
                    msg = TCPConnection.collect_message(data)
                    if msg != "":
                        if self.game_started:
                            self.handle_ingame_commands(connection_idx, msg)
                        else:
                            self.handle_lobby_messages(connection_idx, msg, addr)
            except socket.error as err:
                self.logger.error(
                    "TCP "
                    + str(os.getpid())
                    + ": listener thread error on slot "
                    + str(connection_idx)
                    + " -> "
                    + str(err)
                    + " "
                    + str(conn)
                )
                self.handle_sock_error(connection_idx)
                return

    def handle_ingame_commands(self, connection_idx, msg):
        if msg.get("command") == 1:
            self.current_move += 1
            self.num_of_msg_last_turn = self.num_of_all_msg
            if self.current_move >= self.game_length * self.num_of_players:
                msg = self.modify_ext_turn_msg(connection_idx, msg, 2)
            else:
                msg = self.modify_ext_turn_msg(connection_idx, msg, 1)
                self.game_state = deepcopy(msg)
                msg["gameState"] = ""
        self.add_to_msg_queue(msg)

    def handle_lobby_messages(self, connection_idx, msg, addr):
        print(msg)
        self.add_to_msg_queue(msg)
        self.conn_info[connection_idx].fill_info(msg, addr, connection_idx)
        if self.conn_info[connection_idx].client_status == ClientStatusType.INGAGME:
            self.game_started = True
            self.add_to_msg_queue(
                self.build_ext_turn_msg(self.conn_info[connection_idx].client_id)
            )

    def handle_sock_error(self, connection_idx):
        self.connections_ids[connection_idx] = False
        if not self.game_started:
            self.conn_info[connection_idx].clear_info()
        self.add_to_msg_queue(self.conn_info[connection_idx].response_with_info())

    def send_data(self, conn, connection_idx):
        self.logger.debug(
            "TCP "
            + str(os.getpid())
            + ": sender thread started for slot"
            + str(connection_idx)
        )
        self.prepare_for_sending_data(conn, connection_idx)
        while self.connections_ids[connection_idx]:
            self.locks[connection_idx].acquire()
            current = self.num_of_all_msg % Config.get_max_msg_num()
            diff = self.num_of_all_msg - self.msg_read[connection_idx]
            if diff > Config.get_max_msg_num():
                self.connections_ids[connection_idx] = False
                return
            if diff > 0 and self.connections_ids[connection_idx]:
                self.send_all_msgs(current, diff, conn, connection_idx)

    def prepare_for_sending_data(self, conn, connection_idx):
        if not self.game_started:
            self.msg_read[connection_idx] = self.num_of_all_msg
        else:
            conn.sendall(TCPConnection.prepare_message(self.game_state))
            self.msg_read[connection_idx] = self.num_of_msg_last_turn + 1

    def send_all_msgs(self, current, diff, conn, connection_idx):
        index = (current - diff) % Config.get_max_msg_num()
        for i in range(0, diff):
            conn.sendall(TCPConnection.prepare_message(self.msg_queue[index]))
            self.msg_read[connection_idx] += 1
            index += 1
            index %= Config.get_max_msg_num()

    def receive_large(self, conn, data):
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

    def disconnect_client(self, conn, addr, connection_idx):
        self.logger.warning(
            "TCP " + str(os.getpid()) + ": disconnecting client " + str(addr)
        )
        self.update_num_of_connections(-1)
        self.connections_ids[connection_idx] = False
        self.conn_info[connection_idx].client_status = ClientStatusType.NOTCONNECTED
        if not self.game_started:
            self.conn_info[connection_idx].clear_info()
            self.conn_info[connection_idx].clear_id()
        conn.close()

    def build_ext_turn_msg(self, id):
        msg = {}
        msg["networkId"] = id
        msg["command"] = 1
        msg["args"] = ["0"]
        msg["gameState"] = ""
        return msg

    def modify_ext_turn_msg(self, connection_idx, msg, command):
        new_msg = {}
        conn_number = (connection_idx + 1) % (self.num_of_players)
        print()
        if self.conn_info[conn_number].client_status != ClientStatusType.NOTCONNECTED:
            new_msg["networkId"] = self.conn_info[conn_number].client_id
        else:
            new_msg = self.modify_ext_turn_msg(connection_idx + 1, msg, 1)
        new_msg["command"] = command
        new_msg["args"] = msg["args"]
        new_msg["gameState"] = msg["gameState"]
        return new_msg

    def authorize(self, data, addr):
        try:
            message = json.loads(str(data, "utf-8"))
            if message["password"] != self.password:
                return False, ResponseType.WRONGPASSWORD
            if (
                message["playerInfo"]["id"].strip() == ""
                or message["playerInfo"]["name"].strip() == ""
            ):
                return False, ResponseType.BADPLAYERDATA
        except (KeyError, json.decoder.JSONDecodeError):
            return False, ResponseType.BADCONNECTION
        print(f"{os.getpid()}: connected by {addr}")
        return True, None

    def insert_to_server_ttl(self):
        data = {}
        data["pid"] = os.getpid()
        data["last_msg"] = time.time()
        self.database.save_to_collection(data, Config.get_ttl_collection())

    def update_num_of_connections(self, val):
        self.num_of_connections += val
        # TODO this is temporary as game still wants multilple ports
        # self.database.modify_data(
        #     Config.get_server_collection(),
        #     {"pid": os.getpid()},
        #     {"$set": {"connections": self.num_of_connections}},
        # )

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
