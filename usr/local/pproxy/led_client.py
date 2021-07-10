import os
import sys
import device
import logging
import time
import socket
import os


LM_SOCKET_PATH="/tmp/ledmanagersocket.sock"
LOG_CONFIG="/etc/pproxy/logging-debug.ini"

logging.config.fileConfig(LOG_CONFIG,
        disable_existing_loggers=False)

logger = logging.getLogger("led_client")


class LEDClient:
    def __init__(self):
        self.client = None
        if os.path.exists(LM_SOCKET_PATH):
            self.client = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
            self.client.connect(LM_SOCKET_PATH)

    def __del__(self):
        if self.client is not None:
            self.client.close()

    def set_enabled(self, enabled=True):
        if self.client is None:
            return
        self.send("set_enabled " + str(int(enabled)))


    def send(self, cmd):
        self.client.send(cmd.encode('utf-8'))

    def set_all(self, r, g, b):
        if self.client is None:
            return
        self.send("set_all " +
                str(r) + " " +
                str(g) + " " +
                str(b))

    def blank(self):
        if self.client is None:
            return
        self.send("blank")

    def set_all_slow(self, r, g, b):
        if self.client is None:
            return
        self.send("send_all_slow " +
                str(r) + " " +
                str(g) + " " +
                str(b))

    def progress_wheel_step(self, r, g, b):
        if self.client is None:
            return
        self.send("progress_wheel_step " +
                str(r) + " " +
                str(g) + " " +
                str(b))
