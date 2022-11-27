
import threading
import time
import socket
import sys
import json
import os
import logging
up_dir = os.path.dirname(os.path.abspath(__file__)) + '/../'
sys.path.append(up_dir)
from device import Device # NOQA
from diag import WPDiag # NOQA
from lcd import LCD # NOQA

try:
    from self.configparser import configparser
except ImportError:
    import configparser

CONFIG_FILE = '/etc/pproxy/config.ini'

LOG_CONFIG = "/etc/pproxy/logging-debug.ini"
logging.config.fileConfig(LOG_CONFIG,
                          disable_existing_loggers=False)

logger = logging.getLogger("diag")
logger.setLevel(logging.INFO)

WPD = WPDiag(logger)
D = Device(logger)
print("5000 in blocked? " + str(WPD.check_port_in_blocked(5000)))
print("6000 in blocked? " + str(WPD.check_port_in_blocked(6000)))
print("9051 in blocked? " + str(WPD.check_port_in_blocked(9051)))
print("Testing 80, it should fail")
WPD.check_port_locally_in_use(80)
print("Testing 801, this is tricky since less than 1024")
WPD.check_port_locally_in_use(801)
print("This should pass, 8077")
WPD.check_port_locally_in_use(8077)

print("--------------------------------5001------------------------------------------")
# print(WPD.find_next_good_port(5000))
assert(WPD.find_next_good_port(5000) == (5001, 0))

print("--------------------------------5003------------------------------------------")
# port 5000 is blocked
# open a server on port 5001 so it is in use
WPD.open_test_port(5001)
# redirect port 5002 to another port so that fails too
D.open_port(80, "Unit Test", 5002, 1000)
print(">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>")
D.check_port_mapping_igd()
# assert next good port is port 5003
assert(WPD.find_next_good_port(5000) == (5003, 0))

print("-------------------------------THIS MEANS ALL GOOD ----------------------------")
