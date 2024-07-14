import math
import hmac
import hashlib

def generate_value(server, client, _nonce, _type):
    server_seed = server.encode()
    client_seed = client.encode()
    nonce = str(_nonce).encode()

    _hash = hmac.new(server_seed, client_seed + b":" + nonce + b":" + "0".encode(), hashlib.sha256).digest()
    f4 = _hash[:4]

    x = 1
    y = 0
    for buff in f4:
        y += int(buff) / (256 ** x)
        x += 1

    if _type == "limbo":
        y *= 16777216
        return 16777216 / (y + 1) * (1 - 0.01)
    elif _type == "dice":
        y *= 10001
        return y / 100