
import base64
import configparser
import json
import os
import logging.config
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.backends import default_backend

import requests

from constants import LOG_CONFIG

CONFIG_FILE = '/etc/pproxy/config.ini'
STATUS_FILE = '/var/local/pproxy/status.ini'
GET_TIMEOUT = 10
logging.config.fileConfig(LOG_CONFIG,
                          disable_existing_loggers=False)


class Messages():
    def __init__(self, logger=None) -> None:
        self.config = configparser.ConfigParser()
        self.config.read(CONFIG_FILE)
        self.status = configparser.ConfigParser()
        self.status.read(STATUS_FILE)
        self.pending_items = []
        if logger is not None:
            self.logger = logger
        else:
            self.logger = logging.getLogger("messages")
        pass

    def e2ee_available(self):
        # this can be expanded to check server capability
        return self.status.has_option('status', 'e2e_key')

    def get_messages(self, is_read=False, is_expired=False):
        url = self.config.get('django', 'url') + "/api/message/"
        data = {
            "serial_number": self.config.get('django', 'serial_number'),
            "device_key": self.config.get('django', 'device_key'),
            "is_read": is_read,
            "destination": "DEVICE",
            "is_expired": is_expired,
        }
        headers = {"Content-Type": "application/json"}
        data_json = json.dumps(data)
        response = requests.get(url, data=data_json, headers=headers, timeout=GET_TIMEOUT)
        all_messages = []
        for msg in response.json():
            self.pending_items.append(msg["id"])
            try:
                if "message_body" in msg and "is_secure" in msg["message_body"]:
                    if msg["message_body"]["is_secure"]:
                        # TODO: return this updated array instead
                        msg_nonce = str.encode(msg["message_body"]["nonce"])
                        msg_txt = msg["message_body"]["message"]
                        msg["message_body"]["decrypted"] = self.decrypt_message(msg_txt, msg_nonce)
            except KeyError as e:
                print("key not found:" + str(e))
            except Exception as d:
                print("key not found:" + str(d))
            all_messages.append(msg)
        return all_messages

    def mark_msg_read(self, id):
        url = self.config.get('django', 'url') + "/api/message/" + str(id) + "/"
        data = {
            "serial_number": self.config.get('django', 'serial_number'),
            "device_key": self.config.get('django', 'device_key'),
            "is_read": True,
        }
        headers = {"Content-Type": "application/json"}
        data_json = json.dumps(data)
        self.logger.info(data_json)
        response = requests.patch(url, data=data_json, headers=headers, timeout=GET_TIMEOUT)
        if response.status_code != 200:
            self.logger.critical("Cannot mark message as read: " + str(response.content))
            try:
                self.pending_items.remove(id)
            except ValueError:
                self.logger.critical("Message " + str(id) + "was marked as read, but it was not pending")
        return response

    def send_msg(self, text, destination="APP", cert_id="", secure=True):
        nonce = ""
        if secure:
            secure_text, nonce = self.encrypt_message(text)
            text = base64.urlsafe_b64encode(secure_text).decode("utf-8")
            nonce = base64.urlsafe_b64encode(nonce).decode("utf-8")
        url = self.config.get('django', 'url') + "/api/message/"
        data = {
            "serial_number": self.config.get('django', 'serial_number'),
            "device_key": self.config.get('django', 'device_key'),
            "message_body": {
                "message": text,
                "is_secure": secure,
                "cert_id": cert_id,
                "nonce": nonce
            },
            "destination": destination.upper(),
            "is_read": False,
            "is_expired": False,
        }
        headers = {"Content-Type": "application/json"}
        data_json = json.dumps(data)
        response = requests.post(url, data=data_json, headers=headers, timeout=GET_TIMEOUT)
        if response.status_code != 201:
            self.logger.critical("Could not send message: " + str(response.text))

    def encrypt_message(self, private_msg):
        key = base64.urlsafe_b64decode(str(self.status.get('status', 'e2e_key')))
        nonce = os.urandom(12)
        encryptor = Cipher(algorithms.AES(key), modes.GCM(nonce), default_backend()).encryptor()
        padder = padding.PKCS7(algorithms.AES(key).block_size).padder()
        padded_data = padder.update(base64.b64encode(str.encode(private_msg))) + padder.finalize()
        encrypted_text = encryptor.update(padded_data) + encryptor.finalize()
        return encrypted_text, nonce

    def decrypt_message(self, encoded_encrypted_msg, nonce):
        key = base64.urlsafe_b64decode(str(self.status.get('status', 'e2e_key')))
        encoded_encrypted_msg = base64.urlsafe_b64decode(encoded_encrypted_msg)
        nonce = base64.urlsafe_b64decode(nonce)
        padder = padding.PKCS7(algorithms.AES(key).block_size).padder()
        decryptor = Cipher(algorithms.AES(key), modes.GCM(nonce), default_backend()).decryptor()
        decrypted_data = decryptor.update(encoded_encrypted_msg)
        unpadded = padder.update(decrypted_data) + padder.finalize()
        clear_text = base64.b64decode(unpadded).decode("utf-8")
        self.logger.info(clear_text)
        return clear_text
