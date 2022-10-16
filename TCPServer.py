import json
import socket
import sys

if __name__ == "__main__":
    if len(sys.argv) > 2:
        print("Child started: ")
        #print(int(sys.argv[1]))
    else:
        print("Invocation: " + sys.argv[0] + " <PORT>")