
import pymongo
from pymongo import MongoClient
import json
import socket
import sys
from CommunicationCodes import RequestType
import TCPServerCreator

bufferSize  = 1024

client = pymongo.MongoClient("mongodb://root:pass@0.0.0.0:8081/")
db = client["server_list"]
collection = db["new"]
print(db.list_collection_names())
mydict = { "name": "John", "address": "Highway 37" }

x = collection.insert_one(mydict) 
print(x.inserted_id)

for x in collection.find():
  print(x)
msgFromServer       = "Hello UDP Client"

bytesToSend         = str.encode(msgFromServer)


def getIpAddress():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))
    return s.getsockname()[0]

def reciveRequest(socket):
    bytesAddressPair = socket.recvfrom(bufferSize)
    message = json.loads(str(bytesAddressPair[0], 'utf-8'))
    address = bytesAddressPair[1]
    return (message, address)

def appendToServerList(serverIp, serverPort, PID, message):
    f = open("serverList.txt", "a")
    f.write(serverIp + ":" + str(serverPort) + ":" + str(PID) + message + "\n");
    f.close()


def createTCPServer(id, num_of_players, password):

    TCPServerCreator()


# def startDedicatedServer(serverIp, serverPort):


def startServer(localPort):
    # Create a datagram socket
    UDPSocket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
    
    # Check local IP
    localIP = getIpAddress()
    
    # Bind to address and ip
    print("UDP server up and listening " + localIP + ":" + str(localPort))
    UDPSocket.bind((localIP, localPort))

    # Listen for incoming datagrams
    while(True):
        message, address = reciveRequest(UDPSocket)
        if message["requestType"] == RequestType.create:
            localPort += 1
            createTCPServer(message["serverInfo"]["id"],
                            message["serverInfo"]["numberOfPlayers"],
                            message["serverInfo"]["password"])
            appendToServerList(localIP, localPort, 111, message)
            # startDedicatedServer(localIP, localPort)
        #Logs
        clientMsg = "Message from Client:{}".format(message)
        clientIP  = "Client IP Address:{}".format(address)
        print(clientMsg)
        print(clientIP)

        # Sending a reply to client
        UDPSocket.sendto(bytesToSend, address)



if __name__ == "__main__":
    if len(sys.argv) == 2:
        startServer(int(sys.argv[1]))
    else:
        print("Invocation: " + sys.argv[0] + " <PORT>")