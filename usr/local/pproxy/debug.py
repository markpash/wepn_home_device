from pproxy import PProxy
import time
from oled import OLED as OLED
import os

try:
    from self.configparser import configparser
except ImportError:
    import configparser

CONFIG_FILE='/etc/pproxy/config.ini'

oled = OLED()

config = configparser.ConfigParser()
config.read(CONFIG_FILE)
oled.set_led_present(config.get('hw','led'))
oled.show_logo()


PPROXY_PROCESS = PProxy()
try:
    PPROXY_PROCESS.start()
except Exception as e:
    print(type(e).__name__)
    raise
