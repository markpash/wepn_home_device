from pproxy import PProxy
import time
from oled import OLED as OLED
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
time.sleep(5)

if 1 == int(status.get('status','claimed')):
    while True:
          try:
             PPROXY_PROCESS = PProxy()
             PPROXY_PROCESS.start()
          except:
              del(PPROXY_PROCESS) 
              print("Retrying in 60 seconds ....")
              time.sleep(60)
              continue
          break
else:
    while True:
          try:
             ONBOARD = OnBoard()
             ONBOARD.start()
          except:
              del(ONBOARD) 
              print("Retrying in 60 seconds ....")
              time.sleep(60)
              continue
          break

