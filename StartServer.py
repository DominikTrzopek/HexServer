from faulthandler import disable
from UDP.UDPServer import UDPServer
import sys
import os


def configure_printing(option):
    if option.lower() == "no_logs" or option.lower() == "f":
        block_print()


def block_print():
    sys.stdout = open(os.devnull, 'w')
    sys.stderr = sys.__stdout__


if __name__ == "__main__":
    if len(sys.argv) == 3:
        configure_printing(sys.argv[2])
    if len(sys.argv) >= 2:
        UDPServer(int(sys.argv[1]))
    else:
        print("Invocation: " + sys.argv[0] + " <PORT> <(OPTIONAL) BLOCK LOGS>")
