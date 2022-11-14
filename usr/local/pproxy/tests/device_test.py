
import os
import sys
up_dir = os.path.dirname(os.path.abspath(__file__))+'/../'
sys.path.append(up_dir)
import device
import logging
import logging.config
from device import Device

LOG_CONFIG="/etc/pproxy/logging-debug.ini"

logging.config.fileConfig(LOG_CONFIG,
        disable_existing_loggers=False)

logger = logging.getLogger("device")
device = Device(logger)
#print(device.get_default_gw_mac())
#print(device.get_default_gw_ip())
#print(device.get_default_gw_vendor())
device.wait_for_internet()
print("Repo has version: " + device.repo_pkg_version)
print("Device has version: " + device.get_installed_package_version())
print("Needs update? " + str(device.needs_package_update()))
#print(device.get_repo_package_version())
