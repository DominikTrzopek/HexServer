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

    def response_with_info(self, new_status = None):
        response = {}
        client_info = {}
        if new_status == None:
            new_status = self.client_status
        client_info["id"] = self.client_id
        client_info["name"] = self.client_name
        client_info["status"] = new_status
        response["playerInfo"] = client_info
        return str.encode(json.dumps(response) + "\n")

    def collect_message(msg):
        return json.loads(str(msg, 'utf-8'))

    def prepare_message(msg):
        return str.encode(json.dumps(msg) + "\n")

