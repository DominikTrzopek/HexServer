import json
from CommunicationCodes import ClientStatusType

class TCPConnection():
    def __init__(self, port):
        self.port = port
        self.client_status = ClientStatusType.NOTCONNECTED
        self.client_id = None
        self.client_name = None
        self.addres = None

    def fill_info(self, msg, addr):
        client_data = json.loads(str(msg, 'utf-8')).get("playerInfo")
        self.client_id = client_data.get("id")
        self.client_name = client_data.get("name")
        self.client_status = client_data.get("status")
        self.addres = addr

    def response_with_info(self):
        response = {}
        client_info = {}
        client_info["id"] = self.client_id
        client_info["name"] = self.client_name
        client_info["status"] = self.client_status
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

    def prepare_message(msg):
        return str.encode(json.dumps(msg) + "\n")

