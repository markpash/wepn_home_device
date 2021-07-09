from pproxy import PProxy
import time
from lcd import LCD as LCD
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

lcd = LCD()

config = configparser.ConfigParser()
config.read(CONFIG_FILE)
status = configparser.ConfigParser()
status.read(STATUS_FILE)
lcd.set_lcd_present(config.get('hw','lcd'))
lcd.show_logo()


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
