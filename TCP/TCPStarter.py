import os
import sys
from TCP.TCPServer import TCPServer

class ArgParser():

    def __init__(self, args):
        self.creator_id = args[1]
        self.server_password = args[2]
        self.server_ip = args[3]
        self.ports = self.port_parser(args[4])
        self.game_lenght = (int)(args[5])
        #self.print_args()
        self.start_TCP()

    def port_parser(self, ports):
        return [int(port) for port in ports.strip('][').split(', ')]

    def start_TCP(self):
        TCPServer(self.server_ip, self.creator_id, self.server_password, self.ports, self.game_lenght)
        
    def print_args(self):
        print("TCP server arguments:")
        print("IP: " + self.server_ip) 
        print("ID: " + self.creator_id) 
        print("PASS: " + self.server_password) 
        print("PORTS: " + str(self.ports))
        print("TURNS: " + str(self.game_lenght))


if __name__ == "__main__":
    if len(sys.argv) > 4:
        print("Child started: " + str(os.getpid()))
        ArgParser(sys.argv)
    else:
        print("Invocation: " + sys.argv[0] + "<IP> <ID> <PASS> <PORT> ")


