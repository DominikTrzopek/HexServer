import os

class TCPServerCreator():
    
    def __init__(self, message, port):
        raw_args = self.parse_arguments(message, port)
        self.id = raw_args[0]
        self.password = raw_args[1]
        self.port_pool = raw_args[2]
        self.script_name = "TCPServer.py"

    def parse_arguments(self, message, port):
        id = message["serverInfo"]["creatorId"]
        num_of_players = message["serverInfo"]["numberOfPlayers"]
        password = message["serverInfo"]["password"]
        port_pool = [port for port in range(port, port + num_of_players)]
        return id, password, port_pool

    def start_TCP_server(self):
        args = " " + str(self.id) + " " + self.password
        for port in self.port_pool:
            args = args + " " + str(port)
        os.system("python3 " + self.script_name + args)