from enum import IntEnum


class RequestType(IntEnum):
    GET = 0
    CREATE = 1
    DELETE = 2


class ResponseType(IntEnum):
    SUCCESS = 0
    ENDOFMESSAGE = 1    # End of server list (get)
    BADREQUEST = 2      # No request type scpecified
    BADARGUMENTS = 3    # No required arguments in request
    TCPSERVERFAIL = 4   # TCP process fail to start
    WRONGPASSWORD = 5   # Wrong password
    BADPLAYERDATA = 6   # Missing player information
    BADCONNECTION = 7   # Broken connect msg json

class ClientStatusType(IntEnum):
    NOTCONNECTED = 0,
    NOTREADY = 1,
    READY = 2,
    INGAGME = 3
