from pproxy import PProxy
import time
from oled import OLED as OLED
from setup.onboard import OnBoard
import requests, json
import logging.config
from device import Device


try:
    from self.configparser import configparser
except ImportError:
    import configparser

CONFIG_FILE='/etc/pproxy/config.ini'
STATUS_FILE='/var/local/pproxy/status.ini'
LOG_CONFIG="/etc/pproxy/logging.ini"
logging.config.fileConfig(LOG_CONFIG,
            disable_existing_loggers=False)
logger = logging.getLogger("startup")
logger.critical("Starting WEPN")

oled = OLED()

config = configparser.ConfigParser()
config.read(CONFIG_FILE)
status = configparser.ConfigParser()
status.read(STATUS_FILE)
oled.set_led_present(config.get('hw','led'))
oled.show_logo()
time.sleep(1)

is_claimed = False
server_checkin_done = False
response = None
url_address = config.get('django','url') + "/api/device/is_claimed/"
data = json.dumps({'serial_number': config.get('django','serial_number')})
headers = {'Content-Type': 'application/json'}
try:
  response = requests.post(url_address, data=data, headers=headers)
  is_claimed = (response.status_code == 200)
  jresponse = json.loads(response.content)
  logger.error("is_claimed updated to " + str(is_claimed))
  server_checkin_done = True
except requests.exceptions.RequestException as exception_error:
  logger.error("Error in connecting to server for claim status")


if 1 == int(status.get('status','claimed')):
    if not is_claimed and server_checkin_done:
        # server says device is not claimed, so wipe it
        logger.error("Server says unclaimed, locally cached claimed. Wiping")
        status['status']['mqtt-reason'] = '0'
        status['status']['claimed'] = '0'
        status['status']['mqtt'] = '0'
        status['status']['state'] = '3'
        with open(STATUS_FILE, 'w') as statusfile:
           status.write(statusfile)
        #reboot to go into onboarding
        device = Device(logger)
        device.reboot()

    while True:
          try:
             PPROXY_PROCESS = PProxy()
             PPROXY_PROCESS.start()
          except:
              del(PPROXY_PROCESS) 
              logger.debug("Retrying in 60 seconds ....")
              time.sleep(60)
              continue
          break
else:
    while True:
          try:
             ONBOARD = OnBoard()
             if is_claimed:
                 for name, key in status.items("previous_keys"):
                     logger.debug("Trying an old key: " + name + " , " + key)
                     ONBOARD.set_rand_key(key)
                     ONBOARD.start(True)
             ONBOARD.start()
          except Exception as e:
              logger.error("Exception in onboarding:" + str(e))
              if ONBOARD:
                  del(ONBOARD) 
              logger.debug("Retrying in 60 seconds ....")
              time.sleep(60)
              continue
          break

