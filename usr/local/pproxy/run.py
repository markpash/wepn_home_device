from setup.onboard import OnBoard
from shutil import copyfile
import json
import logging.config
import os
import requests
import time

from device import Device
from lcd import LCD as LCD
from led_client import LEDClient
from pproxy import PProxy

try:
    from self.configparser import configparser
except ImportError:
    import configparser

from constants import LOG_CONFIG

CONFIG_FILE = '/etc/pproxy/config.ini'
CONFIG_FILE_BACKUP = '/var/local/pproxy/config.bak'
STATUS_FILE = '/var/local/pproxy/status.ini'
STATUS_FILE_BACKUP = '/var/local/pproxy/status.bak'
UPDATE_SCRIPT = "/usr/local/pproxy/setup/update_config.py"

logging.config.fileConfig(LOG_CONFIG,
                          disable_existing_loggers=False)
logger = logging.getLogger("startup")
logger.critical("Starting WEPN")


# check if INI configs are corrupted
# restore and upgrade as needed
def check_and_restore(conf, backup):
    if not os.path.exists(conf) or os.stat(conf).st_size == 0:
        if os.path.exists(backup):
            copyfile(backup, conf)
        # backup might have been created before
        # new changes were made. Do upgrades
        exec(open(UPDATE_SCRIPT).read())  # nosec: fixed path python file


check_and_restore(CONFIG_FILE, CONFIG_FILE_BACKUP)
check_and_restore(STATUS_FILE, STATUS_FILE_BACKUP)

lcd = LCD()
leds = LEDClient()

config = configparser.ConfigParser()
config.read(CONFIG_FILE)
status = configparser.ConfigParser()

status.read(STATUS_FILE)
status['status']['booting'] = '1'
status['status']['hb_to_warm'] = '3'
with open(STATUS_FILE, 'w') as statusfile:
    status.write(statusfile)

device = Device(logger)
gateway_vendor = device.get_default_gw_vendor()
logger.critical("Gateway vendor= " + str(gateway_vendor))
device.check_port_mapping_igd()

lcd.set_lcd_present(config.get('hw', 'lcd'))
lcd.set_logo_text("Loading ...")
lcd.show_logo()

# below section will block until connected to the internet
# AND the software version on device is latest.
# If not the same, it will run software update in background
# and keep the message and wheel going until version is the same.

# this blocks boot until version is updated to latest
device.software_update_blocking(lcd, leds)
time.sleep(1)

is_claimed = False
server_checkin_done = False
response = None
url_address = config.get('django', 'url') + "/api/device/is_claimed/"
data = json.dumps({'serial_number': config.get('django', 'serial_number')})
headers = {'Content-Type': 'application/json'}

while not server_checkin_done:
    try:
        response = requests.post(url_address, data=data, headers=headers, timeout=10)
        is_claimed = (response.status_code == 200)
        logger.error("is_claimed updated to " + str(is_claimed))
        leds.progress_wheel_step(color=(255, 255, 255))
    except requests.exceptions.RequestException:
        logger.error("Error in connecting to server for claim status")
        # leds.blink(color=(255, 0, 0),
        #           wait=200,
        #           repetitions=4)
        time.sleep(30)
    else:
        server_checkin_done = True

if 1 == int(status.get('status', 'claimed')):
    if not is_claimed and server_checkin_done:
        # server says device is not claimed, so wipe it
        logger.error("Server says unclaimed, locally cached claimed. Wiping")
        status['status']['mqtt-reason'] = '0'
        status['status']['claimed'] = '0'
        status['status']['mqtt'] = '0'
        status['status']['state'] = '3'
        with open(STATUS_FILE, 'w') as statusfile:
            status.write(statusfile)
        # reboot to go into onboarding
        device.reboot()

    while True:
        try:
            status['status']['booting'] = '0'
            with open(STATUS_FILE, 'w') as statusfile:
                status.write(statusfile)
            PPROXY_PROCESS = PProxy()
            PPROXY_PROCESS.start()
        except Exception:
            logger.exception("Exception in main runner thread")
            del (PPROXY_PROCESS)
            logger.debug("Retrying in 60 seconds ....")
            leds.blink(color=(255, 0, 0),
                       wait=200,
                       repetitions=10)
            time.sleep(60)
            continue
        break
else:
    while True:
        try:
            status['status']['booting'] = '0'
            with open(STATUS_FILE, 'w') as statusfile:
                status.write(statusfile)
            ONBOARD = OnBoard()
            if is_claimed:
                for name, key in status.items("previous_keys"):
                    logger.debug("Trying an old key: " + name + " , " + key)
                    ONBOARD.set_rand_key(key)
                    ONBOARD.start(True)
            ONBOARD.start()
        except Exception:
            logger.exception("Exception in onboarding")
            if ONBOARD:
                del (ONBOARD)
            logger.debug("Retrying in 60 seconds ....")
            leds.blink(color=(255, 0, 0),
                       wait=50,
                       repetitions=20)
            time.sleep(60)
            continue
        break
