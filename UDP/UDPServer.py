import json
import socket
import sys
from CommunicationCodes import RequestType
from CommunicationCodes import ResponseType
from UDP.TCPServerCreator import TCPServerCreator
from Mongo.DBHandler import DBHandler
from Mongo.DBHandler import Config
from Encryption import hash, id_len
from Daemon.Cleaner import Cleaner


bufferSize = 8192


class UDPServer():

    def __init__(self, port):
        self.port = port
        self.ip = self.get_ip_address()
        self.database = DBHandler()
        self.database.clear_collection(Config.get_server_collection())
        self.start_server()

    def get_ip_address(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        # Check local IP
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]

    def start_server(self):
        # Create a datagram socket
        UDPSocket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)

        # Bind to address and ip
        print("UDP server up and listening " + self.ip + ":" + str(self.port))
        UDPSocket.bind((self.ip, self.port))

        # Listen for incoming datagrams
        while (True):
            # Receive request from client
            message, address = self.recive_request(UDPSocket)

            # Client logs
            clientMsg = "Message from Client:{}".format(message)
            clientIP = "Client IP Address:{}".format(address)
            print(clientMsg)
            print(clientIP)

            # Handle request and send response
            if message.get("requestType") == RequestType.CREATE:
                self.handle_create_request(message.get("serverInfo"), UDPSocket, address)
            elif message.get("requestType") == RequestType.GET:
                self.handle_get_request(UDPSocket, address)
            elif message.get("requestType") == RequestType.DELETE:
                self.handle_delete_request(message, UDPSocket, address)
            else:
                response = self.prepare_response(None, ResponseType.BADREQUEST)
                self.send_response(UDPSocket, address, response)

    def handle_create_request(self, server_info, UDPSocket, address):
        try:
            # Fill server ip
            server_info["ip"] = self.ip

            # Create TCPServer as subproces
            port_pool, pid = self.create_TCPserver(server_info)

            # Fill TCP server ports
            server_info["pid"] = pid
            server_info["ports"] = port_pool

            # Hash sensitive data
            if server_info["password"] != None and server_info["password"].strip() != "":
                server_info["password"] = hash(server_info["password"])
            server_info["creatorId"] = hash(server_info["creatorId"])

            # Send response and save to db
            response = self.prepare_response(server_info, ResponseType.SUCCESS)
            self.send_response(UDPSocket, address, response)
            self.database.save_to_collection(server_info, Config.get_server_collection())
    
        # Handle errors
        except KeyError:
            response = self.prepare_response(None, ResponseType.BADARGUMENTS)
            self.send_response(UDPSocket, address, response)
        except ChildProcessError:
            response = self.prepare_response(None, ResponseType.TCPSERVERFAIL)
            self.send_response(UDPSocket, address, response)

    def handle_get_request(self, UDPSocket, address):
        # Get from db
        servers = self.database.get_all_from_collection(Config.get_server_collection())
        for server in servers:
            # For each found server send separete message
            response = self.prepare_response(server, ResponseType.SUCCESS)
            self.send_response(UDPSocket, address, response)
        # Notify client that all data was sent
        response = self.prepare_response(None, ResponseType.ENDOFMESSAGE)
        self.send_response(UDPSocket, address, response)

    def handle_delete_request(self, msg, UDPSocket, address):
        try:
            pid = msg["serverId"]
            id = msg["playerid"]
            server = self.database.get_one_from_collection(Config.get_server_collection(), {"pid" : pid})
            if server != None and server["creatorId"] == hash(id):
                Cleaner(pid).do_cleanup()
                response = self.prepare_response(None, ResponseType.SUCCESS)
                self.send_response(UDPSocket, address, response)
            else:
                response = self.prepare_response(None, ResponseType.BADREQUEST)
                self.send_response(UDPSocket, address, response)
        except KeyError:
            response = self.prepare_response(None, ResponseType.BADARGUMENTS)
            self.send_response(UDPSocket, address, response)

    def recive_request(self, socket):
        try:
            bytesAddressPair = socket.recvfrom(bufferSize)
            message = json.loads(str(bytesAddressPair[0], 'utf-8'))
        except ValueError:
            message = {}
        address = bytesAddressPair[1]
        return (message, address)

    def send_response(self, socket, address, message):
        bytesToSend = str.encode(json.dumps(message))
        socket.sendto(bytesToSend, address)
        print("Server send: " + format(message))

    def prepare_response(self, server_info, responseCode):
        if server_info != None:
            if server_info["password"] != None and server_info["password"].strip() != "":
                server_info["password"] = "##"
        response = {}
        response["responseType"] = responseCode
        response["serverInfo"] = server_info
        return response

    def create_TCPserver(self, server_info):
        print("Starting TCP server")
        creator = TCPServerCreator(server_info, self.port + 1)
        pid = creator.start_TCP_server()
        self.port = creator.port_pool[-1]
        return creator.port_pool, pid


if __name__ == "__main__":
    if len(sys.argv) == 2:
        UDPServer(int(sys.argv[1]))
    else:
        print("Invocation: " + sys.argv[0] + " <PORT>")
