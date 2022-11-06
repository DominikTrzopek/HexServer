import subprocess


class TCPServerCreator():

    def __init__(self, message, port):
        raw_args = self.parse_arguments(message, port)
        self.ip = raw_args[0]
        self.id = raw_args[1]
        self.password = raw_args[2]
        self.port_pool = raw_args[3]
        self.script_name = "TCP.TCPStarter"

    def parse_arguments(self, message, port):
        ip = message["serverInfo"]["ip"]
        id = message["serverInfo"]["creatorId"]
        num_of_players = message["serverInfo"]["numberOfPlayers"]
        password = message["serverInfo"]["password"]
        port_pool = [port for port in range(port, port + num_of_players)]
        return ip, id, password, port_pool

    def start_TCP_server(self):
        try:
            return subprocess.Popen(["python3", "-m", self.script_name, str(self.id), self.password, self.ip, str(self.port_pool)]).pid
        except Exception:
            raise ChildProcessError
