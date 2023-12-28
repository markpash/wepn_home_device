
import os
import logging.config
import sys
up_dir = os.path.dirname(os.path.abspath(__file__)) + '/../'
sys.path.append(up_dir)
from device import Device
from device import random_cron_delay
from ipw import IPW

# commenting out these lines, since ddns runs as user pi
# and user pi cannot write to the error.log file
# DO NOT RE-ENABLE THESE LOGS
# LOG_CONFIG = "/etc/pproxy/logging.ini"
# logging.config.fileConfig(LOG_CONFIG, disable_existing_loggers=False)
logger = logging.getLogger("ddns")

random_cron_delay(sys.argv[1:])

device = Device(logger)
ipw = IPW()
ip_address = ipw.myip()

device.update_dns(ip_address)
