import json
import socket
import sys
import time

if __name__ == "__main__":
    if len(sys.argv) > 2:
        print("Child started: ")
        print((sys.argv[1:]))
        while(True):
            print("i am alive")
            time.sleep(2)
    else:
        print("Invocation: " + sys.argv[0] + " <PORT>")