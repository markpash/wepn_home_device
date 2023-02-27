
import sys
import os
import logging
import logging.config
up_dir = os.path.dirname(os.path.abspath(__file__))+'/../'
sys.path.append(up_dir)

from ipw import IPW
from shadow import Shadow
from openvpn import OpenVPN
from services import Services
from device import Device
try:
    from self.configparser import configparser
except ImportError:
    import configparser

CONFIG_FILE='/etc/pproxy/config.ini'

LOG_CONFIG="/etc/pproxy/logging-debug.ini"
logging.config.fileConfig(LOG_CONFIG,
            disable_existing_loggers=False)

l = logging.getLogger("onboarding")
ipw = IPW()
s   = Shadow(l)
o   = OpenVPN(l)
a   = Services(l)
device = Device(l)

s.recover_missing_servers()
