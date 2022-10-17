import collections
from typing import Collection
import pymongo
import json
import socket
import sys
from CommunicationCodes import RequestType
from CommunicationCodes import ResponseType
from TCPServerCreator import TCPServerCreator

bufferSize  = 1024
db_credentials = "mongodb://root:pass@0.0.0.0:8081/"
collection = "servers"

class UDPServer():

    def __init__(self, port):
        self.port = port
        self.ip = self.get_ip_address()
        self.database = self.connect_to_database("server_list")
        self.clear_db()
        self.startServer()


    def connect_to_database(self, name):
        client = pymongo.MongoClient(db_credentials)
        db = client[name]
        print("Connected to mongodb, db collections: ")
        print(db.list_collection_names())
        return db


    def get_db_collection(self, db, name):
        collection = db[name]
        return collection


    def save_to_db(self, server_info):
        coll = self.get_db_collection(self.database, collection)
        coll.insert_one(server_info) 


    def get_from_db(self):
        coll = self.get_db_collection(self.database, collection)
        servers = [info for info in coll.find({}, {'_id': False})]
        return servers

    def clear_db(self):
        coll = self.get_db_collection(self.database, collection)
        coll.drop()


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
        while(True):
            message, address = self.reciveRequest(UDPSocket)

            #Client logs
            clientMsg = "Message from Client:{}".format(message)
            clientIP  = "Client IP Address:{}".format(address)
            print(clientMsg)
            print(clientIP)

            #Create new TCP server
            if message.get("requestType") == RequestType.CREATE:
                port_pool = self.createTCPServer(message)
                message["serverInfo"]["ip"] = self.ip
                message["serverInfo"]["ports"] = port_pool
                response = self.prepareResponse(message["serverInfo"], ResponseType.SUCCESS)
                self.sendResponse(UDPSocket, address, response)
                self.save_to_db(message["serverInfo"])
            elif message.get("requestType") == RequestType.GET:
                servers = self.get_from_db()
                for server in servers:
                    response = self.prepareResponse(server, ResponseType.SUCCESS)
                    self.sendResponse(UDPSocket, address, response)
                response = self.prepareResponse(None, ResponseType.ENDOFMESSAGE)
                self.sendResponse(UDPSocket, address, response)
            else:
                response = self.prepareResponse(None, ResponseType.BADREQUEST)
                self.sendResponse(UDPSocket, address, response)
    


    def reciveRequest(self, socket):
        bytesAddressPair = socket.recvfrom(bufferSize)
        message = json.loads(str(bytesAddressPair[0], 'utf-8'))
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
