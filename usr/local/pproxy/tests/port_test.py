from diag import WPDiag
import threading
from device import Device
from lcd import LCD
import time
import socket
import sys
import json
import os
import logging
up_dir = os.path.dirname(os.path.abspath(__file__)) + '/../'
sys.path.append(up_dir)

try:
    from self.configparser import configparser
except ImportError:
    import configparser

CONFIG_FILE = '/etc/pproxy/config.ini'

LOG_CONFIG = "/etc/pproxy/logging-debug.ini"
logging.config.fileConfig(LOG_CONFIG,
                          disable_existing_loggers=False)

logger = logging.getLogger("diag")

shutdown = False


def open_listener(host, port):
    print("listener up...")
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(30)
    s.bind((host, port))

    s.listen(1)
    while not shutdown:
        print("Shutdown is " + str(shutdown))
        try:
            conn, addr = s.accept()
            print('Connected by ', addr)
            data = conn.recv(8)
            conn.sendall(data)
            conn.close()
        except socket.timeout:
            continue


# test listing ports
dev = Device(logger)
l, d = dev.get_all_port_mappings()

print("ports = " + str(l))
print("num ports = " + str(d))

os.exit(0)
port = 4092
config = configparser.ConfigParser()
config.read(CONFIG_FILE)
#listener = threading.Thread(target=open_listener,args=['',port])
# listener.setDaemon(False)
# listener.start()
while True:
    WPD = WPDiag(logger)
    local_ip = WPD.get_local_ip()
    print('local ip=' + WPD.get_local_ip())
    WPD.open_test_port(port)

    #print("local port test:" + str(WPD.can_connect_to_internal_port(port)))
    print("remote port test:" + str(WPD.can_connect_to_external_port(port)))
    WPD.close_test_port(port)
    # shutdown=True
    break
# listener._stop()
