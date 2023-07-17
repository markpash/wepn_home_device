import base64
import json

import requests
import os
import sys
import logging


up_dir = os.path.dirname(os.path.abspath(__file__)) + '/../'
sys.path.append(up_dir)
from lcd import LCD  # noqa
from messages import Messages

try:
    from configparser import configparser
except ImportError:
    import configparser
messages = Messages()
#messages.send_msg("added user 8", secure=True)
messages.get_messages()
exit(1)

CONFIG_FILE = '/etc/pproxy/config.ini'
LOG_CONFIG="/etc/pproxy/logging-debug.ini"
logging.config.fileConfig(LOG_CONFIG,
            disable_existing_loggers=False)

logger = logging.getLogger("diag")
lcd = LCD()
config = configparser.ConfigParser()
config.read(CONFIG_FILE)

headers = {"Content-Type": "application/json"}

data = {
    "serial_number": config.get('django', 'serial_number'),
    "device_key": config.get('django', 'device_key'),
}


data_json = json.dumps(data)
url = config.get('django', 'url') + "/api/message/"
try:
    response = requests.get(url, data=data_json, headers=headers)
    logger.debug("Response to messages" + str(response.status_code))
    print(response.text)
except requests.exceptions.RequestException as exception_error:
    logger.error(
        "Error in sending messages: \r\n\t" + str(exception_error))

