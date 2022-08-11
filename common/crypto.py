import base64
from typing import Union
from binascii import unhexlify
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
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
    decryptor = cipher.decryptor()
    len_decrypted = decryptor.update_into(value, buf)
    return (bytes(buf[:len_decrypted]) + decryptor.finalize()).decode().strip("\0")
