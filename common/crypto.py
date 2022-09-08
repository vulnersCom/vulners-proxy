import base64
import socket
from typing import Union
from binascii import unhexlify
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from httpx._models import Request
from common.config import app_opts


encryption_enabled = bool(int(app_opts.get("enableencryption")))
key = base64.urlsafe_b64encode(app_opts.get("secret").ljust(32, "v").encode())[:32]

cipher = Cipher(algorithms.AES(key), modes.ECB())
block_length = 16


def encrypt(value: Union[str, bytes]) -> str:
    if isinstance(value, str):
        value = value.encode()
    len_value = len(value)
    len_value = len_value + (block_length - len_value) % block_length
    value = value.ljust(len_value, b"\0")
    buf = bytearray(len_value + block_length - 1)
    encryptor = cipher.encryptor()
    len_encrypted = encryptor.update_into(value, buf)
    return f"{len_value}:{base64.b64encode(bytes(buf[:len_encrypted]) + encryptor.finalize()).decode()}".encode().hex()


def decrypt(crypt_value: str) -> str:
    len_value, value = unhexlify(crypt_value).decode().split(":")
    value = base64.b64decode(value)
    buf = bytearray(int(len_value) + block_length - 1)
    decrypter = cipher.decryptor()
    len_decrypted = decrypter.update_into(value, buf)
    return (bytes(buf[:len_decrypted]) + decrypter.finalize()).decode().strip("\0")


def encrypt_parameters(request: Request, parameters: dict, objects: Union[list, tuple] = None) -> dict:
    if not objects:
        return parameters
    host = request.client.host
    for obj in objects:
        if obj in ("ip", "ipaddress"):
            parameters.update({"ip": encrypt(host)})
        if obj == "fqdn":
            name = "unknown"
            try:
                name, *_ = socket.gethostbyaddr(host)
            except (socket.herror, TypeError):
                pass
            parameters.update({"fqdn": encrypt(name)})
        if obj_param := parameters.get(obj):
            parameters.update({obj: encrypt(obj_param)})
    return parameters
