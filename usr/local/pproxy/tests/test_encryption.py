from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
import base64

with open("local_server/wepn-local.key", "rb") as f:
    key = f.read()

private_key = serialization.load_pem_private_key(key, password=None, backend=default_backend())
public_key = private_key.public_key()

enc = public_key.encrypt(b"Hello", padding.OAEP(
    mgf=padding.MGF1(algorithm=hashes.SHA256()),
    algorithm=hashes.SHA256(),
    label=None
))
print(base64.b64encode(enc))
dec = private_key.decrypt(enc, padding.OAEP(
    mgf=padding.MGF1(algorithm=hashes.SHA256()),
    algorithm=hashes.SHA256(),
    label=None
))
print(dec)
