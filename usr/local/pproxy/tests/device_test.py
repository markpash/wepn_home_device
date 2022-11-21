
from device import Device
import logging.config
import logging
import device
import os
import sys
up_dir = os.path.dirname(os.path.abspath(__file__)) + '/../'
sys.path.append(up_dir)

LOG_CONFIG = "/etc/pproxy/logging-debug.ini"

logging.config.fileConfig(LOG_CONFIG,
                          disable_existing_loggers=False)

logger = logging.getLogger("device")
device = Device(logger)
device.find_igds()
print(device.get_default_gw_mac())
print(device.get_default_gw_ip())
print(device.get_default_gw_vendor())
device.check_port_locally_in_use(80)
