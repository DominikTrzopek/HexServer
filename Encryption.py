import hashlib

def id_len():
    return 8


def hash(word):
    val = int(hashlib.sha256(word.encode('utf-8')).hexdigest(), 16) % 10**16
    return str(val) 
