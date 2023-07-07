
import configparser
import json
import logging.config

import requests

from constants import LOG_CONFIG

CONFIG_FILE = '/etc/pproxy/config.ini'
STATUS_FILE = '/var/local/pproxy/status.ini'
logging.config.fileConfig(LOG_CONFIG,
                          disable_existing_loggers=False)


class Messages():
    def __init__(self, logger=None) -> None:
        self.config = configparser.ConfigParser()
        self.config.read(CONFIG_FILE)
        self.pending_items = []
        if logger is not None:
            self.logger = logger
        else:
            self.logger = logging.getLogger("messages")
        pass

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
        response = requests.get(url, data=data_json, headers=headers)
        for msg in response.json():
            self.pending_items.append(msg["id"])
        return response.json()

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
        response = requests.patch(url, data=data_json, headers=headers)
        if response.status_code != 200:
            self.logger.critical("Cannot mark message as read: " + str(response.content))
            try:
                self.pending_items.remove(id)
            except ValueError:
                self.logger.critical("Message " + str(id) + "was marked as read, but it was not pending")
        return response
