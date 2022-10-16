from enum import IntEnum
from pickle import GET
from sre_constants import SUCCESS
from venv import create

class RequestType(IntEnum):
    GET = 0
    CREATE = 1

class ResponseType(IntEnum):
    SUCCESS = 0
    BADREQUEST = 1      # No request type scpecified
    BADARGUMENTS = 2    # No required arguments in request
    ENDOFMESSAGE = 3    # End of server list 