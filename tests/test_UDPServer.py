import unittest
import unittest.mock
from unittest.mock import patch
import subprocess
import socket
import time 
from CommunicationCodes import ResponseType

bufferSize = 1024

class TestUDPServer(unittest.TestCase):

    @classmethod
    def getIpAddress(cls):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip


    @classmethod
    def setUpClass(cls):
        cls.UDP_IP = cls.getIpAddress()
        cls.UDP_PORT = 9999
        cls.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) 
        cls.process = subprocess.Popen(["python3", "UDPServer.py", str(cls.UDP_PORT)])
        time.sleep(2)


    @classmethod
    def tearDownClass(cls):
        cls.process.kill()
        cls.process.wait()
        cls.sock.close()


    def test_create_missingRequestType(cls):
        cls.sock.connect((cls.UDP_IP,cls.UDP_PORT))
        cls.sock.send(bytes('{"responseType": 0, "serverInfo": {"creatorId": 1, "password": "pass", "numberOfPlayers": 3, "numberOfTurns": 3, "seed": 1, "mapType": 5, "ip": "192.168.0.219", "ports": [8051, 8052, 8053]}}', "utf-8"))
        response = cls.sock.recv(bufferSize).decode("utf-8")
        assert ('"responseType": ' + str(ResponseType.BADREQUEST.value)) in response


    def test_create_correctRequest(cls):
        cls.sock.connect((cls.UDP_IP,cls.UDP_PORT))
        cls.sock.send(bytes('{"requestType": 1, "serverInfo": {"creatorId": 1, "password": "pass", "numberOfPlayers": 3, "numberOfTurns": 3, "seed": 1, "mapType": 5, "ip": "", "ports": []}}', "utf-8"))
        response = cls.sock.recv(bufferSize).decode("utf-8")
        assert ('"responseType": ' + str(ResponseType.SUCCESS.value)) in response



if __name__ == '__main__':
    unittest.main()