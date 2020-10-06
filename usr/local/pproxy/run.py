from pproxy import PProxy
import time
from oled import OLED as OLED
from setup.onboard import OnBoard
import requests, json


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
          is_claimed = False 
          response = None
          url_address = config.get('django','url') + "/api/device/is_claimed/"
          data = json.dumps({'serial_number': config.get('django','serial_number')})
          headers = {'Content-Type': 'application/json'}
          try:
              response = requests.post(url_address, data=data, headers=headers)
              is_claimed = (response.status_code == 200)
              jresponse = json.loads(response.content)
              print("is_claimed updated to " + str(is_claimed))
          except requests.exceptions.RequestException as exception_error:
              print("Error in connecting to server for claim status")
          try:
             ONBOARD = OnBoard()
             if is_claimed:
                 for name, key in status.items("previous_keys"):
                     print("Trying an old key: " + name + " , " + key)
                     ONBOARD.set_rand_key(key)
                     ONBOARD.start(True)
             ONBOARD.start()
          except Exception as e:
              print("Exception in onboarding")
              print(e)
              if ONBOARD:
              del(ONBOARD) 
              print("Retrying in 60 seconds ....")
              time.sleep(60)
              continue
          break

