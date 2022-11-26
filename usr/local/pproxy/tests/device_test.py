
import logging.config
import logging
import os
import sys
up_dir = os.path.dirname(os.path.abspath(__file__)) + '/../'
sys.path.append(up_dir)
from device import Device  # NOQA
import device  # NOQA

LOG_CONFIG = "/etc/pproxy/logging-debug.ini"

logging.config.fileConfig(LOG_CONFIG,
                          disable_existing_loggers=False)

logger = logging.getLogger("device")
device = Device(logger)
device.find_igds()
print(device.get_default_gw_mac())
print(device.get_default_gw_ip())
print(device.get_default_gw_vendor())
device.wait_for_internet()
print("Repo has version: " + device.repo_pkg_version)
print("Device has version: " + device.get_installed_package_version())
print("Needs update? " + str(device.needs_package_update()))
print("0day? " + str(device.get_min_ota_version()))
print(device.get_repo_package_version())
