import base64
from cryptography.fernet import Fernet
from common.config import app_opts


encryption_enabled = app_opts.get('enableencryption')
secret = base64.urlsafe_b64encode(app_opts.get('secret').ljust(32, '_')[:32].encode())
fernet = Fernet(secret)
