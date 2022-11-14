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
from led_client import LEDClient

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
MAX_UPDATE_RETRIES = 5

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
        exec(open(UPDATE_SCRIPT).read())


check_and_restore(CONFIG_FILE, CONFIG_FILE_BACKUP)
check_and_restore(STATUS_FILE, STATUS_FILE_BACKUP)

lcd = LCD()
leds = LEDClient()

config = configparser.ConfigParser()
config.read(CONFIG_FILE)
status = configparser.ConfigParser()

status.read(STATUS_FILE)

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

update_was_needed = False
retries = 0
while device.needs_package_update() and retries < MAX_UPDATE_RETRIES:
    update_was_needed = True
    retries += 1
    leds.rainbow(10000, 2)
    lcd.long_text("Do not unplug. Searching for updates.", "i", "red")
    if device.get_local_ip() == "127.0.0.1":
        # network has not local IP?
        lcd.long_text("Is network cable connected? Searching for updates.", "M", "red")
    elif not device.reached_repo:
        lcd.long_text("Device cannot reach the internet. Are cables plugged in?", "X", "red")
    device.execute_setuid("1 3")  # run pproxy-update detached
    time.sleep(30)

if update_was_needed:
    if retries == MAX_UPDATE_RETRIES:
        lcd.long_text("Could not finish update. Booting regardless.", "i", "orange")
    else:
        lcd.long_text("Software updated to " + device.get_installed_package_version(), "O", "green")
        # let the service restart
        time.sleep(15)
    leds.blank()
time.sleep(1)

is_claimed = False
server_checkin_done = False
response = None
url_address = config.get('django', 'url') + "/api/device/is_claimed/"
data = json.dumps({'serial_number': config.get('django', 'serial_number')})
headers = {'Content-Type': 'application/json'}

while not server_checkin_done:
    try:
        response = requests.post(url_address, data=data, headers=headers)
        is_claimed = (response.status_code == 200)
        jresponse = json.loads(response.content)
        logger.error("is_claimed updated to " + str(is_claimed))
        leds.progress_wheel_step(color=(255, 255, 255))
    except requests.exceptions.RequestException as exception_error:
        logger.exception("Error in connecting to server for claim status: " + str(exception_error))
        # leds.blink(color=(255, 0, 0),
        #           wait=200,
        #           repetitions=4)
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
            PPROXY_PROCESS = PProxy()
            PPROXY_PROCESS.start()
        except Exception:
            logger.exception("Exception in main runner thread")
            del(PPROXY_PROCESS)
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
            leds.blink(color=(255, 0, 0),
                       wait=50,
                       repetitions=20)
            time.sleep(60)
            continue
        break
