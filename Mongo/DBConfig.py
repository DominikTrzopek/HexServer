class Config():

    @staticmethod
    def get_credentials():
        return "mongodb://root:pass@0.0.0.0:8081/",

    @staticmethod
    def get_db_name():
        return "Hex"

    @staticmethod
    def get_server_collection():
        return "servers"

    @staticmethod
    def get_test_collection():
        return "test"
