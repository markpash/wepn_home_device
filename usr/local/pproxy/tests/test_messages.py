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
print(messages.get_messages())

print("="*10)
messages.send_msg("test message", "DEVICE", "xx", False, msg_type="test")
print("="*10)
messages.send_msg("test secure message", "DEVICE", "xx", True, msg_type="test secure")
print("="*10)

print(messages.get_messages())

msgs = messages.get_messages()
for msg in msgs:
    if msg["message_body"]["is_secure"]:
        print("got a secure message")
        # TODO: check decryption of it
    print(f'marking meessage {msg["id"]} as read')
    messages.mark_msg_read(msg["id"])

print(messages.get_messages())


