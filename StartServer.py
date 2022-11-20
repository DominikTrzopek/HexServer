from multiprocessing import Process
from UDP.UDPServer import UDPServer
from Demon.Worker import run
import sys
import os


def configure_printing(option):
    if option.lower() == "no_logs" or option.lower() == "f":
        block_print()


def block_print():
    sys.stdout = open(os.devnull, 'w')
    sys.stderr = sys.__stdout__

def start_daemon():
    daemon = Process(target=run, daemon=True)
    daemon.start()

if __name__ == "__main__":
    if len(sys.argv) == 3:
        configure_printing(sys.argv[2])
    if len(sys.argv) >= 2:
        start_daemon()
        UDPServer(int(sys.argv[1]))
    else:
        print("Invocation: " + sys.argv[0] + " <PORT> <(OPTIONAL) BLOCK LOGS>")

