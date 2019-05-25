from pproxy import PProxy
import time
from oled import OLED as OLED
import os
from setup.onboard import OnBoard

try:
    from self.configparser import configparser
except ImportError:
    import configparser

CONFIG_FILE='/etc/pproxy/config.ini'
STATUS_FILE='/var/local/pproxy/status.ini'

oled = OLED()

config = configparser.ConfigParser()
config.read(CONFIG_FILE)
status = configparser.ConfigParser()
status.read(STATUS_FILE)
oled.set_led_present(config.get('hw','led'))
oled.show_logo()


try:
    if 1 == int(status.get('status','claimed')):
        PPROXY_PROCESS = PProxy()
        PPROXY_PROCESS.start()
    else:
        ONBOARD = OnBoard()
        ONBOARD.start()
except Exception as e:
    print("Error caught in debug:")
    print(type(e).__name__)
    raise
