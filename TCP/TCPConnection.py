import json
from CommunicationCodes import ClientStatusType
from Encryption import id_len

class TCPConnection():
    def __init__(self, port):
        self.port = port
        self.client_status = ClientStatusType.NOTCONNECTED
        self.client_id = None
        self.client_name = None
        self.addres = None
        self.secret_id = None
        self.thread_number = -1

    def fill_info(self, msg, addr, thread):
        client_data = msg.get("playerInfo")
        self.client_id = client_data.get("id")
        if(client_data.get("secretId") != None and client_data.get("secretId") != ""):
            self.secret_id = client_data.get("secretId")
        self.client_name = client_data.get("name")
        self.client_status = client_data.get("status")
        self.thread_number = thread
        self.addres = addr

    def response_with_info(self):
        response = {}
        client_info = {}
        client_info["id"] = self.client_id
        client_info["name"] = self.client_name
        client_info["status"] = self.client_status
        client_info["number"] = self.thread_number
        response["playerInfo"] = client_info
        return response

    def clear_info(self):
        self.client_status = ClientStatusType.NOTCONNECTED
        self.client_name = None
        self.addres = None

    def clear_id(self):
        self.client_id = None

    def collect_message(msg):
        try:
            collected = json.loads(str(msg, 'utf-8'))
        except (TypeError, ValueError):
            return ""
        return collected

    def prepare_error_response(response_code, message=""):
        response = {}
        response["code"] = response_code
        response["errorMessage"] = message
        return str.encode(json.dumps(response))

    def prepare_message(msg):
        return str.encode(json.dumps(msg) + "\n")

