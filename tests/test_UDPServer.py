import unittest
import subprocess
import socket
import time
from CommunicationCodes import ResponseType
import os
import signal


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
        cls.UDP_PORT = 9900
        cls.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        cls.process = subprocess.Popen(
            ["python3", "-m", "StartServer", str(cls.UDP_PORT), "no_logs"],
            preexec_fn=os.setsid,
        )
        time.sleep(2)  # wait for server to start

    @classmethod
    def tearDownClass(cls):
        cls.sock.close()
        os.killpg(os.getpgid(cls.process.pid), signal.SIGTERM)

    def test_create_missingRequestType(cls):
        cls.sock.connect((cls.UDP_IP, cls.UDP_PORT))
        cls.sock.send(
            bytes(
                '{"responseType": 0, "serverInfo": {"creatorId": 1, "password": "pass", "numberOfPlayers": 3, "numberOfTurns": 3, "seed": 1, "mapType": 5, "ip": "192.168.0.219", "ports": [8051, 8052, 8053]}}',
                "utf-8",
            )
        )
        response = cls.sock.recv(bufferSize).decode("utf-8")
        assert ('"responseType": ' + str(ResponseType.BADREQUEST.value)) in response

    def test_create_correctRequest(cls):
        cls.sock.connect((cls.UDP_IP, cls.UDP_PORT))
        cls.sock.send(
            bytes(
                '{"requestType": 1, "serverInfo": {"creatorId": "86852d82-e20a-4949-a6fc-44d85108614d", "serverName": "", "password": "", "numberOfPlayers": 2, "numberOfTurns": 15, "seed": 3423, "mapType": "plains", "mapSize": 24, "customMap": "", "ip": "", "ports": [], "connections": 0, "pid": 0}}',
                "utf-8",
            )
        )
        response = cls.sock.recv(bufferSize).decode("utf-8")
        assert ('"responseType": ' + str(ResponseType.SUCCESS.value)) in response

    def test_create_correctRequest(cls):
        cls.sock.connect((cls.UDP_IP, cls.UDP_PORT))
        cls.sock.send(
            bytes(
                '{"requestType": 1, "serverInfo": {"creatorId": 1, "password": "pass", "numberOfPlayers": 3, "numberOfTurns": 3, "seed": 1, "mapType": 5, "ip": "", "ports": []}}',
                "utf-8",
            )
        )
        response = cls.sock.recv(bufferSize).decode("utf-8")
        assert ('"responseType": ' + str(ResponseType.TCPSERVERFAIL.value)) in response

    def test_create_badRequestType(cls):
        cls.sock.connect((cls.UDP_IP, cls.UDP_PORT))
        cls.sock.send(
            bytes(
                '{"requestType": 57, "serverInfo": {"creatorId": 1, "password": "pass", "numberOfPlayers": 3, "numberOfTurns": 3, "seed": 1, "mapType": 5, "ip": "", "ports": []}}',
                "utf-8",
            )
        )
        response = cls.sock.recv(bufferSize).decode("utf-8")
        assert ('"responseType": ' + str(ResponseType.BADREQUEST.value)) in response

    def test_create_badJson(cls):
        cls.sock.connect((cls.UDP_IP, cls.UDP_PORT))
        cls.sock.send(
            bytes('{"requestType": 1, "serverInfo": {"creatorId", ts": []}', "utf-8")
        )
        response = cls.sock.recv(bufferSize).decode("utf-8")
        assert ('"responseType": ' + str(ResponseType.BADREQUEST.value)) in response

    def test_create_missingServerInfo(cls):
        cls.sock.connect((cls.UDP_IP, cls.UDP_PORT))
        cls.sock.send(bytes('{"requestType": 1 }', "utf-8"))
        response = cls.sock.recv(bufferSize).decode("utf-8")
        assert ('"responseType": ' + str(ResponseType.BADARGUMENTS.value)) in response

    def test_create_badTCPCreatorArguments(cls):
        cls.sock.connect((cls.UDP_IP, cls.UDP_PORT))
        cls.sock.send(
            bytes(
                '{"requestType": 1, "serverInfo": {"creatorId": 1, "password": 123, "numberOfPlayers": 3, "numberOfTurns": 3, "seed": 1, "mapType": 5, "ports": []}}',
                "utf-8",
            )
        )
        response = cls.sock.recv(bufferSize).decode("utf-8")
        assert ('"responseType": ' + str(ResponseType.TCPSERVERFAIL.value)) in response

    def test_get_correctRequest(cls):
        cls.sock.connect((cls.UDP_IP, cls.UDP_PORT))
        cls.sock.send(bytes('{"id": 1, "requestType": 0}', "utf-8"))
        response = cls.sock.recv(bufferSize).decode("utf-8")
        correct_codes = [
            str(ResponseType.SUCCESS.value),
            str(ResponseType.ENDOFMESSAGE.value),
        ]
        assert any(codes in response for codes in correct_codes)

    def test_get_badJson(cls):
        cls.sock.connect((cls.UDP_IP, cls.UDP_PORT))
        cls.sock.send(bytes('{"requestType" 0}', "utf-8"))
        response = cls.sock.recv(bufferSize).decode("utf-8")
        assert ('"responseType": ' + str(ResponseType.BADREQUEST.value)) in response


if __name__ == "__main__":
    unittest.main()
