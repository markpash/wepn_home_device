from pproxy import PProxy
import time
from oled import OLED as OLED
import os
from setup.onboard import OnBoard
import logging

try:
    from self.configparser import configparser
except ImportError:
    import configparser

CONFIG_FILE='/etc/pproxy/config.ini'
STATUS_FILE='/var/local/pproxy/status.ini'

LOG_CONFIG="/etc/pproxy/logging-debug.ini"
logging.config.fileConfig(LOG_CONFIG,
            disable_existing_loggers=False)

logger = logging.getLogger("debug-pproxy")

oled = OLED()

config = configparser.ConfigParser()
config.read(CONFIG_FILE)
status = configparser.ConfigParser()
status.read(STATUS_FILE)
oled.set_led_present(config.get('hw','led'))
oled.show_logo()


try:
    if 1 == int(status.get('status','claimed')):
        PPROXY_PROCESS = PProxy(logger)
        #PPROXY_PROCESS.set_logger(logger)
        PPROXY_PROCESS.start()
    else:
        ONBOARD = OnBoard()
        ONBOARD.start()
except Exception as e:
    print("Error caught in debug:")
    print(type(e).__name__)
    raise
