class Config(object):

    @staticmethod
    def credentials():
        return "mongodb://root:pass@0.0.0.0:8081/",

    @staticmethod
    def db_name():
        return "Hex"

    @staticmethod
    def server_collection():
        return "servers"

    @staticmethod
    def test_collection():
        return "test"
