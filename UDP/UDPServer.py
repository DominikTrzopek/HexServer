import json
import socket
import sys
from CommunicationCodes import RequestType
from CommunicationCodes import ResponseType
from UDP.TCPServerCreator import TCPServerCreator
from Mongo.DBHandler import DBHandler
from Mongo.DBHandler import Config


bufferSize = 1024


class UDPServer():

    def __init__(self, port):
        self.port = port
        self.ip = self.get_ip_address()
        self.database = DBHandler()
        self.database.clear_collection(Config.get_server_collection())
        self.startServer()

    def get_ip_address(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        # Check local IP
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]

    def startServer(self):
        # Create a datagram socket
        UDPSocket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)

        # Bind to address and ip
        print("UDP server up and listening " + self.ip + ":" + str(self.port))
        UDPSocket.bind((self.ip, self.port))

        # Listen for incoming datagrams
        while (True):
            # Receive request from client
            message, address = self.reciveRequest(UDPSocket)

            # Client logs
            clientMsg = "Message from Client:{}".format(message)
            clientIP = "Client IP Address:{}".format(address)
            print(clientMsg)
            print(clientIP)

            # Handle request and send response
            if message.get("requestType") == RequestType.CREATE:
                self.handle_create_request(message, UDPSocket, address)
            elif message.get("requestType") == RequestType.GET:
                self.handle_get_request(UDPSocket, address)
            else:
                response = self.prepareResponse(None, ResponseType.BADREQUEST)
                self.sendResponse(UDPSocket, address, response)

    def handle_create_request(self, message, UDPSocket, address):
        try:
            # Create TCPServer as subproces
            port_pool = self.createTCPServer(message)

            # Fill TCP server ip and ports
            message["serverInfo"]["ip"] = self.ip
            message["serverInfo"]["ports"] = port_pool

            # Send response and save to db
            response = self.prepareResponse(message["serverInfo"], ResponseType.SUCCESS)
            self.sendResponse(UDPSocket, address, response)
            self.database.save_to_collection(message["serverInfo"], Config.get_server_collection())
    
        # Handle errors
        except KeyError:
            response = self.prepareResponse(None, ResponseType.BADARGUMENTS)
            self.sendResponse(UDPSocket, address, response)
        except ChildProcessError:
            response = self.prepareResponse(None, ResponseType.TCPSERVERFAIL)
            self.sendResponse(UDPSocket, address, response)

    def handle_get_request(self, UDPSocket, address):
        # Get from db
        servers = self.database.get_all_from_collection(Config.get_server_collection())
        for server in servers:
            # For each found server send separete message
            response = self.prepareResponse(server, ResponseType.SUCCESS)
            self.sendResponse(UDPSocket, address, response)
    
        # Notify client that all data was sent
        response = self.prepareResponse(None, ResponseType.ENDOFMESSAGE)
        self.sendResponse(UDPSocket, address, response)

    def reciveRequest(self, socket):
        try:
            bytesAddressPair = socket.recvfrom(bufferSize)
            message = json.loads(str(bytesAddressPair[0], 'utf-8'))
        except ValueError:
            message = {}
        address = bytesAddressPair[1]
        return (message, address)

    def sendResponse(self, socket, address, message):
        bytesToSend = str.encode(json.dumps(message))
        socket.sendto(bytesToSend, address)
        print("Server send: " + format(message))

    def prepareResponse(self, server_info, responseCode):
        response = {}
        response["responseType"] = responseCode
        response["serverInfo"] = server_info
        return response

    def createTCPServer(self, message):
        print("Starting TCP server")
        creator = TCPServerCreator(message, self.port)
        creator.start_TCP_server()
        self.port += message["serverInfo"]["numberOfPlayers"]
        return creator.port_pool


if __name__ == "__main__":
    if len(sys.argv) == 2:
        UDPServer(int(sys.argv[1]))
    else:
        print("Invocation: " + sys.argv[0] + " <PORT>")
