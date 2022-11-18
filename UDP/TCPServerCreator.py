import subprocess
import socket

tcp_script = "TCP.TCPStarter"


class TCPServerCreator():

    def __init__(self, message, port):
        self.ip, self.id, self.password, self.port_pool = self.parse_arguments(
            message, port)
        self.script_name = tcp_script

    def parse_arguments(self, server_info, port):
        ip = server_info["ip"]
        id = server_info["creatorId"]
        num_of_players = server_info["numberOfPlayers"]
        password = server_info["password"]
        port_pool = self.get_ports(num_of_players, port, ip)
        return ip, id, password, port_pool

    def get_ports(self, lenght, port, ip):
        port_pool = []
        while (len(port_pool) < lenght):
            if (not self.is_port_in_use(port, ip)):
                port_pool.append(port)
            port += 1
        return port_pool

    def is_port_in_use(self, port, ip) -> bool:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind((ip, port))
            except socket.error:
                return True
            return False

    def start_TCP_server(self):
        try:
            return subprocess.Popen(
                ["python3", "-m", self.script_name, self.id, self.password, self.ip, str(self.port_pool)]).pid
        except Exception:
            raise ChildProcessError
