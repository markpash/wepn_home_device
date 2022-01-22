from pproxy import PProxy
import time
from lcd import LCD as LCD
from setup.onboard import OnBoard
import requests
import json
import logging.config
from device import Device
import os
from shutil import copyfile

try:
    from self.configparser import configparser
except ImportError:
    import configparser

CONFIG_FILE = '/etc/pproxy/config.ini'
CONFIG_FILE_BACKUP = '/var/local/pproxy/config.bak'
STATUS_FILE = '/var/local/pproxy/status.ini'
STATUS_FILE_BACKUP = '/var/local/pproxy/status.bak'
LOG_CONFIG = "/etc/pproxy/logging.ini"
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
        exec(open(UPDATE_SCRIPT).read())  # nosec: fixed file path


check_and_restore(CONFIG_FILE, CONFIG_FILE_BACKUP)
check_and_restore(STATUS_FILE, STATUS_FILE_BACKUP)

lcd = LCD()

config = configparser.ConfigParser()
config.read(CONFIG_FILE)
status = configparser.ConfigParser()

status.read(STATUS_FILE)
lcd.set_lcd_present(config.get('hw', 'lcd'))
lcd.show_logo()
time.sleep(1)

device = Device(logger)
gateway_vendor = device.get_default_gw_vendor()
logger.critical("Gateway vendor= " + str(gateway_vendor))
device.check_port_mapping_igd()

is_claimed = False
server_checkin_done = False
response = None
url_address = config.get('django', 'url') + "/api/device/is_claimed/"
data = json.dumps({'serial_number': config.get('django', 'serial_number')})
headers = {'Content-Type': 'application/json'}
try:
    response = requests.post(url_address, data=data, headers=headers)
    is_claimed = (response.status_code == 200)
    jresponse = json.loads(response.content)
    logger.error("is_claimed updated to " + str(is_claimed))
    server_checkin_done = True
except requests.exceptions.RequestException as exception_error:
    logger.exception("Error in connecting to server for claim status: " + str(exception_error))


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
            PPROXY_PROCESS = PProxy()
            PPROXY_PROCESS.start()
        except Exception:
            logger.exception("Exception in main runner thread")
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
        except Exception:
            logger.exception("Exception in onboarding")
            if ONBOARD:
                del(ONBOARD)
            logger.debug("Retrying in 60 seconds ....")
            time.sleep(60)
            continue
        break
